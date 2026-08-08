"""Live routing/reference contracts for Work's delegation-only extraction (fn-130.8)."""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-work"


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


class WorkReachedPathRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = _text(WORK / "SKILL.md")
        cls.phases = _text(WORK / "phases.md")
        cls.selection = _text(
            WORK / "references" / "codex-delegation-selection.md"
        )
        cls.delegation = _text(WORK / "references" / "codex-delegation.md")
        # Branch-disclosure refactor: the parallel-wave join contract moved
        # verbatim out of the always-loaded phases.md into this reached-path
        # reference, linked from phases.md's parallel-wave branch.
        cls.wave_join = _text(WORK / "references" / "wave-join.md")

    # Evidence-ledger archaeology removed 2026-08-07 - shipped optimizations are
    # history, not invariants. (Lineage baseline-commit pin and the stored
    # route-matrix shape checks deleted; live skill-file contracts remain.)

    def test_requested_path_loads_exact_selection_before_active_reference(self) -> None:
        self.assertNotIn("STOP and read", self.phases)
        self.assertIn(
            "execute its exact ordered gates, consent ceremony, clean-tree\n"
            "check, and terminal routing, then continue with Phase 2",
            self.phases,
        )
        self.assertIn("codex-delegation-selection.md", self.phases)
        for contract in (
            "platform_gate_ok()",
            "not_inside_codex_sandbox()",
            "codex_available()",
            "work.delegateConsent",
            "work.delegateSandbox",
            "INPUT_WAS_BARE_PROMPT",
            "git status --porcelain",
            "delegation_active=true",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.selection)
        self.assertLess(
            self.phases.index("codex-delegation-selection.md"),
            self.phases.index("Only a passing selection loads"),
        )

    def test_selected_reference_retains_path_handoff_and_safety_rails(self) -> None:
        for contract in (
            "exactly **3 slots**",
            "the task file IS the brief",
            "Do NOT `git commit`",
            "Git ownership",
            "non-scratch `.flow/` integrity",
            "scoped rollback",
            "Host circuit breaker",
            "Autonomous-safe",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.delegation)
        self.assertNotIn("<patterns>", self.delegation)
        self.assertNotIn("<approach>", self.delegation)

    def test_autonomous_consent_routes_cover_the_full_marker_family(self) -> None:
        for source in (self.selection, self.delegation):
            for marker in (
                'FLOW_RALPH:-}" = "1"',
                "REVIEW_RECEIPT_PATH:-",
                'FLOW_AUTONOMOUS:-}" = "1"',
                'AUTONOMOUS:-}" = "1"',
                "mode:autonomous",
            ):
                with self.subTest(source=source[:20], marker=marker):
                    self.assertIn(marker, source)
            self.assertIn("delegation_headless", source)
            self.assertIn("standard Work", source)
            self.assertRegex(source, r"no config write|Do not write")

    def test_common_work_lifecycle_and_no_forbidden_gate_regrowth(self) -> None:
        for contract in (
            "inspect the whole ready frontier",
            "Never run concurrent writers in one checkout",
            "host-deferred",
            "Do not run plan-sync while any peer worker is active",
            "Tracker sync:",
            # phases.md must still route to the join reference it hands off to.
            "references/wave-join.md",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.phases)
        for contract in (
            "wait for every dispatched worker",
            "Use the host's chosen integration mechanism",
        ):
            with self.subTest(contract=contract, file="references/wave-join.md"):
                self.assertIn(contract, self.wave_join)
        self.assertNotIn("plan-sync-probe", self.phases)
        self.assertNotIn("PLAN_DEVIATION", self.phases)


if __name__ == "__main__":
    unittest.main()
