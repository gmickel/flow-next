"""Hill-climb route (fn-265): the recorded fixture run stays consistent and replayable."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
FIXTURE = PLUGIN / "tests" / "fixtures" / "hill-climb-cli"
RUN = FIXTURE / "run"


def _ledger_rows():
    text = (RUN / "ledger.md").read_text(encoding="utf-8")
    section = text.split("## Ledger", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in section.splitlines() if line.startswith("| ")]
    return [row for row in rows[1:] if not set(row[0]) <= {"-"}]


class HillClimbFixtureRun(unittest.TestCase):
    def test_ledger_has_one_row_per_attempt_and_one_diff_per_kept_row(self):
        rows = _ledger_rows()
        self.assertEqual([row[0] for row in rows], [str(n) for n in range(1, len(rows) + 1)])
        verdicts = [row[8] for row in rows]
        self.assertTrue(set(verdicts) <= {"kept", "reverted", "inconclusive"}, verdicts)
        self.assertIn("kept", verdicts)
        self.assertTrue({"reverted", "inconclusive"} & set(verdicts))
        kept = [f"attempt-{row[0]}.diff" for row in rows if row[8] == "kept"]
        self.assertEqual([row[10] for row in rows if row[8] == "kept"], kept)
        self.assertEqual(sorted(p.name for p in RUN.glob("attempt-*.diff")), sorted(kept))

    def test_kept_diffs_replay_in_order_and_the_gate_stays_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "cli"
            shutil.copytree(FIXTURE, work, ignore=shutil.ignore_patterns("run", "__pycache__"))
            kept = [row[0] for row in _ledger_rows() if row[8] == "kept"]
            for number in kept:
                diff = RUN / f"attempt-{number}.diff"
                applied = subprocess.run(["git", "apply", str(diff)], cwd=work, capture_output=True, text=True)
                self.assertEqual(applied.returncode, 0, f"{diff.name}: {applied.stderr}")
            gate = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=work, capture_output=True, text=True)
            self.assertEqual(gate.returncode, 0, gate.stderr)

    def test_harness_rejects_a_wrong_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "cli"
            shutil.copytree(FIXTURE, work, ignore=shutil.ignore_patterns("run", "__pycache__"))
            main = work / "mycli" / "__main__.py"
            main.write_text(main.read_text(encoding="utf-8").replace('f"mycli {VERSION}"', '"mycli 1.4"'), encoding="utf-8")
            result = subprocess.run([sys.executable, "bench.py", "--runs", "1", "--warmup", "0", "."], cwd=work, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("OUTPUT CHECK FAILED", result.stderr)


if __name__ == "__main__":
    unittest.main()
