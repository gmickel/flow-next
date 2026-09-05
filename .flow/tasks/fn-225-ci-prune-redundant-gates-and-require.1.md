---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-225-prune-ci-events-while-preserving.1 Implement CI classification, bounds and release evidence

## Description
# Implement CI classification, bounds and release evidence

**Touches:** CHANGELOG.md, .github/workflows/**, scripts/ci/**, scripts/merge_codex_config.py, plugins/flow-next/tests/test_ci*.py, plugins/flow-next/tests/test_codex_config*.py, agent_docs/project.md
**Satisfies:** R1, R2, R3, R4, R5

Implement the spec through existing workflow/classifier patterns. Remove top-level PR path filtering if needed to expose a stable always-running aggregate check, conservatively classify unrelated bookkeeping paths. Preserve all required unit corpus behavior and Windows coverage. Fix verified locale-dependent UTF-8 decoding in Codex config merger, covered by cp1252 simulation regression. Release may use exact main push CI evidence (not workflow_dispatch diagnostics), or a reusable gate. Do not publish releases.

### Quick commands
- Run focused CI classifier/trigger and release-evidence regression tests.
- python3 scripts/run_tests_parallel.py
- uvx ruff@0.16.0 check .

Read all scoped instructions. No broad test exclusions. Cross-platform acceptance remains GitHub CI. Downstream public docs n/a for CI-only infrastructure; Codex encoding fix may warrant concise Unreleased note if required.
## Acceptance
- [ ] R1: PR cancellation and bounded jobs preserve main/release execution.
- [ ] R2: Conservative PR/main range classification preserves required unit coverage.
- [ ] R3: Scoped Windows stub has weekly backstop; Windows encoding regression fixed.
- [ ] R4: Stable aggregate and exact main push CI block unverified publication.
- [ ] R5: Focused regressions, full suite and Ruff pass.

## Done summary
Implemented PR cancellation, job timeouts, conservative PR/main CI classification, Windows-stub scoping with weekly backstop, stable CI aggregate, and exact main-push release evidence. Fixed Windows Codex config UTF-8 handling; added focused range/rename/aggregate/release/encoding regression coverage and changelog guidance.

Baseline: red before implementation from temporary-storage quota; an in-checkout TMPDIR retry caused containment failures and fixture pollution. All generated tracked pollution was reversed in a separate commit. Final suite used external private TMPDIR and passed 206 files / 4792 tests / 7 skips. Ruff and actionlint passed. Physical Windows/macOS GitHub acceptance remains for conductor after push; no release or push performed.

GATE_SKIPPED:unittest:green-receipt 02b6768a

stage: impl-review - ran [2026-09-05T16:03:27Z..2026-09-05T16:11:46.402340+00:00] | SHIP after rename-source finding fixed and single resumed review. Receipt: /tmp/impl-review-receipt-f3f21b2fd6e1-fn-225-prune-ci-events-while-preserving.1.json
## Evidence
- Commits: 71e1e1d1abcf5c7e6060a35f8b0db461becbf1b9, 384ccd60b0fa8d0bd6ad8a97a190112c11a7cd7a, 02b6768a0a4abce4108a69081f2e03efb140cfe5
- Tests: baseline: interrupted first run (no terminal result); second run red pre-edit with /tmp Disk quota exceeded; in-checkout TMPDIR retry invalidated containment and was stopped; generated fixture pollution reversed in commit 384ccd60, TMPDIR=/home/gordon/.local/state/ci-audit-20260905/flow-next-tmp python3 scripts/run_tests_parallel.py: PASS 206 files, 4792 tests, 7 skips, exit 0 (.flow/tmp/final-tests-2.log), GATE_SKIPPED:unittest:green-receipt 02b6768a, uvx ruff@0.16.0 check .: PASS, python3 -m unittest discover -s plugins/flow-next/tests -p test_ci*.py -q: PASS 6 tests, python3 -m unittest discover -s plugins/flow-next/tests -p test_codex_config_merge.py -q: PASS 13 tests; cp1252 reproduction red-to-green, python3 -m unittest discover -s plugins/flow-next/tests -p test_tracker_package_import.py -q: PASS 8 tests, actionlint .github/workflows/test-flow-next.yml .github/workflows/release.yml .github/workflows/docs-linkcheck.yml: PASS, git diff --check: PASS, Git rename regression: red source path absent, green both paths and full units/stub; divergent PR/main ranges verified
- PRs: