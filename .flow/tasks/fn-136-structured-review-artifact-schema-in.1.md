---
satisfies: [R2]
---
# fn-136-structured-review-artifact-schema-in.1 Field survey + parser fixture corpus per backend

## Description
Catalog what reviewers ACTUALLY emit per backend and build the parser fixture corpus.

**Size:** S

**Files:** new fixtures under the fn-130 reached-path harness home (plugins/flow-next/tests/... fixtures dir - follow its layout); a short survey note in the task summary.

### Approach
- Harvest real reviewer outputs: recent receipts in THIS repo (.flow/review-receipts + tmp receipts), the fn-130 fixtures/b0 corpus, and the flow-swarm dogfood receipts (fn-114..124 plan/impl reviews are codex gpt-5.6-sol shaped) - catalog label variants (Severity vs P-levels, File:Line forms, ratchet lines "Prior finding N - fixed", confidence anchors, classification labels) per backend: codex/copilot/cursor/host/rp/export.
- Write fixture files per backend shape incl. edge cases: no findings (SHIP), ratchet-only re-review, findings without file anchors, unparseable prose.
- Quick commands: cd plugins/flow-next/tests && python3 -m unittest <new fixture test module> -q.

## Acceptance
- [x] Fixture corpus per backend shape committed on the fn-130 harness layout; variant catalog recorded in the done summary (R2).

## Done summary
Surveyed codex, copilot, cursor, host, RepoPrompt and export review shapes. The
v1 corpus under `optimization/reached-path/fixtures/review-findings/v1/`
records directly observed versus synthetic-boundary variants with per-entry
source and fixture references. Its per-backend oracle pins canonical severity,
confidence, classification, current/ratchet status and anchor presence without
guessing missing anchors. Cases cover SHIP without findings, ratchet-only
re-review, anchorless findings, unparseable prose and catalog-specific layouts.
Focused verification:
`cd plugins/flow-next/tests && python3 -m unittest test_review_findings_fixture_corpus -q`.

## Evidence
- Commits:
- Tests:
- PRs:
