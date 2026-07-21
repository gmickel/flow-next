---
satisfies: [R1, R18]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.1 Post-fn-121 rebase audit and characterization ledger

## Description
Completed the hard rebase gate against flow-next 3.1.0 and its immediate post-release follow-up.

Rebased detached HEAD from audit base 3e658c00860e7c94e5ccfccbfc02512635970e80 through the release and tracker-close commits to current origin/main 2977125471dabc0ddb5ccebc0e3b73ee139f15c5 (release tag flow-next-v3.1.0 at a45c7631). Read fn-121's final spec/tasks and implementation delta.

Disposition is embedded in the parent spec. fn-121 added 176 flowctl.py lines for cmd_usage, cmd_setup_mode_set, and parser wiring; model cache and all other audited mechanisms were unchanged. The 29771254 follow-up only changes Grok bridge guidance/scaffolding, usage templates, Ralph docs-truth tests, and the Unreleased changelog; 28 focused tests pass and no flowctl.py assumption changes. Fresh reproductions confirmed task-create data loss (40 successes, 32 persisted, 8 lost, one artifact mismatch) and stale role-map intent (requested gpt-5.6-sol, cached gpt-5.5 dispatched). Full 3.1.0 gate passed 1,957 tests.

Refreshed warm medians and parser inventory are in the spec. Downstream plan changes: task .3 becomes a definite model-cache fix; task .4 adds plugin-bin, usage/setup-mode path semantics and a 0.224s usage target; task .6 replaces the unstable fixed percentage with deterministic/Pascal-heavy proof; tasks .10/.11 preserve and verify fn-121 plugin-mode/mirror surfaces plus corrected Grok bridge syntax.

Complexity: 45/100.

Verification:
- git rebase main
- python3 scripts/run_tests_parallel.py
- python3 -m unittest test_model_routing_scaffold test_ralph_docs_truth -q
- 40-process task-create reproduction
- stale role-pin/cache reproduction
- warm command benchmark and argparse inventory
- active-doc/dead-code/static path sweeps
## Acceptance
- [x] fn-121 is landed in the audited tree; its final spec/tasks and implementation diff have been read.
- [x] Every fn-122 audit finding has a disposition, fresh code anchor/structural check, retained/revised risk, and test implication.
- [x] Model-cache, launcher/runtime, parser/startup, usage-template, mirror, and active-doc assumptions are explicitly re-derived.
- [x] Fresh post-fn-121 timing and deterministic-operation baselines are recorded with reproducible commands.
- [x] Characterization gaps needed by downstream tasks are added or explicitly assigned.
- [x] This spec and task set are plan-synced for 3.1.0 reality.
- [x] No downstream implementation task started before this task completed.
## Done summary
Rebased the audit worktree from `3e658c00` through the 3.1.0 release to current `origin/main` at `29771254`. Re-audited fn-121 and its post-release follow-up, refreshed CLI inventories and warm baselines, ran the full 1,957-test gate plus the 28 follow-up-focused tests, and reproduced the concurrent task-loss and stale model-cache defects on the landed tree. Updated fn-122's requirements, task descriptions, formal dependency, compatibility surfaces, performance budgets, and final gates around the new plugin-bin, `usage`, `setup-mode`, usage-template, and corrected bridge contracts. No implementation task started.
## Evidence
- Commits:
- Tests: python3 scripts/run_tests_parallel.py: 1957 tests, 0 failures/errors, 3 skips, python3 -m unittest test_model_routing_scaffold test_ralph_docs_truth -q: 28 tests passed, 40-process task-create reproduction: 40 successes, 32 persisted, 8 acknowledged writes lost, JSON/Markdown mismatch confirmed, model-cache role-pin reproduction: requested gpt-5.6-sol, stale cached gpt-5.5 dispatched, warm launcher/command benchmark and post-3.1.0 argparse inventory
- PRs: