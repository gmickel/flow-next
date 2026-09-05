"""`flowctl start --reclaim` identity repair (fn-179.4, issue #316).

--reclaim rewrites the claimant deliberately with a repair-flavored claim note.
--force keeps its takeover meaning and its takeover note; the two must stay
distinguishable in the record.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

TAKEOVER_NOTE = "Taken over from other-actor"
REPAIR_NOTE = "Reclaimed from other-actor (identity repair)"


class StartReclaimTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self._run("init")
        self.spec = json.loads(
            self._run("spec", "create", "--title", "Reclaim").stdout
        )["id"]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run(
        self, *args: str, actor: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        if actor:
            env["FLOW_ACTOR"] = actor
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args, "--json"],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
        )

    def _new_task(self, title: str = "Claim me") -> str:
        return json.loads(
            self._run("task", "create", "--spec", self.spec, "--title", title).stdout
        )["id"]

    def _claimed_task(self) -> str:
        task = self._new_task()
        proc = self._run("start", task, actor="other-actor")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return task

    def _state(self, task: str) -> dict:
        path = self.repo / ".git" / "flow-state" / "tasks" / f"{task}.state.json"
        return json.loads(path.read_text(encoding="utf-8"))

    # --- reclaim ---------------------------------------------------------

    def test_reclaim_rewrites_claimant_with_repair_note(self) -> None:
        task = self._claimed_task()
        proc = self._run("start", task, "--reclaim", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertEqual(state["status"], "in_progress")
        self.assertEqual(state["claim_note"], REPAIR_NOTE)

    def test_repair_note_is_distinct_from_takeover_note(self) -> None:
        reclaimed = self._claimed_task()
        self._run("start", reclaimed, "--reclaim", actor="me")
        taken = self._claimed_task()
        self._run("start", taken, "--force", actor="me")
        self.assertNotEqual(
            self._state(reclaimed)["claim_note"], self._state(taken)["claim_note"]
        )
        self.assertEqual(self._state(reclaimed)["claim_note"], REPAIR_NOTE)
        self.assertEqual(self._state(taken)["claim_note"], TAKEOVER_NOTE)

    def test_reclaim_on_unclaimed_task_is_a_plain_claim(self) -> None:
        task = self._new_task()
        proc = self._run("start", task, "--reclaim", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertEqual(state.get("claim_note", ""), "")

    def test_reclaim_of_own_claim_writes_no_repair_note(self) -> None:
        task = self._new_task()
        self._run("start", task, actor="me")
        proc = self._run("start", task, "--reclaim", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertEqual(state.get("claim_note", ""), "")

    def test_explicit_note_wins_and_still_rewrites_claimant(self) -> None:
        task = self._claimed_task()
        proc = self._run("start", task, "--reclaim", "--note", "laptop died", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertEqual(state["claim_note"], "laptop died")

    def test_reclaim_with_force_writes_the_repair_note(self) -> None:
        task = self._claimed_task()
        proc = self._run("start", task, "--reclaim", "--force", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertEqual(state["claim_note"], REPAIR_NOTE)

    def test_reclaim_does_not_relax_the_dependency_gate(self) -> None:
        first = self._new_task("First")
        second = json.loads(
            self._run(
                "task",
                "create",
                "--spec",
                self.spec,
                "--title",
                "Second",
                "--deps",
                first,
            ).stdout
        )["id"]
        proc = self._run("start", second, "--reclaim", actor="me")
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(first, proc.stdout + proc.stderr)

    def test_reclaim_does_not_relax_the_done_gate(self) -> None:
        task = self._new_task()
        self._run("start", task, actor="other-actor")
        self._run("done", task, "--summary", "done", actor="other-actor")
        proc = self._run("start", task, "--reclaim", actor="me")
        self.assertNotEqual(proc.returncode, 0, proc.stdout)

    # --- force stays exactly as it was -----------------------------------

    def test_force_takeover_note_unchanged(self) -> None:
        task = self._claimed_task()
        proc = self._run("start", task, "--force", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertEqual(state["claim_note"], TAKEOVER_NOTE)

    def test_force_with_explicit_note_still_transfers_claim(self) -> None:
        task = self._claimed_task()
        previous_claimed_at = self._state(task)["claimed_at"]
        proc = self._run("start", task, "--force", "--note", "handoff", actor="me")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        state = self._state(task)
        self.assertEqual(state["assignee"], "me")
        self.assertNotEqual(state["claimed_at"], previous_claimed_at)
        self.assertEqual(state["claim_note"], "handoff")

    def test_claimed_by_other_without_flags_still_refuses(self) -> None:
        task = self._claimed_task()
        proc = self._run("start", task, actor="me")
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("other-actor", proc.stdout + proc.stderr)
        self.assertEqual(self._state(task)["assignee"], "other-actor")


if __name__ == "__main__":
    unittest.main()
