---
satisfies: [R5, R6, R8, R26, R32]
---

## Description

Implement the deterministic CLI migration path: `flowctl migrate-rename` (dry-run default + `--yes` to commit) and `flowctl migrate-rollback`. Cross-platform atomic lockfile via `os.mkdir`. Transactional backup with two-phase `.complete` marker for crash recovery. `.flow/.flow_version` sentinel written last as the idempotency anchor. Migration manifest at `.flow/.migration-manifest` (top-level, NOT inside backup). Migration bumps `meta.json` `schema_version` from 2 -> 3 (T1 already raised the source-side `SCHEMA_VERSION` constant; T3 is the on-disk migration that updates existing repo `meta.json` files). The `.migration-manifest` is deleted on rollback. NO auto-trigger (T4).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- New subcommand `flowctl migrate-rename`: `--dry-run` (default), `--yes` (commit), `--json` mode.
- New subcommand `flowctl migrate-rollback`: restores from `.flow/.backup-pre-1.0/`, reverts `.flow/.flow_version`, deletes `.flow/.migration-manifest`. `--yes` required to commit. `--force-overwrite-post-migration-changes` overrides the manifest-safety check.
- **`SCHEMA_VERSION` constant changes are owned by T1** (T1 sets it to 3 + adds 3 to `SUPPORTED_SCHEMA_VERSIONS`). T3 verifies T1's bump landed, then handles the on-disk-migration side: existing `.flow/meta.json` files written by 0.x flowctl have `schema_version: 2`; T3's migration step rewrites them to `schema_version: 3`.
- Migration steps in order:
  1. Verify `SCHEMA_VERSION == 3` (T1 invariant). If not, exit 1 with developer-facing error (T1 must land first).
  2. Acquire lock via `os.mkdir(".flow/.migrating")`. Write PID inside. On `FileExistsError`, read PID; if dead, reclaim. Else wait up to 30s.
  3. Detect pre-1.0 layout: `.flow/epics/` exists AND `.flow/.flow_version` does not exist. If neither, exit 0. If `.flow/.flow_version` exists with version > 1.x, defer to R34 (T4).
  4. Backup: `cp -r .flow/ .flow/.backup-pre-1.0/` (excluding `.flow/.backup-pre-1.0/` itself, `.flow/.migration-manifest`, `.flow/.banner-acknowledged`, `.flow/.migrating`). Write `.flow/.backup-pre-1.0/.complete` ONLY after copy finishes. **Backup is immutable after `.complete`.**
  5. Validate `.flow/.migration-manifest` path is clean before writing it: if it exists from a prior interrupted migrate, DELETE it. Clean re-init.
  6. Initialize migration manifest at `.flow/.migration-manifest` (NOT inside backup) -- top-level JSON list, start empty.
  7. Move JSON files: for each `.flow/epics/*.json`, `os.replace()` to `.flow/specs/`, append manifest entry.
  8. Rewrite `.flow/meta.json`: rename `next_epic` -> `next_spec` AND set `schema_version: 3`. Append manifest entry.
  9. Rewrite task JSON: for each `.flow/tasks/*.json`, set `"spec":` and pop `"epic":`. Atomic write.
  10. Remove empty `.flow/epics/` directory.
  11. Write `.flow/.flow_version = "1.0.0"` LAST.
  12. Release lock (`os.rmdir(".flow/.migrating")`).
- Crash recovery decision tree:
  - No sentinel, no `.complete` -> backup mid-copy crashed; restart from step 4.
  - No sentinel, `.complete` present, partial state -> restore by COPYING from backup, retry from step 4.
  - Sentinel present -> migration complete; idempotent skip.
- Rollback (`migrate-rollback`):
  - Verify `.flow/.backup-pre-1.0/.complete` exists; refuse otherwise.
  - Read `.flow/.migration-manifest` (top-level). Build the set of post-migration paths.
  - Scan `.flow/specs/*.json`. If any exists outside the manifest, refuse (post-migration writes detected). Override via `--force-overwrite-post-migration-changes`.
  - Otherwise: delete the manifest's post-migration files; **copy** `.flow/.backup-pre-1.0/epics` -> `.flow/epics`. Restore `.flow/meta.json` (with `schema_version: 2` from backup) and task JSON files by copying. Remove `.flow/.flow_version`. **Delete `.flow/.migration-manifest`** so a fresh migrate-rename runs cleanly. **Leave `.flow/.backup-pre-1.0/` fully intact**. Repeatable.
- Read-only filesystem: explicit `flowctl migrate-rename --yes` against read-only `.flow/` fails with exit code 1 + clear stderr message.
- `--dry-run` walks the same decision tree but only prints the plan.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` -- existing `cmd_migrate_state` pattern; grep `def cmd_migrate_state` (line refs drifted post-T2). <!-- Updated by plan-sync: T2 added ~150 lines; line numbers stale -->
- `plugins/flow-next/scripts/flowctl.py` -- `cmd_memory_migrate`; grep `def cmd_memory_migrate`. <!-- Updated by plan-sync: line numbers stale post-T2 -->
- `plugins/flow-next/scripts/flowctl.py:50` -- `SCHEMA_VERSION = 3` (T1 landed; T3 verifies and reads).
- `plugins/flow-next/scripts/flowctl.py:4142` -- `meta = {"schema_version": SCHEMA_VERSION, "next_spec": 1}` (T1 already writes `next_spec` for fresh inits; T3 migrates existing 0.x meta files that still have `next_epic`). <!-- Updated by plan-sync: line numbers shifted post-T2; grep `meta = {"schema_version"` for the canonical site -->
- `plugins/flow-next/scripts/flowctl.py:3718-3825` -- `get_specs_json_write_dir` + `find_spec_json_path` + `iter_spec_json_files` helpers from T1; T2 added `_emit_rename_deprecation` + `iter_spec_json_files` in this block (read/write resolution rules). <!-- Updated by plan-sync: line range shifted post-T2 helper additions -->

## Key context

- The `.flow/.flow_version` file is plain text version string ("1.0.0").
- The `.flow/.migration-manifest` is JSON, at the top level. Used by rollback. Deleted by rollback for repeatability.
- `os.mkdir` returning `FileExistsError` is the cross-platform "lock held" signal.
- Backup immutability invariant: nothing under `.flow/.backup-pre-1.0/` is mutated after the `.complete` marker.
- Two version markers: `meta.json["schema_version"] == 3` AND `.flow/.flow_version == "1.0.0"`. Migration writes BOTH; rollback reverts BOTH.
- **T1 owns the `SCHEMA_VERSION` constant change**; T3 only verifies + handles on-disk migration. Avoids merge conflict if T1/T3 run partially-parallel.

## Acceptance

- [ ] T3 verifies `SCHEMA_VERSION == 3` from T1 (refuses to run if T1 didn't land); does NOT modify the constant itself.
- [ ] `flowctl migrate-rename --dry-run` on pre-1.0 `.flow/` prints a plan (including the `meta.json` schema_version bump 2 -> 3); exits 0.
- [ ] `flowctl migrate-rename --yes` on pre-1.0 `.flow/` completes the migration: `.flow/specs/*.json` populated, `.flow/epics/` removed, `.flow/.flow_version = "1.0.0"`, `.flow/meta.json["schema_version"] = 3` AND `next_spec` field, `.flow/.backup-pre-1.0/` populated with `.complete` marker, `.flow/.migration-manifest` populated at top level.
- [ ] Backup directory `.flow/.backup-pre-1.0/` does NOT contain `.migration-manifest`.
- [ ] Re-running `flowctl migrate-rename --yes` on a 1.0 `.flow/` is a no-op.
- [ ] `flowctl migrate-rollback --yes` on a clean post-migration state: restores pre-1.0 layout, reverts `.flow/meta.json["schema_version"]` to 2, removes `.flow/.flow_version`, **deletes `.flow/.migration-manifest`**. `.flow/.backup-pre-1.0/` remains intact.
- [ ] Rollback is re-runnable: migrate -> rollback -> migrate -> rollback all succeed.
- [ ] `flowctl migrate-rollback --yes` after a post-migration spec creation FAILS with exit 1 + "post-migration writes detected".
- [ ] `flowctl migrate-rollback --yes --force-overwrite-post-migration-changes` proceeds.
- [ ] Concurrency: two parallel `migrate-rename --yes` invocations -- second waits, succeeds.
- [ ] Crash simulation: SIGKILL mid-migration; restart -- detects partial state, restores from backup (by copy), retries.
- [ ] Read-only `.flow/`: `flowctl migrate-rename --yes` fails with exit code 1 + stderr message.
- [ ] Cross-platform: lockfile mechanism works on macOS, Linux, Windows.

## Done summary
Implemented `flowctl migrate-rename` (pre-1.0 → 1.0 .flow/ layout migration) and `flowctl migrate-rollback` with cross-platform `os.mkdir` lockfile, two-phase backup with `.complete` marker, top-level `.flow/.migration-manifest`, atomic sentinel write at `.flow/.flow_version`, and full crash-recovery decision tree. SHIP from codex:gpt-5.5:high after 6 review cycles addressing 10 compound findings (cross-platform PID liveness, content-drift detection, manifest SHA256 anchors, mid-migration contamination wipe, atomic sentinel + payload validation).
## Evidence
- Commits: 841e02de81d5aec464c4032edd5231be905cdbdb, 89a1105b7084913eea367197a1b6a299398efb30, be8d7003e7981a4eeb91e0f78c98a50f2e15c47e, 55359f892eaba6641d10fa32be5586cae92fc215, f68145f600a0b0d4ae0291dfa0ab436f647ad1e5, 3153b1424a413246e1d6927f6e61d4bdf7642074, 57cfd7548a9c2cc7dd59f1de5857ccceef344f90, b2f5dd3d63d5f9436883629012c275608f84f4e0
- Tests: bash /tmp/migrate_rename_test.sh (13/13), bash /tmp/migrate_rename_review_fixes.sh (5/5), bash /tmp/migrate_rename_review2.sh (5/5), bash /tmp/migrate_rename_review3.sh (3/3), bash /tmp/migrate_rename_review4.sh (2/2), bash /tmp/migrate_rename_review5.sh (3/3), bash /tmp/migrate_rename_review6.sh (4/4), bash /tmp/migrate_rename_concurrency.sh (2/2), bash plugins/flow-next/scripts/ci_test.sh (57/57)
- PRs: