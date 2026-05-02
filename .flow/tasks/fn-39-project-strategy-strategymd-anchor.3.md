# fn-39-project-strategy-strategymd-anchor.3 Prospect + plan grounding (Phase 0 scan, Strategy Alignment, drift surfacing)

## Description
Wire `STRATEGY.md` grounding into `/flow-next:prospect` (Phase 0 grounding scan, rejection taxonomy) and `/flow-next:plan` (research scan, `## Strategy Alignment` spec section, drift surfacing). Both consume `flowctl strategy read --json` from Task 1; both surface advisory output (never auto-reject, never auto-supersede).

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` (edit Phase 0 + rejection taxonomy)
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` (edit Phase 1 grounding-snapshot section)
- `plugins/flow-next/skills/flow-next-plan/steps.md` (edit Step 1 research scan)

Depends on Task 1.

## Approach

**Prospect** (verbatim-emit grounding pattern — pass the user's strategic language straight through into candidate generation, no paraphrasing):

- `flow-next-prospect/workflow.md` Phase 1 grounding-snapshot section (around lines 178-334 per repo-scout): add `STRATEGY.md` scan block. Block runs `flowctl strategy status --json` first (~5 lines bash); if `sections_filled >= 1`, then runs `flowctl strategy read --json` and emits `## Strategy snapshot` block in the grounding artifact. Includes verbatim:
  - `name` from frontmatter
  - `target_problem` body (full text)
  - `approach` body (full text)
  - `tracks` list (track names + their bodies)
  - `last_updated` ISO date
  Skip if `sections_filled == 0` and emit `scanned: none (no STRATEGY.md or husk)` line.
- `flow-next-prospect/SKILL.md` rejection taxonomy: add `out-of-scope-vs-strategy` to the existing list (currently `duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`). Critique step uses this when a candidate violates an active track. Surface as advisory rejection with track citation: `Rejected: [out-of-scope-vs-strategy] — contradicts active track "<track-name>"`. Document in skill prose that this is advisory — user can override at promote time.
- Critique pass (existing two-pass generate-then-critique) reads the strategy snapshot from Phase 1 artifact and weights candidate generation toward strategy-aligned directions. No new flowctl plumbing needed — the snapshot is already in the candidate-generation prompt.

**Plan** (model after existing docs-gap-scout dispatch at `flow-next-plan/steps.md:102`):

- `flow-next-plan/steps.md` Step 1 (Fast research, parallel): add `STRATEGY.md` read to the existing scout dispatch context. The scouts already get the request text + research findings; add a one-line `flowctl strategy status --json` check, and if `sections_filled >= 1`, pass the parsed `STRATEGY.md` content into the plan-prompt context.
- Step 5 (Write to .flow): add `## Strategy Alignment` section to the epic spec template (just under `## Boundaries / non-goals`). Lists which active tracks the plan serves. If no tracks served, emit `_No active strategy track served — review for drift._` placeholder.
- Drift surfacing: when the plan's scope conflicts with an active track, write a `## Strategy drift flagged for review` block in the epic spec (NOT in STRATEGY.md). Block format mirrors plan-sync's "Decision overrides flagged for review" at `agents/plan-sync.md:101-105`. Read-only — the plan skill never auto-supersedes the strategy doc; the user (or `/flow-next:strategy`) decides whether to revise.
- Husk semantics: if `flowctl strategy status` returns `husk: true OR exists: false`, plan skips the alignment section entirely (no signal to align to). Document this in skill prose so contributors know absence is fine.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` lines 178-334 — Phase 1 grounding-snapshot data sources (model for STRATEGY.md scan block)
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` — rejection taxonomy enumeration
- `plugins/flow-next/skills/flow-next-plan/steps.md` lines 73-128 — Step 1 scout dispatch table
- `plugins/flow-next/skills/flow-next-plan/steps.md` lines 195-280 — Step 5 epic spec template
- `plugins/flow-next/agents/plan-sync.md:101-105` — read-only-surface convention for "Decision overrides flagged for review" (model for `## Strategy drift flagged for review`)

**Optional:**
- The verbatim-emit grounding pattern: when injecting STRATEGY.md content into the candidate-generation / planning prompts, emit `name`, `target_problem`, `approach`, `tracks` raw — no paraphrasing — so downstream prompts see the exact language the user committed to.
- The plan-time strategy check pattern: research scan reads STRATEGY.md if present and emits a `## Strategy Alignment` section listing which active tracks the plan serves; flag scope conflicts as a read-only `## Strategy drift flagged for review` block.

## Key context

- Both surfaces are advisory, not gating. Prospect rejection is shown to user; user can promote anyway. Plan drift is surfaced read-only; user runs `/flow-next:strategy` to revise if intended.
- No auto-supersede — this is the universal rule for shared-state docs in flow-next (mirrors plan-sync's decision-record handling).
- Husk-vs-presence: use `sections_filled >= 1` from `flowctl strategy status`, not `[[ -f STRATEGY.md ]]`. Same trap glossary fell into.
- Track ordering: tracks listed in user-chosen order; do NOT cite "highest-priority track" — strategy doesn't carry priority metadata in v1.
## Acceptance
- [ ] `flow-next-prospect/workflow.md` Phase 1 grounding-snapshot adds `STRATEGY.md` scan block. Calls `flowctl strategy status --json` first; when `sections_filled >= 1`, follows with `flowctl strategy read --json` and emits a `## Strategy snapshot` artifact block.
- [ ] Strategy snapshot includes verbatim: `name`, `target_problem`, `approach`, `tracks` (each track name + body), `last_updated`. No paraphrasing — uses raw values from `flowctl strategy read`.
- [ ] When `sections_filled == 0` (husk) or strategy file absent, prospect emits `scanned: none (no STRATEGY.md signal)` and proceeds normally without strategy grounding.
- [ ] `flow-next-prospect/SKILL.md` rejection taxonomy enumeration adds `out-of-scope-vs-strategy` to the existing 6-category list. Critique pass uses this category when candidate scope contradicts an active track.
- [ ] Rejected candidates with `out-of-scope-vs-strategy` cite the violated track name verbatim: `Rejected: [out-of-scope-vs-strategy] — contradicts active track "<track-name>"`.
- [ ] Rejection is advisory only — user can `flowctl prospect promote <id> --idea N --force` to override (existing flag).
- [ ] Strategy snapshot weights candidate generation in the existing two-pass generate-then-critique flow without new flowctl plumbing — uses prompt-level injection only.
- [ ] `flow-next-plan/steps.md` Step 1 (Fast research) adds `flowctl strategy status --json` check; when `sections_filled >= 1`, parsed `STRATEGY.md` content passes into plan-prompt context alongside research findings.
- [ ] `flow-next-plan/steps.md` Step 5 (Write to .flow) epic-spec template adds `## Strategy Alignment` section between `## Boundaries / non-goals` and `## Decision context`. Section lists active tracks served by the plan.
- [ ] When plan serves no active track, `## Strategy Alignment` contains `_No active strategy track served — review for drift._` placeholder, not a hidden empty section.
- [ ] When plan scope conflicts with an active track, plan emits a `## Strategy drift flagged for review` block (in the epic spec, NOT in STRATEGY.md). Format mirrors plan-sync's decision-overrides convention: bulleted list with track name + plan-decision divergence + `Review for revision via /flow-next:strategy.` line.
- [ ] Plan never edits `STRATEGY.md` — read-only consumption. Drift is surfaced for human review; `/flow-next:strategy` is the only writer.
- [ ] Husk-vs-presence: when `flowctl strategy status` returns `husk: true OR exists: false`, plan skips `## Strategy Alignment` and the drift block entirely. Documented in skill prose.
- [ ] Bash that calls `flowctl strategy status` uses portable `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` shape per existing flow-next conventions.
- [ ] Smoke verification: with a populated STRATEGY.md, `/flow-next:prospect` artifact contains the strategy snapshot block; with a husk file, the artifact has `scanned: none`.
## Done summary
Wired STRATEGY.md grounding into /flow-next:prospect (Phase 1 verbatim snapshot block + out-of-scope-vs-strategy rejection category) and /flow-next:plan (Step 1 strategy status check + Step 5 ## Strategy Alignment section between Boundaries and Decision context + ## Strategy drift flagged for review block mirroring plan-sync's read-only Decision overrides surface). Both surfaces are advisory and never auto-supersede; husk-vs-presence gated on sections_filled >= 1.
## Evidence
- Commits: 28c1647d70d1a64e3e764c91cc051e79849d18bb
- Tests: plugins/flow-next/scripts/ci_test.sh (56 pass), plugins/flow-next/scripts/smoke_test.sh (130 pass), deterministic snapshot fixture: 3 runs byte-identical, verbatim approach + tracks emit, husk + absent variants emit 'scanned: none (no STRATEGY.md signal)'
- PRs: