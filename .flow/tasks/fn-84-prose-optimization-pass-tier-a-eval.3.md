---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Run the eval-gated loop on the `interview` skill: FINALIZE `optimization/interview/` (evals incl. lever scoring eval + fixtures, from real history + ≥1 non-flow-next fixture) → baseline (extended schema) → trim + ≥1 quality lever → ratchet → log → regen mirror → CHANGELOG line.

**Size:** M
**Files:** `optimization/interview/{README.md,evals.md,test-inputs.md,fixtures/*,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-interview/{SKILL.md,questions-shared.md,questions-business.md,questions-technical.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/capture/` (interview is spec.md-authoritative). Extended `results.tsv` schema. **Finalize evals (incl. the NFR-coverage scoring eval) BEFORE baseline (Major-B).**
- **Run permission + isolation (Major-1/C):** interview refines spec.md — write-capable child confined to a throwaway `git worktree` (read-only w.r.t. the real repo); stage the frozen input; discard worktree.
- **Interactive protocol (Major-D):** interview IS a canned Q&A by construction — the frozen input includes the full canned user-answer queue (one frozen answer per question the run reaches), recorded in the fixture; no unanswered prompt may block the run.
- **Frozen inputs:** real spec bodies + Q&A transcript shapes, PLUS ≥1 sanitized non-flow-next spec fixture (technical-detail probing overfits otherwise). Scrub + freeze.
- **Accuracy evals (≥2-3):** question relevance / no-redundancy; **override-respect** (never overwrites hand-edits, refusal paths intact); coverage of the spec's stated gaps.
- **Quality lever (blind spot):** NFR coverage — scoring eval finalized in the suite; try a LEAN NFR-prompt block; keep only if it rises without token/proximity regression.

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — loop + spec.md-authoritative rule
- `optimization/capture/` — closest spec.md-authoritative template
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` — prose being optimized (bulk, 847L)
Optional:
- `plugins/flow-next/skills/flow-next-interview/questions-*.md`

## Key context
- Frozen grammars: interview's receipt/section headers + option strings — confirm before trimming near them.
- Trim per-item verbosity, never item COUNT.

## Acceptance
- [ ] `optimization/interview/` committed with the FINAL eval set (≥2-3 `[ACCURACY]` incl. override-respect + NFR scoring eval) + frozen inputs incl. ≥1 non-flow-next fixture (R1, Major-B)
- [ ] Fixtures scrubbed — scoped privacy grep clean (R1)
- [ ] Baseline row 0 (extended schema) scored under the FINAL eval set before any mutation; write-capable child in a worktree; canned answer queue covers every prompt (R2, Major-B/C/D)
- [ ] ≥1 trim + ≥1 quality-lever (NFR) experiment; kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Frozen grammars unchanged; no relocated consuming-phase tables (R5)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed; `pytest` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
Built a novel **fable-judged question-quality eval suite** for `interview` (a core-workflow skill, per your steer) and ran the loop. Outcome: **quality lever tested and honestly REVERTED**; no prose change. Fable review NEEDS_WORK → all defects fixed.

**Suite (`optimization/interview/`):** 4 fixtures (I1 thin flow-native, I2 non-flow-next DocIQ anti-overfit, I3 override-respect, I4 restraint-stress). Run-trick = question EMISSION at `sonnet`; **E4 (NFR coverage) + E5 (overall question quality) judged by an independent `fable` subagent** (your steer); E1–E3 (ask-vs-investigate, format contract, override-respect) host-scored. Baseline: accuracy 12/12, quality 7/8 — questions are strong EXCEPT **I4 E5 FAIL: interview over-asks on a thorough spec** (asked a `[high]`-confidence Q it would just accept + a taste Q; its own "expect 40+ questions" bias). Real, corroborated blind spot.

**Quality lever (restraint/prune cue) — DISCARD-REVERT.** It fixed the target (I4 E5 fail→PASS, 5 padding Qs → 3 sharp) and tightened I3 — BUT it is **not zero-regression**: on the *thin* fixture I1 it dropped the symlinked-`.flow/` + Windows-Ctrl-C NFR probes (flow-next's real sore spots) — the prune cue bled from well-specified into under-specified specs. Reverted: **primary ground = that I1 coverage regression**; secondary = the E5 aggregate is too noisy (~50%-flip; baseline I3 itself flipped 5/5→3/5 at N=2) to show a clean gain. E1–E3 accuracy floor held 12/12; +144 tok not kept.

**Trim (2nd experiment) — DISCARD-HOLD:** question-surface trims are coverage-load-bearing (the I1 regression proves it); non-exercised-prose trims hold trivially = weak-ratchet. Not run; follow-up logged.

**Fable review verdict NEEDS_WORK → addressed every defect:** (1) added the missing trim row; (2) corrected the "no regression anywhere" over-claim → the real I1 coverage loss, in results.tsv + changelog + optimization-log; (3) named the failing cell (I3-E5) + stated the N=2 tie-break (tie→fail) + flagged the asymmetric baseline-N=1 vs lever-N=2 comparator; (4) fixed the 3→4-fixture doc drift (evals.md header math 15/9/6→20/12/8, README); (5) marked E5 ADVISORY-pending-N≥5 (a coin-flip eval can't solely gate a ratchet); (6) added the Major-B note for I4. The revert itself was affirmed by the review.

**Worktree mechanic (Major-1):** still DEFERRED — emission covered interview too (question quality is emission-scorable); the first suite scoring a written side-effect is where it'd be needed.

**R6/R8:** optimization-log row added; **no mirror regen / no CHANGELOG entry** (reverted → prose byte-identical to baseline); test surface unchanged. No version bump.

**Durable deliverables:** a fable-judged question-quality regression harness for a core skill; a diagnosed blind spot (over-asking on thorough specs); two concrete follow-ups (re-scope the prune cue to well-specified specs only; add a per-fixture must-ask-NFR answer-key + majority-vote E5 N≥5, then re-attempt).
## Evidence
- Commits:
- Tests: no flowctl/test change (lever reverted, prose byte-identical to baseline) — surface unchanged since fn-84.1's green run, fable-model review of the pass: NEEDS_WORK -> all defects addressed (trim row, no-regression correction, named cell+tie-break, doc-drift, E5-advisory, Major-B note); revert affirmed
- PRs: