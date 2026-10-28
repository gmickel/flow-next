---
satisfies: [R1, R2, R3, R4]
---
# fn-305-goal-runs-finish-without-a-review.1 Implement Goal runs finish without a review backend or child-PR waits

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Goal mode's final whole-diff review now takes the invocation's `--review=<backend>` and is skipped, with `skipped(config: review=none)` or `skipped(config: no review backend)` recorded, when the backend is `none` or `review-backend <goal-id>` reads `ASK`; previously it stopped the goal before the final PR (R1, R2: the flag was not forwarded to the final review). A goal run's authorization for a child PR into its `goal/<name>` integration branch now waives land's review-bot patience; the final PR keeps it (R3). Docs (flowctl config table and landing upgrade, orchestration, skills) and an Unreleased changelog entry match (R4). Codex mirror regenerated.

stage: impl-review - ran (model: gpt-6-astra) - SHIP, 3 reviewers (correctness, contracts, integration), no findings

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 6a37e08a282962e2ebba440096c22cf172b20e3c
- Tests: python3 -m unittest test_flow_auto test_flow_merge_destination test_codex_flow_dispatch test_pilot_backlog_mirror_safety test_land_config (39 OK); ./scripts/sync-codex.sh --check (0); review-backend on an unconfigured repo reads ASK
- PRs: