---
satisfies: [R2]
---
# fn-180-declared-vs-evidenced-r-id-coverage.2 make-pr skill: plan-gate rendering + abort re-keyed on undeclared coverage

## Description
Spec fn-180 item 1 (#301). make-pr renders per-criterion claimed-not-evidenced status at a plan gate and aborts only when coverage is undeclared (the condition the abort was meant to catch). Update the skill prose + any reference; sync-codex twice.

## Acceptance
R2 of the spec. #301's abort repro renders instead of aborting; undeclared-coverage state still aborts with corrected stderr advice.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
