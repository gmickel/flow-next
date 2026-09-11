"""fn-238 R15-R18: interview -> refine rename, the research scope, the why-scout.

Behavior or contract only (G2):
  - the alias stub forwards and is non-triggering (frontmatter flag, Codex
    catalog flag off in the regenerated mirror);
  - `flowctl scope` accepts `research`, has no bank for it, and its write
    policy writes exactly the research section and preserves every canonical
    section;
  - the research skip is decided from the section or plan's findings, in
    refine's reference AND plan's research step (symmetric), with the same
    scout set on both sides;
  - the why-scout is read-only by tools and carries the four tiers;
  - every pointer the new prose names resolves.

Run:
    python3 -m unittest plugins.flow-next.tests.test_refine_rename -v
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
REPO_ROOT = PLUGIN.parent.parent
SKILLS = PLUGIN / "skills"
FLOWCTL = PLUGIN / "scripts" / "flowctl.py"

REFINE = SKILLS / "flow-next-refine"
STUB = SKILLS / "flow-next-interview" / "SKILL.md"
STUB_SHIM = PLUGIN / "commands" / "interview.md"
REFINE_SHIM = PLUGIN / "commands" / "refine.md"
RESEARCH_REF = REFINE / "references" / "research-scope.md"
PLAN_STEPS = SKILLS / "flow-next-plan" / "steps.md"
ROUTE_MATRIX = SKILLS / "flow-next-flow" / "references" / "route-matrix.md"
WHY_SCOUT = PLUGIN / "agents" / "why-scout.md"
TEMPLATE = PLUGIN / "templates" / "spec.md"
CODEX_STUB_YAML = PLUGIN / "codex" / "skills" / "flow-next-interview" / "agents" / "openai.yaml"
CODEX_REFINE_YAML = PLUGIN / "codex" / "skills" / "flow-next-refine" / "agents" / "openai.yaml"

SECTION = "## Resolved via Research"
RESEARCH_SCOUTS = ("docs-scout", "practice-scout", "docs-gap-scout", "memory-scout")
CANONICAL = (
    "Goal & Context",
    "Architecture & Data Models",
    "API Contracts",
    "Edge Cases & Constraints",
    "Acceptance Criteria",
    "Boundaries",
    "Decision Context",
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict[str, str]:
    assert text.startswith("---")
    end = text.index("\n---", 3)
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _flowctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FLOWCTL), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )


def _links(text: str) -> list[str]:
    return re.findall(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)", text)


class AliasStubForwardsAndIsNonTriggering(unittest.TestCase):
    def test_stub_frontmatter_is_non_triggering_and_names_refine(self) -> None:
        fm = _frontmatter(_read(STUB))
        self.assertEqual(fm["name"], "flow-next-interview")
        self.assertEqual(fm["disable-model-invocation"], "true")
        self.assertIn("eprecated", fm["description"])
        self.assertIn("flow-next-refine", fm["description"])
        self.assertIn("flow-next-refine", _read(STUB))

    def test_stub_shim_forwards_to_refine(self) -> None:
        shim = _read(STUB_SHIM)
        self.assertEqual(_frontmatter(shim)["name"], "interview")
        self.assertIn("flow-next-refine", shim)
        self.assertIn("/flow-next:refine", shim)
        refine = _read(REFINE_SHIM)
        self.assertEqual(_frontmatter(refine)["name"], "refine")
        self.assertIn("flow-next-refine", refine)
        self.assertIn("--scope=research", refine)

    def test_codex_catalog_flag_off_for_alias_on_for_refine(self) -> None:
        if not CODEX_STUB_YAML.is_file() or not CODEX_REFINE_YAML.is_file():
            self.skipTest("codex mirror not regenerated")
        self.assertIn("allow_implicit_invocation: false", _read(CODEX_STUB_YAML))
        self.assertIn("allow_implicit_invocation: true", _read(CODEX_REFINE_YAML))

    def test_refine_skill_is_the_canonical_skill(self) -> None:
        fm = _frontmatter(_read(REFINE / "SKILL.md"))
        self.assertEqual(fm["name"], "flow-next-refine")
        self.assertNotIn("disable-model-invocation", fm)
        for bank in ("questions-business.md", "questions-technical.md", "questions-shared.md"):
            self.assertTrue((REFINE / bank).is_file(), bank)


class ResearchScopePlumbing(unittest.TestCase):
    def test_scope_resolve_accepts_research_and_passes_force_through(self) -> None:
        r = _flowctl("scope", "resolve", "--json", "--raw", "fn-1 --scope=research --force")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["scope"], "research")
        self.assertEqual(data["remaining_args"], ["fn-1", "--force"])

    def test_scope_bank_has_no_research_bank(self) -> None:
        r = _flowctl("scope", "bank", "research", "--json")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no question bank", r.stdout + r.stderr)

    def test_write_policy_writes_only_the_research_section(self) -> None:
        r = subprocess.run(
            [sys.executable, str(FLOWCTL), "scope", "write-policy", "research",
             "--current-sections-json", "-"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
            input='{"decision_context_has_h3": true}',
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["writable"], ["Resolved via Research"])
        self.assertEqual(set(data["preserved"]), set(CANONICAL))
        self.assertEqual(data["decision_context"]["writable_h3"], [])
        self.assertEqual(data["placeholder_write"], [])


class ResearchSkipIsSymmetric(unittest.TestCase):
    def test_refine_reference_decides_skip_from_section_or_plan_findings(self) -> None:
        ref = _read(RESEARCH_REF)
        self.assertIn(f"skipped(section present: {SECTION})", ref)
        self.assertIn("skipped(plan findings present on", ref)
        self.assertIn("rerun(--force)", ref)
        self.assertIn("rerun(delta:", ref)
        for scout in RESEARCH_SCOUTS:
            self.assertIn(scout, ref)
        self.assertIn(f"### {RESEARCH_SCOUTS[0]}", ref)
        self.assertRegex(ref, r"[Nn]ot `repo-scout`")
        self.assertIn("Source:", ref)

    def test_refine_skill_routes_research_to_the_reference(self) -> None:
        skill = _read(REFINE / "SKILL.md")
        self.assertIn("references/research-scope.md", skill)
        self.assertIn("--scope=business|technical|both|research", skill)
        self.assertIn(SECTION.lstrip("# "), skill)

    def test_plan_skips_the_same_scouts_and_writes_the_same_section(self) -> None:
        steps = _read(PLAN_STEPS)
        self.assertIn(f"skipped(section present: {SECTION})", steps)
        self.assertIn(SECTION, steps)
        for scout in RESEARCH_SCOUTS:
            self.assertIn(scout, steps)
        self.assertRegex(steps, r"`repo-scout`, `spec-scout`, and Step 3's `flow-gap-analyst` still run")

    def test_template_lists_the_section_as_auxiliary(self) -> None:
        self.assertIn("Resolved via Research", _read(TEMPLATE))

    def test_route_matrix_carries_read_first_and_why_scout_clauses(self) -> None:
        matrix = _read(ROUTE_MATRIX)
        self.assertIn("--scope=research", matrix)
        self.assertIn("Read-first signal", matrix)
        self.assertIn("`why-scout`", matrix)
        self.assertNotIn("/flow-next:interview", matrix)


class WhyScoutIsReadOnly(unittest.TestCase):
    def test_tool_enforced_read_only_and_tiers(self) -> None:
        text = _read(WHY_SCOUT)
        fm = _frontmatter(text)
        self.assertEqual(fm["name"], "why-scout")
        tokens = {t.strip() for t in fm["disallowedTools"].split(",")}
        self.assertEqual(tokens, {"Edit", "Write", "Task"})
        self.assertEqual(fm["readonly"], "true")
        for tier in ("direct", "supported", "inferred", "unknown"):
            self.assertIn(f"**{tier}**", text)
        self.assertIn("git blame", text)
        self.assertIn("may not rewrite", text)

    def test_no_command_shim_for_why_scout(self) -> None:
        self.assertFalse((PLUGIN / "commands" / "why-scout.md").exists())


class PointersResolve(unittest.TestCase):
    def test_relative_links_in_new_prose_resolve(self) -> None:
        for path in (RESEARCH_REF, REFINE / "SKILL.md", STUB, WHY_SCOUT, ROUTE_MATRIX):
            for link in _links(_read(path)):
                if link.startswith("http"):
                    continue
                target = (path.parent / link).resolve()
                self.assertTrue(target.is_file(), f"{path.name}: {link} -> {target}")

    def test_no_canonical_call_site_names_the_old_command(self) -> None:
        # Survivors are the alias stub, the alias shim, changelog/history, and
        # rows that assert the alias; every skill call site says refine.
        offenders = []
        for p in SKILLS.rglob("*.md"):
            if p.is_relative_to(SKILLS / "flow-next-interview"):
                continue
            if "/flow-next:interview" in _read(p):
                offenders.append(str(p.relative_to(PLUGIN)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
