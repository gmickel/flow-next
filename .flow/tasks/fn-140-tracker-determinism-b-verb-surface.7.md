---
satisfies: [R19]
---
# fn-140-tracker-determinism-b-verb-surface.7 Lifecycle facade: tracker sync --op push|pull|reconcile|comment

## Description
Build the facade callers actually invoke. The granular verbs are the mechanism; without this, every calling skill would have to compose them in prose - which is exactly what this batch removes, and would make spec C's behavior-preserving teardown impossible.

```
flowctl tracker sync <spec-id> --op push|pull|reconcile|comment --event <perEvent-key> [--flow-file F] [--body-file B]
```

The four ops match the existing `perEvent` vocabulary exactly (`off | pull | push | reconcile | comment`). The facade owns create-if-unlinked, the granular-verb sequence, comment marker + dedup, the event-tagged receipt, and structured conflict/degradation reporting.

Judgment-bearing content is passed **in** as a file. The facade never renders a body, never resolves a merge, never writes comment prose.

## Acceptance
- [ ] All four ops implemented and conformance-tested per adapter
- [ ] `push` on an unlinked spec performs create-if-unlinked, then the sequence
- [ ] Comment marker + dedup reproduce current behavior (no duplicate on re-run)
- [ ] Event-tagged receipt written once per invocation
- [ ] Conflict and degradation surface structurally, not as prose
- [ ] Facade composes NO judgment content; body/comment text is always an input file
- [ ] A caller can replace a today-dispatch with one facade call and observe identical tracker state

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
