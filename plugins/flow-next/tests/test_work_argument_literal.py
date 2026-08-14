"""Work-skill argument-literal prose contract (lifted from the retired
``test_codex_delegation_gates.py`` in flow-98.4).

The host expands raw skill arguments once into the ``<work-arguments>`` block;
Work must treat that block as literal prompt data, never shell input, and strip
``mode:autonomous`` only as a standalone whitespace token. The packaged
codex-delegation subsystem that originally carried these assertions was removed
by flow-98, but the contract itself guards still-shipped Autonomous Mode prose
in the canonical skill and the Codex mirror.
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK_SKILL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-work"
SKILL_MD = WORK_SKILL / "SKILL.md"
CODEX_SKILL_MD = (
    REPO_ROOT
    / "plugins"
    / "flow-next"
    / "codex"
    / "skills"
    / "flow-next-work"
    / "SKILL.md"
)


def _extract_work_argument_block(text: str) -> str:
    """Return the host-substitution slot, which must remain outside shell."""
    start_marker = "<work-arguments>\n"
    end_marker = "\n</work-arguments>"
    start = text.find(start_marker)
    if start == -1:
        raise AssertionError("literal work-arguments block not found")
    start += len(start_marker)
    end = text.find(end_marker, start)
    if end == -1:
        raise AssertionError("literal work-arguments block is unterminated")
    return text[start:end]


def _strip_standalone_autonomous_token(raw: str) -> tuple[int, str]:
    """Executable oracle for the prompt's literal, whitespace-token contract."""
    pattern = re.compile(r"(?<!\S)mode:autonomous(?!\S)")
    matches = list(pattern.finditer(raw))
    result = raw
    for match in reversed(matches):
        start, end = match.span()
        if end < len(result) and result[end].isspace():
            end += 1
        elif start > 0 and result[start - 1].isspace():
            start -= 1
        result = result[:start] + result[end:]
    return (1 if matches else 0), result


class WorkArgumentLiteralContract(unittest.TestCase):
    """The host expands raw skill arguments once; Work must keep them out of shell."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.skills = {
            "canonical": SKILL_MD.read_text(encoding="utf-8"),
            "codex": CODEX_SKILL_MD.read_text(encoding="utf-8"),
        }

    def test_argument_placeholder_is_literal_data_not_shell_input(self) -> None:
        for label, skill in self.skills.items():
            with self.subTest(host=label):
                self.assertEqual(_extract_work_argument_block(skill), "$ARGUMENTS")
                autonomy = skill.split(
                    "## Autonomous Mode (questions off, no receipt obligations)", 1
                )[1].split("## Input", 1)[0]
                self.assertNotIn("for ARG in $ARGUMENTS", autonomy)
                self.assertIn("literal prompt data", autonomy)
                self.assertIn("never shell", autonomy)
                self.assertIn("preserve\nall else verbatim", autonomy)
                self.assertIn("spaces/quotes/globs", autonomy)

    def test_glob_and_spaces_survive_host_substitution_and_strip(self) -> None:
        cases = (
            (
                "handle *.md files mode:autonomous",
                1,
                "handle *.md files",
            ),
            (
                '"handle *.md files" mode:autonomous',
                1,
                '"handle *.md files"',
            ),
            (
                "preserve  repeated spaces and [abc]*.md",
                0,
                "preserve  repeated spaces and [abc]*.md",
            ),
            (
                "mode:autonomous handle *.md files",
                1,
                "handle *.md files",
            ),
        )
        for label, skill in self.skills.items():
            for raw, expected_mode, expected_args in cases:
                with self.subTest(host=label, raw=raw):
                    rendered = skill.replace("$ARGUMENTS", raw)
                    self.assertEqual(_extract_work_argument_block(rendered), raw)
                    self.assertEqual(
                        _strip_standalone_autonomous_token(raw),
                        (expected_mode, expected_args),
                    )

    def test_embedded_autonomy_text_is_not_a_mode_token(self) -> None:
        raw = "document mode:autonomous-like behavior in *.md"
        self.assertEqual(_strip_standalone_autonomous_token(raw), (0, raw))


if __name__ == "__main__":
    unittest.main()
