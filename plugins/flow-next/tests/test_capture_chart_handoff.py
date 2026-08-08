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


def _read_ref(name: str) -> str:
    return (CANONICAL / "references" / name).read_text(encoding="utf-8")


# Branch-disclosure (fn-169) moved the chart-briefing prose out of the
# always-loaded spine into references/chart-briefing.md, which workflow.md
# §0.5b loads when the chart-briefing gate fires. Assertions below target the
# reference for the substance and the spine for reachability.
CHART_REF_LINK = "[references/chart-briefing.md](references/chart-briefing.md)"


class CaptureChartHandoffContract(unittest.TestCase):
    def test_skill_files_exist(self) -> None:
        for name in ("SKILL.md", "workflow.md", "phases.md"):
            self.assertTrue((CANONICAL / name).is_file(), name)
        self.assertTrue(
            (CANONICAL / "references" / "chart-briefing.md").is_file(),
            "references/chart-briefing.md",
        )

    def test_briefing_ingestion_prose(self) -> None:
        workflow = _read("workflow.md")
        ref = _read_ref("chart-briefing.md")
        self.assertIn("chart-briefing ingestion", ref.lower())
        self.assertIn(".flow/charts/*-briefing*.md", ref)
        self.assertIn("0.5b — Chart briefing admission", ref)
        self.assertIn("1.2b — Chart briefing evidence", ref)
        self.assertIn("chart id", ref.lower())
        self.assertIn("B-ID", ref)
        self.assertIn("cluster", ref.lower())
        # Reachability: workflow.md's §0.5b gate names the trigger shapes and
        # loads the reference.
        self.assertIn("0.5b — Chart briefing gate", workflow)
        self.assertIn(".flow/charts/*-briefing*.md", workflow)
        self.assertIn(CHART_REF_LINK, workflow)

    def test_draft_stale_refusal_and_override_readback(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        ref = _read_ref("chart-briefing.md")
        for text in (skill, workflow, ref):
            self.assertIn("draft", text.lower())
            self.assertIn("stale", text.lower())
        self.assertIn("REFUSES draft or stale", ref)
        self.assertIn("forced draft", ref.lower())
        self.assertIn("never", ref.lower())
        self.assertIn("promote", ref.lower())
        self.assertIn("read back the exact risk", ref.lower())
        self.assertIn("risk override", ref.lower())
        self.assertIn("unresolved", ref.lower())
        self.assertIn("invalidated", ref.lower())
        # Reachability: the fail-closed rule stays visible on the spine —
        # SKILL.md forbids silent draft/stale admission, workflow.md's gate
        # states fail-closed + the risk override before loading the reference.
        self.assertIn("draft/stale briefing silently", skill)
        self.assertIn("risk override", workflow.lower())
        self.assertIn("draft/stale fail closed", workflow)

    def test_provenance_separation(self) -> None:
        workflow = _read("workflow.md")
        phases = _read("phases.md")
        ref = _read_ref("chart-briefing.md")
        combined = "\n".join([workflow, phases, ref])
        self.assertIn("Provenance separation", ref)
        self.assertIn("Chart provenance separation", ref)
        self.assertIn("three provenance lanes", ref.lower())
        # Reachability: phases.md points at the chart-briefing gate for the
        # full provenance-lane rule; workflow.md's gate names it as owned there.
        self.assertIn("provenance-lane rule loads with the chart-briefing gate", phases)
        self.assertIn("provenance-separation rule", workflow)
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
        ref = _read_ref("chart-briefing.md")
        self.assertIn("chart link-spec", ref)
        self.assertIn("link-spec", ref)
        # Order: create -> set-plan -> link-spec
        self.assertIn("spec create", ref.lower())
        self.assertIn("spec set-plan", ref.lower())
        self.assertIn("only after", ref.lower())
        # Explicit ordering in the reference's shell block.
        self.assertIn("set-plan", ref)
        self.assertIn("Order is load-bearing", ref)
        self.assertIn("create → set-plan → link-spec", ref)
        # Reachability: the spine still names the handoff callback and routes
        # the ordering detail to the chart-briefing reference.
        self.assertIn("chart link-spec", skill)
        self.assertIn("`chart link-spec` handoff", workflow)
        self.assertIn(CHART_REF_LINK, workflow)

    def test_retry_discovers_existing_spec(self) -> None:
        workflow = _read("workflow.md")
        ref = _read_ref("chart-briefing.md")
        self.assertIn("produced_specs", ref)
        self.assertIn("retry", ref.lower())
        self.assertIn("duplicate", ref.lower())
        self.assertIn("B-ID+cluster", ref)
        self.assertIn("discover", ref.lower())
        self.assertIn("Partial multi-spec", ref)
        self.assertIn("Decline", ref)
        self.assertIn("resumable", ref.lower())
        # Reachability: workflow.md's gate names the retry rules as owned by
        # the reference it loads.
        self.assertIn("retry rules", workflow)
        self.assertIn(CHART_REF_LINK, workflow)

    def test_fn148_non_preemption(self) -> None:
        skill = _read("SKILL.md")
        workflow = _read("workflow.md")
        phases = _read("phases.md")
        ref = _read_ref("chart-briefing.md")
        combined = "\n".join([skill, workflow, phases, ref])
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
            ("references/chart-briefing.md", ref),
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
