"""Regression guard for the flat command-shim surface (fn-124).

Claude Code's slash menu rendered flow-next command shims as
`/flow-next:flow-next:flow-next:qa` because the shims lived in a
plugin-name-colliding nested command directory AND carried
pre-plugin-era frontmatter `name: flow-next:<cmd>` (colon inside `name` is
literal under v2.1.216+ last-segment semantics). The fix flattened the shims
to `commands/*.md`, dropped the `name:` field so the basename governs, pointed
the Cursor manifest at `./commands`, and deleted the dead epic-review alias.

This test pins all of that so a regression can't sneak back in:

  (a) no plugin-name-colliding nested command directory exists
  (b) >= 23 flat `commands/*.md` shims exist
  (c) `.cursor-plugin/plugin.json` `commands` field == `./commands`
  (d) no shim frontmatter `name:` contains a colon (none should exist at all)
  (e) `epic-review.md` is absent (alias removed on all platforms)

Run:
    python3 -m unittest plugins.flow-next.tests.test_command_shim_flatten -v
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent           # plugins/flow-next
COMMANDS = PLUGIN_DIR / "commands"
CURSOR_MANIFEST = PLUGIN_DIR / ".cursor-plugin" / "plugin.json"

FRONTMATTER_NAME = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the first two --- fences)."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


class TestCursorPluginSurface(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(COMMANDS.is_dir(), f"missing {COMMANDS}")
        self.shims = sorted(COMMANDS.glob("*.md"))

    def test_no_nested_flow_next_dir(self) -> None:
        self.assertFalse(
            (COMMANDS / "flow-next").exists(),
            "the nested flow-next command directory is back -- it triples the "
            "slash-menu prefix on Claude Code (fn-124). Shims live FLAT "
            "at commands/*.md.",
        )

    def test_at_least_23_flat_shims(self) -> None:
        self.assertGreaterEqual(
            len(self.shims),
            23,
            f"expected >= 23 flat command shims, found {len(self.shims)}",
        )

    def test_cursor_manifest_points_at_flat_commands(self) -> None:
        manifest = json.loads(CURSOR_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest.get("commands"),
            "./commands",
            ".cursor-plugin/plugin.json 'commands' must point at the flat "
            "./commands dir (kept in lockstep with the shim layout).",
        )

    def test_no_shim_frontmatter_name_with_colon(self) -> None:
        for shim in self.shims:
            with self.subTest(shim=shim.name):
                fm = _frontmatter(shim.read_text(encoding="utf-8"))
                for m in FRONTMATTER_NAME.finditer(fm):
                    self.assertNotIn(
                        ":",
                        m.group(1),
                        f"{shim.name}: frontmatter name '{m.group(1)}' contains "
                        "a colon -- under Claude Code v2.1.216+ semantics the "
                        "plugin prefix is always prepended, so a namespaced "
                        "name renders doubled (fn-124).",
                    )

    def test_epic_review_alias_deleted(self) -> None:
        self.assertFalse(
            (COMMANDS / "epic-review.md").exists(),
            "epic-review.md alias was removed in fn-124 (self-declared dead "
            "since 2.0.0) -- do not resurrect it.",
        )


if __name__ == "__main__":
    unittest.main()
