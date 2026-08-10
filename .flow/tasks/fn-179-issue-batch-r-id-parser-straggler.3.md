---
satisfies: [R6]
---
# fn-179-issue-batch-r-id-parser-straggler.3 tracker resolve --select: run full assignment over remaining slots

## Description
Spec fn-179 item 5 (#308). After merging the selection in _run_select, run the normal slot assignment over the remaining slots and persist the union so missing_required reaches the existing _assignment_to_data CONFLICT guard; never stamp scopeResolvedAt on a REQUIRED-incomplete map. in_review never auto-fills (design stays). Issue #308's five-step repro is the acceptance fixture shape.

**Files:** plugins/flow-next/scripts/flowctl_tracker/resolve_verb.py + dual tracker copy + manifest regen; tracker resolve tests

## Acceptance
R6 of the spec. Repro step 3 yields a complete map; REQUIRED-incomplete yields CONFLICT, no fresh stamp.

## Done summary
tracker resolve --select per fn-179 R6 (#308). _run_select now merges the human tiebreak, then runs the provider's normal slot assignment over the remaining slots (new pure assign_slots_from_pools halves extracted from linear/jira resolvers - no second network call inside the lock) and persists the union inside the transaction's finalize_fn. REQUIRED-incomplete maps persist (progress kept, avoids two-select deadlock) but return CONFLICT through the existing _assignment_to_data guard and are NEVER stamped: resolve_transaction gained a stamp predicate evaluated on the final data inside the lock, and stamp=False also removes a prior stamp so #308-damaged configs self-repair on the next select. in_review never auto-fills (policy unchanged). Five-step #308 repro ends complete at step 3.
## Evidence
- Commits: 81d8e10c
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolution_linear_jira -q (49 OK), 8 tracker suites (449 OK), test_tracker_distribution test_tracker_package_import test_tracker_sync_mirror_parity (44 OK)
- PRs: