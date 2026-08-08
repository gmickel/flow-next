"""Pins the public structured-review findings contract (fn-136 R5)."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "plugins" / "flow-next" / "docs"
CONTRACT = DOCS / "review-findings.md"


class ReviewFindingsDocsTest(unittest.TestCase):
    def test_contract_covers_schema_and_consumer_semantics(self) -> None:
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Field names, enums, and kind mappings only below.
        text = CONTRACT.read_text(encoding="utf-8")
        required = {
            '"schemaVersion": 1',
            '"sourceReceiptId"',
            '"reviewKind"',
            '"supersedesReceiptId"',
            '"priorFindingId"',
            '"firstSeenReceiptId"',
            '"lastSeenReceiptId"',
            "`plan_review` | `plan`",
            "`impl_review` | `implementation`",
            "`completion_review` | `completion`",
            "`qa_verdict` | `qa`",
            "`findings.backend`",
            "`P0`, `P1`, `P2`, `P3`",
            "`introduced`, `pre_existing`",
            "`pre-existing` / `pre existing` → `pre_existing`",
            "`open`, `fixed`, `not_fixed`, `withdrawn`",
            "`base`, `head`",
            "Canonical item order",
        }
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_contract_pins_executable_bounds_and_fallback(self) -> None:
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Numeric bounds only below.
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
        self.assertIn("7–64 lowercase hexadecimal characters", text)

    def test_identity_is_explicit_not_semantically_inferred(self) -> None:
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Identity grammar tokens only below.
        text = CONTRACT.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn("`Prior finding N`", normalized)
        self.assertIn(
            "finding-` plus the first 32 lowercase hexadecimal characters of SHA-256",
            normalized,
        )
        self.assertIn(
            "`flow-next-finding-v1\\0<firstSeenReceiptId>\\0<ordinal>`",
            text,
        )

    def test_receipt_memory_and_discovery_surfaces_cross_link_contract(self) -> None:
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Cross-link existence only below.
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
            # Root GLOSSARY.md is a compact vocabulary dictionary; the
            # long-form `## Structured finding` entry moved to the archive.
            "agent_docs/archive/GLOSSARY-full.md": "## Structured finding",
        }
        for relative, phrase in root_surfaces.items():
            with self.subTest(relative=relative):
                self.assertIn(
                    phrase,
                    (REPO / relative).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
