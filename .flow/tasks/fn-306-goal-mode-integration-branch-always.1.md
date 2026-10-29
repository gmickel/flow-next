---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-306-goal-mode-integration-branch-always.1 Implement Goal mode: integration branch always, rigor set by the goal

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Goal mode states the contract and a few facts instead of a procedure: integration branch always (legacy direct-landing goals finish under their log), rigor from the goal spec's plain words with repo config as default and logged, the run decides split/size/order and drives the stage skills directly (each skill invoked per child, every merge through land, children routed by plan-vs-no-plan). Parallel licence removed (zero gain). Full suite 4067 OK, ruff clean.
stage: impl-review - ran (codex: round 1 NEEDS_WORK fixed; re-reviews NEEDS_WORK on pending eval, then SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 760be687b5df68d3dc5ff48d73447e2ffdb9d795, f691748e8eef64295e079fd254d582e86d84b9b5, 00c4015781480c12d43dd85ccdb8182d41873dfc, 737d20b55183d07a33bfa82ddf03e3f3d4edd35b, b2e303772c3e4a159cb00228095ce7f7f052d969
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: