---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-301-qa-re-checks-only-what-changed-since.1 Implement QA re-checks only what changed since its last pass

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
QA re-checks only what changed since its last pass.

- `flow-next-qa` workflow §2.3 and the gated `references/recheck.md`: with a prior receipt for the
  same spec, branch and a reachable head, QA tree-diffs prior head to HEAD and re-drives failed or
  blocked scenarios, touched surfaces and one smoke scenario; other passes carry. Broad shared-code
  diffs, a changed acceptance contract, a failing smoke run or unclear dependencies run in full.
- `flowctl qa receipt` takes per-scenario rows: live rows are stamped with the current head;
  carried rows are copied from the prior receipt and refused when absent, not passed, from another
  spec or branch, or at the same head. Coverage gains `carried`.
- Tests: two behaviour tests in `test_artifact_writers.py`; docs in `docs/flowctl.md`; CHANGELOG.

R5 study (pre-registered, two passes, 16 draws, Sonnet): recall held in every draw, the time rule
was not met. Local fix: 113 s vs 150 s mean, INCONCLUSIVE (gap 36.8 s, spread 38 s); one S draw
per pass skipped the re-check and ran in full. Shared-file fix: 133 vs 147 s, not confirmed.
Open item for the person: R5 is unmet by its pre-registered rule; landing is a product call.

stage: impl-review - ran [R1 NEEDS_WORK (2 kept: R2 contract wording, R5 evidence) .. R2 SHIP]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 24fea0a36cc7ee0af7db3fbcb9119a6bd258825b, 7e4ec8d062e99e180894622358de4de2902573c6, adf78d6506e8ba14ebe982e6e01bc374e02798fa
- Tests: python3 -m unittest plugins/flow-next/tests/test_artifact_writers.py, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: