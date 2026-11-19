"""fn-341 — Antigravity CLI bundle builder and installer.

Bundle tests drive antigravity_bundle.py against fixtures and the real plugin.
Installer tests run scripts/install-antigravity.sh with a fake `agy` on PATH;
skipped on native Windows.

Run:
    python3 -m unittest test_install_antigravity -q
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
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
INSTALLER = REPO / "scripts" / "install-antigravity.sh"
BUNDLER = PLUGIN / "scripts" / "lib" / "antigravity_bundle.py"

_spec = importlib.util.spec_from_file_location("antigravity_bundle_under_test", BUNDLER)
antigravity_bundle = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(antigravity_bundle)

TIERS = {"inherit", "flash_lite", "flash", "pro"}
WRITE_TOOLS = {"edit_file", "write_file"}
ALL_TOOLS = ["run_command", "read_file", "search_web", "edit_file", "write_file",
             "invoke_subagent", "ask_question"]


def _agent(front: str) -> str:
    return f"---\nname: probe\ndescription: probe\n{front}---\nBody.\n"


def _front(text: str) -> dict[str, str]:
    end = text.index("\n---", 4)
    return dict(line.split(":", 1) for line in text[4:end].splitlines()
                if ":" in line and not line.startswith("#"))


def _tools(text: str) -> list[str]:
    match = re.search(r"^tools: \[(.*)\]$", text, re.M)
    assert match, text
    return [t.strip() for t in match.group(1).split(",")]


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(path.relative_to(root)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


class TranslateAgentTest(unittest.TestCase):
    def test_read_only_scout_gets_tier_and_read_tools(self) -> None:
        out = antigravity_bundle.translate_agent(
            _agent("model: sonnet\ndisallowedTools: Edit, Write, Task\ncolor: blue\n"), "a.md")
        self.assertIn("model: flash\n", out)
        self.assertEqual(_tools(out), ["run_command", "read_file", "search_web"])
        self.assertNotIn("disallowedTools", out)
        self.assertIn("color: blue\n", out)
        self.assertTrue(out.endswith("---\nBody.\n"))

    def test_edit_only_agent_keeps_edit_but_not_write_or_dispatch(self) -> None:
        out = antigravity_bundle.translate_agent(
            _agent("disallowedTools: Write, Task\nmodel: sonnet\n"), "a.md")
        self.assertEqual(_tools(out), ["run_command", "read_file", "search_web", "edit_file"])

    def test_unrestricted_agent_gets_every_tool(self) -> None:
        out = antigravity_bundle.translate_agent(_agent("model: inherit\n"), "a.md")
        self.assertIn("model: inherit\n", out)
        self.assertEqual(_tools(out), ALL_TOOLS)

    def test_opus_maps_to_pro(self) -> None:
        out = antigravity_bundle.translate_agent(
            _agent("model: opus\ndisallowedTools: Edit, Write, Task\n"), "a.md")
        self.assertIn("model: pro\n", out)

    def test_unmapped_model_fails_closed_by_name(self) -> None:
        for front in ("model: haiku\n", "model: claude-opus-5-5\n", "color: red\n"):
            with self.subTest(front=front):
                with self.assertRaises(antigravity_bundle.BundleError) as ctx:
                    antigravity_bundle.translate_agent(_agent(front), "odd-agent.md")
                self.assertEqual(ctx.exception.name, "UNMAPPED_MODEL")
                self.assertIn("odd-agent.md", str(ctx.exception))

    def test_unknown_tool_fails_closed_by_name(self) -> None:
        with self.assertRaises(antigravity_bundle.BundleError) as ctx:
            antigravity_bundle.translate_agent(
                _agent("model: sonnet\ndisallowedTools: Edit, NotebookEdit\n"), "a.md")
        self.assertEqual(ctx.exception.name, "UNMAPPED_DISALLOWED_TOOL")
        self.assertIn("NotebookEdit", str(ctx.exception))

    def test_tools_allowlist_fails_closed(self) -> None:
        with self.assertRaises(antigravity_bundle.BundleError) as ctx:
            antigravity_bundle.translate_agent(_agent("model: sonnet\ntools: Read, Grep\n"), "a.md")
        self.assertEqual(ctx.exception.name, "UNSUPPORTED_TOOLS_KEY")


class CommandStubTest(unittest.TestCase):
    def test_stub_keeps_name_description_and_body_and_hides_itself(self) -> None:
        text = ("---\nname: plan\ndescription: Draft a plan\nargument-hint: \"<idea>\"\n"
                "disable-model-invocation: true\n---\n\nCall `flow-next-plan` with $ARGUMENTS\n")
        out = antigravity_bundle.command_stub(text, "plan.md")
        self.assertEqual(
            out, "---\nname: plan\ndescription: Draft a plan\ndisable-model-invocation: true\n"
                 "---\n\nCall `flow-next-plan` with $ARGUMENTS\n")


class RulesTest(unittest.TestCase):
    def test_rule_is_scoped_by_its_description_and_drops_frontmatter(self) -> None:
        text = ("---\ndescription: Apply when the workspace has .flow/. More text.\n"
                "alwaysApply: false\n---\n\n# Flow-Next\n\nBody.\n")
        out = antigravity_bundle.rules_agents_md(text)
        self.assertEqual(out, "Apply when the workspace has .flow/; otherwise ignore this rule.\n\n"
                              "# Flow-Next\n\nBody.\n")


class BuildRealPluginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.before = _tree_digest(PLUGIN)
        cls.bundle = Path(cls.tmp.name) / "flow-next"
        antigravity_bundle.build(PLUGIN, cls.bundle)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_every_agent_has_a_tier_and_a_tool_allowlist(self) -> None:
        agents = sorted((self.bundle / "agents").glob("*.md"))
        self.assertEqual(len(agents), len(list((PLUGIN / "agents").glob("*.md"))))
        for agent in agents:
            text = agent.read_text(encoding="utf-8")
            front = _front(text)
            self.assertIn(front["model"].strip(), TIERS, agent.name)
            self.assertNotIn("disallowedTools", front, agent.name)
            self.assertLessEqual(set(_tools(text)), set(ALL_TOOLS), agent.name)

    def test_read_only_agents_have_no_file_edit_or_write_tool(self) -> None:
        for source in sorted((PLUGIN / "agents").glob("*.md")):
            denied = _front(source.read_text(encoding="utf-8")).get("disallowedTools", "")
            if {"Edit", "Write"} <= {t.strip() for t in denied.split(",")}:
                tools = _tools((self.bundle / "agents" / source.name).read_text(encoding="utf-8"))
                self.assertFalse(WRITE_TOOLS & set(tools), source.name)
                self.assertIn("run_command", tools, source.name)

    def test_commands_become_hidden_stub_skills(self) -> None:
        self.assertFalse((self.bundle / "commands").exists())
        commands = sorted((PLUGIN / "commands").glob("*.md"))
        self.assertTrue(commands)
        for command in commands:
            stub = (self.bundle / "skills" / command.stem / "SKILL.md").read_text(encoding="utf-8")
            front = _front(stub)
            self.assertEqual(front["name"].strip(), command.stem)
            self.assertEqual(front["disable-model-invocation"].strip(), "true")
        canonical = {p.name for p in (PLUGIN / "skills").iterdir() if (p / "SKILL.md").is_file()}
        bundled = {p.name for p in (self.bundle / "skills").iterdir()}
        self.assertEqual(bundled, canonical | {c.stem for c in commands})

    def test_bundle_carries_native_manifest_rule_and_marker(self) -> None:
        manifest = json.loads((self.bundle / "plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "flow-next")
        self.assertEqual(manifest["version"], claude["version"])
        self.assertNotIn("email", manifest.get("author", {}))
        self.assertTrue((self.bundle / antigravity_bundle.MARKER).is_file())
        rule = (self.bundle / "rules" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertFalse(rule.startswith("---"))
        self.assertIn("otherwise ignore this rule", rule.splitlines()[0])
        self.assertEqual([p.name for p in (self.bundle / "rules").iterdir()], ["AGENTS.md"])

    def test_other_host_files_and_tests_are_left_out(self) -> None:
        for name in ("codex", ".codex-plugin", ".cursor-plugin", "tests", "commands"):
            self.assertFalse((self.bundle / name).exists(), name)
        self.assertTrue((self.bundle / ".claude-plugin" / "plugin.json").is_file())
        self.assertEqual(list(self.bundle.rglob("__pycache__")), [])

    def test_canonical_plugin_is_untouched(self) -> None:
        self.assertEqual(_tree_digest(PLUGIN), self.before)


def _fake_agy(log: Path, mode: str) -> str:
    """A fake agy: install copies the bundle; list and validate report on it."""
    return f'''#!{sys.executable}
import json, shutil, sys
from pathlib import Path
args = sys.argv[1:]
with open({str(log)!r}, "a") as fh:
    fh.write(" ".join(args) + "\\n")
home = Path({str(log.parent)!r}) / "plugins" / "flow-next"
mode = {mode!r}
if args[:2] == ["plugin", "install"]:
    if mode == "install-fails":
        print("install refused", file=sys.stderr); sys.exit(3)
    if not (Path(args[2]) / ".flow-next-antigravity-bundle").is_file():
        sys.exit(9)
    shutil.rmtree(home, ignore_errors=True)
    shutil.copytree(args[2], home)
elif args[:2] == ["plugin", "list"]:
    print(json.dumps([{{"name": "flow-next", "path": str(home)}}]))
elif args[:2] == ["plugin", "validate"]:
    root = Path(args[2])
    skills = len(list(root.glob("skills/*/SKILL.md")))
    agents = len(list(root.glob("agents/*.md")))
    findings = []
    if mode == "validate-errors":
        findings = [{{"severity": "error", "file": "agents/worker.md", "message": "skipped"}}]
    if mode == "agent-skipped":
        agents -= 1
    print(json.dumps({{"components": {{"skills": skills, "agents": agents}}, "findings": findings}}))
    sys.exit(1 if mode == "validate-errors" else 0)
else:
    sys.exit(2)
'''


@unittest.skipIf(os.name == "nt", "POSIX installer")
class InstallerTest(unittest.TestCase):
    def _run(self, mode: str | None) -> tuple[subprocess.CompletedProcess, Path, Path]:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        bin_dir, work_tmp, log = tmp / "bin", tmp / "tmp", tmp / "agy.log"
        bin_dir.mkdir()
        work_tmp.mkdir()
        for tool in ("python3", "bash", "mktemp", "rm", "dirname", "sed"):
            found = shutil.which(tool)
            if found:
                (bin_dir / tool).symlink_to(found)
        if mode is not None:
            agy = bin_dir / "agy"
            agy.write_text(_fake_agy(log, mode), encoding="utf-8")
            agy.chmod(0o755)
        env = {"PATH": str(bin_dir), "HOME": str(tmp), "TMPDIR": str(work_tmp)}
        proc = subprocess.run(["bash", str(INSTALLER)], env=env, capture_output=True,
                              text=True, timeout=120)
        return proc, work_tmp, log

    def test_installs_validates_installed_copy_and_prints_session_command(self) -> None:
        proc, work_tmp, log = self._run("ok")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        calls = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual([c.split()[:2] for c in calls],
                         [["plugin", "install"], ["plugin", "list"], ["plugin", "validate"]])
        self.assertTrue(calls[2].endswith("plugins/flow-next --json"), calls[2])
        self.assertIn("Installed flow-next into Antigravity CLI", proc.stdout)
        self.assertIn("""agy --settings '{"toolPermission":"always-proceed"}'""", proc.stdout)
        self.assertIn("environment you already trust", proc.stdout)
        self.assertEqual(list(work_tmp.iterdir()), [])

    def test_rerun_replaces_the_install(self) -> None:
        proc, _, log = self._run("ok")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        installed = log.parent / "plugins" / "flow-next"
        (installed / "stale.txt").write_text("old", encoding="utf-8")
        env = {"PATH": str(log.parent / "bin"), "HOME": str(log.parent),
               "TMPDIR": str(log.parent / "tmp")}
        again = subprocess.run(["bash", str(INSTALLER)], env=env, capture_output=True,
                               text=True, timeout=120)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertFalse((installed / "stale.txt").exists())

    def test_failed_install_exits_nonzero_without_success(self) -> None:
        proc, work_tmp, log = self._run("install-fails")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("agy plugin install failed", proc.stderr)
        self.assertNotIn("Installed flow-next", proc.stdout)
        self.assertNotIn("plugin validate", log.read_text(encoding="utf-8"))
        self.assertEqual(list(work_tmp.iterdir()), [])

    def test_validation_errors_exit_nonzero_without_success(self) -> None:
        proc, work_tmp, _ = self._run("validate-errors")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("agy plugin validate reported errors", proc.stderr)
        self.assertNotIn("Installed flow-next", proc.stdout)
        self.assertNotIn("toolPermission", proc.stdout)
        self.assertEqual(list(work_tmp.iterdir()), [])

    def test_skipped_agent_exits_nonzero_without_success(self) -> None:
        proc, _, _ = self._run("agent-skipped")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("installed flow-next is incomplete", proc.stderr)
        self.assertIn("agents: 20 loaded, 21 expected", proc.stderr)
        self.assertNotIn("Installed flow-next", proc.stdout)

    def test_missing_agy_is_a_clear_error(self) -> None:
        proc, work_tmp, _ = self._run(None)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("agy not found on PATH", proc.stderr)
        self.assertEqual(list(work_tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
