---
satisfies: [R8]
---

## Description

Docs, CHANGELOG, gates.

**Size:** S
**Files:** plugins/flow-next/docs/tracker-sync.md (+ architecture or orchestration note if apt), CHANGELOG.md, codex mirror

1. docs/tracker-sync.md: a short "Background dispatch (Claude Code)" section - what forks (comment ops, linked, Claude-only), what never forks, the two invariants, pointer to the reference.
2. CHANGELOG `## Unreleased` entry (no version bump - batched releases).
3. Full pytest + smoke green; sync-codex idempotent + all guards green.
4. flow-next.dev + vault ride the release walk, not this task.

## Acceptance
- [ ] R8: docs section + CHANGELOG entry + gates green + mirror clean

## Done summary
Added the "Background dispatch (Claude Code)" section to docs/tracker-sync.md (what forks - comment ops on linked specs, Claude-only; what never forks; both MUST invariants; tier ladder; pointer to references/tracker-dispatch.md as the sole rule source) and the fn-89 CHANGELOG entry under `## Unreleased` (no version bump, batched releases). Gates green: full unittest 1788 OK + smoke 144/144 post-change, sync-codex idempotent with all guards green and a clean mirror (docs are not mirrored). Implemented via codex delegation (gpt-5.6-terra, medium); impl-review resolved as deterministic triage-skip SHIP (docs-only diff).
## Evidence
- Commits: cb446438e193d0b719d424a77283f91cf6cb6d28
- Tests: baseline: green pre-edit (unittest 1788 OK, smoke 144/144), python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (Ran 1788, OK, skipped=2, post-change), bash plugins/flow-next/scripts/smoke_test.sh (144 passed, 0 failed, post-change), ./scripts/sync-codex.sh x2 (idempotent, all guards green, mirror clean - docs not mirrored)
- PRs: