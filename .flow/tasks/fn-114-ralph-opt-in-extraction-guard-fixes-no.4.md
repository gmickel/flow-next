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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
