"""Tracker-first id generator + enumeration-vs-allocation split + no-rename
invariant (fn-52.10, R16).

Covers:
  * `spec create --tracker-first --tracker-identifier WOR-17` yields canonical
    id `wor-17-slug`, tasks `wor-17-slug.M` (via the unchanged task_id =
    spec_id.N), branch `wor-17-slug`, and stores display `tracker.identifier`.
    JSON output shape is pinned.
  * Flow-first create (no flags) is unchanged `fn-NN-slug`.
  * `--tracker-first` requires `--tracker-identifier`; a reserved `fn` key is
    rejected; a malformed identifier is rejected.
  * Enumeration-vs-allocation: a `wor-9999-foo` spec is visible to
    `iter_spec_json_files` / `list` / `specs` but does NOT bump the native
    `fn-N` allocator (`scan_max_native_fn_spec_id` is fn-only).
  * No-rename: `spec set-title` on a tracker-linked spec (tracker-key id OR a
    stored `tracker.identifier`) updates the title only — no id / branch / file
    rename. Unlinked `fn-*` specs keep today's rename.

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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_tracker_gen_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TrackerIdGeneratorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_flowctl()
        self.flow_dir = self.tmpdir / ".flow"
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

    def _create(self, title: str, **kw) -> dict:
        return self._call(
            func=self.flowctl.cmd_spec_create,
            title=title,
            branch=kw.get("branch"),
            tracker_first=kw.get("tracker_first", False),
            tracker_identifier=kw.get("tracker_identifier"),
        )

    def _spec_json(self, spec_id: str) -> dict:
        path = self.flowctl.find_spec_json_path(self.flow_dir, spec_id)
        return json.loads(path.read_text(encoding="utf-8"))

    # --- generator ----------------------------------------------------------

    def test_tracker_first_canonical_id_and_shape(self) -> None:
        res = self._create(
            "Fix login", tracker_first=True, tracker_identifier="WOR-17"
        )
        self.assertEqual(res["id"], "wor-17-fix-login")
        self.assertEqual(res["branch_name"], "wor-17-fix-login")
        self.assertEqual(res["tracker_identifier"], "WOR-17")
        # Pinned JSON shape.
        for key in ("id", "title", "spec_path", "branch_name", "message"):
            self.assertIn(key, res)
        # Display identifier persisted; canonical id carries the lowercase key.
        data = self._spec_json("wor-17-fix-login")
        self.assertEqual(data["tracker"]["identifier"], "WOR-17")
        self.assertEqual(data["branch_name"], "wor-17-fix-login")

    def test_tracker_first_task_id_uses_unchanged_generator(self) -> None:
        self._create("Fix login", tracker_first=True, tracker_identifier="WOR-17")
        res = self._call(
            func=self.flowctl.cmd_task_create,
            spec="wor-17-fix-login",
            epic=None,
            title="First step",
            deps=None,
            priority=None,
            acceptance_file=None,
        )
        # task_id = spec_id.N → wor-17-fix-login.1 (no special construction).
        self.assertEqual(res["id"], "wor-17-fix-login.1")
        self.assertEqual(res["spec"], "wor-17-fix-login")

    def test_flow_first_unchanged_fn_scheme(self) -> None:
        res = self._create("Plain flow spec")
        self.assertTrue(res["id"].startswith("fn-1-"))
        self.assertNotIn("tracker_identifier", res)

    def test_tracker_first_requires_identifier(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._create("No identifier", tracker_first=True)

    def test_reserved_fn_key_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._create(
                    "Reserved", tracker_first=True, tracker_identifier="FN-17"
                )

    def test_malformed_identifier_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                self._create(
                    "Bad id", tracker_first=True, tracker_identifier="not-a-key"
                )

    def test_tracker_first_branch_override(self) -> None:
        res = self._create(
            "Fix login",
            tracker_first=True,
            tracker_identifier="WOR-17",
            branch="custom-branch",
        )
        self.assertEqual(res["branch_name"], "custom-branch")

    # --- enumeration vs allocation -----------------------------------------

    def test_tracker_spec_visible_to_enumeration(self) -> None:
        self._create("Fix login", tracker_first=True, tracker_identifier="WOR-17")
        self._create("Plain flow")  # fn-1-plain-flow
        stems = {p.stem for p in self.flowctl.iter_spec_json_files(self.flow_dir)}
        self.assertIn("wor-17-fix-login", stems)
        self.assertIn("fn-1-plain-flow", stems)
        # `specs` lists both, sorted total-order (fn first, then tracker).
        listing = self._call(func=self.flowctl.cmd_specs)
        ids = [s["id"] for s in listing["specs"]]
        self.assertIn("wor-17-fix-login", ids)
        self.assertIn("fn-1-plain-flow", ids)
        self.assertLess(ids.index("fn-1-plain-flow"), ids.index("wor-17-fix-login"))

    def test_tracker_spec_does_not_bump_native_allocator(self) -> None:
        # A high tracker number must NOT push the next flow-first spec number.
        self._create(
            "Big tracker", tracker_first=True, tracker_identifier="WOR-9999"
        )
        self.assertEqual(
            self.flowctl.scan_max_native_fn_spec_id(self.flow_dir), 0
        )
        res = self._create("Next flow spec")
        self.assertEqual(res["id"], "fn-1-next-flow-spec")

    def test_native_allocator_counts_fn_only(self) -> None:
        self._create("First")  # fn-1
        self._create("Second tracker", tracker_first=True, tracker_identifier="WOR-50")
        self._create("Third")  # must be fn-2, not fn-51
        listing = self._call(func=self.flowctl.cmd_specs)
        ids = [s["id"] for s in listing["specs"]]
        self.assertIn("fn-1-first", ids)
        self.assertIn("fn-2-third", ids)

    # --- no-rename invariant ------------------------------------------------

    def test_set_title_no_rename_for_tracker_key_spec(self) -> None:
        self._create("Fix login", tracker_first=True, tracker_identifier="WOR-17")
        old_path = self.flow_dir / "specs" / "wor-17-fix-login.md"
        res = self._call(
            func=self.flowctl.cmd_spec_set_title,
            id="wor-17-fix-login",
            title="Completely new title",
        )
        self.assertFalse(res["renamed"])
        self.assertEqual(res["id"], "wor-17-fix-login")
        # Files / branch unchanged; only the title moved.
        self.assertTrue(old_path.exists())
        data = self._spec_json("wor-17-fix-login")
        self.assertEqual(data["title"], "Completely new title")
        self.assertEqual(data["branch_name"], "wor-17-fix-login")
        # Body H1 updated but id preserved.
        body = old_path.read_text(encoding="utf-8")
        self.assertIn("# wor-17-fix-login Completely new title", body)

    def test_set_title_no_rename_for_flow_first_with_tracker_identifier(self) -> None:
        # A flow-first fn-NN spec that carries a stored tracker.identifier is
        # also linked → no rename.
        res = self._create("Plain flow")
        spec_id = res["id"]
        self._call(
            func=self.flowctl.cmd_sync_set_tracker_id,
            id=spec_id,
            tracker_id="uuid-x",
            identifier="WOR-3",
            url=None,
            force=False,
        )
        out = self._call(
            func=self.flowctl.cmd_spec_set_title, id=spec_id, title="Renamed flow"
        )
        self.assertFalse(out["renamed"])
        self.assertEqual(out["id"], spec_id)  # id unchanged
        self.assertTrue((self.flow_dir / "specs" / f"{spec_id}.md").exists())

    def test_set_title_renames_unlinked_fn_spec(self) -> None:
        res = self._create("Original title")
        old_id = res["id"]
        out = self._call(
            func=self.flowctl.cmd_spec_set_title, id=old_id, title="Brand new title"
        )
        # Unlinked fn-* spec keeps today's rename behavior.
        self.assertEqual(out["new_id"], "fn-1-brand-new-title")
        self.assertNotEqual(out["new_id"], old_id)
        self.assertFalse((self.flow_dir / "specs" / f"{old_id}.md").exists())
        self.assertTrue(
            (self.flow_dir / "specs" / "fn-1-brand-new-title.md").exists()
        )


if __name__ == "__main__":
    unittest.main()
