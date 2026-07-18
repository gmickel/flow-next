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
Recorded the fn-100 eval in the interview optimization ledger and staged the release note: results.tsv row experiment=3 (v2-only: accuracy 12/12, quality 7/8, tokens 13242->13754 tok-equiv from task .1's before/after measurement, runs=6, sonnet, shipped) + changelog.md Experiment 3 SHIPPED entry (v1 4x2 table, earned-slot-rule story, I1 v2 re-run 3/3, guard reps, partition population 11 = 8 v1 + 3 v2 I1 with guard reps disclosed unscored, E5-noise caveat, and an explicit ledger-contract note that this is a feature-validation entry, not an optimization-ratchet keep); created CHANGELOG.md `## Unreleased` with the frontier-rounds `### Changed` entry (no version bump, batched-release rule); updated teams.md + strategy.md strategy-conflict throttle wording per turn -> per round (R10 grep clean). Gates green (pytest 1794 passed / 2 skipped; smoke 144/0). Codex impl-review SHIP after 1 fix round (r1: ratchet-exception documentation, partition-denominator reconciliation, contract-wording contradiction; plus a post-SHIP FYI unit-typo fix +512B -> +2044B/+512 tok-equiv).
## Evidence
- Commits: 7f1cc8ce3e0f10a136e5c638cd6ad6336f52367c, 12e0889db3ebac7e9c51cfc989655bf5cee40b3e, 1e864b406d992b37643ee6a290cf048737fbc35c, b77c0ed10824d3964e91a85413c8f9b0ed76e8c2
- Tests: uv run --with pytest python -m pytest plugins/flow-next/tests/ -q (1794 passed, 2 skipped, 225 subtests; baseline green pre-edit, green post-edit and after review fixes), bash plugins/flow-next/scripts/smoke_test.sh (144 passed, 0 failed; baseline green pre-edit, green post-fix), grep -rn 'per interview turn|per turn' plugins/flow-next/docs/teams.md plugins/flow-next/docs/strategy.md (no matches - R10 clean)
- PRs: