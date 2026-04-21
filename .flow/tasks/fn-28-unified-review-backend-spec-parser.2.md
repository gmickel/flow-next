## Description

Wire validation into store-time commands (`cmd_epic_set_backend`, `cmd_task_set_backend`) and resolution into read-time (`cmd_task_show_backend`). This is where bad specs get rejected early with helpful errors, and where users can verify what spec will actually run.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

**`cmd_epic_set_backend`** at `flowctl.py:4055-4111`:
- Before storing each of `--impl`, `--review`, `--sync`, call `BackendSpec.parse(value)` if non-empty. On ValueError, call `error_exit` with the parser's message (which already includes valid-values hints).
- Store the raw string (validated) as-is — we don't normalize. User sees back exactly what they typed.

**`cmd_task_set_backend`** at `flowctl.py:4114-4168`:
- Same pattern.

**`cmd_task_show_backend`** at `flowctl.py:4171-~4220`:
- After `resolve_spec` computes the source-traced raw spec, also call `BackendSpec.parse(raw).resolve()` to get the full backend/model/effort triple.
- Extend JSON output to show both raw (stored) and resolved (runtime) forms:
  ```json
  {
    "id": "fn-1.2",
    "review": {
      "raw": "codex:gpt-5.4",
      "source": "task",
      "resolved": {"backend": "codex", "model": "gpt-5.4", "effort": "high"},
      "effort_source": "registry_default",
      "model_source": "spec"
    },
    ...
  }
  ```
- Per-field source tracking: `spec` / `task_spec` / `epic_spec` / `env:FLOW_CODEX_EFFORT` / `registry_default`.
- Text output (non-JSON) shows both lines: `review: codex:gpt-5.4 (task) → codex:gpt-5.4:high (effort: registry)`.

**Graceful legacy fallback**:
- If a stored value fails `BackendSpec.parse(...)` (pre-existing data before this epic), DO NOT crash:
  - At read time (`show-backend`, runtime resolution): warn to stderr: `warning: spec "codex:gpt-5.4-high" failed validation: <reason>. Treating as bare backend "codex".`
  - Fall back to bare `BackendSpec(backend=<first-part-if-valid>)` and continue.
  - At store time, we always validate, so new stores don't need fallback.

**Constants**: export a `VALID_BACKENDS` list (`list(BACKEND_REGISTRY.keys())`) for use in argparse `choices=` where helpful.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:4055-4111` — `cmd_epic_set_backend`
- `plugins/flow-next/scripts/flowctl.py:4114-4168` — `cmd_task_set_backend`
- `plugins/flow-next/scripts/flowctl.py:4171-4220+` — `cmd_task_show_backend` (full function)
- `plugins/flow-next/scripts/flowctl.py:4206-4215` — existing `resolve_spec` helper (extend to return sources)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py` grep for `error_exit` — match the error-reporting style

## Acceptance

- [ ] `flowctl epic set-backend fn-5 --review "codex:gpt-99"` errors with parser message listing valid models
- [ ] `flowctl task set-backend fn-5.2 --review "rp:claude-opus"` errors (rp doesn't accept model)
- [ ] `flowctl task set-backend fn-5.2 --review "copilot:claude-opus-4.5:xhigh"` succeeds
- [ ] `flowctl task show-backend fn-5.2 --json` emits `raw`, `resolved`, `model_source`, `effort_source` fields
- [ ] Non-JSON output shows both stored and resolved forms with source annotations
- [ ] Legacy stored value `"codex:gpt-5.4-high"` (no colon between model and effort) falls back to bare `codex` with stderr warning, no crash
- [ ] `flowctl task show-backend` on a task with no backend set reports the epic default or a sentinel (behavior matches current implementation)
- [ ] No regression: tasks / epics with bare backend values (`codex`, `rp`) still work end-to-end

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
