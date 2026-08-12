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
Landed every platform + listing surface for `/flow-next:visual`: the sync-codex `generate_openai_yaml` call (utility amber `#F59E0B`, explicit `allow_implicit_invocation: false` per R6) plus `REQUIRED_OPENAI_YAML_SKILLS`, the regenerated Codex mirror, the skill/command count bumps to `26 commands, 30 skills` across every pinned surface, the guide routing row, the CLAUDE.md where-to-look row, and a user-outcome-first `## Unreleased` CHANGELOG entry (no version bump).

Closed both known red gates: `test_chart_docs_inventory` (30 skills / 26 commands / 25 slash-skills / snippet + docs phrases, plus the sibling pin in `test_chart_skill_contract`) and the `sync-codex.sh` validation error (`flow-next-visual has no explicit allow_implicit_invocation`). `./scripts/sync-codex.sh` now exits 0 twice with an identical working-tree file set.

Notes:
- `allow_implicit_invocation: false` is the spec's call (R6). It keeps visual's trigger-rich description out of Codex's shared skills catalog budget, which is why it needs no DIET entry; it stays reachable via `/flow-next:visual` and `$flow-next-visual`. A comment in sync-codex.sh states the rationale next to the call.
- Root README has no commands *table* any more (prose since the front-door rework), so the `visual` entry landed in the Commands prose enumeration alongside the count bumps. Repo CLAUDE.md carries neither a command list nor a count, so its surface is the "Where to look" table.
- The commit also carries a conductor-owned plan-sync edit to `.flow/tasks/fn-189-...3.md` that was already in the working tree (swept in by `git add -A`, per conductor instruction).
- Task .5 still owns `test_visual_skill.py` (R9); the spec's Quick command naming it is expected to be unresolvable until then.

baseline: red (`test_chart_docs_inventory` count pin, inherited from task .1 at base commit 4ac591fa; `test_visual_skill` module absent, owned by task .5) - both resolved or accounted for; full suite is green at HEAD.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)
## Evidence
- Commits: 1959949dcdc901de0ba13767d9013ee2ae5d2621
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_command_shim_flatten test_chart_docs_inventory test_chart_skill_contract -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (run twice, rc=0 both, identical file set)
- PRs:
stage: plan-sync - ran (no drift; no editable downstream tasks, verify-only)
