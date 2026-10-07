---
satisfies: [R1]
---
# fn-285-linear-duplicate-status-reads-as.1 Implement Linear Duplicate status reads as cancelled

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Linear issues in the system-managed Duplicate status (type `duplicate`) now normalize to `cancelled` in the Linear read fallback instead of failing with `unmapped-state` (#522). The write side is unchanged: `TYPE_TO_SLOTS` still has no `duplicate` pool, so state resolution never picks Duplicate for the cancelled slot and flow-next never writes an issue into it.

Defect route:
- prior fixes: open PRs none; recent commits on status/providers.py and providers/linear.py none touching the type fallback; memory bug track no match; issues only #522 itself
- diagnosis: confirmed `_norm_linear` falls through to `CONFLICT unmapped-state` for type `duplicate` (regression test calling it with the reporter's measured raw shape returned the CONFLICT on base)
- introduced by: skipped: no known-good revision (the type was never mapped)
- base: test_linear_duplicate_state_reads_cancelled FAILED with TrackerError CONFLICT unmapped-state at a12b8fc0 (test commit 9236dbfd) | head: passes; test_tracker_status 102/102, all test_tracker_*.py 1005/1005
- live: no live surface (library code; no Linear workspace exercised)

stage: impl-review - skipped(policy: risk - one read-taxonomy entry routing duplicate through the existing canceled path, no write-path change, covered by a regression test)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 9236dbfdeb58aa3f977a1b4ebc078fa71c0d3638, 45bd1c1462e5cbf743953aa0c548d2dbe8d0e1ec
- Tests: python3 scripts/run_tests_parallel.py --pattern test_tracker_*.py, uvx ruff@0.16.0 check
- PRs: