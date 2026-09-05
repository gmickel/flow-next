"""Route accuracy must reflect measured files, including missing references."""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


class PlanReviewCandidateMeasurementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        harness = Path(__file__).resolve().parents[3] / "optimization/reached-path"
        sys.path.insert(0, str(harness))
        try:
            cls.candidate = importlib.import_module("plan_review_candidate")
        finally:
            sys.path.remove(str(harness))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        candidate = self.candidate
        paths = [candidate.ROOT, candidate.COMMON]
        paths.extend(candidate.backend_file(name) for name in candidate.BACKENDS)
        for path in paths:
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("instruction\n", encoding="utf-8")
        baseline = self.repo / "optimization/reached-path/fixtures/b1/plan-review"
        baseline.mkdir(parents=True)
        for route in candidate.ROUTES:
            (baseline / f"{route}.json").write_text(
                json.dumps({"metrics": {"reached_path_chars": 1000}}),
                encoding="utf-8",
            )

    def test_complete_routes_can_pass(self):
        evidence = self.candidate.route_evidence(self.repo)
        self.assertTrue(all(evidence["accuracy"].values()))
        self.assertEqual(evidence["ratchet"]["verdict"], "keep")

    def test_missing_root_aborts_measurement(self):
        root = self.repo / self.candidate.ROOT
        root.unlink()
        with self.assertRaises(FileNotFoundError) as raised:
            self.candidate.route_evidence(self.repo)
        self.assertEqual(raised.exception.filename, str(root))

    def test_missing_required_reference_discards_smaller_candidate(self):
        for relative in (
            self.candidate.COMMON,
            self.candidate.backend_file("host"),
        ):
            with self.subTest(path=relative):
                target = self.repo / relative
                original = target.read_text(encoding="utf-8")
                target.unlink()
                try:
                    evidence = self.candidate.route_evidence(self.repo)
                finally:
                    target.write_text(original, encoding="utf-8")
                self.assertTrue(evidence["accuracy"]["every_route_reduced"])
                self.assertEqual(evidence["ratchet"]["verdict"], "discard")


if __name__ == "__main__":
    unittest.main()
