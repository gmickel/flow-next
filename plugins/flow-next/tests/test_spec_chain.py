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

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
            [sys.executable, str(FLOWCTL_PY), *args, "--json"],
            cwd=self.repo, capture_output=True, text=True,
            # Inherit PATH: a fixed POSIX PATH finds no git.exe on Windows, and the chain
            # predicate then reports every remote read as failed (CI on #433).
            env={**os.environ, "HOME": str(self.tmp), "FLOW_ACTOR": "t@example.com"},
        )

    def spec(self, title: str, *, tasks: int = 1, done: bool = False, status: str | None = None, deps: list[str] = ()) -> str:
        res = self.flowctl("spec", "create", "--title", title)
        spec_id = json.loads(res.stdout)["id"]
        self.flowctl("spec", "set-branch", spec_id, "--branch", spec_id)
        for i in range(tasks):
            res = self.flowctl("task", "create", "--spec", spec_id, "--title", f"{title} task {i}")
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
        rc, out = self.chain(self.spec("child", deps=[parent]))
        self.assertEqual((rc, out["eligible"], out["parent"], out["reason"]), (0, True, None, "no open dependency"))

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
