---
satisfies: [R2]
---
# fn-182-tracker-create-first-cas-list-open.2 Linear wire list-open: capability error when readyState unset

## Description
Spec fn-182 item 2 (#311 minimum option). Replace the silent {issues: [], success: true} with an explicit unresolved/capability error naming what is unresolved and how to resolve it - without telling the user to arm the projection (unset readyState is legitimate). readyState-set behavior unchanged.

**Files:** plugins/flow-next/scripts/flowctl_tracker/wire/linear.py (`list_open`) + dual copies + manifest regen; wire tests

## Acceptance
R2 of the spec. No silent-empty path remains for this condition.

## Done summary
Linear wire list-open per fn-182 R2 (#311 minimum option). Unset tracker.readyState now returns TrackerError(UNRESOLVED, subtype=ready_state, details.key=tracker.readyState, exit 4) naming what is unresolved and how to set it, with the "leaving it unset is a valid configuration" phrasing per the spec constraint - never an instruction to arm the projection. readyState-set behavior byte-for-byte unchanged; GitHub/GitLab/Jira untouched (Linear-only per Boundaries). No new enumeration verb. Existing all-four-noop matrices split so Linear asserts the refusal separately; new pins cover absent/null/blank readyState with zero transport calls.
## Evidence
- Commits: 96d9d8bc
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_wire test_tracker_conformance test_tracker_sync_backlog_mode test_tracker_facade test_tracker_caller_oracle test_tracker_caller_execution -q (249 OK), test_tracker_distribution test_prompt_text_pinned (25 OK)
- PRs: