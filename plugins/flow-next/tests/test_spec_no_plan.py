"""Spec no_plan flag tests (fn-214, R1).

Asserts the lazy on-disk / explicit-in-output contract:
  * `spec create` never writes the `no_plan` key (lazy purity) and
    `normalize_epic` does NOT backfill it.
  * All three JSON read surfaces (`show`, `specs`, `list`) emit an explicit
    `"no_plan": false` for a never-toggled spec.
  * `ready --all` backlog rows carry `noPlan` (camelCase) as an explicit
    boolean; absent key reads false.
  * `spec set-no-plan` / `spec clear-no-plan` toggle the flag and are
    idempotent no-ops (no write, no `updated_at` bump, sidecar byte-identical)
    when the value already matches — incl. `clear-no-plan` on a never-toggled
    spec (no key materialized).
  * SETTING is refused once the spec has any tasks; CLEARING is always
    allowed (stale-field cleanup), including on specs with tasks.
  * Unknown sidecar keys survive a toggle round-trip.
  * `.M` task ids are rejected with a targeted error.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_spec_no_plan.py" -v
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

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class SpecNoPlanTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self.flowctl = _load_module("flowctl_spec_no_plan_under_test", FLOWCTL_PY)
        self._call(func=self.flowctl.cmd_init)
        self.spec_id = self._call(
            func=self.flowctl.cmd_spec_create, title="No-plan subject", branch=None
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

    def _sidecar(self) -> dict:
        return json.loads(self.spec_path.read_text(encoding="utf-8"))

    def test_create_writes_no_no_plan_key(self) -> None:
        self.assertTrue(self.spec_path.exists())
        self.assertNotIn("no_plan", self._sidecar())

    def test_normalize_epic_does_not_backfill_no_plan(self) -> None:
        normalized = self.flowctl.normalize_epic(self._sidecar())
        self.assertNotIn("no_plan", normalized)

    def test_json_surfaces_emit_explicit_false(self) -> None:
        show = self._call(func=self.flowctl.cmd_show, id=self.spec_id)
        self.assertIn("no_plan", show)
        self.assertIs(show["no_plan"], False)

        specs = self._call(func=self.flowctl.cmd_specs)
        (entry,) = [e for e in specs["specs"] if e["id"] == self.spec_id]
        self.assertIn("no_plan", entry)
        self.assertIs(entry["no_plan"], False)

        listed = self._call(func=self.flowctl.cmd_list)
        (entry,) = [e for e in listed["specs"] if e["id"] == self.spec_id]
        self.assertIn("no_plan", entry)
        self.assertIs(entry["no_plan"], False)

    def test_ready_all_rows_carry_no_plan(self) -> None:
        out = self._call(
            func=self.flowctl.cmd_ready, all=True, spec=None, epic=None
        )
        (row,) = [r for r in out["specs"] if r["id"] == self.spec_id]
        self.assertIn("noPlan", row)
        self.assertIs(row["noPlan"], False)

        self._call(func=self.flowctl.cmd_spec_set_no_plan, id=self.spec_id)
        out = self._call(
            func=self.flowctl.cmd_ready, all=True, spec=None, epic=None
        )
        (row,) = [r for r in out["specs"] if r["id"] == self.spec_id]
        self.assertIs(row["noPlan"], True)

    def test_set_clear_round_trip(self) -> None:
        res = self._call(func=self.flowctl.cmd_spec_set_no_plan, id=self.spec_id)
        self.assertIs(res["no_plan"], True)
        self.assertIs(res["changed"], True)
        self.assertIs(self._sidecar()["no_plan"], True)

        show = self._call(func=self.flowctl.cmd_show, id=self.spec_id)
        self.assertIs(show["no_plan"], True)

        res = self._call(func=self.flowctl.cmd_spec_clear_no_plan, id=self.spec_id)
        self.assertIs(res["no_plan"], False)
        self.assertIs(res["changed"], True)
        self.assertIs(self._sidecar()["no_plan"], False)

    def test_set_twice_is_byte_identical_noop(self) -> None:
        self._call(func=self.flowctl.cmd_spec_set_no_plan, id=self.spec_id)
        before = self.spec_path.read_bytes()
        updated_at = self._sidecar()["updated_at"]

        res = self._call(func=self.flowctl.cmd_spec_set_no_plan, id=self.spec_id)
        self.assertIs(res["changed"], False)
        self.assertIn("(no change)", res["message"])
        self.assertEqual(self.spec_path.read_bytes(), before)
        self.assertEqual(self._sidecar()["updated_at"], updated_at)

    def test_clear_on_never_set_spec_is_byte_identical_noop(self) -> None:
        before = self.spec_path.read_bytes()
        res = self._call(func=self.flowctl.cmd_spec_clear_no_plan, id=self.spec_id)
        self.assertIs(res["no_plan"], False)
        self.assertIs(res["changed"], False)
        self.assertEqual(self.spec_path.read_bytes(), before)
        self.assertNotIn("no_plan", self._sidecar())

    def test_set_refused_when_tasks_exist(self) -> None:
        self._call(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title="Task",
            priority=None,
            deps=None,
            acceptance_file=None,
        )
        ns = argparse.Namespace(id=self.spec_id, json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.flowctl.cmd_spec_set_no_plan(ns)
        self.assertNotEqual(ctx.exception.code, 0)
        err = json.loads(buf.getvalue().strip())
        self.assertFalse(err["success"])
        self.assertIn("already has tasks", err["error"])

    def test_clear_allowed_when_tasks_exist(self) -> None:
        self._call(func=self.flowctl.cmd_spec_set_no_plan, id=self.spec_id)
        self._call(
            func=self.flowctl.cmd_task_create,
            spec=self.spec_id,
            epic=None,
            title="Task",
            priority=None,
            deps=None,
            acceptance_file=None,
        )
        res = self._call(func=self.flowctl.cmd_spec_clear_no_plan, id=self.spec_id)
        self.assertIs(res["no_plan"], False)
        self.assertIs(res["changed"], True)
        self.assertIs(self._sidecar()["no_plan"], False)

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
                self.flowctl.cmd_spec_set_no_plan(ns)
        self.assertNotEqual(ctx.exception.code, 0)
        err = json.loads(buf.getvalue().strip())
        self.assertFalse(err["success"])
        self.assertIn("spec-level", err["error"])
        self.assertIn("not a task id", err["error"])

    def test_unknown_sidecar_keys_survive_toggle(self) -> None:
        data = self._sidecar()
        data["x_custom_extension"] = {"keep": "me"}
        self.spec_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self._call(func=self.flowctl.cmd_spec_set_no_plan, id=self.spec_id)
        after = self._sidecar()
        self.assertEqual(after["x_custom_extension"], {"keep": "me"})
        self.assertIs(after["no_plan"], True)


if __name__ == "__main__":
    unittest.main()
