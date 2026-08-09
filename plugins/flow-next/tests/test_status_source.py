"""fn-181.1 (R1): `status_source` provenance on show/list + absent-state advisory.

Behavioral, production-wire-form tests (the CLI a caller actually runs):

  * `show <task> --json`, `show <spec> --json` task rows, and `list --json`
    task rows ALWAYS carry `status_source`.
  * The value tracks which store answered: "committed" while no runtime
    entry exists for the task, "flow-state" once one does (after `start`).
  * Plain (non-JSON) `show` / `list` print exactly ONE advisory line per
    invocation when the runtime state directory is absent, and none when it
    exists — the advisory is a property of the invocation, not of each task.
  * The annotation is never persisted: a merged task that round-trips
    through a write path leaves no `status_source` in the tracked JSON.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_status_source -q
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# fn-139.1: the tracker package sits beside flowctl.py; under a test module
# sys.path[0] is THIS directory, not scripts/, so it would not import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

SPEC_ID = "fn-1-sample-spec"
TASK_ID = "fn-1-sample-spec.1"


class StatusSourceProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        subprocess.run(
            ["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True
        )
        self._flowctl("init")
        self._flowctl("spec", "create", "--title", "Sample spec", "--json")
        self._flowctl(
            "task", "create", "--spec", SPEC_ID,
            "--title", "T one", "--acceptance", "acc", "--json",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- drivers ---------------------------------------------------------

    def _flowctl(self, *args: str) -> "subprocess.CompletedProcess[str]":
        result = subprocess.run(
            [sys.executable, str(FLOWCTL_PY)] + list(args),
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def _json(self, *args: str) -> dict:
        return json.loads(self._flowctl(*args).stdout)

    def _start_task(self) -> None:
        """Claim the task so the runtime state store owns its status."""
        self._flowctl("start", TASK_ID, "--json")

    @property
    def _state_dir(self) -> Path:
        return self.tmpdir / ".git" / "flow-state"

    # --- R1: the field is always present ---------------------------------

    def test_show_task_json_carries_status_source(self) -> None:
        self.assertEqual(
            self._json("show", TASK_ID, "--json")["status_source"], "committed"
        )
        self._start_task()
        self.assertEqual(
            self._json("show", TASK_ID, "--json")["status_source"], "flow-state"
        )

    def test_list_json_task_rows_carry_status_source(self) -> None:
        (row,) = self._json("list", "--json")["tasks"]
        self.assertEqual(row["status_source"], "committed")
        self._start_task()
        (row,) = self._json("list", "--json")["tasks"]
        self.assertEqual(row["status_source"], "flow-state")

    def test_spec_show_task_rows_share_the_field(self) -> None:
        """Spec `show` reuses the same merge, not a parallel path."""
        (row,) = self._json("show", SPEC_ID, "--json")["tasks"]
        self.assertEqual(row["status_source"], "committed")
        self._start_task()
        (row,) = self._json("show", SPEC_ID, "--json")["tasks"]
        self.assertEqual(row["status_source"], "flow-state")

    # --- R1: the plain-output advisory -----------------------------------

    def _advisory_lines(self, text: str) -> list:
        return [
            line for line in text.splitlines()
            if line.startswith("note: runtime state absent")
        ]

    def test_plain_output_advises_once_when_state_dir_absent(self) -> None:
        self.assertFalse(self._state_dir.exists())
        for args in (("list",), ("show", TASK_ID), ("show", SPEC_ID)):
            with self.subTest(args=args):
                lines = self._advisory_lines(self._flowctl(*args).stdout)
                self.assertEqual(len(lines), 1, lines)
                self.assertIn("may be stale", lines[0])

    def test_advisory_is_per_invocation_not_per_task(self) -> None:
        for suffix in ("2", "3"):
            self._flowctl(
                "task", "create", "--spec", SPEC_ID,
                "--title", f"T {suffix}", "--acceptance", "acc", "--json",
            )
        listing = self._flowctl("list").stdout
        self.assertEqual(len(self._json("list", "--json")["tasks"]), 3)
        self.assertEqual(len(self._advisory_lines(listing)), 1)

    def test_no_advisory_once_state_dir_exists(self) -> None:
        self._start_task()
        self.assertTrue(self._state_dir.exists())
        for args in (("list",), ("show", TASK_ID), ("show", SPEC_ID)):
            with self.subTest(args=args):
                self.assertEqual(
                    self._advisory_lines(self._flowctl(*args).stdout), []
                )

    def test_json_output_never_prints_the_advisory(self) -> None:
        """--json stays machine-clean; the field carries the provenance."""
        out = self._flowctl("list", "--json").stdout
        self.assertNotIn("note: runtime state absent", out)
        json.loads(out)

    # --- R1: never persisted ---------------------------------------------

    def test_status_source_is_not_written_to_tracked_task_json(self) -> None:
        self._start_task()
        body = self.tmpdir / "desc.md"
        body.write_text("updated body\n", encoding="utf-8")
        self._flowctl(
            "task", "set-description", TASK_ID, "--file", str(body), "--json"
        )
        payload = json.loads(
            (self.tmpdir / ".flow" / "tasks" / f"{TASK_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("status_source", payload)


class MergeProvenanceUnitTest(unittest.TestCase):
    """The merge point itself stamps provenance without changing semantics."""

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "flowctl_status_source_under_test", FLOWCTL_PY
        )
        cls.flowctl = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.flowctl
        spec.loader.exec_module(cls.flowctl)

    def test_runtime_present_reads_flow_state(self) -> None:
        merged = self.flowctl.merge_task_runtime(
            {"id": TASK_ID, "status": "todo"}, {"status": "done"}
        )
        self.assertEqual(merged["status"], "done")
        self.assertEqual(merged["status_source"], "flow-state")

    def test_runtime_absent_reads_committed(self) -> None:
        merged = self.flowctl.merge_task_runtime(
            {"id": TASK_ID, "status": "in_progress"}, None
        )
        self.assertEqual(merged["status"], "in_progress")
        self.assertEqual(merged["status_source"], "committed")

    def test_legacy_definition_without_runtime_fields_still_marked(self) -> None:
        merged = self.flowctl.merge_task_runtime({"id": TASK_ID}, None)
        self.assertEqual(merged["status"], "todo")
        self.assertEqual(merged["status_source"], "committed")

    def test_write_canonicalization_strips_the_annotation(self) -> None:
        merged = self.flowctl.merge_task_runtime(
            {"id": TASK_ID, "status": "todo"}, {"status": "done"}
        )
        self.assertNotIn(
            "status_source", self.flowctl.canonicalize_task_for_write(merged)
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
