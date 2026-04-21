## Description

Add the Copilot backend primitives that mirror `run_codex_exec` + surrounding helpers in `flowctl.py`. This is the early proof point — if the subprocess + session-UUID + verdict-extraction pattern doesn't work, everything downstream breaks.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

Insert a new `# --- Copilot Backend Helpers ---` block in `flowctl.py` (mirroring the Codex block at line 1451). Add:

- `require_copilot()` — mirror `require_codex` at `flowctl.py:1454-1459`. Uses `shutil.which("copilot")`. Error via `error_exit`.
- `get_copilot_version()` — mirror `get_codex_version` at `flowctl.py:1462-1479`. Regex `\d+\.\d+\.\d+`.
- **Reuse `parse_codex_verdict`** at `flowctl.py:1616-1622` as-is. The function is backend-agnostic despite its name — same `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>` tag works for both backends. Call it directly from copilot code. Do NOT rename (3 existing callers at `:6161, :6377, :6729` — rename risk outweighs the naming purity win). A later cleanup can rename to `parse_verdict` once the copilot path is stable.
- `run_copilot_exec(prompt, session_id, repo_root, model, effort) -> (stdout, session_id, exit_code, stderr)` — mirror the SHAPE of `run_codex_exec` at `flowctl.py:1522-1596`. Key deviations from codex:
  - **Session ID is caller-supplied** (`uuid.uuid4()` at call site). No `--resume` fallback branch — `copilot --resume=<uuid>` is create-or-resume, single code path.
  - **No `parse_copilot_thread_id`** needed — we own the UUID.
  - **Prompt delivery**: pass prompt as argv string via `subprocess.run([copilot, "-p", prompt, ...], shell=False)`. This is safe on POSIX (macOS ARG_MAX ~256KB, Linux ~2MB). On Windows (`CreateProcessW` limit ~32KB), fall back to temp file in `.flow/tmp/copilot-prompt-<uuid>.txt`, pass prompt via argv by reading file back into Python string, then unlink in `finally`. Use `len(prompt) < 30000` as the dispatch threshold (safe margin under 32768). Do NOT use the `sh -c` trampoline from `~/work/flow-swarm/src/lib/backends/copilot.ts` — that's a Bun-specific workaround that doesn't apply to Python subprocess.
  - **No sandbox resolver** — copilot uses `--allow-all-tools --no-ask-user --add-dir <repo>` instead.
- Required flags (baseline): `--output-format text`, `-s`, `--no-ask-user`, `--allow-all-tools`, `--add-dir "$REPO_ROOT"`, `--disable-builtin-mcps`, `--no-custom-instructions`, `--log-level error`, `--no-auto-update`, `--model <model>`, `--effort <effort>`, `--resume=<session_id>`, `-p <prompt>`.
- Timeout: 600s (`subprocess.TimeoutExpired`). On timeout return `("", session_id, 2, "copilot -p timed out (600s)")`.
- Exit codes: 0 success, 1 CLI/auth/model error (stderr first line), 130/143 interrupt. Match codex error handling shape.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1451-1700` — existing codex helpers block (mirror shape)
- `plugins/flow-next/scripts/flowctl.py:1522-1596` — `run_codex_exec` (signature, tuple return, subprocess pattern, timeout handling)
- `plugins/flow-next/scripts/flowctl.py:1616-1622` — `parse_codex_verdict` (reused as-is, not renamed)
- `.flow/specs/fn-27-copilot-review-backend.md` §Invocation Template and §Flag Mapping
- `~/work/flow-swarm/src/lib/backends/copilot.ts` — flow-swarm pattern (for context; do NOT port the `sh -c` wrapper)

**Optional** (reference):
- `plugins/flow-next/scripts/flowctl.py:1406-1448` — `gather_context_hints` (reused unchanged in task 3)

## Acceptance

- [ ] `require_copilot()` and `get_copilot_version()` work; errors clean when `copilot` not on PATH
- [ ] `parse_codex_verdict` is called by copilot code without rename (3 existing codex callers untouched at `:6161, :6377, :6729`)
- [ ] `run_copilot_exec` returns `(stdout, session_id, exit_code, stderr)` matching `run_codex_exec` shape
- [ ] Caller-generated UUID flows through `--resume=<uuid>` and creates a real session (verified by `~/.copilot/session-state/<uuid>/` materializing)
- [ ] Small prompt (<30KB) passed directly via argv; large prompt (>30KB) goes via tempfile with `.flow/tmp/` dir
- [ ] Temp file is cleaned up in `finally` block — survives `KeyboardInterrupt`, `TimeoutExpired`, and non-zero exit
- [ ] Timeout path returns tuple with exit_code=2 and descriptive stderr
- [ ] No sandbox logic added (copilot has no sandbox concept)
- [ ] Manual probe: `run_copilot_exec("say OK. End with <verdict>SHIP</verdict>", str(uuid.uuid4()), repo_root, "claude-haiku-4.5", "low")` returns exit 0 with verdict extractable

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
