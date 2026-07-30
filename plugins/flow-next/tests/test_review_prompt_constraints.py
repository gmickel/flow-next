"""Format-only prompt tightening and no-new-LLM guards for fn-136.4.

The subprocess inventory is deliberately grep-shaped: it counts literal
invocation spellings in ``flowctl.py``. Any new subprocess site, or any new
Codex/Copilot/Cursor execution bridge, must update this explicit inventory and
therefore cannot ride along unnoticed with deterministic review plumbing.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
FLOWCTL_PATH = REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
SPEC = importlib.util.spec_from_file_location("flowctl_prompt_constraints", FLOWCTL_PATH)
assert SPEC and SPEC.loader
FLOWCTL: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOWCTL)

SPEC_BODY = "SPEC_BODY_LINE1\nSPEC_BODY_LINE2"
HINTS = "hint-a\nhint-b"
DIFF_SUMMARY = " 3 files changed, 10 insertions(+), 2 deletions(-)"
DIFF_CONTENT = "diff --git a/x.py b/x.py\n+print(1)\n"
TASKS = "TASK1\nTASK2"


def _output_format(text: str) -> str:
    start = text.index("## Output Format\n")
    offset = start + len("## Output Format\n")
    in_fence = False
    end = -1
    for line in text[offset:].splitlines(keepends=True):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            end = offset
            break
        offset += len(line)
    if end == -1:
        raise AssertionError("Output Format has no following section boundary")
    return text[start:end]


class ReviewPromptConstraintTest(unittest.TestCase):
    def rendered_prompts(self) -> dict[str, str]:
        return {
            "impl": FLOWCTL.build_review_prompt(
                "impl",
                SPEC_BODY,
                HINTS,
                diff_summary=DIFF_SUMMARY,
                diff_content=DIFF_CONTENT,
            ),
            "impl_empty_optional": FLOWCTL.build_review_prompt(
                "impl", SPEC_BODY, "", diff_summary="", diff_content=""
            ),
            "plan": FLOWCTL.build_review_prompt(
                "plan", SPEC_BODY, HINTS, task_specs=TASKS
            ),
            "plan_no_tasks": FLOWCTL.build_review_prompt("plan", SPEC_BODY, HINTS),
            "standalone": FLOWCTL.build_standalone_review_prompt(
                "main", "auth and sessions", DIFF_SUMMARY
            ),
            "standalone_no_focus": FLOWCTL.build_standalone_review_prompt(
                "main", None, DIFF_SUMMARY
            ),
            "completion": FLOWCTL.build_completion_review_prompt(
                SPEC_BODY, TASKS, DIFF_SUMMARY, DIFF_CONTENT
            ),
            "completion_no_tasks": FLOWCTL.build_completion_review_prompt(
                SPEC_BODY, "", DIFF_SUMMARY, DIFF_CONTENT
            ),
        }

    def test_every_assembled_prompt_uses_unambiguous_finding_fields(self) -> None:
        for name, prompt in self.rendered_prompts().items():
            with self.subTest(prompt=name):
                output = _output_format(prompt)
                for marker in (
                    "Severity",
                    "Confidence",
                    "Classification",
                    "File:Line",
                    "R-IDs",
                    "Problem",
                    "Suggestion",
                ):
                    self.assertIn(marker, output)
                self.assertRegex(output, r"File:Line[^\n]*path:line[^\n]*`-`")
                self.assertRegex(output, r"R-IDs[^\n]*\[R1, R2\][^\n]*\[\]")
                self.assertRegex(
                    output,
                    r"Classification[^\n]*introduced[^\n]*pre_existing",
                )

    def test_flowctl_subprocess_and_llm_invocation_inventory_is_frozen(self) -> None:
        source = FLOWCTL_PATH.read_text(encoding="utf-8")
        expected = {
            r"subprocess\.run\(": 43,
            r"subprocess\.Popen\(": 2,
            r"run_codex_exec\(": 2,
            r"run_copilot_exec\(": 2,
            r"run_cursor_exec\(": 2,
        }
        observed = {
            pattern: len(re.findall(pattern, source))
            for pattern in expected
        }
        self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
