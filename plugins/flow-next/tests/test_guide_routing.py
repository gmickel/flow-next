"""Exact-matrix + boundary contracts for /flow-next:guide (fn-135.6 / R30/R31).

Locks the smallest-sufficient-workflow matrix, skip-vs-risk distinction,
one-blocking-question rule, natural-language-first output, pure-routing
allowed-tools, and adjacent-skill handover language.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_guide_routing -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
REPO_ROOT = PLUGIN.parent.parent

GUIDE_SKILL = PLUGIN / "skills" / "flow-next-guide" / "SKILL.md"
GUIDE_SHIM = PLUGIN / "commands" / "guide.md"

ADJACENT = {
    "prospect_skill": PLUGIN / "skills" / "flow-next-prospect" / "SKILL.md",
    "prospect_workflow": PLUGIN / "skills" / "flow-next-prospect" / "workflow.md",
    "capture": PLUGIN / "skills" / "flow-next-capture" / "SKILL.md",
    "interview": PLUGIN / "skills" / "flow-next-interview" / "SKILL.md",
    "plan_skill": PLUGIN / "skills" / "flow-next-plan" / "SKILL.md",
    "plan_steps": PLUGIN / "skills" / "flow-next-plan" / "steps.md",
    "pilot": PLUGIN / "skills" / "flow-next-pilot" / "SKILL.md",
}

EM_OR_EN_DASH = re.compile("[\u2012\u2013\u2014\u2015]")

# Every matrix row: signal tokens that must appear for the route.
# Keep stable - these are the R30 contract anchors.
MATRIX_ROWS = (
    {
        "name": "prospect",
        "route_tokens": ("/flow-next:prospect", "prospect"),
        "signal_tokens": ("domain", "candidate"),
        "skip_tokens": ("chart only", "unclear", "oversized"),
    },
    {
        "name": "chart",
        "route_tokens": ("/flow-next:chart",),
        "signal_tokens": ("oversized", "unclear", "unknown"),
        "skip_tokens": ("skip chart", "never mandatory"),
    },
    {
        "name": "capture_clear",
        "route_tokens": ("/flow-next:capture",),
        "signal_tokens": ("clear", "intent", "boundaries"),
        "skip_tokens": ("skip chart", "manufacture"),
    },
    {
        "name": "structured_brief",
        "route_tokens": ("/flow-next:capture",),
        "signal_tokens": ("structured brief", "brief"),
        "skip_tokens": ("read-back", "interview"),
    },
    {
        "name": "direct_change",
        "route_tokens": ("Direct change",),
        "signal_tokens": ("tiny", "low-risk", "local"),
        "skip_tokens": ("full spec pipeline", "Skip chart"),
    },
    {
        "name": "interview",
        "route_tokens": ("/flow-next:interview",),
        "signal_tokens": ("valid spec", "judgment"),
        "skip_tokens": ("not yet specifiable", "reopen"),
    },
    {
        "name": "plan",
        "route_tokens": ("/flow-next:plan",),
        "signal_tokens": ("ready spec", "understood"),
        "skip_tokens": ("too late", "chart"),
    },
    {
        "name": "work",
        "route_tokens": ("/flow-next:work",),
        "signal_tokens": ("Planned tasks", "tasks"),
        "skip_tokens": ("review", "QA", "ship"),
    },
    {
        "name": "unsure",
        "route_tokens": ("This matrix", "guide"),
        "signal_tokens": ("Unsure", "Ambiguous"),
        "skip_tokens": ("blocking question", "materially"),
    },
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class GuideSkillSurface(unittest.TestCase):
    def test_skill_and_shim_exist(self) -> None:
        self.assertTrue(GUIDE_SKILL.is_file(), f"missing {GUIDE_SKILL}")
        self.assertTrue(GUIDE_SHIM.is_file(), f"missing {GUIDE_SHIM}")

    def test_frontmatter_name_and_no_write_edit(self) -> None:
        text = _read(GUIDE_SKILL)
        self.assertIn("name: flow-next-guide", text)
        self.assertIn("user-invocable: false", text)
        m = re.search(r"^allowed-tools:\s*(.+)$", text, re.M)
        self.assertIsNotNone(m, "allowed-tools missing")
        tools = m.group(1)
        self.assertIn("AskUserQuestion", tools)
        self.assertIn("Read", tools)
        self.assertIn("Bash", tools)
        self.assertIn("Grep", tools)
        self.assertIn("Glob", tools)
        self.assertIn("Task", tools)
        self.assertNotIn("Write", tools)
        self.assertNotIn("Edit", tools)

    def test_shim_invokes_skill(self) -> None:
        text = _read(GUIDE_SHIM)
        self.assertIn("name: guide", text)
        self.assertIn("flow-next-guide", text)
        self.assertNotIn("request_user_input", text)

    def test_probes_resolve_bundled_flowctl(self) -> None:
        """Probe prose must resolve the bundled flowctl through all three rungs
        (env var, derived plugin root, .flow/bin) - bare `flowctl` breaks on
        Cursor/Grok hosts with no plugin-root env var and no bin-PATH
        injection, and rung 2 is the one that carries them."""
        text = _read(GUIDE_SKILL)
        self.assertIn(
            'FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}'
            '/scripts/flowctl"',
            text,
        )
        self.assertIn(
            '[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"',
            text,
        )
        self.assertIn('[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"', text)
        # Probe examples reference the resolved path, never bare flowctl.
        self.assertNotRegex(text, re.compile(r"`flowctl\s+(list|show)"))
        self.assertIn("$FLOWCTL list", text)
        self.assertIn("$FLOWCTL show", text)

    def test_no_em_dashes(self) -> None:
        for path in (GUIDE_SKILL, GUIDE_SHIM):
            text = _read(path)
            m = EM_OR_EN_DASH.search(text)
            if m is not None:
                self.fail(
                    f"{path.name}: em/en dash U+{ord(m.group(0)):04X}; "
                    "use plain hyphens only"
                )

    def test_no_state_or_flowctl_mutation(self) -> None:
        text = _read(GUIDE_SKILL)
        lower = text.lower()
        self.assertIn("stateless", lower)
        self.assertIn("no flowctl mutation", lower)
        self.assertRegex(
            text,
            re.compile(r"never mutate|no artifacts|does \*\*not\*\* create", re.I),
        )
        # Must not instruct chart create / spec create as guide actions
        self.assertNotRegex(
            text,
            re.compile(r"flowctl\s+(chart|spec)\s+create", re.I),
        )


class GuideMatrixContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = _read(GUIDE_SKILL)

    def test_every_matrix_row_present(self) -> None:
        for row in MATRIX_ROWS:
            with self.subTest(row=row["name"]):
                for tok in row["route_tokens"]:
                    self.assertIn(
                        tok,
                        self.skill,
                        f"route token missing for {row['name']}: {tok!r}",
                    )
                # At least one signal token and one skip token
                self.assertTrue(
                    any(t in self.skill for t in row["signal_tokens"]),
                    f"no signal token for {row['name']}: {row['signal_tokens']}",
                )
                self.assertTrue(
                    any(t in self.skill for t in row["skip_tokens"]),
                    f"no skip token for {row['name']}: {row['skip_tokens']}",
                )

    def test_skip_vs_risk_distinction(self) -> None:
        skill = self.skill
        self.assertIn("signal absent", skill)
        self.assertIn("despite unresolved risk", skill)
        self.assertRegex(
            skill,
            re.compile(
                r"Skipping a command never skips|"
                r"never skips the evidence|"
                r"evidence, consent, or review",
                re.I,
            ),
        )

    def test_one_blocking_question_rule(self) -> None:
        skill = self.skill
        self.assertRegex(
            skill,
            re.compile(r"at most (one|\*\*one\*\*) blocking question", re.I),
        )
        self.assertIn("AskUserQuestion", skill)
        self.assertRegex(
            skill,
            re.compile(
                r"plain-text numbered|numbered prompt|"
                r"Other - type your own answer",
                re.I,
            ),
        )
        self.assertIn("materially", skill.lower())

    def test_natural_language_first(self) -> None:
        skill = self.skill
        self.assertRegex(
            skill,
            re.compile(
                r"natural-language next prompt|Lead with a \*\*natural-language",
                re.I,
            ),
        )
        self.assertIn("Next:", skill)
        self.assertRegex(
            skill,
            re.compile(r"Flags are secondary|not required vocabulary|flags are secondary", re.I),
        )

    def test_chart_never_mandatory(self) -> None:
        skill = self.skill
        lower = skill.lower()
        self.assertIn("never mandatory", lower)
        self.assertIn("optional", lower)
        self.assertRegex(
            skill,
            re.compile(
                r"never a mandatory stage|never present chart as mandatory|"
                r"chart is never mandatory",
                re.I,
            ),
        )
        self.assertNotRegex(
            skill,
            re.compile(r"must always (run|use) chart|chart is required", re.I),
        )
        # No fixed conveyor
        self.assertRegex(
            skill,
            re.compile(r"no.{0,20}fixed.{0,40}conveyor|not a fixed", re.I | re.S),
        )


class GuideAdjacentHandovers(unittest.TestCase):
    """Adjacent skills agree with the guide matrix (R31)."""

    def test_prospect_routes_chart_only_when_unclear(self) -> None:
        skill = _read(ADJACENT["prospect_skill"])
        workflow = _read(ADJACENT["prospect_workflow"])
        combined = skill + "\n" + workflow
        self.assertRegex(
            combined,
            re.compile(r"singular.{0,40}oversized.{0,40}unclear|still singular", re.I | re.S),
        )
        self.assertRegex(
            combined,
            re.compile(r"do not manufacture a chart|never manufacture", re.I),
        )
        self.assertIn("/flow-next:chart", combined)

    def test_capture_clear_ideas_no_manufactured_chart(self) -> None:
        text = _read(ADJACENT["capture"])
        self.assertRegex(
            text,
            re.compile(r"does \*\*not\*\* manufacture a chart|does not manufacture a chart", re.I),
        )
        self.assertRegex(
            text,
            re.compile(r"clear meaningful|Clear meaningful", re.I),
        )
        self.assertIn("skip chart", text.lower())

    def test_interview_primary_backward_chart_only_if_not_specifiable(self) -> None:
        text = _read(ADJACENT["interview"])
        self.assertRegex(
            text,
            re.compile(r"Existing-spec clarification stays|clarification stays \*\*primary\*\*", re.I),
        )
        self.assertRegex(
            text,
            re.compile(r"not yet specifiable", re.I),
        )
        self.assertIn("/flow-next:chart", text)

    def test_plan_ready_stays_unshaped_to_chart(self) -> None:
        skill = _read(ADJACENT["plan_skill"])
        steps = _read(ADJACENT["plan_steps"])
        combined = skill + "\n" + steps
        self.assertRegex(
            combined,
            re.compile(r"chart is too late|too late", re.I),
        )
        self.assertRegex(
            combined,
            re.compile(r"unshaped oversized|/flow-next:chart first", re.I),
        )
        self.assertIn("/flow-next:chart", combined)

    def test_pilot_chart_outside_build_loop(self) -> None:
        text = _read(ADJACENT["pilot"])
        self.assertRegex(
            text,
            re.compile(r"outside the build loop|never a pilot pipeline stage", re.I),
        )
        self.assertIn("NEEDS_HUMAN", text)
        self.assertRegex(
            text,
            re.compile(r"chart.{0,80}never|never.{0,40}chart", re.I | re.S),
        )
        # chart listed among forbidden stages
        self.assertRegex(
            text,
            re.compile(r"Capture, interview, chart|chart.{0,20}never.*pilot stages", re.I | re.S),
        )


if __name__ == "__main__":
    unittest.main()
