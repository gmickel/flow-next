# fn-119 test-suite speed: parallel sharding + slow-test diet

> STUB (2026-07-20, maintainer pain: full suite ~15-20 min serial, and workers run it at least once per task even with gate receipts honoring baselines). Interview/plan before building.

## Goal & Context

The full unit suite (1944 tests, ~80 files) runs serially via `unittest discover` and dominates worker verification wall-clock. Sampled per-file timings (2026-07-20): test_prime_eval ~120s, test_gate_receipt ~48s, typical files 0-3s - a handful of subprocess/git-fixture-heavy files own most of the runtime. The fn-102/116 gate receipts already eliminate REDUNDANT runs; this spec makes the unavoidable runs fast. Target: full suite under ~3 minutes wall.

## Sketch (design at plan time)

1. **File-level parallel shard runner**: a small stdlib-only script (scripts/test-parallel.sh or a python runner using multiprocessing) that discovers test files and runs N shards concurrently (default N = cores-2), aggregating results + a combined exit code. The flowctl zero-dep constraint binds shipped plugin code, not the dev test runner - but stay stdlib anyway (no pytest dependency). Wall-clock collapses to ~max(slowest file).
2. **Slow-test diet on the heads**: profile properly (per-test, not per-file); test_prime_eval (189 tests) and the git-fixture-heavy files (gate receipts, migrate, tracker state) likely rebuild git repos/tmpdirs per test - share class-level fixtures (setUpClass) where isolation allows; batch subprocess-spawning assertions.
3. **Wire-in**: worker.md Quick-commands guidance + spec templates reference the parallel entrypoint as the canonical full-suite command; CI matrix jobs use it (3 OS x parallel shards); smoke_test.sh untouched (different harness).
4. **Ordering/flakiness guard**: shard by FILE (never split within a file), keep a serial fallback flag, and assert no test depends on cross-file ordering (a randomized-order canary run in CI weekly or per-release).

## Boundaries

- No pytest/xdist or any new dependency; stdlib + shell only.
- No test deletions; the diet is fixture-sharing and profiling-driven, never coverage reduction.
- Gate receipt semantics unchanged (receipts key on the exact command string - the new canonical command becomes the receipt identity going forward; note the transition in the plan).
- Coordinate with the other agent's fn-112/115 work only on CHANGELOG.
