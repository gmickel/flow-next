# fn-197-copy-less-installs-resolve-flowctl-from.5 Docs sweep: retire the dual-mode story from every in-repo doc

## Description
**What:** In-repo docs sweep — the dual-mode story disappears; the documented world is copy-less with a one-line "you can delete old copies" migration note.

**Details (all under `plugins/flow-next/docs/` unless noted):**
- `platforms.md` (13 sites — the biggest): delete the plugin-vs-copy comparison table (~lines 43-45) and rewrite the Cursor, Grok, and Windows sections around the three-rung chain. Each host section states: install once, `/flow-next:setup` once per repo (snippet + config), done. One migration note: repos with old `.flow/bin` copies can delete them.
- `troubleshooting.md` (4 sites): "flowctl not found" remedies point at the chain and install verification, not at copying.
- `flowctl.md` (9 sites): update the CLI-location prose, CI recipe framing (~182-188 stays — user-created file, unrelated), gate cleanliness notes (~1952, 1963) reworded now that `.flow/bin` is historical.
- `architecture.md` (2), `spec-template.md` (3 — drop tier-3 `.flow/templates/spec.md` from the cascade; also fix `references/spec-template-discovery.md:10,38-39`, `templates/spec.md:51`, `skills/flow-next-plan/steps.md:366`, `skills/flow-next-capture/workflow.md:220`), `orchestration.md` (3), `running-lean.md` (1), `memory-schema.md` (1), `ralph.md` (1), `README.md` (1).
- `agent_docs/setup-modes.md`: rewrite wholesale — there is one mode; keep a short history note for contributors.
- `scripts/install-cursor.sh` + `scripts/install-codex.sh` next-steps echo text: drop "writes .flow/bin/flowctl" phrasing; setup now = snippet + config only.
- CHANGELOG entry (register gate): behavioral, user-visible — copies retired, delete-safe migration, one-mode setup. No benchmark numbers, no speed claims, no external attribution.
- Grep-based exit criterion: `grep -rn "\.flow/bin" plugins/flow-next/docs plugins/flow-next/templates plugins/flow-next/skills plugins/flow-next/commands plugins/flow-next/rules agent_docs` returns only (a) the preamble rung-3 line, (b) the migration/leftover-cleanup prose, (c) deliberate history notes.

**Touches:** plugins/flow-next/docs/**, agent_docs/setup-modes.md, plugins/flow-next/templates/spec.md, plugins/flow-next/references/spec-template-discovery.md, plugins/flow-next/skills/** (doc lines), scripts/install-cursor.sh, scripts/install-codex.sh, CHANGELOG.md, plugins/flow-next/codex/** (regenerated)
## Acceptance
- [ ] The grep exit criterion holds: every remaining `.flow/bin` mention is the rung-3 preamble line, migration prose, or a marked history note.
- [ ] `platforms.md` has no mode table; Cursor/Grok/Windows sections describe the chain and the install-once story.
- [ ] Spec-template cascade documented (and prose-implemented) as three tiers: repo-root SPEC.md/spec.md → bundled template; no `.flow/templates` tier anywhere.
- [ ] `agent_docs/setup-modes.md` describes one mode.
- [ ] Install scripts' next-steps text matches the new setup behavior.
- [ ] CHANGELOG entry present and register gate passes.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
