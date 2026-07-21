"""fn-112.4: fenced-JSON review tallies preferred; prose is logged fallback.

The <verdict> tag contract is untouched. JSON-block path is primary;
prose-regex parsers remain as explicit fallback when the block is omitted.
"""

from __future__ import annotations

import importlib.util
import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location(
        "flowctl_review_json_tallies", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


def _with_stderr(fn):
    buf = io.StringIO()
    with redirect_stderr(buf):
        result = fn()
    return result, buf.getvalue()


JSON_BLOCK = (
    "Some prose findings.\n\n"
    "```json\n"
    '{"suppressed_count":{"50":3,"25":7},"classification_counts":'
    '{"introduced":2,"pre_existing":4},"unaddressed":["R4a","R5"]}\n'
    "```\n"
    "<verdict>NEEDS_WORK</verdict>\n"
)

PROSE_ONLY = (
    "Suppressed findings: 3 at anchor 50, 7 at anchor 25.\n"
    "Classification counts: 2 introduced, 4 pre_existing.\n"
    "Unaddressed R-IDs: [R4a, R5]\n"
    "<verdict>NEEDS_WORK</verdict>\n"
)


class TestReviewJsonTalliesPreferred(unittest.TestCase):
    def test_json_block_preferred_over_prose(self) -> None:
        # Prose lines intentionally disagree with the JSON block; JSON wins.
        mixed = (
            "Suppressed findings: 9 at anchor 0.\n"
            "Classification counts: 9 introduced, 9 pre_existing.\n"
            "Unaddressed R-IDs: [R99]\n"
            "```json\n"
            '{"suppressed_count":{"50":3},"classification_counts":'
            '{"introduced":1,"pre_existing":0},"unaddressed":["R1"]}\n'
            "```\n"
            "<verdict>SHIP</verdict>\n"
        )
        suppressed, err1 = _with_stderr(
            lambda: flowctl.parse_suppressed_count(mixed)
        )
        counts, err2 = _with_stderr(
            lambda: flowctl.parse_classification_counts(mixed)
        )
        rids, err3 = _with_stderr(lambda: flowctl.parse_unaddressed_rids(mixed))
        self.assertEqual(suppressed, {"50": 3})
        self.assertEqual(counts, {"introduced": 1, "pre_existing": 0})
        self.assertEqual(rids, ["R1"])
        self.assertIn("via json", err1)
        self.assertIn("via json", err2)
        self.assertIn("via json", err3)

    def test_json_block_parses_canonical_shape(self) -> None:
        suppressed, err = _with_stderr(
            lambda: flowctl.parse_suppressed_count(JSON_BLOCK)
        )
        self.assertEqual(suppressed, {"50": 3, "25": 7})
        self.assertIn("via json", err)

        counts, err = _with_stderr(
            lambda: flowctl.parse_classification_counts(JSON_BLOCK)
        )
        self.assertEqual(counts, {"introduced": 2, "pre_existing": 4})
        self.assertIn("via json", err)

        rids, err = _with_stderr(
            lambda: flowctl.parse_unaddressed_rids(JSON_BLOCK)
        )
        self.assertEqual(rids, ["R4a", "R5"])
        self.assertIn("via json", err)

    def test_prose_fallback_when_block_omitted(self) -> None:
        suppressed, err = _with_stderr(
            lambda: flowctl.parse_suppressed_count(PROSE_ONLY)
        )
        self.assertEqual(suppressed, {"50": 3, "25": 7})
        self.assertIn("prose-fallback", err)

        counts, err = _with_stderr(
            lambda: flowctl.parse_classification_counts(PROSE_ONLY)
        )
        self.assertEqual(counts, {"introduced": 2, "pre_existing": 4})
        self.assertIn("prose-fallback", err)

        rids, err = _with_stderr(
            lambda: flowctl.parse_unaddressed_rids(PROSE_ONLY)
        )
        self.assertEqual(rids, ["R4a", "R5"])
        self.assertIn("prose-fallback", err)

    def test_invalid_json_block_falls_back_to_prose(self) -> None:
        bad = (
            "```json\n"
            '{"suppressed_count":"not-an-object"}\n'
            "```\n"
            "Suppressed findings: 2 at anchor 50.\n"
        )
        suppressed, err = _with_stderr(
            lambda: flowctl.parse_suppressed_count(bad)
        )
        self.assertEqual(suppressed, {"50": 2})
        self.assertIn("prose-fallback", err)

    def test_verdict_tag_still_extracted(self) -> None:
        self.assertEqual(
            flowctl.parse_codex_verdict(JSON_BLOCK), "NEEDS_WORK"
        )
        self.assertEqual(
            flowctl.parse_codex_verdict(PROSE_ONLY), "NEEDS_WORK"
        )

    def test_deep_findings_json_preferred(self) -> None:
        out = (
            "```json\n"
            '{"deep_findings":[{"id":"a1","severity":"P1","confidence":75,'
            '"classification":"introduced","file":"src/x.py","line":10,'
            '"title":"boom","suggested_fix":"fix it"}]}\n'
            "```\n"
        )
        findings, err = _with_stderr(
            lambda: flowctl.parse_deep_findings(out, "adversarial")
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "a1")
        self.assertEqual(findings[0]["pass"], "adversarial")
        self.assertEqual(findings[0]["file"], "src/x.py")
        self.assertEqual(findings[0]["line"], 10)
        self.assertIn("via json", err)

    def test_deep_findings_prose_fallback(self) -> None:
        out = (
            "**a1** | severity=P1 | confidence=75 | classification=introduced\n"
            "- Location: src/x.py:10\n"
            "- Issue: boom\n"
            "- Suggested fix: fix it\n"
        )
        findings, err = _with_stderr(
            lambda: flowctl.parse_deep_findings(out, "adversarial")
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "a1")
        self.assertIn("prose-fallback", err)

    def test_extract_review_json_block_schema(self) -> None:
        block = flowctl.extract_review_json_block(JSON_BLOCK)
        self.assertIsNotNone(block)
        self.assertEqual(block["unaddressed"], ["R4a", "R5"])
        self.assertIsNone(flowctl.extract_review_json_block(PROSE_ONLY))


if __name__ == "__main__":
    unittest.main()
