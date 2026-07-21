"""fn-99 R10 token-budget tripwires.

Budgets measure SIZE ONLY at chars/4 token-equivalent. Future editors: do NOT add
forbidden-token greps here, because a grep for a banned token matches the
prohibition prose that bans it (repo memory: final-gate grep lesson).

Spec `fn-99-setup-block-diet-evidence-schema-inline` and the eval at
`agent_docs/guidance-eval/` (memory note `usage-md-guidance-eval-2026-07-15`)
show that the always-loaded block earns its budget only with the inline evidence
schema; `usage.md` is on-demand and buys efficiency, not correctness. Budgets
sit above targets (250 block / ~2.5k usage) to allow drift headroom while
catching regrowth.
"""

from __future__ import annotations

import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
TESTS_DIR = HERE.parent
PLUGIN_DIR = TESTS_DIR.parent
TEMPLATES = PLUGIN_DIR / "skills" / "flow-next-setup" / "templates"
# fn-121: canonical usage.md moved next to spec.md; setup snippets stay in the skill dir.
PLUGIN_TEMPLATES = PLUGIN_DIR / "templates"

BLOCK_BUDGET_TOKENS = 300
USAGE_BUDGET_TOKENS = 2800
CHARS_PER_TOKEN = 4


def _token_equiv(path: Path) -> float:
    """Return the normalized character-count token equivalent for a file."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return len(text) / CHARS_PER_TOKEN


class TokenBudgetTest(unittest.TestCase):
    def test_setup_snippets_stay_within_block_budget(self) -> None:
        for name in ("claude-md-snippet.md", "agents-md-snippet.md"):
            with self.subTest(template=name):
                self.assertLessEqual(
                    _token_equiv(TEMPLATES / name),
                    BLOCK_BUDGET_TOKENS,
                    f"{name} exceeds the fn-99 block budget; see agent_docs/guidance-eval/README.md.",
                )

    def test_usage_template_stays_within_usage_budget(self) -> None:
        path = PLUGIN_TEMPLATES / "usage.md"
        self.assertLessEqual(
            _token_equiv(path),
            USAGE_BUDGET_TOKENS,
            "usage.md exceeds the fn-99 usage budget; see agent_docs/guidance-eval/README.md.",
        )


if __name__ == "__main__":
    unittest.main()
