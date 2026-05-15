"""Unit tests for /flow-next:capture biz-context routing + sparse-layer
suggestion (fn-44.9, covers R24, R25).

Capture's runtime routing is host-agent-driven (skill-vs-flowctl architectural
rule from CLAUDE.md) — there is no `capture_route()` helper to drive. The
tests cover the contract:

  - Skill content: `workflow.md` documents the 9-row signal-category routing
    table with the exact destinations from R24, the `1 <= count < 3`
    threshold rule, and the no-fire-at-zero rule (R22 invariant). The
    threshold + no-fire-at-zero may live in §2.6 (routing prose) OR Phase 6
    (Biz-suggestion footer); the contract is "documented somewhere in
    workflow.md," scanned whole-file.

  - Runtime threshold: `flowctl scope suggest` returns the expected
    fire/no-fire decision for N ∈ {0, 1, 2, 3, 5}. Both plain-mode
    exit-code semantics (0=fire, 1=no-fire — what SKILL.md branches on)
    and JSON-mode 0-exit-regardless semantics are covered.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
CAPTURE_DIR = PLUGIN_DIR / "skills" / "flow-next-capture"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


# Nine R24 signal categories with their canonical markdown destinations. The
# table-of-record lives in capture's workflow.md §2.6 — tests compare against
# this list to detect drift.
SIGNAL_CATEGORIES = [
    # (category_label, destination_keyword)
    ("Target user", "Goal & Context"),
    ("Problem framing", "Goal & Context"),
    ("Success metric", "outcome-AC"),
    ("MVP", "Boundaries"),
    ("Business constraints", "Goal & Context"),  # OR Decision Context > Motivation
    ("NOT to build", "Boundaries"),
    ("Prioritization", "Decision Context"),
    ("Business risks", "Goal & Context"),  # OR Decision Context > Motivation
    ("UX expectations", "Goal & Context"),
]


class TestCaptureWorkflowDocumentsRoutingTable(unittest.TestCase):
    """R24: workflow.md §2.6 (or equivalent) documents all 9 signal
    categories with their R24 destinations."""

    def setUp(self) -> None:
        self.workflow_path = CAPTURE_DIR / "workflow.md"
        self.body = self.workflow_path.read_text(encoding="utf-8")

    def test_nine_signal_categories_named(self) -> None:
        """All 9 R24 category labels appear in workflow.md (in the routing
        table or its surrounding prose)."""
        # Aliases that the workflow legitimately uses for category labels.
        aliases = {
            "Target user": ["target user", "Target user"],
            "Problem framing": ["problem framing"],
            "Success metric": [
                "success metric",
                "success metrics",
                "definition of done",
            ],
            "MVP": ["MVP", "mvp"],
            "Business constraints": ["business constraint", "Business constraints"],
            "NOT to build": [
                "what NOT to build",
                "non-goals",
                "What NOT to Build",
            ],
            "Prioritization": ["prioritization", "Prioritization"],
            "Business risks": ["business risk", "Business risks"],
            "UX expectations": ["UX", "ux expectations"],
        }
        for category, aliases_for in aliases.items():
            found = any(alias.lower() in self.body.lower() for alias in aliases_for)
            self.assertTrue(found, f"category {category!r} not named in workflow.md")

    def test_routing_destinations_named(self) -> None:
        """R24 destinations — Goal & Context / Boundaries / outcome-AC /
        Decision Context > Motivation — all appear in the routing prose."""
        for dest in (
            "Goal & Context",
            "Boundaries",
            "outcome-AC",
            "Decision Context",
            "Motivation",
        ):
            self.assertIn(dest, self.body, f"destination {dest!r} missing")

    def test_threshold_rule_documented(self) -> None:
        """R25 threshold `1 <= count < 3` must be stated explicitly somewhere
        in workflow.md (§2.6 OR Phase 6 footer — per plan-sync breadcrumb)."""
        # Accept several equivalent ways to state the threshold.
        threshold_patterns = [
            r"1\s*<=?\s*N\s*<\s*3",
            r"1\s*<=?\s*count\s*<\s*3",
            r"at least one .*\bfewer than three",
            r"BIZ_SIGNAL_CATEGORIES\s*=\s*[12]",
        ]
        matched = any(
            re.search(p, self.body, re.IGNORECASE) for p in threshold_patterns
        )
        self.assertTrue(
            matched,
            "workflow.md must document the `1 <= N < 3` threshold somewhere",
        )

    def test_no_fire_at_zero_rule_documented(self) -> None:
        """R22 invariant: BIZ_SIGNAL_CATEGORIES=0 → no-fire. Workflow.md must
        state this somewhere (Phase 6 footer or §2.6 routing prose)."""
        zero_rules = [
            r"BIZ_SIGNAL_CATEGORIES\s*=\s*0.*no.fire",
            r"BIZ_SIGNAL_CATEGORIES=0.*no.fire",
            r"zero biz signals.*silent",
            r"never mentioned biz context.*zero new prompts",
            r"no-fire \(exit 1\), keeping",
            r"count\s*==\s*0.*no.fire",
        ]
        matched = any(
            re.search(p, self.body, re.IGNORECASE | re.DOTALL) for p in zero_rules
        )
        self.assertTrue(
            matched,
            "workflow.md must document the no-fire-at-zero rule (R22 invariant)",
        )

    def test_suggestion_phrasing_matches_r25(self) -> None:
        """R25 spec verbatim: the suggestion text contains
        `business-requirements signals` + `/flow-next:interview --scope=business`."""
        self.assertIn("business-requirements signals", self.body)
        self.assertIn("/flow-next:interview --scope=business", self.body)


class TestScopeSuggestThresholdPlainMode(unittest.TestCase):
    """R25 threshold runtime: `flowctl scope suggest` plain-mode emits 0=fire,
    1=no-fire — what SKILL.md branches on via `if flowctl scope suggest ...`."""

    def _suggest(self, count: int) -> subprocess.CompletedProcess:
        return _run(
            "scope", "suggest", "--signal-categories-count", str(count)
        )

    def test_count_0_plain_no_fire(self) -> None:
        """R22 invariant: zero biz signals → no-fire (exit 1)."""
        proc = self._suggest(0)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.strip(), "no-fire")

    def test_count_1_plain_fire(self) -> None:
        """Sweet spot: at least one signal → fire (exit 0)."""
        proc = self._suggest(1)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "fire")

    def test_count_2_plain_fire(self) -> None:
        """Sweet spot: two signals → fire (still underspecified)."""
        proc = self._suggest(2)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "fire")

    def test_count_3_plain_no_fire(self) -> None:
        """Biz layer reasonably filled → no-fire."""
        proc = self._suggest(3)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.strip(), "no-fire")

    def test_count_5_plain_no_fire(self) -> None:
        """Well above threshold → no-fire."""
        proc = self._suggest(5)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.strip(), "no-fire")

    def test_count_9_plain_no_fire(self) -> None:
        """All 9 categories filled → no-fire."""
        proc = self._suggest(9)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.strip(), "no-fire")


class TestScopeSuggestThresholdJsonMode(unittest.TestCase):
    """R25 threshold JSON mode: `flowctl scope suggest --json` always exits 0
    on valid input; the decision is in the payload (R25 + fn-44.1 review
    fix — JSON callers don't want exit 1 for valid no-fire)."""

    def _suggest(self, count: int) -> dict:
        proc = _run(
            "scope",
            "suggest",
            "--signal-categories-count",
            str(count),
            "--json",
        )
        return {"_rc": proc.returncode, **json.loads(proc.stdout)}

    def test_count_0_json_no_fire_exits_0(self) -> None:
        result = self._suggest(0)
        self.assertEqual(result["_rc"], 0)
        self.assertFalse(result["fire"])
        self.assertEqual(result["decision"], "no-fire")
        self.assertEqual(result["signal_categories_count"], 0)
        self.assertEqual(result["threshold_min"], 1)
        self.assertEqual(result["threshold_max_exclusive"], 3)

    def test_count_1_json_fire(self) -> None:
        result = self._suggest(1)
        self.assertEqual(result["_rc"], 0)
        self.assertTrue(result["fire"])
        self.assertEqual(result["decision"], "fire")

    def test_count_2_json_fire(self) -> None:
        result = self._suggest(2)
        self.assertEqual(result["_rc"], 0)
        self.assertTrue(result["fire"])

    def test_count_3_json_no_fire_exits_0(self) -> None:
        result = self._suggest(3)
        self.assertEqual(result["_rc"], 0)
        self.assertFalse(result["fire"])
        self.assertEqual(result["decision"], "no-fire")

    def test_negative_count_rejected(self) -> None:
        proc = _run(
            "scope",
            "suggest",
            "--signal-categories-count",
            "-1",
            "--json",
        )
        self.assertNotEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("must be >= 0", payload["error"])


class TestScopeSuggestSkillIntegrationContract(unittest.TestCase):
    """Skill ↔ flowctl coupling: SKILL.md / workflow.md branches on plain-
    mode exit code (`if scope suggest ... >/dev/null; then ... fi`). The
    branching token is the exit code, not the stdout payload."""

    def test_workflow_uses_plain_mode_exit_branch(self) -> None:
        """capture/workflow.md must branch on plain-mode exit (the contract
        flowctl scope suggest provides via 0=fire, 1=no-fire)."""
        workflow = (CAPTURE_DIR / "workflow.md").read_text(encoding="utf-8")
        # SKILL.md form: `if "$FLOWCTL" scope suggest ... >/dev/null; then ...`
        self.assertIn(
            "scope suggest --signal-categories-count",
            workflow,
        )
        self.assertIn(
            ">/dev/null",
            workflow,
            "workflow.md must use plain-mode (quieted) suggest invocation",
        )

    def test_capture_workflow_threshold_lives_in_flowctl_not_skill(self) -> None:
        """CLAUDE.md skill-vs-flowctl rule: threshold math lives in flowctl
        (`1 <= N < 3`), NOT inline-reimplemented in skill prose. The skill
        MAY document the rule for reader context but must not branch on
        an inline-computed threshold."""
        workflow = (CAPTURE_DIR / "workflow.md").read_text(encoding="utf-8")
        # Forbidden pattern: actual conditional branching on the count
        # rather than on scope suggest's exit code.
        forbidden_branches = [
            r"if\s*\[\s*\$BIZ_SIGNAL_CATEGORIES\s*-ge\s*1\s*-a\s*\$BIZ_SIGNAL_CATEGORIES\s*-lt\s*3",
            r"if\s*\[\[\s*\$BIZ_SIGNAL_CATEGORIES\s*-ge\s*1\s*&&\s*\$BIZ_SIGNAL_CATEGORIES\s*-lt\s*3",
        ]
        for pattern in forbidden_branches:
            self.assertIsNone(
                re.search(pattern, workflow),
                f"capture must not branch on inline threshold; flowctl owns "
                f"the rule. Found: {pattern}",
            )


if __name__ == "__main__":
    unittest.main()
