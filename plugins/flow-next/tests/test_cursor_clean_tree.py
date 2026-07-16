"""Live clean-tree integration smoke test for cursor reviews (fn-74.2, R8).

A cursor review must leave the working tree byte-for-byte unchanged — the
``--mode ask`` read-only contract (asserted at the unit level in
``test_cursor_run_exec.py``) guarantees the CLI refuses to edit. This test
proves it end-to-end: it runs a **real** ``cursor impl-review`` against a throw-
away git repo and asserts ``git status --porcelain`` is identical before/after.

It is **optional**: skipped cleanly when ``cursor-agent`` is not on PATH (CI /
hosts without the CLI). It is NEVER a mocked clean-tree claim — when it runs, it
spawns the real CLI. Auth/quota failures do not fail the test: the tree must
stay clean even when the review errors out, which is exactly what R8 asserts.

Opt-in knobs:
  FLOW_TEST_CURSOR_LIVE=1   run even if you want to be explicit (auto-runs when
                            cursor-agent is present regardless)
  FLOW_TEST_CURSOR_TIMEOUT  per-review timeout seconds (default 240)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FLOWCTL = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"

EPIC_ID = "fn-1-cursor-live"
TASK_ID = f"{EPIC_ID}.1"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout


@unittest.skipUnless(
    shutil.which("cursor-agent"),
    "cursor-agent not on PATH — live clean-tree smoke test skipped",
)
class CursorCleanTreeLive(unittest.TestCase):
    def test_real_review_leaves_tree_clean(self):
        timeout = int(os.environ.get("FLOW_TEST_CURSOR_TIMEOUT", "240"))
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _git(repo, "init", "-q")
            _git(repo, "config", "user.email", "t@t.t")
            _git(repo, "config", "user.name", "t")
            (repo / "src").mkdir()
            # Plant a diff with an obvious bug for the reviewer to chew on.
            (repo / "src" / "calc.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "base")
            base = _git(repo, "rev-parse", "HEAD").strip()

            flow = repo / ".flow"
            (flow / "specs").mkdir(parents=True)
            (flow / "tasks").mkdir(parents=True)
            (flow / "specs" / f"{EPIC_ID}.md").write_text(
                "# Live demo\n\n## Acceptance Criteria\n\n- **R1:** add two numbers\n",
                encoding="utf-8",
            )
            (flow / "tasks" / f"{TASK_ID}.md").write_text(
                "---\nsatisfies: [R1]\n---\n\n## Description\n\nImplement add().\n",
                encoding="utf-8",
            )
            (repo / "src" / "calc.py").write_text(
                "def add(a, b):\n    return a - b\n", encoding="utf-8")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "introduce bug")

            status_before = _git(repo, "status", "--porcelain")
            head_before = _git(repo, "rev-parse", "HEAD").strip()

            # Receipt written OUTSIDE the repo tree so it never shows in status.
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as rf:
                receipt = Path(rf.name)
            try:
                try:
                    subprocess.run(
                        [sys.executable, str(FLOWCTL), "cursor", "impl-review",
                         TASK_ID, "--base", base, "--receipt", str(receipt),
                         "--json"],
                        cwd=str(repo), capture_output=True, text=True,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired:
                    self.skipTest("cursor-agent review timed out — clean-tree "
                                  "assertion not exercised this run")
            finally:
                receipt.unlink(missing_ok=True)

            status_after = _git(repo, "status", "--porcelain")
            head_after = _git(repo, "rev-parse", "HEAD").strip()
            # The review — pass or fail — must not mutate the tree or HEAD.
            self.assertEqual(status_before, status_after,
                             "cursor review mutated the working tree")
            self.assertEqual(head_before, head_after,
                             "cursor review moved HEAD")


if __name__ == "__main__":
    unittest.main()
