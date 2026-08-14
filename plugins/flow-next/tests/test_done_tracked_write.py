"""fn-192.2 (R3, R5 iv-v) / #346: `done` / `block` name the tracked file they wrote.

`done` and `block` patch the receipt into `.flow/tasks/<id>.md`, which is a
TRACKED file, while the documented loop commits BEFORE calling them - so the
receipt lands unstaged and, before this change, nothing at the point of write
said so. Two additive signals, no staging and no commit from inside flowctl:

  * `--json` carries `modified_paths` listing the tracked path written.
  * ONE stderr advisory naming that path when it is tracked and now dirty -
    and none when the file was never committed, or when there is no repo.

Exit codes and the existing `status` key are untouched (Ralph / pilot / land
guards read exit + status only).

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_done_tracked_write -q
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
ADVISORY_MARKER = "is tracked and now has uncommitted changes"


class _Fixture(unittest.TestCase):
    """A throwaway project with one started task. Git init is opt-in."""

    git = True

    def setUp(self) -> None:
        # .resolve(): macOS hands out /var/... which git reports as
        # /private/var/... - the manifest is compared against git's answer.
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        if self.git:
            self._git("init", "-q")
            self._git("config", "user.email", "test@example.com")
            self._git("config", "user.name", "Test")
        self._flowctl("init")
        self._flowctl("spec", "create", "--title", "Sample spec", "--json")
        self._flowctl(
            "task", "create", "--spec", SPEC_ID,
            "--title", "T one", "--acceptance", "acc", "--json",
        )
        self._flowctl("start", TASK_ID, "--json")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- drivers ---------------------------------------------------------

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=str(self.tmpdir), check=True, capture_output=True
        )

    def _flowctl(self, *args: str) -> "subprocess.CompletedProcess[str]":
        result = subprocess.run(
            [sys.executable, str(FLOWCTL_PY)] + list(args),
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    @property
    def task_path(self) -> Path:
        return self.tmpdir / ".flow" / "tasks" / f"{TASK_ID}.md"

    def _commit_everything(self) -> None:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "baseline")

    def _done(self) -> "subprocess.CompletedProcess[str]":
        summary = self.tmpdir / "_summary.md"
        summary.write_text("- did the thing\n", encoding="utf-8")
        return self._flowctl(
            "done", TASK_ID, "--summary-file", str(summary), "--json"
        )

    def _block(self) -> "subprocess.CompletedProcess[str]":
        reason = self.tmpdir / "_reason.md"
        reason.write_text("upstream API is down\n", encoding="utf-8")
        return self._flowctl("block", TASK_ID, "--reason-file", str(reason), "--json")


class ModifiedPathsManifestTest(_Fixture):
    """R5(iv): the --json payload reports the tracked path it wrote."""

    def test_done_json_reports_modified_paths(self) -> None:
        payload = json.loads(self._done().stdout)
        self.assertEqual(payload["modified_paths"], [str(self.task_path)])
        # Guard keys the autonomous loops read are untouched.
        self.assertEqual(payload["status"], "done")
        self.assertEqual(payload["id"], TASK_ID)

    def test_block_json_reports_modified_paths(self) -> None:
        payload = json.loads(self._block().stdout)
        self.assertEqual(payload["modified_paths"], [str(self.task_path)])
        self.assertEqual(payload["status"], "blocked")

    def test_modified_path_is_the_file_that_actually_changed(self) -> None:
        before = self.task_path.read_text(encoding="utf-8")
        payload = json.loads(self._done().stdout)
        written = Path(payload["modified_paths"][0])
        self.assertNotEqual(before, written.read_text(encoding="utf-8"))


class DirtyTrackedAdvisoryTest(_Fixture):
    """R5(v): one stderr line when the tracked receipt file is left dirty."""

    def test_advisory_on_stderr_when_tracked_file_goes_dirty(self) -> None:
        self._commit_everything()
        result = self._done()
        lines = [ln for ln in result.stderr.splitlines() if ADVISORY_MARKER in ln]
        self.assertEqual(len(lines), 1, result.stderr)
        self.assertIn(f".flow/tasks/{TASK_ID}.md", lines[0])
        self.assertIn("belongs in a commit", lines[0])
        # Advisory is stderr-only: stdout stays clean JSON.
        json.loads(result.stdout)

    def test_advisory_also_fires_for_block(self) -> None:
        self._commit_everything()
        result = self._block()
        self.assertEqual(
            len([ln for ln in result.stderr.splitlines() if ADVISORY_MARKER in ln]),
            1,
            result.stderr,
        )

    def test_no_advisory_when_task_file_was_never_committed(self) -> None:
        # Nothing committed: the task file is untracked, so there is no
        # uncommitted-change claim to make.
        result = self._done()
        self.assertNotIn(ADVISORY_MARKER, result.stderr)

    def test_no_advisory_when_the_write_leaves_no_diff(self) -> None:
        # `done` is run, then its own output is committed; a second write of
        # identical content (via --force) leaves the tree clean.
        self._commit_everything()
        self._done()
        self._commit_everything()
        summary = self.tmpdir / "_summary.md"
        result = self._flowctl(
            "done", TASK_ID, "--force", "--summary-file", str(summary), "--json"
        )
        self.assertNotIn(ADVISORY_MARKER, result.stderr)

    def test_plain_output_mode_still_gets_the_advisory(self) -> None:
        self._commit_everything()
        summary = self.tmpdir / "_summary.md"
        summary.write_text("- did the thing\n", encoding="utf-8")
        result = self._flowctl("done", TASK_ID, "--summary-file", str(summary))
        self.assertIn("completed", result.stdout)
        self.assertIn(ADVISORY_MARKER, result.stderr)


class NoRepoAdvisoryTest(_Fixture):
    """R5(v): absent a git repo, the advisory degrades to silence."""

    git = False

    def test_no_advisory_outside_a_git_repo(self) -> None:
        result = self._done()
        self.assertNotIn(ADVISORY_MARKER, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["modified_paths"], [str(self.task_path)]
        )


if __name__ == "__main__":
    unittest.main()
