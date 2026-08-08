---
satisfies: [R2]
---
# fn-182-tracker-create-first-cas-list-open.2 Linear wire list-open: capability error when readyState unset

## Description
Spec fn-182 item 2 (#311 minimum option). Replace the silent {issues: [], success: true} with an explicit unresolved/capability error naming what is unresolved and how to resolve it - without telling the user to arm the projection (unset readyState is legitimate). readyState-set behavior unchanged.

## Acceptance
R2 of the spec. No silent-empty path remains for this condition.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
