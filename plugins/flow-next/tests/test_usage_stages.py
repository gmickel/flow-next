"""fn-178 R5: `flowctl usage --stages <spec-id>` summarizes stage-outcome lines.

Focused, table-driven coverage of the enumerated error surface: malformed or
absent stage lines land in `unknown` counts and the verb exits 0 — never a
crash. Bare `flowctl usage` (no flag) keeps printing the usage guide.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
FLOWCTL = HERE.parent.parent / "scripts" / "flowctl.py"


def run_flowctl(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
    )


class UsageStagesTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        init = run_flowctl(["init", "--json"], self.repo)
        self.assertEqual(init.returncode, 0, init.stderr)
        create = run_flowctl(
            ["spec", "create", "--title", "Stage summary probe", "--json"],
            self.repo,
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        self.spec_id = json.loads(create.stdout)["id"]
        task = run_flowctl(
            ["task", "create", "--spec", self.spec_id, "--title", "t1", "--json"],
            self.repo,
        )
        self.assertEqual(task.returncode, 0, task.stderr)
        self.task_md = self.repo / ".flow" / "tasks" / f"{self.spec_id}.1.md"

    def append_summary(self, lines: str) -> None:
        self.task_md.write_text(
            self.task_md.read_text(encoding="utf-8") + "\n" + lines + "\n",
            encoding="utf-8",
        )

    def stages_json(self) -> dict:
        result = run_flowctl(
            ["usage", "--stages", self.spec_id, "--json"], self.repo
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_counts_ran_skipped_failed_with_reasons(self) -> None:
        self.append_summary(
            "stage: plan-sync - skipped(config: planSync.enabled != true)\n"
            "stage: impl-review - ran [2026-08-08T10:00:00Z..2026-08-08T10:05:00Z]\n"
            "stage: qa - failed(error: no live app reachable)"
        )
        data = self.stages_json()
        self.assertEqual(data["stages"]["plan-sync"]["skipped"], 1)
        self.assertIn(
            "config: planSync.enabled != true",
            data["stages"]["plan-sync"]["reasons"],
        )
        self.assertEqual(data["stages"]["impl-review"]["ran"], 1)
        self.assertEqual(data["stages"]["qa"]["failed"], 1)
        self.assertEqual(data["unknown_lines"], 0)

    def test_malformed_lines_count_as_unknown_and_exit_zero(self) -> None:
        self.append_summary(
            "stage: plan-sync exploded without an outcome word\n"
            "stage: ???\n"
            "stage: qa - skipped\n"
            "stage: qa - failed(\n"
            "stage: qa - ran trailing junk"
        )
        data = self.stages_json()
        self.assertEqual(data["unknown_lines"], 5)
        self.assertNotIn("qa", data["stages"])
        self.assertTrue(data["success"])

    def test_no_lines_at_all_is_empty_not_an_error(self) -> None:
        data = self.stages_json()
        self.assertEqual(data["stages"], {})
        self.assertEqual(data["unknown_lines"], 0)
        plain = run_flowctl(["usage", "--stages", self.spec_id], self.repo)
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertIn("no stage-outcome lines recorded", plain.stdout)

    def test_review_receipt_counts_separately_and_names_normalize(self) -> None:
        # A prose line and a receipt describe the SAME review attempt: they
        # share one hyphen-normalized bucket, with the receipt under its own
        # key so nothing is double-counted as ran.
        self.append_summary("stage: plan-review - ran")
        receipts = self.repo / ".flow" / "review-receipts"
        receipts.mkdir(parents=True, exist_ok=True)
        (receipts / f"plan-{self.spec_id}.json").write_text(
            json.dumps({"type": "plan_review", "verdict": "SHIP"}),
            encoding="utf-8",
        )
        data = self.stages_json()
        self.assertNotIn("plan_review", data["stages"])
        entry = data["stages"]["plan-review"]
        self.assertEqual(entry["ran"], 1)
        self.assertEqual(entry["receipts"], 1)

    def test_bare_usage_still_prints_the_guide(self) -> None:
        result = run_flowctl(["usage"], self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Stage outcomes", result.stdout)
        self.assertTrue(result.stdout.strip())

    def test_unknown_spec_errors_cleanly(self) -> None:
        result = run_flowctl(
            ["usage", "--stages", "fn-9999-does-not-exist", "--json"], self.repo
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
