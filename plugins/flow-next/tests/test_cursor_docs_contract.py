"""Prose-contract tests for Cursor install truth (fn-123.7 / R10, R12).

Locks the docs surface after the Cursor first-class rewrite:

  * platforms.md — team-marketplace import recommended + admin runbook;
    no stale "autocomplete under-lists" claim
  * install-cursor.sh — no under-lists caveat in post-install output
  * README.md — Cursor section mentions marketplace import

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_cursor_docs_contract -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent  # plugins/flow-next
REPO_ROOT = PLUGIN_DIR.parent.parent

PLATFORMS_MD = PLUGIN_DIR / "docs" / "platforms.md"
INSTALL_SH = REPO_ROOT / "scripts" / "install-cursor.sh"
INSTALL_PS1 = REPO_ROOT / "scripts" / "install-cursor.ps1"
README_MD = REPO_ROOT / "README.md"

# Stale claim that must not reappear on Cursor surfaces (R10).
UNDER_LISTS_RE = re.compile(
    r"autocomplete\s+under-lists|under-lists?\s+them|slash autocomplete under-list",
    re.IGNORECASE,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _cursor_section(text: str) -> str:
    """Slice platforms.md from the Cursor heading through the next top-level ##."""
    m = re.search(r"^## Cursor\b.*", text, re.MULTILINE)
    if not m:
        return ""
    start = m.start()
    rest = text[start + 2 :]  # skip leading ## of the match for the next ## search
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    end = start + 2 + (nxt.start() if nxt else len(rest))
    return text[start:end]


class TestPlatformsCursorSection(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PLATFORMS_MD.is_file(), f"missing {PLATFORMS_MD}")
        self.full = _read(PLATFORMS_MD)
        self.cursor = _cursor_section(self.full)
        self.assertTrue(
            self.cursor,
            "platforms.md must have a '## Cursor' section",
        )

    def test_marketplace_import_recommended(self) -> None:
        # Recommended path is team-marketplace repo import (R12).
        lower = self.cursor.lower()
        self.assertTrue(
            (
                "team-marketplace" in lower
                or "team marketplace" in lower
                or "marketplace repo import" in lower
            )
            and "recommended" in lower,
            "platforms.md Cursor section must present team-marketplace "
            "repo import as recommended",
        )

    def test_admin_runbook_present(self) -> None:
        self.assertRegex(
            self.cursor,
            r"(?i)admin\s+runbook",
            "platforms.md Cursor section must include an Admin runbook subsection",
        )
        # Runbook steps: import, install modes, auto-refresh, per-repo setup.
        for needle in (
            r"(?i)import",
            r"(?i)Default\s+On|Required",
            r"(?i)auto-?refresh",
            r"(?i)/flow-next[:-]setup|per-repo",
        ):
            with self.subTest(needle=needle):
                self.assertRegex(
                    self.cursor,
                    needle,
                    f"admin runbook missing expected content matching {needle!r}",
                )

    def test_no_stale_under_lists_claim(self) -> None:
        self.assertIsNone(
            UNDER_LISTS_RE.search(self.cursor),
            "platforms.md Cursor section must not claim autocomplete under-lists "
            "(slash autocomplete lists hyphenated commands on Cursor)",
        )
        # Positive truth: autocomplete lists / hyphenated form present.
        self.assertTrue(
            re.search(r"(?i)autocomplete|hyphenated", self.cursor),
            "platforms.md Cursor section should document autocomplete / "
            "hyphenated command form",
        )

    def test_no_stale_hook_schema_mismatch(self) -> None:
        # Accurate: intentionally does not build Ralph; NOT "schema mismatch".
        self.assertNotRegex(
            self.cursor,
            r"(?i)hook[- ]schema\s+mismatch|schema\s+mismatch",
            "platforms.md Cursor section must not claim hook-schema mismatch",
        )
        self.assertTrue(
            re.search(
                r"(?i)intentionally\s+(?:does\s+not|not)\s+(?:build|register)|"
                r"not\s+built\s+for\s+Cursor",
                self.cursor,
            ),
            "platforms.md Cursor section must state Ralph is intentionally "
            "not built/registered on Cursor",
        )


class TestInstallCursorNoUnderLists(unittest.TestCase):
    def test_sh_has_no_under_lists_caveat(self) -> None:
        text = _read(INSTALL_SH)
        self.assertIsNone(
            UNDER_LISTS_RE.search(text),
            "install-cursor.sh must not claim autocomplete under-lists",
        )

    def test_ps1_has_no_under_lists_caveat(self) -> None:
        text = _read(INSTALL_PS1)
        self.assertIsNone(
            UNDER_LISTS_RE.search(text),
            "install-cursor.ps1 must not claim autocomplete under-lists",
        )

    def test_sh_mentions_team_marketplace_fallback(self) -> None:
        text = _read(INSTALL_SH).lower()
        self.assertTrue(
            "team-marketplace" in text or "team marketplace" in text,
            "install-cursor.sh should note team-marketplace as recommended path",
        )
        self.assertTrue(
            "fallback" in text or "individual" in text,
            "install-cursor.sh should identify itself as individual/fallback",
        )


class TestReadmeCursorMarketplace(unittest.TestCase):
    def test_readme_cursor_mentions_marketplace_import(self) -> None:
        text = _read(README_MD)
        # Platforms table Cursor row.
        m = re.search(
            r"\|\s*Cursor\s*\|[^|]+\|",
            text,
            re.IGNORECASE,
        )
        self.assertIsNotNone(m, "README.md must have a Cursor platforms table row")
        row = m.group(0).lower()
        self.assertTrue(
            "marketplace" in row and ("import" in row or "team" in row),
            "README Cursor row must mention marketplace import",
        )
        self.assertIsNone(
            UNDER_LISTS_RE.search(row),
            "README Cursor row must not claim autocomplete under-list",
        )


if __name__ == "__main__":
    unittest.main()
