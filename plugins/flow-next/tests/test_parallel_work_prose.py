"""fn-118 — prompt-guided parallel planning and work contracts.

Locks the agent-owned behavior on both canonical Claude surfaces and the
generated Codex mirror. This is intentionally prose-level: fn-118 adds no
scheduler, schema, or deterministic path-overlap machinery.
"""

from __future__ import annotations

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

CANONICAL_PLAN = PLUGIN / "skills" / "flow-next-plan" / "steps.md"
MIRROR_PLAN = PLUGIN / "codex" / "skills" / "flow-next-plan" / "steps.md"
CANONICAL_WORK = PLUGIN / "skills" / "flow-next-work" / "phases.md"
MIRROR_WORK = PLUGIN / "codex" / "skills" / "flow-next-work" / "phases.md"
CANONICAL_WORKER = PLUGIN / "agents" / "worker.md"
MIRROR_WORKER = PLUGIN / "codex" / "agents" / "worker.toml"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class ParallelPlanProse(unittest.TestCase):
    def _assert_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        self.assertIn("Expose useful parallelism without harming task quality", text)
        self.assertIn("Avoid", text)
        self.assertIn("unnecessary dependency edges", text)
        self.assertIn("Disjoint file lists are", text)
        self.assertIn("not proof", text)
        self.assertIn("Never split", text)
        self.assertIn("Step 6.1: Derive execution waves", text)
        self.assertIn("Wave 1 (parallel candidates)", text)
        self.assertIn("same wave are **parallel candidates**, not a promise", text)

    def test_canonical(self) -> None:
        self._assert_contract(CANONICAL_PLAN)

    def test_codex_mirror(self) -> None:
        self._assert_contract(MIRROR_PLAN)


class ParallelWorkConductorProse(unittest.TestCase):
    def _assert_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        self.assertIn("inspect the whole ready frontier", text)
        self.assertIn("Never run concurrent writers in one checkout", text)
        self.assertIn("Selected wave:", text)
        self.assertIn("Isolation:", text)
        self.assertIn("Dispatch count:", text)
        self.assertIn("Sequential fallback:", text)
        self.assertIn("Claim every selected task before dispatch", text)
        self.assertIn("HANDOVER_SUMMARY", text)
        self.assertIn("HANDOVER_EVIDENCE", text)
        self.assertIn("wait for every dispatched worker", text)
        self.assertIn("Worker outcomes:", text)
        self.assertIn("Join: complete", text)
        self.assertIn("normalize each task's evidence to the integrated commit IDs", text)
        self.assertRegex(
            text,
            re.compile(
                r"run the\s+existing Phase 5 Verify contract on the integrated target"
            ),
        )
        self.assertRegex(
            text,
            re.compile(
                r"integrated-target verification's exact commands/results"
            ),
        )
        self.assertIn("Do not run plan-sync while any peer worker is active", text)
        self.assertIn("recompute the next ready frontier", text)

    def test_canonical(self) -> None:
        self._assert_contract(CANONICAL_WORK)

    def test_codex_mirror(self) -> None:
        self._assert_contract(MIRROR_WORK)


class ParallelWorkerHandoverProse(unittest.TestCase):
    def _assert_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        self.assertIn("PARALLEL_WAVE", text)
        self.assertIn("isolated mutable workspace", text)
        self.assertIn("task-unique", text)
        self.assertIn("HANDOVER_SUMMARY", text)
        self.assertIn("HANDOVER_EVIDENCE", text)
        self.assertIn("DO NOT run `flowctl done`", text)
        self.assertIn("invoke impl-review", text)
        self.assertIn("mutate tracker state", text)
        self.assertIn("invoke plan-sync", text)
        self.assertIn("integrate the", text)
        self.assertRegex(
            text,
            re.compile(
                r'Complete the task only on the standard branch'
                r'.{0,500}?SUMMARY_FILE="/tmp/summary\.md"'
                r'.{0,200}?EVIDENCE_FILE="/tmp/evidence\.json"'
                r'.{0,300}?--summary-file "\$SUMMARY_FILE"'
                r' --evidence-json "\$EVIDENCE_FILE"',
                re.DOTALL,
            ),
        )

    def test_canonical(self) -> None:
        self._assert_contract(CANONICAL_WORKER)

    def test_codex_mirror(self) -> None:
        self._assert_contract(MIRROR_WORKER)


if __name__ == "__main__":
    unittest.main()
