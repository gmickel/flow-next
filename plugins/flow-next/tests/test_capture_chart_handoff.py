"""Capture's gated references stay reachable from workflow.md.

Chart-briefing, mark-ready and rewrite-mode prose live in references that
workflow.md's gates load. Only reachability is checked here; the wording of
the references is not pinned.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CANONICAL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-capture"
GATED_REFERENCES = ("chart-briefing.md", "from-goal.md", "mark-ready.md", "rewrite-mode.md")


class CaptureReferenceReachability(unittest.TestCase):
    def test_workflow_reaches_gated_references(self) -> None:
        workflow = (CANONICAL / "workflow.md").read_text(encoding="utf-8")
        for name in GATED_REFERENCES:
            with self.subTest(reference=name):
                self.assertTrue((CANONICAL / "references" / name).is_file(), name)
                self.assertIn(f"references/{name}", workflow)


def _capture_parse(arguments: str) -> subprocess.CompletedProcess:
    """Run SKILL.md's mode-detection fence for real and print what it set."""
    text = (CANONICAL / "SKILL.md").read_text(encoding="utf-8")
    start = text.index('RAW_ARGS="$ARGUMENTS"')
    fence = text[start:text.index("```", start)]
    report = 'printf "FROM_GOAL=%s MODE=%s COMMIT_YES=%s\\n" "$FROM_GOAL" "$MODE" "$COMMIT_YES"'
    return subprocess.run(["bash", "-c", fence + "\n" + report], capture_output=True, text=True,
                          env={**os.environ, "ARGUMENTS": arguments})


@unittest.skipIf(sys.platform == "win32" or shutil.which("bash") is None, "needs a POSIX bash")
class CaptureFromGoalToken(unittest.TestCase):
    def test_from_goal_writes_unattended_and_loads_its_reference(self) -> None:
        res = _capture_parse("from:goal fn-40")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("FROM_GOAL=1 MODE=autofix COMMIT_YES=1", res.stdout)
        self.assertIn("references/from-goal.md", res.stdout)
        self.assertIn("references/autofix-mode.md", res.stdout)

    def test_lookalike_token_is_not_from_goal(self) -> None:
        res = _capture_parse("from:goals fn-40")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("FROM_GOAL=0 MODE=interactive COMMIT_YES=0", res.stdout)
        self.assertNotIn("from-goal.md", res.stdout)


if __name__ == "__main__":
    unittest.main()
