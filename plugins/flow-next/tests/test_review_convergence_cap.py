"""Convergence-ratchet + deterministic-cap tests (fn-90 R4 + R5).

R4 (convergence ratchet): ``build_rereview_preamble`` injects the prior round's
findings and flips the re-review contract to shrink-only (verify prior fixed;
only NEW >=Major blocks; all-fixed + no new >=Major => MUST SHIP). Without prior
findings (round 1 / legacy receipt) it falls back to the original fresh-review
preamble (back-compatible).

R5 (deterministic cap): a flowctl-owned cumulative round counter on spec state,
enforced at ``MAX_REVIEW_ITERATIONS`` (default 3), surviving FRESH invocations,
reset only on SHIP / re-plan. At the cap the review refuses with an ESCALATE
marker (exit REVIEW_CAP_EXIT_CODE), never a retryable error.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location(
        "flowctl_convergence_cap_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


# ------------------------- R4: convergence ratchet -------------------------


class TestConvergenceRatchet(unittest.TestCase):
    def test_no_prior_findings_falls_back_to_fresh_preamble(self):
        """Round 1 / legacy receipt (no prior findings) → original fresh-review
        preamble, no ratchet block, back-compatible."""
        out = flowctl.build_rereview_preamble(["spec.md"], "plan", prior_findings=None)
        self.assertNotIn("CONVERGENCE RATCHET", out)
        self.assertIn("conduct a fresh plan review", out)

    def test_empty_prior_findings_treated_as_fresh(self):
        out = flowctl.build_rereview_preamble(["spec.md"], "plan", prior_findings="   ")
        self.assertNotIn("CONVERGENCE RATCHET", out)

    def test_prior_findings_injects_ratchet_and_shrink_only_contract(self):
        prior = "Finding 1 (Major): worker/Task contradiction with R13."
        out = flowctl.build_rereview_preamble(
            ["spec.md"], "plan", prior_findings=prior
        )
        self.assertIn("CONVERGENCE RATCHET", out)
        self.assertIn(prior, out)
        # Shrink-only contract signals.
        self.assertIn("fixed", out)
        self.assertIn("MUST be", out)
        self.assertIn("SHIP", out)
        # The fresh-review language must be REPLACED by the ratchet closing.
        self.assertNotIn("conduct a fresh plan review", out)

    def test_ratchet_preserves_major_findings_language(self):
        """Convergence, not leniency — every genuine >=Major finding still
        survives (the block says so explicitly)."""
        out = flowctl.build_rereview_preamble(
            ["a.md"], "plan", prior_findings="prior stuff"
        )
        self.assertIn("Major", out)
        self.assertIn("not leniency", out)

    def test_ratchet_applies_to_implementation_review(self):
        out = flowctl.build_rereview_preamble(
            ["src/x.py"], "implementation", prior_findings="prior impl finding"
        )
        self.assertIn("CONVERGENCE RATCHET", out)
        self.assertNotIn("conduct a fresh implementation review", out)

    def test_prior_findings_truncated_when_huge(self):
        prior = "X" * 20000
        out = flowctl.build_convergence_ratchet_block(prior)
        self.assertIn("[prior review truncated]", out)
        self.assertLess(len(out), 20000)

    def test_read_prior_findings_from_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            rp = Path(d) / "receipt.json"
            rp.write_text(json.dumps({"review": "the prior review text"}))
            self.assertEqual(
                flowctl._read_prior_findings(str(rp)), "the prior review text"
            )

    def test_read_prior_findings_missing_field_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            rp = Path(d) / "receipt.json"
            rp.write_text(json.dumps({"verdict": "NEEDS_WORK"}))
            self.assertIsNone(flowctl._read_prior_findings(str(rp)))

    def test_read_prior_findings_no_receipt_returns_none(self):
        self.assertIsNone(flowctl._read_prior_findings(None))
        self.assertIsNone(flowctl._read_prior_findings("/nonexistent/receipt.json"))


# ------------------------- R5: deterministic cap -------------------------


def _init_flow_repo(root: Path) -> Path:
    """Create a minimal .flow/ with one spec json for cap tests."""
    flow = root / ".flow"
    (flow / "specs").mkdir(parents=True)
    (flow / "tasks").mkdir(parents=True)
    spec_id = "fn-1-demo"
    spec_json = {
        "id": spec_id,
        "title": "Demo",
        "status": "in_progress",
    }
    (flow / "specs" / f"{spec_id}.json").write_text(json.dumps(spec_json))
    return flow


class TestDeterministicCap(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_flow_repo(self.root)
        self.spec_id = "fn-1-demo"
        # Point flowctl at this repo.
        self._cwd = os.getcwd()
        os.chdir(self.root)
        # Clear any inherited cap override.
        self._old_env = os.environ.pop("MAX_REVIEW_ITERATIONS", None)

    def tearDown(self):
        os.chdir(self._cwd)
        if self._old_env is not None:
            os.environ["MAX_REVIEW_ITERATIONS"] = self._old_env
        self._tmp.cleanup()

    def _rounds(self) -> int:
        data = json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )
        return int(data.get("plan_review_rounds", 0) or 0)

    def test_default_cap_is_three(self):
        self.assertEqual(flowctl.get_max_review_iterations(), 3)

    def test_env_overrides_cap(self):
        with mock.patch.dict(os.environ, {"MAX_REVIEW_ITERATIONS": "5"}):
            self.assertEqual(flowctl.get_max_review_iterations(), 5)

    def test_cap_never_zero_or_negative(self):
        for bad in ("0", "-1", "abc", ""):
            with mock.patch.dict(os.environ, {"MAX_REVIEW_ITERATIONS": bad}):
                self.assertEqual(flowctl.get_max_review_iterations(), 3)

    def test_increment_persists_across_fresh_calls(self):
        """Each enforce call increments and persists — cap survives fresh
        invocations (the runaway root cause was a per-invocation reset)."""
        self.assertEqual(
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan"), 1
        )
        self.assertEqual(self._rounds(), 1)
        self.assertEqual(
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan"), 2
        )
        self.assertEqual(
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan"), 3
        )
        self.assertEqual(self._rounds(), 3)

    def test_refuses_at_cap_with_escalate_exit(self):
        for _ in range(3):
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan")
        # 4th call (already at cap 3) must refuse with exit REVIEW_CAP_EXIT_CODE.
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as ctx:
                flowctl.enforce_and_increment_review_cap(self.spec_id, "plan")
        self.assertEqual(ctx.exception.code, flowctl.REVIEW_CAP_EXIT_CODE)
        self.assertIn("ESCALATE", err.getvalue())

    def test_refusal_is_idempotent_no_further_increment(self):
        for _ in range(3):
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan")
        with contextlib.redirect_stderr(io.StringIO()):
            for _ in range(3):
                with self.assertRaises(SystemExit):
                    flowctl.enforce_and_increment_review_cap(self.spec_id, "plan")
        # Counter never climbs past the cap.
        self.assertEqual(self._rounds(), 3)

    def test_reset_on_ship_zeroes_counter(self):
        for _ in range(2):
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan")
        self.assertEqual(self._rounds(), 2)
        flowctl.reset_review_cap(self.spec_id, "plan")
        self.assertEqual(self._rounds(), 0)
        # After reset, can review again.
        self.assertEqual(
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan"), 1
        )

    def test_impl_counter_is_per_task(self):
        t1 = f"{self.spec_id}.1"
        t2 = f"{self.spec_id}.2"
        flowctl.enforce_and_increment_review_cap(self.spec_id, "impl", task_id=t1)
        flowctl.enforce_and_increment_review_cap(self.spec_id, "impl", task_id=t1)
        flowctl.enforce_and_increment_review_cap(self.spec_id, "impl", task_id=t2)
        data = json.loads(
            (self.root / ".flow" / "specs" / f"{self.spec_id}.json").read_text()
        )
        self.assertEqual(data["impl_review_rounds"][t1], 2)
        self.assertEqual(data["impl_review_rounds"][t2], 1)

    def test_impl_cap_independent_per_task(self):
        t1 = f"{self.spec_id}.1"
        t2 = f"{self.spec_id}.2"
        for _ in range(3):
            flowctl.enforce_and_increment_review_cap(
                self.spec_id, "impl", task_id=t1
            )
        # t1 at cap, t2 still fresh.
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                flowctl.enforce_and_increment_review_cap(
                    self.spec_id, "impl", task_id=t1
                )
        self.assertEqual(
            flowctl.enforce_and_increment_review_cap(
                self.spec_id, "impl", task_id=t2
            ),
            1,
        )

    def test_no_spec_state_is_noop(self):
        """Standalone/branch review (spec not on disk) → no cap (returns 0)."""
        self.assertEqual(
            flowctl.enforce_and_increment_review_cap("fn-999-missing", "plan"), 0
        )

    def test_reset_review_rounds_command_re_plan(self):
        """`spec reset-review-rounds` clears the counter (re-plan path)."""
        for _ in range(3):
            flowctl.enforce_and_increment_review_cap(self.spec_id, "plan")
        args = mock.Mock()
        args.id = self.spec_id
        args.impl = False
        args.json = False
        flowctl.cmd_spec_reset_review_rounds(args)
        self.assertEqual(self._rounds(), 0)


if __name__ == "__main__":
    unittest.main()
