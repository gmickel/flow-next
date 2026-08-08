---
satisfies: [R1]
---
# fn-181-state-provenance-status-source-review.1 flowctl show/list: status_source provenance field + absent-runtime advisory

## Description
Spec fn-181 item 1 (#304 half 1). status_source: "flow-state"|"committed" on show/list --json (always present); one plain-output advisory line when the runtime dir is absent. The merge code already knows which store answered.

## Acceptance
R1 of the spec.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
