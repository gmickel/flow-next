"""RP workflows keep CE direct review and Classic tab review isolated."""

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
    def test_setup_fence_is_self_contained_and_requests_ce_review(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                matching = [
                    fence for fence in bash_fences(path.read_text(encoding="utf-8"))
                    if "rp setup-review" in fence and "--response-type review" in fence
                ]
                self.assertEqual(len(matching), 1, path)
                fence = matching[0]
                assignment = fence.find('REVIEW_SUMMARY="')
                use = fence.find("--summary \"$REVIEW_SUMMARY\"")
                self.assertGreaterEqual(assignment, 0, path)
                self.assertGreater(use, assignment, path)
                self.assertIn("--response-type review", fence, path)
                self.assertIn("--response-file \"$RESPONSE_FILE\"", fence, path)
                self.assertIn("> \"$SETUP_FILE\"", fence, path)
                self.assertIn('source "$SETUP_FILE"', fence, path)
                self.assertIn("<verdict>", fence, path)

    def test_selection_and_initial_chat_are_classic_only(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                fences = bash_fences(path.read_text(encoding="utf-8"))
                reached = [
                    fence
                    for fence in fences
                    if "rp select-get" in fence
                    or ("rp chat-send" in fence and "--new-chat" in fence)
                ]
                self.assertGreaterEqual(len(reached), 2, path)
                for fence in reached:
                    self.assertIn('RP_MODE" == "classic', fence, path)
                    self.assertIn('source "$SETUP_FILE"', fence, path)

    def test_ce_response_is_recorded_without_an_initial_chat_dispatch(self) -> None:
        for mirror_prefix in ("skills", "codex/skills"):
            for relative in WORKFLOWS:
                path = PLUGIN_ROOT / mirror_prefix / relative
                text = path.read_text(encoding="utf-8")
                self.assertIn('if [[ "$RP_MODE" == "classic" ]]; then', text, path)
                self.assertIn("RP_EXIT=0", text, path)
                self.assertIn("--response-file \"$RESPONSE_FILE\"", text, path)


if __name__ == "__main__":
    unittest.main()
