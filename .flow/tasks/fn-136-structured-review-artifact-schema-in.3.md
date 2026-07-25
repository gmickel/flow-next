---
satisfies: [R1, R4]
---
# fn-136-structured-review-artifact-schema-in.3 Receipt-write integration across backends

## Description
All review receipt writers attach findings[] at write time; schema additive; no latency.

**Size:** M

**Files:** flowctl.py receipt-write paths (codex/copilot/cursor wrappers for plan|impl|completion review; the rp receipt path; host receipt guidance in skill prose gets the field documented), receipt validation, tests.

### Approach
- Wire the .2 parser at every review receipt write (the reviewer output text is already in hand at that point - no new I/O); attempt/refund records (fn-131) untouched and non-colliding.
- Validation: findings optional; legacy receipts valid; new receipts validate field types.
- Micro-benchmark in tests (parse of the largest fixture under a loose bound) documenting no meaningful latency (R4).
- Quick commands: focused receipt/parser test modules.

## Acceptance
- [ ] Findings attached across all backend receipt writers; legacy receipts unaffected (R1).
- [ ] Latency bound documented via test; no added I/O (R4).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
