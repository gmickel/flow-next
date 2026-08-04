---
satisfies: [R13]
---

## Description
The strategy/pipeline docs pass Gordon called out: a canonical end-to-end pipeline page, the missing autonomy-suite content, and the Introduction pipeline narrative brought current. Site repo: ~/work/flow-next.dev.

**Size:** M
**Files:** (site repo) src/content/docs/strategy/pipeline.mdx (new), src/content/docs/introduction.mdx, src/content/docs/autonomous/overview.mdx, src/lib/site.ts, astro.config.mjs

## Approach
- NEW strategy/pipeline.mdx: the one perfect end-to-end description — rough intent → capture/interview → spec → plan (context-fit task graph) → work (fresh re-anchored workers) → adversarial review → PR + receipts + handover → land/ship; where pilot/land/Ralph drive those same stages autonomously (two-instance topology); where the new render lenses sit at each human touchpoint. This is a narrative + diagram page, not a reference dump.
- Introduction.mdx: update the pipeline narrative to match (it predates the autonomy suite), link the new pipeline page, mention render lenses at the review/PR touchpoints.
- autonomous/overview.mdx: close content gaps vs current reality (pilot verdict grammar, land cadence, Ralph v2 direction at stub level) — audit against repo docs (ralph.md, pilot SKILL) rather than inventing.
- Both navbars for the new page (TWO sources rule); pnpm build gate.
<!-- Updated by plan-sync: fn-62.7 already landed in the site repo (flow-next.dev@1dd356d4) — site.ts/astro.config.mjs already carry FLOW_NEXT_VERSION 2.0.0 + the Specs/Review "Visual Aids" nav entries. This task's site.ts/astro.config.mjs edits are ADDITIVE: insert "strategy/pipeline" into the Strategy nav group in BOTH sources; do NOT re-bump the version or touch the visual-aids entries. -->


## Investigation targets
**Required:**
- ~/work/flow-next.dev/src/content/docs/introduction.mdx — current pipeline narrative
- ~/work/flow-next.dev/src/content/docs/autonomous/overview.mdx + ralph pages — coverage today
- plugins/flow-next/docs/ralph.md + skills/flow-next-pilot/SKILL.md — ground truth for autonomy content
**Optional:**
- STRATEGY.md (repo) — track framing to echo

## Acceptance
- [ ] strategy/pipeline.mdx exists, registered in BOTH navbars, covers the full pipeline incl. autonomy tier + render-lens touchpoints
- [ ] Introduction narrative matches the pipeline page (no contradictions) and links it
- [ ] autonomous/overview gaps closed against repo ground truth (no invented behavior)
- [ ] pnpm build green

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: flow-next.dev pipeline/autonomy/introduction pages exist and were reworked twice since (fn-117, fn-151) — any residual scope superseded. No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: