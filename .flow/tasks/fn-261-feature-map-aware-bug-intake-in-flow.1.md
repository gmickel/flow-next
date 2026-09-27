---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-261-feature-map-aware-bug-intake-in-flow.1 Implement Feature-map-aware bug intake in /flow-next:flow

## Description
TBD

## Acceptance
Every R-ID in the parent spec's Acceptance Criteria section is satisfied; judge this task against the spec's criteria directly.

## Done summary
Flow's defect route now reads the feature map: an existence-gated reference (references/defect-intake.md) resolves a bug report or screenshot to one mapped feature by Surface + sub-feature, drives the reproduction along that file, files drift notes on stale routes, and records a validated `resolved_feature` (or `unmapped`) that travels spec -> `flowctl done --resolved-feature` -> cognitive-aid export, where QA and make-pr read it. test_resolved_feature_evidence.py covers the valid, unmapped, malformed, range, export and contract-parity cases.

R5 study (agent-evals branch study/defect-intake-map-2026-09, commit 23045c0, not pushed): 48 draws, sonnet-5, 24/24 success in both arms, 9.2% fewer turns with the map, under the pre-registered 10% bar, so INCONCLUSIVE; screenshot reports -49% turns, vague reports +35%. R5's speed claim is therefore not demonstrated; changelog and docs state the result as inconclusive. Follow-up hypothesis (needs its own preregistration): read the map only for screenshot or where-is-it reports.

Docs: flow-next.dev commit 701ed3c on fn-262-feature-map-stays-current-and-is-always (not pushed).
G1: always-loaded growth is one gate bullet (flow workflow.md) and one sentence each in worker.md, QA workflow 1.3 and make-pr pr-cognitive-aid.md; each is the only place its stage writes or reads the record.

Tier: session (jev intelligent 0.83)
stage: impl-review - ran (codex fan-out, 3 draws SHIP, rid 57b6093d79fb437288965020871c1d3d)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: dace107a71065492a5657cbb6ebafb0c961bde48
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: