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
flow-next.dev B1 quick wins shipped (commit 293579e in ~/work/flow-next.dev, committed there per site conventions): all stale gpt-5.5/gpt-5.4 refs outside dated changelog entries resolved (work.mdx delegateModel -> gpt-5.6-terra fixing the orchestration contradiction; subagent tier tables -> INTELLIGENT/FAST role labels; review examples -> current defaults), 1.13.0/1.14.0 loop badges and shipped-(1.x) callouts removed, homepage testimonials replaced with the verified GitHub pool from agent_docs/testimonials.md (fabricated X set fully removed), schema.mdx duplicate Acceptance Criteria heading renamed, when-to-use overnight section now covers the pilot/land/Ralph ladder, Ralph Overview de-duped from BOTH nav sources, and a new all-skills grid page (/skills/, 28 entries by pipeline stage) added to BOTH nav sources. pnpm build green (66 pages); PSVI + client-name boundary greps clean.
## Evidence
- Commits: flow-next.dev@293579e14d0c2454766ae7a5ffc64956b70a16ce
- Tests: baseline: green (cd ~/work/flow-next.dev && pnpm build rc=0 pre-edit, 65 pages; docsite base c2ebe423d45b214ea6ecfe2db1ea1c992b3de572), cd ~/work/flow-next.dev && pnpm build (rc=0 post-edit, 66 pages incl. new /skills/ index), grep -rni 'gpt-5.5|gpt-5.4' src/ astro.config.mjs minus changelog -> empty (exit 1), grep -rn '1.13.0|1.14.0' src minus changelog/versioning -> empty (exit 1), grep -ri 'PSVI|Velocity Index' ~/work/flow-next.dev/src -> clean (exit 1), grep -riwf ~/.claude/flow-next-client-names.txt ~/work/flow-next.dev/src -> clean (exit 1), nav slug-set diff astro.config.mjs vs site.ts -> only install/introduction (intentional)
- PRs: