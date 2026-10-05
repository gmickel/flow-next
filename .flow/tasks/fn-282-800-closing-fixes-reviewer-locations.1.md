---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-282-800-closing-fixes-reviewer-locations.1 Implement 8.0.0 closing fixes

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Delivered the 8.0.0 closing fixes. R1: the findings parser accepts a note after a location's line or range (plain or backticked), so a merge plan no longer refuses that round on any backend. R2: `spec set-backend` and its sibling `task set-backend` name the flag in errors. R3/R4/R5 (#503): `flowctl spec close --retire <superseded|moot|delivered-elsewhere> [--by ...]` records `retired: {reason, by}`, settles never-run tasks as `retired`, records a `not_required` completion review, and stops `next` routing to the spec. The closed set used by land and make-pr counts a retired record-only close. show, specs, list and the aid export read the retirement, and tracker sync surfaces a merged retired spec as a cancel without applying it. Reopening a retired spec drops the record. The won't-do skill text, tracker create-first and land use the new form. R6: `.flow/criteria.md` drops G3 (STRATEGY.md's back-reference removed) and its header names implementation review. R7: the fn-168 decision record states the three-round rule. R8: CHANGELOG Unreleased credits @sn-furali. Root help regenerated under python3.14 and is byte-identical (HELP_SHA256 unchanged).

Tests (red before the fix, green after): test_review_findings_parser `test_location_with_trailing_note_keeps_its_anchor` (all five registry backends; `-` still no anchor); test_review_fanout `test_merge_plan_accepts_location_with_trailing_note`; test_backend_spec `test_spec_set_backend_error_names_the_flag` plus a strengthened task-level assertion; test_spec_close_reopen retire tests (record/settle/excusal/validate/ready/next/start, task-less next, the three refusals including argparse's accepted list, reopen with completion-review routing, show/specs/list/export); test_pr_cognitive_aid_multi_spec (retired record-only close counts; a renamed retired spec is not a new close; the cheap-path pins now expect one HEAD read, by the AC's declared intent); test_tracker_status (a merged retired spec defers as cancelled-family).

Decisions: the `retired` task status is set only by `--retire`, with no new task command. An already-recorded `ship` is kept rather than overwritten. A location with no parseable path and line keeps today's result: `-` is no anchor, other text stays invalid (recorded invalid-vs-absent rule). fn-196 left as closed: retiring an already-closed spec is refused by design.

Follow-ups (not done): `spec_tasks_all_done` (spec-chain detection) still treats a retired dependency's tasks as in progress. Two bug memory entries still cite `.flow/criteria.md` G3 as history. The smoke_test.sh copilot plan-review re-review step fails whenever the live Copilot verdict in round 1 is not SHIP (artifact-unchanged guard); this predates the change and is unrelated to it. flow-next.dev docs for `--retire` are downstream.

Tier: session (jev intelligent 0.69)

stage: impl-review - ran (codex, 3 reviewers: NEEDS_WORK with 3 findings fixed in 3ed8f4a4, re-review SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
- Post-audit regression check (maintainer-requested, 2026-10-05): one same-load pair on case 4 (gno-233, attended, criteria dropped), 7.1.2 vs fbfe0dcc (rounds fn282-c4-{a,b}-1005). Hidden checks pass on both; judge 19.5 vs 18.5. 7.1.2 took a direct route (no capture) and shipped a defect the person caught (setting change did not re-chunk indexed data): first handoff 197 s, wall 1003 s, $3.78. 8.0 asked the re-chunk question, captured and ran work like all six earlier case-4 draws: first handoff 582 s, wall 1991 s, $9.03, then a full-suite ask and a scope question. 8.0's first handoff and wall sit inside the earlier fn-281/7.1.2 ranges (476-696 s; 976-2890 s); cost is $1.38 above the earlier fn-281 draws, from the post-handback full-suite run. No regression attributable to the change.

## Evidence
- Commits: 550bd0ef22c56d0cda68f3e63bab1bd759c76be0, 3ed8f4a4f43f462082fbef4eea8d0b427122f0fb
- Tests: python3 scripts/run_tests_parallel.py (214 files, 3949 tests, 0 failures), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, python3 scripts/check_doc_anchors.py, python3.14 flowctl.py --help == flowctl-help.txt (HELP_SHA256 unchanged), smoke_test.sh from scratch dir: 131 pass, 1 fail (copilot plan-review re-review, live-verdict dependent, unrelated)
- PRs: