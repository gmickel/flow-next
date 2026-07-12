---
satisfies: [R19]
---

## Description
`flowctl prime classify --json` emitter FRAMEWORK: command/schema skeleton + axes 1-4 signals + shape markers.

**Size:** M | **Files:** `plugins/flow-next/scripts/flowctl.py` AND `.flow/bin/flowctl.py` (byte-identical dual-copy invariant - update BOTH), initial `plugins/flow-next/tests/test_prime_eval.py` (framework tests), `.github/workflows/test-flow-next.yml` (add the new test file to the explicit list)

## Approach
- Pure-stdlib subcommand: `--json` threading, ROOT arg, per-collector budget scaffolding, the completeness-diagnostics envelope per resolution 21b (status/complete/sampled/truncated/cap_hit/errors/tool/op-counts per collector; JSON stdout, diagnostics stderr).
- Axes 1-4 raw signals: lifecycle counters, topology bits + workspace-dampener inputs + `assessment_scope` (repository | workspace-member | constellation-home-base), size/exclusion-filtered LOC via blob-ID dedup (no content reads), legibility sub-signals, manifest-gated stack detection; shape MARKERS only (judgment stays skill-side).
- Schema per classification.md (task 2); parity test (both copies byte-identical); live-subcommand smoke.

## Key context
- Substance collectors, redaction, fixtures, perf accounting land in task 13 (split per final review round).
- unittest not pytest; 3-OS portable; no bare timeout binary; POSIX classes.

## Acceptance
- [ ] Subcommand in BOTH flowctl copies, parity-tested, live-subcommand test green
- [ ] Axes 1-4 signals + shape markers + assessment_scope emitted with the completeness-diagnostics envelope
- [ ] Blob-ID dedup (no content reads); per-collector budget scaffolding present
- [ ] test_prime_eval.py wired into the workflow's explicit test list

## Done summary
Implemented the `flowctl prime classify [ROOT] --json` emitter FRAMEWORK (fn-92.4): a bounded, pure-stdlib, judgment-free Phase-0.5 classifier that emits the pinned classification.md schema — axes 1-4 raw signals + Axis-5 shape markers + assessment_scope, each wrapped in the per-collector completeness-diagnostics envelope (resolution 21b), with blob-ID content-hash dedup (git ls-files -s, no content reads), path exclusions, and per-collector budget scaffolding. Landed byte-identically in both flowctl copies with 34 framework tests (test_prime_eval.py) wired into CI. Substance collectors, redaction, the full R19 fixture corpus, and perf accounting are deferred to fn-92.13.
## Evidence
- Commits: 4c78a721d829d70bf56298f0084f6558733cd4e3
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_prime_eval.py (34 tests, OK), python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1615 tests, OK skipped=2), python3 -m py_compile plugins/flow-next/scripts/flowctl.py, diff -q both flowctl.py copies (byte-identical)
- PRs: