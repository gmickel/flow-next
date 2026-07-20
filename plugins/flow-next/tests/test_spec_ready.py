"""Spec readiness flag tests (fn-58.1, R1 + R2 + R7).

Asserts the lazy on-disk / explicit-in-output contract:
  * `spec create` never writes the `ready` key (lazy purity — R7 invisibility,
    zero working-tree churn for non-adopters) and `normalize_epic` does NOT
    backfill it (that would defeat lazy purity on the next write).
  * All three JSON read surfaces (`show`, `specs`, `list`) emit an explicit
    `"ready": false` for a never-toggled spec — consumers (fn-59's selector)
    always see a stable boolean, never an absent key.
  * `spec ready` / `spec unready` toggle the flag and are idempotent no-ops
    (no write, no `updated_at` bump, sidecar byte-identical) when the value
    already matches — incl. `unready` on a never-toggled spec.
  * Unknown sidecar keys survive a toggle round-trip.
  * `.M` task ids are rejected with a targeted error; tracker handles resolve
    via the central front-door; `done` specs are allowed (status-orthogonal).
  * The human listings badge `[ready]` appears ONLY on ready specs.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_spec_ready.py" -v
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


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class SpecReadyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_module("flowctl_spec_ready_under_test", FLOWCTL_PY)
        self._call(func=self.flowctl.cmd_init)
        self.spec_id = self._call(
            func=self.flowctl.cmd_spec_create, title="Readiness subject", branch=None
        )["id"]
        self.spec_path = self.tmpdir / ".flow" / "specs" / f"{self.spec_id}.json"

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _call(self, *, func, **kwargs) -> dict:
        kwargs.setdefault("json", True)
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def _human(self, *, func, **kwargs) -> str:
        """Invoke a command in human (non-JSON) mode, returning stdout."""
        kwargs["json"] = False
        ns = argparse.Namespace(**kwargs)
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(ns)
        return buf.getvalue()

    def _sidecar(self) -> dict:
        return json.loads(self.spec_path.read_text(encoding="utf-8"))

    # --- lazy on-disk purity (R1 / R7) ---------------------------------------

    def test_create_writes_no_ready_key(self) -> None:
        self.assertTrue(self.spec_path.exists())
        self.assertNotIn("ready", self._sidecar())

    def test_normalize_epic_does_not_backfill_ready(self) -> None:
        # Backfilling would defeat lazy purity on the NEXT write — any
        # normalize→write path would materialize the key for non-adopters.
        normalized = self.flowctl.normalize_epic(self._sidecar())
        self.assertNotIn("ready", normalized)

    def test_all_three_json_surfaces_emit_explicit_false(self) -> None:
        show = self._call(func=self.flowctl.cmd_show, id=self.spec_id)
        self.assertIn("ready", show)
        self.assertIs(show["ready"], False)

        specs = self._call(func=self.flowctl.cmd_specs)
        (entry,) = [e for e in specs["specs"] if e["id"] == self.spec_id]
        self.assertIn("ready", entry)
        self.assertIs(entry["ready"], False)

        listed = self._call(func=self.flowctl.cmd_list)
        (entry,) = [e for e in listed["specs"] if e["id"] == self.spec_id]
        self.assertIn("ready", entry)
        self.assertIs(entry["ready"], False)

    # --- toggle round-trip (R2) ----------------------------------------------

    def test_ready_unready_round_trip(self) -> None:
        res = self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)
        self.assertIs(res["ready"], True)
        self.assertIs(res["changed"], True)
        self.assertIs(self._sidecar()["ready"], True)

        show = self._call(func=self.flowctl.cmd_show, id=self.spec_id)
        self.assertIs(show["ready"], True)
        specs = self._call(func=self.flowctl.cmd_specs)
        (entry,) = [e for e in specs["specs"] if e["id"] == self.spec_id]
        self.assertIs(entry["ready"], True)
        listed = self._call(func=self.flowctl.cmd_list)
        (entry,) = [e for e in listed["specs"] if e["id"] == self.spec_id]
        self.assertIs(entry["ready"], True)

        res = self._call(func=self.flowctl.cmd_spec_unready, id=self.spec_id)
        self.assertIs(res["ready"], False)
        self.assertIs(res["changed"], True)
        self.assertIs(self._sidecar()["ready"], False)
        show = self._call(func=self.flowctl.cmd_show, id=self.spec_id)
        self.assertIs(show["ready"], False)

    # --- idempotent no-ops ----------------------------------------------------

    def test_ready_twice_is_byte_identical_noop(self) -> None:
        self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)
        before = self.spec_path.read_bytes()
        updated_at = self._sidecar()["updated_at"]

        res = self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)
        self.assertIs(res["changed"], False)
        self.assertIn("(no change)", res["message"])
        self.assertEqual(self.spec_path.read_bytes(), before)
        self.assertEqual(self._sidecar()["updated_at"], updated_at)

    def test_unready_on_never_ready_spec_is_byte_identical_noop(self) -> None:
        # The load-bearing no-op: unconditional `unready` callers (capture
        # --rewrite) must not turn a non-adopter spec into a readiness
        # adopter — no key materialized, no updated_at churn.
        before = self.spec_path.read_bytes()
        res = self._call(func=self.flowctl.cmd_spec_unready, id=self.spec_id)
        self.assertIs(res["ready"], False)
        self.assertIs(res["changed"], False)
        self.assertEqual(self.spec_path.read_bytes(), before)
        self.assertNotIn("ready", self._sidecar())

    def test_unready_on_explicit_false_is_byte_identical_noop(self) -> None:
        self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)
        self._call(func=self.flowctl.cmd_spec_unready, id=self.spec_id)
        self.assertIs(self._sidecar()["ready"], False)
        before = self.spec_path.read_bytes()
        res = self._call(func=self.flowctl.cmd_spec_unready, id=self.spec_id)
        self.assertIs(res["changed"], False)
        self.assertEqual(self.spec_path.read_bytes(), before)

    # --- unknown-key round-trip ------------------------------------------------

    def test_unknown_sidecar_keys_survive_toggle(self) -> None:
        data = self._sidecar()
        data["x_custom_extension"] = {"keep": "me"}
        self.spec_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)
        after = self._sidecar()
        self.assertEqual(after["x_custom_extension"], {"keep": "me"})
        self.assertIs(after["ready"], True)

    # --- id handling -----------------------------------------------------------

    def test_task_id_rejected_with_targeted_error(self) -> None:
        self._call(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title="Task",
            priority=None,
            deps=None,
            acceptance_file=None,
        )
        ns = argparse.Namespace(id=f"{self.spec_id}.1", json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.flowctl.cmd_spec_ready(ns)
        self.assertNotEqual(ctx.exception.code, 0)
        err = json.loads(buf.getvalue().strip())
        self.assertFalse(err["success"])
        self.assertIn("spec-level", err["error"])
        self.assertIn("not a task id", err["error"])

    def test_tracker_handle_resolves_via_front_door(self) -> None:
        created = self._call(
            func=self.flowctl.cmd_spec_create,
            title="Tracker first",
            branch=None,
            tracker_first=True,
            tracker_identifier="TST-7",
        )
        res = self._call(func=self.flowctl.cmd_spec_ready, id="TST-7")
        self.assertEqual(res["id"], created["id"])
        self.assertIs(res["ready"], True)
        sidecar = json.loads(
            (self.tmpdir / ".flow" / "specs" / f"{created['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIs(sidecar["ready"], True)

    def test_done_spec_allowed(self) -> None:
        # Readiness is status-orthogonal: a closed spec can still be toggled.
        self._call(func=self.flowctl.cmd_spec_close, id=self.spec_id)
        self.assertEqual(self._sidecar()["status"], "done")
        res = self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)
        self.assertIs(res["ready"], True)
        self.assertEqual(self._sidecar()["status"], "done")

    # --- badge (R2 / R7) --------------------------------------------------------

    def test_badge_only_on_ready_specs(self) -> None:
        other_id = self._call(
            func=self.flowctl.cmd_spec_create, title="Still draft", branch=None
        )["id"]
        self._call(func=self.flowctl.cmd_spec_ready, id=self.spec_id)

        specs_out = self._human(func=self.flowctl.cmd_specs)
        ready_line = next(l for l in specs_out.splitlines() if self.spec_id in l)
        draft_line = next(l for l in specs_out.splitlines() if other_id in l)
        self.assertIn("[ready]", ready_line)
        self.assertNotIn("[ready]", draft_line)

        list_out = self._human(func=self.flowctl.cmd_list)
        ready_line = next(l for l in list_out.splitlines() if self.spec_id in l)
        draft_line = next(l for l in list_out.splitlines() if other_id in l)
        self.assertIn("[ready]", ready_line)
        self.assertNotIn("[ready]", draft_line)

    def test_no_badge_anywhere_for_non_adopters(self) -> None:
        # R7: a repo that never toggled readiness sees zero badge noise.
        self.assertNotIn("[ready]", self._human(func=self.flowctl.cmd_specs))
        self.assertNotIn("[ready]", self._human(func=self.flowctl.cmd_list))

    # --- epic aliases -------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
