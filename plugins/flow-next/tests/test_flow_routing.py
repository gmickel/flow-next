"""Contract checks for /flow-next:flow and its shared routing reference (fn-238).

Behavior and contract only (G2): the skill, shim, and six reference files
exist; every reference opens with a decision record; every reference link from
the always-loaded files resolves and every reference is reachable; every
consumer pointer names a reference file that exists; the retired guide skill
is named nowhere on a canonical surface; the autonomy refusal line and the
--explain token are present.

Run:
    cd plugins/flow-next/tests && python3 -m unittest test_flow_routing -q
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
REPO_ROOT = PLUGIN.parent.parent

FLOW_DIR = PLUGIN / "skills" / "flow-next-flow"
FLOW_SKILL = FLOW_DIR / "SKILL.md"
FLOW_WORKFLOW = FLOW_DIR / "workflow.md"
FLOW_REFERENCES = FLOW_DIR / "references"
FLOW_SHIM = PLUGIN / "commands" / "flow.md"

REFERENCE_NAMES = (
    "route-matrix.md",
    "spec-count.md",
    "plan-vs-no-plan.md",
    "gate-selection.md",
    "prototype-before-ask.md",
    "tail.md",
)

DECISION_RECORD_ITEMS = ("Source", "Trigger", "Purpose", "Evidence", "Disposition")

# Consumers that point at the shared routing reference. A consumer with no
# pointer yet is skipped (it is being edited elsewhere); a pointer that names
# a missing file fails.
CONSUMER_FILES = (
    PLUGIN / "skills" / "flow-next-capture" / "workflow.md",
    PLUGIN / "skills" / "flow-next-capture" / "references" / "split-proposal.md",
    PLUGIN / "skills" / "flow-next-plan" / "references" / "next-steps-menu.md",
    PLUGIN / "skills" / "flow-next-work" / "references" / "no-plan-route.md",
    PLUGIN / "docs" / "pipeline-variations.md",
    PLUGIN / "docs" / "read-back.md",
)

# Tolerant to `../../flow-next-flow/references/x.md`,
# `skills/flow-next-flow/references/x.md`, and bare `references/x.md` inside
# the flow skill itself.
POINTER_RE = re.compile(r"flow-next-flow/references/([A-Za-z0-9_.-]+\.md)")
LOCAL_REF_LINK_RE = re.compile(r"\]\((references/[A-Za-z0-9_.-]+\.md)(?:#[^)]*)?\)")
LOCAL_REF_MENTION_RE = re.compile(r"references/([A-Za-z0-9_.-]+\.md)")

# Canonical surfaces that must not name the retired guide skill.
GUIDE_RE = re.compile(r"flow-next-guide|/flow-next:guide")
CANONICAL_ROOTS = (
    PLUGIN / "skills",
    PLUGIN / "commands",
    PLUGIN / "agents",
    PLUGIN / "templates",
    PLUGIN / "docs",
    REPO_ROOT / "README.md",
    REPO_ROOT / "agent_docs",
)
EXCLUDED_PARTS = ("archive", "optimization", "codex", ".flow")
# Append-only release history keeps the names of retired commands as history,
# the same way CHANGELOG.md does; a historical mention is not a pointer.
EXCLUDED_FILES = ("release-history.md",)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


class FlowSurfaceExists(unittest.TestCase):
    def test_skill_workflow_shim_and_references_exist(self) -> None:
        for path in (FLOW_SKILL, FLOW_WORKFLOW, FLOW_SHIM):
            self.assertTrue(path.is_file(), f"missing {path.relative_to(REPO_ROOT)}")
        for name in REFERENCE_NAMES:
            path = FLOW_REFERENCES / name
            self.assertTrue(path.is_file(), f"missing {path.relative_to(REPO_ROOT)}")
        extra = sorted(p.name for p in FLOW_REFERENCES.glob("*.md"))
        self.assertEqual(
            extra,
            sorted(REFERENCE_NAMES),
            "the routing reference is exactly six files, one per rule",
        )

    def test_shim_frontmatter(self) -> None:
        text = _read(FLOW_SHIM)
        fm = _frontmatter(text)
        self.assertRegex(fm, r"(?m)^name:\s*flow\s*$", "shim name must be the bare `flow`")
        m = re.search(r"(?m)^description:\s*(.+?)\s*$", fm)
        self.assertIsNotNone(m, "shim description missing")
        self.assertTrue(m.group(1).strip(), "shim description must be non-empty")
        self.assertIn("flow-next-flow", text)
        self.assertNotIn("request_user_input", text)

    def test_skill_frontmatter_name(self) -> None:
        fm = _frontmatter(_read(FLOW_SKILL))
        self.assertRegex(fm, r"(?m)^name:\s*flow-next-flow\s*$")


class FlowReferenceDecisionRecords(unittest.TestCase):
    def test_every_reference_opens_with_a_decision_record(self) -> None:
        for name in REFERENCE_NAMES:
            with self.subTest(reference=name):
                text = _read(FLOW_REFERENCES / name)
                marker = text.find("**Decision record**")
                self.assertGreater(marker, -1, f"{name} lacks a decision record marker")
                # The record is the first thing after the title.
                head = text[:marker]
                self.assertNotIn("\n## ", head, f"{name}: decision record must precede any section")
                body = text[marker:]
                first_section = body.find("\n## ")
                record = body if first_section < 0 else body[:first_section]
                last = -1
                for item in DECISION_RECORD_ITEMS:
                    pos = record.find(f"- {item}:")
                    self.assertGreater(pos, -1, f"{name}: decision record lacks `{item}`")
                    self.assertGreater(pos, last, f"{name}: decision record items out of order at `{item}`")
                    last = pos


class FlowReferenceReachability(unittest.TestCase):
    def test_every_local_reference_link_resolves(self) -> None:
        for path in (FLOW_SKILL, FLOW_WORKFLOW):
            text = _read(path)
            for rel in LOCAL_REF_LINK_RE.findall(text):
                with self.subTest(file=path.name, link=rel):
                    self.assertTrue(
                        (FLOW_DIR / rel).is_file(),
                        f"{path.name} links {rel} which does not exist",
                    )

    def test_every_reference_is_reachable_from_always_loaded_prose(self) -> None:
        combined = _read(FLOW_SKILL) + "\n" + _read(FLOW_WORKFLOW)
        mentioned = set(LOCAL_REF_MENTION_RE.findall(combined))
        for name in REFERENCE_NAMES:
            with self.subTest(reference=name):
                self.assertIn(
                    name,
                    mentioned,
                    f"references/{name} is not reachable from SKILL.md or workflow.md",
                )
        unknown = mentioned - set(REFERENCE_NAMES)
        self.assertEqual(unknown, set(), f"always-loaded prose names unknown references: {sorted(unknown)}")


class ConsumerPointersResolve(unittest.TestCase):
    def test_every_consumer_pointer_names_an_existing_reference(self) -> None:
        for path in CONSUMER_FILES:
            if not path.is_file():
                continue
            names = set(POINTER_RE.findall(_read(path)))
            for name in sorted(names):
                with self.subTest(consumer=path.relative_to(REPO_ROOT).as_posix(), reference=name):
                    self.assertTrue(
                        (FLOW_REFERENCES / name).is_file(),
                        f"{path.relative_to(REPO_ROOT)} points at references/{name}, which does not exist",
                    )

    def test_flow_skill_itself_links_all_six(self) -> None:
        combined = _read(FLOW_SKILL) + "\n" + _read(FLOW_WORKFLOW)
        mentioned = set(LOCAL_REF_MENTION_RE.findall(combined))
        self.assertTrue(set(REFERENCE_NAMES) <= mentioned, f"flow skill misses {set(REFERENCE_NAMES) - mentioned}")


class GuideRetired(unittest.TestCase):
    def test_guide_skill_surfaces_are_gone(self) -> None:
        self.assertFalse((PLUGIN / "skills" / "flow-next-guide").exists())
        self.assertFalse((PLUGIN / "commands" / "guide.md").exists())
        self.assertFalse((REPO_ROOT / "agent_docs" / "conduct" / "guide.md").exists())

    def test_no_canonical_surface_names_guide(self) -> None:
        offenders: list[str] = []
        for root in CANONICAL_ROOTS:
            paths = [root] if root.is_file() else sorted(root.rglob("*.md"))
            for path in paths:
                if not path.is_file():
                    continue
                rel = path.relative_to(REPO_ROOT)
                if any(part in EXCLUDED_PARTS for part in rel.parts):
                    continue
                if rel.name in EXCLUDED_FILES:
                    continue
                for lineno, line in enumerate(_read(path).splitlines(), 1):
                    if GUIDE_RE.search(line):
                        offenders.append(f"{rel.as_posix()}:{lineno}: {line.strip()[:120]}")
        self.assertEqual(
            offenders,
            [],
            "canonical surfaces still name the retired guide skill:\n" + "\n".join(offenders),
        )


class FlowInvariantTokens(unittest.TestCase):
    def test_autonomy_refusal_line_present(self) -> None:
        self.assertIn("NEEDS_HUMAN:", _read(FLOW_SKILL))

    def test_explain_token_documented(self) -> None:
        text = _read(FLOW_SKILL)
        self.assertIn("--explain", text, "the skill body must document the --explain token")
        self.assertIn("EXPLAIN=1", text, "mode detection must bind the --explain token")


if __name__ == "__main__":
    unittest.main()
