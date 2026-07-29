"""Mechanical guards for the tracker-sync prose teardown."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TRACKER_SKILL = REPO_ROOT / "plugins/flow-next/skills/flow-next-tracker-sync"

# Explicit inventory. These are the canonical files that formerly duplicated
# executable provider calls. Add a new adapter document here before it ships.
PROSE_INVENTORY = (
    "SKILL.md",
    "steps.md",
    "references/adapter-interface.md",
    "references/linear-ladder.md",
    "references/linear-mcp.md",
    "references/linear-graphql.md",
    "references/github.md",
    "references/gitlab.md",
    "references/jira.md",
)

# Character count at 410756ef, after fn-140 and before this teardown.
PRE_TEARDOWN_CHARACTERS = 370_620
MINIMUM_REDUCTION = 150_000

BASH_FENCE = re.compile(r"^```(?:bash|sh|shell)\s*$\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
EXECUTABLE_INVOCATION = re.compile(
    r"(?:\bgh\s+api\b|\bglab\s+api\b|\bcurl\s+-sS\b|\bPOST\s+/rest/api\b)"
)


class TrackerSyncProseTeardownTests(unittest.TestCase):
    def _texts(self) -> dict[str, str]:
        return {
            relative: (TRACKER_SKILL / relative).read_text(encoding="utf-8")
            for relative in PROSE_INVENTORY
        }

    def test_inventory_exists_and_is_unique(self) -> None:
        self.assertEqual(len(PROSE_INVENTORY), len(set(PROSE_INVENTORY)))
        missing = [
            relative for relative in PROSE_INVENTORY
            if not (TRACKER_SKILL / relative).is_file()
        ]
        self.assertEqual(missing, [])

    def test_no_executable_provider_invocations_in_shell_fences(self) -> None:
        matches: list[str] = []
        for relative, text in self._texts().items():
            for fence_number, fence in enumerate(BASH_FENCE.findall(text), start=1):
                for match in EXECUTABLE_INVOCATION.finditer(fence):
                    matches.append(
                        f"{relative}:shell-fence-{fence_number}:{match.group(0)}"
                    )
        self.assertEqual(matches, [])

    def test_reduction_is_at_least_150000_characters(self) -> None:
        current = sum(len(text) for text in self._texts().values())
        reduction = PRE_TEARDOWN_CHARACTERS - current
        self.assertGreaterEqual(
            reduction,
            MINIMUM_REDUCTION,
            f"tracker prose reduction {reduction:,} is below {MINIMUM_REDUCTION:,}; "
            f"baseline={PRE_TEARDOWN_CHARACTERS:,}, current={current:,}",
        )

    def test_skill_names_exactly_five_judgment_surfaces(self) -> None:
        text = self._texts()["SKILL.md"]
        section = text.split("## Exactly five judgment surfaces\n", 1)[1]
        section = section.split("\n## ", 1)[0]
        entries = re.findall(
            r"^\d+\. \*\*(.+?)\.\*\* (.*?)(?=^\d+\. \*\*|\Z)",
            section,
            re.MULTILINE | re.DOTALL,
        )
        self.assertEqual(len(entries), 5)
        self.assertEqual(
            [name for name, _ in entries],
            [
                "MCP rung",
                "Discovery ceremony",
                "Body-merge conflict adjudication",
                "Comment content synthesis",
                "Recovery routing from a structured error",
            ],
        )
        for name, rationale in entries:
            self.assertGreater(
                len(rationale.strip()),
                40,
                f"{name} must carry a rationale",
            )
        self.assertIn("three-way body conflict is semantic", section)


if __name__ == "__main__":
    unittest.main()
