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
flow-next.dev strategy/pipeline pass (R13): new canonical strategy/pipeline.mdx (end-to-end narrative + 2 mermaid diagrams, autonomy-tier mapping, render-lens touchpoint table), introduction.mdx brought current (ship stage, pipeline link, autonomy-suite + render-lens bullets), autonomous/overview.mdx gains the Ralph v2 direction at stub level (fn-61, marked direction-not-shipped) + pipeline link, page registered in BOTH nav sources. Committed in the site repo (2a226be, not pushed); pnpm build green; RP impl-review SHIP first pass.
## Evidence
- Commits: flow-next.dev@2a226be8 docs(strategy): canonical pipeline page + Introduction/autonomy pass
- Tests: cd ~/work/flow-next.dev && pnpm build (green, 64 pages, strategy/pipeline emitted), slug-set diff between astro.config.mjs sidebar and site.ts navGroups (clean; only intentional astro-only introduction/install), agent-browser render check: both pipeline.mdx mermaid diagrams + all 3 introduction diagrams processed (data-processed=true), grep checks: rail links /strategy/pipeline/ from introduction + autonomous/overview built HTML
- PRs: