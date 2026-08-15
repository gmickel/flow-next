"""fn-123 R3/R6 — Cursor-host-aware setup prose contracts.

Locks the setup workflow (canonical only — Codex mirror is a generated
rewrite and is not the Cursor host path) for:

  (a) Positive Cursor detection — PLUGIN_ROOT under ~/.cursor/; never keys on
      ``codex/`` directory absence (marketplace whole-repo imports contain
      ``codex/`` and must still classify as cursor).
  (b) Host-leads review menu on PLATFORM=cursor; Cursor CLI labeled
      circular/secondary; other backends remain selectable.
  (c) [removed in fn-195.2] the host-native pin scaffold — setup now proposes
      one commented routing block; its contract lives in
      test_model_routing_scaffold.py.
  (d) No Ralph offer/registration on Cursor.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_setup_cursor_host -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
WORKFLOW = PLUGIN / "skills" / "flow-next-setup" / "workflow.md"
CURSOR_REFS = (
    PLUGIN / "skills" / "flow-next-setup" / "references" / "ralph-question.md",
)


def _read() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (WORKFLOW, *CURSOR_REFS)
    )


class TestCursorPositiveDetection(unittest.TestCase):
    """R3: detection never depends on codex/ absence."""

    def setUp(self) -> None:
        self.assertTrue(WORKFLOW.is_file(), f"missing {WORKFLOW}")
        self.text = _read()

    def test_no_codex_absence_rung(self) -> None:
        # Old misclassifier — must be gone from the detection branch.
        self.assertNotIn('[ ! -d "${PLUGIN_ROOT}/codex" ]', self.text)
        self.assertNotIn("[ ! -d \"${PLUGIN_ROOT}/codex\" ]", self.text)
        # Prose must not re-teach the absence rung as the discriminator.
        self.assertNotRegex(
            self.text,
            re.compile(
                r"Requiring `codex/` to be \*\*absent\*\*",
                re.IGNORECASE,
            ),
        )

    def test_positive_cursor_home_path_signal(self) -> None:
        # Positive discriminator: PLUGIN_ROOT under ~/.cursor (CURSOR_HOME_ABS).
        self.assertIn("CURSOR_HOME_ABS", self.text)
        self.assertIn("PLUGIN_ROOT_ABS", self.text)
        self.assertIn("${HOME}/.cursor", self.text)
        self.assertIn('"${CURSOR_HOME_ABS}"/*', self.text)
        # Still requires CURSOR_AGENT + .cursor-plugin manifest.
        self.assertIn("${CURSOR_AGENT:-}", self.text)
        self.assertIn(".cursor-plugin/plugin.json", self.text)

    def test_inherited_cursor_agent_guard_stated(self) -> None:
        low = self.text.lower()
        self.assertIn("inherited", low)
        self.assertIn("cursor_agent", low)
        # Codex-under-codex-home / source-tree fall-through still documented.
        self.assertIn("CODEX_HOME", self.text)
        self.assertIn("~/.codex", self.text)

    def test_marketplace_matrix_covered(self) -> None:
        # Explicit fixture matrix in prose.
        self.assertIn("marketplace", self.text.lower())
        self.assertIn("install-cursor", self.text)
        # Whole-repo import may contain codex/ and still be cursor.
        self.assertRegex(
            self.text,
            re.compile(r"may contain `codex/`", re.IGNORECASE),
        )
        # Claude/Droid precedence unchanged.
        self.assertIn("CLAUDE_PLUGIN_ROOT", self.text)
        self.assertIn("DROID_PLUGIN_ROOT", self.text)
        self.assertIn("precedence unchanged", self.text.lower())


class TestHostLeadsReviewMenu(unittest.TestCase):
    """R6: on PLATFORM=cursor, host leads; cursor CLI secondary."""

    def setUp(self) -> None:
        self.text = _read()

    def test_host_recommended_label(self) -> None:
        self.assertIn('"label": "Host (Recommended)"', self.text)
        # Cursor-platform branch is gated explicitly.
        self.assertIn("When `PLATFORM=cursor`", self.text)

    def test_cursor_cli_circular_secondary(self) -> None:
        self.assertIn(
            "Cursor CLI (secondary — circular from inside Cursor)",
            self.text,
        )
        self.assertIn("circular", self.text.lower())

    def test_other_backends_still_selectable(self) -> None:
        # Within the Cursor review options block (between Host Recommended and
        # the non-cursor review branch), all backends appear.
        host_idx = self.text.index('"label": "Host (Recommended)"')
        non_cursor_idx = self.text.index(
            "**When `PLATFORM` is neither `cursor` nor `grok`**", host_idx
        )
        cursor_menu = self.text[host_idx:non_cursor_idx]
        for label in (
            "Codex CLI",
            "Copilot CLI",
            "RepoPrompt",
            "None",
        ):
            self.assertIn(label, cursor_menu, f"missing {label} in cursor menu")

    def test_host_maps_to_review_backend(self) -> None:
        self.assertIn('"Host"*) REVIEW_BACKEND="host"', self.text)
        # Host branch before Cursor* so labels don't collide.
        host_case = self.text.index('"Host"*) REVIEW_BACKEND="host"')
        cursor_case = self.text.index('"Cursor"*|"cursor"*) REVIEW_BACKEND="cursor"')
        self.assertLess(host_case, cursor_case)


class TestNoRalphOnCursor(unittest.TestCase):
    """R6 / boundary: no Ralph offer or registration on Cursor."""

    def setUp(self) -> None:
        self.text = _read()

    def test_ralph_skipped_on_cursor(self) -> None:
        self.assertRegex(
            self.text,
            re.compile(
                r"skip entirely when `PLATFORM=cursor`|PLATFORM=cursor.*no Ralph"
                r"|no Ralph support on Cursor|unsupported on Cursor",
                re.I | re.S,
            ),
        )
        self.assertIn("unsupported on Cursor", self.text)

    def test_never_run_ralph_init_on_cursor(self) -> None:
        # Processing path: never offer, never register, never run ralph-init.
        self.assertRegex(
            self.text,
            re.compile(
                r"never offer, never register, never run ralph-init"
                r"|never run `/flow-next:ralph-init`",
                re.I,
            ),
        )

    def test_ralph_question_still_present_for_other_hosts(self) -> None:
        # Non-Cursor hosts keep the Ralph ceremony (test_no_default_hooks pin).
        self.assertIn('"header": "Ralph"', self.text)
        self.assertIn("No (Recommended)", self.text)


class TestCursorHostNotes(unittest.TestCase):
    """Cursor resolves flowctl from the plugin (fn-197); non-Cursor routing retained."""

    def setUp(self) -> None:
        self.text = _read()

    def test_cursor_resolution_stated_without_copies(self) -> None:
        self.assertRegex(
            self.text,
            re.compile(r"Cursor exposes no plugin-root env vars.*nothing is copied", re.I | re.S),
        )

    def test_non_cursor_review_menu_retained(self) -> None:
        # Claude/Droid/Codex menu still ships without Host-first requirement.
        self.assertIn("**When `PLATFORM` is neither `cursor` nor `grok`**", self.text)
        non = self.text.split("**When `PLATFORM` is neither `cursor` nor `grok`**", 1)[1]
        # First review-options block after that header should still lead with Codex CLI
        # (not Host) for the non-cursor path.
        self.assertIn('"label": "Codex CLI"', non[:2000])
        self.assertNotIn('"label": "Host (Recommended)"', non[:2000])


if __name__ == "__main__":
    unittest.main()
