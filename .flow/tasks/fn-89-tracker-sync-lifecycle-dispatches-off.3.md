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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
