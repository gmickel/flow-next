"""Pins the evidence-bounded sibling audit for confirmed bot findings."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT
CODEX = ROOT / "codex"


class ResolvePrBotSiblingAuditProse(unittest.TestCase):
    def test_canonical_agent_and_workflow_carry_the_same_cycle_rule(self) -> None:
        agent = (CANONICAL / "agents/pr-comment-resolver.md").read_text()
        workflow = (
            CANONICAL / "skills/flow-next-resolve-pr/workflow.md"
        ).read_text()

        for text in (agent, workflow):
            self.assertIn("confirmed", text.lower())
            self.assertIn("sibling", text.lower())
            self.assertIn("automated reviewer", text)
            self.assertIn("Stop at evidence", text)
            self.assertIn("regression-test", text)

    def test_rule_preserves_cross_round_cluster_gate(self) -> None:
        cluster = (
            CANONICAL / "skills/flow-next-resolve-pr/cluster-analysis.md"
        ).read_text()
        self.assertIn("confirmed bot sibling audit", cluster)
        self.assertIn("does not relax this cross-round gate", cluster)

    def test_codex_mirror_carries_the_agent_and_workflow_rule(self) -> None:
        agent = (CODEX / "agents/pr-comment-resolver.toml").read_text()
        workflow = (
            CODEX / "skills/flow-next-resolve-pr/workflow.md"
        ).read_text()
        for text in (agent, workflow):
            self.assertIn("confirmed", text.lower())
            self.assertIn("sibling", text.lower())
            self.assertIn("Stop at evidence", text)


if __name__ == "__main__":
    unittest.main()
