---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-319-replayable-defect-proof.1 Implement Replayable defect proof

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Guidance-only change for replayable defect proof (R1-R5); R6 is the post-implementation A/B (agent-evals studies/replayable-defect-proof-2026-11), not part of this diff.

- working-rules Tests: the failing test fails by assertion on the unchanged code as written (a literal for a constant the fix adds); a defect fix commits it alone, then the fix, attended or not; a refusing hook means one commit, never a bypass. (R1, R2)
- working-rules Tests: deferred or coalesced persisted writes keep the in-process value exact; a test reads it straight after the event. (R5)
- working-rules Attended: the commit rule names the defect-fix commits. (R2)
- working-rules Handoff: every reply that hands back a fix restates base and head observations from runs already made. (R3)
- defect-route step 4: one base/head pair per named symptom; the base reproduction run replaces the test when no assertion red is possible, and the hand-back says which. (R1, R4)
- work phases.md Phase 3 and agents/worker.md point at the Tests rule. Codex mirror regenerated.

stage: impl-review - ran [cecda6f80..e1b3c7c3d] SHIP, 0 findings (model: gpt-6.1-sol high, codex)

Follow-up rounds after the first A/B (maintainer: "fold it in"):
- working-rules Tests: targeted tests cover the changed code and its callers, including callers outside the changed folder; full suite only when asked. Handoff names the tests run and any caller with no tests. (R7; d0fd9ed5b, dd054fd2d, 9e3805edc)
- working-rules Tests: the test-only commit applies whenever a test is written first, features included; on a defect fix the tests also cover nearby cases reaching the same broken code. (R2, R8; 6f815d2bb)

stage: impl-review - ran [9e3805edc..6f815d2bb] SHIP, 0 findings (model: gpt-6.1-sol high, codex)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: e1b3c7c3d922b4a4fb51c0d9ee6b4f94557ed2ce, d0fd9ed5b, dd054fd2d, 9e3805edc, 6f815d2bb
- Tests: python3 scripts/run_tests_parallel.py (4209 ran, 0 failures); uvx ruff@0.16.0 check . (clean); ./scripts/sync-codex.sh --check (fresh)
- PRs: