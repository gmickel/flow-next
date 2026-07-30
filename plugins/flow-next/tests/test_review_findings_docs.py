"""Pins the public structured-review findings contract (fn-136 R5)."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "plugins" / "flow-next" / "docs"
CONTRACT = DOCS / "review-findings.md"


class ReviewFindingsDocsTest(unittest.TestCase):
    def test_contract_covers_schema_and_consumer_semantics(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        required = {
            '"schemaVersion": 1',
            '"sourceReceiptId"',
            '"reviewKind"',
            '"supersedesReceiptId"',
            '"priorFindingId"',
            '"firstSeenReceiptId"',
            '"lastSeenReceiptId"',
            "`P0`, `P1`, `P2`, `P3`",
            "`introduced`, `pre_existing`",
            "`pre-existing` / `pre existing` → `pre_existing`",
            "`open`, `fixed`, `not_fixed`, `withdrawn`",
            "`base`, `head`",
            "Canonical item order",
            "Exactly one must remain",
            "A stale sibling tip does not invalidate",
            "stale evidence",
            "Explicit empty `items`",
            "receipt contract, not an internal API",
        }
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_contract_pins_executable_bounds_and_fallback(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        for bound in (
            "1 MiB UTF-8",
            "256 KiB UTF-8",
            "| Items per container | 200 |",
            "| `rIds` per item | 32, unique |",
            "| `baseSha` and `headSha` | 160 characters |",
            "| Anchor paths | 1,024 characters |",
            "| Item title | 240 characters |",
            "| Item body | 4,000 characters |",
            "| Item suggestion | 4,000 characters |",
        ):
            with self.subTest(bound=bound):
                self.assertIn(bound, text)
        self.assertIn("rejection boundaries, not truncation targets", text)
        self.assertIn("Unsupported version, invalid field, or ambiguous lineage", text)
        self.assertIn("Ignore unsupported structured data without turning it into a pass", text)
        self.assertIn("positive JSON integers—booleans do not qualify", text)
        self.assertIn("must use round 1", text)
        self.assertIn("7–64 lowercase hexadecimal characters", text)

    def test_identity_is_explicit_not_semantically_inferred(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn(
            "Fully restated finding prose is not semantic identity",
            " ".join(text.split()),
        )
        self.assertIn(
            "Only parser-emitted `id` and `priorFindingId` edges establish identity",
            " ".join(text.split()),
        )
        self.assertIn("consumers never match findings by title", " ".join(text.split()))
        self.assertIn(
            "Every valid successor carries the complete prior snapshot forward",
            " ".join(text.split()),
        )
        self.assertIn(
            "A `Prior finding N` ratchet record updates the carried item's status",
            " ".join(text.split()),
        )
        self.assertIn("creates an additional finding and ID", " ".join(text.split()))

    def test_anchor_absence_and_invalid_evidence_are_distinct(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn(
            "valid location evidence without enough snapshot binding, produces no anchor",
            normalized,
        )
        self.assertIn(
            "Malformed or conflicting supplied locations, unsafe paths, invalid ranges or sides, and invalid blob OIDs reject the entire structured generation",
            normalized,
        )
        self.assertIn("must not repair or truncate invalid anchor evidence", normalized)

    def test_receipt_memory_and_discovery_surfaces_cross_link_contract(self) -> None:
        for relative in (
            "README.md",
            "architecture.md",
            "flowctl.md",
            "memory-schema.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(
                    "review-findings.md",
                    (DOCS / relative).read_text(encoding="utf-8"),
                )

        root_surfaces = {
            "README.md": "docs/review-findings.md",
            "GLOSSARY.md": "## Structured finding",
            "STRATEGY.md": "Receipts are the portable product boundary",
            "CHANGELOG.md": "optional versioned structured findings",
        }
        for relative, phrase in root_surfaces.items():
            with self.subTest(relative=relative):
                self.assertIn(
                    phrase,
                    (REPO / relative).read_text(encoding="utf-8"),
                )

    def test_memory_contract_does_not_conflate_status_owners(self) -> None:
        text = (DOCS / "memory-schema.md").read_text(encoding="utf-8")
        self.assertIn("Review findings are evidence, memory is learning", text)
        self.assertIn("not whether a review finding is open or fixed", text)
        self.assertIn("never mutates a receipt", text)


if __name__ == "__main__":
    unittest.main()
