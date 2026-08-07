"""Parser + CLI tests for global acceptance criteria (fn-137.1)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.co",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.co",
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


class TestCriteriaParse(unittest.TestCase):
    def test_valid_body_skips_non_bullets_and_allows_gaps(self) -> None:
        text = (
            "# Global criteria\n"
            "\n"
            "Standing project-wide rules.\n"
            "\n"
            "- **G1:** Every route change regenerates the contract.\n"
            "- **G3:** No new dependency without a health check.\n"
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(errors, [])
        self.assertEqual([e["id"] for e in entries], ["G1", "G3"])
        self.assertEqual(
            entries[0]["text"],
            "Every route change regenerates the contract.",
        )
        self.assertEqual(
            entries[1]["text"],
            "No new dependency without a health check.",
        )

    def test_duplicate_id_keeps_first(self) -> None:
        text = (
            "- **G1:** first occurrence.\n"
            "- **G1:** second occurrence.\n"
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(len(errors), 1)
        self.assertIn("G1", errors[0])
        self.assertIn("duplicate", errors[0])
        self.assertEqual(entries, [{"id": "G1", "text": "first occurrence."}])

    def test_empty_prose_rejected(self) -> None:
        text = "- **G2:**\n- **G2:**   \n"
        entries, errors = flowctl._criteria_parse(text)
        self.assertTrue(any("empty" in e and "G2" in e for e in errors))
        self.assertEqual(entries, [])

    def test_at_limit_parses_ok(self) -> None:
        text = "".join(
            f"- **G{i}:** criterion {i}.\n"
            for i in range(1, flowctl._REVIEW_CRITERIA_MAX_ENTRIES + 1)
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), flowctl._REVIEW_CRITERIA_MAX_ENTRIES)

    def test_over_limit_rejected(self) -> None:
        text = "".join(
            f"- **G{i}:** criterion {i}.\n"
            for i in range(1, flowctl._REVIEW_CRITERIA_MAX_ENTRIES + 2)
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(len(errors), 1)
        self.assertIn("too many criteria", errors[0])
        self.assertIn(str(flowctl._REVIEW_CRITERIA_MAX_ENTRIES), errors[0])

    def test_non_matching_bullets_ignored(self) -> None:
        text = (
            "- plain bullet\n"
            "- **R1:** rid style\n"
            "- **G1:** real criterion.\n"
        )
        entries, errors = flowctl._criteria_parse(text)
        self.assertEqual(errors, [])
        self.assertEqual(entries, [{"id": "G1", "text": "real criterion."}])


class TestCriteriaCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        (self.root / ".flow").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "flowctl.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_absent_file_empty_json(self) -> None:
        proc = self._run("criteria", "list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload["criteria"], [])
        self.assertEqual(payload["count"], 0)

    def test_valid_file_round_trips(self) -> None:
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** Every route change regenerates the contract.\n"
            "- **G3:** No new dependency without a health check.\n",
            encoding="utf-8",
        )
        proc = self._run("criteria", "list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            payload["criteria"],
            [
                {
                    "id": "G1",
                    "text": "Every route change regenerates the contract.",
                },
                {
                    "id": "G3",
                    "text": "No new dependency without a health check.",
                },
            ],
        )

    def test_invalid_file_nonzero_exit(self) -> None:
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** first.\n- **G1:** second.\n",
            encoding="utf-8",
        )
        proc = self._run("criteria", "list", "--json")
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stdout + proc.stderr
        self.assertIn("duplicate", combined)
        self.assertIn("G1", combined)

    def test_over_limit_file_nonzero_exit(self) -> None:
        limit = flowctl._REVIEW_CRITERIA_MAX_ENTRIES
        (self.root / ".flow" / "criteria.md").write_text(
            "".join(
                f"- **G{i}:** criterion {i}.\n" for i in range(1, limit + 2)
            ),
            encoding="utf-8",
        )
        proc = self._run("criteria", "list", "--json")
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stdout + proc.stderr
        self.assertIn("too many criteria", combined)
        self.assertIn(str(limit), combined)

    def test_at_limit_file_ok(self) -> None:
        limit = flowctl._REVIEW_CRITERIA_MAX_ENTRIES
        (self.root / ".flow" / "criteria.md").write_text(
            "".join(
                f"- **G{i}:** criterion {i}.\n" for i in range(1, limit + 1)
            ),
            encoding="utf-8",
        )
        proc = self._run("criteria", "list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["count"], limit)


class TestCriteriaHeadingConstant(unittest.TestCase):
    def test_heading_value_pinned(self) -> None:
        self.assertEqual(
            flowctl.GLOBAL_CRITERIA_HEADING,
            "## Global acceptance criteria",
        )

    def test_completion_review_prompt_has_no_criteria_marker_when_absent(self) -> None:
        """Assembled completion-review prompt must not contain the criteria
        heading when .flow/criteria.md is absent (R1). Greps the shared
        constant so fn-137.2's injection is provably gated on file existence."""
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "criteria.md"
            with mock.patch.object(flowctl, "get_criteria_path", lambda: absent):
                prompt = self._build_prompt()
        self.assertNotIn(flowctl.GLOBAL_CRITERIA_HEADING, prompt)

    @staticmethod
    def _build_prompt() -> str:
        return flowctl.build_completion_review_prompt(
            spec_path=".flow/specs/fn-1.md",
            task_spec_paths=[".flow/tasks/fn-1.1.md"],
            review_scope="1\t0\tx",
            diff_range="aaa..bbb",
        )


class TestGlobalCriteriaBlock(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "criteria.md"
        self._orig = flowctl.get_criteria_path
        flowctl.get_criteria_path = lambda: self.path  # type: ignore[assignment]

    def tearDown(self) -> None:
        flowctl.get_criteria_path = self._orig  # type: ignore[assignment]
        self._tmp.cleanup()

    def test_absent_path_returns_empty(self) -> None:
        self.assertEqual(flowctl.build_global_criteria_block(), "")

    def test_invalid_file_raises_fail_closed(self) -> None:
        """Existing-but-invalid criteria.md must raise, not silently
        disable the configured standing criteria (fail closed)."""
        self.path.write_text(
            "- **G1:** first.\n- **G1:** second.\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as ctx:
            flowctl.build_global_criteria_block()
        self.assertIn("invalid .flow/criteria.md", str(ctx.exception))
        self.assertIn("duplicate", str(ctx.exception))

    def test_valid_empty_template_returns_empty(self) -> None:
        """Present file that parses to zero active criteria is a no-op."""
        self.path.write_text(
            "# Global acceptance criteria\n\n<!-- comment only -->\n",
            encoding="utf-8",
        )
        self.assertEqual(flowctl.build_global_criteria_block(), "")

    def test_invalid_file_fails_prompt_build(self) -> None:
        """Backend completion-review prompt build must error on an invalid
        criteria file, never assemble a prompt without the standing rules."""
        self.path.write_text(
            "- **G1:** first.\n- **G1:** second.\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            flowctl.build_completion_review_prompt(
                spec_path=".flow/specs/fn-1.md",
                task_spec_paths=[".flow/tasks/fn-1.1.md"],
                review_scope="1\t0\tx",
                diff_range="aaa..bbb",
            )

    def test_valid_file_renders_block(self) -> None:
        self.path.write_text(
            "- **G1:** Every route change regenerates the contract.\n"
            "- **G2:** No new dependency without a health check.\n",
            encoding="utf-8",
        )
        block = flowctl.build_global_criteria_block()
        self.assertTrue(block.startswith(flowctl.GLOBAL_CRITERIA_HEADING))
        self.assertIn(
            "- **G1:** Every route change regenerates the contract.",
            block,
        )
        self.assertIn(
            "- **G2:** No new dependency without a health check.",
            block,
        )
        self.assertIn("## Global criteria", block)
        self.assertIn(
            "G<N>: met|violated|n/a - <one-line note>",
            block,
        )
        self.assertTrue(block.endswith("\n\n"))


class TestGlobalCriteriaPromptInjection(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "criteria.md"
        self._orig = flowctl.get_criteria_path
        flowctl.get_criteria_path = lambda: self.path  # type: ignore[assignment]

    def tearDown(self) -> None:
        flowctl.get_criteria_path = self._orig  # type: ignore[assignment]
        self._tmp.cleanup()

    def test_valid_criteria_injected_before_output_format(self) -> None:
        self.path.write_text(
            "- **G1:** Every route change regenerates the contract.\n"
            "- **G2:** No new dependency without a health check.\n",
            encoding="utf-8",
        )
        prompt = flowctl.build_completion_review_prompt(
            spec_path=".flow/specs/fn-1.md",
            task_spec_paths=[".flow/tasks/fn-1.1.md"],
            review_scope="1\t0\tx",
            diff_range="aaa..bbb",
        )
        self.assertIn(flowctl.GLOBAL_CRITERIA_HEADING, prompt)
        self.assertIn(
            "- **G1:** Every route change regenerates the contract.",
            prompt,
        )
        self.assertIn(
            "- **G2:** No new dependency without a health check.",
            prompt,
        )
        self.assertIn("<one-line note>\n\n## Output Format", prompt)
        self.assertIn("<verdict>SHIP</verdict>", prompt)
        self.assertIn("<verdict>NEEDS_WORK</verdict>", prompt)


_SAMPLE_COMPLETION_REVIEW = """## Requirements Extracted

1. Route changes regenerate the contract
2. Health checks for new deps

## Coverage Verification

1. Route changes - COVERED - evidence: contract.py:10
2. Health checks - GAP - not found

## Global criteria

G1: met - contract regenerated
G2: violated - dep added without health check
G3: n/a - no UI in this change

## Gaps Found

Severity: P1
Confidence: 75
Classification: introduced
File:Line: deps.py:1
R-IDs: [R2]
Problem: missing health check
Suggestion: add one

<verdict>NEEDS_WORK</verdict>
"""


class TestParseReviewCriteria(unittest.TestCase):
    def test_happy_path(self) -> None:
        entries = flowctl.parse_review_criteria(_SAMPLE_COMPLETION_REVIEW)
        self.assertEqual(
            entries,
            [
                {"id": "G1", "status": "met", "note": "contract regenerated"},
                {
                    "id": "G2",
                    "status": "violated",
                    "note": "dep added without health check",
                },
                {"id": "G3", "status": "n/a", "note": "no UI in this change"},
            ],
        )

    def test_line_without_note(self) -> None:
        text = "## Global criteria\n\nG1: met\n"
        entries = flowctl.parse_review_criteria(text)
        self.assertEqual(entries, [{"id": "G1", "status": "met"}])
        self.assertNotIn("note", entries[0])

    def test_bulleted_lines(self) -> None:
        text = "## Global criteria\n\n- G1: met - ok\n"
        self.assertEqual(
            flowctl.parse_review_criteria(text),
            [{"id": "G1", "status": "met", "note": "ok"}],
        )

    def test_oversized_note_returns_none(self) -> None:
        text = "## Global criteria\n\nG1: met - " + ("x" * 401) + "\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_max_length_note_kept_verbatim(self) -> None:
        note = "x" * 400
        text = f"## Global criteria\n\nG1: met - {note}\n"
        self.assertEqual(
            flowctl.parse_review_criteria(text),
            [{"id": "G1", "status": "met", "note": note}],
        )

    def test_needs_human_terminal_ends_section(self) -> None:
        # fn-159.3 r1: the terminator knows the FULL verdict grammar. A
        # completion reviewer that escalates must still project its G-IDs.
        text = (
            "## Global criteria\n"
            "\n"
            "G1: met - ok\n"
            "\n"
            "<verdict>NEEDS_HUMAN</verdict>\n"
        )
        self.assertEqual(
            flowctl.parse_review_criteria(text),
            [{"id": "G1", "status": "met", "note": "ok"}],
        )

    def test_major_rethink_terminal_ends_section(self) -> None:
        text = (
            "## Global criteria\n"
            "\n"
            "G1: violated - wrong approach\n"
            "\n"
            "<verdict>MAJOR_RETHINK</verdict>\n"
        )
        self.assertEqual(
            flowctl.parse_review_criteria(text),
            [{"id": "G1", "status": "violated", "note": "wrong approach"}],
        )

    def test_no_section_returns_none(self) -> None:
        text = "## Requirements Extracted\n\n1. something\n\n<verdict>SHIP</verdict>\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_duplicate_id_returns_none(self) -> None:
        text = "## Global criteria\n\nG1: met - a\nG1: violated - b\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_prose_only_section_returns_none(self) -> None:
        text = "## Global criteria\n\nNo criteria applicable.\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_malformed_gid_record_returns_none(self) -> None:
        # A G-ID-looking line that fails the record grammar poisons the whole
        # projection - even when every other configured id parsed validly.
        text = (
            "## Global criteria\n"
            "\n"
            "G1: met - ok\n"
            "G2: violated - dep added\n"
            "G1: pass - contradictory rating\n"
        )
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_bolded_malformed_gid_record_returns_none(self) -> None:
        text = "## Global criteria\n\n**G1**: met - ok\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_plain_prose_line_amid_valid_records_degrades(self) -> None:
        # Strict-section contract (PR #275 round 12): ANY non-blank non-record
        # line inside the section is ambiguity -> whole projection absent.
        text = (
            "## Global criteria\n"
            "\n"
            "G1: met - ok\n"
            "All criteria were checked against the diff.\n"
            "G2: n/a - no UI\n"
        )
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_heading_then_immediate_next_heading(self) -> None:
        text = "## Global criteria\n## Gaps Found\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_section_ends_at_next_heading(self) -> None:
        text = (
            "## Global criteria\n"
            "\n"
            "G1: met - ok\n"
            "\n"
            "## Gaps Found\n"
            "\n"
            "G2: violated - should not parse\n"
        )
        self.assertEqual(
            flowctl.parse_review_criteria(text),
            [{"id": "G1", "status": "met", "note": "ok"}],
        )

    def test_last_heading_wins(self) -> None:
        text = (
            "## Global criteria\n"
            "\n"
            "G1: met - first\n"
            "\n"
            "## Other\n"
            "\n"
            "## Global criteria\n"
            "\n"
            "G1: violated - last\n"
            "G2: n/a - ignored elsewhere\n"
        )
        self.assertEqual(
            flowctl.parse_review_criteria(text),
            [
                {"id": "G1", "status": "violated", "note": "last"},
                {"id": "G2", "status": "n/a", "note": "ignored elsewhere"},
            ],
        )

    def test_non_str_and_empty(self) -> None:
        self.assertIsNone(flowctl.parse_review_criteria(None))  # type: ignore[arg-type]
        self.assertIsNone(flowctl.parse_review_criteria(""))
        self.assertIsNone(flowctl.parse_review_criteria(123))  # type: ignore[arg-type]


class TestValidateReviewReceiptCriteria(unittest.TestCase):
    def test_absent_criteria_ok(self) -> None:
        self.assertTrue(
            flowctl.validate_review_receipt_criteria(
                {"type": "completion_review", "id": "fn-1"}
            )
        )

    def test_valid_completion_list(self) -> None:
        receipt = {
            "type": "completion_review",
            "criteria": [
                {"id": "G1", "status": "met", "note": "ok"},
                {"id": "G2", "status": "n/a"},
            ],
        }
        self.assertTrue(flowctl.validate_review_receipt_criteria(receipt))

    def test_wrong_type_rejected(self) -> None:
        receipt = {
            "type": "impl_review",
            "criteria": [{"id": "G1", "status": "met"}],
        }
        self.assertFalse(flowctl.validate_review_receipt_criteria(receipt))

    def test_bad_status_id_duplicate_extra_empty(self) -> None:
        base = {"type": "completion_review"}
        self.assertFalse(
            flowctl.validate_review_receipt_criteria(
                {**base, "criteria": [{"id": "G1", "status": "pass"}]}
            )
        )
        self.assertFalse(
            flowctl.validate_review_receipt_criteria(
                {**base, "criteria": [{"id": "X1", "status": "met"}]}
            )
        )
        self.assertFalse(
            flowctl.validate_review_receipt_criteria(
                {
                    **base,
                    "criteria": [
                        {"id": "G1", "status": "met"},
                        {"id": "G1", "status": "violated"},
                    ],
                }
            )
        )
        self.assertFalse(
            flowctl.validate_review_receipt_criteria(
                {
                    **base,
                    "criteria": [
                        {"id": "G1", "status": "met", "extra": True},
                    ],
                }
            )
        )
        self.assertFalse(
            flowctl.validate_review_receipt_criteria({**base, "criteria": []})
        )


class TestCriteriaReceiptCli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        (self.root / ".flow").mkdir()
        (self.root / "tracked.txt").write_text("x\n", encoding="utf-8")
        _git(self.root, "add", "tracked.txt")
        _git(self.root, "commit", "-qm", "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "flowctl.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_prompt_block_absent_empty(self) -> None:
        proc = self._run("criteria", "prompt-block")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_prompt_block_valid_file(self) -> None:
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** Every route change regenerates the contract.\n",
            encoding="utf-8",
        )
        proc = self._run("criteria", "prompt-block")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(
            proc.stdout.startswith("## Global acceptance criteria"),
            proc.stdout[:80],
        )

    def test_prompt_block_invalid_file_fails_closed(self) -> None:
        """Existing-but-invalid criteria.md: nonzero exit, errors on stderr,
        stdout empty (so a careless append injects nothing)."""
        (self.root / ".flow" / "criteria.md").write_text(
            "- **G1:** first.\n- **G1:** second.\n",
            encoding="utf-8",
        )
        proc = self._run("criteria", "prompt-block")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertIn("invalid .flow/criteria.md", proc.stderr)

    def _write_criteria(self, *ids: str) -> None:
        lines = "".join(f"- **{cid}:** Criterion {cid} prose.\n" for cid in ids)
        (self.root / ".flow" / "criteria.md").write_text(lines, encoding="utf-8")

    def _attach(self, review_text: str) -> tuple[dict, Path]:
        review = self.root / "review.md"
        review.write_text(review_text, encoding="utf-8")
        in_path = self.root / "in.json"
        out_path = self.root / "out.json"
        in_path.write_text(
            json.dumps(
                {
                    "type": "completion_review",
                    "id": "fn-9",
                    "mode": "host",
                    "verdict": "SHIP",
                }
            ),
            encoding="utf-8",
        )
        proc = self._run(
            "review-findings",
            "attach",
            "--input",
            str(in_path),
            "--receipt",
            str(out_path),
            "--review-file",
            str(review),
            "--head",
            "HEAD",
            "--json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        return payload, out_path

    def test_review_findings_attach_with_criteria(self) -> None:
        self._write_criteria("G1", "G2", "G3")
        review = self.root / "review.md"
        review.write_text(_SAMPLE_COMPLETION_REVIEW, encoding="utf-8")
        in_path = self.root / "in.json"
        out_path = self.root / "out.json"
        in_path.write_text(
            json.dumps(
                {
                    "type": "completion_review",
                    "id": "fn-9",
                    "mode": "host",
                    "verdict": "SHIP",
                }
            ),
            encoding="utf-8",
        )
        proc = self._run(
            "review-findings",
            "attach",
            "--input",
            str(in_path),
            "--receipt",
            str(out_path),
            "--review-file",
            str(review),
            "--head",
            "HEAD",
            "--json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        self.assertTrue(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(
            receipt["criteria"],
            [
                {"id": "G1", "status": "met", "note": "contract regenerated"},
                {
                    "id": "G2",
                    "status": "violated",
                    "note": "dep added without health check",
                },
                {"id": "G3", "status": "n/a", "note": "no UI in this change"},
            ],
        )

    def test_review_findings_attach_without_criteria_section(self) -> None:
        review = self.root / "review.md"
        review.write_text(
            "## Requirements Extracted\n\n1. something\n\n"
            "<verdict>SHIP</verdict>\n",
            encoding="utf-8",
        )
        in_path = self.root / "in.json"
        out_path = self.root / "out.json"
        in_path.write_text(
            json.dumps(
                {
                    "type": "completion_review",
                    "id": "fn-9",
                    "mode": "host",
                    "verdict": "SHIP",
                }
            ),
            encoding="utf-8",
        )
        proc = self._run(
            "review-findings",
            "attach",
            "--input",
            str(in_path),
            "--receipt",
            str(out_path),
            "--review-file",
            str(review),
            "--head",
            "HEAD",
            "--json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("success"))
        self.assertFalse(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("criteria", receipt)

    def test_attach_no_criteria_file_suppresses_criteria(self) -> None:
        # Reviewer emits a Global criteria section but the repo has no
        # .flow/criteria.md - fabricated compliance must not attach.
        payload, out_path = self._attach(_SAMPLE_COMPLETION_REVIEW)
        self.assertFalse(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("criteria", receipt)

    def test_attach_omitted_criterion_suppresses_criteria(self) -> None:
        # Configured G1-G4 but the reviewer only reported G1-G3 - a dropped
        # standing criterion degrades to absent.
        self._write_criteria("G1", "G2", "G3", "G4")
        payload, out_path = self._attach(_SAMPLE_COMPLETION_REVIEW)
        self.assertFalse(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("criteria", receipt)

    def test_attach_invented_id_suppresses_criteria(self) -> None:
        # Reviewer reports G1-G3 but only G1-G2 are configured - invented ids
        # degrade to absent.
        self._write_criteria("G1", "G2")
        payload, out_path = self._attach(_SAMPLE_COMPLETION_REVIEW)
        self.assertFalse(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("criteria", receipt)

    def test_attach_oversized_note_suppresses_criteria(self) -> None:
        # A >400-char note is invalid reviewer output - the projection
        # degrades to absent rather than truncating the evidence.
        self._write_criteria("G1", "G2", "G3")
        review_text = _SAMPLE_COMPLETION_REVIEW.replace(
            "G2: violated - dep added without health check",
            "G2: violated - " + ("x" * 401),
        )
        payload, out_path = self._attach(review_text)
        self.assertFalse(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("criteria", receipt)

    def test_attach_exact_match_attaches(self) -> None:
        self._write_criteria("G1", "G2", "G3")
        payload, out_path = self._attach(_SAMPLE_COMPLETION_REVIEW)
        self.assertTrue(payload.get("criteria_attached"))
        receipt = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["id"] for item in receipt["criteria"]], ["G1", "G2", "G3"]
        )


class TestCriteriaTemplate(unittest.TestCase):
    """Bundled setup scaffold template parses clean (fn-137.3)."""

    _TEMPLATE = (
        REPO_ROOT / "plugins" / "flow-next" / "templates" / "criteria.md"
    )

    def test_template_parses_clean_with_zero_active_criteria(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            _git(root, "init", "-q")
            flow_dir = root / ".flow"
            flow_dir.mkdir()
            (flow_dir / "criteria.md").write_text(
                self._TEMPLATE.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "flowctl.py"),
                    "criteria",
                    "list",
                    "--json",
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload.get("success"))
            self.assertEqual(payload["count"], 0)
            self.assertEqual(payload["criteria"], [])
        finally:
            tmp.cleanup()

    def test_commented_examples_match_grammar_when_uncommented(self) -> None:
        text = self._TEMPLATE.read_text(encoding="utf-8")
        commented = [
            line
            for line in text.splitlines()
            if line.startswith("<!-- - **G")
        ]
        self.assertEqual(len(commented), 3)
        stripped_lines = []
        for line in commented:
            self.assertTrue(line.endswith(" -->"))
            stripped_lines.append(line[len("<!-- ") : -len(" -->")])
        entries, errors = flowctl._criteria_parse("\n".join(stripped_lines))
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 3)
        self.assertEqual([e["id"] for e in entries], ["G1", "G2", "G3"])

    def test_no_active_criterion_lines_in_template(self) -> None:
        text = self._TEMPLATE.read_text(encoding="utf-8")
        for line in text.splitlines():
            self.assertIsNone(
                flowctl._CRITERIA_LINE_RE.match(line),
                f"active criterion line in template: {line!r}",
            )


if __name__ == "__main__":
    unittest.main()


class TestCriteriaLooksLikeSource(unittest.TestCase):
    """Malformed G-ID-looking bullets are validation errors (fail closed)."""

    def test_bold_colon_outside_typo_errors(self):
        entries, errors = flowctl._criteria_parse("- **G1**: must run tests\n")
        self.assertEqual(entries, [])
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))

    def test_unbolded_gid_bullet_errors(self):
        _, errors = flowctl._criteria_parse("- G2: no new deps\n")
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))

    def test_prose_and_headings_still_ignored(self):
        entries, errors = flowctl._criteria_parse(
            "# Criteria\n\nSome prose about G1 and rules.\n- **G1:** valid one\n"
        )
        self.assertEqual(errors, [])
        self.assertEqual([e["id"] for e in entries], ["G1"])

    def test_template_grammar_fence_line_not_flagged(self):
        _, errors = flowctl._criteria_parse("- **G<N>:** <criterion prose>\n")
        self.assertEqual(errors, [])


class TestCriteriaLooksLikeRound9(unittest.TestCase):
    """Colon-less bold G-bullets are malformed; unreadable file errors cleanly."""

    def test_bold_no_colon_errors(self):
        _, errors = flowctl._criteria_parse("- **G2** must lint\n")
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))

    def test_unbolded_no_colon_stays_prose(self):
        entries, errors = flowctl._criteria_parse("- G20 railway station\n- **G1:** valid\n")
        self.assertEqual(errors, [])
        self.assertEqual([e["id"] for e in entries], ["G1"])

    def test_valid_lines_never_probed(self):
        entries, errors = flowctl._criteria_parse("- **G1:** a\n- **G2:** b\n")
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 2)

    def test_unreadable_file_clean_error(self):
        import subprocess, tempfile, os
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)
            flow = os.path.join(td, ".flow")
            os.makedirs(flow)
            p = os.path.join(flow, "criteria.md")
            with open(p, "wb") as fh:
                fh.write(b"- **G1:** \xff\xfe invalid utf8\n")
            r = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "flowctl.py"), "criteria", "list", "--json"],
                capture_output=True, text=True, cwd=td,
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn("unreadable", r.stdout + r.stderr)


class TestCriteriaAltBulletMarkers(unittest.TestCase):
    """Alternate Markdown bullet markers with G-IDs fail closed as malformed."""

    def test_star_bullet_errors(self):
        _, errors = flowctl._criteria_parse("* **G1:** must lint\n")
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))

    def test_plus_bullet_errors(self):
        _, errors = flowctl._criteria_parse("+ **G2** no new deps\n")
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))

    def test_star_prose_without_gid_ignored(self):
        entries, errors = flowctl._criteria_parse("* just a note\n- **G1:** valid\n")
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 1)


class TestReceiptPlusBullet(unittest.TestCase):
    """Plus-bulleted records in the reviewer section are seen by the parser."""

    def test_plus_bulleted_contradictory_record_degrades(self):
        text = (
            "## Global criteria\n"
            "G1: met - fine\n"
            "+ G1: violated - actually failed\n"
        )
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_plus_bulleted_valid_record_parses(self):
        text = "## Global criteria\n+ G1: met - fine\n"
        out = flowctl.parse_review_criteria(text)
        self.assertEqual([c["id"] for c in out], ["G1"])


class TestReceiptStrictSection(unittest.TestCase):
    """Round 12: any non-record line in the section degrades - generic, no prefix enumeration."""

    def test_ordered_list_contradiction_degrades(self):
        text = "## Global criteria\nG1: met - ok\n1. G1: violated - actually failed\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_blockquote_contradiction_degrades(self):
        text = "## Global criteria\nG1: met - ok\n> G1: violated - actually failed\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_blank_lines_still_fine(self):
        text = "## Global criteria\n\nG1: met - ok\n\nG2: n/a - x\n"
        out = flowctl.parse_review_criteria(text)
        self.assertEqual([c["id"] for c in out], ["G1", "G2"])


class TestReceiptVerdictTerminator(unittest.TestCase):
    """Round 13: the required verdict tag ends the section instead of poisoning it."""

    def test_section_final_with_verdict_tag_parses(self):
        text = "## Global criteria\nG1: met - ok\nG2: n/a - x\n<verdict>SHIP</verdict>\n"
        out = flowctl.parse_review_criteria(text)
        self.assertEqual([c["id"] for c in out], ["G1", "G2"])

    def test_needs_work_tag_also_terminates(self):
        text = "## Global criteria\nG1: violated - bad\n<verdict>NEEDS_WORK</verdict>\n"
        out = flowctl.parse_review_criteria(text)
        self.assertEqual(out[0]["status"], "violated")

    def test_prose_before_verdict_still_degrades(self):
        text = "## Global criteria\nG1: met - ok\nsome prose\n<verdict>SHIP</verdict>\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))


class TestCriteriaBrokenSymlink(unittest.TestCase):
    """Round 14: a dangling criteria.md symlink fails closed, not silently absent."""

    def test_dangling_symlink_raises_in_block_builder(self):
        import tempfile, os as _os
        with tempfile.TemporaryDirectory() as td:
            import subprocess
            subprocess.run(["git", "init", "-q", td], check=True)
            flow = _os.path.join(td, ".flow")
            _os.makedirs(flow)
            _os.symlink(_os.path.join(td, "nonexistent-target.md"), _os.path.join(flow, "criteria.md"))
            r = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "flowctl.py"), "criteria", "list", "--json"],
                capture_output=True, text=True, cwd=td,
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("broken symlink", r.stdout + r.stderr)


class TestGidNumberGrammar(unittest.TestCase):
    """Round 15: G-IDs start at 1, no leading zeros - consistently on all three surfaces."""

    def test_source_g0_and_zero_padded_fail_closed(self):
        _, errors = flowctl._criteria_parse("- **G0:** zero\n")
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))
        _, errors = flowctl._criteria_parse("- **G01:** padded\n")
        self.assertTrue(any("malformed criterion bullet" in e for e in errors))

    def test_receipt_g0_line_degrades(self):
        text = "## Global criteria\nG0: met - zero\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_receipt_zero_padded_degrades(self):
        text = "## Global criteria\nG01: met - padded\n"
        self.assertIsNone(flowctl.parse_review_criteria(text))

    def test_validator_rejects_zero_padded_id(self):
        receipt = {"type": "completion_review", "criteria": [{"id": "G01", "status": "met"}]}
        self.assertFalse(flowctl.validate_review_receipt_criteria(receipt))

    def test_g10_still_valid_everywhere(self):
        entries, errors = flowctl._criteria_parse("- **G10:** tenth\n")
        self.assertEqual(errors, [])
        self.assertEqual(entries[0]["id"], "G10")
        out = flowctl.parse_review_criteria("## Global criteria\nG10: met - ok\n")
        self.assertEqual(out[0]["id"], "G10")


class TestAsciiDigitGids(unittest.TestCase):
    """Round 16: G-ID digits are ASCII-only on all surfaces."""

    def test_unicode_digit_source_fails_closed(self):
        _, errors = flowctl._criteria_parse("- **G1١:** arabic-one suffix\n")
        self.assertTrue(errors)

    def test_unicode_digit_receipt_degrades(self):
        self.assertIsNone(flowctl.parse_review_criteria("## Global criteria\nG1١: met - x\n"))

    def test_unicode_digit_validator_rejects(self):
        r = {"type": "completion_review", "criteria": [{"id": "G1０", "status": "met"}]}
        self.assertFalse(flowctl.validate_review_receipt_criteria(r))
