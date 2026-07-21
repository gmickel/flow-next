"""Unit tests for /flow-next:capture biz-context routing + sparse-layer
suggestion (fn-44.9 / fn-113.3, covers R24, R25).

Capture's runtime routing is host-agent-driven (skill-vs-flowctl architectural
rule from CLAUDE.md) — there is no `capture_route()` helper to drive. The
tests cover the contract:

  - Skill content: `workflow.md` documents the 9-row signal-category routing
    table with the exact destinations from R24, the `1 <= count < 3`
    threshold rule, and the no-fire-at-zero rule (R22 invariant). The
    threshold + no-fire-at-zero may live in §2.6 (routing prose) OR Phase 6
    (Biz-suggestion footer); the contract is "documented somewhere in
    workflow.md," scanned whole-file.

  - R25 threshold (fn-113 eviction): the fire/no-fire rule lives in capture
    skill prose, not `flowctl scope suggest` (subcommand deleted). A
    prose-contract pin locks the constant threshold sentence so the rule
    stays stated.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
CAPTURE_DIR = PLUGIN_DIR / "skills" / "flow-next-capture"

# Byte-exact R25 threshold sentence pinned by fn-113.3. Keep in sync with
# capture SKILL.md + workflow.md Phase 6 Biz-suggestion footer.
R25_THRESHOLD_SENTENCE = (
    "The R25 business-pass suggestion fires when the captured conversation "
    "names 1-2 distinct R24 signal categories (the same `1 <= n < 3` rule), "
    "agent-judged."
)


# Nine R24 signal categories with their canonical markdown destinations
# (per the spec R24). Each entry: (row_number, category_substring,
# required_destinations) where row_number is the 1-based index in
# capture/workflow.md's routing table and required_destinations is a list
# of substrings ALL of which must appear in the table row's Destination
# column. Categories 5 and 8 carry two `OR`-joined destinations — both
# must be present in the row body. Categories 3 carries an `outcome-AC +`
# pair — both must be present.
SIGNAL_CATEGORIES = [
    # (row, category-substring, [destination-substrings-all-required])
    (1, "Target user", ["Goal & Context"]),
    (2, "Problem framing", ["Goal & Context"]),
    (3, "Success metrics", ["outcome-AC", "Decision Context", "Motivation"]),
    (4, "MVP", ["Boundaries"]),
    (5, "Business constraints", ["Goal & Context", "Decision Context", "Motivation"]),
    (6, "NOT to build", ["Boundaries"]),
    (7, "Prioritization", ["Decision Context", "Motivation"]),
    (8, "Business risks", ["Goal & Context", "Decision Context", "Motivation"]),
    (9, "UX", ["Goal & Context"]),
]


def _parse_routing_table(body: str) -> list[tuple[int, str, str]]:
    """Extract the 9-row R24 routing table from workflow.md.

    Returns list of (row_number, category_cell, destination_cell). Rows
    are recognized by the leading `| <int> | ... |` shape, scoped to
    the table whose header is `| # | Signal category | Destination(s) |`.
    """
    lines = body.splitlines()
    rows: list[tuple[int, str, str]] = []
    in_table = False
    for i, line in enumerate(lines):
        if line.strip().startswith("| # | Signal category | Destination"):
            in_table = True
            continue
        if not in_table:
            continue
        # Separator line `|---|---|---|`.
        if line.strip().startswith("|---"):
            continue
        # End of table = blank line or non-pipe row.
        stripped = line.strip()
        if not stripped or not stripped.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue
        try:
            row_num = int(cells[0])
        except ValueError:
            continue
        rows.append((row_num, cells[1], cells[2]))
    return rows


class TestCaptureWorkflowDocumentsRoutingTable(unittest.TestCase):
    """R24: workflow.md §2.6 (or equivalent) documents all 9 signal
    categories with their R24 destinations."""

    def setUp(self) -> None:
        self.workflow_path = CAPTURE_DIR / "workflow.md"
        self.body = self.workflow_path.read_text(encoding="utf-8")

    def test_routing_table_has_nine_rows(self) -> None:
        """The 9-row R24 routing table is present at the expected shape
        (header `| # | Signal category | Destination(s) |`, 9 numbered
        rows below). Failure modes: missing rows, accidental drop of
        the header, renumbered rows."""
        rows = _parse_routing_table(self.body)
        self.assertEqual(
            len(rows),
            9,
            f"expected 9 R24 routing rows in workflow.md, got {len(rows)}: "
            f"{rows!r}",
        )

    def test_routing_table_rows_in_order(self) -> None:
        """Rows numbered 1..9 in declared order — no gaps, no
        renumbering."""
        rows = _parse_routing_table(self.body)
        numbers = [r[0] for r in rows]
        self.assertEqual(numbers, list(range(1, 10)))

    def test_each_row_routes_to_required_destinations(self) -> None:
        """Per-row routing assertion: each of the 9 R24 categories appears
        on its expected row AND the destination cell lists every required
        destination substring. Catches accidental swaps of destinations
        between rows (e.g., MVP -> Goal & Context instead of Boundaries),
        dropped destinations (e.g., category 3 missing outcome-AC), or
        renumbered rows."""
        rows = _parse_routing_table(self.body)
        rows_by_num = {n: (cat, dest) for n, cat, dest in rows}
        for row_num, category_substr, dests in SIGNAL_CATEGORIES:
            self.assertIn(
                row_num,
                rows_by_num,
                f"row {row_num} missing from routing table",
            )
            cat_cell, dest_cell = rows_by_num[row_num]
            self.assertIn(
                category_substr,
                cat_cell,
                f"row {row_num}: category cell {cat_cell!r} missing "
                f"substring {category_substr!r}",
            )
            for dest in dests:
                self.assertIn(
                    dest,
                    dest_cell,
                    f"row {row_num} ({category_substr}): destination cell "
                    f"{dest_cell!r} missing required destination {dest!r}",
                )

    def test_category_5_and_8_have_or_routing(self) -> None:
        """R24 specifies categories 5 (constraints) and 8 (risks) have
        `Goal & Context` OR `Decision Context > Motivation` — the table
        row must surface the OR (the rule on line 357 says "pick one
        destination per signal"). Test the table-row text contains the
        word "OR" for those two rows so the routing rule is discoverable
        in the table, not just the prose."""
        rows = _parse_routing_table(self.body)
        rows_by_num = {n: (cat, dest) for n, cat, dest in rows}
        for row_num in (5, 8):
            cat_cell, dest_cell = rows_by_num[row_num]
            self.assertRegex(
                dest_cell,
                r"\bOR\b",
                f"row {row_num} ({cat_cell}) must use OR-routing notation",
            )

    def test_category_3_lists_both_destinations(self) -> None:
        """Category 3 (success metrics) routes to BOTH outcome-AC AND
        Decision Context > Motivation — joined by `+` per the table.
        A success metric becomes both an R-ID AND a rationale entry
        (not OR — both, per R24)."""
        rows = _parse_routing_table(self.body)
        rows_by_num = {n: (cat, dest) for n, cat, dest in rows}
        _, dest_cell = rows_by_num[3]
        self.assertIn("outcome-AC", dest_cell)
        self.assertIn("Motivation", dest_cell)
        # Must use `+` not `OR` for category 3.
        self.assertNotRegex(
            dest_cell.replace("OR", ""), r"\bOR\b"
        )

    def test_threshold_rule_documented(self) -> None:
        """R25 threshold `1 <= count < 3` must be stated explicitly somewhere
        in workflow.md (§2.6 OR Phase 6 footer — per plan-sync breadcrumb)."""
        # Accept several equivalent ways to state the threshold.
        threshold_patterns = [
            r"1\s*<=?\s*N\s*<\s*3",
            r"1\s*<=?\s*n\s*<\s*3",
            r"1\s*<=?\s*count\s*<\s*3",
            r"at least one .*\bfewer than three",
            r"BIZ_SIGNAL_CATEGORIES\s*=\s*[12]",
        ]
        matched = any(
            re.search(p, self.body, re.IGNORECASE) for p in threshold_patterns
        )
        self.assertTrue(
            matched,
            "workflow.md must document the `1 <= N < 3` threshold somewhere",
        )

    def test_no_fire_at_zero_rule_documented(self) -> None:
        """R22 invariant: BIZ_SIGNAL_CATEGORIES=0 → no-fire. Workflow.md must
        state this somewhere (Phase 6 footer or §2.6 routing prose)."""
        zero_rules = [
            r"BIZ_SIGNAL_CATEGORIES\s*=\s*0.*no.fire",
            r"BIZ_SIGNAL_CATEGORIES=0.*no.fire",
            r"zero biz signals.*silent",
            r"never mentioned biz context.*zero new prompts",
            r"no-fire \(exit 1\), keeping",
            r"count\s*==\s*0.*no.fire",
        ]
        matched = any(
            re.search(p, self.body, re.IGNORECASE | re.DOTALL) for p in zero_rules
        )
        self.assertTrue(
            matched,
            "workflow.md must document the no-fire-at-zero rule (R22 invariant)",
        )

    def test_suggestion_phrasing_matches_r25(self) -> None:
        """R25 spec verbatim: the suggestion text contains
        `business-requirements signals` + `/flow-next:interview --scope=business`."""
        self.assertIn("business-requirements signals", self.body)
        self.assertIn("/flow-next:interview --scope=business", self.body)


class TestR25ThresholdProseContract(unittest.TestCase):
    """fn-113.3: R25 threshold lives in capture skill prose, not flowctl.

    Pins the constant threshold sentence so the rule stays stated after the
    `scope suggest` eviction. Scope resolve/bank/write-policy are untouched.
    """

    def test_threshold_sentence_in_workflow_md(self) -> None:
        body = (CAPTURE_DIR / "workflow.md").read_text(encoding="utf-8")
        self.assertIn(
            R25_THRESHOLD_SENTENCE,
            body,
            "workflow.md Phase 6 must carry the pinned R25 threshold sentence",
        )

    def test_threshold_sentence_in_skill_md(self) -> None:
        body = (CAPTURE_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            R25_THRESHOLD_SENTENCE,
            body,
            "SKILL.md step 6 must carry the pinned R25 threshold sentence",
        )

    def test_workflow_branches_on_agent_threshold_not_flowctl(self) -> None:
        """Phase 6 must branch on BIZ_SIGNAL_CATEGORIES inline; must not call
        the deleted `flowctl scope suggest` subcommand."""
        workflow = (CAPTURE_DIR / "workflow.md").read_text(encoding="utf-8")
        self.assertNotIn(
            "scope suggest",
            workflow,
            "capture must not call deleted `flowctl scope suggest`",
        )
        # Agent-owned shell branch for the 1 <= n < 3 rule.
        self.assertRegex(
            workflow,
            r'BIZ_SIGNAL_CATEGORIES"\s+-ge\s+1\s*\]\s*&&\s*\[\s*"\$BIZ_SIGNAL_CATEGORIES"\s+-lt\s+3',
            "workflow.md must branch on 1 <= BIZ_SIGNAL_CATEGORIES < 3 inline",
        )


if __name__ == "__main__":
    unittest.main()
