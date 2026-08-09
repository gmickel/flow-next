"""Two-axis in-host quality audit — contract pins.

The Phase 4 audit dispatches the quality-auditor agent twice in one message
(AXIS: correctness / AXIS: standards), aggregates both reports verbatim under
two headings, and holds the standards axis to a Should-Fix ceiling so hygiene
cannot inflate the fix loop. These pins assert the load-bearing contract
tokens on the canonical surfaces and the generated Codex mirror
(content + reachability; prose quality judged via .flow/criteria.md, not grep).
"""

from __future__ import annotations

import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

AUDITOR = PLUGIN / "agents" / "quality-auditor.md"
CANONICAL_WORK = PLUGIN / "skills" / "flow-next-work" / "phases.md"
MIRROR_WORK = PLUGIN / "codex" / "skills" / "flow-next-work" / "phases.md"
MIRROR_AUDITOR = PLUGIN / "codex" / "agents" / "quality-auditor.toml"
CONDUCT = REPO_ROOT / "agent_docs" / "conduct" / "quality-auditor.md"
CONDUCT_INDEX = REPO_ROOT / "agent_docs" / "conduct" / "README.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class AuditorAxisCharter(unittest.TestCase):
    def test_axis_selection_and_default(self) -> None:
        text = _read(AUDITOR)
        self.assertIn("AXIS: correctness", text)
        self.assertIn("AXIS: standards", text)
        self.assertIn(
            "Axis defaulted: correctness (no AXIS line in dispatch)", text
        )

    def test_standards_severity_ceiling(self) -> None:
        text = _read(AUDITOR)
        self.assertIn(
            "The standards axis's highest tier is Should Fix", text
        )
        self.assertIn("It never emits a Critical finding", text)
        self.assertIn("Blocking: none possible (standards axis)", text)

    def test_per_axis_caps_and_overflow_declaration(self) -> None:
        text = _read(AUDITOR)
        self.assertIn("At most 8 tiered findings", text)
        self.assertIn("At most 5 tiered findings", text)
        self.assertIn("+N over cap", text)

    def test_out_of_axis_escape_hatch(self) -> None:
        text = _read(AUDITOR)
        self.assertIn("Out-of-axis observation:", text)
        # Both axis output templates carry the section.
        self.assertGreaterEqual(
            text.count("### Out-of-axis observations"), 2
        )

    def test_fail_closed_diff_contract_survives(self) -> None:
        text = _read(AUDITOR)
        self.assertIn("Audit FAILED", text)


class WorkPhaseFourDispatch(unittest.TestCase):
    def _assert_dispatch_contract(
        self, text: str, dispatch_literal: str
    ) -> None:
        self.assertEqual(text.count(dispatch_literal), 2)
        self.assertIn("AXIS: correctness", text)
        self.assertIn("AXIS: standards", text)
        self.assertIn("### Correctness axis", text)
        self.assertIn("### Standards axis", text)
        # Parallel mandated + verbatim aggregation, stated as failure signatures.
        self.assertIn(
            "Both axis dispatches go out in the same message.", text
        )
        self.assertIn("Never merged, never reranked, never interleaved", text)

    def test_canonical(self) -> None:
        self._assert_dispatch_contract(
            _read(CANONICAL_WORK), "Task flow-next:quality-auditor"
        )

    def test_codex_mirror(self) -> None:
        # sync-codex.sh rewrites the dispatch spelling for the Codex surface.
        self._assert_dispatch_contract(
            _read(MIRROR_WORK), "Use the quality_auditor agent"
        )

    def test_mirror_auditor_carries_axis_charter(self) -> None:
        text = _read(MIRROR_AUDITOR)
        self.assertIn("AXIS: correctness", text)
        self.assertIn("AXIS: standards", text)
        self.assertIn("The standards axis's highest tier is Should Fix", text)


class ConductChecklist(unittest.TestCase):
    def test_checklist_exists_and_is_indexed(self) -> None:
        text = _read(CONDUCT)
        self.assertIn("AXIS:", text)
        self.assertIn("Should Fix", text)
        self.assertIn("quality-auditor.md", _read(CONDUCT_INDEX))


if __name__ == "__main__":
    unittest.main()
