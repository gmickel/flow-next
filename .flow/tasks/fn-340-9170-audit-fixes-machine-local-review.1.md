---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-340-9170-audit-fixes-machine-local-review.1 Implement 9.17.0 audit fixes: machine-local review commands

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Fixed the nine confirmed 9.17.0 audit findings.

- R1/R3: the command backend's argv comes only from the machine-local `FLOW_REVIEW_COMMAND_<LABEL>` JSON array (label upper-cased, `-` as `_`). A `review.commands` key in config is refused, naming the variable. Labels are `[a-z0-9_-]+` in runtime and schema alike. A leading `~` expands in every element. The program is fixed before dispatch: a bare name from PATH (refused when it is not found), a relative path from home. A program inside the checkout, or a checkout symlink, is refused. On Windows a `.cmd`/`.bat` program is refused after resolution. Values that are NUL-bearing, unencodable or nested too deep are refused before any round. Errors name the variable and label, never the value. The command starts in the home directory.
- R2: `review.commands` is gone from the schema and generator. Setup, the three review skills, flowctl.md (with an interpreter-first example and no `#!` dependence), orchestration.md, the CHANGELOG, the conduct checklists and the Codex mirror all describe the variable. Help, the bootstrap hash and the manifest are regenerated.
- R4: `--spec command:<label>` rides the fan-out and re-reviews on SKILL.md, other-paths.md (`workflow-cli.md`) and `fix-pass.md`.
- R5: plan review accepts a bare `--review=command`.
- R6: drift reads only a plan row whose status leg completed (legacy rows without the leg still count).
- R7: in `flow --auto`, a drift-routed plan-review hop advances only when `plan_review_drift` reads empty afterwards.
- R8: the CHANGELOG states the post-upgrade drift check for CLI-reviewed SHIP specs.
- R9: the teams guide adds the command backend, which depends on the wrapper.
- R10 (live, measured on final code 49b8dc1fc): the docs wrapper ran through `opencode run` on `xai/grok-4.7` in a disposable fixture with `FLOW_REVIEW_COMMAND_GROK` set. Receipt: `mode: command`, `label: grok`, `model: xai/grok-4.7`, verdict SHIP. With a tracked `review.commands` and no variable, flowctl exited 2 naming `FLOW_REVIEW_COMMAND_GROK`, wrote no receipt, and the tracked argv never ran.

stage: impl-review - ran (model: codex gpt-6.2-sol medium). Panel rounds 1 and 2 were dispatched, but their fixes were committed before finalize, so flowctl refused those rounds and refunded them. Round 3 was finalized NEEDS_WORK; the fixes followed and the single re-review returned SHIP.
Declined: label whitespace (the spec grammar trims it for every backend); argv[0] in spawn errors (the spec allows what fn-337 already recorded).

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: a815549b73fd82fcec0dec0c9e4a4393c0890f98, e90d7181e61e3235ac6d90cd40cd85e11d80318c, 33818150e33f7a6b2d08de06a19e7f8ac1bde339, b34f4835beec1490ae55120c7e8843cc5042ae8f, 3db94bf9a308961b7d6acec9962b4598804b7350, 30d3f098b565a6a9bcce348fcf46cb62e273a2bb, e77b5671ff4ae34c292688df7d10f6f47e4a524c, fb40725390b38ca16cec98a416de78198cc0b9df, 49b8dc1fcf72d7b0fb29e9e3024ce6b2dcdc7f4c
- Tests: python3 scripts/run_tests_parallel.py --pattern 'test_*review*.py' (695 pass); python3 -m unittest test_command_review_backend test_plan_review_drift test_backend_spec test_startup_bootstrap test_flow_config_schema test_flow_config_schema_drift; R10 live command review via opencode xai/grok-4.7
- PRs: