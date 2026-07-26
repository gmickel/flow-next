---
satisfies: [R13]
---
# fn-139-tracker-sync-determinism-flowctl-owns.6 Cross-adapter conformance matrix + fault injection

## Description
Focused regression tests live with the code in .1-.5. This task is the **cross-adapter conformance matrix** (same operation, all four adapters, same assertions) plus **fault injection** for the failure modes no single task owns.

Fault points: the open pre-create window, post-write readback failure, scoped invalidation, lock race on `tracker.resolved`, retry exhaustion, rate-limit backoff. Every measured edge case in the spec gets a case, including the no-dedup reality (identical title+body creates a second issue on all three tested adapters).

## Acceptance
- [ ] Conformance matrix covers every verb across all four adapters
- [ ] Fault injection covers all six fault points above
- [ ] The pre-create window is tested as OPEN (documenting the accepted gap, not asserting it closed)
- [ ] Rate-limit backoff asserted per adapter's own header shape
- [ ] Full gate green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
