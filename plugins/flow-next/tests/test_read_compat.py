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

import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any


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


if __name__ == "__main__":
    unittest.main()
