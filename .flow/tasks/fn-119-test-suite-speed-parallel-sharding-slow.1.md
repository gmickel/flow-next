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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
