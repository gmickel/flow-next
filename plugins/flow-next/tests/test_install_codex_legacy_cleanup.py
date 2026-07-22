"""install-codex.sh upgrade cleanup: stale legacy aliases removed, nothing else.

The flow-next-epic-review deprecation alias was removed from the source tree
(fn-124), but install-codex.sh's copy loops only replace skills still present
in source and only copy current prompts -- a stale alias from an older install
would survive upgrades forever. The installer therefore removes EXACTLY:

    ~/.codex/skills/flow-next-epic-review/
    ~/.codex/prompts/epic-review.md

and must never touch unrelated user skills or prompts. Because ``epic-review.md``
is a generic prompt name a user could legitimately author, deletion is gated on
an OWNERSHIP SENTINEL: the flow-next redirect body names
``flow-next-spec-completion-review``. A same-named file WITHOUT that marker is
the user's own and is preserved.

These tests run the real installer against a temp HOME and assert:
  1. flow-next's own stale artifacts (sentinel present) are removed, the current
     canonical prompt set is delivered, and unrelated user entries survive;
  2. a user-authored ``epic-review.md`` (no sentinel) is NOT deleted.
Skipped on native Windows (plain ``bash`` there resolves to the WSL stub).

Run:
    python3 -m unittest plugins.flow-next.tests.test_install_codex_legacy_cleanup -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
INSTALLER = REPO_ROOT / "scripts" / "install-codex.sh"
COMMANDS_DIR = REPO_ROOT / "plugins" / "flow-next" / "commands"

# The ownership sentinel the installer greps for before deleting (must match
# scripts/install-codex.sh LEGACY_SENTINEL).
SENTINEL = "flow-next-spec-completion-review"

# A realistic flow-next legacy redirect body carrying the sentinel.
LEGACY_BODY = (
    "---\nname: flow-next-epic-review\n---\n\n"
    "This alias is renamed to flow-next-spec-completion-review. "
    "Invoke the flow-next-spec-completion-review skill instead.\n"
)


def _run_installer(home: Path) -> subprocess.CompletedProcess:
    # Preserve the runner environment (Git Bash on Windows needs SystemRoot
    # etc.); only HOME is redirected to the temp dir.
    env = dict(os.environ, HOME=str(home))
    return subprocess.run(
        ["bash", str(INSTALLER)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


@unittest.skipIf(
    sys.platform == "win32",
    "POSIX shell installer test; plain `bash` on Windows resolves to the WSL stub",
)
@unittest.skipIf(shutil.which("bash") is None, "bash not available")
class TestInstallCodexLegacyCleanup(unittest.TestCase):
    def test_flow_next_stale_alias_removed_unrelated_survive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            # Stale flow-next artifacts (pre-fn-124), sentinel present.
            stale_skill = codex / "skills" / "flow-next-epic-review"
            stale_skill.mkdir(parents=True)
            (stale_skill / "SKILL.md").write_text(LEGACY_BODY)
            (codex / "prompts").mkdir(parents=True)
            (codex / "prompts" / "epic-review.md").write_text(LEGACY_BODY)
            # Unrelated user entries that MUST survive.
            user_skill = codex / "skills" / "my-own-skill"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("mine\n")
            user_prompt = codex / "prompts" / "my-own-prompt.md"
            user_prompt.write_text("mine too\n")

            result = _run_installer(home)
            self.assertEqual(
                result.returncode,
                0,
                f"install-codex.sh failed:\n{result.stdout}\n{result.stderr}",
            )

            # flow-next's own stale artifacts gone.
            self.assertFalse(stale_skill.exists(), "stale legacy skill survived upgrade")
            self.assertFalse(
                (codex / "prompts" / "epic-review.md").exists(),
                "stale legacy prompt survived upgrade",
            )
            # Unrelated user entries untouched.
            self.assertEqual((user_skill / "SKILL.md").read_text(), "mine\n")
            self.assertEqual(user_prompt.read_text(), "mine too\n")

            # Installer delivers EXACTLY the current canonical command set as
            # prompts (count-only would pass if extras masked a missing shim).
            installed = {p.name for p in (codex / "prompts").glob("*.md")}
            expected = {p.name for p in COMMANDS_DIR.glob("*.md")}
            self.assertTrue(expected, "no canonical command shims found in source")
            missing = expected - installed
            self.assertFalse(missing, f"canonical prompts not installed: {sorted(missing)}")
            # epic-review must NOT be among the canonical set (alias retired).
            self.assertNotIn("epic-review.md", expected, "epic-review shim not deleted from source")
            # The user's own prompt still there alongside the canonical set.
            self.assertIn("my-own-prompt.md", installed)

    def test_user_authored_epic_review_prompt_is_preserved(self) -> None:
        # A user's OWN epic-review.md (no flow-next sentinel) must NOT be
        # deleted by the upgrade cleanup — the HIGH finding from the sol review.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            (codex / "prompts").mkdir(parents=True)
            user_epic = codex / "prompts" / "epic-review.md"
            user_epic.write_text("# My own epic review checklist\n- step 1\n")

            result = _run_installer(home)
            self.assertEqual(
                result.returncode,
                0,
                f"install-codex.sh failed:\n{result.stdout}\n{result.stderr}",
            )

            self.assertTrue(
                user_epic.exists(),
                "user-authored epic-review.md (no flow-next sentinel) was deleted",
            )
            self.assertEqual(
                user_epic.read_text(),
                "# My own epic review checklist\n- step 1\n",
                "user-authored epic-review.md was modified",
            )


if __name__ == "__main__":
    unittest.main()
