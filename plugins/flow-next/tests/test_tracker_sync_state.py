"""Per-spec tracker sync-state setter / enumerate tests (fn-52.1, R4 + R5).

Asserts:
  * Spec sidecar carries a `tracker` block at creation with the documented
    fields (id, identifier, url, lastSyncedAt, merge-base flow+tracker form,
    content hashes), all writes atomic.
  * Setters follow the set-branch idiom: resolve → mutate → stamp updated_at →
    atomic-write. `set-tracker-id`, `set-last-synced`, `set-merge-base`, `clear`.
  * Merge-base stores BOTH flow-form and tracker-form snapshots plus their
    content hashes (the echo-fence).
  * `list-unsynced` lists specs with no tracker id.
  * `list-stale --older-than-hours N` honors the flag and defaults to
    `tracker.staleAfterHours`; a MISSING lastSyncedAt always counts stale; an
    unlinked spec is never "stale".
  * Dup-tracker-id is refused without --force; `check-collisions` flags two
    specs sharing one tracker id.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_tracker_state_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TrackerSyncStateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        # A git repo so get_repo_root() resolves to the temp dir.
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self._call("init")

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- helpers ------------------------------------------------------------

    def _call(self, func_name: str = None, *, func=None, **kwargs) -> dict:
        """Invoke a cmd handler in-process with --json and capture the JSON."""
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        handler = func or getattr(self.flowctl, f"cmd_{func_name}")
        buf = io.StringIO()
        with redirect_stdout(buf):
            handler(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _create_spec(self, title: str) -> str:
        res = self._call(func=self.flowctl.cmd_spec_create, title=title, branch=None)
        return res["id"]

    def _state(self, spec_id: str) -> dict:
        return self._call(func=self.flowctl.cmd_sync_get_state, id=spec_id)["tracker"]

    def _set_id(self, spec_id: str, tracker_id: str, **kw) -> dict:
        return self._call(
            func=self.flowctl.cmd_sync_set_tracker_id,
            id=spec_id,
            tracker_id=tracker_id,
            identifier=kw.get("identifier"),
            url=kw.get("url"),
            force=kw.get("force", False),
        )

    # --- sidecar schema -----------------------------------------------------

    def test_new_spec_sidecar_has_tracker_block(self) -> None:
        spec_id = self._create_spec("Alpha tracker state")
        state = self._state(spec_id)
        for field in (
            "id",
            "identifier",
            "url",
            "lastSyncedAt",
            "baseHashFlow",
            "baseHashTracker",
            "mergeBaseFlow",
            "mergeBaseTracker",
        ):
            self.assertIn(field, state)
            self.assertIsNone(state[field])

    def test_set_tracker_id_persists_atomically(self) -> None:
        spec_id = self._create_spec("Beta tracker state")
        self._set_id(spec_id, "uuid-beta", identifier="WOR-9", url="https://x/WOR-9")
        # Re-read from disk (not the return value) to prove the write landed.
        state = self._state(spec_id)
        self.assertEqual(state["id"], "uuid-beta")
        self.assertEqual(state["identifier"], "WOR-9")
        self.assertEqual(state["url"], "https://x/WOR-9")

    def test_set_last_synced_defaults_to_now(self) -> None:
        spec_id = self._create_spec("Gamma tracker state")
        res = self._call(func=self.flowctl.cmd_sync_set_last_synced, id=spec_id, at=None)
        self.assertTrue(res["lastSyncedAt"].endswith("Z"))
        self.assertEqual(self._state(spec_id)["lastSyncedAt"], res["lastSyncedAt"])

    def test_merge_base_stores_both_forms_and_hashes(self) -> None:
        spec_id = self._create_spec("Delta tracker state")
        self._call(
            func=self.flowctl.cmd_sync_set_merge_base,
            id=spec_id,
            flow="## Goal\nflow body",
            flow_file=None,
            tracker="free-form tracker body",
            tracker_file=None,
        )
        state = self._state(spec_id)
        self.assertEqual(state["mergeBaseFlow"], "## Goal\nflow body")
        self.assertEqual(state["mergeBaseTracker"], "free-form tracker body")
        self.assertEqual(
            state["baseHashFlow"], self.flowctl._content_hash("## Goal\nflow body")
        )
        self.assertEqual(
            state["baseHashTracker"], self.flowctl._content_hash("free-form tracker body")
        )
        # Distinct content → distinct hashes.
        self.assertNotEqual(state["baseHashFlow"], state["baseHashTracker"])

    def test_clear_wipes_state(self) -> None:
        spec_id = self._create_spec("Epsilon tracker state")
        self._set_id(spec_id, "uuid-eps", identifier="WOR-3")
        self._call(func=self.flowctl.cmd_sync_set_last_synced, id=spec_id, at=None)
        res = self._call(func=self.flowctl.cmd_sync_clear, id=spec_id)
        self.assertIsNone(res["tracker"]["id"])
        self.assertIsNone(res["tracker"]["lastSyncedAt"])
        self.assertIsNone(self._state(spec_id)["id"])

    # --- enumerate helpers (R5) ---------------------------------------------

    def test_list_unsynced(self) -> None:
        s1 = self._create_spec("Unsynced one")
        s2 = self._create_spec("Unsynced two")
        res = self._call(func=self.flowctl.cmd_sync_list_unsynced)
        self.assertIn(s1, res["unsynced"])
        self.assertIn(s2, res["unsynced"])
        # Linking one removes it.
        self._set_id(s1, "uuid-1")
        res2 = self._call(func=self.flowctl.cmd_sync_list_unsynced)
        self.assertNotIn(s1, res2["unsynced"])
        self.assertIn(s2, res2["unsynced"])

    def test_list_stale_missing_last_synced_counts_stale(self) -> None:
        s1 = self._create_spec("Stale linked")
        self._set_id(s1, "uuid-stale")  # linked, never synced
        s2 = self._create_spec("Unlinked")  # no tracker id → not "stale"
        res = self._call(func=self.flowctl.cmd_sync_list_stale, older_than_hours=None)
        ids = [item["id"] for item in res["stale"]]
        self.assertIn(s1, ids)
        self.assertNotIn(s2, ids)
        self.assertEqual(res["olderThanHours"], self.flowctl.TRACKER_DEFAULT_STALE_HOURS)

    def test_list_stale_honors_flag_and_recency(self) -> None:
        s1 = self._create_spec("Fresh sync")
        self._set_id(s1, "uuid-fresh")
        self._call(func=self.flowctl.cmd_sync_set_last_synced, id=s1, at=None)
        # 24h threshold: just-synced spec is NOT stale.
        res = self._call(func=self.flowctl.cmd_sync_list_stale, older_than_hours=24)
        self.assertNotIn(s1, [i["id"] for i in res["stale"]])
        # 0h threshold: everything synced "in the past" is stale.
        res0 = self._call(func=self.flowctl.cmd_sync_list_stale, older_than_hours=0)
        self.assertIn(s1, [i["id"] for i in res0["stale"]])
        self.assertEqual(res0["olderThanHours"], 0)

    def test_list_stale_default_reads_config_override(self) -> None:
        # Override the configured staleAfterHours; list-stale default honors it.
        self.flowctl.set_config("tracker.staleAfterHours", 999)
        s1 = self._create_spec("Config-default stale")
        self._set_id(s1, "uuid-cfg")
        self._call(func=self.flowctl.cmd_sync_set_last_synced, id=s1, at=None)
        res = self._call(func=self.flowctl.cmd_sync_list_stale, older_than_hours=None)
        self.assertEqual(res["olderThanHours"], 999)
        self.assertNotIn(s1, [i["id"] for i in res["stale"]])

    # --- dup-id detection (R5) ----------------------------------------------

    def test_dup_tracker_id_refused_without_force(self) -> None:
        s1 = self._create_spec("Dup owner")
        s2 = self._create_spec("Dup claimant")
        self._set_id(s1, "uuid-shared")
        with self.assertRaises(SystemExit):
            self._set_id(s2, "uuid-shared")
        # s2 stays unlinked.
        self.assertIsNone(self._state(s2)["id"])

    def test_relink_same_spec_same_id_is_fine(self) -> None:
        s1 = self._create_spec("Relink self")
        self._set_id(s1, "uuid-self")
        # No SystemExit: re-linking the SAME spec to the SAME id is allowed.
        self._set_id(s1, "uuid-self", url="https://x/updated")
        self.assertEqual(self._state(s1)["url"], "https://x/updated")

    def test_check_collisions_flags_shared_id(self) -> None:
        s1 = self._create_spec("Collide one")
        s2 = self._create_spec("Collide two")
        self._set_id(s1, "uuid-coll")
        self._set_id(s2, "uuid-coll", force=True)
        res = self._call(func=self.flowctl.cmd_sync_check_collisions)
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["collisions"][0]["trackerId"], "uuid-coll")
        self.assertEqual(sorted(res["collisions"][0]["specs"]), sorted([s1, s2]))


if __name__ == "__main__":
    unittest.main()
