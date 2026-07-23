"""fn-130 R3 — Plan-only copy-mode version drift contract."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
CODEX_SKILLS = ROOT / "codex" / "skills"
PLUGIN_TEMPLATE = (
    SKILLS / "flow-next-setup" / "templates" / "claude-md-snippet-plugin.md"
)

PLAN = "flow-next-plan"
REMOVED_CARRIERS = [
    "flow-next-audit",
    "flow-next-capture",
    "flow-next-interview",
    "flow-next-land",
    "flow-next-make-pr",
    "flow-next-map",
    "flow-next-memory-migrate",
    "flow-next-pilot",
    "flow-next-prime",
    "flow-next-prospect",
    "flow-next-qa",
    "flow-next-ralph-init",
    "flow-next-resolve-pr",
    "flow-next-strategy",
    "flow-next-sync",
    "flow-next-tracker-sync",
    "flow-next-work",
]

QUESTION = (
    "Local Flow-Next copy v<X> differs from plugin v<Y>. "
    "Refresh before planning?"
)
REFRESH = "Refresh now (Recommended)"
CONTINUE = "Continue this run"
LEGACY_MARKERS = (
    "FLOW_SETUP_ASK",
    "FLOW_SNIPPET_ASK",
    "SETUP_STALE",
    "setup_stale",
    "## Pre-check: Local setup version",
    "## Pre-check: local setup version",
)


def _skill(root: Path, name: str) -> str:
    return (root / name / "SKILL.md").read_text(encoding="utf-8")


class PrecheckModeContractTest(unittest.TestCase):
    def test_canonical_plan_owns_exact_copy_mode_contract(self) -> None:
        text = _skill(SKILLS, PLAN)
        self.assertEqual(text.count(QUESTION), 1)
        self.assertEqual(text.count(REFRESH), 1)
        self.assertEqual(text.count(CONTINUE), 1)
        self.assertIn("AskUserQuestion", text)
        self.assertIn("In copy mode only", text)
        self.assertIn("run `/flow-next:setup`, then rerun Plan", text)
        self.assertIn("never invoke Setup or resume this Plan invocation", text)
        self.assertIn("Under autonomous, Ralph, or receipt-driven execution", text)
        self.assertIn("warn once and proceed without asking", text)
        self.assertIn(
            "Version match, plugin mode, or unavailable comparison evidence is silent",
            text,
        )
        self.assertIn("Never read or write legacy `version_ack` / `snippet_ack`", text)
        for marker in LEGACY_MARKERS:
            self.assertNotIn(marker, text)

    def test_other_lifecycle_skills_have_no_runtime_version_ceremony(self) -> None:
        forbidden = LEGACY_MARKERS + (
            "version_ack",
            "snippet_ack",
            "setup_version",
            "differs from plugin",
        )
        for name in REMOVED_CARRIERS:
            with self.subTest(skill=name):
                text = _skill(SKILLS, name)
                for marker in forbidden:
                    self.assertNotIn(marker, text)

    def test_pilot_and_land_no_longer_carry_verdict_stash(self) -> None:
        for name in ("flow-next-pilot", "flow-next-land"):
            for filename in ("SKILL.md", "workflow.md"):
                with self.subTest(skill=name, file=filename):
                    text = (SKILLS / name / filename).read_text(encoding="utf-8")
                    self.assertNotIn("setup_stale", text)
                    self.assertNotIn("SETUP_STALE", text)

    def test_codex_mirror_preserves_contract_without_legacy_fleet(self) -> None:
        text = _skill(CODEX_SKILLS, PLAN)
        self.assertEqual(text.count(QUESTION), 1)
        self.assertEqual(text.count(REFRESH), 1)
        self.assertEqual(text.count(CONTINUE), 1)
        self.assertIn("plain-text numbered prompt", text)
        self.assertNotIn("AskUserQuestion", text)
        for name in REMOVED_CARRIERS:
            with self.subTest(skill=name):
                mirror = _skill(CODEX_SKILLS, name)
                for marker in LEGACY_MARKERS + (
                    "version_ack",
                    "snippet_ack",
                    "setup_version",
                ):
                    self.assertNotIn(marker, mirror)

    def test_setup_template_contract_remains_intact(self) -> None:
        text = PLUGIN_TEMPLATE.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertEqual(lines[0], "<!-- BEGIN FLOW-NEXT -->")
        self.assertEqual(lines[-1], "<!-- END FLOW-NEXT -->")
        self.assertIn("flow-next:snippet:v", lines[1])
        self.assertNotIn(".flow/bin", text)
        self.assertIn("flowctl usage", text)
        self.assertIn("/flow-next:setup", text)


if __name__ == "__main__":
    unittest.main()
