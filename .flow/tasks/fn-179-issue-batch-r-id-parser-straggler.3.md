---
satisfies: [R6]
---
# fn-179-issue-batch-r-id-parser-straggler.3 tracker resolve --select: run full assignment over remaining slots

## Description
Spec fn-179 item 5 (#308). After merging the selection in _run_select, run the normal slot assignment over the remaining slots and persist the union so missing_required reaches the existing _assignment_to_data CONFLICT guard; never stamp scopeResolvedAt on a REQUIRED-incomplete map. in_review never auto-fills (design stays). Issue #308's five-step repro is the acceptance fixture shape.

## Acceptance
R6 of the spec. Repro step 3 yields a complete map; REQUIRED-incomplete yields CONFLICT, no fresh stamp.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
