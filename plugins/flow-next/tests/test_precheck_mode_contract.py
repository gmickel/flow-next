"""fn-130 R3 — Plan-only copy-mode version drift contract."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKILLS = ROOT / "skills"
CODEX_SKILLS = ROOT / "codex" / "skills"
CODEX_INSTALLER = REPO_ROOT / "scripts" / "install-codex.sh"
SNIPPET_TEMPLATES = {
    "claude-md-snippet.md": "/flow-next:setup",
    "agents-md-snippet.md": "$flow-next-setup",
}

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

# Smallest distinctive token of the drift question — also the marker forbidden
# in every other lifecycle skill, so its exactly-one count pins the sole
# carrier. (Full question/option copy pins removed 2026-08-07 - judged via
# .flow/criteria.md G1, not grep.)
DRIFT_TOKEN = "differs from plugin"
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
        self.assertEqual(text.count(DRIFT_TOKEN), 1)
        self.assertIn("AskUserQuestion", text)
        self.assertIn("`.flow/meta.json`", text)
        self.assertIn(
            "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json",
            text,
        )
        for marker in LEGACY_MARKERS:
            self.assertNotIn(marker, text)

    def test_other_lifecycle_skills_have_no_runtime_version_ceremony(self) -> None:
        forbidden = LEGACY_MARKERS + (
            "version_ack",
            "snippet_ack",
            "setup_version",
            DRIFT_TOKEN,
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
        self.assertEqual(text.count(DRIFT_TOKEN), 1)
        self.assertIn("plain-text numbered prompt", text)
        self.assertNotIn("AskUserQuestion", text)
        self.assertIn("`${CODEX_HOME:-$HOME/.codex}/plugin.json`", text)
        self.assertNotIn(".codex/.codex-plugin/plugin.json", text)
        installer = CODEX_INSTALLER.read_text(encoding="utf-8")
        self.assertIn(
            'cp "$PLUGIN_DIR/.codex-plugin/plugin.json" "$CODEX_DIR/plugin.json"',
            installer,
        )
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
        # fn-197: setup ships exactly these two snippet templates, both slim
        # and copy-less. The contract is asserted on BOTH twins, not one.
        templates_dir = SKILLS / "flow-next-setup" / "templates"
        shipped = {
            p.name for p in templates_dir.glob("*-md-snippet*.md")
        }
        self.assertEqual(shipped, set(SNIPPET_TEMPLATES))
        for name, setup_cmd in SNIPPET_TEMPLATES.items():
            with self.subTest(template=name):
                text = (templates_dir / name).read_text(encoding="utf-8")
                lines = [ln for ln in text.splitlines() if ln.strip()]
                self.assertEqual(lines[0], "<!-- BEGIN FLOW-NEXT -->")
                self.assertEqual(lines[-1], "<!-- END FLOW-NEXT -->")
                self.assertIn("flow-next:snippet:v", lines[1])
                self.assertNotIn(".flow/bin", text)
                self.assertNotIn(".flow/templates/spec.md", text)
                self.assertNotIn(".flow/usage.md", text)
                self.assertIn("flowctl usage", text)
                self.assertIn(setup_cmd, text)


if __name__ == "__main__":
    unittest.main()
