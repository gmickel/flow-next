---
satisfies: [R7]
---
# fn-195-orchestration-by-intent-named-tiers-per.4 Record what actually ran, so prose routing is checkable

## Description
Where the harness exposes it, record the model that executed a stage on the receipt surface that already carries review provenance. Recording only - nothing prescribes, nothing fails.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (the stage-receipt and review-attempt writers), the receipt schema documentation in the docs tree
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/docs/**, .flow/bin/flowctl.py]

### Approach
- Extend the existing provenance rows rather than adding a second store. Review attempts already carry work-volume and head-origin fields; a stage's executing model belongs in the same shape.
- Absence is a first-class value: a harness that cannot report which model ran records unknown, never the configured or preferred value. Recording a preference as if it were an observation is exactly the fabrication this surface exists to prevent.
- No new verb and no new file. If it does not fit the existing receipt shape, stop and report rather than inventing a parallel record.
- Read-only consumers (the autonomous loop, the merge gate) must not change behavior because a new optional field appeared.

### Investigation targets
**Required** (read before coding):
- the review-attempt row writer and its optional-field conventions - absence means unknown, never zero
- the merge-gate and loop consumers of those receipts - the compatibility surface

### Acceptance
- [ ] Stage receipts record the executing model where the harness exposes it, unknown where it does not
- [ ] No new store, no new verb; existing consumers behave identically
- [ ] A preference is never recorded as an observation
- [ ] Focused suites green: review-attempt, receipt-schema and merge-gate tests

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
