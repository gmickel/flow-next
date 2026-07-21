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


VALID_RECEIPT_VERDICTS = {"SHIP", "NEEDS_WORK", "MAJOR_RETHINK"}


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


def handle_pre_tool_use(data: dict) -> None:
    """Handle PreToolUse event - validate commands before execution."""
    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")
    session_id = data.get("session_id", "unknown")

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
            r"<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>", response_text
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
            r"<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>", response_text
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
        r"<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>", response_text
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
