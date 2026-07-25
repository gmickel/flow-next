"""fn-134.4 — Spec-id routing gate, setup question, and discoverability contracts.

Skill-prose contract tests (R7/R8/R9/R11/R20). Behavioral create-first recovery
and mint plumbing live in earlier tasks; this gate pins that every mint site
routes on tracker.specIds from an existing root snapshot, states network cost
conditionally, and that setup asks once when the key is unset.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SKILLS = PLUGIN / "skills"

PLAN_STEPS = SKILLS / "flow-next-plan" / "steps.md"
WORK_MINT_REF = SKILLS / "flow-next-work" / "references" / "spec-id-mint.md"
WORK_PHASES = SKILLS / "flow-next-work" / "phases.md"
WORK_SKILL = SKILLS / "flow-next-work" / "SKILL.md"
CAPTURE_WF = SKILLS / "flow-next-capture" / "workflow.md"
INTERVIEW_WB = SKILLS / "flow-next-interview" / "references" / "write-back.md"
QA_BUG = SKILLS / "flow-next-qa" / "references" / "bug-filing.md"
SETUP_WF = SKILLS / "flow-next-setup" / "workflow.md"

# Five mint sites named in the spec / task.
MINT_SITES = {
    "plan": PLAN_STEPS,
    # fn-134 review: the gate moved off the always-loaded path into an on-demand
    # reference to keep the reached path below the fn-130 baseline. Same contract,
    # different file - concatenate both so the assertions are unchanged.
    "work": [WORK_PHASES, WORK_MINT_REF],
    "capture": CAPTURE_WF,
    "interview": INTERVIEW_WB,
    "qa": QA_BUG,
}


def _read(path) -> str:
    """Read one path, or concatenate a list of paths that jointly form one site."""
    if isinstance(path, (list, tuple)):
        return "\n".join(p.read_text(encoding="utf-8") for p in path)
    return path.read_text(encoding="utf-8")


class SpecIdConfigReadBudget(unittest.TestCase):
    """R7: mint sites route from a root snapshot, never a per-leaf read, and
    never take a SECOND snapshot when the skill already holds one."""

    # A mint site may (and does) PROHIBIT the per-leaf read in prose, so match an
    # actual invocation - the flowctl binary followed by the leaf - not the bare
    # phrase, which also appears inside "never a per-leaf `config get ...`".
    LEAF_INVOCATION = re.compile(
        r"""(?:\$FLOWCTL|"\$FLOWCTL"|flowctl(?:\.py)?)\s+config\s+get\s+tracker\.specIds"""
    )

    def test_no_per_leaf_specids_read_at_any_mint_site(self) -> None:
        for name, path in MINT_SITES.items():
            with self.subTest(site=name):
                hit = self.LEAF_INVOCATION.search(_read(path))
                self.assertIsNone(
                    hit,
                    f"{name}: per-leaf read invoked: {hit.group(0) if hit else ''}",
                )

    def test_sites_holding_a_snapshot_do_not_take_a_second(self) -> None:
        # plan and capture take a root snapshot early; their mint sites must jq
        # that file rather than issue another `config get --json`.
        for name, path in (("plan", PLAN_STEPS), ("capture", CAPTURE_WF)):
            text = _read(path)
            with self.subTest(site=name):
                self.assertLessEqual(
                    text.count("config get --json"),
                    1,
                    f"{name}: more than one root snapshot taken",
                )

    def test_work_mint_reuses_phase0_snapshot(self) -> None:
        # work promotes its Phase 0 leaf read to a root snapshot; the mint
        # reference must REUSE it, not take its own.
        ref = _read(WORK_MINT_REF)
        self.assertNotIn("config get --json", ref)
        self.assertIn("WORK_CFG", ref)
        self.assertLessEqual(_read(WORK_PHASES).count("config get --json"), 1)


class SpecIdRoutingGate(unittest.TestCase):
    """R7 / R20: every mint site routes on tracker.specIds."""

    def test_every_mint_site_names_specIds_and_tracker_first(self) -> None:
        for name, path in MINT_SITES.items():
            text = _read(path)
            with self.subTest(site=name):
                self.assertIn(
                    "tracker.specIds",
                    text,
                    f"{name}: must route on tracker.specIds",
                )
                self.assertIn(
                    "--tracker-first",
                    text,
                    f"{name}: must name the real CLI flag shipped by task .2",
                )

    def test_plan_work_capture_interview_own_the_gate(self) -> None:
        """These sites implement the gate (create-first + degrade), not only mention it."""
        for name, path in (
            ("plan", PLAN_STEPS),
            ("work", [WORK_PHASES, WORK_MINT_REF]),
            ("capture", CAPTURE_WF),
            ("interview", INTERVIEW_WB),
        ):
            text = _read(path)
            with self.subTest(site=name):
                self.assertIn("create-first", text)
                self.assertRegex(
                    text,
                    r"SILENT|silently|silent degrade|fall-through to flow-first|degrades?\s+\*?\*?silently",
                    f"{name}: must degrade silently to flow-first",
                )
                self.assertIn("override", text.lower())

    def test_qa_inherits_capture_and_names_owner(self) -> None:
        text = _read(QA_BUG)
        self.assertIn("owned by capture", text)
        self.assertIn("capture/workflow.md", text)
        # Direct compose path still carries the gate shape.
        self.assertIn("create-first", text)
        self.assertIn("--tracker-first", text)

    def test_no_new_per_leaf_specIds_config_get_at_mint_sites(self) -> None:
        """Mint sites must derive tracker.specIds from a root snapshot, not a leaf config get call."""
        # Real invocation shapes only — prose that *forbids* the call is allowed.
        leaf_get = re.compile(
            r"""(?:\$FLOWCTL|"\$FLOWCTL"|\$\{FLOWCTL\})\s+config\s+get\s+tracker\.specIds""",
            re.IGNORECASE,
        )
        for name, path in (
            ("plan", PLAN_STEPS),
            ("work", [WORK_PHASES, WORK_MINT_REF]),
            ("capture", CAPTURE_WF),
            ("interview", INTERVIEW_WB),
            ("qa", QA_BUG),
        ):
            text = _read(path)
            with self.subTest(site=name):
                self.assertIsNone(
                    leaf_get.search(text),
                    f"{name}: mint site must not call `config get tracker.specIds` "
                    "(use the root snapshot)",
                )

    def test_plan_and_capture_use_existing_snapshot_path(self) -> None:
        plan = _read(PLAN_STEPS)
        self.assertIn("flow-plan-config-", plan)
        self.assertIn(".value.tracker.specIds", plan)
        capture = _read(CAPTURE_WF)
        self.assertIn("flow-capture-config-", capture)
        self.assertIn(".value.tracker.specIds", capture)

    def test_issue_first_and_fresh_idea_paths_both_present(self) -> None:
        for name, path in (
            ("plan", PLAN_STEPS),
            ("work", [WORK_PHASES, WORK_MINT_REF]),
            ("capture", CAPTURE_WF),
            ("interview", INTERVIEW_WB),
        ):
            text = _read(path)
            with self.subTest(site=name):
                self.assertRegex(
                    text,
                    r"Named existing issue|named issue|Named issue",
                    f"{name}: issue-first linking path missing",
                )
                self.assertRegex(
                    text,
                    r"Fresh idea|fresh idea",
                    f"{name}: fresh-idea create-first path missing",
                )


class SpecIdNetworkCost(unittest.TestCase):
    """R8: network cost stated conditionally — never the withdrawn blanket claim."""

    def test_no_blanket_zero_cost_claim(self) -> None:
        banned = re.compile(
            r"no net (?:new )?(?:network )?cost|adds no net network cost|"
            r"zero network cost|no network cost",
            re.IGNORECASE,
        )
        for name, path in MINT_SITES.items():
            text = _read(path)
            with self.subTest(site=name):
                self.assertIsNone(
                    banned.search(text),
                    f"{name}: withdrawn blanket 'no net cost' claim must not appear",
                )
        setup = _read(SETUP_WF)
        self.assertIsNone(banned.search(setup), "setup: blanket zero-cost claim")

    def test_conditional_cost_stated_at_primary_mints(self) -> None:
        for name, path in (
            ("plan", PLAN_STEPS),
            ("work", [WORK_PHASES, WORK_MINT_REF]),
            ("capture", CAPTURE_WF),
            ("setup", SETUP_WF),
        ):
            text = _read(path)
            with self.subTest(site=name):
                self.assertRegex(
                    text,
                    r"REORDER|reorder",
                    f"{name}: must state reorder when perEvent is active",
                )
                self.assertRegex(
                    text,
                    r"EARLIER remote write|earlier remote write",
                    f"{name}: must state earlier remote write when perEvent is off",
                )


class SpecIdDiscoverability(unittest.TestCase):
    """R11: plan / work / capture name tracker-first as recommended team default."""

    def test_plan_work_capture_name_team_default(self) -> None:
        for name, path in (
            ("plan", PLAN_STEPS),
            ("work", [WORK_PHASES, WORK_MINT_REF]),
            ("work-skill", WORK_SKILL),
            ("capture", CAPTURE_WF),
        ):
            text = _read(path)
            with self.subTest(site=name):
                self.assertRegex(
                    text,
                    r"recommended team default|team default",
                    f"{name}: must name tracker-first as recommended team default",
                )
                self.assertIn("tracker-first", text)

    def test_no_runtime_advisory_nag(self) -> None:
        """Withdrawn R10: no nag/advisory line at mint time."""
        # Positive nag shapes only. Forbidden-by-prose mentions ("do not … runtime
        # advisory", "withdrawn R10") must not trip this gate.
        nag = re.compile(
            r"consider setting tracker\.specIds|"
            r"you should set tracker\.specIds|"
            r"please set tracker\.specIds|"
            r"set tracker\.specIds to (?:tracker|flow) to avoid",
            re.IGNORECASE,
        )
        for name, path in MINT_SITES.items():
            text = _read(path)
            with self.subTest(site=name):
                hits = [m.group(0) for m in nag.finditer(text)]
                self.assertEqual(hits, [], f"{name}: unexpected runtime nag: {hits}")
            # And every site that mentions the topic must record the rejection.
            if "R10" in text or "runtime advisory" in text.lower() or "nag" in text.lower():
                self.assertRegex(
                    text,
                    r"withdrawn R10|Do \*\*not\*\* nag|do not nag|No runtime nag|no runtime nag",
                    f"{name}: mentions nag/advisory without the R10 rejection",
                )


class SpecIdSetupQuestion(unittest.TestCase):
    """R9: setup asks when tracker configured AND key unset; never re-asks."""

    def test_raw_probe_and_unset_gate(self) -> None:
        text = _read(SETUP_WF)
        self.assertIn("tracker.specIds --raw", text)
        self.assertIn("TRACKER_CONFIGURED", text)
        self.assertIn("CURRENT_SPEC_IDS", text)
        # Both conditions in the include rule.
        self.assertRegex(
            text,
            r"TRACKER_CONFIGURED=1.*CURRENT_SPEC_IDS|tracker configured.*CURRENT_SPEC_IDS",
            re.IGNORECASE | re.DOTALL,
        )
        self.assertIn("never re-ask", text.lower())

    def test_default_tracker_and_collision_rationale(self) -> None:
        text = _read(SETUP_WF)
        block_start = text.index("**Spec ids question**")
        block = text[block_start : block_start + 2500]
        self.assertIn("Tracker (Recommended)", block)
        self.assertIn("collide on fn-N", block)
        self.assertIn(
            "creates the issue BEFORE the local spec exists",
            block,
        )
        self.assertIn("earlier remote write", block)

    def test_write_back_sets_either_value(self) -> None:
        text = _read(SETUP_WF)
        self.assertIn('config set tracker.specIds tracker', text)
        self.assertIn('config set tracker.specIds flow', text)
        self.assertIn("ask-once", text.lower())

    def test_explicit_flow_is_remembered(self) -> None:
        text = _read(SETUP_WF)
        # The Flow option description must say an explicit Flow answer is remembered.
        self.assertRegex(
            text,
            r"explicit Flow answer is remembered|will not ask again",
            re.IGNORECASE,
        )


class NamedIssueMintMustAttach(unittest.TestCase):
    """Every named-issue mint branch must also attach + seed (PR #241 P1).

    `spec create --tracker-first` stores the display identifier but NOT the
    durable `tracker.id`. Three mint sites minted from a user-named key and
    stopped there, so the spec was effectively unlinked: the next lifecycle
    touchpoint took the create-if-unlinked path and opened a SECOND remote
    issue instead of linking the one the user actually named. Duplicate remote
    issues are not locally reversible, which is why this is pinned in prose.
    """

    SITES = {
        "capture": SKILLS / "flow-next-capture" / "workflow.md",
        "plan": SKILLS / "flow-next-plan" / "steps.md",
        "interview": SKILLS / "flow-next-interview" / "references" / "write-back.md",
    }

    def test_each_named_issue_branch_requires_attach(self) -> None:
        for name, path in self.SITES.items():
            with self.subTest(site=name):
                text = path.read_text(encoding="utf-8")
                i = text.find("Named existing issue")
                self.assertNotEqual(i, -1, f"{name}: named-issue branch not found")
                # The attach obligation must appear in the branch itself, before
                # the fresh-idea branch that already carries its own attach step.
                branch = text[i : i + 1200]
                self.assertIn(
                    "attach", branch,
                    f"{name}: named-issue branch mints without attaching - a later "
                    "touchpoint would create a second remote issue",
                )
                self.assertIn(
                    "tracker.id", branch,
                    f"{name}: branch does not say WHY attach is required "
                    "(the durable tracker.id is what is missing)",
                )



if __name__ == "__main__":
    unittest.main()
