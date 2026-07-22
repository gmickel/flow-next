---
satisfies: [R1, R2, R3]
---
# fn-128-scope-capture-readiness-prompts-to-the.1 Fix capture readiness prompt and release 3.3.3

## Description
Make Capture's readiness follow-up target-aware for rewrites, clarify autonomous-queue semantics, add regression coverage, regenerate the Codex mirror, update public docs, and publish patch release 3.3.3.

## Acceptance
- [ ] New capture + adopted local readiness retains the optional mark-ready question.
- [ ] Ready rewrite target gets a restore-readiness question; draft rewrite target gets no question regardless of unrelated ready specs.
- [ ] Tracker-authoritative suppression, autofix no-write, rewrite reset, and existing option tokens remain unchanged.
- [ ] Canonical/mirror contracts, full repository gate, and exact docs-site build pass.
- [ ] Version 3.3.3 is committed, pushed, tagged, and verified publicly.

## Done summary
Capture readiness consent is now target-aware. New captures retain the adopted-local-readiness offer; rewrites ask only when the target itself was ready before the rewrite. Tracker-authoritative suppression, rewrite reset, option tokens, and autofix no-write behavior remain intact. Copy now explains Pilot/autonomous eligibility. Canonical/Codex contracts, regression coverage, public docs, and 3.3.3 release surfaces are updated.
## Evidence
- Commits: 83616353, 38a9f0b (flow-next.dev)
- Tests: python3 -m unittest plugins.flow-next.tests.test_capture_readiness_contract plugins.flow-next.tests.test_capture_compaction_contract plugins.flow-next.tests.test_readback_ask_contract plugins.flow-next.tests.test_spec_ready -q (31 passed), ./scripts/sync-codex.sh && ./scripts/sync-codex.sh (passed), python3 scripts/run_tests_parallel.py (2156 passed, 3 skipped), cd /Users/gordon/work/flow-next.dev && pnpm build (74 pages, 0 diagnostics)
- PRs: