"""`qa_verdict` receipt schema + four-outcome projection tests (fn-53.2, fn-72.1).

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

fn-72.1 extends the receipt with the lean additive fields the pilot stage +
make-pr read from the persisted receipt (workflow.md §6.3):

  * `head_sha`  — the R1b freshness key (`git rev-parse HEAD` at QA time);
  * `branch`    — the branch the pass ran against;
  * `rid_coverage` — `{covered, total, rids: [{id, coverage}]}`, the §2.2 spine;
  * `open_p0p1` — now an array of OBJECTS `{id, severity, reason, file}`
                  (was bare ids), so make-pr surfaces structured findings.

The additive fields must be **additive only** — the receipt still passes the
guard (which gates on `verdict` and ignores everything else), and the
free-form object fields must survive `json.dump` escaping unscathed (the
heredoc-vs-python lesson — a hostile reason with a quote/backslash/newline
must round-trip to valid JSON).

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


# A single open P0/P1 finding as the workflow §6.3 object shape (fn-72.1: objects,
# not bare ids). Only NEEDS_WORK carries an open finding in these fixtures.
_OPEN_FINDING = {
    "id": "S2-F1",
    "severity": "P0",
    "reason": "checkout submit throws; cart never clears",
    "file": "app/routes/checkout.tsx",
}


def _build_receipt(qa_outcome: str, spec_id: str = "fn-53-flow-nextqa-live-app-real-user-qa-pass") -> dict:
    """Build a qa_verdict receipt exactly as workflow.md §6.3 writes it (fn-72.1 fields)."""
    verdict = _project(qa_outcome)
    receipt = {
        "type": "qa_verdict",
        "id": spec_id,
        "mode": "ralph",
        "verdict": verdict,
        "qa_outcome": qa_outcome,
        # fn-72.1 additive fields:
        "head_sha": "0123456789abcdef0123456789abcdef01234567",
        "branch": spec_id,
        "rid_coverage": {
            "covered": 2,
            "total": 3,
            "rids": [
                {"id": "R1", "coverage": "live"},
                {"id": "R2", "coverage": "subtracted"},
                {"id": "R3", "coverage": "no_live_scenario"},
            ],
        },
        # open_p0p1 is now an array of objects (was bare ids).
        "open_p0p1": [_OPEN_FINDING] if qa_outcome == "NEEDS_WORK" else [],
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


class TestQaReceiptAdditiveFields(unittest.TestCase):
    """fn-72.1 — head_sha / branch / rid_coverage + object-shaped open_p0p1."""

    def test_freshness_and_orientation_fields_present(self) -> None:
        """Every receipt carries head_sha (R1b freshness key) + branch as strings."""
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                receipt = _build_receipt(qa_outcome)
                self.assertIn("head_sha", receipt)
                self.assertIsInstance(receipt["head_sha"], str)
                self.assertIn("branch", receipt)
                self.assertIsInstance(receipt["branch"], str)

    def test_rid_coverage_shape(self) -> None:
        """rid_coverage is {covered, total, rids:[{id, coverage}]} with valid coverage enum."""
        valid_coverage = {"live", "subtracted", "no_live_scenario", "backend_cli"}
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                cov = _build_receipt(qa_outcome)["rid_coverage"]
                self.assertIsInstance(cov, dict)
                self.assertIn("covered", cov)
                self.assertIn("total", cov)
                self.assertIsInstance(cov["rids"], list)
                for row in cov["rids"]:
                    self.assertIn("id", row)
                    self.assertIn(row["coverage"], valid_coverage)

    def test_open_p0p1_entries_are_objects(self) -> None:
        """Open findings are {id, severity, reason, file} objects, not bare ids (fn-72.1)."""
        receipt = _build_receipt("NEEDS_WORK")
        self.assertTrue(receipt["open_p0p1"], "NEEDS_WORK fixture must carry an open finding")
        for finding in receipt["open_p0p1"]:
            self.assertIsInstance(finding, dict)
            self.assertEqual({"id", "severity", "reason", "file"}, set(finding))
            self.assertIn(finding["severity"], {"P0", "P1"})

    def test_additive_fields_do_not_break_the_guard(self) -> None:
        """The extra fields are additive — the guard (gates on verdict only) still accepts."""
        for qa_outcome in PROJECTION:
            with self.subTest(qa_outcome=qa_outcome):
                err = guard.validate_receipt_data(_build_receipt(qa_outcome))
                self.assertEqual(err, "", f"{qa_outcome} receipt rejected: {err!r}")

    def test_free_form_object_fields_serialize_safely(self) -> None:
        """A hostile finding reason (quote + backslash + newline) round-trips to valid JSON.

        Mirrors the heredoc-vs-python lesson: open_p0p1[].reason / .file and the
        rid_coverage rows are agent-authored free-form — they MUST be JSON-encoded
        (json.dump), never raw-interpolated. A receipt built with a hostile value
        must still parse back identically.
        """
        receipt = _build_receipt("NEEDS_WORK")
        receipt["open_p0p1"][0]["reason"] = 'he said "boom"\\crash\nnext line'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qa-hostile.json"
            path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            roundtrip = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(roundtrip["open_p0p1"][0]["reason"], 'he said "boom"\\crash\nnext line')
        # And the guard still accepts the on-disk file.
        with tempfile.TemporaryDirectory() as tmp:
            rdir = Path(tmp) / ".flow" / "review-receipts"
            rdir.mkdir(parents=True, exist_ok=True)
            fpath = rdir / f"qa-{receipt['id']}.json"
            fpath.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            self.assertEqual(guard.validate_receipt_file(str(fpath)), "")


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
