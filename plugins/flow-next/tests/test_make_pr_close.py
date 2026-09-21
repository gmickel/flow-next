"""R2: execute make-pr's preflight against real git and flowctl state."""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "plugins/flow-next/scripts"
WORKFLOW = ROOT / "plugins/flow-next/skills/flow-next-make-pr/workflow.md"
sys.path.insert(0, str(ROOT / "plugins/flow-next/scripts"))


@unittest.skipIf(
    os.name == "nt",
    "These tests execute make-pr's bash fences against PATH shims for git, gh "
    "and flowctl; Windows CreateProcess never consults a script shim, and the "
    "fence logic under test is OS-independent.",
)
class MakePrCloseTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".flow/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.previous = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, self.previous)
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("FLOW_STATE_DIR", None)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        module = importlib.util.spec_from_file_location("flowctl_make_pr_close_test", SCRIPTS / "flowctl.py")
        self.flow = importlib.util.module_from_spec(module)
        sys.modules[module.name] = self.flow
        module.loader.exec_module(self.flow)
        self.call("init")
        self.spec_id = self.call("spec_create", title="PR close", branch=None)["id"]
        self.task_id = self.call("task_create", spec=self.spec_id, epic=None, title="Task", priority=None, deps=None, acceptance_file=None)["id"]
        self.spec_rel = f".flow/specs/{self.spec_id}.json"
        self.task_rel = f".flow/tasks/{self.task_id}.json"
        self.git("add", ".")
        self.git("commit", "-qm", "Base")
        self.git("checkout", "-qb", "feature")
        (self.repo / "change.txt").write_text("feature\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Feature")
        self.flow.save_task_runtime(self.task_id, {"status": "done"})
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.executable("gh", '''#!/bin/bash
if [[ "$1 $2" == "pr view" ]]; then
  if [[ "$UPDATE_MODE" == 1 ]]; then echo '{"url":"https://example.test/pr/1","number":1,"state":"OPEN"}'; fi
elif [[ "$1 $2" == "pr create" ]]; then
  git rev-parse HEAD > "$OBSERVATIONS/create-head"
  git show "HEAD:$SPEC_REL" > "$OBSERVATIONS/create-spec.json"
else exit 91
fi
''')

    def executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)
        return path

    def call(self, name, **kwargs):
        out = io.StringIO()
        with redirect_stdout(out):
            getattr(self.flow, "cmd_" + name)(argparse.Namespace(json=True, **kwargs))
        return json.loads(out.getvalue())

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout.strip()

    def execute(self, *, dry=False, update=False, autonomous=False, ralph=False, failure=False):
        if failure:
            flowctl = self.executable("flowctl-fail", '#!/bin/bash\nif [[ "$1 $2" == "spec close" ]]; then echo "injected close failure" >&2; exit 9; fi\nexec ' + shlex.quote(str(SCRIPTS / "flowctl")) + ' "$@"\n')
        else:
            flowctl = SCRIPTS / "flowctl"
        fence = next(f for f in re.findall(r"```bash\n(.*?)\n```", WORKFLOW.read_text(encoding="utf-8"), re.S) if "# --- §0.5:" in f)
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], FLOWCTL=str(flowctl), REPO_ROOT=str(self.repo), SPEC_ID=self.spec_id, HEAD_SHA=self.git("rev-parse", "HEAD"), BASE_REF="main", COMMITS_AHEAD=self.git("rev-list", "--count", "main..HEAD"), DRY_RUN=str(int(dry)), UPDATE_MODE=str(int(update)), AUTONOMOUS=str(int(autonomous)), RALPH=str(int(ralph)), WRITE_MEMORY="0", DRAFT_FORCE="", OBSERVATIONS=str(self.root), SPEC_REL=self.spec_rel)
        # Observe the exact head seen by the artifact/export phase and PR creation.
        tail = '''
printf '%s' "$PHASE0_CONTEXT" > "$OBSERVATIONS/context.json"
"$FLOWCTL" spec export-cognitive-aid "$SPEC_ID" --base "$BASE_REF" --json > "$OBSERVATIONS/export.json"
git rev-parse HEAD > "$OBSERVATIONS/artifact-head"
git show "HEAD:$SPEC_REL" > "$OBSERVATIONS/artifact-spec.json"
if [[ "$DRY_RUN" != 1 && "$UPDATE_MODE" != 1 ]]; then gh pr create; fi
'''
        return subprocess.run(["bash", "-c", "set -e\n" + fence + tail], cwd=self.repo, env=env, capture_output=True, text=True)

    def test_r2_close_commit_precedes_artifact_and_pr_and_binds_branch(self):
        for branch in (None, "old-branch", "feature"):
            with self.subTest(branch=branch):
                spec = json.loads((self.repo / self.spec_rel).read_text(encoding="utf-8"))
                spec.update(status="open", branch_name=branch)
                (self.repo / self.spec_rel).write_text(json.dumps(spec))
                self.git("add", self.spec_rel)
                self.git("commit", "--allow-empty", "-qm", "Prepare branch metadata")
                before = self.git("rev-parse", "HEAD")
                result = self.execute()
                self.assertEqual(result.returncode, 0, result.stderr)
                head = self.git("rev-parse", "HEAD")
                self.assertNotEqual(head, before, "all-done create must commit the close")
                for phase in ("artifact", "create"):
                    self.assertEqual((self.root / f"{phase}-head").read_text(encoding="utf-8").strip(), head)
                    state = json.loads((self.root / f"{phase}-spec.json").read_text(encoding="utf-8"))
                    self.assertEqual((state["status"], state["branch_name"]), ("done", "feature"))
                context = json.loads((self.root / "context.json").read_text(encoding="utf-8"))
                self.assertEqual(context["head"], head)
                self.assertEqual(context["commits_ahead"], int(self.git("rev-list", "--count", "main..HEAD")))
                self.assertEqual(json.loads(self.git("show", f"HEAD:{self.task_rel}"))["status"], "done")
                changed = self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
                self.assertTrue(set(changed) <= {self.spec_rel, self.task_rel}, changed)
                self.assertEqual(self.git("status", "--porcelain"), "")

    def test_r2_incomplete_task_opens_without_close(self):
        self.flow.save_task_runtime(self.task_id, {"status": "todo"})
        before = self.git("rev-parse", "HEAD")
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "create-head").read_text(encoding="utf-8").strip(), before)
        self.assertEqual(json.loads((self.root / "create-spec.json").read_text(encoding="utf-8"))["status"], "open")
        self.assertIn(self.task_id, result.stderr)
        self.assertRegex(result.stderr.lower(), r"(?:not clos|stay[s]? open|remain[s]? open)")
        # The existing autonomous refusal is untouched: nothing opens, nothing closes.
        for flags in ({"autonomous": True}, {"ralph": True}):
            with self.subTest(flags=flags):
                refused = self.execute(**flags)
                self.assertEqual(refused.returncode, 2, refused.stderr)
                self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_r2_dry_run_closes_nothing(self):
        before = self.git("rev-parse", "HEAD")
        stored = (self.repo / self.spec_rel).read_bytes()
        result = self.execute(dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual((self.repo / self.spec_rel).read_bytes(), stored)
        self.assertFalse((self.root / "create-head").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_r2_failed_close_stops_before_artifact_and_pr_with_reason(self):
        result = self.execute(failure=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("injected close failure", result.stderr + result.stdout)
        self.assertFalse((self.root / "artifact-head").exists())
        self.assertFalse((self.root / "create-head").exists())

    def test_r2_failed_commit_stops_before_artifact_and_pr(self):
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text('#!/bin/sh\necho "injected commit failure" >&2\nexit 1\n')
        hook.chmod(0o755)
        before = self.git("rev-parse", "HEAD")
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertFalse((self.root / "artifact-head").exists())
        self.assertFalse((self.root / "create-head").exists())

    def test_r2_failed_staging_retains_written_close_without_opening(self):
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
        self.executable("git", '#!/bin/bash\nfor arg in "$@"; do if [[ "$arg" == add ]]; then echo "injected staging failure" >&2; exit 7; fi; done\nexec ' + shlex.quote(real_git) + ' "$@"\n')
        before = self.git("rev-parse", "HEAD")
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(json.loads((self.repo / self.spec_rel).read_text(encoding="utf-8"))["status"], "done")
        self.assertFalse((self.root / "artifact-head").exists())
        self.assertFalse((self.root / "create-head").exists())
        self.assertIn("injected staging failure", result.stderr)

    def test_r2_dirty_tree_stops_without_consuming_existing_changes(self):
        task = json.loads((self.repo / self.task_rel).read_text(encoding="utf-8"))
        task["title"] = "Uncommitted task work"
        (self.repo / self.task_rel).write_text(json.dumps(task))
        self.git("add", self.task_rel)
        before = self.git("diff", "--cached")
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("diff", "--cached"), before)
        self.assertEqual(json.loads((self.repo / self.spec_rel).read_text(encoding="utf-8"))["status"], "open")
        self.assertFalse((self.root / "create-head").exists())

    def test_r2_unrelated_dirty_and_untracked_files_survive_close(self):
        (self.repo / "change.txt").write_text("uncommitted work\n")
        self.git("add", "change.txt")
        staged = self.git("diff", "--cached")
        config = self.repo / ".flow/config.json"
        config.write_text(config.read_text(encoding="utf-8") + "\n")
        config_bytes = config.read_bytes()
        artifact = self.repo / f".flow/artifacts/{self.spec_id}/pr.html"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("local lens")
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("diff", "--cached"), staged)
        self.assertEqual(config.read_bytes(), config_bytes)
        self.assertEqual(artifact.read_text(encoding="utf-8"), "local lens")
        changed = self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
        self.assertEqual(set(changed), {self.spec_rel, self.task_rel})
        self.assertTrue((self.root / "create-head").exists())

    def test_r2_legacy_split_layout_closes_and_commits_reported_paths(self):
        legacy = self.repo / f".flow/epics/{self.spec_id}.json"
        legacy.parent.mkdir(exist_ok=True)
        (self.repo / self.spec_rel).rename(legacy)
        self.git("add", ".flow")
        self.git("commit", "-qm", "Legacy metadata layout")
        self.spec_rel = legacy.relative_to(self.repo).as_posix()
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.git("show", f"HEAD:{self.spec_rel}"))["status"], "done")
        changed = self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
        self.assertEqual(set(changed), {self.spec_rel, self.task_rel})
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_r2_taskless_spec_opens_without_close(self):
        self.spec_id = self.call("spec_create", title="Taskless PR", branch="feature")["id"]
        self.spec_rel = f".flow/specs/{self.spec_id}.json"
        self.git("add", ".flow")
        self.git("commit", "-qm", "Taskless spec")
        before = self.git("rev-parse", "HEAD")
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "create-head").read_text(encoding="utf-8").strip(), before)
        self.assertEqual(json.loads((self.root / "create-spec.json").read_text(encoding="utf-8"))["status"], "open")
        self.assertFalse(json.loads((self.root / "context.json").read_text(encoding="utf-8"))["spec_closed"])

    def test_r2_html_fallback_preserves_closed_head(self):
        self.call("spec_close", id=self.spec_id)
        self.git("add", self.spec_rel, self.task_rel)
        self.git("commit", "-qm", "Closed")
        before = self.git("rev-parse", "HEAD")
        artifact = self.repo / f".flow/artifacts/{self.spec_id}/pr.html"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("<html>Fallback lens</html>")
        lens = WORKFLOW.with_name("html-lens.md").read_text(encoding="utf-8")
        fence = next(f for f in re.findall(r"```bash\n(.*?)\n\s*```", lens, re.S) if "LENS_OK=true" in f)
        env = dict(os.environ, SPEC_ID=self.spec_id, HTML_AID_STATUS="missing", PHASE0_CONTEXT=json.dumps({"spec_closed": True, "head": before}))
        result = subprocess.run(["bash", "-c", "set -e\n" + fence + '\nprintf "%s" "$LINK_MODE"'], cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(result.stdout, "local")

    def test_r2_head_move_stops_before_push(self):
        document = WORKFLOW.with_name("create-and-finalize.md")
        fence = next(f for f in re.findall(r"```bash\n(.*?)\n```", document.read_text(encoding="utf-8"), re.S) if "PUSH_OUT=$(git push" in f)
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
        self.executable("git", '#!/bin/bash\nif [[ "$1" == push ]]; then touch "$OBSERVATIONS/pushed"; exit 7; fi\nexec ' + shlex.quote(real_git) + ' "$@"\n')
        for context in ({"head": self.git("rev-parse", "main"), "branch": "feature"}, {"head": self.git("rev-parse", "HEAD"), "branch": "other"}):
            with self.subTest(context=context):
                env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"], PHASE0_CONTEXT=json.dumps(dict(context, spec_closed=True)), OBSERVATIONS=str(self.root))
                result = subprocess.run(["bash", "-c", fence], cwd=self.repo, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / "pushed").exists())
                self.assertIn("head changed", result.stderr.lower())

    def test_r2_update_does_not_close_or_commit(self):
        before = self.git("rev-parse", "HEAD")
        result = self.execute(update=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(json.loads((self.repo / self.spec_rel).read_text(encoding="utf-8"))["status"], "open")


if __name__ == "__main__":
    unittest.main()
