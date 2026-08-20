"""fn-201.3 / R3 — OpenCode agent frontmatter translation.

Generator fixtures: canonical-shaped agent -> pinned-schema frontmatter
(including a Bash-carrying agent) and the three fail-closed cases.
Invariant over the live canonical agents dir: every disallowedTools token
must have a mapping (style: test_cursor_agent_frontmatter.py). Does not
assert live skill/agent prose.

Run:
    python3 -m unittest test_opencode_agent_frontmatter -q
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))  # flowctl_tracker reachability (test_tracker_package_import guard)
HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
AGENTS_DIR = PLUGIN / "agents"
GENERATOR = PLUGIN / "scripts" / "lib" / "opencode_generate.py"
FIXTURES = HERE.parent / "fixtures" / "opencode-install"


def _load_generate() -> Any:
    spec = importlib.util.spec_from_file_location(
        "opencode_generate_under_test", GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GENERATOR}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _agent_mds(dest: Path) -> list[Path]:
    agents = dest / "agents"
    if not agents.is_dir():
        return []
    return sorted(p for p in agents.glob("*.md") if p.is_file())


class TestOpencodeAgentFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gen = _load_generate()

    def _generate_one(self, src_name: str, dest: Path, paths: Path) -> None:
        src = Path(dest).parent / "src-agents"
        src.mkdir()
        shutil.copy(FIXTURES / "agents" / src_name, src / src_name)
        self.gen.generate_agents(src, dest, paths)

    def test_happy_scout_matches_pinned_schema_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            self._generate_one("happy-scout.md", dest, paths)
            got = (dest / "agents" / "flow-next-happy-scout.md").read_bytes()
            expected = (FIXTURES / "expected" / "happy-scout.md").read_bytes()
            self.assertEqual(got, expected)
            text = got.decode("utf-8")
            self.assertIn("mode: subagent", text)
            self.assertNotIn("tools:", text)
            self.assertNotIn("name:", text.split("---", 2)[1])
            self.assertNotIn("model:", text.split("---", 2)[1])
            self.assertNotIn("readonly:", text.split("---", 2)[1])

    def test_happy_bash_carrying_agent_maps_bash_deny(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            self._generate_one("happy-bash.md", dest, paths)
            got = (dest / "agents" / "flow-next-happy-bash.md").read_bytes()
            expected = (FIXTURES / "expected" / "happy-bash.md").read_bytes()
            self.assertEqual(got, expected)
            self.assertIn(b"bash: deny", got)
            self.assertIn(b"mode: subagent", got)

    def test_fail_closed_unmapped_token_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            with self.assertRaises(self.gen.GenerateError) as cm:
                self._generate_one("fail-unmapped.md", dest, paths)
            self.assertEqual(cm.exception.name, "UNMAPPED_DISALLOWED_TOOL")
            self.assertIn("NotebookEdit", cm.exception.detail)
            self.assertEqual(_agent_mds(dest), [])

    def test_fail_closed_unrepresentable_denial_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            src = Path(tmp) / "src-agents"
            src.mkdir()
            shutil.copy(FIXTURES / "agents" / "happy-scout.md", src / "happy-scout.md")
            with mock.patch.dict(
                self.gen.DISALLOWED_TO_PERMISSION, {"Edit": "not_a_permission_key"}
            ):
                with self.assertRaises(self.gen.GenerateError) as cm:
                    self.gen.generate_agents(src, dest, paths)
            self.assertEqual(cm.exception.name, "UNREPRESENTABLE_DENIAL")
            self.assertEqual(_agent_mds(dest), [])

    def test_fail_closed_readonly_disagreement_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            with self.assertRaises(self.gen.GenerateError) as cm:
                self._generate_one("fail-readonly.md", dest, paths)
            self.assertEqual(
                cm.exception.name, "READONLY_DISALLOWEDTOOLS_DISAGREEMENT"
            )
            self.assertEqual(_agent_mds(dest), [])

    def test_fail_closed_mixed_dir_emits_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "dest"
            paths = Path(tmp) / "paths"
            src = Path(tmp) / "src-agents"
            src.mkdir()
            shutil.copy(FIXTURES / "agents" / "happy-scout.md", src / "happy-scout.md")
            shutil.copy(
                FIXTURES / "agents" / "fail-unmapped.md", src / "fail-unmapped.md"
            )
            with self.assertRaises(self.gen.GenerateError) as cm:
                self.gen.generate_agents(src, dest, paths)
            self.assertEqual(cm.exception.name, "UNMAPPED_DISALLOWED_TOOL")
            self.assertEqual(_agent_mds(dest), [])


class TestCanonicalDisallowedToolsMapping(unittest.TestCase):
    """Fails when a live canonical agent carries an unmapped token."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.gen = _load_generate()
        cls.agent_files = sorted(
            p for p in AGENTS_DIR.glob("*.md") if p.is_file() and not p.name.startswith(".")
        )
        assert cls.agent_files, f"no agents under {AGENTS_DIR}"

    def test_agents_directory_has_expected_population(self) -> None:
        self.assertGreaterEqual(len(self.agent_files), 10)

    def test_every_canonical_disallowed_token_has_a_mapping(self) -> None:
        unmapped: list[str] = []
        for path in self.agent_files:
            text = path.read_text(encoding="utf-8")
            fields, _body = self.gen.split_frontmatter(text, path)
            tokens = self.gen.parse_disallowed_tools(
                fields.get("disallowedTools", "")
            )
            for token in tokens:
                if token not in self.gen.DISALLOWED_TO_PERMISSION:
                    unmapped.append(f"{path.name}: {token!r}")
        self.assertEqual(
            unmapped,
            [],
            "canonical agents/*.md carries a disallowedTools token with no "
            "OpenCode mapping in DISALLOWED_TO_PERMISSION:\n  "
            + "\n  ".join(unmapped),
        )


if __name__ == "__main__":
    unittest.main()
