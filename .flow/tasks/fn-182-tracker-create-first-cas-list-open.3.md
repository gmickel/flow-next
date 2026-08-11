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
Linear per-spec Project per fn-182 R3-R4 (#315 option 1). Sidecar fields tracker.projectId/projectMilestoneId: spec_project_fields returns only present non-empty keys (absent/null = unmanaged, {} -> zero extra requests, create input dict byte-identical to pre-fn-182 by dict-equality test; present-but-unusable value = INVALID_INPUT, never a silent drop). Create side lands in lifecycle/providers.py create_linear IssueCreateInput (the actual payload builder - task Files line named providers/linear.py which builds no issue payload). Update side is a deliberate SIBLING wire.project_set issueUpdate called from the push path BEFORE the body branch so converged-body pushes still reconcile membership; none of the three body/status issueUpdate sites widened. Non-Linear tracker + sidecar present = capability error pre-request. R4: no projectId:null can ever be synthesized; project_set never called when sidecar empty. Live flow-next-smoke sandbox: create with projectId landed in the Project, sidecar removed + pushed -> membership unchanged (live R4 proof), issue deleted. Declined payload-extension seam honored. 14 new tests.
## Evidence
- Commits: 1334bf9b
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_project_sidecar -q (14 OK), 8 tracker suites (406 OK), test_tracker_distribution test_tracker_sync_mirror_parity + focused (50 OK), live Linear sandbox smoke (create/reconcile/R4/cleanup)
- PRs: