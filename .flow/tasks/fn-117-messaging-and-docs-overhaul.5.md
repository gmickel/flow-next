---
satisfies: [R2, R7]
---

## Description

The flexibility cluster: "Menu, not a rail" doctrine page + the Cookbook nav group. Repo: ~/work/flow-next.dev. This is the #1 coaching-gap fix.

**Size:** L
**Files:** new src/content/docs/strategy/menu-not-a-rail.mdx (or start/ placement - decide vs nav), new cookbook/ pages (index + per-category or single long page - decide by recipe density), src/content/docs/strategy/core-concepts.mdx (absorb "Tunable baseline"), src/lib/site.ts + astro.config.mjs

## Approach

- Menu-not-a-rail page: the doctrine in the field voice - "The default stages are rails, not a prohibition on exploration." / "The spec is the ratchet... not the permission to explore." / "The primitives are composable... both routes retain the same execution, evidence and review contracts." / "Use the smallest sufficient workflow." Kill the rigid-conveyor strawman explicitly (name it as the most common misreading). Absorb core-concepts "Tunable baseline" (leave a pointer).
- Cookbook: >= 35 recipes from the fn-117 research annex inventory. ADD the meta-recipe (maintainer-flagged, evidence-first category): "Plan from research you already have" - when a spec was preceded by real research (audits, evals, a long exploration), tell the planner so: `/flow-next:plan fn-N - we already did the research, it is in the spec; skip redundant scouting and go straight to breakdown`. The skill's scout fan-out is the default floor for cold starts, not a tax on warm ones; the R-ID/coverage/review gates still apply either way. Live example: fn-117 itself was planned this way from a 6-audit pass. (9 categories: skip/lighten, prompt-into, one-shot chains, evidence-first, model routing, parallelize, autonomy dial, integration tricks, team patterns). Each recipe: name, one-line scenario, exact invocation, one line on why the quality gates still hold. Include BOTH task-parallelism forms (Decision 7); exclude the 4 banned patterns. Use the RecipeCard component from .4.
- Cross-link: orchestration page <-> cookbook <-> menu page; hero teaser (from .4) points here.

## Acceptance

- [ ] Menu page live, linked from landing; core-concepts absorbed (R2)
- [ ] Cookbook >= 35 recipes, every invocation copy-paste-valid against current skill contracts (spot-check 10 against the repo), banned patterns absent (R2)
- [ ] Both nav sources; pnpm build green (R7)

## Done summary
Flexibility cluster shipped in ~/work/flow-next.dev (commit bebd3b0): new strategy/menu-not-a-rail.mdx doctrine page (kills the rigid-conveyor misreading, canonical field lines, absorbs core-concepts "Tunable baseline" leaving a pointer, contracts-hold section, nine-moves table) + new single-page Cookbook (44 verified recipes across the 9 categories, incl. the maintainer-flagged plan-from-research meta-recipe; Decision 7 both live parallelism forms marketed; 4 banned patterns absent; every invocation checked against current skill/flowctl contracts - 15+ spot-checked). Both nav sources updated (site.ts navGroups + astro.config sidebar: Strategy gains Menu, Not a Rail; new Cookbook group); landing menu teaser retargeted to the doctrine page; orchestration page cross-linked both ways. pnpm build green (68 pages); PSVI + client-name boundary greps clean. Cookbook shipped as one long page (Orchestration single-page precedent; ~5 recipes/category too thin for 9 pages; one copy-paste surface for agents).
## Evidence
- Commits: bebd3b0
- Tests: baseline: green (cd ~/work/flow-next.dev && pnpm build, 66 pages, rc=0), cd ~/work/flow-next.dev && pnpm build (post-change: 68 pages, rc=0; green receipt recorded via flowctl gate receipt --gate build), grep -ri 'PSVI|Velocity Index' ~/work/flow-next.dev/src (empty), client-name boundary grep via ~/.claude/flow-next-client-names.txt over flow-next.dev/src (empty), anchor check: all 9 cookbook category ids present in dist/cookbook/index.html; 44 recipe cards rendered; Menu, Not a Rail + All Recipes present in built rail
- PRs: