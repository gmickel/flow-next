---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-155-ci-wall-clock-run-the-unit-suite-at-the.1 Full runner parallelism on CI, with its first tests and a measured result

## Description
Spend the idle cores on CI, and give `scripts/run_tests_parallel.py` its first tests.

**The change.** `_default_jobs()` (`scripts/run_tests_parallel.py:65-67`) currently returns `max(1, cpu_count - 2)` unconditionally. Make it return the full `cpu_count` when the process is running non-interactively on a build machine, and keep `cpu_count - 2` otherwise. Write the rationale in a comment at the site: the reservation exists to leave room for whoever else is using the machine, which is a human's editor and agent locally and nothing at all on a runner.

**Do NOT pass `--jobs` from the workflow.** That works too, but it puts a platform-conditional core-count expression across three OS legs and edits the exact CI step fn-120 owns for its Windows `EXCLUDES` block. Keeping the change inside one Python function touches no YAML.

**This is new precedent.** The repo has no existing "detect CI, behave differently" branch - the one live convention is `RUNNER_OS`, and it only ever branches on operating system. Say so in the comment.

**Then measure, before claiming anything.** R2 needs the runner's own `wall=`/`jobs=` line AND the whole-job duration for all four matrices, before and after, on the same commit. The runner step is roughly half of a leg (367s of 777s on ubuntu-3.11 in PR #285); ten sequential `if: always()` smoke scripts make up most of the rest and are out of scope. If the Linux and macOS legs do not clearly improve, stop and report that rather than shipping a change that buys nothing - the conclusion would be that the suite is spawn-dominated rather than core-starved.

**Size:** M
**Files:** `scripts/run_tests_parallel.py`, a new test module for it, `.github/workflows/test-flow-next.yml` (comment only), `plugins/flow-next/tests/test_spec_id_allocation.py` (comment only), `CHANGELOG.md`

### Approach

- The runner is subprocess-bound, not CPU-bound in Python: `ThreadPoolExecutor` threads block on `subprocess.run` (`:99-149`, `:228-245`), so `jobs` is the count of concurrent OS interpreters. That is why core count is the right dial.
- Preserve the existing precedence exactly: `--serial` beats `--jobs` beats the default (`:350-359`), and `--jobs < 1` is still rejected (`:354-356`).
- There is no existing test module for this file to extend (`grep -rn "import run_tests_parallel"` returns nothing) - create one. Import the module by path the way `plugins/flow-next/tests/` modules already load `flowctl` via `importlib.util.spec_from_file_location`, and drive `_default_jobs()` / the parser directly with a patched environment and `os.cpu_count`.

### Investigation targets

**Required** (read before coding):
- `scripts/run_tests_parallel.py:60-80` - `_default_jobs()` and `_discover()`
- `scripts/run_tests_parallel.py:281-360` - `build_parser()` and the `main()` precedence chain
- `scripts/run_tests_parallel.py:1-20` - the module docstring that states the default
- `.github/workflows/test-flow-next.yml:118-151` - the unit-test step; note that fn-120 owns lines 132-149

**Optional** (reference as needed):
- `scripts/run_tests_parallel.py:99-149` - `_run_one()`, evidence for the subprocess-bound claim
- `plugins/flow-next/tests/test_spec_id_allocation.py:495-506` - the stale "14 jobs" comment to correct

### Key context

Do NOT introduce path-based test selection, a docs-skip filter, or CI job sharding. The spec's Boundaries rule all three out: the regression CI caught on PR #285 was itself in prose, so narrowing the trigger would have let it through.

Do NOT edit `CHANGELOG.md:789` or `.flow/specs/fn-119-*.md` - both are shipped historical records. A new `## Unreleased` entry is the correct place.

Do NOT restate "the runner has 4 cores" as fact. Nothing in the repo documents runner core counts; `jobs=2` implies `cpu_count == 4` through the existing formula, which is an inference. R2's measurement is what settles it.

No version bump (`CLAUDE.md:101` batching rule) - stage under `## Unreleased`.

### Acceptance
- [ ] `_default_jobs()` returns full `cpu_count` on a build machine and `cpu_count - 2` otherwise, with the rationale and the new-precedent note in a comment at the site (R1)
- [ ] `--serial` > `--jobs` > default precedence unchanged; `--jobs 0` still rejected (R4)
- [ ] New test module covers the interactive default, the CI default, and the full precedence chain (R5)
- [ ] Same discovered file set, test count, excludes, shuffle behavior and exit codes as before (R3)
- [ ] Docstring (`:5-6`), `--jobs` help (`:304`), the workflow comment (`:121`) and the stale "14 jobs" comment all updated; `CHANGELOG.md:789` and the fn-119 spec untouched (R6)
- [ ] Before/after measurement recorded for all four matrices - runner `wall=`/`jobs=` line AND whole-job duration, same commit. If Linux and macOS do not clearly improve, STOP and report instead of shipping (R2)
- [ ] `## Unreleased` CHANGELOG entry, no version bump
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .`

## Acceptance
- [ ] Full cores on a build machine, headroom locally, rationale + new-precedent note at the site
- [ ] `--serial` > `--jobs` > default precedence intact; `--jobs 0` rejected
- [ ] First test module for run_tests_parallel.py covers both defaults and the precedence chain
- [ ] Discovered file set, test count, excludes, shuffle and exit codes unchanged
- [ ] All four stale-default statements updated; frozen CHANGELOG/fn-119 surfaces untouched
- [ ] Four-matrix before/after measured on one commit; no-improvement means STOP and report
- [ ] Unreleased CHANGELOG entry, no version bump
- [ ] Full gate green


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
