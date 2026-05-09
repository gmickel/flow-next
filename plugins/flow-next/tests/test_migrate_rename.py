"""Unit tests for the pre-1.0 → 1.0 migration (fn-43.17 / R-IDs covered by T3+T4).

The migration is a transactional protocol with explicit recovery semantics —
not just "move some files." These tests exercise the protocol invariants that
end-to-end smoke tests can't reach cleanly:

  * Atomic-sentinel write — `_migrate_sentinel_state` rejects empty / partial
    payloads so a crashed `write_text` never tricks the no-op branch.
  * SHA256 drift detection — manifest records `post_sha256` per rewritten task
    so user edits between migrate and rollback are flagged.
  * Mid-migration crash recovery — `_migrate_recover_from_complete_backup`
    wipes migration-created artefacts BEFORE restoring from backup so leftovers
    don't contaminate the pre-migration snapshot.
  * Crash-recovery decision tree — four cases (no-backup, partial-backup,
    complete-no-manifest, complete-with-manifest) each take the right branch.
  * Idempotency-before-readonly — already-migrated repo on read-only fs is a
    no-op (NOT exit 1) regardless of `--dry-run` / `--yes` mode.
  * Plan / apply round-trip — `_migrate_collect_plan` + `_migrate_apply_plan`
    produce the sentinel-last sequence with stable manifest entries.

Run:
    python3 -m unittest plugins.flow-next.tests.test_migrate_rename -v
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_migrate_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# --- Fixture helpers --------------------------------------------------


@contextlib.contextmanager
def _chdir(target: Path):
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prev)


def _make_pre_1_0_repo(repo_root: Path) -> Path:
    """Build a representative 0.x repo under `repo_root`. Returns `.flow/` path.

    Includes:
      - meta.json with `schema_version: 2` + `next_epic: 3`
      - epics/fn-1.json + fn-2.json with valid spec data
      - tasks/fn-1.1.json with `epic` field (legacy)
      - tasks/fn-2.1.json with `epic_id` field (legacy)
      - specs/fn-1.md (markdown survives across both layouts)
      - memory/ (empty dir)
    """
    flow_dir = repo_root / ".flow"
    flow_dir.mkdir(parents=True)

    epics_dir = flow_dir / flowctl.EPICS_DIR
    epics_dir.mkdir()
    specs_md_dir = flow_dir / flowctl.SPECS_DIR
    specs_md_dir.mkdir()
    tasks_dir = flow_dir / flowctl.TASKS_DIR
    tasks_dir.mkdir()
    (flow_dir / flowctl.MEMORY_DIR).mkdir()

    # meta.json — 0.x shape (schema 2, next_epic).
    flowctl.atomic_write_json(
        flow_dir / flowctl.META_FILE,
        {"schema_version": 2, "next_epic": 3},
    )

    # epics/fn-1.json
    flowctl.atomic_write_json(
        epics_dir / "fn-1.json",
        {
            "id": "fn-1",
            "title": "Test epic",
            "status": "open",
            "next_task": 1,
            "spec_path": ".flow/specs/fn-1.md",
            "depends_on_epics": [],
            "created_at": "2026-05-01T00:00:00Z",
            "updated_at": "2026-05-01T00:00:00Z",
        },
    )
    flowctl.atomic_write_json(
        epics_dir / "fn-2.json",
        {
            "id": "fn-2",
            "title": "Another epic",
            "status": "open",
            "next_task": 1,
            "spec_path": ".flow/specs/fn-2.md",
            "depends_on_epics": [],
            "created_at": "2026-05-02T00:00:00Z",
            "updated_at": "2026-05-02T00:00:00Z",
        },
    )

    # specs/fn-1.md (markdown lived at .flow/specs/ even in 0.x).
    (specs_md_dir / "fn-1.md").write_text("# fn-1\n\nspec body\n", encoding="utf-8")
    (specs_md_dir / "fn-2.md").write_text("# fn-2\n\nspec body\n", encoding="utf-8")

    # Task with legacy `epic` field.
    flowctl.atomic_write_json(
        tasks_dir / "fn-1.1.json",
        {
            "id": "fn-1.1",
            "epic": "fn-1",
            "title": "Task A",
            "status": "todo",
            "depends_on": [],
            "created_at": "2026-05-01T00:00:00Z",
        },
    )
    (tasks_dir / "fn-1.1.md").write_text("## Description\n\nx\n", encoding="utf-8")

    # Task with legacy `epic_id` field.
    flowctl.atomic_write_json(
        tasks_dir / "fn-2.1.json",
        {
            "id": "fn-2.1",
            "epic_id": "fn-2",
            "title": "Task B",
            "status": "todo",
            "depends_on": [],
            "created_at": "2026-05-02T00:00:00Z",
        },
    )

    return flow_dir


# --- Sentinel-state helper -----------------------------------------------


class TestSentinelState(unittest.TestCase):
    """Atomic-sentinel write — empty/partial/garbage payloads invalid."""

    def test_missing_sentinel_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            valid, payload = flowctl._migrate_sentinel_state(flow_dir)
            self.assertFalse(valid)
            self.assertIsNone(payload)

    def test_canonical_1_0_0_payload_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
                flowctl.FLOW_VERSION_PAYLOAD + "\n", encoding="utf-8"
            )
            valid, payload = flowctl._migrate_sentinel_state(flow_dir)
            self.assertTrue(valid)
            self.assertEqual(payload, "1.0.0")

    def test_empty_payload_invalid(self) -> None:
        """Crashed `write_text` mid-flush — empty file → invalid (recovery path)."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text("", encoding="utf-8")
            valid, _ = flowctl._migrate_sentinel_state(flow_dir)
            self.assertFalse(valid)

    def test_garbage_payload_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
                "garbage", encoding="utf-8"
            )
            valid, payload = flowctl._migrate_sentinel_state(flow_dir)
            self.assertFalse(valid)
            self.assertEqual(payload, "garbage")

    def test_future_semver_payload_valid(self) -> None:
        """Forward-compat: 2.0.0 / 1.5.2 → valid (treat as already-migrated)."""
        for payload in ("2.0.0", "1.5.2", "10.0.0"):
            with tempfile.TemporaryDirectory() as tmp:
                flow_dir = Path(tmp) / ".flow"
                flow_dir.mkdir()
                (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
                    payload + "\n", encoding="utf-8"
                )
                valid, returned = flowctl._migrate_sentinel_state(flow_dir)
                self.assertTrue(valid, f"payload={payload}")
                self.assertEqual(returned, payload)


# --- File-SHA256 helper -------------------------------------------------


class TestFileSha256(unittest.TestCase):
    """Stable SHA256 for content drift detection in the manifest."""

    def test_known_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "f.txt"
            p.write_text("hello\n", encoding="utf-8")
            # `echo -n hello | sha256sum` — but with the LF
            import hashlib

            expected = hashlib.sha256(b"hello\n").hexdigest()
            self.assertEqual(flowctl._migrate_file_sha256(p), expected)

    def test_missing_path_returns_empty_string(self) -> None:
        self.assertEqual(
            flowctl._migrate_file_sha256(Path("/nonexistent/path/here.txt")), ""
        )


# --- Plan + apply round-trip ----------------------------------------------


class TestMigratePlanAndApply(unittest.TestCase):
    """Plan describes the work; apply produces the manifest entries."""

    def test_collect_plan_finds_all_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            plan = flowctl._migrate_collect_plan(flow_dir)
            # 2 epic JSONs to move.
            self.assertEqual(len(plan["epic_jsons"]), 2)
            self.assertTrue(plan["meta_rewrite"])
            # Both tasks have legacy keys → both rewritten.
            self.assertEqual(len(plan["task_rewrites"]), 2)
            self.assertTrue(plan["remove_epics_dir"])

    def test_collect_plan_idempotent_on_1_0_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir()
            (flow_dir / flowctl.TASKS_DIR).mkdir()
            flowctl.atomic_write_json(
                flow_dir / flowctl.META_FILE,
                {"schema_version": flowctl.SCHEMA_VERSION, "next_spec": 1},
            )
            plan = flowctl._migrate_collect_plan(flow_dir)
            # Nothing to do.
            self.assertEqual(plan["epic_jsons"], [])
            self.assertFalse(plan["meta_rewrite"])
            self.assertEqual(plan["task_rewrites"], [])
            self.assertFalse(plan["remove_epics_dir"])

    def test_apply_plan_produces_manifest_entries_and_rewrites_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            plan = flowctl._migrate_collect_plan(flow_dir)
            entries, meta_summary = flowctl._migrate_apply_plan(flow_dir, plan)

            # Manifest entries cover all four expected actions.
            actions = sorted(e["action"] for e in entries)
            self.assertIn("move_spec_json", actions)
            self.assertIn("rewrite_meta", actions)
            self.assertIn("rewrite_task", actions)
            self.assertIn("rmdir_epics", actions)

            # Every rewrite_task entry has a SHA256 hash recorded.
            task_entries = [e for e in entries if e["action"] == "rewrite_task"]
            self.assertEqual(len(task_entries), 2)
            for entry in task_entries:
                self.assertIn("post_sha256", entry)
                self.assertEqual(len(entry["post_sha256"]), 64)
                self.assertTrue(all(c in "0123456789abcdef" for c in entry["post_sha256"]))

            # Tasks now have canonical `spec` / `spec_id` (no legacy fields).
            t1 = json.loads((flow_dir / flowctl.TASKS_DIR / "fn-1.1.json").read_text())
            self.assertEqual(t1.get("spec"), "fn-1")
            self.assertNotIn("epic", t1)
            t2 = json.loads((flow_dir / flowctl.TASKS_DIR / "fn-2.1.json").read_text())
            self.assertEqual(t2.get("spec_id"), "fn-2")
            self.assertNotIn("epic_id", t2)

            # Meta migrated: schema_version 3, next_spec preserved from next_epic.
            meta = json.loads((flow_dir / flowctl.META_FILE).read_text())
            self.assertEqual(meta["schema_version"], flowctl.SCHEMA_VERSION)
            self.assertEqual(meta.get("next_spec"), 3)
            self.assertNotIn("next_epic", meta)
            self.assertEqual(meta_summary["next"]["next_spec"], 3)

            # Empty epics/ dir removed.
            self.assertFalse((flow_dir / flowctl.EPICS_DIR).exists())

            # Spec JSONs landed at canonical specs/.
            self.assertTrue((flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json").exists())
            self.assertTrue((flow_dir / flowctl.SPECS_JSON_DIR / "fn-2.json").exists())


# --- Crash-recovery decision tree (4 cases) -----------------------------


class TestCrashRecoveryDecisionTree(unittest.TestCase):
    """`_migrate_handle_crash_recovery` walks the 4-case decision tree."""

    def test_case1_no_backup_no_op(self) -> None:
        """No backup dir at all → recovery is a no-op (fall through to fresh migrate)."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            self.assertFalse(backup_dir.exists())
            actions = flowctl._migrate_handle_crash_recovery(
                flow_dir, backup_dir, use_json=False, dry_run=False
            )
            self.assertEqual(actions, [])

    def test_case2_partial_backup_wiped(self) -> None:
        """Backup dir exists but no `.complete` → mid-copy crash → wipe partial."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            backup_dir.mkdir()
            # Stuff some partial content (no .complete marker).
            (backup_dir / "stub").write_text("partial", encoding="utf-8")

            actions = flowctl._migrate_handle_crash_recovery(
                flow_dir, backup_dir, use_json=False, dry_run=False
            )
            self.assertEqual(len(actions), 1)
            self.assertIn("discarded partial backup", actions[0])
            self.assertFalse(backup_dir.exists())

    def test_case3_complete_no_manifest_clean_rollback_aftermath(self) -> None:
        """Complete backup + no manifest → user ran rollback. Preserve backup, fresh migrate."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            backup_dir.mkdir()
            (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).write_text(
                flowctl.now_iso(), encoding="utf-8"
            )
            # Manifest absent → clean-rollback aftermath path.
            self.assertFalse((flow_dir / flowctl.MIGRATE_MANIFEST_FILE).exists())

            actions = flowctl._migrate_handle_crash_recovery(
                flow_dir, backup_dir, use_json=False, dry_run=False
            )
            self.assertEqual(len(actions), 1)
            self.assertIn("clean rollback aftermath", actions[0])
            # Backup is preserved (NOT discarded — repeatable rollback).
            self.assertTrue(backup_dir.exists())
            self.assertTrue(
                (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).exists()
            )

    def test_case4_complete_with_manifest_mid_migration_crash_restore(self) -> None:
        """Complete backup + manifest → mid-migration crash. Restore + discard backup."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            backup_dir.mkdir()
            (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).write_text(
                flowctl.now_iso(), encoding="utf-8"
            )
            # Stage a backup with the original epics/ content.
            (backup_dir / flowctl.EPICS_DIR).mkdir()
            (backup_dir / flowctl.EPICS_DIR / "fn-1.json").write_text(
                '{"id":"fn-1"}', encoding="utf-8"
            )
            # Manifest present → mid-migration-crash path.
            flowctl.atomic_write_json(
                flow_dir / flowctl.MIGRATE_MANIFEST_FILE,
                {"version": 1, "entries": []},
            )

            # Simulate mid-migration state — partially-applied move (specs/ dir
            # has been created with a moved file).
            (flow_dir / flowctl.SPECS_JSON_DIR / "fn-NEW.json").write_text(
                '{"id":"fn-NEW"}', encoding="utf-8"
            )

            actions = flowctl._migrate_handle_crash_recovery(
                flow_dir, backup_dir, use_json=False, dry_run=False
            )
            self.assertEqual(len(actions), 1)
            self.assertIn("restored", actions[0])
            self.assertIn("discarded", actions[0])
            # Backup directory was discarded.
            self.assertFalse(backup_dir.exists())
            # Mid-migration leftover wiped — `.flow/specs/fn-NEW.json` should
            # NOT survive (the wipe-then-restore sequence killed it).
            self.assertFalse(
                (flow_dir / flowctl.SPECS_JSON_DIR / "fn-NEW.json").exists()
            )
            # Backup content was restored — fn-1.json now in epics/.
            self.assertTrue((flow_dir / flowctl.EPICS_DIR / "fn-1.json").exists())

    def test_case4_dry_run_describes_without_mutating(self) -> None:
        """Dry-run path describes case-4 recovery without touching state."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            backup_dir.mkdir()
            (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).write_text(
                flowctl.now_iso(), encoding="utf-8"
            )
            flowctl.atomic_write_json(
                flow_dir / flowctl.MIGRATE_MANIFEST_FILE,
                {"version": 1, "entries": []},
            )

            actions = flowctl._migrate_handle_crash_recovery(
                flow_dir, backup_dir, use_json=False, dry_run=True
            )
            self.assertEqual(len(actions), 1)
            self.assertIn("would restore", actions[0])
            # Backup left intact.
            self.assertTrue(backup_dir.exists())


# --- Mid-migration contamination wipe -----------------------------------


class TestRecoverFromBackupContaminationWipe(unittest.TestCase):
    """Mid-migration crash recovery wipes migration-created leftovers FIRST."""

    def test_specs_fn_new_json_wiped_before_restore(self) -> None:
        """Migration-created `.flow/specs/fn-NEW.json` MUST go away — without
        the wipe, it would survive the "restore from pre-migration backup"
        and contaminate the next plan-collect."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()

            # Pre-migration backup: only had epics/.
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            (backup_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            (backup_dir / flowctl.EPICS_DIR / "fn-1.json").write_text(
                '{"id":"fn-1"}', encoding="utf-8"
            )
            (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).write_text(
                "ok", encoding="utf-8"
            )

            # Simulate mid-migration state: specs/ has been created with a
            # moved file. The "restore from backup" must NOT preserve specs/.
            (flow_dir / flowctl.SPECS_JSON_DIR).mkdir()
            (flow_dir / flowctl.SPECS_JSON_DIR / "fn-NEW.json").write_text(
                '{"id":"fn-NEW"}', encoding="utf-8"
            )
            # Also: a stale manifest file (gets wiped + caller re-inits).
            (flow_dir / flowctl.MIGRATE_MANIFEST_FILE).write_text(
                "{}", encoding="utf-8"
            )

            flowctl._migrate_recover_from_complete_backup(flow_dir, backup_dir)

            # Migration-created artefact wiped.
            self.assertFalse(
                (flow_dir / flowctl.SPECS_JSON_DIR / "fn-NEW.json").exists()
            )
            # specs/ dir itself wiped (it didn't exist in the backup).
            self.assertFalse((flow_dir / flowctl.SPECS_JSON_DIR).exists())
            # Manifest wiped (caller re-inits).
            self.assertFalse((flow_dir / flowctl.MIGRATE_MANIFEST_FILE).exists())
            # Backup content restored.
            self.assertTrue((flow_dir / flowctl.EPICS_DIR / "fn-1.json").exists())

    def test_backup_itself_preserved_through_recovery(self) -> None:
        """Phase-1 wipe MUST NOT delete the backup we're about to restore from."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            (backup_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            (backup_dir / flowctl.EPICS_DIR / "fn-1.json").write_text(
                '{"id":"fn-1"}', encoding="utf-8"
            )
            (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).write_text(
                "ok", encoding="utf-8"
            )

            flowctl._migrate_recover_from_complete_backup(flow_dir, backup_dir)
            self.assertTrue(backup_dir.exists())
            self.assertTrue(
                (backup_dir / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).exists()
            )


# --- SHA256 drift detection on rollback ---------------------------------


class TestRollbackDriftDetection(unittest.TestCase):
    """`_rollback_post_migration_writes` flags content drift via SHA256."""

    def test_rewritten_task_drift_is_flagged(self) -> None:
        """User edits `tasks/fn-1.1.json` post-migration → drift detected."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            # Apply the migration to populate the manifest with hashes.
            plan = flowctl._migrate_collect_plan(flow_dir)
            entries, meta_summary = flowctl._migrate_apply_plan(flow_dir, plan)

            # Record manifest as cmd_migrate_rename does.
            manifest = {
                "version": 1,
                "schema_version_to": flowctl.SCHEMA_VERSION,
                "entries": entries,
                "meta_summary": meta_summary,
            }

            # Stage backup directory (full snapshot) so post-migration-writes
            # detection can compare against it. We did NOT actually run
            # cmd_migrate_rename here, so we have to materialize the backup
            # by hand to mimic what step 4 would have written.
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            (backup_dir / flowctl.EPICS_DIR).mkdir(parents=True)
            # We just deleted the source epics/ in apply_plan, so back-fill
            # the backup with placeholder content matching the rewritten files.
            # The "expected" path comparison uses the post-migration content
            # via SHA, NOT the backup, so we don't need full faithful backup.
            (backup_dir / flowctl.TASKS_DIR).mkdir(parents=True)
            shutil.copy2(
                flow_dir / flowctl.TASKS_DIR / "fn-1.1.json",
                backup_dir / flowctl.TASKS_DIR / "fn-1.1.json",
            )
            shutil.copy2(
                flow_dir / flowctl.TASKS_DIR / "fn-2.1.json",
                backup_dir / flowctl.TASKS_DIR / "fn-2.1.json",
            )
            shutil.copy2(
                flow_dir / flowctl.TASKS_DIR / "fn-1.1.md",
                backup_dir / flowctl.TASKS_DIR / "fn-1.1.md",
            )

            # Drift the rewritten task content (user edit post-migration).
            t1 = json.loads(
                (flow_dir / flowctl.TASKS_DIR / "fn-1.1.json").read_text()
            )
            t1["title"] = "DRIFTED"
            flowctl.atomic_write_json(
                flow_dir / flowctl.TASKS_DIR / "fn-1.1.json", t1
            )

            unexpected = flowctl._rollback_post_migration_writes(flow_dir, manifest)
            unexpected_paths = sorted(
                p for p in unexpected if p.endswith("fn-1.1.json")
            )
            self.assertEqual(len(unexpected_paths), 1)

    def test_rewritten_task_no_drift_passes(self) -> None:
        """No edits post-migration → rewritten task is NOT flagged."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = _make_pre_1_0_repo(Path(tmp))
            plan = flowctl._migrate_collect_plan(flow_dir)
            entries, meta_summary = flowctl._migrate_apply_plan(flow_dir, plan)
            manifest = {
                "version": 1,
                "schema_version_to": flowctl.SCHEMA_VERSION,
                "entries": entries,
                "meta_summary": meta_summary,
            }
            # Stage backup with the rewritten content (so backup drift detection
            # for the .md spec file doesn't false-positive).
            backup_dir = flow_dir / flowctl.MIGRATE_BACKUP_DIR
            (backup_dir / flowctl.SPECS_DIR).mkdir(parents=True)
            (backup_dir / flowctl.TASKS_DIR).mkdir(parents=True)
            (backup_dir / flowctl.SPECS_DIR / "fn-1.md").write_text(
                (flow_dir / flowctl.SPECS_DIR / "fn-1.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (backup_dir / flowctl.SPECS_DIR / "fn-2.md").write_text(
                (flow_dir / flowctl.SPECS_DIR / "fn-2.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            shutil.copy2(
                flow_dir / flowctl.TASKS_DIR / "fn-1.1.json",
                backup_dir / flowctl.TASKS_DIR / "fn-1.1.json",
            )
            shutil.copy2(
                flow_dir / flowctl.TASKS_DIR / "fn-1.1.md",
                backup_dir / flowctl.TASKS_DIR / "fn-1.1.md",
            )
            shutil.copy2(
                flow_dir / flowctl.TASKS_DIR / "fn-2.1.json",
                backup_dir / flowctl.TASKS_DIR / "fn-2.1.json",
            )
            unexpected = flowctl._rollback_post_migration_writes(flow_dir, manifest)
            # No drift on tasks the migration rewrote.
            self.assertEqual(unexpected, [])


# --- End-to-end migrate-rename via cmd_migrate_rename --------------------


class TestCmdMigrateRenameEndToEnd(unittest.TestCase):
    """Drive `cmd_migrate_rename` through chdir + faked argparse Namespace."""

    def setUp(self) -> None:
        self._tmp_obj = tempfile.TemporaryDirectory()
        self._tmp = Path(self._tmp_obj.name)
        # Build a non-git repo (get_repo_root falls back to cwd).
        self.flow_dir = _make_pre_1_0_repo(self._tmp)

    def tearDown(self) -> None:
        self._tmp_obj.cleanup()

    def _make_args(self, **kwargs: Any) -> Any:
        import argparse

        defaults = {
            "json": False,
            "yes": False,
            "dry_run": False,
            "force_overwrite_post_migration_changes": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_dry_run_writes_no_state_but_describes_plan(self) -> None:
        with _chdir(self._tmp):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                flowctl.cmd_migrate_rename(self._make_args(dry_run=True))
            output = buf.getvalue()
            self.assertIn("Migration plan", output)
            self.assertIn("--yes to apply", output)
        # No sentinel written.
        self.assertFalse((self.flow_dir / flowctl.FLOW_VERSION_SENTINEL).exists())
        # No manifest written.
        self.assertFalse((self.flow_dir / flowctl.MIGRATE_MANIFEST_FILE).exists())
        # ack file IS written by dry-run (per fn-43.4 / R34 — explicit user
        # acknowledgement starts the 7-day re-nudge clock).
        self.assertTrue((self.flow_dir / flowctl.BANNER_ACK_FILE).exists())

    def test_yes_applies_and_writes_sentinel_last(self) -> None:
        with _chdir(self._tmp):
            buf = io.StringIO()
            with (
                contextlib.redirect_stdout(buf),
                mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None),
            ):
                flowctl.cmd_migrate_rename(self._make_args(yes=True, json=True))

        sentinel = self.flow_dir / flowctl.FLOW_VERSION_SENTINEL
        manifest = self.flow_dir / flowctl.MIGRATE_MANIFEST_FILE
        backup = self.flow_dir / flowctl.MIGRATE_BACKUP_DIR
        self.assertTrue(sentinel.exists())
        self.assertEqual(
            sentinel.read_text(encoding="utf-8").strip(),
            flowctl.FLOW_VERSION_PAYLOAD,
        )
        self.assertTrue(manifest.exists())
        self.assertTrue(backup.exists())
        self.assertTrue((backup / flowctl.MIGRATE_BACKUP_COMPLETE_MARKER).exists())
        # epics/ removed.
        self.assertFalse((self.flow_dir / flowctl.EPICS_DIR).exists())
        # specs/ has the JSONs.
        self.assertTrue((self.flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json").exists())
        # tasks have canonical key.
        t1 = json.loads(
            (self.flow_dir / flowctl.TASKS_DIR / "fn-1.1.json").read_text()
        )
        self.assertEqual(t1.get("spec"), "fn-1")
        self.assertNotIn("epic", t1)

    def test_yes_then_re_yes_is_idempotent(self) -> None:
        """Re-running --yes on an already-migrated repo is a no-op."""
        with _chdir(self._tmp):
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_migrate_rename(self._make_args(yes=True, json=True))
            sentinel_mtime_before = (
                self.flow_dir / flowctl.FLOW_VERSION_SENTINEL
            ).stat().st_mtime

            # Second invocation — should hit the fast-path idempotency check
            # and exit cleanly without rewriting the sentinel.
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_migrate_rename(self._make_args(yes=True, json=True))
            sentinel_mtime_after = (
                self.flow_dir / flowctl.FLOW_VERSION_SENTINEL
            ).stat().st_mtime
            self.assertEqual(sentinel_mtime_before, sentinel_mtime_after)

    def test_idempotency_check_runs_before_readonly_check(self) -> None:
        """Already-migrated repo on read-only fs is a no-op (NOT exit 1).

        Validates ordering invariant: idempotency check runs BEFORE the
        read-only writability probe. Fakes `_migrate_writable` to return
        False so we can assert the no-op completes without hitting the
        read-only refusal branch."""
        # First run a real migration to install the sentinel.
        with _chdir(self._tmp):
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_migrate_rename(self._make_args(yes=True, json=True))

        # Now simulate read-only `.flow/`. Without the ordering invariant,
        # cmd_migrate_rename would raise SystemExit (read-only refusal).
        with _chdir(self._tmp):
            with (
                mock.patch.object(flowctl, "_migrate_writable", return_value=False),
                mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None),
            ):
                # Must NOT raise — sentinel is valid → fast-path no-op.
                flowctl.cmd_migrate_rename(self._make_args(yes=True, json=True))

    def test_dry_run_and_yes_mutually_exclusive(self) -> None:
        """Passing both surfaces an error (fn-43.3 conflict-detection)."""
        with _chdir(self._tmp):
            with (
                contextlib.redirect_stderr(io.StringIO()),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as cm:
                    flowctl.cmd_migrate_rename(
                        self._make_args(yes=True, dry_run=True)
                    )
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
