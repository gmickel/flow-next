---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-313-opt-in-spec-wins-issue-body-at-first.1 Implement opt-in spec-wins issue body at first claim and make-pr

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added opt-in `tracker.specWins` (boolean, absent = off; only the literal `true` activates).

- First claim (`push --status-only --event work.firstClaim`): also writes the rendered spec as the issue body via sync_body with an explicit body (echo fence off, so the live body decides), no title, no relations, no project membership. Outcome recorded in the receipt as `details.specWinsBody` = written | unchanged | failed; a failed write still moves status, and a later status/comment failure keeps the body outcome in its error details and receipt.
- make-pr reconcile (`--event makePr`): the final body is `render_body(flow_body)` instead of the folded tracker snapshot; existing readback/pair recording means a later push writes nothing.
- Schema (generator table + regenerated JSON), drift allowlist, flowctl.md config row, tracker-sync.md paragraph, tracker-sync steps.md sentence (no body merge, genuine comments still folded), CHANGELOG Unreleased entry, manifest + Codex mirror regenerated.
- Tests: tests/test_tracker_spec_wins.py, 10 tests on GitHub and Linear (edited, equal-with-stale-pair, failed write, failure after failure, project membership untouched, off/non-true values, reconcile write + follow-up push noop, reconcile off, reconcile failed write, schema boolean). Verified the tests fail with the feature disabled.

stage: impl-review - ran (model: codex gpt-6.1-sol high) round 1 NEEDS_WORK (3 findings, all fixed), re-review SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: ef4eba4249e7602c143cf9f91440646540dc4b2b, 18a9fba38096a3c9d91b963ad3c62152aee67bc7
- Tests: python3 scripts/run_tests_parallel.py --pattern 'test_tracker*.py' (1018 ok); python3 scripts/run_tests_parallel.py --pattern 'test_flow_config_schema*.py' (41 ok)
- PRs: