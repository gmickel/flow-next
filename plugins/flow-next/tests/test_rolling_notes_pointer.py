"""Rolling scheduler notes pointer is keyed by RUN_ID (fn-204, R3).

Two concurrent rolling runs on one checkout each get their own pointer file
under `.flow/tmp/`, so the second run neither overwrites the first run's
pointer nor removes its notes directory, and the 3f cleanup of one run leaves
the sibling's pointer and directory in place. The test executes the skill's
own bash fences (3.0 create, 3f cleanup) rather than a paraphrase of them.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SCHEDULER = PLUGIN / "skills" / "flow-next-work" / "references" / "rolling-scheduler.md"


def fence(marker: str) -> str:
    text = SCHEDULER.read_text(encoding="utf-8")
    return next(
        block for block in re.findall(r"```bash\n(.*?)```", text, re.S) if marker in block
    )


@unittest.skipIf(
    sys.platform == "win32" or not shutil.which("bash"),
    "skill fences require POSIX bash",
)
class RollingNotesPointerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.state_dir = self.repo / "state" / "flow-state"
        self.state_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _bash(self, code: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "FLOW_STATE_DIR": str(self.state_dir)}
        return subprocess.run(
            ["bash", "-c", code], cwd=self.repo, env=env, capture_output=True, text=True
        )

    def _create_run(self) -> tuple[str, Path]:
        """Run the 3.0 fence once; return (RUN_ID, notes dir) it minted."""
        code = fence('RUN_ID="$(date').replace("<spec-id>", "fn-1")
        proc = self._bash(code)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        match = re.search(r"^RUN_ID=(\S+)$", proc.stdout, re.M)
        self.assertIsNotNone(match, proc.stdout)
        run_id = match.group(1)
        pointer = self.repo / ".flow" / "tmp" / f"notes_dir.{run_id}"
        self.assertTrue(pointer.is_file(), f"pointer missing for {run_id}")
        notes_dir = Path(pointer.read_text(encoding="utf-8"))
        self.assertTrue(notes_dir.is_dir(), notes_dir)
        self.assertEqual(notes_dir, self.repo / "state" / "flow-notes" / f"fn-1-{run_id}")
        return run_id, notes_dir

    def test_second_run_keeps_its_own_pointer_and_first_run_survives_cleanup(self) -> None:
        first_id, first_dir = self._create_run()
        second_id, second_dir = self._create_run()
        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(first_dir, second_dir)
        # The second run's 3.0 neither overwrote the first pointer nor removed its dir.
        first_pointer = self.repo / ".flow" / "tmp" / f"notes_dir.{first_id}"
        self.assertEqual(first_pointer.read_text(encoding="utf-8"), str(first_dir))
        self.assertTrue(first_dir.is_dir())
        self.assertFalse((self.repo / ".flow" / "tmp" / "notes_dir").exists())

        # The first run's 3f cleanup removes only its own pointer and directory.
        cleanup = fence("NOTES_POINTER=\".flow/tmp/notes_dir.<RUN_ID>\"").replace(
            "<RUN_ID>", first_id
        )
        proc = self._bash(cleanup)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(first_pointer.exists())
        self.assertFalse(first_dir.exists())
        second_pointer = self.repo / ".flow" / "tmp" / f"notes_dir.{second_id}"
        self.assertEqual(second_pointer.read_text(encoding="utf-8"), str(second_dir))
        self.assertTrue(second_dir.is_dir())

    def test_cleanup_without_a_pointer_is_a_no_op(self) -> None:
        run_id, notes_dir = self._create_run()
        cleanup = fence("NOTES_POINTER=\".flow/tmp/notes_dir.<RUN_ID>\"").replace(
            "<RUN_ID>", "never-minted"
        )
        proc = self._bash(cleanup)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(notes_dir.is_dir())
        self.assertTrue((self.repo / ".flow" / "tmp" / f"notes_dir.{run_id}").is_file())


if __name__ == "__main__":
    unittest.main()
