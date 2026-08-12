"""Prose contract for the /flow-next:visual digest skill (fn-189.5).

Pins CONTENT and REACHABILITY, per the repo's prose-contract heuristic:
what the skill must carry, and the link that makes a contract's home file
reachable from its skill's entry point. Location is pinned only where it is
load-bearing (the shim frontmatter name, the make-pr sketch section).

No stored-hash pins, no size ceilings, no sentence-level prose assertions.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_visual_skill -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

SKILL_DIR = PLUGIN / "skills" / "flow-next-visual"
SKILL_MD = SKILL_DIR / "SKILL.md"
SHIM = PLUGIN / "commands" / "visual.md"

CAPTURE_SKILL = PLUGIN / "skills" / "flow-next-capture" / "SKILL.md"
CAPTURE_WORKFLOW = PLUGIN / "skills" / "flow-next-capture" / "workflow.md"
PLAN_SKILL = PLUGIN / "skills" / "flow-next-plan" / "SKILL.md"
PLAN_STEPS = PLUGIN / "skills" / "flow-next-plan" / "steps.md"
INTERVIEW_SKILL = PLUGIN / "skills" / "flow-next-interview" / "SKILL.md"

MAKE_PR_DIR = PLUGIN / "skills" / "flow-next-make-pr"
MAKE_PR_WORKFLOW = MAKE_PR_DIR / "workflow.md"
MERMAID_RULES = MAKE_PR_DIR / "mermaid-rules.md"

CONDUCT_VISUAL = REPO_ROOT / "agent_docs" / "conduct" / "visual.md"
CONDUCT_README = REPO_ROOT / "agent_docs" / "conduct" / "README.md"

# Natural-language triggers R1 requires in the skill description so the skill
# fires without the slash command.
TRIGGER_PHRASES = (
    "show me",
    "explain this visually",
    "restate that",
    "digest the plan",
    "walk me through",
    "too much text",
)

# The eight vocabulary shapes (R2). Each entry: (label, content probes).
SHAPE_PROBES = {
    "1 pseudocode": ("Pseudocode",),
    "2 call tree": ("Call tree",),
    "3 component tree": ("Component tree", "```tsx"),
    "4 file tree": ("file tree",),
    "5 diff-fenced sketch": ("Diff-fenced structural sketch", "```diff"),
    "6 types and signatures": ("Types and signatures", "```ts"),
    "7 compact table": ("Compact table",),
    "8 mermaid last resort": ("Mermaid", "LAST resort"),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _skill_dir_prose() -> str:
    return "\n".join(_read(p) for p in sorted(SKILL_DIR.rglob("*.md")))


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body) for a markdown file with YAML frontmatter."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m is not None, "file has no YAML frontmatter"
    return m.group(1), text[m.end() :]


def _frontmatter(text: str) -> str:
    return _split_frontmatter(text)[0]


class VisualSkillFiles(unittest.TestCase):
    def test_skill_and_shim_exist(self) -> None:
        self.assertTrue(SKILL_MD.is_file(), f"missing {SKILL_MD}")
        self.assertTrue(SHIM.is_file(), f"missing {SHIM}")


class VisualShimContract(unittest.TestCase):
    def test_shim_bare_colon_free_name_and_description(self) -> None:
        front = _frontmatter(_read(SHIM))
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        self.assertIsNotNone(name, "shim frontmatter has no name")
        value = name.group(1).strip().strip("\"'")
        self.assertEqual(
            value,
            "visual",
            "shim name must be the bare, colon-free command name",
        )
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        self.assertIsNotNone(desc, "shim frontmatter has no description")
        self.assertTrue(
            desc.group(1).strip().strip("\"'"),
            "shim description must be non-empty",
        )

    def test_shim_invokes_the_skill(self) -> None:
        self.assertIn("flow-next-visual", _read(SHIM))


class VisualSkillDescription(unittest.TestCase):
    def test_description_carries_natural_language_triggers(self) -> None:
        description = _frontmatter(_read(SKILL_MD)).lower()
        for phrase in TRIGGER_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(
                    phrase,
                    description,
                    "skill description must carry the natural-language trigger "
                    f"{phrase!r} so plain language invokes the skill",
                )

    def test_description_names_the_four_targets(self) -> None:
        description = _frontmatter(_read(SKILL_MD)).lower()
        for target in ("spec", "task", "diff", "topic"):
            with self.subTest(target=target):
                self.assertIn(target, description)


class VisualOutputContract(unittest.TestCase):
    def test_body_states_markdown_chat_output_not_images_or_html(self) -> None:
        """R1: the contract lives in the BODY, not the trigger description."""
        _, body = _split_frontmatter(_read(SKILL_MD))
        self.assertRegex(body, re.compile(r"compact markdown", re.I))
        self.assertRegex(body, re.compile(r"never images|Never images", re.I))
        self.assertRegex(body, re.compile(r"HTML", re.I))

    def test_read_only_and_grounding_rules_present(self) -> None:
        prose = _skill_dir_prose()
        self.assertRegex(prose, re.compile(r"read-only", re.I))
        self.assertRegex(prose, re.compile(r"never writes|never write", re.I))
        self.assertIn("satisfies", prose)
        self.assertRegex(prose, re.compile(r"never invented|no invented", re.I))


class VisualShapeVocabulary(unittest.TestCase):
    def test_all_eight_shapes_present_in_skill_dir(self) -> None:
        prose = _skill_dir_prose()
        for label, probes in SHAPE_PROBES.items():
            for probe in probes:
                with self.subTest(shape=label, probe=probe):
                    self.assertIn(
                        probe,
                        prose,
                        f"shape vocabulary entry {label} missing probe {probe!r}",
                    )

    def test_selection_and_trimming_rules_present(self) -> None:
        prose = _skill_dir_prose()
        self.assertRegex(prose, re.compile(r"smallest", re.I))
        self.assertRegex(prose, re.compile(r"one or a few", re.I))
        self.assertRegex(prose, re.compile(r"Whole-block rule", re.I))
        self.assertRegex(prose, re.compile(r"Trimming rule", re.I))


class VisualCloserOffers(unittest.TestCase):
    """R4: capture, plan, interview each offer the digest at their read-back."""

    def test_capture_closer_offers_digest_and_is_reachable(self) -> None:
        self.assertIn("/flow-next:visual", _read(CAPTURE_WORKFLOW))
        self.assertIn("workflow.md", _read(CAPTURE_SKILL))

    def test_plan_closer_offers_digest_and_is_reachable(self) -> None:
        steps = _read(PLAN_STEPS)
        self.assertIn("/flow-next:visual", steps)
        self.assertRegex(steps, re.compile(r"never run for them|offer", re.I))
        self.assertIn("steps.md", _read(PLAN_SKILL))

    def test_interview_closer_offers_digest(self) -> None:
        self.assertIn("/flow-next:visual", _read(INTERVIEW_SKILL))


class MakePrSketchClause(unittest.TestCase):
    """R5: the sketch is licensed in mermaid-rules and reachable from Phase 3."""

    def test_sketch_section_lives_in_mermaid_rules(self) -> None:
        rules = _read(MERMAID_RULES)
        self.assertIn("Diff-fenced structural sketches", rules)
        self.assertIn("```diff", rules)
        # Licensed situations, inherited guardrails, and --no-mermaid semantics.
        self.assertRegex(rules, re.compile(r"collapse-to-one", re.I))
        self.assertRegex(rules, re.compile(r"marginal", re.I))
        self.assertIn("--no-mermaid", rules)

    def test_phase_three_reaches_the_sketch_clause(self) -> None:
        workflow = _read(MAKE_PR_WORKFLOW)
        self.assertIn("mermaid-rules.md", workflow)
        self.assertRegex(workflow, re.compile(r"sketch", re.I))


class VisualConductChecklist(unittest.TestCase):
    """R8: maintainer doc exists, indexed, and never referenced at runtime."""

    def test_conduct_page_exists_and_is_indexed(self) -> None:
        self.assertTrue(CONDUCT_VISUAL.is_file(), f"missing {CONDUCT_VISUAL}")
        readme = _read(CONDUCT_README)
        self.assertIn("(visual.md)", readme)
        self.assertIn("/flow-next:visual", readme)

    def test_skill_files_never_reference_the_conduct_page(self) -> None:
        prose = _skill_dir_prose() + "\n" + _read(SHIM)
        self.assertNotIn("conduct/", prose)
        self.assertNotIn("agent_docs", prose)


if __name__ == "__main__":
    unittest.main()
