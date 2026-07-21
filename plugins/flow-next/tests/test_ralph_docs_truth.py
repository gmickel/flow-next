"""fn-114.4 - Ralph docs truth-up pins (shipped .1-.3 state).

Pins prose contracts on the three public surfaces + flowctl CLI ref:
  * ralph.md: opt-in zero-default, ralphctl control, soft-probe, no plugin hooks.json path
  * platforms.md: zero-default + retained [features] hooks=true note
  * CLAUDE.md checklist: ralph-init owns registration (no plugin-level hooks)
  * flowctl.md: no flowctl ralph subcommand; points at ralphctl.py
  * CHANGELOG Unreleased: upgrade re-run-ralph-init note
"""

from __future__ import annotations

import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent

RALPH_MD = PLUGIN_DIR / "docs" / "ralph.md"
PLATFORMS_MD = PLUGIN_DIR / "docs" / "platforms.md"
FLOWCTL_MD = PLUGIN_DIR / "docs" / "flowctl.md"
SYNC_CODEX_MD = PLUGIN_DIR / "docs" / "sync-codex.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestRalphDocsTruth(unittest.TestCase):
    def test_ralph_md_opt_in_and_control_surface(self) -> None:
        text = _read(RALPH_MD)
        self.assertIn("fully opt-in", text.lower())
        self.assertIn("zero hooks", text.lower())
        self.assertIn("ralphctl.py", text)
        self.assertIn("soft-probe", text.lower())
        self.assertIn("promise=COMPLETE", text)
        self.assertIn("key=value", text)
        # Control is NOT flowctl ralph after extraction
        self.assertNotRegex(
            text,
            r"flowctl\s+ralph\s+(pause|resume|stop|status)",
            "ralph.md must not document removed flowctl ralph subcommands",
        )
        # Plugin-level hooks.json location is gone
        self.assertNotIn("hooks/hooks.json              # Config", text)
        self.assertNotIn("plugins/flow-next/\n  hooks/hooks.json", text)
        # Structured done + dual-platform + file-tool receipt in guard table
        self.assertIn("no word sniff", text.lower())
        self.assertIn("ApplyPatch", text)
        self.assertIn("RALPH_GUARD_DEBUG=1", text)

    def test_platforms_md_codex_zero_default_and_hooks_flag(self) -> None:
        text = _read(PLATFORMS_MD)
        self.assertIn("ship `hooks/hooks.json`", text)
        self.assertIn("hooks = true", text)
        self.assertIn("feature flag only", text.lower())
        self.assertNotIn(
            "A pre-built `codex/hooks.json` may exist",
            text,
            "Codex zero-default is complete; no mirror hooks.json",
        )

    def test_claude_md_checklist_ralph_init_owns_registration(self) -> None:
        text = _read(CLAUDE_MD)
        self.assertIn("No plugin-level hooks", text)
        self.assertIn("ralph-init", text)
        self.assertIn("plugins/flow-next/hooks/", text)

    def test_flowctl_md_points_at_ralphctl(self) -> None:
        text = _read(FLOWCTL_MD)
        self.assertIn("ralphctl.py", text)
        self.assertIn("soft-probe", text.lower())
        self.assertNotRegex(
            text,
            r"flowctl\s+ralph\s+(status|pause|resume|stop)",
            "flowctl.md must not list flowctl ralph commands",
        )
        # Available Commands list must not advertise ralph group
        avail = text.split("## Available Commands", 1)[1].split("##", 1)[0]
        self.assertNotRegex(avail, r"\bralph\b")

    def test_sync_codex_md_zero_default_hooks(self) -> None:
        text = _read(SYNC_CODEX_MD)
        self.assertIn("No `hooks.json`", text)
        self.assertNotIn("Generate hooks.json", text)
        self.assertNotIn("plugins/flow-next/hooks/hooks.json", text)

    def test_changelog_upgrade_note(self) -> None:
        text = _read(CHANGELOG)
        # Bound to the top of the changelog: Unreleased before the batched
        # release, the newest released entry after it (batched-release-proof).
        # Scan the top TWO sections, not one - a fresh Unreleased opened for a
        # LATER spec sits above the released section that carries this note
        # (fn-121 exposed the single-section scan).
        head_marker = "## [Unreleased]" if "## [Unreleased]" in text else "## ["
        after = text.split(head_marker, 1)[1]
        parts = after.split("\n## [", 2)
        unreleased = "\n".join(parts[:2])
        self.assertIn("fn-114", unreleased)
        self.assertIn("re-run `/flow-next:ralph-init`", unreleased)
        self.assertIn("Upgrade note", unreleased)
        self.assertIn("ralphctl.py", unreleased)
        self.assertIn("hooks = true", unreleased)


if __name__ == "__main__":
    unittest.main()
