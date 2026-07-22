"""install-codex.sh upgrade cleanup: stale legacy aliases removed, nothing else.

The flow-next-epic-review deprecation alias was removed from the source tree
(fn-124), but install-codex.sh's copy loops only replace skills still present
in source and only copy current prompts -- a stale alias from an older install
would survive upgrades forever. The installer therefore removes EXACTLY:

    ~/.codex/skills/flow-next-epic-review/
    ~/.codex/prompts/epic-review.md

and must never touch unrelated user skills or prompts. Because ``epic-review.md``
is a generic prompt name a user could legitimately author -- and body text can
be mimicked -- deletion is gated on an EXACT match of the generator's own
frontmatter ``name:`` id, which a hand-authored file will not carry:
  - retired command-shim prompt: ``name: flow-next:epic-review``
  - retired generated skill:     ``name: flow-next-epic-review``

These tests run the real installer against a temp HOME and assert:
  1. flow-next's own stale artifacts (exact frontmatter id) are removed, the
     current canonical prompt set is delivered exactly, and unrelated user
     entries survive;
  2. a user-authored ``epic-review.md`` is preserved even when its BODY mimics
     the redirect text -- because its frontmatter id is not ours.
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

# The installer gates deletion on an EXACT frontmatter `name:` id (see
# scripts/install-codex.sh frontmatter_name). These are the generator's own ids.
SKILL_BODY = (
    "---\nname: flow-next-epic-review\n"
    'description: "[deprecated alias] Renamed to flow-next-spec-completion-review."\n'
    "---\n\n# renamed to flow-next-spec-completion-review\n"
    "Invoke the flow-next-spec-completion-review skill instead.\n"
)
PROMPT_BODY = (
    "---\nname: flow-next:epic-review\n"
    'description: "[deprecated] Renamed to /flow-next:spec-completion-review"\n'
    "---\n\n# `/flow-next:epic-review` is renamed to `/flow-next:spec-completion-review`\n"
    "Invoke the flow-next-spec-completion-review skill now.\n"
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
            # Stale flow-next artifacts (pre-fn-124), exact frontmatter id.
            stale_skill = codex / "skills" / "flow-next-epic-review"
            stale_skill.mkdir(parents=True)
            (stale_skill / "SKILL.md").write_text(SKILL_BODY)
            (codex / "prompts").mkdir(parents=True)
            (codex / "prompts" / "epic-review.md").write_text(PROMPT_BODY)
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
            # prompts. Set-based, not count-only: every canonical shim present,
            # the retired epic-review alias absent, and no OTHER canonical-named
            # prompt lingering. (The user's own prompt is expected alongside.)
            installed = {p.name for p in (codex / "prompts").glob("*.md")}
            expected = {p.name for p in COMMANDS_DIR.glob("*.md")}
            self.assertTrue(expected, "no canonical command shims found in source")
            self.assertNotIn("epic-review.md", expected, "epic-review shim not deleted from source")
            # The flow-next-owned prompt subset installed == exactly the canonical set.
            installed_canonical = installed & (expected | {"epic-review.md"})
            self.assertEqual(
                installed_canonical,
                expected,
                f"delivered flow-next prompts != canonical set: "
                f"missing={sorted(expected - installed)} "
                f"stale={sorted(installed_canonical - expected)}",
            )
            # The user's own prompt still there alongside the canonical set.
            self.assertIn("my-own-prompt.md", installed)

    def test_user_authored_epic_review_prompt_is_preserved(self) -> None:
        # A user's OWN epic-review.md must NOT be deleted by the upgrade cleanup
        # (the HIGH finding from the sol review). Deletion is gated on the exact
        # frontmatter `name:` id, so these user files -- including one whose BODY
        # deliberately mimics the flow-next redirect text (the adversarial
        # migration-wrapper case) -- must all survive, because none carries the
        # `name: flow-next:epic-review` frontmatter id:
        cases = {
            "no-frontmatter": "# My own epic review checklist\n- step 1\n",
            "own-frontmatter-name": (
                "---\nname: epic-review\n---\n\n# My epic review\n- step 1\n"
            ),
            "body-mimics-redirect": (  # sol's adversarial example
                "---\nname: my-epic-review\n---\n\n# My epic review\n"
                "Flow Next renamed epic-review to flow-next-spec-completion-review.\n"
                "Run that review, then apply our private release checklist.\n"
            ),
        }
        for label, body in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                codex = home / ".codex"
                (codex / "prompts").mkdir(parents=True)
                user_epic = codex / "prompts" / "epic-review.md"
                user_epic.write_text(body)

                result = _run_installer(home)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"install-codex.sh failed:\n{result.stdout}\n{result.stderr}",
                )

                self.assertTrue(
                    user_epic.exists(),
                    f"[{label}] user-authored epic-review.md was deleted",
                )
                self.assertEqual(
                    user_epic.read_text(),
                    body,
                    f"[{label}] user-authored epic-review.md was modified",
                )


if __name__ == "__main__":
    unittest.main()
