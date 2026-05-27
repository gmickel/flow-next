"""Tests for `parse_unaddressed_rids` — the review-output R-ID extractor.

This is the *review-output* parser (reads a reviewer's `Unaddressed R-IDs:`
summary line or a `## Requirements coverage` table), distinct from the *spec*
acceptance-criteria parser (`_export_parse_acceptance_criteria`, covered by
`test_acceptance_criteria_parser.py`).

Regression context: fn-49.1 (1.2.1) taught the spec parser the `R\\d+[a-z]?`
suffix form (R4a / R4b) but left this review-output path on bare `\\bR(\\d+)\\b`
in BOTH the summary-line extractor (`_extract_rids`) and the coverage-table
fallback. A reviewer reporting `Unaddressed R-IDs: [R4a, R4b]` therefore parsed
to `[R5]`-style results with the suffixed R-IDs silently dropped — the R-ID
coverage gate and fix-loop targeting lost exactly the new form. Surfaced by a
live impl-review A/B in 1.3.x; fixed in 1.3.4 by extending both regexes to
`\\bR(\\d+[a-z]?)\\b`, in lockstep with the spec parser.
"""

import unittest
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402  (path-injected import)


class SummaryLineSuffix(unittest.TestCase):
    """The `Unaddressed R-IDs:` summary line preserves single-letter suffixes."""

    def test_suffixed_rids_survive(self) -> None:
        # The regression: this used to drop R4a / R4b and return ['R5'].
        self.assertEqual(
            flowctl.parse_unaddressed_rids("Unaddressed R-IDs: [R4a, R4b, R5]"),
            ["R4a", "R4b", "R5"],
        )

    def test_mixed_plain_and_suffixed(self) -> None:
        self.assertEqual(
            flowctl.parse_unaddressed_rids("Unaddressed R-IDs: [R3, R4a, R10]"),
            ["R3", "R4a", "R10"],
        )

    def test_plain_rids_unchanged(self) -> None:
        # Back-compat: bare R-IDs still parse exactly as before.
        self.assertEqual(
            flowctl.parse_unaddressed_rids("Unaddressed R-IDs: [R3, R5]"),
            ["R3", "R5"],
        )

    def test_singular_heading_suffix(self) -> None:
        self.assertEqual(
            flowctl.parse_unaddressed_rids("Unaddressed R-ID: R4b"),
            ["R4b"],
        )

    def test_empty_marker_returns_empty(self) -> None:
        self.assertEqual(
            flowctl.parse_unaddressed_rids("Unaddressed R-IDs: []"),
            [],
        )

    def test_dedup_preserves_first_seen_order(self) -> None:
        self.assertEqual(
            flowctl.parse_unaddressed_rids("Unaddressed R-IDs: [R4a, R4a, R2]"),
            ["R4a", "R2"],
        )


class CoverageTableFallbackSuffix(unittest.TestCase):
    """The `## Requirements coverage` table fallback preserves suffixes."""

    def _table(self, *rows: str) -> str:
        head = (
            "## Requirements coverage\n\n"
            "| R-ID | Status | Evidence |\n"
            "|------|--------|----------|\n"
        )
        return head + "\n".join(rows) + "\n"

    def test_suffixed_not_addressed_row_surfaces(self) -> None:
        out = self._table(
            "| R4a | not-addressed | — |",
            "| R4b | met | src/x.ts:10 |",
            "| R5 | not-addressed | — |",
        )
        # No summary line → falls through to the table parser.
        self.assertEqual(flowctl.parse_unaddressed_rids(out), ["R4a", "R5"])

    def test_suffixed_met_rows_yield_empty(self) -> None:
        out = self._table(
            "| R4a | met | a |",
            "| R4b | deferred | later |",
        )
        self.assertEqual(flowctl.parse_unaddressed_rids(out), [])


class RejectsMalformed(unittest.TestCase):
    """Multi-letter suffixes and separators stay rejected (parity with spec parser)."""

    def test_multiletter_suffix_not_treated_as_rid(self) -> None:
        # `R4ab` must not parse as `R4a` or `R4`.
        self.assertNotIn(
            "R4a",
            flowctl.parse_unaddressed_rids("Unaddressed R-IDs: [R4ab]") or [],
        )

    def test_separator_form_rejected(self) -> None:
        # `R-4` is not a canonical R-ID token.
        result = flowctl.parse_unaddressed_rids("Unaddressed R-IDs: [R-4]") or []
        self.assertNotIn("R4", result)


if __name__ == "__main__":
    unittest.main()
