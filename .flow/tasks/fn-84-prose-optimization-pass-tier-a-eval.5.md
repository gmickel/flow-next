---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Run the eval-gated loop on the `audit` skill (memory garbage-collector: Keep/Update/Consolidate/Replace/Delete per entry). FINALIZE `optimization/audit/` (evals incl. lever scoring eval + answer-key fixture) → baseline (extended schema) → trim + ≥1 quality lever → ratchet → log → regen mirror → CHANGELOG line. Audit is FINDER-SHAPED → over-flag guard mandatory.

**Size:** M
**Files:** `optimization/audit/{README.md,evals.md,fixtures/*,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-audit/{SKILL.md,phases.md,workflow.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/make-pr/` (fixture-shaped input suits audit). Extended `results.tsv` schema. **Finalize evals (incl. the Consolidate-vs-Delete scoring eval) BEFORE baseline (Major-B).**
- **Run permission + isolation (Major-1/C):** audit mutates memory (`memory mark-stale` etc.) — write-capable child confined to a throwaway `git worktree` (read-only w.r.t. the real repo) with a frozen COPY of a `.flow/memory/` snapshot + codebase state staged in; emit per-entry Keep/Update/Consolidate/Replace/Delete verdicts; score vs a hand-labeled answer key; discard worktree.
- **Interactive protocol (Major-D):** audit defaults interactive — run with `mode:autofix` (non-interactive, documented), recorded in the suite README; any residual prompt gets a canned fixture answer.
- **Frozen inputs:** real memory stores (SCRUB private data — memory holds real names/keys; freeze copies).
- **Accuracy evals (≥2-3):** classification correctness vs the answer key; **over-flag guard on a CLEAN corpus** (current/valid memory → zero false "stale/delete"); no silent deletion of a valid entry.
- **Quality lever (blind spot):** Consolidate-vs-Delete discrimination — scoring eval finalized above; try a LEAN discriminator; keep only if classification-accuracy rises.

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — loop + accuracy guard + over-flag guard for finders
- `optimization/make-pr/` — fixture-shaped suite template
- `plugins/flow-next/skills/flow-next-audit/workflow.md` — prose being optimized (bulk, 863L)
Optional:
- `plugins/flow-next/docs/memory-schema.md` — the classification taxonomy audit applies

## Key context
- Finder-shaped: false-missing = 0 AND finding-rate ≈ baseline on the clean corpus — the over-flag guard is the ratchet's teeth here.
- Frozen grammars: audit's classification labels + any receipt — assert unchanged.
- Memory snapshots are the HIGHEST private-data risk in this spec — scrub hard, grep before commit.

## Acceptance
- [ ] `optimization/audit/` committed with the FINAL eval set (≥2-3 `[ACCURACY]` incl. answer-key classification + lever scoring eval) + frozen inputs (R1, Major-B)
- [ ] Fixtures scrubbed — scoped privacy grep clean over `optimization/audit/` (highest-risk: real memory names/keys) (R1)
- [ ] Baseline row 0 (extended schema) under the FINAL eval set before any mutation; write-capable child in a worktree against a COPIED memory snapshot; `mode:autofix` (no hang) (R2, Major-B/C/D)
- [ ] ≥1 trim + ≥1 quality-lever experiment; kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Over-flag guard on a CLEAN corpus: false-missing = 0, finding-rate ≈ baseline (R4)
- [ ] Frozen classification labels unchanged; no relocated consuming-phase tables (R5)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed; `pytest` + `audit_smoke_test.sh` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
