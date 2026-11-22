---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-349-split-flowctl-usage-specs-json-carries.1 Implement Split flowctl usage; specs --json carries dependencies

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Split `flowctl usage`: `templates/usage.md` keeps the CLI cheatsheet and lifecycle workflow (4.2 KB, from 17.8 KB); the bridge and model-steering recipes moved unchanged to `templates/usage-orchestration.md`, printed by `flowctl usage --orchestration` through flowctl.py. Plain usage keeps an `## Orchestration & model steering` heading pointing at the new command, so pre-split instruction blocks still resolve. Pointers in the setup snippets, the Cursor rule, the work skill's bridge references, the setup summary, Codex sync, repo instructions, agent_docs and runtime docs are updated; help text, hash, manifest and Codex mirror regenerated.

`flowctl specs --json` adds `depends_on_epics` per spec; `flow-next-deps` gathers its graph from that one call (the unused `plan_review` field dropped) and its conduct checklist matches.

Review fix (a6dbb160d): the launchers send only single-argument calls to the bootstrap, so its `usage --orchestration` branch was unreachable; the bootstrap is back to main apart from the help hash, and flowctl.md and the tests are corrected.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: caae97f48, a6dbb160d
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, python3 scripts/gen_tracker_manifest.py --check, all 9 plugins/flow-next/scripts/*smoke_test.sh (run outside the repo), python3 -m unittest tests.test_cmd_usage tests.test_startup_bootstrap tests.test_usage_stages tests.test_spec_dep_cycles
- PRs: https://github.com/gmickel/flow-next/pull/648