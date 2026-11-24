"""Status policy: a just-captured spec against an issue in the ready lane (fn-326 R6)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "flow" / "skills" / "flow" / "scripts"))

from flowctl_tracker.status.policy import decide  # noqa: E402


class CapturedSpecAgainstReadyIssue(unittest.TestCase):
    """A captured spec has no tasks (flow=backlog); its issue sits in Todo.
    Both are "not started": the push keeps the tracker's slot instead of
    reporting a conflict or demoting the issue out of the ready lane."""

    def test_backlog_push_against_todo_noops_under_every_tiebreak(self) -> None:
        for tiebreak in ("always-ask", "flow-wins", "tracker-wins"):
            for requested in ("backlog", "todo"):
                with self.subTest(tiebreak=tiebreak, requested=requested):
                    d = decide(requested, None, "backlog", "todo", "none", tiebreak)
                    self.assertEqual(d.kind, "noop")
                    self.assertEqual(d.target_slot, "todo")

    def test_started_or_finished_requests_against_the_pair_still_refuse(self) -> None:
        d = decide("in_progress", None, "backlog", "todo", "none")
        self.assertEqual((d.kind, d.reason), ("conflict", "unmapped"))
        d = decide("done", None, "backlog", "todo", "none")
        self.assertEqual((d.kind, d.reason), ("conflict", "merge-evidence-gate"))


if __name__ == "__main__":
    unittest.main()
