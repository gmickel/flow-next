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
    def test_historical_compaction_is_advisory(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertIn(
                    "advisory, not an automatic refusal",
                    workflow,
                )
                self.assertIn(
                    "A historical system-summary block, `[compacted]` marker, or unrelated truncated tool result alone does not make the capture source incomplete.",
                    workflow,
                )
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

    def test_complete_relevant_evidence_proceeds_with_warning(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertIn(
                    "Prior compaction detected; relevant capture evidence remains visible.",
                    workflow,
                )
                self.assertIn(
                    "signals exist but the relevant evidence remains fully visible, proceed",
                    workflow,
                )


if __name__ == "__main__":
    unittest.main()
