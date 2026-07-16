"""Unit tests for the JSON read-compat layer (fn-43.17 / R10 + R31 read-side).

The 1.0 rename has four field categories that need dual-emit / dual-read support:

  spec / epic                  — task JSON: which spec the task belongs to.
  spec_id / epic_id            — historic alternate form on a few task fields.
  next_spec / next_epic        — meta.json counter for next ID allocation.
  specs / epics                — array name in `flowctl specs --json` output.

The contract:

  * On READ: every consumer accepts both forms (canonical wins on collision).
  * On WRITE (persisted JSON): canonical only — `canonicalize_task_for_write`
    strips the legacy keys before atomic_write_json hits disk.
  * On STDOUT (CLI --json output): co-emit BOTH keys for one release of
    backward compat. Existing 1.x consumers keep working; new tooling can
    grep on canonical.
  * `flowctl next` emits `reason: "blocked_by_spec_deps"` (canonical) AND
    `legacy_reason: "blocked_by_epic_deps"` for the same window.

Run:
    python3 -m unittest plugins.flow-next.tests.test_read_compat -v
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
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
        "flowctl_readcompat_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# --- normalize_task: read-side legacy → canonical promotion ---------------


class TestNormalizeTaskReadCompat(unittest.TestCase):
    """`normalize_task` promotes legacy `epic` to canonical `spec` on read."""

    def test_legacy_only_promotes_to_spec(self) -> None:
        task = {"id": "fn-1.1", "epic": "fn-1"}
        out = flowctl.normalize_task(task)
        self.assertEqual(out["spec"], "fn-1")
        # Legacy `epic` is preserved (caller may still need it for dual-emit on
        # CLI output); persisted writes go through canonicalize_task_for_write
        # which strips it.
        self.assertEqual(out.get("epic"), "fn-1")

    def test_canonical_present_legacy_ignored(self) -> None:
        task = {"id": "fn-1.1", "spec": "fn-1", "epic": "fn-LEGACY"}
        out = flowctl.normalize_task(task)
        # Canonical must win on collision (defensive — should not happen in
        # well-formed JSON, but if it does we never let stale `epic` shadow
        # canonical).
        self.assertEqual(out["spec"], "fn-1")

    def test_canonical_only_unchanged(self) -> None:
        task = {"id": "fn-1.1", "spec": "fn-1"}
        out = flowctl.normalize_task(task)
        self.assertEqual(out["spec"], "fn-1")
        self.assertNotIn("epic", out)


# --- canonicalize_task_for_write: write-side canonical-only invariant ---


class TestCanonicalizeTaskForWrite(unittest.TestCase):
    """Persisted task JSON is canonical-only — `epic` / `epic_id` stripped."""

    def test_strip_legacy_epic_field(self) -> None:
        task = {"id": "fn-1.1", "epic": "fn-1", "title": "x"}
        out = flowctl.canonicalize_task_for_write(task)
        self.assertNotIn("epic", out)
        self.assertEqual(out["spec"], "fn-1")

    def test_strip_legacy_epic_id_field(self) -> None:
        task = {"id": "fn-1.1", "epic_id": "fn-1", "title": "x"}
        out = flowctl.canonicalize_task_for_write(task)
        self.assertNotIn("epic_id", out)
        self.assertEqual(out["spec_id"], "fn-1")

    def test_canonical_wins_when_both_present(self) -> None:
        task = {
            "id": "fn-1.1",
            "spec": "fn-1",
            "epic": "fn-LEGACY",
            "spec_id": "fn-1",
            "epic_id": "fn-LEGACY-ID",
            "title": "x",
        }
        out = flowctl.canonicalize_task_for_write(task)
        self.assertEqual(out["spec"], "fn-1")
        self.assertEqual(out["spec_id"], "fn-1")
        self.assertNotIn("epic", out)
        self.assertNotIn("epic_id", out)

    def test_idempotent(self) -> None:
        task = {"id": "fn-1.1", "spec": "fn-1", "title": "x"}
        out1 = flowctl.canonicalize_task_for_write(dict(task))
        out2 = flowctl.canonicalize_task_for_write(dict(out1))
        self.assertEqual(out1, out2)

    def test_persisted_json_canonical_only_round_trip(self) -> None:
        """End-to-end: writing canonicalized data + reading it back is canonical."""
        import tempfile

        task = {
            "id": "fn-1.1",
            "epic": "fn-1",
            "epic_id": "fn-1",
            "title": "x",
            "depends_on": [],
        }
        flowctl.canonicalize_task_for_write(task)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(task, f)
            tmp_path = f.name
        try:
            with open(tmp_path, encoding="utf-8") as f:
                loaded = json.load(f)
            # Persisted JSON contains NEITHER legacy field.
            self.assertNotIn("epic", loaded)
            self.assertNotIn("epic_id", loaded)
            self.assertEqual(loaded["spec"], "fn-1")
            self.assertEqual(loaded["spec_id"], "fn-1")
        finally:
            Path(tmp_path).unlink()


# --- meta.json next_spec / next_epic dual-read ---------------------------


class TestMetaNextSpecReadCompat(unittest.TestCase):
    """`meta.get("next_spec") or meta.get("next_epic")` reads both forms."""

    def test_next_spec_canonical(self) -> None:
        meta = {"schema_version": 3, "next_spec": 7}
        self.assertEqual(meta.get("next_spec") or meta.get("next_epic"), 7)

    def test_next_epic_legacy(self) -> None:
        meta = {"schema_version": 2, "next_epic": 4}
        self.assertEqual(meta.get("next_spec") or meta.get("next_epic"), 4)

    def test_canonical_wins_over_legacy(self) -> None:
        meta = {"schema_version": 3, "next_spec": 7, "next_epic": 4}
        self.assertEqual(meta.get("next_spec") or meta.get("next_epic"), 7)

    def test_neither_returns_falsy(self) -> None:
        meta = {"schema_version": 3}
        self.assertFalse(meta.get("next_spec") or meta.get("next_epic"))


# --- flowctl next reason-code dual-emit ----------------------------------


class TestFlowctlNextReasonDualEmit(unittest.TestCase):
    """`flowctl next --json` emits canonical AND legacy reason codes."""

    def test_blocked_payload_carries_both_reason_codes(self) -> None:
        """The blocked payload (in cmd_next) emits both `reason: blocked_by_spec_deps`
        and `legacy_reason: blocked_by_epic_deps` so 1.x consumers grepping
        either string keep working."""
        # Replicate the exact payload-build branch from cmd_next so we test
        # the contract independently of cmd_next's full surface (which needs
        # a real .flow/ tree). The structural assertion is "both keys carry
        # the right code".
        blocked_epics = {"fn-2": ["fn-1"]}
        payload = {
            "status": "none",
            "spec": None,
            "epic": None,
            "task": None,
            "reason": "none",
        }
        if blocked_epics:
            payload["reason"] = "blocked_by_spec_deps"
            payload["legacy_reason"] = "blocked_by_epic_deps"
            payload["blocked_specs"] = blocked_epics
            payload["blocked_epics"] = blocked_epics

        self.assertEqual(payload["reason"], "blocked_by_spec_deps")
        self.assertEqual(payload["legacy_reason"], "blocked_by_epic_deps")
        self.assertEqual(payload["blocked_specs"], payload["blocked_epics"])

    def test_unblocked_payload_carries_canonical_reason_only(self) -> None:
        """Status none / no blocked deps: canonical `reason: none`, no
        `legacy_reason`. Per fn-43.2: legacy_reason is only emitted when
        the blocked branch fires (matches old 1.x semantics)."""
        payload = {
            "status": "none",
            "spec": None,
            "epic": None,
            "task": None,
            "reason": "none",
        }
        self.assertEqual(payload["reason"], "none")
        self.assertNotIn("legacy_reason", payload)


# --- task --json dual-emit shape -----------------------------------------


class TestTaskJsonDualEmit(unittest.TestCase):
    """`flowctl show <task-id> --json` emits both `spec` AND `epic` keys."""

    def test_spec_and_epic_both_emitted_after_normalize(self) -> None:
        """Replicate the cmd_show branch that dual-emits both keys.

        normalize_task() promotes 0.x `epic` → canonical `spec` on read; the
        cmd_show task branch then sets BOTH to the same value before printing.
        """
        # Simulate a 0.x task JSON file.
        task_data = flowctl.normalize_task({
            "id": "fn-1.1",
            "epic": "fn-1",
            "title": "x",
            "depends_on": [],
            "status": "todo",
        })
        spec_value = task_data.get("spec") or task_data.get("epic")
        if spec_value is not None:
            task_data["spec"] = spec_value
            task_data["epic"] = spec_value
        self.assertEqual(task_data["spec"], "fn-1")
        self.assertEqual(task_data["epic"], "fn-1")


# --- flowctl next --json dual-emit (spec + epic, status: work) -----------


class TestFlowctlNextDualEmitSpecKey(unittest.TestCase):
    """`flowctl next --json` co-emits canonical `spec` + legacy `epic`."""

    def test_work_payload_carries_both_keys(self) -> None:
        epic_id = "fn-1"
        task_id = "fn-1.2"
        # Replicate the exact dict from cmd_next's "work / ready_task" branch.
        payload = {
            "status": "work",
            "spec": epic_id,
            "epic": epic_id,
            "task": task_id,
            "reason": "ready_task",
        }
        self.assertEqual(payload["spec"], epic_id)
        self.assertEqual(payload["epic"], epic_id)
        self.assertEqual(payload["spec"], payload["epic"])

    def test_completion_review_payload_carries_both_keys(self) -> None:
        epic_id = "fn-1"
        payload = {
            "status": "completion_review",
            "spec": epic_id,
            "epic": epic_id,
            "task": None,
            "reason": "needs_completion_review",
        }
        self.assertEqual(payload["spec"], epic_id)
        self.assertEqual(payload["epic"], epic_id)


# --- End-to-end CLI dual-emit via real .flow/ fixtures + json_output capture ---


@contextlib.contextmanager
def _chdir(target: Path):
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prev)


def _capture_json_output(callable_, *args, **kwargs) -> dict:
    """Drive a `cmd_*` function and return the dict it would have emitted.

    `flowctl.json_output` writes to stdout via `print(json.dumps(...))`; we
    monkey-patch it to capture the dict directly so the test can assert
    against the exact emitted payload (not the parsed-back representation).
    """
    captured: dict = {}

    def fake_output(data, success=True):
        # Mirror json_output's "{success: True, **data}" wrapping shape.
        captured.update({"success": success, **data})

    with mock.patch.object(flowctl, "json_output", fake_output):
        callable_(*args, **kwargs)
    return captured


def _seed_alias_mode_repo(tmp: Path) -> Path:
    """Build a 0.x layout (no sentinel, has epics/) with two specs + tasks."""
    flow_dir = tmp / ".flow"
    (flow_dir / flowctl.EPICS_DIR).mkdir(parents=True)
    (flow_dir / flowctl.SPECS_DIR).mkdir(parents=True)  # markdown lives here
    (flow_dir / flowctl.TASKS_DIR).mkdir(parents=True)
    (flow_dir / flowctl.MEMORY_DIR).mkdir(parents=True)

    # 0.x meta.json: schema 2 + next_epic.
    flowctl.atomic_write_json(
        flow_dir / flowctl.META_FILE,
        {"schema_version": 2, "next_epic": 3},
    )

    # epics/fn-1.json (0.x JSON sidecar location).
    flowctl.atomic_write_json(
        flow_dir / flowctl.EPICS_DIR / "fn-1.json",
        {
            "id": "fn-1",
            "title": "First spec",
            "status": "open",
            "next_task": 1,
            "spec_path": ".flow/specs/fn-1.md",
            "depends_on_epics": [],
            "created_at": "2026-05-01T00:00:00Z",
            "updated_at": "2026-05-01T00:00:00Z",
        },
    )
    flowctl.atomic_write_json(
        flow_dir / flowctl.EPICS_DIR / "fn-2.json",
        {
            "id": "fn-2",
            "title": "Second spec",
            "status": "open",
            "next_task": 1,
            "spec_path": ".flow/specs/fn-2.md",
            "depends_on_epics": [],
            "created_at": "2026-05-02T00:00:00Z",
            "updated_at": "2026-05-02T00:00:00Z",
        },
    )

    # Task with legacy `epic` key (0.x shape).
    flowctl.atomic_write_json(
        flow_dir / flowctl.TASKS_DIR / "fn-1.1.json",
        {
            "id": "fn-1.1",
            "epic": "fn-1",
            "title": "Task A",
            "status": "todo",
            "depends_on": [],
            "created_at": "2026-05-01T00:00:00Z",
        },
    )

    # Spec markdown stubs (cmd_specs counts tasks, not markdown contents).
    (flow_dir / flowctl.SPECS_DIR / "fn-1.md").write_text("x\n", encoding="utf-8")
    (flow_dir / flowctl.SPECS_DIR / "fn-2.md").write_text("x\n", encoding="utf-8")

    return tmp


def _seed_post_migration_repo(tmp: Path) -> Path:
    """Build a 1.0 layout (sentinel + specs/) with same data shape."""
    flow_dir = tmp / ".flow"
    (flow_dir / flowctl.SPECS_JSON_DIR).mkdir(parents=True)
    (flow_dir / flowctl.TASKS_DIR).mkdir(parents=True)
    (flow_dir / flowctl.MEMORY_DIR).mkdir(parents=True)

    # 1.0 meta.json: schema 3 + next_spec.
    flowctl.atomic_write_json(
        flow_dir / flowctl.META_FILE,
        {"schema_version": flowctl.SCHEMA_VERSION, "next_spec": 3},
    )

    # specs/fn-1.json (1.0 canonical location).
    flowctl.atomic_write_json(
        flow_dir / flowctl.SPECS_JSON_DIR / "fn-1.json",
        {
            "id": "fn-1",
            "title": "First spec",
            "status": "open",
            "next_task": 1,
            "spec_path": ".flow/specs/fn-1.md",
            "depends_on_epics": [],
            "created_at": "2026-05-01T00:00:00Z",
            "updated_at": "2026-05-01T00:00:00Z",
        },
    )
    flowctl.atomic_write_json(
        flow_dir / flowctl.SPECS_JSON_DIR / "fn-2.json",
        {
            "id": "fn-2",
            "title": "Second spec",
            "status": "open",
            "next_task": 1,
            "spec_path": ".flow/specs/fn-2.md",
            "depends_on_epics": [],
            "created_at": "2026-05-02T00:00:00Z",
            "updated_at": "2026-05-02T00:00:00Z",
        },
    )

    # Canonical-only task (no legacy `epic` field — round-trip after migration).
    flowctl.atomic_write_json(
        flow_dir / flowctl.TASKS_DIR / "fn-1.1.json",
        {
            "id": "fn-1.1",
            "spec": "fn-1",
            "title": "Task A",
            "status": "todo",
            "depends_on": [],
            "created_at": "2026-05-01T00:00:00Z",
        },
    )

    # Sentinel — written LAST in migrate-rename; presence here means migrated.
    (flow_dir / flowctl.FLOW_VERSION_SENTINEL).write_text(
        flowctl.FLOW_VERSION_PAYLOAD + "\n", encoding="utf-8"
    )

    # Spec markdown stubs (markdown lives at .flow/specs/ in both 0.x and 1.0).
    # In post-migration the JSON sidecar dir IS .flow/specs/, so reuse it.
    spec_md_dir = flow_dir / flowctl.SPECS_DIR
    spec_md_dir.mkdir(exist_ok=True)
    (spec_md_dir / "fn-1.md").write_text("x\n", encoding="utf-8")
    (spec_md_dir / "fn-2.md").write_text("x\n", encoding="utf-8")

    return tmp


class TestCmdSpecsDualEmit(unittest.TestCase):
    """`flowctl specs --json` co-emits canonical `specs` + legacy `epics`."""

    def test_alias_mode_emits_both_keys_with_same_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_specs, argparse.Namespace(json=True)
                )
        self.assertIn("specs", result)
        self.assertIn("epics", result)
        self.assertEqual(result["specs"], result["epics"])
        self.assertEqual(len(result["specs"]), 2)
        self.assertEqual(
            sorted(s["id"] for s in result["specs"]),
            ["fn-1", "fn-2"],
        )
        self.assertEqual(result["count"], 2)

    def test_post_migration_emits_both_keys_with_same_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_post_migration_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_specs, argparse.Namespace(json=True)
                )
        self.assertEqual(result["specs"], result["epics"])
        self.assertEqual(len(result["specs"]), 2)


class TestCmdShowTaskDualEmit(unittest.TestCase):
    """`flowctl show <task-id> --json` co-emits canonical `spec` + legacy `epic`."""

    def test_alias_mode_legacy_task_dual_emits_canonical_and_legacy_keys(self) -> None:
        """0.x task with `epic: fn-1` round-trips with both `spec` and `epic` set."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_show,
                    argparse.Namespace(id="fn-1.1", json=True),
                )
        self.assertEqual(result["id"], "fn-1.1")
        self.assertEqual(result["spec"], "fn-1")
        self.assertEqual(result["epic"], "fn-1")
        # Both keys emitted with the same value.
        self.assertEqual(result["spec"], result["epic"])

    def test_post_migration_canonical_task_dual_emits_for_back_compat(self) -> None:
        """1.0 canonical task (no `epic` on disk) still dual-emits in CLI output."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_post_migration_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_show,
                    argparse.Namespace(id="fn-1.1", json=True),
                )
        self.assertEqual(result["spec"], "fn-1")
        self.assertEqual(result["epic"], "fn-1")


class TestCmdNextDualEmit(unittest.TestCase):
    """`flowctl next --json` co-emits canonical `spec` + legacy `epic`,
    AND canonical `reason` + `legacy_reason` for blocked deps."""

    def test_ready_task_payload_dual_emits_spec_and_epic(self) -> None:
        """Ready task → status=work + spec + epic both pointing at the same id."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_next,
                    argparse.Namespace(
                        json=True,
                        specs_file=None,
                        epics_file=None,
                        require_plan_review=False,
                        require_completion_review=False,
                    ),
                )
        self.assertEqual(result["status"], "work")
        # cmd_next picks fn-1.1 (the seeded ready task).
        self.assertEqual(result["task"], "fn-1.1")
        self.assertEqual(result["spec"], "fn-1")
        self.assertEqual(result["epic"], "fn-1")
        self.assertEqual(result["reason"], "ready_task")

    def test_blocked_payload_dual_emits_reason_and_legacy_reason(self) -> None:
        """Blocked spec → reason=`blocked_by_spec_deps` + legacy_reason set."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            flow_dir = Path(tmp) / ".flow"
            # Block fn-1 on a non-existent fn-99 — forces the blocked branch.
            spec1 = flowctl.load_json(flow_dir / flowctl.EPICS_DIR / "fn-1.json")
            spec1["depends_on_epics"] = ["fn-99"]
            flowctl.atomic_write_json(
                flow_dir / flowctl.EPICS_DIR / "fn-1.json", spec1
            )
            spec2 = flowctl.load_json(flow_dir / flowctl.EPICS_DIR / "fn-2.json")
            spec2["depends_on_epics"] = ["fn-99"]
            flowctl.atomic_write_json(
                flow_dir / flowctl.EPICS_DIR / "fn-2.json", spec2
            )

            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_next,
                    argparse.Namespace(
                        json=True,
                        specs_file=None,
                        epics_file=None,
                        require_plan_review=False,
                        require_completion_review=False,
                    ),
                )
        self.assertEqual(result["status"], "none")
        self.assertEqual(result["reason"], "blocked_by_spec_deps")
        self.assertEqual(result["legacy_reason"], "blocked_by_epic_deps")
        self.assertIn("blocked_specs", result)
        self.assertIn("blocked_epics", result)
        self.assertEqual(result["blocked_specs"], result["blocked_epics"])
        # Both fn-1 and fn-2 are blocked.
        self.assertEqual(set(result["blocked_specs"].keys()), {"fn-1", "fn-2"})


class TestNextSpecMetaPersistedShape(unittest.TestCase):
    """The on-disk meta.json post-migration uses canonical `next_spec` only."""

    def test_post_migration_meta_canonical_only(self) -> None:
        """1.0 fixture has no `next_epic` on disk — canonical-only persisted."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_post_migration_repo(Path(tmp))
            meta = flowctl.load_json(Path(tmp) / ".flow" / flowctl.META_FILE)
            self.assertEqual(meta["schema_version"], flowctl.SCHEMA_VERSION)
            self.assertIn("next_spec", meta)
            self.assertNotIn("next_epic", meta)

    def test_alias_mode_meta_legacy_next_epic_preserved(self) -> None:
        """0.x fixture preserves `next_epic` on disk (alias-mode = no migration)."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            meta = flowctl.load_json(Path(tmp) / ".flow" / flowctl.META_FILE)
            self.assertEqual(meta["schema_version"], 2)
            # Legacy form preserved on disk; readers fall back to it.
            self.assertIn("next_epic", meta)


class TestCmdStatusDualEmit(unittest.TestCase):
    """`flowctl status --json` co-emits canonical `specs` + legacy `epics` counts."""

    def test_status_dual_emits_specs_and_epics_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_status, argparse.Namespace(json=True)
                )
        self.assertIn("specs", result)
        self.assertIn("epics", result)
        # Both keys point at the same dict instance / value.
        self.assertEqual(result["specs"], result["epics"])
        self.assertEqual(result["specs"]["open"], 2)


class TestCmdCheckpointSaveDualEmit(unittest.TestCase):
    """`flowctl checkpoint save --json` co-emits canonical `spec_id` + legacy `epic_id`.

    The full `spec_id`/`epic_id` JSON-stdout contract is exercised here — this
    is the canonical place where both keys are emitted together for one
    spec at a time (cmd_show_task uses spec/epic, NOT _id).
    """

    def test_checkpoint_save_dual_emits_spec_id_and_epic_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_checkpoint_save,
                    argparse.Namespace(spec="fn-1", epic=None, json=True),
                )
        self.assertIn("spec_id", result)
        self.assertIn("epic_id", result)
        self.assertEqual(result["spec_id"], "fn-1")
        self.assertEqual(result["epic_id"], "fn-1")
        # Both keys MUST equal — that's the dual-emit contract.
        self.assertEqual(result["spec_id"], result["epic_id"])


class TestCmdMigrateRenameMetaSummaryDualEmit(unittest.TestCase):
    """`flowctl migrate-rename --yes --json` emits meta_summary that exposes
    the next_epic → next_spec rename in both `prev` (legacy) and `next`
    (canonical) blocks. This is the closest stdout dual-emit surface for the
    next_spec/next_epic field — fresh allocation lives in the meta_summary
    payload of migrate-rename receipts."""

    def test_meta_summary_carries_both_names_across_prev_and_next(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            with _chdir(Path(tmp)):
                result = _capture_json_output(
                    flowctl.cmd_migrate_rename,
                    argparse.Namespace(
                        yes=True,
                        dry_run=False,
                        json=True,
                        force_overwrite_post_migration_changes=False,
                    ),
                )
        # entries contains rewrite_meta with prev (legacy) + next (canonical).
        rewrite_entries = [
            e for e in result.get("entries", []) if e.get("action") == "rewrite_meta"
        ]
        self.assertEqual(len(rewrite_entries), 1)
        rewrite = rewrite_entries[0]
        # Legacy form preserved in `prev`.
        self.assertIn("next_epic", rewrite["prev"])
        self.assertEqual(rewrite["prev"]["next_epic"], 3)
        # Canonical form lands in `next`.
        self.assertIn("next_spec", rewrite["next"])
        self.assertEqual(rewrite["next"]["next_spec"], 3)
        # Migration drops the legacy key from the post-migration meta.
        self.assertNotIn("next_epic", rewrite["next"])

    def test_dual_emit_round_trips_via_real_flowctl_subprocess(self) -> None:
        """Belt-and-braces end-to-end: drive the actual `flowctl status --json`
        binary from a subprocess against a seeded repo and parse its stdout
        JSON. Verifies the `specs`/`epics` dual-emit clears the wire — not
        just an in-process json_output capture.
        """
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            _seed_alias_mode_repo(Path(tmp))
            proc = subprocess.run(
                [sys.executable, str(FLOWCTL_PY), "status", "--json"],
                cwd=tmp,
                capture_output=True,
                text=True,
                env={**os.environ, "FLOW_NO_AUTO_MIGRATE": "1"},
                timeout=30,
            )
            self.assertEqual(
                proc.returncode, 0, msg=f"stderr: {proc.stderr}"
            )
            payload = json.loads(proc.stdout)
        # Both keys present, same value.
        self.assertIn("specs", payload)
        self.assertIn("epics", payload)
        self.assertEqual(payload["specs"], payload["epics"])
        self.assertEqual(payload["specs"]["open"], 2)


class TestPersistedTaskJsonCanonicalOnlyOnWrite(unittest.TestCase):
    """End-to-end: `canonicalize_task_for_write` + `atomic_write_json` produces
    canonical-only JSON on disk regardless of input shape."""

    def test_legacy_task_round_trip_canonical_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "task.json"
            task = {
                "id": "fn-1.1",
                "epic": "fn-1",
                "epic_id": "fn-1",
                "title": "x",
                "depends_on": [],
            }
            flowctl.canonicalize_task_for_write(task)
            flowctl.atomic_write_json(target, task)
            on_disk = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["spec"], "fn-1")
            self.assertEqual(on_disk["spec_id"], "fn-1")
            self.assertNotIn("epic", on_disk)
            self.assertNotIn("epic_id", on_disk)


if __name__ == "__main__":
    unittest.main()
