# fn-119 test-suite speed: parallel sharding + slow-test diet

> STUB (2026-07-20, maintainer pain: full suite ~15-20 min serial, and workers run it at least once per task even with gate receipts honoring baselines). Interview/plan before building.

## Goal & Context

The full unit suite (1944 tests, ~80 files) runs serially via `unittest discover` and dominates worker verification wall-clock. Sampled per-file timings (2026-07-20): test_prime_eval ~120s, test_gate_receipt ~48s, typical files 0-3s - a handful of subprocess/git-fixture-heavy files own most of the runtime. The fn-102/116 gate receipts already eliminate REDUNDANT runs; this spec makes the unavoidable runs fast. Target: full suite under ~3 minutes wall.

## Sketch (design at plan time)

0. **Scope note (maintainer, 2026-07-20): items 5-6 are FLOW-NEXT-REPO-SPECIFIC** - they change this repo's test corpus and its spec-authoring conventions, NOT the flow-next product. The plugin ships no test-selection machinery; at most, the plan skill's Quick-commands guidance gains one generic sentence (focused suites preferred, full suite as the final gate) - decide at plan whether even that is warranted.

1. **File-level parallel shard runner**: a small stdlib-only script (scripts/test-parallel.sh or a python runner using multiprocessing) that discovers test files and runs N shards concurrently (default N = cores-2), aggregating results + a combined exit code. The flowctl zero-dep constraint binds shipped plugin code, not the dev test runner - but stay stdlib anyway (no pytest dependency). Wall-clock collapses to ~max(slowest file).
2. **Slow-test diet on the heads**: profile properly (per-test, not per-file); test_prime_eval (189 tests) and the git-fixture-heavy files (gate receipts, migrate, tracker state) likely rebuild git repos/tmpdirs per test - share class-level fixtures (setUpClass) where isolation allows; batch subprocess-spawning assertions.
3. **Wire-in**: worker.md Quick-commands guidance + spec templates reference the parallel entrypoint as the canonical full-suite command; CI matrix jobs use it (3 OS x parallel shards); smoke_test.sh untouched (different harness).
4. **Ordering/flakiness guard**: shard by FILE (never split within a file), keep a serial fallback flag, and assert no test depends on cross-file ordering (a randomized-order canary run in CI weekly or per-release).
5. **Stale-test sweep (repo-specific)**: audit the corpus for tests pinning removed/superseded behavior - candidates already known: test_config_alias.py's no-op-path tests (alias map empty since 2.0.0; fn-111 deletes the machinery), alias_smoke/read-compat suites (fn-111 scope - coordinate, do not double-delete), any suite exercising pre-1.0 migration paths (fn-111's basket), superseded prose-contract assertions. Every removal names what made it stale; coverage-reducing removals need the behavior to be GONE, not merely untested.
6. **Scoped verification convention (repo-specific)**: this repo's specs stop listing the full discover as a per-task Quick command. New convention: Quick commands list the FOCUSED suites for the feature's files (e.g. `python3 -m unittest test_config_snapshot test_task_create_files -q`) - that is what workers baseline against and verify per task; the FULL (parallel, item 1) suite runs ONCE at the final gate (work Phase 4 / completion review), where gate receipts already dedupe it. CARRIER: the convention is written into THIS repo's committed CLAUDE.md (AGENTS.md symlinks to it) - a short spec-authoring rule in the Flow-Next section stating the focused-vs-full split and naming the parallel full-suite entrypoint - plus the repo-local .flow/templates/spec.md Quick-commands scaffold comment and .flow/usage.md guidance. The worker/gate mechanics need no product change - workers already run "the spec's Quick commands"; this fixes what our specs put there, enforced where our spec authors read.

## Boundaries

- No pytest/xdist or any new dependency; stdlib + shell only.
- Item 2's diet is fixture-sharing, never coverage reduction; item 5's deletions are allowed ONLY for stale behavior (see its rule) and coordinate with fn-111's test-fallout list.
- Gate receipt semantics unchanged (receipts key on the exact command string - the new canonical command becomes the receipt identity going forward; note the transition in the plan).
- Coordinate with the other agent's fn-112/115 work only on CHANGELOG.
