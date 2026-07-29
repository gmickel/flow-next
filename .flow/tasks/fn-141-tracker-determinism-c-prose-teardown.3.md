---
satisfies: [R6, R7]
---
# fn-141-tracker-determinism-c-prose-teardown.3 Verify inactive path + every perEvent value end to end

## Description
Verify the invariant this whole batch rests on, AFTER rewiring - because .2 is what changes the final inactive path.

Bridge-inactive: one config read, no adapter import, no new output, byte-for-byte unchanged. Asserted via the reached-path harness.

Then test every configured `perEvent` value end to end: `off | pull | push | reconcile | comment` - an earlier draft omitted **`pull`**. Enumerate every event key and its legal values, including QA's comment-only rule and land's unconditional status rule.

Instrument each caller with a **fake flowctl** and assert config reads, argv, imports, stdout and stderr against a **pre-teardown captured oracle**, so "byte-for-byte" names both the streams and the thing compared.

## Acceptance
- [ ] Bridge-inactive path byte-for-byte unchanged (reached-path harness)
- [ ] No adapter package import occurs on the inactive path
- [ ] Every perEvent value incl. `pull` tested end to end; QA comment-only and land unconditional-status rules covered
- [ ] Fake flowctl asserts config reads, argv, imports, stdout, stderr vs a pre-teardown oracle

## Done summary
Added an executable fake-flowctl harness for all ten tracker lifecycle callers. It proves inactive-path silence against the pinned oracle and validates every perEvent value, facade input contract, QA coercion, Work fixed operation, make-pr unconditional reconcile, and land merge-evidence route.
## Evidence
- Commits: f630180d35b7854bb3ff8f7e7d529e05302dc210, 8b0a6cc1dd1c9cc779e52616403182d82c80c8d2, 6b4c1924731965cf673b854b8f2ab76f2c8dae89
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_caller_execution test_tracker_caller_oracle test_tracker_sync_prose_teardown test_tracker_sync_mirror_parity test_reached_path_harness -q, cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_mirror_parity test_reached_path_harness -q, python3 -m py_compile plugins/flow-next/tests/test_tracker_caller_execution.py plugins/flow-next/tests/fixtures/tracker_callers/fake_flowctl.py, Codex impl-review: SHIP (gpt-5.6-sol, medium)
- PRs: