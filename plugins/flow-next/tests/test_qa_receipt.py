"""`qa_verdict` receipt schema + four-outcome projection tests (fn-53.2).

`/flow-next:qa` emits a `type: qa_verdict` receipt carrying the four QA
outcomes in a separate `qa_outcome` field, while `verdict` holds the
Ralph-guard-compatible projection. The guard (`ralph-guard.py`) validates
ONLY `verdict in {SHIP, NEEDS_WORK, MAJOR_RETHINK}` — so every one of the
four outcomes MUST project to a verdict the guard accepts.

This test mirrors the §6.2 projection table from
`skills/flow-next-qa/workflow.md` and asserts, for each of the four
`qa_outcome` fixtures, that:

  1. the documented projection holds (SHIP→SHIP, NEEDS_WORK→NEEDS_WORK,
     BLOCKED→NEEDS_WORK, NA→SHIP);
  2. the projected `verdict` is in the guard's accepted enum;
  3. the on-disk receipt passes the guard's `validate_receipt_data` AND
     `validate_receipt_file` (the standalone-file path — `qa-*.json` is not
     a `parse_receipt_path` pattern, so no type/id mismatch is enforced).

Hermetic: loads the guard in-process via importlib (no subprocess, no
network, no LLM) and writes fixtures to a `tempfile.TemporaryDirectory`.
Windows-portable: `pathlib` everywhere, no shell, no hard-coded separators.

Run:
    python3 -m unittest plugins.flow-next.tests.test_qa_receipt -v
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
TESTS_DIR = HERE.parent
PLUGIN_DIR = TESTS_DIR.parent
GUARD_PY = PLUGIN_DIR / "scripts" / "hooks" / "ralph-guard.py"


def _load_guard() -> Any:
    if not GUARD_PY.is_file():
        raise RuntimeError(f"ralph-guard.py not found at {GUARD_PY}")
    spec = importlib.util.spec_from_file_location("ralph_guard_qa_receipt_under_test", GUARD_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


guard = _load_guard()


# The §6.2 projection table from workflow.md, encoded as the contract under test.
# qa_outcome -> (verdict projection, requires a *_reason field).
PROJECTION = {
    "SHIP": ("SHIP", None),
    "NEEDS_WORK": ("NEEDS_WORK", None),
    "BLOCKED": ("NEEDS_WORK", "blocked_reason"),
    "NA": ("SHIP", "na_reason"),
}


def _project(qa_outcome: str) -> str:
    """Mirror the workflow §6.2 case-statement (the source of truth in prose)."""
    return PROJECTION[qa_outcome][0]


def _build_receipt(qa_outcome: str, spec_id: str = "fn-53-flow-nextqa-live-app-real-user-qa-pass") -> dict:
    """Build a qa_verdict receipt exactly as workflow.md §6.3 writes it."""
    verdict = _project(qa_outcome)
    receipt = {
        "type": "qa_verdict",
        "id": spec_id,
        "mode": "ralph",
        "verdict": verdict,
        "qa_outcome": qa_outcome,
        "open_p0p1": ["S2-F1"] if qa_outcome == "NEEDS_WORK" else [],
        "timestamp": "2026-06-05T12:00:00Z",
    }
    # Reason fields are set ONLY for their own outcome (workflow §6.3 EXTRA).
    reason_field = PROJECTION[qa_outcome][1]
    if reason_field == "blocked_reason":
        receipt["blocked_reason"] = "no live deploy reachable"
    elif reason_field == "na_reason":
        receipt["na_reason"] = "all acceptance criteria are backend/CLI — no driveable UI"
    return receipt


class TestQaVerdictProjection(unittest.TestCase):
    """Each of the four qa_outcome values projects to the documented verdict."""

    def test_all_four_outcomes_projected(self) -> None:
        expected = {
            "SHIP": "SHIP",
            "NEEDS_WORK": "NEEDS_WORK",
            "BLOCKED": "NEEDS_WORK",
            "NA": "SHIP",
        }
        # Guard against the matrix silently growing/shrinking.
        self.assertEqual(set(PROJECTION), set(expected))
        for qa_outcome, want in expected.items():
            with self.subTest(qa_outcome=qa_outcome):
                self.assertEqual(_project(qa_outcome), want)

    def test_blocked_is_not_ship(self) -> None:
        """BLOCKED ≠ FAIL but also ≠ ship-claim — it must project to NEEDS_WORK."""
        self.assertEqual(_project("BLOCKED"), "NEEDS_WORK")

    def test_na_projects_to_ship(self) -> None:
        """No driveable UI → live QA raises no objection → SHIP (with na_reason)."""
        self.assertEqual(_project("NA"), "SHIP")
        self.assertIn("na_reason", _build_receipt("NA"))

    def test_qa_never_emits_major_rethink(self) -> None:
        """The QA matrix has no outcome that maps to MAJOR_RETHINK."""
        self.assertNotIn("MAJOR_RETHINK", {v for v, _ in PROJECTION.values()})


class TestQaReceiptPassesGuard(unittest.TestCase):
    """Each fixture's projected verdict passes the Ralph guard's validators."""

    def test_projected_verdict_in_guard_enum(self) -> None:
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                self.assertIn(_project(qa_outcome), guard.VALID_RECEIPT_VERDICTS)

    def test_validate_receipt_data_accepts_each_fixture(self) -> None:
        """In-memory: validate_receipt_data returns '' (valid) for all four."""
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                receipt = _build_receipt(qa_outcome)
                err = guard.validate_receipt_data(receipt)
                self.assertEqual(err, "", f"{qa_outcome} receipt rejected: {err!r}")

    def test_validate_receipt_file_accepts_each_fixture(self) -> None:
        """On-disk: each qa-*.json fixture passes validate_receipt_file.

        `qa-<id>.json` is NOT a parse_receipt_path pattern, so the file
        validator does not enforce a type/id match — it only checks the
        verdict enum + presence of type/id. All four must pass.
        """
        with tempfile.TemporaryDirectory() as tmp:
            receipts_dir = Path(tmp) / ".flow" / "review-receipts"
            receipts_dir.mkdir(parents=True, exist_ok=True)
            for qa_outcome in PROJECTION:
                with self.subTest(qa_outcome=qa_outcome):
                    receipt = _build_receipt(qa_outcome)
                    path = receipts_dir / f"qa-{receipt['id']}-{qa_outcome.lower()}.json"
                    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
                    err = guard.validate_receipt_file(str(path))
                    self.assertEqual(err, "", f"{qa_outcome} file rejected: {err!r}")

    def test_reason_fields_scoped_to_their_outcome(self) -> None:
        """blocked_reason only on BLOCKED; na_reason only on NA; neither elsewhere."""
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                receipt = _build_receipt(qa_outcome)
                if qa_outcome == "BLOCKED":
                    self.assertIn("blocked_reason", receipt)
                    self.assertNotIn("na_reason", receipt)
                elif qa_outcome == "NA":
                    self.assertIn("na_reason", receipt)
                    self.assertNotIn("blocked_reason", receipt)
                else:
                    self.assertNotIn("blocked_reason", receipt)
                    self.assertNotIn("na_reason", receipt)

    def test_open_p0p1_present_on_every_receipt(self) -> None:
        """open_p0p1 is always a list (empty unless there are open P0/P1)."""
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                receipt = _build_receipt(qa_outcome)
                self.assertIsInstance(receipt["open_p0p1"], list)


class TestGuardRejectsMalformedQaReceipts(unittest.TestCase):
    """Negative cases — the guard is the gate, so confirm it actually rejects."""

    def test_missing_verdict_rejected(self) -> None:
        receipt = _build_receipt("SHIP")
        del receipt["verdict"]
        self.assertNotEqual(guard.validate_receipt_data(receipt), "")

    def test_bad_verdict_rejected(self) -> None:
        receipt = _build_receipt("SHIP")
        receipt["verdict"] = "PASS"  # not in the enum
        self.assertNotEqual(guard.validate_receipt_data(receipt), "")

    def test_missing_id_rejected(self) -> None:
        receipt = _build_receipt("NA")
        del receipt["id"]
        self.assertNotEqual(guard.validate_receipt_data(receipt), "")


if __name__ == "__main__":
    unittest.main()
