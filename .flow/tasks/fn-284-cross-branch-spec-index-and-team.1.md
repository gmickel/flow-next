---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9]
---
# fn-284-cross-branch-spec-index-and-team.1 Implement Cross-branch spec index and team branching docs

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added `flowctl specs --refs [--fetch] [--json]`: a read-only index of specs across the base ref, local branches and remote-tracking refs. A branch copy is live when merging the branch would change the spec body (three-way `git merge-file` over temporary blob files, squash-safe, no git version floor raised), stale otherwise; `--fetch` prune-fetches origin and fails open. Plain `specs` is unchanged. spec-scout reads the index (step 1b): cross-branch specs become ref-named overlaps unless both endpoints exist in the checkout; conflicting copies stay overlaps with their tip date; older flowctl falls back. Runtime docs updated (`docs/flowctl.md` + Codex mirror); flow-next.dev teams-guide section and CLI reference committed separately on flow-next.dev branch `docs/fn-284-specs-across-branches` (104575f), unpublished until release.

Evidence: 15 fixture tests (simulation scenarios, R1/R2/R4 errors, unchanged plain output, no writes without --fetch, hash-seed determinism); classifier mutations and the three review-round regressions each fail before their fix. R6: 1.19-1.23s on this repo (131 refs, 274 specs). Full suite ran once (3972 tests, 1 failure: the new module's missing scripts/ sys.path line, fixed and re-checked); ruff, sync-codex --check, site build green.

stage: impl-review - ran [round 1 NEEDS_WORK (3 findings fixed) .. round 2 SHIP] (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: a7589dc2420c0ef18a2360e8a20b6c2bad695778, 434b40ba6cbb949bd8f032f67674c64b1bcdf0fd
- Tests: python3 scripts/run_tests_parallel.py, python3 scripts/run_tests_parallel.py --pattern test_spec_ref_index.py, uvx ruff@0.16.0 check .
- PRs: