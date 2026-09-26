"""Model-side invocations name skill ids; command shims are user-only (fn-258 R6).

Every command shim carries `disable-model-invocation: true`, so an agent can
no longer reach a flow-next skill through its command form. Model-side
invocations therefore name the skill id (`flow-next:flow-next-<name>`); this
test resolves every such target in the canonical sources to an existing,
model-invocable skill, and pins the skill-id token at the dispatch sites the
spec names (flow --auto's stage dispatch, flow's land hand-off, work's
completion-review call, the worker's impl-review call, the setup snippet).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL_ID = re.compile(r"(?<![/\w$])flow-next:flow-next-([a-z][a-z-]*[a-z])")
SOURCE_DIRS = ("skills", "agents", "references", "templates")


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    return text[4 : text.index("\n---\n", 4)]


def _model_invocable(skill_dir: Path) -> bool:
    fields = _frontmatter(skill_dir / "SKILL.md").splitlines()
    return "disable-model-invocation: true" not in fields


class SkillIdInvocationTest(unittest.TestCase):
    def test_every_command_shim_disables_model_invocation(self) -> None:
        shims = sorted((PLUGIN / "commands").glob("*.md"))
        self.assertTrue(shims)
        for shim in shims:
            with self.subTest(shim=shim.name):
                self.assertIn(
                    "disable-model-invocation: true",
                    _frontmatter(shim).splitlines(),
                )

    def test_every_skill_id_target_is_a_model_invocable_skill(self) -> None:
        targets: dict[str, list[str]] = {}
        for top in SOURCE_DIRS:
            for path in (PLUGIN / top).rglob("*.md"):
                rel = path.relative_to(PLUGIN).as_posix()
                for name in SKILL_ID.findall(path.read_text(encoding="utf-8")):
                    targets.setdefault(name, []).append(rel)
        self.assertTrue(targets)
        for name, sites in sorted(targets.items()):
            with self.subTest(skill=name, first_site=sites[0]):
                skill_dir = PLUGIN / "skills" / f"flow-next-{name}"
                self.assertTrue((skill_dir / "SKILL.md").is_file())
                self.assertTrue(_model_invocable(skill_dir))

    def test_named_dispatch_sites_use_skill_ids(self) -> None:
        sites = [
            ("skills/flow-next-flow/auto.md", ["plan", "plan-review", "work", "qa", "make-pr", "land", "tracker-sync"]),
            ("skills/flow-next-flow/references/tail.md", ["land"]),
            ("skills/flow-next-work/phases.md", ["spec-completion-review"]),
            ("agents/worker.md", ["impl-review"]),
            ("skills/flow-next-setup/templates/claude-md-snippet.md", ["plan", "prose", "setup"]),
        ]
        for rel, skills in sites:
            found = set(SKILL_ID.findall((PLUGIN / rel).read_text(encoding="utf-8")))
            for skill in skills:
                with self.subTest(site=rel, skill=skill):
                    self.assertIn(skill, found)


if __name__ == "__main__":
    unittest.main()
