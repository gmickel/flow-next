---
satisfies: [R4b, R5, R6, R7]
---

## Description

Consolidate the canonical FLOWCTL prelude so it's no longer re-emitted on every flowctl-invoking bash block. The 100-byte boilerplate `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"` repeats across every flowctl-using bash block in every skill (~14 skills × multiple bash blocks each = dozens of occurrences). The fn-45 analysis counted 41 of 117 bash calls starting with this prelude.

**R8 verdict — Path A (modified).** fn-48.2 web-verified the Factory Droid platform contract (decision entry: `.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md`) <!-- Updated by plan-sync: fn-48.2 recorded Path A modified — neither original A nor B applies -->. Findings:
- **KEEP** `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` env-var fallback — Droid still uses `DROID_PLUGIN_ROOT` as canonical plugin-root env var (with `CLAUDE_PLUGIN_ROOT` documented as Claude Code compatibility alias).
- **KEEP** `Bash|Execute` hook matcher — Droid's hooks-reference still lists `Execute` as the canonical tool name; `Bash` is not a recognized Droid matcher.
- **DROP** `.factory-plugin/plugin.json` fallback references — Droid auto-translates Claude Code plugin format via its interop layer; the fallback is dead code in this Claude-first plugin.

Consolidation work: prelude is collapsed to once-per-skill (PATH-export at SKILL.md preamble, or a shell function, or `.flow/bin/flowctl` wrapper) but **preserves** the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback logic. Bash blocks call `flowctl` (or `$F`) bare. Separately sweep `.factory-plugin/plugin.json` references from the 9 canonical files that mention it.

**Size:** M (touches many files but each touch is small and mechanical)
**Files:** all canonical skill files using the prelude (~14 skills × SKILL.md + workflow.md each), `scripts/sync-codex.sh` (rewrite rules), `plugins/flow-next/codex/skills/*` (regenerated mirror), 9 canonical files referencing `.factory-plugin/plugin.json` (sweep).
**Dependencies:** fn-48.2 (R8 outcome — already recorded; verdict locked).

## Approach

- **First, re-read the decision recorded by fn-48.2** at `.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md`. R4b form is locked: Path A modified (keep env-var fallback + `Bash|Execute` matcher; drop `.factory-plugin/plugin.json` fallback references only).
- **Enumerate every bash block in every canonical skill** that contains the FLOWCTL prelude: `grep -rn "DROID_PLUGIN_ROOT" plugins/flow-next/skills/`. This produces the consolidation work list.
- **Enumerate every `.factory-plugin/plugin.json` reference** for the sweep: `grep -rn "\.factory-plugin/plugin\.json" plugins/flow-next/skills/ plugins/flow-next/agents/`. Per the fn-48.2 decision, this is expected to hit ~9 canonical files including `flow-next-capture/SKILL.md:127`, `flow-next-make-pr/SKILL.md:110`, `flow-next-setup/workflow.md:116`, `flow-next-interview/SKILL.md`, `flow-next-plan/SKILL.md`. <!-- Updated by plan-sync: fn-48.2 identified the sweep target list -->
- **Consolidation mechanism (Path A modified):** At SKILL.md preamble, run once: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"; export PATH="$(dirname "$FLOWCTL"):$PATH"`. Subsequent bash blocks call `flowctl` bare. The PATH export is one block per skill, not per bash call. Or: declare a shell function in `phases.md`-style shared content.
- **Apply mechanically** to all affected skill files. Each file gets the new preamble; each bash block drops the prelude.
- **Sweep `.factory-plugin/plugin.json` references** from canonical files. Replace path fallback patterns with the `.claude-plugin/plugin.json`-only form. Update any prose describing the dual-manifest setup to reflect Droid's interop-layer auto-translation (Claude-first plugin format works on Droid directly).
- **Hooks file is preserved:** `plugins/flow-next/hooks/hooks.json` `Bash|Execute` matcher stays. Do not touch.
- **Update `scripts/sync-codex.sh`** as needed — the rewrite rules at lines 183/188-195/198-201/204-207 <!-- Updated by plan-sync: fn-48.1 shifted lines (FLOWCTL prelude block now 175-185); was 179/195/196/201/202 --> may need updating for the new canonical prelude form. The `'s|\.factory-plugin/plugin\.json|.claude-plugin/plugin.json|g'` rule at `:206` becomes a no-op once canonical references are removed, but is harmless to keep as defense-in-depth (per fn-48.2 decision).
- **Per the audit rule from memory**: re-verify sync-codex.sh handles every changed pattern before regenerating.
- **Regenerate the mirror**: `./scripts/sync-codex.sh`. Diff the mirror — should show systematic preamble changes + bash-block simplifications across every skill.
- **Smoke**: `bash plugins/flow-next/scripts/smoke_test.sh` for ALL skills, not just the three review skills (this task touches every flowctl-using skill).
- **CHANGELOG entry** under "Changed": document the prelude consolidation. Note the Droid platform-status re-verification (Path A modified — kept env-var fallback + `Bash|Execute` matcher; dropped `.factory-plugin/plugin.json` references after confirming Droid's interop layer auto-translates Claude Code plugin format).

## Investigation targets

**Required**:
- fn-48.2's recorded decision entry — `.flow/memory/knowledge/decisions/factory-droid-platform-status-*`.
- All canonical skill files using the prelude — enumerate via `grep -rn "DROID_PLUGIN_ROOT" plugins/flow-next/skills/ plugins/flow-next/agents/`.
- `scripts/sync-codex.sh:170-210` — rewrite-rule block governing the prelude.
- `CLAUDE.md` root, `## Cross-platform patterns` section.
- `plugins/flow-next/docs/platforms.md`.
- Memory entries: `sync-codexsh-tool-substitution-needs-2026-05-18`, `audit-sync-codexsh-during-planning-for-2026-04-30`, `fn-44-review-cycle-lessons-2026-05-21`.

**Optional**:
- `plugins/flow-next/hooks/hooks.json` — `Bash|Execute` matcher regex (touched only on Path B).

## Acceptance

- [ ] FLOWCTL prelude appears at most once per skill in canonical files (in the SKILL.md preamble or workflow.md top), not in every bash block.
- [ ] Bash blocks throughout the affected skills invoke `flowctl` (or a short alias) without the 100-byte boilerplate.
- [ ] `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` env-var fallback is **preserved** in the consolidated preamble (per fn-48.2 verdict — Droid still divergent on env-var name). <!-- Updated by plan-sync: fn-48.2 locked Path A modified -->
- [ ] `plugins/flow-next/hooks/hooks.json` `Bash|Execute` matcher is **preserved** (per fn-48.2 — Droid still uses `Execute` tool name).
- [ ] All `.factory-plugin/plugin.json` references **removed** from canonical skill/agent files (per fn-48.2 — Droid auto-translates Claude Code plugin format via interop layer; the fallback is dead code).
- [ ] `scripts/sync-codex.sh` updated to handle the new canonical prelude form correctly; mirror regenerates cleanly. The `.factory-plugin → .claude-plugin` rewrite rule at line 206 is kept as defense-in-depth (per fn-48.2).
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` is green for ALL skills (not just review skills).
- [ ] End-to-end behavior of every affected skill unchanged on Claude Code, Codex, Copilot, and Droid (fn-48.2 confirmed Droid is still actively supported).
- [ ] CHANGELOG entry drafted covering the prelude consolidation + Droid platform-status re-verification outcome.

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_
