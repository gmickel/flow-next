---
satisfies: [R1, R2]
---
# fn-136-structured-review-artifact-schema-in.2 Deterministic finding parser in flowctl

## Description
Implement the pure-stdlib parser and finding-lineage model for the versioned `findings` container.

**Size:** L

**Files:** flowctl.py parser/lineage helpers, dual-copy pin, focused fixtures/tests.

### Approach
- Parse current review fields into canonical P0-P3 severity, confidence anchors 0/25/50/75/100, introduced/pre_existing classification and open/fixed/not_fixed/withdrawn status.
- Generate deterministic round-1 IDs from source receipt identity plus ordinal. Carry IDs through ratchet `Prior finding N` forms; new later findings get new IDs and explicit lineage where needed.
- Parse portable anchors only when path, side/line and base/head context are available. Never guess an anchor; preserve rename/original-path metadata when evidenced.
- Preserve explicit receipt/round/supersedes context and canonical finding order.
- Tolerate observed backend label variants. Unknown enums/unsupported versions retain prose as unsupported; wholly unparseable output emits no structured container and never raises.
- Bound parser input and cover arbitrary-text never-throws behavior.
## Acceptance
- [ ] Parser emits the exact versioned findings schema, canonical enums, stable lineage IDs, portable anchors and ordering (R1).
- [ ] Real backend and ratchet fixtures prove identity carry-forward, no guessed anchors, unsupported-version behavior, degrade-to-prose and never-throws safety (R2).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
