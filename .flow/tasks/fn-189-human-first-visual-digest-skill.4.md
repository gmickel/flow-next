---
satisfies: [R6, R7]
---
# fn-189-human-first-visual-digest-skill.4 Platform + listing surfaces: sync-codex, EXPECTED_COMMANDS, README, CLAUDE.md, guide, CHANGELOG

## Description
Full adding-skills checklist surfaces: (1) `scripts/sync-codex.sh`: `generate_openai_yaml` call in the utility section (amber #F59E0B, display name, short description, explicit `allow_implicit_invocation: false`); add `visual` to `REQUIRED_OPENAI_YAML_SKILLS`. (2) Run `./scripts/sync-codex.sh` TWICE - zero errors, second run idempotent; commit the regenerated `plugins/flow-next/codex/` mirror. (3) `plugins/flow-next/tests/test_command_shim_flatten.py`: add `visual` to EXPECTED_COMMANDS. (4) Root `README.md` commands table row. (5) `CLAUDE.md` command surface (the flow-next template block or command count, whichever this repo carries). (6) `plugins/flow-next/skills/flow-next-guide/SKILL.md` routing table: new row for starting state 'output too dense / want to review a plan, spec, or diff at a glance' -> `/flow-next:visual`. (7) CHANGELOG under `## Unreleased`: user-outcome-first entry (the review-at-a-glance outcome leads, machinery last). NO version bump.

## Acceptance
R6: yaml entry + REQUIRED array + double sync run green + mirror committed. R7: README row, CLAUDE.md surface, guide row, EXPECTED_COMMANDS entry, Unreleased CHANGELOG entry all present; `python3 -m unittest test_command_shim_flatten -q` green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
