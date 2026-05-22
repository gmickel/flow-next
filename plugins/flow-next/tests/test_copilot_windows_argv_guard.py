"""Tests for `_copilot_windows_argv_too_long` (1.1.8).

Windows CreateProcessW caps lpCommandLine at 32767 chars. Copilot CLI
delivers the prompt only via argv (no --prompt-file / @file / stdin),
so spec-sized review prompts on Windows hit the cap. The guard returns
an actionable error message; callers handle it like any other Copilot
failure (exit_code 2 + clean error_exit).

Pure helper — these tests don't spawn copilot or touch the filesystem.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


# A minimal-but-realistic argv shape. The non-prompt args contribute
# ~150 chars at typical paths; the prompt arg dominates.
_FIXED_ARGS = [
    "/opt/homebrew/bin/copilot",
    "-p",
    # prompt placeholder — tests rewrite this
    "",
    "--resume=00000000-0000-0000-0000-000000000000",
    "--output-format",
    "text",
    "-s",
    "--no-ask-user",
    "--allow-all-tools",
    "--add-dir",
    "/Users/gordon/repo",
    "--disable-builtin-mcps",
    "--no-custom-instructions",
    "--log-level",
    "error",
    "--no-auto-update",
    "--model",
    "claude-opus-4.5",
]


def _cmd_with_prompt(n: int) -> list:
    cmd = list(_FIXED_ARGS)
    cmd[2] = "x" * n
    return cmd


class CopilotWindowsArgvGuard(unittest.TestCase):

    def test_non_windows_returns_none_even_when_huge(self):
        # On macOS / Linux the guard is a no-op even for absurd prompts.
        for platform in ("darwin", "linux", "linux2"):
            with self.subTest(platform=platform), \
                    mock.patch.object(sys, "platform", platform):
                # 200 KB prompt — would crash Windows, fine elsewhere.
                self.assertIsNone(
                    flowctl._copilot_windows_argv_too_long(
                        _cmd_with_prompt(200_000)
                    )
                )

    def test_windows_under_cap_returns_none(self):
        # Small prompt — well under the 32767 cap.
        with mock.patch.object(sys, "platform", "win32"):
            self.assertIsNone(
                flowctl._copilot_windows_argv_too_long(
                    _cmd_with_prompt(1_000)
                )
            )

    def test_windows_over_cap_returns_actionable_message(self):
        # 40 KB prompt — comfortably over the 32767 cap.
        with mock.patch.object(sys, "platform", "win32"):
            msg = flowctl._copilot_windows_argv_too_long(
                _cmd_with_prompt(40_000)
            )
        self.assertIsNotNone(msg)
        # Message must surface: the actual cap, the Copilot-CLI cause,
        # the WSL workaround. These are the three things the operator
        # needs to know to recover or escalate.
        self.assertIn("32,767", msg)
        self.assertIn("Copilot CLI offers no", msg)
        self.assertIn("WSL", msg)
        # Sanity: actual lengths surface for diagnosability.
        self.assertIn("40,000", msg)

    def test_windows_just_at_boundary(self):
        # Prompt sized so projected ≈ cap - margin should trip; margin - 1
        # below should be clean. Use a synthetic cmd with only the prompt
        # arg to make the math obvious.
        with mock.patch.object(sys, "platform", "win32"):
            budget = (
                flowctl.WINDOWS_CMDLINE_CAP_CHARS
                - flowctl.WINDOWS_CMDLINE_SAFETY_MARGIN
            )
            # Per-arg overhead is 3 chars (2 quotes + 1 separator). With a
            # single arg, projected = len + 3.
            self.assertIsNone(
                flowctl._copilot_windows_argv_too_long(["x" * (budget - 10)])
            )
            self.assertIsNotNone(
                flowctl._copilot_windows_argv_too_long(["x" * (budget + 10)])
            )

    def test_empty_cmd_returns_none(self):
        # Defensive: an empty cmd list shouldn't raise even on Windows.
        with mock.patch.object(sys, "platform", "win32"):
            self.assertIsNone(flowctl._copilot_windows_argv_too_long([]))


if __name__ == "__main__":
    unittest.main()
