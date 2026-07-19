"""Hermetic docs-only gate tiering tests for `flowctl gate classify` (fn-102).

The production CLI exercises NUL-delimited git parsing. Direct helper calls
pin the intentionally path-only classifier and its shared Windows normalization.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


FLOWCTL_PY = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location("flowctl_gate_classify_under_test", FLOWCTL_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()


class GateClassifyTestCase(unittest.TestCase):
    """Temporary real git repo with a stable base commit for each test."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.prev_cwd = Path.cwd()
        os.chdir(self.tmpdir)
        self._git("init", "-q")
        self._git("config", "user.email", "classify@example.com")
        self._git("config", "user.name", "Classify Test")
        self._write("seed.txt", "seed\n")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        self.base = self._git("rev-parse", "HEAD")

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @staticmethod
    def _pinned_env() -> dict:
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00Z"
        env["GIT_COMMITTER_DATE"] = "2026-01-01T00:00:00Z"
        return env

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            check=True,
            env=self._pinned_env(),
        )
        return result.stdout.strip()

    def _write(self, rel: str, content: str = "x\n") -> Path:
        path = self.tmpdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _commit_paths(self, *paths: str) -> None:
        for path in paths:
            self._write(path)
        self._git("add", "-A")
        self._git("commit", "-qm", "change")

    def _classify(self, base: str = "") -> tuple[subprocess.CompletedProcess, dict]:
        result = subprocess.run(
            [sys.executable, str(FLOWCTL_PY), "gate", "classify", "--base", base or self.base, "--json"],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
        )
        return result, json.loads(result.stdout)

    def test_force_full_paths(self) -> None:
        paths = [
            "plugins/flow-next/skills/x/SKILL.md",
            "plugins/flow-next/agents/worker.md",
            "plugins/flow-next/commands/foo.md",
            "plugins/flow-next/references/bar.md",
            "plugins/flow-next/templates/spec.md",
            "plugins/flow-next/hooks/h.md",
            "plugins/flow-next/codex/mirror.md",
            ".flow/bin/flowctl.py",
            ".flow/bin/anything.md",
            "scripts/x.md",
            "plugins/flow-next/scripts/y.md",
            "plugins/flow-next/tests/t.md",
            ".flow/config.json",
            "docs/evil.py",
            "docs/conf.json",
            "README.yaml",
            "unknown_dir/file.weird",
        ]
        for path in paths:
            with self.subTest(path=path):
                created = self._write(path)
                result, data = self._classify()
                self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
                self.assertEqual(data["tier"], "full")
                self.assertTrue(any(entry["path"] == path and entry["class"] != "safe" for entry in data["paths"]))
                created.unlink()

    def test_safe_single_docs_file(self) -> None:
        self._commit_paths("docs/a.md")
        result, data = self._classify()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(data["tier"], "tier-b")

    def test_safe_multi_file_set_including_untracked_flow_state(self) -> None:
        safe_paths = [
            "docs/a.md",
            "agent_docs/b.md",
            "optimization/c.md",
            "CHANGELOG.md",
            "README.md",
            "GLOSSARY.md",
            "STRATEGY.md",
            "plugins/flow-next/docs/d.mdx",
        ]
        self._commit_paths(*safe_paths)
        self._write(".flow/specs/fn-1.md")
        result, data = self._classify()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(data["changed_file_count"], len(safe_paths) + 1)
        self.assertTrue(all(entry["class"] == "safe" for entry in data["paths"]))

    def test_mixed_docs_and_code_is_full(self) -> None:
        self._commit_paths("docs/a.md", "src/app.py")
        result, data = self._classify()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(data["tier"], "full")

    def test_empty_diff_is_full(self) -> None:
        result, data = self._classify(base=self.base)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(data["tier"], "full")

    def test_untracked_code_is_unioned_with_safe_diff(self) -> None:
        self._commit_paths("docs/a.md")
        self._write("scratch.py")
        result, data = self._classify()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(entry["path"] == "scratch.py" for entry in data["paths"]))

    def test_rename_crossing_flow_boundary_is_full(self) -> None:
        self._commit_paths(".flow/notes/a.md")
        rename_base = self._git("rev-parse", "HEAD")
        (self.tmpdir / "src_notes").mkdir()
        self._git("mv", ".flow/notes/a.md", "src_notes/a.md")
        self._git("commit", "-qm", "move note")
        result, data = self._classify(base=rename_base)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(entry["path"] == "src_notes/a.md" and entry["class"] == "full" for entry in data["paths"]))

    def test_filename_with_spaces_is_safe(self) -> None:
        self._commit_paths("docs/my file.md")
        result, data = self._classify()
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(data["paths"][0]["path"], "docs/my file.md")

    def test_windows_normalization_is_shared(self) -> None:
        self.assertEqual(flowctl._classify_gate_path("docs\\a.md")[0], "safe")
        self.assertEqual(flowctl._classify_triage_path("docs\\a.md"), "docs")

    def test_path_only_classifier_handles_missing_paths_and_all_force_extensions(self) -> None:
        self.assertEqual(flowctl._classify_gate_path("docs/ghost.md")[0], "safe")
        self.assertEqual(
            flowctl._classify_gate_path("plugins/flow-next/skills/ghost.md")[0],
            "force-full",
        )
        self.assertEqual(
            flowctl._classify_gate_path("plugins/flow-next/agents/worker.md")[0],
            "force-full",
        )
        self.assertEqual(flowctl._classify_gate_path(".flow/bin/x.py")[0], "force-full")
        for ext in {".py", ".sh", ".cmd", ".ps1", ".toml", ".json", ".yaml", ".yml"}:
            with self.subTest(ext=ext):
                self.assertEqual(flowctl._classify_gate_path(f"ghost{ext}")[0], "force-full")

    def test_json_evidence_shape(self) -> None:
        self._commit_paths("docs/a.md", "unknown_dir/file.weird")
        _result, data = self._classify()
        for entry in data["paths"]:
            self.assertEqual(set(entry), {"path", "class", "reason"})
            self.assertIn(entry["class"], {"safe", "force-full", "full"})
