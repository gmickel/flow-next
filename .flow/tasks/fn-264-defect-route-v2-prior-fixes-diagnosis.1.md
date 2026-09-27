---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-264-defect-route-v2-prior-fixes-diagnosis.1 Implement Defect route v2: prior fixes, diagnosis, bisect, base vs head

## Description
TBD

## Acceptance
Every R-ID in the parent spec's Acceptance Criteria section is satisfied; judge this task against the spec's criteria directly.

## Done summary
The defect route now runs four ordered steps from a new gated work reference (plugins/flow-next/skills/flow-next-work/references/defect-route.md): prior-fix check, reproduce twice and diagnose with runtime evidence, bisect from a known-good revision, prove on base and head, plus a done-summary record that make-pr turns into shared PR proof cells. The worker reads it on both the standard and bridged paths. The route-matrix defect row, the judge's defect Next: wording, pipeline-variations, teams (stale diagnose-skill mention removed) and CHANGELOG Unreleased agree with it. A routing-accuracy rerun found no regression: 60/60 draws correct in both arms on the defect and neighbour items.

- Test: test_flow_routing.test_defect_route_reference_is_linked_from_its_readers (red on base, green on head)
- flow-next.dev: worktree /home/gordon/work/flow-next.dev-630, branch flow-next-6-3-0, commit 7722ef5 (7 pages; not pushed)
- agent-evals: worktree /home/gordon/work/agent-evals-wt/fn264-defect-route, branch study/fn264-defect-route-rerun, commits b90deba, 24c15cc, b58ed84 (NO REGRESSION; not pushed)
- Review focus "overengineering, slop, YAGNI" could not be passed: flowctl refuses --focus on task-scoped reviews
- baseline: green (full suite pre-edit, 5229 tests)
- GATE_SKIPPED:unittest:green-receipt 04f4cb77 - baseline reused from prior post-gate pass
- Follow-up (not built): the flow-next.dev changelog page is written at release time

Tier: session (jev intelligent 0.70)

stage: impl-review - ran (codex gpt-6-astra high; round 1 fan-out NEEDS_WORK with 2 findings fixed, round 2 SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 1195f57f6e2476493dc61417bb278011df28c48c, 04f4cb7739110fb479a616406281f33d49f174d7
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., GATE_SKIPPED:unittest:green-receipt 04f4cb77 - baseline reused from prior post-gate pass
- PRs: