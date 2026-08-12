---
satisfies: [R6, R7]
---
# fn-189-human-first-visual-digest-skill.4 Platform + listing surfaces: sync-codex, EXPECTED_COMMANDS, README, CLAUDE.md, guide, CHANGELOG

## Description
Full adding-skills checklist surfaces: (1) `scripts/sync-codex.sh`: `generate_openai_yaml` call in the utility section (amber #F59E0B, display name, short description, explicit `allow_implicit_invocation: false`); add `visual` to `REQUIRED_OPENAI_YAML_SKILLS`. (2) Run `./scripts/sync-codex.sh` TWICE - zero errors, second run idempotent; commit the regenerated `plugins/flow-next/codex/` mirror. (3) `plugins/flow-next/tests/test_command_shim_flatten.py`: add `visual` to EXPECTED_COMMANDS. (4) Root `README.md` commands table row. (5) `CLAUDE.md` command surface (the flow-next template block or command count, whichever this repo carries). (6) `plugins/flow-next/skills/flow-next-guide/SKILL.md` routing table: new row for starting state 'output too dense / want to review a plan, spec, or diff at a glance' -> `/flow-next:visual`. (7) CHANGELOG under `## Unreleased`: user-outcome-first entry (the review-at-a-glance outcome leads, machinery last). NO version bump.

<!-- Updated by plan-sync: fn-189-human-first-visual-digest-skill.2 confirmed the pre-existing full-suite failure this task closes -->
(8) `test_chart_docs_inventory.py` (`ChartRegistryCounts.test_counts_match_filesystem_and_registries`) pins exact skill/command/slash-command/phrase counts and the literal snippet `"25 commands, 29 skills"` across `.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`, plus count phrases in `docs/skills.md`, `docs/README.md`, and root `README.md`. Task .1's new `flow-next-visual` skill dir (and this task's new `visual` command shim) moved every one of those numbers by one - bump the pinned integers/snippets in `test_chart_docs_inventory.py` alongside the registry/doc files themselves in this task, or the full suite stays red on an unrelated-looking count assertion (confirmed red at task .2's baseline, caused by task .1, closed here per task .2's done summary).

## Acceptance
R6: yaml entry + REQUIRED array + double sync run green + mirror committed. R7: README row, CLAUDE.md surface, guide row, EXPECTED_COMMANDS entry, Unreleased CHANGELOG entry all present; `python3 -m unittest test_command_shim_flatten -q` green. Also green: `python3 -m unittest test_chart_docs_inventory -q` (registry/doc skill+command counts updated for `flow-next-visual` / `visual`).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
