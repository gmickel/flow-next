---
satisfies: [R3, R4, R5]
---
# fn-181-state-provenance-status-source-review.3 ready/anchor behind-upstream advisory; list/status/next untouched

## Description
Spec fn-181 item 3 (#307 RESCOPED). One advisory line + stale_vs_upstream JSON field on ready and anchor when HEAD is behind its upstream; one check per invocation; instant skip when no upstream; any git failure degrades to no advisory. list/status/next gain NO upstream check (R4 exists so the narrowing survives delegation) - assert spawn-count parity in tests or record an inspection note.

**Files:** plugins/flow-next/scripts/flowctl.py (ready/anchor) + `.flow/bin/flowctl.py` dual copy; advisory + spawn-count tests

## Acceptance
R3, R4, R5 of the spec.

## Done summary
ready (incl. --all) and anchor emit a behind-upstream advisory (plain note + stale_vs_upstream JSON count) via one read-only git spawn per invocation (git --no-optional-locks status --porcelain=v2 --branch -uno; upstream name comes from the same spawn). Any git failure degrades to no advisory. list/status/next proven spawn-clean by git-shim counting tests; inspection note pins the sanctioned call sites. 12 new tests (test_upstream_advisory.py) + orchestrator review fix dc329c12.
## Evidence
- Commits: 19577611, dc329c12
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_upstream_advisory -q
- PRs: