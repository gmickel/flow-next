# fn-32-opt-in-review-flags.5 Smoke tests + Ralph regression verification

## Description

Extend impl-review smoke tests to cover the three new flags and verify Ralph regression-free operation.

**Size:** S

**Files:**
- `plugins/flow-next/scripts/impl-review_smoke_test.sh` (extend if exists; create if not)
- No changes expected to `ralph_smoke_test.sh` — verify it passes unchanged

## Smoke test cases

Add to `impl-review_smoke_test.sh`:

### Case 1: default review (regression check)

Run `impl-review` with no flags on a synthetic branch with a known minor bug. Verify:
- Primary review runs
- Verdict + receipt produced in legacy shape
- No validator / deep_passes / walkthrough fields in receipt

### Case 2: --validate

Run `impl-review --validate` on branch with two contrived findings (one real, one false-positive — e.g., flagged null-deref that's actually guarded). Verify:
- Validator pass runs after primary
- False-positive dropped in receipt's `validator.reasons`
- Verdict reflects surviving finding
- If only real finding remains: verdict = NEEDS_WORK; if false-positive was the only finding, verdict upgrades to SHIP

### Case 3: --deep

Run `impl-review --deep` on branch touching auth files. Verify:
- Adversarial pass runs (always)
- Security pass auto-enables
- Performance pass does NOT auto-enable (no perf-sensitive paths touched)
- Receipt has `deep_passes: ["adversarial", "security"]`

### Case 4: --deep=performance explicit

Run `impl-review --deep=performance` on non-perf-sensitive diff. Verify:
- Only performance pass runs
- Receipt has `deep_passes: ["performance"]`

### Case 5: --interactive Ralph-block

Set `FLOW_RALPH=1`; run `impl-review --interactive`. Verify:
- Exits with code 2
- Error message mentions Ralph incompatibility
- No review invoked

### Case 6: combination (--validate --deep)

Run `impl-review --validate --deep` on branch. Verify:
- Phase order: primary → deep → validate
- Receipt has both `validator` and `deep_passes` fields
- Merged + validated findings drive verdict

### Case 7: env-var opt-ins

- Set `FLOW_VALIDATE_REVIEW=1`; run without `--validate`; verify validator runs.
- Set `FLOW_REVIEW_DEEP=1`; run without `--deep`; verify deep runs (adversarial + auto-enables).
- Unset both; run; verify neither runs.

## Ralph regression verification

Run `plugins/flow-next/scripts/ralph_smoke_test.sh` **4 times** under different environments:

1. Baseline: no flags, no env vars — should pass unchanged.
2. `FLOW_VALIDATE_REVIEW=1 ralph_smoke_test.sh` — should pass; receipts carry validator data.
3. `FLOW_REVIEW_DEEP=1 ralph_smoke_test.sh` — should pass; receipts carry deep_passes data.
4. Both env vars set — should pass; receipts carry both.

**Expected:** all 4 runs succeed with the same number of Ralph iterations and same final state. Receipt shape varies but Ralph gate logic (which reads verdict) works identically.

Document results in the task PR: "Ralph smoke: 4/4 configurations passing."

## Acceptance

- **AC1:** `impl-review_smoke_test.sh` covers 7 cases above.
- **AC2:** Each case verifies receipt shape + verdict + expected behavior.
- **AC3:** Ralph smoke test passes under all 4 env-var configurations.
- **AC4:** Test fixtures use contrived diffs (small, reproducible) — not real project state.
- **AC5:** Smoke tests complete in under 2 minutes total.
- **AC6:** Test failures produce actionable error messages (not just "assertion failed").

## Dependencies

- fn-32-opt-in-review-flags.1, .2, .3, .4 (all flags implemented)

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
