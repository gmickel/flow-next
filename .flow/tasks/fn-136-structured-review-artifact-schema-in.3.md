---
satisfies: [R1, R4]
---
# fn-136-structured-review-artifact-schema-in.3 Receipt-write integration across backends

## Description
Integrate the versioned findings container across every review receipt writer and enforce currentness without adding I/O.

**Size:** M

**Files:** flowctl receipt-write paths for all backends/review kinds, receipt validation/currentness helpers, focused tests and benchmark.

### Approach
- Attach the parsed container where reviewer output is already in memory. Keep legacy receipts valid and attempt/refund records non-colliding.
- Persist sourceReceiptId, reviewKind/backend, round, base/head SHAs and supersedesReceiptId. Validate IDs, enums, anchors, references and duplicate lineage.
- Define current state solely from the newest explicit supersedes chain member whose head matches the current review head. Stale receipts stay visible evidence but never current resolution state.
- Benchmark the largest pinned finding fixture. Parsing/validation must add no model/network I/O and remain under the documented local budget.
## Acceptance
- [ ] Every backend/review receipt writer emits the optional versioned container; legacy receipts remain valid (R1).
- [ ] Supersedes/head rules deterministically select current finding status while preserving stale evidence (R4).
- [ ] Pinned benchmark passes and inspection proves no added model/network I/O (R4).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
