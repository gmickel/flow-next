---
satisfies: [R7]
---
# fn-155-ci-wall-clock-run-the-unit-suite-at-the.2 Measure p95 budgets on CPU time so parallelism cannot make them flaky

## Description
R2's measurement surfaced a regression the plan did not anticipate: raising the CI job count makes a wall-clock latency-budget test **intermittently** fail on Windows.

Observed on the `legacy_baseline=false` leg of measurement wave 2 (run 30719512156, `jobs=4`):

```
FAIL: test_validation_plus_render_p95_under_100_ms_for_30_warm_runs
AssertionError: 167.89329999994607 not less than 100 : p95=167.893 ms
```

It passed at `jobs=2` in both baseline runs and at `jobs=4` in wave 1, so it is intermittent rather than a clean break - the worst shape, because it costs time on unrelated PRs.

**Root cause: the budget is measured on the wrong clock.** `time.perf_counter()` is wall time, so with four sibling interpreters competing for four Windows cores it measures scheduler contention, not the cost of the operation. The operation is pure in-memory rendering with no I/O, so process CPU time is both the honest measure and immune to sibling load.

**Fix both p95 budgets, not just the one that failed.** `test_review_findings_receipts.py` has the identical shape (30 warm runs, `sorted(...)[28]`, `perf_counter`) and is the same landmine one unlucky scheduling window away. `test_spec_id_allocation.py` also uses `perf_counter` but takes `min(samples)`, which is already contention-robust - leave it alone.

Record the clock in the pinned metadata rather than changing it silently: `golden.meta.json`'s `performanceBudget` gains an explicit clock field, and the test's exact-dict assertion is updated in the same commit so the fixture and the assertion cannot drift.

**Size:** S
**Files:** `plugins/flow-next/tests/test_pr_cognitive_aid.py`, `plugins/flow-next/tests/test_review_findings_receipts.py`, `plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.meta.json`

### Approach

- `time.process_time()` measures CPU time consumed by this process and does not tick while descheduled, so it is unaffected by how many sibling test processes are running.
- Keep the 100ms budget. On an unloaded machine CPU time is approximately the current wall time, so the budget still bites on a genuine regression; it just stops firing on contention.
- The `sha256` field in `golden.meta.json` hashes `golden.json`, NOT the meta file, so adding a key to `performanceBudget` does not invalidate it. Verify that assertion still passes.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/tests/test_pr_cognitive_aid.py:34-39` - `assert_strict_30_sample_p95_under_budget`
- `plugins/flow-next/tests/test_pr_cognitive_aid.py:752-786` - the failing test, its metadata exact-dict assertion, and the warm-up loop
- `plugins/flow-next/tests/test_review_findings_receipts.py:1250-1267` - the identical p95 shape
- `plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.meta.json` - the pinned `performanceBudget` block

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_spec_id_allocation.py:529-540` - the `min(samples)` variant that needs no change, for contrast

### Key context

Do NOT raise the budget number to make the failure go away. The budget is a real performance guard; the defect is the clock it is measured on. Raising it would weaken the guard on every platform to work around contention on one.

Do NOT skip the test on Windows or under CI. That trades a flaky signal for no signal.

`golden.json` itself is a pinned fixture - do not touch it. Only the meta file's `performanceBudget` block changes.

### Acceptance
- [ ] Both 30-sample p95 budgets measure `time.process_time()` instead of `time.perf_counter()`
- [ ] A comment at each site states why: a wall-clock p95 under parallel test execution measures scheduler contention, not the operation
- [ ] `golden.meta.json`'s `performanceBudget` names the clock explicitly, and the test's exact-dict assertion is updated to match in the same commit
- [ ] The `sha256` assertion against `golden.json` still passes (the meta file's hash field covers the artifact, not itself)
- [ ] The 100ms budget is unchanged; no test is skipped or made conditional on platform or CI
- [ ] `test_spec_id_allocation.py`'s `min(samples)` timing is left untouched
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_pr_cognitive_aid test_review_findings_receipts -q` green, and green again under `python3 scripts/run_tests_parallel.py` at full local parallelism

## Acceptance
- [ ] Both p95 budgets use process CPU time, not wall clock
- [ ] Rationale comment at each site
- [ ] Clock named in golden.meta.json; exact-dict assertion updated in the same commit
- [ ] golden.json sha256 assertion still passes
- [ ] Budget unchanged at 100ms; nothing skipped or platform-conditional
- [ ] min(samples) timing in test_spec_id_allocation untouched
- [ ] Focused suites green, and green under full-parallelism run


## Done summary
Both 30-sample p95 budget tests (test_pr_cognitive_aid, test_review_findings_receipts) now sample time.process_time() instead of time.perf_counter(), with a rationale comment at each site: under parallel test execution a wall-clock p95 measures scheduler contention between sibling interpreters, not the pure in-memory operation. The 100ms budget, warm-up loop, and sample count are unchanged, nothing is skipped or platform-conditional, and test_spec_id_allocation's min(samples) timing is untouched. golden.meta.json's performanceBudget now names the clock ("clock": "time.process_time") and both exact-dict assertions on that block (test_pr_cognitive_aid and test_pr_cognitive_aid_fixture_contract) were updated in the same commit; the golden.json sha256 assertion still passes. pr-cognitive-aid.md documents the clock for downstream vendoring consumers.
## Evidence
- Commits: f8ebdf0ee7c5399fe866d8670917120bcfd9bd4c
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_pr_cognitive_aid test_review_findings_receipts test_pr_cognitive_aid_fixture_contract -q, python3 scripts/run_tests_parallel.py (files=179 ran=3863 failures=0 errors=0 wall=149.40s jobs=14), uvx ruff@0.16.0 check .
- PRs: