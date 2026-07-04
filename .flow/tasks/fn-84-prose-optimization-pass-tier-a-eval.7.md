---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Run the eval-gated loop on the `qa` skill's PROSE SURFACES: scenario derivation (from spec AC / R-IDs / boundaries) + bug-filing (P0/P1/P2 findings with evidence). BOOTSTRAP `optimization/qa/`, baseline (extended schema), trim + ≥1 quality lever, ratchet, log, regen mirror, CHANGELOG line. Scoring is on the prose outputs — NOT on driving a live app.

**Size:** M
**Files:** `optimization/qa/{README.md,evals.md,fixtures/*,results.tsv,changelog.md,baseline/*}`; `plugins/flow-next/skills/flow-next-qa/{SKILL.md,workflow.md,references/qa-discipline.md,references/bug-filing.md,references/autonomy.md}` (mutations); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- Clone suite shape from `optimization/make-pr/`. Extended `results.tsv` schema.
- **Run-trick (no worktree — prose scoring, no `.flow/` write):** (a) scenario derivation — stage a frozen spec (AC + R-IDs + boundaries) as a fixture, dispatch a read-only subagent given the qa scenario-derivation prose, score scenario coverage vs the spec's R-IDs; (b) bug-filing — stage canned findings/evidence, run the bug-filing prose, score P0/P1/P2 severity + evidence-not-narration discipline.
- **Frozen inputs:** real spec bodies + canned finding sets, PLUS ≥1 sanitized NON-flow-next app spec (Major-2 — scenario derivation is code-aware and overfits to flow-next specs otherwise). Scrub + freeze.
- **Accuracy evals (≥2-3):** scenario coverage vs spec R-IDs; severity-classification correctness (P0/P1/P2); evidence-discipline (never asserts PASS from source narration — evidence-grounded only).
- **Quality lever (blind spot):** scenario-derivation completeness (boundary/negative scenarios under-derived) — its boundary-coverage scoring eval is part of the FINAL eval set authored BEFORE baseline (Major-B); try a LEAN boundary-scenario cue; keep only if coverage rises.
- Permission model: output-only (read-only) child — qa scores prose, writes nothing; inputs staged as fixtures so no `AskUserQuestion` blocks (C/D covered).

## Investigation targets
Required:
- `agent_docs/optimizing-skills.md` — loop + accuracy guard
- `optimization/make-pr/` — fixture-shaped suite template
- `plugins/flow-next/skills/flow-next-qa/workflow.md` (589L) + `references/bug-filing.md`
Optional:
- `plugins/flow-next/skills/flow-next-qa/references/qa-discipline.md`

## Key context
- Frozen grammars: `qa_verdict` receipt; `SHIP/NA/BLOCKED/NEEDS_WORK` tokens; `P0/P1/P2` taxonomy — assert unchanged.
- qa is FORBIDDEN from marking PASS by reading source — the evidence-discipline eval must protect this exact property through any trim.

## Acceptance
- [ ] `optimization/qa/` committed with ≥2-3 `[ACCURACY]` evals (coverage, severity, evidence-discipline) + frozen inputs incl. ≥1 non-flow-next fixture (R1)
- [ ] Fixtures scrubbed — privacy grep clean (R1)
- [ ] Baseline row 0 (extended schema) scored under the FINAL eval set before any mutation (R2, Major-B)
- [ ] ≥1 trim + ≥1 quality-lever (with scoring eval); kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Frozen `qa_verdict` / severity tokens unchanged; evidence-discipline preserved (R5)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed; `pytest` (incl. `test_qa_smoke.py`, `test_qa_receipt.py`) + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
