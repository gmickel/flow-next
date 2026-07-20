## Description

The parallel shard runner + everything that makes it canonical. MAINTAINER DIRECTIVE: no cross-model review (REVIEW_MODE none) - verification is running serial vs parallel and comparing result sets + wall time.

**Size:** M
**Files:** scripts/test-parallel.sh (new; or scripts/run_tests_parallel.py stdlib), .github/workflows/test-flow-next.yml, plugins/flow-next/agents/worker.md (canonical full-suite command mention), CHANGELOG.md (Unreleased entry - stays unreleased per directive)

## Approach

- Stdlib-only file-level shard runner: discover test files, run N shards concurrently (default cores-2), aggregate pass/fail + combined exit code; serial fallback flag (--serial); shard by FILE only.
- Prove equivalence: run the serial discover AND the parallel runner at the same HEAD; assert identical test counts + failure sets; record both wall times in the task evidence (target: parallel < 4 min).
- Wire-in: CI matrix uses the parallel entrypoint; worker.md names it as the canonical full-suite command (one-line edit, both fences already carry the foreground rule).
- Ordering canary: a --shuffle flag or documented canary invocation; note in CI as a weekly/manual job (do not add a new scheduled workflow unless trivial).
- sync-codex x2 if any canonical skill/agent file changed; dual-copy untouched (no flowctl.py changes expected).

## Acceptance

- [ ] Parallel run reproduces the serial run's exact result set at the same HEAD (counts + failures identical); both timings recorded in evidence
- [ ] Parallel wall time under 4 minutes on this machine (serial baseline ~15-20 min)
- [ ] CI uses the parallel entrypoint; worker.md references it; smoke_test.sh untouched
- [ ] CHANGELOG Unreleased entry (register-conformant); NO version bump, NO release

## Done summary
File-level parallel shard runner shipped: scripts/run_tests_parallel.py (stdlib only, shard-by-file, default jobs=cores-2, --serial fallback, --shuffle/--seed ordering canary, --pattern scoping, zero-match = exit 2). CI's ~30 per-file unittest steps collapsed into one parallel step with a workflow_dispatch shuffle input; path triggers include the runner. worker.md (+ codex mirror via sync-codex x2) names the entrypoint with portable phrasing (consumer repos without the script are unaffected). CHANGELOG Unreleased entry; no version bump per directive. Equivalence at 06faf106: serial 1945 tests OK (skipped=3) in 313.6s; parallel 87 files / 1945 tests / 0 failures / skipped=3 in 82.1s wall (jobs=14, measured under concurrent-baseline contention). Review: host session model (maintainer-directed self-review); fixed shipped-prose portability + step-name style in the delegate's draft.
## Evidence
- Commits: 06faf1066a95332c7de784f37bb951cdb87c8490
- Tests: python3 scripts/run_tests_parallel.py (87 files, 1945 tests, 0 failures, skipped=3, wall 82.1s jobs=14), python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' -q (serial baseline, Ran 1945 OK skipped=3, 313.6s, same HEAD), python3 scripts/run_tests_parallel.py --pattern test_worker_anchor_prose.py|test_foreground_rule_fences.py|test_skill_prose_diet.py (green)
- PRs: