"""Maintained docs inventory for fn-135 chart + guide surfaces.

Fails when chart is absent from pipeline/when-to-use routes, presented as
mandatory, skill/command counts drift from registries, canonical skills or
Codex mirror copies are missing, flowctl chart --help diverges from
docs/flowctl.md, or grounding/prototype/projection/URL re-entry invariants
disappear.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_chart_docs_inventory -q
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"
DOCS = PLUGIN / "docs"
SKILLS = PLUGIN / "skills"
COMMANDS = PLUGIN / "commands"
CODEX = PLUGIN / "codex"
FLOWCTL_PY = PLUGIN / "scripts" / "flowctl.py"

# Branch-disclosure refactor: chart prose that used to sit inline in SKILL.md /
# workflow.md now lives in the mode reference that reaches it. Contracts are
# asserted against their new home, plus the link that keeps the home reachable.
CHART_SKILL_DIR = SKILLS / "flow-next-chart"
CHART_REFERENCES = CHART_SKILL_DIR / "references"
CHART_MODE_REFS = (
    "chart-mode.md",  # Phase 1 chart mode
    "work-mode.md",  # Phase 2 + 5 work mode
    "briefing-and-reopen.md",  # Phase 4 + 6 briefing / reopen
    "re-entry.md",  # Phase 0.2 locator re-entry
    "tracker-projection.md",  # Phase 0.2b projection gate
)

REGISTRY_COUNT_FILES = (
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
    PLUGIN / ".claude-plugin" / "plugin.json",
    PLUGIN / ".codex-plugin" / "plugin.json",
)

# Subcommands from the live CLI - keep in sync with flowctl chart --help.
EXPECTED_CHART_SUBCOMMANDS = frozenset(
    {
        "create",
        "show",
        "list",
        "add-decision",
        "park-question",
        "remove-question",
        "wire-decision",
        "frontier",
        "claim",
        "release-claim",
        "attach-asset",
        "resolve",
        "out-of-scope",
        "abandon",
        "briefing",
        "reopen",
        "locate",
        "link-spec",
    }
)

# Wording that presents chart as a required pipeline stage (surgical).
MANDATORY_CHART_PATTERNS = (
    re.compile(r"\bmust chart\b", re.IGNORECASE),
    re.compile(r"\balways chart\b", re.IGNORECASE),
    re.compile(r"\bchart is (?:a |the )?mandatory\b", re.IGNORECASE),
    re.compile(r"\bmandatory (?:pre-capture |discovery )?stage\b.*\bchart\b", re.IGNORECASE),
    re.compile(r"\bchart\b.*\bmandatory stage\b", re.IGNORECASE),
    re.compile(r"\brequire(?:s|d)? chart\b", re.IGNORECASE),
    re.compile(r"\bchart is required\b", re.IGNORECASE),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _skill_dirs() -> list[str]:
    return sorted(
        p.name
        for p in SKILLS.iterdir()
        if p.is_dir() and p.name.startswith("flow-next")
    )


def _command_stems() -> list[str]:
    return sorted(p.stem for p in COMMANDS.glob("*.md"))


def _slash_command_skills() -> list[str]:
    """Skills that have a matching /flow-next:<stem> command shim."""
    stems = set(_command_stems())
    out = []
    for name in _skill_dirs():
        # flow-next -> no slash; flow-next-chart -> chart
        if name == "flow-next":
            continue
        stem = name.removeprefix("flow-next-")
        if stem in stems:
            out.append(name)
    return out


class ChartDocsFilesExist(unittest.TestCase):
    def test_canonical_chart_and_guide_skills_exist(self) -> None:
        for rel in (
            "skills/flow-next-chart/SKILL.md",
            "skills/flow-next-chart/workflow.md",
            "skills/flow-next-guide/SKILL.md",
            "commands/chart.md",
            "commands/guide.md",
        ):
            path = PLUGIN / rel
            self.assertTrue(path.is_file(), f"missing {path.relative_to(REPO_ROOT)}")

    def test_codex_mirror_chart_and_guide_exist(self) -> None:
        """Host regenerates the mirror after docs land; assert unconditionally.

        The mirror carries skills only - command shims are Claude-side and
        are not mirrored (sync-codex.sh emits skills/agents/references/
        templates).
        """
        mirrored = [
            "skills/flow-next-chart/SKILL.md",
            "skills/flow-next-chart/workflow.md",
            "skills/flow-next-guide/SKILL.md",
        ]
        # Mode references carry the branch-disclosed prose - the mirror is
        # useless without them.
        mirrored += [
            f"skills/flow-next-chart/references/{name}" for name in CHART_MODE_REFS
        ]
        for rel in mirrored:
            path = CODEX / rel
            self.assertTrue(
                path.is_file(),
                f"missing Codex mirror {path.relative_to(REPO_ROOT)} "
                "(host must run ./scripts/sync-codex.sh after this task)",
            )


class ChartPipelineSurfaces(unittest.TestCase):
    """Chart must appear on idea-to-PR / when-to-use routes as optional."""

    PIPELINE_SURFACES = (
        REPO_ROOT / "README.md",
        DOCS / "skills.md",
        DOCS / "teams.md",
        DOCS / "README.md",
        DOCS / "orchestration.md",
        DOCS / "ralph.md",
        DOCS / "architecture.md",
        DOCS / "flowctl.md",
        DOCS / "tracker-sync.md",
        REPO_ROOT / "GLOSSARY.md",
        REPO_ROOT / "CHANGELOG.md",
        PLUGIN / "templates" / "usage.md",
    )

    def test_chart_mentioned_on_every_named_surface(self) -> None:
        for path in self.PIPELINE_SURFACES:
            self.assertTrue(path.is_file(), f"missing {path}")
            text = _read(path)
            self.assertRegex(
                text,
                r"(?i)\bchart\b",
                f"{path.relative_to(REPO_ROOT)} must document chart",
            )

    def test_guide_on_router_surfaces(self) -> None:
        for path in (
            REPO_ROOT / "README.md",
            DOCS / "skills.md",
            DOCS / "README.md",
            REPO_ROOT / "CHANGELOG.md",
        ):
            text = _read(path)
            self.assertRegex(
                text,
                r"(?i)flow-next:guide|/flow-next:guide|flow-next-guide",
                f"{path.relative_to(REPO_ROOT)} must mention guide",
            )

    def test_readme_pipeline_includes_optional_chart(self) -> None:
        readme = _read(REPO_ROOT / "README.md")
        self.assertIn("/flow-next:chart", readme)
        self.assertRegex(readme, r"(?i)optional")
        # mermaid or prose places chart before capture
        self.assertTrue(
            "chart" in readme.lower() and "capture" in readme.lower(),
            "README must place chart in the idea-to-PR narrative",
        )
        self.assertRegex(
            readme,
            r"(?i)optional[^\n.]{0,80}chart|chart[^\n.]{0,80}optional",
            "README must present chart as optional",
        )

    def test_skills_catalog_lists_chart_and_guide(self) -> None:
        skills = _read(DOCS / "skills.md")
        self.assertIn("flow-next-chart", skills)
        self.assertIn("flow-next-guide", skills)
        self.assertIn("/flow-next:chart", skills)
        self.assertIn("/flow-next:guide", skills)
        self.assertRegex(skills, r"(?i)optional")

    def test_no_mandatory_chart_wording(self) -> None:
        # Scan human-facing docs only (not the inventory test itself).
        roots = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "GLOSSARY.md",
            REPO_ROOT / "CHANGELOG.md",
            DOCS,
            SKILLS / "flow-next-chart",
            SKILLS / "flow-next-guide",
            PLUGIN / "templates" / "usage.md",
        ]
        offenders: list[str] = []
        for root in roots:
            paths = [root] if root.is_file() else list(root.rglob("*.md"))
            for path in paths:
                if not path.is_file():
                    continue
                if "test_chart_docs_inventory" in path.name:
                    continue
                text = _read(path)
                for pat in MANDATORY_CHART_PATTERNS:
                    for m in pat.finditer(text):
                        # Allow explicit negation: "never a mandatory stage"
                        start = max(0, m.start() - 40)
                        window = text[start : m.end() + 40]
                        if re.search(
                            r"(?i)\b(?:never|not|no longer)\b.{0,30}mandatory",
                            window,
                        ) or re.search(
                            r"(?i)mandatory.{0,30}\b(?:never|not)\b",
                            window,
                        ):
                            continue
                        if "never a mandatory" in window.lower():
                            continue
                        if "never mandatory" in window.lower():
                            continue
                        if "not a mandatory" in window.lower():
                            continue
                        offenders.append(
                            f"{path.relative_to(REPO_ROOT)}: {m.group(0)!r} near {window!r}"
                        )
        self.assertEqual(offenders, [], "chart must not be presented as mandatory:\n" + "\n".join(offenders))


class ChartRegistryCounts(unittest.TestCase):
    # Experimental-tier carve-out (agent_docs/adding-skills.md §Experimental
    # skills): the filesystem/registry numbers below count every shipped skill
    # dir, experimental ones included, while the published-count phrases
    # (README.md, docs/skills.md, docs/README.md) deliberately exclude them.
    # When an experimental skill lands, bump the filesystem/registry
    # assertions only and leave the published phrases at the stable total;
    # when it graduates, the two totals converge again.
    def test_counts_match_filesystem_and_registries(self) -> None:
        skill_dirs = _skill_dirs()
        commands = _command_stems()
        slash_skills = _slash_command_skills()
        phrase = [s for s in skill_dirs if s not in slash_skills and s != "flow-next"]
        # base flow-next is phrase-triggered too
        phrase_count = len(phrase) + (1 if "flow-next" in skill_dirs else 0)

        # 31/27/26 include the experimental flow-next-work-rolling beta
        # (fn-203.4); the published phrases below stay at the stable totals
        # per the experimental-tier carve-out.
        self.assertEqual(len(skill_dirs), 31, f"skills dirs: {skill_dirs}")
        self.assertEqual(len(commands), 27, f"commands: {commands}")
        self.assertIn("flow-next-chart", skill_dirs)
        self.assertIn("flow-next-guide", skill_dirs)
        self.assertIn("chart", commands)
        self.assertIn("guide", commands)
        self.assertEqual(len(slash_skills), 26, f"slash skills: {slash_skills}")
        self.assertEqual(phrase_count, 5, f"phrase skills expected 5, got {phrase_count}")

        expected_snippet = "27 commands, 31 skills"
        for path in REGISTRY_COUNT_FILES:
            text = _read(path)
            self.assertIn(
                expected_snippet,
                text,
                f"{path.relative_to(REPO_ROOT)} must advertise {expected_snippet!r}",
            )

        # Docs surfaces that publish counts
        for path, needles in (
            (DOCS / "skills.md", ("30 skills", "25 slash-command", "5 phrase")),
            (DOCS / "README.md", ("30 skills",)),
            (REPO_ROOT / "README.md", ("30 skills",)),
        ):
            text = _read(path)
            for n in needles:
                self.assertIn(
                    n,
                    text,
                    f"{path.relative_to(REPO_ROOT)} missing count phrase {n!r}",
                )


class ChartFlowctlDocsParity(unittest.TestCase):
    def test_help_subcommands_match_docs(self) -> None:
        proc = subprocess.run(
            ["python3", str(FLOWCTL_PY), "chart", "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        help_text = proc.stdout
        # argparse lists choices in braces or as indented names
        found = set()
        for name in EXPECTED_CHART_SUBCOMMANDS:
            if re.search(rf"\b{re.escape(name)}\b", help_text):
                found.add(name)
        self.assertEqual(
            found,
            EXPECTED_CHART_SUBCOMMANDS,
            f"flowctl chart --help missing {EXPECTED_CHART_SUBCOMMANDS - found}",
        )

        docs = _read(DOCS / "flowctl.md")
        # chart section must document each subcommand
        chart_section = docs
        idx = docs.find("## chart")
        self.assertGreater(idx, 0, "docs/flowctl.md must have ## chart section")
        # take until next top-level ## that is not a subsection under chart... 
        # next major after chart is "## flowctl tracker"
        end = docs.find("## flowctl tracker", idx)
        chart_section = docs[idx:end] if end > idx else docs[idx:]
        missing = [s for s in sorted(EXPECTED_CHART_SUBCOMMANDS) if s not in chart_section]
        self.assertEqual(missing, [], f"flowctl.md chart section missing subcommands: {missing}")

    def test_envelope_error_classes_documented(self) -> None:
        docs = _read(DOCS / "flowctl.md")
        for cls in (
            "not_found",
            "conflict",
            "invalid_state",
            "invalid_graph",
            "stale_claim",
            "validation",
            "io",
        ):
            self.assertIn(cls, docs, f"flowctl.md must document error class {cls}")

    def test_supersedes_stale_discriminator_documented(self) -> None:
        """The briefing discriminator must stay documented where consumers look.

        Modelled on test_envelope_error_classes_documented above, and scoped the
        same way it is: the contract must live IN the `### v1 JSON envelope`
        section, because that is the section a driver reads to learn the shape
        of a `chart … --json` response. A mention buried elsewhere in the file
        would satisfy a whole-file grep while leaving the envelope contract
        silent, so the section slice is part of the assertion, not a shortcut.

        Each clause below is a distinct half of the shipped contract (flowctl.py
        emit_chart_briefing): the type, the fresh-emission precondition, the
        non-empty rule, the three envelopes it must be ABSENT from, and where
        per-briefing status actually lives. Dropping any one of them describes a
        different contract than the code ships, so each is pinned by name.
        """
        docs = _read(DOCS / "flowctl.md")
        start = docs.find("### v1 JSON envelope")
        self.assertGreater(start, 0, "flowctl.md must have a v1 JSON envelope section")
        end = docs.find("### Subcommands", start)
        self.assertGreater(end, start, "v1 JSON envelope section must be bounded")
        section = docs[start:end]
        self.assertIn(
            "supersedes_stale",
            section,
            "the supersedes_stale contract must live in the v1 JSON envelope "
            "section of flowctl.md, not merely somewhere in the file",
        )
        # Normalize hyphens/whitespace so a reflow or an "idempotent-retry" ->
        # "idempotent retry" rewording does not fail; the CLAUSES are pinned,
        # not their exact typography.
        normalized = re.sub(r"[\s\-]+", " ", section).lower()
        for phrase, why in (
            ("array of b id strings", "type: an array of B-ID strings"),
            ("noop: false", "presence: a fresh emission, never an idempotent retry"),
            ("non empty", "presence: only when the array is non-empty"),
            (
                "idempotent retry",
                "absence: idempotent-retry envelopes stay byte-identical",
            ),
            (
                "first emission",
                "absence: first-emission envelopes stay byte-identical",
            ),
            ("error envelope", "absence: error envelopes stay byte-identical"),
            (
                "briefings[]",
                "per-briefing status lives in the sidecar, not in this field",
            ),
        ):
            self.assertIn(
                phrase,
                normalized,
                f"flowctl.md v1 envelope section must state {why} ({phrase!r})",
            )

    def test_alias_collision_contract_documented(self) -> None:
        """The initial-map alias contract must stay documented (fn-153 R8).

        Scoped to the `### v1 JSON envelope` section for the same reason as
        test_supersedes_stale_discriminator_documented: that is the section a
        driver reads to learn what a failed `chart … --json` looks like. Each
        pinned clause is a distinct half of the shipped contract in flowctl.py
        (_InitialMapAliasRegistrar): the code, the details keys, which side is
        the incumbent, the owner-based definition that keeps same-decision
        re-registration legal, and the atomicity guarantee. Dropping any one of
        them describes a different contract than the code ships.
        """
        docs = _read(DOCS / "flowctl.md")
        start = docs.find("### v1 JSON envelope")
        self.assertGreater(start, 0, "flowctl.md must have a v1 JSON envelope section")
        end = docs.find("### Subcommands", start)
        self.assertGreater(end, start, "v1 JSON envelope section must be bounded")
        section = docs[start:end]
        self.assertIn(
            "alias_collision",
            section,
            "the alias_collision contract must live in the v1 JSON envelope "
            "section of flowctl.md, not merely somewhere in the file",
        )
        normalized = re.sub(r"[\s\-]+", " ", section).lower()
        for phrase, why in (
            ("class `validation`", "the error class is validation"),
            ("`alias`", "details carries the normalized alias"),
            ("`first`", "details carries the incumbent registration"),
            ("`second`", "details carries the rejected registration"),
            ("`index`", "each side carries its 1-based batch index"),
            ("`title`", "each side carries its title"),
            (
                "is the incumbent registration and `second` the rejected one",
                "first is the incumbent, second the rejected one",
            ),
            (
                "two **different** decisions",
                "collision is defined by different owners, not duplicate keys",
            ),
            (
                "same** decision is legal and idempotent",
                "same-owner re-registration stays legal",
            ),
            (
                "no chart files are written",
                "atomicity: a rejection makes no durable reservation",
            ),
        ):
            self.assertIn(
                re.sub(r"[\s\-]+", " ", phrase).lower(),
                normalized,
                f"flowctl.md v1 envelope section must state {why} ({phrase!r})",
            )

    def test_config_keys_documented(self) -> None:
        docs = _read(DOCS / "flowctl.md")
        for key in (
            "chart.maxDecisions",
            "chart.claimStaleAfter",
            "tracker.charts",
        ):
            self.assertIn(key, docs)


class ChartInvariantPhrases(unittest.TestCase):
    """Grounding / prototype / projection / URL re-entry must remain greppable."""

    def test_skill_grounding_and_prototype(self) -> None:
        skill = _read(CHART_SKILL_DIR / "SKILL.md")
        workflow = _read(CHART_SKILL_DIR / "workflow.md")
        # Reference bodies are part of the skill's reachable prose after the
        # branch-disclosure refactor - workflow.md routes to exactly one per
        # invocation, and reachability is asserted below.
        references = "\n".join(
            _read(CHART_REFERENCES / name) for name in CHART_MODE_REFS
        )
        combined = skill + "\n" + workflow + "\n" + references
        for name in CHART_MODE_REFS:
            self.assertIn(
                f"references/{name}",
                workflow,
                f"workflow.md must link references/{name}",
            )
        for phrase in (
            "Grounding Snapshot",
            "attach-asset",
            "prototype",
            "never promote",
            "CHART_VERDICT",
            "one decision",
            "chart locate",
            "local ledger",
            "tracker.charts",
            "chart.maxDecisions",
            # A reopen stales briefings but does NOT close the capture door:
            # the next briefing mints B(n+1) and says what it supersedes.
            # Pinned here for the same reason as the phrases above - the skill
            # is where an operator learns it, and the prose is the only place
            # that contract exists on the skill side.
            "chart reopen",
            "supersedes stale",
        ):
            self.assertIn(
                phrase,
                combined,
                f"chart skill missing invariant phrase {phrase!r}",
            )

        # Pin the moved contracts to their exact new homes, not just the blob.
        briefing = _read(CHART_REFERENCES / "briefing-and-reopen.md")
        self.assertIn("chart reopen", briefing)
        self.assertIn("supersedes stale", briefing)
        re_entry = _read(CHART_REFERENCES / "re-entry.md")
        self.assertIn("chart locate", re_entry)
        projection = _read(CHART_REFERENCES / "tracker-projection.md")
        self.assertIn("tracker.charts", projection)
        chart_mode = _read(CHART_REFERENCES / "chart-mode.md")
        self.assertIn("Grounding Snapshot", chart_mode)
        work_mode = _read(CHART_REFERENCES / "work-mode.md")
        self.assertIn("attach-asset", work_mode)

    def test_tracker_sync_projection_and_url_reentry(self) -> None:
        text = _read(DOCS / "tracker-sync.md")
        for phrase in (
            "Chart lifecycle projection",
            "tracker.charts",
            "local-first",
            "provenance ledger",
            "chart locate",
            "no network",
            "title inference",
            "visibility",
            "control plane",
            "resolved or superseded",
        ):
            self.assertRegex(
                text,
                re.compile(re.escape(phrase), re.IGNORECASE),
                f"tracker-sync.md missing {phrase!r}",
            )

    def test_flowctl_locate_and_projection(self) -> None:
        text = _read(DOCS / "flowctl.md")
        for phrase in (
            "chart locate",
            "local provenance",
            "no network",
            "title inference",
            "schema_version",
            "CHART_VERDICT",
            "blocked_by",
            "depends_on",
            "attach-asset",
        ):
            self.assertIn(phrase, text, f"flowctl.md missing {phrase!r}")

    def test_architecture_charts_layout(self) -> None:
        text = _read(DOCS / "architecture.md")
        for phrase in (
            "charts/",
            ".transactions",
            "shared",
            "fn-N",
            "briefing",
        ):
            self.assertIn(phrase, text)

    def test_glossary_terms(self) -> None:
        # Root GLOSSARY.md keeps a single `## Chart` dictionary entry (pinned
        # by ChartPipelineSurfaces); the six long-form chart term definitions
        # live in the archived full glossary.
        self.assertIn("## Chart", _read(REPO_ROOT / "GLOSSARY.md"))
        text = _read(REPO_ROOT / "agent_docs" / "archive" / "GLOSSARY-full.md")
        for heading in (
            "## Chart",
            "## Decision record",
            "## D-ID",
            "## Frontier (chart)",
            "## Briefing package",
            "## Supersession",
        ):
            self.assertIn(heading, text)

    def test_orchestration_not_pilot_stage(self) -> None:
        text = _read(DOCS / "orchestration.md")
        self.assertRegex(text, r"(?i)not a pilot stage")
        self.assertIn("CHART_VERDICT", text)
        self.assertIn("/flow-next:chart", text)

    def test_ralph_not_pilot_stage(self) -> None:
        text = _read(DOCS / "ralph.md")
        self.assertRegex(text, r"(?i)never a pilot stage|Chart is never a pilot stage")


class ChartUsageParity(unittest.TestCase):
    def test_usage_has_compact_chart_section(self) -> None:
        text = _read(PLUGIN / "templates" / "usage.md")
        self.assertIn("## Chart", text)
        self.assertIn("CHART_VERDICT", text)
        self.assertIn("chart frontier", text)
        self.assertIn(".D", text)


class ChartChangelogEntry(unittest.TestCase):
    """The chart entry must exist and keep its co-tenants, in whichever
    section currently holds it: `## Unreleased` before the release, the
    versioned section after `bump.sh` promotes it. Pinning `## Unreleased`
    would fail the release commit itself."""

    def test_top_section_has_chart_entry_and_preserves_prior(self) -> None:
        text = _read(REPO_ROOT / "CHANGELOG.md")
        first_heading = re.search(r"^## .+", text, re.MULTILINE)
        self.assertIsNotNone(first_heading)
        heading = first_heading.group(0)
        self.assertRegex(
            heading,
            r"^## (Unreleased|\[flow-next \d+\.\d+\.\d+\] - \d{4}-\d{2}-\d{2})$",
            "the top changelog section must be Unreleased or a released version",
        )
        # The chart entry lives in its own release section, with the co-tenants
        # that shipped alongside it. Anchor on the version, not on position -
        # every later release pushes 3.13.0 down, and that is not a regression.
        shipped = re.search(
            r"^## \[flow-next 3\.13\.0\].*?(?=\n## |\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(shipped, "the flow-next 3.13.0 section must survive")
        section = shipped.group(0)
        self.assertRegex(section, r"(?i)/flow-next:chart")
        self.assertRegex(section, r"(?i)fn-135")
        self.assertIn("#279", section)
        self.assertIn("Review sidecar write transaction", section)


class ChartGuideOptionality(unittest.TestCase):
    def test_destination_test_documented(self) -> None:
        """Chart's entry condition is destination-known/route-unknown.

        A theme or direction has no nameable end state, so no Outcome can be
        stated and no boundary can rule anything out of scope. Both the chart
        skill and the guide matrix must name that refusal, and the chart skill
        must carry the verdict a driver greps for.
        """
        skill = _read(CHART_SKILL_DIR / "SKILL.md")
        workflow = _read(CHART_SKILL_DIR / "workflow.md")
        chart_mode = _read(CHART_REFERENCES / "chart-mode.md")
        chart = skill + "\n" + workflow
        guide = _read(SKILLS / "flow-next-guide" / "SKILL.md")
        for label, text in (("chart skill", chart), ("guide skill", guide)):
            self.assertRegex(
                text,
                r"(?i)\bdestination\b",
                f"{label} must name the destination test (destination known, route unknown)",
            )
            self.assertRegex(
                text,
                r"(?i)make X more Y|direction",
                f"{label} must name the direction-not-destination disqualifier",
            )
        # The discriminator stays inline in SKILL.md; the exact refusal verdict
        # a driver greps for moved into the chart-mode reference (Phase 1) that
        # workflow.md routes to for free-form ideas.
        self.assertIn("No nameable destination -> STOP", skill)
        self.assertIn(
            'reason="direction not destination; narrow to one effort or run prospect"',
            chart_mode,
            "chart skill must carry the exact refusal verdict for a direction-only prompt",
        )
        self.assertIn("references/chart-mode.md", workflow)

    def test_guide_skill_optional_chart(self) -> None:
        text = _read(SKILLS / "flow-next-guide" / "SKILL.md")
        self.assertRegex(text, r"(?i)optional")
        self.assertRegex(text, r"(?i)never (?:a )?mandatory")
        lowered = text.lower()
        self.assertTrue(
            "signal absent" in lowered
            or "skip kind" in lowered
            or "despite unresolved risk" in lowered,
            "guide must distinguish optional-because-signal-absent from skipped-despite-risk",
        )


if __name__ == "__main__":
    unittest.main()
