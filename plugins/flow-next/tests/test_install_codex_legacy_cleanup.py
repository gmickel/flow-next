"""install-codex.sh upgrade cleanup: stale legacy aliases removed, nothing else.

The flow-next-epic-review deprecation alias was removed from the source tree
(fn-124), but install-codex.sh's copy loops only replace skills still present
in source and only copy current prompts -- a stale alias from an older install
would survive upgrades forever. The installer therefore removes EXACTLY:

    ~/.codex/skills/flow-next-epic-review/
    ~/.codex/prompts/epic-review.md

and must never touch unrelated user skills or prompts.

This test runs the real installer against a temp HOME with a pre-seeded
~/.codex containing both stale artifacts plus unrelated user entries, and
asserts the stale ones are gone while the user's own survive. Skipped on
platforms without bash.

Run:
    python3 -m unittest plugins.flow-next.tests.test_install_codex_legacy_cleanup -v
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
INSTALLER = REPO_ROOT / "scripts" / "install-codex.sh"


@unittest.skipIf(shutil.which("bash") is None, "bash not available")
class TestInstallCodexLegacyCleanup(unittest.TestCase):
    def test_stale_aliases_removed_unrelated_survive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            # Stale legacy artifacts (pre-fn-124 install).
            stale_skill = codex / "skills" / "flow-next-epic-review"
            stale_skill.mkdir(parents=True)
            (stale_skill / "SKILL.md").write_text("stale alias\n")
            (codex / "prompts").mkdir(parents=True)
            (codex / "prompts" / "epic-review.md").write_text("stale prompt\n")
            # Unrelated user entries that MUST survive.
            user_skill = codex / "skills" / "my-own-skill"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("mine\n")
            user_prompt = codex / "prompts" / "my-own-prompt.md"
            user_prompt.write_text("mine too\n")

            result = subprocess.run(
                ["bash", str(INSTALLER)],
                cwd=str(REPO_ROOT),
                env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"install-codex.sh failed:\n{result.stdout}\n{result.stderr}",
            )

            # Stale aliases gone.
            self.assertFalse(stale_skill.exists(), "stale legacy skill survived upgrade")
            self.assertFalse(
                (codex / "prompts" / "epic-review.md").exists(),
                "stale legacy prompt survived upgrade",
            )
            # Unrelated user entries untouched.
            self.assertEqual((user_skill / "SKILL.md").read_text(), "mine\n")
            self.assertEqual(user_prompt.read_text(), "mine too\n")
            # Installer still delivers the current prompt set (loop not broken).
            prompts = list((codex / "prompts").glob("*.md"))
            self.assertGreaterEqual(
                len(prompts),
                24,  # 23 shims + the user's own prompt
                f"prompts loop delivered too few files: {sorted(p.name for p in prompts)}",
            )


if __name__ == "__main__":
    unittest.main()
