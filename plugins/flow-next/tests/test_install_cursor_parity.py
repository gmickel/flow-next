"""Drift guard: the Cursor installers (bash + PowerShell) must agree.

flow-next ships two Cursor local-installers:

    scripts/install-cursor.sh    -- macOS / Linux (rsync, tar fallback)
    scripts/install-cursor.ps1   -- Windows (robocopy)

They must stay behaviorally in lockstep: same destination
(~/.cursor/plugins/local/flow-next), same exclude set (the Codex mirror, tests,
and Python/OS cruft must never leak into a Cursor install), the same
real-directory contract (Cursor's plugin loader rejects a symlink whose realpath
escapes ~/.cursor, so NEITHER installer may symlink), and both must surface the
rules/ rail (flow-next.mdc) in their install summary so a rules-only drop is
visible on re-install.

Without this guard, adding an exclude (or fixing the dest) in one script and
forgetting the other ships a divergent install on the other OS -- exactly the
class of slip the dual-copy / dogfood-parity guards exist to prevent.

Pure text containment checks -- no shell/PowerShell execution -- so this runs on
every CI leg (ubuntu / macos / windows) without needing rsync or pwsh present.

Run:
    python3 -m unittest plugins.flow-next.tests.test_install_cursor_parity -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent           # plugins/flow-next
REPO_ROOT = PLUGIN_DIR.parent.parent      # repo root

SH = REPO_ROOT / "scripts" / "install-cursor.sh"
PS1 = REPO_ROOT / "scripts" / "install-cursor.ps1"

# The canonical things both installers must keep out of a Cursor install.
EXCLUDE_TOKENS = ["codex", "tests", "__pycache__", "*.pyc", ".DS_Store"]


class TestInstallCursorParity(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SH.is_file(), f"missing {SH.relative_to(REPO_ROOT)}")
        self.assertTrue(PS1.is_file(), f"missing {PS1.relative_to(REPO_ROOT)}")
        self.sh = SH.read_text(encoding="utf-8")
        self.ps1 = PS1.read_text(encoding="utf-8")

    def test_both_target_cursor_local_plugins(self) -> None:
        # bash uses forward slashes, PowerShell uses backslashes.
        self.assertIn(".cursor/plugins/local", self.sh)
        self.assertIn(".cursor\\plugins\\local", self.ps1)

    def test_exclude_sets_match(self) -> None:
        for token in EXCLUDE_TOKENS:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.sh,
                    f"install-cursor.sh no longer excludes '{token}' -- "
                    f"the two Cursor installers have drifted (update both).",
                )
                self.assertIn(
                    token,
                    self.ps1,
                    f"install-cursor.ps1 no longer excludes '{token}' -- "
                    f"the two Cursor installers have drifted (update both).",
                )

    def test_neither_installer_symlinks(self) -> None:
        # Real-dir contract: Cursor's plugin loader rejects symlinks escaping ~/.cursor.
        self.assertNotIn("ln -s", self.sh)
        self.assertNotRegex(self.ps1, r"(?i)New-Item[^\n]*SymbolicLink")

    def test_ps1_uses_robocopy_mirror(self) -> None:
        # robocopy is the Windows-native rsync analogue; /MIR is the --delete analogue.
        self.assertIn("robocopy", self.ps1)
        self.assertIn("/MIR", self.ps1)

    def test_sh_uses_rsync_delete(self) -> None:
        self.assertIn("rsync", self.sh)
        self.assertIn("--delete", self.sh)

    def test_installers_purge_excluded_paths(self) -> None:
        # A stale excluded dir (e.g. codex/) left in the dest must be removed so the
        # install is a TRUE mirror — setup's Cursor-vs-Codex detection keys on codex/
        # being absent. rsync --delete alone does NOT remove excluded paths; robocopy
        # /MIR + /XD skips excluded dirs from its purge. Both need explicit handling.
        self.assertIn(
            "--delete-excluded",
            self.sh,
            "install-cursor.sh must pass rsync --delete-excluded so a stale "
            "excluded codex/ is removed from the dest (plain --delete won't).",
        )
        # PowerShell side: explicit Remove-Item of the excluded dirs after robocopy.
        self.assertRegex(
            self.ps1,
            r"(?is)Remove-Item.*codex",
            "install-cursor.ps1 must explicitly Remove-Item the excluded dirs "
            "(robocopy /MIR + /XD does not purge them).",
        )

    def test_both_surface_rules_in_install_summary(self) -> None:
        # fn-123 R9: rules/flow-next.mdc is part of the Cursor surface. The
        # installers already copy the whole plugin tree (rules/ included via
        # non-exclude); both must report the rules count so operators see the
        # guidance rail landed.
        self.assertRegex(
            self.sh,
            r"rules/.*\.mdc|rules:\s+",
            "install-cursor.sh must mention rules (*.mdc) in comments or summary",
        )
        self.assertRegex(
            self.ps1,
            r"rules\\.*\.mdc|rules:\s+",
            "install-cursor.ps1 must mention rules (*.mdc) in comments or summary",
        )
        # Source rule must exist so a clean install has something to copy.
        rule = PLUGIN_DIR / "rules" / "flow-next.mdc"
        self.assertTrue(
            rule.is_file(),
            f"missing {rule.relative_to(REPO_ROOT)} — installers copy rules/",
        )


if __name__ == "__main__":
    unittest.main()
