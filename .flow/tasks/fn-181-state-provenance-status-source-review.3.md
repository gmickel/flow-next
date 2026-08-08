---
satisfies: [R3, R4, R5]
---
# fn-181-state-provenance-status-source-review.3 ready/anchor behind-upstream advisory; list/status/next untouched

## Description
Spec fn-181 item 3 (#307 RESCOPED). One advisory line + stale_vs_upstream JSON field on ready and anchor when HEAD is behind its upstream; one check per invocation; instant skip when no upstream; any git failure degrades to no advisory. list/status/next gain NO upstream check (R4 exists so the narrowing survives delegation) - assert spawn-count parity in tests or record an inspection note.

## Acceptance
R3, R4, R5 of the spec.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
