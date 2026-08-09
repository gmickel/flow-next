---
satisfies: [R7]
---
# fn-179-issue-batch-r-id-parser-straggler.4 flowctl start --reclaim: identity repair distinct from --force takeover

## Description
Spec fn-179 item 6 (#316). Add --reclaim to flowctl start: rewrites the claimant with a repair claim note (distinct wording from the --force takeover note). No identity validation, no sibling-warning heuristic. --force unchanged.

**Files:** plugins/flow-next/scripts/flowctl.py (`cmd_start`) + `.flow/bin/flowctl.py` dual copy; start/claim tests

## Acceptance
R7 of the spec. Both notes distinguishable in the record; existing --force tests green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
