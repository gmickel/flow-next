# fn-111-flowctl-dead-surface-removal-sweep-docs.4 Docs-drift sweep + CHANGELOG rider + full gate

## Description
Docs-drift sweep + CHANGELOG rider + final full gate.

**Size:** M
**Files:** plugins/flow-next/docs/flowctl.md, plugins/flow-next/docs/architecture.md, plugins/flow-next/docs/ralph.md, CHANGELOG.md

### Approach

- Read fn-101 plan section 6 (11 drift items). flowctl.md: document setup-block, scope, strategy section, spec skeleton, codex classify-result/rollback-plan, rp setup-review/chat-send (NOT the removed rp commands), done --summary/--evidence; add pilot-log append + review-rounds to Available Commands; REMOVE all commands tasks 1-3 deleted (migrate-*, aliases, rp windows/pick-window/ensure-workspace/builder/prep-chat, memory discoverability-patch, task show-backend/set-deps, sync clear-dep-relation, strategy list, repo-map show/since-ref, prospect list/read, checkpoint delete, state-path, pilot-log summary, backend check); fix the File Structure tree.
- architecture.md: complete the .flow/ layout (add pilot-runs/, sync-runs/, locks/, receipts/ etc. per actual init scaffold).
- ralph.md + flowctl.md: fix the state.json claim (PAUSE/STOP sentinels + progress.txt are the actual mechanism); complete the guard-rules table. Do NOT touch the "zero overhead" claim (fn-114 owns it).
- CHANGELOG: ONE `## Unreleased` entry covering the whole sweep. MUST carry the breaking-change note: pre-1.0 repos port by hand via the usage.md prose (point at it), and the epic-alias/dual-emit removal requires the flow-swarm migration (maintainer-owned). Register-conformant, no em dashes.
- Final gate: python3 scripts/run_tests_parallel.py (full corpus) green; bash smoke_test.sh + ci_test.sh from temp dirs green.
- sync-codex x2 if any canonical skill/docs files under the mirror changed. NO git commands.

### Acceptance

- [ ] All 11 fn-101 section-6 drift items addressed; no removed command remains documented anywhere in docs/
- [ ] CHANGELOG Unreleased entry with both breaking-change notes (pre-1.0 porting prose pointer, flow-swarm migration flag); NO version bump
- [ ] Full parallel suite green; smoke_test.sh + ci_test.sh green; timings recorded in evidence

## Acceptance
- [ ] TBD

## Done summary
Docs-drift sweep: all 11 fn-101 section-6 items addressed (setup-block/scope/strategy/spec-skeleton/codex classify-result+rollback-plan/rp setup-review+chat-send/done --summary+--evidence documented; pilot-log append + review-rounds listed; File Structure + architecture.md .flow/ layout completed; ralph state.json claim fixed to PAUSE/STOP sentinels + progress.txt; guard table expanded; removed commands scrubbed from all docs). CHANGELOG consolidated into ONE Unreleased entry with both breaking notes (pre-1.0 porting prose pointer; flow-swarm epics-key migration, maintainer-owned). Host review fixed final-gate fallout in the smoke harness: legacy epic/legacy_reason/blocked_epics/epic_blocked_by asserts updated to canonical keys WITH resurface guards, and a syntax-broken copilot availability probe introduced in .3 (bash -n added to review checks; the script's rc=0-on-midfile-syntax-error masked it). Final gates all green: full parallel suite 83 files / 1815 tests / 0 failures / 90.5s; smoke_test.sh All tests passed (end-to-end this time); ci_test.sh 67/67.
## Evidence
- Commits: e7b0e239aa0109e1b7d783d61ff4aa179dda6c21
- Tests: python3 scripts/run_tests_parallel.py (83 files, 1815 tests, 0 failures, 90.5s), bash smoke_test.sh (All tests passed, rc=0), bash ci_test.sh (67 passed, 0 failed), bash -n smoke_test.sh (syntax clean)
- PRs: