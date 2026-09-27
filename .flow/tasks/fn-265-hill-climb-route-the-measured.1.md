---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-265-hill-climb-route-the-measured.1 Implement Hill-climb route: the measured improvement loop

## Description
Implement the hill-climb route as the spec describes (whole-spec implicit task).

Review focus (maintainer steering): overengineering, slop and YAGNI. Prefer prose over machinery; flowctl gains no statistics engine. Flag anything built past the spec's R-IDs.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Work now runs a measured hill-climb loop on specs that carry a `## Hill-climb pre-registration` section or whose goal is one metric moved toward a target. The loop lives in a new gated reference, `flow-next-work/references/hill-climb.md`, which the worker reads (Phase 1.5) or names for the bridged child (Phase 1b). It covers the nine-label pre-registration, harness proof and freeze, interleaved measurement, the keep rule, the ledger, the stop rules, a verify step before done, the done-summary record and a worked example. The route matrix's hill-climb route cell points at the loop, make-pr maps the `Hill climb:` block to proof cells, pipeline-variations describes the loop, and CHANGELOG has an Unreleased entry. R8 is proven on a fixture CLI (`tests/fixtures/hill-climb-cli/`): a recorded run, a ledger, a harness proof and the three kept diffs. `test_hill_climb_fixture.py` replays those diffs and checks the ledger and the pre-registration labels.

- Tier: session (jev intelligent 0.71) - explicit override: implementer opus 5.5
- Routing literals: the starting-state, signal and skip cells and every judge literal are unchanged; only the route cell changed. The routing-accuracy study (agent-evals routing-accuracy-2026-09) was not rerun, for two reasons. Its 27 items include no hill-climb case, and the kind-classification text the judge sends is unchanged.
- Spec reconciliation: the Architecture line "a simplification that holds the number may be kept" conflicts with R3's keep rule. R3 governs, so a simplification that holds the number is not kept.
- Budget-exhausted path: the worker records in the task description that the target's R-ID is `partial` by the pre-registered budget. Review's coverage gate forces NEEDS_WORK only on `not-addressed`, so a SHIP on the kept commits reaches done and make-pr with the target shown unverified.
- flow-next.dev: the loop, the PR cells and the worked example are committed on branch fn-265-hill-climb-route-the-measured in the worktree /home/gordon/work/flow-next.dev-fn-265 (commit 8b3a91d, based on origin/main 49acc34). It is not pushed. `astro build`, the link check and the markdown-export tests passed. An untracked `node_modules` symlink I created for the build remains in that worktree because the guard blocked removing it.
- Follow-up (not built): capture has no hint to draft the pre-registration section. Specs get it from the author, refine, or work's missing-field question.

Fixture run (R8): `--version` cold start went from 124 ms to 8 ms over 5 attempts: 3 kept, 1 reverted, 1 inconclusive. The run stopped with the target met and the attempt floor reached. The artifacts are in `plugins/flow-next/tests/fixtures/hill-climb-cli/run/`.

Tests: test_hill_climb_fixture.py covers the ledger rows against the kept diffs, replay plus the regression gate, harness rejection of a wrong output, and pre-registration label parity. The extended test_flow_routing gated-reference link test covers the route-matrix and worker links. Full suite green (5235 tests); ruff clean; codex mirror fresh.

stage: impl-review - ran (codex gpt-6-astra high: fan-out NEEDS_WORK with 3 findings, then re-review NEEDS_WORK with 1, then SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 8241e618c883d98518dc47008d25cc328d9b31a9, 4665acdc4b264b418059d40b5a5c7f39580b36e4, 6f46bf3ec443d77adb16146e00df95b0f250d6f0, f8e4eb4caf719dda13e2aefdf1b9fa5c51002d72, 1412403b77f108f42b426279593610ee0f296570
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, hill-climb fixture ledger: 5 attempts (kept 3, reverted 1, inconclusive 1); 124 ms -> 8 ms
- PRs: