# Flatten plugin command shims: fix tripled command names in Claude Code menu

## Overview

Claude Code's slash menu renders flow-next command shims as `/flow-next:flow-next:flow-next:qa` (observed 2026-07-22). Three name layers stack:

1. Shims live in a subdirectory `plugins/flow-next/commands/flow-next/*.md`; Claude Code's namespacing is `<plugin-name>:<basename>` and the plugin-name-colliding subdir contributes an extra segment.
2. Each shim carries pre-plugin-era frontmatter `name: flow-next:qa` (colon inside `name` is non-standard; per current docs, `name` replaces only the LAST segment, plugin prefix stays - v2.1.216+ semantics; before that, `name` replaced the whole command name, which is why the literal names once looked right).
3. Claude Code prefixes the plugin name.

Fix: flatten the shim directory to `plugins/flow-next/commands/*.md` and drop the namespace from frontmatter, updating the Cursor manifest, the Codex prompts installer, and all other live path consumers in lockstep.

Verified namespacing rules (docs-scout, code.claude.com/docs skills + plugins-reference, Jul 2026):
- Namespace is exactly ONE segment: `<plugin-name>:<file-basename>`; subdirs under `commands/` are not a documented nesting feature - the `flow-next/` subdir naming collides with the plugin prefix.
- Frontmatter `name:` overrides only the last segment (v2.1.216+); `name: flow-next:qa` renders the colon literally -> doubled prefix.
- Flat `commands/qa.md` with no `name:` (or `name: qa`) -> `/flow-next:qa`. This satisfies R2; live-menu evidence still required (R1).

## Live path-consumer inventory (complete - verified by grep 2026-07-22)

| Consumer | Ref | Change |
|---|---|---|
| Cursor manifest | `plugins/flow-next/.cursor-plugin/plugin.json:19` `"commands": "./commands/flow-next"` | -> `"./commands"` |
| Cursor installer | `scripts/install-cursor.sh:21-23` (comments), `:87` (count glob); `scripts/install-cursor.ps1` equivalents | flat path |
| Cursor CI verifier | `scripts/ci/verify_cursor_install.py:41` (`root / "commands" / "flow-next"`), check `:79,:111` | flat path |
| Codex prompts installer | `scripts/install-codex.sh:252` loop `"$PLUGIN_DIR/commands/$PLUGIN/"*.md` (+ comment `:20`) | -> `"$PLUGIN_DIR/commands/"*.md` - MISSING THIS INSTALLS ZERO CODEX PROMPTS |
| CI gate | `plugins/flow-next/scripts/ci_test.sh:440` (`commands/flow-next/strategy.md` in jargon scan) | flat path |
| Tests | `plugins/flow-next/tests/test_no_default_hooks.py:25`, `test_model_routing_scaffold.py:24,45` (UNINSTALL path) | flat path |
| Codex sync | `scripts/sync-codex.sh` comment `:1487`; epic-review generator `:1519` | comment update; generator line REMOVED (see epic-review decision) |
| Smoke tests | `plugins/flow-next/scripts/prospect_smoke_test.sh:217`, `smoke_test.sh:1979,1997`, `resolve-pr_smoke_test.sh:26,140`, `map_smoke_test.sh:132`, `strategy_smoke_test.sh:535,542,549,565` (fixture builds a nested dir) | flat path (incl. fixture layout in strategy smoke) |
| Codex installer upgrade cleanup | `scripts/install-codex.sh:82-88` skills loop only replaces skills still in source; prompts loop only copies current prompts - stale `~/.codex/skills/flow-next-epic-review/` + `~/.codex/prompts/epic-review.md` would survive upgrades | add exact-target legacy cleanup for those two artifacts |
| Docs prose | `plugins/flow-next/docs/strategy.md:58`, `plugins/flow-next/docs/platforms.md:208,237,241`, `agent_docs/adding-skills.md:7` | task .2 |
| Manifests (counts) | `plugins/flow-next/.claude-plugin/plugin.json:4` + `.claude-plugin/marketplace.json:14` say "24 commands" | -> "23 commands" (task .2) |

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_install_cursor_parity test_cursor_review_commands test_cursor_clean_tree test_model_routing_scaffold test_no_default_hooks test_cursor_plugin_surface -q
claude plugin validate plugins/flow-next   # schema check (not a substitute for menu proof)
./scripts/sync-codex.sh && ./scripts/sync-codex.sh   # twice, idempotent
# FULL suite once at the final gate (work Phase 4): python3 scripts/run_tests_parallel.py
```

## Approach

- `git mv plugins/flow-next/commands/flow-next/*.md plugins/flow-next/commands/` (preserve history; 23 files), and delete `epic-review.md` (below). Confirm `commands/flow-next/` is gone (no .gitkeep exists).
- Frontmatter: strip the `flow-next:` prefix from every shim's `name:` (e.g. `name: qa`), or remove `name:` entirely so the basename governs - implementer verifies which renders cleanest on current Claude Code AND keeps Cursor's command names stable (Cursor may key display names off `name:`); prefer removing the field if both hosts derive from filename. Uniform across all shims; document the choice in the commit message.
- **Epic-review alias removed on ALL platforms** (explicit cross-platform decision): delete the Claude/Cursor shim AND remove the `generate_redirect_skill "flow-next-epic-review" ...` line at `scripts/sync-codex.sh:1519`, regenerating the mirror so the Codex redirect skill disappears too. Rationale: the alias's own prose says it was slated for removal in 2.0.0; repo is 3.2.x. **Existing Codex installs do NOT shed it automatically** - `install-codex.sh` only replaces skills still present in source and only copies current prompts - so add exact-target upgrade cleanup to `install-codex.sh`: remove `~/.codex/skills/flow-next-epic-review/` and `~/.codex/prompts/epic-review.md` (exact paths only, never touching unrelated user skills/prompts), with an installer test proving stale-alias removal leaves other entries intact.
- Update every consumer in the inventory table above.
- **Live-menu proof (R1, mandatory evidence, not narrative):** from a fresh `claude` session with the modified plugin loaded (e.g. `claude --plugin-dir plugins/flow-next` or reinstalled local marketplace), capture `/help` / menu inventory showing `/flow-next:qa` with NO duplicated prefixes, and one typed invocation reaching the `flow-next-qa` skill. `claude plugin validate` passes as schema validation.
- **New regression test:** create `plugins/flow-next/tests/test_cursor_plugin_surface.py` asserting: flat layout (no `commands/flow-next/` dir; >=23 `commands/*.md`), `.cursor-plugin/plugin.json` `commands` field == `./commands`, no shim frontmatter `name:` containing a colon, `epic-review.md` absent.
- `verify_cursor_install.py` runs against a fresh temp-HOME install (`CURSOR_HOME`-style override or the script's install-dir flag) - never against the user's live `~/.cursor` state.
- Run `./scripts/sync-codex.sh` twice; second run byte-identical; mirror diff (epic-review skill removal) committed with the change.
- Post-change sweep scoped to live trees: `grep -rn "commands/flow-next" plugins/flow-next/commands plugins/flow-next/skills plugins/flow-next/docs plugins/flow-next/tests plugins/flow-next/scripts scripts agent_docs README.md docs 2>/dev/null` -> zero hits. Historical CHANGELOG prose and `optimization/` fixtures are out of scope (immutable snapshots).

## Boundaries / non-goals

- Do NOT change skill names or the skills surface - command shims only (the epic-review Codex redirect-skill removal is part of the shim-alias removal, not a skills-surface change).
- Do NOT rewrite historical CHANGELOG entries or `optimization/` fixture snapshots.
- Droid/Grok have no test harness here: flat `commands/` is the standard Claude plugin layout both consume; doc-level verification suffices (platforms.md note).
- fn-123 already landed on main and is included in this worktree; no rebase pending.
- flow-next.dev / downstream walk happens at the batched release, not in this spec (maintainer workflow).

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** - one shim surface that renders correctly on Claude Code while keeping Cursor manifest commands and Codex prompt installs working; epic-review alias retired uniformly on every host.

## Decision context

- Flatten + de-prefix beats "keep nested dir and add an explicit `commands` key to `.claude-plugin/plugin.json`": the docs define no per-plugin commands-path override for Claude Code discovery, and the nested dir exists only as a Cursor accommodation that a one-line manifest edit removes.
- Epic-review alias removed everywhere (not just Claude/Cursor) to keep cross-platform parity - a Codex-only surviving alias would contradict the parity rationale.

## Acceptance Criteria

- **R1:** On current Claude Code, flow-next commands render without duplicated prefixes (target `/flow-next:qa`); no `flow-next:flow-next` entries remain except the inherent plugin-prefix + `flow-next` management-skill pairing. Evidence: fresh-session menu inventory + one typed invocation reaching the skill (captured output, not narration).
- **R2:** Current Claude Code command-namespacing rules verified against docs/release notes; chosen fix justified against them (documented in Overview; commit message states the frontmatter choice).
- **R3:** Cursor commands keep working: manifest `commands` path updated in lockstep; `install-cursor.sh`/`.ps1` + `scripts/ci/verify_cursor_install.py` (fresh temp-HOME install) updated and green; regression test `test_cursor_plugin_surface.py` created and green alongside `test_install_cursor_parity`, `test_cursor_review_commands`.
- **R4:** `scripts/sync-codex.sh` run twice stays idempotent; Codex mirror regenerated cleanly (epic-review redirect skill removed); `install-codex.sh` prompts loop updated so Codex installs still receive all command prompts.
- **R5:** No version bump; CHANGELOG entry staged under `## Unreleased`; manifest command counts (plugin.json + marketplace.json descriptions) updated to 23 without version changes.

## Early proof point

Task fn-124-flatten-plugin-command-shims-fix.1 validates the core approach (flat dir + de-prefixed frontmatter renders `/flow-next:qa` in a live Claude Code session). If the menu still doubles, re-verify frontmatter `name` semantics before touching docs.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Clean menu names on Claude Code, live evidence | fn-124-flatten-plugin-command-shims-fix.1 | - |
| R2 | Namespacing rules verified, fix justified | fn-124-flatten-plugin-command-shims-fix.1 | - |
| R3 | Cursor path + scripts + tests green, new regression test | fn-124-flatten-plugin-command-shims-fix.1 | - |
| R4 | sync-codex idempotent, codex installer fixed, alias removed | fn-124-flatten-plugin-command-shims-fix.1 | - |
| R5 | CHANGELOG Unreleased, manifest counts, no bump | fn-124-flatten-plugin-command-shims-fix.2 | - |

## References

- `plugins/flow-next/commands/flow-next/` - 24 shims, uniform frontmatter (`qa.md:2` shows `name: flow-next:qa`)
- Live consumer inventory table above (verified grep 2026-07-22)
- Claude Code docs: skills "How a skill gets its command name"; plugins-reference; CHANGELOG v2.1.208/v2.1.216 name-semantics fixes
