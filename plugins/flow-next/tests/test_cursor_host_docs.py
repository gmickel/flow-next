"""Docs drift guard for Cursor-host first-class experience (fn-123).

Locks the Cursor-host model-tiering / review.backend host sentinel language in
canonical templates + docs so the usage guide, orchestration notes, and flowctl
grammar stay consistent.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_cursor_host_docs -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent  # plugins/flow-next

USAGE_TEMPLATE = PLUGIN_DIR / "templates" / "usage.md"
ORCHESTRATION_DOC = PLUGIN_DIR / "docs" / "orchestration.md"
FLOWCTL_DOC = PLUGIN_DIR / "docs" / "flowctl.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestCursorHostUsageTemplate(unittest.TestCase):
    def test_usage_template_has_cursor_host_section(self) -> None:
        text = _read(USAGE_TEMPLATE)
        self.assertIn("Cursor host", text)

        # No shipped model identifier: the Cursor section names a placeholder and
        # tells the reader to ask the harness (fn-195 R2 - identifiers are the
        # user's, verified against their own account, never ours to enumerate).
        # Same slug detector as test_model_routing_scaffold.MODEL_SLUG_RE - a
        # two-literal denylist would go green the moment a NEW slug shipped.
        from test_model_routing_scaffold import MODEL_SLUG_RE

        cursor_section = text[text.index("Cursor host"):]
        cursor_section = cursor_section.split("\n## ", 1)[0]
        hit = MODEL_SLUG_RE.search(cursor_section)
        self.assertIsNone(
            hit,
            f"usage.md Cursor section must not ship a concrete model identifier "
            f"(fn-195 R2); found {hit.group(0) if hit else None!r}",
        )
        self.assertIn("<model>", text)

        # list-models discovery
        self.assertTrue(
            re.search(r"list-models|cursor-agent --list-models", text),
            "usage.md must mention list-models / cursor-agent --list-models",
        )

        # review.backend host
        self.assertIn("review.backend host", text)

        # Distinguish host backend from external cursor CLI backend
        self.assertTrue(
            re.search(
                r"(≠|!=|distinct|separate|not).{0,80}(cursor CLI|`cursor`|cursor-agent)"
                r"|(cursor CLI|`cursor`|cursor-agent).{0,80}(≠|!=|distinct|separate|not)",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            or (
                "host" in text.lower()
                and re.search(
                    r"≠\s*`cursor`|≠\s*cursor CLI|Distinct from the headless `cursor`",
                    text,
                )
            ),
            "usage.md must distinguish the host backend from the external cursor CLI backend",
        )


class TestCursorHostOrchestrationDoc(unittest.TestCase):
    def test_orchestration_cursor_alias_inherit(self) -> None:
        text = _read(ORCHESTRATION_DOC)
        self.assertTrue(
            re.search(r"resolve(?:s| to)?\s+\*?\*?inherit\*?\*?", text, re.IGNORECASE)
            or re.search(r"aliases?\s+.*inherit", text, re.IGNORECASE),
            "orchestration.md must say family aliases resolve to inherit on Cursor",
        )
        self.assertIn("Cursor", text)
        self.assertTrue(
            re.search(
                r"no alias-to-slug rewrite|none is planned|no alias.to.slug rewrite",
                text,
                re.IGNORECASE,
            ),
            "orchestration.md must state no alias-to-slug rewrite is planned",
        )


class TestCursorHostFlowctlDoc(unittest.TestCase):
    def test_flowctl_host_sentinel(self) -> None:
        text = _read(FLOWCTL_DOC)
        self.assertTrue(
            re.search(
                r"host.{0,120}(sentinel|model-less|modeless)|"
                r"(sentinel|model-less|modeless).{0,120}host",
                text,
                re.IGNORECASE | re.DOTALL,
            ),
            "flowctl.md must document host as a selection sentinel",
        )
        self.assertTrue(
            re.search(
                r"host:<model>.*reject|reject.*host:<model>|host:<model>.*REJECTED",
                text,
                re.IGNORECASE | re.DOTALL,
            ),
            "flowctl.md must document rejecting host:<model>",
        )


if __name__ == "__main__":
    unittest.main()
