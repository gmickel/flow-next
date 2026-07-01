"""Tests for ``run_copilot_exec`` platform branching (1.1.9).

The function takes two prompt-delivery paths:

- **POSIX** — argv ``-p <prompt>`` + create-or-resume ``--resume=<uuid>``.
- **Windows** — stdin (``subprocess.run(input=prompt, ...)``) + create vs
  resume picked from a touch marker because stdin-mode ``--resume`` is
  resume-only.

These tests mock ``subprocess.run`` and ``require_copilot`` so they run
cleanly on any host without spawning copilot.
"""

import io
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


def _completed(stdout: str = "ok", returncode: int = 0, stderr: str = ""):
    """Build a fake ``subprocess.CompletedProcess`` for the mock."""
    result = mock.MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    result.stderr = stderr
    return result


class CopilotPosixPath(unittest.TestCase):
    """POSIX path: -p + argv; session flag is marker-tracked (copilot >= 1.0.65
    made --resume resume-only here too, so the FIRST call uses --session-id)."""

    def test_posix_uses_argv_with_dash_p(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(sys, "platform", "darwin"), \
                    mock.patch.object(flowctl, "require_copilot",
                                      return_value="/usr/local/bin/copilot"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed()) as m_run:
                stdout, sid, rc, _ = flowctl.run_copilot_exec(
                    prompt="hello world",
                    session_id="11111111-1111-1111-1111-111111111111",
                    repo_root=repo_root,
                )
            self.assertEqual(rc, 0)
            self.assertEqual(stdout, "ok")
            # Argv must contain -p with the literal prompt, and --session-id on
            # the FIRST call (no marker yet) — copilot --resume is resume-only.
            cmd = m_run.call_args.args[0]
            self.assertIn("-p", cmd)
            self.assertEqual(cmd[cmd.index("-p") + 1], "hello world")
            self.assertIn(
                "--session-id=11111111-1111-1111-1111-111111111111", cmd
            )
            # stdin is NOT used on POSIX path.
            self.assertNotIn("input", m_run.call_args.kwargs)
            # Marker dir IS created on POSIX now (success-touch) so the NEXT
            # call switches to --resume.
            marker_dir = repo_root / ".flow" / "tmp" / "copilot-sessions"
            self.assertTrue(marker_dir.exists())


class CopilotWindowsStdinPath(unittest.TestCase):
    """Windows path: stdin delivery, --session-id first, --resume after."""

    def test_first_call_uses_session_id_and_stdin(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(sys, "platform", "win32"), \
                    mock.patch.object(flowctl, "require_copilot",
                                      return_value="C:\\copilot.exe"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed()) as m_run:
                stdout, sid, rc, _ = flowctl.run_copilot_exec(
                    prompt="x" * 60_000,  # would blow argv cap if -p path
                    session_id="22222222-2222-2222-2222-222222222222",
                    repo_root=repo_root,
                )
            self.assertEqual(rc, 0)
            cmd = m_run.call_args.args[0]
            kwargs = m_run.call_args.kwargs
            # Windows path MUST use --session-id (resume errors on first call).
            self.assertIn(
                "--session-id=22222222-2222-2222-2222-222222222222", cmd
            )
            # Windows path MUST NOT use -p (would blow argv cap).
            self.assertNotIn("-p", cmd)
            # Prompt is delivered via stdin.
            self.assertEqual(kwargs.get("input"), "x" * 60_000)
            # Marker file is created after the successful first call so the
            # next invocation switches to --resume.
            marker = flowctl._copilot_session_marker(
                repo_root, "22222222-2222-2222-2222-222222222222"
            )
            self.assertTrue(marker.exists())

    def test_second_call_uses_resume(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            # Simulate prior successful call by pre-creating the marker.
            marker = flowctl._copilot_session_marker(
                repo_root, "33333333-3333-3333-3333-333333333333"
            )
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()
            with mock.patch.object(sys, "platform", "win32"), \
                    mock.patch.object(flowctl, "require_copilot",
                                      return_value="C:\\copilot.exe"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed()) as m_run:
                flowctl.run_copilot_exec(
                    prompt="continuation",
                    session_id="33333333-3333-3333-3333-333333333333",
                    repo_root=repo_root,
                )
            cmd = m_run.call_args.args[0]
            self.assertIn(
                "--resume=33333333-3333-3333-3333-333333333333", cmd
            )
            self.assertNotIn(
                "--session-id=33333333-3333-3333-3333-333333333333", cmd
            )

    def test_failed_first_call_does_not_create_marker(self):
        # If copilot exits non-zero on first call, the session likely wasn't
        # created — leave the marker absent so the next attempt also tries
        # --session-id.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(sys, "platform", "win32"), \
                    mock.patch.object(flowctl, "require_copilot",
                                      return_value="C:\\copilot.exe"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed(
                                          stdout="", returncode=2,
                                          stderr="boom")):
                flowctl.run_copilot_exec(
                    prompt="x",
                    session_id="44444444-4444-4444-4444-444444444444",
                    repo_root=repo_root,
                )
            marker = flowctl._copilot_session_marker(
                repo_root, "44444444-4444-4444-4444-444444444444"
            )
            self.assertFalse(marker.exists())

    def test_no_temp_file_on_windows(self):
        # The POSIX path stages large prompts to .flow/tmp/copilot-prompt-*.txt
        # as a scratch buffer. Windows stdin path doesn't need it.
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            with mock.patch.object(sys, "platform", "win32"), \
                    mock.patch.object(flowctl, "require_copilot",
                                      return_value="C:\\copilot.exe"), \
                    mock.patch.object(flowctl.subprocess, "run",
                                      return_value=_completed()):
                flowctl.run_copilot_exec(
                    prompt="y" * 50_000,
                    session_id="55555555-5555-5555-5555-555555555555",
                    repo_root=repo_root,
                )
            tmp_dir = repo_root / ".flow" / "tmp"
            stray = [p for p in tmp_dir.glob("copilot-prompt-*")
                     if tmp_dir.exists()]
            self.assertEqual(stray, [],
                             "Windows stdin path must not leave temp prompt files")


if __name__ == "__main__":
    unittest.main()
