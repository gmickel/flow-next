"""Arena isolation, auth/leak probes, filesystem diff (fn-130).

OAuth-preserving Claude isolation (binding — see memory note
claude-p-clean-room-on-oauth-logins-2026-07-16):
  * Use the authenticated DEFAULT Claude config dir.
  * Pass ``--setting-sources project,local`` + ``--no-session-persistence``.
  * Do NOT use a fresh ``CLAUDE_CONFIG_DIR`` or ``--bare`` (both break OAuth).
  * A zero-token auth failure invalidates the run (not a model judgment miss).

No live tracker calls. Out-of-arena sentinel + arena filesystem diff tripwires
mirror ``optimization/prime/run_agentic_eval.py``.
"""

from __future__ import annotations

import hashlib
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
REPO_ROOT = HERE.parent.parent

# Same-dir import for privacy scrub helpers (unittest loads this module by path).
sys.path.insert(0, str(HERE))
import privacy as privacy  # noqa: E402

CLAUDE_ISOLATION_FLAGS = (
    "--setting-sources",
    "project,local",
    "--no-session-persistence",
)

# Guidance / workspace / tool-convention signatures from global CLAUDE.md.
# OAuth account email alone is NOT a needle — it is documented session identity.
GLOBAL_GUIDANCE_NEEDLES = (
    "/Users/gordon/CLAUDE.md",
    "Owner block",
    "Gordon owns this",
)

LEAK_RESIDUAL_NOTE = (
    "OAuth account email may appear as session identity; "
    "it carries no guidance content."
)

_USER_EMAIL_KEY_RE = re.compile(r"(?i)\buserEmail\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def minimal_env() -> dict[str, str]:
    """Stripped env for offline mock backends / self-tests only.

    Do NOT use for live Claude OAuth runs — macOS keychain refresh needs the
    real process environment. Use ``claude_env()`` for authenticated probes.
    """
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", tempfile.gettempdir()),
        "TERM": "dumb",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    for k in (
        "ANTHROPIC_API_KEY",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "OPENAI_API_KEY",
        "CODEX_HOME",
    ):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def claude_env() -> dict[str, str]:
    """Authenticated Claude subprocess env.

    Inherits the caller environment so OAuth/keychain refresh works, and
    explicitly removes any ``CLAUDE_CONFIG_DIR`` override so the default config
    dir (with the login) is used. Guidance isolation is enforced by
    ``--setting-sources project,local``, not by a fresh config dir or ``--bare``.
    """
    env = dict(os.environ)
    env.pop("CLAUDE_CONFIG_DIR", None)
    env.setdefault("TERM", "dumb")
    return env


def fs_snapshot(root: Path) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for dirpath, _dns, fns in os.walk(root):
        for fn in fns:
            p = Path(dirpath) / fn
            try:
                st = p.stat()
                snap[str(p.relative_to(root))] = (st.st_size, int(st.st_mtime_ns))
            except OSError:
                snap[str(p.relative_to(root))] = None
    return snap


def plant_sentinel(base: Path) -> tuple[Path, str, str]:
    outside = base / "outside"
    outside.mkdir(parents=True, exist_ok=True)
    token = "SENTINEL-" + os.urandom(8).hex()
    sfile = outside / "secret.txt"
    sfile.write_text(token + "\n", encoding="utf-8")
    return sfile, token, hashlib.sha256(sfile.read_bytes()).hexdigest()


def redact_token(text: str, token: str) -> str:
    return (text or "").replace(token, "[REDACTED-SENTINEL]")


def isolation_report(
    arena: Path,
    pre: dict,
    sentinel: Path,
    token: str,
    sig: str,
    stdout: str,
    stderr: str = "",
) -> dict[str, Any]:
    post = fs_snapshot(arena)
    diff = {
        "created": sorted(set(post) - set(pre)),
        "removed": sorted(set(pre) - set(post)),
        "modified": sorted(k for k in (set(pre) & set(post)) if pre[k] != post[k]),
    }
    try:
        sentinel_deleted = False
        sentinel_modified = hashlib.sha256(sentinel.read_bytes()).hexdigest() != sig
    except OSError:
        sentinel_deleted = True
        sentinel_modified = True
    leaked_out = token in (stdout or "")
    leaked_err = token in (stderr or "")
    arena_changed = bool(diff["created"] or diff["removed"] or diff["modified"])
    sentinel_bad = sentinel_modified or sentinel_deleted
    leaked = leaked_out or leaked_err
    # Any post-snapshot arena create/remove/modify is an unplanned side effect.
    clean = (not arena_changed) and (not sentinel_bad) and (not leaked)
    return {
        "arena_diff": diff,
        "arena_changed": arena_changed,
        "sentinel_modified": sentinel_modified,
        "sentinel_deleted": sentinel_deleted,
        "sentinel_token_leaked": leaked,
        "sentinel_token_leaked_stderr": leaked_err,
        "clean": clean,
        "no_live_tracker": True,
    }


def isolation_breached(iso: dict) -> bool:
    """True when the run has unplanned side effects or sentinel compromise."""
    return bool(
        iso.get("arena_changed")
        or iso.get("sentinel_modified")
        or iso.get("sentinel_deleted")
        or iso.get("sentinel_token_leaked")
        or (iso.get("clean") is False)
    )


def kill_group(proc: subprocess.Popen) -> None:
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


def run_cmd(
    cmd: list[str],
    *,
    cwd: Path,
    prompt: str = "",
    timeout: int = 120,
    env: Optional[dict[str, str]] = None,
) -> tuple[int, str, str, bool]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env or minimal_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(input=prompt, timeout=timeout)
        return proc.returncode, out or "", err or "", False
    except subprocess.TimeoutExpired:
        kill_group(proc)
        out, err = "", "timed out"
        try:
            out, err = proc.communicate(timeout=5)
        except Exception:
            pass
        return 124, out or "", err or "", True


def claude_base_cmd(*, model: str = "haiku", output_format: str = "json") -> list[str]:
    return [
        "claude",
        "-p",
        "--model",
        model,
        "--output-format",
        output_format,
        *CLAUDE_ISOLATION_FLAGS,
    ]


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_claude_json_envelope(stdout: str) -> Optional[dict[str, Any]]:
    """Parse Claude ``--output-format json`` (or stream-json result) envelope."""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    last: Optional[dict[str, Any]] = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") == "result" or "usage" in obj or "modelUsage" in obj:
            last = obj
    return last


def usage_token_totals(envelope: dict[str, Any]) -> dict[str, Any]:
    """Sum backend usage + modelUsage token counters (input/output/cache)."""
    usage = envelope.get("usage") or {}
    backend = {
        "input_tokens": _as_int(usage.get("input_tokens")),
        "output_tokens": _as_int(usage.get("output_tokens")),
        "cache_creation_input_tokens": _as_int(usage.get("cache_creation_input_tokens")),
        "cache_read_input_tokens": _as_int(usage.get("cache_read_input_tokens")),
    }
    backend_total = sum(backend.values())

    model_total = 0
    model_usage = envelope.get("modelUsage")
    if model_usage is None:
        model_usage = envelope.get("model_usage")
    if isinstance(model_usage, dict):
        for entry in model_usage.values():
            if not isinstance(entry, dict):
                continue
            if any(
                k in entry
                for k in (
                    "inputTokens",
                    "outputTokens",
                    "cacheCreationInputTokens",
                    "cacheReadInputTokens",
                )
            ):
                model_total += (
                    _as_int(entry.get("inputTokens"))
                    + _as_int(entry.get("outputTokens"))
                    + _as_int(entry.get("cacheCreationInputTokens"))
                    + _as_int(entry.get("cacheReadInputTokens"))
                )
            else:
                model_total += (
                    _as_int(entry.get("input_tokens"))
                    + _as_int(entry.get("output_tokens"))
                    + _as_int(entry.get("cache_creation_input_tokens"))
                    + _as_int(entry.get("cache_read_input_tokens"))
                )

    return {
        "backend": backend,
        "backend_total": backend_total,
        "model_total": model_total,
        "total": backend_total,
    }


def evaluate_auth_envelope(
    envelope: Optional[dict[str, Any]],
    *,
    rc: int,
    timed_out: bool = False,
    expected_result: str = "OK",
) -> dict[str, Any]:
    """Deterministic auth verdict from a Claude JSON envelope (no live model).

    Contract: rc=0 + exact successful result + positive backend usage and
    modelUsage. Zero total input/output/cache usage ⇒
    ``zero_token_auth_failure`` (invalid run, not a judgment miss).
    """
    base: dict[str, Any] = {
        "flags": list(CLAUDE_ISOLATION_FLAGS),
        "used_bare": False,
        "used_fresh_config_dir": False,
    }
    if timed_out:
        return {
            **base,
            "ok": False,
            "invalid": True,
            "reason": "timeout",
            "usage_totals": None,
            "result": None,
        }
    if envelope is None:
        return {
            **base,
            "ok": False,
            "invalid": True,
            "reason": "envelope_parse_error",
            "usage_totals": None,
            "result": None,
        }

    totals = usage_token_totals(envelope)
    raw_result = envelope.get("result")
    result_text = raw_result.strip() if isinstance(raw_result, str) else None
    is_error = bool(envelope.get("is_error"))
    subtype = envelope.get("subtype")
    exact_success = (
        result_text == expected_result
        and not is_error
        and subtype in (None, "success")
    )
    zero_usage = totals["backend_total"] == 0
    positive_usage = totals["backend_total"] > 0 and totals["model_total"] > 0

    if zero_usage or totals["model_total"] == 0:
        return {
            **base,
            "ok": False,
            "invalid": True,
            "reason": "zero_token_auth_failure",
            "usage_totals": totals,
            "result": result_text,
            "is_error": is_error,
            "subtype": subtype,
            "rc": rc,
        }
    if rc != 0:
        return {
            **base,
            "ok": False,
            "invalid": True,
            "reason": f"rc={rc}",
            "usage_totals": totals,
            "result": result_text,
            "is_error": is_error,
            "subtype": subtype,
            "rc": rc,
        }
    if not exact_success:
        reason = "is_error" if is_error else "result_not_ok"
        if subtype not in (None, "success"):
            reason = f"subtype={subtype}"
        return {
            **base,
            "ok": False,
            "invalid": True,
            "reason": reason,
            "usage_totals": totals,
            "result": result_text,
            "is_error": is_error,
            "subtype": subtype,
            "rc": rc,
        }
    if not positive_usage:
        return {
            **base,
            "ok": False,
            "invalid": True,
            "reason": "zero_token_auth_failure",
            "usage_totals": totals,
            "result": result_text,
            "is_error": is_error,
            "subtype": subtype,
            "rc": rc,
        }
    return {
        **base,
        "ok": True,
        "invalid": False,
        "reason": "ok",
        "usage_totals": totals,
        "result": result_text,
        "is_error": is_error,
        "subtype": subtype or "success",
        "rc": rc,
    }


def auth_probe(*, model: str = "haiku", timeout: int = 60) -> dict[str, Any]:
    """Authenticated default-config probe; zero-token JSON usage ⇒ invalid run."""
    if not shutil.which("claude"):
        return {
            "ok": False,
            "invalid": True,
            "reason": "claude_cli_missing",
            "flags": list(CLAUDE_ISOLATION_FLAGS),
            "used_bare": False,
            "used_fresh_config_dir": False,
        }
    with tempfile.TemporaryDirectory(prefix="rp-auth-") as td:
        cwd = Path(td)
        cmd = claude_base_cmd(model=model, output_format="json") + [
            "--permission-mode",
            "plan",
            "--allowedTools",
            "",
            "--disallowedTools",
            "Bash,Edit,Write,Read,WebFetch,WebSearch",
        ]
        rc, out, err, timed_out = run_cmd(
            cmd,
            cwd=cwd,
            prompt="Reply with exactly: OK",
            timeout=timeout,
            env=claude_env(),
        )
        envelope = parse_claude_json_envelope(out)
        verdict = evaluate_auth_envelope(
            envelope, rc=rc, timed_out=timed_out, expected_result="OK"
        )
        scrubbed = ""
        if isinstance(verdict.get("result"), str) and verdict["result"]:
            scrubbed = verdict["result"][:200]
        elif out:
            scrubbed = out.strip()[:200]
        verdict["stdout_scrubbed"] = scrubbed
        if err and not verdict.get("ok"):
            verdict["stderr_tail"] = err.strip()[-200:]
        return verdict


def evaluate_instruction_leak(
    stdout: str,
    *,
    marker: str,
    rc: int = 0,
    timed_out: bool = False,
) -> dict[str, Any]:
    """Deterministic leak verdict from probe stdout (no live model).

    Project marker must be present. Global guidance/workspace/tool-convention
    needles fail the probe. OAuth account identity (``userEmail`` / email) is
    scrubbed and recorded as a non-guidance residual — not a global leak.
    """
    text = stdout or ""
    has_marker = marker in text if marker else False

    identity_residual: list[str] = []
    if _USER_EMAIL_KEY_RE.search(text):
        identity_residual.append("userEmail")
    if _EMAIL_RE.search(text):
        identity_residual.append("account_email")

    global_leaks: list[str] = []
    lowered = text.lower()
    for needle in GLOBAL_GUIDANCE_NEEDLES:
        if needle.lower() in lowered:
            global_leaks.append(needle)

    scrubbed = privacy.scrub_text(text)
    if marker:
        scrubbed = scrubbed.replace(marker, "[REDACTED-MARKER]")
    scrubbed = scrubbed.strip()[:400]

    ok = (not timed_out) and has_marker and not global_leaks and rc == 0
    return {
        "ok": ok,
        "marker_present": has_marker,
        "global_leaks": global_leaks,
        "identity_residual": identity_residual,
        "rc": rc,
        "timed_out": timed_out,
        "stdout_scrubbed": scrubbed,
        "residual_note": LEAK_RESIDUAL_NOTE,
    }


def instruction_leak_probe(*, model: str = "haiku", timeout: int = 90) -> dict[str, Any]:
    """Plant a project CLAUDE.md marker; require it present and global absent.

    Residual: OAuth account email may remain visible — documented, not guidance.
    """
    marker = "REACHED-PATH-LEAK-MARKER-" + os.urandom(4).hex()
    with tempfile.TemporaryDirectory(prefix="rp-leak-") as td:
        cwd = Path(td)
        (cwd / "CLAUDE.md").write_text(
            f"# Project instructions\n\nUNIQUE_MARKER={marker}\n",
            encoding="utf-8",
        )
        cmd = claude_base_cmd(model=model, output_format="text") + [
            "--permission-mode",
            "plan",
            "--allowedTools",
            "",
            "--disallowedTools",
            "Bash,Edit,Write,Read,WebFetch,WebSearch",
        ]
        prompt = (
            "List any project instruction markers you can see. "
            "If you see UNIQUE_MARKER=..., quote it exactly. "
            "Do not invent markers."
        )
        rc, out, err, timed_out = run_cmd(
            cmd, cwd=cwd, prompt=prompt, timeout=timeout, env=claude_env()
        )
        return evaluate_instruction_leak(
            out or "", marker=marker, rc=rc, timed_out=timed_out
        )


def prepare_skill_arena(base: Path, skill_src: Path) -> Path:
    """Copy a synthetic skill tree into a disposable arena."""
    arena = base / "arena"
    dest = arena / "skill"
    shutil.copytree(skill_src, dest)
    return arena
