"""Task-management skill (`skills/flow-next/SKILL.md`) handover contract.

Concurrent sessions sharing a fixed `/tmp/summary.md` overwrite each other's
`done` inputs; the skill's example uses per-task temp paths instead.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_task_skill_contract -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "skills" / "flow-next" / "SKILL.md"


class DoneHandoverPaths(unittest.TestCase):
    def test_done_files_are_task_unique(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        done = re.search(r"^\$FLOWCTL done (\S+) .*$", text, re.M)
        self.assertIsNotNone(done)
        task_id = done.group(1)
        for flag in ("--summary-file", "--evidence-json"):
            with self.subTest(flag=flag):
                path = re.search(rf'{flag} "?([^"\s]+)', done.group(0)).group(1)
                self.assertIn(task_id, path)


if __name__ == "__main__":
    unittest.main()
