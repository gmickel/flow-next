# Hill-climb run: mycli --version cold start

End-to-end run of the loop in `skills/flow-next-work/references/hill-climb.md` on this fixture (`../SPEC.md` holds the pre-registration). The run repository was a fresh `git init` of the fixture; each kept attempt's commit is saved here as `attempt-<n>.diff`, applied in order to the fixture.

Recorded 2026-09-28, Linux, CPython 3.12.14, one machine.

## Pre-registration

Metric `mycli --version` cold-start wall time (median, ms); direction lower; target below 40 ms; attempt floor 5; budget 10 attempts; 11 runs per measurement after 3 discarded warm-ups; minimum detectable effect 10 ms. Regression gate `python3 -m unittest discover -s tests`.

## Harness proof and freeze

- Regression gate on the unchanged tree: green (3 tests).
- Baseline: median 124 ms, range 118-132 ms. Effective minimum detectable effect: 14 ms (the 14 ms range width beats the 10 ms floor). Gap to target: 84 ms, so the instrument can resolve the goal.
- Known worse (a 30 ms sleep in `main`): 154 ms (148-158) against the baseline's 122 ms in the same interleaved measurement.
- Known better (plugin discovery stubbed out): 74 ms (71-77) against 122 ms.
- Wrong output (`mycli 1.4` printed): rejected, `OUTPUT CHECK FAILED in .: rc=0 stdout='mycli 1.4\n'`, harness exit 1.
- Order worse > baseline > better, both gaps (32 ms, 48 ms) above the 14 ms range. Probes reverted; tree clean.
- Frozen: `python3 bench.py --runs 11 --warmup 3 <dir> [<dir>]`, `bench.py` sha256 `9a8e6539ee7a4e1631854eff329d9b99bc2d8f85720f6dc1c14ba9078567230a` (no other inputs). Re-checked before every measurement; unchanged.

Profile before attempt 1 (`python3 -m cProfile`): `discover` called twice (70 ms together), `mycli.tables` import 62 ms (a prime sieve that only `stats` uses).

## Ledger

| # | Family | Mechanism | Change | Before (median, range) | After (median, range) | Delta | Gate | Verdict | Reason | Commit |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | delete | `validate` re-walks the whole search path to re-find what `discover` just found | drop `validate`; `main` calls `discover` once | 119 (116-124) | 96 (94-104) | -23 | green | kept | clears 14 ms, no overlap; replicate 96 (93-100) vs 118 (116-129) | attempt-1.diff |
| 2 | represent | profile after attempt 1: 2016 file opens, text wrapper plus decode per marker read | read the marker in binary mode | 97 (94-100) | 93 (90-97) | -4 | not run | inconclusive | inside the noise; ranges overlap | - |
| 3 | parallelise | the scan is 2016 opens across 6 roots; opens release the GIL | walk the roots on a `ThreadPoolExecutor` | 95 (94-101) | 135 (122-144) | +40 | green | reverted | worse: `concurrent.futures` costs 8 ms to import and the threads contend | - |
| 4 | defer | `--version` pays for plugin discovery that only `list` uses | discover inside the `list` branch | 100 (93-104) | 73 (70-77) | -27 | green | kept | clears 14 ms, no overlap; replicate 73 (70-78) vs 95 (93-103) | attempt-4.diff |
| 5 | defer | the 62 ms sieve in `mycli.tables` loads for every subcommand; only `stats` reads it | import `tables` (and `plugins`) inside their branches | 73 (71-78) | 7 (7-9) | -66 | green | kept | clears 14 ms, no overlap; replicate 8 (7-9) vs 73 (71-77) | attempt-5.diff |

Stop: target met (8 ms < 40 ms) and attempt floor 5 reached, after 5 of 10 budgeted attempts.

## Record (as it goes into the done summary)

```text
Hill climb:
- metric: mycli --version cold-start wall time, median ms (lower is better); target below 40 ms
- baseline: 124 ms (118-132) | final: 8 ms (7-9) at attempt 5 | change: -93% (120 -> 8 ms, final interleaved against the baseline commit)
- attempts: 5 (kept 3, reverted 1, inconclusive 1); floor 5; budget 10 attempts
- kept commits: attempt-1 perf(plugins): drop the redundant validate rescan; attempt-4 perf(cli): discover plugins only for list; attempt-5 perf(cli): import the stats tables only for stats
- harness: python3 bench.py --runs 11 --warmup 3 <dir> [<dir>], sha256 9a8e6539ee7a; proof: worse 154, baseline 122, better 74; wrong output rejected (output check, exit 1)
- gate: python3 -m unittest discover -s tests green at the final head
- stop: target met and attempt floor reached
- target: met
- best untried: skip `site` initialisation with a `-S` launcher (tune); interpreter startup is now the remaining cost
```

## PR briefing proof cells (as make-pr renders them)

| Label | Value | Outcome |
|---|---|---|
| Metric and target | `mycli --version` cold start, median ms, lower is better; target below 40 ms | |
| Baseline to final | 124 ms (118-132) to 8 ms (7-9), -93% | pass |
| Attempts | 5: kept 3, reverted 1, inconclusive 1 (floor 5, budget 10) | |
| Kept commits | attempt 1 drop rescan; attempt 4 defer discovery; attempt 5 defer tables | |
| Harness proof | worse 154 > baseline 122 > better 74; wrong output rejected; sha256 9a8e6539ee7a | pass |
| Final gate | `python3 -m unittest discover -s tests` green at the final head | pass |
| Best untried | `-S` launcher to skip `site` initialisation (tune) | |
