"""Reached-path ratchet for Work's delegation-only extraction (fn-130.8)."""

from __future__ import annotations

import hashlib
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-work"
EVIDENCE = REPO_ROOT / "optimization" / "reached-path" / "work-candidate.json"


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _hash(path: pathlib.Path) -> str:
    return hashlib.sha256(_text(path).encode("utf-8")).hexdigest()


class WorkReachedPathRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.skill = _text(WORK / "SKILL.md")
        cls.phases = _text(WORK / "phases.md")
        cls.selection = _text(
            WORK / "references" / "codex-delegation-selection.md"
        )
        cls.delegation = _text(WORK / "references" / "codex-delegation.md")

    def test_candidate_is_chained_from_b1_only(self) -> None:
        lineage = self.evidence["lineage"]
        self.assertEqual(lineage["baseline"], "B1")
        self.assertEqual(
            lineage["baseline_commit"],
            "8ed71a73ccc593a8a018dcdb805a86f396dcf76f",
        )
        self.assertIn("never B0", lineage["rule"])

    def test_candidate_hashes_match_live_canonical_inputs(self) -> None:
        for relative, expected in self.evidence["prompt_hashes"].items():
            with self.subTest(path=relative):
                self.assertEqual(_hash(REPO_ROOT / relative), expected)

    def test_measured_default_and_active_paths_shrink(self) -> None:
        metrics = self.evidence["metrics"]
        self.assertEqual(
            metrics["algorithm"],
            "lf-full-file-on-activation-once-per-path-hash",
        )
        default_chars = len(self.skill) + len(self.phases)
        active_chars = default_chars + len(self.selection) + len(self.delegation)
        self.assertEqual(
            default_chars, metrics["default_path"]["candidate_reached_path_chars"]
        )
        self.assertEqual(
            active_chars,
            metrics["delegation_active_path"]["candidate_reached_path_chars"],
        )
        for route in ("default_path", "delegation_active_path"):
            row = metrics[route]
            self.assertLess(
                row["candidate_reached_path_chars"],
                row["baseline_reached_path_chars"],
            )
            self.assertGreater(row["reduction_chars"], 0)

    def test_requested_path_loads_exact_selection_before_active_reference(self) -> None:
        self.assertIn("STOP and read", self.phases)
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

    def test_route_matrix_covers_every_frozen_terminal(self) -> None:
        arms = self.evidence["trace_arms"]
        self.assertIn("fixtures/b1/work", arms["baseline"])
        self.assertEqual(arms["candidate"], "route_traces below")
        self.assertEqual(arms["observable_behavior_delta"], [])
        routes = {row["id"]: row for row in self.evidence["route_traces"]}
        required = {
            "serial",
            "parallel-eligible",
            "shared-file-conflict",
            "worker-failure",
            "host-deferred-handover",
            "delegation-off",
            "delegation-declined",
            "delegation-cli-unavailable",
            "delegation-on-consented",
            "delegation-implementation-failure",
            "delegation-circuit-breaker",
            "tracker-inactive",
            "tracker-active",
            "tracker-probe-error",
            "review-pass",
            "review-fail",
            "plan-sync-no-op",
            "plan-sync-update",
            "autonomous-consent-missing",
            "autonomous-consent-granted",
        }
        self.assertEqual(set(routes), required)
        for route in (
            "delegation-off",
            "delegation-declined",
            "delegation-cli-unavailable",
            "autonomous-consent-missing",
        ):
            self.assertFalse(routes[route]["delegation_reference"])
        for route in (
            "delegation-on-consented",
            "delegation-implementation-failure",
            "delegation-circuit-breaker",
            "autonomous-consent-granted",
        ):
            self.assertTrue(routes[route]["delegation_reference"])
        self.assertFalse(routes["tracker-inactive"]["tracker_reference"])
        self.assertTrue(routes["tracker-active"]["tracker_reference"])
        self.assertTrue(routes["tracker-probe-error"]["tracker_reference"])

    def test_selected_reference_retains_path_handoff_and_safety_rails(self) -> None:
        for contract in (
            "exactly **3 slots**",
            "the task file IS the brief",
            "Do NOT `git commit`",
            "Git ownership",
            "non-scratch `.flow/` integrity",
            "scoped rollback",
            "Host circuit breaker",
            "Ralph-safe",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.delegation)
        self.assertNotIn("<patterns>", self.delegation)
        self.assertNotIn("<approach>", self.delegation)

    def test_common_work_lifecycle_and_no_forbidden_gate_regrowth(self) -> None:
        for contract in (
            "inspect the whole ready frontier",
            "Never run concurrent writers in one checkout",
            "wait for every dispatched worker",
            "host-deferred",
            "Use the host's chosen integration mechanism",
            "Do not run plan-sync while any peer worker is active",
            "Tracker sync:",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, self.phases)
        self.assertNotIn("plan-sync-probe", self.phases)
        self.assertNotIn("PLAN_DEVIATION", self.phases)


if __name__ == "__main__":
    unittest.main()
