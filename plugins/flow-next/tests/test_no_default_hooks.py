"""fn-114.1 / fn-114.2 - plugin ships zero hooks by default (Ralph opt-in).

Pins:
  * plugins/flow-next/hooks/ is absent (no hooks.json, no empty dir required)
  * .claude-plugin/plugin.json carries no ``hooks`` key
  * codex mirror ships no hooks.json (sync-codex zero-default)
  * ralph-init skill prose owns registration (mentions project settings merge)
  * setup workflow asks Ralph with default No and documents removal
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
PLUGIN_JSON = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
HOOKS_DIR = PLUGIN_DIR / "hooks"
HOOKS_JSON = HOOKS_DIR / "hooks.json"
CODEX_HOOKS_JSON = PLUGIN_DIR / "codex" / "hooks.json"
RALPH_INIT = PLUGIN_DIR / "skills" / "flow-next-ralph-init" / "SKILL.md"
SETUP_WORKFLOW = PLUGIN_DIR / "skills" / "flow-next-setup" / "workflow.md"
SETUP_RALPH_QUESTION = (
    PLUGIN_DIR
    / "skills"
    / "flow-next-setup"
    / "references"
    / "ralph-question.md"
)
SETUP_RALPH_DISABLE = (
    PLUGIN_DIR
    / "skills"
    / "flow-next-setup"
    / "references"
    / "ralph-disable.md"
)
UNINSTALL = PLUGIN_DIR / "commands" / "uninstall.md"


class TestNoDefaultHooks(unittest.TestCase):
    def test_hooks_dir_and_hooks_json_absent(self) -> None:
        self.assertFalse(
            HOOKS_JSON.is_file(),
            f"plugin must not ship {HOOKS_JSON.relative_to(PLUGIN_DIR)} — "
            "Ralph hooks are opt-in via ralph-init skill prose",
        )
        # Prefer no hooks/ tree at all; allow neither a residual empty dir
        # nor a dir that still holds files.
        if HOOKS_DIR.exists():
            leftover = sorted(p.name for p in HOOKS_DIR.rglob("*") if p.is_file())
            self.assertEqual(
                leftover,
                [],
                f"plugins/flow-next/hooks/ must be empty or absent; found {leftover}",
            )

    def test_plugin_manifest_has_no_hooks_key(self) -> None:
        self.assertTrue(PLUGIN_JSON.is_file(), f"missing {PLUGIN_JSON}")
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        self.assertNotIn(
            "hooks",
            data,
            "plugin.json must not declare a hooks field — zero default registration",
        )

    def test_codex_mirror_ships_no_hooks_json(self) -> None:
        self.assertFalse(
            CODEX_HOOKS_JSON.is_file(),
            "plugins/flow-next/codex/hooks.json must not ship - "
            "Ralph hooks are opt-in via ralph-init project settings",
        )

    def test_ralph_init_owns_registration_prose(self) -> None:
        text = RALPH_INIT.read_text(encoding="utf-8")
        self.assertIn(".claude/settings.json", text)
        self.assertIn(".factory/hooks.json", text)
        self.assertIn("scripts/ralph/hooks/ralph-guard", text)
        self.assertIn("idempotent", text.lower())
        # Hard boundary: no flowctl hook subcommand.
        self.assertNotRegex(
            text,
            r"flowctl\s+hooks?\b",
            "ralph-init must not introduce a flowctl hooks subcommand",
        )

    def test_setup_asks_ralph_default_no(self) -> None:
        workflow = SETUP_WORKFLOW.read_text(encoding="utf-8")
        question = SETUP_RALPH_QUESTION.read_text(encoding="utf-8")
        disable = SETUP_RALPH_DISABLE.read_text(encoding="utf-8")
        self.assertIn("references/ralph-question.md", workflow)
        self.assertIn('"header": "Ralph"', question)
        self.assertIn("No (Recommended)", question)
        self.assertIn("Yes, enable or keep", question)
        # Removal path on No
        self.assertIn("scripts/ralph/hooks/ralph-guard", disable)
        self.assertIn("before deleting it", disable.lower())
        # Codex setup must not auto-copy hooks
        self.assertNotIn("Copied hooks.json to .codex/hooks.json", workflow)

    def test_uninstall_strips_hook_entries(self) -> None:
        text = UNINSTALL.read_text(encoding="utf-8")
        self.assertIn("scripts/ralph/hooks/ralph-guard", text)
        self.assertIn(".claude/settings.json", text)
        self.assertIn(".factory/hooks.json", text)


if __name__ == "__main__":
    unittest.main()
