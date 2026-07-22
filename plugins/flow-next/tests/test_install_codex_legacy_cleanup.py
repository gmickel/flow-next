"""install-codex.sh upgrade cleanup: stale legacy alias RETIRED non-destructively.

The flow-next-epic-review deprecation alias was removed from the source tree
(fn-124), but install-codex.sh's copy loops only replace skills still present
in source and only copy current prompts -- a stale alias from an older install
would keep surfacing as a live redirect forever. On upgrade the installer
retires exactly:

    ~/.codex/skills/flow-next-epic-review/
    ~/.codex/prompts/epic-review.md

Two safety layers (see scripts/install-codex.sh):
  1. Identity gate -- act ONLY when the artifact's leading-frontmatter ``name:``
     is EXACTLY the generator's own id (``flow-next:epic-review`` for the prompt,
     ``flow-next-epic-review`` for the skill). Body-text is NOT used (a user
     migration wrapper can mimic it); frontmatter id is what our tooling wrote.
  2. Non-destructive move -- even on a match nothing is deleted. The artifact is
     MOVED into ``~/.codex/.flow-next-retired/`` (outside the scanned skills/ +
     prompts/ trees), so it stops surfacing but every byte is preserved and
     restorable. So even the pathological case (a user file that really does
     carry our exact id) loses nothing -- it is relocated, not destroyed.

These tests run the real installer against a temp HOME and assert:
  1. flow-next's own stale artifacts are de-surfaced AND recoverable, the
     canonical prompt set is delivered exactly, unrelated user entries survive;
  2. user files whose frontmatter id is NOT ours are left untouched in place --
     including one whose BODY mimics the redirect text;
  3. even a file carrying our EXACT id is relocated (not destroyed) -- its bytes
     survive under the retired-backups dir.
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

# Deletion is gated on an EXACT frontmatter `name:` id (see
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
    def test_flow_next_stale_alias_retired_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            # Stale flow-next artifacts (pre-fn-124), exact frontmatter id.
            stale_skill = codex / "skills" / "flow-next-epic-review"
            stale_skill.mkdir(parents=True)
            (stale_skill / "SKILL.md").write_text(SKILL_BODY)
            (codex / "prompts").mkdir(parents=True)
            stale_prompt = codex / "prompts" / "epic-review.md"
            stale_prompt.write_text(PROMPT_BODY)
            # Unrelated user entries that MUST survive in place.
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

            # De-surfaced from the scanned trees...
            self.assertFalse(stale_skill.exists(), "stale legacy skill still surfaced")
            self.assertFalse(stale_prompt.exists(), "stale legacy prompt still surfaced")
            # ...but preserved (recoverable) under the retired-backups dir.
            retired = codex / ".flow-next-retired"
            self.assertEqual(
                (retired / "skills" / "flow-next-epic-review" / "SKILL.md").read_text(),
                SKILL_BODY,
                "retired skill not preserved byte-for-byte",
            )
            self.assertEqual(
                (retired / "prompts" / "epic-review.md").read_text(),
                PROMPT_BODY,
                "retired prompt not preserved byte-for-byte",
            )
            # Unrelated user entries untouched in place.
            self.assertEqual((user_skill / "SKILL.md").read_text(), "mine\n")
            self.assertEqual(user_prompt.read_text(), "mine too\n")

            # Installer delivers EXACTLY the current canonical command set as
            # prompts. Set-based, not count-only: every canonical shim present,
            # the retired epic-review alias absent from the live surface, and no
            # OTHER canonical-named prompt lingering. (User prompt expected too.)
            installed = {p.name for p in (codex / "prompts").glob("*.md")}
            expected = {p.name for p in COMMANDS_DIR.glob("*.md")}
            self.assertTrue(expected, "no canonical command shims found in source")
            self.assertNotIn("epic-review.md", expected, "epic-review shim not deleted from source")
            installed_canonical = installed & (expected | {"epic-review.md"})
            self.assertEqual(
                installed_canonical,
                expected,
                f"delivered flow-next prompts != canonical set: "
                f"missing={sorted(expected - installed)} "
                f"stale={sorted(installed_canonical - expected)}",
            )
            self.assertIn("my-own-prompt.md", installed)

    def test_user_file_without_our_id_is_untouched(self) -> None:
        # A user's OWN epic-review.md whose frontmatter id is NOT ours must be
        # left untouched IN PLACE (not even relocated). Includes the adversarial
        # case whose BODY mimics the redirect text (sol review) -- body is never
        # a signal, only the frontmatter id is.
        cases = {
            "no-frontmatter": "# My own epic review checklist\n- step 1\n",
            "own-frontmatter-name": (
                "---\nname: epic-review\n---\n\n# My epic review\n- step 1\n"
            ),
            "body-mimics-redirect": (
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
                self.assertEqual(result.returncode, 0, result.stderr)

                self.assertTrue(user_epic.exists(), f"[{label}] user file was moved/deleted")
                self.assertEqual(user_epic.read_text(), body, f"[{label}] user file modified")
                # Never relocated to the retired dir either.
                self.assertFalse(
                    (codex / ".flow-next-retired" / "prompts" / "epic-review.md").exists(),
                    f"[{label}] user file was wrongly retired",
                )

    def test_exact_id_file_is_relocated_not_destroyed(self) -> None:
        # The pathological case: a file that genuinely carries our exact
        # frontmatter id but custom body. It IS de-surfaced (treated as our
        # retired shim) -- but non-destructively: nothing is deleted, the bytes
        # survive under the retired-backups dir and are restorable.
        custom = PROMPT_BODY.replace(
            "Invoke the flow-next-spec-completion-review skill now.\n",
            "Run the renamed review, then my private release checklist.\n",
        )
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            (codex / "prompts").mkdir(parents=True)
            (codex / "prompts" / "epic-review.md").write_text(custom)

            result = _run_installer(home)
            self.assertEqual(result.returncode, 0, result.stderr)

            self.assertFalse(
                (codex / "prompts" / "epic-review.md").exists(),
                "exact-id file should be de-surfaced from prompts/",
            )
            self.assertEqual(
                (codex / ".flow-next-retired" / "prompts" / "epic-review.md").read_text(),
                custom,
                "exact-id file was not preserved byte-for-byte on retirement",
            )

    def test_retirement_never_clobbers_a_prior_backup(self) -> None:
        # No-clobber: if a backup already exists (a user recreated the live alias
        # with DIFFERENT content between upgrades), retiring the new one must NOT
        # overwrite the earlier backup — both survive under distinct names.
        body_a = PROMPT_BODY.replace("skill now.\n", "skill now. VARIANT-A\n")
        body_b = PROMPT_BODY.replace("skill now.\n", "skill now. VARIANT-B\n")
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            retired_prompts = codex / ".flow-next-retired" / "prompts"
            retired_prompts.mkdir(parents=True)
            # An earlier retirement already parked body A here.
            (retired_prompts / "epic-review.md").write_text(body_a)
            # A freshly-recreated live exact-id alias carrying body B.
            (codex / "prompts").mkdir(parents=True)
            (codex / "prompts" / "epic-review.md").write_text(body_b)

            result = _run_installer(home)
            self.assertEqual(result.returncode, 0, result.stderr)

            # Live alias de-surfaced.
            self.assertFalse((codex / "prompts" / "epic-review.md").exists())
            # BOTH backups intact — A untouched, B parked under a fresh name.
            self.assertEqual(
                (retired_prompts / "epic-review.md").read_text(),
                body_a,
                "prior backup A was clobbered",
            )
            parked = sorted(p for p in retired_prompts.glob("epic-review.md*")
                            if p.name != "epic-review.md")
            self.assertTrue(parked, "recreated alias B was not parked under a new name")
            self.assertIn(body_b, [p.read_text() for p in parked], "body B not preserved")

    def test_second_run_is_idempotent_no_op(self) -> None:
        # A plain second run (no live alias recreated) must not touch backups.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex = home / ".codex"
            stale_prompt = codex / "prompts"
            stale_prompt.mkdir(parents=True)
            (stale_prompt / "epic-review.md").write_text(PROMPT_BODY)

            self.assertEqual(_run_installer(home).returncode, 0)
            first = (codex / ".flow-next-retired" / "prompts" / "epic-review.md").read_text()
            self.assertEqual(first, PROMPT_BODY)
            self.assertFalse((codex / "prompts" / "epic-review.md").exists())

            # Second run: nothing to retire, backups unchanged, no duplicates.
            self.assertEqual(_run_installer(home).returncode, 0)
            retired = codex / ".flow-next-retired" / "prompts"
            backups = sorted(retired.glob("epic-review.md*"))
            self.assertEqual(
                [p.name for p in backups],
                ["epic-review.md"],
                f"second run created spurious backups: {[p.name for p in backups]}",
            )
            self.assertEqual((retired / "epic-review.md").read_text(), PROMPT_BODY)


if __name__ == "__main__":
    unittest.main()
