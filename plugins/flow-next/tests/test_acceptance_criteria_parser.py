"""Tests for `_export_parse_acceptance_criteria` heading tolerance + R-ID forms.

Canonical heading since 1.1.4 is `## Acceptance Criteria` (matches the
canonical template at `plugins/flow-next/templates/spec.md`). The parser
also tolerates two legacy forms for back-compat:

- `## Acceptance` — plan-skill template pre-1.1.4 and `flowctl prospect
  promote` output (the pre-fn-220 `spec skeleton` shape; the skeleton now
  renders the canonical template).
- `## Acceptance criteria` — older lowercase-criteria form.

R-ID format: canonical is `R<digits>`. Since fn-49.1 the parser also
recognizes `R<digits><a-z>` (single-letter suffix) for sub-scoped sibling
criteria like `R4a` / `R4b`. Multi-letter suffixes (`R4ab`) and separators
(`R-4`) remain rejected by design.
"""

import unittest
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402  (path-injected import)


_BODY_TEMPLATE = """# Spec Title

## Goal & Context

Some goal.

{heading}

- **R1:** First criterion. [user]
- **R2:** Second criterion. [paraphrase]

## Boundaries

Some boundaries.
"""


class TestAcceptanceCriteriaHeadingTolerance(unittest.TestCase):
    def _parse(self, heading: str) -> list[dict]:
        return flowctl._export_parse_acceptance_criteria(
            _BODY_TEMPLATE.format(heading=heading)
        )

    def test_canonical_heading_parses(self) -> None:
        crits = self._parse("## Acceptance Criteria")
        self.assertEqual([c["id"] for c in crits], ["R1", "R2"])

    def test_legacy_acceptance_heading_parses(self) -> None:
        """Plan template pre-1.1.4 / `flowctl spec skeleton` use `## Acceptance`."""
        crits = self._parse("## Acceptance")
        self.assertEqual([c["id"] for c in crits], ["R1", "R2"])

    def test_legacy_lowercase_criteria_heading_parses(self) -> None:
        """Older specs may use `## Acceptance criteria` (lowercase)."""
        crits = self._parse("## Acceptance criteria")
        self.assertEqual([c["id"] for c in crits], ["R1", "R2"])

    def test_no_acceptance_section_returns_empty(self) -> None:
        body = "# Spec\n\n## Goal\n\nText.\n\n## Boundaries\n\nText.\n"
        self.assertEqual(flowctl._export_parse_acceptance_criteria(body), [])

    def test_unrelated_section_with_acceptance_prefix_does_not_match(self) -> None:
        """`## Acceptance Tests` (not Criteria) should NOT match — distinct concept."""
        body = _BODY_TEMPLATE.format(heading="## Acceptance Tests")
        # The R-IDs under "Acceptance Tests" must not leak through as accepted criteria.
        self.assertEqual(flowctl._export_parse_acceptance_criteria(body), [])


class TestAcceptanceCriteriaRIdSuffix(unittest.TestCase):
    """R-ID parser tolerates `R<digits><a-z>` sub-scoped form (fn-49.1).

    Capture-driven specs that emerge with sub-scoped criteria (e.g. fn-48's
    `R4a` / `R4b`) get correctly counted in `acceptance_count` and
    `uncovered_r_ids` instead of being silently dropped.
    """

    def _parse(self, body: str) -> list[dict]:
        return flowctl._export_parse_acceptance_criteria(body)

    def test_all_suffixed_R_ids_parse_in_declaration_order(self) -> None:
        """A spec with only suffixed R-IDs surfaces every one in body order."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R1:** Plain. [user]\n"
            "- **R2:** Plain. [paraphrase]\n"
            "- **R4a:** Sub-scoped a. [user]\n"
            "- **R4b:** Sub-scoped b. [paraphrase]\n"
            "- **R5:** Plain again. [inferred]\n"
            "\n## Boundaries\n\nText.\n"
        )
        ids = [c["id"] for c in self._parse(body)]
        self.assertEqual(ids, ["R1", "R2", "R4a", "R4b", "R5"])

    def test_mixed_plain_and_suffixed_R_ids_preserve_order(self) -> None:
        """`R1`, `R4a`, `R4b` returns three entries, no synthetic `R4` insertion."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R1:** First. [user]\n"
            "- **R4a:** Sub-a. [user]\n"
            "- **R4b:** Sub-b. [user]\n"
            "\n## Boundaries\n\nText.\n"
        )
        ids = [c["id"] for c in self._parse(body)]
        self.assertEqual(ids, ["R1", "R4a", "R4b"])

    def test_R4_and_R4a_R4b_coexist(self) -> None:
        """Rare but valid: R4 was the original, then sub-scoped during revision."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R4:** Parent. [user]\n"
            "- **R4a:** Sub-a. [paraphrase]\n"
            "- **R4b:** Sub-b. [paraphrase]\n"
            "- **R5:** Next. [user]\n"
            "\n## Boundaries\n\nText.\n"
        )
        ids = [c["id"] for c in self._parse(body)]
        self.assertEqual(ids, ["R4", "R4a", "R4b", "R5"])

    def test_lexical_sort_preserves_sibling_order(self) -> None:
        """`sorted(['R5', 'R4b', 'R4a', 'R4'])` → `['R4', 'R4a', 'R4b', 'R5']`.

        The parser itself preserves body order via `finditer`, but downstream
        consumers may re-sort the `acceptance_criteria[].id` array. Verify the
        canonical lexical ordering matches what spec authors expect.
        """
        ids = sorted(["R5", "R4b", "R4a", "R4"])
        self.assertEqual(ids, ["R4", "R4a", "R4b", "R5"])

    def test_multi_letter_suffix_rejected(self) -> None:
        """`R4ab` is out of scope — only single-letter suffix accepted."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R1:** Keep. [user]\n"
            "- **R4ab:** Reject. [user]\n"
            "\n## Boundaries\n\nText.\n"
        )
        ids = [c["id"] for c in self._parse(body)]
        self.assertEqual(ids, ["R1"])

    def test_separator_form_rejected(self) -> None:
        """`R-4` is not a tolerated form — separator breaks the contract."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R1:** Keep. [user]\n"
            "- **R-4:** Reject. [user]\n"
            "\n## Boundaries\n\nText.\n"
        )
        ids = [c["id"] for c in self._parse(body)]
        self.assertEqual(ids, ["R1"])

    def test_lowercase_r_rejected(self) -> None:
        """`r4` / `r4a` are not tolerated — parser stays strict on case."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R1:** Keep. [user]\n"
            "- **r4:** Reject. [user]\n"
            "- **r4a:** Reject. [user]\n"
            "\n## Boundaries\n\nText.\n"
        )
        ids = [c["id"] for c in self._parse(body)]
        self.assertEqual(ids, ["R1"])

    def test_suffix_preserves_tag_extraction(self) -> None:
        """Source-tag suffix (`[user]` / `[paraphrase]` / ...) still extracts on suffixed R-IDs."""
        body = (
            "# Spec\n\n## Acceptance Criteria\n\n"
            "- **R4a:** Sub-a text. [user]\n"
            "- **R4b:** Sub-b text. [paraphrase]\n"
            "\n## Boundaries\n\nText.\n"
        )
        entries = self._parse(body)
        self.assertEqual(
            entries,
            [
                {"id": "R4a", "text": "Sub-a text.", "tag": "user"},
                {"id": "R4b", "text": "Sub-b text.", "tag": "paraphrase"},
            ],
        )


class TestAcceptanceCriteriaBoldRunShapes(unittest.TestCase):
    """Issue #303: bold runs that continue past the R-ID token still parse.

    The old pattern required the bold run to close immediately after the
    token, so title-form (`**R14 - title**`) and parenthetical-form
    (`**R15 (note):**`) bullets were dropped entirely - not flagged, not
    counted. Recognition now anchors on the token and stops at the first
    `**` or `:` boundary.
    """

    # The reporter's five-bullet repro, verbatim in shape.
    REPRO = (
        "## Acceptance Criteria\n"
        "\n"
        "- **R1:** the canonical form, accepted.\n"
        "- **R5a:** a qualified sibling id, also accepted here.\n"
        "- **R14 - the pause protocol must survive a restart** and this is "
        "its body.\n"
        "- **R15 (the parenthetical form):** body text.\n"
        "- **R16:** a criterion whose text\n"
        "  wraps onto a second line that the parser never sees.\n"
        "\n"
        "## Next section\n"
    )

    def test_issue_303_repro_parses_five_of_five(self) -> None:
        crits = flowctl._export_parse_acceptance_criteria(self.REPRO)
        self.assertEqual(
            [c["id"] for c in crits], ["R1", "R5a", "R14", "R15", "R16"]
        )

    def test_R5a_control_still_parses(self) -> None:
        """The #147 positive control: this bug is about the run, not the token."""
        crits = flowctl._export_parse_acceptance_criteria(self.REPRO)
        entry = next(c for c in crits if c["id"] == "R5a")
        self.assertEqual(
            entry["text"], "a qualified sibling id, also accepted here."
        )

    def test_title_form_keeps_title_and_body(self) -> None:
        crits = flowctl._export_parse_acceptance_criteria(self.REPRO)
        entry = next(c for c in crits if c["id"] == "R14")
        self.assertEqual(
            entry["text"],
            "the pause protocol must survive a restart and this is its body.",
        )

    def test_parenthetical_form_keeps_qualifier_and_body(self) -> None:
        crits = flowctl._export_parse_acceptance_criteria(self.REPRO)
        entry = next(c for c in crits if c["id"] == "R15")
        self.assertEqual(entry["text"], "(the parenthetical form): body text.")

    def test_wrapped_text_keeps_continuation_lines(self) -> None:
        crits = flowctl._export_parse_acceptance_criteria(self.REPRO)
        entry = next(c for c in crits if c["id"] == "R16")
        self.assertEqual(
            entry["text"],
            "a criterion whose text wraps onto a second line that the "
            "parser never sees.",
        )

    def test_canonical_bold_close_then_colon_unchanged(self) -> None:
        """`**R1**: text` (colon outside the bold run) parsed before, still does."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1**: outside-colon form. [user]\n"
            "\n## Boundaries\n\nText.\n"
        )
        self.assertEqual(
            flowctl._export_parse_acceptance_criteria(body),
            [{"id": "R1", "text": "outside-colon form.", "tag": "user"}],
        )

    def test_wrapped_capture_stops_at_next_bullet_and_blank_line(self) -> None:
        """A criterion never swallows the next bullet or trailing prose."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1:** first\n"
            "  continues here.\n"
            "- **R2:** second.\n"
            "\n"
            "Trailing prose that belongs to nobody.\n"
            "\n## Boundaries\n\nText.\n"
        )
        self.assertEqual(
            flowctl._export_parse_acceptance_criteria(body),
            [
                {"id": "R1", "text": "first continues here.", "tag": ""},
                {"id": "R2", "text": "second.", "tag": ""},
            ],
        )

    def test_sub_bullet_ends_the_criterion_text(self) -> None:
        """An indented sub-bullet is not criterion text and is not a criterion."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1:** parent text.\n"
            "  - a sub-bullet.\n"
            "- **R2:** next.\n"
            "\n## Boundaries\n\nText.\n"
        )
        self.assertEqual(
            [c["text"] for c in flowctl._export_parse_acceptance_criteria(body)],
            ["parent text.", "next."],
        )

    def test_wrapped_tag_extraction_uses_the_joined_text(self) -> None:
        """A source tag on the continuation line still lands in `tag`."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1:** a criterion whose text\n"
            "  wraps before its tag. [paraphrase]\n"
            "\n## Boundaries\n\nText.\n"
        )
        self.assertEqual(
            flowctl._export_parse_acceptance_criteria(body),
            [
                {
                    "id": "R1",
                    "text": "a criterion whose text wraps before its tag.",
                    "tag": "paraphrase",
                }
            ],
        )


class TestAcceptanceCriteriaResidue(unittest.TestCase):
    """Issue #303 second half: unparsed criterion-shaped bullets are counted.

    The residue count is the durable half of the fix - it stays correct for
    the next unseen bullet shape, which a widened pattern does not. It never
    aborts anything.
    """

    def _scan(self, body: str) -> tuple[list[dict], int]:
        return flowctl._export_scan_acceptance_criteria(body)

    def test_zero_when_every_bullet_parses(self) -> None:
        crits, residue = self._scan(
            TestAcceptanceCriteriaBoldRunShapes.REPRO
        )
        self.assertEqual(len(crits), 5)
        self.assertEqual(residue, 0)

    def test_counts_deliberately_rejected_spellings(self) -> None:
        """`R4ab` / `R-4` stay rejected by design - but no longer silently."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1:** kept.\n"
            "- **R4ab:** multi-letter suffix, rejected.\n"
            "- **R-4:** separator form, rejected.\n"
            "\n## Boundaries\n\nText.\n"
        )
        crits, residue = self._scan(body)
        self.assertEqual([c["id"] for c in crits], ["R1"])
        self.assertEqual(residue, 2)

    def test_ordinary_bold_prose_bullet_is_not_residue(self) -> None:
        """A bold word starting with `R` is prose, not a dropped criterion."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1:** kept.\n"
            "- **Renumber-forbidden** after the first review cycle.\n"
            "\n## Boundaries\n\nText.\n"
        )
        crits, residue = self._scan(body)
        self.assertEqual([c["id"] for c in crits], ["R1"])
        self.assertEqual(residue, 0)

    def test_residue_never_aborts_the_parse(self) -> None:
        """Criteria after an unreadable bullet still come through."""
        body = (
            "## Acceptance Criteria\n\n"
            "- **R1:** kept.\n"
            "- **R2 an unterminated bold run that never closes\n"
            "- **R3:** also kept.\n"
            "\n## Boundaries\n\nText.\n"
        )
        crits, residue = self._scan(body)
        self.assertEqual([c["id"] for c in crits], ["R1", "R3"])
        self.assertEqual(residue, 1)

    def test_no_acceptance_section_has_no_residue(self) -> None:
        self.assertEqual(self._scan("# Spec\n\n## Goal\n\nText.\n"), ([], 0))


if __name__ == "__main__":
    unittest.main()
