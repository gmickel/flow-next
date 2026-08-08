"""fn-118 — prompt-guided parallel planning and work contracts.

Locks contract tokens, handover grammar, and mirror parity on both canonical
Claude surfaces and the generated Codex mirror. fn-118 adds no scheduler,
schema, or deterministic path-overlap machinery.

Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md G1, not grep.
"""

from __future__ import annotations

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

CANONICAL_PLAN = PLUGIN / "skills" / "flow-next-plan" / "steps.md"
MIRROR_PLAN = PLUGIN / "codex" / "skills" / "flow-next-plan" / "steps.md"
CANONICAL_WORK = PLUGIN / "skills" / "flow-next-work" / "phases.md"
MIRROR_WORK = PLUGIN / "codex" / "skills" / "flow-next-work" / "phases.md"
# Branch-disclosure refactor: the wave join/handover-consumption prose moved
# verbatim out of the always-loaded phases.md into the reached-path reference
# phases.md links from its parallel-wave branch. Same contract, new home.
CANONICAL_WAVE_JOIN = (
    PLUGIN / "skills" / "flow-next-work" / "references" / "wave-join.md"
)
MIRROR_WAVE_JOIN = (
    PLUGIN
    / "codex"
    / "skills"
    / "flow-next-work"
    / "references"
    / "wave-join.md"
)
CANONICAL_WORKER = PLUGIN / "agents" / "worker.md"
MIRROR_WORKER = PLUGIN / "codex" / "agents" / "worker.toml"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class ParallelPlanProse(unittest.TestCase):
    def _assert_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Structural tokens only below.
        self.assertIn("Step 6.1: Derive execution waves", text)
        self.assertIn("Wave 1 (parallel candidates)", text)

    def test_canonical(self) -> None:
        self._assert_contract(CANONICAL_PLAN)

    def test_codex_mirror(self) -> None:
        self._assert_contract(MIRROR_PLAN)


class ParallelWorkConductorProse(unittest.TestCase):
    def _assert_contract(self, path: pathlib.Path, join: pathlib.Path) -> None:
        text = _read(path)
        join_text = _read(join)
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Handover field labels + grammar tokens only below.
        # Dispatch-side labels stay on the always-loaded conductor path.
        self.assertIn("Selected wave:", text)
        self.assertIn("Isolation:", text)
        self.assertIn("Dispatch count:", text)
        self.assertIn("Sequential fallback:", text)
        self.assertIn("HANDOVER_SUMMARY", text)
        self.assertIn("HANDOVER_EVIDENCE", text)
        # The parallel branch must name the reached-path join reference…
        self.assertIn("references/wave-join.md", text)
        # …which owns the join/outcome grammar.
        self.assertIn("Worker outcomes:", join_text)
        self.assertIn("Join: complete", join_text)
        self.assertIn("HANDOVER_SUMMARY", join_text)
        self.assertIn("HANDOVER_EVIDENCE", join_text)

    def test_canonical(self) -> None:
        self._assert_contract(CANONICAL_WORK, CANONICAL_WAVE_JOIN)
        self.assertIn(
            "/flow-next:impl-review <task-id> --base "
            "<task-normalized-integrated-base> --review=<backend>",
            _read(CANONICAL_WAVE_JOIN),
        )

    def test_codex_mirror(self) -> None:
        self._assert_contract(MIRROR_WORK, MIRROR_WAVE_JOIN)
        text = _read(MIRROR_WAVE_JOIN)
        self.assertIn(
            "$flow-next-impl-review <task-id> --base "
            "<task-normalized-integrated-base> --review=<backend>",
            text,
        )
        self.assertNotIn(
            "/flow-next:impl-review <task-id> --base "
            "<task-normalized-integrated-base> --review=<backend>",
            text,
        )


class ParallelWorkerHandoverProse(unittest.TestCase):
    def _assert_contract(self, path: pathlib.Path) -> None:
        text = _read(path)
        # Prose-quality pins removed 2026-08-07 - judged via .flow/criteria.md
        # G1, not grep. Tokens, executable fragments, and ordering only below.
        self.assertIn("PARALLEL_WAVE", text)
        self.assertIn("task-unique", text)
        self.assertIn("HANDOVER_SUMMARY", text)
        self.assertIn("HANDOVER_EVIDENCE", text)
        self.assertIn("Phase 0: Enter the assigned workspace (FIRST)", text)
        self.assertIn('EXPECTED_WORKSPACE="$(cd -- "<WORKSPACE>" && pwd -P)"', text)
        workspace_pos = text.index("Phase 0: Enter the assigned workspace (FIRST)")
        anchor_pos = text.index("<FLOWCTL> anchor <TASK_ID> --md")
        self.assertLess(workspace_pos, anchor_pos)
        # Parallel-wave terminal guard: worker never completes the task itself.
        self.assertIn("DO NOT run `flowctl done`", text)
        self.assertIn("`in_progress`", text)
        # Standard-branch completion keeps its executable evidence fragments.
        self.assertIn('SUMMARY_FILE="/tmp/summary.md"', text)
        self.assertIn('EVIDENCE_FILE="/tmp/evidence.json"', text)
        self.assertIn(
            '--summary-file "$SUMMARY_FILE" --evidence-json "$EVIDENCE_FILE"', text
        )

    def test_canonical(self) -> None:
        self._assert_contract(CANONICAL_WORKER)

    def test_codex_mirror(self) -> None:
        self._assert_contract(MIRROR_WORKER)


if __name__ == "__main__":
    unittest.main()
