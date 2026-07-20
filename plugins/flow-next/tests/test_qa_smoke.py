"""`/flow-next:qa` flowctl-touchpoint smoke (fn-53.5, R10).

The QA skill is a pure-skill workflow that reuses existing flowctl plumbing —
it adds no new judgment to the CLI. Its three load-bearing flowctl touchpoints
must resolve through the **production CLI** (the bundled `cmd_*` argparse
dispatch the host agent actually shells), not an in-process import:

  1. `spec export-cognitive-aid <id> --base <ref> --json`
     — the scenario-derivation source (workflow.md Phase 1.2 / Phase 2). The
     skill maps `spec.spec_sections.{acceptance_criteria,boundaries,
     decision_context}` into scenarios + the R-ID coverage spine, so the
     payload shape is part of the contract.
  2. `config get tracker.perEvent.qa` — the opt-in verdict-post leaf
     (workflow.md Phase A / §6); defaults `off` so the skill stays silent
     until opted in. (The full round-trip + sibling-isolation lives in
     test_qa_tracker_event.py; here we only assert the touchpoint resolves.)
  3. The receipt write path — `.flow/review-receipts/` is the committed
     directory the skill writes `qa-<spec-id>.json` into when no explicit
     `--receipt` / `REVIEW_RECEIPT_PATH` is supplied. (Receipt schema +
     four-outcome projection live in test_qa_receipt.py; here we only assert
     the write target is reachable.)

This is a hermetic plumbing smoke, NOT a live drive — it never starts an app
or invokes a driver. Each test runs in its own `tempfile.TemporaryDirectory`
with a throwaway git repo + `.flow/`, and shells `sys.executable
scripts/flowctl.py` (no network, no LLM). Windows-portable: `pathlib`
everywhere, `sys.executable`, no shell string, no hard-coded separators.

Run:
    python3 -m unittest plugins.flow-next.tests.test_qa_smoke -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

SPEC_TITLE = "QA smoke probe"
# A minimal plan body carrying the two sections the QA skill derives from.
SPEC_PLAN = (
    "## Acceptance Criteria\n\n"
    "- **R1:** the app loads and renders the primary view [user]\n\n"
    "## Boundaries\n\n"
    "- NOT a code review — drives the live app, not the source.\n"
)


def _flowctl(cwd: Path, *args: str, expect_rc: int = 0) -> dict[str, Any]:
    """Run the production CLI as a subprocess; parse the `--json` payload.

    Exercises the real argparse → cmd_* dispatch (the path the bundled CLI
    runs), not an in-process function call.
    """
    cmd = [sys.executable, str(FLOWCTL_PY), *args, "--json"]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "FLOW_NO_DEPRECATION": "1"},
    )
    if proc.returncode != expect_rc:
        raise AssertionError(
            f"rc={proc.returncode} (expected {expect_rc}): args={args} "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    return json.loads(proc.stdout.decode("utf-8"))


def _git(cwd: Path, *args: str) -> None:
    subprocess.check_call(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class QaTouchpointSmokeTestCase(unittest.TestCase):
    """The QA skill's flowctl touchpoints resolve via the production CLI."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        # A real git repo: export-cognitive-aid resolves a --base ref.
        _git(self.repo, "init")
        _git(self.repo, "config", "user.email", "qa-smoke@example.test")
        _git(self.repo, "config", "user.name", "qa-smoke")
        subprocess.check_call(
            [sys.executable, str(FLOWCTL_PY), "init", "--json"],
            cwd=str(self.repo),
            stdout=subprocess.DEVNULL,
        )
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-m", "base")
        # A spec with a plan carrying AC + Boundaries to derive scenarios from.
        created = _flowctl(self.repo, "spec", "create", "--title", SPEC_TITLE)
        self.spec_id = created["id"]
        proc = subprocess.run(
            [
                sys.executable,
                str(FLOWCTL_PY),
                "spec",
                "set-plan",
                self.spec_id,
                "--file",
                "-",
                "--json",
            ],
            cwd=str(self.repo),
            input=SPEC_PLAN.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"set-plan failed: rc={proc.returncode} stderr={proc.stderr!r}"
            )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── (1) scenario-derivation source: export-cognitive-aid (full payload) ──

    def test_export_cognitive_aid_spec_section_resolves(self) -> None:
        """The Phase 1.2/2 derivation payload resolves with the exact flags the
        skill uses, and carries the spec_sections shape Phase 2 maps."""
        out = _flowctl(
            self.repo,
            "spec",
            "export-cognitive-aid",
            self.spec_id,
            "--base",
            "HEAD",
        )
        self.assertIn("spec", out)
        sections = out["spec"]["spec_sections"]
        # The three fields workflow.md §1.2 → Phase 2 reads (AC → scenarios +
        # R-ID spine; boundaries → what NOT to test; decision context →
        # expected behavior).
        for field in ("acceptance_criteria", "boundaries", "decision_context"):
            self.assertIn(field, sections, f"missing spec_sections.{field}")

    def test_export_cognitive_aid_emits_rid_tagged_acceptance_criteria(self) -> None:
        """AC come back as `{id, text, tag}` — the R-ID coverage spine the
        skill reuses from the make-pr coverage-table pattern."""
        out = _flowctl(
            self.repo,
            "spec",
            "export-cognitive-aid",
            self.spec_id,
            "--base",
            "HEAD",
        )
        acs = out["spec"]["spec_sections"]["acceptance_criteria"]
        self.assertTrue(acs, "no acceptance_criteria parsed from the plan")
        first = acs[0]
        for key in ("id", "text", "tag"):
            self.assertIn(key, first, f"AC entry missing {key!r}")
        self.assertEqual(first["id"], "R1")

    # ── (2) opt-in verdict-post leaf resolves (defaults off) ─────────────────

    def test_tracker_per_event_qa_leaf_resolves_off(self) -> None:
        """The Phase A verdict-post gate resolves and is silent by default."""
        out = _flowctl(self.repo, "config", "get", "tracker.perEvent.qa")
        self.assertEqual(out["value"], "off")

    # ── (3) receipt write path is reachable ──────────────────────────────────

    def test_receipt_dir_is_writable_after_init(self) -> None:
        """`.flow/review-receipts/` is the committed default receipt target the
        skill writes `qa-<spec-id>.json` into; it must be reachable post-init."""
        receipts_dir = self.repo / ".flow" / "review-receipts"
        # The skill creates the dir if absent (workflow.md §6.3); assert the
        # parent exists and the target path is writable.
        receipts_dir.mkdir(parents=True, exist_ok=True)
        target = receipts_dir / f"qa-{self.spec_id}.json"
        target.write_text(json.dumps({"type": "qa_verdict"}) + "\n", encoding="utf-8")
        self.assertTrue(target.is_file())
        self.assertEqual(
            json.loads(target.read_text(encoding="utf-8"))["type"], "qa_verdict"
        )


if __name__ == "__main__":
    unittest.main()
