"""Tests for `_export_parse_acceptance_criteria` heading tolerance.

Canonical heading since 1.1.4 is `## Acceptance Criteria` (matches the
canonical template at `plugins/flow-next/templates/spec.md`). The parser
also tolerates two legacy forms for back-compat:

- `## Acceptance` — plan-skill template pre-1.1.4 (and `flowctl spec
  skeleton` output, locked by the R22 invariant).
- `## Acceptance criteria` — older lowercase-criteria form.
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


if __name__ == "__main__":
    unittest.main()
