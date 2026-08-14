"""fn-130.3 — Setup reached-path router contracts."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parents[1]
SETUP = PLUGIN / "skills" / "flow-next-setup"
WORKFLOW = SETUP / "workflow.md"
REFS = SETUP / "references"
EVIDENCE = REPO / "optimization" / "reached-path" / "setup-routing-evidence.json"


class SetupReferenceRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_every_routed_reference_exists_one_level_below_skill(self) -> None:
        links = set(re.findall(r"\(references/([^)]+\.md)\)", self.text))
        expected = {
            "ralph-question.md",
            "ralph-enable.md",
            "ralph-disable.md",
        }
        self.assertTrue(expected <= links)
        for name in expected:
            self.assertTrue((REFS / name).is_file(), name)

    def test_routed_references_do_not_chain_to_sibling_references(self) -> None:
        for path in REFS.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("(references/", text, path)
            self.assertNotIn("bridge reference", text.lower(), path)

    def test_no_routing_or_pin_reference_is_routed(self) -> None:
        # fn-195.2: the probe-and-pin ceremony and the routing menu are deleted,
        # not skipped - so no setup reference exists to route to, and the
        # workflow must not link one.
        for gone in ("references/model-pins.md", "references/model-routing-"):
            self.assertNotIn(gone, self.text, gone)
        for stale in REFS.glob("model-*.md"):
            self.fail(f"deleted routing/pin reference regrew: {stale.name}")

    def test_ralph_routes_only_selected_answer(self) -> None:
        block = self.text[
            self.text.index("**Ralph** (only when") :
            self.text.index("**Star:**")
        ]
        self.assertIn("references/ralph-enable.md", block)
        self.assertIn("references/ralph-disable.md", block)
        self.assertIn("Unknown answer fails safe", block)
        self.assertIn("non-interactive", block)

    def test_ralph_question_is_cold_when_unsupported_or_autonomous(self) -> None:
        block = self.text[
            self.text.index("**Ralph question.**") :
            self.text.index("**Star question**")
        ]
        self.assertIn("RALPH_ASK=0", block)
        self.assertIn("FLOW_AUTONOMOUS", block)
        self.assertIn("references/ralph-question.md", block)
        self.assertIn("read no Ralph reference", block)

    def test_optional_payloads_are_not_in_common_workflow(self) -> None:
        self.assertNotIn("cursor-agent --list-models", self.text)
        self.assertNotIn("codex accept-probe", self.text)
        self.assertNotIn("### Dispatch pins (host agent picked)", self.text)
        self.assertNotIn("Remove only flow-next Ralph guard matcher", self.text)

    # Live-file hash/char freeze removed 2026-08-07 (.flow/criteria.md G1).


if __name__ == "__main__":
    unittest.main()
