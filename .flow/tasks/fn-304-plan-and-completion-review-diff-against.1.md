---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-304-plan-and-completion-review-diff-against.1 Implement Plan and completion review diff against the spec's own base

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Plan review falls back to the repository's default branch instead of a literal main (#538). Completion review, on every CLI backend and the host workflow, uses an explicit base, else the base work recorded for this spec (`.flow/tmp/spec_base_branch`, spec id + branch name, written by work's branch fence), else the chain parent's branch, else the default branch (#569). Host compares the record against the canonical spec id and only queries the chain when no valid record exists.

Tests: master-only repo (plan + completion), recorded integration base excludes another child's commits, foreign/dead record falls through, chain parent branch, explicit base wins / fails closed, no base names --base; work fence records the branch for chain and --base runs; host fence order incl. short alias.

stage: impl-review - ran codex 3-draw NEEDS_WORK (host short-alias P1, eager chain lookup P2; both fixed) -> re-review SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 12d09ad224cd795f4870fd61e0eb3289c9322443, 5ab34056b4839fbc73516435ceedce2357285434
- Tests: python3 scripts/run_tests_parallel.py; python3 -m unittest test_host_review_backend test_claude_review_commands test_sync_codex_check
- PRs: