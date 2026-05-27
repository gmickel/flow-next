"""Cross-platform prose-contract test for the PNPM_HOME hint in /flow-next:map.

The runtime behavior of the PNPM_HOME hint is exercised hermetically in
``plugins/flow-next/scripts/map_smoke_test.sh`` Case 4b. That smoke uses a
bash-shebang ``pnpm`` stub with POSIX ``chmod +x`` exec bits, which does not
translate to Windows Git Bash (NTFS lacks POSIX exec bits; MSYS resolves
executables via PATHEXT). On Windows, Case 4b skips with a precondition.

This unit test runs on the full ubuntu / macos / windows CI matrix and locks
the prose contract — the structural invariants the hint must carry — so
Windows users still get coverage that the actual hint branch is wired into
the skill workflow and names every load-bearing token (PNPM_HOME, pnpm
setup, pnpm bin -g, re-source the shell rc).

The mirror Codex workflow file at ``plugins/flow-next/codex/skills/
flow-next-map/workflow.md`` is checked too — sync-codex.sh regenerates it,
but the prose contract must survive that rewrite pass.
"""

from __future__ import annotations

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CLAUDE_WORKFLOW = (
    REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-map" / "workflow.md"
)
CODEX_WORKFLOW = (
    REPO_ROOT
    / "plugins"
    / "flow-next"
    / "codex"
    / "skills"
    / "flow-next-map"
    / "workflow.md"
)


REQUIRED_HINT_TOKENS = (
    "PNPM_HOME",
    "pnpm setup",
    "pnpm bin -g",
)


class PnpmHomeHintProseContract(unittest.TestCase):
    """The PNPM_HOME hint must be wired into the install-detect branch.

    Verified on every platform in CI so Windows + the Codex mirror keep
    coverage even though the runtime smoke can't easily stub ``pnpm`` under
    MSYS exec semantics.
    """

    def setUp(self) -> None:
        self.assertTrue(
            CLAUDE_WORKFLOW.exists(),
            f"Canonical Claude workflow.md missing at {CLAUDE_WORKFLOW}",
        )
        self.assertTrue(
            CODEX_WORKFLOW.exists(),
            f"Codex mirror workflow.md missing at {CODEX_WORKFLOW}",
        )
        self.claude_text = CLAUDE_WORKFLOW.read_text(encoding="utf-8")
        self.codex_text = CODEX_WORKFLOW.read_text(encoding="utf-8")

    def test_claude_workflow_carries_all_hint_tokens(self) -> None:
        """Each load-bearing token must appear in the canonical Claude workflow."""

        for token in REQUIRED_HINT_TOKENS:
            with self.subTest(token=token, file="claude"):
                self.assertIn(
                    token,
                    self.claude_text,
                    f"Canonical workflow.md missing required hint token: {token!r}",
                )

    def test_codex_mirror_carries_all_hint_tokens(self) -> None:
        """Same contract on the Codex mirror (sync-codex.sh must preserve it)."""

        for token in REQUIRED_HINT_TOKENS:
            with self.subTest(token=token, file="codex"):
                self.assertIn(
                    token,
                    self.codex_text,
                    f"Codex mirror workflow.md missing required hint token: {token!r}",
                )

    def test_hint_branch_is_inside_install_detect_path(self) -> None:
        """The hint must fire only when pnpm is on PATH AND clawpatch is not.

        Lock in the exact branch structure so a future refactor can't
        accidentally surface the hint when clawpatch IS installed (would be
        actively misleading).
        """

        # The hint must appear AFTER the "clawpatch not found" exit branch's
        # install instructions ('pnpm add -g clawpatch') — i.e. inside the
        # missing-binary branch, not at top-of-file or after a successful
        # detection.
        install_idx = self.claude_text.find("pnpm add -g clawpatch")
        hint_idx = self.claude_text.find("PNPM_HOME")
        self.assertGreater(
            install_idx,
            -1,
            "Canonical workflow.md must surface the install instruction",
        )
        self.assertGreater(
            hint_idx,
            install_idx,
            "PNPM_HOME hint must follow the install-instructions block "
            "(it's part of the missing-binary branch, not a separate section)",
        )

    def test_hint_branch_is_guarded_by_pnpm_probe(self) -> None:
        """The hint must be inside an ``if command -v pnpm`` guard.

        Without the guard, the hint would print even on systems without
        pnpm — which would be wrong because the actionable advice (`pnpm
        setup`) requires pnpm to be installed in the first place.

        Locking the guard via proximity: ``command -v pnpm`` must appear
        within 500 chars of *some* PNPM_HOME mention. The literal pattern
        used in the skill is ``command -v pnpm >/dev/null 2>&1 && pnpm bin
        -g >/dev/null 2>&1`` and the hint body follows directly. Anchoring
        on proximity (rather than which-came-first) keeps the assertion
        robust to comment-line re-ordering inside the branch.
        """

        # All PNPM_HOME occurrences AND all `command -v pnpm` occurrences;
        # require at least one pair within 500 chars of each other.
        pnpm_home_positions = [m.start() for m in re.finditer(r"PNPM_HOME", self.claude_text)]
        guard_positions = [m.start() for m in re.finditer(r"command -v pnpm\b", self.claude_text)]

        self.assertTrue(pnpm_home_positions, "PNPM_HOME hint missing")
        self.assertTrue(
            guard_positions,
            "`command -v pnpm` guard missing — without it the PNPM_HOME "
            "hint would surface even when pnpm isn't installed",
        )

        for hint in pnpm_home_positions:
            if any(abs(g - hint) < 500 for g in guard_positions):
                return  # at least one PNPM_HOME mention is co-located with the guard
        self.fail(
            "No PNPM_HOME mention is within 500 chars of a `command -v "
            "pnpm` guard — the hint branch must be inside the pnpm-probe "
            "block, not a free-standing section"
        )

    def test_hint_recommends_reopening_shell(self) -> None:
        """The hint must instruct re-sourcing/re-opening shell after pnpm setup.

        On Windows, pnpm setup writes to user env vars via the registry; the
        change does NOT propagate to the existing shell. The hint must
        surface this so users don't try ``pnpm setup`` and then re-run map
        in the same shell and hit the same error.
        """

        for label, text in (("claude", self.claude_text), ("codex", self.codex_text)):
            with self.subTest(file=label):
                # Match any of: "re-source", "new shell", "open a new shell",
                # "reopen", "re-open" — flexible on wording but lock the
                # intent.
                self.assertRegex(
                    text,
                    r"(re-?source|new shell|re-?open)",
                    "Hint must recommend re-sourcing the shell rc or "
                    "opening a new shell after `pnpm setup` (otherwise "
                    "the PATH change won't take effect in the current "
                    "shell — same trap, just one step further)",
                )


if __name__ == "__main__":
    unittest.main()
