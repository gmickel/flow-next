---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-155-ci-wall-clock-run-the-unit-suite-at-the.1 Full runner parallelism on CI, with its first tests and a measured result

## Description
Spend the idle cores on CI, and give `scripts/run_tests_parallel.py` its first tests.

**The change.** `_default_jobs()` (`scripts/run_tests_parallel.py:65-67`) currently returns `max(1, cpu_count - 2)` unconditionally. Make it return the full `cpu_count` on a build machine and keep `cpu_count - 2` locally. **The signal is exact, not a judgment call:**

```
ci = os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
```

Absent, empty, `"false"`, `"0"` and anything unrecognized all mean local; mixed case is normalized. `CI` and not `GITHUB_ACTIONS` because the scope is any build machine. Call the two cases **CI** and **local** - TTY state is deliberately not part of this design, so a redirected local run stays local. Write the rationale in a comment at the site: the reservation exists to leave room for whoever else is using the machine, which is a human's editor and agent locally and nothing at all on a runner.

**Job-count policy lives in the runner, not in YAML** - ordinary push/PR runs pass no `--jobs`, keep shuffle and exclusions, and behave exactly as before (the YAML source does change; the guarantee is behavioral, not byte identity). The workflow gains exactly one thing: the diagnostic `legacy_baseline` lever R2 needs (below). Do not touch the Windows `EXCLUDES` block at 132-149; fn-120 owns it.

**This is new precedent.** The repo has no existing "detect CI, behave differently" branch - the one live convention is `RUNNER_OS`, and it only ever branches on operating system. Say so in the comment.

**The baseline needs a lever, or R2 is unsatisfiable.** Once the commit contains CI detection, every run from that SHA uses the new behavior - the old number cannot be produced from it. Add a **boolean** `workflow_dispatch` input `legacy_baseline`; when true, compute the pre-change formula ON the runner and pass it through the existing override:

```bash
JOBS_ARGS=()
if [ "$LEGACY_BASELINE" = "true" ]; then
  JOBS_ARGS=(--jobs "$(python -c 'import os; print(max(1, (os.cpu_count() or 2) - 2))')")
fi
python scripts/run_tests_parallel.py "${JOBS_ARGS[@]}" "${SHUFFLE_ARGS[@]}" "${EXCLUDES[@]}"
```

`JOBS_ARGS` is ADDED to the existing arrays, never replacing them - `legacy_baseline=true` with `shuffle=true` must still produce a shuffled baseline run.

Boolean and read via `env:`, never direct `${{ }}` interpolation - a free-form string input is untrusted text in a shell line. And `--jobs 2` would be WRONG as a baseline: the old default is `max(1, cpu_count - 2)`, and nothing establishes that ubuntu, macOS and Windows runners report the same core count. Computing it per-runner is exact by construction.

**Then measure, with a stated rule.** Two dispatches per configuration x two configurations x four matrix rows = 16 raw results. Median the two `wall=` values per (configuration, row), and median the two whole-job durations the same way - never a single run or a worst case. **AMENDED after measurement (authoritative):** ship only if, on ALL FOUR matrix rows, neither metric regresses against its baseline median, AND at least one row's median runner-step `wall=` improves by at least 25%. The original rule (>=25% on all three of ubuntu/3.11, ubuntu/3.x and macos/3.11, Windows excluded) was tested, failed on both Ubuntu rows, and is retained only as history in the spec's Decision Context. Record BOTH tables (16 raw rows, then an 8-row aggregate whose every median names its two source run URLs) in the done-summary evidence AND the spec's `## Decision Context`. The runner step is roughly half of a leg (367s of 777s on ubuntu-3.11 in PR #285); ten sequential `if: always()` smoke scripts make up most of the rest and are out of scope. If the Linux and macOS legs do not clearly improve, stop and report that rather than shipping a change that buys nothing - the conclusion would be that the suite is spawn-dominated rather than core-starved.

**Size:** M
**Files:** `scripts/run_tests_parallel.py`, a new test module for it, `.github/workflows/test-flow-next.yml` (the stale comment + the boolean `legacy_baseline` dispatch input and its conditional - do NOT touch the Windows `EXCLUDES` block at 132-149, fn-120 owns it), `plugins/flow-next/tests/test_spec_id_allocation.py` (comment only), `CHANGELOG.md`, and `.flow/specs/fn-155-ci-wall-clock-run-the-unit-suite-at-the.md` (R2 requires both measurement tables and the ship/stop decision to land in its `## Decision Context` - that edit is a completion artifact of this task, not spec maintenance)

### Approach

- The runner is subprocess-bound, not CPU-bound in Python: `ThreadPoolExecutor` threads block on `subprocess.run` (`:99-149`, `:228-245`), so `jobs` is the count of concurrent OS interpreters. That is why core count is the right dial.
- Preserve the existing precedence exactly: `--serial` beats `--jobs` beats the default (`:350-359`), and `--jobs < 1` is still rejected (`:354-356`).
- There is no existing test module for this file to extend (`grep -rn "import run_tests_parallel"` returns nothing) - create one. Import the module by path the way `plugins/flow-next/tests/` modules already load `flowctl` via `importlib.util.spec_from_file_location`.
- **Test precedence at `main()`, not at the parser.** The chain lives at `:350-359`, after parsing, so a parser test cannot prove `--serial > --jobs > default` nor that `--jobs 0` exits 2 without running the suite. Patch `run_suite` and `_default_jobs` and assert the selected job count, whether `_default_jobs` was called at all, and the return code.

### Quick loop

```bash
cd plugins/flow-next/tests && python3 -m unittest test_run_tests_parallel -v
```

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

No docs-site work: this is maintainer-only CI tooling, invisible to anyone installing or running flow-next, so the user-visible-behavior rule does not apply. The root CHANGELOG entry is the whole release surface.
## Acceptance
- [ ] `_default_jobs()` uses full `cpu_count` when `CI` parses truthy (`1|true|yes`, case-insensitive) and `cpu_count - 2` otherwise; absent/empty/`false`/`0`/unrecognized all mean local; rationale + new-precedent note in a comment at the site (R1)
- [ ] Boolean `workflow_dispatch` input `legacy_baseline`, read via `env:` not `${{ }}`; when true it computes `max(1, cpu_count-2)` ON the runner and passes it via `--jobs`. Invocation composes as `"${JOBS_ARGS[@]}" "${SHUFFLE_ARGS[@]}" "${EXCLUDES[@]}"` - shuffle still works with either baseline mode. Push/PR runs pass no `--jobs` and keep shuffle+exclusions (behavioral equivalence, not byte identity of the YAML); Windows `EXCLUDES` block untouched (R2)
- [ ] 16 raw results (2 dispatches x 2 configurations x 4 rows); aggregate table carries median wall=, median job duration, and the percentage delta for each; AMENDED criterion (authoritative): on ALL FOUR rows neither metric regresses vs its baseline median, AND at least one row's median runner-step wall= improves >=25% (median-of-two for both metrics, never a single run). Original all-three->=25% rule retained as history only. Both tables (16 raw + 8 aggregate with source run URLs per median) in the done-summary AND the spec's Decision Context. No improvement means STOP and report (R2)
- [ ] Sorted `--list-only` output AND `parallel-runner:`/`SUMMARY` counts all identical at `--jobs 2` and at auto on the same corpus (counts alone do not prove an identical file set); new tests pin `--exclude` behavior, zero-match exit 2, and failure exit 1 (R3)
- [ ] `--serial` > `--jobs` > default precedence proven at `main()` with `run_suite`/`_default_jobs` patched; `--jobs 0` exits 2 without running the suite (R4, R5)
- [ ] New test module covers the local default, the CI default, and every `CI` value case (R5)
- [ ] Docstring `:5-6`, `--jobs` help `:304`, workflow comment `:121`, and the stale "14 jobs" comment updated; `CHANGELOG.md:789` and the fn-119 spec untouched (R6)
- [ ] `## Unreleased` CHANGELOG entry, no version bump, no docs-site update (maintainer-only CI tooling)
- [ ] Full gate green
- [ ] Both measurement tables and the ship/stop decision recorded in `.flow/specs/fn-155-*.md` `## Decision Context` (R2 completion artifact)
## Done summary
`scripts/run_tests_parallel.py` now defaults to the runner's full core count when `CI` parses truthy (`1|true|yes`, strip+lower; absent/empty/`false`/`0`/unrecognized are local) and keeps `cpu_count - 2` locally, with the reservation rationale and the new-precedent note written at the site; `--serial` > `--jobs` > default and the `--jobs < 1` rejection are unchanged and now proven at `main()`. The workflow gains only the boolean `legacy_baseline` `workflow_dispatch` lever (read via `env:`, computing the pre-change formula per runner and composing as `"${JOBS_ARGS[@]}" "${SHUFFLE_ARGS[@]}" "${EXCLUDES[@]}"`), the runner gets its first test module (15 tests), and every stale statement of the old default is corrected.

R2 split (conductor-owned by explicit instruction): the measurement MECHANISM landed and is inert on push/pull_request, but the 16 measurement runs (4 dispatches x 4 matrix rows) and the two evidence tables in the spec's `## Decision Context` are NOT done here - they need the branch on origin plus repeated `gh workflow run`, which is conductor orchestration. No numbers were invented or estimated. The ship/stop decision against the >=25% improvement / <=5% regression rule on ubuntu/3.11, ubuntu/3.x and macos/3.11 (Windows recorded, not gating) remains open until the conductor runs them.
## Evidence
- Commits: 9abd4d4f3de3f018a28551afff32ebe20d79ab19, fdf218dca02427e03f61391de9d7afeb0dc9940e, 119e2a5a171464b50743c408452f1ef251a89e56
- Tests: python3 scripts/run_tests_parallel.py (files=179 ran=3863 failures=0 errors=0 skipped=0/4 wall=172.45s jobs=14, green), uvx ruff@0.16.0 check . (All checks passed), cd plugins/flow-next/tests && python3 -m unittest test_run_tests_parallel -v (15 tests, OK), R3 parity, full 179-file corpus: 'python3 scripts/run_tests_parallel.py --jobs 2 --list-only' vs 'python3 scripts/run_tests_parallel.py --list-only' - sorted file lists byte-identical, both 'parallel-runner: 179 file(s)', R3 parity, same 58-file corpus at both job counts: 'python3 scripts/run_tests_parallel.py --pattern test_[a-h]*.py --jobs 2' -> 'SUMMARY files=58 ran=1107 failures=0 errors=0 skipped=3 jobs=2' vs the auto default -> identical counts at jobs=14 (full-corpus SUMMARY at jobs=2 would exceed the 600s foreground cap locally; CI measures it), R1 live check: 'CI=true ... --list-only' -> jobs=16 (cpu_count), 'CI=false ...' -> jobs=14 (cpu_count-2) on a 16-core box, impl-review (rp, RepoPrompt CE): round 1 NEEDS_WORK (2 introduced findings), round 2 SHIP with all six R-IDs met, 0 surviving findings
- PRs: