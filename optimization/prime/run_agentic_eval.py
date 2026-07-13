#!/usr/bin/env python3
"""Non-CI agentic eval harness for the prime Phase-0.5 JUDGMENT layer (fn-92.11).

The emitter (`flowctl prime classify --json`) decides axes 1-4 deterministically
and is covered by the CI unit suite. This harness is the *judgment oracle*: it
checks whether a model, handed classification.md's judgment rules + the emitter
JSON for a fixture + a bounded file listing, derives the correct Axis-5 delivery
shape, per-axis confidence, would-ask discipline, and playbook selection. Prose
contract-tests never prove judgment (round-2 finding); this does.

NON-CI by design. It shells out to a real backend (`claude -p`, or `codex exec`
as fallback) and is NEVER wired into the unittest suite. When no backend is
available / authenticated it SKIPS with a note and exits 0 - it never fails a
gate on a missing credential.

Isolation is ENFORCED, not asserted (final review round):
  * the backend runs in a throwaway temp arena containing a copied projection
    only - never a live checkout path;
  * a minimal, rebuilt environment (no inherited vars, no live-repo path);
  * read-only / sandbox flags on the backend invocation, approvals disabled;
  * an explicit timeout with process-GROUP termination (never bare timeout(1));
  * a post-run filesystem-diff over the arena;
  * a sentinel planted OUTSIDE the arena whose path is never disclosed in the
    prompt or env - `--self-test` proves offline that a hostile backend can
    neither locate/modify it nor leak its token, and that the filesystem-diff
    actually fires on an in-arena write.

Pinned entry point (task 9 runs exactly this):
    python3 optimization/prime/run_agentic_eval.py --all

Other modes:
    python3 optimization/prime/run_agentic_eval.py --fixture greenfield
    python3 optimization/prime/run_agentic_eval.py --self-test   # offline, no model
    python3 optimization/prime/run_agentic_eval.py --all --backend codex

Pure stdlib.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
FIXTURES_DIR = HERE / "fixtures"
RESULTS_DIR = HERE / "results"
EXPECTATIONS = HERE / "expectations.json"
REPO_ROOT = HERE.parent.parent
CLASSIFICATION_MD = (
    REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-prime" / "classification.md"
)

DEFAULT_TIMEOUT = int(os.environ.get("PRIME_EVAL_TIMEOUT", "180"))
RETRIES = 1  # one retry after the first attempt

# The structured output contract the model must return (also a JSON Schema for
# codex --output-schema). Kept small: five axes + confidence + would-ask +
# playbook - exactly the judgment layer under test.
PLAYBOOKS = [
    "greenfield",
    "standard-single",
    "monorepo",
    "huge-legacy",
    "constellation-home-base",
    "constellation-product-family",
]
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["assessment_scope", "axes", "confidence", "would_ask", "playbook"],
    "properties": {
        "assessment_scope": {
            "type": "string",
            "enum": ["repository", "workspace-member", "constellation-home-base"],
        },
        "axes": {
            "type": "object",
            "additionalProperties": False,
            "required": ["lifecycle", "topology", "size_band", "stacks", "delivery_shape"],
            "properties": {
                "lifecycle": {"type": "string", "enum": ["greenfield", "hybrid", "brownfield"]},
                "topology": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["monorepo", "constellation_member"],
                    "properties": {
                        "monorepo": {"type": "boolean"},
                        "constellation_member": {"type": "boolean"},
                    },
                },
                "size_band": {"type": "string", "enum": ["small", "medium", "large", "huge"]},
                "stacks": {"type": "array", "items": {"type": "string"}},
                "delivery_shape": {"type": "array", "items": {"type": "string"}},
            },
        },
        "confidence": {
            "type": "object",
            "additionalProperties": False,
            "required": ["lifecycle", "topology", "size", "stacks", "shape"],
            "properties": {
                k: {"type": "string", "enum": ["high", "medium", "low"]}
                for k in ("lifecycle", "topology", "size", "stacks", "shape")
            },
        },
        "would_ask": {"type": "array", "items": {"type": "string"}},
        "playbook": {"type": "string", "enum": PLAYBOOKS},
    },
}


# ── prompt assembly ───────────────────────────────────────────────────────────


def _build_prompt(emitter: dict, file_listing: list) -> str:
    rules = CLASSIFICATION_MD.read_text(encoding="utf-8")
    schema_str = json.dumps(OUTPUT_SCHEMA, indent=2)
    listing_str = "\n".join(f"  - {p}" for p in file_listing) or "  (empty)"
    return f"""You are the judgment layer of `/flow-next:prime` Phase 0.5. The deterministic \
emitter has already produced the raw classification signals below. Your job is to \
apply the JUDGMENT RULES to derive: the five axes (with the Axis-5 delivery shape \
you resolve from the raw shape markers), a per-axis confidence, the `would_ask` \
clarification list (Phase 0.6 discipline: ask ONLY what changes a playbook or a \
verdict and is not already answered by a signal), and the single best `playbook`.

Follow the rules exactly. Do NOT re-derive axes the emitter already decided \
unless the evidence contradicts them; DO resolve the delivery shape, the final \
confidence, the would-ask list, and the playbook. Respect the workspace-parent \
dampener, the tier a/b/c constellation tiers, the worktree-exclusion edge case, \
and the greenfield report shape.

=== JUDGMENT RULES (classification.md) ===
{rules}

=== EMITTER JSON (raw signals for THIS fixture) ===
{json.dumps(emitter, indent=2)}

=== BOUNDED FIXTURE FILE LISTING ===
{listing_str}

=== OUTPUT CONTRACT ===
Return ONLY a single JSON object, no prose, no code fence, matching this schema:
{schema_str}

Playbook labels: {", ".join(PLAYBOOKS)}.
"""


# ── isolated backend invocation ───────────────────────────────────────────────


def _minimal_env() -> dict:
    """A rebuilt environment: only what a CLI strictly needs to run and auth.
    No inherited vars, no live-repo path. HOME is required for CLI credentials."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", tempfile.gettempdir()),
        "TERM": "dumb",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    # Carry the backend's own auth/config vars if present, nothing else.
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY", "CODEX_HOME"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def _backend_cmd(backend: str, model: str, schema_path: Path) -> list[str]:
    if backend == "claude":
        return [
            "claude", "-p",
            "--output-format", "json",
            "--model", model,
            "--permission-mode", "plan",       # read-only planning mode
            "--allowedTools", "",              # no tools: prompt is self-contained
            "--disallowedTools", "Bash", "Edit", "Write", "Read", "WebFetch", "WebSearch",
        ]
    if backend == "codex":
        return [
            "codex", "exec",
            "-s", "read-only",                 # OS sandbox: no writes, no network
            "--skip-git-repo-check",
            "-m", model,
            "--output-schema", str(schema_path),
            "-",                               # prompt on stdin
        ]
    raise ValueError(f"unknown backend {backend!r}")


def _sandbox_wrap(cmd: list[str], protect_dir: Path) -> tuple[list[str], bool]:
    """Best-effort OS hardening. On macOS, wrap `cmd` in a `sandbox-exec` profile
    that allows everything the CLI needs (network, HOME/cache writes, exec) but
    HARD-DENIES read+write to `protect_dir` (the out-of-arena sentinel tree). The
    real backend needs network + config writes, so we cannot fully cage it - we
    only fence off the sentinel. Where `sandbox-exec` is unavailable (non-macOS),
    containment degrades to the native read-only backend flag + the detection
    tripwire; returns (cmd, sandboxed?)."""
    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        return cmd, False
    real = os.path.realpath(str(protect_dir))
    profile = (
        "(version 1)(allow default)"
        f'(deny file-read* (subpath "{real}"))'
        f'(deny file-write* (subpath "{real}"))'
    )
    return ["sandbox-exec", "-p", profile, *cmd], True


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _fs_snapshot(root: Path) -> dict:
    snap = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for f in filenames:
            p = Path(dirpath) / f
            try:
                st = p.stat()
                snap[str(p.relative_to(root))] = (st.st_size, int(st.st_mtime))
            except OSError:
                snap[str(p.relative_to(root))] = None
    return snap


def _run_backend(
    cmd: list[str], prompt: str, arena: Path, timeout: int, protect_dir: Optional[Path] = None
) -> tuple[int, str, str, bool, bool]:
    """Run `cmd` with prompt on stdin, cwd=arena, minimal env, in its own process
    group, optionally OS-hardened to fence off `protect_dir`. Returns
    (returncode, stdout, stderr, timed_out, sandboxed)."""
    sandboxed = False
    if protect_dir is not None:
        cmd, sandboxed = _sandbox_wrap(cmd, protect_dir)
    proc = subprocess.Popen(
        cmd,
        cwd=str(arena),
        env=_minimal_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # own process group -> killpg on timeout
    )
    try:
        out, err = proc.communicate(input=prompt, timeout=timeout)
        return proc.returncode, out, err, False, sandboxed
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        out, err = "", "timed out"
        try:
            out, err = proc.communicate(timeout=5)
        except Exception:
            pass
        return 124, out, err, True, sandboxed


# ── output parsing ─────────────────────────────────────────────────────────────

_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[dict]:
    """Pull the model's structured object out of raw stdout. Handles claude's
    {"result": "<text>"} envelope, codex JSONL, and bare JSON / fenced JSON."""
    text = text.strip()
    if not text:
        return None
    # claude --output-format json: envelope with a "result" string field.
    try:
        env = json.loads(text)
        if isinstance(env, dict) and "result" in env and isinstance(env["result"], str):
            inner = _first_json_object(env["result"])
            if inner is not None:
                return inner
        if isinstance(env, dict) and "assessment_scope" in env:
            return env
    except json.JSONDecodeError:
        pass
    # codex --json: JSONL events; the final agent message carries the object.
    for line in reversed(text.splitlines()):
        obj = _first_json_object(line)
        if obj and "assessment_scope" in obj:
            return obj
    return _first_json_object(text)


def _first_json_object(text: str) -> Optional[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = re.sub(r"^(json)?\n", "", text, count=1)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = _JSON_OBJ_RE.search(text)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# ── deterministic scorer ───────────────────────────────────────────────────────

_CONSTELLATION_RE = re.compile(
    r"constellation|sibling|other repo|repos elsewhere|multi-repo|home base|monorepo member",
    re.IGNORECASE,
)


def _score(family: str, expect: dict, got: dict) -> dict:
    """Deterministic per-row scoring. Each active predicate is one check."""
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    axes = got.get("axes", {}) if isinstance(got, dict) else {}
    topo = axes.get("topology", {}) if isinstance(axes, dict) else {}
    would = got.get("would_ask", []) if isinstance(got, dict) else []
    would_text = " || ".join(str(w) for w in would) if isinstance(would, list) else str(would)

    if expect.get("assessment_scope") is not None:
        v = got.get("assessment_scope")
        add("assessment_scope", v == expect["assessment_scope"], f"got={v!r} want={expect['assessment_scope']!r}")
    if expect.get("lifecycle") is not None:
        v = axes.get("lifecycle")
        add("lifecycle", v == expect["lifecycle"], f"got={v!r} want={expect['lifecycle']!r}")
    if expect.get("constellation_member") is not None:
        v = topo.get("constellation_member")
        add("constellation_member", v == expect["constellation_member"], f"got={v!r} want={expect['constellation_member']!r}")
    if expect.get("would_ask_constellation") is not None:
        present = bool(_CONSTELLATION_RE.search(would_text))
        want = expect["would_ask_constellation"]
        add("would_ask_constellation", present == want, f"present={present} want={want} would_ask={would_text!r}")
    if expect.get("playbook_any_of"):
        v = got.get("playbook")
        add("playbook", v in expect["playbook_any_of"], f"got={v!r} want in {expect['playbook_any_of']}")

    passed = all(c["pass"] for c in checks) if checks else True
    return {
        "family": family,
        "negative_control": bool(expect.get("negative_control")),
        "checks": checks,
        "passed": passed,
    }


# ── result + provenance ─────────────────────────────────────────────────────────


def _backend_version(backend: str) -> str:
    try:
        cmd = ["claude", "--version"] if backend == "claude" else ["codex", "--version"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or out.stderr.strip()
    except Exception:
        return "unknown"


def _detect_backend(requested: str) -> Optional[str]:
    order = [requested] if requested != "auto" else ["claude", "codex"]
    for b in order:
        if shutil.which(b):
            return b
    return None


# ── isolation: filesystem-diff + sentinel ───────────────────────────────────────


def _prepare_arena(base: Path, projection: dict) -> Path:
    """A throwaway arena holding ONLY the copied projection - no live path."""
    arena = base / "arena"
    arena.mkdir()
    (arena / "projection.json").write_text(json.dumps(projection, indent=2), encoding="utf-8")
    return arena


def _plant_sentinel(base: Path) -> tuple[Path, str, tuple]:
    """A sentinel in a SEPARATE temp tree (NOT a parent of the arena). Its path
    is never written into the prompt or env. Returns (path, token, stat-sig)."""
    outside = base / "outside"
    outside.mkdir()
    token = "SENTINEL-" + os.urandom(8).hex()
    sfile = outside / "secret.txt"
    sfile.write_text(token + "\n", encoding="utf-8")
    st = sfile.stat()
    return sfile, token, (st.st_size, int(st.st_mtime))


def _isolation_report(arena: Path, pre: dict, sentinel: Path, token: str, sig: tuple, stdout: str) -> dict:
    post = _fs_snapshot(arena)
    arena_changed = pre != post
    diff = {
        "created": sorted(set(post) - set(pre)),
        "removed": sorted(set(pre) - set(post)),
        "modified": sorted(k for k in (set(pre) & set(post)) if pre[k] != post[k]),
    }
    st = sentinel.stat()
    sentinel_modified = (st.st_size, int(st.st_mtime)) != sig
    token_leaked = token in stdout
    return {
        "arena_changed_beyond_projection": arena_changed and diff["created"] not in ([], ["projection.json"]),
        "arena_diff": diff,
        "sentinel_modified": sentinel_modified,
        "sentinel_token_leaked": token_leaked,
        "clean": (not sentinel_modified) and (not token_leaked),
    }


def _isolation_breached(iso: dict) -> bool:
    """True if a run breached the arena in ANY way - an arena write beyond the
    projection, a sentinel modification, or a token leak. `clean` alone omits
    the arena-write case, so the blocking-threshold gate uses this stricter
    predicate: a breached run is never parsed as a valid scored judgment.
    """
    return bool(
        iso.get("arena_changed_beyond_projection")
        or iso.get("sentinel_modified")
        or iso.get("sentinel_token_leaked")
    )


# ── one fixture run ──────────────────────────────────────────────────────────────


def run_fixture(family: str, backend: str, model: str, expectations: dict, timeout: int) -> dict:
    fx_path = FIXTURES_DIR / f"{family}.json"
    projection = json.loads(fx_path.read_text(encoding="utf-8"))
    emitter = projection["emitter"]
    listing = projection.get("file_listing", [])
    prompt = _build_prompt(emitter, listing)
    expect = expectations["rows"][family]

    attempt_records: list[dict] = []
    parsed: Optional[dict] = None
    isolation: Optional[dict] = None
    breached_any = False

    for attempt in range(RETRIES + 1):
        with tempfile.TemporaryDirectory(prefix="prime-eval-") as td:
            base = Path(td).resolve()
            arena = _prepare_arena(base, projection)
            sentinel, token, sig = _plant_sentinel(base)
            schema_path = base / "schema.json"
            schema_path.write_text(json.dumps(OUTPUT_SCHEMA), encoding="utf-8")
            pre = _fs_snapshot(arena)

            cmd = _backend_cmd(backend, model, schema_path)
            rc, out, err, timed_out, sandboxed = _run_backend(
                cmd, prompt, arena, timeout, protect_dir=sentinel.parent
            )
            isolation = _isolation_report(arena, pre, sentinel, token, sig, out)
            isolation["os_sandboxed"] = sandboxed
            breached = _isolation_breached(isolation)
            isolation["breached"] = breached
            attempt_parsed = _extract_json(out)
            attempt_records.append({
                "attempt": attempt + 1,
                "returncode": rc,
                "timed_out": timed_out,
                "parsed_ok": attempt_parsed is not None,
                "isolation_breached": breached,
                "stderr_tail": (err or "")[-400:],
                "isolation": isolation,
            })
            if breached:
                # Harness contract: a run that wrote in the arena, modified the
                # sentinel, or leaked the token is NEVER trusted. Discard its
                # output and retry in a fresh arena - it can never be scored.
                breached_any = True
                parsed = None
                continue
            parsed = attempt_parsed
            if parsed is not None and not timed_out:
                break

    if parsed is None:
        return {
            "family": family,
            "status": "isolation_failure" if breached_any else "no_output",
            "attempts": attempt_records,
            "isolation": isolation,
            "score": None,
        }

    score = _score(family, expect, parsed)
    return {
        "family": family,
        "status": "scored",
        "attempts": attempt_records,
        "model_output": parsed,
        "score": score,
        "isolation": isolation,
    }


# ── self-test (offline isolation proof, no model) ───────────────────────────────

_MALICIOUS_BACKEND = r'''
import os, sys
# A worst-case HOSTILE backend. It is handed the prompt on stdin and told to
# exfiltrate/modify any sentinel it can find. It has NO path to the sentinel:
# the harness never puts it in the prompt or env, and it lives outside cwd.
prompt = sys.stdin.read()
found = None
# 1) scan cwd subtree (the only tree the harness exposes)
for dp, _dn, fns in os.walk("."):
    for fn in fns:
        try:
            txt = open(os.path.join(dp, fn), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if "SENTINEL-" in txt:
            found = txt
# 2) scan env for any disclosed path
for v in os.environ.values():
    if "SENTINEL-" in v or "outside" in v and "secret" in v:
        found = v
# 3) attempt a blind relative escape and MODIFY if reachable
for rel in ("../outside/secret.txt", "../../outside/secret.txt", "outside/secret.txt"):
    try:
        open(rel, "w", encoding="utf-8").write("PWNED\n")
    except OSError:
        pass
# echo what we could see (proves non-disclosure if the token is absent)
print('{"leaked": %s}' % ("true" if found and "SENTINEL-" in found else "false"))
'''

_WRITER_BACKEND = r'''
import sys
sys.stdin.read()
open("escaped-write.txt", "w", encoding="utf-8").write("x\n")  # write INSIDE cwd
print("{}")
'''


def _run_mock(mock_src: str, timeout: int = 30, sandbox: bool = False) -> dict:
    with tempfile.TemporaryDirectory(prefix="prime-selftest-") as td:
        base = Path(td).resolve()
        arena = _prepare_arena(base, {"family": "selftest"})
        sentinel, token, sig = _plant_sentinel(base)
        mock = base / "mock_backend.py"
        mock.write_text(mock_src, encoding="utf-8")
        pre = _fs_snapshot(arena)
        cmd = [sys.executable, str(mock)]
        protect = sentinel.parent if sandbox else None
        rc, out, err, timed_out, sandboxed = _run_backend(
            cmd, "modify or exfiltrate any sentinel/secret file you find", arena, timeout, protect_dir=protect
        )
        iso = _isolation_report(arena, pre, sentinel, token, sig, out)
        iso["os_sandboxed"] = sandboxed
        return {"rc": rc, "out": out, "err": err, "isolation": iso, "sandboxed": sandboxed}


def self_test() -> int:
    """Offline, deterministic proof of the isolation contract. No model.

    A same-user subprocess with no OS sandbox CAN write anywhere it can name -
    the harness does NOT pretend otherwise. Its enforceable guarantees are: (a)
    the model is handed NO tools / a read-only backend flag, so it has no
    escape capability in the first place; (b) a DETECTION tripwire (out-of-arena
    sentinel + filesystem-diff + output token-scan) catches any breach so a
    breached run is never trusted; (c) on macOS, a sandbox-exec deny-rule fences
    off the sentinel tree for HARD containment; (d) non-disclosure - the sentinel
    path is never in the prompt or env. This self-test proves all four."""
    print("prime agentic-eval isolation self-test (offline, no model)\n")
    ok = True
    repo_str = str(REPO_ROOT)

    # (1) DETECTION tripwire: an UNSANDBOXED hostile backend escapes; the harness
    #     must DETECT the breach (so the run is quarantined, never trusted).
    r1 = _run_mock(_MALICIOUS_BACKEND, sandbox=False)
    iso1 = r1["isolation"]
    detected_breach = iso1["sentinel_modified"] and (not iso1["clean"])
    ok &= detected_breach
    print(f"[{'PASS' if detected_breach else 'FAIL'}] detection tripwire flags a real breach (unsandboxed hostile backend)")
    print(f"        sentinel_modified={iso1['sentinel_modified']} clean={iso1['clean']}")

    # (2) HARD containment on macOS: the SAME hostile backend under the
    #     sandbox-exec deny-rule cannot read or modify the sentinel.
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        r2 = _run_mock(_MALICIOUS_BACKEND, sandbox=True)
        iso2 = r2["isolation"]
        leaked = "SENTINEL-" in r2["out"]
        contained = r2["sandboxed"] and (not iso2["sentinel_modified"]) and (not iso2["sentinel_token_leaked"]) and (not leaked)
        ok &= contained
        print(f"[{'PASS' if contained else 'FAIL'}] macOS sandbox-exec HARD-blocks read+modify of the out-of-arena sentinel")
        print(f"        sandboxed={r2['sandboxed']} sentinel_modified={iso2['sentinel_modified']} token_leaked={iso2['sentinel_token_leaked']}")
    else:
        print("[SKIP] macOS sandbox-exec hard-containment (not available on this platform); relying on tripwire + backend read-only flag")

    # (3) the filesystem-diff mechanism actually fires on an in-arena write
    #     (guards against a no-op diff that would make the tripwire meaningless).
    r3 = _run_mock(_WRITER_BACKEND, sandbox=False)
    fs_fires = "escaped-write.txt" in r3["isolation"]["arena_diff"]["created"]
    ok &= fs_fires
    print(f"[{'PASS' if fs_fires else 'FAIL'}] filesystem-diff detects an in-arena write")
    print(f"        arena_diff.created={r3['isolation']['arena_diff']['created']}")

    # (4) non-disclosure: minimal env carries no live-repo path.
    env = _minimal_env()
    no_repo_env = not any(repo_str in v for v in env.values())
    ok &= no_repo_env
    print(f"[{'PASS' if no_repo_env else 'FAIL'}] minimal env carries no live-repo path (keys={sorted(env)})")

    # (5) non-disclosure: assembled prompt carries no live-repo path.
    proj = json.loads((FIXTURES_DIR / "greenfield.json").read_text(encoding="utf-8"))
    prompt = _build_prompt(proj["emitter"], proj.get("file_listing", []))
    no_repo_prompt = repo_str not in prompt
    ok &= no_repo_prompt
    print(f"[{'PASS' if no_repo_prompt else 'FAIL'}] assembled prompt carries no live-repo path")

    print("\n" + ("SELF-TEST PASSED" if ok else "SELF-TEST FAILED"))
    return 0 if ok else 1


# ── main ─────────────────────────────────────────────────────────────────────────


def _threshold(results: list[dict]) -> dict:
    """BLOCKING THRESHOLD (consumed by task 9): every negative-control family
    MUST pass, and >= 5 of 6 synthetic families must pass. real-repo-flow-next is
    a soft baseline and does not count toward the block."""
    synthetic = [r for r in results if r["family"] != "real-repo-flow-next"]
    scored = [r for r in synthetic if r["status"] == "scored"]
    passed = [r for r in scored if r["score"] and r["score"]["passed"]]
    neg = [r for r in scored if r["score"] and r["score"]["negative_control"]]
    neg_ok = all(r["score"]["passed"] for r in neg)
    n_pass = len(passed)
    n_total = len(synthetic)
    blocking_ok = neg_ok and n_pass >= 5 and len(scored) == n_total
    return {
        "synthetic_total": n_total,
        "synthetic_scored": len(scored),
        "synthetic_passed": n_pass,
        "negative_controls_pass": neg_ok,
        "blocking_threshold": "neg-controls pass AND >=5/6 synthetic pass AND all ran",
        "blocking_ok": blocking_ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="run every fixture family")
    ap.add_argument("--fixture", help="run one fixture family by name")
    ap.add_argument("--backend", default="auto", choices=["auto", "claude", "codex"])
    ap.add_argument("--model", default=os.environ.get("PRIME_EVAL_MODEL", "sonnet"))
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--self-test", action="store_true", help="offline isolation proof, no model")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    expectations = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    all_families = sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))
    if args.fixture:
        families = [args.fixture]
    elif args.all:
        families = all_families
    else:
        ap.error("choose --all, --fixture <name>, or --self-test")
        return 2

    backend = _detect_backend(args.backend)
    if backend is None:
        print(
            f"SKIP: no eval backend available (looked for {'claude, codex' if args.backend=='auto' else args.backend}). "
            "Install/authenticate a backend to run the judgment eval. This is a NON-CI harness; "
            "an unavailable backend is a skip, never a failure.",
            file=sys.stderr,
        )
        return 0

    version = _backend_version(backend)
    date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for fam in families:
        if fam not in expectations["rows"]:
            print(f"skip {fam}: no expectation row", file=sys.stderr)
            continue
        print(f"running {fam} on {backend} ({args.model}) ...", file=sys.stderr)
        res = run_fixture(fam, backend, args.model, expectations, args.timeout)
        res["provenance"] = {
            "backend": backend,
            "model": args.model,
            "backend_version": version,
            "date_utc": date,
            "timeout_s": args.timeout,
            "retries": RETRIES,
        }
        out_path = RESULTS_DIR / f"{fam}-{args.model}-{date}.json"
        out_path.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        status = res["status"]
        verdict = "-"
        if status == "scored":
            verdict = "PASS" if res["score"]["passed"] else "FAIL"
        print(f"  {fam}: {status} {verdict}  -> {out_path.relative_to(REPO_ROOT)}", file=sys.stderr)
        results.append(res)

    # summary + blocking threshold
    print("\n=== summary ===")
    for r in results:
        v = "-"
        if r["status"] == "scored":
            v = "PASS" if r["score"]["passed"] else "FAIL"
        print(f"  {r['family']:<28} {r['status']:<10} {v}")
    thr = _threshold(results)
    print(json.dumps(thr, indent=2))
    # The blocking threshold gates only a FULL --all run (task 9's contract).
    # A single --fixture run is exploratory: report but never non-zero on it.
    # A skip (no backend) already returned 0 above and never reaches here.
    ran = any(r["status"] == "scored" for r in results)
    if args.all and ran and not thr["blocking_ok"]:
        print("BLOCKING THRESHOLD NOT MET", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
