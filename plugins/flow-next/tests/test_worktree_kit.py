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


def run(
    repo: Path,
    *args: str,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bash_executable(), str(SCRIPT), *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        input=stdin,
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


class RepoCase(unittest.TestCase):
    """Temp git repo with one commit, shared by every case in this module."""

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

    def current_branch(self) -> str:
        head = git(self.repo, "symbolic-ref", "--short", "HEAD")
        self.assertEqual(head.returncode, 0, head.stderr)
        return head.stdout.strip()

    def add_origin(self) -> None:
        """Give the fixture a real origin so create resolves origin/<base>."""
        remote_dir = tempfile.TemporaryDirectory()
        self.addCleanup(remote_dir.cleanup)
        remote = Path(remote_dir.name)
        self.assertEqual(git(remote, "init", "-q", "--bare").returncode, 0)
        added = git(self.repo, "remote", "add", "origin", str(remote))
        self.assertEqual(added.returncode, 0, added.stderr)
        pushed = git(self.repo, "push", "-q", "origin", self.current_branch())
        self.assertEqual(pushed.returncode, 0, pushed.stderr)


class WorktreeIgnore(RepoCase):
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


class WorktreeCleanupNonInteractive(RepoCase):
    def test_cleanup_without_names_or_terminal_fails_loudly(self) -> None:
        result = run(self.repo, "cleanup", stdin="")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("no terminal and no names given", result.stderr)
        self.assertIn("--yes", result.stderr)

    def test_cleanup_with_name_and_yes_removes_worktree(self) -> None:
        created = run(self.repo, "create", "feature")
        self.assertEqual(created.returncode, 0, created.stderr)
        target = self.repo / ".worktrees" / "feature"
        self.assertIn(target.resolve().as_posix(), git(self.repo, "worktree", "list").stdout)

        result = run(self.repo, "cleanup", "feature", "--yes", stdin="")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = git(self.repo, "worktree", "list")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertNotIn(target.resolve().as_posix(), listed.stdout)
        self.assertFalse(target.exists())

    def test_cleanup_with_name_without_yes_refuses_off_terminal(self) -> None:
        created = run(self.repo, "create", "feature")
        self.assertEqual(created.returncode, 0, created.stderr)

        result = run(self.repo, "cleanup", "feature", stdin="")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("--yes", result.stderr)
        listed = git(self.repo, "worktree", "list")
        self.assertIn((self.repo / ".worktrees" / "feature").resolve().as_posix(), listed.stdout)

    def test_cleanup_rejects_unknown_option(self) -> None:
        result = run(self.repo, "cleanup", "--force", stdin="")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("--force", result.stderr)


class WorktreeCreateTracking(RepoCase):
    def test_created_branch_has_no_upstream(self) -> None:
        self.add_origin()
        created = run(self.repo, "create", "feature")
        self.assertEqual(created.returncode, 0, created.stderr)

        remotes = git(self.repo, "rev-parse", "--verify", "-q", "refs/remotes/origin/" + self.current_branch())
        self.assertEqual(remotes.returncode, 0, "fixture must have a remote-tracking base ref")

        worktree = self.repo / ".worktrees" / "feature"
        upstream = git(worktree, "rev-parse", "--abbrev-ref", "@{upstream}")
        self.assertNotEqual(upstream.returncode, 0, upstream.stdout)


if __name__ == "__main__":
    unittest.main()
