"""Unit tests for `_ensure_flow_gitignore` and its integration into `cmd_init`
and `cmd_migrate_rename`. Covers fresh write, idempotency, user-pattern
preservation, and the migrate-rename hook."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

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
            content = (flow_dir / ".gitignore").read_text()
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
            (flow_dir / ".gitignore").write_text("user-pattern-A\n# user comment\n*.local\n")
            self.assertTrue(flowctl._ensure_flow_gitignore(flow_dir))
            content = (flow_dir / ".gitignore").read_text()
            # Auto block sits at top; user content survives below.
            self.assertTrue(content.startswith(flowctl.FLOW_GITIGNORE_AUTO_HEADER))
            self.assertIn("user-pattern-A", content)
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
            (flow_dir / ".gitignore").write_text(stale_block + "\n\nuser-pattern-Z\n")
            self.assertTrue(flowctl._ensure_flow_gitignore(flow_dir))
            content = (flow_dir / ".gitignore").read_text()
            self.assertIn("sync-runs/", content)
            self.assertIn("user-pattern-Z", content)  # user content preserved
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
