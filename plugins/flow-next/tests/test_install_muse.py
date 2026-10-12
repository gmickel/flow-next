"""fn-293 — Muse Code bundle builder and installer.

Bundle tests drive muse_bundle.py against fixtures and the real plugin.
Installer tests run scripts/install-muse.sh with a fake `muse` on PATH;
skipped on native Windows.

Run:
    python3 -m unittest test_install_muse -q
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))  # flowctl_tracker reachability (test_tracker_package_import guard)
HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
REPO = PLUGIN.parent.parent
INSTALLER = REPO / "scripts" / "install-muse.sh"
BUNDLER = PLUGIN / "scripts" / "lib" / "muse_bundle.py"

_spec = importlib.util.spec_from_file_location("muse_bundle_under_test", BUNDLER)
muse_bundle = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(muse_bundle)

MUSE_TOOLS = {"edit_file", "write_file", "bash"}


def _agent(front: str) -> str:
    return f"---\nname: probe\ndescription: probe\n{front}---\nBody.\n"


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(path.relative_to(root)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


class TranslateAgentTest(unittest.TestCase):
    def test_claude_names_become_muse_names_and_task_is_dropped(self) -> None:
        out = muse_bundle.translate_agent(
            _agent("disallowedTools: Edit, Write, Task\ncolor: blue\n"), "a.md")
        self.assertIn("disallowedTools: edit_file, write_file\n", out)
        self.assertIn("color: blue\n", out)
        self.assertTrue(out.endswith("---\nBody.\n"))

    def test_list_that_empties_drops_the_key(self) -> None:
        out = muse_bundle.translate_agent(_agent("disallowedTools: Task\nmodel: sonnet\n"), "a.md")
        self.assertNotIn("disallowedTools", out)
        self.assertIn("model: sonnet\n", out)

    def test_agent_without_restrictions_is_unchanged(self) -> None:
        text = _agent("model: inherit\n")
        self.assertEqual(muse_bundle.translate_agent(text, "a.md"), text)

    def test_unknown_tool_fails_closed(self) -> None:
        with self.assertRaises(muse_bundle.BundleError) as ctx:
            muse_bundle.translate_agent(_agent("disallowedTools: Edit, NotebookEdit\n"), "a.md")
        self.assertEqual(ctx.exception.name, "UNMAPPED_DISALLOWED_TOOL")

    def test_tools_allowlist_fails_closed(self) -> None:
        with self.assertRaises(muse_bundle.BundleError) as ctx:
            muse_bundle.translate_agent(_agent("tools: Read, Grep\n"), "a.md")
        self.assertEqual(ctx.exception.name, "UNSUPPORTED_TOOLS_KEY")


class BuildRealPluginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.before = _tree_digest(PLUGIN / "agents") + _tree_digest(PLUGIN / "references")
        cls.bundle = Path(cls.tmp.name) / "flow-next"
        muse_bundle.build(PLUGIN, cls.bundle)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_every_agent_restriction_uses_muse_tool_names(self) -> None:
        agents = sorted((self.bundle / "agents").glob("*.md"))
        self.assertEqual(len(agents), len(list((PLUGIN / "agents").glob("*.md"))))
        for agent in agents:
            for line in agent.read_text(encoding="utf-8").splitlines():
                if line.startswith("disallowedTools:"):
                    names = {t.strip() for t in line.split(":", 1)[1].split(",")}
                    self.assertLessEqual(names, MUSE_TOOLS, agent.name)

    def test_read_only_scouts_deny_file_writes(self) -> None:
        text = (self.bundle / "agents" / "repo-scout.md").read_text(encoding="utf-8")
        self.assertIn("disallowedTools: edit_file, write_file\n", text)

    def test_bundle_carries_marker_and_dispatch_note(self) -> None:
        self.assertTrue((self.bundle / muse_bundle.MARKER).is_file())
        rules = (self.bundle / "references" / "working-rules.md").read_text(encoding="utf-8")
        self.assertIn('`subagent_type: "flow-next/<name>"`', rules)

    def test_other_host_files_and_tests_are_left_out(self) -> None:
        for name in ("codex", ".codex-plugin", ".cursor-plugin", "tests"):
            self.assertFalse((self.bundle / name).exists(), name)
        self.assertTrue((self.bundle / ".claude-plugin" / "plugin.json").is_file())
        self.assertEqual(list(self.bundle.rglob("__pycache__")), [])

    def test_canonical_plugin_is_untouched(self) -> None:
        after = _tree_digest(PLUGIN / "agents") + _tree_digest(PLUGIN / "references")
        self.assertEqual(after, self.before)


@unittest.skipIf(os.name == "nt", "POSIX installer")
class InstallerTest(unittest.TestCase):
    def _run(self, muse_script: str | None) -> tuple[subprocess.CompletedProcess, Path, Path]:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        bin_dir, work_tmp, log = tmp / "bin", tmp / "tmp", tmp / "muse.log"
        bin_dir.mkdir()
        work_tmp.mkdir()
        for tool in ("python3", "bash", "mktemp", "rm", "dirname", "sed"):
            found = shutil.which(tool)
            if found:
                (bin_dir / tool).symlink_to(found)
        if muse_script is not None:
            muse = bin_dir / "muse"
            muse.write_text(f"#!/bin/bash\necho \"$*\" >> {log}\n{muse_script}\n", encoding="utf-8")
            muse.chmod(0o755)
        env = {"PATH": str(bin_dir), "HOME": str(tmp), "TMPDIR": str(work_tmp)}
        proc = subprocess.run(["bash", str(INSTALLER)], env=env, capture_output=True,
                              text=True, timeout=120)
        return proc, work_tmp, log

    def test_installs_then_approves_and_removes_the_bundle(self) -> None:
        proc, work_tmp, log = self._run(
            'if [ "$1 $2" = "plugins install" ]; then test -f "$3/.flow-next-muse-bundle" || exit 9; fi')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        calls = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0].startswith("plugins install ") and calls[0].endswith(" --scope user"))
        self.assertEqual(calls[1], "plugins approve flow-next")
        self.assertEqual(list(work_tmp.iterdir()), [])

    def test_failed_install_exits_nonzero_and_cleans_up(self) -> None:
        proc, work_tmp, log = self._run('echo "install refused" >&2; exit 3')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("muse plugins install failed", proc.stderr)
        self.assertEqual(log.read_text(encoding="utf-8").count("plugins approve"), 0)
        self.assertEqual(list(work_tmp.iterdir()), [])

    def test_missing_muse_is_a_clear_error(self) -> None:
        proc, work_tmp, _ = self._run(None)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("muse not found on PATH", proc.stderr)
        self.assertEqual(list(work_tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
