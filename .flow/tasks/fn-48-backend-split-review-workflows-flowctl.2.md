---
satisfies: [R8]
---

## Description

Verify whether current Factory Droid (factory.ai) still requires the cross-platform scaffolding flow-next has carried since 2026-02-03: `DROID_PLUGIN_ROOT` env var, `.factory-plugin/plugin.json` manifest path, and `Execute` tool matcher (vs Claude's `Bash`). Surface evidence is suspicious — `.factory-plugin/plugin.json` is referenced from 9 canonical skill files but doesn't exist in the repo; the last Droid-specific commit was 2026-02-03; releases 1.0.0 through 1.1.11 had zero Droid-specific work.

The outcome decides R4b's form: if Droid is still divergent, the canonical prelude keeps the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback (consolidated to once-per-skill); if Droid has converged with Claude Code's plugin contract, the Droid scaffolding is removed across the codebase. **T6 depends on this task.**

**Size:** M
**Files:** `plugins/flow-next/docs/platforms.md` (update to reflect findings), `CLAUDE.md` (root, `## Cross-platform patterns` section), `.flow/memory/knowledge/decisions/` (new decision entry recording the verdict).

## Approach

- **Web-research current Factory Droid platform contract.** Check factory.ai docs / blog / changelog for the current plugin-system shape. Look specifically for:
  - Does Droid still set `DROID_PLUGIN_ROOT` as its plugin-root env var? Or has it adopted `CLAUDE_PLUGIN_ROOT` (or some converged form)?
  - Does Droid still expect `.factory-plugin/plugin.json`? Or does it now read `.claude-plugin/plugin.json` directly?
  - Does Droid's tool matcher still use `Execute` for shell commands? Or has it switched to `Bash`?
  - Has Droid documented compatibility with Claude Code plugin format?
- **If documentation is ambiguous, install Droid CLI and test** (if practical): clone this repo, install flow-next via Droid's plugin marketplace path documented in `platforms.md`, run a skill (`/flow-next:list` is harmless), observe whether the prelude resolves or fails.
- **Record findings as a decision entry** via `flowctl memory add --track knowledge --category decisions`. Title: "Factory Droid platform status — 2026-05". Body covers what was checked, what's true today, and the implication for R4b.
- **Update `plugins/flow-next/docs/platforms.md`** to reflect current state. If Droid is still divergent: update prelude / hook-matcher examples to match. If converged or dead: rewrite the Droid section (either mark as legacy/deprecated, or remove if zero users — Gordon's call based on findings).
- **Update `CLAUDE.md` root `## Cross-platform patterns`** similarly.

The decision recorded here is what feeds T6 (fn-48.6). Be explicit: "R4b should take form X because Y."

## Investigation targets

**Required**:
- `plugins/flow-next/docs/platforms.md:16-37` — current Droid documentation claims.
- `CLAUDE.md` root, `## Cross-platform patterns` section — the canonical statement of what platforms flow-next supports and how.
- `scripts/sync-codex.sh:206` <!-- Updated by plan-sync: fn-48.1 shifted lines (FLOWCTL prelude block now 175-185); was :202 --> — the `.factory-plugin/plugin.json` → `.claude-plugin/plugin.json` rewrite rule (evidence that canonical files reference `.factory-plugin/plugin.json` which doesn't exist).
- Commit `103c708` (Feb 3 2026, last Droid-specific commit) — read message + diff to understand original justification.

**Optional**:
- `plugins/flow-next/hooks/hooks.json` (or equivalent) — `Bash|Execute` matcher regex usage.
- factory.ai homepage / docs (web research).

## Acceptance

- [ ] Decision entry recorded under `.flow/memory/knowledge/decisions/` with title naming "Factory Droid platform status", body covering (a) `DROID_PLUGIN_ROOT` env var status, (b) `.factory-plugin/plugin.json` manifest path status, (c) `Execute` tool matcher status, (d) explicit recommendation for R4b's form.
- [ ] `plugins/flow-next/docs/platforms.md` updated to reflect verified current Droid status (either: kept as-is with explicit "last verified <date>" note if Droid is still divergent; updated prelude/matcher examples if it has converged; marked deprecated/removed if Droid is unsupported).
- [ ] `CLAUDE.md` `## Cross-platform patterns` section updated in lockstep.
- [ ] CHANGELOG entry drafted (not necessarily committed; entry text in PR body when fn-48 lands).
- [ ] No code changes to canonical skill files — those happen in T6 based on this task's recommendation.
- [ ] The decision is unambiguous: T6 can be implemented without re-litigating Droid status.

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_
