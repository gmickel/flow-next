# fn-114-ralph-opt-in-extraction-guard-fixes-no.4 Ralph docs truth-up + CHANGELOG rider + full gate

## Description
Ralph docs truth-up + CHANGELOG rider + full gate.

**Size:** S
**Files:** plugins/flow-next/docs/ralph.md, docs/platforms.md, CLAUDE.md (cross-platform checklist hooks row), CHANGELOG.md

### Approach

- ralph.md: opt-in install story (ralph-init registers hooks, consent-gated; nothing by default), guard-rules table completeness, the zero-overhead claim is now literally true - say so plainly; PAUSE/STOP + progress.txt already fixed by fn-111 - verify current text.
- platforms.md: per-host hook installation difference (Claude Code + Droid supported, Cursor not - different hook events).
- CLAUDE.md cross-platform checklist: hooks row updated (no plugin-level hooks; ralph-init owns registration).
- CHANGELOG [Unreleased] rider covering all fn-114 tasks (register-conformant, no em dashes; note the fresh-install zero-hooks change loudly - existing ralph users re-run ralph-init after upgrade).
- Full gate: full parallel suite + smoke_test.sh + ci_test.sh green (host re-runs).

### Acceptance

- [ ] Docs truthful on all three surfaces; CHANGELOG rider with the re-run-ralph-init upgrade note
- [ ] Full suite + smokes green

## Acceptance
- [ ] TBD

## Done summary
Docs describe the shipped state on every surface: ralph.md carries the opt-in install story (ralph-init registers project hooks, consent-gated, nothing by default) and the zero-overhead claim is now literally true and stated as such; platforms.md documents per-host hook installation (Claude/Droid supported, Codex subset, Cursor scaffold-only); flowctl.md drops the ralph command group and documents the status soft-probe; sync-codex.md reflects no-hooks-generation; CLAUDE.md cross-platform checklist row 4 updated. Consolidated CHANGELOG rider covers all four tasks with the loud upgrade note (existing ralph users re-run ralph-init or the guard never fires and flowctl ralph is gone). test_ralph_docs_truth (6) pins the claims. Host review: fixed the README ralph-init one-liner and local-dev.md plugin-hooks flavor grok flagged; smoke failure triaged as a live-copilot-CLI flake (clean rerun 136/136; leg untouched by fn-114, CI does not run it). Final gates: full parallel suite 89 files / 1889 tests / 0 failures / 71.6s; smoke_test.sh all-pass on rerun; ci_test.sh 67/67; sync-codex x2. flow-next.dev intentionally NOT walked - the batched release (stopped before, per maintainer) owns the downstream walk.
## Evidence
- Commits: f8074ae8d1b9483c0d123e50835c993bbf287d7b
- Tests: python3 scripts/run_tests_parallel.py (89 files, 1889 tests, 0 failures, 71.6s), bash smoke_test.sh (All tests passed 136/136 on rerun; first run hit a live-copilot flake), bash ci_test.sh (67/67), test_ralph_docs_truth 6 green
- PRs: