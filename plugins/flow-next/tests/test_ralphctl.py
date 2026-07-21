"""fn-114.2/.3 - ralphctl.py template owns Ralph run control (pause/resume/stop/status).

Pins:
  * template ships under flow-next-ralph-init/templates/ralphctl.py
  * find_active_runs uses key=value progress contract; excludes
    promise=COMPLETE + completion_reason= pairs
  * pause/resume/stop write/remove PAUSE and STOP sentinels
  * multi-run without --run errors
  * flowctl.py has no cmd_ralph_* / find_active_runs; soft-probe remains
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
RALPHCTL_PY = (
    PLUGIN_DIR
    / "skills"
    / "flow-next-ralph-init"
    / "templates"
    / "ralphctl.py"
)
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRalphctlTemplate(unittest.TestCase):
    def test_template_exists(self) -> None:
        self.assertTrue(RALPHCTL_PY.is_file(), f"missing {RALPHCTL_PY}")

    def test_flowctl_has_no_ralph_control(self) -> None:
        src = FLOWCTL_PY.read_text(encoding="utf-8")
        self.assertNotIn("def cmd_ralph_", src)
        self.assertNotIn("def find_active_runs", src)
        self.assertNotIn('add_parser("ralph"', src)
        self.assertIn("def soft_probe_active_runs", src)
        self.assertIn("stamp_ralph_iteration", src)


class TestRalphctlCommands(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.runs = self.root / "scripts" / "ralph" / "runs"
        self.runs.mkdir(parents=True)
        # Point git root resolution at the temp dir.
        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        self.mod = _load_module("ralphctl_under_test", RALPHCTL_PY)
        self._cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def _write_progress(self, run_id: str, body: str) -> Path:
        run_dir = self.runs / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        progress = run_dir / "progress.txt"
        progress.write_text(body, encoding="utf-8")
        return run_dir

    def test_find_active_runs_and_completion_markers(self) -> None:
        self._write_progress(
            "active",
            "iteration=2\nspec=fn-1-x\ntask=fn-1-x.1\npromise=RETRY\n",
        )
        self._write_progress(
            "done",
            "iteration=9\npromise=RETRY\n\ncompletion_reason=DONE\npromise=COMPLETE\n",
        )
        runs = self.mod.find_active_runs()
        ids = sorted(r["id"] for r in runs)
        self.assertEqual(ids, ["active"])
        self.assertEqual(runs[0]["iteration"], 2)
        self.assertEqual(runs[0]["current_epic"], "fn-1-x")
        self.assertEqual(runs[0]["current_task"], "fn-1-x.1")

    def test_parse_progress_kv_ignores_prose(self) -> None:
        kv = self.mod.parse_progress_kv(
            "## header\niteration=3\nlast_output:\nsome free text\npromise=RETRY\n"
        )
        self.assertEqual(kv.get("iteration"), "3")
        self.assertEqual(kv.get("promise"), "RETRY")
        self.assertNotIn("last_output", kv)

    def test_pause_resume_stop(self) -> None:
        run_dir = self._write_progress("r1", "iteration=1\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.main(["pause", "--run", "r1"])
        self.assertTrue((run_dir / "PAUSE").is_file())
        with redirect_stdout(buf):
            self.mod.main(["resume", "--run", "r1"])
        self.assertFalse((run_dir / "PAUSE").exists())
        with redirect_stdout(buf):
            self.mod.main(["stop", "--run", "r1"])
        self.assertTrue((run_dir / "STOP").is_file())

    def test_status_json(self) -> None:
        self._write_progress("r1", "iteration=3\ntask=fn-2.1\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.main(["status", "--run", "r1", "--json"])
        data = json.loads(buf.getvalue())
        self.assertTrue(data["success"])
        self.assertEqual(data["run"], "r1")
        self.assertEqual(data["iteration"], 3)
        self.assertEqual(data["current_task"], "fn-2.1")
        self.assertFalse(data["paused"])

    def test_multi_run_requires_run_flag(self) -> None:
        self._write_progress("a", "iteration=1\n")
        self._write_progress("b", "iteration=1\n")
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.mod.main(["pause"])
        self.assertNotEqual(ctx.exception.code, 0)


class TestSoftProbeStatus(unittest.TestCase):
    """flowctl status soft-probes runs/ only when present."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_module("flowctl_soft_probe", FLOWCTL_PY)

    def test_soft_probe_absent_dir_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(
                ["git", "init", "-q"], cwd=root, check=True, capture_output=True
            )
            with mock.patch.object(self.flowctl, "get_repo_root", return_value=root):
                self.assertFalse(self.flowctl._ralph_runs_dir_present())
                self.assertEqual(self.flowctl.soft_probe_active_runs(), [])

    def test_soft_probe_present_dir_reads_progress(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(
                ["git", "init", "-q"], cwd=root, check=True, capture_output=True
            )
            run = root / "scripts" / "ralph" / "runs" / "live"
            run.mkdir(parents=True)
            (run / "progress.txt").write_text(
                "iteration=4\nspec=fn-9\ntask=fn-9.2\n", encoding="utf-8"
            )
            with mock.patch.object(self.flowctl, "get_repo_root", return_value=root):
                self.assertTrue(self.flowctl._ralph_runs_dir_present())
                runs = self.flowctl.soft_probe_active_runs()
                self.assertEqual(len(runs), 1)
                self.assertEqual(runs[0]["id"], "live")
                self.assertEqual(runs[0]["iteration"], 4)
                self.assertEqual(runs[0]["current_epic"], "fn-9")
                self.assertEqual(runs[0]["current_task"], "fn-9.2")

    def test_soft_probe_excludes_complete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(
                ["git", "init", "-q"], cwd=root, check=True, capture_output=True
            )
            run = root / "scripts" / "ralph" / "runs" / "done"
            run.mkdir(parents=True)
            (run / "progress.txt").write_text(
                "completion_reason=DONE\npromise=COMPLETE\n", encoding="utf-8"
            )
            with mock.patch.object(self.flowctl, "get_repo_root", return_value=root):
                self.assertEqual(self.flowctl.soft_probe_active_runs(), [])


if __name__ == "__main__":
    unittest.main()
