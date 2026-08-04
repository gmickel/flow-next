#!/usr/bin/env python3
"""First tests for scripts/run_tests_parallel.py (fn-155).

Three groups:

1. `_default_jobs()` value semantics - the CI/local split and every `CI` value
   case the design names (absent / empty / "false" / "TRUE" / "0").
2. Precedence at `main()`, NOT at the parser. The chain lives after parsing, so
   a parser-level test cannot prove `--serial` > `--jobs` > default, nor that
   `--jobs 0` exits 2 without running the suite. `run_suite` and
   `_default_jobs` are patched so the assertions are about the selection.
3. Contracts a job-count change could plausibly disturb: coverage parity
   between two job counts on the same corpus (sorted `--list-only` output, the
   `parallel-runner:` line and the `SUMMARY` counts), `--exclude` behavior and
   its `EXCLUDED` line, zero-match exit 2, and a failing file exit 1.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PY = REPO_ROOT / "scripts" / "run_tests_parallel.py"

# The module under test lives in repo-root scripts/, which is not on sys.path
# when this file runs (sys.path[0] is the tests dir). Insert it so the runner's
# own directory is importable, and so this module satisfies the repo-wide
# sys.path guard in test_tracker_package_import.py.
sys.path.insert(0, str(REPO_ROOT / "scripts"))

_RUNNER_MOD = None


def _load_runner():
    """Load the runner by path (same pattern the flowctl test modules use)."""
    global _RUNNER_MOD
    if _RUNNER_MOD is None:
        spec = importlib.util.spec_from_file_location(
            "run_tests_parallel_under_test", RUNNER_PY
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _RUNNER_MOD = mod
    return _RUNNER_MOD


PASSING_FILE = """\
import unittest


class Passing(unittest.TestCase):
    def test_one(self):
        self.assertTrue(True)

    def test_two(self):
        self.assertEqual(2, 1 + 1)
"""

FAILING_FILE = """\
import unittest


class Failing(unittest.TestCase):
    def test_boom(self):
        self.assertEqual(1, 2)
"""

# fn-120.3 (R6/R11): a shard that spawns a GRANDCHILD inheriting the runner's
# stdout pipe and then hangs. This is the shape that turns one hung file into a
# hung suite - killing only the direct child leaves the grandchild holding the
# write handle, so the parent's output collection never sees EOF.
GRANDCHILD_HOLDS_STDOUT = """\
import os
import subprocess
import sys
import time
import unittest

GRANDCHILD = (
    "import os, sys, time\\n"
    "pid_path, beat_path = sys.argv[1], sys.argv[2]\\n"
    "open(pid_path, 'w').write(str(os.getpid()))\\n"
    "for _ in range(1200):\\n"
    "    f = open(beat_path, 'a')\\n"
    "    f.write('t')\\n"
    "    f.close()\\n"
    "    time.sleep(0.1)\\n"
)


class GrandchildHoldsStdout(unittest.TestCase):
    def test_spawns_grandchild_then_hangs(self):
        print("SHARD-MARKER stdout before the hang", flush=True)
        # No stdout/stderr redirection: the grandchild INHERITS this process's
        # stdout, which is the runner's capture pipe.
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                GRANDCHILD,
                os.environ["FN120_PID_FILE"],
                os.environ["FN120_BEAT_FILE"],
            ]
        )
        time.sleep(1200)
"""

# The nastier leak shape (codex review, P1): the shard EXITS IMMEDIATELY after
# spawning the descendant. `proc.kill()` has nothing to kill and `taskkill /T`
# has no live parent to walk from, yet the descendant still holds the shard's
# stdout - so output collection blocks and the process is orphaned.
GRANDCHILD_OUTLIVES_SHARD = """\
import os
import subprocess
import sys
import unittest

GRANDCHILD = (
    "import os, sys, time\\n"
    "pid_path, beat_path = sys.argv[1], sys.argv[2]\\n"
    "open(pid_path, 'w').write(str(os.getpid()))\\n"
    "for _ in range(1200):\\n"
    "    f = open(beat_path, 'a')\\n"
    "    f.write('t')\\n"
    "    f.close()\\n"
    "    time.sleep(0.1)\\n"
)


class GrandchildOutlivesShard(unittest.TestCase):
    def test_spawns_grandchild_and_returns(self):
        print("SHARD-MARKER stdout before exiting", flush=True)
        # Inherits this process's stdout, then the shard exits right away.
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                GRANDCHILD,
                os.environ["FN120_PID_FILE"],
                os.environ["FN120_BEAT_FILE"],
            ]
        )
"""

# Success-path counterpart: a shard that spawns a short-lived grandchild and
# exits normally. Proves the hardened launch path (own process group/tree,
# stdin=DEVNULL, owned capture) still completes and captures output.
GRANDCHILD_EXITS_FILE = """\
import subprocess
import sys
import unittest


class GrandchildExits(unittest.TestCase):
    def test_grandchild_finishes_and_shard_passes(self):
        print("SHARD-MARKER grandchild spawned", flush=True)
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.2)"])
        self.assertEqual(proc.wait(timeout=30), 0)
"""

# A shard that READS stdin. With stdin=DEVNULL it gets immediate EOF; with the
# runner's stdin inherited from an interactive console it would block forever.
STDIN_EOF_FILE = """\
import sys
import unittest


class StdinIsClosed(unittest.TestCase):
    def test_stdin_reads_eof_immediately(self):
        self.assertEqual(sys.stdin.read(), "")
"""


class DefaultJobsTest(unittest.TestCase):
    """R1/R5: the CI vs local split and the `CI` value semantics."""

    def setUp(self):
        self.mod = _load_runner()

    def _jobs(self, ci_value, cpus=8, cursor_agent=None):
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CI", "CURSOR_AGENT")
        }
        if ci_value is not None:
            env["CI"] = ci_value
        if cursor_agent is not None:
            env["CURSOR_AGENT"] = cursor_agent
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            self.mod.os, "cpu_count", return_value=cpus
        ):
            return self.mod._default_jobs()

    def test_local_default_reserves_two_cores(self):
        self.assertEqual(self._jobs(None), 6)

    def test_ci_truthy_values_use_full_cpu_count(self):
        for value in ("1", "true", "yes", "TRUE", "  True  ", "Yes"):
            with self.subTest(value=value):
                self.assertEqual(self._jobs(value), 8)

    def test_ci_falsey_and_unrecognized_values_are_local(self):
        for value in ("", "  ", "false", "FALSE", "0", "no", "off", "maybe"):
            with self.subTest(value=value):
                self.assertEqual(self._jobs(value), 6)

    def test_absent_ci_is_local(self):
        self.assertEqual(self._jobs(None), 6)

    def test_cursor_agent_shell_keeps_local_headroom_despite_ci(self):
        """Cursor's agent shell sets CI=1 on a developer machine.

        Documented in plugins/flow-next/skills/flow-next-setup/workflow.md.
        That is exactly the case the reservation protects - the editor and the
        agent driving the session compete for the same cores - so CURSOR_AGENT
        must force the local branch even though CI parses truthy.
        """
        for ci_value in ("1", "true", "yes", "TRUE"):
            with self.subTest(ci=ci_value):
                self.assertEqual(
                    self._jobs(ci_value, cursor_agent="1"), 6
                )

    def test_cursor_agent_empty_or_absent_does_not_suppress_ci(self):
        """Only a non-empty CURSOR_AGENT forces local; hosted CI never sets it."""
        self.assertEqual(self._jobs("true", cursor_agent=None), 8)
        self.assertEqual(self._jobs("true", cursor_agent=""), 8)
        self.assertEqual(self._jobs("true", cursor_agent="   "), 8)

    def test_cursor_agent_alone_is_still_local(self):
        self.assertEqual(self._jobs(None, cursor_agent="1"), 6)

    def test_low_core_machines_never_go_below_one(self):
        self.assertEqual(self._jobs(None, cpus=1), 1)
        self.assertEqual(self._jobs(None, cpus=2), 1)
        self.assertEqual(self._jobs("true", cpus=1), 1)

    def test_unknown_cpu_count_falls_back_to_two(self):
        env = {k: v for k, v in os.environ.items() if k != "CI"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            self.mod.os, "cpu_count", return_value=None
        ):
            self.assertEqual(self.mod._default_jobs(), 1)
        env["CI"] = "true"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            self.mod.os, "cpu_count", return_value=None
        ):
            self.assertEqual(self.mod._default_jobs(), 2)


class MainPrecedenceTest(unittest.TestCase):
    """R4/R5: --serial > --jobs > default, resolved inside main()."""

    def setUp(self):
        self.mod = _load_runner()

    @contextlib.contextmanager
    def _patched(self, default_jobs=7, run_rc=0):
        calls = {}

        def fake_run_suite(**kwargs):
            calls["kwargs"] = kwargs
            return run_rc

        default = mock.Mock(return_value=default_jobs)
        with mock.patch.object(self.mod, "run_suite", side_effect=fake_run_suite), \
                mock.patch.object(self.mod, "_default_jobs", default):
            yield calls, default

    def test_bare_invocation_uses_default_jobs(self):
        with self._patched() as (calls, default):
            rc = self.mod.main([])
        self.assertEqual(rc, 0)
        self.assertEqual(default.call_count, 1)
        self.assertEqual(calls["kwargs"]["jobs"], 7)

    def test_explicit_jobs_wins_over_default_and_never_calls_it(self):
        with self._patched() as (calls, default):
            rc = self.mod.main(["--jobs", "6"])
        self.assertEqual(rc, 0)
        self.assertEqual(default.call_count, 0)
        self.assertEqual(calls["kwargs"]["jobs"], 6)

    def test_serial_beats_explicit_jobs(self):
        with self._patched() as (calls, default):
            rc = self.mod.main(["--serial", "--jobs", "6"])
        self.assertEqual(rc, 0)
        self.assertEqual(default.call_count, 0)
        self.assertEqual(calls["kwargs"]["jobs"], 1)

    def test_jobs_below_one_exits_two_without_running(self):
        for value in ("0", "-1"):
            with self.subTest(value=value):
                with self._patched() as (calls, default):
                    buf = io.StringIO()
                    with contextlib.redirect_stderr(buf):
                        rc = self.mod.main(["--jobs", value])
                self.assertEqual(rc, 2)
                self.assertNotIn("kwargs", calls)
                self.assertEqual(default.call_count, 0)
                self.assertIn("--jobs must be >= 1", buf.getvalue())


class CorpusContractTest(unittest.TestCase):
    """R3: coverage parity across job counts, plus the exclude/exit contracts."""

    def setUp(self):
        self.mod = _load_runner()
        self._tmp = tempfile.TemporaryDirectory()
        self.corpus = Path(self._tmp.name)
        for name in ("test_alpha.py", "test_beta.py", "test_gamma.py"):
            (self.corpus / name).write_text(PASSING_FILE, encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def _run(self, extra_args, auto_jobs=None):
        """Run main() over the temp corpus.

        `auto_jobs` omits both overrides so the auto default path is the one
        under test, with `_default_jobs` pinned so the comparison is
        deterministic on any machine.
        """
        buf = io.StringIO()
        ctx = (
            mock.patch.object(self.mod, "_default_jobs", return_value=auto_jobs)
            if auto_jobs is not None
            else contextlib.nullcontext()
        )
        with ctx, contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = self.mod.main(["--tests-dir", str(self.corpus)] + extra_args)
        return rc, buf.getvalue()

    @staticmethod
    def _line_starting(text, prefix):
        for line in text.splitlines():
            if line.startswith(prefix):
                return line
        return None

    def test_list_only_file_set_identical_at_jobs_two_and_auto(self):
        rc_a, out_a = self._run(["--jobs", "2", "--list-only"])
        # No --jobs and no --serial: the auto default is the path under test.
        rc_b, out_b = self._run(["--list-only"], auto_jobs=3)
        self.assertEqual((rc_a, rc_b), (0, 0))
        self.assertIn("jobs=2", self._line_starting(out_a, "parallel-runner:"))
        self.assertIn("jobs=3", self._line_starting(out_b, "parallel-runner:"))
        names_a = sorted(ln for ln in out_a.splitlines() if ln.endswith(".py"))
        names_b = sorted(ln for ln in out_b.splitlines() if ln.endswith(".py"))
        self.assertEqual(names_a, ["test_alpha.py", "test_beta.py", "test_gamma.py"])
        self.assertEqual(names_a, names_b)
        # Counts alone are not proof, so the file list above is compared too.
        self.assertIn("3 file(s)", self._line_starting(out_a, "parallel-runner:"))
        self.assertIn("3 file(s)", self._line_starting(out_b, "parallel-runner:"))

    def test_summary_counts_identical_at_jobs_two_and_auto(self):
        rc_a, out_a = self._run(["--jobs", "2"])
        # Auto default (no overrides), pinned to a different job count so the
        # comparison is between two genuinely different schedules.
        rc_b, out_b = self._run([], auto_jobs=3)
        self.assertEqual((rc_a, rc_b), (0, 0))
        summary_a = self._line_starting(out_a, "SUMMARY")
        summary_b = self._line_starting(out_b, "SUMMARY")
        self.assertIsNotNone(summary_a)
        counts_a = summary_a.split("  wall=")[0]
        counts_b = summary_b.split("  wall=")[0]
        self.assertEqual(counts_a, counts_b)
        self.assertIn("files=3 ran=6 failures=0 errors=0 skipped=0", counts_a)
        # ... and the serial fallback agrees with both.
        rc_c, out_c = self._run(["--serial"])
        self.assertEqual(rc_c, 0)
        self.assertEqual(self._line_starting(out_c, "SUMMARY").split("  wall=")[0], counts_a)

    def test_exclude_drops_exactly_the_named_file_and_prints_it(self):
        rc, out = self._run(["--jobs", "2", "--exclude", "test_beta.py", "--list-only"])
        self.assertEqual(rc, 0)
        self.assertIn("EXCLUDED  test_beta.py  (--exclude)", out)
        names = sorted(ln for ln in out.splitlines() if ln.endswith(".py"))
        self.assertEqual(names, ["test_alpha.py", "test_gamma.py"])
        self.assertIn("2 file(s)", self._line_starting(out, "parallel-runner:"))

    def test_zero_match_pattern_exits_two(self):
        rc, out = self._run(["--pattern", "test_nothing_here*.py"])
        self.assertEqual(rc, 2)
        self.assertIn("zero test files matched", out)

    def test_failing_file_exits_one(self):
        (self.corpus / "test_delta.py").write_text(FAILING_FILE, encoding="utf-8")
        rc, out = self._run(["--jobs", "2"])
        self.assertEqual(rc, 1)
        self.assertEqual(self._line_starting(out, "FAILED FILES"), "FAILED FILES (1):")
        self.assertIn("- test_delta.py", out)


class ProcessTreeCleanupTest(unittest.TestCase):
    """fn-120.3 R6/R11: timeout diagnostics + process-tree cleanup.

    The synthetic corpus spawns a grandchild that inherits the shard's stdout
    and never exits on its own. On POSIX the shard runs in its own session, so
    `killpg` reaps the grandchild; on Windows `taskkill /F /T` walks the tree
    from the shard's pid. Either way the runner must report the timed-out file,
    its elapsed time, rc=124 and the output captured before the kill, collect
    that output under a bound, and leave no descendant running.
    """

    FILE_TIMEOUT = 3

    def setUp(self):
        self.mod = _load_runner()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.corpus = Path(self._tmp.name) / "corpus"
        self.corpus.mkdir()
        self.pid_file = Path(self._tmp.name) / "grandchild.pid"
        self.beat_file = Path(self._tmp.name) / "grandchild.beat"
        self._env = mock.patch.dict(
            os.environ,
            {
                "FN120_PID_FILE": str(self.pid_file),
                "FN120_BEAT_FILE": str(self.beat_file),
            },
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        # Safety net: if an assertion below fails because cleanup did NOT work,
        # do not leave a 2-minute orphan behind on the developer's machine.
        self.addCleanup(self._force_kill_grandchild)

    # -- helpers ---------------------------------------------------------
    def _grandchild_pid(self):
        try:
            return int(self.pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def _force_kill_grandchild(self):
        pid = self._grandchild_pid()
        if pid is None:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                )
            else:
                os.kill(pid, 9)
        except (OSError, subprocess.SubprocessError):
            pass

    def _beats(self):
        try:
            return len(self.beat_file.read_bytes())
        except OSError:
            return 0

    def _assert_grandchild_terminated(self):
        """The grandchild ticks a heartbeat every 0.1s while alive.

        Comparing two samples ~1.5s apart is OS-neutral (no psutil, no
        tasklist parsing) and proves absence of a *running* descendant rather
        than merely the absence of a pid.
        """
        self.assertTrue(
            self.pid_file.exists(),
            "grandchild never started - the fixture proves nothing",
        )
        self.assertGreater(self._beats(), 0, "grandchild never wrote a heartbeat")
        first = self._beats()
        time.sleep(1.5)
        self.assertEqual(
            self._beats(),
            first,
            "grandchild survived the kill (heartbeat still advancing) - "
            "orphan descendant holding the shard's stdout",
        )

    def _write_corpus(self, source):
        (self.corpus / "test_hang.py").write_text(source, encoding="utf-8")

    def _run(self, extra_args=()):
        buf = io.StringIO()
        t0 = time.perf_counter()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = self.mod.main(
                [
                    "--tests-dir",
                    str(self.corpus),
                    "--serial",
                    "--file-timeout",
                    str(self.FILE_TIMEOUT),
                    *extra_args,
                ]
            )
        return rc, buf.getvalue(), time.perf_counter() - t0

    # -- tests -----------------------------------------------------------
    def test_timeout_reports_file_elapsed_rc_and_captured_output(self):
        self._write_corpus(GRANDCHILD_HOLDS_STDOUT)
        rc, out, wall = self._run()
        self.assertEqual(rc, 1, out)
        # Status line: file, exit code, elapsed.
        status = next(
            (ln for ln in out.splitlines() if ln.startswith("FAIL  test_hang.py")), None
        )
        self.assertIsNotNone(status, out)
        self.assertIn("rc=124 TIMEOUT", status)
        self.assertRegex(status, r"\d+\.\d\ds$")
        # Diagnostics block: named file, elapsed, the per-file limit, and the
        # output the shard produced before it was killed.
        self.assertIn("TIMEOUT test_hang.py  rc=124  after ", out)
        self.assertIn(
            "(per-file limit {}s, --file-timeout)".format(self.FILE_TIMEOUT), out
        )
        self.assertIn("SHARD-MARKER stdout before the hang", out)
        self.assertIn("--- captured output before kill ---", out)
        # The whole run stays bounded: the timeout plus a killed-tree drain,
        # never the 1200s the fixture would otherwise sleep.
        self.assertLess(wall, 90, "timeout path was not bounded (wall={})".format(wall))
        self.assertIn("FAILED FILES (1):", out)

    def test_timeout_kills_the_descendant_and_collects_under_bound(self):
        self._write_corpus(GRANDCHILD_HOLDS_STDOUT)
        rc, out, _wall = self._run()
        self.assertEqual(rc, 1, out)
        if os.name == "nt":
            self.assertRegex(out, r"process-tree: pid=\d+ .*shard alive")
            self.assertIn("TerminateJobObject=", out)
        else:
            self.assertRegex(out, r"process-tree: killpg pgid=\d+ SIGKILL")
        # Killing the tree closes the inherited handle, so collection finishes
        # rather than hitting the abandonment bound.
        self.assertIn("output collection: complete in ", out)
        self.assertNotIn("ABANDONED", out)
        self._assert_grandchild_terminated()

    def test_descendant_that_outlives_the_shard_is_still_killed(self):
        """codex review P1: the shard exits, the descendant keeps stdout.

        `proc.kill()` has nothing to kill and a `taskkill /T` tree walk has no
        live parent, so the kill identity must be owned independently of the
        shard (POSIX process group captured at launch; Windows Job Object). The
        file itself PASSES - the leak is reported as a WARN, not swallowed.
        """
        self._write_corpus(GRANDCHILD_OUTLIVES_SHARD)
        with mock.patch.object(self.mod, "POST_KILL_COLLECT_S", 2):
            rc, out, wall = self._run()
        self.assertEqual(rc, 0, out)
        # `ran=1` is itself proof the shard's output was captured and parsed
        # despite the descendant holding the pipe open.
        self.assertIn("PASS  test_hang.py  ran=1", out)
        self.assertIn("WARN  test_hang.py  descendant outlived the shard", out)
        # Bounded: the leak is detected and killed, never waited out (the
        # descendant would otherwise hold the pipe for 120s).
        self.assertLess(wall, 60, "leak path was not bounded (wall={})".format(wall))
        self._assert_grandchild_terminated()

    def test_output_captured_before_a_leak_survives_in_the_result(self):
        """Nothing captured is discarded on the leak path (codex review P2)."""
        self._write_corpus(GRANDCHILD_OUTLIVES_SHARD)
        with mock.patch.object(self.mod, "POST_KILL_COLLECT_S", 2):
            result = self.mod._run_one(
                self.corpus, self.corpus / "test_hang.py", False, self.FILE_TIMEOUT
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("SHARD-MARKER stdout before exiting", result.output)
        self.assertIn("descendant outlived the shard", result.note)
        self._assert_grandchild_terminated()

    def test_collection_is_bounded_and_keeps_output_when_the_kill_fails(self):
        """The bound is unconditional, not a side effect of a working kill.

        `_ShardTree.terminate` is neutered so the grandchild keeps the stdout
        write handle open. The runner must still return - with an explicit
        ABANDONED diagnostic - and must NOT discard the output it already
        captured (codex review P2: that is the failure path whose evidence
        matters most).
        """
        self._write_corpus(GRANDCHILD_HOLDS_STDOUT)
        with mock.patch.object(
            self.mod._ShardTree,
            "terminate",
            lambda _self: "process-tree: kill suppressed (test)",
        ), mock.patch.object(self.mod, "POST_KILL_COLLECT_S", 2):
            rc, out, wall = self._run()
        self.assertEqual(rc, 1, out)
        self.assertIn("output collection: ABANDONED after 2s", out)
        self.assertIn("surviving descendant still holds this shard's stdout", out)
        self.assertIn("output captured so far is kept", out)
        # The captured marker MUST survive the abandonment.
        self.assertIn("SHARD-MARKER stdout before the hang", out)
        self.assertLess(
            wall, 60, "abandonment path was not bounded (wall={})".format(wall)
        )
        # Housekeeping only - the suppressed kill is why this one is alive.
        self._force_kill_grandchild()


class ShardLaunchContractTest(unittest.TestCase):
    """fn-120.3 R6/R11: how the shard is launched, asserted on both platforms."""

    def setUp(self):
        self.mod = _load_runner()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.corpus = Path(self._tmp.name)

    def test_shard_gets_devnull_stdin_and_its_own_process_tree(self):
        captured = {}
        real_popen = self.mod.subprocess.Popen

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["kwargs"] = kwargs
            # Launch the stand-in in its OWN session too: a stray group kill
            # must never be able to reach this test process's own group.
            return real_popen(
                [sys.executable, "-c", "print('ok')"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                **self.mod._isolation_kwargs(),
            )

        (self.corpus / "test_alpha.py").write_text(PASSING_FILE, encoding="utf-8")
        with mock.patch.object(self.mod.subprocess, "Popen", side_effect=fake_popen):
            self.mod._run_one(
                self.corpus, self.corpus / "test_alpha.py", False, 60
            )
        kwargs = captured["kwargs"]
        # Never the runner's own stdin: a shard, or any CLI it spawns, must get
        # EOF instead of blocking on an interactive read nothing will answer.
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.PIPE)
        self.assertIs(kwargs["stderr"], subprocess.STDOUT)
        if os.name == "nt":
            self.assertEqual(
                kwargs["creationflags"], subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.assertNotIn("start_new_session", kwargs)
        else:
            self.assertTrue(kwargs["start_new_session"])
            self.assertNotIn("creationflags", kwargs)

    def test_isolation_kwargs_match_the_platform(self):
        kwargs = self.mod._isolation_kwargs()
        if os.name == "nt":
            self.assertEqual(
                kwargs, {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            )
        else:
            self.assertEqual(kwargs, {"start_new_session": True})

    def test_shard_reading_stdin_sees_eof_and_passes(self):
        (self.corpus / "test_stdin.py").write_text(STDIN_EOF_FILE, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = self.mod.main(
                ["--tests-dir", str(self.corpus), "--serial", "--file-timeout", "60"]
            )
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS  test_stdin.py  ran=1", out)

    def test_successful_shard_with_a_grandchild_completes_and_captures_output(self):
        (self.corpus / "test_gc.py").write_text(GRANDCHILD_EXITS_FILE, encoding="utf-8")
        buf = io.StringIO()
        t0 = time.perf_counter()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = self.mod.main(
                [
                    "--tests-dir",
                    str(self.corpus),
                    "--serial",
                    "--file-timeout",
                    "60",
                    "--verbose",
                ]
            )
        wall = time.perf_counter() - t0
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS  test_gc.py  ran=1", out)
        self.assertNotIn("TIMEOUT", out)
        self.assertLess(wall, 60, "success path stalled (wall={})".format(wall))

    def test_terminate_without_an_attached_shard_is_a_no_op(self):
        tree = self.mod._ShardTree()
        self.addCleanup(tree.close)
        self.assertEqual(tree.terminate(), "process-tree: nothing attached")

    def test_terminate_still_names_the_group_after_the_shard_exited(self):
        """The kill identity outlives the shard (codex review P1).

        An exited shard must NOT short-circuit termination: its descendants are
        exactly what needs killing. With an empty group the call reports that
        explicitly instead of claiming there was nothing to do.
        """
        tree = self.mod._ShardTree()
        self.addCleanup(tree.close)
        proc = self.mod.subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            **tree.popen_kwargs(),
        )
        tree.attach(proc)
        proc.communicate(timeout=60)
        note = tree.terminate()
        self.assertIn("already exited" if os.name == "nt" else "pgid=", note)
        self.assertNotIn("nothing attached", note)
        if os.name != "nt":
            # Own session ⇒ the group id is the shard's pid, and it is the
            # GROUP the runner kills, not just the (dead) shard.
            self.assertIn("pgid={}".format(proc.pid), note)


if __name__ == "__main__":
    unittest.main()
