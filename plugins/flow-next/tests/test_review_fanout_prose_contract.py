"""fn-215 fan-out prose-contract pins (completion review R8/R15).

Grep-shaped assertions on minimal STRUCTURAL tokens of the fan-out workflow
surfaces: command names, flag names, heading presence, the two quoted
user-facing steering phrasings (command-like tokens), and executable-line
greps for the round lifecycle. No sentence-level prose assertions
(2026-08-07 rule) - prose quality is judged via .flow/criteria.md, and
deliberate-prose-change detection is test_prompt_text_pinned's job.
Canonical files and the generated Codex mirror are both pinned.
"""

from __future__ import annotations

import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

CANONICAL = PLUGIN / "skills" / "flow-next-impl-review"
MIRROR = PLUGIN / "codex" / "skills" / "flow-next-impl-review"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class CodexWorkflowFanoutContract(unittest.TestCase):
    """workflow-codex.md: command/flag tokens + quoted steering phrasings."""

    def _texts(self) -> list[str]:
        return [
            _read(CANONICAL / "workflow-codex.md"),
            _read(MIRROR / "workflow-codex.md"),
        ]

    def test_steering_phrasings_present(self) -> None:
        # Quoted user-facing phrasings the coordinator matches against - these
        # are command-like tokens, not prose.
        for text in self._texts():
            self.assertIn('"use 1 reviewer instead of 3"', text)
            self.assertIn(
                '"use three different model families for the review fan-out"',
                text,
            )

    def test_fanout_commands_and_flags_present(self) -> None:
        for text in self._texts():
            self.assertIn("impl-review-fanout ", text)
            self.assertIn("review-route ", text)
            self.assertIn("--rotate-stale", text)
            self.assertIn("impl-review-fanout-finalize", text)
            self.assertIn("--draw ", text)
            self.assertIn("--merged-file", text)
            self.assertIn("--rid", text)
            self.assertIn("--receipt", text)

    def test_needs_work_survivors_flag_in_executable_block(self) -> None:
        # The finalize's executable argument array must carry the flag - not
        # just prose mentioning it.
        for text in self._texts():
            exec_lines = [
                line
                for line in text.splitlines()
                if line.lstrip().startswith("args+=(")
                and "--needs-work-survivors" in line
            ]
            self.assertTrue(
                exec_lines,
                "--needs-work-survivors missing from an args+=( executable line",
            )


class HostWorkflowFanoutContract(unittest.TestCase):
    """workflow-host.md: round-lifecycle executable lines + heading presence."""

    def _texts(self) -> list[str]:
        return [
            _read(CANONICAL / "workflow-host.md"),
            _read(MIRROR / "workflow-host.md"),
        ]

    def test_one_increment_one_record_executable_lines(self) -> None:
        # Exactly one executable increment line and one executable record line
        # (FLOWCTL invocations), pinning the one-increment/one-record shape.
        for text in self._texts():
            increment_lines = [
                line
                for line in text.splitlines()
                if "review-rounds increment" in line and "FLOWCTL" in line
            ]
            record_lines = [
                line
                for line in text.splitlines()
                if "review-rounds record" in line and "FLOWCTL" in line
            ]
            self.assertEqual(len(increment_lines), 1)
            self.assertEqual(len(record_lines), 1)

    def test_first_round_three_draws_heading(self) -> None:
        for text in self._texts():
            self.assertIn(
                "### First round: three axis draws in ONE message", text
            )

    def test_sequential_fallback_degradation_token(self) -> None:
        for text in self._texts():
            self.assertIn("degradation", text)
            self.assertIn("review-route ", text)


if __name__ == "__main__":
    unittest.main()
