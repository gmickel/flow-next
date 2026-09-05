# fn-225-prune-ci-events-while-preserving.1 Implement CI classification, bounds and release evidence

## Description
# Implement CI classification, bounds and release evidence

**Touches:** .github/workflows/**, scripts/ci/**, scripts/merge_codex_config.py, plugins/flow-next/tests/test_ci*.py, plugins/flow-next/tests/test_codex_config*.py, agent_docs/project.md
**Satisfies:** R1, R2, R3, R4, R5

Implement the spec through existing workflow/classifier patterns. Remove top-level PR path filtering if needed to expose a stable always-running aggregate check, conservatively classify unrelated bookkeeping paths. Preserve all required unit corpus behavior and Windows coverage. Fix verified locale-dependent UTF-8 decoding in Codex config merger, covered by cp1252 simulation regression. Release may use exact main push CI evidence (not workflow_dispatch diagnostics), or a reusable gate. Do not publish releases.

### Quick commands
- Run focused CI classifier/trigger and release-evidence regression tests.
- python3 scripts/run_tests_parallel.py
- uvx ruff@0.16.0 check .

Read all scoped instructions. No broad test exclusions. Cross-platform acceptance remains GitHub CI. Downstream public docs n/a for CI-only infrastructure; Codex encoding fix may warrant concise Unreleased note if required.
## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
