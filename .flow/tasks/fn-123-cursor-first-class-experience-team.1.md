---
satisfies: [R1, R2, R9, R11]
---
# fn-123-cursor-first-class-experience-team.1 Cursor marketplace + validated plugin surface + rules rail

## Description
Ship the Cursor marketplace + validated plugin surface. Add root `.cursor-plugin/marketplace.json` (alongside `.claude-plugin/marketplace.json`) listing flow-next with `source` at `plugins/flow-next`. Expand `plugins/flow-next/.cursor-plugin/plugin.json` with explicit `skills`, `agents`, `commands`, and `rules` component paths so repo-sourced marketplace installs never auto-discover `codex/` mirror skills or `tests/`. Add `plugins/flow-next/rules/flow-next.mdc` (Cursor-native guidance rail: flowctl lifecycle commands + the two `flowctl usage` pull directives - Cursor analog of the fn-121 slim snippet; copy-mode `.flow/bin/flowctl` resolution retained). Extend `scripts/ci/verify_cursor_install.py`; add `plugins/flow-next/tests/test_cursor_plugin_surface.py`; extend `test_install_cursor_parity.py` and `.github/workflows/test-flow-next.yml` triggers. Validate manifests against Cursor's official schemas (verify-first: https://github.com/cursor/plugins/blob/main/schemas/{plugin,marketplace}.schema.json - live as of 2026-07-22).

NOTE (from plan review): path overrides do NOT remove `codex/` from a marketplace-imported install dir - they only stop component discovery. Host detection with `codex/` PRESENT is task 4's problem; do not add exclusion assumptions here.

## Acceptance
- Root marketplace.json imports `plugins/flow-next` as the sole plugin source; no public-marketplace submission metadata or workflow added.
- plugin.json explicitly exposes only canonical skills, agents, commands, and `rules/flow-next.mdc`; `codex/` and `tests/` remain undiscoverable as components.
- `flow-next.mdc` carries the flowctl task lifecycle + `flowctl usage` pull directives; resolves flowctl via `.flow/bin/flowctl` (no plugin-root/PATH assumptions).
- CI parses both manifests, resolves every declared component path, and requires non-empty `name` and `description` frontmatter on every skill, agent, and command.
- Install smoke verifies rule + component trees complete and excluded payloads absent; `.cursor-plugin/**` changes trigger the test workflow.
- NEEDS-HUMAN CHECKPOINT (do not self-attest): manual Cursor Teams smoke by the maintainer - repo import succeeds, install under Default On and Required modes, auto-refresh after a pushed change. Record evidence in the task summary.


## Done summary
Root .cursor-plugin/marketplace.json (team-marketplace repo import); plugin.json component path overrides (skills/agents/commands/rules); rules/flow-next.mdc guidance rail; verify_cursor_install.py + new test_cursor_plugin_surface (21 tests) + parity test + CI triggers. Grok-implemented; reviewer fix applied: alwaysApply true->false with trigger-shaped description (plugin rules with alwaysApply:true inject into every workspace incl. non-flow repos) + test locked to false. Manual Teams import/install-modes/auto-refresh smoke REMAINS OPEN (needs-human).
## Evidence
- Commits: f732bcaf
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_cursor_plugin_surface test_install_cursor_parity -q
- PRs: