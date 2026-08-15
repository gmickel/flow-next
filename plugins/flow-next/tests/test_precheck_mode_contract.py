"""fn-197 — no runtime version-drift ceremony survives in any lifecycle skill.

fn-130 made copy-mode drift detection Plan-only; fn-197 deletes copy mode
itself, so Plan's version comparison is gone too and the whole fleet is
uniform: nothing reads `setup_version` / `version_ack` / `snippet_ack`, and
nothing asks the user to refresh a local copy. Plan's replacement — a one-line
nudge when legacy copy artifacts are still on disk — is prose judged via
`.flow/criteria.md` G1, not pinned here beyond its residue-probe anchor.
"""

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
LIFECYCLE_SKILLS = [
    "flow-next-audit",
    "flow-next-capture",
    "flow-next-interview",
    "flow-next-land",
    "flow-next-make-pr",
    "flow-next-map",
    "flow-next-memory-migrate",
    "flow-next-pilot",
    PLAN,
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

# Smallest distinctive token of the retired drift question, plus the legacy
# pre-check markers that preceded it. None may appear in any skill.
DRIFT_TOKEN = "differs from plugin"
FORBIDDEN_MARKERS = (
    "FLOW_SETUP_ASK",
    "FLOW_SNIPPET_ASK",
    "SETUP_STALE",
    "setup_stale",
    "## Pre-check: Local setup version",
    "## Pre-check: local setup version",
    "version_ack",
    "snippet_ack",
    "setup_version",
    DRIFT_TOKEN,
)


def _skill(root: Path, name: str) -> str:
    return (root / name / "SKILL.md").read_text(encoding="utf-8")


class PrecheckModeContractTest(unittest.TestCase):
    def test_no_lifecycle_skill_carries_a_version_ceremony(self) -> None:
        for root, label in ((SKILLS, "canonical"), (CODEX_SKILLS, "codex")):
            for name in LIFECYCLE_SKILLS:
                with self.subTest(skill=name, tree=label):
                    text = _skill(root, name)
                    for marker in FORBIDDEN_MARKERS:
                        self.assertNotIn(marker, text)

    def test_plan_nudges_on_legacy_copy_residue_only(self) -> None:
        # The replacement touchpoint: Plan probes for residue and says one
        # line about deleting it. No question, no version compare.
        for root, label in ((SKILLS, "canonical"), (CODEX_SKILLS, "codex")):
            with self.subTest(tree=label):
                text = _skill(root, PLAN)
                self.assertIn(".flow/bin/flowctl_bootstrap.py", text)
                self.assertIn("LEGACY_COPY_ARTIFACTS", text)

    def test_pilot_and_land_no_longer_carry_verdict_stash(self) -> None:
        for name in ("flow-next-pilot", "flow-next-land"):
            for filename in ("SKILL.md", "workflow.md"):
                with self.subTest(skill=name, file=filename):
                    text = (SKILLS / name / filename).read_text(encoding="utf-8")
                    self.assertNotIn("setup_stale", text)
                    self.assertNotIn("SETUP_STALE", text)

    def test_codex_installer_ships_the_plugin_manifest(self) -> None:
        installer = CODEX_INSTALLER.read_text(encoding="utf-8")
        self.assertIn(
            'cp "$PLUGIN_DIR/.codex-plugin/plugin.json" "$CODEX_DIR/plugin.json"',
            installer,
        )

    def test_setup_template_contract_remains_intact(self) -> None:
        # fn-197: setup ships exactly these two snippet templates, both slim
        # and copy-less. The contract is asserted on BOTH twins, not one.
        templates_dir = SKILLS / "flow-next-setup" / "templates"
        shipped = {p.name for p in templates_dir.glob("*-md-snippet*.md")}
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
