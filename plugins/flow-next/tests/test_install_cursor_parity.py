"""Drift guard: the Cursor installers (bash + PowerShell) must agree.

flow-next ships two Cursor local-installers:

    scripts/install-cursor.sh    -- macOS / Linux (rsync, tar fallback)
    scripts/install-cursor.ps1   -- Windows (robocopy)

They must stay behaviorally in lockstep: same destination
(~/.cursor/plugins/local/flow-next), same exclude set (the Codex mirror, tests,
and Python/OS cruft must never leak into a Cursor install), and the same
real-directory contract (Cursor's plugin loader rejects a symlink whose realpath
escapes ~/.cursor, so NEITHER installer may symlink).

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


if __name__ == "__main__":
    unittest.main()
