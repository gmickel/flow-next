"""`flowctl spec chain` and the chained task-admission gate (fn-152 R1/R2/R2a/R13).

Each test builds a disposable clone with a bare `origin`, mints specs through
flowctl itself, and reads the predicate through the CLI so the exit codes and
the exhaustive output shape are pinned end to end. The admission gates
(`ready --spec`, `next`, `ready --all`) are read through the same clone so a
chained parent is proven satisfied where the work schedulers look.

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_spec_chain.py" -v
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
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD

HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"

SHAPE = {"success", "spec", "eligible", "parent", "parent_branch", "parent_branch_on_remote", "reason"}


def git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {out.stderr}")
    return out.stdout.strip()


class ChainCliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn152-chain-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin = self.tmp / "origin.git"
        self.repo = self.tmp / "repo"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(self.tmp, "clone", "-q", str(self.origin), str(self.repo))
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "checkout", "-q", "-b", "main")
        (self.repo / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", "base.txt")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "push", "-q", "-u", "origin", "main")
        self.flowctl("init")

    # ---- flowctl ----
    def flowctl(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [*FLOWCTL_CMD, *args, "--json"],
            cwd=self.repo, capture_output=True, text=True,
            # Inherit PATH: a fixed POSIX PATH finds no git.exe on Windows, and the chain
            # predicate then reports every remote read as failed (CI on #433).
            env={**os.environ, "HOME": str(self.tmp), "FLOW_ACTOR": "t@example.com"},
        )

    def spec(self, title: str, *, tasks: int = 1, done: bool = False, status: str | None = None, deps: list[str] = ()) -> str:
        res = self.flowctl("spec", "create", "--title", title)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        spec_id = json.loads(res.stdout)["id"]
        self.flowctl("spec", "set-branch", spec_id, "--branch", spec_id)
        for i in range(tasks):
            res = self.flowctl("task", "create", "--spec", spec_id, "--title", f"{title} task {i}")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            task_id = json.loads(res.stdout)["id"]
            if done:
                self.patch(self.repo / ".flow" / "tasks" / f"{task_id}.json", status="done")
        for dep in deps:
            self.flowctl("spec", "add-dep", spec_id, dep)
        if status:
            self.patch(self.repo / ".flow" / "specs" / f"{spec_id}.json", status=status)
        return spec_id

    @staticmethod
    def patch(path: Path, **fields) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(fields)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def push_branch(self, name: str) -> None:
        git(self.repo, "push", "-q", "origin", f"HEAD:refs/heads/{name}")

    def chain(self, spec_id: str) -> tuple[int, dict]:
        res = self.flowctl("spec", "chain", spec_id)
        return res.returncode, json.loads(res.stdout)

    # ---- R2: the exhaustive states ----
    def test_no_dependencies_is_eligible_without_a_remote_read(self) -> None:
        git(self.repo, "remote", "set-url", "origin", str(self.tmp / "nowhere.git"))
        rc, out = self.chain(self.spec("solo"))
        self.assertEqual(rc, 0)
        self.assertEqual(set(out), SHAPE)
        self.assertEqual((out["eligible"], out["parent"], out["parent_branch"], out["parent_branch_on_remote"], out["reason"]),
                         (True, None, None, None, "no open dependency"))

    def test_all_dependencies_done_is_eligible_with_null_parent(self) -> None:
        parent = self.spec("parent", done=True, status="done")
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "closed parent at base")
        git(self.repo, "push", "-q", "origin", "main")
        rc, out = self.chain(self.spec("child", deps=[parent]))
        self.assertEqual((rc, out["eligible"], out["parent"], out["reason"]), (0, True, None, "no open dependency"))

    def closed_parent_branch(self) -> tuple[str, str]:
        parent = self.spec("parent", done=True)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "open parent at base")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-q", "-b", parent)
        closed = self.flowctl("spec", "close", parent)
        self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "close on parent branch")
        child = self.spec("child", deps=[parent])
        return parent, child

    def assert_dependency_blocked(self, parent: str, child: str) -> None:
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual((ready["ready"], ready["blocked_by_specs"]), ([], [parent]))
        nxt = json.loads(self.flowctl("next").stdout)
        self.assertEqual(nxt["blocked_specs"], {child: [parent]})
        rows = {r["id"]: r for r in json.loads(self.flowctl("ready", "--all").stdout)["specs"]}
        self.assertEqual(rows[child]["blockedBy"], [parent])

    def test_branch_closed_parent_stays_chained_and_unpushed_parent_blocks(self) -> None:
        parent, child = self.closed_parent_branch()
        rc, out = self.chain(child)
        self.assertEqual((rc, out["eligible"], out["parent"]), (0, False, parent))
        self.assert_dependency_blocked(parent, child)
        # Publishing the branch permits the existing chain admission waiver,
        # but must not erase the parent before it has merged.
        self.push_branch(parent)
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, parent))

    def test_parent_advanced_after_child_stacked_stays_unlanded(self) -> None:
        parent, child = self.closed_parent_branch()
        self.push_branch(parent)
        git(self.repo, "checkout", "-q", "-b", child)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "stack child")
        git(self.repo, "checkout", "-q", parent)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "parent review fix")
        self.push_branch(parent)
        git(self.repo, "checkout", "-q", child)
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, parent))
        self.assertIn(f"dependency branch refs/remotes/origin/{parent}", out["reason"])
        git(self.origin, "update-ref", "-d", f"refs/heads/{parent}")
        self.assert_dependency_blocked(parent, child)

    def test_base_closed_parent_is_unchained_and_unblocked(self) -> None:
        parent, child = self.closed_parent_branch()
        git(self.repo, "push", "-q", "origin", "HEAD:main")
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, None))
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual(len(ready["ready"]), 1)
        self.assertNotIn("blocked_by_specs", ready)
        nxt = json.loads(self.flowctl("next").stdout)
        self.assertEqual((nxt["status"], nxt["spec"]), ("work", child))
        rows = {r["id"]: r for r in json.loads(self.flowctl("ready", "--all").stdout)["specs"]}
        self.assertEqual(rows[child]["blockedBy"], [])

    def integration_parent(self, *, merge_commit: bool = False) -> str:
        parent = self.spec("integration parent", done=True)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "open integration parent")
        start = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "-b", parent)
        closed = self.flowctl("spec", "close", parent)
        self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "close integration parent")
        self.push_branch(parent)
        git(self.repo, "checkout", "-q", "-B", "integration", start)
        if merge_commit:
            git(self.repo, "merge", "-q", "--no-ff", "-m", "merge parent", parent)
        else:
            git(self.repo, "merge", "-q", "--squash", parent)
            git(self.repo, "commit", "-q", "-m", "squash parent into integration")
        return parent

    def assert_dependency_landed(self, child: str) -> None:
        rc, out = self.chain(child)
        self.assertEqual((rc, out["eligible"], out["parent"], out["reason"]),
                         (0, True, None, "no open dependency"))
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual([t["id"] for t in ready["ready"]], [child + ".1"])
        self.assertNotIn("blocked_by_specs", ready)
        nxt = json.loads(self.flowctl("next").stdout)
        self.assertEqual((nxt["status"], nxt["spec"]), ("work", child))
        rows = {r["id"]: r for r in json.loads(self.flowctl("ready", "--all").stdout)["specs"]}
        self.assertEqual(rows[child]["blockedBy"], [])

    def test_integration_squash_unchains_and_unblocks_child(self) -> None:
        parent = self.integration_parent()
        git(self.repo, "checkout", "-q", "-b", "child")
        self.assert_dependency_landed(self.spec("child", deps=[parent]))

    def test_integration_squash_deleted_branches_are_landed(self) -> None:
        parent = self.integration_parent()
        git(self.repo, "branch", "-D", parent)
        git(self.repo, "push", "-q", "origin", "--delete", parent)
        self.assertEqual(git(self.repo, "branch", "-a", "--list", parent, f"remotes/origin/{parent}"), "")
        git(self.repo, "checkout", "-q", "-b", "child")
        self.assert_dependency_landed(self.spec("child", deps=[parent]))

    def test_two_integration_squashes_have_no_open_parents(self) -> None:
        parents = [self.integration_parent(), self.integration_parent()]
        git(self.repo, "checkout", "-q", "-b", "child")
        self.assert_dependency_landed(self.spec("child", deps=parents))

    def test_stacked_child_blocks_until_chain_waiver(self) -> None:
        parent, child = self.closed_parent_branch()
        git(self.repo, "checkout", "-q", "-b", "child")
        self.assert_dependency_blocked(parent, child)
        self.push_branch(parent)
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, parent))
        self.assertIn("in this branch's history", out["reason"])
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual([t["id"] for t in ready["ready"]], [child + ".1"])
        self.assertNotIn("blocked_by_specs", ready)

    def test_integration_merge_commit_conservatively_keeps_parent(self) -> None:
        parent = self.integration_parent(merge_commit=True)
        git(self.repo, "checkout", "-q", "-b", "child")
        child = self.spec("child", deps=[parent])
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, parent))
        self.assertIn(f"dependency {parent} closed locally but not recorded at origin/main", out["reason"])
        self.assertIn("in this branch's history", out["reason"])
        # Removing the server branch disables the waiver; local refs still
        # conservatively identify the merged parent in HEAD's ancestry.
        git(self.origin, "update-ref", "-d", f"refs/heads/{parent}")
        self.assert_dependency_blocked(parent, child)

    def test_unreadable_parent_ref_fails_closed(self) -> None:
        storage = subprocess.run(
            ["git", "config", "extensions.refstorage"], cwd=self.repo,
            capture_output=True, text=True, encoding="utf-8",
        )
        if storage.stdout.strip() == "reftable":
            self.skipTest("loose-ref corruption requires the files ref backend")
        parent = self.integration_parent()
        git(self.repo, "checkout", "-q", "-b", "child")
        child = self.spec("child", deps=[parent])
        # An existing ref pointing at a missing object is not a deleted branch.
        ref = self.repo / ".git" / "refs" / "remotes" / "origin" / parent
        ref.write_text("f" * 40 + "\n", encoding="utf-8", newline="\n")
        _, out = self.chain(child)
        self.assertFalse(out["eligible"])
        self.assertIn("base query failed: base read failed:", out["reason"])
        self.assert_dependency_blocked(parent, child)

    def test_unrelated_remote_history_continues_to_local_ref(self) -> None:
        parent, child = self.closed_parent_branch()
        git(self.repo, "checkout", "-q", "-b", "child")
        root = git(self.repo, "commit-tree", "HEAD^{tree}", "-m", "unrelated root")
        git(self.repo, "update-ref", f"refs/remotes/origin/{parent}", root)
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (False, parent))
        self.assertIn(f"dependency branch refs/heads/{parent}", out["reason"])
        git(self.repo, "branch", "-D", parent)
        self.assert_dependency_landed(child)

    def test_done_dependency_without_branch_is_landed(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "child")
        parent = self.spec("parent", done=True, status="done")
        self.patch(self.repo / ".flow" / "specs" / f"{parent}.json", branch_name=None)
        self.assert_dependency_landed(self.spec("child", deps=[parent]))

    def test_no_base_ref_lets_the_local_close_stand(self) -> None:
        # A repo with no default branch to merge into (or no git at all) has
        # no base evidence to wait for; the pre-chain reading of done applies.
        parent, child = self.closed_parent_branch()
        self.push_branch(parent)
        git(self.repo, "update-ref", "-d", "refs/heads/main")
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")
        second = self.spec("second closed parent", done=True, status="done")
        self.flowctl("spec", "add-dep", child, second)
        res = self.flowctl("spec", "chain", child)
        out = json.loads(res.stdout)
        self.assertEqual((res.returncode, out["eligible"], out["parent"]), (0, True, None))
        self.assertEqual(res.stderr.count("note: no base ref resolved"), 1)
        for token in ("refs/remotes/origin/HEAD", "origin/main", "main",
                      "origin/master", "master", "using local status"):
            self.assertIn(token, res.stderr)
            self.assertIn(token, out["reason"])
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual(len(ready["ready"]), 1)

    def test_stale_base_with_server_deleted_parent_keeps_tracking_ref_history(self) -> None:
        parent = self.spec("parent", done=True, status="done")
        child = self.spec("child", deps=[parent])
        git(self.repo, "checkout", "-q", "-b", parent)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "closed parent")
        self.push_branch(parent)
        # Model a merge and branch deletion elsewhere, without refreshing
        # this checkout's origin/main (where the parent is absent).
        git(self.origin, "update-ref", "refs/heads/main", git(self.repo, "rev-parse", "HEAD"))
        git(self.origin, "update-ref", "-d", f"refs/heads/{parent}")
        _, out = self.chain(child)
        self.assertFalse(out["eligible"])
        self.assertEqual(out["reason"],
                         f"dependency {parent} closed locally but not recorded at origin/main; "
                         f"dependency branch refs/remotes/origin/{parent} is in this branch's history; "
                         "fetch the base or land it")
        self.assertNotIn("push it", out["reason"])

    def test_brief_reads_local_status_without_git_or_remote(self) -> None:
        # brief keeps its zero-git contract: a parent closed on its own branch
        # reads unblocked there, as the schedulers' chain-parent waiver does,
        # and a broken remote cannot affect it.
        parent, child = self.closed_parent_branch()
        self.push_branch(parent)
        git(self.repo, "remote", "set-url", "origin", str(self.tmp / "nowhere.git"))
        res = self.flowctl("brief", "--full")
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        self.assertIn(child + ".1", json.dumps(out["actionable_tasks"]["items"]))

    def test_base_resolution_cache_is_success_only_and_cwd_scoped(self) -> None:
        scripts_dir = str(Path(__file__).resolve().parents[1] / "scripts")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        self.addCleanup(sys.path.remove, scripts_dir)
        spec = importlib.util.spec_from_file_location("flowctl_chain_cache", FLOWCTL_PY)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        self.addCleanup(sys.modules.pop, spec.name)
        spec.loader.exec_module(mod)
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(self.repo)
        git(self.repo, "checkout", "-q", "-b", "feature")  # off the base, on the parent tip
        parent = self.spec("parent", done=True, status="done")
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "record close for cached reads")
        with mock.patch.object(mod.subprocess, "run", wraps=subprocess.run) as run:
            for _ in range(2):
                self.assertFalse(mod.spec_landed_at_base(self.repo / ".flow", parent, {"status": "done", "branch_name": "feature"})[0])
            self.assertEqual(sum(c.args[0][-1] == "refs/remotes/origin/HEAD" for c in run.call_args_list), 1)
        other = self.tmp / "other"
        other.mkdir()
        git(other, "init", "-q", "-b", "develop")
        os.chdir(other)
        with mock.patch.object(mod.subprocess, "run", wraps=subprocess.run) as run:
            for _ in range(2):
                self.assertTrue(mod.spec_landed_at_base(other / ".flow", parent, {"status": "done"})[0])
            self.assertEqual(sum(c.args[0][-1] == "refs/remotes/origin/HEAD" for c in run.call_args_list), 2)
        self.assertNotIn(other, mod._SPEC_BASE_CACHE)

    def test_close_on_the_base_branch_itself_stands(self) -> None:
        # Work done directly on the base has nothing left to merge.
        parent = self.spec("parent", done=True, status="done")
        child = self.spec("child", deps=[parent])
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, None))

    def test_done_parent_absent_at_base_is_not_landed(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature")
        parent = self.spec("parent", done=True, status="done")
        git(self.repo, "checkout", "-q", "-b", parent)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "close parent absent from base")
        git(self.repo, "checkout", "-q", "-b", "child")
        child = self.spec("child", deps=[parent])
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (False, parent))
        self.assert_dependency_blocked(parent, child)

    def test_open_parent_with_all_tasks_done_and_branch_on_origin_is_eligible(self) -> None:
        parent = self.spec("parent", done=True)
        self.push_branch(parent)
        rc, out = self.chain(self.spec("child", deps=[parent]))
        self.assertEqual(rc, 0)
        self.assertEqual((out["eligible"], out["parent"], out["parent_branch"], out["parent_branch_on_remote"]),
                         (True, parent, parent, True))
        self.assertEqual(out["reason"], "parent open, all tasks done, branch on origin")

    def test_no_plan_parent_counts_its_implicit_task(self) -> None:
        res = self.flowctl("spec", "create", "--title", "direct parent")
        parent = json.loads(res.stdout)["id"]
        self.flowctl("spec", "set-branch", parent, "--branch", parent)
        self.flowctl("spec", "set-no-plan", parent)
        child = self.spec("child", deps=[parent])
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["reason"]), (False, f"dependency {parent} in progress"))
        res = self.flowctl("task", "create", "--spec", parent, "--title", "implicit owner")
        self.patch(self.repo / ".flow" / "tasks" / f"{json.loads(res.stdout)['id']}.json", status="done", implicit_owner=True)
        self.push_branch(parent)
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, parent))

    def test_parent_with_unfinished_tasks_refuses_naming_it(self) -> None:
        parent = self.spec("parent", tasks=2)
        _, out = self.chain(self.spec("child", deps=[parent]))
        self.assertEqual((out["eligible"], out["parent"], out["parent_branch_on_remote"], out["reason"]),
                         (False, None, None, f"dependency {parent} in progress"))

    def test_two_open_parents_refuse_naming_both(self) -> None:
        a = self.spec("a", done=True)
        b = self.spec("b", done=True)
        _, out = self.chain(self.spec("child", deps=[a, b]))
        self.assertEqual((out["eligible"], out["parent"]), (False, None))
        self.assertEqual(out["reason"], f"two open parents: {a}, {b}; chains are linear")

    def test_unpushed_parent_refuses_with_branch_absent(self) -> None:
        parent = self.spec("parent", done=True)
        _, out = self.chain(self.spec("child", deps=[parent]))
        self.assertEqual((out["eligible"], out["parent"], out["parent_branch_on_remote"]), (False, parent, False))
        self.assertEqual(out["reason"], f"parent branch {parent} not on origin; push it or land the parent first")

    def test_sibling_already_chained_refuses_naming_the_sibling(self) -> None:
        parent = self.spec("parent", done=True)
        self.push_branch(parent)
        sibling = self.spec("first child", deps=[parent])
        self.push_branch(sibling)
        _, out = self.chain(self.spec("second child", deps=[parent]))
        self.assertEqual((out["eligible"], out["parent"], out["parent_branch_on_remote"]), (False, parent, True))
        self.assertEqual(out["reason"], f"parent {parent} already chained by {sibling}")
        # a sibling that has not pushed is invisible to the predicate (documented race window)
        git(self.tmp, "--git-dir", str(self.origin), "update-ref", "-d", f"refs/heads/{sibling}")
        _, out = self.chain(self.spec("third child", deps=[parent]))
        self.assertTrue(out["eligible"])

    def test_closed_unmerged_sibling_still_occupies_chain(self) -> None:
        # Seen from a branch that carries the sibling's close (on the base
        # itself the sibling still reads open and occupies the chain as before).
        git(self.repo, "checkout", "-q", "-b", "feature")
        parent = self.spec("parent", done=True)
        self.push_branch(parent)
        sibling = self.spec("first child", done=True, status="done", deps=[parent])
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "record sibling close")
        self.push_branch(sibling)
        _, out = self.chain(self.spec("second child", deps=[parent]))
        self.assertEqual((out["eligible"], out["parent"]), (False, parent))
        self.assertIn(sibling, out["reason"])

    def test_divergent_closed_sibling_currently_does_not_occupy_chain(self) -> None:
        parent, child = self.closed_parent_branch()
        sibling = self.spec("first child", done=True, deps=[parent])
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "record children on parent")
        self.push_branch(parent)
        git(self.repo, "checkout", "-q", "-b", sibling)
        closed = self.flowctl("spec", "close", sibling)
        self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "close first child")
        self.push_branch(sibling)
        git(self.repo, "checkout", "-q", "-b", child, parent)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "second child work")
        # Shared local metadata knows the sibling is closed, but its close
        # commit belongs only to the divergent sibling branch.
        self.patch(self.repo / ".flow" / "specs" / f"{sibling}.json", status="done")
        shared = git(self.repo, "merge-base", sibling, "HEAD")
        self.assertNotEqual(shared, git(self.repo, "rev-parse", sibling))
        self.assertNotEqual(shared, git(self.repo, "rev-parse", "HEAD"))
        _, out = self.chain(child)
        self.assertEqual((out["eligible"], out["parent"]), (True, parent))
        self.assertNotIn(f"already chained by {sibling}", out["reason"])

    def test_legacy_base_close_is_landing_evidence(self) -> None:
        parent = self.spec("parent", done=True, status="done")
        canonical = self.repo / ".flow" / "specs" / f"{parent}.json"
        legacy = self.repo / ".flow" / "epics" / f"{parent}.json"
        legacy.parent.mkdir(exist_ok=True)
        canonical.rename(legacy)
        git(self.repo, "add", ".flow")
        git(self.repo, "commit", "-q", "-m", "closed legacy parent at base")
        git(self.repo, "push", "-q", "origin", "main")
        legacy.rename(canonical)
        _, out = self.chain(self.spec("child", deps=[parent]))
        self.assertEqual((out["eligible"], out["parent"]), (True, None))

    def test_remote_failure_is_distinct_from_an_absent_branch(self) -> None:
        parent = self.spec("parent", done=True)
        child = self.spec("child", deps=[parent])
        git(self.repo, "remote", "set-url", "origin", str(self.tmp / "nowhere.git"))
        rc, out = self.chain(child)
        self.assertEqual((rc, out["eligible"], out["parent"], out["parent_branch_on_remote"]), (0, False, parent, None))
        self.assertTrue(out["reason"].startswith("remote query failed: "), out["reason"])
        self.assertNotIn("not on origin", out["reason"])

    def test_unknown_spec_and_missing_dependency_exit_2(self) -> None:
        res = self.flowctl("spec", "chain", "fn-999")
        self.assertEqual(res.returncode, 2)
        self.assertEqual(json.loads(res.stdout)["error"], "Spec fn-999 not found")
        child = self.spec("child")
        self.patch(self.repo / ".flow" / "specs" / f"{child}.json", depends_on_epics=["fn-777"])
        res = self.flowctl("spec", "chain", child)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(json.loads(res.stdout)["error"], f"Spec {child}: depends_on_epics missing spec fn-777")

    # ---- R2a: the task-admission gate ----
    def test_admission_gates_treat_the_chain_parent_as_satisfied(self) -> None:
        parent = self.spec("parent", done=True)
        child = self.spec("child", deps=[parent])
        # unpushed parent: every gate still blocks
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual((ready["ready"], ready["blocked_by_specs"]), ([], [parent]))
        nxt = json.loads(self.flowctl("next").stdout)
        self.assertEqual(nxt["blocked_specs"], {child: [parent]})
        rows = {r["id"]: r for r in json.loads(self.flowctl("ready", "--all").stdout)["specs"]}
        self.assertEqual(rows[child]["blockedBy"], [parent])
        # pushed parent: the chain parent is satisfied and the child's task is admitted
        self.push_branch(parent)
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual(len(ready["ready"]), 1)
        self.assertNotIn("blocked_by_specs", ready)
        nxt = json.loads(self.flowctl("next").stdout)
        self.assertEqual((nxt["status"], nxt["spec"], nxt["reason"]), ("work", child, "ready_task"))
        rows = {r["id"]: r for r in json.loads(self.flowctl("ready", "--all").stdout)["specs"]}
        self.assertEqual(rows[child]["blockedBy"], [])

    def test_admission_gate_keeps_every_other_unfinished_dependency_blocking(self) -> None:
        parent = self.spec("parent", done=True)
        self.push_branch(parent)
        other = self.spec("other", tasks=1)
        child = self.spec("child", deps=[parent, other])
        ready = json.loads(self.flowctl("ready", "--spec", child).stdout)
        self.assertEqual(sorted(ready["blocked_by_specs"]), sorted([parent, other]))
        task_deps = self.spec("with task deps", tasks=2, deps=[parent])
        tasks = sorted((self.repo / ".flow" / "tasks").glob(f"{task_deps}.*.json"))
        self.patch(tasks[1], depends_on=[tasks[0].stem])
        ready = json.loads(self.flowctl("ready", "--spec", task_deps).stdout)
        self.assertEqual([t["id"] for t in ready["ready"]], [tasks[0].stem])
        self.assertEqual([t["blocked_by"] for t in ready["blocked"]], [[tasks[0].stem]])

    # ---- R9: the decision-log row carries the chained reason ----
    def test_pilot_log_row_carries_the_reason_only_when_given(self) -> None:
        spec = self.spec("subject")
        res = self.flowctl("pilot-log", "append", "--id", spec, "--action", "advanced", "--stage", "work",
                           "--reason", "chained on fn-1-parent; work: 1 task done")
        self.assertEqual(res.returncode, 0, res.stdout)
        rows = sorted((self.repo / ".flow" / "pilot-runs").glob("pilot-*.json"))
        self.assertEqual(json.loads(rows[-1].read_text(encoding="utf-8"))["reason"], "chained on fn-1-parent; work: 1 task done")
        self.flowctl("pilot-log", "append", "--id", spec, "--action", "advanced", "--stage", "work")
        rows = sorted((self.repo / ".flow" / "pilot-runs").glob("pilot-*.json"), key=lambda p: p.stat().st_mtime)
        self.assertEqual(set(json.loads(rows[-1].read_text(encoding="utf-8"))), {"tick", "id", "action", "stage", "costTokens", "timestamp"})


if __name__ == "__main__":
    unittest.main()
