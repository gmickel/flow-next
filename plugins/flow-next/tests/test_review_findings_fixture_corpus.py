"""Contracts for the fn-136 backend review-output fixture corpus."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "optimization" / "reached-path" / "fixtures" / "review-findings" / "v1"
BACKENDS = {"codex", "copilot", "cursor", "host", "rp", "export"}
CASES = {"no-findings-ship", "ratchet-only", "no-anchor", "unparseable"}


class ReviewFindingsFixtureCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads((CORPUS / "INDEX.json").read_text(encoding="utf-8"))

    def test_manifest_names_every_backend_and_edge_case(self) -> None:
        self.assertEqual(self.index["schema_version"], 1)
        self.assertEqual(set(self.index["backends"]), BACKENDS)
        self.assertEqual({case["id"] for case in self.index["cases"]}, CASES)

    def test_fixture_matrix_is_complete_and_has_no_extra_markdown(self) -> None:
        expected = {
            CORPUS / backend / f"{case}.md"
            for backend in BACKENDS
            for case in CASES
        }
        actual = set(CORPUS.glob("*/*.md"))
        self.assertEqual(actual, expected)
        for path in actual:
            self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 20, path)

    def test_ship_controls_have_no_finding_labels(self) -> None:
        for backend in BACKENDS:
            text = (CORPUS / backend / "no-findings-ship.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("<verdict>SHIP</verdict>", text, backend)
            self.assertNotIn("Problem:", text, backend)

    def test_ratchet_controls_only_describe_prior_findings(self) -> None:
        for backend in BACKENDS:
            text = (CORPUS / backend / "ratchet-only.md").read_text(
                encoding="utf-8"
            )
            self.assertRegex(text, r"(?i)prior finding")
            self.assertNotRegex(text, r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?severity")

    def test_no_anchor_controls_never_guess_a_file_or_line(self) -> None:
        for backend in BACKENDS:
            text = (CORPUS / backend / "no-anchor.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?i)(?:severity|P[0-3])")
            self.assertNotRegex(text, r"(?i)file\s*:\s*line")
            self.assertNotRegex(text, r"(?m)^\s*(?:path|file|line)\s*[:=]")

    def test_unparseable_controls_have_no_schema_labels_or_verdict(self) -> None:
        for backend in BACKENDS:
            text = (CORPUS / backend / "unparseable.md").read_text(encoding="utf-8")
            for marker in (
                "<verdict>",
                "Severity:",
                "Severity =",
                "Confidence:",
                "Confidence =",
                "Classification:",
                "Classification =",
                "Prior finding",
            ):
                self.assertNotIn(marker, text, f"{backend}: {marker}")

    def test_manifest_keeps_ground_truth_separate_from_raw_input(self) -> None:
        cases = {case["id"]: case["expected"] for case in self.index["cases"]}
        self.assertEqual(cases["no-findings-ship"]["item_count"], 0)
        self.assertTrue(cases["ratchet-only"]["ratchet_only"])
        self.assertEqual(cases["no-anchor"]["anchor_count"], 0)
        self.assertFalse(cases["unparseable"]["structured"])
        for backend, survey in self.index["backends"].items():
            self.assertGreaterEqual(len(survey["observed_variants"]), 3, backend)


if __name__ == "__main__":
    unittest.main()
