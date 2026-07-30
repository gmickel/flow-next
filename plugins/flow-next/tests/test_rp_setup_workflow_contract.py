"""RP review setup must not borrow summaries from earlier shell blocks."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "flow-next"
WORKFLOWS = (
    "flow-next-impl-review/workflow-rp.md",
    "flow-next-plan-review/workflow-rp.md",
    "flow-next-spec-completion-review/workflow-rp.md",
)


def bash_fences(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)


class RepoPromptSetupWorkflowContractTest(unittest.TestCase):
    def test_setup_fence_owns_substantive_summary_in_canonical_and_codex(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                matching = [
                    fence for fence in bash_fences(path.read_text(encoding="utf-8"))
                    if 'eval "$(' in fence and "rp setup-review" in fence
                ]
                self.assertEqual(len(matching), 1, path)
                fence = matching[0]
                assignment = fence.find('REVIEW_SUMMARY="')
                use = fence.find("--summary \"$REVIEW_SUMMARY\"")
                self.assertGreaterEqual(assignment, 0, path)
                self.assertGreater(use, assignment, path)
                self.assertIn("1-2 sentence", fence, path)


if __name__ == "__main__":
    unittest.main()
