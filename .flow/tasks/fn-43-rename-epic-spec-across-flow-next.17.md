---
satisfies: [R20, R26, R27]
---

## Description

Python unit tests for the new flowctl.py logic that bash smoke tests can't reach cleanly: migration step ordering + crash recovery, cross-platform `os.mkdir` lockfile contention with stale-PID reclaim, `_resolve_spec_json_path` fallback, write-location selector, JSON read-compat helpers across all four field categories (`epic`/`spec`, `epic_id`/`spec_id`, `next_epic`/`next_spec`, `epics`/`specs`), banner suppression matrix, and forward-compat downgrade parsing. T14 (bash smoke) verifies end-to-end behavior; T14b verifies the unit-level invariants with mocked filesystem + signals + env state.

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
  - Crash recovery (mock SIGKILL between steps; restart resumes correctly).
  - Read-only filesystem -> exit code 1 + stderr message.
- **`test_lockfile.py`** — covers R8 + R32:
  - `os.mkdir(".flow/.migrating")` atomic-create succeeds.
  - Second invocation `FileExistsError`; PID reclaim if dead (mock `os.kill` raising `ProcessLookupError`).
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
- **`test_banner.py`** — covers R7 + R9 + R24 + R34 + R35:
  - Pre-1.0 -> banner emits to stderr; subcommand exit code preserved.
  - `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`, `FLOW_NO_AUTO_MIGRATE=1`, sentinel present, `.banner-acknowledged` < 7d -> banner suppressed.
  - Future-version (`.flow_version > 1.x`) -> warning printed, exit code preserved (NOT forced).
  - `.banner-acknowledged` written ONLY by `migrate-rename --dry-run` (or setup defer) — bare `flowctl <verb>` invocations DO NOT write it.

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

- [ ] `pytest plugins/flow-next/tests/test_migrate_rename.py` passes; covers all 9 scenarios listed above.
- [ ] `pytest plugins/flow-next/tests/test_lockfile.py` passes; lockfile contention + stale-PID reclaim verified.
- [ ] `pytest plugins/flow-next/tests/test_read_compat.py` passes; dual-emit + read-fallback for all 4 field categories.
- [ ] `pytest plugins/flow-next/tests/test_write_location.py` passes; three layouts (fresh / 0.x-unmigrated / 1.0-migrated) verified.
- [ ] `pytest plugins/flow-next/tests/test_banner.py` passes; suppression matrix + ack-write semantics verified.
- [ ] CI integration: the Python unit tests run alongside existing pytest invocations on Linux + macOS + Windows.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
