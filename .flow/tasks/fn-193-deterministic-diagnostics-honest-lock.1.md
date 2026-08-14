---
satisfies: [R1, R2]
---
# fn-193-deterministic-diagnostics-honest-lock.1 config_lock: fail fast + honest message composition on unavailable locks

## Description
R1+R2 in plugins/flow-next/scripts/flowctl_tracker/config_lock.py: keep the last mkdir exception in the acquire loop (~:262-266 currently swallows PermissionError for the Windows delete-pending case); when the lock path does NOT exist and the last error was PermissionError, fail FAST (do not burn the deadline) raising ConfigLockUnavailable (subclass ConfigLockTimeout so all ~25 except sites keep working) with errno/strerror + the lock parent path - never the 'holder appears alive' text. When the lock path EXISTS: PermissionError keeps polling to the deadline (Windows carve-out preserved); on timeout, compose the message from what was observed - owner.json readable -> pid/host/acquired_at; owner absent/unreadable -> say so + when the dir becomes stale-reclaimable (STALE_OWNER_S minus dir age). 'holder appears alive' appears ONLY when an owner was actually read. R5(a-d) tests: add to the lock-test surface (tests/test_tracker_resolved_cache.py lock class or tests/test_portable_locks.py - match whichever harness fits): unwritable .locks -> ConfigLockUnavailable well under timeout_s, message has permission+path, NOT 'holder appears alive' (skipIf Windows or euid==0); held lock -> pid/host in message; ownerless fresh config.d -> owner-absent + reclaim-at message; PermissionError-while-exists -> polls to deadline. FORBIDDEN: changing LOCK_TIMEOUT_S/STALE_OWNER_S/poll interval (spec-fixed constants, no config keys); environment diagnosers (no uid checks, mount sniffing, ACL parsing); touching the review-attempt code (task 2). Compare paths/messages in posix form where git-facing.

## Acceptance
R1+R2+R5(a-d) met; cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolved_cache test_portable_locks -q green (run BARE, never piped); ruff clean.

## Done summary
ConfigLockUnavailable (subclass of ConfigLockTimeout) fails fast when the lock can never be created (denied mkdir + path absent - errno/strerror + parent path in the message); real timeouts compose the message from observations: owner facts when read, owner-absent + reclaim-at when not, denied-while-exists keeps the Windows pending-delete poll; "holder appears alive" reserved for an actually-observed owner. FileExistsError resets last_error so contention never hits the permission branch. Bonus in-family: the pre-loop parent mkdir (previously a raw traceback) wraps to the same class. 6 new tests, 81 total green.
## Evidence
- Commits: d15f63a5
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolved_cache test_portable_locks -q
- PRs: