"""Unit tests for /flow-next:capture biz-context routing + sparse-layer
suggestion (fn-44.9 / fn-113.3, covers R24, R25).

Capture's runtime routing is host-agent-driven (skill-vs-flowctl architectural
rule from CLAUDE.md) — there is no `capture_route()` helper to drive. The
tests cover the contract:

  - Skill content: the capture skill documents the 9-row signal-category
    routing table with the exact destinations from R24, the `1 <= count < 3`
    threshold rule, and the no-fire-at-zero rule (R22 invariant).

  - R25 threshold (fn-113 eviction): the fire/no-fire rule lives in capture
    skill prose, not `flowctl scope suggest` (subcommand deleted). A
    prose-contract pin locks the constant threshold sentence so the rule
    stays stated.

Pin shape (agent_docs/adding-skills.md, "Prose-contract tests — pin content +
reachability"): every assertion below pins CONTENT at whichever capture file
carries it today, plus REACHABILITY — the home must sit on the load path that
starts at `SKILL.md`. None of these contracts care that the prose currently
sits in `workflow.md`; they care that an agent reading capture still meets it.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
CAPTURE_DIR = PLUGIN_DIR / "skills" / "flow-next-capture"

# The always-loaded entry file every capture agent starts from.
SPINE = "SKILL.md"

# Byte-exact R25 threshold sentence pinned by fn-113.3. Keep in sync with
# capture SKILL.md + the Phase 6 Biz-suggestion footer, wherever it lives.
R25_THRESHOLD_SENTENCE = (
    "The R25 business-pass suggestion fires when the captured conversation "
    "names 1-2 distinct R24 signal categories (the same `1 <= n < 3` rule), "
    "agent-judged."
)


# Nine R24 signal categories with their canonical markdown destinations
# (per the spec R24). Each entry: (row_number, category_substring,
# required_destinations) where row_number is the 1-based index in the
# capture routing table and required_destinations is a list of substrings
# ALL of which must appear in the table row's Destination column.
# Categories 5 and 8 carry two `OR`-joined destinations — both must be
# present in the row body. Category 3 carries an `outcome-AC +` pair —
# both must be present.
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

ROUTING_TABLE_HEADER = "| # | Signal category | Destination"


def _capture_corpus() -> dict[str, str]:
    """Every markdown file the capture skill ships, keyed by relative path."""
    paths = [
        CAPTURE_DIR / "SKILL.md",
        CAPTURE_DIR / "workflow.md",
        CAPTURE_DIR / "phases.md",
        *sorted((CAPTURE_DIR / "references").glob("*.md")),
    ]
    return {
        p.relative_to(CAPTURE_DIR).as_posix(): p.read_text(encoding="utf-8")
        for p in paths
        if p.is_file()
    }


def _reachable(corpus: dict[str, str]) -> set[str]:
    """Files an agent can reach from `SKILL.md` by following file mentions.

    BFS: a file is reachable when an already-reachable file names it (by
    relative path or basename). This IS the reachability half of the pin —
    content that lands in a file nobody routes to has left the load path.
    """
    seen = {SPINE}
    queue = [SPINE]
    while queue:
        text = corpus[queue.pop()]
        for rel in corpus:
            if rel in seen:
                continue
            if rel in text or rel.rsplit("/", 1)[-1] in text:
                seen.add(rel)
                queue.append(rel)
    return seen


CORPUS = _capture_corpus()
REACHABLE = _reachable(CORPUS)


def homes_for(predicate) -> list[str]:
    """Capture files whose body satisfies `predicate`, reachable ones first."""
    hits = [rel for rel, text in CORPUS.items() if predicate(text)]
    return sorted(hits, key=lambda rel: rel not in REACHABLE)


def assert_reachable_content(case: unittest.TestCase, predicate, what: str) -> str:
    """Assert `what` is stated in SOME capture file that is reachable.

    Returns the reachable home (relative path) so callers can pin the
    routing link at the spine when they want the stricter statement.
    """
    hits = homes_for(predicate)
    case.assertTrue(
        hits,
        f"no file in the capture skill states {what} — scanned {sorted(CORPUS)}",
    )
    reachable_hits = [rel for rel in hits if rel in REACHABLE]
    case.assertTrue(
        reachable_hits,
        f"{what} only lives in unreachable file(s) {hits} — nothing on the "
        f"path from {SPINE} carries it",
    )
    return reachable_hits[0]


def _parse_routing_table(body: str) -> list[tuple[int, str, str]]:
    """Extract the 9-row R24 routing table from a capture file.

    Returns list of (row_number, category_cell, destination_cell). Rows
    are recognized by the leading `| <int> | ... |` shape, scoped to
    the table whose header is `| # | Signal category | Destination(s) |`.
    """
    lines = body.splitlines()
    rows: list[tuple[int, str, str]] = []
    in_table = False
    for _i, line in enumerate(lines):
        if line.strip().startswith(ROUTING_TABLE_HEADER):
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


class TestCaptureDocumentsRoutingTable(unittest.TestCase):
    """R24: the capture skill documents all 9 signal categories with their
    R24 destinations, in a file the agent can reach from `SKILL.md`."""

    def setUp(self) -> None:
        self.table_home = assert_reachable_content(
            self,
            lambda text: ROUTING_TABLE_HEADER in text,
            f"the R24 routing table header ({ROUTING_TABLE_HEADER!r})",
        )
        self.body = CORPUS[self.table_home]
        self.rows = _parse_routing_table(self.body)
        self.rows_by_num = {n: (cat, dest) for n, cat, dest in self.rows}

    def test_routing_table_has_nine_rows(self) -> None:
        """The 9-row R24 routing table is present at the expected shape
        (header `| # | Signal category | Destination(s) |`, 9 numbered
        rows below). Failure modes: missing rows, accidental drop of
        the header, renumbered rows."""
        self.assertEqual(
            len(self.rows),
            9,
            f"expected 9 R24 routing rows in {self.table_home}, got "
            f"{len(self.rows)}: {self.rows!r}",
        )

    def test_routing_table_rows_in_order(self) -> None:
        """Rows numbered 1..9 in declared order — no gaps, no
        renumbering."""
        numbers = [r[0] for r in self.rows]
        self.assertEqual(numbers, list(range(1, 10)))

    def test_each_row_routes_to_required_destinations(self) -> None:
        """Per-row routing assertion: each of the 9 R24 categories appears
        on its expected row AND the destination cell lists every required
        destination substring. Catches accidental swaps of destinations
        between rows (e.g., MVP -> Goal & Context instead of Boundaries),
        dropped destinations (e.g., category 3 missing outcome-AC), or
        renumbered rows."""
        for row_num, category_substr, dests in SIGNAL_CATEGORIES:
            self.assertIn(
                row_num,
                self.rows_by_num,
                f"row {row_num} missing from routing table ({self.table_home})",
            )
            cat_cell, dest_cell = self.rows_by_num[row_num]
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
        row must surface the OR (the routing prose says "pick one
        destination per signal"). Test the table-row text contains the
        word "OR" for those two rows so the routing rule is discoverable
        in the table, not just the prose."""
        for row_num in (5, 8):
            cat_cell, dest_cell = self.rows_by_num[row_num]
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
        _, dest_cell = self.rows_by_num[3]
        self.assertIn("outcome-AC", dest_cell)
        self.assertIn("Motivation", dest_cell)
        # Must use `+` not `OR` for category 3.
        self.assertNotRegex(dest_cell.replace("OR", ""), r"\bOR\b")

    def test_threshold_rule_documented(self) -> None:
        """R25 threshold `1 <= count < 3` must be stated explicitly in a
        capture file the agent reaches (routing prose, Phase 6 footer, or a
        reference the spine routes to)."""
        # Accept several equivalent ways to state the threshold.
        threshold_patterns = [
            r"1\s*<=?\s*N\s*<\s*3",
            r"1\s*<=?\s*n\s*<\s*3",
            r"1\s*<=?\s*count\s*<\s*3",
            r"at least one .*\bfewer than three",
            r"BIZ_SIGNAL_CATEGORIES\s*=\s*[12]",
        ]
        assert_reachable_content(
            self,
            lambda text: any(
                re.search(p, text, re.IGNORECASE) for p in threshold_patterns
            ),
            "the `1 <= N < 3` R25 threshold",
        )

    def test_no_fire_at_zero_rule_documented(self) -> None:
        """R22 invariant: BIZ_SIGNAL_CATEGORIES=0 → no-fire. Some reachable
        capture file must state this (Phase 6 footer, routing prose, or a
        routed reference)."""
        zero_rules = [
            r"BIZ_SIGNAL_CATEGORIES\s*=\s*0.*no.fire",
            r"BIZ_SIGNAL_CATEGORIES=0.*no.fire",
            r"zero biz signals.*silent",
            r"never mentioned biz context.*zero new prompts",
            r"no-fire \(exit 1\), keeping",
            r"count\s*==\s*0.*no.fire",
        ]
        assert_reachable_content(
            self,
            lambda text: any(
                re.search(p, text, re.IGNORECASE | re.DOTALL) for p in zero_rules
            ),
            "the no-fire-at-zero rule (R22 invariant)",
        )

    def test_suggestion_phrasing_matches_r25(self) -> None:
        """R25 spec verbatim: the suggestion text contains
        `business-requirements signals` + `/flow-next:interview --scope=business`.
        Both phrases stay pinned; either may live in any reachable capture
        file."""
        for phrase in (
            "business-requirements signals",
            "/flow-next:interview --scope=business",
        ):
            with self.subTest(phrase=phrase):
                assert_reachable_content(
                    self,
                    lambda text, phrase=phrase: phrase in text,
                    f"the R25 suggestion phrase {phrase!r}",
                )


class TestR25ThresholdProseContract(unittest.TestCase):
    """fn-113.3: R25 threshold lives in capture skill prose, not flowctl.

    Pins the constant threshold sentence so the rule stays stated after the
    `scope suggest` eviction. Scope resolve/bank/write-policy are untouched.
    """

    def test_threshold_sentence_is_stated_and_reachable(self) -> None:
        """The byte-exact R25 threshold sentence survives somewhere on the
        capture load path — and `SKILL.md` names that home, so the sentence
        is reachable rather than merely present."""
        home = assert_reachable_content(
            self,
            lambda text: R25_THRESHOLD_SENTENCE in text,
            "the pinned R25 threshold sentence",
        )
        if home != SPINE:
            self.assertIn(
                home,
                CORPUS[SPINE],
                f"{SPINE} must route to {home}, the home of the pinned R25 "
                f"threshold sentence",
            )

    def test_threshold_rule_reachable_from_skill_md(self) -> None:
        """`SKILL.md` step 6 is the gating index: whatever file carries the
        pinned sentence, the spine itself must still state the
        `1 <= BIZ_SIGNAL_CATEGORIES < 3` fire rule so the branch is decided
        before any deeper file is read."""
        self.assertIn(
            "the R25 business-pass suggestion fires at "
            "`1 <= BIZ_SIGNAL_CATEGORIES < 3`",
            CORPUS[SPINE],
            "SKILL.md step 6 must carry the R25 threshold fire rule",
        )

    def test_capture_branches_on_agent_threshold_not_flowctl(self) -> None:
        """Phase 6 must branch on BIZ_SIGNAL_CATEGORIES inline; no capture
        file may call the deleted `flowctl scope suggest` subcommand.

        The executed fence is a location-is-contract case (agent_docs
        exception: an executed gate skeleton must sit in the file that runs
        it) — but that file only has to be reachable, so the fence is
        located dynamically and the negative sweeps the whole skill."""
        for rel, text in CORPUS.items():
            with self.subTest(file=rel):
                self.assertNotIn(
                    "scope suggest",
                    text,
                    f"capture must not call deleted `flowctl scope suggest` "
                    f"({rel})",
                )
        # Agent-owned shell branch for the 1 <= n < 3 rule.
        assert_reachable_content(
            self,
            lambda text: re.search(
                r'BIZ_SIGNAL_CATEGORIES"\s+-ge\s+1\s*\]\s*&&\s*\[\s*'
                r'"\$BIZ_SIGNAL_CATEGORIES"\s+-lt\s+3',
                text,
            )
            is not None,
            "the inline `1 <= BIZ_SIGNAL_CATEGORIES < 3` shell branch",
        )


if __name__ == "__main__":
    unittest.main()
