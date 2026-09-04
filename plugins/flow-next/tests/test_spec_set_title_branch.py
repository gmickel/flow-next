"""``spec set-title`` re-derives the default ``branch_name`` on rename.

``branch_name`` defaults to the spec id at create time. Renaming the spec used
to leave it at the old slug, which silently broke land's PR discovery and
autonomous work's branch naming (observed on fn-218 / PR #395). A rename now
moves a still-default ``branch_name`` to the new id and keeps an explicit
``set-branch`` value untouched. Routes through production argparse.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_spec_set_title_branch_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


class TestSpecSetTitleBranch(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.root, check=True, capture_output=True
        )
        code, out, err = self._run("init", "--json")
        self.assertEqual(code, 0, err or out)
        code, out, err = self._run(
            "spec", "create", "--title", "Old title here", "--json"
        )
        self.assertEqual(code, 0, err or out)
        self.spec_id = json.loads(out)["id"]

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _run(self, *argv: str) -> "tuple[int, str, str]":
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["flowctl", *argv]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    flowctl.main()
                except SystemExit as e:
                    code = int(e.code or 0)
        return code, out.getvalue(), err.getvalue()

    def _spec_json(self, spec_id: str) -> dict:
        return json.loads(
            (self.root / ".flow" / "specs" / f"{spec_id}.json").read_text(
                encoding="utf-8"
            )
        )

    def test_default_branch_name_follows_rename(self) -> None:
        self.assertEqual(self._spec_json(self.spec_id)["branch_name"], self.spec_id)
        code, out, err = self._run(
            "spec", "set-title", self.spec_id, "--title", "New title now", "--json"
        )
        self.assertEqual(code, 0, err or out)
        result = json.loads(out)
        new_id = result["new_id"]
        self.assertNotEqual(new_id, self.spec_id)
        self.assertTrue(result["branch_rederived"])
        self.assertEqual(result["branch_name"], new_id)
        self.assertEqual(self._spec_json(new_id)["branch_name"], new_id)

    def test_explicit_branch_name_survives_rename(self) -> None:
        code, out, err = self._run(
            "spec", "set-branch", self.spec_id, "--branch", "feat/custom", "--json"
        )
        self.assertEqual(code, 0, err or out)
        code, out, err = self._run(
            "spec", "set-title", self.spec_id, "--title", "New title now", "--json"
        )
        self.assertEqual(code, 0, err or out)
        result = json.loads(out)
        self.assertFalse(result["branch_rederived"])
        self.assertEqual(result["branch_name"], "feat/custom")
        self.assertEqual(self._spec_json(result["new_id"])["branch_name"], "feat/custom")


if __name__ == "__main__":
    unittest.main()
