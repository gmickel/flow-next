---
satisfies: [R12]
---

## Description
flow-next.dev mainline surfacing of the feature. Site repo: ~/work/flow-next.dev (separate repo; commit there separately).

**Size:** M
**Files:** (site repo) src/content/docs/specs/visual-aids.mdx (new), src/content/docs/review/visual-aids.mdx (new), src/pages/index.astro, src/content/docs/specs/writing-specs.mdx, src/content/docs/review/workflow.mdx, src/content/docs/teams/collaboration.mdx, src/content/docs/autonomous/overview.mdx, src/content/docs/releases/changelog.mdx, src/lib/site.ts, astro.config.mjs, package.json

## Approach
- Two NEW pages: specs/visual-aids (spec lens: activation, pre/post-plan rendering, lavish annotate loop, GitHub limitation) and review/visual-aids (PR instrument: diff-derived, R-ID evidence, why no annotate loop).
- NAV TWO SOURCES (memory: flow-nextdev-docs-page-needs): every new page registered in BOTH src/lib/site.ts navGroups AND astro.config.mjs sidebar — missing one silently drops it from the rail. Run the slug-set diff sanity check from the site CLAUDE.md.
- Landing: featureCards entry ("Visual review aids" / render lenses) linking specs/visual-aids; evaluate a proofPillars addition.
- Cross-page callouts: writing-specs, review/workflow, teams/collaboration, autonomous/overview (generate-never-poll note).
- Site changelog: `### 2.0.0 — HTML artifact mode & render lenses` per the strict releasing.md format; bump src/lib/site.ts FLOW_NEXT_VERSION + package.json to 2.0.0.
- Gate: `cd ~/work/flow-next.dev && pnpm build` green before handoff.

## Investigation targets
**Required:**
- ~/work/flow-next.dev/CLAUDE.md — "Navigation — TWO sources" + slug-set diff check
- ~/work/flow-next.dev/src/lib/site.ts:1-60 — version const + navGroups
- ~/work/flow-next.dev/astro.config.mjs — sidebar
- agent_docs/releasing.md "Docs-site changelog entry" — strict format
**Optional:**
- ~/work/flow-next.dev/src/pages/index.astro — featureCards/proofPillars shapes

## Acceptance
- [ ] Both new pages exist and appear in BOTH navbars (slug-set diff clean)
- [ ] Landing page carries the feature card; cross-page callouts in the 4 listed pages
- [ ] Site changelog entry follows the strict per-release format; FLOW_NEXT_VERSION + package.json read 2.0.0
- [ ] pnpm build green

## Done summary
flow-next.dev feature pass for 2.0.0 HTML artifact mode (R12): two new pages (specs/visual-aids — spec render lens; review/visual-aids — PR review instrument) registered in BOTH navbars, landing feature card + "Render lenses" proof pillar, cross-page callouts in writing-specs/review-workflow/teams-collaboration/autonomous-overview (generate-never-poll), strict-format 2.0.0 changelog entry incl. planSync.crossEpic breaking-change line, FLOW_NEXT_VERSION + package.json bumped to 2.0.0. Committed in the site repo (1dd356d, not pushed); pnpm build green; RP impl-review SHIP first pass.
## Evidence
- Commits: flow-next.dev@1dd356d4 feat(visual-aids): surface HTML artifact mode as a mainline feature; 2.0.0
- Tests: cd ~/work/flow-next.dev && pnpm build (green, 63 pages, both visual-aids pages emitted), slug-set diff between astro.config.mjs sidebar and site.ts navGroups (clean; only intentional introduction/install astro-only), grep checks: rail links to /specs/visual-aids/ and /review/visual-aids/ in built HTML; v2.0.0 on landing; 2.0.0 changelog entry rendered
- PRs: