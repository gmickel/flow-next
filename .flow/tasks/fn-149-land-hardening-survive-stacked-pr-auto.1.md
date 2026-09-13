---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16]
---
# fn-149-land-hardening-survive-stacked-pr-auto.1 Implement Land over chains and stacks: frontier-only merge, patch-id verdict carry-over, bounded retarget

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Land now drains chains and GitHub stacks one frontier at a time: every tick classifies each PR from the REST `stack` object and its base ref (workflow §2.0, nothing stored), merges only the lowest open layer (§2.8 frontier rule with a second stack read before the `merge-async` submit in §3.5b, `sha` pin, uuid poll, MERGED re-probe), keeps a review verdict across an equal-patch-id head move against the bound `verdict_head` (§2.2b, §2.3 window anchor), retargets the layers above a merged parent with a leased prepare-then-publish cascade driven by a resumable ledger record (§3.7, references/chains-and-stacks.md), and defers branch deletion through the top-level `pending_branch_deletes` map swept by the §0.5 janitor. A standalone PR with no children keeps today's merge arguments (`MERGE_FLAGS` is `--squash --delete-branch` unless the child count is non-zero or unread). No config key, no flowctl change (R13).

Error cases and their tests (plugins/flow-next/tests/test_land_chain_fixtures.py, bare origin + stubbed gh in fixtures/land_chain_gh_stub.py): failed REST/parent/children reads hold or keep the branch (R1/R4/R5: FailedReadsAndPrecedenceTestCase); stack 404 vs other (R1); stale pin refused, unenforced pin observed and disabled, pending uuid polled never re-submitted, non-frontier submit refused (R3: MergeAsyncTestCase); conflict → BLOCKED nothing published, lease failure resumed, moved layer re-prepared, push-then-lost-write resumed without a second rewrite, foreign rewrite and broken boundary NEEDS_HUMAN, unreadable child list prepares nothing, conflict mid-reconcile leaves the record untouched (R6: CascadeTestCase, CascadeRecoveryPersistenceTestCase); one clean-review comment carries across two equivalent rebases and clears on a real change, an unsatisfied evaluation writes no binding (R7/R8: PatchIdCarryOverTestCase); merge → janitor keeps → retarget → janitor deletes across four invocations, 403 keeps and 422 removes (R5: MergeAndJanitorTicksTestCase); the scoped handoff reconcile moves a clean checkout onto a validated rewrite and refuses unpushed local work (ScopedHandoffReconcileTestCase). Pinned tests updated for the deliberate merge-flag and action-enumeration changes (R5/R6/R11).

Docs (R14): land SKILL.md chains section + Forbidden list, references/chains-and-stacks.md, docs/skills.md land row, orchestration.md landing section, troubleshooting.md entry, CHANGELOG Unreleased, conduct/land.md item; codex mirror regenerated.

Reviewer note carried as non-blocking: the merge-verdict command (`land.mergeVerdictCommand`) re-runs at the current head on every merge attempt instead of being carried by the binding; the spec's R7 wording lists "the merge-verdict pin" among carried conjuncts, and carrying it from review evidence was a gate bypass (round-1 finding 1). Follow-up candidate, not built: a marker-derived chain base for a human-chosen non-default base that itself heads a PR (the walk stops at the default branch).

baseline: green (python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .)

stage: impl-review - ran [codex fan-out round 1 NEEDS_WORK (9 findings) -> round 2 NEEDS_WORK (2) -> round 3 NEEDS_WORK (1) -> round 4 SHIP]
## Evidence
- Commits: e4e020474587e2be77da1fe0a0e5968bee8355fe, 1d2030997e2a61016607da86b1504cc933eab4fa, 95c1a891876f2f749b2163e02e794d83c5e3c9f1, fac401b7fe1b5468e1359b3f0720bf7f7183fae9
- Tests: python3 scripts/run_tests_parallel.py (baseline: green, 4910 tests; verify runs after each fix round: green, 4948 tests at fac401b7), GATE_SKIPPED:unittest:green-receipt fac401b7 - baseline reused from prior post-gate pass, uvx ruff@0.16.0 check . (green at every round), python3 -m unittest test_land_chain_fixtures test_land_config test_land_patience_after_review test_land_merge_cmd_shell test_flow_merge_destination (focused, green), ./scripts/sync-codex.sh twice (idempotent, mirror committed)
- PRs: