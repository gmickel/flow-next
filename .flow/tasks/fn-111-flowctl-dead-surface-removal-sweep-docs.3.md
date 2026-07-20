# fn-111-flowctl-dead-surface-removal-sweep-docs.3 Dead command surfaces + dep-helper extraction + test prune

## Description
Remove the remaining dead command surfaces + dead fields, extract the shared dep helper, prune their tests.

**Size:** M
**Files:** both flowctl.py copies, plugins/flow-next/scripts/ci_test.sh (line ~716 cleanup), tests per fn-101 section 7

### Approach

- Read fn-101 plan sections 2 + 7 first. Remove: `rp windows`, `rp pick-window` (+ its state-file write ~flowctl.py:20389 and stale docstring ~20287), `rp ensure-workspace`, `rp builder`, `prep-chat`; `memory discoverability-patch` (~357 LOC); `task show-backend` (~180); `task set-deps` (~80 - FIRST extract the shared dep-validation helper for the two surviving dep paths, then delete the third copy); `sync clear-dep-relation`; `strategy list`; `repo-map show`; `repo-map since-ref`; `prospect list`; `prospect read`; `checkpoint delete`; `state-path`; `pilot-log summary` (reader ONLY - `append` and .flow/pilot-runs/ rows stay); backend `check` triplet; always-empty `review_receipts` export field; dead `--section` export filter.
- `scope suggest` is NOT in scope (fn-113 owns it). Do not touch it or its tests.
- ci_test.sh: remove the pick-window state-file cleanup (~line 716) and any invocations of removed commands.
- Prune tests per fn-101 section 7 (set-deps/show-backend cases; leave scope-suggest cases alone). Verify each candidate pins the removed surface before deleting.
- Dual-copy mirrored; sync-codex x2. NO git commands.

### Acceptance

- [ ] Every listed surface gone from flowctl --help and code; scope suggest + pilot-log append untouched
- [ ] Shared dep helper extracted; the two surviving dep paths use it; behavior unchanged
- [ ] ci_test.sh green (bash plugins/flow-next/scripts/ci_test.sh from a temp dir) with no references to removed commands
- [ ] Focused suites green: --pattern "test_task*.py", --pattern "test_memory*.py", --pattern "test_export*.py", --pattern "test_prospect*.py"
- [ ] Both flowctl.py copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
All remaining dead command surfaces removed (-2075 LOC flowctl dual-copy, ~5.1k LOC total with smokes+tests): rp windows/pick-window/ensure-workspace/builder + state-file write, prep-chat, memory discoverability-patch, task show-backend, task set-deps (third dep copy deleted after extracting _resolve_same_spec_deps shared by task create --deps and dep add), sync clear-dep-relation, strategy list, repo-map show/since-ref, prospect list/read, checkpoint delete, state-path, pilot-log summary (append + rows stay), backend check triplet, always-empty review_receipts export field, dead --section export filter. scope suggest untouched (fn-113). Delegate applied both task-2 lessons (smoked neighboring flags; grepped tests for removed symbols - rewrote set-deps tests to dep add, pilot substrate to row files). Host review found 2 stale prose refs via fleet-caller sweep: tracker-sync SKILL.md still named clear-dep-relation (no live caller - set-dep-relation, the live one, was correctly kept), and the usage.md template still pointed at flowctl state-path (reworded to name .git/flow-state/ directly; template+dogfood byte-identical). Full parallel suite green: 83 files, 1815 tests, 0 failures, 81.5s; ci_test.sh 67/67; sync-codex x2 idempotent.
## Evidence
- Commits: 576bc6792e5d26aa2b8e826a07ca81def0728965
- Tests: python3 scripts/run_tests_parallel.py (83 files, 1815 tests, 0 failures, 81.5s), bash ci_test.sh from temp dir (67 passed, 0 failed), focused: test_task* 19 / test_memory* 136 / test_export* 31 / test_prospect* 90 / parity suites green
- PRs: