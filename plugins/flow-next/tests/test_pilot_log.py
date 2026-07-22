"""O(1) pilot counter state and recovery regression tests.

fn-122.8 deterministic evidence: at tick 41, pre-change append read all 40
historical rows; steady-state append now reads one counter and exactly one
historical commit witness. Missing/corrupt/crash-ahead state performs the
bounded recovery scan once, then returns to constant work.
"""

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


class TestPilotLogCounter(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        with contextlib.redirect_stdout(io.StringIO()):
            flowctl.cmd_init(argparse.Namespace(json=True))

    def tearDown(self) -> None:
        os.chdir(self.previous)
        self._tmp.cleanup()

    @property
    def run_dir(self) -> Path:
        return self.root / ".flow" / "pilot-runs"

    def _append(self, raw_id: str = "fn-scale") -> dict:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            flowctl.cmd_pilot_log_append(
                argparse.Namespace(
                    id=raw_id,
                    action="advanced",
                    stage="work",
                    cost_tokens=None,
                    json=True,
                )
            )
        return json.loads(output.getvalue())

    def test_steady_state_reads_one_historical_witness_not_full_history(self) -> None:
        for _ in range(40):
            self._append()
        real_read = Path.read_text
        counts: Counter[str] = Counter()

        def counting_read(path, *args, **kwargs):
            counts[str(path)] += 1
            return real_read(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", counting_read):
            out = self._append()
        historical_reads = [
            path
            for path in counts
            if Path(path).name.startswith("pilot-")
        ]
        self.assertEqual(out["tick"], 41)
        self.assertEqual(len(historical_reads), 1)
        self.assertEqual(sum(counts[path] for path in historical_reads), 1)

    def test_missing_and_corrupt_counter_reconstruct_from_rows(self) -> None:
        for _ in range(3):
            self._append()
        counter = next(self.run_dir.glob(".pilot-*.counter.json"))
        counter.unlink()
        self.assertEqual(self._append()["tick"], 4)
        counter.write_text("{broken", encoding="utf-8")
        self.assertEqual(self._append()["tick"], 5)

    def test_crash_ahead_counter_without_witness_reconstructs(self) -> None:
        for _ in range(2):
            self._append()
        counter = next(self.run_dir.glob(".pilot-*.counter.json"))
        state = json.loads(counter.read_text(encoding="utf-8"))
        state["nextTick"] = 99
        state["lastRow"] = "pilot-missing-witness.json"
        counter.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self._append()["tick"], 3)

    def test_stale_but_internally_valid_counter_cannot_reuse_tick(self) -> None:
        for _ in range(3):
            self._append()
        counter = next(self.run_dir.glob(".pilot-*.counter.json"))
        row_one = next(
            path
            for path in self.run_dir.glob("pilot-*.json")
            if json.loads(path.read_text(encoding="utf-8"))["tick"] == 1
        )
        stale = json.loads(counter.read_text(encoding="utf-8"))
        stale["nextTick"] = 2
        stale["lastRow"] = row_one.name
        counter.write_text(json.dumps(stale), encoding="utf-8")

        self.assertEqual(self._append()["tick"], 4)
        ticks = sorted(
            json.loads(path.read_text(encoding="utf-8"))["tick"]
            for path in self.run_dir.glob("pilot-*.json")
        )
        self.assertEqual(ticks, [1, 2, 3, 4])

    def test_orphaned_reservation_is_skipped_after_row_write_failure(self) -> None:
        real_write = flowctl.atomic_write_json

        def fail_row(path, payload):
            if Path(path).name.startswith("pilot-"):
                raise OSError("injected row failure")
            return real_write(path, payload)

        with mock.patch.object(flowctl, "atomic_write_json", side_effect=fail_row):
            with self.assertRaises(OSError):
                self._append()

        # Tick 1 may have been observed/reserved before the failure. Recovery
        # consumes the orphan slot and publishes tick 2, never a duplicate 1.
        self.assertEqual(self._append()["tick"], 2)


if __name__ == "__main__":
    unittest.main()
