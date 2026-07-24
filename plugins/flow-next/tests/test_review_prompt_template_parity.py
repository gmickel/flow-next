"""Parity guard: review-prompt skill templates ≡ embedded FALLBACK strings (fn-112.3).

Embedded review prompts moved into skill-owned ``references/*.md`` templates.
``flowctl`` still ships byte-identical FALLBACK constants for installs where the
plugin root is unavailable. Edit one, edit the other - this test fails on drift.

Also pins rendered-prompt byte-identity against frozen fixtures for fixed inputs
so template/fallback edits cannot silently change what backends receive.

Run:
    python3 -m unittest plugins.flow-next.tests.test_review_prompt_template_parity -v
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any


def _load_flowctl() -> Any:
    here = Path(__file__).resolve()
    flowctl_path = here.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location(
        "flowctl_review_prompt_parity", flowctl_path
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent  # plugins/flow-next
REPO_ROOT = PLUGIN_DIR.parent.parent
FIXTURES = HERE.parent / "fixtures" / "review_prompts"

# (embedded FALLBACK constant, on-disk template relative to repo root)
PARITY_PAIRS = [
    (
        "IMPL_REVIEW_PROMPT_FALLBACK",
        "plugins/flow-next/skills/flow-next-impl-review/references/impl-review-prompt.md",
    ),
    (
        "STANDALONE_REVIEW_PROMPT_FALLBACK",
        "plugins/flow-next/skills/flow-next-impl-review/references/standalone-review-prompt.md",
    ),
    (
        "PLAN_REVIEW_PROMPT_FALLBACK",
        "plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md",
    ),
    (
        "COMPLETION_REVIEW_PROMPT_FALLBACK",
        "plugins/flow-next/skills/flow-next-spec-completion-review/references/completion-review-prompt.md",
    ),
]

# Fixed inputs used when freezing fixtures/review_prompts/*.txt
_SPEC = "SPEC_BODY_LINE1\nSPEC_BODY_LINE2"
_HINTS = "hint-a\nhint-b"
_DSUM = " 3 files changed, 10 insertions(+), 2 deletions(-)"
_DDIFF = "diff --git a/x.py b/x.py\n+print(1)\n"
_TASKS = "TASK1\nTASK2"
_BASE = "main"
_FOCUS = "auth and sessions"


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


class TestReviewPromptTemplateParity(unittest.TestCase):
    def test_fallbacks_match_template_files(self) -> None:
        for const_name, rel in PARITY_PAIRS:
            with self.subTest(template=rel):
                fallback = getattr(flowctl, const_name)
                path = REPO_ROOT / rel
                self.assertTrue(path.is_file(), f"template missing: {rel}")
                self.assertEqual(
                    _normalize(fallback),
                    _normalize(path.read_text(encoding="utf-8")),
                    f"{const_name} drifted from {rel} - keep FALLBACK byte-identical "
                    f"to the skill template (fn-112.3).",
                )


class TestReviewPromptRenderedFixtures(unittest.TestCase):
    """Rendered prompts must stay byte-identical to pre-extraction fixtures."""

    def _assert_fixture(self, name: str, rendered: str) -> None:
        path = FIXTURES / f"{name}.txt"
        self.assertTrue(path.is_file(), f"fixture missing: {path}")
        self.assertEqual(
            _normalize(rendered),
            _normalize(path.read_text(encoding="utf-8")),
            f"rendered {name} prompt drifted from fixture {path.name}",
        )

    def test_impl_review_prompt(self) -> None:
        self._assert_fixture(
            "impl",
            flowctl.build_review_prompt(
                "impl", _SPEC, _HINTS, diff_summary=_DSUM, diff_content=_DDIFF
            ),
        )

    def test_impl_review_prompt_empty_optionals(self) -> None:
        self._assert_fixture(
            "impl_empty_optional",
            flowctl.build_review_prompt(
                "impl", _SPEC, "", diff_summary="", diff_content=""
            ),
        )

    def test_plan_review_prompt(self) -> None:
        self._assert_fixture(
            "plan",
            flowctl.build_review_prompt(
                "plan", _SPEC, _HINTS, task_specs=_TASKS
            ),
        )

    def test_plan_review_prompt_no_tasks(self) -> None:
        self._assert_fixture(
            "plan_no_tasks",
            flowctl.build_review_prompt("plan", _SPEC, _HINTS),
        )

    def test_standalone_review_prompt(self) -> None:
        self._assert_fixture(
            "standalone",
            flowctl.build_standalone_review_prompt(_BASE, _FOCUS, _DSUM),
        )

    def test_standalone_review_prompt_no_focus(self) -> None:
        self._assert_fixture(
            "standalone_no_focus",
            flowctl.build_standalone_review_prompt(_BASE, None, _DSUM),
        )

    def test_completion_review_prompt(self) -> None:
        self._assert_fixture(
            "completion",
            flowctl.build_completion_review_prompt(_SPEC, _TASKS, _DSUM, _DDIFF),
        )

    def test_completion_review_prompt_no_tasks(self) -> None:
        self._assert_fixture(
            "completion_no_tasks",
            flowctl.build_completion_review_prompt(_SPEC, "", _DSUM, _DDIFF),
        )

    def test_completion_review_prompt_starts_with_terminal_reviewer_override(self) -> None:
        """All subprocess backends share this builder: Codex, Copilot, Cursor."""
        prompt = flowctl.build_completion_review_prompt(
            _SPEC, _TASKS, _DSUM, _DDIFF
        )
        self.assertTrue(prompt.startswith("## TERMINAL REVIEWER ROLE"))
        self.assertIn("not a workflow coordinator", prompt)
        self.assertIn("Do not invoke Flow-Next skills", prompt)
        self.assertIn("`flowctl *-review`", prompt)
        self.assertIn("launch another reviewer", prompt)


if __name__ == "__main__":
    unittest.main()
