---
satisfies: [R8, R8b, R10, R12, R13]
---

# fn-139-tracker-determinism-a-transport.3 tracker.resolved: scoped timestamps, lock transaction, migration
# fn-139-tracker-sync-determinism-flowctl-owns.3 Spec-aware status verb: fn-66 evidence gate + who-wins ladder

## Description
Implement the cache using the epic's schema **verbatim**: a `scopeResolvedAt` map keyed by exact scope path (`destination`, `destination.statusIds`, `destination.stateIds`, `capabilities`), plus a top-level `resolvedAt`.

`resolvedAt` is set **only** when every required field is present, **preserved** across a partial refresh, and **cleared** if a refresh reveals a now-missing required field. It is never a TTL input. A scoped destination refresh must not make capabilities look fresh.

**The transaction is the hard part.** Atomic write plus a lock does NOT prevent stale-read clobbering: two resolvers can read, compute different scopes, then serially replace the whole config. Required order: network work **outside** the lock; acquire the lock **shared by every `.flow/config.json` writer** (today `set_config` writes without it and can race a resolve); re-read **inside**; merge **only the resolved scope**; validate; atomically replace.

Implement the state machine and its transitions behind a seam. Rows triggered by a mutation verb (stale-id retry, capability downgrade, retry exhaustion) are unit-tested through that seam here and wired to real verbs in spec B.

Migrate `perTracker.apiVersion: 3` to 2.

## Acceptance
- [ ] `scopeResolvedAt` map with the epic's exact keys; no `destinationResolvedAt`/`capabilitiesCheckedAt` fields
- [ ] `resolvedAt` set/preserved/cleared per the rule above, tested for each transition
- [ ] Scoped refresh does not falsely freshen another scope
- [ ] Two DIFFERENT-scope concurrent resolves do not clobber each other
- [ ] Discovery-input FINGERPRINT compared inside the lock; a mid-resolve project/type change is discarded or returns `class: conflict` (tested with a real repoint, not an unrelated write)
- [ ] Lock path, timeout, stale-owner recovery and crash behavior specified and tested
- [ ] `set_config` AND `cmd_init` both route through the shared lock
- [ ] Contention + crash recovery exercised on the Windows CI row
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
