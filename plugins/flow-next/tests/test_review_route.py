"""Behavioral tests for `flowctl review-route` (PR #392).

The verb replaces the agent-executed bash gates in the impl-review workflows:
canonical task id, repo/scope-keyed receipt path, receipt identity + verdict
routing, stale-receipt rotation, and the task-mode ledger fences. Every rule
the prose used to carry is pinned here, once.
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


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    spec = importlib.util.spec_from_file_location(
        "flowctl_review_route_under_test", here.parent.parent / "scripts" / "flowctl.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


class TestReviewRoute(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        flow = self.root / ".flow"
        (flow / "specs").mkdir(parents=True)
        (flow / "tasks").mkdir(parents=True)
        self.spec_id = "fn-1-demo"
        self.task_id = f"{self.spec_id}.1"
        (flow / "specs" / f"{self.spec_id}.json").write_text(
            json.dumps({"id": self.spec_id, "title": "Demo", "status": "in_progress"})
        )
        (flow / "specs" / f"{self.spec_id}.md").write_text("# Demo\n")
        (flow / "tasks" / f"{self.task_id}.json").write_text(
            json.dumps({"id": self.task_id, "title": "Task 1", "status": "todo"})
        )
        (flow / "tasks" / f"{self.task_id}.md").write_text("# Task 1\n")
        for argv in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "t@example.com"],
            ["config", "user.name", "t"],
        ):
            subprocess.run(["git", *argv], cwd=self.root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (self.root / "app.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.root, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self._cwd)
        self._env = os.environ.pop("REVIEW_RECEIPT_PATH", None)
        if self._env is not None:
            self.addCleanup(os.environ.__setitem__, "REVIEW_RECEIPT_PATH", self._env)

    # -- harness -----------------------------------------------------------

    def _route(self, *argv: str) -> tuple[int, dict, str]:
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["flowctl", "review-route", *argv, "--json"]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    flowctl.main()
                except SystemExit as exc:
                    code = int(exc.code or 0)
        payload = json.loads(out.getvalue()) if out.getvalue().strip() else {}
        return code, payload, err.getvalue()

    def _spec(self) -> dict:
        return json.loads((self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text())

    def _write_spec(self, data: dict) -> None:
        (self.root / ".flow" / "specs" / f"{self.spec_id}.json").write_text(json.dumps(data))

    def _receipt(self, path: Path, **fields: Any) -> Path:
        base = {
            "type": "impl_review", "id": self.task_id, "mode": "codex",
            "verdict": "NEEDS_WORK", "session_id": "sess", "review": "prior text",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        base.update(fields)
        path.write_text(json.dumps(base))
        return path

    # -- path derivation ---------------------------------------------------

    def test_default_path_is_repo_and_scope_keyed(self) -> None:
        code, task, err = self._route(self.task_id)
        self.assertEqual(code, 0, err)
        self.assertTrue(task["receipt_path"].startswith("/tmp/impl-review-receipt-"))
        self.assertTrue(task["receipt_path"].endswith(f"-{self.task_id}.json"))
        code, standalone, err = self._route()
        self.assertEqual(code, 0, err)
        self.assertIn("-branch-", standalone["receipt_path"])
        self.assertTrue(standalone["standalone"])
        self.assertEqual(standalone["scope_id"], "branch")
        # Same repo tag for both scopes; different scopes.
        repo_tag = task["receipt_path"].split("-")[3]
        self.assertIn(repo_tag, standalone["receipt_path"])
        self.assertNotEqual(task["receipt_path"], standalone["receipt_path"])

    def test_standalone_path_hashes_exact_ref_and_is_stable_when_detached(self) -> None:
        code, a, _ = self._route()
        subprocess.run(["git", "checkout", "-q", "-b", "feature/foo"], cwd=self.root, check=True)
        code, b, _ = self._route()
        subprocess.run(["git", "checkout", "-q", "-b", "feature-foo"], cwd=self.root, check=True)
        code, c, _ = self._route()
        self.assertNotEqual(b["receipt_path"], c["receipt_path"])
        self.assertNotEqual(a["receipt_path"], b["receipt_path"])
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root,
                              capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "checkout", "-q", head], cwd=self.root, check=True)
        code, d1, _ = self._route()
        (self.root / "app.py").write_text("x = 2\n")
        subprocess.run(["git", "commit", "-qam", "fix"], cwd=self.root, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        code, d2, _ = self._route()
        self.assertTrue(d1["receipt_path"].endswith("branch-detached.json"))
        self.assertEqual(d1["receipt_path"], d2["receipt_path"])

    def test_explicit_and_env_receipt_paths_win(self) -> None:
        code, r, _ = self._route(self.task_id, "--receipt", "/tmp/explicit.json")
        self.assertEqual(r["receipt_path"], "/tmp/explicit.json")
        with mock.patch.dict(os.environ, {"REVIEW_RECEIPT_PATH": "/tmp/env.json"}):
            code, r, _ = self._route(self.task_id)
        self.assertEqual(r["receipt_path"], "/tmp/env.json")

    def test_short_handle_canonicalizes(self) -> None:
        code, r, err = self._route("fn-1.1")
        self.assertEqual(code, 0, err)
        self.assertEqual(r["task_id"], self.task_id)
        self.assertTrue(r["receipt_path"].endswith(f"-{self.task_id}.json"))

    # -- receipt routing ---------------------------------------------------

    def test_open_receipt_routes_to_fix_then_rereview(self) -> None:
        receipt = self._receipt(self.root / "r.json")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt), "--rotate-stale")
        self.assertEqual(r["action"], "fix-then-rereview")
        self.assertEqual(r["receipt_state"], "open")
        self.assertTrue(receipt.exists(), "an open receipt is never rotated")

    def test_closed_receipt_fans_out_and_rotates_only_when_asked(self) -> None:
        receipt = self._receipt(self.root / "r.json", verdict="SHIP")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt))
        self.assertEqual(r["action"], "fanout")
        self.assertEqual(r["receipt_state"], "closed")
        self.assertIsNone(r["rotated_to"])
        self.assertTrue(receipt.exists(), "pure call must not rotate")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt), "--rotate-stale")
        self.assertEqual(r["action"], "fanout")
        self.assertEqual(r["rotated_to"], str(receipt) + ".prev")
        self.assertFalse(receipt.exists())
        self.assertTrue(Path(str(receipt) + ".prev").exists())

    def test_foreign_receipt_never_resumes(self) -> None:
        receipt = self._receipt(self.root / "r.json", id="fn-9-other.3")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt), "--rotate-stale")
        self.assertEqual(r["receipt_state"], "foreign")
        self.assertEqual(r["action"], "fanout")
        self.assertFalse(receipt.exists())

    def test_needs_human_receipt_stops(self) -> None:
        receipt = self._receipt(self.root / "r.json", verdict="NEEDS_HUMAN")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt), "--rotate-stale")
        self.assertEqual(r["action"], "stop")
        self.assertEqual(r["reason"], "needs_human")
        self.assertTrue(r["message"].startswith("NEEDS_HUMAN:"))
        self.assertTrue(receipt.exists())

    def test_deep_overturned_receipt_is_not_resumable(self) -> None:
        receipt = self._receipt(self.root / "r.json", verdict_before_deep="SHIP")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt))
        self.assertEqual(r["action"], "stop")
        self.assertEqual(r["reason"], "deep_overturn_not_resumable")
        self.assertEqual(r["receipt_state"], "open_deep")

    def test_unreadable_receipt_is_stale(self) -> None:
        receipt = self.root / "r.json"
        receipt.write_text("{not json")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt), "--rotate-stale")
        self.assertEqual(r["receipt_state"], "unreadable")
        self.assertEqual(r["action"], "fanout")
        self.assertFalse(receipt.exists())

    # -- task-mode ledger fences ------------------------------------------

    def test_pending_reservation_stops(self) -> None:
        data = self._spec()
        data["review_pending_rounds"] = {f"impl:{self.task_id}": 1}
        self._write_spec(data)
        code, r, _ = self._route(self.task_id)
        self.assertEqual(r["action"], "stop")
        self.assertEqual(r["reason"], "in_flight")
        self.assertEqual(r["pending"], 1)

    def test_unjournaled_reservation_stops(self) -> None:
        data = self._spec()
        data["review_reservations"] = {
            "ab" * 16: {"counter_scope": f"impl:{self.task_id}", "review_type": "impl"},
            "cd" * 16: {"counter_scope": f"impl:{self.task_id}", "superseded_by": "reset"},
        }
        self._write_spec(data)
        code, r, _ = self._route(self.task_id)
        self.assertEqual(r["action"], "stop")
        self.assertEqual(r["reason"], "unjournaled_reservation")
        self.assertEqual(r["unjournaled_reservation"], "ab" * 16)

    def test_lost_receipt_on_open_cycle_stops(self) -> None:
        data = self._spec()
        data["impl_review_rounds"] = {self.task_id: 2}
        data["review_attempts"] = [
            {"counter_kind": "impl", "task": self.task_id, "verdict": "NEEDS_WORK",
             "outcome": "verdict", "round_consumed": True},
        ]
        self._write_spec(data)
        code, r, _ = self._route(self.task_id)
        self.assertEqual(r["action"], "stop")
        self.assertEqual(r["reason"], "lost_receipt")
        self.assertEqual(r["last_verdict"], "NEEDS_WORK")
        # A closed cycle (MAJOR_RETHINK) admits a fresh fan-out.
        data["review_attempts"].append(
            {"counter_kind": "impl", "task": self.task_id, "verdict": "MAJOR_RETHINK",
             "outcome": "verdict", "round_consumed": True},
        )
        self._write_spec(data)
        code, r, _ = self._route(self.task_id)
        self.assertEqual(r["action"], "fanout")

    def test_superseded_rows_are_ignored(self) -> None:
        data = self._spec()
        data["impl_review_rounds"] = {self.task_id: 1}
        data["review_attempts"] = [
            {"counter_kind": "impl", "task": self.task_id, "verdict": "NEEDS_WORK",
             "outcome": "verdict", "round_consumed": True, "superseded_by": "reset"},
        ]
        self._write_spec(data)
        code, r, _ = self._route(self.task_id)
        self.assertEqual(r["action"], "fanout")
        self.assertIsNone(r["last_verdict"])

    def test_force_bypasses_every_guard(self) -> None:
        data = self._spec()
        data["review_pending_rounds"] = {f"impl:{self.task_id}": 1}
        self._write_spec(data)
        receipt = self._receipt(self.root / "r.json", verdict="NEEDS_HUMAN")
        code, r, _ = self._route(self.task_id, "--receipt", str(receipt), "--force")
        self.assertEqual(r["action"], "fanout")
        self.assertEqual(r["reason"], "force")
        self.assertTrue(r["force"])

    def test_standalone_ignores_ledger(self) -> None:
        data = self._spec()
        data["review_pending_rounds"] = {f"impl:{self.task_id}": 1}
        self._write_spec(data)
        code, r, _ = self._route()
        self.assertEqual(r["action"], "fanout")
        self.assertEqual(r["pending"], 0)

    def test_invalid_task_rejected(self) -> None:
        code, r, err = self._route("not-a-task")
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
