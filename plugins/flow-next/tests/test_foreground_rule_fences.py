"""Foreground-rule fence embedding (fn-110 rider; fn-78 stall-class recurrence).

Every executable review-command fence (codex/copilot/cursor x impl/plan/completion
review) must carry the FOREGROUND RULE comment INSIDE the fence, so the rule lands
in fresh context at the exact invocation moment regardless of how deep the calling
worker's context has decayed. Prose paragraphs above the fence demonstrably do not
survive long runs (fn-110.1 stall, 2026-07-20).

Also pins the inverse boundary: the rp workflow (chat-based, different call shape)
carries no such comment, and worker.md's delegation step keeps its sanctioned
background-launch disambiguation.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLUGIN = REPO / "plugins" / "flow-next"

RULE = "# FOREGROUND RULE: run this as ONE blocking foreground Bash call"
RULE2 = "# NEVER run_in_background + monitor"

# A fence is "review-invoking" when its body launches a backend review command.
INVOKE = re.compile(
    r"(^(FLOW_\w+=\S+ )?\$FLOWCTL (codex|copilot|cursor) "
    r"(impl-review|plan-review|completion-review)\b"
    r"|args=\((codex|copilot|cursor) (impl-review|plan-review|completion-review)\))",
    re.M,
)

CANONICAL_FILES = [
    "skills/flow-next-impl-review/workflow-codex.md",
    "skills/flow-next-impl-review/workflow-copilot.md",
    "skills/flow-next-impl-review/workflow-cursor.md",
    "skills/flow-next-impl-review/workflow-common.md",
    "skills/flow-next-plan-review/SKILL.md",
    "skills/flow-next-plan-review/workflow.md",
    "skills/flow-next-spec-completion-review/workflow-codex.md",
    "skills/flow-next-spec-completion-review/workflow-copilot.md",
    "skills/flow-next-spec-completion-review/workflow-cursor.md",
    "skills/flow-next-spec-completion-review/workflow-common.md",
]


def review_fences(text):
    """Yield code-fence bodies that invoke a backend review command."""
    parts = text.split("```")
    for i in range(1, len(parts), 2):
        if INVOKE.search(parts[i]):
            yield parts[i]


class ForegroundRuleFenceTestCase(unittest.TestCase):
    def test_every_review_fence_carries_the_rule(self):
        for rel in CANONICAL_FILES:
            path = PLUGIN / rel
            self.assertTrue(path.exists(), f"missing canonical file: {rel}")
            text = path.read_text(encoding="utf-8")
            fences = list(review_fences(text))
            self.assertTrue(fences, f"no review-invoking fence found in {rel}")
            for body in fences:
                self.assertIn(RULE, body, f"{rel}: review fence lacks FOREGROUND RULE line")
                self.assertIn(RULE2, body, f"{rel}: review fence lacks the never-background line")

    def test_rule_not_duplicated_within_a_fence(self):
        for rel in CANONICAL_FILES:
            text = (PLUGIN / rel).read_text(encoding="utf-8")
            for body in review_fences(text):
                self.assertEqual(
                    body.count(RULE), 1, f"{rel}: FOREGROUND RULE duplicated inside one fence"
                )

    def test_codex_mirror_carries_the_rule(self):
        mirror = PLUGIN / "codex"
        mirrored = 0
        for rel in CANONICAL_FILES:
            candidates = list(mirror.rglob(Path(rel).name))
            for cand in candidates:
                text = cand.read_text(encoding="utf-8")
                for body in review_fences(text):
                    self.assertIn(RULE, body, f"mirror {cand}: review fence lacks the rule")
                    mirrored += 1
        self.assertGreater(mirrored, 0, "codex mirror has no review fences at all?")

    def test_rp_workflow_untouched(self):
        for rel in [
            "skills/flow-next-impl-review/workflow-rp.md",
            "skills/flow-next-spec-completion-review/workflow-rp.md",
        ]:
            path = PLUGIN / rel
            if path.exists():
                self.assertNotIn(RULE, path.read_text(encoding="utf-8"),
                                 f"{rel}: rp workflow should not carry the CLI foreground comment")

    def test_worker_delegation_disambiguation_present_once(self):
        text = (PLUGIN / "agents" / "worker.md").read_text(encoding="utf-8")
        marker = "DELEGATION-ONLY exception"
        self.assertEqual(text.count(marker), 1, "worker.md delegation disambiguation missing or duplicated")
        # The prose Foreground rule paragraph must also still exist.
        self.assertIn("Foreground rule (do not background the review)", text)


if __name__ == "__main__":
    unittest.main()
