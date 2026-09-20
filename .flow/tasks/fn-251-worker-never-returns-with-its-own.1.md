---
satisfies: [R1, R2, R3, R4]
---
# fn-251-worker-never-returns-with-its-own.1 Implement Worker never returns with its own commands still running

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The worker instructions now say a worker does not return while a command it started is still running, and that it inspects another tree state in a temporary worktree, never `git stash` (R1, R3). Work's Phase 3d, and the rolling scheduler's worker-return event by pointer to it, check task status and live commands before accepting a return; `in_progress` with a live command means wait and resume the same worker with no failed attempt counted (R2). `agent_docs/conduct/work.md` gained three checklist items covering the rules, the generated mirrors were regenerated, and an `## Unreleased` changelog entry was added (R4).

The spec enumerates no error case that code could exercise: every rule is prose, and no existing pinned test needed changing.

baseline: none (the spec defines no Quick commands); lint was green pre-edit and no test receipt existed for the base.

Follow-up, not built: `references/wave-join.md` is reached through Phase 3d and carries no sentence of its own for the check.

Tier: implementer = gpt-6-astra at medium (explicit invocation; reached over the codex CLI bridge)

stage: implement - ran (model: gpt-6-astra at medium; delegated: 0)
stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
## Evidence
- Commits: af602b82648146134ae3eef930ebca9e1cd0f726, 95687098ef2fa981eed2976fa3fa2c3f3dbff93a, 564375ec617d92a836fbefae24f684f0c8c789e9
- Tests: python3 scripts/run_tests_parallel.py (suite_rc=0; files=225 ran=5042 failures=0 errors=0 skipped=6), uvx ruff@0.16.0 check . (rc=0), PYTHONPATH=plugins/flow-next/tests python3 -m unittest test_foreground_rule_fences test_parallel_work_prose test_worker_anchor_prose test_work_reached_path_routes test_rolling_notes_pointer test_prompt_text_pinned (child-reported rc=0, 31 tests), ./scripts/sync-codex.sh twice (second run no-op; host re-ran once, no diff), python3 scripts/run_tests_parallel.py (5042 ran, 0 failures, exit 0, after review fixes), uvx ruff@0.16.0 check . (exit 0), python3 scripts/check_doc_anchors.py (exit 0)
- PRs: