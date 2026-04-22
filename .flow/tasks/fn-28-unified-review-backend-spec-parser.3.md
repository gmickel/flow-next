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
- Return resolved spec. For stored values (per-task/per-epic/config — anything that may be legacy), use `parse_backend_spec_lenient(raw, warn=True)` from task 2 (`flowctl.py:1906`) rather than `BackendSpec.parse` directly. That helper returns `Optional[BackendSpec]` (None when unparseable), warns to stderr on degrade, and handles the bare-backend fallback uniformly. <!-- Updated by plan-sync: fn-28.2 added parse_backend_spec_lenient; reuse it instead of rewriting fallback -->
- For a value typed right now (e.g. `--spec` argv), use strict `BackendSpec.parse` — the user should see a parse error immediately.

**`run_codex_exec` at `flowctl.py:1535`** <!-- Updated by plan-sync: verified post-fn-28.2; lines unchanged -->:
- Current signature (verified): `(prompt: str, session_id: Optional[str] = None, sandbox: str = "read-only", model: Optional[str] = None)`
- New: `(prompt, session_id, sandbox, spec: BackendSpec)`
- Drop the `os.environ.get("FLOW_CODEX_MODEL")` fallback at line **1556** — that lives inside `spec.resolve()` now
- Build the `-c model_reasoning_effort=<spec.effort>` flag from the spec instead of hard-coding `"high"` at line **1589**
- Receipt continues to get `model` + `effort` populated from `spec.model` + `spec.effort`. Prefer writing `str(resolved_spec)` as the canonical spec string alongside model/effort so receipts round-trip with `show-backend` output. <!-- plan-sync note: fn-28.2 uses str(resolved) as the canonical form in show-backend's resolved.str field -->

**`run_copilot_exec` (from fn-27 task 1) at `flowctl.py:1985`** <!-- Updated by plan-sync: was 1939 pre-fn-28.2, shifted by +46 after parse_backend_spec_lenient + VALID_BACKENDS insertion -->:
- Same pattern. Drop direct env reads for model/effort (currently at **flowctl.py:2017-2022**). Take `spec: BackendSpec`. Pass `spec.model` to `--model`, `spec.effort` to `--effort`.
- **Preserve existing claude-* effort skip** at **flowctl.py:2061** (`if not effective_model.startswith("claude-"):`). Keep that branch — the registry accepts `{low,medium,high,xhigh}` for all copilot models, but the runtime must still strip effort for Claude models. <!-- plan-sync note: verified post-fn-28.2 at line 2061 -->


**Six `cmd_*_review` functions** (`cmd_codex_impl_review`, `cmd_codex_plan_review`, `cmd_codex_completion_review`, and the three copilot equivalents from fn-27):
- Add `--spec` argument to each (optional; defaults to result of `resolve_review_spec(task_id)`).
- Inside the function: if `args.spec` provided, parse; else resolve from task ID.
- Pass resolved spec into `run_codex_exec` / `run_copilot_exec`.
- Receipt `mode`, `model`, `effort` fields come from the resolved spec (not env directly).

**Skill-side contract**: skills continue to call `flowctl <backend> impl-review <task-id> ...` — the backend is encoded in the command name. Spec parsing inside the command resolves per-task/per-epic model+effort automatically. No skill changes needed at this step; task 4 handles env/Ralph.

## Investigation targets

**Required:** <!-- Updated by plan-sync: line numbers shifted after fn-28.2; cmd_*_review line nums approximate — grep `def cmd_codex_impl_review` etc. to confirm -->
- `plugins/flow-next/scripts/flowctl.py:1535` — `run_codex_exec` signature to change
- `plugins/flow-next/scripts/flowctl.py:1985` — `run_copilot_exec` (was 1939 pre-fn-28.2)
- `plugins/flow-next/scripts/flowctl.py:1906` — `parse_backend_spec_lenient` — reuse for stored-value resolution (added by fn-28.2)
- `plugins/flow-next/scripts/flowctl.py:1766` — `VALID_BACKENDS` — use in any argparse `choices=` that needs bare-backend validation (added by fn-28.2)
- `plugins/flow-next/scripts/flowctl.py` — grep `^def cmd_codex_impl_review` / `^def cmd_codex_plan_review` / `^def cmd_codex_completion_review` / `^def cmd_copilot_impl_review` / `^def cmd_copilot_plan_review` / `^def cmd_copilot_completion_review` (line numbers drifted by ~+60 from fn-28.2 insertions; grep is more reliable than line refs here)
- `plugins/flow-next/scripts/flowctl.py:3083` — `cmd_review_backend` (was 3037 pre-fn-28.2; task 4 extends)
- `plugins/flow-next/scripts/flowctl.py:1715` — `BACKEND_REGISTRY` (codex backend: gpt-5.4, gpt-5.2, gpt-5, gpt-5-mini, gpt-5-codex — no `gpt-5.2-codex`; copilot backend does include `gpt-5.2-codex`)
- `plugins/flow-next/scripts/flowctl.py:1769` — `BackendSpec` class (was 1765)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:4606` — `cmd_task_show_backend` (was 4529 pre-fn-28.2; reference for source-tracking semantics: sources are `task` / `epic` / `None` + per-field `spec` / `env:FLOW_<BACKEND>_<FIELD>` / `registry_default`) <!-- Updated by plan-sync -->

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
