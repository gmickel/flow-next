---
satisfies: [R3, R4, R5]
---
# fn-141-tracker-determinism-c-prose-teardown.2 Remove tracker-runner; rewire callers; RETAIN the caller gate

## Description
Remove the `tracker-runner` agent and `references/tracker-dispatch.md`. Touchpoints call `flowctl tracker <verb>` directly.

**Retain the caller-side gate** - only transport-ladder and dispatch prose is removed. Every flowctl command emits JSON and `inactive` is an error class, so routing a bridge-inactive repo into flowctl would replace silence with output and an extra process. The gate is what preserves the invariant that non-tracker users see nothing.

Explicitly enumerate the `perEvent` to verb mapping (`push`/`reconcile`/`comment`) rather than deleting it with the dispatch prose, and reassign comment content synthesis by name to each calling skill so it is not orphaned.

Sweep all fourteen calling skills plus the codex mirror plus `docs/platforms.md:120,300`.

## Acceptance
- [ ] tracker-runner agent + dispatch reference removed
- [ ] Caller-side gate retained; perEvent->verb mapping enumerated
- [ ] Comment synthesis reassigned by name to each calling skill
- [ ] Zero dangling references across 14 skills, codex mirror, docs/platforms.md (asserted by test)
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
