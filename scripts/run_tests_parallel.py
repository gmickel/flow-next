#!/usr/bin/env python3
"""File-level parallel unittest runner for plugins/flow-next/tests (fn-119).

Discovers top-level test_*.py files and runs each as its own unittest discover
subprocess. Default concurrency is the full cpu_count on CI (`CI` set to
1/true/yes) and max(1, cpu_count - 2) locally. Shards by FILE only (never
splits within a file). Stdlib only - no pytest.

Exit codes:
  0  all matched files passed (or --list-only)
  1  one or more files failed / errored
  2  usage / discovery error (including zero files matched)

Examples:
  ./scripts/run_tests_parallel.py
  ./scripts/run_tests_parallel.py --serial
  ./scripts/run_tests_parallel.py --jobs 4
  ./scripts/run_tests_parallel.py --shuffle
  ./scripts/run_tests_parallel.py --pattern 'test_banner*.py'
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import random
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TESTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "tests"
DEFAULT_PATTERN = "test_*.py"

RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
FAIL_SUMMARY_RE = re.compile(
    r"^FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?(?:, )?(?:skipped=(\d+))?\)",
    re.MULTILINE,
)
OK_SKIPPED_RE = re.compile(r"^OK \(skipped=(\d+)\)", re.MULTILINE)

# Post-kill output collection is BOUNDED: after the process tree is killed the
# pipe should hit EOF immediately, but an unreachable descendant must not be
# able to stall the runner a second time. 15s is generous for draining a pipe
# and still small next to any per-file timeout.
POST_KILL_COLLECT_S = 15
# Windows-only: how long the `taskkill /T` call itself may take.
TREE_KILL_TIMEOUT_S = 30


@dataclass
class FileResult:
    path: Path
    returncode: int
    ran: int
    failures: int
    errors: int
    skipped: int
    elapsed_s: float
    output: str

    @property
    def ok(self) -> bool:
        # ran == 0 with a zero exit is a silent no-op file (e.g. pytest-style
        # module-level functions unittest cannot discover) - fail it loudly.
        return self.returncode == 0 and self.ran > 0


def _default_jobs() -> int:
    """Concurrent file shards to use when neither --jobs nor --serial is given.

    Two cases, CI and local. The two-core reservation exists for machines with a
    human on them: locally this runner competes with an editor, a language
    server and whatever agent is driving the session, so leaving headroom keeps
    the box usable. A build machine has none of that - reserving there just
    leaves cores idle for the whole run.

    The signal is the vendor-neutral `CI` variable rather than
    `GITHUB_ACTIONS`, because the scope is "any build machine" and every
    mainstream CI sets it. Truthy is exactly {1, true, yes} after strip+lower;
    absent, empty, "false", "0" and anything unrecognized all mean local. TTY
    state is deliberately NOT part of this - a redirected local run is still a
    local run.

    New precedent, on purpose: nothing else in this repo branches on "am I on
    CI". The one live convention is `RUNNER_OS`, which only ever branches on
    operating system (.github/workflows/test-flow-next.yml, the smoke scripts).

    `CI` alone is not sufficient: Cursor's agent shell sets `CI=1` on a
    developer machine (documented in
    plugins/flow-next/skills/flow-next-setup/workflow.md), which is precisely
    the case the reservation protects - the editor and the agent driving the
    session are both competing for those cores. `CURSOR_AGENT` is Cursor's own
    canonical signal, so its presence forces the local branch. Hosted runners
    never set it, so this cannot mis-detect real CI. Note `CURSOR_AGENT` is
    inherited by child processes; that is the desired behavior here, because a
    process spawned from a Cursor agent shell is still running on the
    developer's machine.
    """
    cpus = os.cpu_count() or 2
    ci = os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    if os.environ.get("CURSOR_AGENT", "").strip():
        ci = False
    if ci:
        return max(1, cpus)
    return max(1, cpus - 2)


def _discover(
    tests_dir: Path, pattern: str, excludes: Sequence[str]
) -> Tuple[List[Path], List[str]]:
    """Return (sorted matching test files, excluded names actually matched)."""
    if not tests_dir.is_dir():
        raise FileNotFoundError("tests dir not found: {}".format(tests_dir))
    files = sorted(p for p in tests_dir.glob(pattern) if p.is_file())
    excluded = [p.name for p in files if p.name in set(excludes)]
    files = [p for p in files if p.name not in set(excludes)]
    return files, excluded


def _parse_unittest_output(text: str) -> Tuple[int, int, int, int]:
    """Extract (ran, failures, errors, skipped) from unittest stdout/stderr."""
    ran_m = RAN_RE.search(text)
    ran = int(ran_m.group(1)) if ran_m else 0
    failures = errors = skipped = 0
    fail_m = FAIL_SUMMARY_RE.search(text)
    if fail_m:
        failures = int(fail_m.group(1) or 0)
        errors = int(fail_m.group(2) or 0)
        skipped = int(fail_m.group(3) or 0)
    else:
        ok_m = OK_SKIPPED_RE.search(text)
        if ok_m:
            skipped = int(ok_m.group(1))
    return ran, failures, errors, skipped


def _isolation_kwargs() -> dict:
    """Popen kwargs that give each shard its own killable process tree.

    POSIX: `start_new_session=True` puts the shard in a new session/process
    group, so `killpg` reaches every descendant it spawned.
    Windows: `CREATE_NEW_PROCESS_GROUP` detaches the shard from the parent's
    console group (no inherited Ctrl events); `taskkill /T` walks the tree by
    parent pid, which is the NT equivalent of a process-group kill.
    """
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate_tree(proc: "subprocess.Popen") -> str:
    """Kill a timed-out shard AND its descendants. Returns a diagnostic line.

    Killing only the direct child is what turns one hung test into a hung
    suite: a surviving grandchild keeps the inherited stdout write handle open,
    so the parent's output collection never sees EOF.
    """
    if proc.poll() is not None:
        return "process-tree: shard already exited (rc={})".format(proc.returncode)
    if os.name == "nt":
        try:
            killed = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                timeout=TREE_KILL_TIMEOUT_S,
            )
            note = "process-tree: taskkill /F /T pid={} rc={}".format(
                proc.pid, killed.returncode
            )
        except (OSError, subprocess.SubprocessError) as exc:
            note = "process-tree: taskkill pid={} unavailable ({})".format(
                proc.pid, exc.__class__.__name__
            )
        # taskkill can miss a descendant that re-parented; the direct child is
        # ours either way, so kill it unconditionally as a backstop.
        try:
            proc.kill()
        except OSError:
            pass
        return note
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGKILL)
        return "process-tree: killpg pgid={} SIGKILL (shard + descendants)".format(pgid)
    except (OSError, AttributeError) as exc:
        try:
            proc.kill()
        except OSError:
            pass
        return "process-tree: killpg pid={} failed ({}) - killed shard only".format(
            proc.pid, exc.__class__.__name__
        )


def _run_one(tests_dir: Path, test_file: Path, verbose: bool, file_timeout: int) -> FileResult:
    """Run one test file via unittest discover (file-level shard)."""
    cmd = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(tests_dir),
        "-p",
        test_file.name,
    ]
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    t0 = time.perf_counter()
    # stdin=DEVNULL: a shard (or anything it spawns - git, a backend CLI, a
    # pager) must never block reading the runner's inherited stdin. It gets
    # immediate EOF instead of an interactive wait nothing will ever answer.
    # universal_newlines with no `encoding=`: deliberate (fn-120.2/fn-120.3).
    # Parent and child share the locale, so the transport is symmetric; forcing
    # UTF-8 on children would hand all files a UTF-8 console and destroy the
    # Windows leg's ability to catch the real cp1252 print-crash class
    # (evidence: windows-latest run 30913423957).
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        **_isolation_kwargs(),
    )
    try:
        output = proc.communicate(timeout=file_timeout)[0] or ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        # A hung file must fail LOUDLY with its name, never stall the suite
        # (first seen: windows-latest CI hang on the first full-corpus run).
        returncode = 124
        kill_note = _terminate_tree(proc)
        collect0 = time.perf_counter()
        try:
            partial = proc.communicate(timeout=POST_KILL_COLLECT_S)[0] or ""
            collect_note = "post-kill collection: complete in {:.2f}s ({} chars)".format(
                time.perf_counter() - collect0, len(partial)
            )
        except subprocess.TimeoutExpired:
            # Bounded, unconditionally: a descendant we could not reach still
            # holds the write handle. Abandon the pipe rather than hang the
            # suite on it (the reader threads are daemons).
            partial = ""
            collect_note = (
                "post-kill collection: ABANDONED after {}s - a surviving "
                "descendant still holds this shard's stdout".format(POST_KILL_COLLECT_S)
            )
        output = (
            "TIMEOUT {name}  rc=124  after {elapsed:.2f}s "
            "(per-file limit {limit}s, --file-timeout)\n"
            "{kill}\n{collect}\n"
            "--- captured output before kill ---\n{partial}".format(
                name=test_file.name,
                elapsed=time.perf_counter() - t0,
                limit=file_timeout,
                kill=kill_note,
                collect=collect_note,
                partial=partial,
            )
        )
    elapsed = time.perf_counter() - t0
    ran, failures, errors, skipped = _parse_unittest_output(output)
    return FileResult(
        path=test_file,
        returncode=returncode,
        ran=ran,
        failures=failures,
        errors=errors,
        skipped=skipped,
        elapsed_s=elapsed,
        output=output,
    )


def _format_status(result: FileResult) -> str:
    if result.ok:
        extra = ""
        if result.skipped:
            extra = " (skipped={})".format(result.skipped)
        return "PASS  {name}  ran={ran}{extra}  {elapsed:.2f}s".format(
            name=result.path.name,
            ran=result.ran,
            extra=extra,
            elapsed=result.elapsed_s,
        )
    if result.returncode == 124:
        # Timed-out file: name, exit code and elapsed time on the status line;
        # the kill/collection diagnostics and captured output ride in
        # result.output, which the FAILED FILES section always prints.
        return "FAIL  {name}  rc=124 TIMEOUT  ran={ran}  {elapsed:.2f}s".format(
            name=result.path.name, ran=result.ran, elapsed=result.elapsed_s
        )
    if result.returncode == 0 and result.ran == 0:
        return "FAIL  {name}  rc=0 ran=0 (no tests discovered - unittest cannot see pytest-style module functions)  {elapsed:.2f}s".format(
            name=result.path.name, elapsed=result.elapsed_s
        )
    return "FAIL  {name}  rc={rc} ran={ran} failures={f} errors={e}  {elapsed:.2f}s".format(
        name=result.path.name,
        rc=result.returncode,
        ran=result.ran,
        f=result.failures,
        e=result.errors,
        elapsed=result.elapsed_s,
    )


def run_suite(
    tests_dir: Path,
    pattern: str,
    jobs: int,
    shuffle: bool,
    seed: Optional[int],
    verbose: bool,
    list_only: bool,
    file_timeout: int,
    excludes: Sequence[str],
) -> int:
    files, excluded = _discover(tests_dir, pattern, excludes)
    for name in excluded:
        # Never a silent cap: every exclusion is printed on every run.
        print("EXCLUDED  {}  (--exclude)".format(name))
    if not files:
        print(
            "ERROR: zero test files matched pattern {!r} under {}".format(
                pattern, tests_dir
            ),
            file=sys.stderr,
        )
        return 2

    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(files)
        seed_note = "seed={}".format(seed if seed is not None else "non-deterministic")
        print("shuffle: on ({})".format(seed_note))

    print(
        "parallel-runner: {} file(s), jobs={}, dir={}".format(
            len(files), jobs, tests_dir
        )
    )
    if list_only:
        for f in files:
            print(f.name)
        return 0

    wall0 = time.perf_counter()
    results: List[FileResult] = []

    if jobs <= 1:
        for f in files:
            results.append(_run_one(tests_dir, f, verbose, file_timeout))
            print(_format_status(results[-1]), flush=True)
            if not results[-1].ok and verbose:
                sys.stdout.write(results[-1].output)
                if not results[-1].output.endswith("\n"):
                    sys.stdout.write("\n")
    else:
        # Preserve discovery/shuffle order in the printed summary via index map.
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            future_map = {
                pool.submit(_run_one, tests_dir, f, verbose, file_timeout): idx
                for idx, f in enumerate(files)
            }
            ordered: List[Optional[FileResult]] = [None] * len(files)
            for fut in concurrent.futures.as_completed(future_map):
                idx = future_map[fut]
                result = fut.result()
                ordered[idx] = result
                print(_format_status(result), flush=True)
                if not result.ok and verbose:
                    sys.stdout.write(result.output)
                    if not result.output.endswith("\n"):
                        sys.stdout.write("\n")
            results = [r for r in ordered if r is not None]

    wall = time.perf_counter() - wall0
    total_ran = sum(r.ran for r in results)
    total_fail = sum(r.failures for r in results)
    total_err = sum(r.errors for r in results)
    total_skip = sum(r.skipped for r in results)
    failed_files = [r for r in results if not r.ok]

    print("-" * 70)
    print(
        "SUMMARY  files={files} ran={ran} failures={f} errors={e} skipped={s}  "
        "wall={wall:.2f}s  jobs={jobs}".format(
            files=len(results),
            ran=total_ran,
            f=total_fail,
            e=total_err,
            s=total_skip,
            wall=wall,
            jobs=jobs,
        )
    )
    if failed_files:
        print("FAILED FILES ({}):".format(len(failed_files)))
        for r in failed_files:
            print("  - {}".format(r.path.name))
            # Always surface failing-file output so CI logs are actionable.
            if r.output.strip():
                print(r.output.rstrip())
                print()
        return 1

    print("OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "File-level parallel unittest runner for plugins/flow-next/tests. "
            "Canonical full-suite entrypoint (fn-119)."
        )
    )
    p.add_argument(
        "--tests-dir",
        type=Path,
        default=DEFAULT_TESTS_DIR,
        help="Directory of top-level test_*.py files (default: %(default)s)",
    )
    p.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Glob for test files relative to --tests-dir (default: %(default)s)",
    )
    p.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=None,
        help="Concurrent file shards (default: cpu_count on CI, else max(1, cpu_count-2))",
    )
    p.add_argument(
        "--serial",
        action="store_true",
        help="Force jobs=1 (serial fallback; same file set, same result aggregation)",
    )
    p.add_argument(
        "--shuffle",
        action="store_true",
        help="Randomize file order before running (ordering canary; still file-level)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for --shuffle (omit for non-deterministic)",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Pass -v to unittest and print failing-file output inline",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="FILENAME",
        help="Exclude a test file by exact name (repeatable; every exclusion is printed)",
    )
    p.add_argument(
        "--file-timeout",
        type=int,
        default=900,
        help="Per-file hard timeout in seconds; a hung file fails as rc=124 (default: %(default)s)",
    )
    p.add_argument(
        "--list-only",
        action="store_true",
        help="Print matched files and exit 0 (no tests run)",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.serial:
        jobs = 1
    elif args.jobs is not None:
        if args.jobs < 1:
            print("ERROR: --jobs must be >= 1", file=sys.stderr)
            return 2
        jobs = args.jobs
    else:
        jobs = _default_jobs()

    try:
        return run_suite(
            tests_dir=args.tests_dir.resolve(),
            pattern=args.pattern,
            jobs=jobs,
            shuffle=args.shuffle,
            seed=args.seed,
            verbose=args.verbose,
            list_only=args.list_only,
            file_timeout=args.file_timeout,
            excludes=args.exclude,
        )
    except FileNotFoundError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
