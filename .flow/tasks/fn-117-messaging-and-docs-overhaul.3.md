---
satisfies: [R7]
---

## Description

flow-next.dev B1 quick wins - mechanical fixes clearing the ground for the makeover. Repo: ~/work/flow-next.dev.

**Size:** M
**Files:** src/pages/index.astro, src/content/docs/skills/work.mdx, subagents/*.mdx, review/*.mdx, specs/schema.mdx, when-to-use.mdx, src/lib/site.ts, astro.config.mjs, new skills index page

## Approach

The audit's B1 list verbatim: stale model refs (index.astro L329/345 codex:gpt-5.5:high; work.mdx L80/L120 delegateModel gpt-5.5 vs orchestration's terra - resolve to terra/role labels); kill 1.13.0/1.14.0 loop badges (index.astro L415/421) + soften "shipped (1.x)" callouts; replace the @ben testimonial with a verified entry from agent_docs/testimonials.md; fix duplicated "## Acceptance Criteria" heading in specs/schema.mdx; add pilot/land to when-to-use.mdx overnight-execution section; de-dupe Ralph nav entries (both nav sources!); new skills index page (26-skill grid by pipeline stage) added to BOTH navbars.

## Acceptance

- [ ] Zero gpt-5.5/gpt-5.4 refs outside dated eval notes; work.mdx/orchestration contradiction resolved
- [ ] Skills index page live in both nav sources; Ralph single-listed
- [ ] pnpm build green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
