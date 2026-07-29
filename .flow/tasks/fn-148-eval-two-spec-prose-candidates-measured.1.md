---
satisfies: [R1, R2, R3, R6, R7]
---
# fn-148-eval-two-spec-prose-candidates-measured.1 Pre-register study, stratified fixtures, arms (agent-evals)

## Description
Stand up the study in `~/work/agent-evals` (private repo, NOT this repo): pre-registration committed before any draw, stratified fixtures, arm files. Mirrors `studies/spec-format-2026-07`; reuse `lib/evalkit.py` and follow `METHODOLOGY.md` (all five rules).

**Size:** M

**Files (all in ~/work/agent-evals):**
- `studies/spec-prose-<YYYY-MM>/PREREGISTER.md` (FIRST commit of the study)
- `studies/spec-prose-<YYYY-MM>/README.md`, `evals.md`, `briefs/`, `keys/`, `arms/`
- `docs/fixtures.md` (register new fixtures by SHA with leak-check greps)

### Approach

- PREREGISTER.md declares: single primary endpoint, decision thresholds (screen -> paired replication with >=3 draws/cell, INCONCLUSIVE as a first-class branch), which cuts will not be reported, and that a positive result licenses only a follow-up spec proposing the template prose change with measured cost.
- Fixtures stratified by shape: >=2 bug/root-cause, >=2 greenfield/feature. Reuse F1/F2/F3 where they fit; mine at least one new fixture for the gap. Prerequisite baseline: fixtures authored under post-fn-147 behavior so the baseline arm already carries criteria tags.
- Arms A0 / M / V / MV generated from ONE shared preamble string; verify byte-identity of the shared part (`gen_arms.py` pattern).
- Keys: every candidate item passes "would a different competent implementation be marked wrong?" - if yes, drop or re-key to the guarantee. Label FLOOR vs DISC. Do not resurrect the invalidated items (F1 L9, F3 M4, F3 M9).
- Eval design guards (predeclared, rule 5): measured-claims eval credits only numbers traceable to a checkable source (never bare precision); verified-facts eval includes a discrimination check failing uniform marking; spec size measured on both axes per arm.

### Key context

Expect a null; budget for it. Nothing in flow-next changes in this spec regardless of outcome.

## Acceptance
- [ ] PREREGISTER.md committed to agent-evals BEFORE any draw exists, with endpoint, thresholds, unreported cuts, and licensing statement
- [ ] Fixture register: >=2 bug-shaped + >=2 greenfield, SHAs recorded, leak-check greps pass, post-fn-147 baseline noted
- [ ] Arm files A0/M/V/MV generated from one preamble; shared-part byte-identity verified and recorded
- [ ] Keys labelled FLOOR/DISC; every DISC item survives the competent-alternative test; invalidated items stay dropped
- [ ] Measured-claims traceability guard and verified-facts discrimination guard written into evals.md before scoring


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
