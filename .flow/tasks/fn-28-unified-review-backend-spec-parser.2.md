## Description

Wire validation into store-time commands (`cmd_epic_set_backend`, `cmd_task_set_backend`) and resolution into read-time (`cmd_task_show_backend`). This is where bad specs get rejected early with helpful errors, and where users can verify what spec will actually run.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

**`cmd_epic_set_backend`** at `flowctl.py:4413` <!-- Updated by plan-sync: task 1 added BackendSpec+registry at 1715-1898, shifting later defs -->:
- Before storing each of `--impl`, `--review`, `--sync`, call `BackendSpec.parse(value)` if non-empty. On ValueError, call `error_exit` with the parser's message (which already includes valid-values hints).
- Store the raw string (validated) as-is — we don't normalize. User sees back exactly what they typed.

**`cmd_task_set_backend`** at `flowctl.py:4472`:
- Same pattern.

**`cmd_task_show_backend`** at `flowctl.py:4529`:
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
- Display the resolved form via `str(resolved_spec)` — task 1's `__str__` preserves the empty-model slot (`codex::high` round-trips), which keeps effort-only specs honest. <!-- plan-sync note from fn-28.1 -->


**Graceful legacy fallback**:
- If a stored value fails `BackendSpec.parse(...)` (pre-existing data before this epic), DO NOT crash:
  - At read time (`show-backend`, runtime resolution): warn to stderr: `warning: spec "codex:gpt-5.4-high" failed validation: <reason>. Treating as bare backend "codex".`
  - Fall back to bare `BackendSpec(backend=<first-part-if-valid>)` and continue.
  - At store time, we always validate, so new stores don't need fallback.
  <!-- plan-sync note: task 1's parser raises "Unknown model for codex: 'gpt-5.4-high'. Valid: [...]" for this example (not a separator-count error). Fallback logic must catch ValueError generically, not match on message text. -->


**Constants**: export a `VALID_BACKENDS` list (`list(BACKEND_REGISTRY.keys())`) for use in argparse `choices=` where helpful. <!-- plan-sync note: task 1 did NOT add VALID_BACKENDS — grep `^VALID_BACKENDS` returns nothing. Add it here alongside the set-backend wiring. -->

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:4413-` — `cmd_epic_set_backend` <!-- Updated by plan-sync: fn-28.1 inserted BackendSpec+registry at 1715-1898 -->
- `plugins/flow-next/scripts/flowctl.py:4472-` — `cmd_task_set_backend`
- `plugins/flow-next/scripts/flowctl.py:4529-` — `cmd_task_show_backend` (full function)
- `plugins/flow-next/scripts/flowctl.py:1715` — `BACKEND_REGISTRY` dict (codex models: gpt-5.4, gpt-5.2, gpt-5, gpt-5-mini, gpt-5-codex)
- `plugins/flow-next/scripts/flowctl.py:1765` — `BackendSpec` class with `parse`/`resolve`/`__str__`
- `plugins/flow-next/scripts/flowctl.py` — look inside `cmd_task_show_backend` for the existing `resolve_spec` inner helper (extend to return sources)

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
Wired BackendSpec.parse validation into cmd_epic_set_backend and cmd_task_set_backend, added VALID_BACKENDS constant, and rebuilt cmd_task_show_backend to emit raw + resolved + per-field model/effort sources with graceful legacy fallback (warns to stderr on unparseable stored values, degrades to bare backend). 24 new unittests (80 total) and 8 new smoke tests.
## Evidence
- Commits: 628d6046b42023245d712b35fde5e1732927bf04
- Tests: python3 -m unittest plugins.flow-next.tests.test_backend_spec (80/80 OK), plugins/flow-next/scripts/smoke_test.sh (67/67 OK)
- PRs: