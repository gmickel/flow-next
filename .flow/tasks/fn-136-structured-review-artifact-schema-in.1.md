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
Added a six-backend review-output fixture corpus with SHIP, ratchet-only, anchorless, unparseable, and catalog-specific cases. The survey distinguishes directly observed from synthetic-boundary variants, resolves each catalog entry to provenance and fixtures, and pins normalized per-fixture severity, confidence, classification, status, and anchor expectations.

RepoPrompt CE review converged in chat `review-fixture-corpus-96EEF1`: NEEDS_WORK findings were fixed in `4af52b72` and `adfe1b28`; final verdict SHIP with zero introduced findings and no unaddressed R-IDs.
## Evidence
- Commits: 1681f4125c026026ce899af5bff8ab936c0f6aa3, 4af52b72, adfe1b28
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_findings_fixture_corpus -q
- PRs: