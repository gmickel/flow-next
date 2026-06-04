---
satisfies: [R6, R8, R9]
---

## Description
Make delegation Ralph-safe and close the proof-of-work loop: the host-owned circuit-breaker counter (fed by a structured worker signal), the `ralph-guard.py` inline-sentinel amendment, receipts folded into `flowctl done --evidence-json`, mixed-model attribution, and the `REVIEW_MODE=none` verification backstop. This is the task that makes R9 actually possible (the guard currently blocks every delegation batch in Ralph mode) and closes the trust gap when review is off.

**Size:** M
**Files:** `plugins/flow-next/scripts/hooks/ralph-guard.py`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `plugins/flow-next/agents/worker.md` (evidence-json fold + review-none verification), `plugins/flow-next/skills/flow-next-work/phases.md` (host breaker counter), `plugins/flow-next/tests/` (guard-amendment regression test)

## Approach
- **ralph-guard amendment** (`ralph-guard.py:250-266`): the PreToolUse Bash matcher currently allows only `flowctl codex|FLOWCTL.*codex` and blocks bare `codex exec`. Allow the delegation invocation ONLY when the command matches the **full canonical delegation shape** — NOT merely the sentinel's presence (else any Ralph Bash call bypasses the guard by prepending `FLOW_DELEGATE_CODEX=1`). Require ALL of: inline `FLOW_DELEGATE_CODEX=1` prefix; `codex exec` (reject `resume`/`review`); `--ignore-user-config` (load-bearing — without it MCP servers can re-enable and silently drop `--output-schema`); `--output-schema` present; `-o` target under `.flow/tmp/codex-*`; prompt/schema paths under the same scratch dir; a sandbox flag from the allowlist (`--dangerously-bypass-approvals-and-sandbox` | `-s workspace-write`); and NO `--last`. Keep the copilot block (immediately below) intact. **Bump `RALPH_GUARD_VERSION`** (currently `0.14.0`) and update its tests.
- **Host-owned circuit breaker:** workers are fresh-context per task → an in-worker counter resets every task. The worker returns terminal `DELEGATION_RESULT=<class>` + `DELEGATION_ACTION=<action>` lines (the `action` from `classify-result`) and **inlines** the result into `evidence.delegation={result:{status,files_modified,issues,summary,verification_summary},model,effort,class}` (NOT a `result_file` pointer — the scratch dir is cleaned post-commit, so a path would dangle). The host loop (`phases.md`) bridges them: `DELEGATION_ACTION=rollback_and_disable` (a `cli_failure`) → disable IMMEDIATELY for all remaining tasks; `task_failure`/`partial` → `consecutive_failures++` (disable at 3); `success` → reset to 0. The host owns the counter (workers can't).
- **`REVIEW_MODE=none` verification backstop:** when delegation is active and `REVIEW_MODE=none` (worker Phase 4 skipped), the worker MUST run its own **Phase 5** verification on the delegated diff before `flowctl done` (its existing verify-before-done gate; fix + follow-up commit on failure) — `verification_summary` is not trusted as the sole gate. (When `REVIEW_MODE != none`, the impl-review SHIP gate is the independent check and no duplicate test run is needed.)
- **Receipts:** no generic `flowctl receipt` command exists — inline each delegated batch's result fields into the task's `flowctl done --evidence-json` (worker Phase 5, `worker.md:232-269`) as `evidence.delegation.result` (no scratch-file pointer). That IS the proof-of-work surface.
- **Ralph behavior:** proceed only if `work.delegateConsent` already `true`; any failure → standard mode, never blocks the loop; the per-batch result block routes to the Ralph log/receipt (no human).
- **Mixed-model attribution (concrete):** on a delegated commit the worker (Phase 3) appends commit-message trailers `AI-Orchestrator: Claude` + `AI-Implementer: codex <model> (<effort>)` (e.g. `codex gpt-5.5 (medium)`). `/flow-next:make-pr`'s model line reflects both when it later runs. Define the exact trailer strings + the write site (worker commit).
- Drop-receipt-between-cycles guard for confabulation accumulation if a delegated task runs multiple review-fix cycles (memory `drop-receipt-to-break-codex-2026-05-09`).

## Investigation targets
**Required**:
- `plugins/flow-next/scripts/hooks/ralph-guard.py:21` (`RALPH_GUARD_VERSION`), `:250-266` — the `codex exec` block to amend (note the `--last` hard-block + the copilot block right after — must stay intact)
- `plugins/flow-next/agents/worker.md:137-161` (Phase 4 `REVIEW_MODE=none` skip), `:232-269` (Phase 5 done + verification + `--evidence-json`)
- `plugins/flow-next/skills/flow-next-work/phases.md:76-218` — per-task loop (where the host breaker counter lives)
- `plugins/flow-next/docs/ralph.md` — Ralph internals (autonomous-mode contract the delegation must honor)
**Optional**:
- memory `drop-receipt-to-break-codex-2026-05-09`, `final-integration-tasks-need-wider-impl-2026-05-26`

## Acceptance
- [ ] `ralph-guard.py` allows ONLY the full canonical delegation shape (inline `FLOW_DELEGATE_CODEX=1` + `codex exec` + `--ignore-user-config` + `--output-schema` + `-o .flow/tmp/codex-*` + sandbox-flag allowlist, no `--last`/`resume`/`review`) and STILL blocks: bare `codex exec`, a sentinel-prefixed but otherwise-arbitrary command (e.g. `FLOW_DELEGATE_CODEX=1 codex exec --last`, or one MISSING `--ignore-user-config`), `codex ... --last`, and the copilot invocation — each covered by a regression test. `RALPH_GUARD_VERSION` bumped and its tests updated.
- [ ] The circuit-breaker counter is host-owned: the worker emits `DELEGATION_RESULT=<class>` + `DELEGATION_ACTION=<action>` + `evidence.delegation`; a test (or documented host-loop logic) shows `cli_failure`/`rollback_and_disable` → IMMEDIATE disable for remaining tasks, and 3 consecutive `task_failure`/`partial` → `delegation_active=false` (counter survives per-task context resets).
- [ ] With `REVIEW_MODE=none` + delegation, the worker runs its own Phase 5 verification before `flowctl done` (no blind trust of `verification_summary`); with `REVIEW_MODE != none`, the impl-review SHIP gate covers it (no duplicate test run).
- [ ] Delegated batch result is INLINED into `flowctl done --evidence-json` as `evidence.delegation.result` ({status, files_modified, issues, summary, verification_summary} + model/effort/class) — no scratch-file pointer, no new receipt subsystem; evidence survives scratch-dir cleanup.
- [ ] Ralph mode: delegation runs only when `work.delegateConsent=true` is pre-set; a forced failure falls back to standard mode and the loop continues (never blocks); the result block lands in the Ralph log/receipt.
- [ ] Delegated commits carry the exact trailers `AI-Orchestrator: Claude` + `AI-Implementer: codex <model> (<effort>)` (written by the worker at Phase 3); make-pr reflects both models when run.
- [ ] Test suite green.

## Done summary
_(pending implementation)_

## Evidence
_(pending implementation)_
