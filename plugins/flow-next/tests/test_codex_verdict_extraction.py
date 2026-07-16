"""Codex verdict-extraction regression tests (fn-90 R3).

Root-cause bug (2026-07-09 live repro): ``parse_codex_verdict`` first-matched a
``<verdict>...</verdict>`` regex over the ENTIRE ``codex exec --json`` stream,
including ``command_execution`` / ``aggregated_output`` events that echo repo
files the reviewer grepped. A reviewer that grepped ``smoke_test.sh`` (which
asserts ``<verdict>SHIP</verdict>``) poisoned the stream so flowctl reported
SHIP while the reviewer's real final message said NEEDS_WORK.

Fix: extract only the ``agent_message`` text from the JSON stream (parity with
cursor's ``_parse_cursor_result``), then take the LAST verdict match.

These are the two pollution shapes the spec calls out:
  1. tool-output literal — a verdict token in a ``command_execution`` /
     ``aggregated_output`` event that is NOT the reviewer's answer.
  2. quoted-grammar literal — the reviewer quotes the verdict grammar in its
     own final message before emitting the real terminal verdict tag.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from typing import Any


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location(
        "flowctl_codex_verdict_under_test", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


def _stream(*events: dict) -> str:
    """Serialize codex ``--json`` events as JSON-lines stdout."""
    return "\n".join(json.dumps(e) for e in events) + "\n"


def _agent_message(text: str) -> dict:
    return {"type": "item.completed", "item": {"type": "agent_message", "text": text}}


def _command_execution(aggregated_output: str) -> dict:
    return {
        "type": "item.completed",
        "item": {
            "type": "command_execution",
            "status": "completed",
            "aggregated_output": aggregated_output,
        },
    }


class TestCodexVerdictExtraction(unittest.TestCase):
    # --- shape 1: tool-output literal poisons the stream ---

    def test_tool_output_verdict_literal_does_not_win(self):
        """A grep echoing `<verdict>SHIP</verdict>` from a repo file must not
        override the reviewer's real NEEDS_WORK verdict."""
        output = _stream(
            {"type": "thread.started", "thread_id": "t1"},
            {"type": "turn.started"},
            # Reviewer grepped smoke_test.sh — its assertion literal lands in
            # aggregated_output BEFORE the reviewer's own message.
            _command_execution(
                "smoke_test.sh: assert '<verdict>SHIP</verdict>' in output\n"
                "smoke_test.sh: assert '<verdict>NEEDS_WORK</verdict>' in output"
            ),
            _agent_message(
                "I found a Critical issue in the plan.\n<verdict>NEEDS_WORK</verdict>"
            ),
            {"type": "turn.completed", "usage": {}},
        )
        self.assertEqual(flowctl.parse_codex_verdict(output), "NEEDS_WORK")

    def test_tool_output_literal_after_agent_message_still_ignored(self):
        """Even if a tool event with a SHIP literal appears AFTER the agent
        message in the stream, only agent_message text is parsed."""
        output = _stream(
            _agent_message("Blocking finding.\n<verdict>NEEDS_WORK</verdict>"),
            _command_execution("cat smoke_test.sh -> <verdict>SHIP</verdict>"),
        )
        self.assertEqual(flowctl.parse_codex_verdict(output), "NEEDS_WORK")

    # --- shape 2: quoted grammar in the final message ---

    def test_quoted_grammar_in_final_message_last_match_wins(self):
        """The reviewer quotes the verdict grammar (SHIP) while explaining the
        contract, then emits the real NEEDS_WORK verdict last. Last-match wins."""
        output = _stream(
            _agent_message(
                "Per the contract I emit either `<verdict>SHIP</verdict>` or "
                "`<verdict>NEEDS_WORK</verdict>`.\n\n"
                "There is a Major finding, so:\n<verdict>NEEDS_WORK</verdict>"
            ),
        )
        self.assertEqual(flowctl.parse_codex_verdict(output), "NEEDS_WORK")

    def test_both_pollution_shapes_combined(self):
        """Tool-output SHIP literal + quoted-grammar SHIP in the final message,
        real verdict NEEDS_WORK last — the fixture the spec pins."""
        output = _stream(
            {"type": "thread.started", "thread_id": "t-poison"},
            _command_execution("grep smoke_test.sh: <verdict>SHIP</verdict>"),
            _agent_message(
                "The grammar is `<verdict>SHIP</verdict>` or "
                "`<verdict>NEEDS_WORK</verdict>`.\n"
                "Findings remain unaddressed.\n<verdict>NEEDS_WORK</verdict>"
            ),
        )
        self.assertEqual(flowctl.parse_codex_verdict(output), "NEEDS_WORK")

    # --- honest SHIP still parses ---

    def test_clean_ship_still_parses(self):
        output = _stream(
            _agent_message("All findings addressed.\n<verdict>SHIP</verdict>"),
        )
        self.assertEqual(flowctl.parse_codex_verdict(output), "SHIP")

    def test_major_rethink_parses(self):
        output = _stream(
            _agent_message("Architecture is wrong.\n<verdict>MAJOR_RETHINK</verdict>"),
        )
        self.assertEqual(flowctl.parse_codex_verdict(output), "MAJOR_RETHINK")

    # --- plain-text (copilot / non-stream) fallback ---

    def test_plaintext_output_falls_through(self):
        """Copilot `--output-format text` emits plain text (no JSON stream).
        Verdict parse must still work on the raw text, last-match."""
        text = (
            "The contract accepts `<verdict>SHIP</verdict>` or NEEDS_WORK.\n"
            "I found a blocker.\n<verdict>NEEDS_WORK</verdict>"
        )
        self.assertEqual(flowctl.parse_codex_verdict(text), "NEEDS_WORK")

    def test_plaintext_single_verdict(self):
        self.assertEqual(
            flowctl.parse_codex_verdict("Looks good.\n<verdict>SHIP</verdict>"),
            "SHIP",
        )

    def test_no_verdict_returns_none(self):
        output = _stream(_agent_message("I could not determine a verdict."))
        self.assertIsNone(flowctl.parse_codex_verdict(output))

    def test_empty_output_returns_none(self):
        self.assertIsNone(flowctl.parse_codex_verdict(""))

    # --- extract_codex_final_message unit behavior ---

    def test_extract_isolates_agent_messages_only(self):
        output = _stream(
            _command_execution("noise <verdict>SHIP</verdict>"),
            _agent_message("real answer"),
        )
        self.assertEqual(flowctl.extract_codex_final_message(output), "real answer")

    def test_extract_concatenates_multiple_agent_messages_in_order(self):
        output = _stream(
            _agent_message("first"),
            _command_execution("tool noise"),
            _agent_message("second"),
        )
        self.assertEqual(
            flowctl.extract_codex_final_message(output), "first\nsecond"
        )

    def test_extract_plaintext_returns_unchanged(self):
        text = "not a json stream <verdict>SHIP</verdict>"
        self.assertEqual(flowctl.extract_codex_final_message(text), text)

    def test_extract_json_without_agent_message_returns_raw(self):
        """A JSON stream that errored (no agent_message) falls through to raw
        so we never silently blank a caller."""
        output = _stream(
            {"type": "thread.started", "thread_id": "t1"},
            {"type": "turn.failed", "error": {"message": "boom"}},
        )
        self.assertEqual(flowctl.extract_codex_final_message(output), output)


class TestCodexReceiptReviewFieldExtraction(unittest.TestCase):
    """fn-90 review round 1: codex receipts must store the EXTRACTED final
    message in ``review``, never the raw stream.

    The convergence ratchet (``_read_prior_findings`` -> ``<prior_findings>``)
    consumes the receipt's ``review`` field and truncates it to its first 8000
    chars. Raw-stream storage would inject early tool-call JSON as "prior
    findings" and break the shrink-only contract on every codex re-review
    (cursor masked this in validation — its receipt review text was already
    clean). Guarded at the source level: every codex-mode receipt write must
    wrap ``output`` in ``extract_codex_final_message``.
    """

    def test_no_codex_receipt_stores_raw_stream(self):
        src_path = (
            Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"
        )
        lines = src_path.read_text(encoding="utf-8").split("\n")
        offenders = []
        for i, line in enumerate(lines):
            if '"review": output' not in line:
                continue
            if "extract_codex_final_message" in line:
                continue
            ctx = "\n".join(lines[max(0, i - 30):i])
            if '"mode": "codex"' in ctx:
                offenders.append(f"flowctl.py:{i + 1}")
        self.assertEqual(
            offenders,
            [],
            "codex receipt(s) store the raw stream in the review field; the "
            "ratchet would inject stream JSON as prior findings: "
            f"{offenders}",
        )

    def test_ratchet_prior_findings_from_extracted_stream_are_clean(self):
        # End-to-end shape: raw stream -> extraction (what receipts now store)
        # -> ratchet block. The tool echo must not reach <prior_findings>.
        raw = _stream(
            _command_execution("noise <verdict>SHIP</verdict> noise"),
            _agent_message(
                "- Severity: Major\n  Problem: X is wrong.\n\n"
                "<verdict>NEEDS_WORK</verdict>"
            ),
        )
        stored = flowctl.extract_codex_final_message(raw)
        block = flowctl.build_convergence_ratchet_block(stored)
        self.assertIn("Problem: X is wrong.", block)
        self.assertNotIn("aggregated_output", block)
        self.assertNotIn("command_execution", block)


if __name__ == "__main__":
    unittest.main()
