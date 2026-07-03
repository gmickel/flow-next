---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Run the eval-gated loop on the `prospect` skill (candidate-spec generation + rejection taxonomy). FINALIZE `optimization/prospect/` (evals incl. lever scoring eval + fixtures) → baseline (extended schema) → trim + ≥1 quality lever → ratchet → log → regen mirror → CHANGELOG line. Finder-shaped → over-flag guard mandatory.

**Size:** M
**Files:** `optimization/prospect/{README.md,evals.md,fixtures|test-inputs,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-prospect/{SKILL.md,workflow.md,personas.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/capture/` or `make-pr/`. Extended `results.tsv` schema. **Finalize evals (incl. the lever scoring eval) BEFORE baseline (Major-B).**
- **Run permission + isolation (Major-1/C):** prospect creates candidate specs — write-capable child confined to a throwaway `git worktree` (read-only w.r.t. the real repo) with a frozen signal set (backlog snapshot / rough ideas) staged in; emit candidate specs + rejection decisions; score idea quality + taxonomy application; discard worktree.
- **Interactive protocol (Major-D):** prospect has Phase 0 / Phase 6 blocking prompts — supply a **canned answer queue** mapping each blocking prompt (e.g. `regenerate | loosen-floor | ship-anyway`, `keep | drop`) to a frozen answer, recorded in the suite fixture; every prompt the frozen input reaches must have an answer.
- **Frozen inputs:** real signals / open-backlog snapshots (scrub, freeze).
- **Accuracy evals (≥2-3):** rejection-taxonomy applied correctly (right slug per case); no duplicate of an open epic; strategy-alignment respected (out-of-scope-vs-strategy).
- **Quality lever (blind spot):** a diagnosed miss (e.g. insufficient-signal vs too-large discrimination) — scoring eval finalized above; try a LEAN discriminator; keep only if accuracy rises.
- **Over-flag guard:** clean corpus (all-valid signals → no false rejection; all-duplicate → correctly rejected) — finding-rate ≈ baseline.

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — loop + over-flag guard
- `optimization/capture/` — suite template
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` — prose being optimized (bulk, 909L)
Optional:
- `plugins/flow-next/skills/flow-next-prospect/personas.md`

## Key context
- Frozen grammars (R19 anchor — MUST match across backends): rejection-taxonomy slugs (`duplicates-open-epic | out-of-scope | out-of-scope-vs-strategy | insufficient-signal | too-large | backward-incompat | other`); option strings (`regenerate | loosen-floor | ship-anyway`, `keep | drop`). Assert unchanged.

## Acceptance
- [ ] `optimization/prospect/` committed with the FINAL eval set (≥2-3 `[ACCURACY]` + lever scoring eval) + frozen inputs (R1, Major-B)
- [ ] Fixtures scrubbed — scoped privacy grep clean (R1)
- [ ] Baseline row 0 (extended schema) under the FINAL eval set before any mutation; write-capable child in a worktree; canned answer queue covers Phase 0/6 prompts (R2, Major-B/C/D)
- [ ] ≥1 trim + ≥1 quality-lever experiment; kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Over-flag guard on a CLEAN corpus: false-missing = 0, finding-rate ≈ baseline (R4)
- [ ] Frozen rejection-taxonomy slugs + option strings asserted unchanged (R5)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed; `pytest` + `prospect_smoke_test.sh` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
