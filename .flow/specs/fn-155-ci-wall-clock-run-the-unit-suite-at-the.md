# CI wall-clock: run the unit suite at the parallelism the runner actually has

## Overview

`scripts/run_tests_parallel.py` defaults to `max(1, cpu_count - 2)` workers. Reserving two cores is right on a machine a human is typing on, and pure waste on a dedicated CI runner with nothing else to do. A 16-core laptop gets `jobs=14`; the GitHub runner reports `jobs=2`.

Every pull request touching `plugins/flow-next/**` pays that, four matrices at a time. This spec spends the idle cores. It does **not** run fewer tests.

## Quick commands

Compare the two job counts locally (the runner is subprocess-bound, so this is a real proxy):

```bash
python3 scripts/run_tests_parallel.py --jobs 2
python3 scripts/run_tests_parallel.py
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

## Goal & Context
<!-- scope: business -->

Measured on PR #285's four legs, with the parallel runner's own reported wall alongside the whole job:

| matrix | runner step | whole job | runner share |
|---|---|---|---|
| ubuntu-latest 3.11 | 367s (`jobs=2`) | 777s | 47% |
| ubuntu-latest 3.x | - | 971s | - |
| macos-latest 3.11 | - | 833s | - |
| windows-latest 3.11 | - | 974s | - |

The same suite runs in **131s locally at `jobs=14`**.

**The honest ceiling: the unit-test step is roughly half of a leg, not all of it.** Ten smoke scripts run sequentially after it, unconditionally (`if: always()`), plus the Cursor install verification - none of which this spec touches. Halving the runner step on the ubuntu leg saves roughly 3 minutes of 13, not 13 of 13. That is still the single largest lever available for one small change, and it compounds across four legs on every PR, but the spec must not be sold as collapsing CI time.

This is **not** a test-selection problem and must not become one. Skill prose is genuinely covered (docs inventory, prompt-text SHA pinning, Codex mirror parity), and a "docs are cheap, skip CI" filter would disable exactly the guards that catch prose regressions - PR #285 shipped a broken changelog assertion that only the full suite caught. The suite keeps running in full. It should just stop leaving half the runner idle.

## Architecture & Data Models
<!-- scope: technical -->

**The runner is subprocess-bound, which is why job count maps to real parallelism.** `run_tests_parallel.py:228-245` uses a `ThreadPoolExecutor(max_workers=jobs)`, but each submitted unit is `_run_one()` (`:99-149`), which shells out to `subprocess.run([sys.executable, "-m", "unittest", "discover", ...])`. The threads only block on those processes, so `jobs` is the count of concurrent OS-level interpreters - exactly the thing a runner's core count gates. Result ordering is index-mapped (`:229-245`) and independent of worker count, so nothing about output or aggregation changes.

**Chosen mechanism: CI detection inside `_default_jobs()`** (`run_tests_parallel.py:65-67`). When the process is running non-interactively on a build machine, use the full `cpu_count`; otherwise keep `cpu_count - 2`. The reservation then says what it always meant - *leave room for whoever else is using this machine* - rather than assuming a human is always present.

**Why not have the workflow pass `--jobs` explicitly.** It works, but it puts a platform-conditional core-count expression across three OS legs, and it edits the exact 30-line CI step that fn-120 (Windows test-corpus sweep) owns for its `EXCLUDES` block (`.github/workflows/test-flow-next.yml:132-149`). Keeping the change inside one Python function touches no YAML at all, shrinks the collision surface to nothing, and fixes any other automation that shells out to the runner.

**This establishes a new precedent, deliberately.** The repo has no existing "detect CI, behave differently" pattern - the one live convention is `RUNNER_OS`, and it only ever branches on operating system (`.github/workflows/test-flow-next.yml:134`, `prospect_smoke_test.sh:740`, `impl-review_smoke_test.sh:553`). A new environment-keyed branch therefore needs its rationale written at the site, not just in this spec.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a CI runner the unit suite runs at the runner's full core count; on a developer machine the default still reserves headroom. The chosen signal and the reservation's rationale (*it exists for machines with a human on them*) are documented in a comment at `_default_jobs()`.
- **R2:** Wall-clock is **measured, not assumed**: record the runner step's own reported `wall=`/`jobs=` line and the whole-job duration for all four matrices, before and after, on the same commit. Ship only if the Linux and macOS legs clearly improve. If a leg does not improve, record that in the spec's Decision Context rather than quietly claiming a win.
- **R3:** Coverage is unchanged - same discovered file set, same test count (`files=178 ran=3846` at time of writing, allowing for tests added since), same excludes, same shuffle behavior, same exit-code contract. No path-based test selection is introduced.
- **R4:** `--jobs` and `--serial` keep working as explicit overrides and still win over auto-detection, in that precedence order (`--serial` beats `--jobs` beats the default, as today at `:350-359`). A `--jobs` value below 1 is still rejected.
- **R5:** `scripts/run_tests_parallel.py` gains its first tests. `_default_jobs()` is covered for: interactive default, CI default, and the flag-precedence chain. There is no existing coverage of this file to extend - `grep -rn "import run_tests_parallel"` returns nothing - so the task creates the test module.
- **R6:** Every place that states the old default is updated in the same change: the module docstring (`:5-6`), the `--jobs` help string (`:304`), and the workflow comment (`.github/workflows/test-flow-next.yml:121`). The stale "the full suite runs 14 jobs in parallel" comment in `plugins/flow-next/tests/test_spec_id_allocation.py:495-506` is corrected too - its skip heuristic is live-computed and unaffected, but the prose is laptop-specific and would mislead. **Frozen surfaces are NOT edited:** the shipped `CHANGELOG.md:789` entry and `.flow/specs/fn-119-*.md` are historical records.

## Boundaries
<!-- scope: business -->

- **No test selection, no path filters, no "docs skip CI".** The full suite keeps running on every triggering change. This spec is about idle cores, not about running less.
- **No larger runners, no self-hosted runners, no paid tiers.** Free-tier runners only.
- **No sharding across CI jobs.** Splitting the suite into parallel GitHub jobs is a different, larger change. If R2's measurement shows parallelism alone is not enough, capture that as a follow-up rather than growing this spec.
- **No change to the workflow's trigger paths.** They are deliberately in step with the ruff lint scope (comment at `.github/workflows/test-flow-next.yml:22`).
- **The smoke-script tail is out of scope.** The ten sequential `if: always()` smoke scripts after the unit step are most of the remaining leg time; speeding them up is separate work.
- **No `--jobs` in the workflow invocation.** Chosen deliberately to keep fn-120's CI-step surface untouched.

## Decision Context
<!-- scope: both -->

**Why not narrow what runs.** The obvious reaction to "16 minutes for a docs change" is to stop running tests for docs changes. PR #285 is the counter-example: the failure CI caught there *was* in prose (a changelog assertion pinned by `test_chart_docs_inventory`), and the guards that catch prose regressions live in the same suite as everything else. Narrowing the trigger would have let it through.

**Why the Windows number is a warning, not a target.** Windows took 974s against ubuntu's 777s. The gap is process-spawn overhead - and this runner spawns one interpreter per test file - so more workers will not close it proportionally. Expect Linux and macOS to improve most, and do not write a changelog claim that outruns the measurement.

**The core-count claim is derived, not documented.** Nothing in this repo documents GitHub-hosted runner core counts. `jobs=2` in the CI log implies `cpu_count == 4` through `max(1, cpu_count - 2)`; that is an inference from observed behavior, and R2's measurement is what actually settles the win. Do not restate "4-core runner" as a fact.

**Open question for implementation:** whether the suite is CPU-saturated at full core count or still spawn-dominated. R2's before/after is the cheapest way to find out, and the answer decides whether CI-job sharding is worth a follow-up.

## Early proof point

Task fn-155-ci-wall-clock-run-the-unit-suite-at-the.1 is the whole behavior change and its first-ever tests. If R2's measurement on the real matrices shows no meaningful Linux/macOS improvement, stop and record it: the conclusion would be that the suite is spawn-dominated rather than core-starved, which redirects the effort to the smoke-script tail or to job sharding instead of shipping a change that buys nothing.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Full cores on CI, headroom locally, rationale at the site | .1 | - |
| R2 | Measured before/after on all four matrices | .1 | - |
| R3 | Coverage unchanged | .1 | - |
| R4 | `--jobs` / `--serial` precedence intact | .1 | - |
| R5 | First tests for the parallel runner | .1 | - |
| R6 | Stale default documented in step; frozen surfaces untouched | .1 | - |

## References

- `scripts/run_tests_parallel.py:65-67` `_default_jobs()`; `:99-149` `_run_one()` (subprocess shell-out); `:228-245` ThreadPoolExecutor; `:299-310` `--jobs` / `--serial`; `:350-359` precedence; `:5-6` docstring; `:304` help string
- `.github/workflows/test-flow-next.yml:118-151` the unit-test step (`:121` the stale comment, `:151` the invocation); `:57-70` the four-matrix definition; no `timeout-minutes` anywhere in the file
- `.github/workflows/test-flow-next.yml:161-249` the Cursor install smoke + ten sequential `if: always()` smoke scripts that make up the rest of a leg
- `plugins/flow-next/tests/test_spec_id_allocation.py:495-506` the stale "14 jobs" comment
- Overlap risk: fn-120 owns `.github/workflows/test-flow-next.yml:132-149` and `run_tests_parallel.py:99` `_run_one()`. No dependency edge; do not implement both concurrently on parallel branches.
