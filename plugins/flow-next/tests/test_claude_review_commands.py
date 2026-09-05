"""Real-CLI tests for the ``flowctl claude`` review commands (fn-221.2, R2/R6).

Every case drives the REAL entry point (``flowctl.main`` with ``sys.argv``
set) so argparse, the thin ``cmd_claude_*`` wrappers, the shared
``cmd_backend_review`` driver, ``_claude_run_exec`` and ``run_claude_exec``
all execute; only ``subprocess.run`` / ``shutil.which`` are replaced at the
Python boundary (a fake ``claude`` that records argv + stdin and returns a
canned result JSON). A PATH shim cannot observe spawns on Windows, so the
stub lives here, not in the shell. ``git`` passes through to the real binary.
"""

from __future__ import annotations

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


EPIC_ID = "fn-1-claude-demo"
TASK_ID = f"{EPIC_ID}.1"
SID = "11111111-2222-3333-4444-555555555555"
FAKE_CLAUDE = "/fake/bin/claude"
FIXED_ARGV = [
    "-p", "--output-format", "json", "--permission-mode", "dontAsk",
    "--tools", "Read", "Grep", "Glob", "--strict-mcp-config",
]
FORBIDDEN_TOKENS = ("--allowedTools", "Bash", "Edit", "Write")
REVIEW_TEXT = "Reviewed the diff.\n\n<verdict>NEEDS_WORK</verdict>\n"
PASS_TEXT = "No new issues.\n<verdict>NEEDS_WORK</verdict>\n"


def _git_raw(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
    ).stdout


def _git(repo: Path, *args: str) -> str:
    return _git_raw(repo, *args).strip()


@contextlib.contextmanager
def _flow_repo():
    """Real temp git repo + ``.flow`` tree with a base..HEAD diff, chdir'd."""
    prev_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td).resolve()
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t.t")
        _git(repo, "config", "user.name", "t")
        (repo / "src").mkdir()
        (repo / "src" / "mod.py").write_text("def a(x):\n    return x\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")
        base = _git(repo, "rev-parse", "HEAD")

        flow = repo / ".flow"
        (flow / "specs").mkdir(parents=True)
        (flow / "tasks").mkdir(parents=True)
        (flow / "specs" / f"{EPIC_ID}.md").write_text(
            "# Demo spec\n\n## Acceptance Criteria\n\n- **R1:** do a thing\n",
            encoding="utf-8",
        )
        (flow / "specs" / f"{EPIC_ID}.json").write_text(
            json.dumps({"id": EPIC_ID, "title": "Demo", "status": "in_progress"}),
            encoding="utf-8",
        )
        (flow / "tasks" / f"{TASK_ID}.md").write_text(
            "---\nsatisfies: [R1]\n---\n\n## Description\n\nImplement a().\n",
            encoding="utf-8",
        )
        _commit_change(repo, "def a(x):\n    return x + 1\n", "change")

        os.chdir(repo)
        try:
            yield repo, base
        finally:
            os.chdir(prev_cwd)


def _commit_change(repo: Path, body: str, message: str) -> str:
    (repo / "src" / "mod.py").write_text(body, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _result_json(text: str = REVIEW_TEXT, session_id: str = SID, **extra) -> str:
    payload = {
        "type": "result", "subtype": "success", "is_error": False,
        "result": text, "session_id": session_id,
    }
    payload.update(extra)
    return json.dumps(payload)


class _Fake:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _scratch(repo: Path) -> Path:
    return repo / ".flow" / "tmp" / "claude-review"


def _diff_files(repo: Path) -> list[str]:
    scratch = _scratch(repo)
    return sorted(p.name for p in scratch.glob("*.diff")) if scratch.exists() else []


@contextlib.contextmanager
def _fake_claude(*, dispatch=None, missing: bool = False):
    """Stub the subprocess boundary. Yields the recorded ``calls`` list.

    Each dispatch appends ``{"argv", "stdin", "cwd", "diff_files"}`` -
    ``diff_files`` is the scratch directory snapshot taken WHILE the fake CLI
    runs, so "the diff file exists before the spawn" is observed, not inferred.
    ``dispatch(argv, stdin) -> (stdout, stderr, rc)`` decides the outcome
    (default: a canned NEEDS_WORK result). ``missing`` hides the CLI from PATH.
    """
    calls: list[dict] = []
    real_run = flowctl.subprocess.run
    real_which = flowctl.shutil.which

    def fake_run(cmd, **kwargs):
        argv = list(cmd)
        if argv and argv[0] == "git":
            return real_run(cmd, **kwargs)
        if argv[0] != FAKE_CLAUDE:
            raise AssertionError(f"unexpected spawn: {argv}")
        if argv[1:] == ["--version"]:
            return _Fake(stdout="2.1.260 (Claude Code)")
        cwd = Path(kwargs.get("cwd") or os.getcwd())
        calls.append({
            "argv": argv[1:], "stdin": kwargs.get("input"), "cwd": cwd,
            "diff_files": _diff_files(cwd),
        })
        if dispatch is None:
            return _Fake(stdout=_result_json())
        out, err, rc = dispatch(argv[1:], kwargs.get("input"))
        return _Fake(stdout=out, stderr=err, returncode=rc)

    def fake_which(binary):
        if binary == "claude":
            return None if missing else FAKE_CLAUDE
        return real_which(binary)

    flowctl._CLI_VERSION_CACHE.pop(FAKE_CLAUDE, None)
    with mock.patch.object(flowctl.subprocess, "run", fake_run), \
            mock.patch.object(flowctl.shutil, "which", fake_which):
        yield calls


def _run_cli(*argv: str) -> tuple[int, str, str]:
    """Drive ``flowctl.main`` exactly as the shell would."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with mock.patch.object(sys, "argv", ["flowctl", *argv]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            flowctl.main()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def _impl_review(repo: Path, base: str, receipt: Path, *extra: str):
    return _run_cli(
        "claude", "impl-review", TASK_ID, "--base", base,
        "--receipt", str(receipt), "--json", *extra,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_fixed_read_only_argv(tc: unittest.TestCase, argv: list[str]) -> None:
    tc.assertEqual(argv[: len(FIXED_ARGV)], FIXED_ARGV)
    for token in FORBIDDEN_TOKENS:
        tc.assertNotIn(token, argv)


class ClaudeSurface(unittest.TestCase):
    """The five subcommands exist; the codex-only fan-out is an invalid choice."""

    def test_five_subcommands_have_help(self):
        for sub in ("impl-review", "plan-review", "completion-review",
                    "validate", "deep-pass"):
            with self.subTest(sub=sub):
                code, out, _err = _run_cli("claude", sub, "--help")
                self.assertEqual(code, 0)
                self.assertIn("--spec", out)

    def test_fanout_is_an_argparse_invalid_choice(self):
        code, _out, err = _run_cli("claude", "impl-review-fanout", "--base", "HEAD~1")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)
        self.assertIn("impl-review-fanout", err)


class ClaudeImplReview(unittest.TestCase):
    """R2: receipt shape, stdin transport, fixed read-only argv, diff by path."""

    def test_receipt_argv_stdin_and_diff_file(self):
        with _flow_repo() as (repo, base):
            head = _git(repo, "rev-parse", "HEAD")
            receipt = repo / "receipt.json"
            with _fake_claude() as calls:
                code, out, err = _impl_review(repo, base, receipt)
            self.assertEqual(code, 0, err)
            payload = json.loads(out)
            data = _read_json(receipt)
            default = flowctl.BACKEND_REGISTRY["claude"]["default_model"]
            for row in (payload, data):
                self.assertEqual(row["mode"], "claude")
                self.assertEqual(row["model"], default)
                self.assertEqual(row["effort"], "high")
                self.assertEqual(row["session_id"], SID)
                self.assertEqual(row["verdict"], "NEEDS_WORK")
            self.assertEqual(data["type"], "impl_review")
            self.assertTrue(data["spec"].startswith("claude:"))

            self.assertEqual(len(calls), 1)
            call = calls[0]
            self.assertEqual(
                call["argv"],
                [*FIXED_ARGV, "--model", default, "--effort", "high"],
            )
            _assert_fixed_read_only_argv(self, call["argv"])
            self.assertNotIn("--resume", call["argv"])
            # Prompt on stdin, naming the diff path and the reviewed range.
            diff_name = f"receipt-{base[:7]}-{head[:7]}.diff"
            diff_path = _scratch(repo) / diff_name
            self.assertIn("<verdict>", call["stdin"])
            self.assertIn(str(diff_path), call["stdin"])
            self.assertIn(f"{base}..{head}", call["stdin"])
            # The file existed with the reviewed range WHILE the CLI ran.
            self.assertEqual(call["diff_files"], [diff_name])
            self.assertEqual(
                diff_path.read_text(encoding="utf-8"),
                _git_raw(repo, "diff", f"{base}..{head}"),
            )

    def test_rereview_after_fix_resumes_and_writes_new_range_file(self):
        # Real-command regression: review -> fix commit -> same command on the
        # same receipt. The second run resumes the receipt's session, writes a
        # NEW range file, names it in the prompt, leaves the first untouched.
        with _flow_repo() as (repo, base):
            head1 = _git(repo, "rev-parse", "HEAD")
            receipt = repo / "receipt.json"
            with _fake_claude():
                code, _out, err = _impl_review(repo, base, receipt)
            self.assertEqual(code, 0, err)
            first = _scratch(repo) / f"receipt-{base[:7]}-{head1[:7]}.diff"
            first_bytes = first.read_bytes()

            head2 = _commit_change(repo, "def a(x):\n    return x + 2\n", "fix")
            with _fake_claude() as calls:
                code, _out, err = _impl_review(repo, base, receipt)
            self.assertEqual(code, 0, err)
            argv = calls[0]["argv"]
            _assert_fixed_read_only_argv(self, argv)
            self.assertEqual(argv[argv.index("--resume") + 1], SID)
            second = _scratch(repo) / f"receipt-{base[:7]}-{head2[:7]}.diff"
            self.assertEqual(_diff_files(repo), sorted([first.name, second.name]))
            self.assertEqual(second.read_text(encoding="utf-8"),
                             _git_raw(repo, "diff", f"{base}..{head2}"))
            self.assertIn(str(second), calls[0]["stdin"])
            self.assertIn(f"{base}..{head2}", calls[0]["stdin"])
            self.assertEqual(first.read_bytes(), first_bytes)
            self.assertEqual(_read_json(receipt)["session_id"], SID)


class ClaudeSessionPasses(unittest.TestCase):
    """deep-pass / validate resume the primary session and write nothing."""

    def _primary(self, repo: Path, base: str, receipt: Path) -> Path:
        with _fake_claude():
            code, _out, err = _impl_review(repo, base, receipt)
        self.assertEqual(code, 0, err)
        (only,) = _diff_files(repo)
        return _scratch(repo) / only

    def _assert_resumed_and_wrote_nothing(self, repo: Path, calls: list[dict],
                                          primary: Path, primary_bytes: bytes):
        self.assertEqual(len(calls), 1)
        argv = calls[0]["argv"]
        _assert_fixed_read_only_argv(self, argv)
        self.assertEqual(argv[argv.index("--resume") + 1], SID)
        self.assertNotIn("## Diff delivery (claude backend)", calls[0]["stdin"])
        self.assertEqual(calls[0]["diff_files"], [primary.name])
        self.assertEqual(_diff_files(repo), [primary.name])
        self.assertEqual(primary.read_bytes(), primary_bytes)

    def test_deep_pass_after_head_moves(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            primary = self._primary(repo, base, receipt)
            primary_bytes = primary.read_bytes()
            _commit_change(repo, "def a(x):\n    return x + 3\n", "moved")
            with _fake_claude(dispatch=lambda a, i: (_result_json(PASS_TEXT), "", 0)) as calls:
                code, _out, err = _run_cli(
                    "claude", "deep-pass", "--pass", "adversarial",
                    "--receipt", str(receipt), "--json",
                )
            self.assertEqual(code, 0, err)
            self._assert_resumed_and_wrote_nothing(repo, calls, primary, primary_bytes)

    def test_validate_after_head_moves(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            primary = self._primary(repo, base, receipt)
            primary_bytes = primary.read_bytes()
            _commit_change(repo, "def a(x):\n    return x + 3\n", "moved")
            findings = repo / "findings.jsonl"
            findings.write_text(
                json.dumps({"id": "f1", "severity": "P1", "file": "src/mod.py",
                            "line": 2, "description": "x"}) + "\n",
                encoding="utf-8",
            )
            with _fake_claude(dispatch=lambda a, i: (_result_json(PASS_TEXT), "", 0)) as calls:
                code, _out, err = _run_cli(
                    "claude", "validate", "--findings-file", str(findings),
                    "--receipt", str(receipt), "--json",
                )
            self.assertEqual(code, 0, err)
            self._assert_resumed_and_wrote_nothing(repo, calls, primary, primary_bytes)


class ClaudeFailures(unittest.TestCase):
    """CLI missing -> backend-missing failure; bad payload -> RETRY, no verdict."""

    def test_missing_cli_fails_before_any_spawn(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            with _fake_claude(missing=True) as calls:
                code, _out, err = _run_cli(
                    "claude", "impl-review", TASK_ID, "--base", base,
                    "--receipt", str(receipt),
                )
            self.assertEqual(code, 2)
            self.assertIn("claude not found in PATH", err)
            self.assertEqual(calls, [])
            self.assertFalse(receipt.exists())

    def test_malformed_payload_is_a_transport_failure_never_a_verdict(self):
        cases = {
            "not-json": ("this is not json", "", 0),
            "wrong-type": (json.dumps({"type": "assistant", "result": REVIEW_TEXT}), "", 0),
            "error-envelope-with-verdict-text": (
                _result_json("<verdict>SHIP</verdict>", is_error=True), "", 0),
        }
        for name, result in cases.items():
            with self.subTest(case=name), _flow_repo() as (repo, base):
                receipt = repo / "receipt.json"
                with _fake_claude(dispatch=lambda a, i, r=result: r) as calls:
                    code, out, _err = _impl_review(repo, base, receipt)
                self.assertEqual(code, 2)
                self.assertEqual(len(calls), 1)
                self.assertFalse(receipt.exists())
                self.assertNotIn("SHIP", json.loads(out).get("verdict", "") or "")
                attempts = _read_json(
                    repo / ".flow" / "specs" / f"{EPIC_ID}.json"
                )["review_attempts"]
                self.assertIsNone(attempts[-1]["verdict"])
                self.assertEqual(attempts[-1]["failure_class"], "nonzero_exit")

    def test_foreign_spec_rejected_before_spawn(self):
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            with _fake_claude() as calls:
                code, out, _err = _impl_review(
                    repo, base, receipt, "--spec", "codex:gpt-5.5:high")
            self.assertEqual(code, 2)
            self.assertIn("claude:<model>[:<effort>]", json.loads(out)["error"])
            self.assertEqual(calls, [])
            self.assertFalse(receipt.exists())

    def test_session_passes_reject_foreign_spec_before_spawn(self):
        # Review round 1 finding: the optional passes share the primary
        # commands' strict grammar - a foreign model id never reaches the CLI.
        with _flow_repo() as (repo, base):
            receipt = repo / "receipt.json"
            receipt.write_text(json.dumps({
                "type": "impl_review", "id": TASK_ID, "mode": "claude",
                "verdict": "NEEDS_WORK", "session_id": SID,
            }), encoding="utf-8")
            findings = repo / "findings.jsonl"
            findings.write_text(json.dumps({"id": "f1", "description": "x"}) + "\n",
                                encoding="utf-8")
            for argv in (
                ("claude", "deep-pass", "--pass", "adversarial"),
                ("claude", "validate", "--findings-file", str(findings)),
            ):
                with self.subTest(command=argv[1]), _fake_claude() as calls:
                    code, out, _err = _run_cli(
                        *argv, "--receipt", str(receipt), "--json",
                        "--spec", "codex:gpt-5.5:high",
                    )
                    self.assertEqual(code, 2)
                    self.assertIn("claude:<model>[:<effort>]", json.loads(out)["error"])
                    self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
