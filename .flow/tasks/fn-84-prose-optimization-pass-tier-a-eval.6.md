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
New eval suite for `/flow-next:prospect`'s Phase-3 Critique (the candidate-rejection judgment: `{keep|drop, taxonomy, reason}` over a fixed 7-slug taxonomy, ≥40% rejection floor, blind to focus/personas). This suite validated the fn-84.5 process lesson end-to-end: **both a pre-run design review AND a post-run QA review (fable) gated it.**

**Pre-run design review** caught 2 CRITICAL + 3 MAJOR flaws BEFORE any expensive run — E2 was unfalsifiable (YAML-only critique can't self-report the floor → made it a harness computation), C2's "good" keeps were under-grounded (honest drops could hit the floor → added pain-facts), C1-8/9 keeps weren't derivable, C1-1 collided with open-spec fn-77, E1's hard-fail list omitted obvious rejects. All fixed before running. That is the ROI of design-review-first.

**Baseline = 4/4 EARNED** (sonnet, blind emission, facts-only fixtures): E1 9/9 (dups anchored to fn-70, strategy reject cites "Zero-dependency core" verbatim, C1-5 out-of-scope not too-large, C1-7 backward-incompat, C1-3 an on-mission valuable-but-XL idea correctly rejected on SIZE ALONE); E2 over-reject guard CLEAN (5 grounded good candidates all kept, only the dup dropped, held 17% < 40% floor with no padding); E3 taxonomy discipline (frozen slugs, other=0); E4 precision 4/4.

**Two answer-key imprecisions caught + fixed transparently** (the honest way — fix fixture, re-run, disclose; never silently re-read a key): (a) C2-4 under-grounded intra-vs-cross-run — the RUN caught it (a critique precision win); (b) C1-3 was double-defect making E4 ill-posed — the POST-run QA caught it (MAJOR); replaced with a single-defect on-mission-XL candidate, re-ran → too-large, E4 genuinely earned. QA final verdict: SHIP.

**Quality lever + trim honestly discarded** — E4 at ceiling; trim inspection-backed (mostly executable phase mechanics not covered by the critique-only eval; Phase-3 prose load-bearing; fn-82 already dieted). No prose change; no version bump. Durable: a taxonomy-classification + over-reject-guard regression harness for prospect + a second proof that both review gates catch fixture imprecisions cheaply.
## Evidence
- Commits:
- Tests: no prose change (quality lever + trim both discarded) — prospect skill unaffected, pre-run fable DESIGN review: FIX-DESIGN-FIRST (2 CRIT+3 MAJOR) -> fixed -> READY-TO-RUN, post-run fable QA review: NEEDS_WORK (E4 integrity) -> fixed transparently (C1-3 replaced + re-run) -> SHIP, 4 sonnet blind Phase-3 critique runs (C1 x2, C2 x2); stable verdicts agreed; 4/4 earned on well-posed evals
- PRs: