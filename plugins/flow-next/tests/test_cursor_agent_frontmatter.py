"""fn-123.2 / R4 — Cursor-native `readonly: true` on read-only agents.

Cursor ignores Claude's `disallowedTools` and uses its own `readonly: true`
frontmatter field to restrict writes. Every canonical agent whose
`disallowedTools` already denies BOTH Edit and Write must declare
`readonly: true`; writing agents must not.

Invariant (both directions, derived from frontmatter — no hardcoded roster):

  denies Edit+Write  <=>  readonly: true

Run:
    python3 -m unittest test_cursor_agent_frontmatter -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
AGENTS_DIR = HERE.parent.parent / "agents"

# Frontmatter key = value (scalar only; lists stay as raw strings).
_FM_LINE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm: dict[str, Any] = {}
    for line in text[4:end].splitlines():
        m = _FM_LINE.match(line.strip())
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw in ("true", "false"):
            fm[key] = raw == "true"
        else:
            fm[key] = raw
    return fm


def _disallowed_tools(fm: dict[str, Any]) -> set[str]:
    raw = fm.get("disallowedTools") or ""
    if not isinstance(raw, str) or not raw.strip():
        return set()
    return {t.strip() for t in raw.split(",") if t.strip()}


def _denies_edit_and_write(tools: set[str]) -> bool:
    return "Edit" in tools and "Write" in tools


class TestCursorAgentFrontmatter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agent_files = sorted(AGENTS_DIR.glob("*.md"))
        assert cls.agent_files, f"no agents under {AGENTS_DIR}"

    def test_agents_directory_has_expected_population(self) -> None:
        # Sanity: roster must be non-trivial so an empty-dir pass can't hide.
        self.assertGreaterEqual(len(self.agent_files), 10)

    def test_readonly_iff_denies_edit_and_write(self) -> None:
        """Bidirectional invariant over every agent file."""
        mismatches: list[str] = []
        for path in self.agent_files:
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
            tools = _disallowed_tools(fm)
            denies = _denies_edit_and_write(tools)
            readonly = fm.get("readonly") is True
            name = path.name
            if denies and not readonly:
                mismatches.append(
                    f"{name}: denies Edit+Write but missing readonly: true "
                    f"(disallowedTools={sorted(tools)})"
                )
            if readonly and not denies:
                mismatches.append(
                    f"{name}: has readonly: true but does not deny both Edit and "
                    f"Write (disallowedTools={sorted(tools)})"
                )
        self.assertEqual(
            mismatches,
            [],
            "readonly / disallowedTools invariant broken:\n  "
            + "\n  ".join(mismatches),
        )

    def test_writing_agents_are_not_readonly(self) -> None:
        """Agents that retain Edit or Write must not carry readonly: true.

        Derived: any agent that does NOT deny both Edit and Write. Named
        examples (worker / plan-sync / pr-comment-resolver / tracker-runner)
        are writing agents but the check is property-based, not a roster.
        """
        writers_with_readonly: list[str] = []
        writers_seen = 0
        for path in self.agent_files:
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
            tools = _disallowed_tools(fm)
            if _denies_edit_and_write(tools):
                continue
            writers_seen += 1
            if fm.get("readonly") is True:
                writers_with_readonly.append(path.name)
        self.assertGreaterEqual(
            writers_seen,
            1,
            "expected at least one writing agent (no Edit+Write deny)",
        )
        self.assertEqual(
            writers_with_readonly,
            [],
            f"writing agents must not be readonly: {writers_with_readonly}",
        )

    def test_readonly_scouts_exist(self) -> None:
        """Positive half: at least one scout/reviewer carries the flag."""
        readonly_agents = []
        for path in self.agent_files:
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
            if fm.get("readonly") is True:
                readonly_agents.append(path.stem)
        self.assertGreaterEqual(
            len(readonly_agents),
            5,
            f"expected several readonly agents, found {readonly_agents}",
        )


if __name__ == "__main__":
    unittest.main()
