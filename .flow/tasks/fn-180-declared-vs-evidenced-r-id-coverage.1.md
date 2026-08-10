---
satisfies: [R1]
---
# fn-180-declared-vs-evidenced-r-id-coverage.1 export-cognitive-aid: undeclared_r_ids alongside uncovered_r_ids

## Description
Spec fn-180 item 1 (#301). Accumulate a second set from all tasks' satisfies regardless of status; expose undeclared_r_ids in the payload. uncovered_r_ids semantics byte-identical. Tests: plan-gate state (all todo, full declaration) shows zero undeclared + full uncovered; a genuinely unassigned criterion appears in undeclared.

**Files:** plugins/flow-next/scripts/flowctl.py (export-cognitive-aid payload) + `.flow/bin/flowctl.py` dual copy; export tests

## Acceptance
R1 of the spec.

## Done summary
export-cognitive-aid per fn-180 R1 (#301). tasks_summary gains undeclared_r_ids (R-IDs not claimed by ANY task at any status), accumulated in the same loop as the untouched evidenced-only uncovered_r_ids; both preserve spec R-ID order; new key sits directly after uncovered_r_ids. Plan-gate state reports zero undeclared + full uncovered; a genuinely unassigned criterion appears in both; done-state both empty; partial-done pinned so a todo declaration cannot leak into the evidenced set. 4 new tests.
## Evidence
- Commits: 01ec9e9c
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_export_traceability -q (37 OK), test_export_cognitive_aid test_acceptance_criteria_parser test_make_pr_reached_path (35 OK), test_tracker_distribution test_bin_launcher_parity test_prompt_text_pinned (28 OK)
- PRs: