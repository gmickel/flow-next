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
sys.path.insert(0, str(ROOT / "scripts"))
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

    def test_completion_rereview_branches_on_ratchet_presence(self) -> None:
        with_ratchet = flowctl.build_rereview_preamble(
            ["src/app.py"],
            "completion",
            prior_findings="Finding #1: missing R2 check.",
        )
        without_ratchet = flowctl.build_rereview_preamble(["src/app.py"], "completion")
        self.assertIn("CONVERGENCE RATCHET", with_ratchet)
        self.assertNotIn("CONVERGENCE RATCHET", without_ratchet)
        with_body = with_ratchet.split("## IMPORTANT:", 1)[1]
        without_body = without_ratchet.split("## IMPORTANT:", 1)[1]
        self.assertIn("CONVERGENCE RATCHET", with_body)
        self.assertNotIn("CONVERGENCE RATCHET", without_body)

    def test_completion_review_prompt_omits_duplicate_terminal_role_header(self) -> None:
        prompt = flowctl.build_completion_review_prompt(
            review_scope="fn-1",
            diff_range="abc..def",
            spec_path=".flow/specs/fn-1.md",
            task_spec_paths=[".flow/tasks/fn-1.1.md"],
        )
        self.assertNotIn("## TERMINAL REVIEWER ROLE", prompt)

    def test_attach_review_diff_reuses_shared_round_diff_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            diff_dir = repo / ".flow" / "tmp" / "claude-review"
            diff_dir.mkdir(parents=True)
            shared = diff_dir / "rid-1-aaaaaaa-bbbbbbb.diff"
            shared.write_text("diff --git a/x b/x\n", encoding="utf-8")
            ns = mock.MagicMock(
                review_range=("aaaaaaa", "bbbbbbb", "rid-1-correctness"),
                _review_diff_path=shared,
            )
            with mock.patch.object(
                flowctl,
                "_materialise_review_diff",
                side_effect=AssertionError("should reuse shared round diff path"),
            ):
                out = flowctl._attach_review_diff("PROMPT", "claude", repo, ns)
            self.assertIn(str(shared), out)


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
            "--title", "Alpha parser failure", "--module", "src/clean.py",
        )
        e2 = self._run(
            "memory", "add", "--track", "bug", "--category", "runtime-errors",
            "--title", "Beta socket timeout", "--module", "src/dirty.py",
        )
        old_env = {
            **os.environ,
            "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2020-01-01T00:00:00Z",
        }
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True, capture_output=True, env=old_env)

        # Stamp both entries (non-substantive) with today's date, then dirty only src/dirty.py.
        plan = self.root / "plan.json"
        plan.write_text(
            json.dumps({
                "entries": [
                    {"id": e1["entry_id"], "stamp": True},
                    {"id": e2["entry_id"], "stamp": True},
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

    def test_dot_prefixed_module_and_untracked_nested_file_and_apply_null_delete(self) -> None:
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
        e_dot = self._run(
            "memory", "add", "--track", "bug", "--category", "runtime-errors",
            "--title", "CI workflow trigger drift", "--module", "./.github",
        )
        e_untracked = self._run(
            "memory", "add", "--track", "bug", "--category", "runtime-errors",
            "--title", "New subdir alert", "--module", "pkg/newdir/file.py",
        )
        old_env = {
            **os.environ,
            "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2020-01-01T00:00:00Z",
        }
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True, capture_output=True, env=old_env)

        # Stamp both entries + harden e_dot, then clear hardened_into via memory apply set=null.
        self._run("memory", "mark-hardened", e_dot["entry_id"], "--gate-ref", ".github/workflows/ci.yml#ci -- test")
        plan = self.root / "plan.json"
        plan.write_text(
            json.dumps({
                "entries": [
                    {"id": e_dot["entry_id"], "stamp": True, "set": {"status": "active", "hardened_into": None}},
                    {"id": e_untracked["entry_id"], "stamp": True},
                ]
            }),
            encoding="utf-8",
        )
        self._run("memory", "apply", "--plan", str(plan))
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "stamp"], cwd=self.root, check=True, capture_output=True)

        # Dirty .github/workflows/ci.yml AND create an untracked file inside an untracked directory.
        (self.root / ".github" / "workflows" / "ci.yml").write_text("name: ci-v2\n", encoding="utf-8")
        (self.root / "pkg" / "newdir").mkdir(parents=True)
        (self.root / "pkg" / "newdir" / "file.py").write_text("x = 1\n", encoding="utf-8")

        rows = {r["id"]: r for r in self._run("memory", "audit-scan")["entries"]}
        self.assertTrue(rows[e_dot["entry_id"]]["module_changed"])
        self.assertNotIn("hardened_into", rows[e_dot["entry_id"]]["frontmatter"])
        self.assertTrue(rows[e_untracked["entry_id"]]["module_changed"])


class SetupAndPrimeFoldedFieldsTest(unittest.TestCase):
    """R5: setup-status exposes features_status; prime classify exposes features_status and glossary_terms."""

    def test_setup_status_includes_features_status_and_respects_config_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
            (repo / ".flow" / "features").mkdir(parents=True)
            (repo / ".flow" / "config.json").write_text(
                json.dumps({"features": {"staleAfterCommits": "2"}}),
                encoding="utf-8",
            )
            (repo / ".flow" / "memory" / "knowledge" / "conventions").mkdir(parents=True)
            (repo / ".flow" / "memory" / "knowledge" / "conventions" / "drift-2026-01-01.md").write_text(
                "---\ntitle: drift note\ndate: 2026-01-01\ntrack: knowledge\ncategory: conventions\n"
                "applies_when: always\ntags: [feature-map-drift]\nstatus: active\n---\n\nbody\n",
                encoding="utf-8",
            )
            res = subprocess.run(
                [*FLOWCTL_CMD, "setup-status", "--json"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            data = json.loads(res.stdout)
            self.assertEqual(data["features_status"]["recommendation"], "maintain")
            self.assertTrue(data["features_status"]["due"])
            self.assertTrue(
                any("drift" in r for r in data["features_status"]["reasons"]),
                data["features_status"],
            )
            full_feat = flowctl._compute_features_status(
                repo_root_override=repo, use_json=True
            )
            self.assertEqual(full_feat["threshold"], 2)

    def test_prime_classify_includes_features_status_and_package_glossary_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
            pkg = repo / "packages" / "web"
            pkg.mkdir(parents=True)
            (pkg / "app.py").write_text("x = 1\n", encoding="utf-8")
            (pkg / "GLOSSARY.md").write_text(
                "# Glossary\n\n## Widget\n\nA sample term.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)

            old_cwd = os.getcwd()
            try:
                os.chdir(pkg)
                payload = flowctl._prime_classify(repo)
            finally:
                os.chdir(old_cwd)
            self.assertEqual(payload["substance"]["features_status"]["recommendation"], "seed")
            self.assertEqual(payload["substance"]["glossary_terms"]["total_terms"], 1)


class ResolvePrShellScriptsTest(unittest.TestCase):
    """R2: get-pr-comments single-pass pagination + OWNER/REPO arg."""

    def _write_fake_gh(self, bin_dir: Path, script_body: str) -> None:
        gh = bin_dir / "gh"
        gh.write_text("#!/usr/bin/env bash\n" + script_body, encoding="utf-8")
        gh.chmod(0o755)

    def test_get_pr_comments_accepts_owner_repo_and_paginates_only_unexhausted_threads(self) -> None:
        script = ROOT / "skills" / "flow-next-resolve-pr" / "scripts" / "get-pr-comments"
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            log = Path(tmp) / "gh.log"
            first_page = json.dumps({
                "data": {
                    "repository": {
                        "pullRequest": {
                            "author": {"login": "alice"},
                            "comments": {"nodes": []},
                            "reviews": {"nodes": []},
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "id": "T1",
                                        "isResolved": False,
                                        "isOutdated": False,
                                        "path": "a.py",
                                        "line": 1,
                                        "originalLine": 1,
                                        "diffSide": "RIGHT",
                                        "comments": {
                                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                                            "nodes": [{"id": "C1", "body": "one", "author": {"login": "bob"}, "createdAt": "2026-01-01T00:00:00Z"}],
                                        },
                                    },
                                    {
                                        "id": "T2",
                                        "isResolved": False,
                                        "isOutdated": False,
                                        "path": "b.py",
                                        "line": 2,
                                        "originalLine": 2,
                                        "diffSide": "RIGHT",
                                        "comments": {
                                            "pageInfo": {"hasNextPage": True, "endCursor": "CUR1"},
                                            "nodes": [{"id": "C2", "body": "two", "author": {"login": "bob"}, "createdAt": "2026-01-01T00:00:00Z"}],
                                        },
                                    },
                                ],
                            },
                        }
                    }
                }
            })
            second_page = json.dumps({
                "data": {
                    "node": {
                        "comments": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [{"id": "C3", "body": "three", "author": {"login": "carol"}, "createdAt": "2026-01-02T00:00:00Z"}],
                        }
                    }
                }
            })
            (Path(tmp) / "p1.json").write_text(first_page, encoding="utf-8")
            (Path(tmp) / "p2.json").write_text(second_page, encoding="utf-8")
            self._write_fake_gh(
                bin_dir,
                f'''printf "%s\\n" "$*" >> "{log}"
if [ "$1" = "repo" ]; then
  echo "should not call gh repo view when OWNER/REPO is passed" >&2
  exit 99
fi
if echo "$*" | grep -q "thread=T2"; then
  cat "{Path(tmp) / 'p2.json'}"
else
  cat "{Path(tmp) / 'p1.json'}"
fi
''',
            )
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}
            res = subprocess.run(
                [str(script), "42", "acme/widget"],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["pr_number"], 42)
            by_id = {t["id"]: t for t in out["review_threads"]}
            self.assertEqual([c["id"] for c in by_id["T1"]["comments"]], ["C1"])
            self.assertEqual([c["id"] for c in by_id["T2"]["comments"]], ["C2", "C3"])
            self.assertNotIn("repo view", log.read_text(encoding="utf-8"))

    def test_get_thread_for_comment_propagates_pagination_failure(self) -> None:
        script = (
            ROOT / "skills" / "flow-next-resolve-pr" / "scripts" / "get-thread-for-comment"
        )
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            first_page = json.dumps({
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [
                                    {
                                        "id": "T1",
                                        "isResolved": False,
                                        "isOutdated": False,
                                        "path": "a.py",
                                        "line": 1,
                                        "originalLine": 1,
                                        "startLine": None,
                                        "originalStartLine": None,
                                        "comments": {
                                            "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
                                            "nodes": [
                                                {
                                                    "id": "C1",
                                                    "body": "first",
                                                    "author": {"login": "alice"},
                                                    "createdAt": "2026-01-01T00:00:00Z",
                                                }
                                            ],
                                        },
                                    }
                                ],
                            }
                        }
                    }
                }
            })
            (Path(tmp) / "p1.json").write_text(first_page, encoding="utf-8")
            self._write_fake_gh(
                bin_dir,
                f'''if echo "$*" | grep -q "thread=T1"; then
  echo "simulated API failure" >&2
  exit 17
fi
cat "{Path(tmp) / 'p1.json'}"
''',
            )
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}
            res = subprocess.run(
                [str(script), "42", "C1", "acme/widget"],
                text=True,
                capture_output=True,
                env=env,
            )
            self.assertNotEqual(res.returncode, 0)
            self.assertEqual(res.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
