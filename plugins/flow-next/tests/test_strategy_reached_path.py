import hashlib
import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
STRATEGY = REPO / "plugins/flow-next/skills/flow-next-strategy"
SKILL = STRATEGY / "SKILL.md"
FIRST_RUN = STRATEGY / "references/first-run.md"
UPDATE = STRATEGY / "references/update.md"
INTERVIEW = STRATEGY / "references/interview.md"
TEMPLATE = STRATEGY / "references/strategy-template.md"
LEDGER = REPO / "optimization/reached-path/strategy-candidate.json"
B1 = REPO / "optimization/reached-path/fixtures/b1/strategy"
MIRROR = REPO / "plugins/flow-next/codex/skills/flow-next-strategy"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StrategyReachedPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = _text(SKILL)
        cls.first = _text(FIRST_RUN)
        cls.update = _text(UPDATE)
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_ledger_is_anchored_to_consistent_b1_inputs(self) -> None:
        expected = self.ledger["lineage"]["input_hashes"]
        for manifest_path in B1.glob("*.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(expected, manifest["prompt_hashes"])
            self.assertEqual("B1", manifest["baseline"])
        self.assertTrue(self.ledger["lineage"]["verified_before_mutation"])
        self.assertIn("never to B0", self.ledger["lineage"]["rule"])

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

    def test_candidate_hashes_and_reached_path_metrics_are_exact(self) -> None:
        paths = {
            str(path.relative_to(REPO)): path
            for path in (SKILL, FIRST_RUN, UPDATE, INTERVIEW, TEMPLATE)
        }
        self.assertEqual(
            self.ledger["candidate"]["source_hashes"],
            {name: _hash(path) for name, path in paths.items()},
        )

        chars = {name: len(_text(path)) for name, path in paths.items()}
        root = str(SKILL.relative_to(REPO))
        first = str(FIRST_RUN.relative_to(REPO))
        update = str(UPDATE.relative_to(REPO))
        interview = str(INTERVIEW.relative_to(REPO))
        template = str(TEMPLATE.relative_to(REPO))
        expected = {
            "strategy.absent": chars[root] + chars[first] + chars[interview] + chars[template],
            "strategy.husk": chars[root] + chars[first] + chars[interview],
            "strategy.foreign-keep": chars[root],
            "strategy.foreign-abort": chars[root],
            "strategy.generated-first-run": chars[root] + chars[first] + chars[interview] + chars[template],
            "strategy.update": chars[root] + chars[update] + chars[interview],
            "strategy.malformed-unknown": chars[root],
        }
        for fixture in self.ledger["fixtures"]:
            self.assertEqual(expected[fixture["id"]], fixture["candidate_reached_path_chars"])
            baseline = fixture["baseline_reached_path_chars"]
            if baseline is not None:
                self.assertLess(fixture["candidate_reached_path_chars"], baseline)
                self.assertEqual(
                    fixture["candidate_reached_path_chars"] - baseline,
                    fixture["delta_chars"],
                )

    def test_every_accuracy_cell_passes_and_discards_are_retained(self) -> None:
        self.assertTrue(all(v == "pass" for v in self.ledger["accuracy_checks"].values()))
        self.assertEqual("keep", self.ledger["verdict"]["decision"])
        self.assertIsNone(self.ledger["verdict"]["wall_time_claim"])
        self.assertEqual(2, len(self.ledger["discards"]))
        self.assertTrue(all(row["decision"] == "discard" for row in self.ledger["discards"]))
        self.assertTrue(all(row["score"]["quality"] for row in self.ledger["discards"]))
        self.assertTrue(all(row["score"]["efficiency"] for row in self.ledger["discards"]))
        self.assertTrue(all(row["reason"].startswith("Discarded:") for row in self.ledger["discards"]))

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
