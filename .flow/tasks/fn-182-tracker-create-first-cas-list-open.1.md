---
satisfies: [R1]
---
# fn-182-tracker-create-first-cas-list-open.1 create-first-put --if-absent (compare-and-set mint claim)

## Description
Spec fn-182 item 1 (#310). --if-absent succeeds only when the record's specId is absent (optional --expect-spec-id); race loser gets a distinct CONFLICT. Runs under the existing config lock. Without the flag, behavior unchanged. Pending-claim design and stale-claim reclaim window untouched.

**Files:** plugins/flow-next/scripts/flowctl_tracker/lifecycle/ (create-first verbs) + flowctl.py dispatch + dual copies + manifest regen; tracker lifecycle tests

## Acceptance
R1 of the spec. Two-promoter race fixture: one recorded spec, one informed loser.

## Done summary
create-first-put CAS per fn-182 R1 (#310). --if-absent (succeed only when specId absent; strict - same-id re-put also conflicts, with details showing recordedSpecId == attemptedSpecId so a resumer recognizes itself) and --expect-spec-id (CAS update; the sanctioned idempotent path), mutually exclusive. Race loser gets a tracker-shaped error envelope, exit 10 (CREATE_FIRST_CONFLICT_EXIT mirroring ErrorClass.CONFLICT), subtypes spec_already_minted / spec_id_mismatch / record_unreadable / lock_timeout (retryable). A refused CAS writes nothing at all. Spec drift resolved: the put path held NO lock (spec said "already held") - conditional path now wraps read-check-write in the existing _shared_config_lock; flagless path unchanged byte-for-byte incl. last-write-wins, pinned by test. Legacy no-tracker-package copies degrade to narrowed-window, documented inline. 9 new tests (two-promoter race, CAS match/mismatch, flagless unchanged).
## Evidence
- Commits: 04677664
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_create_first_recovery test_create_first_sequence -q (46 OK), test_flowctl_surface test_tracker_distribution test_tracker_lifecycle (89 OK)
- PRs: