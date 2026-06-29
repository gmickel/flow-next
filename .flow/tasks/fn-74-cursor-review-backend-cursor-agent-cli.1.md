---
satisfies: [R1, R2, R3, R4, R11]
---

## Description

Foundation of the `cursor` review backend in flowctl — the registry entry, the helper trio, the `cursor check` subcommand, and the parser/run-exec unit tests. **This is the early proof point:** it validates the `cursor-agent` contract (run_cursor_exec parses `.result`/`.session_id`/`.is_error`, read-only `--mode ask`, resume-only session) and confirms the existing `BackendSpec`/registry already accept the model-yes/effort-no shape with **zero parser changes** (verified during spec smoke-tests).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_cursor_run_exec.py` (new), `plugins/flow-next/tests/test_backend_spec.py`

## Approach

- Add `"cursor"` to `BACKEND_REGISTRY` after the copilot entry — `models` set (`auto`, `gpt-5.5-high`, `gpt-5.4-high`, `gpt-5.3-codex(-high/-xhigh)`, `gpt-5.2`, `composer-2.5`, `claude-opus-4-8-thinking-high`, `claude-opus-4-7-thinking-high`), `efforts: None`, `default_model: "gpt-5.5-high"`. `VALID_BACKENDS` derives.
- Mirror `require_copilot` / `get_copilot_version` / `run_copilot_exec` → `require_cursor` / `get_cursor_version` / `run_cursor_exec`. Invocation: `cursor-agent -p --output-format json --trust --mode ask --model <m> [--resume <sid>]`, run with `cwd=repo_root`, `timeout=600`. `session_id` is an **optional input** (None ⇒ omit `--resume`, capture the returned id; non-None ⇒ `--resume <id>`). Parse `.result`/`.session_id`/`.is_error`; non-zero exit on `is_error`/timeout/CLI failure.
- **Prompt delivery is positional argv** (cursor-agent takes the prompt as a positional arg, NOT stdin). Up to a threshold, pass positionally. **Above the threshold, raise an explicit "prompt too large" error** — do NOT copy copilot's temp-file step (it just reads the file back into argv and bypasses no cap; cursor-agent stdin is unconfirmed). A stdin path is added only if cursor-agent confirms stdin input.
- **Do NOT copy `run_copilot_exec`'s `--effort`/`claude-`-drop logic** — cursor folds effort into the model name and takes no `--effort` flag.
- Add `cursor check [--skip-probe]` subparser + `cmd_cursor_check` returning `{available, version, authed}` (text + `--json`), schema-aligned to copilot's `check`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:3416-3477` — `BACKEND_REGISTRY` + `VALID_BACKENDS`
- `plugins/flow-next/scripts/flowctl.py:3753`,`:3761`,`:3798` — `require_copilot` / `get_copilot_version` / `run_copilot_exec` (the template; note its argv-vs-temp + `--effort` logic is what we deliberately diverge from)
- `plugins/flow-next/scripts/flowctl.py:3480`,`:3617`,`:3658` — `BackendSpec` / `parse_backend_spec_lenient` / `resolve_review_spec` (already handle model-yes/effort-no — add tests, no edits)
- `plugins/flow-next/scripts/flowctl.py:18622`, `:25938-25948` — `cmd_copilot_check` + copilot `check` subparser
- `plugins/flow-next/tests/test_copilot_run_exec.py`, `plugins/flow-next/tests/test_backend_spec.py` — test templates

## Key context

`run_cursor_exec` MUST set `cwd=repo_root` (cursor scopes to the workspace dir; a review from a subdir reads the wrong tree). `--trust` is mandatory headless or the CLI hangs on a trust prompt. (Both verified in spec smoke-tests.)

## Acceptance

- [ ] `BACKEND_REGISTRY` has `cursor` (models set, `efforts: None`, `default_model: gpt-5.5-high`); `VALID_BACKENDS` includes it; `flowctl review-backend` reports `cursor` from `.flow/config.json` + `FLOW_REVIEW_BACKEND` (R1)
- [ ] `BackendSpec.parse("cursor")` / `parse("cursor:gpt-5.5-high")` succeed; `parse("cursor:gpt-5.5-high:high")` raises (effort rejected); `parse("cursor:bogus")` raises listing valid models; `.resolve()` fills `gpt-5.5-high` with effort `None` (R2)
- [ ] `run_cursor_exec` shells `cursor-agent -p --output-format json --trust --mode ask --model <m>` with `cwd=repo_root`, no `--effort`; test asserts the `--mode ask` (read-only) flag is present; first call omits `--resume` and returns the generated `session_id`; returns non-zero on `is_error`/600s timeout (R3)
- [ ] above the argv threshold `run_cursor_exec` raises an explicit "prompt too large" error (asserted by a test) — never a silent read-back-into-argv (R3)
- [ ] `flowctl cursor check [--skip-probe]` reports `{available, version, authed}` in text and `--json` (R4)
- [ ] `test_cursor_run_exec.py` (success / `is_error` / timeout / first-call-omits-resume / resume-passes-id / cwd=repo_root / mode-ask-flag / prompt-too-large) + `test_backend_spec.py` cursor cases pass; full Python suite green (R11)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
