"""Unit tests for `_ensure_flow_gitignore` and its integration into `cmd_init`.
Covers fresh write, idempotency, user-pattern preservation, and pattern sets."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

spec = importlib.util.spec_from_file_location("flowctl", ROOT / "scripts" / "flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
sys.modules["flowctl"] = flowctl
spec.loader.exec_module(flowctl)


class TestEnsureFlowGitignore(unittest.TestCase):
    """`_ensure_flow_gitignore(flow_dir) -> bool` invariants."""

    def test_fresh_write_creates_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            self.assertTrue(flowctl._ensure_flow_gitignore(flow_dir))
            content = (flow_dir / ".gitignore").read_text(encoding="utf-8")
            self.assertIn(flowctl.FLOW_GITIGNORE_AUTO_HEADER, content)
            self.assertIn(flowctl.FLOW_GITIGNORE_AUTO_FOOTER, content)
            for pattern in flowctl.FLOW_GITIGNORE_AUTO_PATTERNS:
                self.assertIn(pattern, content)

    def test_idempotent_when_managed_block_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            flowctl._ensure_flow_gitignore(flow_dir)
            mtime_before = (flow_dir / ".gitignore").stat().st_mtime
            # Sleep would slow tests; rely on os.utime to advance comparison
            os.utime(flow_dir / ".gitignore", (mtime_before - 100, mtime_before - 100))
            self.assertFalse(flowctl._ensure_flow_gitignore(flow_dir))
            self.assertEqual(
                (flow_dir / ".gitignore").stat().st_mtime, mtime_before - 100
            )

    def test_existing_user_gitignore_preserved_at_bottom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            (flow_dir / ".gitignore").write_text(
                "user-pattern-A — UTF-8\n# user comment\n*.local\n",
                encoding="utf-8",
            )
            self.assertTrue(flowctl._ensure_flow_gitignore(flow_dir))
            content = (flow_dir / ".gitignore").read_text(encoding="utf-8")
            # Auto block sits at top; user content survives below.
            self.assertTrue(content.startswith(flowctl.FLOW_GITIGNORE_AUTO_HEADER))
            self.assertIn("user-pattern-A", content)
            self.assertIn("user-pattern-A — UTF-8", content)
            self.assertIn("*.local", content)
            # And the auto-managed footer comes before user content.
            footer_idx = content.index(flowctl.FLOW_GITIGNORE_AUTO_FOOTER)
            user_idx = content.index("user-pattern-A")
            self.assertLess(footer_idx, user_idx)

    def test_migrate_transients_in_pattern_set(self) -> None:
        """All four fn-43 transients are in the auto-managed list."""
        for pattern in [
            ".backup-pre-1.0/",
            ".banner-acknowledged",
            ".migrating",
            ".migration-manifest",
        ]:
            self.assertIn(pattern, flowctl.FLOW_GITIGNORE_AUTO_PATTERNS, pattern)

    def test_sync_runs_in_pattern_set(self) -> None:
        """fn-52 tracker-sync receipts dir is auto-ignored (proof-of-work, like receipts/)."""
        self.assertIn("sync-runs/", flowctl.FLOW_GITIGNORE_AUTO_PATTERNS)

    def test_stale_managed_block_is_reconciled(self) -> None:
        """A pre-existing managed block missing a newer pattern is upgraded in
        place — the new pattern is added, user content below the footer survives,
        and the call reports True (changed)."""
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flow_dir.mkdir()
            # Simulate an older managed block (no sync-runs/) + user content below.
            stale_block = "\n".join(
                [
                    flowctl.FLOW_GITIGNORE_AUTO_HEADER,
                    ".checkpoint-*.json",
                    "receipts/",
                    flowctl.FLOW_GITIGNORE_AUTO_FOOTER,
                ]
            )
            (flow_dir / ".gitignore").write_text(
                stale_block + "\n\nuser-pattern-Z — UTF-8\n", encoding="utf-8"
            )
            self.assertTrue(flowctl._ensure_flow_gitignore(flow_dir))
            content = (flow_dir / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("sync-runs/", content)
            self.assertIn("user-pattern-Z", content)  # user content preserved
            self.assertIn("user-pattern-Z — UTF-8", content)
            # Footer still precedes user content (block stays at top).
            self.assertLess(
                content.index(flowctl.FLOW_GITIGNORE_AUTO_FOOTER),
                content.index("user-pattern-Z"),
            )
            # Second call is now a no-op (block current).
            self.assertFalse(flowctl._ensure_flow_gitignore(flow_dir))


class TestCmdInitWritesGitignore(unittest.TestCase):
    """cmd_init writes .flow/.gitignore on fresh init and reports it."""

    def _run_init(self, tmp: Path) -> dict:
        ns = mock.Mock()
        ns.json = True
        captured = {}
        with mock.patch.object(flowctl, "json_output", side_effect=lambda d: captured.update(d)):
            with mock.patch.object(flowctl, "get_flow_dir", return_value=tmp / ".flow"):
                flowctl.cmd_init(ns)
        return captured

    def test_aid_ignore_refresh_and_broad_stage(self) -> None:
        """R6: init keeps aid state local without hiding durable artifacts."""
        user_patterns = "\n# user café\n*.private\n!artifacts/keep.private\n"
        for mode in ("fresh", "existing", "hand-edited"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)

                def git(*args: str) -> subprocess.CompletedProcess:
                    return subprocess.run(
                        ["git", *args], cwd=repo, capture_output=True,
                        text=True, encoding="utf-8", check=True,
                    )

                git("init", "-q")
                flow_dir = repo / ".flow"
                flow_dir.mkdir()
                tracked = ".flow/artifacts/fn-1/pr-cognitive-aid/old.json"
                paths = {
                    tracked: False,  # refresh must never untrack existing files
                    ".flow/artifacts/fn-1/pr-cognitive-aid/new.json": True,
                    ".flow/artifacts/fn-2/pr-cognitive-aid/another.json": True,
                    ".flow/artifacts/fn-1/pr-cognitive-aid/.write.lock": True,
                    ".flow/artifacts/fn-1/pr.html": False,
                    ".flow/artifacts/fn-1/spec.html": False,
                    ".flow/artifacts/fn-1/other-kind/result.json": False,
                    ".flow/artifacts/fn-1/other-kind/.write.lock": False,
                    ".flow/artifacts/fn-1/pr-cognitive-aid/notes.md": False,
                    ".flow/artifacts/fn-249-make-pr-measurement/results.json": False,
                    ".flow/artifacts/fn-249-make-pr-measurement/baseline.md": False,
                    ".flow/artifacts/notes.json": False,
                    ".flow/artifacts/keep.private": False,
                }
                if mode != "fresh":
                    paths[".flow/artifacts/secret.private"] = True
                for path in paths:
                    target = repo / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("{}\n", encoding="utf-8")
                git("add", "--", tracked)
                if mode != "fresh":
                    block = "\n".join([
                        flowctl.FLOW_GITIGNORE_AUTO_HEADER,
                        "receipts/",
                        *(["artifacts/"] if mode == "hand-edited" else []),
                        flowctl.FLOW_GITIGNORE_AUTO_FOOTER,
                    ])
                    (flow_dir / ".gitignore").write_text(
                        block + user_patterns, encoding="utf-8"
                    )
                self._run_init(repo)
                if mode != "fresh":
                    content = (flow_dir / ".gitignore").read_text(encoding="utf-8")
                    self.assertEqual(
                        content.split(flowctl.FLOW_GITIGNORE_AUTO_FOOTER, 1)[1],
                        user_patterns,
                    )
                for path, ignored in paths.items():
                    with self.subTest(path=path):
                        result = subprocess.run(
                            ["git", "check-ignore", "-q", "--", path], cwd=repo,
                            capture_output=True, text=True, encoding="utf-8",
                        )
                        self.assertEqual(result.returncode, 0 if ignored else 1)
                git("add", "-A")
                staged = set(git("ls-files").stdout.splitlines())
                self.assertEqual(staged, {p for p, ignored in paths.items() if not ignored}
                                 | {".flow/.gitignore", ".flow/meta.json", ".flow/config.json"})
                self.assertFalse(flowctl._ensure_flow_gitignore(flow_dir))

    def test_fresh_init_writes_gitignore_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = self._run_init(tmp)
            self.assertTrue(result.get("success"))
            self.assertIn("wrote .gitignore", result.get("actions", []))
            self.assertTrue((tmp / ".flow" / ".gitignore").exists())

    def test_re_init_does_not_re_report_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self._run_init(tmp)
            second = self._run_init(tmp)
            self.assertNotIn("wrote .gitignore", second.get("actions", []))


if __name__ == "__main__":
    unittest.main()
