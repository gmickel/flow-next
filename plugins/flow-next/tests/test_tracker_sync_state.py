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
        # fn-64: depRelations is a provenance LIST, defaulting to [] (not None).
        self.assertIn("depRelations", state)
        self.assertEqual(state["depRelations"], [])

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

    def test_merge_base_partial_update_rejected(self) -> None:
        # The merge base is a PAIRED snapshot at one sync point. A partial
        # write (only one side) would desync the 3-way merge base, so it must
        # be rejected and leave state unchanged.
        spec_id = self._create_spec("Paired base invariant")
        # Seed a complete paired base.
        self._call(
            func=self.flowctl.cmd_sync_set_merge_base,
            id=spec_id,
            flow="flow v1",
            flow_file=None,
            tracker="tracker v1",
            tracker_file=None,
        )
        before = self._state(spec_id)
        # Attempt a flow-only update → must error.
        with self.assertRaises(SystemExit):
            self._call(
                func=self.flowctl.cmd_sync_set_merge_base,
                id=spec_id,
                flow="flow v2",
                flow_file=None,
                tracker=None,
                tracker_file=None,
            )
        # State unchanged — the stale-half pin never happened.
        after = self._state(spec_id)
        self.assertEqual(after["mergeBaseFlow"], before["mergeBaseFlow"])
        self.assertEqual(after["mergeBaseTracker"], before["mergeBaseTracker"])
        self.assertEqual(after["baseHashFlow"], before["baseHashFlow"])
        # A tracker-only update is likewise rejected.
        with self.assertRaises(SystemExit):
            self._call(
                func=self.flowctl.cmd_sync_set_merge_base,
                id=spec_id,
                flow=None,
                flow_file=None,
                tracker="tracker v2",
                tracker_file=None,
            )
        # And a no-arg call is rejected too.
        with self.assertRaises(SystemExit):
            self._call(
                func=self.flowctl.cmd_sync_set_merge_base,
                id=spec_id,
                flow=None,
                flow_file=None,
                tracker=None,
                tracker_file=None,
            )

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

    # --- GitHub `#N` reference identifiers (fn-52 GitHub round-trip) ---------
    # A GitHub identifier is a `#N` reference (display-only, used in a
    # `Refs #N` PR cross-link), NOT a resolvable Linear handle. set-tracker-id
    # must accept it; the strict Linear-handle validator alone would reject it
    # and the whole GitHub adapter could never store a link.

    def test_github_reference_identifier_accepted(self) -> None:
        spec_id = self._create_spec("GH ref link")
        self._set_id(
            spec_id,
            "I_kwDO_nodeid",
            identifier="#42",
            url="https://github.com/o/r/issues/42",
        )
        state = self._state(spec_id)
        self.assertEqual(state["id"], "I_kwDO_nodeid")
        self.assertEqual(state["identifier"], "#42")  # stored display-only, not rejected

    def test_owner_repo_reference_identifier_accepted(self) -> None:
        spec_id = self._create_spec("GH qualified ref")
        self._set_id(spec_id, "node-2", identifier="octo/repo#7")
        self.assertEqual(self._state(spec_id)["identifier"], "octo/repo#7")

    def test_malformed_reference_identifier_still_rejected(self) -> None:
        # The reference must be `#<digits>` — `#abc` is not a valid identifier.
        spec_id = self._create_spec("Bad ref")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "node-3", identifier="#abc")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_linear_handle_identifier_still_strict(self) -> None:
        # The Linear handle path is unchanged — a slugged identifier is rejected.
        spec_id = self._create_spec("Linear strict")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "uuid-x", identifier="wor-17-slug")
        self.assertIsNone(self._state(spec_id)["id"])

    def test_bare_numeric_identifier_accepted(self) -> None:
        # fn-64: `sync set-tracker-id --identifier 42` must succeed; a bare
        # numeric is a display-only reference normalized to the `#42` form.
        spec_id = self._create_spec("Bare numeric link")
        self._set_id(spec_id, "node-bare", identifier="42")
        state = self._state(spec_id)
        self.assertEqual(state["id"], "node-bare")
        self.assertEqual(state["identifier"], "#42")  # normalized display form

    def test_bare_zero_identifier_rejected(self) -> None:
        # A leading-zero / zero number is not a valid issue reference.
        spec_id = self._create_spec("Bare zero")
        with self.assertRaises(SystemExit):
            self._set_id(spec_id, "node-zero", identifier="0")
        self.assertIsNone(self._state(spec_id)["id"])


class TrackerDepRelationsTestCase(unittest.TestCase):
    """fn-64: depRelations ledger + list/set/clear-dep-relation plumbing."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
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

    def _add_dep(self, spec_id: str, dep_id: str) -> dict:
        return self._call(
            func=self.flowctl.cmd_spec_add_dep, epic=spec_id, depends_on=dep_id
        )

    def _set_dep_relation(self, spec_id: str, dep_spec: str, frm: str, to: str, **kw) -> dict:
        return self._call(
            func=self.flowctl.cmd_sync_set_dep_relation,
            id=spec_id,
            dep_spec=dep_spec,
            from_tracker_id=frm,
            to_tracker_id=to,
            type=kw.get("type", "blocks"),
            source=kw.get("source", "flow"),
        )

    def _list_dep_relations(self, spec_id: str) -> dict:
        return self._call(func=self.flowctl.cmd_sync_list_dep_relations, id=spec_id)

    # --- ledger: add / idempotent / clear -----------------------------------

    def test_set_dep_relation_records_entry_shape(self) -> None:
        parent = self._create_spec("Parent spec")
        dep = self._create_spec("Dep spec")
        res = self._set_dep_relation(parent, dep, "node-parent", "node-dep")
        self.assertTrue(res["success"])
        # Re-read from disk to prove the atomic write landed.
        ledger = self._state(parent)["depRelations"]
        self.assertEqual(len(ledger), 1)
        entry = ledger[0]
        self.assertEqual(entry["dep_spec"], dep)
        self.assertEqual(entry["from_tracker_id"], "node-parent")
        self.assertEqual(entry["to_tracker_id"], "node-dep")
        self.assertEqual(entry["type"], "blocks")
        self.assertEqual(entry["source"], "flow")
        self.assertTrue(entry["updatedAt"].endswith("Z"))
        # key is an opaque token, never a raw tracker id inlined.
        self.assertTrue(entry["key"])
        self.assertNotIn("node-dep", entry["key"])
        self.assertNotIn("node-parent", entry["key"])

    def test_set_dep_relation_idempotent_no_dup(self) -> None:
        parent = self._create_spec("Parent idem")
        dep = self._create_spec("Dep idem")
        self._set_dep_relation(parent, dep, "node-p", "node-d")
        first = self._state(parent)["depRelations"]
        first_ts = first[0]["updatedAt"]
        # Re-run with the SAME directed edge → no-op, no second entry, no ts bump.
        res = self._set_dep_relation(parent, dep, "node-p", "node-d")
        self.assertIn("already recorded", res["message"])
        ledger = self._state(parent)["depRelations"]
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["updatedAt"], first_ts)

    def test_clear_dep_relation_by_dep_spec(self) -> None:
        parent = self._create_spec("Parent clear")
        dep = self._create_spec("Dep clear")
        self._set_dep_relation(parent, dep, "node-p", "node-d")
        res = self._call(
            func=self.flowctl.cmd_sync_clear_dep_relation,
            id=parent,
            dep_spec=dep,
            key=None,
        )
        self.assertEqual(res["removed"], 1)
        self.assertEqual(self._state(parent)["depRelations"], [])

    def test_clear_dep_relation_by_key(self) -> None:
        parent = self._create_spec("Parent clearkey")
        dep = self._create_spec("Dep clearkey")
        set_res = self._set_dep_relation(parent, dep, "node-p", "node-d")
        res = self._call(
            func=self.flowctl.cmd_sync_clear_dep_relation,
            id=parent,
            dep_spec=None,
            key=set_res["key"],
        )
        self.assertEqual(res["removed"], 1)
        self.assertEqual(self._state(parent)["depRelations"], [])

    def test_clear_missing_dep_relation_is_noop(self) -> None:
        parent = self._create_spec("Parent noclear")
        res = self._call(
            func=self.flowctl.cmd_sync_clear_dep_relation,
            id=parent,
            dep_spec=None,
            key="nope",
        )
        self.assertEqual(res["removed"], 0)

    def test_clear_dep_relation_requires_selector(self) -> None:
        parent = self._create_spec("Parent noselect")
        with self.assertRaises(SystemExit):
            self._call(
                func=self.flowctl.cmd_sync_clear_dep_relation,
                id=parent,
                dep_spec=None,
                key=None,
            )

    def test_self_edge_dep_relation_rejected(self) -> None:
        parent = self._create_spec("Parent self")
        with self.assertRaises(SystemExit):
            self._set_dep_relation(parent, parent, "node-p", "node-p")
        self.assertEqual(self._state(parent)["depRelations"], [])

    # --- list-dep-relations -------------------------------------------------

    def test_list_dep_relations_resolves_link_and_projected(self) -> None:
        parent = self._create_spec("Parent list")
        dep = self._create_spec("Dep list")
        self._add_dep(parent, dep)
        # Both endpoints must be linked for a relation to be projectable.
        self._set_id(parent, "node-parent-uuid", identifier="WOR-1")
        self._set_id(dep, "node-dep-uuid", identifier="WOR-9")
        res = self._list_dep_relations(parent)
        self.assertEqual(res["count"], 1)
        rel = res["depRelations"][0]
        self.assertEqual(rel["dep_spec"], dep)
        self.assertEqual(rel["dep_tracker_id"], "node-dep-uuid")
        self.assertEqual(rel["dep_identifier"], "WOR-9")
        self.assertEqual(rel["dep_status"], "open")  # local dep-spec status
        self.assertFalse(rel["projected"])  # not yet in the ledger
        # After recording the relation (parent→dep edge), projected flips true.
        self._set_dep_relation(parent, dep, "node-parent-uuid", "node-dep-uuid")
        rel2 = self._list_dep_relations(parent)["depRelations"][0]
        self.assertTrue(rel2["projected"])

    def test_list_dep_relations_projected_false_after_relink(self) -> None:
        # Regression (fn-64 R7): `projected` keys off the directed tracker EDGE,
        # not the dep spec id. After the dep is relinked to a DIFFERENT issue,
        # the stored ledger edge no longer matches the current resolution, so
        # projected must read false — the old edge was never projected to the
        # new issue. A dep-spec-membership check would wrongly report true.
        parent = self._create_spec("Parent relink")
        dep = self._create_spec("Dep relink")
        self._add_dep(parent, dep)
        self._set_id(parent, "node-parent-uuid", identifier="WOR-1")
        self._set_id(dep, "node-dep-uuid", identifier="WOR-9")
        self._set_dep_relation(parent, dep, "node-parent-uuid", "node-dep-uuid")
        self.assertTrue(self._list_dep_relations(parent)["depRelations"][0]["projected"])
        # Relink the dependency to a different tracker issue.
        self._set_id(dep, "node-dep-MOVED", identifier="WOR-42", force=True)
        rel = self._list_dep_relations(parent)["depRelations"][0]
        self.assertEqual(rel["dep_tracker_id"], "node-dep-MOVED")
        self.assertFalse(rel["projected"])  # stale ledger edge no longer matches

    def test_list_dep_relations_missing_link_surfaced(self) -> None:
        # A dependency spec with no tracker id resolves to dep_tracker_id=None
        # — the skill surfaces this as the missing-link warning.
        parent = self._create_spec("Parent missing")
        dep = self._create_spec("Dep missing")
        self._add_dep(parent, dep)
        rel = self._list_dep_relations(parent)["depRelations"][0]
        self.assertEqual(rel["dep_spec"], dep)
        self.assertIsNone(rel["dep_tracker_id"])
        self.assertIsNone(rel["dep_identifier"])
        self.assertEqual(rel["dep_status"], "open")

    def test_list_dep_relations_completed_blocker_status(self) -> None:
        # A `done` dependency surfaces dep_status=done (the completed-blocker
        # signal the skill keys off — local flow status, not a remote fetch).
        parent = self._create_spec("Parent done-dep")
        dep = self._create_spec("Dep done")
        self._add_dep(parent, dep)
        self._set_id(dep, "node-done", identifier="WOR-5")
        self._call(func=self.flowctl.cmd_spec_close, id=dep)
        rel = self._list_dep_relations(parent)["depRelations"][0]
        self.assertEqual(rel["dep_status"], "done")

    def test_list_dep_relations_empty_when_no_deps(self) -> None:
        parent = self._create_spec("Parent nodeps")
        res = self._list_dep_relations(parent)
        self.assertEqual(res["count"], 0)
        self.assertEqual(res["depRelations"], [])


if __name__ == "__main__":
    unittest.main()
