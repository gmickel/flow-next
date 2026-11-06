---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-320-plan-only-when-the-person-asks-for-it.1 Implement Plan only when the person asks for it

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Plan is chosen only when the person asks for a plan or a task breakdown, in their request or in the spec.

- **The rule:** plan-vs-no-plan keeps that one signal. Owners, several PRs, several repos, an order between parts, size and risk all stay on the direct route.
- **Code route:** flowctl no longer reads a plan ask from the spec body. A ready zero-task spec with no recorded route routes direct, and flow's host applies the ask, attended (Step 2) and under `--auto`.
- **Skill text:** the plan skill's trigger text sends other build requests to flow. Work's zero-task question lists the direct route first as the recommended option.
- **Pointers:** stale pointers in the task-manager skill, prime, prospect, strategy and map now point to flow, and six runtime docs, the Codex mirror and the CHANGELOG are updated.

Pre-registered study at agent-evals `studies/plan-route-explicit-2026-11` (Opus 5.5, 3 draws per item): SHIP.
- 9.7.0 sent 9 of 24 no-ask states to plan; the candidate sent 0 of 24.
- Explicit asks reached plan 12 of 12 in both.
- The plan skill fired on build prompts 0 of 18 in both.
- The follow-up on the final text passed, including an ask written only in the spec (3 of 3).

stage: impl-review - ran (codex, 3 rounds: NEEDS_WORK -> NEEDS_WORK -> SHIP; the word-list regex was replaced by host reading after two failed patches) (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 0bde2ec7b7cd89badf7abf0d4e6c7ebedc24c031, 9813042d8617593482a0500fc86db8959d12b930, eb521651e3446782a4b8b504678cc27a10904ee2, a8926b90055e0ad8ea385bd4c9826defe39d2fd4
- Tests: python3 scripts/run_tests_parallel.py
- PRs: