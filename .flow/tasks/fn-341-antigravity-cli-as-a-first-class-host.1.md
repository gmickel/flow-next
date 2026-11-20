---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-341-antigravity-cli-as-a-first-class-host.1 Implement Antigravity CLI as a first-class host and a driven target

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Antigravity CLI support through an installer-built bundle. `scripts/install-antigravity.sh` builds a native bundle with `lib/antigravity_bundle.py` (agent models mapped to tiers, `disallowedTools` rewritten as a `tools` allowlist, commands as hidden stub skills, the rule as `rules/AGENTS.md`, a detection marker; named fail-closed errors for unmapped models, tools and unsupported field forms), installs it with `agy plugin install`, and validates the installed copy. Setup detects the marker beside the Muse rung and writes `AGENTS.md`; flowctl host evidence and `setup-status` accept `antigravity`. Platforms docs, the usage guide's agy bridge recipe and a read-only agy review wrapper for `command:<label>` record what was verified live on Antigravity CLI 1.5.13 (install, dispatch tool lists, stub commands, setup, plan with scouts, two-task work with worker commits and codex receipts, the bridge deny rules and the wrapper's fresh, resumed and unknown-id paths).

stage: impl-review - ran [3 rounds: NEEDS_WORK, NEEDS_WORK, SHIP] (model: gpt-6.2-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 896c34a9eae7004749cc8ea0d88962d57565aff6, 86fde8ce8950946b96369865b6a935b5f0106c70, b4e07cd3df66fbc1ca78d9fe4807de76add4c206
- Tests: python3 scripts/run_tests_parallel.py; python3 -m unittest test_install_antigravity test_setup_grok_host test_install_opencode test_setup_status test_cmd_usage
- PRs: