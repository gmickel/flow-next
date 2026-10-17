---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-299-worker-reasoning-effort-follows-the.1 Implement Worker reasoning effort follows the dispatch tier

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Worker reasoning effort now follows the dispatch tier: `flowctl judge --preset tier --task` takes the host's effort levels and default (`--effort-levels`, `--default-effort`) plus `--explicit-effort` / `--role-effort`, returns `spawn_effort` (one level below the default for a confident mechanical answer, one above for a confident intelligent one, the default otherwise and without a judge), carries it as `<model> at <effort>` for a bridged implementer, and names the effort applied or why not on the `Tier:` line; scouts are unchanged. The judge-tier recipe, multi-task 3c (and its Codex SECTION3C copy), worker-bridge, judge/flowctl docs, the Claude Code and Codex reach pages, and the changelog state the behaviour.

Tests: `test_judge_consumers.py` covers R1 bounds and floors, R2 precedence (requested, role pin, explicit model keeps tier effort), R3 no-judge default, R4 not-applied lines and bridge transport, R5 line text, and the CLI path without a key.

Decisions: the 0.8 confidence floor that gates the model tier gates effort in both directions (an intelligent answer below 0.8 keeps the default). A requested effort covers the invocation and, below it, the routing block's implementer line; the conductor resolves which, per routing precedence. A role-pinned effort applies only to a native spawn. A rejected level is retried once without effort (conductor prose); flowctl cannot observe the rejection.

OPEN_ITEM: R6 evidence is partial. Worker replay (claude-opus-5-5, 3 judge-confident mechanical fixtures x 5 reps per arm): pass rate 15/15 at low vs 15/15 at medium; mechanical medians 55.0/43.0/130.9 s vs 76.1/67.2/138.0 s, but the pre-registered paired verdict is INCONCLUSIVE (pooled gap 10.0 s against a 9.7 s floor, within-cell spread 29-88 s). End-to-end large-feature control (3 draws each, same time): review rounds median 2 vs 2, wall median 1,886 vs 1,992 s, all hidden checks pass, but null by construction: no draw spawned a worker or made a tier call. Only about 1% of historical tasks are judge-confident mechanical and 2% intelligent. Whether to accept this or run a multi-task `--auto` study on Claude Code 2.1.296+ is the maintainer's call.

Follow-up: the end-to-end harness pins Claude Code 2.1.283, whose Agent spawn has no effort parameter; an opt-in `FN271_CLAUDE_DIR` override was added there, uncommitted.

stage: impl-review - ran (codex, 3 rounds: NEEDS_WORK -> NEEDS_WORK (R6 only) -> SHIP)

Tier: session (jev intelligent 0.63) (model: claude-opus-5-5)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: bb9f1a8673f13ef6f8be7295e8609de76270a967, 3fca663b35a42f7de00fb1af06019858a40efc01, 8f3b80b770ae9e34e09e9ba47bd358f904132fad, bdbafacbe99588d3c98038ac17dc61b49597969f
- Tests: python3 -m unittest plugins/flow-next/tests/test_judge_consumers.py, python3 -m unittest plugins/flow-next/tests/test_work_reached_path_routes.py plugins/flow-next/tests/test_tracker_caller_execution.py plugins/flow-next/tests/test_review_convergence_journal.py plugins/flow-next/tests/test_startup_bootstrap.py, ./scripts/sync-codex.sh --check, uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/tests/test_judge_consumers.py
- PRs: