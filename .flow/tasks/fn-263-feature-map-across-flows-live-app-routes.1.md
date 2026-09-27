---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-263-feature-map-across-flows-live-app-routes.1 Implement Feature map across flow's live-app routes

## Description
TBD

## Acceptance
Every R-ID in the parent spec's Acceptance Criteria section is satisfied; judge this task against the spec's criteria directly.

## Done summary
Every flow stage that drives the running app now reads the feature map the same way. That covers the slowness baseline and post-change measurement, the defect route's live proof on base and head, QA, and PR live checks. Each reads the index plus one matched file, never the whole map, even when the target names its page. All of them share one `resolved_feature` record: the spec line, then task done evidence, then the QA receipt, which newly carries the record through `qa receipt` using the same validator as `done`. The rule is one "Live-app stages" section in feature-entry-contract.md; the route matrix (slowness row), worker, defect-route, QA, drive and make-pr point at it. fn-261's intake gate is unchanged, and routes with no running app never read the map. flowctl gains no new command, only the optional QA receipt field. Tests: test_artifact_writers `test_qa_receipt_carries_a_valid_resolved_feature_only` covers a valid object, `unmapped`, and a malformed or null record rejected with the prior receipt kept. PR cell label changed from `Reproduced via` to `Resolved feature`.

Site docs: ~/work/flow-next.dev-630 branch flow-next-6-3-0, commits d9baf49 and 7294486 (not pushed).
baseline: green (python3 scripts/run_tests_parallel.py, 5230 tests pre-edit)

Tier: session (jev intelligent 0.79)
stage: impl-review - ran (codex gpt-6-astra high; round 1 fan-out refunded after a fix landed before finalize; round 2 fan-out NEEDS_WORK -> single re-review SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: de4a317a907543e96b6b0f5262c360a89b6b8b17, 49c270aa664fa42ceb1199fd635419e9c20e02b4, d909fef2f53f88f96b1d36013a8f349dbdb5cac7
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: