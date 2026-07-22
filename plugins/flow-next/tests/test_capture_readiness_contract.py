"""Regression contract for Capture's target-aware readiness prompt (fn-128)."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CANONICAL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-capture"
MIRROR = REPO_ROOT / "plugins" / "flow-next" / "codex" / "skills" / "flow-next-capture"


def _read(directory: pathlib.Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


class CaptureReadinessContract(unittest.TestCase):
    def test_rewrite_offer_follows_target_state(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertIn(
                    "Rewrite:** offer only when `REWRITE_WAS_READY` is `true`.",
                    workflow,
                )
                self.assertIn(
                    "For a rewrite, an unrelated ready spec never triggers this question.",
                    workflow,
                )
                self.assertIn(
                    '[[ "$REWRITE_WAS_READY" == true ]] && READY_OFFER=true',
                    workflow,
                )

    def test_new_capture_retains_adoption_gate(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertIn(
                    "New capture:** offer only when `READY_ADOPTED >= 1`.",
                    workflow,
                )
                self.assertIn(
                    '[[ "$READY_ADOPTED" =~ ^[0-9]+$ && "$READY_ADOPTED" -ge 1 ]]',
                    workflow,
                )

    def test_tracker_authority_and_copy_contract(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertIn("tracker.readyState", workflow)
                self.assertIn('&& -z "$READY_STATE"', workflow)
                self.assertIn("Pilot or another autonomous driver", workflow)
                self.assertNotIn("after you've read it on disk", workflow)

    def test_option_tokens_reset_and_autofix_invariants(self) -> None:
        for directory in (CANONICAL, MIRROR):
            workflow = _read(directory, "workflow.md")
            with self.subTest(directory=directory):
                self.assertIn("`mark-ready`", workflow)
                self.assertIn("`keep-draft`", workflow)
                self.assertIn('spec unready "$SPEC_ID"', workflow)
                self.assertIn("autofix **never writes readiness**", workflow)


if __name__ == "__main__":
    unittest.main()
