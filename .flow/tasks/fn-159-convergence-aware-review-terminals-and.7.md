---
satisfies: [R1]
---
# fn-159-convergence-aware-review-terminals-and.7 Hash-guard wiring: blob builders, per-transport reserve points, NOT_RETRYABLE contract, RP/host fences

## Description
Wire the artifact-hash dispatch guard onto the .1 foundation: domain-separated blob builders, per-transport reserve points (incl. the new side-effect-free `rp mode-probe`), `--force`, the NOT_RETRYABLE refusal + driver terminal mapping, and the RP/host workflow fence updates.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, plan/impl/completion `workflow-rp.md` AND `workflow-host.md`, the exact terminal-owning files per surface: plan-review `workflow.md`; impl-review `workflow-common.md` + the fix-loop terminal owner in its SKILL.md; completion-review `workflow-common.md` + its SKILL.md terminal owner (NOT_RETRYABLE mapping — non-pinned prose; verified file inventory: impl and completion have NO workflow.md), pilot + land workflow prose and Ralph driver docs/`scripts/ralph/ralph.sh` template (non-pinned; pinned prompt templates coordinate via .4), `plugins/flow-next/tests/test_review_convergence_cap.py` + a driver-facing no-repeat regression (test_ralph_guard.py or sibling)

### Approach
- Guard in `enforce_and_increment_review_cap()` after sidecar check, before cap branch: compare caller-supplied hash to baseline (latest consumed verdict row in scope + current epoch). Refuse: `NOT_RETRYABLE: artifact unchanged since last verdict`, exit 1, zero mutation. `--force` consumes normally, stamps `forced`. Absent hash or hash failure → inert/fail-open with warning. No sidecar → inert.
- Blob builders per type: plan = sorted normalized spec+task md; impl = exact diff handed to reviewer; completion = spec+tasks+diff+criteria. Hash key includes review type (plan↔completion never equate).
- Reserve points: new side-effect-free `rp mode-probe` (CLI availability, no window mutation) → CE reserves immediately before setup/review call; Classic after final prompt assembly immediately before chat-send; Cursor hashes the post-fit prompt's diff component; host reserves in its dispatch fence post-compose. Exactly one reservation per branch; setup failure refunds only what was reserved (per-branch tests).
- Workflow fences: three workflow-rp.md capture reservation id from increment JSON, pass to record; REMOVE the explicit `review-rounds reset` post-SHIP calls (record owns it since .1); add the incomplete-finalization replay check before increment. workflow-host.md per surface: same reserve/record/replay contract; at least one host-path reserve/finalize regression.
- Driver terminal mapping (rounds 5+7+9): terminal-owning files per surface — plan `workflow.md`; impl `workflow-common.md` + its SKILL.md fix-loop terminal; completion `workflow-common.md` + its SKILL.md terminal — plus pilot + land workflow prose and Ralph driver docs/ralph.sh: exit 1 + the exact NOT_RETRYABLE marker = human-action terminal (edit artifact / human reset / human --force), never transport refund, never redispatch. Surface-specific regressions prove the marker stops plan, impl, AND completion autonomous flows without refund/force/reset/redispatch.
- fn-155 regression shape: 4 same-artifact dispatches → 1 dispatch + refusals; reset → clean dispatch without --force. Completion shape: NEEDS_WORK → impl-only fix → re-dispatch proceeds. Intervening-file-change + Cursor-fitted-diff tests bind stored hash to the exact artifact received.

### Investigation targets
**Required:**
- Task .1's landed foundation (registry/journal/lock APIs) — build on, don't duplicate
- `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md` — Phase 2/3/4 fences
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` — host dispatch fence shape
- `plugins/flow-next/scripts/flowctl.py:36160-36230` — cursor fitting path

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:10104-10250` — enforce entry, now `_enforce_and_increment_review_cap_locked` (was :9429-9510 pre-.1; the file grew ~788 lines in this region). The sidecar-exists check landed at :10117-10120; the cap branch (`if current >= cap:`) is at :10245 — the hash guard goes between them, per the spec's "after the sidecar-exists check, before the cap branch" placement. <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.1 shifted this region; anchor corrected -->
- `_backend_completion_review` diff assembly (grep)

### Key context
- Exit code MUST NOT be 4 (cap/escalate) nor 2/3/5. Marker text is a driver contract — byte-exact.
- SKILL.md terminal-contract prose is not hash-pinned; templates are — touch none here.

### Acceptance
- [ ] Guard refuses/permits per domain-separated baseline; --force + forced stamp; fail-open paths
- [ ] mode-probe branches reserve at the specified points; one reservation per branch; per-branch refund tests
- [ ] Three workflow-rp.md + host workflows: id passing, reset-call removal, replay check; host regression green
- [ ] NOT_RETRYABLE driver mapping in the three common terminal contracts; no-repeat regression
- [ ] fn-155 + completion + intervening-change + Cursor-fitted tests green

### Round-8 additions
- RP fences assemble the receipt inputs (receipt/status targets, session/model metadata) BEFORE `review-rounds record` and pass them as record's new parameters; `review-findings attach` only validates + publishes the journaled payload by reservation id. The named crash test (fresh process after record, before attach input exists) runs against THIS fence ordering.
- Fences consume the plural replay result (`replays: []`) with terminal precedence NEEDS_HUMAN > NEEDS_WORK > all-SHIP.
## Acceptance
- [ ] Guard half of R1 satisfied end-to-end on all transports incl. host
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
