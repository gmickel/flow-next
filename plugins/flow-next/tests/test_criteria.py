"""Parser + CLI tests for global acceptance criteria (fn-137.1)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.co",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.co",
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


class TestCriteriaParse(unittest.TestCase):
    def test_valid_body_skips_non_bullets_and_allows_gaps(self) -> None:
        text = (
            "# Global criteria\n"
            "\n"
            "Standing project-wide rules.\n"
            "\n"
            "- **G1:** Every route change regenerates the contract.\n"
            "- **G3:** No new dependency without a health check.\n"
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(errors, [])
        self.assertEqual([e["id"] for e in entries], ["G1", "G3"])
        self.assertEqual(
            entries[0]["text"],
            "Every route change regenerates the contract.",
        )
        self.assertEqual(
            entries[1]["text"],
            "No new dependency without a health check.",
        )

    def test_duplicate_id_keeps_first(self) -> None:
        text = (
            "- **G1:** first occurrence.\n"
            "- **G1:** second occurrence.\n"
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(len(errors), 1)
        self.assertIn("G1", errors[0])
        self.assertIn("duplicate", errors[0])
        self.assertEqual(entries, [{"id": "G1", "text": "first occurrence."}])

    def test_empty_prose_rejected(self) -> None:
        text = "- **G2:**\n- **G2:**   \n"
        entries, errors = flowctl._criteria_parse(text)
        self.assertTrue(any("empty" in e and "G2" in e for e in errors))
        self.assertEqual(entries, [])

    def test_non_matching_bullets_ignored(self) -> None:
        text = (
            "- plain bullet\n"
            "- **R1:** rid style\n"
            "- **G1:** real criterion.\n"
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(errors, [])
        self.assertEqual(entries, [{"id": "G1", "text": "real criterion."}])


class TestCriteriaCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        (self.root / ".flow").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "flowctl.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_absent_file_empty_json(self) -> None:
        proc = self._run("criteria", "list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload["criteria"], [])
        self.assertEqual(payload["count"], 0)

    def test_valid_file_round_trips(self) -> None:
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** Every route change regenerates the contract.\n"
            "- **G3:** No new dependency without a health check.\n",
            encoding="utf-8",
        )
        proc = self._run("criteria", "list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            payload["criteria"],
            [
                {
                    "id": "G1",
                    "text": "Every route change regenerates the contract.",
                },
                {
                    "id": "G3",
                    "text": "No new dependency without a health check.",
                },
            ],
        )

    def test_invalid_file_nonzero_exit(self) -> None:
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** first.\n- **G1:** second.\n",
            encoding="utf-8",
        )
        proc = self._run("criteria", "list", "--json")
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stdout + proc.stderr
        self.assertIn("duplicate", combined)
        self.assertIn("G1", combined)


class TestCriteriaHeadingConstant(unittest.TestCase):
    def test_heading_value_pinned(self) -> None:
        self.assertEqual(
            flowctl.GLOBAL_CRITERIA_HEADING,
            "## Global acceptance criteria",
        )

    def test_completion_review_prompt_has_no_criteria_marker_when_absent(self) -> None:
        """Assembled completion-review prompt must not contain the criteria
        heading when .flow/criteria.md is absent (R1). Greps the shared
        constant so fn-137.2's injection is provably gated on file existence."""
        prompt = flowctl.build_completion_review_prompt(
            epic_spec="# Spec\n\n- **R1:** something\n",
            task_specs="task body",
            diff_summary="1 file changed",
            diff_content="diff --git a/x b/x\n",
        )
        self.assertNotIn(flowctl.GLOBAL_CRITERIA_HEADING, prompt)


if __name__ == "__main__":
    unittest.main()
