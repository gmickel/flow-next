"""Prose/guard/verdict/registry contract for the prompt-first chart skill (fn-135.4).

Locks load-bearing contracts in the canonical skill, command shim, and the four
registry surfaces that enumerate the public command/skill inventory. Scope is
canonical only - sync-codex regenerates the Codex mirror in a later task.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_chart_skill_contract -q
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"
SKILL_DIR = PLUGIN / "skills" / "flow-next-chart"
SHIM = PLUGIN / "commands" / "chart.md"

SKILL_MD = SKILL_DIR / "SKILL.md"
WORKFLOW_MD = SKILL_DIR / "workflow.md"
REFERENCES = SKILL_DIR / "references"
EXAMPLES_MD = REFERENCES / "examples.md"

# Branch-disclosure refactor: workflow.md routes to exactly one mode reference
# per invocation. Prose that used to sit inline in workflow.md now lives in the
# reference for the mode that reaches it. Each contract below is asserted
# against its new home PLUS the link that makes that home reachable.
CHART_MODE_MD = REFERENCES / "chart-mode.md"  # Phase 1 (chart mode)
WORK_MODE_MD = REFERENCES / "work-mode.md"  # Phase 2 + 5 (work mode)
BRIEFING_MD = REFERENCES / "briefing-and-reopen.md"  # Phase 4 + 6
RE_ENTRY_MD = REFERENCES / "re-entry.md"  # Phase 0.2 locator re-entry
TRACKER_PROJECTION_MD = REFERENCES / "tracker-projection.md"  # Phase 0.2b gate

REGISTRY_FILES = (
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
    REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
    PLUGIN / ".claude-plugin" / "plugin.json",
    PLUGIN / ".codex-plugin" / "plugin.json",
)

# Exact terminal verdict grammar pinned by R15 / SKILL.md.
VERDICT_GRAMMAR_LINE = (
    "CHART_VERDICT=<RESOLVED|BLOCKED|NEEDS_HUMAN|COMPLETE|NO_WORK> "
    "chart=<id> decision=<D> reason="
)

# Em dash and en dash - skill prose must use plain hyphens only.
EM_OR_EN_DASH = re.compile("[\u2012\u2013\u2014\u2015]")

# Conservative scan for literal destructive shell shapes (R20). Files may
# DESCRIBE such operations in prose but must not embed the literal tokens.
DESTRUCTIVE_LITERALS = (
    re.compile(r"\brm\s+-[A-Za-z]*[rf][A-Za-z]*\b"),
    re.compile(r"\bgit\s+clean\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bmkfs\."),
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r"\bshred\b"),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _combined_skill_prose() -> str:
    return "\n".join(
        (
            _read(SKILL_MD),
            _read(WORKFLOW_MD),
            _read(EXAMPLES_MD),
            _read(SHIM),
        )
    )


def _near(text: str, needle: str, *, window: int = 500) -> list[str]:
    """Return windows around each case-sensitive occurrence of needle."""
    out: list[str] = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx == -1:
            break
        lo = max(0, idx - window)
        hi = min(len(text), idx + len(needle) + window)
        out.append(text[lo:hi])
        start = idx + len(needle)
    return out


class ChartSkillFilesExist(unittest.TestCase):
    def test_skill_tree_and_shim_exist(self) -> None:
        for path in (SKILL_MD, WORKFLOW_MD, EXAMPLES_MD, SHIM):
            self.assertTrue(path.is_file(), f"missing {path}")

    def test_mode_references_exist_and_are_reachable(self) -> None:
        """Every mode reference exists and workflow.md links it by path."""
        workflow = _read(WORKFLOW_MD)
        for path in (
            CHART_MODE_MD,
            WORK_MODE_MD,
            BRIEFING_MD,
            RE_ENTRY_MD,
            TRACKER_PROJECTION_MD,
        ):
            with self.subTest(reference=path.name):
                self.assertTrue(path.is_file(), f"missing {path}")
                self.assertIn(
                    f"references/{path.name}",
                    workflow,
                    f"workflow.md must link references/{path.name} "
                    "(prose moved there is unreachable otherwise)",
                )


class ChartVerdictGrammar(unittest.TestCase):
    def test_exact_verdict_grammar_line(self) -> None:
        skill = _read(SKILL_MD)
        examples = _read(EXAMPLES_MD)
        self.assertIn(VERDICT_GRAMMAR_LINE, skill)
        self.assertIn(VERDICT_GRAMMAR_LINE, examples)
        for token in (
            "RESOLVED",
            "BLOCKED",
            "NEEDS_HUMAN",
            "COMPLETE",
            "NO_WORK",
        ):
            self.assertIn(token, skill)

    def test_exactly_one_verdict_per_work_invocation(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        combined = skill + "\n" + workflow
        self.assertRegex(
            combined,
            re.compile(r"exactly one.{0,40}CHART_VERDICT|one terminal line", re.I),
        )
        self.assertIn("one D-ID", skill)
        self.assertIn("No batch", skill)


class ChartAttendedHardGate(unittest.TestCase):
    def test_needs_human_no_self_resolve_prototype_interview(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        combined = skill + "\n" + workflow
        self.assertIn("NEEDS_HUMAN", combined)
        # Attendance field + hard gate language
        self.assertRegex(
            combined,
            re.compile(r"attendance:\s*`?attended`?|attendance` is `attended"),
        )
        self.assertIn("no answer", combined.lower())
        # Prototype and interview are attended hard gates
        self.assertIn("prototype", combined.lower())
        self.assertIn("interview", combined.lower())
        self.assertRegex(
            combined,
            re.compile(
                r"(never self-answer|Never self-answer|cannot self-resolve|"
                r"hard gate|never infer approval)",
                re.I,
            ),
        )
        # Unattended driver must not write answers for attended decisions
        self.assertIn("Unattended driver", skill)
        self.assertIn("no answer write", skill.lower().replace("**", ""))


class ChartFrontierAndClaim(unittest.TestCase):
    def test_frontier_is_sole_selection_input(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        work_mode = _read(WORK_MODE_MD)
        self.assertIn("sole selection input", skill)
        self.assertIn("chart frontier", skill)
        # Work-mode selection prose lives in the work-mode reference now;
        # workflow.md keeps the frontier render for status mode.
        self.assertIn("sole selection input", work_mode)
        self.assertIn('chart frontier "$CHART_ID"', work_mode)
        self.assertIn('chart frontier "$CHART_ID"', workflow)
        self.assertIn("references/work-mode.md", workflow)

    def test_claim_before_work(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        work_mode = _read(WORK_MODE_MD)
        self.assertIn("Claim before any work", skill)
        self.assertIn("Claim before any work", work_mode)
        self.assertIn("chart claim", work_mode)
        self.assertIn("references/work-mode.md", workflow)

    def test_one_decision_per_invocation_no_batch(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        combined = skill + "\n" + workflow
        self.assertIn("one D-ID", skill)
        self.assertIn("one claim", skill.lower())
        self.assertIn("one verdict", skill.lower())
        self.assertRegex(
            combined,
            re.compile(r"no batch|never batch|not a batch", re.I),
        )
        self.assertIn("separate", skill.lower())
        # Parallelism = separate invocations (may live in skill or workflow)
        self.assertRegex(
            combined,
            re.compile(r"parallel|fan out", re.I),
        )

    def test_no_fixed_route_order(self) -> None:
        skill = _read(SKILL_MD)
        examples = _read(EXAMPLES_MD)
        workflow = _read(WORKFLOW_MD)
        combined = skill + "\n" + examples + "\n" + workflow
        self.assertRegex(
            combined,
            re.compile(
                r"not a mandatory (phase|sequence)|not a fixed ceremony|"
                r"never follow a frozen|does not execute a frozen|"
                r"not.*mandatory phase order|illustrative.*not phases",
                re.I,
            ),
        )
        self.assertIn("adaptive", combined.lower())


class ChartModeContracts(unittest.TestCase):
    def test_breadth_first_initial_frontier_resolves_nothing(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        chart_mode = _read(CHART_MODE_MD)
        combined = skill + "\n" + workflow + "\n" + chart_mode
        self.assertIn("breadth-first", chart_mode)
        self.assertIn("Charting resolves nothing", skill)
        self.assertIn("Resolve no decisions", chart_mode)
        self.assertIn("resolves nothing", combined.lower())
        self.assertIn("references/chart-mode.md", workflow)

    def test_cost_readback_before_persistence_and_force_size(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        combined = skill + "\n" + workflow
        self.assertIn("cost", combined.lower())
        self.assertIn("read-back", combined.lower().replace("read back", "read-back"))
        self.assertIn("--force-size", combined)
        self.assertIn("--reason", combined)
        self.assertRegex(
            combined,
            re.compile(
                r"before persist|before any write|before persisting|"
                r"Read-back before persistence",
                re.I,
            ),
        )
        self.assertIn("consent", combined.lower())
        self.assertIn("chart.maxDecisions", combined)


class ChartPrototypeLifecycle(unittest.TestCase):
    def test_attach_before_reaction_and_resumability(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        work_mode = _read(WORK_MODE_MD)
        combined = skill + "\n" + workflow + "\n" + work_mode
        self.assertIn("attach-asset", combined)
        self.assertIn("reaction", combined.lower())
        self.assertRegex(
            combined,
            re.compile(r"attach.{0,80}(while open|open)", re.I | re.S),
        )
        self.assertRegex(
            combined,
            re.compile(
                r"resume.{0,60}(existing|asset)|resumable|"
                r"never rebuild|never infer approval",
                re.I,
            ),
        )
        # Prototype lifecycle detail lives in the work-mode reference.
        self.assertIn("awaiting reaction", work_mode.lower())
        self.assertIn("references/work-mode.md", workflow)


class ChartLocateReentry(unittest.TestCase):
    def test_locate_local_only_readback_history_not_new_work(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        examples = _read(EXAMPLES_MD)
        re_entry = _read(RE_ENTRY_MD)
        combined = skill + "\n" + workflow + "\n" + examples + "\n" + re_entry
        self.assertIn("chart locate", combined)
        self.assertRegex(
            combined,
            re.compile(r"local (ledger|only)|strictly local", re.I),
        )
        # Locator re-entry contract moved to the Phase 0.2 reference.
        self.assertIn("No remote search", re_entry)
        self.assertIn("references/re-entry.md", workflow)
        self.assertIn("title inference", combined.lower())
        self.assertRegex(
            combined,
            re.compile(r"read back|Read back", re.I),
        )
        self.assertRegex(
            combined,
            re.compile(
                r"history.{0,80}(never|not).{0,40}(silent|new work)|"
                r"historical decision|"
                r"never silently choose",
                re.I | re.S,
            ),
        )
        self.assertIn("mutate nothing", re_entry.lower())


class ChartPortableHostAndAsk(unittest.TestCase):
    def test_portable_host_fallback_near_ask(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        for label, text in (("SKILL.md", skill), ("workflow.md", workflow)):
            with self.subTest(file=label):
                self.assertIn("AskUserQuestion", text)
                windows = _near(text, "AskUserQuestion", window=400)
                self.assertTrue(windows, f"{label}: no AskUserQuestion")
                portable_ok = any(
                    re.search(
                        r"portable|plain-text numbered|numbered prompt|"
                        r"Other - type your own answer",
                        w,
                        re.I,
                    )
                    for w in windows
                )
                self.assertTrue(
                    portable_ok,
                    f"{label}: AskUserQuestion lacks nearby portable-host fallback",
                )

    def test_portable_host_fallback_near_task_explore(self) -> None:
        skill = _read(SKILL_MD)
        workflow = _read(WORKFLOW_MD)
        for label, text in (("SKILL.md", skill), ("workflow.md", workflow)):
            with self.subTest(file=label):
                self.assertIn("Explore", text)
                self.assertIn("Task", text)
                windows = _near(text, "Explore", window=400)
                portable_ok = any(
                    re.search(
                        r"portable|generic read-only|Edit/Write disallowed|"
                        r"read-only dispatch",
                        w,
                        re.I,
                    )
                    for w in windows
                )
                self.assertTrue(
                    portable_ok,
                    f"{label}: Explore/Task lacks nearby portable-host fallback",
                )

    def test_bare_ask_user_question_no_request_user_input(self) -> None:
        combined = _combined_skill_prose()
        self.assertIn("AskUserQuestion", combined)
        self.assertNotIn("request_user_input", combined)
        # Bare form preferred - no platform-prefixed tool names
        self.assertNotIn("tools.AskUserQuestion", combined)


class ChartProvenanceAndSafety(unittest.TestCase):
    def test_no_verified_inferred_grammar(self) -> None:
        combined = _combined_skill_prose()
        self.assertIn("fn-148", combined)
        # Chart must not invent a verified/inferred *fact* grammar (fn-148
        # STOPPED). Mentions of the phrase / [verified] must be prohibitions.
        # Bare `[inferred]` as part of the capture AC four-tag list
        # (`[user]`/`[paraphrase]`/`[inferred]`/`[strategy:*]`) is allowed when
        # the prose says those tags do not apply to chart facts.
        for m in re.finditer(
            r"verified/inferred|verified-vs-inferred|\[verified\]",
            combined,
            re.I,
        ):
            start = max(0, m.start() - 80)
            end = min(len(combined), m.end() + 40)
            window = combined[start:end].lower()
            self.assertTrue(
                any(
                    tok in window
                    for tok in (
                        "no ",
                        "not ",
                        "never",
                        "nothing",
                        "stopped",
                        "include no",
                        "out of scope",
                    )
                ),
                f"verified/inferred must appear only as prohibition: {window!r}",
            )
        # No positive "use verified/inferred" instruction
        self.assertNotRegex(
            combined,
            re.compile(
                r"(?:use|apply|emit|write|author)\s+verified/inferred",
                re.I,
            ),
        )

    def test_no_em_dashes_in_skill_files(self) -> None:
        for path in (
            SKILL_MD,
            WORKFLOW_MD,
            EXAMPLES_MD,
            CHART_MODE_MD,
            WORK_MODE_MD,
            BRIEFING_MD,
            RE_ENTRY_MD,
            TRACKER_PROJECTION_MD,
            SHIM,
        ):
            text = _read(path)
            m = EM_OR_EN_DASH.search(text)
            if m is not None:
                self.fail(
                    f"{path.name}: em/en dash U+{ord(m.group(0)):04X} at "
                    f"offset {m.start()}; use plain hyphens"
                )

    def test_no_literal_destructive_command_strings(self) -> None:
        for path in (
            SKILL_MD,
            WORKFLOW_MD,
            EXAMPLES_MD,
            CHART_MODE_MD,
            WORK_MODE_MD,
            BRIEFING_MD,
            RE_ENTRY_MD,
            TRACKER_PROJECTION_MD,
            SHIM,
        ):
            text = _read(path)
            for pat in DESTRUCTIVE_LITERALS:
                m = pat.search(text)
                if m is not None:
                    self.fail(
                        f"{path.name}: literal destructive shape {m.group(0)!r} "
                        f"(describe operations; do not embed command strings)"
                    )
        # Prose must still talk about the safety rule
        combined = _combined_skill_prose()
        self.assertRegex(
            combined,
            re.compile(r"destructive (shell )?command", re.I),
        )


class ChartShimContract(unittest.TestCase):
    def test_shim_invokes_skill(self) -> None:
        text = _read(SHIM)
        self.assertIn("name: chart", text)
        self.assertIn("flow-next-chart", text)
        self.assertIn("CHART_VERDICT=", text)
        self.assertNotIn("request_user_input", text)


class ChartRegistryEntries(unittest.TestCase):
    def test_four_registry_files_exist_and_list_plugin(self) -> None:
        for path in REGISTRY_FILES:
            self.assertTrue(path.is_file(), f"missing registry {path}")
            data = json.loads(_read(path))
            blob = json.dumps(data)
            self.assertIn("flow-next", blob)

    def test_command_and_skill_counts_bumped_where_enumerated(self) -> None:
        """Registries that publish inventory counts must reflect chart +1.

        `.agents/plugins/marketplace.json` does not enumerate command/skill
        counts - it only lists the plugin - so it is checked for presence only.
        """
        # 28/32 include the stable flow-next-prose skill (fn-207.5) and
        # flow-next-features (fn-211.4); the work-rolling beta graduated into
        # work's default scheduler (fn-218). Registry manifests count every
        # shipped dir.
        expected_snippet = "28 commands, 32 skills"
        count_surfaces = (
            REPO_ROOT / ".claude-plugin" / "marketplace.json",
            PLUGIN / ".claude-plugin" / "plugin.json",
            PLUGIN / ".codex-plugin" / "plugin.json",
        )
        for path in count_surfaces:
            text = _read(path)
            self.assertIn(
                expected_snippet,
                text,
                f"{path.relative_to(REPO_ROOT)} must advertise {expected_snippet!r}",
            )
            self.assertNotIn("25 commands, 29 skills", text)
            self.assertNotIn("24 commands, 29 skills", text)

        # Agents marketplace: plugin entry only (no count enumeration).
        agents = json.loads(_read(REPO_ROOT / ".agents" / "plugins" / "marketplace.json"))
        names = [p.get("name") for p in agents.get("plugins", [])]
        self.assertIn("flow-next", names)

    def test_skill_and_command_surface_include_chart(self) -> None:
        self.assertTrue(SKILL_DIR.is_dir())
        self.assertTrue(SHIM.is_file())
        skill_names = {
            p.name
            for p in (PLUGIN / "skills").iterdir()
            if p.is_dir() and p.name.startswith("flow-next")
        }
        self.assertIn("flow-next-chart", skill_names)
        command_stems = {p.stem for p in (PLUGIN / "commands").glob("*.md")}
        self.assertIn("chart", command_stems)


if __name__ == "__main__":
    unittest.main()
