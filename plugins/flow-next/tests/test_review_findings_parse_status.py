"""Additive parse diagnostics and zero-introduced review containers."""
import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_review_findings_parser import FLOWCTL, parse

BLOCK = """Severity: P2
Confidence: 100
Classification: introduced
Problem: A stale result is reused.
Suggestion: Refresh the result.
"""


class ParseStatusTest(unittest.TestCase):
    def test_six_draw_shapes(self):
        shapes = [
            (BLOCK.replace("\nConfidence: 100\nClassification:", " · Confidence: 100 · Classification:"), None),
            ("0 introduced findings.\n<verdict>SHIP</verdict>", None),
            (BLOCK.replace("100", "90"), "invalid-enum"),
            (BLOCK + "Confidence: 25\n", "duplicate-label"),
            (BLOCK + "File:line: ../escape.py:9\n", "invalid-anchor"),
            ("Review appears fine.", "no-findings-container"),
        ]
        for text, reason in shapes:
            with self.subTest(text=text):
                status = {}
                result = parse(text, "codex", parse_status=status)
                self.assertEqual(result is None, reason is not None)
                self.assertEqual(status["reason"], reason)
                self.assertEqual(status["status"], "unparsed" if reason else "parsed")

    def test_first_bad_block(self):
        status = {}
        self.assertIsNone(parse(BLOCK + "\n" + BLOCK.replace("100", "90"), "codex", parse_status=status))
        self.assertEqual(status, {"status": "unparsed", "reason": "invalid-enum", "block": 2})

    def test_zero_introduced_preserves_prior_and_preexisting(self):
        prior = parse(BLOCK, "codex")
        text = BLOCK.replace("introduced", "pre_existing") + "\nClassification counts: 0 introduced, 1 pre_existing.\n<verdict>SHIP</verdict>"
        result = parse(text, "codex", receipt="round-2", round_number=2,
                       prior=prior, supersedes=prior["sourceReceiptId"])
        self.assertIsNotNone(result)
        self.assertEqual(len(result["items"]), 2)
        carried = next(item for item in result["items"] if item["id"] == prior["items"][0]["id"])
        self.assertEqual(carried["status"], "open")
        self.assertEqual(carried["firstSeenReceiptId"], prior["sourceReceiptId"])
        self.assertEqual(carried["lastSeenReceiptId"], "round-2")
        self.assertEqual(result["items"][1]["classification"], "pre_existing")
        status = {}
        self.assertIsNone(parse(text + "\nPrior findings: all fixed except #1", "codex",
                               receipt="round-2", round_number=2, prior=prior,
                               supersedes=prior["sourceReceiptId"], parse_status=status))
        self.assertEqual(status["reason"], "invalid-prior-resolution")

    def test_count_only_and_ship_required(self):
        for wording in ("No introduced findings", "zero introduced findings", "Classification counts: 0 introduced, 0 pre_existing", "Introduced: 0"):
            self.assertIsNotNone(parse(wording + "\n<verdict>SHIP</verdict>", "codex"))
            self.assertIsNone(parse(wording + "\n<verdict>NEEDS_WORK</verdict>", "codex"))

    def test_fanout_draw_exposes_parse_status(self):
        review = "Zero introduced findings.\n<verdict>SHIP</verdict>"
        registry = {"run_exec": lambda *a, **kw: (review, None, 0, ""),
                    "extract_review": lambda output: output}
        with tempfile.TemporaryDirectory() as temp, patch.dict(FLOWCTL.BACKEND_REGISTRY, {"codex": registry}), patch.object(FLOWCTL, "_receipt_model_effort", return_value=("model", None)):
            row = FLOWCTL._review_fanout_run_draw(
                {"axis": "correctness", "spec": SimpleNamespace(backend="codex")},
                "prompt", Path(temp), argparse.Namespace(), Path(temp))
            self.assertEqual(row["parse_status"]["status"], "parsed")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                FLOWCTL._review_fanout_emit_dispatch(
                    argparse.Namespace(json=True), None, True, "rid", "reservation",
                    Path(temp), [row], "main")
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["draws"][0]["parse_status"], row["parse_status"])
