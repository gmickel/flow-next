---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-327-9110-final-audit-fixes-for-issue-start.1 Implement 9.11.0 final-audit fixes for issue start and intake

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Final-audit fixes: R1 find_linked_specs fails closed on an unreadable ref tree or listing (test ff0ea1666 failed first, fix 1d2a963e9). R2 a remote-only link fast-forwards an existing local branch or stops, and the checkout's spec must carry the link. R3 a spec captured from an issue states every task gets implementation review and working-rules honours it. R4 the question slug ends in the issue body's SHA-256 digest. R5 intake reads the whole issue before capture or fold. Contract tokens pinned (5271470da failed first).

Full suite 4334/0 failures at 90fd625f7; P2 follow-ups re-checked with focused tests.

stage: impl-review - ran codex three lenses SHIP with two P2s taken (model: gpt-6.1-sol)
Implemented inline by the conductor (claude-opus-5-5).

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: ff0ea16668ab72b8973e97c3ca43f5554fec2bd9, 1d2a963e951d06773ca091c8a0bfec2ccda7b4af, 5271470da7202cc886f1e504599bef2e40733363, 90fd625f7311f3a49d0cd2132a96043c541c206b, a172d7dd51e30119195189b4b25f814e8bf5a359
- Tests: python3 scripts/run_tests_parallel.py (4334/0); focused test_flow_auto, test_tracker_list_open_intake, test_flow_routing, test_spec_ref_index after follow-ups
- PRs: