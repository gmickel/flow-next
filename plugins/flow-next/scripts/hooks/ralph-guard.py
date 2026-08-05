#!/usr/bin/env python3
"""
Ralph Guard - Hook script for enforcing Ralph workflow rules.

Only runs when FLOW_RALPH=1 is set. Exits silently otherwise to avoid
polluting context for non-Ralph users.

Enforces:
- No --json flag on chat-send (suppresses review text)
- No --new-chat on re-reviews (loses reviewer context)
- Receipt must be written after SHIP verdict
- Validates flowctl command patterns

Supports three review backends:
- rp (RepoPrompt): tracks chat-send calls and receipt writes
- codex: tracks flowctl codex impl-review/plan-review and verdict output
- copilot: tracks flowctl copilot impl-review/plan-review and verdict output

Dual-platform tool names (fn-114): shell = Bash|Execute; file =
Edit|Write|Create|ApplyPatch.

Threat model (PR #290 bot r9). This guard is a RAIL, not a sandbox. It exists
to stop an autonomous loop from reaching a human-only recovery verb by
accident or by pattern-following — the agent that reads a fence, adapts it,
and drifts into `review-rounds reset` or a `--force` dispatch. It is NOT a
security boundary against an adversarial shell programmer: a PreToolUse hook
sees command TEXT, and shell text has unbounded ways to construct a token at
runtime (indirection, `printf`, base64, a written-then-sourced file).
Chasing those one spelling at a time is an arms race the guard loses.

So the boundary is STRUCTURAL: launcher recognition follows one hop of
same-command assignment (`fc=…/flowctl; "$fc" …`), subcommand positions must
be literal, and any command that BOTH composes a variable and executes that
variable fails closed regardless of content — closing the composed-token class
wholesale. Real containment for a hostile actor is the permission system and
the sandbox, not this file.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Optional

# Host tool names the guard accepts (Claude Code + Factory Droid).
SHELL_TOOLS = frozenset({"Bash", "Execute"})
FILE_TOOLS = frozenset({"Edit", "Write", "Create", "ApplyPatch"})


def _debug_enabled() -> bool:
    return os.environ.get("RALPH_GUARD_DEBUG") == "1"


def debug_log(message: str) -> None:
    """Append to debug log only when RALPH_GUARD_DEBUG=1 (Windows-safe tempdir)."""
    if not _debug_enabled():
        return
    path = Path(tempfile.gettempdir()) / "ralph-guard-debug.log"
    with path.open("a", encoding="utf-8") as f:
        f.write(message if message.endswith("\n") else message + "\n")


def get_state_file(session_id: str) -> Path:
    """Get state file path for this session (tempdir, not hardcoded /tmp)."""
    return Path(tempfile.gettempdir()) / f"ralph-guard-{session_id}.json"


def load_state(session_id: str) -> dict:
    """Load session state."""
    state_file = get_state_file(session_id)
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(), object_hook=state_decoder)
            # Ensure all expected keys exist
            state.setdefault("chats_sent", 0)
            state.setdefault("last_verdict", None)
            state.setdefault("window", None)
            state.setdefault("tab", None)
            state.setdefault("chat_send_succeeded", False)
            state.setdefault("flowctl_done_called", set())
            state.setdefault("codex_review_succeeded", False)
            state.setdefault("copilot_review_succeeded", False)
            return state
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return {
        "chats_sent": 0,
        "last_verdict": None,
        "window": None,
        "tab": None,
        "chat_send_succeeded": False,  # Track if chat-send actually returned review text
        "flowctl_done_called": set(),  # Track tasks that had flowctl done called
        "codex_review_succeeded": False,  # Track if codex review returned verdict
        "copilot_review_succeeded": False,  # Track if copilot review returned verdict
    }


def state_decoder(obj):
    """JSON decoder that handles sets."""
    if "flowctl_done_called" in obj and isinstance(obj["flowctl_done_called"], list):
        obj["flowctl_done_called"] = set(obj["flowctl_done_called"])
    return obj


def state_encoder(obj):
    """JSON encoder that handles sets."""
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def save_state(session_id: str, state: dict) -> None:
    """Save session state."""
    state_file = get_state_file(session_id)
    state_file.write_text(json.dumps(state, default=state_encoder))


def output_block(reason: str) -> None:
    """Output blocking response (exit code 2 style via stderr)."""
    print(reason, file=sys.stderr)
    sys.exit(2)


VALID_RECEIPT_VERDICTS = {"SHIP", "NEEDS_WORK", "MAJOR_RETHINK", "NEEDS_HUMAN"}


def is_receipt_write_command(command: str, receipt_path: str) -> bool:
    """Return true when a Bash command redirects output to the active receipt."""
    if not receipt_path:
        return False

    patterns = [
        rf">\s*['\"]?{re.escape(receipt_path)}['\"]?",
        r">\s*['\"]?.*receipts/.*\.json",
        r">\s*['\"]?\$[{]?REVIEW_RECEIPT_PATH[}]?['\"]?",
        r">\s*['\"]?\$[{]?RECEIPT_PATH[}]?['\"]?",
        r">\s*['\"]?\$[{]?RECEIPT_DIR[}]?/",
        r"cat\s*>\s*.*receipt",
        r"\btee\s+['\"]?\$[{]?REVIEW_RECEIPT_PATH[}]?['\"]?",
        r"\btee\s+['\"]?\$[{]?RECEIPT_PATH[}]?['\"]?",
    ]
    receipt_dir = os.path.dirname(receipt_path)
    if receipt_dir:
        patterns.append(rf">\s*['\"]?{re.escape(receipt_dir)}")
    return any(re.search(pattern, command, re.I) for pattern in patterns)


def _normalize_path_for_match(path: str) -> str:
    """Normalize a path string for receipt equality checks (no filesystem resolve)."""
    if not path:
        return ""
    p = path.strip().strip("'\"")
    p = p.replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    if p.startswith("./"):
        p = p[2:]
    return p.rstrip("/")


def is_receipt_file_path(file_path: str, receipt_path: str) -> bool:
    """True when a file-tool path targets the active review receipt."""
    if not receipt_path or not file_path:
        return False
    fp = _normalize_path_for_match(file_path)
    rp = _normalize_path_for_match(receipt_path)
    if not fp or not rp:
        return False
    if fp == rp or fp.endswith("/" + rp) or rp.endswith("/" + fp):
        return True
    # Basename match under a receipts/ directory (same convention as Bash patterns)
    if "/receipts/" in fp and os.path.basename(fp) == os.path.basename(rp):
        return True
    return False


def file_tool_path(tool_input: dict) -> str:
    """Best-effort file path from Edit/Write/Create/ApplyPatch tool_input."""
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "path", "filePath", "target_file"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def file_tool_content(tool_input: dict) -> str:
    """Best-effort body text from a file-write tool_input."""
    if not isinstance(tool_input, dict):
        return ""
    for key in ("content", "new_string", "new_str", "contents"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def command_has_json_field(command: str, field: str) -> bool:
    """Best-effort check that a shell command writes a JSON field literally."""
    return bool(re.search(rf"['\"]{re.escape(field)}['\"]\s*:", command))


def content_has_json_field(content: str, field: str) -> bool:
    """Best-effort check that a file body includes a JSON field literally."""
    if not content:
        return False
    return bool(re.search(rf"['\"]{re.escape(field)}['\"]\s*:", content))


def _tool_response_text(tool_response) -> str:
    """Extract stdout/text from a PostToolUse tool_response payload."""
    if isinstance(tool_response, dict):
        stdout = tool_response.get("stdout", "")
        if isinstance(stdout, str) and stdout:
            return stdout
        return str(tool_response) if tool_response else ""
    if isinstance(tool_response, str):
        return tool_response
    return ""


def _tool_response_exit_code(tool_response) -> Optional[int]:
    """Return integer exit code from tool_response when present, else None."""
    if not isinstance(tool_response, dict):
        return None
    if tool_response.get("interrupted") is True:
        return 1
    for key in ("exit_code", "exitCode", "returncode", "statusCode"):
        if key not in tool_response:
            continue
        try:
            return int(tool_response[key])
        except (TypeError, ValueError):
            return 1
    return None


def _parse_json_objects(text: str) -> Iterator[dict]:
    """Yield JSON objects from full text or individual lines."""
    if not text:
        return
    stripped = text.strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            yield data
            return
    except (json.JSONDecodeError, TypeError):
        pass
    for line in stripped.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            yield data


def is_flowctl_done_success(task_id: str, command: str, tool_response, response_text: str) -> bool:
    """Structured success signal for flowctl done (no prose word sniff).

    Accepts:
      * tool_response exit code == 0 (when present), and
      * --json stdout with status=="done" (preferred), or
      * exact flowctl plain-text contract line: ``Task <id> completed``
    Rejects non-zero exit, interrupted, JSON errors, and free-form "done" text.
    """
    exit_code = _tool_response_exit_code(tool_response)
    if exit_code is not None and exit_code != 0:
        return False

    wants_json = bool(re.search(r"--json\b", command))
    for obj in _parse_json_objects(response_text):
        if obj.get("success") is False:
            continue
        if obj.get("status") != "done":
            continue
        obj_id = obj.get("id")
        if obj_id and obj_id != task_id:
            continue
        return True

    if wants_json:
        # --json required a parseable status=done object; none found.
        return False

    # Exit code alone is a structured success signal when the host provides it.
    if exit_code == 0:
        return True

    # Exact non-JSON flowctl contract (not a substring word sniff).
    if re.search(rf"(?m)^Task\s+{re.escape(task_id)}\s+completed\s*$", response_text):
        return True

    return False


def review_succeeded(state: dict) -> bool:
    """True when any review backend has completed for this session."""
    return bool(
        state.get("chat_send_succeeded")
        or state.get("codex_review_succeeded")
        or state.get("copilot_review_succeeded")
    )


# Sandbox flags allowed in a canonical Codex delegation invocation (R9). Exactly
# the two the reference emits: yolo (--dangerously-bypass-approvals-and-sandbox)
# and full-auto (-s workspace-write). Nothing else (no --full-auto, no other -s).
_DELEGATE_YOLO_FLAG = "--dangerously-bypass-approvals-and-sandbox"


# Canonical scratch-file basenames the reference emits (codex-delegation.md). A
# delegation path must be EXACTLY `[./].flow/tmp/codex-<id>/<one-of-these>` — no
# extra path segments, no `..` traversal (which would prefix-match the scratch
# dir yet escape it, e.g. `.flow/tmp/codex-x/../../tasks/y.json`).
_SCRATCH_BASENAMES = {
    "schema": r"result-schema\.json",
    "result": r"result-batch-\d+\.json",
    "prompt": r"prompt-batch-\d+\.md",
}


def _scratch_dir_of(path: str, kind: str):
    """Return the `.flow/tmp/codex-<id>` scratch dir of a delegation `path`, or
    None. STRICT — the path must be exactly
    ``[./].flow/tmp/codex-<id>/<canonical-basename>`` for the given `kind`
    (schema | result | prompt). No nested subdirs, no ``..`` traversal, no
    absolute path, no backslash — so a path that prefix-matches the scratch dir
    but then escapes it (`codex-x/../../tasks/y.json`) is rejected.

    The `<id>` segment itself is constrained to a flow-id charset
    (`[A-Za-z0-9._-]+`) so it cannot smuggle a `.` (current-dir) or a slash."""
    basename = _SCRATCH_BASENAMES[kind]
    m = re.fullmatch(
        r"(?:\./)?(\.flow/tmp/codex-[A-Za-z0-9._-]+)/" + basename, path
    )
    if not m:
        return None
    # Defensive: the id charset allows dots, so explicitly reject any `..` segment
    # in the captured scratch dir (e.g. a literal `codex-..`).
    scratch = m.group(1)
    if any(seg in ("", ".", "..") for seg in scratch.split("/")):
        return None
    return scratch


def is_canonical_codex_delegation(command: str) -> bool:
    """Return True ONLY for the FULL canonical Codex implementation-delegation
    shape that fn-55 teaches (worker.md Phase 2 / codex-delegation.md).

    **Tokenized, not substring-matched.** The command is parsed with ``shlex``
    (POSIX shell-token semantics) and validated as an ARGV — so required flags
    cannot be smuggled inside a quoted positional prompt while ``codex exec``
    actually receives none of them. Every argv token must be one the canonical
    invocation emits; an unexpected token (a stray prompt arg, an extra flag, a
    chaining operator that survives tokenization) → block.

    EVERY one of the following must hold:

      * the command tokenizes cleanly and contains NO shell control operator
        (``;`` ``&&`` ``||`` ``|`` ``&`` ``$(`` backtick ``>`` newline …) — a
        canonical delegation is exactly ONE command;
      * leading ``FLOW_DELEGATE_CODEX=1`` env-prefix token, then ``codex``
        ``exec`` (NOT ``resume`` / ``review``) — exactly ONE ``codex`` token;
      * ``--ignore-user-config`` as a standalone token (load-bearing — without it
        MCP servers can re-enable and silently drop ``--output-schema``);
      * ``-o`` output target under a ``.flow/tmp/codex-<id>/`` scratch dir, AND
        ``--output-schema`` + the stdin prompt (``- < …``) under the SAME dir;
      * a sandbox flag from the allowlist (yolo | ``-s workspace-write``);
      * NO ``--last``; and no token outside the canonical set.

    Any deviation falls through → the normal block path.
    """
    # 0. Reject shell control operators BEFORE tokenizing. shlex tokenizes `;`,
    #    `&&`, `|` as ordinary WORDS (it is not a parser), so it would not catch
    #    chaining on its own. A literal control char means this is not one
    #    canonical command. `<` is NOT banned — it is the single permitted stdin
    #    redirect (`- < <scratch>/prompt…`), validated as a token in the walk
    #    below. `>` (any output redirect), `;`, `&`, `|`, backtick, newline,
    #    `$(…)`, `${…}`, and subshell parens ARE banned (none are canonical).
    #    Quotes/backslashes are fine — shlex handles them; we only ban operators.
    if re.search(r"[;&|`\n>()]|\$\(|\$\{", command):
        return False

    # 1. Tokenize with POSIX shell semantics. A `<` stdin redirect tokenizes to a
    #    standalone `<` word (shlex is not a parser), which we validate in-stream.
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return False  # unbalanced quotes / parse error → not canonical
    if not tokens:
        return False

    # 2. Leading env-prefix token, then `codex exec`.
    if tokens[0] != "FLOW_DELEGATE_CODEX=1":
        return False
    if len(tokens) < 3 or tokens[1] != "codex" or tokens[2] != "exec":
        return False
    # Exactly ONE codex token total (no smuggled second `codex …`).
    if tokens.count("codex") != 1:
        return False
    # `--last` is forbidden ANYWHERE, including as a consumed option value
    # (e.g. `-m --last` would otherwise slip past the per-option check by being
    # swallowed as the `-m` value). A global token-level reject closes that.
    if "--last" in tokens:
        return False

    # 3. Walk the remaining argv as a strict allowlist. Track required flags +
    #    the scratch dir. ANY unexpected token → block (this is what defeats the
    #    quoted-prompt-smuggling vector: a stray positional prompt is unexpected).
    i = 3
    n = len(tokens)
    # Each singleton may appear AT MOST ONCE — a duplicate flag (e.g. a second
    # `-c` smuggling `mcp_servers.evil.command=…` to re-enable MCP and undo the
    # `--ignore-user-config` isolation) is non-canonical. `counts` enforces it.
    counts = {
        "--ignore-user-config": 0,
        "-m": 0,
        "-c": 0,
        "--output-schema": 0,
        "-o": 0,
        "sandbox": 0,
        "prompt": 0,
    }
    scratch = None
    schema_dir = None
    prompt_dir = None

    def _need_value(idx: int):
        return tokens[idx + 1] if idx + 1 < n else None

    while i < n:
        tok = tokens[i]
        if tok == "--last":
            return False  # always forbidden
        if tok == "--ignore-user-config":
            counts["--ignore-user-config"] += 1
            i += 1
        elif tok == "-m":  # model — a single safe model token (pinned upstream)
            val = _need_value(i)
            # Must be a real model name, not a swallowed flag. Constrain to a
            # model charset (alnum + . _ : -) and forbid a leading `-` so an
            # adversary can't park a flag (e.g. `-m --last`) as the value.
            if val is None or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", val):
                return False
            counts["-m"] += 1
            i += 2
        elif tok == "-c":  # reasoning-effort pair ONLY
            val = _need_value(i)
            # Exactly the effort knob — NOT an arbitrary Codex `-c key=value`
            # override. An extra `-c mcp_servers.…` would re-enable MCP and
            # silently defeat --ignore-user-config, so only the effort pair with
            # an enum value is allowed.
            if val is None or not re.fullmatch(
                r'model_reasoning_effort="(none|low|medium|high|xhigh)"', val
            ):
                return False
            counts["-c"] += 1
            i += 2
        elif tok == "--output-schema":
            val = _need_value(i)
            if val is None:
                return False
            counts["--output-schema"] += 1
            schema_dir = _scratch_dir_of(val, "schema")
            i += 2
        elif tok == "-o":
            val = _need_value(i)
            if val is None:
                return False
            counts["-o"] += 1
            scratch = _scratch_dir_of(val, "result")
            i += 2
        elif tok == _DELEGATE_YOLO_FLAG:
            counts["sandbox"] += 1
            i += 1
        elif tok == "-s":  # full-auto sandbox: -s workspace-write
            if _need_value(i) != "workspace-write":
                return False
            counts["sandbox"] += 1
            i += 2
        elif tok == "-":
            # stdin prompt: `-` then `<` then the prompt path.
            if _need_value(i) != "<":
                return False
            path = tokens[i + 2] if i + 2 < n else None
            if path is None:
                return False
            counts["prompt"] += 1
            prompt_dir = _scratch_dir_of(path, "prompt")
            i += 3
        else:
            # Unknown / unexpected token (a smuggled prompt, an extra flag,
            # a second positional). Non-canonical → block.
            return False

    # 4. Each singleton must appear EXACTLY ONCE (no missing, no duplicate).
    #    `-m` is REQUIRED, not optional: with `--ignore-user-config` a missing
    #    `-m` falls back to codex's built-in default model (NOT gpt-5.5), which
    #    violates the "model always passed explicitly from flow config" contract
    #    (R6/R9). Require exactly one, same as `-c` (effort) and the rest.
    for key in ("--ignore-user-config", "-m", "-c", "--output-schema", "-o", "sandbox", "prompt"):
        if counts[key] != 1:
            return False

    # 5. The -o / schema / prompt must share ONE valid scratch dir.
    if scratch is None:
        return False
    if schema_dir != scratch or prompt_dir != scratch:
        return False

    return True


def validate_receipt_data(
    data: object,
    receipt_path: str = "",
    expected_kind: str = "",
    expected_id: str = "",
) -> str:
    """Return empty string for valid receipt data, otherwise an error string."""
    if not isinstance(data, dict):
        return "expected object"

    receipt_type = data.get("type")
    receipt_id = data.get("id")
    verdict = data.get("verdict")
    if not receipt_type or not receipt_id:
        return "missing type/id"
    if verdict not in VALID_RECEIPT_VERDICTS:
        return "missing or invalid verdict"

    if receipt_path and (not expected_kind or not expected_id):
        parsed_kind, parsed_id = parse_receipt_path(receipt_path)
        if parsed_id != "UNKNOWN":
            expected_kind = expected_kind or parsed_kind
            expected_id = expected_id or parsed_id

    if expected_kind and receipt_type != expected_kind:
        return f"type mismatch: expected {expected_kind}, got {receipt_type}"
    if expected_id and receipt_id != expected_id:
        return f"id mismatch: expected {expected_id}, got {receipt_id}"

    return ""


def validate_receipt_file(receipt_path: str) -> str:
    """Return empty string for a valid receipt file, otherwise an error string."""
    path = Path(receipt_path)
    if not path.exists():
        return "missing receipt"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"invalid JSON: {exc}"
    return validate_receipt_data(data, receipt_path=receipt_path)


# --- Memory helpers ---


def get_repo_root() -> Path:
    """Find git repo root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return Path.cwd()


def is_memory_enabled() -> bool:
    """Check if memory is enabled in .flow/config.json."""
    config_path = get_repo_root() / ".flow" / "config.json"
    if not config_path.exists():
        return False
    try:
        config = json.loads(config_path.read_text())
        return config.get("memory", {}).get("enabled", False)
    except (json.JSONDecodeError, Exception):
        return False


def output_json(data: dict) -> None:
    """Output JSON response."""
    print(json.dumps(data))
    sys.exit(0)


# Files that Ralph must never modify during a run
PROTECTED_FILE_PATTERNS = [
    "ralph-guard.py",
    "ralph-guard",
    # fn-114: hooks live in PROJECT settings now - a Ralph-driven agent must
    # not be able to edit its own registration out from under the guard.
    ".claude/settings.json",
    ".factory/hooks.json",
    ".factory/settings.json",
    ".codex/hooks.json",
    "flowctl.py",
    "flowctl",
    "/hooks/hooks.json",
    # fn-168 R7: the review-round cap has a persistent rung (review.maxIterations),
    # so the config file is now a self-grant path — an agent could raise its own
    # gate with a file tool and never touch `flowctl config set`. Screens FILE
    # TOOLS only, so flowctl's own writers (`config set`, tracker resolve
    # transactions) are unaffected.
    ".flow/config.json",
]


def handle_protected_file_check(data: dict) -> None:
    """Block file tools targeting protected workflow files (prevent self-modification)."""
    tool_input = data.get("tool_input", {})
    file_path = file_tool_path(tool_input)
    if not file_path:
        return
    for pattern in PROTECTED_FILE_PATTERNS:
        if file_path.endswith(pattern):
            output_block(
                f"BLOCKED: Cannot modify protected file '{os.path.basename(file_path)}'. "
                "Ralph must not edit its own workflow tooling (ralph-guard, flowctl, hooks). "
                "If the guard is blocking incorrectly, report the bug instead of bypassing it."
            )


def handle_file_tool_receipt_check(data: dict) -> None:
    """Block Edit|Write|Create|ApplyPatch of the receipt path before review (Bash parity)."""
    receipt_path = os.environ.get("REVIEW_RECEIPT_PATH", "")
    if not receipt_path:
        return
    tool_input = data.get("tool_input", {})
    file_path = file_tool_path(tool_input)
    if not is_receipt_file_path(file_path, receipt_path):
        return

    session_id = data.get("session_id", "unknown")
    state = load_state(session_id)
    if not review_succeeded(state):
        output_block(
            "BLOCKED: Cannot write receipt before review completes. "
            "You must run 'flowctl rp chat-send', 'flowctl codex impl-review/plan-review', "
            "or 'flowctl copilot impl-review/plan-review' and receive a review "
            "response before writing the receipt."
        )

    content = file_tool_content(tool_input)
    if content:
        if not content_has_json_field(content, "type"):
            output_block(
                "BLOCKED: Receipt JSON is missing required 'type' field. "
                'Receipt must include: {"type":"...","id":"...","verdict":"...",...} '
                "Copy the exact command from the prompt template."
            )
        if not content_has_json_field(content, "id"):
            output_block(
                "BLOCKED: Receipt JSON is missing required 'id' field. "
                'Receipt must include: {"type":"...","id":"<TASK_OR_EPIC_ID>",...} '
                "Copy the exact command from the prompt template."
            )
        if not content_has_json_field(content, "verdict"):
            output_block(
                "BLOCKED: Receipt JSON is missing required 'verdict' field. "
                'Review receipts must include: {"verdict":"SHIP",...} '
                "Copy the exact command from the prompt template."
            )

    receipt_type, item_id = parse_receipt_path(receipt_path)
    if receipt_type == "impl_review":
        task_id = item_id
        done_set = state.get("flowctl_done_called", set())
        if isinstance(done_set, list):
            done_set = set(done_set)
        if task_id not in done_set:
            output_block(
                f"BLOCKED: Cannot write impl receipt for {task_id} - flowctl done was not called. "
                f"You MUST run 'flowctl done {task_id} --evidence ...' BEFORE writing the receipt. "
                "The task is NOT complete until flowctl done succeeds."
            )


_SHELL_COMMAND_SEPARATORS = frozenset({"|", "||", "&", "&&", ";", "(", ")"})
_FLOWCTL_PATH_RE = re.compile(r"(?:.*/)?flowctl(?:\.py)?$")
_REVIEW_BACKENDS = frozenset({"codex", "copilot", "cursor"})
_REVIEW_DISPATCHES = frozenset({"impl-review", "plan-review", "completion-review"})
_ENV_ASSIGN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
_DURATION_RE = re.compile(r"\d+(?:\.\d+)?[smhd]?")
# PR #290 bot r4: raw-text launcher reference — `$FLOWCTL`/`${FLOWCTL}`, a bare
# or path-qualified `flowctl` / `flowctl.py`. Used only by the raw floor, where
# "this text drives flowctl" is the question, not "which argv".
_FLOWCTL_TEXT_RE = re.compile(
    r"\$\{?FLOWCTL\}?|(?<![\w./-])(?:[\w.-]+/)*flowctl(?:\.py)?(?![\w-])"
)
# An assignment whose VALUE is a guarded recovery verb: `verb=review-rounds`,
# `sub="reset"`, `v='reset-review-rounds'`. The verb never touches the launcher
# until expansion, so the adjacency screens above cannot see it.
_RECOVERY_ASSIGN_RE = re.compile(
    r"(?:^|[\s;&|(])[A-Za-z_][A-Za-z0-9_]*=['\"]?"
    r"(?:reset-review-rounds|review-rounds|reset)['\"]?(?=[\s;&|)]|$)"
)
# Same, for the --force screen's verbs.
_FORCE_ASSIGN_RE = re.compile(
    r"(?:^|[\s;&|(])[A-Za-z_][A-Za-z0-9_]*=['\"]?"
    r"(?:review-rounds|increment|impl-review|plan-review|completion-review)"
    r"['\"]?(?=[\s;&|)]|$)"
)
# PR #290 bot r5: an argv token carrying an unexpanded shell expansion —
# `$verb`, `${verb}`, `$(…)`, backticks. Composition (`verb="${verb}-rounds"`)
# defeats every value-matching screen, so the SUBCOMMAND positions are held to
# a literal-only contract instead: what a variable might expand to is
# unknowable here, so an expansion in those positions fails closed.
_ARGV_EXPANSION_RE = re.compile(r"[$`]")
# The FIRST token after the launcher is always a subcommand, so an expansion
# there is unknowable and blocked outright. The SECOND token is a subcommand
# only under a group (`review-rounds reset`, `spec reset-review-rounds`,
# `codex impl-review`); under a leaf verb it is an ARGUMENT, and
# `flowctl show "$TASK_ID"` / `flowctl done "$ID"` must stay legal. So depth 2
# is enforced exactly for the groups that OWN a guarded verb.
_GUARDED_SUBCOMMAND_GROUPS = frozenset({"spec", "review-rounds"})
# PR #290 bot r6: the literal-subcommand rule stopped at the subcommand slots,
# so a composed FLAG still executed —
# `flag=--for; flag="${flag}ce"; "$FLOWCTL" codex impl-review fn-1.1 "$flag"`.
# For the GUARDED dispatches only (a review backend's `*-review`, and
# `review-rounds increment`), an argument-position expansion is therefore held
# to the two shapes every shipped fence actually uses: the value of a literal
# value-taking flag, or the id positional that comes first. Anything else is
# unknowable pre-expansion and fails closed.
#
# The value-taking long options of `{codex,copilot,cursor} {impl,plan,
# completion}-review` and `review-rounds increment` (their store_true flags —
# --force, --json, --help — deliberately absent: nothing may follow them).
_GUARDED_DISPATCH_VALUE_FLAGS = frozenset({
    "--base", "--files", "--focus", "--receipt", "--sandbox", "--spec",
    "--kind", "--task", "--review-type", "--artifact-sha256", "--artifact-file",
})
# Raw-text floor for the same smuggle: an assignment whose VALUE starts a flag
# (`flag=--for`, `f+='-'`). Fences build flags inside `args+=(--base …)` array
# appends, never as a dash-leading scalar assignment, so this only fires on
# composition — and only when the command also drives a launcher AND names a
# guarded dispatch verb.
_DASH_VALUE_ASSIGN_RE = re.compile(
    r"(?:^|[\s;&|(])[A-Za-z_][A-Za-z0-9_]*\+?=['\"]?-{1,2}[A-Za-z]"
)
_GUARDED_DISPATCH_TEXT_RE = re.compile(
    r"impl-review|plan-review|completion-review"
    r"|review-rounds['\"]?\s+['\"]?increment\b"
)
_ARGV_WRAPPERS = frozenset({
    "env", "timeout", "nice", "xargs", "nohup", "stdbuf",
    # PR #290 bot r3: shell builtins that run their argv transparently. Without
    # them, `command "$FLOWCTL" "review-rounds" "reset" …` was classified as a
    # `command` invocation and never reached the flowctl argv screen.
    "command", "exec", "builtin", "sudo",
})
# PR #290 bot r8: an option that takes a SEPARATE value token. Popping the
# option alone left its value sitting in the launcher position
# (`env -u X "$FLOWCTL" review-rounds "$sub" …` classified `X` as the
# executable), so the whole flowctl argv screen — including the composed-verb
# rules — was skipped. Attached spellings (`--unset=X`, `-I{}`, `-n5`) carry
# their value inside the one token and need no extra pop.
_WRAPPER_VALUE_OPTIONS: dict[str, frozenset[str]] = {
    "env": frozenset({"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}),
    "timeout": frozenset({"-s", "--signal", "-k", "--kill-after"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "xargs": frozenset({
        "-a", "--arg-file", "-I", "-i", "--replace", "-d", "--delimiter",
        "-n", "--max-args", "-P", "--max-procs", "-s", "--max-chars",
        "-L", "--max-lines", "-E", "-e", "--eof",
    }),
    "stdbuf": frozenset({"-i", "--input", "-o", "--output", "-e", "--error"}),
    "nohup": frozenset(),
    "sudo": frozenset({"-u", "--user", "-g", "--group", "-p", "--prompt"}),
    # `command -p/-v/-V`, `builtin`, `exec -a NAME`.
    "command": frozenset(),
    "builtin": frozenset(),
    "exec": frozenset({"-a"}),
}
# Only `timeout` takes a bare DURATION positional before its command; popping
# digit-ish tokens for every wrapper would eat a legitimate first argument.
_DURATION_POSITIONAL_WRAPPERS = frozenset({"timeout"})
_SHELL_INTERPRETERS = frozenset({"sh", "bash", "zsh", "dash", "ksh"})
# Single-letter flags a shell accepts in a combined cluster alongside `c`
# (`-lc`, `-xec`). Used only to tell a cluster apart from an ATTACHED command
# string (`-cecho hi`), never to validate the invocation.
_SHELL_SHORT_FLAG_LETTERS = frozenset("abefhiklmnprstuvxBCEHPT")
_MAX_WRAPPER_DEPTH = 3
# A shell line continuation: backslash + newline, which bash removes entirely.
_LINE_CONTINUATION_RE = re.compile(r"\\\r?\n")
# PR #290 bot r9 (a): a shell assignment, split into name / operator / value.
# Values may be single-quoted, double-quoted, or bare.
_SHELL_ASSIGN_RE = re.compile(
    r"(?:^|[\s;&|(])([A-Za-z_][A-Za-z0-9_]*)(\+?=)"
    r"('[^']*'|\"[^\"]*\"|[^\s;&|)]*)"
)
# The variable names the bash preamble always uses for the bundled launcher.
_LAUNCHER_VAR_NAMES = frozenset({"FLOWCTL"})
# Names inside an expansion token: `$fc`, `${fc}`, `${fc%.*}`, `"${a}${b}"`.
_EXPANSION_NAME_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")
# The `args=` / `args+=` token that precedes an array literal's `(`.
_ARRAY_ASSIGN_PREFIX_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
# A token that is NOTHING BUT one variable expansion: `$fc`, `${fc}`. Quotes
# are already stripped by the tokenizer. Deliberately strict — a token that
# merely CONTAINS `$FLOWCTL` (an assignment capturing a command substitution,
# say) is not an execution of it.
_SIMPLE_VAR_TOKEN_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}$|\$([A-Za-z_][A-Za-z0-9_]*)$")


def _collapse_line_continuations(command: str) -> str:
    """Remove `\\<newline>` the way bash does, before any screen reads it.

    Bash deletes the pair ENTIRELY — it is not whitespace. Substituting a space
    (fn-159 verification F1) re-split every INTRA-word continuation the guard
    exists to catch: `re\\<newline>set`, `reset-review-\\<newline>rounds` and
    `--fo\\<newline>rce` all ran as the joined word while both screens saw two
    harmless tokens. Removal also joins across single quotes, where bash would
    keep the backslash-newline literal; that direction over-blocks a quoted
    string that happens to look like a guarded verb, which is the fail-closed
    side and matches the raw-text floor's existing posture.
    """
    return _LINE_CONTINUATION_RE.sub("", command)


def _tokenize_shell_command(command: str) -> Optional[list[str]]:
    """Return shell tokens, preserving operators as command boundaries.

    These are guard decisions, so quoted flags must become their real argv
    tokens rather than matching only as raw command substrings. ``shlex`` is
    sufficient here because this only identifies each top-level flowctl argv.
    Malformed shell text is NOT classified here: it returns ``None`` so the
    caller falls back to the raw-text marker screen, which is what actually
    fails closed on the forbidden verbs.

    Line continuations are collapsed FIRST (fn-159 review F2): ``shlex`` keeps
    ``\\<newline>`` as a token of its own, so `review-rounds \\\\n reset` split
    the verb from its subcommand for both this pass and the raw-text floor
    while bash ran the very command both screens exist to block.
    """
    command = _collapse_line_continuations(command)
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;()<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return None


def _expansion_names(token: str) -> set:
    """Variable names referenced by an expansion token."""
    return set(_EXPANSION_NAME_RE.findall(token))


def _simple_variable_name(token: str) -> Optional[str]:
    """The variable name when the token is exactly one expansion, else None."""
    match = _SIMPLE_VAR_TOKEN_RE.fullmatch(token)
    if not match:
        return None
    return match.group(1) or match.group(2)


def _launcher_variables(command: str) -> frozenset:
    """Variables this command text ASSIGNS a flowctl launcher path.

    One hop, same command text, no composition (PR #290 bot r9 (a)):
    `fc=.flow/bin/flowctl; "$fc" review-rounds "$verb" …` executes the launcher
    just as surely as spelling it out, so `"$fc"` in a command position is
    launcher-equivalent and the whole flowctl argv screen applies to it.
    Deliberately NOT a dataflow engine — a value that is itself built from
    other variables is handled by the composition screen below, not resolved.
    """
    names = set(_LAUNCHER_VAR_NAMES)
    for name, operator, value in _SHELL_ASSIGN_RE.findall(command):
        if operator != "=":
            continue
        value = _unquote(value)
        if _FLOWCTL_PATH_RE.fullmatch(value):
            names.add(name)
            continue
        # fn-159 verification F2: a SELF-DEFAULT binds the launcher just as
        # surely (`fc="${fc:-.flow/bin/flowctl}"`). Recognizing only the bare
        # literal left such a var neither launcher-recognized nor composed, so
        # `"$fc" review-rounds "$V" …` was screened by nothing at all.
        default = _self_default_value(name, value)
        if default is not None and _FLOWCTL_PATH_RE.fullmatch(default):
            names.add(name)
    return frozenset(names)


def _unquote(value: str) -> str:
    """Drop one matched pair of surrounding quotes from an assignment value."""
    if value[:1] in ("'", '"') and value[-1:] == value[:1] and len(value) > 1:
        return value[1:-1]
    return value


def _strip_self_default_expansions(name: str, value: str) -> str:
    """Drop `${name:-…}`-style default heads so they read as no self-reference.

    Covers the four default-expansion operators (`:-`, `-`, `:=`, `=`). The
    head alone is removed, so anything nested in the DEFAULT is still seen.
    """
    return re.sub(r"\$\{" + re.escape(name) + r":?[-=]", "", value)


def _self_default_value(name: str, value: str) -> Optional[str]:
    """The fallback literal when `value` is EXACTLY `${name:-…}`, else None.

    Covers the four default operators (`:-`, `-`, `:=`, `=`). A self reference
    that is only PART of the value (`"${p:-$p}ctl"`) is not a self-default —
    it is composition — and returns None.
    """
    if not value.startswith("${" + name) or not value.endswith("}"):
        return None
    head = re.match(r"\$\{" + re.escape(name) + r":?[-=]", value)
    if head is None:
        return None
    return value[head.end() : -1]


def _composed_variables(command: str) -> frozenset:
    """Variables this command builds by APPEND or SELF-REFERENCE.

    `v+=set`, `v="${v}set"`, `v=$v-rounds`. These are the shapes that defeat
    every value-matching screen: no guarded verb — and no launcher path — ever
    appears as a literal. Assignments that merely interpolate OTHER variables
    (`FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`)
    are the standard preamble and are NOT composition.

    Neither is a pure DEFAULT expansion of the name being assigned (fn-159
    review F5): `FLOWCTL="${FLOWCTL:-.flow/bin/flowctl}"` builds nothing — it
    picks a literal fallback — yet the self-reference read as composition and
    blocked `review-rounds record`, a REQUIRED fence step, in the exact
    self-defaulting idiom the preamble ships. Only the default-expansion head
    is exempt: a self reference anywhere else in the value
    (`${v:-$v}`, `${v}x`) is still composition.

    The exemption is narrowed to the shapes that motivate it (fn-159
    verification F2): a self-default whose fallback IS a launcher path — that
    var is registered by `_launcher_variables`, so the full flowctl argv screen
    applies to it — or an empty fallback (`${v:-}`), which carries no content.
    A self-default to any OTHER literal (`V="${V:-reset}"`) stays composition:
    exempting it would leave a guarded verb reachable through a variable that
    no value-matching screen can see.
    """
    launchers = _launcher_variables(command)
    composed = set()
    for name, operator, value in _SHELL_ASSIGN_RE.findall(command):
        if operator == "+=":
            composed.add(name)
            continue
        default = _self_default_value(name, _unquote(value))
        if default is not None and (not default or name in launchers):
            continue
        if name in _expansion_names(_strip_self_default_expansions(name, value)):
            composed.add(name)
    return frozenset(composed)


class _ShellScan:
    """One command's launcher/composition facts plus its execution positions."""

    def __init__(self, command: str) -> None:
        self.launcher_vars = _launcher_variables(command)
        self.composed_vars = _composed_variables(command)
        # Executable-position tokens (after wrapper stripping), at every depth.
        self.exec_tokens: list[str] = []


def _is_flowctl_executable(token: str, launcher_vars: frozenset = frozenset()) -> bool:
    """Recognize direct, path, and variable-backed bundled flowctl launchers."""
    name = _simple_variable_name(token)
    if name is not None and name in (launcher_vars or _LAUNCHER_VAR_NAMES):
        return True
    return token in {"$FLOWCTL", "${FLOWCTL}", "FLOWCTL"} or bool(
        _FLOWCTL_PATH_RE.fullmatch(token)
    )


def _flowctl_argvs(
    command: str, scan: "Optional[_ShellScan]" = None
) -> Optional[list[list[str]]]:
    """Extract flowctl argv vectors from a tokenized shell command.

    Wrappers are unwrapped rather than trusted: a launcher is a launcher no
    matter which prefix (`timeout`, `env`, `nice`, `xargs`) or interpreter
    (`sh -c "…"`, `eval "…"`) carries it.
    """
    tokens = _tokenize_shell_command(command)
    if tokens is None:
        return None
    return _argvs_from_tokens(tokens, 0, scan if scan is not None else _ShellScan(command))


def _strip_array_literals(tokens: list[str]) -> list[str]:
    """Drop `args=( … )` / `args+=( … )` groups — data, never a command.

    ``shlex`` treats the parentheses as command separators, so an array append
    otherwise splits into bogus one-token "commands" whose first element is an
    array ELEMENT (`args+=("$TASK_ID")` → a segment executing `$TASK_ID`).
    Fences build their flags exactly this way, so the composition screen would
    read them as execution through a variable.
    """
    out: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if (
            _ARRAY_ASSIGN_PREFIX_RE.fullmatch(token)
            and index + 1 < len(tokens)
            and tokens[index + 1] == "("
        ):
            depth = 0
            index += 1
            while index < len(tokens):
                if tokens[index] == "(":
                    depth += 1
                elif tokens[index] == ")":
                    depth -= 1
                    if depth == 0:
                        index += 1
                        break
                index += 1
            continue
        out.append(token)
        index += 1
    return out


def _argvs_from_tokens(
    tokens: list[str], depth: int, scan: "_ShellScan"
) -> list[list[str]]:
    """Split tokens on shell operators and classify each command segment."""
    commands: list[list[str]] = []
    tokens = _strip_array_literals(tokens)
    start = 0
    for index, token in enumerate([*tokens, ";"]):
        if token not in _SHELL_COMMAND_SEPARATORS:
            continue
        commands.extend(_segment_argvs(tokens[start:index], depth, scan))
        start = index + 1
    return commands


def _strip_argv_wrappers(segment: list[str]) -> list[str]:
    """Drop leading env assignments and prefix wrappers with their options."""
    while segment:
        if _ENV_ASSIGN_RE.fullmatch(segment[0]):
            segment.pop(0)
            continue
        wrapper = os.path.basename(segment[0])
        if wrapper in _ARGV_WRAPPERS:
            segment.pop(0)
            _strip_wrapper_options(segment, wrapper)
            continue
        break
    return segment


def _strip_wrapper_options(segment: list[str], wrapper: str) -> None:
    """Consume one wrapper's options — value-taking ones with their value."""
    value_options = _WRAPPER_VALUE_OPTIONS.get(wrapper, frozenset())
    while segment:
        token = segment[0]
        if _ENV_ASSIGN_RE.fullmatch(token):
            segment.pop(0)
            continue
        if wrapper in _DURATION_POSITIONAL_WRAPPERS and _DURATION_RE.fullmatch(token):
            segment.pop(0)
            continue
        if not token.startswith("-") or len(token) == 1:
            return
        segment.pop(0)
        if _wrapper_option_takes_value(token, value_options) and segment:
            # The value is the NEXT token, so it is not the executable.
            segment.pop(0)
    return


def _wrapper_option_takes_value(token: str, value_options: frozenset) -> bool:
    """Whether this option spelling expects a separate value token."""
    if "=" in token:
        return False  # `--unset=X` / `-d=,`: value is attached.
    if token in value_options:
        return True
    # Short-option cluster (`env -iu NAME`): only the LAST letter can take a
    # value. `-I{}` / `-n5` carry an attached value, and their trailing char
    # is not a known option, so nothing extra is consumed.
    if not token.startswith("--") and len(token) > 2:
        return f"-{token[-1]}" in value_options
    return False


def _interpreter_command_string(segment: list[str]) -> Optional[str]:
    """Return the command string a `sh`/`bash`/… argv runs, else None.

    PR #290 bot r9: matching the exact token ``-c`` recognized only the
    textbook spelling. Every combined short-option cluster POSIX shells accept
    — `bash -lc '…'`, `-xec`, `-lec` — runs the very same command string, so a
    guarded verb hidden behind one bypassed the recursion entirely. A cluster
    is one dash plus single-letter flags, so any cluster CONTAINING `c` is the
    command-string form and the string is the next token (`--` may sit between
    them). Anything attached after the `c` (`-cecho hi`) IS the string.

    ``None`` means this argv runs no command string: a login shell (`bash -l`),
    a script file (`bash script.sh`), or an unrecognized option shape — all of
    which fall through to the raw-text floor rather than being trusted.
    """
    index = 1
    seen_c = False
    while index < len(segment):
        token = segment[index]
        if token == "--":
            index += 1
            break
        if not token.startswith("-") or token == "-":
            break
        if token.startswith("--"):
            # Long options (`--norc`, `--posix`) never carry the command string.
            index += 1
            continue
        head, found, tail = token[1:].partition("c")
        if not found or set(head) - _SHELL_SHORT_FLAG_LETTERS:
            # No `c`, or the token is not an option cluster at all (a value).
            if not found:
                index += 1
                continue
            return None
        if tail and set(tail) - _SHELL_SHORT_FLAG_LETTERS:
            # Attached command string: `-cflowctl review-rounds …`.
            return tail
        seen_c = True
        index += 1
    if not seen_c or index >= len(segment):
        return None
    return segment[index]


def _segment_argvs(
    segment: list[str], depth: int, scan: "_ShellScan"
) -> list[list[str]]:
    """Return flowctl argvs invoked by one command segment (wrappers unwrapped)."""
    segment = _strip_argv_wrappers(list(segment))
    if not segment:
        return []

    base = os.path.basename(segment[0])
    if depth < _MAX_WRAPPER_DEPTH:
        # `sh -c "flowctl …"` / `eval "flowctl …"` — recurse into the script text.
        if base in _SHELL_INTERPRETERS:
            nested = _interpreter_command_string(segment)
            if nested is not None:
                return _nested_argvs(nested, depth + 1, scan)
        if base == "eval" and len(segment) > 1:
            return _nested_argvs(" ".join(segment[1:]), depth + 1, scan)

    # `python3 .flow/bin/flowctl.py …` is the same launcher one hop out.
    if (
        len(segment) > 1
        and re.fullmatch(r"(?:.*/)?python(?:3)?(?:\.\d+)?", segment[0])
        and _is_flowctl_executable(segment[1], scan.launcher_vars)
    ):
        segment.pop(0)
    scan.exec_tokens.append(segment[0])
    if _is_flowctl_executable(segment[0], scan.launcher_vars):
        return [segment[1:]]
    return []


def _nested_argvs(text: str, depth: int, scan: "_ShellScan") -> list[list[str]]:
    """Classify shell text carried as a string argument of a wrapper."""
    tokens = _tokenize_shell_command(text)
    if tokens is None:
        # Unparseable nested text is still screened by the raw-text floor in
        # `_blocks_review_counter_recovery`, which sees the whole command.
        return []
    return _argvs_from_tokens(tokens, depth, scan)


def _command_has_recovery_markers(command: str) -> bool:
    """Raw-text screen run on EVERY command as a wrapper-proof floor.

    Valid bash can defeat ``shlex`` (a heredoc body with an odd apostrophe
    count, say) and novel wrappers can defeat argv classification; blocking
    every such command would break ordinary Ralph prose-bearing writes.
    Instead the forbidden verbs stay fail-closed on a marker co-occurrence
    screen while everything else passes.

    Line continuations are collapsed first (fn-159 review F2) — bash removes
    `\\<newline>` before it ever parses, so every adjacency screen below must
    read the command the shell will actually run.
    """
    command = _collapse_line_continuations(command)
    if re.search(r"reset-review-rounds", command):
        return True
    # fn-168 R7: extending the cap is the same self-grant as resetting it. Three
    # routes, all screened here as the raw-text floor (each also has an argv
    # screen below where argv is parseable):
    #   1. `flowctl config set review.maxIterations 99`
    #   1b. the parent-key form `flowctl config set review '{"maxIterations":99}'`
    #       — `_set_config_locked` JSON-coerces a `{`-leading value and replaces
    #       whole subtrees, so a leaf-key-only screen would be no screen at all.
    #   2. `MAX_REVIEW_ITERATIONS=99 <anything>` — the HIGHER-precedence rung,
    #       and a hole that predates the config key.
    # Matching the key NAME (not the whole invocation) keeps this scoped to the
    # cap: `config set review.backend codex`, tracker resolve transactions, and
    # setup's config writes all still pass.
    if re.search(r"MAX_REVIEW_ITERATIONS['\"]?\s*=", command):
        return True
    if re.search(r"config['\"]?\s+['\"]?set\b", command):
        if re.search(r"maxIterations", command):
            return True
        # Composition floor, mirroring `_RECOVERY_ASSIGN_RE`: the key or value can
        # be built in assignments (`k=maxIter; k+=ations`) so no single token ever
        # reads `maxIterations`. Only fires when the command also drives a
        # launcher AND targets the `review` namespace, so ordinary variable-valued
        # writes in other namespaces stay legal.
        if (
            _FLOWCTL_TEXT_RE.search(command)
            and re.search(r"set['\"]?\s+['\"]?review\b", command)
            and re.search(r"[A-Za-z_][A-Za-z0-9_]*\+?=", command)
        ):
            return True
    # Quotes are stripped on BOTH sides of the gap (PR #290 bot r3): a
    # per-token-quoted `"review-rounds" "reset"` closes its quote before the
    # whitespace, which the old one-sided screen never matched.
    if re.search(r"review-rounds['\"]?\s+['\"]?reset\b", command):
        return True
    # (?![\w-]) so `--force-with-lease` — a different, legitimate flag — never
    # trips the screen.
    if re.search(r"--force(?![\w-])", command) and re.search(
        r"review-rounds['\"]?\s+['\"]?increment\b"
        r"|impl-review|plan-review|completion-review",
        command,
    ):
        return True
    # PR #290 bot r4: variable-expansion smuggle. In
    # `verb=review-rounds; sub=reset; "$FLOWCTL" "$verb" "$sub" fn-1 --kind plan`
    # no guarded verb is ever adjacent to the launcher — the verbs sit in
    # assignment VALUES and only meet it at expansion time, which neither the
    # argv pass nor the adjacency screens above can model. So when a command
    # BOTH references a flowctl launcher AND assigns a guarded verb, fail
    # closed. Direct `review-rounds record` carries no such assignment and
    # stays allowed; prose that names the verbs without naming a launcher also
    # stays allowed. The remaining false positives (a legitimate command whose
    # variable happens to hold `reset`) match the floor's documented posture:
    # rewrite it with the file tool.
    if _FLOWCTL_TEXT_RE.search(command):
        if _RECOVERY_ASSIGN_RE.search(command):
            return True
        if re.search(r"--force(?![\w-])", command) and _FORCE_ASSIGN_RE.search(
            command
        ):
            return True
        # PR #290 bot r6: composed-flag smuggle (`flag=--for; flag+=ce`). No
        # `--force` text ever appears, so the screen above cannot see it.
        if _GUARDED_DISPATCH_TEXT_RE.search(command) and _DASH_VALUE_ASSIGN_RE.search(
            command
        ):
            return True
    return False


def _json_mentions_review_cap(value: str) -> bool:
    """True when a `config set` VALUE carries a `maxIterations` member.

    Decoded rather than substring-matched, so an escaped key
    (`{"\\u006daxIterations": 99}`) cannot slip past: `json.loads` resolves the
    escape and the member name is compared literally. A value that is not valid
    JSON falls back to the raw text — an unparseable blob naming the key is
    still suspicious, and `config set` itself keeps a malformed `{`-leading
    value as a literal string, so nothing is lost by being strict here.
    """
    try:
        decoded = json.loads(value)
    except (ValueError, TypeError):
        return "maxIterations" in value

    def walk(node: object) -> bool:
        if isinstance(node, dict):
            return any(
                key == "maxIterations" or walk(child) for key, child in node.items()
            )
        if isinstance(node, list):
            return any(walk(child) for child in node)
        return False

    return walk(decoded)


def _config_set_touches_review_cap(argv: list[str]) -> bool:
    """Does this `flowctl config set` argv write the review-round cap?

    Three shapes reach the same on-disk value, so all three are screened:
      * the leaf key `review.maxIterations`;
      * the parent key `review` with a JSON value carrying a `maxIterations`
        member — `_set_config_locked` json.loads-coerces a `{`-leading value and
        its nested walk REPLACES whole subtrees, so a leaf-only screen would be
        no screen at all;
      * either of the above assembled at expansion time. Under the `review`
        namespace an unexpanded key or value is unknowable pre-expansion, so it
        fails closed — the same literal-only contract the guarded subcommand
        slots already use. Other namespaces keep their variable values legal
        (`config set tracker.perTracker.teamId "$TEAM_ID"` must still run).
    """
    rest = argv[2:]
    if not rest:
        return False
    key = rest[0]
    values = rest[1:]
    if _ARGV_EXPANSION_RE.search(key):
        # An unknowable key could expand to review.maxIterations.
        return True
    if key == "review.maxIterations":
        return True
    if key == "review" or key.startswith("review."):
        if any(_ARGV_EXPANSION_RE.search(value) for value in values):
            return True
        return any(_json_mentions_review_cap(value) for value in values)
    return any("maxIterations" in value for value in values)


def _guarded_dispatch_index(argv: list[str]) -> "int | None":
    """Index of the guarded dispatch subcommand in a flowctl argv, else None."""
    if len(argv) > 1 and argv[0] in _REVIEW_BACKENDS and argv[1] in _REVIEW_DISPATCHES:
        return 1
    if argv[:2] == ["review-rounds", "increment"]:
        return 1
    return None


def _guarded_dispatch_smuggles_argument(argv: list[str], dispatch: int) -> bool:
    """Whether a guarded dispatch carries an expansion in argument position.

    Fail-closed but fence-compatible (PR #290 bot r6). A token carrying an
    unexpanded expansion is allowed ONLY:

      (a) as the value immediately after a literal value-taking flag
          (`--task "$TASK_ID"`, `--receipt "$RECEIPT_PATH"`, also the
          `--receipt=$P` spelling); or
      (b) as the FIRST token after the dispatch subcommand — the spec/task id
          every fence passes there (`"$SPEC_ID"`, `"${TASK_ID%.*}"`,
          `"${args[@]}"`).

    Everything else — a bare `"$flag"` later in the line, or a value trailing a
    flag that takes none — is a composed flag as far as this guard can know.
    """
    rest = argv[dispatch + 1:]
    for index, token in enumerate(rest):
        if not _ARGV_EXPANSION_RE.search(token):
            continue
        if index == 0:
            continue  # (b) the id positional
        if rest[index - 1] in _GUARDED_DISPATCH_VALUE_FLAGS:
            continue  # (a) the value of a literal value-taking flag
        if token.startswith("-") and "=" in token:
            name = token.split("=", 1)[0]
            if name in _GUARDED_DISPATCH_VALUE_FLAGS:
                continue  # (a), `--flag=$VALUE` spelling
        return True
    return False


def _composed_indirect_execution(
    scan: "_ShellScan", flowctl_argvs: list[list[str]]
) -> bool:
    """Composition screen: composed variables + execution through a variable.

    PR #290 bot r9 (b), and the END of the per-idiom regex arms race. A command
    that BUILDS a variable by append or self-reference (`v+=…`, `v="${v}…"`)
    and then EXECUTES that variable fails closed on structure, regardless of
    content: composition leaves no launcher path and no verb anywhere in the
    text for any value-matching screen to find, so `p=.flow/bin/flow; p+=ctl;
    "$p" review-rounds "$v" fn-1` was invisible to every other rule here. No
    fence has that shape — fences spell the launcher literally (or bind it in
    one hop, see `_launcher_variables`) and compose only ARGUMENT arrays
    (`args+=(--base …)`, expanded as `"${args[@]}"` in argument position).

    Deliberately narrow to COMPOSED names. "Any expansion in command position"
    was tried and is wrong: this segmenter reads `case` patterns and `[[ … ]]`
    tests as commands, so it fired on six shipped fences. Composition in a
    SUBCOMMAND position needs nothing here — the literal-subcommand rule
    already blocks an expansion in either token after a launcher.

    ``flowctl_argvs`` is accepted so this stays the one place a future
    structural screen over classified argvs would live.
    """
    if not scan.composed_vars:
        return False
    return any(
        _simple_variable_name(token) in scan.composed_vars
        for token in scan.exec_tokens
    )


def _blocks_review_counter_recovery(command: str) -> bool:
    """Return whether the command invokes a human-only review escape hatch.

    Two independent screens, unioned. The argv pass classifies precisely
    (wrappers unwrapped, `review-rounds record` stays allowed); the raw-text
    marker screen runs unconditionally as a floor, so a novel wrapper the argv
    pass cannot model still fails closed. The floor's prose false positives
    match the guard's existing posture for the codex/`--last` screens: an
    unparseable or verb-mentioning command is rewritten via the file tool.
    """
    if _command_has_recovery_markers(command):
        return True

    scan = _ShellScan(command)
    flowctl_argvs = _flowctl_argvs(command, scan)
    if flowctl_argvs is not None and _composed_indirect_execution(scan, flowctl_argvs):
        return True
    if flowctl_argvs is None:
        # Unparseable shell text cannot be classified as argv; the marker
        # screen above already had its say.
        return False

    for argv in flowctl_argvs:
        # Structural rule, ending the regex arms race (PR #290 bot r5): in a
        # guarded session a flowctl SUBCOMMAND must be a literal. Composition
        # (`verb=review; verb="${verb}-rounds"`) leaves no verb text anywhere
        # for a value-matching screen to find, so the position — not the value
        # — decides: an unexpanded variable or command substitution in a
        # subcommand slot is blocked regardless of what it might expand to.
        # Every shipped fence spells its subcommands literally; variable
        # ARGUMENTS (ids, paths, `--reservation-id "$(jq …)"`) stay legal.
        if argv and _ARGV_EXPANSION_RE.search(argv[0]):
            return True
        if len(argv) > 1 and _ARGV_EXPANSION_RE.search(argv[1]):
            if argv[0] in _GUARDED_SUBCOMMAND_GROUPS:
                return True
            if argv[0] in _REVIEW_BACKENDS and "--force" in argv:
                return True
        # Argument-position expansions on a guarded dispatch (composed flags).
        dispatch = _guarded_dispatch_index(argv)
        if dispatch is not None and _guarded_dispatch_smuggles_argument(argv, dispatch):
            return True
        if argv[:2] == ["spec", "reset-review-rounds"]:
            return True
        if argv[:2] == ["review-rounds", "reset"]:
            return True
        # fn-168 R7: the cap write. Token comparison, never a substring —
        # `config set review.backend codex` must pass.
        if argv[:2] == ["config", "set"] and _config_set_touches_review_cap(argv):
            return True
        if "--force" not in argv:
            continue
        if argv[:2] == ["review-rounds", "increment"]:
            return True
        if argv and argv[0] in _REVIEW_BACKENDS and any(
            token in _REVIEW_DISPATCHES for token in argv[1:]
        ):
            return True
    return False


def handle_pre_tool_use(data: dict) -> None:
    """Handle PreToolUse event - validate commands before execution."""
    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")
    session_id = data.get("session_id", "unknown")

    # fn-159 R9: SHIP resets inside ``review-rounds record``; these explicit
    # resets and forced review dispatches are human-only recovery tools. Match
    # argv tokens, not raw substrings, so quoting/spacing cannot evade the gate.
    if _blocks_review_counter_recovery(command):
        output_block(
            "BLOCKED: review-counter reset, raising the review-round cap "
            "(review.maxIterations / MAX_REVIEW_ITERATIONS), and --force review "
            "dispatch/increment are "
            "human-only recovery tools. Ralph must surface the terminal instead. "
            "A shell command that merely mentions those verbs (prose, heredoc) trips "
            "the same screen - write the text with the file tool instead. "
            "flowctl SUBCOMMANDS must also be spelled literally: a variable or "
            "command substitution in either of the two tokens after the launcher "
            "is blocked (variable ARGUMENTS - ids, paths, --reservation-id - are fine). "
            "On a review dispatch (codex/copilot/cursor *-review, review-rounds "
            "increment) a variable ARGUMENT is only allowed as the id right after "
            "the subcommand or as the value of a literal value-taking flag - "
            "spell every other flag out literally."
        )

    # Check for chat-send commands
    if "chat-send" in command:
        # Block --json flag
        if re.search(r"chat-send.*--json", command):
            output_block(
                "BLOCKED: Do not use --json with chat-send. "
                "It suppresses the review text. Remove --json flag."
            )

        # Check for --new-chat on re-reviews
        if "--new-chat" in command:
            state = load_state(session_id)
            if state["chats_sent"] > 0:
                output_block(
                    "BLOCKED: Do not use --new-chat for re-reviews. "
                    "Stay in the same chat so reviewer has context. "
                    "Remove --new-chat flag."
                )

    # Block direct codex calls (must use flowctl codex wrappers)
    if re.search(r"\bcodex\b", command):
        # Allow flowctl codex wrappers
        is_wrapper = re.search(r"flowctl\s+codex|FLOWCTL.*codex", command)
        # Allow the FULL canonical Codex implementation-delegation shape (fn-55).
        # NOT the mere presence of FLOW_DELEGATE_CODEX=1 — a sentinel-prefixed but
        # otherwise-arbitrary command (missing --ignore-user-config, carrying
        # --last, using resume/review, or an -o outside .flow/tmp/codex-*) STILL
        # falls through to the block path. The canonical shape itself rejects
        # --last, so an early return here cannot leak a --last invocation.
        is_delegation = is_canonical_codex_delegation(command)
        if is_delegation:
            # Canonical delegation passes the codex section untouched.
            pass
        elif not is_wrapper:
            # Block direct codex usage
            if re.search(r"\bcodex\s+exec\b", command):
                output_block(
                    "BLOCKED: Do not call 'codex exec' directly. "
                    "Use 'flowctl codex impl-review' or 'flowctl codex plan-review' "
                    "to ensure proper receipt handling and session continuity. "
                    "(Implementation-delegation must match the full canonical shape: "
                    "FLOW_DELEGATE_CODEX=1 codex exec --ignore-user-config "
                    "--output-schema ... -o .flow/tmp/codex-<task>/... with a sandbox "
                    "flag and no --last.)"
                )
            if re.search(r"\bcodex\s+review\b", command):
                output_block(
                    "BLOCKED: Do not call 'codex review' directly. "
                    "Use 'flowctl codex impl-review' or 'flowctl codex plan-review'."
                )
        # Block --last even through wrappers (breaks session continuity).
        # Unreachable for the canonical-delegation early-pass (it rejects --last),
        # so this still guards every wrapper / direct invocation that carries it.
        if not is_delegation and re.search(r"--last\b", command):
            output_block(
                "BLOCKED: Do not use '--last' with codex. "
                "Session continuity is managed via session_id in receipts."
            )

    # Block direct copilot calls (must use flowctl copilot wrappers)
    if re.search(r"\bcopilot\b", command):
        # Allow flowctl copilot wrappers
        is_wrapper = re.search(r"flowctl\s+copilot|FLOWCTL.*copilot", command)
        if not is_wrapper:
            # Block any direct copilot invocation
            output_block(
                "BLOCKED: Do not call 'copilot' directly. "
                "Use 'flowctl copilot impl-review', 'flowctl copilot plan-review', "
                "or 'flowctl copilot completion-review' to ensure proper receipt "
                "handling and session continuity (via client-generated UUID)."
            )
        # Block --continue even through wrappers (resumes most recent session,
        # conflicts with parallel reviews and multi-project usage)
        if re.search(r"--continue\b", command):
            output_block(
                "BLOCKED: Do not use '--continue' with copilot. "
                "It resumes the most recent session and conflicts with parallel "
                "reviews. Session continuity is managed via session_id (UUID) "
                "stored in receipts and replayed with --resume=<uuid>."
            )

    # Validate setup-review usage
    if "setup-review" in command:
        if not re.search(r"--repo-root", command):
            output_block(
                "BLOCKED: setup-review requires --repo-root flag. "
                'Use: setup-review --repo-root "$REPO_ROOT" --summary "..."'
            )
        if not re.search(r"--summary", command):
            output_block(
                "BLOCKED: setup-review requires --summary flag. "
                'Use: setup-review --repo-root "$REPO_ROOT" --summary "..."'
            )

    # Validate select-add has --window and --tab
    if "select-add" in command:
        if not re.search(r"--window", command):
            output_block(
                "BLOCKED: select-add requires --window flag. "
                'Use: select-add --window "$W" --tab "$T" <path>'
            )

    # Enforce flowctl done requires --evidence-json and --summary-file
    if " done " in command and ("flowctl" in command or "FLOWCTL" in command):
        # Skip if it's just "flowctl done --help" or similar
        if not re.search(r"--help|-h", command):
            if not re.search(r"--evidence-json|--evidence", command):
                output_block(
                    "BLOCKED: flowctl done requires --evidence-json flag. "
                    "You must capture commit SHAs and test commands. "
                    "Use: flowctl done <task> --summary-file <s.md> --evidence-json <e.json>"
                )
            if not re.search(r"--summary-file|--summary", command):
                output_block(
                    "BLOCKED: flowctl done requires --summary-file flag. "
                    "You must write a done summary. "
                    "Use: flowctl done <task> --summary-file <s.md> --evidence-json <e.json>"
                )

    # Block receipt writes unless chat-send has succeeded + validate format
    receipt_path = os.environ.get("REVIEW_RECEIPT_PATH", "")
    if receipt_path:
        is_receipt_write = is_receipt_write_command(command, receipt_path)
        if is_receipt_write:
            state = load_state(session_id)
            if not review_succeeded(state):
                output_block(
                    "BLOCKED: Cannot write receipt before review completes. "
                    "You must run 'flowctl rp chat-send', 'flowctl codex impl-review/plan-review', "
                    "or 'flowctl copilot impl-review/plan-review' and receive a review "
                    "response before writing the receipt."
                )
            # Validate receipt has required fields. Stop/ralph.sh validate the actual file.
            if not command_has_json_field(command, "type"):
                output_block(
                    "BLOCKED: Receipt JSON is missing required 'type' field. "
                    'Receipt must include: {"type":"...","id":"...","verdict":"...",...} '
                    "Copy the exact command from the prompt template."
                )
            if not command_has_json_field(command, "id"):
                output_block(
                    "BLOCKED: Receipt JSON is missing required 'id' field. "
                    'Receipt must include: {"type":"...","id":"<TASK_OR_EPIC_ID>",...} '
                    "Copy the exact command from the prompt template."
                )
            if not command_has_json_field(command, "verdict"):
                output_block(
                    "BLOCKED: Receipt JSON is missing required 'verdict' field. "
                    'Review receipts must include: {"verdict":"SHIP",...} '
                    "Copy the exact command from the prompt template."
                )
            # For impl receipts, verify flowctl done was called
            receipt_type, item_id = parse_receipt_path(receipt_path)
            if receipt_type == "impl_review" or "impl_review" in command:
                # Extract task id from receipt
                id_match = re.search(r'"id"\s*:\s*"([^"]+)"', command)
                task_id = id_match.group(1) if id_match else item_id
                done_set = state.get("flowctl_done_called", set())
                if isinstance(done_set, list):
                    done_set = set(done_set)
                if task_id not in done_set:
                    output_block(
                        f"BLOCKED: Cannot write impl receipt for {task_id} - flowctl done was not called. "
                        f"You MUST run 'flowctl done {task_id} --evidence ...' BEFORE writing the receipt. "
                        "The task is NOT complete until flowctl done succeeds."
                    )

    # All checks passed
    sys.exit(0)


def parse_receipt_path(receipt_path: str) -> tuple:
    """Parse receipt path to derive type and id.

    Returns (receipt_type, item_id) based on filename pattern:
    - plan-fn-N.json or plan-fn-N-xxx.json or plan-fn-N-slug.json
      -> ("plan_review", "fn-N" or "fn-N-xxx" or "fn-N-slug")
    - impl-fn-N.M.json or impl-fn-N-xxx.M.json or impl-fn-N-slug.M.json
      -> ("impl_review", "fn-N.M" or "fn-N-xxx.M" or "fn-N-slug.M")
    - completion-fn-N.json or completion-fn-N-xxx.json or completion-fn-N-slug.json
      -> ("completion_review", "fn-N" or "fn-N-xxx" or "fn-N-slug")

    Suffix pattern supports:
    - Legacy: fn-N (no suffix)
    - Short: fn-N-xxx (1-3 char random)
    - Slug: fn-N-longer-slug (multi-segment slugified title)
    """
    basename = os.path.basename(receipt_path)
    # Suffix pattern: optional hyphen + alphanumeric slug (1-3 char or multi-segment)
    # Pattern: (?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?
    suffix_pattern = r"(?:-[a-z0-9][a-z0-9-]*[a-z0-9]|-[a-z0-9]{1,3})?"

    # Try plan pattern first: plan-fn-N.json, plan-fn-N-xxx.json, plan-fn-N-slug.json
    plan_match = re.match(rf"plan-(fn-\d+{suffix_pattern})\.json$", basename)
    if plan_match:
        return ("plan_review", plan_match.group(1))
    # Try impl pattern: impl-fn-N.M.json, impl-fn-N-xxx.M.json, impl-fn-N-slug.M.json
    impl_match = re.match(rf"impl-(fn-\d+{suffix_pattern}\.\d+)\.json$", basename)
    if impl_match:
        return ("impl_review", impl_match.group(1))
    # Try completion pattern: completion-fn-N.json, completion-fn-N-xxx.json, etc.
    completion_match = re.match(rf"completion-(fn-\d+{suffix_pattern})\.json$", basename)
    if completion_match:
        return ("completion_review", completion_match.group(1))
    # Fallback
    return ("impl_review", "UNKNOWN")


def handle_post_tool_use(data: dict) -> None:
    """Handle PostToolUse event - track state and provide feedback."""
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    command = tool_input.get("command", "")
    session_id = data.get("session_id", "unknown")

    response_text = _tool_response_text(tool_response)
    state = load_state(session_id)

    # Track chat-send calls - must have actual review text, not null
    if "chat-send" in command:
        # Check for successful chat (has "Chat Send" and review text, not null)
        if "Chat Send" in response_text and '{"chat": null}' not in response_text:
            state["chats_sent"] = state.get("chats_sent", 0) + 1
            state["chat_send_succeeded"] = True
            save_state(session_id, state)
        elif '{"chat": null}' in response_text or '{"chat":null}' in response_text:
            # Failed - --json was used incorrectly
            state["chat_send_succeeded"] = False
            save_state(session_id, state)

    # Track codex review calls - check for verdict in output
    if (
        "flowctl" in command
        and "codex" in command
        and ("impl-review" in command or "plan-review" in command or "completion-review" in command)
    ):
        # Codex writes receipt automatically with --receipt flag, but we still track success
        verdict_in_output = re.search(
            r"<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN)</verdict>", response_text
        )
        if verdict_in_output:
            state["codex_review_succeeded"] = True
            state["last_verdict"] = verdict_in_output.group(1)
            save_state(session_id, state)

    # Track copilot review calls - check for verdict in output
    if (
        "flowctl" in command
        and "copilot" in command
        and ("impl-review" in command or "plan-review" in command or "completion-review" in command)
    ):
        # Copilot writes receipt automatically with --receipt flag, but we still track success
        verdict_in_output = re.search(
            r"<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN)</verdict>", response_text
        )
        if verdict_in_output:
            state["copilot_review_succeeded"] = True
            state["last_verdict"] = verdict_in_output.group(1)
            save_state(session_id, state)

    # Track flowctl done calls - match various invocation patterns:
    # - flowctl done <task>
    # - flowctl.py done <task>
    # - .flow/bin/flowctl done <task>
    # - scripts/ralph/flowctl done <task>
    # - $FLOWCTL done <task>
    # - "$FLOWCTL" done <task>
    # Success is structured only (exit code / --json status=done / exact contract line).
    if " done " in command and ("flowctl" in command or "FLOWCTL" in command):
        debug_log(f"  -> flowctl done detected in: {command[:100]}...\n")

        done_match = re.search(r"\bdone\s+([a-zA-Z0-9][a-zA-Z0-9._-]*)", command)
        if done_match:
            task_id = done_match.group(1)
            exit_code = _tool_response_exit_code(tool_response)
            has_json = bool(re.search(r"--json\b", command))
            debug_log(
                f"  -> Extracted task_id: {task_id}, exit_code={exit_code}, "
                f"json={has_json}\n"
            )

            if is_flowctl_done_success(task_id, command, tool_response, response_text):
                done_set = state.get("flowctl_done_called", set())
                if isinstance(done_set, list):
                    done_set = set(done_set)
                done_set.add(task_id)
                state["flowctl_done_called"] = done_set
                save_state(session_id, state)
                debug_log(f"  -> Added {task_id} to flowctl_done_called: {done_set}\n")
            else:
                debug_log(f"  -> flowctl done for {task_id} did not pass structured success\n")

    # Track receipt writes - reset review state after write
    # Must match actual shell redirects (cat > file, echo > file), not commands
    # that merely contain the receipt path as an argument (e.g. --receipt flag)
    receipt_path = os.environ.get("REVIEW_RECEIPT_PATH", "")
    if receipt_path:
        if is_receipt_write_command(command, receipt_path):
            state["chat_send_succeeded"] = False  # Reset for next review
            state["codex_review_succeeded"] = False  # Reset codex state too
            state["copilot_review_succeeded"] = False  # Reset copilot state too
            save_state(session_id, state)

    # Track setup-review output (W= T=)
    if "setup-review" in command:
        w_match = re.search(r"W=(\d+)", response_text)
        t_match = re.search(r"T=([A-F0-9-]+)", response_text, re.I)
        if w_match:
            state["window"] = w_match.group(1)
        if t_match:
            state["tab"] = t_match.group(1)
        save_state(session_id, state)

    # Check for verdict in response
    verdict_match = re.search(
        r"<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK|NEEDS_HUMAN)</verdict>", response_text
    )
    if verdict_match:
        state["last_verdict"] = verdict_match.group(1)
        save_state(session_id, state)

        # If SHIP, remind about receipt (only for rp mode - codex writes receipt automatically)
        if verdict_match.group(1) == "SHIP":
            receipt_path = os.environ.get("REVIEW_RECEIPT_PATH", "")
            # Only remind if receipt doesn't exist and we're in rp mode (not codex)
            if (
                receipt_path
                and not Path(receipt_path).exists()
                and state.get("chat_send_succeeded")
            ):
                # Derive type and id from receipt path
                receipt_type, item_id = parse_receipt_path(receipt_path)
                # Build command with ts variable to avoid shell substitution in JSON
                cmd = (
                    f"mkdir -p \"$(dirname '{receipt_path}')\"\n"
                    'ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"\n'
                    f"cat > '{receipt_path}' <<EOF\n"
                    f'{{"type":"{receipt_type}","id":"{item_id}","mode":"rp","verdict":"SHIP","timestamp":"$ts"}}\n'
                    "EOF"
                )
                # Provide feedback to Claude (rp mode only - codex writes receipt automatically)
                output_json(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": (
                                f"IMPORTANT: SHIP verdict received. You MUST now write the receipt. "
                                f"Run this command:\n{cmd}"
                            ),
                        }
                    }
                )

        # Prompt Claude to capture learnings from NEEDS_WORK/MAJOR_RETHINK
        elif verdict_match.group(1) in ("NEEDS_WORK", "MAJOR_RETHINK"):
            if is_memory_enabled():
                output_json(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": (
                                "MEMORY: Review returned NEEDS_WORK. After fixing, consider if any lessons are "
                                "GENERALIZABLE (apply beyond this task). If so, capture with:\n"
                                '  flowctl memory add --type <type> "<one-line lesson>"\n'
                                "Types: pitfall (gotchas/mistakes), convention (patterns to follow), decision (architectural choices)\n"
                                "Skip: task-specific fixes, typos, style issues, or 'fine as-is' explanations."
                            ),
                        }
                    }
                )

    elif "chat-send" in command and "Chat Send" in response_text:
        # chat-send returned but no verdict tag found
        # Check for informal approvals that should have been verdict tags
        if re.search(
            r"\bLGTM\b|\bLooks good\b|\bApproved\b|\bNo issues\b", response_text, re.I
        ):
            output_json(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": (
                            "WARNING: Reviewer responded with informal approval (LGTM/Looks good) "
                            "but did NOT use the required <verdict>SHIP</verdict> tag. "
                            "This means your review prompt was incorrect. "
                            "You MUST use /flow-next:impl-review skill which has the correct prompt format. "
                            "Do NOT improvise review prompts. Re-invoke the skill and try again."
                        ),
                    }
                }
            )

    # Check for {"chat": null} which indicates --json was used incorrectly
    if '{"chat":' in response_text or '{"chat": ' in response_text:
        if "null" in response_text:
            output_json(
                {
                    "decision": "block",
                    "reason": (
                        'ERROR: chat-send returned {"chat": null} which means --json was used. '
                        "This suppresses the review text. Re-run without --json flag."
                    ),
                }
            )

    sys.exit(0)


def handle_stop(data: dict) -> None:
    """Handle Stop event - verify receipt written before allowing stop."""
    session_id = data.get("session_id", "unknown")
    stop_hook_active = data.get("stop_hook_active", False)

    # Prevent infinite loops
    if stop_hook_active:
        sys.exit(0)

    receipt_path = os.environ.get("REVIEW_RECEIPT_PATH", "")

    if receipt_path:
        validation_error = validate_receipt_file(receipt_path)
        if validation_error:
            # Derive type and id from receipt path
            receipt_type, item_id = parse_receipt_path(receipt_path)
            # Tell worker to invoke the review skill, not write receipt manually
            if receipt_type == "impl_review":
                skill = "/flow-next:impl-review"
                skill_desc = "implementation review"
            elif receipt_type == "completion_review":
                skill = "/flow-next:spec-completion-review"
                skill_desc = "spec completion review"
            else:
                skill = "/flow-next:plan-review"
                skill_desc = "plan review"
            # Block stop - review not completed
            output_json(
                {
                    "decision": "block",
                    "reason": (
                        f"Cannot stop: {skill_desc} not completed ({validation_error}).\n"
                        f"You MUST invoke `{skill} {item_id}` to complete the review.\n"
                        f"The skill writes the receipt on SHIP verdict.\n"
                        f"Do NOT write the receipt manually - that skips the actual review."
                    ),
                }
            )

    # Clean up state file
    state_file = get_state_file(session_id)
    if state_file.exists():
        state_file.unlink()

    sys.exit(0)


def handle_subagent_stop(data: dict) -> None:
    """Handle SubagentStop event - same as Stop for subagents."""
    handle_stop(data)


def handle_post_file_tool_use(data: dict) -> None:
    """PostToolUse for file tools: reset review state after a receipt write."""
    receipt_path = os.environ.get("REVIEW_RECEIPT_PATH", "")
    if not receipt_path:
        return
    tool_input = data.get("tool_input", {})
    file_path = file_tool_path(tool_input)
    if not is_receipt_file_path(file_path, receipt_path):
        return
    session_id = data.get("session_id", "unknown")
    state = load_state(session_id)
    state["chat_send_succeeded"] = False
    state["codex_review_succeeded"] = False
    state["copilot_review_succeeded"] = False
    save_state(session_id, state)


def main():
    debug_log(f"[{os.environ.get('FLOW_RALPH', 'unset')}] Hook called\n")

    # Early exit if not in Ralph mode - no output, no context pollution
    if os.environ.get("FLOW_RALPH") != "1":
        debug_log("  -> Exiting: FLOW_RALPH not set to 1\n")
        sys.exit(0)

    # Read input
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        debug_log("  -> Exiting: JSON decode error\n")
        sys.exit(0)

    event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")

    debug_log(f"  -> Event: {event}, Tool: {tool_name}\n")

    # File tools: protected-path + receipt-path gates (Claude + Droid names)
    if event == "PreToolUse" and tool_name in FILE_TOOLS:
        handle_protected_file_check(data)
        handle_file_tool_receipt_check(data)
        sys.exit(0)

    if event == "PostToolUse" and tool_name in FILE_TOOLS:
        handle_post_file_tool_use(data)
        sys.exit(0)

    # Shell tools only for command Pre/Post (Bash on Claude, Execute on Droid)
    if event in ("PreToolUse", "PostToolUse") and tool_name not in SHELL_TOOLS:
        debug_log(f"  -> Skipping: not a shell tool ({tool_name})\n")
        sys.exit(0)

    # Route to handler
    if event == "PreToolUse":
        handle_pre_tool_use(data)
    elif event == "PostToolUse":
        handle_post_tool_use(data)
    elif event == "Stop":
        handle_stop(data)
    elif event == "SubagentStop":
        handle_subagent_stop(data)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
