---
satisfies: [R1, R3, R5, R7, R9]
---

## Description

flow-next.dev design makeover: landing rework around the claim hierarchy + the docs-body component kit the content tasks (.5/.6) will consume. Repo: ~/work/flow-next.dev. USE the frontend-design skill discipline.

**Size:** L (the big lift; landing and component-kit halves are separable checkpoints within the task)
**Files:** src/pages/index.astro, src/styles/* (tokens/home*/starlight/rail), src/components/* (new: RecipeCard, ReceiptCallout, CodeTabs or Starlight-native equivalents, case-study capsule), public/llms.txt, src/lib/site.ts + astro.config.mjs (nav for any new landing anchors)

## Approach

- SINGLE THEME, beautify everything (Decision 3): keep Fraunces/IBM Plex + ink-teal/cream identity; polish, never genericize.
- Landing hero rework: claim hierarchy order - "Agents generate. flow-next proves." lead; proof-artifact hero (a real receipt/verdict render as the visual, replacing adjective copy); refresh ALL mockup content (current models via role labels, no version badges); autonomy section keeps loop cards with badges removed.
- New landing sections: verification-spine pillar strip (feeds .6's page), menu-not-rail teaser (feeds .5), field-notes/testimonial capsules (from agent_docs/testimonials.md - case-study capsule component, all linked).
- Docs-body rhythm kit: recipe card, receipt-styled callout (make "receipt" the visual motif), code-tabs, capsule - components the .5/.6 pages consume; apply to 2-3 existing pages as proof (pipeline.mdx, orchestration page).
- Agent-legibility: public/llms.txt (site map + canonical claims), copy-paste command blocks pattern.
- Both nav sources for anything new; pnpm build gate.

## Investigation targets

**Required:**
- src/styles/tokens.css + home*.css + starlight.css (current system)
- fn-117 messaging architecture section (claim order is the layout order)
- agent_docs/testimonials.md

## Acceptance

- [ ] Landing leads with the approved hero line + proof-artifact visual; zero stale model ids/version badges in mockups (R1, R9)
- [ ] Component kit exists and is used by >= 2 existing pages; receipt motif present (R9)
- [ ] Testimonial capsules all-linked (R5); verification pillar strip present (R3 landing half)
- [ ] llms.txt served; pnpm build green (R7)

## Done summary
flow-next.dev design makeover shipped (commit cdd5937 in ~/work/flow-next.dev, committed there per site conventions): landing reworked around the claim hierarchy - hero leads with "Agents generate. flow-next proves." plus a real paper-receipt proof-artifact render in the mockup; new claim-ordered sections 01 Proof (bias-towards-verification register tape), 02 Flexibility (menu-not-a-rail teaser), 03 Loops, 04 Signal (all-linked case capsules + anonymized field line). Docs-body rhythm kit created (ReceiptCallout, RecipeCard, CaseCapsule + Starlight-native Tabs) and applied to two existing pages (strategy/pipeline.mdx, orchestration); public/llms.txt served with canonical claims + site map; copy buttons wired. Single dark-ink/cream theme kept; no new pages so both nav sources untouched. pnpm build green (66 pages); PSVI + client-name boundary greps clean.
## Evidence
- Commits: flow-next.dev@cdd59374366ddab20d144da884cd60555a08c118
- Tests: baseline: green (cd ~/work/flow-next.dev && pnpm build, suite_rc=0, 66 pages, pre-edit), cd ~/work/flow-next.dev && pnpm build (suite_rc=0, 66 pages, post-change), grep -ri 'PSVI|Velocity Index' ~/work/flow-next.dev/src (clean, exit 1), grep -riwf ~/.claude/flow-next-client-names.txt ~/work/flow-next.dev/src (clean, exit 1), grep stale model ids/1.x badges in touched surfaces (clean, exit 1), nav sanity diff astro.config.mjs vs site.ts (only intentional install/introduction astro-only entries), curl http://localhost:4322/llms.txt -> 200; visual verification via agent-browser screenshots (hero receipt, verify tape, menu recipes, capsules, pipeline Tabs+ReceiptCallout, orchestration RecipeCards)
- PRs: