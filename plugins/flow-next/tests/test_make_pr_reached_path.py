"""Reached-path contract for Make PR's opt-in HTML lens (fn-130.11).

The immutable B1 manifests remain frozen. This suite validates the retained
candidate ledger, exact corpus hashes, enabled/off router, and the action-site
contracts that must not move with the HTML-only extraction.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / "plugins" / "flow-next" / "skills" / "flow-next-make-pr"
MIRROR = REPO / "plugins" / "flow-next" / "codex" / "skills" / "flow-next-make-pr"
SHARED_HTML = "plugins/flow-next/references/html-artifacts.md"
HTML_LENS = "plugins/flow-next/skills/flow-next-make-pr/html-lens.md"
CREATE = "plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md"
LEDGER = REPO / "optimization" / "reached-path" / "make-pr-candidates.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lf_chars(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n"))


class MakePrReachedPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        cls.root = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        cls.workflow = (SKILL / "workflow.md").read_text(encoding="utf-8")
        cls.html = (SKILL / "html-lens.md").read_text(encoding="utf-8")
        cls.create = (SKILL / "create-and-finalize.md").read_text(encoding="utf-8")

    def test_candidate_hashes_and_frozen_corpora_are_exact(self) -> None:
        for relative, expected in self.ledger["candidate_prompt_hashes"].items():
            self.assertEqual(_sha256(REPO / relative), expected, relative)
        for relative, expected in self.ledger["frozen_corpora"].items():
            path = REPO / relative
            json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(_sha256(path), expected, relative)

    def test_non_html_workflow_is_byte_identical_to_b1(self) -> None:
        slices = self.ledger["b1_unchanged_workflow_slices"]
        before, rest = self.workflow.split("## Phase 1.5:", 1)
        _html_phase, after = rest.split("## Phase 2:", 1)
        self.assertEqual(
            hashlib.sha256(before.encode()).hexdigest(),
            slices["before_phase_1_5_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(after.encode()).hexdigest(),
            slices["after_phase_1_5_sha256"],
        )

    def test_off_and_dry_run_keep_both_html_references_cold(self) -> None:
        kept = self.ledger["kept_candidate"]
        for route in ("dry-run", "html-off"):
            forbidden = kept["forbidden_reads"][route]
            self.assertIn(HTML_LENS, forbidden)
            self.assertIn(SHARED_HTML, forbidden)
        self.assertIn(CREATE, kept["forbidden_reads"]["dry-run"])

        gate = self.workflow.index("HTML_LENS=$(\"$FLOWCTL\" config get")
        route = self.workflow.index("read [html-lens.md](html-lens.md) in full")
        body = self.workflow.index("## Phase 2: Render body header sections")
        self.assertLess(gate, route)
        self.assertLess(route, body)
        self.assertIn('[[ "$DRY_RUN" == "1" ]] && HTML_LENS=false', self.workflow)
        self.assertIn("do not read `html-lens.md`", self.workflow)
        self.assertNotIn("git check-ignore --no-index -q", self.workflow)

    def test_enabled_path_retains_html_safety_contract(self) -> None:
        required = self.ledger["kept_candidate"]["required_reads"]["html-on"]
        self.assertIn(HTML_LENS, required)
        self.assertIn(SHARED_HTML, required)
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

    def test_b1_to_candidate_metrics_match_full_file_algorithm(self) -> None:
        sizes = {
            "root": _lf_chars(SKILL / "SKILL.md"),
            "workflow": _lf_chars(SKILL / "workflow.md"),
            "create": _lf_chars(SKILL / "create-and-finalize.md"),
            "mermaid": _lf_chars(SKILL / "mermaid-rules.md"),
            "html_lens": _lf_chars(SKILL / "html-lens.md"),
            "html_ref": _lf_chars(REPO / SHARED_HTML),
        }
        routes = {
            "dry-run": sizes["root"] + sizes["workflow"] + sizes["mermaid"],
            "html-off": sizes["root"] + sizes["workflow"] + sizes["create"] + sizes["mermaid"],
            "html-on": (
                sizes["root"]
                + sizes["workflow"]
                + sizes["create"]
                + sizes["mermaid"]
                + sizes["html_lens"]
                + sizes["html_ref"]
            ),
            "create": sizes["root"] + sizes["workflow"] + sizes["create"] + sizes["mermaid"],
            "finalize": sizes["root"] + sizes["workflow"] + sizes["create"],
            "existing-pr": sizes["root"] + sizes["workflow"] + sizes["create"],
            "push-retry": sizes["root"] + sizes["workflow"] + sizes["create"],
        }
        metrics = self.ledger["kept_candidate"]["route_metrics"]
        for route, observed in routes.items():
            self.assertEqual(metrics[route]["candidate_chars"], observed, route)
            self.assertEqual(
                metrics[route]["delta_chars"],
                observed - metrics[route]["b1_chars"],
                route,
            )
        self.assertLess(metrics["html-off"]["candidate_chars"], metrics["html-off"]["b1_chars"])
        self.assertIsNone(self.ledger["kept_candidate"]["wall_time_claim"])

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

    def test_discard_ledger_is_complete(self) -> None:
        discarded = self.ledger["discarded_candidates"]
        self.assertGreaterEqual(len(discarded), 3)
        for row in discarded:
            self.assertEqual(row["verdict"], "discard")
            self.assertTrue(row["reason"])
        self.assertEqual(
            self.ledger["overlap_recheck"]["spec"],
            "fn-73-glab-git-ops-make-prresolve-prland-over",
        )
        self.assertEqual(self.ledger["overlap_recheck"]["status"], "open")

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
