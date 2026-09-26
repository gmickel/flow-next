---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-262-feature-map-stays-current-and-is-always.1 Implement Feature map stays current and is always recommended

## Description
TBD

## Acceptance
Every R-ID in the parent spec's Acceptance Criteria section is satisfied; judge this task against the spec's criteria directly.

## Done summary
The feature map now stays current as part of normal work, and setup and prime always recommend it. The new read-only `flowctl features status [--json]` reports each feature file's `**Last proven:**` line, its age in surface-touching default-branch commits (`features.staleAfterCommits`, default 50), the open `feature-map-drift` notes, and a seed/maintain/none recommendation. Work's quality phase updates only the feature files its change altered (new reference `flow-next-work/references/feature-map-update.md`), and workers never edit the map. Seed and maintain write the provenance line. Maintain refreshes it on every file it proves and retires drift notes whose route it re-proved; a note with uncommitted edits is left open. Readers reopen a retired note when the same route drifts again (`mark-fresh`), and drive now files drift notes as QA does. Flow's no-argument reading prints `Also recommended: /flow-next:features` when the map is due. Setup and prime print the recommendation on every run.

R7 site docs are on flow-next.dev branch `fn-262-feature-map-stays-current-and-is-always` (worktree /home/gordon/work/flow-next.dev-fn-262, commits d7aa175 and dbd9395). They are not pushed; `pnpm build`, `test`, `check:links` and `check:seo` exited 0.

Tests: plugins/flow-next/tests/test_features_status.py (R1 line states and malformed-as-absent, R5 age counting, date fallback, drift due and recurrence, memory disabled, no .flow/ reads as seed). Surface and invocation inventories were updated for the new command.

Tier: session (jev intelligent 0.70)
stage: impl-review - ran (codex fan-out NEEDS_WORK, 4 findings fixed; round 2 SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b292c13b2ccb1f784d5faedd919d15c013c5acf8, ab985db5ede08cf102f61cfdb7ae87e9656e4f23, f2d2be1ba8a10628a1c1f4886af82424496f7ac9
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: