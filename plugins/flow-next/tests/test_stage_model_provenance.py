"""fn-195 R7: stage receipts record the model that ACTUALLY ran.

Two surfaces, one rule: record an observation where the harness exposes one,
`unknown` where it does not, and never a configured preference.

- `flowctl usage --stages` tallies an executing model per counted stage, from
  the optional `(model: …)` stage-line annotation and from the model a review
  receipt already carries.
- Review receipts already carry the model a backend dispatch resolved
  (fn-193); the summary reads it rather than storing a second copy.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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


class _RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        init = run_flowctl(["init", "--json"], self.repo)
        self.assertEqual(init.returncode, 0, init.stderr)
        create = run_flowctl(
            ["spec", "create", "--title", "Stage model provenance", "--json"],
            self.repo,
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        self.spec_id = json.loads(create.stdout)["id"]


class StageLineModelTest(_RepoCase):
    def setUp(self) -> None:
        super().setUp()
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

    def test_annotation_is_recorded_and_absence_is_unknown(self) -> None:
        self.append_summary(
            "stage: work - ran [2026-08-14T10:00:00Z..2026-08-14T10:20:00Z] "
            "(model: some-implementer-slug)\n"
            "stage: work - ran\n"
            "stage: plan-sync - skipped(config: planSync.enabled != true) "
            "(model: some-session-slug)"
        )
        stages = self.stages_json()["stages"]
        self.assertEqual(
            stages["work"]["models"],
            {"some-implementer-slug": 1, "unknown": 1},
        )
        self.assertEqual(stages["work"]["ran"], 2)
        self.assertEqual(
            stages["plan-sync"]["models"], {"some-session-slug": 1}
        )
        self.assertEqual(stages["plan-sync"]["skipped"], 1)
        self.assertIn(
            "config: planSync.enabled != true",
            stages["plan-sync"]["reasons"],
        )

    def test_placeholder_values_record_unknown_not_a_preference(self) -> None:
        for placeholder in ("auto", "default", "unknown", "  ", "None"):
            with self.subTest(placeholder=placeholder):
                self.task_md.write_text(
                    self.task_md.read_text(encoding="utf-8")
                    + f"\nstage: qa - ran (model: {placeholder})\n",
                    encoding="utf-8",
                )
        stages = self.stages_json()["stages"]
        self.assertEqual(stages["qa"]["models"], {"unknown": 5})

    def test_receipt_model_is_tallied_and_missing_one_is_unknown(self) -> None:
        receipts = self.repo / ".flow" / "review-receipts"
        receipts.mkdir(parents=True, exist_ok=True)
        (receipts / f"plan-{self.spec_id}.json").write_text(
            json.dumps(
                {
                    "type": "plan_review",
                    "verdict": "SHIP",
                    "model": "some-reviewer-slug",
                }
            ),
            encoding="utf-8",
        )
        (receipts / f"impl-{self.spec_id}.json").write_text(
            json.dumps({"type": "impl_review", "verdict": "SHIP"}),
            encoding="utf-8",
        )
        stages = self.stages_json()["stages"]
        self.assertEqual(
            stages["plan-review"]["receipt_models"], {"some-reviewer-slug": 1}
        )
        self.assertEqual(stages["impl-review"]["receipt_models"], {"unknown": 1})

    def test_malformed_annotation_still_lands_in_unknown_lines(self) -> None:
        self.append_summary(
            "stage: qa - ran (model: x) trailing junk\n"
            "stage: qa - ran (model x)\n"
            "stage: qa - ran (model: x"
        )
        data = self.stages_json()
        self.assertEqual(data["unknown_lines"], 3)
        self.assertNotIn("qa", data["stages"])

    def test_plain_output_prints_the_model_tally(self) -> None:
        self.append_summary("stage: work - ran (model: some-implementer-slug)")
        result = run_flowctl(["usage", "--stages", self.spec_id], self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("models: some-implementer-slug=1", result.stdout)


if __name__ == "__main__":
    unittest.main()


class CombinedSourceTallyTest(StageLineModelTest):
    """A prose stage line AND a receipt for the same review never merge tallies.

    The pilot's real shape: `stage: plan-review - ran` (no model annotation)
    plus a plan_review receipt carrying the dispatcher-resolved model. Merging
    the two made a fully receipt-observed review read as half `unknown`; the
    split maps mirror the deliberate ran/receipts counter split.
    """

    def test_stage_line_and_receipt_keep_separate_maps(self) -> None:
        self.append_summary("stage: plan-review - ran")
        receipts = self.repo / ".flow" / "review-receipts"
        receipts.mkdir(parents=True, exist_ok=True)
        (receipts / f"plan-{self.spec_id}.json").write_text(
            '{"type": "plan_review", "verdict": "SHIP",'
            ' "model": "some-reviewer-slug"}',
            encoding="utf-8",
        )
        entry = self.stages_json()["stages"]["plan-review"]
        self.assertEqual(entry["models"], {"unknown": 1})
        self.assertEqual(entry["receipt_models"], {"some-reviewer-slug": 1})
        self.assertEqual(entry["ran"], 1)
        self.assertEqual(entry["receipts"], 1)
