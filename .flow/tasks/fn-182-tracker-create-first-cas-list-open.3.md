---
satisfies: [R3, R4]
---
# fn-182-tracker-create-first-cas-list-open.3 Linear provider: per-spec tracker.projectId / projectMilestoneId

## Description
Spec fn-182 item 3 (#315 option 1). Sidecar fields sent on issueCreate and reconciled on issueUpdate. Absent fields = byte-identical payload today AND reconcile never clears tracker-side membership (absent = unmanaged). Invalid project id surfaces the provider error. Smoke against the flow-next-smoke Linear sandbox where practical (LINEAR_API_KEY in env per keychain setup).

**Files:** plugins/flow-next/scripts/flowctl_tracker/providers/linear.py + dual copies + manifest regen; provider payload tests

## Acceptance
R3, R4 of the spec.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
