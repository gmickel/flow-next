---
satisfies: [R8,R10,R12,R13]
---

# fn-139-tracker-determinism-a-transport.3 tracker.resolved: scoped timestamps, lock transaction, migration
# fn-139-tracker-sync-determinism-flowctl-owns.3 Spec-aware status verb: fn-66 evidence gate + who-wins ladder

## Description
Implement the cache with **per-scope timestamps** - `destinationResolvedAt`, `capabilitiesCheckedAt`, and a top-level `resolvedAt` meaning "all required fields complete", never a TTL input. A scoped destination refresh must not make capabilities look fresh.

**The transaction is the hard part.** Atomic write plus a lock does NOT prevent stale-read clobbering: two resolvers can read, compute different scopes, then serially replace the whole config. Required order: network work **outside** the lock; acquire the lock **shared by every `.flow/config.json` writer** (today `set_config` writes without it and can race a resolve); re-read **inside**; merge **only the resolved scope**; validate; atomically replace.

Implement the state machine and its transitions behind a seam. Rows triggered by a mutation verb (stale-id retry, capability downgrade, retry exhaustion) are unit-tested through that seam here and wired to real verbs in spec B.

Migrate `perTracker.apiVersion: 3` to 2.

## Acceptance
- [ ] Per-scope timestamps; scoped refresh does not falsely freshen another scope
- [ ] Two DIFFERENT-scope concurrent resolves do not clobber each other
- [ ] resolve-versus-`config set` race tested; shared writer lock
- [ ] State machine transitions unit-tested through the seam
- [ ] `resolve` backfill vs consuming-verb `class: unresolved` separately tested
- [ ] Transient 403 on tier probe does not flip a capability
- [ ] `apiVersion: 3` migrates to 2; partial resolution never stamps `resolvedAt`

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
