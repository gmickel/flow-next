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
