"""Contracts for the fn-136 backend review-output fixture corpus."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "optimization" / "reached-path" / "fixtures" / "review-findings" / "v1"
BACKENDS = {"codex", "copilot", "cursor", "host", "rp", "export"}
CASES = {
    "no-findings-ship",
    "ratchet-only",
    "no-anchor",
    "unparseable",
    "catalog-sample",
}
SEVERITIES = {"P0", "P1", "P2", "P3"}
CONFIDENCES = {0, 25, 50, 75, 100}
CLASSIFICATIONS = {"introduced", "pre_existing"}
STATUSES = {"open", "fixed", "not_fixed", "withdrawn"}


class ReviewFindingsFixtureCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads((CORPUS / "INDEX.json").read_text(encoding="utf-8"))

    def test_manifest_names_every_backend_and_edge_case(self) -> None:
        self.assertEqual(self.index["schema_version"], 1)
        self.assertEqual(set(self.index["backends"]), BACKENDS)
        self.assertEqual(set(self.index["cases"]), CASES)
        self.assertEqual(set(self.index["expectations"]), BACKENDS)

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

    def test_every_catalog_variant_has_provenance_and_fixture_refs(self) -> None:
        sources = {
            source["id"]: source for source in self.index["provenance"]["sources"]
        }
        self.assertEqual(len(sources), len(self.index["provenance"]["sources"]))
        for backend, survey in self.index["backends"].items():
            self.assertGreaterEqual(len(survey["variants"]), 3, backend)
            for variant in survey["variants"]:
                self.assertIn(
                    variant["status"],
                    {"directly_observed", "synthetic_boundary"},
                    variant,
                )
                self.assertTrue(variant["source_refs"], variant)
                self.assertTrue(variant["fixture_refs"], variant)
                for source_ref in variant["source_refs"]:
                    self.assertIn(source_ref, sources, variant)
                    if variant["status"] == "directly_observed":
                        self.assertIn(backend, sources[source_ref]["backends"], variant)
                for fixture_ref in variant["fixture_refs"]:
                    fixture = CORPUS / fixture_ref
                    self.assertTrue(fixture.is_file(), variant)
                    self.assertEqual(fixture.parent.name, backend, variant)

    def test_per_fixture_oracle_is_complete_and_normalized(self) -> None:
        for backend in BACKENDS:
            oracle = self.index["expectations"][backend]
            self.assertEqual(set(oracle), CASES, backend)
            for case, expected in oracle.items():
                fixture = CORPUS / backend / f"{case}.md"
                self.assertTrue(fixture.is_file())
                self.assertIsInstance(expected["structured"], bool)
                if not expected["structured"]:
                    self.assertEqual(expected, {"structured": False})
                    continue
                if case == "ratchet-only":
                    self.assertEqual(expected["new_item_count"], 0)
                    self.assertTrue(expected["ordered_prior_statuses"])
                    self.assertTrue(
                        set(expected["ordered_prior_statuses"]) <= STATUSES
                    )
                    continue
                items = expected["items"]
                if case == "no-findings-ship":
                    self.assertEqual(expected["verdict"], "SHIP")
                    self.assertEqual(items, [])
                    continue
                self.assertGreaterEqual(len(items), 1)
                for item in items:
                    self.assertIn(item["severity"], SEVERITIES)
                    self.assertIn(item["confidence"], CONFIDENCES)
                    self.assertIn(item["classification"], CLASSIFICATIONS)
                    self.assertIn(item["status"], STATUSES)
                    anchor = item["anchor"]
                    if anchor is not None:
                        self.assertEqual(set(anchor), {"path", "startLine"})
                        self.assertFalse(Path(anchor["path"]).is_absolute())
                        self.assertGreater(anchor["startLine"], 0)

    def test_oracle_pins_aliases_anchor_absence_and_ratchet_order(self) -> None:
        expected = self.index["expectations"]
        self.assertEqual(expected["rp"]["no-anchor"]["items"][0]["severity"], "P0")
        self.assertEqual(
            expected["export"]["no-anchor"]["items"][0]["severity"], "P3"
        )
        self.assertIsNone(expected["codex"]["no-anchor"]["items"][0]["anchor"])
        self.assertEqual(
            expected["codex"]["ratchet-only"]["ordered_prior_statuses"],
            ["fixed", "not_fixed"],
        )
        self.assertEqual(
            expected["copilot"]["ratchet-only"]["ordered_prior_statuses"],
            ["fixed", "withdrawn"],
        )


if __name__ == "__main__":
    unittest.main()
