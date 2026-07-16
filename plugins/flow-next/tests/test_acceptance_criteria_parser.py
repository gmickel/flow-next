"""Tests for `_export_parse_acceptance_criteria` heading tolerance + R-ID forms.

Canonical heading since 1.1.4 is `## Acceptance Criteria` (matches the
canonical template at `plugins/flow-next/templates/spec.md`). The parser
also tolerates two legacy forms for back-compat:

- `## Acceptance` — plan-skill template pre-1.1.4 (and `flowctl spec
  skeleton` output, locked by the R22 invariant).
- `## Acceptance criteria` — older lowercase-criteria form.

R-ID format: canonical is `R<digits>`. Since fn-49.1 the parser also
recognizes `R<digits><a-z>` (single-letter suffix) for sub-scoped sibling
criteria like `R4a` / `R4b`. Multi-letter suffixes (`R4ab`) and separators
(`R-4`) remain rejected by design.
"""

import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
