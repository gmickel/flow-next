---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Run the eval-gated loop on the `strategy` skill (creates/maintains STRATEGY.md: target problem, approach, users, metrics, tracks; surfaces drift). Smallest Tier-A target (503L). FINALIZE `optimization/strategy/` (evals incl. lever scoring eval + fixtures) → baseline (extended schema) → trim + ≥1 quality lever → ratchet → log → regen mirror → CHANGELOG line.

**Size:** S/M (smallest target)
**Files:** `optimization/strategy/{README.md,evals.md,test-inputs.md,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-strategy/{SKILL.md,references/strategy-template.md,references/interview.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/capture/`. Extended `results.tsv` schema. **Finalize evals (incl. the lever scoring eval) BEFORE baseline (Major-B).**
- **Run permission + isolation (Major-1/C):** strategy writes STRATEGY.md — write-capable child confined to a throwaway `git worktree` (read-only w.r.t. the real repo) with a frozen repo-context / rough-direction input staged in; emit the STRATEGY.md sections it would write; score section completeness + drift-surfacing; discard worktree.
- **Interactive protocol (Major-D):** strategy asks multiple `AskUserQuestion` prompts — supply a **canned answer queue** mapping each prompt to a frozen answer, recorded in the suite fixture; no unanswered prompt may block the run.
- **Frozen inputs:** real repo-context snapshots / rough direction statements (this repo's own STRATEGY.md history is a rich source; format/flow-specific so flow-next history alone is acceptable). Scrub + freeze.
- **Accuracy evals (≥2-3):** required sections present (target problem, approach, users, metrics, tracks); no fabricated metrics (grounded in the input); drift-surfacing fires when input conflicts with an existing track.
- **Quality lever (blind spot):** a diagnosed miss (e.g. non-measurable metrics, or tracks lacking a decision rationale) — scoring eval finalized above; try a LEAN cue; keep only if it rises.

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — loop + accuracy guard
- `optimization/capture/` — suite template
- `plugins/flow-next/skills/flow-next-strategy/SKILL.md` — prose being optimized (bulk, 266L)
Optional:
- `plugins/flow-next/skills/flow-next-strategy/references/strategy-template.md`

## Key context
- Frozen grammars: strategy's section headers / track format (`### <track-name>` H3) — assert unchanged (plan + other skills parse `tracks` from this shape).
- Smallest target — expect fewer trim opportunities; a trim-that-holds + one honest quality lever is a complete loop here.

## Acceptance
- [ ] `optimization/strategy/` committed with the FINAL eval set (≥2-3 `[ACCURACY]` + lever scoring eval) + frozen inputs (R1, Major-B)
- [ ] Fixtures scrubbed — scoped privacy grep clean (R1)
- [ ] Baseline row 0 (extended schema) under the FINAL eval set before any mutation; write-capable child in a worktree; canned answer queue covers every `AskUserQuestion` (R2, Major-B/C/D)
- [ ] ≥1 trim + ≥1 quality-lever experiment; kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Frozen section-header / track-format grammar unchanged (R5)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed; `pytest` + `strategy_smoke_test.sh` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
