"""Tests for ``run_cursor_exec`` + the cursor-agent contract (fn-74.1).

cursor-agent diverges from copilot in four ways the spec locks down here:

- prompt is a **positional** argv arg (not ``-p <prompt>``, not stdin)
- session is **resume-only** — first call omits ``--resume`` and we capture the
  id cursor-agent mints; continuation passes ``--resume <id>``
- effort folds into the model name → **no** ``--effort`` flag
- run with ``cwd=repo_root`` and ``--mode ask`` (read-only) + ``--trust``

These tests mock ``subprocess.run`` and ``require_cursor`` so they run cleanly
on any host without spawning cursor-agent.
"""

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


SID = "aaaaaaaa-1111-2222-3333-444444444444"


def _result_json(result: str = "looks good", session_id: str = SID,
                 is_error: bool = False) -> str:
    """Build a cursor-agent ``--output-format json`` result line."""
    import json
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": is_error,
            "result": result,
            "session_id": session_id,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
    )


def _completed(stdout: str = "", returncode: int = 0, stderr: str = ""):
    """Fake ``subprocess.CompletedProcess`` for the mock."""
    result = mock.MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    result.stderr = stderr
    return result


class CursorInvocation(unittest.TestCase):
    """The shelled command must match the verified cursor-agent contract."""

    def test_success_parses_result_and_session(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/usr/local/bin/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json("ok body"))) as m_run:
                text, sid, rc, stderr = flowctl.run_cursor_exec(
                    prompt="review this", repo_root=repo_root,
                )
            self.assertEqual(rc, 0)
            self.assertEqual(text, "ok body")
            self.assertEqual(sid, SID)
            cmd = m_run.call_args.args[0]
            # Core flags present.
            for flag in ("-p", "--output-format", "json", "--trust",
                         "--mode", "ask", "--model"):
                self.assertIn(flag, cmd)
            # Prompt is the trailing POSITIONAL arg (not after -p).
            self.assertEqual(cmd[-1], "review this")
            self.assertNotEqual(cmd[cmd.index("-p") + 1], "review this")
            # No --effort (cursor folds effort into the model name).
            self.assertNotIn("--effort", cmd)
            # No stdin delivery.
            self.assertNotIn("input", m_run.call_args.kwargs)

    def test_mode_ask_is_read_only_no_edit_flags(self):
        # R8 unit-level: --mode ask must be present and no edit/write flag.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json())) as m_run:
                flowctl.run_cursor_exec(prompt="x", repo_root=repo_root)
            cmd = m_run.call_args.args[0]
            self.assertIn("--mode", cmd)
            self.assertEqual(cmd[cmd.index("--mode") + 1], "ask")
            # Must never pass an edit/write/agent mutation flag.
            for forbidden in ("--mode=agent", "--edit", "--write",
                              "--allow-all-tools", "--force"):
                self.assertNotIn(forbidden, cmd)
            # ``--mode`` is never anything but ``ask``.
            self.assertNotIn("agent", cmd)

    def test_cwd_is_repo_root(self):
        # R3 / repo-scoping: invoked from a subdir, must still pass cwd=repo_root.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            subdir = repo_root / "pkg" / "deep"
            subdir.mkdir(parents=True)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json())) as m_run:
                flowctl.run_cursor_exec(prompt="x", repo_root=repo_root)
            self.assertEqual(m_run.call_args.kwargs.get("cwd"), str(repo_root))


class CursorSessionResume(unittest.TestCase):
    """Resume-only session model."""

    def test_first_call_omits_resume_and_returns_generated_id(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            gen = "bbbbbbbb-9999-8888-7777-666666666666"
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json(session_id=gen))) as m_run:
                text, sid, rc, _ = flowctl.run_cursor_exec(
                    prompt="x", session_id=None, repo_root=repo_root,
                )
            cmd = m_run.call_args.args[0]
            # First call: NO --resume; we capture the generated id from result.
            self.assertNotIn("--resume", cmd)
            self.assertEqual(sid, gen)

    def test_continuation_passes_resume_id(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json(session_id=SID))) as m_run:
                flowctl.run_cursor_exec(
                    prompt="continue", session_id=SID, repo_root=repo_root,
                )
            cmd = m_run.call_args.args[0]
            self.assertIn("--resume", cmd)
            self.assertEqual(cmd[cmd.index("--resume") + 1], SID)


class CursorFailureModes(unittest.TestCase):
    """is_error / timeout / unparseable output must never SHIP silently."""

    def test_is_error_true_returns_nonzero_even_on_exit_zero(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json(
                                              result="boom", is_error=True),
                                          returncode=0)):
                text, sid, rc, _ = flowctl.run_cursor_exec(
                    prompt="x", repo_root=repo_root,
                )
            self.assertNotEqual(rc, 0)

    def test_cli_nonzero_exit_propagates(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout="", returncode=3,
                                          stderr="auth failed")):
                text, sid, rc, stderr = flowctl.run_cursor_exec(
                    prompt="x", repo_root=repo_root,
                )
            self.assertEqual(rc, 3)
            self.assertEqual(stderr, "auth failed")

    def test_timeout_returns_exit_two(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(
                        flowctl.subprocess, "run",
                        side_effect=flowctl.subprocess.TimeoutExpired(
                            cmd="cursor-agent", timeout=600)):
                text, sid, rc, stderr = flowctl.run_cursor_exec(
                    prompt="x", session_id=SID, repo_root=repo_root,
                )
            self.assertEqual(rc, 2)
            self.assertEqual(sid, SID)  # input id preserved on timeout
            self.assertIn("timed out", stderr)

    def test_empty_stdout_is_backend_failure(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout="", returncode=0)):
                text, sid, rc, _ = flowctl.run_cursor_exec(
                    prompt="x", repo_root=repo_root,
                )
            self.assertNotEqual(rc, 0)
            self.assertEqual(text, "")


class CursorPromptTooLarge(unittest.TestCase):
    """Above the argv threshold: fail closed via a non-zero return tuple (NOT a
    raised exception), so cursor command handlers hit their ``exit_code != 0``
    cleanup (drop stale receipt + structured error) instead of leaking a
    traceback."""

    def test_oversized_prompt_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            big = "x" * (flowctl.CURSOR_ARGV_PROMPT_MAX + 1)
            # Fail closed BEFORE shelling out — subprocess.run must not be called.
            with mock.patch.object(flowctl.subprocess, "run") as m_run, \
                    mock.patch.object(flowctl, "require_cursor",
                                      return_value="/cursor-agent"):
                out, _sid, rc, err = flowctl.run_cursor_exec(
                    prompt=big, repo_root=repo_root)
            m_run.assert_not_called()
            self.assertEqual(out, "")
            self.assertNotEqual(rc, 0)
            self.assertIn("too large", err)

    def test_at_threshold_boundary_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            # ``>=`` threshold: exactly MAX chars fails closed (no spawn).
            at = "x" * flowctl.CURSOR_ARGV_PROMPT_MAX
            with mock.patch.object(flowctl.subprocess, "run") as m_run, \
                    mock.patch.object(flowctl, "require_cursor",
                                      return_value="/cursor-agent"):
                _out, _sid, rc, err = flowctl.run_cursor_exec(
                    prompt=at, repo_root=repo_root)
            m_run.assert_not_called()
            self.assertNotEqual(rc, 0)
            self.assertIn("too large", err)

    def test_just_under_threshold_does_not_raise(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            ok = "x" * (flowctl.CURSOR_ARGV_PROMPT_MAX - 1)
            with mock.patch.object(flowctl, "require_cursor",
                                   return_value="/cursor-agent"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout=_result_json())):
                _, _, rc, _ = flowctl.run_cursor_exec(
                    prompt=ok, repo_root=repo_root,
                )
            self.assertEqual(rc, 0)


class CursorResultParser(unittest.TestCase):
    """``_parse_cursor_result`` tolerates single-object + streaming JSON-lines."""

    def test_single_object(self):
        text, sid, is_err = flowctl._parse_cursor_result(_result_json("hi"))
        self.assertEqual(text, "hi")
        self.assertEqual(sid, SID)
        self.assertFalse(is_err)

    def test_streaming_jsonlines_takes_result_object(self):
        import json
        stream = "\n".join([
            json.dumps({"type": "assistant", "text": "thinking"}),
            json.dumps({"type": "tool_call", "name": "read"}),
            _result_json("final answer"),
        ])
        text, sid, is_err = flowctl._parse_cursor_result(stream)
        self.assertEqual(text, "final answer")
        self.assertEqual(sid, SID)
        self.assertFalse(is_err)

    def test_unparseable_is_error(self):
        text, sid, is_err = flowctl._parse_cursor_result("not json at all")
        self.assertEqual(text, "")
        self.assertIsNone(sid)
        self.assertTrue(is_err)


if __name__ == "__main__":
    unittest.main()
