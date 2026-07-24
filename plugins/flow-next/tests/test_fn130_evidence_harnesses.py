"""Offline contracts for fn-130 completion-evidence harnesses."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN = load(
    "fn130_plan_agentic_eval",
    REPO / "optimization/plan/run_fn130_agentic_eval.py",
)
PRIME = load(
    "fn130_prime_agentic_eval",
    REPO / "optimization/prime/run_agentic_eval.py",
)
PLAN_REVIEW = load(
    "fn130_plan_review_real_eval",
    REPO / "optimization/reached-path/plan_review_real_eval.py",
)


class Fn130EvidenceHarnessTest(unittest.TestCase):
    def test_plan_output_only_override_is_last(self) -> None:
        prompt = PLAN.emission_prompt("RULES CALL WRITE", "P1", "FIXTURE")
        self.assertGreater(prompt.index("<eval_override>"), prompt.index("</fixture>"))
        self.assertIn("response itself must contain the full", prompt)
        self.assertIn("Do not stop at a proposed tool", prompt)

    def test_prime_transport_usage_extracts_only_usage_object(self) -> None:
        usage = {"input_tokens": 2, "output_tokens": 7}
        self.assertEqual(
            PRIME._transport_usage(json.dumps({"usage": usage, "result": "{}"})),
            usage,
        )
        self.assertIsNone(PRIME._transport_usage("not json"))
        self.assertIsNone(PRIME._transport_usage(json.dumps({"usage": []})))

    def test_plan_score_ratchet_detects_and_clears_regressions(self) -> None:
        emissions = []
        score_rows = []
        for variant in ("b1", "candidate"):
            for run in (1, 2, 3):
                for fixture in ("P1", "P2", "P3", "P4", "P5"):
                    if run == 3 and fixture != "P5":
                        continue
                    row_id = f"{variant}-r{run}-{fixture}"
                    emissions.append(
                        {"id": row_id, "variant": variant, "run": run, "fixture": fixture}
                    )
                    ids = (
                        [f"H{i}" for i in range(1, 8)]
                        if fixture == "P5"
                        else [f"E{i}" for i in range(1, 6)]
                    )
                    score_rows.append(
                        {
                            "id": row_id,
                            "cells": [
                                {"id": cell, "pass": True, "reason": "fixture"}
                                for cell in ids
                            ],
                        }
                    )
        result = PLAN.validate_score(emissions, {"rows": score_rows})
        self.assertTrue(result["zero_loss"])
        self.assertEqual(result["regressions"], [])
        next(
            row
            for row in score_rows
            if row["id"] == "candidate-r1-P1"
        )["cells"][0]["pass"] = False
        result = PLAN.validate_score(emissions, {"rows": score_rows})
        self.assertFalse(result["zero_loss"])
        self.assertEqual(result["regressions"], ["run1/P1/E1"])

    def test_plan_review_corpus_has_all_three_controls(self) -> None:
        corpus = PLAN_REVIEW.corpus()
        self.assertEqual(set(corpus), {"risky", "clean", "user-edited"})
        self.assertIn("batch size 37", corpus["user-edited"])


if __name__ == "__main__":
    unittest.main()
