"""fn-215 fan-out prose-contract pins (completion review R8/R15).

Grep-shaped assertions on the load-bearing decision tokens of the fan-out
workflow surfaces — steering phrasings, the merge/Act-On contract, the
one-increment/three-draws/one-record host shape, and the sequential-fallback
degradation disclosure. Tokens, not sentence freezes (2026-08-07 rule);
prose quality is judged via .flow/criteria.md, not grep. Canonical files and
the generated Codex mirror are both pinned (content + reachability).
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
    """workflow-codex.md: steering phrasings + merge/Act-On/finalize contract."""

    def _texts(self) -> list[str]:
        return [
            _read(CANONICAL / "workflow-codex.md"),
            _read(MIRROR / "workflow-codex.md"),
        ]

    def test_steering_phrasings_present(self) -> None:
        for text in self._texts():
            self.assertIn("use 1 reviewer instead of 3", text)
            self.assertIn(
                "use three different model families for the review fan-out",
                text,
            )

    def test_merge_and_act_on_contract(self) -> None:
        for text in self._texts():
            self.assertIn("Same-defect dedupe", text)
            self.assertIn("Act-On tier capped at 5", text)
            self.assertIn("impl-review-fanout-finalize", text)

    def test_needs_work_survivors_documented(self) -> None:
        for text in self._texts():
            self.assertIn("--needs-work-survivors", text)


class HostWorkflowFanoutContract(unittest.TestCase):
    """workflow-host.md: one increment / three draws / one record, plus the
    sequential-fallback degradation disclosure (fn-215 R1 narrowing)."""

    def _texts(self) -> list[str]:
        return [
            _read(CANONICAL / "workflow-host.md"),
            _read(MIRROR / "workflow-host.md"),
        ]

    def test_one_increment_one_record(self) -> None:
        for text in self._texts():
            self.assertIn(
                "ONE `review-rounds increment` before the dispatch", text
            )
            self.assertIn("never three cap slots per merged round", text)

    def test_three_draws_one_message(self) -> None:
        for text in self._texts():
            self.assertIn("three axis draws in ONE message", text)

    def test_sequential_fallback_reports_degradation(self) -> None:
        for text in self._texts():
            self.assertIn("report the degradation in the review record", text)


if __name__ == "__main__":
    unittest.main()
