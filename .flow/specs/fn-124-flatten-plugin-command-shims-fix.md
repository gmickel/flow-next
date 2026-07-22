## Goal & Context

<!-- Source-tag breakdown: 80% [user], 20% [paraphrase] -->

Claude Code's slash menu renders flow-next command shims with duplicated namespace prefixes, e.g. `/flow-next:flow-next:flow-next:qa` (observed live 2026-07-22 on current Claude Code CLI). [user]

Three name layers stack: (1) shims live in a subdirectory `plugins/flow-next/commands/flow-next/*.md` and Claude Code treats the subdir as a namespace segment; (2) each shim carries explicit frontmatter `name: flow-next:qa` (pre-plugin-era literal names); (3) Claude Code prefixes the plugin name. The shims exist for non-Claude hosts - the Cursor manifest (`plugins/flow-next/.cursor-plugin/plugin.json`) points `commands` at `./commands/flow-next`. On Claude Code the skills are the invocable surface, so these entries are pure menu pollution. Predates fn-123; likely surfaced by a recent Claude Code namespacing change. [paraphrase]

## Acceptance Criteria

- **R1:** On current Claude Code, flow-next commands render without duplicated prefixes (target `/flow-next:qa` or the cleanest form current namespacing rules allow); no `flow-next:flow-next` entries remain except the inherent plugin-prefix + `flow-next` management-skill pairing. [user]
- **R2:** Current Claude Code command-namespacing rules are verified against release notes/docs first (subdir-as-namespace behavior); the chosen fix (bare frontmatter names, flattened dir, or both) is justified against them. [paraphrase]
- **R3:** Cursor commands keep working: manifest `commands` path updated in lockstep, `install-cursor.sh`/`.ps1` + `scripts/ci/verify_cursor_install.py` + tests (`test_install_cursor_parity`, `test_cursor_plugin_surface`, `test_cursor_review_commands`) updated and green. [paraphrase]
- **R4:** `scripts/sync-codex.sh` run twice stays idempotent; Codex mirror unaffected or regenerated cleanly. [paraphrase]
- **R5:** No version bump; CHANGELOG entry staged under `## Unreleased`. [paraphrase]

## Boundaries

- Do NOT change skill names or the skills surface - command shims only. [paraphrase]
- Coordinate with fn-123 (Cursor manifest component paths landed there); rebase on main after fn-123 merges before implementing. [user]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-N.M (TBD - populate via /flow-next:plan) |
| R2 | fn-N.M (TBD - populate via /flow-next:plan) |
| R3 | fn-N.M (TBD - populate via /flow-next:plan) |
| R4 | fn-N.M (TBD - populate via /flow-next:plan) |
| R5 | fn-N.M (TBD - populate via /flow-next:plan) |
