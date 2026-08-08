"""Regression contract for Capture's target-aware readiness prompt (fn-128)."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CANONICAL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-capture"
MIRROR = REPO_ROOT / "plugins" / "flow-next" / "codex" / "skills" / "flow-next-capture"


def _read(directory: pathlib.Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


def _ref(directory: pathlib.Path, name: str) -> str:
    return (directory / "references" / name).read_text(encoding="utf-8")


# Branch-disclosure (fn-169) moved the readiness machinery out of workflow.md
# into the references its §5.9 / rewrite gates load. Substance is asserted
# against those references; workflow.md is asserted to still route to them.
MARK_READY_LINK = "[references/mark-ready.md](references/mark-ready.md)"


class CaptureReadinessContract(unittest.TestCase):
    # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md G1,
    # not grep. What remains: executable bash gates, option/field tokens, and
    # the autofix never-writes-readiness guard.

    def test_rewrite_offer_follows_target_state(self) -> None:
        for directory in (CANONICAL, MIRROR):
            with self.subTest(directory=directory):
                self.assertIn(
                    '[[ "$REWRITE_WAS_READY" == true ]] && READY_OFFER=true',
                    _ref(directory, "mark-ready.md"),
                )
                self.assertIn(MARK_READY_LINK, _read(directory, "workflow.md"))

    def test_new_capture_retains_adoption_gate(self) -> None:
        for directory in (CANONICAL, MIRROR):
            with self.subTest(directory=directory):
                self.assertIn(
                    '[[ "$READY_ADOPTED" =~ ^[0-9]+$ && "$READY_ADOPTED" -ge 1 ]]',
                    _ref(directory, "mark-ready.md"),
                )
                self.assertIn(MARK_READY_LINK, _read(directory, "workflow.md"))

    def test_tracker_authority_gate(self) -> None:
        for directory in (CANONICAL, MIRROR):
            with self.subTest(directory=directory):
                mark_ready = _ref(directory, "mark-ready.md")
                self.assertIn("tracker.readyState", mark_ready)
                self.assertIn('&& -z "$READY_STATE"', mark_ready)
                # Spine keeps the tracker-authority branch visible: when the
                # gate is silent because tracker.readyState is configured, no
                # readiness question is ever offered.
                self.assertIn("tracker.readyState", _read(directory, "workflow.md"))

    def test_option_tokens_reset_and_autofix_invariants(self) -> None:
        for directory in (CANONICAL, MIRROR):
            with self.subTest(directory=directory):
                mark_ready = _ref(directory, "mark-ready.md")
                self.assertIn("`mark-ready`", mark_ready)
                self.assertIn("`keep-draft`", mark_ready)
                self.assertIn("never writes readiness", mark_ready)
                # Autofix never writes readiness either.
                self.assertIn(
                    "never writes readiness", _ref(directory, "autofix-mode.md")
                )
                # The rewrite branch's idempotent readiness reset.
                self.assertIn(
                    'spec unready "$SPEC_ID"', _ref(directory, "rewrite-mode.md")
                )
                workflow = _read(directory, "workflow.md")
                self.assertIn("`mark-ready`", workflow)
                self.assertIn("references/rewrite-mode.md", workflow)


if __name__ == "__main__":
    unittest.main()
