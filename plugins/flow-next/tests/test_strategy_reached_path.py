import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
STRATEGY = REPO / "plugins/flow-next/skills/flow-next-strategy"
SKILL = STRATEGY / "SKILL.md"
FIRST_RUN = STRATEGY / "references/first-run.md"
UPDATE = STRATEGY / "references/update.md"
MIRROR = REPO / "plugins/flow-next/codex/skills/flow-next-strategy"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


class StrategyReachedPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = _text(SKILL)
        cls.first = _text(FIRST_RUN)
        cls.update = _text(UPDATE)

    # Evidence-ledger archaeology removed 2026-08-07 - shipped optimizations are
    # history, not invariants. (Ledger B1 input-hash anchoring and the
    # accuracy/discards ledger-shape checks deleted; live skill-file tests remain.)

    def test_root_keeps_classification_and_non_clobber_safety_inline(self) -> None:
        for required in (
            "Foreign-file resolution",
            "Keeping existing STRATEGY.md unchanged.",
            "Confirm destructive overwrite?",
            "confirm-overwrite",
            "unable to classify STRATEGY.md safely",
            "leaving it unchanged",
            "and $n >= 5",
            ".sections_filled <= .total_sections",
            '.generator_match == (.generator == "flow-next-strategy")',
        ):
            self.assertIn(required, self.root)
        self.assertIn("read and follow `references/first-run.md`", self.root)
        self.assertIn("read and follow `references/update.md`", self.root)
        self.assertIn("Do not read the unselected workflow.", self.root)

    def test_mutually_exclusive_workflows_are_cold_in_root(self) -> None:
        self.assertNotIn("### Phase 1: First-run interview", self.root)
        self.assertNotIn("### Phase 2: Update run", self.root)
        self.assertNotIn("Evidence scan (ground drift", self.root)
        self.assertNotIn("Per-section atomic writes", self.root)
        self.assertIn("## Phase 1: First-run interview", self.first)
        self.assertIn("## Phase 2: Update run", self.update)

    def test_first_run_preserves_interview_write_and_confirmation_contracts(self) -> None:
        for required in (
            "Read `references/interview.md`.",
            "read `references/strategy-template.md`",
            "before the next question fires",
            "<!-- worth revisiting -->",
            "`commit`, `edit-section`, `abandon`",
            "leave the file as-is",
        ):
            self.assertIn(required, self.first)
        self.assertLess(
            self.first.index("read `references/strategy-template.md`"),
            self.first.index("build the partial draft"),
        )

    def test_update_preserves_grounding_non_clobber_and_confirmation(self) -> None:
        for required in (
            "Read `references/interview.md`",
            "Dormant track",
            "Undeclared work",
            "Contradicted boundary",
            "Untouched sections preserved byte-identical",
            "`commit`, `edit-section`, `abandon`",
            "leave the file as-is",
        ):
            self.assertIn(required, self.update)
        self.assertNotIn("references/first-run.md", self.update)
        self.assertNotIn("references/strategy-template.md", self.update)

    def test_codex_mirror_routes_match_after_conductor_regeneration(self) -> None:
        mirror_first = MIRROR / "references/first-run.md"
        mirror_update = MIRROR / "references/update.md"
        if not mirror_first.exists() or not mirror_update.exists():
            self.skipTest("parallel-wave conductor owns combined Codex mirror regeneration")

        mirror_root = _text(MIRROR / "SKILL.md")
        self.assertIn("references/first-run.md", mirror_root)
        self.assertIn("references/update.md", mirror_root)
        self.assertIn("Do not read the unselected workflow.", mirror_root)
        self.assertIn("## Phase 1: First-run interview", _text(mirror_first))
        self.assertIn("## Phase 2: Update run", _text(mirror_update))


if __name__ == "__main__":
    unittest.main()
