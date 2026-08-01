# CI wall-clock: run the unit suite at the parallelism the runner actually has

## Overview

`scripts/run_tests_parallel.py` defaults to `max(1, cpu_count - 2)` workers. Reserving two cores is right on a machine a human is typing on, and pure waste on a dedicated CI runner with nothing else to do. A 16-core laptop gets `jobs=14`; the GitHub runner reports `jobs=2`.

Every pull request touching `plugins/flow-next/**` pays that, four matrices at a time. This spec spends the idle cores. It does **not** run fewer tests.

## Quick commands

Focused loop for the new runner tests (this is the implementation loop):

```bash
cd plugins/flow-next/tests && python3 -m unittest test_run_tests_parallel -v
```

R3 parity evidence - same corpus at two job counts, compare the `parallel-runner:` and `SUMMARY` lines:

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

**Chosen mechanism: CI detection inside `_default_jobs()`** (`run_tests_parallel.py:65-67`).

**The signal, exactly** (not "interactive" - TTY state is deliberately NOT part of this design, so a redirected local run behaves like any other local run):

```
ci = os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
jobs = cpu_count if ci else max(1, cpu_count - 2)
```

Absent, empty, `"false"`, `"0"`, and any unrecognized value all mean **local**. Mixed case is normalized. `CI` rather than `GITHUB_ACTIONS` because the scope is any build machine, not one vendor - every mainstream CI sets `CI=true`. The two cases are named **CI** and **local**; the word *interactive* appears nowhere in the implementation.

**Why the ordinary push/PR invocation stays unchanged.** The workflow could pass `--jobs` on every run, but that hard-codes a core-count policy into YAML across three OS legs and enlarges the diff against the CI step fn-120 owns for its `EXCLUDES` block (`.github/workflows/test-flow-next.yml:132-149`). Keeping the *policy* inside one Python function fixes any automation that shells out to the runner, not just this workflow.

**The workflow does gain one diagnostic lever, and only that.** R2 is unsatisfiable without it - see below. The YAML change is: a boolean `workflow_dispatch` input `legacy_baseline`, plus a conditional that prepends the legacy job count when it is set. Ordinary push and pull_request runs pass no `--jobs`, keep `SHUFFLE_ARGS` and `EXCLUDES` intact, and behave exactly as before. The YAML source necessarily changes - the guarantee is behavioral equivalence on those triggers, not byte identity of the file. The Windows `EXCLUDES` block at 132-149 is not touched.

**This establishes a new precedent, deliberately.** The repo has no existing "detect CI, behave differently" pattern - the one live convention is `RUNNER_OS`, and it only ever branches on operating system (`.github/workflows/test-flow-next.yml:134`, `prospect_smoke_test.sh:740`, `impl-review_smoke_test.sh:553`). A new environment-keyed branch therefore needs its rationale written at the site, not just in this spec.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On a CI runner the unit suite runs at the runner's full core count; on a developer machine the default still reserves headroom. The chosen signal and the reservation's rationale (*it exists for machines with a human on them*) are documented in a comment at `_default_jobs()`.
- **R2:** Wall-clock is **measured, not assumed**, and the measurement is **executable on one commit**. Adding CI detection makes every run from that SHA use the new behavior, so the baseline needs an explicit lever: a **boolean** `workflow_dispatch` input `legacy_baseline`. When true, the step computes the pre-change formula **on each runner** and passes it through the existing override:

  ```bash
  JOBS_ARGS=()
  if [ "$LEGACY_BASELINE" = "true" ]; then
    JOBS_ARGS=(--jobs "$(python -c 'import os; print(max(1, (os.cpu_count() or 2) - 2))')")
  fi
  python scripts/run_tests_parallel.py "${JOBS_ARGS[@]}" "${SHUFFLE_ARGS[@]}" "${EXCLUDES[@]}"
  ```

  The composed invocation is pinned: `JOBS_ARGS` is **added to** the existing `SHUFFLE_ARGS` and `EXCLUDES`, never replacing either. `legacy_baseline=true` together with `shuffle=true` is a valid combination and must still work - the ordering canary is not collateral damage of the measurement lever.

  Boolean, not a free-form integer: a `workflow_dispatch` string input is untrusted text, and interpolating it into a shell line invites both parsing surprises and malformed-value usage failures. A boolean carries no attacker-chosen text, and it is read via `env:` rather than direct `${{ }}` interpolation. **`--jobs 2` would NOT be a valid baseline** - the old default is `max(1, cpu_count - 2)`, and nothing here establishes that ubuntu, macOS, and Windows runners report the same core count. Computing the formula per-runner is exact by construction; one Python one-liner behaves identically on all three legs. Baseline = dispatch the branch head with `legacy_baseline=true`; after = dispatch the same head with it false.
  - **Decision rule (stated, not judged):** two dispatches per configuration x two configurations x four matrix rows = **16 raw results**. Take the **median of the two** runner-step `wall=` values per (configuration, matrix row). Ship only if the median improves by at least **25% on all three of `ubuntu-latest/3.11`, `ubuntu-latest/3.x`, and `macos-latest/3.11`** - both Ubuntu rows, named explicitly, not an aggregate - AND, computed the same way, **the median of the two baseline whole-job durations vs the median of the two after whole-job durations** regresses by more than 5% on none of **those same three rows**. Both metrics use median-of-two throughout - never a single run, a worst case, or a paired-run delta. `windows-latest/3.11` is measured and recorded in both tables but gates **neither** metric: it is excluded from the 25% improvement condition and from the 5% regression condition alike (see Decision Context).
  - **Evidence destination:** BOTH the task's done-summary evidence and the spec's `## Decision Context`, as two tables: **16 raw rows** (one per run - run URL, head SHA, matrix identity, configuration, `jobs=`, `wall=`, whole-job duration) and an **8-row aggregate** (one per configuration x matrix row) carrying the median `wall=`, the median whole-job duration, the percentage delta for each against its baseline counterpart, and both source run URLs, so every median is traceable to its inputs.
- **R3:** Coverage is unchanged, **proven rather than asserted**: run the suite at `--jobs 2` and at the auto default on the same corpus and compare the **sorted `--list-only` output** (the runner prints one filename per line) as well as the `parallel-runner: <n> file(s)` line and the `SUMMARY files=/ran=/failures=/errors=/skipped=` counts - all three must be identical. Counts alone are not proof: two different file sets can have the same file and test totals (`files=178 ran=3846` at time of writing, allowing for tests added since). The new test module additionally pins the contracts a job-count change could plausibly disturb: `--exclude` still drops exactly the named files and still prints its `EXCLUDED` line, a zero-match pattern still exits 2, and a failing file still exits 1. No path-based test selection is introduced.
- **R4:** `--jobs` and `--serial` keep working as explicit overrides and still win over auto-detection, in that precedence order (`--serial` beats `--jobs` beats the default, as today at `:350-359`). A `--jobs` value below 1 is still rejected.
- **R5:** `scripts/run_tests_parallel.py` gains its first tests. There is no existing coverage to extend (`grep -rn "import run_tests_parallel"` returns nothing), so the task creates the module. `_default_jobs()` is covered directly for the local default, the CI default, and the value semantics of `CI` (absent / empty / `"false"` / `"TRUE"` / `"0"`). **Precedence is covered at `main()`, not at the parser** - the chain lives at `:350-359`, after parsing, so a parser-level test cannot prove it. With `run_suite` and `_default_jobs` patched, assert: bare invocation calls `_default_jobs`; `--jobs 6` uses 6 and never calls `_default_jobs`; `--serial --jobs 6` resolves to 1; `--jobs 0` returns exit code 2 without running the suite.
- **R6:** Every place that states the old default is updated in the same change: the module docstring (`:5-6`), the `--jobs` help string (`:304`), and the workflow comment (`.github/workflows/test-flow-next.yml:121`). The stale "the full suite runs 14 jobs in parallel" comment in `plugins/flow-next/tests/test_spec_id_allocation.py:495-506` is corrected too - its skip heuristic is live-computed and unaffected, but the prose is laptop-specific and would mislead. **Frozen surfaces are NOT edited:** the shipped `CHANGELOG.md:789` entry and `.flow/specs/fn-119-*.md` are historical records.

## Boundaries
<!-- scope: business -->

- **No test selection, no path filters, no "docs skip CI".** The full suite keeps running on every triggering change. This spec is about idle cores, not about running less.
- **No larger runners, no self-hosted runners, no paid tiers.** Free-tier runners only.
- **No sharding across CI jobs.** Splitting the suite into parallel GitHub jobs is a different, larger change. If R2's measurement shows parallelism alone is not enough, capture that as a follow-up rather than growing this spec.
- **No change to the workflow's trigger paths.** They are deliberately in step with the ruff lint scope (comment at `.github/workflows/test-flow-next.yml:22`).
- **Maintainer-only CI tooling: no docs-site update.** This changes how the repo's own test runner schedules work on a build machine. It is invisible to anyone installing or running flow-next - no command, flag, config key, or output a user sees changes - so the `CLAUDE.md` docs-site rule for user-visible behavior does not apply. A root `## Unreleased` CHANGELOG entry is the whole release surface. Recorded here so the omission reads as a decision, not a miss.
- **The smoke-script tail is out of scope.** The ten sequential `if: always()` smoke scripts after the unit step are most of the remaining leg time; speeding them up is separate work.
- **No `--jobs` on ordinary push/PR runs.** Job-count policy lives in the runner, not in YAML. The one exception is the `legacy_baseline` dispatch lever R2 needs, which is inert unless explicitly dispatched and never fires on push or pull_request.

## Decision Context
<!-- scope: both -->

**Why not narrow what runs.** The obvious reaction to "16 minutes for a docs change" is to stop running tests for docs changes. PR #285 is the counter-example: the failure CI caught there *was* in prose (a changelog assertion pinned by `test_chart_docs_inventory`), and the guards that catch prose regressions live in the same suite as everything else. Narrowing the trigger would have let it through.

**Why Windows is measured but not gating.** Windows took 974s against ubuntu's 777s. The gap is process-spawn overhead - and this runner spawns one interpreter per test file - so more workers will not close it proportionally. That is why R2's ship condition names `ubuntu-latest/3.11`, `ubuntu-latest/3.x` and `macos-latest/3.11` only: holding Windows to the same threshold would block a change that genuinely helps the other three rows. Windows is still measured and recorded; it just does not gate. Do not write a changelog claim that outruns the measurement.

**The core-count claim is derived, not documented.** Nothing in this repo documents GitHub-hosted runner core counts. `jobs=2` in the CI log implies `cpu_count == 4` through `max(1, cpu_count - 2)`; that is an inference from observed behavior, and R2's measurement is what actually settles the win. Do not restate "4-core runner" as a fact.

**Open question for implementation:** whether the suite is CPU-saturated at full core count or still spawn-dominated. R2's before/after is the cheapest way to find out, and the answer decides whether CI-job sharding is worth a follow-up.

## Early proof point

Task fn-155-ci-wall-clock-run-the-unit-suite-at-the.1 is the whole behavior change and its first-ever tests. If R2's measurement on the real matrices shows no meaningful Linux/macOS improvement, stop and record it: the conclusion would be that the suite is spawn-dominated rather than core-starved, which redirects the effort to the smoke-script tail or to job sharding instead of shipping a change that buys nothing.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Full cores on CI, headroom locally, rationale at the site | .1 | - |
| R2 | Measured before/after on all four matrices | .1 | - |
| R3 | Coverage parity proven at two job counts | .1 | - |
| R4 | `--jobs` / `--serial` precedence intact | .1 | - |
| R5 | First tests for the parallel runner, precedence at main() | .1 | - |
| R6 | Stale default documented in step; frozen surfaces untouched | .1 | - |

## References

- `scripts/run_tests_parallel.py:65-67` `_default_jobs()`; `:99-149` `_run_one()` (subprocess shell-out); `:228-245` ThreadPoolExecutor; `:299-310` `--jobs` / `--serial`; `:350-359` precedence; `:5-6` docstring; `:304` help string
- `.github/workflows/test-flow-next.yml:118-151` the unit-test step (`:121` the stale comment, `:151` the invocation); `:57-70` the four-matrix definition; no `timeout-minutes` anywhere in the file
- `.github/workflows/test-flow-next.yml:161-249` the Cursor install smoke + ten sequential `if: always()` smoke scripts that make up the rest of a leg
- `plugins/flow-next/tests/test_spec_id_allocation.py:495-506` the stale "14 jobs" comment
- Overlap: fn-120 owns `.github/workflows/test-flow-next.yml:132-149` (Windows `EXCLUDES`) and `run_tests_parallel.py:99` `_run_one()`. **Serialized by a real edge, verifiable in state: `.flow/specs/fn-120-windows-test-corpus-compatibility-sweep.json` carries `depends_on_epics: ["fn-155-ci-wall-clock-run-the-unit-suite-at-the"]`.** The edge belongs on fn-120 because fn-120 is the waiter; fn-155's own `depends_on_epics` is correctly empty. fn-155 lands first and creates the runner test module; fn-120.3 then extends that module rather than scaffolding a second one.
