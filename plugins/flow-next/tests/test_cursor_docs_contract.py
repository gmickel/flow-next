"""Prose-contract tests for Cursor install truth (fn-123.7 / R10, R12).

Locks the docs surface after the Cursor first-class rewrite:

  * platforms.md — team-marketplace import recommended + admin runbook;
    no stale "autocomplete under-lists" claim
  * install-cursor.sh — no under-lists caveat in post-install output
  * README.md — Cursor section mentions marketplace import

Pin shape (agent_docs/adding-skills.md, "Prose-contract tests — pin content +
reachability"): the POSITIVE pins assert the fact somewhere on the Cursor
READING SURFACE — the `## Cursor` section of platforms.md plus every markdown
file that section routes to — instead of welding it to the section body. Move
the admin runbook into a routed page and the contract still holds; drop it and
the test fails. The NEGATIVE sweeps stay pinned to the section (and to the
install scripts): "this stale claim must not appear HERE" is a location
assertion by construction.

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


def _cursor_surface(section: str) -> dict[str, str]:
    """The Cursor reading surface: the section plus every page it routes to.

    A fact may live in the section body or in a markdown file the section
    links — that is the reachability half of the pin. Files the section does
    NOT route to are absent from the surface, so content that drifts off the
    reader's path still fails.
    """
    surface = {"docs/platforms.md §Cursor": section}
    for target in sorted(set(re.findall(r"[A-Za-z0-9_./-]+\.md", section))):
        for base in (PLUGIN_DIR / "docs", PLUGIN_DIR, REPO_ROOT):
            candidate = (base / target).resolve()
            if candidate.is_file() and candidate != PLATFORMS_MD:
                surface[target] = _read(candidate)
                break
    return surface


class TestPlatformsCursorSection(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PLATFORMS_MD.is_file(), f"missing {PLATFORMS_MD}")
        self.full = _read(PLATFORMS_MD)
        self.cursor = _cursor_section(self.full)
        self.assertTrue(
            self.cursor,
            "platforms.md must have a '## Cursor' section",
        )
        self.surface = _cursor_surface(self.cursor)

    def assert_on_surface(self, predicate, what: str) -> str:
        """`what` is stated on some page of the Cursor reading surface."""
        hits = [label for label, text in self.surface.items() if predicate(text)]
        self.assertTrue(
            hits,
            f"nothing on the Cursor reading surface states {what} — "
            f"searched {sorted(self.surface)}",
        )
        return hits[0]

    def test_marketplace_import_recommended(self) -> None:
        """R12: team-marketplace repo import is the recommended path — stated
        on the Cursor surface (section body or a page it routes to)."""
        self.assert_on_surface(
            lambda text: (
                "team-marketplace" in text.lower()
                or "team marketplace" in text.lower()
                or "marketplace repo import" in text.lower()
            )
            and "recommended" in text.lower(),
            "team-marketplace repo import as the recommended path",
        )

    def test_admin_runbook_present(self) -> None:
        """The admin runbook and its steps are reachable from the Cursor
        section — whether inline or in a routed page."""
        self.assert_on_surface(
            lambda text: re.search(r"(?i)admin\s+runbook", text) is not None,
            "an Admin runbook",
        )
        # Runbook steps: import, install modes, auto-refresh, per-repo setup.
        for needle in (
            r"(?i)import",
            r"(?i)Default\s+On|Required",
            r"(?i)auto-?refresh",
            r"(?i)/flow-next[:-]setup|per-repo",
        ):
            with self.subTest(needle=needle):
                self.assert_on_surface(
                    lambda text, needle=needle: re.search(needle, text) is not None,
                    f"admin runbook content matching {needle!r}",
                )

    def test_no_stale_under_lists_claim(self) -> None:
        self.assertIsNone(
            UNDER_LISTS_RE.search(self.cursor),
            "platforms.md Cursor section must not claim autocomplete under-lists "
            "(slash autocomplete lists hyphenated commands on Cursor)",
        )
        # Positive truth: autocomplete lists / hyphenated form documented
        # somewhere on the Cursor reading surface.
        self.assert_on_surface(
            lambda text: re.search(r"(?i)autocomplete|hyphenated", text) is not None,
            "the autocomplete / hyphenated command form",
        )

    def test_no_stale_hook_schema_mismatch(self) -> None:
        # Accurate: intentionally does not build Ralph; NOT "schema mismatch".
        self.assertNotRegex(
            self.cursor,
            r"(?i)hook[- ]schema\s+mismatch|schema\s+mismatch",
            "platforms.md Cursor section must not claim hook-schema mismatch",
        )
        self.assert_on_surface(
            lambda text: re.search(
                r"(?i)intentionally\s+(?:does\s+not|not)\s+(?:build|register)|"
                r"not\s+built\s+for\s+Cursor",
                text,
            )
            is not None,
            "that Ralph is intentionally not built/registered on Cursor",
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
