"""Regression contract for capture's relevance-scoped compaction guard (fn-127)."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CANONICAL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-capture"
MIRROR = REPO_ROOT / "plugins" / "flow-next" / "codex" / "skills" / "flow-next-capture"


def _read(directory: pathlib.Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


class CaptureCompactionContract(unittest.TestCase):
    # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md G1,
    # not grep. What remains: the fn-127 fail-closed guard tokens and the
    # negative guard against the old detect-anything-then-refuse behavior.

    def test_historical_compaction_is_not_an_automatic_refusal(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertNotIn(
                    "If any are detected AND `FROM_COMPACTED_OK` is `0`, refuse",
                    workflow,
                )

    def test_incomplete_relevant_evidence_still_fails_closed(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            skill = _read(directory, "SKILL.md")
            phases = _read(directory, "phases.md")
            combined = "\n".join((workflow, skill, phases))
            with self.subTest(directory=directory):
                self.assertIn(
                    "If relevant evidence is incomplete AND `FROM_COMPACTED_OK` is `0`, refuse",
                    workflow,
                )
                self.assertIn("summary-only", combined)
                self.assertIn("--from-compacted-ok", combined)
                self.assertIn("autofix", combined.lower())


if __name__ == "__main__":
    unittest.main()
