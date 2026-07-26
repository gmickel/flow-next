---
satisfies: [R3, R4, R5]
---
# fn-141-tracker-determinism-c-prose-teardown.2 Remove tracker-runner; rewire callers; RETAIN the caller gate

## Description
Touchpoints call the **fn-140 lifecycle facade** `flowctl tracker sync <spec-id> --op push|pull|reconcile|comment --event <key>` - NOT the granular verbs, which cannot preserve behavior alone (create-if-unlinked, comment markers, dedup and receipts are orchestration). **Gated on fn-140 R19 conformance.** Then remove the `tracker-runner` agent and `references/tracker-dispatch.md`.

**Retain the caller-side gate** - only transport-ladder and dispatch prose is removed. Every flowctl command emits JSON and `inactive` is an error class, so routing a bridge-inactive repo into flowctl would replace silence with output and an extra process. The gate is what preserves the invariant that non-tracker users see nothing.

Explicitly enumerate the `perEvent` to verb mapping (`push`/`reconcile`/`comment`) rather than deleting it with the dispatch prose, and reassign comment content synthesis by name to each calling skill so it is not orphaned.

Sweep is **enumerated, not a single grep**: every canonical calling skill by name; `scripts/sync-codex.sh` (**18** runner-specific references incl. transforms and guards); runner-specific tests; the generated mirror's agent TOML; `docs/platforms.md:120,300`.

## Acceptance
- [ ] tracker-runner agent + dispatch reference removed
- [ ] Caller-side gate retained; perEvent->op mapping enumerated for ALL values incl. `pull`
- [ ] Comment synthesis reassigned by name to each calling skill
- [ ] Zero dangling references across the ENUMERATED inventory incl. sync-codex.sh transforms/guards, runner tests, mirror TOML (asserted by test over the named list)
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
