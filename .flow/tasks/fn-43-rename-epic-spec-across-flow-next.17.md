---
satisfies: [R20, R26, R27]
---

## Description

Python unit tests for the new flowctl.py logic that bash smoke tests can't reach cleanly: migration step ordering + crash recovery, cross-platform `os.mkdir` lockfile contention with stale-PID reclaim, `find_spec_json_path` fallback, write-location selector, JSON read-compat helpers across all four field categories (`epic`/`spec`, `epic_id`/`spec_id`, `next_epic`/`next_spec`, `epics`/`specs`), banner suppression matrix, and forward-compat downgrade parsing. T14 (bash smoke) verifies end-to-end behavior; T14b verifies the unit-level invariants with mocked filesystem + signals + env state. <!-- Updated by plan-sync: T1 shipped helper as find_spec_json_path not _resolve_spec_json_path -->

Helpers landed in T2 that downstream tests should target: `_emit_rename_deprecation` (one-shot stderr per legacy form), `canonicalize_task_for_write` (strips `epic`/`epic_id` from persisted task JSON before write), `normalize_task` (in-place legacy 0.x epic->spec migration on read), `find_spec_json_path` (read-side filesystem fallback specs/<id>.json -> epics/<id>.json).

**Size:** M
**Files:**
- NEW: `plugins/flow-next/tests/test_migrate_rename.py`
- NEW: `plugins/flow-next/tests/test_lockfile.py`
- NEW: `plugins/flow-next/tests/test_read_compat.py`
- NEW: `plugins/flow-next/tests/test_write_location.py`
- NEW: `plugins/flow-next/tests/test_banner.py`
- Possibly: extension to existing `plugins/flow-next/tests/conftest.py` for fixtures

## Approach

- Use the existing pytest harness in `plugins/flow-next/tests/` (already set up for memory / prospect / review-receipt schema tests). Match the conftest fixture style.
- **`test_migrate_rename.py`** — covers T3 invariants:
  - Pre-1.0 detection (epics dir present, no sentinel) -> dry-run plan + yes commit.
  - Idempotent re-run on 1.0 state.
  - Schema_version migration (meta.json `schema_version: 2` -> `3`).
  - `next_epic` -> `next_spec` rename in meta.json.
  - Task JSON `"epic":` -> `"spec":` field rename + legacy strip.
  - Backup `.complete` two-phase marker.
  - Migration manifest at `.flow/.migration-manifest` (top-level, NOT inside backup).
  - Crash recovery — T3's 4-case decision tree, one test per case: <!-- Updated by plan-sync: T3 done summary enumerated 4 cases; original spec said "mock SIGKILL" generically -->
    - No-backup case: simulate crash before backup starts; restart begins from step 4 cleanly.
    - Partial-backup case: simulate crash mid-copy (no `.complete` marker); restart re-runs backup.
    - Complete-no-manifest case: simulate crash after `.complete` but before manifest init; restart wipes any pre-existing manifest and reinitializes.
    - Mid-migration case: simulate crash after manifest populated but before sentinel; restart restores from backup by COPY (not move), retries.
  - Read-only filesystem -> exit code 1 + stderr message; idempotency check runs BEFORE read-only refusal (already-migrated 1.0 repo on read-only fs is a no-op, NOT exit 1). <!-- Updated by plan-sync: T3 ships idempotency-before-readonly ordering -->
  - Atomic sentinel write — `.flow/.flow_version` written via tmpfile + `os.replace`; partial-write byte states never persist. <!-- Updated by plan-sync: T3 ships atomic sentinel write -->
  - SHA256 task-drift detection — manifest records SHA256 per migrated task; rollback refuses on drift unless `--force-overwrite-post-migration-changes`. <!-- Updated by plan-sync: T3 ships content-drift detection beyond mere path enumeration -->
  - Mid-migration contamination — pre-existing `.flow/.migration-manifest` from interrupted prior run is wiped before re-init on retry. <!-- Updated by plan-sync: T3 done summary called this out -->
- **`test_lockfile.py`** — covers R8 + R32:
  - `os.mkdir(".flow/.migrating")` atomic-create succeeds.
  - Second invocation `FileExistsError`; PID reclaim if dead.
  - PID-liveness branching — T3 ships POSIX `os.kill(pid, 0)` AND Windows `OpenProcess` ctypes paths. Test both: <!-- Updated by plan-sync: T3 done summary called out cross-platform PID liveness as separate POSIX and Windows ctypes branches -->
    - POSIX path: mock `os.kill` raising `ProcessLookupError` for dead pid (reclaim succeeds); raising `PermissionError` for live foreign pid (reclaim refuses, waits).
    - Windows path: mock `ctypes.windll.kernel32.OpenProcess` returning NULL for dead pid (reclaim succeeds); returning a handle for live pid (reclaim refuses).
  - PID-grace window — lockdir present without pid file longer than `MIGRATE_LOCK_PID_GRACE_SECS` triggers reclaim; within grace window, waits.
  - 30-second wait loop with poll; eventual error.
  - Cross-platform: parametrize fixtures for POSIX and Windows code paths (skip Windows-specific paths on POSIX runner; vice-versa).
  - `migrate-rollback` verifying `.complete` exists; refuses otherwise.
  - Manifest-safety: post-migration write detection refuses rollback unless `--force-overwrite-post-migration-changes`.
- **`test_read_compat.py`** — covers R10 + R31 read-side:
  - `task.get("spec") or task.get("epic")` reads both forms.
  - `meta.get("next_spec") or meta.get("next_epic")` reads both.
  - JSON output dual-emit across all four field categories: `spec`/`epic`, `spec_id`/`epic_id`, `specs`/`epics`, `next_spec`/`next_epic`.
  - `flowctl next --json` reason-code dual-emit (`reason: blocked_by_spec_deps` AND `legacy_reason: blocked_by_epic_deps`).
  - Persisted task JSON: assert canonical-only on write (no `"epic":` field).
- **`test_write_location.py`** — covers R33 + write-location helper:
  - Fresh `.flow/` (no sentinel, no epics dir) -> writes to `.flow/specs/`.
  - 0.x `.flow/` (no sentinel, has epics dir) -> writes to `.flow/epics/`.
  - 1.0 `.flow/` (sentinel present) -> writes to `.flow/specs/`.
  - Read-path fallback: stage `.flow/epics/fn-X.json` only -> read finds it; stage `.flow/specs/fn-X.json` only -> read finds it.
- **`test_banner.py`** — covers R7 + R9 + R24 + R34 + R35: <!-- Updated by plan-sync: T4 shipped richer banner surface than original spec captured -->
  - Pre-1.0 -> banner emits to stderr; subcommand exit code preserved.
  - `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`, `FLOW_NO_AUTO_MIGRATE=1`, sentinel present, `.banner-acknowledged` < 7d -> banner suppressed.
  - Future-version sentinel (`.flow/.flow_version` major >= 2, e.g. `2.0.0`) -> one-line warning to stderr, subcommand exit code preserved (NOT forced); v1.x sentinel is silent (already-migrated). <!-- Updated by plan-sync: T4 keys future-version on major >= 2; v1.x silent because _migrate_sentinel_state validates 1.x as already migrated -->
  - `.banner-acknowledged` written ONLY by `migrate-rename --dry-run` (or setup defer) — bare `flowctl <verb>` invocations DO NOT write it.
  - Process-level dedup — module-level `_MIGRATION_BANNER_EMITTED` flag flips to `True` on first emission within a single `flowctl` invocation; second `_check_migration_banner` call in same process is a no-op. <!-- Updated by plan-sync: T4 ships process-level dedup flag not previously specified -->
  - Defensive ack-file parsing — empty / garbage / future-dated `.banner-acknowledged` timestamp falls through to banner emission (treated as un-acknowledged). <!-- Updated by plan-sync: T4 ships defensive timestamp parsing -->
  - Re-nudge cadence — 8-day-old ack timestamp re-fires the banner once on next invocation; the ack timestamp is NOT auto-refreshed (user must run `migrate-rename --dry-run` again or migrate). <!-- Updated by plan-sync: T4 done summary made the no-auto-refresh contract explicit -->
  - stderr-only — banner output never lands on stdout; `flowctl <verb> --json` stdout parses cleanly with `json.load` even with banner active. <!-- Updated by plan-sync: T4 acceptance and done summary explicit on this -->
  - Helper `_banner_ack_within_renudge_window(flow_dir)` covered as a separate unit (returns False on missing/empty/garbage/future-dated/expired; True on within-window). <!-- Updated by plan-sync: T4 ships as a separately-testable helper -->
  - No `.flow/` at all — banner silent; `flowctl init` still works. <!-- Updated by plan-sync: T4 manual test confirmed -->
  - Banner exception path — `_check_migration_banner` swallows internal exceptions silently; main() wraps the call in a try/except so a hostile `get_flow_dir` failure cannot block subcommand dispatch. <!-- Updated by plan-sync: T4 main() shipped a defensive try/except around the banner call -->

  Implementation surface to target in tests (helpers + constants from T4, all module-level in flowctl.py): `_check_migration_banner(flow_dir)`, `_banner_ack_within_renudge_window(flow_dir)`, `_MIGRATION_BANNER_EMITTED` module flag, `BANNER_ACK_FILE = ".banner-acknowledged"`, `BANNER_RENUDGE_DAYS = 7`. Tests should reset `_MIGRATION_BANNER_EMITTED` between cases (monkeypatch the module attribute) since the dedup flag persists across calls within a process.

## Investigation targets

**Required:**
- `plugins/flow-next/tests/conftest.py` -- existing fixture style.
- `plugins/flow-next/tests/test_*.py` -- conventions (any one of the existing tests).
- `pytest.ini` or equivalent (verify location).

## Key context

- The unit tests target *invariants*, not end-to-end flows. End-to-end is T14's job.
- Mock filesystem state via `tmp_path` pytest fixture; mock env via `monkeypatch`; mock signals via `pytest-subprocess` or manual `os.kill` patching.
- Cross-platform `os.mkdir` lockfile means tests run on macOS/Linux/Windows CI matrix. Use `pytest.mark.skipif` for OS-specific paths.
- The Python unit tests are fast (sub-second per file, no shell process spawning); add to the existing `pytest` invocation in `ci_test.sh` or wherever the Python harness runs.

## Acceptance

- [ ] `pytest plugins/flow-next/tests/test_migrate_rename.py` passes; covers all 13 scenarios listed above (9 originally; expanded to 13 per T3's actual surface — 4-case crash-recovery decision tree replaces single "SIGKILL" test, atomic sentinel write, SHA256 drift detection, mid-migration contamination wipe, idempotency-before-readonly ordering). <!-- Updated by plan-sync: scenario count expanded to match T3 implementation -->
- [ ] `pytest plugins/flow-next/tests/test_lockfile.py` passes; lockfile contention + stale-PID reclaim verified across BOTH POSIX `os.kill` and Windows `OpenProcess` ctypes branches; PID-grace window honored. <!-- Updated by plan-sync: T3 ships separate POSIX and Windows PID-liveness paths -->
- [ ] `pytest plugins/flow-next/tests/test_read_compat.py` passes; dual-emit + read-fallback for all 4 field categories.
- [ ] `pytest plugins/flow-next/tests/test_write_location.py` passes; three layouts (fresh / 0.x-unmigrated / 1.0-migrated) verified.
- [ ] `pytest plugins/flow-next/tests/test_banner.py` passes; covers all 9 scenarios listed above (4 originally + 5 added per T4's actual surface — process-level dedup, defensive ack parsing, re-nudge no-auto-refresh, stderr-only invariant, ack-window helper as separate unit, no-`.flow/`-silent path, banner exception swallowing). <!-- Updated by plan-sync: scenario count expanded from 4 -> 9 to match T4 implementation -->
- [ ] Test fixtures reset `_MIGRATION_BANNER_EMITTED` between cases via monkeypatch; verify the dedup flag actually flips on first emit and prevents double emission within one process. <!-- Updated by plan-sync: T4 module-level flag persists across calls -->
- [ ] `--json` stdout invariant — at least one `test_banner.py` case asserts `flowctl <verb> --json` stdout parses cleanly with `json.load` while banner is active on stderr. <!-- Updated by plan-sync: T4 stderr-only acceptance criterion -->
- [ ] Future-version path keyed on major >= 2 (semver match `^\d+\.\d+\.\d+$` then `int(major) >= 2`); test 1.5.2 and 1.99.99 are silent (validated as 1.x via `_migrate_sentinel_state`); 2.0.0 + 3.1.0 emit warning. <!-- Updated by plan-sync: T4 forward-compat path uses major >= 2, not major > 1 -->
- [ ] `_banner_ack_within_renudge_window` direct unit coverage — missing file, empty body, garbage body, future-dated timestamp, exactly 7d boundary, 8d expired all match expected return values. <!-- Updated by plan-sync: T4 ships as separate helper -->
- [ ] CI integration: the Python unit tests run alongside existing pytest invocations on Linux + macOS + Windows.

## Done summary
Added 5 Python unittest suites totaling 104 tests covering fn-43.17 invariants: pre-1.0 → 1.0 migration (24 cases incl. 4-case crash recovery, SHA256 drift, atomic sentinel write), cross-platform `os.mkdir` lockfile + POSIX `os.kill` and Windows `OpenProcess` ctypes PID liveness (12 cases), JSON read-compat dual-emit driven through real `cmd_*` invocations (30 cases — `spec`/`epic`, `specs`/`epics`, `spec_id`/`epic_id`, `next_spec`/`next_epic` all covered via `json_output` capture + one subprocess round-trip), three-layout write-location selector + read fallback (12 cases), and banner suppression matrix incl. dedup flag, ack-window helper, forward-compat warning on major≥2, stderr-only invariant, exception swallowing (26 cases). Wired into `.github/workflows/test-flow-next.yml` to run on ubuntu/macos/windows.
## Evidence
- Commits: 033616dec7350a45ee87197f8605f7bc5fd1fe72, 7059d3cb89c2b066e8b6df04e6e35e164e3d3d57, 8e90f2891d0f806f0c90fa4acde97acf5739b529
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_migrate_rename.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_lockfile.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_read_compat.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_write_location.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_banner.py
- PRs: