"""Prompt/workflow contract for capture chart-briefing handoff (fn-135.3).

Canonical capture skill only (no codex mirror - this task does not sync-codex).
Asserts briefing ingestion, draft/stale refusal + override read-back, provenance
separation, link-spec-after-create ordering, retry-discovers-existing-spec,
and fn-148 non-preemption (no verified/inferred fact grammar).
"""

from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CANONICAL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-capture"


def _read(name: str) -> str:
    return (CANONICAL / name).read_text(encoding="utf-8")


class CaptureChartHandoffContract(unittest.TestCase):
    def test_skill_files_exist(self) -> None:
        for name in ("SKILL.md", "workflow.md", "phases.md"):
            self.assertTrue((CANONICAL / name).is_file(), name)

    def test_briefing_ingestion_prose(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        self.assertIn("Chart briefing ingestion", skill)
        self.assertIn(".flow/charts/*-briefing*.md", skill)
        self.assertIn("0.5b — Chart briefing admission", workflow)
        self.assertIn("1.2b — Chart briefing evidence", workflow)
        self.assertIn("chart id", skill.lower())
        self.assertIn("B-ID", skill)
        self.assertIn("cluster", skill.lower())

    def test_draft_stale_refusal_and_override_readback(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        phases = _read("phases.md")
        for text in (skill, workflow, phases):
            self.assertIn("draft", text.lower())
            self.assertIn("stale", text.lower())
        self.assertIn("REFUSES draft or stale", skill)
        self.assertIn("forced draft", skill.lower())
        self.assertIn("never", skill.lower())
        self.assertIn("promote", skill.lower())
        self.assertIn("read back the exact risk", skill.lower())
        self.assertIn("risk override", workflow.lower())
        self.assertIn("unresolved", workflow.lower())
        self.assertIn("invalidated", workflow.lower())

    def test_provenance_separation(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        phases = _read("phases.md")
        combined = "\n".join([skill, workflow, phases])
        self.assertIn("Provenance separation", skill)
        self.assertIn("Chart provenance separation", workflow)
        self.assertIn("three provenance lanes", phases.lower())
        # D-ID evidence never source-tagged
        self.assertIn("never source-tag", combined.lower())
        self.assertIn("D-ID", combined)
        # Four-tag grammar only on newly authored criteria
        self.assertIn("[user]", combined)
        self.assertIn("[paraphrase]", combined)
        self.assertIn("[inferred]", combined)
        self.assertIn("[strategy:", combined)
        self.assertIn("newly authors", combined.lower())
        self.assertRegex(combined, r"(?i)not\*?\*?\s*automatically")
        self.assertIn("automatically `[user]`", combined)
        self.assertIn("Never retag", combined)

    def test_link_spec_after_create_ordering(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        phases = _read("phases.md")
        self.assertIn("chart link-spec", skill)
        self.assertIn("link-spec", workflow)
        # Order: create -> set-plan -> link-spec
        self.assertIn("spec create", skill.lower())
        self.assertIn("spec set-plan", skill.lower())
        self.assertIn("only after", skill.lower())
        # Explicit ordering in workflow shell block
        self.assertIn('chart link-spec', workflow)
        self.assertIn("set-plan", workflow)
        self.assertIn("Order is load-bearing", workflow)
        self.assertIn("create → set-plan → link-spec", phases)

    def test_retry_discovers_existing_spec(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        self.assertIn("produced_specs", skill)
        self.assertIn("retry", skill.lower())
        self.assertIn("duplicate", skill.lower())
        self.assertIn("B-ID+cluster", skill)
        self.assertIn("produced_specs", workflow)
        self.assertIn("discover", workflow.lower())
        self.assertIn("Partial multi-spec", skill)
        self.assertIn("Decline", skill)
        self.assertIn("resumable", skill.lower())

    def test_fn148_non_preemption(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        phases = _read("phases.md")
        combined = "\n".join([skill, workflow, phases])
        self.assertIn("fn-148", combined)
        self.assertIn("STOPPED", combined)
        # Bracket tag form is only allowed as a prohibition (fn-148 non-preemption).
        for m in re.finditer(r"\[verified\]", combined):
            start = max(0, m.start() - 50)
            end = min(len(combined), m.end() + 30)
            window = combined[start:end].lower()
            self.assertTrue(
                "no" in window or "not" in window or "nothing" in window,
                f"[verified] must appear only as a prohibition: {window!r}",
            )
        # Chart-scoped prose must reject verified/inferred fact grammar.
        chart_blocks = []
        for name, text in (
            ("SKILL.md", skill),
            ("workflow.md", workflow),
            ("phases.md", phases),
        ):
            for m in re.finditer(
                r"(?is)(?:chart briefing|chart provenance|fn-135|fn-148).{0,800}",
                text,
            ):
                chart_blocks.append((name, m.group(0)))
        self.assertTrue(chart_blocks, "expected chart/fn-148 blocks")
        for name, block in chart_blocks:
            if re.search(r"verified/inferred|verified-vs-inferred|\[verified\]", block):
                self.assertRegex(
                    block,
                    r"(?i)(no|not|nothing|stopped|licenses).{0,40}(verified|\[verified\])"
                    r"|(verified).{0,40}(no|not|nothing|stopped|licenses)",
                    f"{name}: chart block must reject verified grammar",
                )


if __name__ == "__main__":
    unittest.main()
