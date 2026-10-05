---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-283-review-failures-name-their-cause-a.1 Implement review failure cause, stale plan SHIP, queued merge

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
No-verdict CLI reviews now record and print the CLI's own last error text (`CLI message:`; codex error/turn.failed event, else last output line, else last stderr line, bounded at 300 chars) and the three review skills stop on a usage, credit or spend limit instead of retrying (#515). `spec set-plan` marks a `ship` plan review `stale` on a body change under the sidecar lock, the route judge sends stale specs to `plan_review`, work stops on stale at any task count, refine names plan-review after changing a planned spec, and land reports `QUEUED` for an enqueued merge (#514, #516).

Tests: test_review_convergence_cap (message per backend, stderr fallback, sandbox line, TRANSPORT_UNHEALTHY), test_review_fanout (draw result + every-draw-failed line), test_task_create_files (stale only on changed ship), test_judge_route (stale routing, unknown unchanged), test_flow_merge_destination (QUEUED wait). Each was red on 049ab77b and green on head. Full suite: 214 files, 3958 tests, 0 failures (run once before the fix pass; focused suites re-run after it). Help snapshot unchanged under python3.14; manifest and Codex mirror regenerated and --check fresh; doc anchors and ruff clean.

Decisions: the host `review-rounds record` path is not a CLI reviewer and records no message. The maintainability pointer's set-plan write on a SHIP round restores `ship` via set-plan-review-status, so plan-review's own advisory line never stales its fresh SHIP. The stale test uses the plan review artifact's normalization, so a stale spec is never refused as unchanged.

Follow-ups (not fixed): `docs/architecture.md` still says the host `review-rounds record` CLI carries no `--model` flag (stale since #513). The comment in `cmd_spec_set_plan` calls the plan JSON stamp "unlocked", though `_apply_spec_plan_writes` holds the sidecar lock.

Tier: session (jev intelligent 0.68)

stage: impl-review - ran (codex fan-out NEEDS_WORK: 2 merged findings fixed in 20f57eb2; re-review SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 03ae8e173400768d09a5f65be2fcacca3fce8640, 20f57eb2795fdf42a1f9df56a8056c3fe3474952
- Tests: python3 scripts/run_tests_parallel.py, python3 scripts/run_tests_parallel.py --pattern test_review_convergence_cap.py (and test_review_fanout, test_task_create_files, test_judge_route, test_flow_merge_destination), uvx ruff@0.16.0 check ., python3 scripts/check_doc_anchors.py, bash scripts/sync-codex.sh --check
- PRs: