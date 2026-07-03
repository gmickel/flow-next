---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
**Proof point for the whole spec** — validates the loop shape AND the riskiest mechanics: worktree run isolation + permission model (Major-1/C), the non-flow-next anti-overfit fixture (Major-2), the interactive input protocol (Major-D), and eval-set-finalized-before-baseline (Major-B). Run the eval-gated autoresearch loop on the `plan` skill: FINALIZE `optimization/plan/` (evals incl. the quality-lever scoring eval + fixtures, from real history + ≥1 non-flow-next fixture) → baseline (extended schema) → trims + ≥1 quality lever → ratchet → log → regen mirror → CHANGELOG line. Prose-only.

If this loop cannot reach trustworthy binary evals within one iteration, STOP, log why, and re-evaluate the bootstrap+isolation approach BEFORE fanning out .2–.8 (the fn-85 reclassify escape).

**Size:** M (files small but numerous; time-boxed)
**Files:** `optimization/plan/{README.md,evals.md,test-inputs.md,fixtures/*,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-plan/{SKILL.md,steps.md,examples.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/capture/` + `optimization/make-pr/`; extended `results.tsv` schema.
- **Finalize the eval set BEFORE baseline (Major-B):** author ALL evals now, including the dependency-ordering scoring eval the quality lever targets. No eval added after baseline without a fresh baseline row.
- **Run permission + isolation (Major-1/C):** plan writes to `.flow/` — the harness child is **write-capable but confined to a throwaway `git worktree` (read-only w.r.t. the real repo)**, NOT a pure read-only Explore agent. Stage the frozen input into the temp repo; let plan write THAT `.flow/` exactly as live; score there; discard the worktree.
- **Interactive protocol (Major-D):** plan blocks on readiness + setup `AskUserQuestion`s — run with `mode:autonomous` (suppresses the setup/readiness questions), record the mode token in the suite README; any remaining prompt gets a canned answer in the fixture.
- **Frozen inputs:** 3-5 real rough ideas of varied size from real spec Goal sections, PLUS ≥1 sanitized NON-flow-next app + feature-request fixture (Major-2), all scrubbed + frozen.
- **Accuracy evals (≥2-3):** every acceptance criterion carries an R-ID; requirement-coverage table maps every R to ≥1 task or gap-justifies; **override-respect** on the existing-spec (Route A) path (never renumbers existing R-IDs, preserves hand-authored sections).
- **Quality lever (blind spot):** plan's task-ORDERING / dependency weakness (P6) — its scoring eval is in the finalized suite; try a LEAN dependency-ordering checklist; keep only if that eval rises without token/proximity regression.
- Methodology refs: `agent_docs/optimizing-skills.md` L42-72, L136-157, L179-202; `~/repos/autoresearch-skill/{SKILL.md,eval-guide.md}` (`git pull` first).
- **Harness:** dispatch the child from a `Task`-capable context (worker has no `Task` — see spec Execution note).

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — the ratchet methodology (loop, run-trick, accuracy guard, proximity)
- `~/repos/autoresearch-skill/SKILL.md` + `eval-guide.md` — the external methodology source (required for the proof point)
- `optimization/capture/` AND `optimization/make-pr/` — the two existing suite templates
- `plugins/flow-next/skills/flow-next-plan/steps.md` — the prose being optimized (bulk, 622L)
Optional:
- `agent_docs/optimization-log.md` — the ledger row schema

## Key context
- Frozen grammars NOT to touch: `Spec dependencies set:`; AskUserQuestion option strings (`proceed | mark-ready-then-proceed | abort`); autonomous-marker family. Bake "unchanged" into an accuracy eval.
- Proximity rule: never relocate routing/taxonomy/guardrail tables out of their consuming phase (capture DRY trim regressed 15→14).

## Acceptance
- [ ] `optimization/plan/` committed with the FINAL eval set (≥2-3 `[ACCURACY]` evals + the lever's scoring eval) + frozen inputs INCLUDING ≥1 non-flow-next fixture (R1, Major-B)
- [ ] Fixtures SCRUBBED — the scoped privacy grep (Tier-A dirs, synthetic domains allowlisted) returns nothing (R1)
- [ ] Baseline row 0 in the extended schema, scored under the FINAL eval set, before any mutation (R2, Major-B)
- [ ] Run permission/isolation verified: write-capable child confined to a throwaway worktree; the real `.flow/` untouched; `mode:autonomous` (no hang on prompts) (Major-1/C/D)
- [ ] ≥1 trim + ≥1 quality-lever experiment; each kept row shows accuracy held/raised AND tokens↓/quality↑, each discard logged with the regression (R3, R4)
- [ ] Frozen grammars asserted unchanged by an eval; no relocated consuming-phase tables (R5)
- [ ] `agent_docs/optimization-log.md` row per experiment (R6)
- [ ] `./scripts/sync-codex.sh` regenerated + committed; `pytest` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no version bump (R8)
- [ ] If time-boxed out: STOP, log why, reclassify to fn-85 (R9 handoff)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
