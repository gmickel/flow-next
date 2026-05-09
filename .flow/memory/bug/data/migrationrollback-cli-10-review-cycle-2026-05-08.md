---
title: "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)"
date: "2026-05-08"
track: bug
category: data
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-43, migration, rollback, lockfile, sentinel, atomic-write, crash-recovery, cross-platform, review-feedback]
problem_type: data
symptoms: migrate-rename / migrate-rollback design surfaced 10 compound bugs across 6 review cycles
root_cause: treating migration as 'plain file moves' rather than as a transactional protocol with explicit recovery semantics
resolution_type: fix
---

## Problem
fn-43.3 implements `migrate-rename` + `migrate-rollback` for the pre-1.0 → 1.0 .flow/ layout migration. Reviewers (codex:gpt-5.5:high) surfaced 6 cycles of compound concerns:

1. Cross-platform PID liveness — `os.kill(pid, 0)` is destructive on Windows.
2. Crash-recovery decision tree — distinguishing "clean rollback aftermath" from "mid-migration crash" via manifest presence.
3. Paired markdown twins — rollback that only removes `.json` leaves orphan `.md` files.
4. No-op contract — "no epics/ + no sentinel" must NOT mutate state.
5. Stale-lock pid-write race — crash between `os.mkdir(lock_dir)` and `pid_file.write_text` left a pidless lock that never reclaimed.
6. Manifest-only check insufficient — rewritten task JSON drift bypassed detection because `expected_tasks` skipped content compare.
7. Mid-migration recovery contamination — leftover `specs/fn-1.json` from a partially applied migration survived "restore from backup".
8. Read-only writability check ordered before idempotency — already-migrated read-only repo was rejected instead of no-op.
9. Sentinel write was non-atomic + existence-only check — empty/partial sentinel fooled idempotent skip into running on a half-migrated tree.

## What Didn't Work
- Initial cross-platform lock used `os.kill(pid, 0)` — works on POSIX as a no-op signal but on Windows actually maps to TerminateProcess semantics. A second `migrate-rename` could kill its peer holder.
- Crash-recovery treated "complete backup + no sentinel" as a single state → mid-migration crash. But "rolled back, then user edited legacy state, then re-ran migrate-rename" hit the same predicate and silently restored stale pre-1.0 state over edits.
- Manifest-as-whitelist for post-migration-write detection skipped content drift on tasks the migration itself touched. A user editing `tasks/fn-1.1.json` post-migration was silently clobbered by rollback.
- Plain `write_text` for the sentinel — a crash mid-write left an empty file that the existence-check treated as "already migrated".

## Solution
- **F1:** Branch `_migrate_pid_alive` on `sys.platform`. Windows uses `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE)` + `GetExitCodeProcess` via ctypes (no pywin32 dep). POSIX path unchanged.
- **F2:** Three-way decision tree: no `.complete` → mid-copy crash; `.complete` + no manifest → clean rollback aftermath (preserve backup, fresh snapshot below); `.complete` + manifest → mid-migration crash (restore + retry).
- **F3:** Detection scans `specs/*.md` and `tasks/*.md` AND compares against backup. Restore phase also copies `specs/fn-*.md` from backup.
- **F4:** "No epics/ + no sentinel" returns `{migrated: false, reason: "no pre-1.0 layout detected"}` with no writes. Spec step 3 says "if neither, exit 0" — true no-op.
- **F5:** Per-file content compare via `filecmp.cmp(shallow=False)` for spec/task JSON + markdown. Restore step C now copies both `.json` and `.md` from backup.
- **F6:** Grace window (`MIGRATE_LOCK_PID_GRACE_SECS = 5`) for pid-file write race. Lock-dir mtime older than grace + missing pid → reclaim.
- **F7:** Manifest entries for `rewrite_task` now carry `post_sha256` (from `_migrate_file_sha256`). Drift detection compares current SHA against recorded post-migration SHA.
- **F8:** `_migrate_recover_from_complete_backup` now does two phases: (1) wipe all `.flow/` contents except backup, lock, banner; (2) copy backup back. Prevents migration-created leftovers from surviving "restore from pre-migration backup".
- **F9:** Idempotency check moved BEFORE the read-only writability probe. Already-migrated repo on read-only filesystem is a no-op regardless of mode.
- **F10:** `atomic_write(sentinel, payload)` instead of `write_text`. New `_migrate_sentinel_state(flow_dir)` returns `(valid, payload)` — empty/garbage triggers crash recovery; matches `FLOW_VERSION_PAYLOAD` OR forward-compat semver shape.

## Prevention
When implementing migration / rollback / lockfile primitives:

- **Never use `os.kill(pid, 0)` blindly** for cross-platform liveness. Branch on `sys.platform`. POSIX → no-op signal probe; Windows → `OpenProcess` + `GetExitCodeProcess` via ctypes.
- **Never use existence-only checks for idempotency anchors.** Validate the payload. Empty/partial files from crashed writes look identical to "I'm done" without a content check.
- **Always use atomic_write for files that gate idempotency.** A crashed plain `write_text` is the single highest-leverage data-loss footgun in stateful CLI tools.
- **The "manifest-as-whitelist" pattern is insufficient for files the migration itself touches.** Record content hashes in the manifest so post-migration drift on rewritten files is detectable.
- **Recovery must be content-clean, not append-only.** When restoring from a backup over a partially-mutated tree, wipe migration-created artefacts FIRST. "Copy backup over" alone leaves leftovers that contaminate the next snapshot.
- **Distinguish "I rolled back cleanly" from "I crashed mid-migration"** via a non-overlapping signal. Backup `.complete` alone can't distinguish; manifest presence does (rollback deletes manifest, mid-migration crash leaves it).
- **Read-only filesystem checks must come AFTER idempotency checks.** A no-op should never fail just because the underlying tree happens to be frozen.
- **Two-phase commit for state migrations:** lock → snapshot → write manifest → mutate → write sentinel-LAST. Each step is atomic; the sentinel-last invariant is the recovery anchor.
- **Pid-file write race after `os.mkdir(lock)`:** never assume the pid file is present. Add a grace window + mtime-based stale detection so a crashed peer doesn't leave a permanently-occupied lock.
