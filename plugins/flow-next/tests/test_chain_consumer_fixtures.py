"""Dependent-spec chains, consumer side (fn-152 R13): behaviour fixtures.

Runs the REAL fences the skill prose carries — work's branch step
(`# fence:work-branch`), make-pr's chain detection, merged-parent rewrite,
draft matrix and stack link (`chain-detect`, `chain-rewrite`, `draft-matrix`,
`stack-link`), and flow --auto's verdict prefix (`verdict-reason`) — against a
disposable bare origin, a stubbed `gh` (`fixtures/land_chain_gh_stub.py`), and a
real flowctl. Tests pin behaviour and shapes (refs, boundaries, exit codes,
stub argv, body lines), never prose (G2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_chain_consumer_fixtures.py" -v
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from chain_fixture_support import ChainWorld, fence, git

HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
FLOWCTL_PY = PLUGIN / "scripts" / "flowctl.py"
MAKE_PR = PLUGIN / "skills" / "flow-next-make-pr"
WORK = PLUGIN / "skills" / "flow-next-work" / "phases.md"
AUTO = PLUGIN / "skills" / "flow-next-flow" / "auto.md"

_POSIX = unittest.skipIf(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("jq") is None,
    "chain fixtures need a POSIX bash + jq",
)

DETECT_OUT = ["BASE_REF", "CHAIN_PARENT", "CHAIN_PARENT_BRANCH", "CHAIN_BOUNDARY", "PARENT_PR", "PARENT_PR_STATE", "CHAIN_REWRITE", "REWRITE_ONTO", "COMMITS_AHEAD"]
REWRITE_ENV = {"SPEC_ID": "x", "OPEN_COUNT": "0", "RALPH": "0", "AUTONOMOUS": "0", "NO_MERMAID": "0", "WRITE_MEMORY": "0", "DRAFT_FORCE": "", "HEAD_SHA": "unset", "COMMITS_AHEAD": "0"}


class ConsumerWorld(ChainWorld):
    """ChainWorld plus a real flowctl in the author clone and a tolerant runner."""

    def __init__(self, tmp: Path) -> None:
        super().__init__(tmp)
        shim = self.bin / "flowctl"
        shim.write_text(f"#!/bin/sh\nexec {sys.executable} {FLOWCTL_PY} \"$@\"\n", encoding="utf-8")
        shim.chmod(0o755)
        (self.work / ".git" / "info" / "exclude").write_text(".flow/\n", encoding="utf-8")
        self.flowctl("init")

    def flowctl(self, *args: str) -> dict:
        res = subprocess.run([str(self.bin / "flowctl"), *args, "--json"], cwd=self.work, capture_output=True, text=True,
                             env={"PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin", "HOME": str(self.tmp), "FLOW_ACTOR": "t"})
        return json.loads(res.stdout) if res.stdout.strip() else {}

    def spec(self, title: str, branch: str, *, deps: list[str] = (), tasks_done: bool = True, status: str | None = None) -> str:
        spec_id = self.flowctl("spec", "create", "--title", title, "--branch", branch)["id"]
        task_id = self.flowctl("task", "create", "--spec", spec_id, "--title", f"{title} task")["id"]
        if tasks_done:
            path = self.work / ".flow" / "tasks" / f"{task_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["status"] = "done"
            path.write_text(json.dumps(data), encoding="utf-8")
        for dep in deps:
            self.flowctl("spec", "add-dep", spec_id, dep)
        if status:
            path = self.work / ".flow" / "specs" / f"{spec_id}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["status"] = status
            path.write_text(json.dumps(data), encoding="utf-8")
        return spec_id

    def run_rc(self, script: str, env: dict[str, str], outputs: list[str], cwd: Path) -> tuple[int, dict[str, str]]:
        # `set -e`: the make-pr workflow preamble runs its fences under it, so a fence
        # that only degrades without `set -e` is a fence that aborts in production.
        prelude = "set -e\n" + "".join(f"{k}={v!r}\n" for k, v in env.items())
        epilogue = "\n" + "".join(f'printf "%s\\n" "__OUT__ {k}=${{{k}:-}}"\n' for k in outputs)
        run_env = {"PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin", "HOME": str(self.tmp), "GH_WORLD": str(self.world_path),
                   "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "FLOW_ACTOR": "t"}
        res = subprocess.run(["bash", "-c", prelude + script + epilogue], cwd=cwd, env=run_env, capture_output=True, text=True, timeout=120)
        got = {"_stdout": res.stdout, "_stderr": res.stderr}
        for line in res.stdout.splitlines():
            if line.startswith("__OUT__ "):
                k, _, v = line[8:].partition("=")
                got[k] = v
        return res.returncode, got

    def pull_ref(self, number: int, sha: str) -> None:
        git(self.tmp, "--git-dir", str(self.origin), "update-ref", f"refs/pull/{number}/head", sha)


def parent_child(w: ConsumerWorld) -> tuple[str, str, str]:
    """Parent spec on branch A (1 commit past main), child spec on B (1 commit past A). Returns (parent, child, A tip)."""
    a_tip = w.branch("A", "main", [("a.txt", "a\n")])
    w.branch("B", "A", [("b.txt", "b\n")])
    parent = w.spec("parent", "A")
    child = w.spec("child", "B", deps=[parent])
    return parent, child, a_tip


@_POSIX
class WorkBranchTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn152-work-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ConsumerWorld(self.tmp)
        self.fence = fence(WORK, "work-branch")

    def run_branch(self, spec: str, branch: str, mode: str) -> tuple[int, dict[str, str]]:
        return self.w.run_rc(self.fence, {"FLOWCTL": str(self.w.bin / "flowctl"), "SPEC_ID": spec, "BRANCH_NAME": branch, "BRANCH_MODE": mode, "DEFAULT_BASE": "origin/main"},
                             ["BASE_BRANCH", "CHAIN_PARENT"], cwd=self.w.work)

    def test_new_branch_forks_from_the_parent_tip_and_records_it_as_the_spec_base(self) -> None:
        a_tip = self.w.branch("A", "main", [("a.txt", "a\n")])
        parent = self.w.spec("parent", "A")
        child = self.w.spec("child", "B", deps=[parent])
        git(self.w.work, "checkout", "-q", "main")
        git(self.w.work, "branch", "-D", "A")   # no local parent branch: the fetched remote-tracking ref is the base
        rc, got = self.run_branch(child, "B", "new")
        self.assertEqual(rc, 0, got["_stdout"] + got["_stderr"])
        self.assertEqual((got["BASE_BRANCH"], got["CHAIN_PARENT"]), ("origin/A", parent))
        self.assertEqual(git(self.w.work, "branch", "--show-current"), "B")
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), a_tip)
        self.assertEqual((self.w.work / ".flow" / "tmp" / "spec_base").read_text(encoding="utf-8").strip(), a_tip)
        self.assertEqual(git(self.w.work, "branch", "--list", "A"), "")   # never creates a local branch named after the parent

    def test_new_branch_carries_the_specs_tracked_files_the_parent_tip_lacks(self) -> None:
        (self.w.work / ".git" / "info" / "exclude").write_text("", encoding="utf-8")
        parent = self.w.spec("parent", "A")
        git(self.w.work, "add", ".flow")
        git(self.w.work, "commit", "-q", "-m", "flow: parent")
        git(self.w.work, "push", "-q", "origin", "main")
        a_tip = self.w.branch("A", "main", [("a.txt", "a\n")])
        git(self.w.work, "checkout", "-q", "main")
        child = self.w.spec("child", "B", deps=[parent], tasks_done=False)   # planned on main after the parent branched
        git(self.w.work, "add", ".flow")
        git(self.w.work, "commit", "-q", "-m", "flow: child")
        git(self.w.work, "push", "-q", "origin", "main")
        rc, got = self.run_branch(child, "B", "new")
        self.assertEqual(rc, 0, got["_stdout"] + got["_stderr"])
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD~1"), a_tip)
        self.assertEqual(git(self.w.work, "status", "--porcelain"), "")
        self.assertTrue((self.w.work / ".flow" / "specs" / f"{child}.json").exists())
        self.assertEqual(sorted(git(self.w.work, "diff", "--name-only", "HEAD~1", "HEAD").splitlines()),
                         sorted(f".flow/{p}" for p in (f"specs/{child}.json", f"specs/{child}.md", f"tasks/{child}.1.json", f"tasks/{child}.1.md")))
        ready = self.w.flowctl("ready", "--spec", child)
        self.assertEqual(len(ready["ready"]), 1, ready)

    def test_non_chained_new_branch_forks_from_main(self) -> None:
        solo = self.w.spec("solo", "S")
        rc, got = self.run_branch(solo, "S", "new")
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_BRANCH"], got["CHAIN_PARENT"]), ("origin/main", ""))
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), self.w.origin_sha("main"))

    def test_current_branch_needs_the_parent_tip_in_its_ancestry(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        rc, got = self.run_branch(child, "B", "current")
        self.assertEqual((rc, got["BASE_BRANCH"]), (0, "origin/A"))
        self.assertEqual((self.w.work / ".flow" / "tmp" / "spec_base").read_text(encoding="utf-8").strip(), a_tip)
        git(self.w.work, "checkout", "-q", "-b", "stray", "main")
        rc, got = self.run_branch(child, "stray", "current")
        self.assertEqual(rc, 2)
        self.assertIn("BLOCKED: current branch stray does not contain the parent tip origin/A", got["_stdout"])

    def test_ineligible_spec_blocks_with_the_predicate_reason_before_any_branch(self) -> None:
        parent = self.w.spec("parent", "A")   # all tasks done but never pushed
        child = self.w.spec("child", "B", deps=[parent])
        rc, got = self.run_branch(child, "B", "new")
        self.assertEqual(rc, 2)
        self.assertIn("BLOCKED: parent branch A not on origin; push it or land the parent first", got["_stdout"])
        self.assertEqual(git(self.w.work, "branch", "--list", "B"), "")


@_POSIX
class ChainDetectTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn152-detect-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ConsumerWorld(self.tmp)
        self.fence = fence(MAKE_PR / "workflow.md", "chain-detect")

    def detect(self, spec: str, *, base: str = "", dry_run: str = "0") -> tuple[int, dict[str, str]]:
        env = {"REPO_ROOT": str(self.w.work), "FLOWCTL": str(self.w.bin / "flowctl"), "SPEC_ID": spec, "BASE_REF": base, "DRY_RUN": dry_run, "RALPH": "0", "AUTONOMOUS": "0"}
        return self.w.run_rc(self.fence, env, DETECT_OUT, cwd=self.w.work)

    def test_explicit_base_uses_remote_tracking_when_local_branch_is_stale(self) -> None:
        self.w.branch("advanced", "main", [("upstream.txt", "upstream\n")])
        git(self.w.work, "push", "-q", "origin", "advanced:main")
        self.w.branch("feature", "advanced", [("feature.txt", "feature\n")])
        spec = self.w.spec("explicit base", "feature")
        self.assertNotEqual(git(self.w.work, "rev-parse", "main"),
                            git(self.w.work, "rev-parse", "origin/main"))
        rc, got = self.detect(spec, base="main")
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["COMMITS_AHEAD"]), ("origin/main", "1"))

    def test_open_parent_branch_resolves_the_base_and_the_boundary(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main")
        rc, got = self.detect(child)
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["CHAIN_PARENT"], got["CHAIN_PARENT_BRANCH"], got["CHAIN_BOUNDARY"], got["PARENT_PR"], got["PARENT_PR_STATE"], got["CHAIN_REWRITE"]),
                         ("origin/A", parent, "A", a_tip, "1", "OPEN", "0"))
        self.assertEqual(got["COMMITS_AHEAD"], "1")

    def test_parent_that_advanced_after_the_fork_keeps_the_same_boundary(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main")
        self.w.branch("A", "A", [("a2.txt", "a2\n")])   # parent advances; child still forked at a_tip
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.detect(child)
        self.assertEqual((rc, got["BASE_REF"], got["CHAIN_BOUNDARY"], got["CHAIN_REWRITE"]), (0, "origin/A", a_tip, "0"))

    def test_squash_merged_parent_with_deleted_branch_is_detected_from_the_pr_head(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main", state="MERGED")
        self.w.squash_merge("A")
        self.w.pull_ref(1, a_tip)
        git(self.w.tmp, "--git-dir", str(self.w.origin), "update-ref", "-d", "refs/heads/A")
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.detect(child)
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertEqual((got["BASE_REF"], got["CHAIN_PARENT"], got["CHAIN_BOUNDARY"], got["CHAIN_REWRITE"], got["REWRITE_ONTO"], got["PARENT_PR_STATE"]),
                         ("origin/main", parent, a_tip, "1", "origin/main", "MERGED"))

    def test_parent_advanced_then_squash_merged_still_yields_the_fork_boundary(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main", state="MERGED")
        a2 = self.w.branch("A", "A", [("a2.txt", "a2\n")])
        self.w.squash_merge("A")
        self.w.pull_ref(1, a2)
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.detect(child)   # branch A still on origin: its tip is the ref, the boundary is the fork point
        self.assertEqual((rc, got["CHAIN_BOUNDARY"], got["CHAIN_REWRITE"], got["BASE_REF"]), (0, a_tip, "1", "origin/main"))

    def test_merge_commit_parent_needs_no_rewrite(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main", state="MERGED")
        git(self.w.work, "checkout", "-q", "main")
        git(self.w.work, "merge", "-q", "--no-ff", "-m", "merge A", "A")
        git(self.w.work, "push", "-q", "origin", "main")
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.detect(child)
        self.assertEqual((rc, got["CHAIN_PARENT"], got["BASE_REF"], got["CHAIN_REWRITE"]), (0, "", "origin/main", "0"))

    def test_parent_merged_from_another_clone_is_seen_after_the_base_refresh(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main", state="MERGED")
        git(self.w.land, "fetch", "-q", "origin")                       # another clone lands the parent with a merge commit
        git(self.w.land, "checkout", "-q", "-B", "main", "origin/main")
        git(self.w.land, "merge", "-q", "--no-ff", "-m", "merge A", "origin/A")
        git(self.w.land, "push", "-q", "origin", "main")
        stale = git(self.w.work, "rev-parse", "origin/main")            # this clone's origin/main still predates the merge
        rc, got = self.detect(child)
        self.assertEqual((rc, got["CHAIN_PARENT"], got["BASE_REF"], got["CHAIN_REWRITE"]), (0, "", "origin/main", "0"))
        self.assertNotEqual(git(self.w.work, "rev-parse", "origin/main"), stale)

    def test_unreachable_parent_history_and_closed_parent_exit_2(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        git(self.w.tmp, "--git-dir", str(self.w.origin), "update-ref", "-d", "refs/heads/A")
        rc, got = self.detect(child)
        self.assertEqual(rc, 2)
        self.assertIn(f"NEEDS_HUMAN: cannot establish the chain boundary for {parent}; parent history unreachable", got["_stderr"])
        self.w.branch("A", "A", [])   # back on origin
        git(self.w.work, "checkout", "-q", "B")
        self.w.add_pr(1, "A", "main", state="CLOSED")
        rc, got = self.detect(child)
        self.assertEqual(rc, 2)
        self.assertIn(f"NEEDS_HUMAN: parent {parent} PR #1 closed unmerged; the chain is broken", got["_stderr"])

    def test_closed_unmerged_parent_without_remote_history_still_stops(self) -> None:
        parent, child, _ = parent_child(self.w)
        git(self.w.work, "checkout", "-q", "A")
        closed = self.w.flowctl("spec", "close", parent)
        self.assertEqual(closed["status"], "done")
        git(self.w.work, "add", "-f", ".flow/specs", ".flow/tasks")
        git(self.w.work, "commit", "-q", "-m", "record parent close")
        git(self.w.work, "checkout", "-q", "B")
        git(self.w.work, "merge", "-q", "--no-edit", "A")
        git(self.w.tmp, "--git-dir", str(self.w.origin), "update-ref", "-d", "refs/heads/A")
        rc, got = self.detect(child)
        self.assertEqual(rc, 2, got)
        self.assertIn(parent, got["_stderr"])
        self.assertIn("NEEDS_HUMAN", got["_stderr"])

    def test_merged_parent_whose_chain_base_cannot_be_refreshed_is_unresolved(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main", state="MERGED")
        self.w.squash_merge("A")
        git(self.w.tmp, "--git-dir", str(self.w.origin), "update-ref", "-d", "refs/heads/main")   # the fetch of the chain base fails
        git(self.w.work, "checkout", "-q", "B")
        head = git(self.w.work, "rev-parse", "HEAD")
        rc, got = self.detect(child)
        self.assertEqual(rc, 2)
        self.assertIn("NEEDS_HUMAN: cannot refresh chain base main from origin; no rewrite", got["_stderr"])
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), head)   # exit 2 happened before the rewrite flag was set

    def test_parent_without_a_pr_uses_the_parent_branch_with_no_link_target(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        rc, got = self.detect(child)
        self.assertEqual((rc, got["BASE_REF"], got["CHAIN_PARENT"], got["PARENT_PR"], got["PARENT_PR_STATE"]), (0, "origin/A", parent, "", ""))

    def test_no_dependency_edges_and_explicit_base_leave_the_cascade_untouched(self) -> None:
        self.w.branch("S", "main", [("s.txt", "s\n")])
        solo = self.w.spec("solo", "S")
        rc, got = self.detect(solo)
        self.assertEqual((rc, got["BASE_REF"], got["CHAIN_PARENT"], got["CHAIN_REWRITE"]), (0, "origin/main", "", "0"))
        self.assertEqual(self.w.calls("pr", "list"), [])
        parent, child, _ = parent_child(self.w)
        self.w.add_pr(1, "A", "main")
        rc, got = self.detect(child, base="origin/main")
        self.assertEqual((rc, got["BASE_REF"], got["CHAIN_PARENT"]), (0, "origin/main", ""))

    def test_detection_reads_head_and_ignores_the_scratch_file(self) -> None:
        parent, child, a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main")
        self.w.branch("C", "B", [("c.txt", "c\n")])
        grandchild = self.w.spec("grandchild", "C", deps=[child])
        (self.w.work / ".flow" / "tmp").mkdir(parents=True, exist_ok=True)
        (self.w.work / ".flow" / "tmp" / "spec_base").write_text("deadbeef\n", encoding="utf-8")
        self.w.add_pr(2, "B", "A")
        rc, got = self.detect(grandchild)   # HEAD is C: chained on B at B's tip, whatever the scratch file says
        self.assertEqual((rc, got["CHAIN_PARENT"], got["BASE_REF"]), (0, child, "origin/B"))
        self.assertEqual(got["CHAIN_BOUNDARY"], git(self.w.work, "rev-parse", "origin/B"))
        shutil.rmtree(self.w.work / ".flow" / "tmp")
        rc, got2 = self.detect(grandchild)
        self.assertEqual(got2["CHAIN_BOUNDARY"], got["CHAIN_BOUNDARY"])


@_POSIX
class ChainRewriteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn152-rewrite-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ConsumerWorld(self.tmp)
        self.fence = fence(MAKE_PR / "workflow.md", "chain-rewrite").split("# fence:spec-close", 1)[0]
        self.parent, self.child, self.a_tip = parent_child(self.w)
        self.w.add_pr(1, "A", "main", state="MERGED")
        self.main_tip = self.w.squash_merge("A")
        git(self.w.work, "checkout", "-q", "B")
        git(self.w.work, "fetch", "-q", "origin")
        self.b_tip = git(self.w.work, "rev-parse", "HEAD")

    def rewrite(self, **extra: str) -> tuple[int, dict[str, str]]:
        env = {**REWRITE_ENV, "REPO_ROOT": str(self.w.work), "BASE_REF": "origin/main", "CHAIN_REWRITE": "1", "CHAIN_PARENT": self.parent,
               "CHAIN_BOUNDARY": self.a_tip, "REWRITE_ONTO": "origin/main", "DRY_RUN": "0", "UPDATE_MODE": "0", **extra}
        return self.w.run_rc(self.fence, env, ["HEAD_SHA", "COMMITS_AHEAD", "CHAIN_PARENT"], cwd=self.w.work)

    def test_create_run_rebases_onto_the_chain_base_with_a_leased_push(self) -> None:
        rc, got = self.rewrite()
        self.assertEqual(rc, 0, got["_stderr"])
        head = git(self.w.work, "rev-parse", "HEAD")
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD~1"), self.main_tip)
        self.assertEqual((got["HEAD_SHA"], got["COMMITS_AHEAD"], self.w.origin_sha("B")), (head, "1", head))
        self.assertEqual(got["CHAIN_PARENT"], "")   # a rewritten branch is a standalone bottom layer: no draft exception, no link

    def test_conflict_aborts_and_names_the_files(self) -> None:
        git(self.w.work, "checkout", "-q", "main")
        self.w.commit(self.w.work, "b.txt", "conflict\n", "main edits b")
        git(self.w.work, "push", "-q", "origin", "main")
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.rewrite()
        self.assertEqual(rc, 2)
        self.assertIn(f"NEEDS_HUMAN: parent {self.parent} merged; rebase B onto main conflicts in b.txt", got["_stderr"])
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), self.b_tip)
        self.assertEqual(git(self.w.work, "status", "--porcelain"), "")

    def test_lease_failure_restores_head_and_pushes_nothing(self) -> None:
        self.w.reject_pushes_to("B")
        rc, got = self.rewrite()
        self.assertEqual(rc, 2)
        self.assertIn("NEEDS_HUMAN: B moved on origin during rewrite", got["_stderr"])
        self.assertEqual((git(self.w.work, "rev-parse", "HEAD"), self.w.origin_sha("B")), (self.b_tip, self.b_tip))

    def test_origin_ahead_of_head_refuses_before_rewriting(self) -> None:
        git(self.w.work, "checkout", "-q", "-b", "B-elsewhere", "B")
        moved = self.w.commit(self.w.work, "b2.txt", "b2\n", "someone else")
        git(self.w.work, "push", "-q", "origin", "B-elsewhere:B")
        git(self.w.work, "checkout", "-q", "B")
        rc, got = self.rewrite()
        self.assertEqual(rc, 2)
        self.assertIn(f"NEEDS_HUMAN: B on origin ({moved}) differs from HEAD", got["_stderr"])
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), self.b_tip)

    def test_failed_remote_read_refuses_before_rewriting(self) -> None:
        git(self.w.work, "remote", "set-url", "origin", str(self.tmp / "nowhere.git"))
        rc, got = self.rewrite()
        self.assertEqual(rc, 2)
        self.assertIn("NEEDS_HUMAN: cannot read origin for B; no rewrite", got["_stderr"])
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), self.b_tip)

    def test_dry_run_and_update_never_rewrite_or_push(self) -> None:
        rc, got = self.rewrite(DRY_RUN="1")
        self.assertEqual(rc, 0, got["_stderr"])
        self.assertIn(f"would rebase B onto main from {self.a_tip}", got["_stderr"])
        rc, got2 = self.rewrite(UPDATE_MODE="1")
        self.assertEqual(rc, 0, got2["_stderr"])
        self.assertNotIn("rebase", got2["_stderr"])
        self.assertEqual((git(self.w.work, "rev-parse", "HEAD"), self.w.origin_sha("B")), (self.b_tip, self.b_tip))
        self.assertEqual(self.w.calls("pr", "list"), [])

    def test_a_branch_with_a_prior_pr_is_never_rewritten(self) -> None:
        self.w.add_pr(2, "B", "A", state="MERGED")
        rc, got = self.rewrite()
        self.assertEqual(rc, 2)
        self.assertIn("already has an open or merged PR", got["_stderr"])
        self.assertEqual(git(self.w.work, "rev-parse", "HEAD"), self.b_tip)


@_POSIX
class DraftMatrixTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn152-draft-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ConsumerWorld(self.tmp)
        self.fence = fence(MAKE_PR / "create-and-finalize.md", "draft-matrix")

    def flag(self, *, autonomous: str, open_items: str, force: str, chain: str) -> str:
        rc, got = self.w.run_rc(self.fence, {"RALPH": "0", "AUTONOMOUS": autonomous, "OPEN_ITEMS_COUNT": open_items, "DRAFT_FORCE": force, "CHAIN_PARENT": chain}, ["DRAFT_FLAG"], cwd=self.w.work)
        self.assertEqual(rc, 0, got["_stderr"])
        return got["DRAFT_FLAG"]

    def test_matrix(self) -> None:
        cases = [
            # (autonomous, open_items, force, chain) -> flag
            (("0", "0", "", ""), ""),
            (("0", "2", "", ""), "--draft"),
            (("1", "0", "", ""), "--draft"),
            (("1", "0", "ready", ""), "--draft"),
            (("1", "0", "", "fn-1-parent"), ""),
            (("1", "1", "", "fn-1-parent"), "--draft"),
            (("1", "0", "draft", "fn-1-parent"), "--draft"),
            (("0", "0", "draft", "fn-1-parent"), "--draft"),
            (("0", "2", "ready", "fn-1-parent"), "--draft"),
            (("0", "2", "ready", ""), ""),
        ]
        for (autonomous, open_items, force, chain), expected in cases:
            with self.subTest(autonomous=autonomous, open_items=open_items, force=force, chain=chain):
                self.assertEqual(self.flag(autonomous=autonomous, open_items=open_items, force=force, chain=chain), expected)


@_POSIX
class StackLinkTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn152-stack-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ConsumerWorld(self.tmp)
        self.fence = fence(MAKE_PR / "create-and-finalize.md", "stack-link")
        self.parent, self.child, _ = parent_child(self.w)
        self.w.add_pr(1, "A", "main")
        self.w.add_pr(7, "B", "A")
        self.body = self.tmp / "body.md"
        # fn-252 retires Branch/Tasks headers; stack linkage appends to the briefing.
        self.briefing = "## Why\n\nReview the feature.\n"
        self.body.write_text(self.briefing, encoding="utf-8")
        git(self.w.work, "remote", "set-url", "origin", "https://github.com/o/r.git")

    def link(self, **extra: str) -> tuple[int, dict[str, str]]:
        env = {"REPO_ROOT": str(self.w.work), "PR_URL": "https://github.com/o/r/pull/7", "BODY_FILE": str(self.body), "CHAIN_PARENT": self.parent, "PARENT_PR": "1", "PARENT_PR_STATE": "OPEN", **extra}
        return self.w.run_rc(self.fence, env, ["STACK_LINE"], cwd=self.w.work)

    def posts(self) -> list[list[str]]:
        return [c for c in self.w.calls("api") if "--method" in c]

    def test_creates_a_stack_from_parent_plus_child_with_integer_payloads(self) -> None:
        rc, got = self.link()
        self.assertEqual(rc, 0, got["_stderr"])
        posts = self.posts()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][:4], ["api", "--method", "POST", "repos/o/r/stacks"])
        self.assertEqual([a for a in posts[0] if a.startswith("pull_requests[]=")], ["pull_requests[]=1", "pull_requests[]=7"])
        self.assertEqual(posts[0].count("-F"), 2)
        self.assertNotIn("-f", posts[0])
        self.assertEqual(got["STACK_LINE"], "**Stack:** #11, layer 2 of 2")
        body = self.w.reload()["prs"]["7"]["body"]
        self.assertEqual(body, self.briefing + "\n> **Stack:** #11, layer 2 of 2\n")
        self.assertEqual(body.count("Stack:"), 1)

    def test_adds_to_the_parents_existing_stack(self) -> None:
        self.w.world["stacks"]["11"] = {"pull_requests": [{"number": 1, "state": "open"}]}
        self.w.save()
        rc, got = self.link()
        self.assertEqual(rc, 0, got["_stderr"])
        posts = self.posts()
        self.assertEqual(posts[0][:4], ["api", "--method", "POST", "repos/o/r/stacks/11/add"])
        self.assertEqual([a for a in posts[0] if a.startswith("pull_requests[]=")], ["pull_requests[]=7"])
        self.assertEqual(got["STACK_LINE"], "**Stack:** #11, layer 2 of 2")

    def test_each_degrade_code_prints_one_line_and_leaves_a_plain_layer(self) -> None:
        for code in ("404", "409", "422", "transport"):
            with self.subTest(code=code):
                self.w.world["stack_link_error"] = code
                self.w.world["calls"] = []
                self.w.save()
                rc, got = self.link()
                self.assertEqual(rc, 0)
                self.assertEqual(got["STACK_LINE"], "")
                lines = [ln for ln in got["_stderr"].splitlines() if ln.startswith("stack link skipped: HTTP ")]
                self.assertEqual(len(lines), 1, got["_stderr"])
                self.assertTrue(lines[0].startswith(f"stack link skipped: HTTP {code} "), lines[0])
                self.assertEqual(len(self.posts()), 1)   # no retry
                self.assertEqual(self.w.calls("pr", "edit"), [])
        self.assertNotIn("Stack:", self.body.read_text(encoding="utf-8"))

    def test_update_refresh_reinserts_the_stack_line_from_the_pr_payload(self) -> None:
        refresh = fence(MAKE_PR / "create-and-finalize.md", "stack-line-refresh")
        self.w.world["prs"]["7"]["stack"] = {"number": 11, "position": 2, "size": 3}
        self.w.save()
        rc, got = self.w.run_rc(refresh, {"UPDATE_MODE": "1", "UPDATE_PR_NUMBER": "7", "BODY_FILE": str(self.body)}, ["STACK_LINE"], cwd=self.w.work)
        self.assertEqual(rc, 0, got["_stderr"])
        body = self.body.read_text(encoding="utf-8")
        self.assertEqual(body, self.briefing + "\n> **Stack:** #11, layer 2 of 3\n")
        rc, _ = self.w.run_rc(refresh, {"UPDATE_MODE": "1", "UPDATE_PR_NUMBER": "7", "BODY_FILE": str(self.body)}, ["STACK_LINE"], cwd=self.w.work)
        self.assertEqual(self.body.read_text(encoding="utf-8").count("Stack:"), 1)   # idempotent
        self.w.world["prs"]["7"]["stack"] = None
        self.w.save()
        self.body.write_text(self.briefing, encoding="utf-8")
        rc, _ = self.w.run_rc(refresh, {"UPDATE_MODE": "1", "UPDATE_PR_NUMBER": "7", "BODY_FILE": str(self.body)}, ["STACK_LINE"], cwd=self.w.work)
        self.assertEqual((rc, self.body.read_text(encoding="utf-8")), (0, self.briefing))
        self.assertEqual([c for c in self.w.calls("api") if "--method" in c], [])

    def test_non_github_remote_and_missing_parent_pr_make_no_call(self) -> None:
        git(self.w.work, "remote", "set-url", "origin", str(self.w.origin))
        rc, got = self.link()
        self.assertEqual((rc, got["STACK_LINE"], got["_stderr"], self.w.calls("api")), (0, "", "", []))
        git(self.w.work, "remote", "set-url", "origin", "https://github.com/o/r.git")
        rc, got = self.link(PARENT_PR="", PARENT_PR_STATE="")
        self.assertEqual((rc, got["STACK_LINE"], self.w.calls("api")), (0, "", []))
        rc, got = self.link(CHAIN_PARENT="")
        self.assertEqual((rc, self.w.calls("api")), (0, []))


@_POSIX
class VerdictReasonTestCase(unittest.TestCase):
    def test_prefix_only_on_a_chained_spec(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="fn152-verdict-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        w = ConsumerWorld(tmp)
        script = fence(AUTO, "verdict-reason")
        rc, got = w.run_rc(script, {"CHAIN_PARENT": "fn-9-parent", "REASON": "make-pr: open PR https://x/pull/3"}, ["REASON"], cwd=w.work)
        self.assertEqual((rc, got["REASON"]), (0, "chained on fn-9-parent; make-pr: open PR https://x/pull/3"))
        rc, got = w.run_rc(script, {"CHAIN_PARENT": "", "REASON": "make-pr: open PR https://x/pull/3"}, ["REASON"], cwd=w.work)
        self.assertEqual((rc, got["REASON"]), (0, "make-pr: open PR https://x/pull/3"))


if __name__ == "__main__":
    unittest.main()
