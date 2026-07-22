"""fn-123 R3/R6 — Cursor-host-aware setup prose contracts.

Locks the setup workflow (canonical only — Codex mirror is a generated
rewrite and is not the Cursor host path) for:

  (a) Positive Cursor detection — PLUGIN_ROOT under ~/.cursor/; never keys on
      ``codex/`` directory absence (marketplace whole-repo imports contain
      ``codex/`` and must still classify as cursor).
  (b) Host-leads review menu on PLATFORM=cursor; Cursor CLI labeled
      circular/secondary; other backends remain selectable.
  (c) Host-native model-routing scaffold rules — cheap scout pin, cross-family
      host-review pin, inherit otherwise; date-stamp + re-run-to-refresh;
      offered without requiring a bridge CLI.
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


def _read() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


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
            "**When `PLATFORM` is NOT `cursor`**", host_idx
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


class TestCursorRoutingScaffold(unittest.TestCase):
    """R6: host-native routing rules + no bridge required on Cursor."""

    def setUp(self) -> None:
        self.text = _read()

    def test_offered_without_bridge_on_cursor(self) -> None:
        # Gate: ROUTING_ASK=1 AND (BRIDGE_DETECTED=1 OR PLATFORM=cursor)
        self.assertIn("PLATFORM=cursor", self.text)
        self.assertRegex(
            self.text,
            re.compile(
                r"BRIDGE_DETECTED=1`?\s*OR\s*`?PLATFORM=cursor"
                r"|PLATFORM=cursor`?\s*OR\s*`?BRIDGE_DETECTED=1"
                r"|`BRIDGE_DETECTED=1` OR `PLATFORM=cursor`"
                r"|bridge CLI required",
                re.IGNORECASE,
            ),
        )
        # Explicit: host-native needs no external bridge.
        self.assertRegex(
            self.text,
            re.compile(r"no external bridge|without requiring.*bridge|zero bridge", re.I),
        )
        # Non-Cursor still keeps the classic AND gate (lockstep with scaffold tests).
        self.assertIn("`ROUTING_ASK=1` AND `BRIDGE_DETECTED=1`", self.text)

    def test_host_agent_enumerates_and_picks_pins(self) -> None:
        low = self.text.lower()
        self.assertIn("host agent", low)
        self.assertIn("never python", low)
        self.assertIn("cursor-agent --list-models", self.text)
        self.assertIn("SCOUT_PIN", self.text)
        self.assertIn("REVIEW_PIN", self.text)

    def test_routing_rules_cheap_cross_family_inherit(self) -> None:
        # cheap scout / cross-family review / inherit otherwise
        self.assertRegex(
            self.text,
            re.compile(r"read-only scouts.*cheap|cheap.*read-only scouts", re.I | re.S),
        )
        self.assertRegex(
            self.text,
            re.compile(r"cross-family", re.I),
        )
        self.assertRegex(
            self.text,
            re.compile(r"everything else.*inherit|inherit.*session model", re.I | re.S),
        )

    def test_date_stamp_and_refresh_note(self) -> None:
        self.assertRegex(
            self.text,
            re.compile(r"YYYY-MM-DD|ISO date|date-stamp", re.I),
        )
        self.assertRegex(
            self.text,
            re.compile(r"re-run setup to refresh", re.I),
        )
        self.assertIn("volatile", self.text.lower())

    def test_cursor_host_native_block_markers(self) -> None:
        self.assertIn("<!-- flow-next:model-routing:start -->", self.text)
        self.assertIn("<!-- flow-next:model-routing:end -->", self.text)
        self.assertIn("Cursor host-native", self.text)


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


class TestCursorCopyModeUnchanged(unittest.TestCase):
    """Cursor stays copy mode; non-Cursor routing behavior retained."""

    def setUp(self) -> None:
        self.text = _read()

    def test_cursor_copy_mode_stated(self) -> None:
        self.assertRegex(
            self.text,
            re.compile(r"Copy mode only.*\.flow/bin/flowctl|Cursor exposes no plugin-root", re.I | re.S),
        )

    def test_non_cursor_review_menu_retained(self) -> None:
        # Claude/Droid/Codex menu still ships without Host-first requirement.
        self.assertIn("**When `PLATFORM` is NOT `cursor`**", self.text)
        non = self.text.split("**When `PLATFORM` is NOT `cursor`**", 1)[1]
        # First review-options block after that header should still lead with Codex CLI
        # (not Host) for the non-cursor path.
        self.assertIn('"label": "Codex CLI"', non[:2000])
        self.assertNotIn('"label": "Host (Recommended)"', non[:2000])


if __name__ == "__main__":
    unittest.main()
