---
satisfies: [R11]
---

## Description

Update the public docs site for the interview rounds protocol. SEPARATE repo: `~/work/flow-next.dev` - commit there directly; nothing from this task enters the flow-next repo PR.

**Size:** S
**Files (in ~/work/flow-next.dev):** the interview skill page (`src/content/docs/skills/interview.mdx` or equivalent - locate via grep for "interview"), the docs-site changelog page per its conventions

1. Interview skill page: update the question-flow description to the rounds protocol - frontier rounds (every prerequisite-settled question per round, split across question calls of up to 4, dependencies never asked alongside their own prerequisite), earned-slot restraint, recompute-between-rounds, doc-aware budgets per round. Match the page's existing voice and depth; do not paste SKILL.md wholesale.
2. Changelog: DO NOT touch the docs-site changelog now - that site's changelog entries are versioned and coupled to FLOW_NEXT_VERSION/package.json bumps at release time, and it has no unreleased-staging convention. Instead, write one line in this task's completion summary: 'Docs-site changelog entry pending batched release: interview rounds protocol (fn-100)' so the release walk picks it up.
3. Navigation: NO new page is added, so the two-navbar rule should need no edits - verify the existing interview page stays in both navs.
4. Gate: `cd ~/work/flow-next.dev && pnpm build` - green.
5. Commit in that repo (Conventional Commits), do NOT push unless the maintainer's standing config says otherwise.

## Investigation targets

**Required:**
- `~/work/flow-next.dev/CLAUDE.md` - navigation two-sources rule + changelog entry conventions + version-bump rules
- the interview page source (grep -ri "interview" ~/work/flow-next.dev/src --include=*.mdx -l)
- `.flow/specs/fn-100-interview-question-rounds-frontier.md` (this repo) - the shipped Edit B wording to summarize faithfully

## Acceptance

- [ ] R11: interview page describes rounds accurately (frontier, <=4 per call, dependency deferral, earned slots, per-round doc-aware budgets)
- [ ] Docs-site changelog untouched; deferred-entry note recorded in the completion summary; FLOW_NEXT_VERSION / package.json untouched
- [ ] pnpm build green (paste tail)
- [ ] Committed in flow-next.dev (separate repo), not pushed unless standing config allows

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
