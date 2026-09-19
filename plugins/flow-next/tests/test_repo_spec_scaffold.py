"""Drift guard for this repo's own tier-1 spec scaffold (`<repo_root>/SPEC.md`).

The flow-next repo dogfoods the template cascade: its root `SPEC.md` is a copy of
the bundled `plugins/flow-next/templates/spec.md` with exactly one deliberate
difference - `Conversation Evidence` is dropped from `auxiliary_sections`, so specs
captured in this repo omit the evidence block.

A tier-1 copy stops receiving bundled-template edits, so a later template change
would silently miss this repo's own specs. These tests pin the byte relation (G2:
a parity relation, never prose): everything outside the frontmatter's leading
comment lines and that one list entry is identical.

Skipped when no root `SPEC.md` exists (an installed plugin layout, or a fork that
removed the override).
"""

from __future__ import annotations

import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
BUNDLED = PLUGIN_DIR / "templates" / "spec.md"
REPO_SCAFFOLD = REPO_ROOT / "SPEC.md"

DROPPED_ENTRY = "Conversation Evidence"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")


def _split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    assert lines[0] == "---", "template must open with a frontmatter fence"
    end = lines.index("---", 1)
    return lines[1:end], lines[end + 1 :]


def _is_dropped_entry(line: str) -> bool:
    return line.strip().startswith(f"- {DROPPED_ENTRY}")


@unittest.skipUnless(REPO_SCAFFOLD.is_file(), "no repo-root SPEC.md override")
class TestRepoSpecScaffoldTracksBundled(unittest.TestCase):
    def setUp(self) -> None:
        self.bundled_fm, self.bundled_body = _split_frontmatter(_lines(BUNDLED))
        self.repo_fm, self.repo_body = _split_frontmatter(_lines(REPO_SCAFFOLD))

    def test_body_is_byte_identical_to_bundled(self) -> None:
        """The rendered scaffold (frontmatter stripped) must not drift."""
        self.assertEqual(self.repo_body, self.bundled_body)

    def test_frontmatter_differs_only_by_the_dropped_entry(self) -> None:
        """Leading `#` comment lines are the override's own note; nothing else
        may differ except the one removed auxiliary entry."""
        repo_fm = [ln for ln in self.repo_fm if not ln.startswith("#")]
        expected = [ln for ln in self.bundled_fm if not _is_dropped_entry(ln)]
        self.assertEqual(repo_fm, expected)

    def test_bundled_still_names_the_entry_and_repo_does_not(self) -> None:
        """If the bundled template ever renames or drops the entry, this override
        is stale and must be revisited rather than silently matching."""
        self.assertTrue(any(_is_dropped_entry(ln) for ln in self.bundled_fm))
        self.assertFalse(any(_is_dropped_entry(ln) for ln in self.repo_fm))


if __name__ == "__main__":
    unittest.main()
