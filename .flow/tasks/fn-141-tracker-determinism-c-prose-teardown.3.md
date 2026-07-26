---
satisfies: [R6, R7]
---
# fn-141-tracker-determinism-c-prose-teardown.3 Verify inactive path + every perEvent value end to end

## Description
Verify the invariant this whole batch rests on, AFTER rewiring - because .2 is what changes the final inactive path.

Bridge-inactive: one config read, no adapter import, no new output, byte-for-byte unchanged. Asserted via the reached-path harness.

Then test every configured `perEvent` value end to end, not just the inactive case - `off`, `push`, `reconcile`, `comment` across the touchpoint set.

## Acceptance
- [ ] Bridge-inactive path byte-for-byte unchanged (reached-path harness)
- [ ] No adapter package import occurs on the inactive path
- [ ] Every perEvent value tested end to end across the touchpoint set

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
