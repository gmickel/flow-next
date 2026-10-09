"""Contract checks for /flow-next:flow and its shared routing reference.

Reachability only: every file in references/ is reached from the always-loaded
files, auto.md, or a reached reference; every reference link from the
always-loaded files and auto.md resolves; every consumer pointer names a
reference file that exists; the shim and skill frontmatter names that hosts
invoke are intact.

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
FLOW_AUTO = FLOW_DIR / "auto.md"
FLOW_REFERENCES = FLOW_DIR / "references"
FLOW_SHIM = PLUGIN / "commands" / "flow.md"

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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


class FlowSurfaceExists(unittest.TestCase):

    def test_no_orphan_reference(self) -> None:
        # Every file in references/ is reached: from SKILL.md or
        # auto.md, or linked from a reference that is itself reached.
        reached: set[str] = set()
        frontier = [FLOW_SKILL, FLOW_AUTO]
        while frontier:
            text = _read(frontier.pop())
            for name in set(LOCAL_REF_MENTION_RE.findall(text)) | set(
                re.findall(r"\]\(([A-Za-z0-9_.-]+\.md)(?:#[^)]*)?\)", text)
            ):
                if name not in reached and (FLOW_REFERENCES / name).is_file():
                    reached.add(name)
                    frontier.append(FLOW_REFERENCES / name)
        on_disk = {p.name for p in FLOW_REFERENCES.glob("*.md")}
        self.assertEqual(on_disk - reached, set(), "unreachable references")

    def test_shim_frontmatter(self) -> None:
        text = _read(FLOW_SHIM)
        fm = _frontmatter(text)
        self.assertRegex(fm, r"(?m)^name:\s*flow\s*$", "shim name must be the bare `flow`")
        m = re.search(r"(?m)^description:\s*(.+?)\s*$", fm)
        self.assertIsNotNone(m, "shim description missing")
        self.assertTrue(m.group(1).strip(), "shim description must be non-empty")
        self.assertIn("flow-next-flow", text)

    def test_skill_frontmatter_name(self) -> None:
        fm = _frontmatter(_read(FLOW_SKILL))
        self.assertRegex(fm, r"(?m)^name:\s*flow-next-flow\s*$")


class FlowReferenceReachability(unittest.TestCase):
    def test_every_local_reference_link_resolves(self) -> None:
        for path in (FLOW_SKILL,):
            text = _read(path)
            for rel in LOCAL_REF_LINK_RE.findall(text):
                with self.subTest(file=path.name, link=rel):
                    self.assertTrue(
                        (FLOW_DIR / rel).is_file(),
                        f"{path.name} links {rel} which does not exist",
                    )

    def test_gated_work_references_are_linked_from_their_readers(self) -> None:
        # Its matrix row routes to each gated reference and the worker reads it; every link resolves.
        # The matrix rows span route-matrix.md and its continuation file.
        matrix = (FLOW_REFERENCES / "route-matrix.md", FLOW_REFERENCES / "route-matrix-more.md")
        worker = PLUGIN / "agents" / "worker.md"
        for name in ("defect-route.md", "hill-climb.md"):
            for label, readers in (("route matrix", matrix), ("worker.md", (worker,))):
                found = []
                for reader in readers:
                    for rel in re.findall(r"\]\(([^)#]*" + re.escape(name) + r")\)", _read(reader)):
                        found.append(rel)
                        self.assertTrue((reader.parent / rel).resolve().is_file(), f"{reader.name} links {rel}")
                with self.subTest(reference=name, reader=label):
                    self.assertTrue(found, f"{label} does not link {name}")

    def test_every_auto_md_reference_link_resolves(self) -> None:
        for rel in LOCAL_REF_LINK_RE.findall(_read(FLOW_AUTO)):
            with self.subTest(link=rel):
                self.assertTrue((FLOW_DIR / rel).is_file(), f"auto.md links {rel} which does not exist")


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


if __name__ == "__main__":
    unittest.main()
