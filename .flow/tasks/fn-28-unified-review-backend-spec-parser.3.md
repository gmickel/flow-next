## Description

Thread the resolved `BackendSpec` (backend + model + effort) from spec sources through to the two execution primitives (`run_codex_exec`, `run_copilot_exec`) and the six `cmd_*_review` command functions. This is what makes per-task model pinning actually run.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

**New helper `resolve_review_spec(task_id_or_spec: str) -> BackendSpec`**:
- Precedence (most specific wins):
  1. If arg is a spec string (`codex:gpt-5.4`), parse directly
  2. If arg is a task ID: read task's `review` field → epic's `default_review` → none
  3. If no per-task/per-epic spec: read `FLOW_REVIEW_BACKEND` env → may itself be a spec string
  4. Read `.flow/config.json` `review.backend` (same may be spec string)
  5. Call `.resolve()` on whatever BackendSpec falls out → fills missing fields from `FLOW_<BACKEND>_MODEL` / `FLOW_<BACKEND>_EFFORT` env → then registry defaults
- Return resolved spec. Graceful fallback via task 2's legacy rules if any stored value fails to parse.

**`run_codex_exec` at `flowctl.py:1522-1596`**:
- Current signature: `(prompt, session_id, sandbox, model=None)`
- New: `(prompt, session_id, sandbox, spec: BackendSpec)`
- Drop the `os.environ.get("FLOW_CODEX_MODEL")` fallback at line 1543 — that lives inside `spec.resolve()` now
- Build the `-c model_reasoning_effort=<spec.effort>` flag from the spec instead of hard-coding `"high"` at line 1576
- Receipt continues to get `model` + `effort` populated from `spec.model` + `spec.effort`

**`run_copilot_exec` (from fn-27 task 1)**:
- Same pattern. Drop direct env reads for model/effort. Take `spec: BackendSpec`. Pass `spec.model` to `--model`, `spec.effort` to `--effort`.

**Six `cmd_*_review` functions** (`cmd_codex_impl_review`, `cmd_codex_plan_review`, `cmd_codex_completion_review`, and the three copilot equivalents from fn-27):
- Add `--spec` argument to each (optional; defaults to result of `resolve_review_spec(task_id)`).
- Inside the function: if `args.spec` provided, parse; else resolve from task ID.
- Pass resolved spec into `run_codex_exec` / `run_copilot_exec`.
- Receipt `mode`, `model`, `effort` fields come from the resolved spec (not env directly).

**Skill-side contract**: skills continue to call `flowctl <backend> impl-review <task-id> ...` — the backend is encoded in the command name. Spec parsing inside the command resolves per-task/per-epic model+effort automatically. No skill changes needed at this step; task 4 handles env/Ralph.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:1522-1596` — `run_codex_exec` signature to change
- `plugins/flow-next/scripts/flowctl.py:5998-6222` — `cmd_codex_impl_review` (add --spec)
- `plugins/flow-next/scripts/flowctl.py:6224-6430` — `cmd_codex_plan_review`
- `plugins/flow-next/scripts/flowctl.py:6574-6790` — `cmd_codex_completion_review`
- The three copilot equivalents (from fn-27 task 3)
- `plugins/flow-next/scripts/flowctl.py:2679-2702` — `cmd_review_backend` (task 4 extends this; stay aware)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:4171-4220+` — `cmd_task_show_backend` (for source-tracking semantics)

## Acceptance

- [ ] `run_codex_exec(..., spec=BackendSpec("codex", "gpt-5.2", "medium"))` uses `gpt-5.2` + `model_reasoning_effort="medium"`, not the hardcoded defaults
- [ ] `run_copilot_exec(..., spec=BackendSpec("copilot", "claude-haiku-4.5", "low"))` uses those values
- [ ] Task `fn-3.1` with `review: "codex:gpt-5.2"`: running `flowctl codex impl-review fn-3.1` uses gpt-5.2 (not gpt-5.4 default)
- [ ] Env `FLOW_CODEX_EFFORT=low` fills in effort when spec doesn't set it; does NOT override when spec sets `xhigh`
- [ ] Receipt `model` and `effort` fields reflect the resolved spec, not the env vars directly
- [ ] `--spec` flag on each review command overrides the resolved default
- [ ] No change in behavior for existing setups that use only bare backend (spec resolves to registry defaults)
- [ ] `FLOW_CODEX_MODEL` / `FLOW_COPILOT_MODEL` still work as before (backward compat; env overrides into missing fields)
- [ ] All six review commands pass `--help` smoke; new `--spec` flag documented

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
