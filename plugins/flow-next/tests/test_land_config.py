"""R9 retained land config and legacy-file compatibility.

Retires pattern, reviewer, ledger, merge-identity and post-merge shell tests:
those mechanisms are deleted; the named-PR contract owns their replacement.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location(
        "flowctl_land_config_under_test", FLOWCTL_PY
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class LandConfigDefaultsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        scratch = HERE.parents[3] / ".flow" / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmpdir = Path(tempfile.mkdtemp(dir=scratch))
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self.flowctl = _load_flowctl()
        self.flowctl.get_repo_root = lambda: self.tmpdir
        flow_dir = self.tmpdir / ".flow"
        flow_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_config_get_cli(self, key: str, *extra: str) -> dict:
        """Invoke cmd_config_get via the argparse namespace; capture JSON stdout."""
        ns = argparse.Namespace(key=key, json=True, raw="--raw" in extra)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_get(ns)
        return json.loads(buf.getvalue())

    def _run_config_set_cli(self, key: str, value: str) -> dict:
        ns = argparse.Namespace(key=key, value=value, json=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.flowctl.cmd_config_set(ns)
        return json.loads(buf.getvalue())

    def test_r9_only_retained_defaults_and_schema_keys(self):
        expected = {"patienceMinutes": 30, "mergeVerdictCommand": ""}
        self.assertEqual(self.flowctl.get_default_config()["land"], expected)
        schema = json.loads((HERE.parents[1] / "schema/flow-config.schema.json").read_text())
        self.assertEqual(set(schema["properties"]["land"]["properties"]), set(expected))
        self.assertTrue(schema["properties"]["land"]["additionalProperties"])

    def test_r9_retired_keys_load_without_error_or_rewriting(self):
        retired = {"release": False, "reviewSignal": "approve", "automatedReviewers": "bot",
                   "reviewTrigger": "review", "ciFixBudget": 99, "cleanReviewCommentPattern": r"(Didn'?t find any( major)? issues|No( major)? issues found).*Reviewed commit",
                   "requestReviewers": "alice", "patienceMinutesAfterReview": 15}
        path = self.tmpdir / ".flow/config.json"
        path.write_text(json.dumps({"land": retired}))
        before = path.read_bytes()
        self.assertEqual(self.flowctl.load_flow_config()["land"]["patienceMinutes"], 30)
        self.assertEqual(self._run_config_get_cli("land.mergeVerdictCommand")["value"], "")
        self.assertEqual(self.flowctl.load_flow_config()["land"]["cleanReviewCommentPattern"],
                         retired["cleanReviewCommentPattern"])
        self.assertEqual(path.read_bytes(), before)

    def test_retained_keys_round_trip_without_clobbering(self):
        self._run_config_set_cli("land.patienceMinutes", "45")
        self._run_config_set_cli("land.mergeVerdictCommand", "make verdict")
        self.assertEqual(self._run_config_get_cli("land.patienceMinutes")["value"], 45)
        self.assertEqual(self._run_config_get_cli("land.mergeVerdictCommand")["value"], "make verdict")


if __name__ == "__main__":
    unittest.main()
