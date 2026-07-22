---
satisfies: [R5]
---

## Description

Update all live docs and manifest descriptions that reference the old nested shim path or the 24-command count, and stage the CHANGELOG entry under `## Unreleased`. No version bump (batched-release rule).

**Size:** S
**Files:** `plugins/flow-next/docs/platforms.md`, `plugins/flow-next/docs/strategy.md`, `agent_docs/adding-skills.md`, `plugins/flow-next/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`

## Approach

- `agent_docs/adding-skills.md:7` - highest priority: the authoring instruction "Slash command at `plugins/flow-next/commands/flow-next/<name>.md`" must point at the flat path or every future skill lands in the wrong place.
- `plugins/flow-next/docs/platforms.md:208` - Grok section "22 `commands/flow-next/*.md` wrappers": fix path AND count (23 after epic-review deletion; 22 was already stale).
- `plugins/flow-next/docs/platforms.md:237,241` - Cursor install section: rewrite the "nested `commands/flow-next/` path-override" prose to describe the flat `./commands` path.
- `plugins/flow-next/docs/strategy.md:58` - jargon-scan prose references `commands/flow-next/strategy.md` -> flat path (keep in sync with the ci_test.sh:440 change from task .1).
- Manifest counts, descriptions only (NO version fields): `plugins/flow-next/.claude-plugin/plugin.json:4` and `.claude-plugin/marketplace.json:14` "24 commands" -> "23 commands". Check `.codex-plugin/plugin.json` for a similar count string.
- Re-grep `commands/flow-next` across `docs/`, `agent_docs/`, `README.md`, `plugins/flow-next/` (excluding codex mirror regen artifacts and historical CHANGELOG prose) for any stragglers.
- `CHANGELOG.md`: add `## Unreleased` entry (fix: flattened command shims, de-prefixed frontmatter, Cursor manifest + Codex installer paths, epic-review alias removed on all platforms). Match existing register. Do NOT run `scripts/bump.sh` or touch version manifests.

## Investigation targets

**Required:**
- `plugins/flow-next/docs/platforms.md:200-250` - Grok + Cursor sections
- `agent_docs/adding-skills.md` - step list for new skills
- `CHANGELOG.md:1-40` - Unreleased-entry conventions

## Acceptance

- [ ] No live doc (docs/, agent_docs/, README, skills prose, strategy.md) references `commands/flow-next/`; historical CHANGELOG prose and optimization/ fixtures untouched
- [ ] platforms.md wrapper count/path and Cursor manifest description match the new layout
- [ ] plugin.json + marketplace.json descriptions say 23 commands; no version fields changed
- [ ] CHANGELOG entry staged under `## Unreleased`; no version bump anywhere

## Done summary
Swept all live docs and manifests for the flattened command-shim layout: adding-skills.md authoring path, platforms.md Grok wrapper count/path (23 commands/*.md) and Cursor manifest prose (flat ./commands), strategy.md jargon-scan path, teams.md adoption-ladder count, plugin.json + marketplace.json descriptions (24 -> 23 commands, no version fields), and staged the fn-124 CHANGELOG entry under ## Unreleased with no version bump. Impl-review (codex): SHIP first pass.
## Evidence
- Commits: a36ff8662b733db5ac9854ac9e085f57e12f5230
- Tests: baseline: green - python3 -m unittest test_install_cursor_parity test_cursor_review_commands test_cursor_clean_tree test_model_routing_scaffold test_no_default_hooks test_cursor_plugin_surface -q (72 tests OK, pre-edit), python3 -m unittest test_install_cursor_parity test_cursor_review_commands test_cursor_clean_tree test_model_routing_scaffold test_no_default_hooks test_cursor_plugin_surface -q (72 tests OK, post-edit), ./scripts/sync-codex.sh x2 (idempotent, mirror unchanged), grep -rn commands/flow-next live trees -> zero hits
- PRs: