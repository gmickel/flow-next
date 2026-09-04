---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-218-rolling-frontier-becomes-the-work.1 Implement Rolling frontier becomes the work skill's default scheduler

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Rolling frontier is now `/flow-next:work`'s default scheduler. Phase 3 decides the route once from spec state: rolling unless plan-sync is on, the spec has fewer than two open tasks, or no two open tasks are dependency-independent; the decision prints as `Scheduling: rolling | wave (<reason>)`. The scheduler reference moved to `skills/flow-next-work/references/rolling-scheduler.md`, loaded only on the rolling route, with its beta-only plan-sync serial mode and no-plan refusal deleted (the route owns both). The `flow-next-work-rolling` skill, its command shim, the guide's experimental-variant route, the sync-codex mirror entries and guard rows, the conduct checklist (folded into `conduct/work.md`), and the count enumerations (28 commands, 32 skills) are removed; no alias. Repo docs describe rolling as the default and the wave route as the fallback; CHANGELOG carries Unreleased Changed + Removed entries. Codex mirror regenerated twice (idempotent), full parallel suite and ruff green.
## Evidence
- Commits: fdf89091a89bf5c0942e6c7e0ae3bea90cd3c8d6
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_work_reached_path_routes test_command_shim_flatten test_skill_prose_diet test_skill_prose_flowctl_surface test_chart_docs_inventory test_chart_skill_contract -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh && ./scripts/sync-codex.sh
- PRs: