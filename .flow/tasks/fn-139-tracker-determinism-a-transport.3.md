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
tracker.resolved cache delivered with the epic's schema verbatim and the R8/R8b transaction.

- config_lock.py: the ONE shared .flow/config.json writer lock - atomic lock dir .flow/.locks/config.d + owner.json {pid,host,acquired_at}; 10s timeout; stale owner (>120s, pid dead on same host) reclaimed by rule; crash between mkdir and owner write reclaimed by dir age; other hosts never reclaimed by age. Windows liveness is query-only (OpenProcess/GetExitCodeProcess - os.kill(pid,0) TERMINATES on Windows). Reclamation is ABA-free: a kernel-released OS file-lock claim (flock/msvcrt) serializes reclaimers with a race-free staleness re-check inside it, and removal goes through rename-to-trash so the live path is never rmtree'd. Full symlink containment on lock dirs AND the claim leaf (lstat + O_NOFOLLOW).
- resolved_cache.py: canonical scopeResolvedAt (exactly 4 scope paths, legacy flat fields rejected); resolvedAt set-only-complete / preserved-on-partial / cleared-on-missing per tracker; scope-isolated merges; discovery fingerprint compared INSIDE the lock, one bounded re-resolve then class conflict; capability truth table + tier-probe application (failed probe never flips/re-stamps); TTL GitLab-only; apiVersion 3->2 in-transaction; state table as total plan_transition seam (spec-B rows tested through it); corrupt (non-object) config refused with zero byte change.
- flowctl.py: set_config + cmd_init whole read-modify-write inside the shared lock (guarded import, older copies degrade to current semantics); .locks/ gitignored.

4 review rounds (codex): 7 findings (Windows kill-probe, two ABA layers, unbounded reclaim spin, two symlink escapes, corrupt-config overwrite) all fixed with regression tests; round 4 SHIP, R8/R10/R12/R13 met, R8b met after fixes.
## Evidence
- Commits: 58e418af, 623ede52, 286a562b, 21fd4dc3
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolved_cache -q, python3 scripts/run_tests_parallel.py
- PRs: