---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-274-agent-first-sweep-defect-route-stops.1 Implement Agent-first sweep: defect route stops and feature-map plumbing

## Description
Delete agent-first ceremony from two shipped surfaces (STRATEGY.md "Agent first", `.flow/criteria.md` G4). This is deletion, not replacement.

- Defect route (`skills/flow-next-work/references/defect-route.md`, route-matrix defect row, flowctl judge presentation text): the prior-fix step records open PRs touching the area and continues, stopping only when one fixes the bug or a person visibly owns a fix in progress (R1); reproduction asks for one that fires reliably, no fixed count (R2). Judge classification criteria text stays unchanged.
- Resolved-feature plumbing: remove the record, `flowctl done --resolved-feature`, the QA receipt field, the first-current-record precedence rule, the defect-intake verbatim-confirmation step, and the make-pr "Resolved feature" proof cell, with their tests (R3). Live-app stages read the feature map and match the feature themselves. Old receipts/task files carrying `resolved_feature` still load (R4).
- Docs, codex mirror, CHANGELOG Unreleased, flow-next.dev pages match; full suite green (R5).

Review focus: overengineering, slop and YAGNI. Reject any replacement mechanism, compat scaffolding beyond what R4 needs, or leftover references to the removed record.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
