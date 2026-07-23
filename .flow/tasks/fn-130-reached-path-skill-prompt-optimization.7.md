---
satisfies: [R2, R8, R12]
---
# fn-130-reached-path-skill-prompt-optimization.7 Gate Plan optional paths and trim examples

## Description
Move Plan tracker, HTML artifact, and review-only material behind explicit branch reads and apply the already promising examples trim. Re-baseline on the canonical current skill and add a sealed holdout so the examples mutation does not overfit P4.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/{SKILL.md,steps.md,examples.md,references/*.md}`, `optimization/plan/**`, route fixtures/tests including `test_skill_prose_diet.py`, corresponding Codex mirror.

### Approach
- Preserve Step 0 single config snapshot, Flow/tracker handle recognition, readiness, all depth-appropriate scouts, spec template, R-ID coverage, task sizing/waves, and user-authored spec overrides.
- Gate tracker sync, HTML lens, and selected review machinery only after their existing config/choice signals.
- Replace the two oversized BAD implementation examples with shorter anti-pattern anchors without weakening the no-implementation rule.
- Reuse P1–P4 and add a sealed non-flow-next/no-code/research/Mermaid holdout authored before the candidate is scored.
- Use paired baseline/candidate runs; do not claim wall-time improvement from noisy runs.

### Frozen fixtures
- P1 flow-native; P2 DocIQ FastAPI/OOXML; P3 hand-edited spec; P4 ordering/sizing.
- New sealed holdout: no-code architecture plan with research bundle, task cohesion/dependencies, R-ID table, Mermaid condition, tracker/HTML/review branches on and off.
- Readiness ready/unready, autonomous, tracker configured/unconfigured, HTML disabled/enabled, review none/selected.

### Investigation targets
**Required**
- `optimization/plan/README.md` and `results.tsv` — current baseline, contamination caveat, and ratchet.
- `plugins/flow-next/skills/flow-next-plan/steps.md:615-661` — existing optional HTML gate.
- `plugins/flow-next/skills/flow-next-plan/examples.md` — measured candidate surface.
- `plugins/flow-next/tests/test_skill_prose_diet.py:118-153` — one-snapshot/create-path invariants.
- `.flow/specs/fn-118-work-skill-sanctioned-parallel-worker.md` — task DAG/wave semantics.

**Optional**
- `plugins/flow-next/templates/spec.md` and spec-template discovery reference.

## Acceptance
- [ ] Task input prompt hashes match version-adjusted `V1/B1`; every structural candidate compares against `B1`, never original `B0`.
- [ ] Current-main baseline plus sealed holdout are recorded before the examples mutation; answer key is not visible to the subject.
- [ ] Tracker, HTML, and review refs load only on selected paths; default planning retains one config snapshot and no added round trips.
- [ ] P1–P4 and holdout preserve R-ID/requirement coverage, user override, task sizing/cohesion/dependencies/waves, no implementation leakage, source grammar, and Mermaid behavior.
- [ ] Paired candidate runs meet the zero-loss ratchet and record deterministic reached-path and backend telemetry separately.
- [ ] Plan-specific prose/fixture/mirror tests pass and the Codex mirror keeps portable prompt/question behavior.
- [ ] If either examples or routing candidate regresses any cell, revert that mutation independently and retain its evidence.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
