"""Regression coverage for the phrase-triggered worktree manager."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    ROOT
    / "plugins"
    / "flow-next"
    / "skills"
    / "flow-next-worktree-kit"
    / "scripts"
    / "worktree.sh"
)


def _bash_executable() -> str:
    """Return Git Bash on Windows, never the WSL compatibility launcher."""
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            git_bash = Path(git).resolve().parent.parent / "bin" / "bash.exe"
            if git_bash.is_file():
                return str(git_bash)
    bash = shutil.which("bash")
    if bash:
        return bash
    raise RuntimeError("bash executable not found")


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bash_executable(), str(SCRIPT), *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


class WorktreeIgnore(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo = Path(self.temp_dir.name)
        self.assertEqual(git(self.repo, "init", "-q").returncode, 0)
        self.assertEqual(
            git(self.repo, "config", "user.email", "test@example.com").returncode,
            0,
        )
        self.assertEqual(
            git(self.repo, "config", "user.name", "Flow Next Test").returncode,
            0,
        )
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self.assertEqual(git(self.repo, "add", "README.md").returncode, 0)
        self.assertEqual(
            git(self.repo, "commit", "-qm", "fixture").returncode,
            0,
        )

    def test_create_prevents_nested_worktree_gitlink_staging(self) -> None:
        created = run(self.repo, "create", "feature")
        self.assertEqual(created.returncode, 0, created.stderr)

        ignore = self.repo / ".worktrees" / ".gitignore"
        self.assertEqual(ignore.read_text(encoding="utf-8"), "*\n!.gitignore\n")

        staged = git(self.repo, "add", "-A")
        self.assertEqual(staged.returncode, 0, staged.stderr)
        entries = git(self.repo, "ls-files", "--stage")
        self.assertEqual(entries.returncode, 0, entries.stderr)
        worktree_entries = [
            line for line in entries.stdout.splitlines()
            if line.endswith("\t.worktrees/.gitignore")
            or "\t.worktrees/" in line
        ]
        self.assertEqual(len(worktree_entries), 1, entries.stdout)
        self.assertTrue(
            worktree_entries[0].startswith("100644 "),
            worktree_entries[0],
        )
        self.assertNotIn("160000 ", entries.stdout)

    def test_create_preserves_existing_custom_ignore(self) -> None:
        worktrees = self.repo / ".worktrees"
        worktrees.mkdir()
        ignore = worktrees / ".gitignore"
        ignore.write_text("# custom\nfeature/\n", encoding="utf-8")

        created = run(self.repo, "create", "feature")
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertEqual(
            ignore.read_text(encoding="utf-8"),
            "# custom\nfeature/\n",
        )

    def test_create_extends_custom_ignore_that_does_not_cover_target(self) -> None:
        worktrees = self.repo / ".worktrees"
        worktrees.mkdir()
        ignore = worktrees / ".gitignore"
        ignore.write_text("# custom\nfeature/", encoding="utf-8")

        created = run(self.repo, "create", "other")
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertEqual(
            ignore.read_text(encoding="utf-8"),
            "# custom\nfeature/\n/other/\n",
        )

        staged = git(self.repo, "add", "-A")
        self.assertEqual(staged.returncode, 0, staged.stderr)
        entries = git(self.repo, "ls-files", "--stage")
        self.assertEqual(entries.returncode, 0, entries.stderr)
        self.assertNotIn("160000 ", entries.stdout)


if __name__ == "__main__":
    unittest.main()
