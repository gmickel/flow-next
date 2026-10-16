---
satisfies: [R1, R2, R3, R4]
---
# fn-297-defect-route-legitimate-state-fixes-and.1 Implement Defect route: legitimate-state fixes and the reported surface

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Blocked:
R5 unmet after two wording iterations; human call needed.

Same-time A/B (defect cases, 3 draws per arm, four rounds; table in the R5 evidence file kept locally): with the final wording (3bec8697) judge scores and hidden checks are level, the signal line appears in 4 of 9 handoffs, and median first hand-back on the small defect is 23-35 s slower (case 2: +17 s). The softer wording (710228fd) was no slower on either case but carried the signal line in 1 of 6.

Decide one: (a) accept the time cost and ship 3bec8697; (b) ship 710228fd wording and accept low signal uptake; (c) relax R5's time or signal clause; (d) another lever. Codex re-review NEEDS_WORK on R5 only (R1-R4 met).
## Evidence
- Commits:
- Tests:
- PRs:
