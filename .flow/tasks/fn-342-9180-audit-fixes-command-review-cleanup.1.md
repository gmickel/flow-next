---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11]
---
# fn-342-9180-audit-fixes-command-review-cleanup.1 Implement 9.18.0 audit fixes: command review cleanup, criteria probe and Antigravity recipe

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Fixed the 9.18.0 audit findings, each reproduced as a failing test first (10531ce1a): the documented agy wrapper runs agy by an absolute path outside the checkout (R1); the criteria probe runs git from the repository root (R2) and fires only while the file holds a tracked link target, against every merge stage (R5); an interrupted fan-out stops running command trees promptly and gives other draws at most the pipe grace (R3); the caller owns oversized-response cleanup, with a bounded reap and a closed response window (R4); a failed primary command draw keeps its label but not its session (R6); validate and deep-pass parse an explicit --spec strictly, and the schema's command pattern ends at end of input (R7); workflow-cli states the label-bound fallback (R8); setup marks no reviewer cross-family on Antigravity (R9); ladder pins by name (R10); fn-339 R1 reworded (R11). Windows limit documented beside the detached-helper note.

Declined (per spec): a Windows Job Object; rejecting a regular criteria file whose text is a path.

stage: impl-review - ran [r1 3-draw NEEDS_WORK .. r4 SHIP] (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 10531ce1a50a4ff5b4a6b1f30b6f94af0c5c78df, 0d425d9290338a6d68a884477e939af3c4461351, 7c09a2413293afd4f970fe29369b5b02a723db7d, 9502c68236069389d3c826a072fe41ab74b24e54, a31fe782d6128db205cf1a908e2a814acb9f95d4
- Tests: python3 scripts/run_tests_parallel.py (4591 ran, 0 failures); uvx ruff@0.16.0 check .
- PRs: