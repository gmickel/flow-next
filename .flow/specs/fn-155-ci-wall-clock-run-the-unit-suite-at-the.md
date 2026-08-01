# CI wall-clock: run the unit suite at the parallelism the runner actually has

## Goal & Context
<!-- scope: business -->

Every pull request that touches anything under `plugins/flow-next/**` pays the same CI bill, and that bill is now the slowest part of landing a change. Measured on PR #285 (a change that was almost entirely skill prose plus one test):

| matrix | wall |
|---|---|
| ubuntu-latest 3.11 | 9m12s |
| ubuntu-latest 3.x | 13m28s |
| macos-latest 3.11 | 14m48s |
| windows-latest 3.11 | 17m41s |

The same suite runs locally in **131s**. The gap is not scope and it is not machine speed alone: `scripts/run_tests_parallel.py` defaults to `max(1, cpu_count - 2)` workers, so a 16-core laptop gets `jobs=14` while a 4-core GitHub runner gets `jobs=2`. The reservation of two cores is correct for the machine a human is typing on - it leaves room for the editor and the agent driving the run - and is pure waste on a dedicated CI runner that has nothing else to do.

This is not a test-selection problem and must not become one. Skill prose is genuinely covered (docs inventory, prompt-text SHA pinning, Codex mirror parity), and a "docs are cheap" path filter would disable exactly the guards that catch prose regressions - #285 shipped a broken changelog assertion that only the full suite caught. The suite should keep running in full. It should just stop leaving half the runner idle.

## Architecture & Data Models
<!-- scope: technical -->

`_default_jobs()` (`scripts/run_tests_parallel.py:65`) returns `max(1, (os.cpu_count() or 2) - 2)`. The workflow invokes the runner with no `--jobs` (`.github/workflows/test-flow-next.yml:151`), so CI inherits the interactive default.

Two candidate mechanisms, to be chosen at plan time:

- **(a) Workflow passes `--jobs` explicitly**, computed per-runner (`nproc` / `sysctl -n hw.ncpu` / `%NUMBER_OF_PROCESSORS%`). Keeps all policy in CI, leaves the script's interactive default untouched, but spreads a platform-conditional expression across three OS legs.
- **(b) The runner detects a non-interactive environment** (`CI=true`, which every GitHub-hosted runner sets) and uses full `cpu_count` there, keeping `cpu_count - 2` for humans. One place, no workflow churn, and it fixes any other automation that shells out to the script.

Either way the reserved-core policy becomes a statement about *who else is using this machine*, which is the thing it was always trying to express.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On CI the unit suite runs at the runner's full core count; locally the default still reserves headroom. The chosen mechanism is documented where the default is defined, stating that the reservation exists for interactive machines.
- **R2:** Wall-clock is **measured, not assumed**: record before/after for all four matrices on the same commit. Ship only if the change is a clear improvement on at least the Linux and macOS legs; if a leg does not improve, say so in the spec's Decision Context rather than quietly claiming a win.
- **R3:** Coverage is unchanged - same file set, same test count (`files=178 ran=3832` at time of writing, allowing for tests added since), same excludes, same shuffle behavior. No path-based test selection is introduced by this change.
- **R4:** `--jobs` and `--serial` keep working as explicit overrides and still win over any auto-detection.

## Boundaries
<!-- scope: business -->

- **No test selection, no path filters, no "docs skip CI".** The full suite keeps running on every triggering change. This spec is about idle cores, not about running less.
- **No larger runners, no self-hosted runners, no paid tiers.** Free-tier runners only.
- **No sharding across jobs.** Splitting the suite into parallel CI jobs is a different, larger change; if the measurement in R2 shows parallelism alone is not enough, capture that as a follow-up rather than growing this spec.
- **No change to the workflow's trigger paths.** They are deliberately in step with the ruff lint scope (see the comment at `.github/workflows/test-flow-next.yml:22`).

## Decision Context
<!-- scope: both -->

**Why not narrow what runs.** The obvious reaction to "16 minutes for a docs change" is to stop running tests for docs changes. That is the wrong lesson from #285: the failure that CI caught there *was* in prose (a changelog assertion), and the guards that catch prose regressions live in the same suite as everything else. Narrowing the trigger would have let it through.

**Why the Windows number is a warning, not a target.** Windows was 17m41s against ubuntu's 9m12s at identical job counts. That gap is process-spawn overhead, not CPU saturation, so doubling workers will not halve it. Expect the Linux and macOS legs to improve most, and do not write a changelog claim that outruns the measurement.

**Open question for plan time:** whether the suite is actually CPU-bound at 4 workers or whether subprocess startup dominates. R2's before/after is the cheapest way to find out, and the answer decides whether sharding is worth a follow-up.

## Quick commands
<!-- scope: technical -->

Focused check for this change:

```bash
python3 scripts/run_tests_parallel.py --jobs 2
python3 scripts/run_tests_parallel.py
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```
