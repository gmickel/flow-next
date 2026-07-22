"""Regression guard for the flat command-shim surface (fn-124).

Claude Code's slash menu rendered flow-next command shims as
`/flow-next:flow-next:flow-next:qa` because the shims lived in a
plugin-name-colliding nested command directory AND carried
pre-plugin-era frontmatter `name: flow-next:<cmd>` (colon inside `name` is
literal under v2.1.216+ last-segment semantics). The fix flattened the shims
to `commands/*.md` and de-prefixed the `name:` field to the BARE command name
(`name: qa`, not `name: flow-next:qa`) so the plugin prefix is prepended
exactly once, pointed the Cursor manifest at `./commands`, and deleted the
dead epic-review alias. The bare name (not a removed name) is deliberate:
Cursor's marketplace review checklist (fn-123 R11) requires every command to
carry both `name` and `description`, so the name stays present — just
colon-free.

This test pins all of that so a regression can't sneak back in:

  (a) no plugin-name-colliding nested command directory exists
  (b) >= 23 flat `commands/*.md` shims exist
  (c) `.cursor-plugin/plugin.json` `commands` field == `./commands`
  (d) every shim carries a `name:` (fn-123 R11) and no `name:` contains a colon
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

    def test_every_shim_name_equals_stem_bare_and_unique(self) -> None:
        # The load-bearing invariant: each shim carries EXACTLY ONE bare,
        # colon-free `name:` that equals its own filename stem, and no two
        # shims share a name. A weaker "name present + colon-free" check would
        # pass even if every shim said `name: qa` (collision) or `qa.md` said
        # `name: plan` (mismatch) -- both silently break the command surface.
        seen: dict[str, str] = {}
        for shim in self.shims:
            with self.subTest(shim=shim.name):
                fm = _frontmatter(shim.read_text(encoding="utf-8"))
                names = FRONTMATTER_NAME.findall(fm)
                # (fn-123 R11) every command must carry a name for Cursor's
                # marketplace review checklist.
                self.assertEqual(
                    len(names),
                    1,
                    f"{shim.name}: expected exactly one frontmatter 'name:', "
                    f"found {len(names)} -- Cursor's marketplace review "
                    "checklist (fn-123 R11) requires a single name.",
                )
                value = names[0]
                # (fn-124) bare/colon-free: under Claude Code v2.1.216+ the
                # plugin prefix is always prepended, so a namespaced name
                # renders a doubled prefix.
                self.assertNotIn(
                    ":",
                    value,
                    f"{shim.name}: frontmatter name '{value}' contains a colon "
                    "-- it renders doubled on Claude Code (fn-124). Use the "
                    "bare command name, e.g. 'name: qa'.",
                )
                # name must match the filename stem, else the menu entry and the
                # file diverge (a command silently renamed or shadowed).
                self.assertEqual(
                    value,
                    shim.stem,
                    f"{shim.name}: frontmatter name '{value}' does not match the "
                    f"filename stem '{shim.stem}'.",
                )
                # uniqueness across the whole surface.
                self.assertNotIn(
                    value,
                    seen,
                    f"{shim.name}: duplicate command name '{value}' (also in "
                    f"{seen.get(value)}) -- names collide in the slash menu.",
                )
                seen[value] = shim.name

    def test_epic_review_alias_deleted(self) -> None:
        self.assertFalse(
            (COMMANDS / "epic-review.md").exists(),
            "epic-review.md alias was removed in fn-124 (self-declared dead "
            "since 2.0.0) -- do not resurrect it.",
        )


if __name__ == "__main__":
    unittest.main()
