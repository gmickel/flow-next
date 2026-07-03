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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
