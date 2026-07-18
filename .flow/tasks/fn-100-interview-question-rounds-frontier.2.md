---
satisfies: [R5, R6, R7, R10]
---

## Description

Record the fn-100 eval in the interview optimization ledger, add the CHANGELOG entry, and run the gates.

**Size:** S
**Files:** optimization/interview/results.tsv, optimization/interview/changelog.md, CHANGELOG.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/strategy.md (+ codex mirror if sync-codex covers docs - it does not; docs are not mirrored)

1. `optimization/interview/results.tsv`: append row `experiment=3` using the exact numeric mapping in the spec's Appendix - v2-only observations (accuracy 12/12, quality 7/8, runs=6, model=sonnet, status=shipped). tokens_before/tokens_after come from task .1's completion summary (bytes/4, measured immediately before and after the edits by one documented command). Append-only: rows 0-2 untouched.
2. `optimization/interview/changelog.md`: add `## Experiment 3 - frontier rounds (fn-100) - SHIPPED` entry following the existing entry shape (headline metrics in the heading; bold sub-bullets for mutation, results, verdict). Source data: the spec's Decision Context + Appendix (first-pass 4x2xN=2 table, v2 I1 re-run 3/3, guard reps, partition 11/11 zero violations, the earned-slot-rule story, E5-noise caveat). Keep it a faithful summary, not a copy of the whole appendix.
3. `CHANGELOG.md`: create the `## Unreleased` heading directly under the intro (before `## [flow-next 2.15.0]`), add a `### Changed` bullet in the repo's bold-lead-in format: interview now asks in frontier rounds (whole frontier per round across AskUserQuestion calls of up to 4, dependencies never asked alongside their prerequisite, earned-slot restraint, doc-aware budgets per round), eval-validated on the optimization/interview harness. End with the no-version-bump note per batched-release convention.
4. R10: update the two per-TURN doc-aware throttle promises to per-round wording (word-level edits only): `plugins/flow-next/docs/teams.md` ~line 137 and `plugins/flow-next/docs/strategy.md` ~line 49. Verify with `grep -rn "per interview turn\|per turn" plugins/flow-next/docs/teams.md plugins/flow-next/docs/strategy.md` that no stale per-turn interview-throttle promise remains.
5. Gates: `python3 -m pytest plugins/flow-next/tests/` and `bash plugins/flow-next/scripts/smoke_test.sh` - both green.

## Investigation targets

**Required:**
- `.flow/specs/fn-100-interview-question-rounds-frontier.md` - Appendix (numeric mapping + eval data)
- `optimization/interview/results.tsv` - column order
- `optimization/interview/changelog.md` - entry shape
- `CHANGELOG.md:1-20` + `git show 2bbca6ff -- CHANGELOG.md | head -40` - Unreleased entry format

## Acceptance

- [ ] R5: results.tsv row 3 appended per mapping (real tokens_after recorded); changelog.md Experiment 3 entry added; fn-84 content untouched
- [ ] R6: `## Unreleased` heading created with the interview-rounds `### Changed` entry; no version bump anywhere
- [ ] R10: teams.md + strategy.md throttle lines read per-round; grep shows no stale per-turn interview promise
- [ ] R7: full pytest suite + smoke_test.sh green (paste tails as evidence)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
