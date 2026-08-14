"""Live routing/reference contracts for Work's reached-path extraction (fn-130.8).

The delegation-route contracts retired with the packaged codex-delegation
subsystem (flow-98); the common work lifecycle + wave-join contracts remain.
"""

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
        # Branch-disclosure refactor: the parallel-wave join contract moved
        # verbatim out of the always-loaded phases.md into this reached-path
        # reference, linked from phases.md's parallel-wave branch.
        cls.wave_join = _text(WORK / "references" / "wave-join.md")

    # Evidence-ledger archaeology removed 2026-08-07 - shipped optimizations are
    # history, not invariants. (Lineage baseline-commit pin and the stored
    # route-matrix shape checks deleted; live skill-file contracts remain.)

    def test_no_delegation_route_regrowth(self) -> None:
        """flow-98: the packaged delegation path is deleted, not deprecated."""
        for name, text in (("SKILL.md", self.skill), ("phases.md", self.phases)):
            with self.subTest(file=name):
                self.assertNotIn("delegate:codex", text)
                self.assertNotIn("codex-delegation", text)
                self.assertNotIn("work.delegate", text)
        for stale in ("codex-delegation.md", "codex-delegation-selection.md"):
            with self.subTest(reference=stale):
                self.assertFalse((WORK / "references" / stale).exists())

    def test_common_work_lifecycle_and_no_forbidden_gate_regrowth(self) -> None:
        for contract in (
            "inspect the whole ready frontier",
            "Never run concurrent writers in one checkout",
            "host-deferred",
            "Do not run plan-sync while any peer worker is active",
            "Tracker sync:",
            # Executable handoff + pointer-shaped worker return (n13 doctrine).
            "Next: /flow-next:make-pr <spec-id>",
            "Content lives in those files",
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
