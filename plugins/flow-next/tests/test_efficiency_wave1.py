"""Focused behavioral tests for fn-345 (efficiency audit 2026-11 wave 1)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowctl_test_support import FLOWCTL_CMD, MemoryRepoTemplate  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_module("flowctl_wave1", SCRIPTS / "flowctl.py")
bootstrap = _load_module("flowctl_bootstrap_wave1", SCRIPTS / "flowctl_bootstrap.py")


class PilotSnapshotForgeOnlyTest(unittest.TestCase):
    """R2: flowctl pilot snapshot --forge-only --json avoids PR listings and spec scans."""

    def test_forge_only_returns_forge_without_pr_listing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://gitlab.com/acme/widget.git"],
                cwd=repo,
                check=True,
            )
            res = subprocess.run(
                [*FLOWCTL_CMD, "pilot", "snapshot", "--forge-only", "--json"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            data = json.loads(res.stdout)
            self.assertTrue(data["success"])
            self.assertEqual(data["forge"], "gitlab")
            self.assertNotIn("candidates", data)
            self.assertNotIn("selected", data)


class ReviewPromptFixesTest(unittest.TestCase):
    """R3: plan re-review, completion re-review ratchet, completion role, shared fanout diff."""

    def test_plan_rereview_omits_author_task_spec_sync_instructions(self) -> None:
        preamble = flowctl.build_rereview_preamble(
            [".flow/specs/fn-1.md"],
            "plan",
            prior_findings="Finding #1: fix acceptance.",
        )
        self.assertNotIn("Task Spec Sync Required", preamble)
        self.assertNotIn("flowctl task set-spec", preamble)

    def test_completion_rereview_uses_ratchet_closing_when_ratchet_present(self) -> None:
        preamble = flowctl.build_rereview_preamble(
            ["src/app.py"],
            "completion",
            prior_findings="Finding #1: missing R2 check.",
        )
        self.assertIn("Apply the CONVERGENCE RATCHET contract above", preamble)
        self.assertNotIn("Re-verify each requirement from the epic spec", preamble)

    def test_completion_rereview_without_ratchet_keeps_fresh_instruction(self) -> None:
        preamble = flowctl.build_rereview_preamble(["src/app.py"], "completion")
        self.assertIn("Re-verify each requirement from the epic spec", preamble)

    def test_completion_review_prompt_omits_duplicate_terminal_role_header(self) -> None:
        prompt = flowctl.build_completion_review_prompt(
            review_scope="fn-1",
            diff_range="abc..def",
            spec_path=".flow/specs/fn-1.md",
            task_spec_paths=[".flow/tasks/fn-1.1.md"],
        )
        self.assertNotIn("TERMINAL REVIEWER ROLE", prompt)
        self.assertIn("You ARE the reviewer", prompt)

    def test_materialise_review_diff_reuses_precomputed_diff_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".flow" / "tmp").mkdir(parents=True)
            with mock.patch.object(flowctl, "_review_diff_text", side_effect=AssertionError("should not spawn git diff")):
                leaf = flowctl._materialise_review_diff(
                    repo,
                    "rid-1-correctness",
                    "aaaaaaa",
                    "bbbbbbb",
                    diff_text="diff --git a/x b/x\n",
                )
            self.assertEqual(leaf.read_text(encoding="utf-8"), "diff --git a/x b/x\n")


class BootstrapHelpFastPathTest(unittest.TestCase):
    """R4: supported Python 3.11-3.14 take the authenticated --help fast path."""

    def test_current_python_uses_help_fast_path_and_matches_live(self) -> None:
        source = SCRIPTS / "flowctl.py"
        direct = subprocess.run(
            [sys.executable, str(source), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        buf = io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != "COLUMNS"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(bootstrap.sys, "stdout", buf):
            ok = bootstrap._root_help_fast_path(source)
        self.assertTrue(ok, f"fast path declined on Python {sys.version_info[:2]}")
        self.assertEqual(buf.getvalue(), direct.stdout)

    def test_unknown_future_python_minor_still_falls_back(self) -> None:
        source = SCRIPTS / "flowctl.py"
        with mock.patch.object(bootstrap.sys, "version_info", (3, 99, 0)):
            self.assertFalse(bootstrap._root_help_fast_path(source))


class AuditScanBatchingTest(MemoryRepoTemplate, unittest.TestCase):
    """R4: batched cmd_memory_audit_scan preserves dirty, module_changed, and rename counts."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.memory = self.init_repo(self.root)
        for args in [
            ("init", "-q"),
            ("config", "user.name", "test"),
            ("config", "user.email", "test@example.com"),
        ]:
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def _run(self, *args: str) -> dict:
        res = subprocess.run(
            [*FLOWCTL_CMD, *args, "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return json.loads(res.stdout)

    def test_dirty_and_clean_modules_and_renamed_entry(self) -> None:
        (self.root / "src").mkdir()
        (self.root / "src" / "clean.py").write_text("x = 1\n", encoding="utf-8")
        (self.root / "src" / "dirty.py").write_text("y = 1\n", encoding="utf-8")
        e1 = self._run(
            "memory", "add", "--track", "bug", "--category", "runtime-errors",
            "--title", "Clean module bug", "--module", "src/clean.py",
        )
        e2 = self._run(
            "memory", "add", "--track", "bug", "--category", "runtime-errors",
            "--title", "Dirty module bug", "--module", "src/dirty.py",
        )
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True, capture_output=True)

        # Stamp both entries with a future last_audited so git log --since is empty;
        # then dirty only src/dirty.py.
        plan = self.root / "plan.json"
        plan.write_text(
            json.dumps({
                "entries": [
                    {"id": e1["entry_id"], "set": {"last_audited": "2099-01-01"}},
                    {"id": e2["entry_id"], "set": {"last_audited": "2099-01-01"}},
                ]
            }),
            encoding="utf-8",
        )
        self._run("memory", "apply", "--plan", str(plan))
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "stamp"], cwd=self.root, check=True, capture_output=True)

        # Move e1 to test rename follow fallback
        moved = e1["entry_id"].replace("runtime-errors", "integration")
        plan.write_text(
            json.dumps({"entries": [{"id": e1["entry_id"], "move": moved}]}),
            encoding="utf-8",
        )
        self._run("memory", "apply", "--plan", str(plan))
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "move"], cwd=self.root, check=True, capture_output=True)

        (self.root / "src" / "dirty.py").write_text("y = 2\n", encoding="utf-8")

        rows = {r["id"]: r for r in self._run("memory", "audit-scan")["entries"]}
        self.assertFalse(rows[moved]["module_changed"])
        self.assertTrue(rows[e2["entry_id"]]["module_changed"])
        # Creation + move category change; stamp commit excluded.
        self.assertEqual(rows[moved]["recurrence"]["commits"], 2)
        self.assertEqual(rows[e2["entry_id"]]["recurrence"]["commits"], 1)


class SetupAndPrimeFoldedFieldsTest(unittest.TestCase):
    """R5: setup-status exposes features_status; prime classify exposes features_status and glossary_terms."""

    def test_setup_status_includes_features_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            res = subprocess.run(
                [*FLOWCTL_CMD, "setup-status", "--json"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            data = json.loads(res.stdout)
            self.assertIn("features_status", data)
            self.assertEqual(data["features_status"]["recommendation"], "seed")

    def test_prime_classify_includes_features_status_and_glossary_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            (repo / "GLOSSARY.md").write_text(
                "# Glossary\n\n## Widget\n\nA sample term.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)

            payload = flowctl._prime_classify(repo)
            self.assertEqual(payload["substance"]["features_status"]["recommendation"], "seed")
            self.assertEqual(payload["substance"]["glossary_terms"]["total_terms"], 1)


if __name__ == "__main__":
    unittest.main()
