"""Receipt schema stability tests (fn-32.4).

Verifies that `--validate`, `--deep`, and `--interactive` each write exactly
their own additive receipt block without mutating other blocks. Ralph's
gate logic reads `verdict` / `mode` / `session_id` only, so new fields are
optional by contract.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v

Covers fn-32.4 AC3-AC7:
  - AC3: default review (no flags) produces only base fields.
  - AC4: each flag alone writes exactly its own block.
  - AC5: combined flags accumulate without mutation.
  - AC6: Ralph gate keys (`verdict`, `mode`, `session_id`) remain stable.
  - AC7: edge cases — empty validator block, all-dropped upgrade path,
         deep SHIP → NEEDS_WORK upgrade, walkthrough never flips verdict.

These tests exercise the in-process merge helpers directly rather than
spawning the backend LLM — the backend-interactive paths are covered by
the smoke suite (see `ralph_smoke_test.sh`).
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location(
        "flowctl_review_receipt_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


BASE_RECEIPT_KEYS = {"type", "id", "mode", "verdict", "session_id", "timestamp"}
VALIDATOR_KEYS = {"validator", "validator_timestamp"}
DEEP_KEYS = {"deep_passes", "deep_findings_count", "deep_timestamp"}
DEEP_OPTIONAL_KEYS = {"cross_pass_promotions", "verdict_before_deep"}
WALKTHROUGH_KEYS = {"walkthrough", "walkthrough_timestamp"}


def _seed_primary_receipt(path: Path, verdict: str = "NEEDS_WORK") -> dict:
    """Write a realistic post-primary-review receipt to ``path``."""
    receipt = {
        "type": "impl_review",
        "id": "fn-32.4",
        "mode": "codex",
        "verdict": verdict,
        "session_id": "019ba000-0000-7000-8000-000000000001",
        "timestamp": "2026-04-24T10:00:00Z",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def _finding(
    fid: str,
    *,
    severity: str = "P1",
    confidence: int = 75,
    classification: str = "introduced",
    file: str = "src/x.py",
    line: int = 10,
    title: str = "something",
) -> dict:
    return {
        "id": fid,
        "severity": severity,
        "confidence": confidence,
        "classification": classification,
        "file": file,
        "line": line,
        "title": title,
        "suggested_fix": "fix it",
    }


# --- AC3: default review has no flag blocks -----------------------------


class TestReceiptDefaultShape(unittest.TestCase):
    """Default review (no flags) writes only base fields."""

    def test_no_flag_blocks_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="SHIP")
            receipt = json.loads(rp.read_text(encoding="utf-8"))

            # Ralph gate keys present
            self.assertIn("verdict", receipt)
            self.assertIn("mode", receipt)
            self.assertIn("session_id", receipt)

            # No flag blocks
            for k in VALIDATOR_KEYS | DEEP_KEYS | DEEP_OPTIONAL_KEYS | WALKTHROUGH_KEYS:
                self.assertNotIn(
                    k,
                    receipt,
                    f"default receipt must not carry {k!r} (flag not set)",
                )


# --- AC4/AC7: validator block shape + upgrade path ----------------------


class TestValidatorBlock(unittest.TestCase):
    """--validate writes exactly its own block; SHIP upgrade only on all-drop."""

    def test_validator_block_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            # Simulate validator dropped 2/3 findings.
            result = {
                "dispatched": 3,
                "dropped": 2,
                "kept": 1,
                "reasons": [
                    {"id": "f1", "file": "a.py", "line": 1, "reason": "already guarded"},
                    {"id": "f2", "file": "b.py", "line": 2, "reason": "misread narrowing"},
                ],
            }
            flowctl._apply_validator_to_receipt(
                str(rp), result, prior_verdict="NEEDS_WORK"
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))

            # Validator block has exactly the 4 contract keys
            self.assertEqual(
                set(receipt["validator"].keys()),
                {"dispatched", "dropped", "kept", "reasons"},
            )
            self.assertIn("validator_timestamp", receipt)

            # Non-validator flag blocks remain absent
            for k in DEEP_KEYS | DEEP_OPTIONAL_KEYS | WALKTHROUGH_KEYS:
                self.assertNotIn(k, receipt)

            # Verdict unchanged (kept > 0)
            self.assertEqual(receipt["verdict"], "NEEDS_WORK")
            self.assertNotIn("verdict_before_validate", receipt)

    def test_validator_all_dropped_upgrades_from_needs_work(self) -> None:
        """All findings dropped + prior NEEDS_WORK → SHIP + verdict_before_validate."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            result = {
                "dispatched": 2,
                "dropped": 2,
                "kept": 0,
                "reasons": [
                    {"id": "f1", "file": "a.py", "line": 1, "reason": "guarded"},
                    {"id": "f2", "file": "b.py", "line": 2, "reason": "correct"},
                ],
            }
            flowctl._apply_validator_to_receipt(
                str(rp), result, prior_verdict="NEEDS_WORK"
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertEqual(receipt["verdict"], "SHIP")
            self.assertEqual(receipt["verdict_before_validate"], "NEEDS_WORK")

    def test_validator_does_not_downgrade_ship(self) -> None:
        """Prior SHIP stays SHIP — validator is drop-only, never invents findings."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="SHIP")

            result = {
                "dispatched": 1,
                "dropped": 1,
                "kept": 0,
                "reasons": [{"id": "f1", "file": "a.py", "line": 1, "reason": "ok"}],
            }
            flowctl._apply_validator_to_receipt(
                str(rp), result, prior_verdict="SHIP"
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertEqual(receipt["verdict"], "SHIP")
            # No upgrade marker because verdict didn't change
            self.assertNotIn("verdict_before_validate", receipt)

    def test_validator_empty_dispatch_writes_block(self) -> None:
        """Zero dispatched findings still writes a deterministic empty block."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            empty = {"dispatched": 0, "dropped": 0, "kept": 0, "reasons": []}
            flowctl._apply_validator_to_receipt(
                str(rp), empty, prior_verdict="NEEDS_WORK"
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertEqual(
                receipt["validator"],
                {"dispatched": 0, "dropped": 0, "kept": 0, "reasons": []},
            )
            self.assertIn("validator_timestamp", receipt)
            self.assertEqual(receipt["verdict"], "NEEDS_WORK")  # unchanged
            self.assertNotIn("verdict_before_validate", receipt)


# --- AC4/AC7: deep-pass block shape + upgrade path ----------------------


class TestDeepPassBlock(unittest.TestCase):
    """--deep writes deep_passes/counts/promotions/timestamp; upgrades SHIP→NEEDS_WORK only."""

    def test_deep_block_shape_no_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="SHIP")

            primary = [_finding("f1", confidence=50, severity="P2", file="src/p.py", line=1)]
            deep_by_pass = {
                "adversarial": [
                    _finding("d1", confidence=25, severity="P3", file="src/d.py", line=2)
                ],
                "security": [],
            }
            merge = flowctl.merge_deep_findings(primary, deep_by_pass)
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial", "security"],
                deep_by_pass=deep_by_pass,
                merge_result=merge,
                prior_verdict="SHIP",
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertEqual(receipt["deep_passes"], ["adversarial", "security"])
            self.assertEqual(
                receipt["deep_findings_count"], {"adversarial": 1, "security": 0}
            )
            self.assertIn("deep_timestamp", receipt)

            # No blocking deep findings → verdict stays SHIP, no upgrade marker.
            self.assertEqual(receipt["verdict"], "SHIP")
            self.assertNotIn("verdict_before_deep", receipt)

            # Non-deep flag blocks remain absent.
            for k in VALIDATOR_KEYS | WALKTHROUGH_KEYS:
                self.assertNotIn(k, receipt)

    def test_deep_ship_to_needs_work_upgrade(self) -> None:
        """SHIP + deep-introduced P0@50+ (or P1+@75+) → NEEDS_WORK + verdict_before_deep."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="SHIP")

            primary: list[dict] = []
            deep_by_pass = {
                "adversarial": [
                    _finding("d1", severity="P0", confidence=75),
                ]
            }
            merge = flowctl.merge_deep_findings(primary, deep_by_pass)
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial"],
                deep_by_pass=deep_by_pass,
                merge_result=merge,
                prior_verdict="SHIP",
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertEqual(receipt["verdict"], "NEEDS_WORK")
            self.assertEqual(receipt["verdict_before_deep"], "SHIP")

    def test_deep_never_downgrades_needs_work(self) -> None:
        """NEEDS_WORK stays NEEDS_WORK even if deep finds nothing — no SHIP path."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            primary: list[dict] = []
            deep_by_pass = {"adversarial": []}
            merge = flowctl.merge_deep_findings(primary, deep_by_pass)
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial"],
                deep_by_pass=deep_by_pass,
                merge_result=merge,
                prior_verdict="NEEDS_WORK",
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertEqual(receipt["verdict"], "NEEDS_WORK")
            self.assertNotIn("verdict_before_deep", receipt)

    def test_deep_cross_pass_promotion_emitted(self) -> None:
        """Primary+deep fingerprint collision promotes primary confidence by one anchor."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            # Primary and deep share fingerprint (same file:line:severity:title).
            primary = [
                _finding("pa", severity="P1", confidence=50, file="src/a.py", line=1)
            ]
            deep_by_pass = {
                "adversarial": [
                    _finding("da", severity="P1", confidence=75, file="src/a.py", line=1)
                ]
            }
            merge = flowctl.merge_deep_findings(primary, deep_by_pass)
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial"],
                deep_by_pass=deep_by_pass,
                merge_result=merge,
                prior_verdict="NEEDS_WORK",
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertIn("cross_pass_promotions", receipt)
            self.assertEqual(len(receipt["cross_pass_promotions"]), 1)
            promo = receipt["cross_pass_promotions"][0]
            self.assertEqual(promo["pass"], "adversarial")
            # Promotion steps up one anchor (50 → 75).
            self.assertEqual(promo["from"], 50)
            self.assertEqual(promo["to"], 75)


# --- AC4/AC7: walkthrough block shape + verdict immutability ------------


class TestWalkthroughBlock(unittest.TestCase):
    """--interactive writes exactly walkthrough+timestamp; verdict never changes."""

    def test_walkthrough_block_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            args = types.SimpleNamespace(
                receipt=str(rp),
                applied=2,
                deferred=1,
                skipped=0,
                acknowledged=0,
                lfg_rest=False,
                json=True,
            )
            # Suppress JSON stdout during the call so test output stays clean.
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_review_walkthrough_record(args)

            receipt = json.loads(rp.read_text(encoding="utf-8"))

            # Walkthrough has exactly the 5 contract keys.
            self.assertEqual(
                set(receipt["walkthrough"].keys()),
                {"applied", "deferred", "skipped", "acknowledged", "lfg_rest"},
            )
            self.assertIn("walkthrough_timestamp", receipt)

            # Walkthrough never flips verdict.
            self.assertEqual(receipt["verdict"], "NEEDS_WORK")

            # Non-walkthrough flag blocks remain absent.
            for k in VALIDATOR_KEYS | DEEP_KEYS | DEEP_OPTIONAL_KEYS:
                self.assertNotIn(k, receipt)

    def test_walkthrough_with_lfg_rest_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            args = types.SimpleNamespace(
                receipt=str(rp),
                applied=3,
                deferred=5,
                skipped=0,
                acknowledged=0,
                lfg_rest=True,
                json=True,
            )
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_review_walkthrough_record(args)

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertIs(receipt["walkthrough"]["lfg_rest"], True)

    def test_walkthrough_lfg_rest_string_parsed(self) -> None:
        """`--lfg-rest` coming in as a string (CLI) is normalized to bool."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            args = types.SimpleNamespace(
                receipt=str(rp),
                applied=0,
                deferred=0,
                skipped=0,
                acknowledged=0,
                lfg_rest="true",
                json=True,
            )
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_review_walkthrough_record(args)

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            self.assertIs(receipt["walkthrough"]["lfg_rest"], True)


# --- AC5: combined flags accumulate without mutation --------------------


class TestCombinedFlags(unittest.TestCase):
    """Running deep → validate → walkthrough composes cleanly."""

    def test_all_three_phases_compose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            # Phase 2: --deep
            primary = [_finding("pa", severity="P1", confidence=50)]
            deep_by_pass = {
                "adversarial": [_finding("da", severity="P2", confidence=25)],
            }
            merge = flowctl.merge_deep_findings(primary, deep_by_pass)
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial"],
                deep_by_pass=deep_by_pass,
                merge_result=merge,
                prior_verdict="NEEDS_WORK",
            )
            after_deep = json.loads(rp.read_text(encoding="utf-8"))
            self.assertIn("deep_passes", after_deep)

            # Phase 3: --validate drops the deep finding.
            validator_result = {
                "dispatched": 2,
                "dropped": 1,
                "kept": 1,
                "reasons": [
                    {"id": "da", "file": "src/x.py", "line": 10, "reason": "fp"}
                ],
            }
            flowctl._apply_validator_to_receipt(
                str(rp), validator_result, prior_verdict="NEEDS_WORK"
            )
            after_validate = json.loads(rp.read_text(encoding="utf-8"))

            # Deep block survived the validate write.
            self.assertEqual(after_validate["deep_passes"], ["adversarial"])
            self.assertIn("deep_findings_count", after_validate)
            # Validator block present.
            self.assertIn("validator", after_validate)
            self.assertIn("validator_timestamp", after_validate)

            # Phase 4: --interactive records walkthrough counts.
            args = types.SimpleNamespace(
                receipt=str(rp),
                applied=1,
                deferred=0,
                skipped=0,
                acknowledged=0,
                lfg_rest=False,
                json=True,
            )
            with mock.patch.object(flowctl, "json_output", lambda *_a, **_kw: None):
                flowctl.cmd_review_walkthrough_record(args)

            final = json.loads(rp.read_text(encoding="utf-8"))

            # All three blocks present.
            self.assertIn("deep_passes", final)
            self.assertIn("validator", final)
            self.assertIn("walkthrough", final)

            # All three timestamps present.
            self.assertIn("deep_timestamp", final)
            self.assertIn("validator_timestamp", final)
            self.assertIn("walkthrough_timestamp", final)

            # Base / Ralph gate keys untouched across composition.
            self.assertEqual(final["type"], "impl_review")
            self.assertEqual(final["id"], "fn-32.4")
            self.assertEqual(final["mode"], "codex")
            self.assertEqual(
                final["session_id"], "019ba000-0000-7000-8000-000000000001"
            )
            self.assertEqual(final["timestamp"], "2026-04-24T10:00:00Z")

    def test_validate_then_deep_does_not_clobber_validator(self) -> None:
        """Order independence: writing deep after validate preserves validator."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="NEEDS_WORK")

            # Validate first (keeps 1, drops 1).
            vr = {
                "dispatched": 2,
                "dropped": 1,
                "kept": 1,
                "reasons": [
                    {"id": "x", "file": "a", "line": 1, "reason": "fp"}
                ],
            }
            flowctl._apply_validator_to_receipt(
                str(rp), vr, prior_verdict="NEEDS_WORK"
            )

            # Then deep (no blocking).
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial"],
                deep_by_pass={"adversarial": []},
                merge_result=flowctl.merge_deep_findings([], {"adversarial": []}),
                prior_verdict="NEEDS_WORK",
            )

            receipt = json.loads(rp.read_text(encoding="utf-8"))
            # Validator block preserved after deep write.
            self.assertIn("validator", receipt)
            self.assertEqual(receipt["validator"]["kept"], 1)
            self.assertIn("validator_timestamp", receipt)
            # Deep block added.
            self.assertIn("deep_passes", receipt)


# --- AC6: Ralph gate reads verdict/mode/session_id across combos --------


class TestRalphGateStability(unittest.TestCase):
    """Existing Ralph scripts read these keys; all flag combos must keep them."""

    RALPH_GATE_KEYS = ("verdict", "mode", "session_id")

    def test_gate_keys_survive_every_combo(self) -> None:
        combos: list[tuple[bool, bool, bool]] = [
            (False, False, False),
            (True,  False, False),
            (False, True,  False),
            (False, False, True),
            (True,  True,  False),
            (True,  False, True),
            (False, True,  True),
            (True,  True,  True),
        ]
        for validate, deep, interactive in combos:
            with self.subTest(validate=validate, deep=deep, interactive=interactive):
                with tempfile.TemporaryDirectory() as tmp:
                    rp = Path(tmp) / "receipt.json"
                    _seed_primary_receipt(rp, verdict="NEEDS_WORK")

                    if deep:
                        flowctl._apply_deep_passes_to_receipt(
                            str(rp),
                            passes_run=["adversarial"],
                            deep_by_pass={"adversarial": []},
                            merge_result=flowctl.merge_deep_findings(
                                [], {"adversarial": []}
                            ),
                            prior_verdict="NEEDS_WORK",
                        )
                    if validate:
                        flowctl._apply_validator_to_receipt(
                            str(rp),
                            {"dispatched": 1, "dropped": 0, "kept": 1, "reasons": []},
                            prior_verdict="NEEDS_WORK",
                        )
                    if interactive:
                        args = types.SimpleNamespace(
                            receipt=str(rp),
                            applied=0,
                            deferred=0,
                            skipped=1,
                            acknowledged=0,
                            lfg_rest=False,
                            json=True,
                        )
                        with mock.patch.object(
                            flowctl, "json_output", lambda *_a, **_kw: None
                        ):
                            flowctl.cmd_review_walkthrough_record(args)

                    receipt = json.loads(rp.read_text(encoding="utf-8"))
                    for k in self.RALPH_GATE_KEYS:
                        self.assertIn(
                            k,
                            receipt,
                            f"Ralph gate key {k!r} missing for combo "
                            f"validate={validate} deep={deep} interactive={interactive}",
                        )
                    self.assertEqual(receipt["mode"], "codex")

    def test_absent_blocks_when_flag_off(self) -> None:
        """Each flag block is absent unless its flag ran (schema additivity)."""
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / "receipt.json"
            _seed_primary_receipt(rp, verdict="SHIP")

            # Only deep.
            flowctl._apply_deep_passes_to_receipt(
                str(rp),
                passes_run=["adversarial"],
                deep_by_pass={"adversarial": []},
                merge_result=flowctl.merge_deep_findings(
                    [], {"adversarial": []}
                ),
                prior_verdict="SHIP",
            )
            receipt = json.loads(rp.read_text(encoding="utf-8"))

            # Deep present; validator + walkthrough absent.
            self.assertIn("deep_passes", receipt)
            for k in VALIDATOR_KEYS | WALKTHROUGH_KEYS:
                self.assertNotIn(k, receipt)


if __name__ == "__main__":
    unittest.main()
