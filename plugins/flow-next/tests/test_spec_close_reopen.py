"""R1/R3: committed close state and explicit task-change reopening."""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "plugins/flow-next/scripts"
sys.path.insert(0, str(ROOT / "plugins/flow-next/scripts"))


class SpecCloseReopenTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".flow/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "source"
        self.repo.mkdir()
        self.previous = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, self.previous)
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("FLOW_STATE_DIR", None)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        spec = importlib.util.spec_from_file_location(
            "flowctl_close_reopen_under_test", SCRIPTS / "flowctl.py"
        )
        self.flow = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.flow
        spec.loader.exec_module(self.flow)
        self.call("init")
        self.spec_id = self.call("spec_create", title="Close lifecycle", branch=None)["id"]
        self.spec_path = self.repo / ".flow/specs" / f"{self.spec_id}.json"

    def git(self, *args):
        return subprocess.run(["git", *args], check=True, capture_output=True, text=True)

    def call(self, name, **kwargs):
        out = io.StringIO()
        with redirect_stdout(out):
            getattr(self.flow, "cmd_" + name)(argparse.Namespace(json=True, **kwargs))
        return json.loads(out.getvalue())

    def create(self, title="Task"):
        return self.call("task_create", spec=self.spec_id, epic=None, title=title,
                         priority=None, deps=None, acceptance_file=None)["id"]

    def closed(self):
        task = self.create()
        self.flow.save_task_runtime(task, {"status": "done"})
        self.call("spec_close", id=self.spec_id)
        return task

    def status(self):
        return json.loads(self.spec_path.read_text(encoding="utf-8"))["status"]

    def snapshot(self):
        return {str(p.relative_to(self.repo)): p.read_bytes()
                for p in self.repo.rglob("*") if p.is_file()}

    def test_r1_close_persists_every_task_and_fresh_clone_consumers(self):
        tasks = [self.create("First"), self.create("Second")]
        for task in tasks:
            self.flow.save_task_runtime(task, {"status": "done", "assignee": "local"})
        # A task already committed done has no local runtime state at all.
        committed_task = self.create("Already committed")
        committed_path = self.repo / ".flow/tasks" / f"{committed_task}.json"
        committed = json.loads(committed_path.read_text(encoding="utf-8"))
        committed["status"] = "done"
        committed_path.write_text(json.dumps(committed))
        tasks.append(committed_task)
        self.call("spec_close", id=self.spec_id)
        self.git("add", ".flow")
        self.git("commit", "-qm", "Closed spec")
        clone = Path(self.temp.name) / "clone"
        self.git("clone", "-q", str(self.repo), str(clone))
        os.chdir(clone)
        self.assertFalse((clone / ".git/flow-state").exists())
        for task in tasks:
            stored = json.loads((clone / ".flow/tasks" / f"{task}.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["status"], "done")
            self.assertNotEqual(stored.get("assignee"), "local")
        shown = self.call("show", id=self.spec_id)
        self.assertEqual([t["status"] for t in shown["tasks"]], ["done"] * 3)
        listed = self.call("specs")["specs"][0]
        self.assertEqual((listed["tasks"], listed["done"]), (3, 3))
        validated = self.call("validate", spec=self.spec_id, epic=None, all=False)
        self.assertTrue(validated["valid"])
        exported = self.call("spec_export_cognitive_aid", id=self.spec_id, base="HEAD")
        self.assertEqual(exported["tasks_summary"]["done"], 3)
        self.assertEqual(exported["tasks_summary"]["open"], 0)

    def test_r1_incomplete_close_changes_no_file(self):
        done = self.create("Done")
        incomplete = self.create("Incomplete")
        self.flow.save_task_runtime(done, {"status": "done"})
        before = self.snapshot()
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            self.flow.cmd_spec_close(argparse.Namespace(id=self.spec_id, json=True))
        self.assertNotEqual(raised.exception.code, 0)
        self.assertIn(incomplete, json.loads(out.getvalue())["error"])
        self.assertEqual(self.snapshot(), before)

    def test_close_reports_only_rewritten_paths_including_legacy_spec(self):
        changed, unchanged = self.create("Changed"), self.create("Already done")
        task_path = self.repo / ".flow/tasks" / f"{unchanged}.json"
        data = json.loads(task_path.read_text(encoding="utf-8"))
        data["status"] = "done"
        task_path.write_text(json.dumps(data))
        before = task_path.read_bytes()
        legacy = self.repo / ".flow/epics" / self.spec_path.name
        legacy.parent.mkdir()
        self.spec_path.rename(legacy)
        self.flow.save_task_runtime(changed, {"status": "done"})
        result = self.call("spec_close", id=self.spec_id)
        self.assertEqual(set(result["modified_paths"]), {
            str(legacy), str(self.repo / ".flow/tasks" / f"{changed}.json")})
        self.assertEqual(task_path.read_bytes(), before)

    def test_plain_close_advises_about_each_tracked_write(self):
        task = self.create()
        self.git("add", ".flow")
        self.git("commit", "-qm", "Before close")
        self.flow.save_task_runtime(task, {"status": "done"})
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.flow.cmd_spec_close(argparse.Namespace(id=self.spec_id, json=False))
        self.assertIn(f".flow/specs/{self.spec_id}.json", err.getvalue())
        self.assertIn(f".flow/tasks/{task}.json", err.getvalue())
        self.assertEqual(len(err.getvalue().splitlines()), 2)

    def test_start_without_spec_or_epic_fails_before_any_write(self):
        task = self.create()
        path = self.repo / ".flow/tasks" / f"{task}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("spec", None)
        data.pop("epic", None)
        path.write_text(json.dumps(data))
        before = self.snapshot()
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            self.flow.cmd_start(argparse.Namespace(id=task, json=True, force=False, note=None))
        self.assertIn("neither spec nor epic", json.loads(out.getvalue())["error"])
        self.assertEqual(self.snapshot(), before)

    def test_r1_runtime_state_overrides_committed_done(self):
        task = self.closed()
        # Emulate an existing committed completion in an older clone, too.
        path = self.repo / ".flow/tasks" / f"{task}.json"
        stored = json.loads(path.read_text(encoding="utf-8"))
        stored["status"] = "done"
        path.write_text(json.dumps(stored))
        self.flow.save_task_runtime(task, {"status": "todo"})
        self.assertEqual(self.call("show", id=task)["status"], "todo")
        self.assertEqual(self.call("specs")["specs"][0]["done"], 0)
        before = self.snapshot()
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            self.flow.cmd_spec_close(argparse.Namespace(id=self.spec_id, json=True))
        self.assertIn("incomplete tasks", json.loads(out.getvalue())["error"])
        self.assertEqual(self.snapshot(), before)

    def test_r3_single_create_reopens_closed_spec(self):
        self.closed()
        self.create("Follow-up")
        self.assertEqual(self.status(), "open")

    def test_r3_reopen_reports_the_spec_file_it_rewrote(self):
        # A caller that commits only the new task would leave `done` at the
        # head; the reopen names its write the way close does.
        self.closed()
        out = self.call("task_create", spec=self.spec_id, epic=None, title="Follow-up",
                        priority=None, deps=None, acceptance_file=None)
        self.assertEqual(out["reopened_spec"], self.spec_id)
        self.assertEqual(out["modified_paths"], [str(self.spec_path)])
        again = self.call("task_create", spec=self.spec_id, epic=None, title="Second",
                          priority=None, deps=None, acceptance_file=None)
        self.assertNotIn("reopened_spec", again)
        self.assertNotIn("modified_paths", again)

    def test_r3_bulk_create_reopens_closed_spec(self):
        self.closed()
        bulk = self.repo / ".flow/tmp/bulk.json"
        bulk.parent.mkdir(parents=True, exist_ok=True)
        bulk.write_text(json.dumps([{"title": "One"}, {"title": "Two"}]))
        self.call("task_create", spec=self.spec_id, epic=None, from_json=str(bulk))
        self.assertEqual(self.status(), "open")

    def test_r3_start_reopens_closed_spec(self):
        task = self.closed()
        self.flow.save_task_runtime(task, {"status": "todo"})
        self.call("start", id=task, force=False, note=None)
        self.assertEqual(self.status(), "open")

    def test_r3_completing_followup_keeps_spec_open_until_explicit_close(self):
        self.closed()
        task = self.create("Follow-up")
        self.call("start", id=task, force=False, note=None)
        self.call("done", id=task, force=False, summary="Finished follow-up",
                  summary_file=None, evidence=None, evidence_json=None)
        self.assertEqual(self.status(), "open")
        self.call("spec_close", id=self.spec_id)
        self.assertEqual(self.status(), "done")

    def test_r3_no_task_change_keeps_closed_spec_unchanged(self):
        self.closed()
        before = self.spec_path.read_bytes()
        self.call("show", id=self.spec_id)
        self.call("specs")
        self.assertEqual(self.status(), "done")
        self.assertEqual(self.spec_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
