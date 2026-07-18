---
satisfies: [R12]
---

## Description

Add the eval-validated async fact-scout mode to the interview skill and its downstream surfaces.

**Size:** S/M
**Files:** plugins/flow-next/skills/flow-next-interview/SKILL.md, plugins/flow-next/codex/ (regenerated), CHANGELOG.md, optimization/interview/changelog.md, and (separate repo, committed there, not in this PR) ~/work/flow-next.dev/src/content/docs/skills/interview.mdx

1. Edit D: insert the "#### Async fact-scouts (optional, rounds mode)" subsection VERBATIM from the spec's "Exact SKILL.md edit D" block, at the end of "### Investigate Codebase Before Asking" (after the "that's the bug" paragraph, before "#### Code-versus-assertion contradiction").
2. Regenerate the Codex mirror (`./scripts/sync-codex.sh`), verify the Task/Explore transform reads correctly in the mirror, second run byte-identical, R2-injection audit clean (same drill as task .1).
3. CHANGELOG.md: extend the existing fn-100 Unreleased entry with one nested bullet describing async fact-scouts (background read-only scout during rounds; sonnet-minimum tier; brief-is-the-contract; eval-validated).
4. optimization/interview/changelog.md: append a short "Async fact-scout addendum (fn-100 R12)" paragraph INSIDE the Experiment 3 entry, summarizing the scout eval from the spec Decision Context (haiku-tier failure on the load-bearing fact, sonnet recovery on identical brief, granular-brief effect, no-token-saving honesty, guardrails shipped). No results.tsv row.
5. flow-next.dev interview.mdx: add ONE sentence to the Question rounds section: while the user answers a round, a read-only fact-scout can resolve the lookups gating the next round in the background. `pnpm build` green; commit in that repo (do not push); docs-site changelog still deferred to release.
6. Gates: pytest full suite + smoke_test.sh green.

## Investigation targets

**Required:**
- `.flow/specs/fn-100-interview-question-rounds-frontier.md` - "Exact SKILL.md edit D" verbatim block + the async-fact-scout eval paragraphs in Decision Context
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` - the insertion site (end of Investigate Codebase Before Asking)
- `CHANGELOG.md` Unreleased fn-100 entry - extension point
- `optimization/interview/changelog.md` Experiment 3 - addendum point

## Acceptance

- [ ] R12: Edit D inserted verbatim at the specified site; no other SKILL.md changes
- [ ] Mirror regenerated, idempotent, audit clean
- [ ] CHANGELOG bullet + eval-ledger addendum added (append-only elsewhere)
- [ ] interview.mdx sentence added, pnpm build green, committed in flow-next.dev (not pushed)
- [ ] pytest + smoke green (paste tails)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
