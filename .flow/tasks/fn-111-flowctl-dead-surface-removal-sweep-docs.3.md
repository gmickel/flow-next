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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
