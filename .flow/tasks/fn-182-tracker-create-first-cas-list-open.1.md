---
satisfies: [R1]
---
# fn-182-tracker-create-first-cas-list-open.1 create-first-put --if-absent (compare-and-set mint claim)

## Description
Spec fn-182 item 1 (#310). --if-absent succeeds only when the record's specId is absent (optional --expect-spec-id); race loser gets a distinct CONFLICT. Runs under the existing config lock. Without the flag, behavior unchanged. Pending-claim design and stale-claim reclaim window untouched.

## Acceptance
R1 of the spec. Two-promoter race fixture: one recorded spec, one informed loser.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
