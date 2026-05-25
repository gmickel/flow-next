---
satisfies: [R4b, R5, R6, R7]
---

## Description

Consolidate the canonical FLOWCTL prelude so it's no longer re-emitted on every flowctl-invoking bash block. The 100-byte boilerplate `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"` repeats across every flowctl-using bash block in every skill (~14 skills × multiple bash blocks each = dozens of occurrences). The fn-45 analysis counted 41 of 117 bash calls starting with this prelude.

**The exact form depends on the R8 finding from fn-48.2.** Two paths:
- **R8 says "Droid is still divergent"**: prelude is consolidated (PATH-export at SKILL.md preamble, or a shell function, or `.flow/bin/flowctl` wrapper) but preserves the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback logic. Bash blocks call `flowctl` (or `$F`) bare.
- **R8 says "Droid has converged / is unsupported"**: the entire DROID scaffolding goes away. Prelude simplifies to a single PATH-injection or `.flow/bin/flowctl` reference. Also remove `.factory-plugin/plugin.json` fallback references in 9 canonical files, `Execute` from the `Bash|Execute` matcher regex in hooks (if present), and the `Factory Droid (native support)` section from `docs/platforms.md`.

**Size:** M (touches many files but each touch is small and mechanical)
**Files:** all canonical skill files using the prelude (~14 skills × SKILL.md + workflow.md each), `scripts/sync-codex.sh` (rewrite rules), `plugins/flow-next/codex/skills/*` (regenerated mirror), conditionally `CLAUDE.md` / `docs/platforms.md` / hooks files (depending on R8 outcome).
**Dependencies:** fn-48.2 (R8 outcome).

## Approach

- **First, re-read the decision recorded by fn-48.2** (`flowctl memory read <entry-id>`). Confirm the recommended R4b form before touching code.
- **Enumerate every bash block in every canonical skill** that contains the FLOWCTL prelude: `grep -rn "DROID_PLUGIN_ROOT" plugins/flow-next/skills/`. This produces the work list.
- **Decide the consolidation mechanism** based on the R8 path:
  - **Path A (Droid kept, simpler)**: At SKILL.md preamble, run once: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"; export PATH="$(dirname "$FLOWCTL"):$PATH"`. Subsequent bash blocks call `flowctl` bare. The PATH export is one block per skill, not per bash call. Or: declare a shell function in `phases.md`-style shared content.
  - **Path B (Droid dropped, cleanest)**: Bash blocks call `flowctl` bare, assuming `.flow/bin/flowctl` is on PATH (setup-installed projects) OR `${CLAUDE_PLUGIN_ROOT}/scripts/flowctl` is on PATH (Claude Code marketplace install). At SKILL.md preamble, one PATH-export line handles both. Remove all DROID/.factory-plugin/Execute scaffolding repo-wide.
- **Apply mechanically** to all affected skill files. Each file gets the new preamble; each bash block drops the prelude.
- **Update `scripts/sync-codex.sh`** as needed — the rewrite rules at lines 179/195/196/201/202 may need updating or removing depending on what the canonical form becomes.
- **Per the audit rule from memory**: re-verify sync-codex.sh handles every changed pattern before regenerating.
- **Regenerate the mirror**: `./scripts/sync-codex.sh`. Diff the mirror — should show systematic preamble changes + bash-block simplifications across every skill.
- **Update docs (conditional on R8 path B)**: `CLAUDE.md` `## Cross-platform patterns`, `docs/platforms.md` Droid section, any `.factory-plugin/plugin.json` references in skill prose.
- **Smoke**: `bash plugins/flow-next/scripts/smoke_test.sh` for ALL skills, not just the three review skills (this task touches every flowctl-using skill).
- **CHANGELOG entry** under "Changed" (and "Removed" if Path B): document the prelude consolidation and Droid status with one paragraph each.

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
- [ ] `scripts/sync-codex.sh` updated to handle the new canonical form correctly; mirror regenerates cleanly.
- [ ] If R8 path B (Droid dropped): no remaining references to `DROID_PLUGIN_ROOT`, `.factory-plugin/plugin.json`, or `Execute` matcher in canonical skill/agent files. `docs/platforms.md` Droid section + `CLAUDE.md` cross-platform bullets updated accordingly.
- [ ] If R8 path A (Droid kept): all Droid-related fallbacks preserved in the consolidated preamble; `docs/platforms.md` updated to reflect the new prelude form.
- [ ] `bash plugins/flow-next/scripts/smoke_test.sh` is green for ALL skills (not just review skills).
- [ ] End-to-end behavior of every affected skill unchanged on Claude Code, Codex, Copilot (and Droid if R8 says still supported).
- [ ] CHANGELOG entry drafted covering the prelude consolidation + Droid status outcome.

## Done summary

_(filled by `/flow-next:work` when the task completes)_

## Evidence

_(filled by `/flow-next:work` — commit hashes + test commands run)_
