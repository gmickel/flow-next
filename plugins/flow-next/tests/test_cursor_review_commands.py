"""Handler + dispatch tests for the cursor review commands (fn-74.2).

Covers the five cursor review subcommands layered on the .1 foundation:

- R5  ``cursor impl-review`` writes a ``mode:"cursor"`` receipt (NO ``effort``
      key) and prints ``VERDICT=...``.
- R6  ``plan-review`` / ``completion-review`` / ``validate`` / ``deep-pass``
      dispatch through ``run_cursor_exec`` and write the same additive receipt
      shapes as codex/copilot (``mode:"cursor"``).
- R7  re-review resumes via ``--resume <session_id>`` **only** when the prior
      receipt's ``mode == "cursor"``; a cross-backend receipt starts fresh
      (session_id None ⇒ run_cursor_exec omits --resume).
- R14 impl/completion receipts carry copilot's rigor fields (suppressed counts,
      introduced-vs-pre_existing, unaddressed R-IDs) AND ``effort`` is absent.

These mock ``run_cursor_exec`` (so no cursor-agent spawn) but exercise the real
handlers against a real temp git repo + ``.flow`` tree. The live clean-tree
integration smoke test (R8) lives in ``test_cursor_clean_tree.py``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
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


EPIC_ID = "fn-1-cursor-demo"
TASK_ID = f"{EPIC_ID}.1"
MINTED_SID = "cccccccc-1111-2222-3333-444444444444"
PRIOR_SID = "dddddddd-5555-6666-7777-888888888888"

REVIEW_OUTPUT = (
    "Reviewed the diff.\n\n"
    "Suppressed findings: 3 at anchor 50, 7 at anchor 25.\n"
    "Classification counts: 2 introduced, 4 pre_existing.\n"
    "Unaddressed R-IDs: [R3, R5]\n\n"
    "<verdict>NEEDS_WORK</verdict>\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


@contextlib.contextmanager
def _flow_repo():
    """Real temp git repo + ``.flow`` tree, with a base..HEAD diff. chdir'd."""
    prev_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / "src").mkdir()
        (repo / "src" / "mod.py").write_text("def a(x):\n    return x\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")
        base = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

        flow = repo / ".flow"
        (flow / "specs").mkdir(parents=True)
        (flow / "tasks").mkdir(parents=True)
        (flow / "specs" / f"{EPIC_ID}.md").write_text(
            "# Demo spec\n\n## Acceptance Criteria\n\n- **R1:** do a thing\n",
            encoding="utf-8",
        )
        (flow / "tasks" / f"{TASK_ID}.md").write_text(
            "---\nsatisfies: [R1]\n---\n\n## Description\n\nImplement a().\n",
            encoding="utf-8",
        )
        # Second commit so base..HEAD has a real diff.
        (repo / "src" / "mod.py").write_text(
            "def a(x):\n    return x + 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "change")

        os.chdir(repo)
        try:
            yield repo, base
        finally:
            os.chdir(prev_cwd)


def _fake_exec(result_text: str = REVIEW_OUTPUT, session_id: str = MINTED_SID,
               exit_code: int = 0, stderr: str = ""):
    """A ``run_cursor_exec`` stand-in that records its call and returns canned data."""
    calls: list[dict] = []

    returned_sid = session_id

    def _runner(prompt, session_id=None, *, spec=None, repo_root):
        calls.append({"session_id": session_id, "spec": spec,
                      "repo_root": repo_root, "prompt": prompt})
        return result_text, returned_sid, exit_code, stderr

    _runner.calls = calls  # type: ignore[attr-defined]
    return _runner


def _impl_args(repo: Path, base: str, receipt: Path, *, json_mode: bool = False,
               task: str = TASK_ID, spec=None):
    return argparse.Namespace(
        task=task, base=base, focus=None, receipt=str(receipt),
        json=json_mode, spec=spec,
    )


def _read_receipt(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CursorImplReview(unittest.TestCase):
    """R5 + R14 — impl-review receipt mode:cursor, no effort, rigor fields."""

    def test_writes_cursor_receipt_no_effort_and_prints_verdict(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            runner = _fake_exec()
            args = _impl_args(repo, base, receipt, json_mode=False)
            buf = io.StringIO()
            with mock.patch.object(flowctl, "run_cursor_exec", runner), \
                    contextlib.redirect_stdout(buf):
                flowctl.cmd_cursor_impl_review(args)
            # R5: prints VERDICT=
            self.assertIn("VERDICT=NEEDS_WORK", buf.getvalue())
            data = _read_receipt(receipt)
            self.assertEqual(data["mode"], "cursor")
            self.assertEqual(data["verdict"], "NEEDS_WORK")
            self.assertEqual(data["session_id"], MINTED_SID)
            self.assertEqual(data["type"], "impl_review")
            # R5 / R14: effort must NEVER appear in a cursor receipt.
            self.assertNotIn("effort", data)
            # model present, spec is cursor:<model>.
            self.assertTrue(data["model"])
            self.assertTrue(data["spec"].startswith("cursor:"))

    def test_carries_rigor_fields(self):
        # R14: confidence/suppressed, introduced-vs-pre_existing, unaddressed.
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", _fake_exec()):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            data = _read_receipt(receipt)
            self.assertEqual(data["suppressed_count"], {"50": 3, "25": 7})
            self.assertEqual(data["introduced_count"], 2)
            self.assertEqual(data["pre_existing_count"], 4)
            self.assertEqual(data["unaddressed"], ["R3", "R5"])
            self.assertNotIn("effort", data)

    def test_first_call_omits_resume_session(self):
        # R7: no prior receipt ⇒ run_cursor_exec gets session_id=None (resume-only,
        # NO uuid fabrication).
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            runner = _fake_exec()
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertEqual(len(runner.calls), 1)
            self.assertIsNone(runner.calls[0]["session_id"])

    def test_json_mode_payload_has_no_effort(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            args = _impl_args(repo, base, receipt, json_mode=True)
            buf = io.StringIO()
            with mock.patch.object(flowctl, "run_cursor_exec", _fake_exec()), \
                    contextlib.redirect_stdout(buf):
                flowctl.cmd_cursor_impl_review(args)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["mode"], "cursor")
            self.assertNotIn("effort", payload)
            self.assertEqual(payload["verdict"], "NEEDS_WORK")


class CursorResumeGuard(unittest.TestCase):
    """R7 — own-mode resume; cross-backend receipt ⇒ fresh session."""

    def test_resumes_only_when_prior_receipt_is_cursor(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "impl_review", "id": TASK_ID, "mode": "cursor",
                "verdict": "NEEDS_WORK", "session_id": PRIOR_SID,
            }), encoding="utf-8")
            runner = _fake_exec()
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertEqual(runner.calls[0]["session_id"], PRIOR_SID)

    def test_cross_backend_receipt_starts_fresh(self):
        # A copilot receipt at the path must NOT feed its session_id to cursor.
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "impl_review", "id": TASK_ID, "mode": "copilot",
                "verdict": "NEEDS_WORK", "session_id": "copilot-uuid-xyz",
            }), encoding="utf-8")
            runner = _fake_exec()
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertIsNone(runner.calls[0]["session_id"])

    def test_empty_prior_session_id_does_not_resume(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "impl_review", "id": TASK_ID, "mode": "cursor",
                "verdict": "NEEDS_WORK", "session_id": "",
            }), encoding="utf-8")
            runner = _fake_exec()
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertIsNone(runner.calls[0]["session_id"])


class CursorImplFailure(unittest.TestCase):
    """A backend failure / missing verdict must drop the receipt, never SHIP."""

    def test_nonzero_exit_drops_receipt_and_exits(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            receipt.write_text(json.dumps({
                "mode": "cursor", "session_id": PRIOR_SID,
            }), encoding="utf-8")
            runner = _fake_exec(result_text="", session_id=PRIOR_SID,
                                exit_code=2, stderr="auth failed")
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with self.assertRaises(SystemExit), \
                        contextlib.redirect_stderr(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertFalse(receipt.exists())

    def test_missing_verdict_drops_receipt_and_exits(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            runner = _fake_exec(result_text="no verdict here")
            args = _impl_args(repo, base, receipt)
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with self.assertRaises(SystemExit), \
                        contextlib.redirect_stderr(io.StringIO()):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertFalse(receipt.exists())


class CursorPlanReview(unittest.TestCase):
    """R6 — plan-review dispatches via run_cursor_exec, mode:cursor receipt."""

    def test_plan_review_writes_cursor_receipt(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            runner = _fake_exec()
            args = argparse.Namespace(
                epic=EPIC_ID, files="src/mod.py", base=base,
                receipt=str(receipt), json=False, spec=None,
            )
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_plan_review(args)
            self.assertEqual(len(runner.calls), 1)
            data = _read_receipt(receipt)
            self.assertEqual(data["type"], "plan_review")
            self.assertEqual(data["mode"], "cursor")
            self.assertEqual(data["session_id"], MINTED_SID)
            self.assertNotIn("effort", data)


class CursorCompletionReview(unittest.TestCase):
    """R6 + R14 — completion-review dispatch, rigor fields, no effort."""

    def test_completion_review_writes_cursor_receipt_with_rigor(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            runner = _fake_exec()
            args = argparse.Namespace(
                epic=EPIC_ID, base=base, receipt=str(receipt),
                json=False, spec=None,
            )
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_completion_review(args)
            data = _read_receipt(receipt)
            self.assertEqual(data["type"], "completion_review")
            self.assertEqual(data["mode"], "cursor")
            self.assertEqual(data["introduced_count"], 2)
            self.assertEqual(data["pre_existing_count"], 4)
            self.assertEqual(data["unaddressed"], ["R3", "R5"])
            self.assertNotIn("effort", data)


class CursorValidateDispatch(unittest.TestCase):
    """R6 — validator pass routes through run_cursor_exec with session continuity."""

    def _seed_cursor_receipt(self, receipt: Path, mode: str = "cursor"):
        receipt.write_text(json.dumps({
            "type": "impl_review", "id": TASK_ID, "mode": mode,
            "verdict": "NEEDS_WORK", "session_id": PRIOR_SID,
        }), encoding="utf-8")

    def test_validate_resumes_prior_session(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            self._seed_cursor_receipt(receipt)
            findings = repo / "findings.jsonl"
            findings.write_text(
                json.dumps({"id": "f1", "severity": "P1",
                            "file": "src/mod.py", "line": 2,
                            "description": "x"}) + "\n",
                encoding="utf-8",
            )
            validator_out = "All findings stand.\n<verdict>NEEDS_WORK</verdict>\n"
            runner = _fake_exec(result_text=validator_out, session_id=PRIOR_SID)
            args = argparse.Namespace(
                findings_file=str(findings), receipt=str(receipt),
                spec=None, json=True,
            )
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_validate(args)
            self.assertEqual(len(runner.calls), 1)
            self.assertEqual(runner.calls[0]["session_id"], PRIOR_SID)

    def test_validate_refuses_cross_backend_receipt(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            self._seed_cursor_receipt(receipt, mode="copilot")
            findings = repo / "findings.jsonl"
            findings.write_text(
                json.dumps({"id": "f1", "description": "x"}) + "\n",
                encoding="utf-8",
            )
            runner = _fake_exec()
            args = argparse.Namespace(
                findings_file=str(findings), receipt=str(receipt),
                spec=None, json=True,
            )
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with self.assertRaises(SystemExit), \
                        contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    flowctl.cmd_cursor_validate(args)
            # Cross-backend guard fires before any cursor invocation.
            self.assertEqual(len(runner.calls), 0)


class CursorDeepPassDispatch(unittest.TestCase):
    """R6 — deep-pass routes through run_cursor_exec with session continuity."""

    def test_deep_pass_resumes_prior_session(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "impl_review", "id": TASK_ID, "mode": "cursor",
                "verdict": "NEEDS_WORK", "session_id": PRIOR_SID,
            }), encoding="utf-8")
            deep_out = "No new issues.\n<verdict>NEEDS_WORK</verdict>\n"
            runner = _fake_exec(result_text=deep_out, session_id=PRIOR_SID)
            args = argparse.Namespace(
                pass_name="adversarial", primary_findings=None,
                receipt=str(receipt), spec=None, json=True,
            )
            with mock.patch.object(flowctl, "run_cursor_exec", runner):
                with contextlib.redirect_stdout(io.StringIO()):
                    flowctl.cmd_cursor_deep_pass(args)
            self.assertEqual(len(runner.calls), 1)
            self.assertEqual(runner.calls[0]["session_id"], PRIOR_SID)
            data = _read_receipt(receipt)
            self.assertIn("adversarial", data.get("deep_passes", []))


class CursorSpecBackendGuard(unittest.TestCase):
    """fn-74 completion-review fix — cursor commands reject a non-cursor ``--spec``.

    Without the guard, ``--spec codex:gpt-5.5:high`` parses and runs cursor-agent
    with a foreign model + serializes ``spec:"codex:..."`` under ``mode:"cursor"``
    (violating R5/R6/R14's cursor:<model> / no-effort contract).
    """

    def test_resolve_helper_rejects_non_cursor_spec(self):
        args = argparse.Namespace(spec="codex:gpt-5.5:high", json=False)
        with self.assertRaises(SystemExit):
            flowctl._resolve_cursor_review_spec(args, None)

    def test_resolve_helper_accepts_cursor_spec(self):
        args = argparse.Namespace(spec="cursor:gpt-5.5-high", json=False)
        spec = flowctl._resolve_cursor_review_spec(args, None)
        self.assertEqual(spec.backend, "cursor")
        self.assertEqual(spec.model, "gpt-5.5-high")
        self.assertIsNone(spec.effort)

    def test_impl_review_rejects_non_cursor_spec(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "r.json"
            args = _impl_args(repo, base, receipt, spec="codex:gpt-5.5:high")
            with mock.patch.object(flowctl, "run_cursor_exec", _fake_exec()):
                with self.assertRaises(SystemExit):
                    flowctl.cmd_cursor_impl_review(args)
            self.assertFalse(receipt.exists())


class CursorCheckIsError(unittest.TestCase):
    """fn-74 completion-review fix — ``cursor check`` honors ``is_error`` (R4).

    A cursor-agent probe can exit 0 yet carry ``is_error:true`` in its JSON
    result (an auth/backend failure); that must NOT report ``authed:true``.
    """

    def _probe(self, returncode: int, stdout: str) -> dict:
        fake = subprocess.CompletedProcess(args=[], returncode=returncode,
                                           stdout=stdout, stderr="")
        args = argparse.Namespace(json=True, skip_probe=False)
        buf = io.StringIO()
        with mock.patch.object(flowctl.shutil, "which",
                               return_value="/fake/cursor-agent"), \
                mock.patch.object(flowctl, "get_cursor_version",
                                  return_value="2026.06"), \
                mock.patch.object(flowctl.subprocess, "run", return_value=fake), \
                contextlib.redirect_stdout(buf):
            flowctl.cmd_cursor_check(args)
        return json.loads(buf.getvalue())

    def test_exit0_with_is_error_is_not_authed(self):
        out = self._probe(
            0, '{"type":"result","is_error":true,"result":"","session_id":"x"}')
        self.assertFalse(out["authed"])
        self.assertIsNotNone(out["error"])

    def test_clean_result_is_authed(self):
        out = self._probe(
            0, '{"type":"result","is_error":false,"result":"ok","session_id":"x"}')
        self.assertTrue(out["authed"])
        self.assertIsNone(out["error"])


if __name__ == "__main__":
    unittest.main()
