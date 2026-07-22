---
satisfies: [R1, R2, R3]
---
# fn-127-scope-capture-compaction-guard-to.1 Fix capture compaction relevance guard and release 3.3.2

## Description
Replace capture's any-signal hard refusal with a relevance-based evidence check, pin the behavior in a focused test, regenerate the Codex mirror, and publish patch release 3.3.2 including the public docs-site release entry.

## Acceptance
- [ ] Historical compaction alone does not block a fully visible capture source.
- [ ] Relevant missing/truncated/summary-only evidence still refuses without `--from-compacted-ok`; autofix remains fail-closed.
- [ ] Canonical and Codex mirror prose stay aligned and focused regression coverage passes.
- [ ] Full repository gate and docs-site build pass.
- [ ] Version 3.3.2 is committed, pushed, tagged, and verified on GitHub.

## Done summary
Scoped capture's compaction guard to evidence relevant to the requested spec. Historical compaction markers and system-summary blocks are advisory when the relevant user turns remain fully visible; missing, truncated, summary-only, or gap-dependent requirements still fail closed without `--from-compacted-ok`. Added canonical/Codex prose-contract coverage and prepared patch release 3.3.2.
## Evidence
- Commits: 6a34dfe4
- Tests: python3 -m unittest plugins.flow-next.tests.test_capture_compaction_contract -v, python3 -m unittest plugins.flow-next.tests.test_readback_ask_contract plugins.flow-next.tests.test_capture_biz_routing -q, ./scripts/sync-codex.sh (twice, idempotent), python3 scripts/run_tests_parallel.py (116 files, 2152 tests, 0 failures, 0 errors, 3 skipped)
- PRs: