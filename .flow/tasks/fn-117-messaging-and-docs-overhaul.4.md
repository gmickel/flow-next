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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
