"""Live routing contract for Make PR's opt-in HTML lens (fn-130.11).

Validates the enabled/off router and the action-site contracts that must not
move with the HTML-only extraction, against the live skill files.
"""

from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / "plugins" / "flow-next" / "skills" / "flow-next-make-pr"
MIRROR = REPO / "plugins" / "flow-next" / "codex" / "skills" / "flow-next-make-pr"


class MakePrReachedPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        cls.workflow = (SKILL / "workflow.md").read_text(encoding="utf-8")
        cls.html = (SKILL / "html-lens.md").read_text(encoding="utf-8")
        cls.create = (SKILL / "create-and-finalize.md").read_text(encoding="utf-8")

    # Evidence-ledger archaeology removed 2026-08-07 - shipped optimizations are
    # history, not invariants. (Candidate-ledger required/forbidden-read and
    # discard-shape checks deleted; live skill-file contracts remain.)

    def test_off_and_dry_run_keep_both_html_references_cold(self) -> None:
        gate = self.workflow.index("HTML_LENS=$(\"$FLOWCTL\" config get")
        route = self.workflow.index("read [html-lens.md](html-lens.md) in full")
        body = self.workflow.index("## Phase 2: Render body header sections")
        self.assertLess(gate, route)
        self.assertLess(route, body)
        self.assertIn('[[ "$DRY_RUN" == "1" ]] && HTML_LENS=false', self.workflow)
        self.assertIn("do not read `html-lens.md`", self.workflow)
        self.assertNotIn("git check-ignore --no-index -q", self.workflow)

    def test_enabled_path_retains_html_safety_contract(self) -> None:
        for needle in (
            "git check-ignore --no-index -q",
            'git add -- "$ARTIFACT_PATH"',
            "git diff --cached --quiet",
            'git commit -m "chore(flow): pr artifact ${SPEC_ID}" -- "$ARTIFACT_PATH"',
            'LENS_OK=false',
            'LINK_MODE=""',
            "Exactly one stderr note total per skipped lens",
            "NO `lavish-axi` session opened",
            "Ralph `PR_URL=<url>` stdout contract",
        ):
            self.assertIn(needle, self.html)
        self.assertIn("[html-lens.md](html-lens.md)", self.root)

    def test_creation_failure_and_autonomous_contracts_stay_at_consumers(self) -> None:
        for needle in (
            "gh pr create",
            "3-attempt retry loop",
            "Manual recovery: wait 30s and re-run /flow-next:make-pr",
            "Eventual-consistency exhaustion",
        ):
            self.assertIn(needle, self.create)
        for needle in (
            "OPEN_COUNT > 0",
            "Ralph/autonomous hard-errors (exit 2)",
            "existing OPEN PR is REQUIRED",
            'select(.state == "OPEN")',
        ):
            self.assertIn(needle, self.workflow)

    # --- fn-180.2 (#301): declared vs evidenced R-ID coverage ---

    def _section(self, text: str, start: str, end: str) -> str:
        """Slice a reached section so a pin proves reachability, not mere presence."""
        head = text.index(start)
        return text[head : text.index(end, head)]

    def test_coverage_abort_is_keyed_on_undeclared_not_uncovered(self) -> None:
        """Contract tokens only (repo rule: no sentence-level prose pins)."""
        aborts = self._section(self.workflow, "### 2.7 — Abort conditions", "### Done when")
        self.assertIn("`tasks_summary.undeclared_r_ids` length", aborts)
        # Distinctive condition token of the abort's stderr contract - the
        # advice wording is free to evolve (no sentence pins).
        self.assertIn("Undeclared R-ID coverage", aborts)
        # The retired condition + its unfollowable advice must not survive anywhere.
        self.assertNotIn("Empty R-ID coverage", self.workflow)
        self.assertNotIn(
            "Every R-ID uncovered (`tasks_summary.uncovered_r_ids` length", self.workflow
        )
        # The abort condition never keys on the evidenced set.
        self.assertNotIn("`tasks_summary.uncovered_r_ids` length == `len(acceptance_criteria)`", aborts)
        # Reachable from the table section too, where the check is described inline.
        table = self._section(
            self.workflow, "### 2.3 — R-ID coverage table", "### 2.3b — Verification"
        )
        self.assertIn("`tasks_summary.undeclared_r_ids` length equals", table)

    def test_claimed_not_evidenced_renders_in_table_and_ratio(self) -> None:
        """Rendered-output literals: table cells, follow-up markers, ratio shape."""
        table = self._section(
            self.workflow, "### 2.3 — R-ID coverage table", "### 2.3b — Verification"
        )
        self.assertIn("| Claimed, not yet evidenced |", table)
        self.assertIn("`⏳ claimed, not yet evidenced`", table)
        self.assertIn("⏳ **<M> criterion(a) claimed but not yet evidenced:**", table)
        # The warning marker stays bound to the undeclared set only.
        self.assertIn("⚠️ **<N> undeclared acceptance criterion(a):**", table)
        self.assertNotIn("⚠️ **<N> uncovered acceptance criterion(a):**", self.workflow)

        summary = self._section(
            self.workflow, "### 2.1 — Title + summary block", "### 2.2 — TL;DR composition"
        )
        self.assertIn(
            "> **R-ID coverage:** <covered>/<total> evidenced"
            "<, <M> claimed not yet evidenced><, <N> undeclared>",
            summary,
        )
        self.assertIn("`len(uncovered_r_ids) - len(undeclared_r_ids)`", summary)

    def test_orphaned_evidence_shas_render_marked_never_linked(self) -> None:
        """fn-180 #302 / PR #327: an orphaned SHA is annotated, not a live link."""
        table = self._section(
            self.workflow, "### 2.3 — R-ID coverage table", "### 2.3b — Verification"
        )
        self.assertIn("(orphaned by a history rewrite)", table)
        self.assertIn("evidence commit <token> is not reachable from HEAD", table)

    def test_artifact_path_keeps_per_criterion_state_visible(self) -> None:
        """PR #327: the legacy coverage table is suppressed only on fully
        evidenced coverage; with any gap it renders beside the artifact."""
        aid = (SKILL / "pr-cognitive-aid.md").read_text(encoding="utf-8")
        self.assertIn("tasks_summary.undeclared_r_ids", aid)
        self.assertIn("`tasks_summary.uncovered_r_ids` is empty", aid)
        order = self._section(
            self.workflow, "### 2.0 — Section order", "### 2.1 — Title + summary block"
        )
        self.assertIn("ONLY when `tasks_summary.uncovered_r_ids` is empty", order)

    def test_codex_mirror_carries_the_coverage_contract(self) -> None:
        mirror_workflow = MIRROR / "workflow.md"
        if not mirror_workflow.exists():
            self.skipTest("Codex mirror regeneration is conductor-owned in parallel wave")
        text = mirror_workflow.read_text(encoding="utf-8")
        self.assertIn("Undeclared R-ID coverage (no task's satisfies frontmatter", text)
        self.assertIn("`⏳ claimed, not yet evidenced`", text)
        self.assertNotIn("Empty R-ID coverage", text)

    def test_codex_mirror_route_when_regenerated(self) -> None:
        """Conductor regenerates the mirror after joining the parallel wave."""
        mirror_html = MIRROR / "html-lens.md"
        if not mirror_html.exists():
            self.skipTest("Codex mirror regeneration is conductor-owned in parallel wave")
        mirror_root = (MIRROR / "SKILL.md").read_text(encoding="utf-8")
        mirror_workflow = (MIRROR / "workflow.md").read_text(encoding="utf-8")
        mirror_lens = mirror_html.read_text(encoding="utf-8")
        self.assertIn("[html-lens.md](html-lens.md)", mirror_root)
        self.assertIn("read [html-lens.md](html-lens.md) in full", mirror_workflow)
        self.assertNotIn("git check-ignore --no-index -q", mirror_workflow)
        self.assertIn("git check-ignore --no-index -q", mirror_lens)


if __name__ == "__main__":
    unittest.main()
