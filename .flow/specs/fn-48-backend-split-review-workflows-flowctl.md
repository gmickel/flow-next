## Overview

Three context-load reductions in the flow-next plugin internals:

1. **Backend-split workflow.md** for the three review skills (`spec-completion-review`, `impl-review`, `resolve-pr`) so only the active backend's workflow content loads into context per invocation.
2. **Codex mirror prelude — drop dead fallback chain.** The mirror's `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}` chain has dead code (Codex never sets DROID or CLAUDE env vars).
3. **Canonical FLOWCTL prelude consolidation** so the 100-byte boilerplate isn't re-emitted on every flowctl-invoking bash block.

Plus a gating investigation: **R8 verifies whether current Factory Droid still requires the `DROID_PLUGIN_ROOT` / `.factory-plugin/plugin.json` / `Execute` matcher scaffolding**, since last Droid-specific commit was 2026-02-03 and `.factory-plugin/plugin.json` is referenced from 9 canonical files but doesn't exist in the repo. R8's outcome decides R4b's exact form.

All work is mechanical / behavior-preserving — same bash, same logic, smaller per-invocation context window.

## Conversation Evidence

> user (turn 1): "flow-next gives us amazing quality but right now it is too slow and uses too many tokens. check some recent flow-next planning/work/review that we did via the logs here /Users/gordon/.claude/projects (gmickel-claude-marketplace should have lots) and do a really deep analysis to see if there is anything we can fix/tweak to keep our quality etc while making things more efficient, ultrathink"
> user (turn 2): "which of these are 0% risk low hanging fruit"
> user (turn 3): "capture #4 and #8 as a spec"
> user (turn 4): "codex doesnt have this droid stuff in there right / also before we do this, check if the droid stuff is still necessary at all, afaik we did it because of variations in the tool names between claude code and droid, deep analysis"
> user (turn 5, picking from Droid-scope options): "verify droid, then decide but also: codex doesnt need this preface as codex-s version always just runs in codex surely"

(Agent context: turn 3 references a 9-item ranked list of efficiency cuts produced by the analysis in this conversation. #4 = "Backend-split workflow.md for review skills". #8 = "FLOWCTL prelude consolidation". Both classified as zero-risk mechanical refactors. Turn 4-5 expanded the prelude question — Codex mirror has dead-code fallbacks because Codex never sets `DROID_PLUGIN_ROOT` or `CLAUDE_PLUGIN_ROOT`; and current Droid platform compatibility hasn't been validated since 2026-02-03.)

## Goal & Context
<!-- Source-tag breakdown: 55% [user], 45% [paraphrase] -->

flow-next delivers excellent output quality but consumes too many tokens and runs too slowly per cycle. [user] (turn 1) A forensic analysis of two recent full cycles (fn-45, fn-42) traced where the cost goes: one fn-45 cycle billed 12.4M cost-relevant main-agent tokens plus 1.3M sub-agent tokens, with `cache_read` dominating at ~671M tokens. Two of the largest sources are pure context bloat that no behavior depends on — skill files load content unrelated to the active execution path. [paraphrase]

This spec narrows the work to the two zero-risk mechanical fixes from that analysis. [user] (turn 2, turn 3) Both preserve agent behavior exactly; the only thing that changes is what gets loaded into the model's context window per skill invocation. The work benefits every flow-next user every cycle (review skills fire on every spec). [paraphrase]

A secondary scope question surfaced during analysis: the FLOWCTL prelude carries cross-platform fallbacks for Factory Droid that may be stale. [user] (turn 4) The current Codex mirror also carries dead-code fallbacks because Codex never sets `DROID_PLUGIN_ROOT` or `CLAUDE_PLUGIN_ROOT` — only `$HOME/.codex` ever resolves in that environment. [user] (turn 5) / [paraphrase] This spec addresses both the always-safe Codex-mirror simplification and the Droid-status investigation that determines the canonical-file form.

## Architecture & Data Models
<!-- Source-tag breakdown: 100% [paraphrase] -->

Three refactors, no behavior change, no public-API change.

**(A) Backend-split workflow.md** for the three review skills:

- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow.md` (currently 645 lines; ~430 are the RP-backend prompt template)
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` (currently 1126 lines)
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (currently 411 lines; backend logic mixed with cross-cutting phases)

Split each into per-backend files (`workflow-rp.md`, `workflow-codex.md`, `workflow-copilot.md`, plus shared `workflow-common.md` for backend-detection and gating). The SKILL.md (or a small router preamble) reads `$BACKEND` and points the agent at the relevant file. Only the active backend's workflow file enters context per invocation.

**(B) Codex mirror prelude — drop dead fallbacks.** The Codex mirror at `plugins/flow-next/codex/skills/*/SKILL.md` currently carries `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"` — produced by `scripts/sync-codex.sh:179`. Neither `DROID_PLUGIN_ROOT` nor `CLAUDE_PLUGIN_ROOT` is ever set in Codex; only `$HOME/.codex` resolves. The chain is dead code. Replace with the direct form `FLOWCTL="$HOME/.codex/scripts/flowctl"` (or `flowctl` bare on PATH) in the sync output. Zero risk — the resolved value is identical in every Codex environment.

**(C) Canonical files: FLOWCTL prelude consolidation.** The boilerplate is currently re-emitted by every flowctl-invoking bash block (41 of 117 bash calls in the fn-45 cycle started with the 100-byte prelude). Replace with a once-per-skill PATH/helper mechanism so bash blocks call `flowctl` (or its equivalent short form) without the prelude. **The exact form depends on R8 — whether the DROID fallback is still needed.** Candidates: PATH-export at skill preamble, `.flow/bin/flowctl`-style wrapper that auto-resolves at install time, a tiny shell function, or — if Droid is dead — a direct `${CLAUDE_PLUGIN_ROOT}/scripts/flowctl` form.

Cross-platform: refactors (A) and (C) apply identically to canonical files; `scripts/sync-codex.sh` rewrites them for the Codex mirror with existing per-platform substitution rules (plus the (B) simplification baked into the rewrite output).

## Edge Cases & Constraints
<!-- Source-tag breakdown: 100% [paraphrase] -->

- **Backward compatibility for actively supported platforms is non-negotiable.** Behavior of each skill must remain byte-identical to the pre-refactor state when invoked end-to-end on Claude Code and Codex. Droid status is the subject of R8 — if it's still actively supported, behavior must be preserved there too; if it's not, R8's findings document the deprecation.
- **sync-codex.sh Stage 3 prose surgery is fragile.** Per memory entry `bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18`, sed rewrites silently miss tool names inside fenced code blocks and markdown tables. Any new tool / file-reference pattern introduced by the workflow-split must be explicitly handled in `scripts/sync-codex.sh`.
- **Audit sync-codex.sh during planning** (standing rule from memory entry `knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30`). Before each backend-split task ships, enumerate every new/changed tool call in affected workflow.md files and confirm sync-codex.sh handles each.
- **Cross-platform parity (canonical files).** Claude Code, Codex (via sync-codex.sh mirror), and Factory Droid (if R8 confirms support) all see the same logical structure. The Codex mirror at `plugins/flow-next/codex/` must regenerate cleanly from the new layout.
- **Setup-installed vs bare projects.** Some projects ran `/flow-next:setup` and have `.flow/bin/flowctl`; others rely purely on plugin-root resolution. The FLOWCTL prelude consolidation must support both.
- **Smoke tests pass unchanged.** `plugins/flow-next/scripts/smoke_test.sh` already exercises the affected skills end-to-end; the refactor lands only when every smoke suite stays green.
- **The Codex mirror prelude simplification (R4a) is independent and always safe** — it can ship even if R8 stalls.

## Acceptance Criteria
<!-- Source-tag breakdown: 35% [user], 65% [paraphrase] -->

- **R1:** `spec-completion-review/workflow.md` is split so that loading the skill under a given backend pulls only that backend's workflow content (RP-only, codex-only, or copilot-only) into the main agent's context. [paraphrase]
- **R2:** `impl-review/workflow.md` is split on the same backend-routing principle. [paraphrase]
- **R3:** `resolve-pr/workflow.md` is split on the same backend-routing principle (or, if its structure resists a clean backend axis, restructured to extract long backend-specific blocks into separate sourced files). [paraphrase]
- **R4a:** The Codex mirror's FLOWCTL prelude no longer carries the dead `DROID_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT` fallback chain; bash blocks in `plugins/flow-next/codex/skills/*/` resolve `flowctl` via `$HOME/.codex` directly (or a bare `flowctl` on PATH). The rewrite is encoded in `scripts/sync-codex.sh`. [user] (turn 5) / [paraphrase]
- **R4b:** The canonical-file FLOWCTL prelude is no longer re-emitted on every flowctl-invoking bash block inside the affected skill workflows; bash blocks invoke `flowctl` (or its equivalent short form) without the 100-byte prelude. The exact form is determined by R8's finding on Droid status. [paraphrase]
- **R5:** End-to-end behavior of all three review skills is unchanged across all actively supported backends (RP, codex, copilot — plus Droid if R8 confirms it). [user] (turn 2: "0% risk") / [paraphrase]
- **R6:** The Codex mirror at `plugins/flow-next/codex/` regenerates cleanly via `scripts/sync-codex.sh` after the refactor; all existing rewrites continue to apply. [paraphrase]
- **R7:** `plugins/flow-next/scripts/smoke_test.sh` runs green for all affected skills (and the broader suite is not regressed). [paraphrase]
- **R8:** Current Factory Droid platform status is verified — specifically whether Droid still (a) sets `DROID_PLUGIN_ROOT` as its plugin-root env var, (b) requires `.factory-plugin/plugin.json` (which is currently referenced from 9 canonical files but does not exist in the repo), and (c) uses `Execute` rather than `Bash` as the tool matcher name. Findings are documented (CHANGELOG entry, `docs/platforms.md` update). The verification feeds R4b's exact form: if Droid is still divergent, the canonical prelude keeps the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback (consolidated to once-per-skill); if Droid has converged with Claude's plugin contract, the Droid scaffolding (env var fallback, `.factory-plugin/plugin.json` references, `Execute` matcher in hooks, `docs/platforms.md` Droid section) is removed across the codebase. [user] (turn 4, turn 5)

## Boundaries
<!-- Source-tag breakdown: 65% [user], 35% [paraphrase] -->

In scope:
- The three review skills named above (`spec-completion-review`, `impl-review`, `resolve-pr`).
- The FLOWCTL prelude pattern wherever it appears in skill workflow.md / SKILL.md files (canonical) and the Codex mirror.
- Factory Droid platform-support investigation (R8) and any cleanup that follows from it.

Out of scope (deferred to separate specs, per turn 3's "#4 and #8" narrowing):
- The seven other cuts identified in the source analysis — plan-sync drift pre-gate, scout fan-out reduction, cache-TTL pacing, zombie-subagent guards, capture diff-redraw, task-size enforcement, avoidable AskUserQuestion gates. [user] (turn 3)
- Any behavior change to review logic, gating, or verdict semantics. The refactor is mechanical only. [user] (turn 2)
- Workflow.md restructuring for non-review skills (capture, plan, work, audit, prospect, etc.).
- Removing other cross-platform scaffolding (OpenCode community port references; Windows/Copilot path handling) — unless R8 demonstrably shows a path is dead, leave it alone.

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — refactor preserves the canonical-source-of-truth + sync-codex.sh mirror pattern. R8 investigation produces a clean go/no-go on Droid as a supported target, removing ambiguity that's existed since Feb 2026.
- **Spec-driven team patterns** — lower per-cycle context cost makes the spec-driven workflow cheaper to run, supporting adoption by teams who balk at the token bill of the full cycle.

## Decision Context

### Motivation
<!-- Source-tag breakdown: 50% [user], 50% [paraphrase] -->

Prioritization: these two changes are the only two from the nine-item analysis with zero behavioral risk. [user] (turn 2: "0% risk low hanging fruit") The other seven cuts all require trusting a heuristic, removing a question, or shortening a redraw — small risks that need empirical testing before shipping. The workflow-split and prelude trim are pure context-load reductions: the agent sees less data per turn, executes identical bash, and produces identical output.

Why now: cache_read traffic dominates per-session cost (~671M tokens in the fn-45 cycle alone). Each review-skill invocation re-loads ~1k lines of workflow.md regardless of which backend will actually run — the codex path is ~30 lines, the RP path is ~430, but the main agent loads both. Backend-split is the highest-leverage mechanical change available with zero behavioral risk. The FLOWCTL prelude is smaller per-occurrence but multiplies across every bash call in every skill.

Why the Droid investigation (R8): the FLOWCTL prelude form depends on it. Surface evidence is suspicious — `.factory-plugin/plugin.json` is referenced from 9 canonical files but doesn't exist in the repo; the last Droid-specific commit was 2026-02-03 (commits `103c708` / `72068df` / `bc7093d`); there has been zero Droid-specific work in 3+ months across releases 1.0.0 through 1.1.11. If Droid has converged with Claude Code's plugin contract upstream (likely given the broader Claude-plugin ecosystem maturing in 2026), the cross-platform scaffolding is dead weight; if it's still divergent, the prelude must preserve the fallback (just consolidated). R8 settles which path R4b takes with evidence rather than guess.

Why R4a (Codex mirror) is separated: it ships immediately because `DROID_PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT` are never set inside Codex — the existing fallback chain is dead code regardless of R8's outcome. [user] (turn 5)

## Quick commands

```bash
# Regenerate Codex mirror after canonical file changes
./scripts/sync-codex.sh

# Smoke-test affected skills
bash plugins/flow-next/scripts/smoke_test.sh

# Inspect prelude occurrences in any skill file
grep -n "DROID_PLUGIN_ROOT" plugins/flow-next/skills/<skill>/SKILL.md
grep -n "DROID_PLUGIN_ROOT" plugins/flow-next/codex/skills/<skill>/SKILL.md
```

## Early proof point

Task **fn-48.1** (Codex mirror prelude drop) validates the core approach (single-rule edit to sync-codex.sh + regen, no behavior change). It's the most isolated change with zero dependency on R8 — if its smoke fails or the mirror diff looks surprising, re-evaluate the sync-codex.sh rewrite strategy before proceeding with fn-48.3+.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | spec-completion-review/workflow.md backend-split | fn-48.3 | — |
| R2  | impl-review/workflow.md backend-split | fn-48.4 | — |
| R3  | resolve-pr/workflow.md backend-split | fn-48.5 | — |
| R4a | Codex mirror prelude — drop dead chain | fn-48.1 | — |
| R4b | Canonical FLOWCTL prelude consolidation | fn-48.6 | Depends on R8 (fn-48.2) outcome for exact form |
| R5  | Behavior unchanged across supported backends | fn-48.3, fn-48.4, fn-48.5, fn-48.6 | Verified per-task via smoke |
| R6  | Codex mirror regenerates cleanly | fn-48.1, fn-48.3, fn-48.4, fn-48.5, fn-48.6 | Verified per-task via sync-codex.sh re-run |
| R7  | smoke_test.sh green across affected skills | fn-48.1, fn-48.3, fn-48.4, fn-48.5, fn-48.6 | Verified per-task |
| R8  | Factory Droid platform status verified + docs updated | fn-48.2 | — |

## References

- Source analysis: this conversation's deep-dive on fn-45 / fn-42 session logs (`/Users/gordon/.claude/projects/-Users-gordon-work-gmickel-claude-marketplace/`).
- Memory entries:
  - `bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18` — sync-codex.sh Stage 3 prose-surgery pitfalls
  - `knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30` — standing rule: audit sync-codex.sh during planning when touching skills
  - `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21` — relative-path drift, missing codex-mirror smoke, JSON-contract mismatches
- `scripts/sync-codex.sh` (especially line 179, the FLOWCTL prelude rewrite rule)
- `plugins/flow-next/docs/platforms.md` (current Droid documentation)
- `CLAUDE.md` root `## Cross-platform patterns` section
