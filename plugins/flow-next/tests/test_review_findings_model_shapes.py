"""Findings parser reads the finding layouts current reviewer models write.

The fixtures under fixtures/review-findings/model-shapes/ are real reviewer
outputs (GPT-6.1 Sol in the prompt's labeled layout; GPT-6.2 Sol and Astra in
the layouts they write instead), plus one constructed plan review in the
GPT-6.2 one-line layout.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "plugins" / "flow-next" / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "flowctl_model_shapes_test", REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
)
assert SPEC and SPEC.loader
FLOWCTL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOWCTL)

SHAPES = Path(__file__).resolve().parent / "fixtures" / "review-findings" / "model-shapes"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def text(name: str) -> str:
    return (SHAPES / f"{name}.md").read_text(encoding="utf-8")


def parse(review: str, *, review_kind: str = "implementation", status: dict | None = None):
    return FLOWCTL.parse_review_findings(
        review,
        source_receipt_id="receipt-round-1",
        review_kind=review_kind,
        backend="codex",
        round_number=1,
        head_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        anchor_side="head",
        parse_status=status,
    )


class ModelShapesTest(unittest.TestCase):
    def test_each_layout_parses_every_finding_it_holds(self) -> None:
        cases = {
            "gpt-6.1-sol-labeled": ["P2", "P2"],
            "gpt-6.2-sol-one-line": ["P1", "P1", "P1", "P2", "P2", "P2", "P2", "P2"],
            "gpt-6.2-sol-numbered-heading": ["P1"] + ["P2"] * 7,
            "gpt-6.2-sol-tuple-heading": ["P1", "P1", "P2", "P2", "P2", "P2", "P3"],
            "gpt-6.2-astra-table": ["P1"] * 4 + ["P2"] * 4,
        }
        for name, severities in cases.items():
            with self.subTest(fixture=name):
                status: dict = {}
                result = parse(text(name), status=status)
                self.assertEqual(status["status"], "parsed", status)
                self.assertEqual([item["severity"] for item in result["items"]], severities)
                self.assertTrue(all(item["body"] for item in result["items"]))

    def test_one_line_layout_keeps_anchor_and_rids(self) -> None:
        result = parse(text("gpt-6.2-sol-one-line"))
        first = result["items"][0]
        self.assertEqual(first["anchor"]["path"], "plugins/flow-next/scripts/flowctl_tracker/resolve_verb.py")
        self.assertEqual(first["anchor"]["startLine"], 86)
        self.assertEqual(first["rIds"], ["R1"])
        self.assertIn("suggestion", first)

    def test_prompt_layout_parses_without_the_rewrite(self) -> None:
        # Text in the prompt's layout parses as written, so its findings are
        # exactly what the parser produced before the layout tolerance existed.
        review = text("gpt-6.1-sol-labeled")
        status: dict = {}
        direct = FLOWCTL._parse_review_findings_v1(
            review,
            source_receipt_id="receipt-round-1",
            review_kind="implementation",
            backend="codex",
            round_number=1,
            head_sha=HEAD_SHA,
            base_sha=BASE_SHA,
            supersedes_receipt_id=None,
            prior_findings=None,
            anchor_side="head",
            parse_status=status,
        )
        self.assertIsNotNone(direct)
        self.assertEqual(parse(review), direct)

    def test_plan_review_path_reads_the_one_line_layout(self) -> None:
        container = FLOWCTL.build_review_receipt_findings(
            text("plan-gpt-6.2-sol-one-line"),
            review_type="plan_review",
            review_id="fn-7-rate-limit",
            backend="codex",
            head_sha=HEAD_SHA,
            base_sha=BASE_SHA,
        )
        self.assertIsNotNone(container)
        self.assertEqual(container["reviewKind"], "plan")
        self.assertEqual([item["rIds"] for item in container["items"]], [["R3"], ["R5"]])
        self.assertEqual(container["items"][0]["anchor"]["path"], ".flow/specs/fn-7-rate-limit.md")

    def test_every_review_kind_reads_the_new_layouts(self) -> None:
        for kind in ("plan", "implementation", "completion", "qa"):
            with self.subTest(kind=kind):
                result = parse(text("plan-gpt-6.2-sol-one-line"), review_kind=kind)
                self.assertEqual(len(result["items"]), 2)
                result = parse(text("gpt-6.2-astra-table"), review_kind=kind)
                self.assertEqual(len(result["items"]), 8)

    def test_review_without_findings_or_all_clear_still_fails(self) -> None:
        review = (
            "**Severity** of the change is hard to judge from here; I read the diff.\n\n"
            "<verdict>NEEDS_WORK</verdict>\n"
        )
        status: dict = {}
        self.assertIsNone(parse(review, status=status))
        self.assertEqual(status["reason"], "no-findings-container")

    def test_invalid_anchor_in_a_new_layout_still_fails_with_its_reason(self) -> None:
        review = (
            "- **Severity** P1 · **Confidence** 100 · **Classification** introduced"
            " · **File:Line** `/etc/passwd:3`\n"
            "  **Problem** Reads outside the repository.\n\n"
            "<verdict>NEEDS_WORK</verdict>\n"
        )
        status: dict = {}
        self.assertIsNone(parse(review, status=status))
        self.assertEqual(status["reason"], "invalid-anchor")

    def test_link_anchor_resolves_or_is_dropped(self) -> None:
        review = (
            "- **Severity** P1 · **Confidence** 75 · **Classification** introduced\n"
            "  **File:Line** [providers.py:100](plugins/x/providers.py#L100)\n"
            "  **Problem** First.\n\n"
            "- **Severity** P2 · **Confidence** 75 · **Classification** introduced\n"
            "  **File:Line** [providers.py](/home/someone/wt/plugins/x/providers.py:99)\n"
            "  **Problem** Second.\n\n"
            "<verdict>NEEDS_WORK</verdict>\n"
        )
        items = parse(review)["items"]
        self.assertEqual((items[0]["anchor"]["path"], items[0]["anchor"]["startLine"]), ("plugins/x/providers.py", 100))
        self.assertNotIn("anchor", items[1])

    def test_new_layout_beside_a_parsed_finding_is_not_dropped(self) -> None:
        one_line = (
            "- **Severity** P1 · **Confidence** 100 · **Classification** introduced"
            " · **File:Line** `src/a.py:3`\n  **Problem** New-layout finding.\n\n"
        )
        canonical = (
            "- **Severity:** P2\n- **Confidence:** 75\n- **Classification:** introduced\n"
            "- **Problem:** Canonical finding.\n\n"
        )
        items = parse(canonical + one_line + "<verdict>NEEDS_WORK</verdict>\n")["items"]
        self.assertEqual([item["severity"] for item in items], ["P1", "P2"])

        prior = parse(canonical + "<verdict>NEEDS_WORK</verdict>\n")
        status: dict = {}
        round_two = FLOWCTL.parse_review_findings(
            "Prior finding #1: fixed\n\n" + one_line + "<verdict>NEEDS_WORK</verdict>\n",
            source_receipt_id="receipt-round-2",
            review_kind="implementation",
            backend="codex",
            round_number=2,
            head_sha=HEAD_SHA,
            base_sha=BASE_SHA,
            supersedes_receipt_id="receipt-round-1",
            prior_findings=prior,
            anchor_side="head",
            parse_status=status,
        )
        self.assertEqual(status["status"], "parsed", status)
        self.assertEqual(
            sorted((item["severity"], item["status"]) for item in round_two["items"]),
            [("P1", "open"), ("P2", "fixed")],
        )

    def test_invalid_relative_link_anchor_still_fails(self) -> None:
        for link in ("[outside.py:9](../outside.py#L9)", "[example.py](src/example.py#L0)"):
            with self.subTest(link=link):
                review = (
                    "- **Severity** P1 · **Confidence** 75 · **Classification** introduced\n"
                    f"  **File:Line** {link}\n  **Problem** First.\n\n"
                    "<verdict>NEEDS_WORK</verdict>\n"
                )
                status: dict = {}
                self.assertIsNone(parse(review, status=status))
                self.assertEqual(status["reason"], "invalid-anchor")

    def test_second_location_after_a_comma_keeps_the_first(self) -> None:
        review = (
            "- **Severity:** P2\n- **Confidence:** 100\n- **Classification:** introduced\n"
            "- **File:Line:** `scripts/a.sh:95`, `scripts/b.sh:108`\n"
            "- **Problem:** Both helpers split differently.\n\n"
            "<verdict>NEEDS_WORK</verdict>\n"
        )
        anchor = parse(review)["items"][0]["anchor"]
        self.assertEqual((anchor["path"], anchor["startLine"]), ("scripts/a.sh", 95))


if __name__ == "__main__":
    unittest.main()
