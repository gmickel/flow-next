"""Execute work/sync fences and check unattended handover wire contracts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
WORK = ROOT / "skills/flow-next-work"
SYNC = ROOT / "skills/flow-next-sync/SKILL.md"


def fence(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    return next(block for block in re.findall(r"```bash\n(.*?)```", text, re.S)
                if f"# fence:{name}" in block)


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"),
                 "requires POSIX bash and jq")
class WorkBranchRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.env = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="t@x",
                        GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="t@x")
        self.git("init", "-q", "-b", "trunk")
        (self.repo / "tracked").write_text("base\n", encoding="utf-8")
        self.git("add", "tracked")
        self.git("commit", "-qm", "base")
        shim = self.repo / "flowctl"
        shim.write_text('#!/bin/sh\nprintf \'%s\\n\' \'{"eligible":true}\'\n', encoding="utf-8")
        shim.chmod(0o755)
        self.env.update(FLOWCTL=str(shim), SPEC_ID="fn-1", BRANCH_NAME="task",
                        BRANCH_MODE="new", DEFAULT_BASE="trunk")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def branch(self) -> subprocess.CompletedProcess[str]:
        # No set -e: the fence itself must stop after a failed git command.
        return subprocess.run(["bash", "-c", fence(WORK / "phases.md", "work-branch")],
                              cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_trunk_and_permitted_flow_dirt_are_carried(self) -> None:
        path = self.repo / ".flow/tasks/fn-1.1.md"
        path.parent.mkdir(parents=True)
        path.write_text("planned", encoding="utf-8")
        run = self.branch()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.git("branch", "--show-current"), "task")
        self.assertEqual(path.read_text(encoding="utf-8"), "planned")

    def test_locally_committed_spec_survives_older_default_base(self) -> None:
        base = self.git("rev-parse", "HEAD")
        path = self.repo / ".flow/tasks/fn-1.1.md"
        path.parent.mkdir(parents=True)
        path.write_text("planned", encoding="utf-8")
        self.git("add", ".flow")
        self.git("commit", "-qm", "plan")
        self.env["DEFAULT_BASE"] = base
        run = self.branch()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.git("branch", "--show-current"), "task")
        self.assertEqual(path.read_text(encoding="utf-8"), "planned")
        self.assertEqual((self.repo / ".flow/tmp/spec_base").read_text(encoding="utf-8").strip(), base)

    def test_preexisting_stage_is_not_included_in_planning_checkpoint(self) -> None:
        base = self.git("rev-parse", "HEAD")
        for needs_carry in (False, True):
            with self.subTest(needs_carry=needs_carry):
                self.git("checkout", "-q", "trunk")
                path = self.repo / ".flow/tasks/fn-1.1.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("planned", encoding="utf-8")
                if not self.git("ls-files", str(path.relative_to(self.repo))):
                    self.git("add", ".flow/tasks/fn-1.1.md")
                    self.git("commit", "-qm", "plan")
                (self.repo / "tracked").write_text("user staged work", encoding="utf-8")
                self.git("add", "tracked")
                self.env["BRANCH_NAME"] = f"task-{needs_carry}"
                self.env["DEFAULT_BASE"] = base if needs_carry else "trunk"
                run = self.branch()
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(self.git("diff", "--cached", "--name-only"), "tracked")
                self.assertEqual(self.git("show", "HEAD:tracked"), "base")
                self.assertEqual(path.read_text(encoding="utf-8"), "planned")

    def test_existing_branch_is_reused(self) -> None:
        self.git("branch", "task")
        run = self.branch()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(self.git("branch", "--show-current"), "task")

    def test_offline_remote_stops_before_branch_work(self) -> None:
        self.git("remote", "add", "origin", str(self.repo / "missing.git"))
        self.env["DEFAULT_BASE"] = "origin/trunk"
        run = self.branch()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("BLOCKED:", run.stderr)
        self.assertFalse((self.repo / ".flow/tmp/spec_base").exists())

    def test_checkout_conflict_retains_git_error_and_stops(self) -> None:
        self.git("checkout", "-qb", "task")
        (self.repo / "tracked").write_text("task\n", encoding="utf-8")
        self.git("commit", "-qam", "task")
        self.git("checkout", "-q", "trunk")
        (self.repo / "tracked").write_text("user dirt\n", encoding="utf-8")
        run = self.branch()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("BLOCKED:", run.stderr)
        self.assertIn("tracked", run.stderr)
        self.assertEqual((self.repo / "tracked").read_text(encoding="utf-8"), "user dirt\n")

    def test_sync_inputs_use_defaults_for_empty_and_failed_reads(self) -> None:
        for body in ("exit 0", "printf partial; exit 1"):
            with self.subTest(body=body):
                Path(self.env["FLOWCTL"]).write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
                run = subprocess.run(["bash", "-c", fence(SYNC, "plan-sync-inputs")],
                                     cwd=self.repo, env=self.env, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                paths = [Path(p) for p in run.stdout.splitlines()]
                self.assertEqual(len(paths), 3)
                self.assertTrue(all(p.is_absolute() for p in paths))
                data = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
                self.assertEqual(data[0]["total_terms"], 0)
                self.assertEqual(data[1]["count"], 0)
                self.assertEqual(data[2], {})


class DispatchContracts(unittest.TestCase):
    def test_both_plan_sync_dispatches_pass_paths_and_plural_ids(self) -> None:
        for path in (SYNC, WORK / "references/plan-sync-dispatch.md"):
            text = path.read_text(encoding="utf-8")
            fields = set(re.findall(r"^(\w+):", text, re.M))
            self.assertTrue({"COMPLETED_TASK_IDS", "GLOSSARY_JSON_FILE", "DECISIONS_JSON_FILE",
                             "STRATEGY_CONTENT_FILE"} <= fields, path)
            self.assertTrue({"GLOSSARY_JSON", "DECISIONS_JSON", "STRATEGY_CONTENT",
                             "COMPLETED_TASK_ID"}.isdisjoint(fields), path)
        agent = (ROOT / "agents/plan-sync.md").read_text(encoding="utf-8")
        denied = re.search(r"^disallowedTools: (.+)$", agent, re.M).group(1).split(", ")
        self.assertNotIn("Bash", denied)
        self.assertIn("Task", denied)

    def test_worker_handover_is_task_unique_on_all_routes(self) -> None:
        text = (ROOT / "agents/worker.md").read_text(encoding="utf-8")
        self.assertNotIn("/tmp/summary.md", text)
        self.assertNotIn("/tmp/evidence.json", text)
        self.assertIn(".flow/tmp/<TASK_ID>-summary.md", text)
        self.assertIn(".flow/tmp/<TASK_ID>-evidence.json", text)
        self.assertIn("### Investigation targets", text)
        self.assertIn("## Investigation targets", text)

    def test_conductor_capture_reachable_on_both_ship_paths(self) -> None:
        for name in ("rolling-scheduler.md", "host-deferred-review.md"):
            text = (WORK / "references" / name).read_text(encoding="utf-8")
            links = re.findall(r"\]\(([^)]+worker\.md#[^)]+)\)", text)
            self.assertEqual(len(links), 1, name)
            self.assertTrue((WORK / "references" / links[0].split("#")[0]).resolve().exists())
            self.assertIn("memory.enabled", text)
            self.assertNotIn("$(cat .flow/tmp/base_commit)", text)
