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

<!-- Updated by plan-sync: fn-32.1 validator block contains dispatched/dropped/kept/reasons; upgrade path only fires NEEDS_WORK → SHIP and records verdict_before_validate. -->

Run `impl-review --validate` on branch with two contrived findings (one real, one false-positive — e.g., flagged null-deref that's actually guarded). Verify:
- Validator pass runs after primary (invoked via `flowctl <backend> validate --findings-file ... --receipt ...`)
- False-positive dropped: `receipt.validator.reasons[]` contains entry with matching id / file / line / reason
- Receipt carries `validator.dispatched` + `validator.dropped` + `validator.kept` counts + `validator_timestamp`
- Verdict reflects surviving finding
- If only real finding remains: verdict = NEEDS_WORK; `validator.kept == 1`, no `verdict_before_validate` field
- If false-positive was the only finding: verdict upgrades to SHIP, `validator.kept == 0`, `verdict_before_validate == "NEEDS_WORK"` recorded

### Case 3: --deep

<!-- Updated by plan-sync: fn-32.2 receipt carries `deep_findings_count`, `cross_pass_promotions`, `deep_timestamp` alongside `deep_passes`. Skill uses `flowctl review-deep-auto` against the changed-file list for auto-enable. -->

Run `impl-review --deep` on branch touching auth files. Verify:
- Adversarial pass runs (always)
- Security pass auto-enables (via `flowctl review-deep-auto` glob match)
- Performance pass does NOT auto-enable (no perf-sensitive paths touched)
- Receipt has `deep_passes: ["adversarial", "security"]`
- Receipt has `deep_findings_count` object keyed by pass name
- Receipt has `cross_pass_promotions` array (may be empty) and `deep_timestamp`
- If deep surfaces a new blocking `introduced` finding and primary was SHIP, receipt carries `verdict_before_deep == "SHIP"` and final `verdict == "NEEDS_WORK"`

### Case 4: --deep=performance explicit

Run `impl-review --deep=performance` on non-perf-sensitive diff. Verify:
- Only performance pass runs (explicit CSV overrides auto-enable)
- Receipt has `deep_passes: ["performance"]`
- Receipt has `deep_findings_count: {"performance": <n>}`

### Case 5: --interactive Ralph-block

Set `FLOW_RALPH=1`; run `impl-review --interactive`. Verify:
- Exits with code 2
- Error message mentions Ralph incompatibility
- No review invoked

### Case 6: combination (--validate --deep)

Run `impl-review --validate --deep` on branch. Verify:
- Phase order: primary → deep → validate
- Receipt has both `validator` and `deep_passes` fields
- Receipt also has `deep_findings_count`, `cross_pass_promotions`, `deep_timestamp` (deep phase) and `validator_timestamp` (validator phase)
- Merged + validated findings drive verdict

### Case 7: env-var opt-ins

- Set `FLOW_VALIDATE_REVIEW=1`; run without `--validate`; verify validator runs.
- Set `FLOW_REVIEW_DEEP=1`; run without `--deep`; verify deep runs (adversarial + auto-enables).
- Unset both; run; verify neither runs.

## Ralph regression verification

Run `plugins/flow-next/scripts/ralph_smoke_test.sh` **4 times** under different environments:

1. Baseline: no flags, no env vars — should pass unchanged.
2. `FLOW_VALIDATE_REVIEW=1 ralph_smoke_test.sh` — should pass; receipts carry validator data.
3. `FLOW_REVIEW_DEEP=1 ralph_smoke_test.sh` — should pass; receipts carry `deep_passes`, `deep_findings_count`, `cross_pass_promotions`, `deep_timestamp` data.
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
