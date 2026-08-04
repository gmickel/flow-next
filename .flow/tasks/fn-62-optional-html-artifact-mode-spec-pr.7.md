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
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: flow-next.dev visual-aids pages exist (/review/visual-aids/, /specs/visual-aids/) with landing card + cross-links (2.0.0 render-lens release; fn-151 landing rework superseded the card design). No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: