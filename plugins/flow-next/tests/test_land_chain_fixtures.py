"""Land over chains and stacks (fn-149 R16): behaviour fixtures.

Each test builds a disposable bare origin plus a land clone, stubs `gh` with
`fixtures/land_chain_gh_stub.py` (a JSON world file the stub reads and
mutates), and runs the REAL fences sliced out of the land workflow and its
chains-and-stacks reference by their `# fence:<name>` marker. The tests pin
behaviour and shapes (branch tips, boundaries, patch-ids, ledger fields,
verdict tokens), never prose (G2).

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -p "test_land_chain_fixtures.py" -v
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN = HERE.parent.parent
LAND = PLUGIN / "skills" / "flow-next-land"
MIRROR_LAND = PLUGIN / "codex" / "skills" / "flow-next-land"
WORKFLOW = LAND / "workflow.md"
REFERENCE = LAND / "references" / "chains-and-stacks.md"
STUB = HERE.parent / "fixtures" / "land_chain_gh_stub.py"

_POSIX = unittest.skipIf(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("jq") is None,
    "chain fixtures need a POSIX bash + jq",
)

_FENCE_RE = re.compile(r"^[ \t]*# fence:(?P<name>[a-z-]+)\b.*?$", re.MULTILINE)


def fence(path: Path, name: str) -> str:
    """The bash block that starts at `# fence:<name>` up to its closing ```."""
    text = path.read_text(encoding="utf-8")
    for m in _FENCE_RE.finditer(text):
        if m.group("name") == name:
            end = text.index("```", m.end())
            block = text[m.start():end]
            # the frontier fence is indented inside a list item
            indent = re.match(r"[ \t]*", block).group(0)
            return "\n".join(line[len(indent):] if line.startswith(indent) else line for line in block.splitlines()) + "\n"
    raise AssertionError(f"fence {name!r} not found in {path}")


def scan_fence(path: Path) -> str:
    """The §2.6 clean-review comment scan: from its `if` to the end of its bash block."""
    text = path.read_text(encoding="utf-8")
    start = text.index('if [[ "$REVIEW_SIGNAL" == "silence" && -n "$CLEAN_REVIEW_PATTERN" ]]; then')
    end = text.index("```", start)
    return text[start:end]


def git(cwd: Path, *args: str, check: bool = True) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and out.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {out.stderr}")
    return out.stdout.strip()


class ChainWorld:
    """Bare origin + author clone + land clone + gh world for one scenario."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.origin = tmp / "origin.git"
        self.work = tmp / "work"
        self.land = tmp / "land"
        self.ledger_dir = tmp / "ledger"
        self.ledger = self.ledger_dir / "land-strikes.json"
        self.world_path = tmp / "world.json"
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(f"#!/bin/sh\nexec {sys.executable} {STUB} \"$@\"\n", encoding="utf-8")
        gh.chmod(0o755)
        git(tmp, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(tmp, "clone", "-q", str(self.origin), str(self.work))
        git(self.work, "config", "user.email", "t@example.com")
        git(self.work, "config", "user.name", "t")
        git(self.work, "checkout", "-q", "-b", "main")
        self.commit(self.work, "base.txt", "base\n", "base")
        git(self.work, "push", "-q", "-u", "origin", "main")
        git(tmp, "clone", "-q", str(self.origin), str(self.land))
        git(self.land, "config", "user.email", "land@example.com")
        git(self.land, "config", "user.name", "land")
        self.world = {"owner_repo": "o/r", "origin": str(self.origin), "prs": {}, "stacks": {}, "delete_mode": "ok", "comments": {}, "calls": []}
        self.save()

    # ---- world ----
    def save(self) -> None:
        self.world_path.write_text(json.dumps(self.world), encoding="utf-8")

    def reload(self) -> dict:
        self.world = json.loads(self.world_path.read_text(encoding="utf-8"))
        return self.world

    def add_pr(self, number: int, head: str, base: str, stack: dict | None = None, state: str = "OPEN") -> None:
        self.world["prs"][str(number)] = {
            "number": number, "url": f"https://github.com/o/r/pull/{number}", "state": state,
            "headRefName": head, "baseRefName": base, "stack": stack, "mergedAt": None, "reviewDecision": "",
        }
        self.save()

    def calls(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.reload()["calls"] if c[:len(prefix)] == list(prefix)]

    # ---- git ----
    def commit(self, cwd: Path, name: str, content: str, msg: str) -> str:
        (cwd / name).write_text(content, encoding="utf-8")
        git(cwd, "add", name)
        git(cwd, "commit", "-q", "-m", msg)
        return git(cwd, "rev-parse", "HEAD")

    def branch(self, name: str, from_ref: str, files: list[tuple[str, str]]) -> str:
        git(self.work, "checkout", "-q", "-B", name, from_ref)
        for f, c in files:
            self.commit(self.work, f, c, f"{name}: {f}")
        git(self.work, "push", "-q", "-f", "-u", "origin", name)
        return git(self.work, "rev-parse", "HEAD")

    def squash_merge(self, branch: str, into: str = "main") -> str:
        git(self.work, "fetch", "-q", "origin")
        git(self.work, "checkout", "-q", "-B", into, f"origin/{into}")
        git(self.work, "merge", "-q", "--squash", f"origin/{branch}")
        git(self.work, "commit", "-q", "-m", f"squash {branch}")
        git(self.work, "push", "-q", "origin", into)
        return git(self.work, "rev-parse", "HEAD")

    def origin_sha(self, branch: str) -> str:
        return git(self.tmp, "--git-dir", str(self.origin), "rev-parse", "-q", "--verify", f"refs/heads/{branch}", check=False)

    def patch_id(self, base: str, head: str) -> str:
        git(self.land, "fetch", "-q", "origin")
        diff = subprocess.run(["git", "diff", f"origin/{base}...origin/{head}"], cwd=self.land, capture_output=True, text=True).stdout
        out = subprocess.run(["git", "patch-id", "--stable"], cwd=self.land, input=diff, capture_output=True, text=True).stdout
        return out.split()[0] if out else ""

    def boundary(self, child: str, parent: str) -> str:
        git(self.land, "fetch", "-q", "origin")
        return git(self.land, "merge-base", f"origin/{child}", f"origin/{parent}")

    def reject_pushes_to(self, branch: str | None) -> None:
        hook = self.origin / "hooks" / "pre-receive"
        if branch is None:
            hook.unlink(missing_ok=True)
            return
        hook.write_text(
            "#!/bin/sh\nwhile read old new ref; do\n"
            f"  [ \"$ref\" = \"refs/heads/{branch}\" ] && {{ echo \"rejected $ref\" >&2; exit 1; }}\n"
            "done\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)

    # ---- fences ----
    def run(self, script: str, env: dict[str, str], outputs: list[str], cwd: Path | None = None) -> dict[str, str]:
        prelude = "".join(f"{k}={v!r}\n" for k, v in env.items())
        prelude += f"LEDGER_DIR={str(self.ledger_dir)!r}\nLEDGER={str(self.ledger)!r}\nTODAY='2026-09-13T00:00:00Z'\n"
        if "LEDGER_JSON" not in env:
            prelude += "LEDGER_JSON=\"$(cat \"$LEDGER\" 2>/dev/null || echo '{}')\"\n"
        epilogue = "\n" + "".join(f'printf "%s\\n" "__OUT__ {k}=${{{k}:-}}"\n' for k in outputs)
        run_env = {
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "HOME": str(self.tmp), "GH_WORLD": str(self.world_path),
            "GIT_AUTHOR_NAME": "land", "GIT_AUTHOR_EMAIL": "l@x", "GIT_COMMITTER_NAME": "land", "GIT_COMMITTER_EMAIL": "l@x",
        }
        res = subprocess.run(["bash", "-c", prelude + script + epilogue], cwd=cwd or self.land,
                             env=run_env, capture_output=True, text=True, timeout=120)
        assert res.returncode == 0, f"fence exited {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        got = {}
        for line in res.stdout.splitlines():
            if line.startswith("__OUT__ "):
                k, _, v = line[8:].partition("=")
                got[k] = v
        got["_stdout"] = res.stdout
        got["_stderr"] = res.stderr
        return got

    def ledger_json(self) -> dict:
        return json.loads(self.ledger.read_text(encoding="utf-8")) if self.ledger.exists() else {}

    def write_ledger(self, data: dict) -> None:
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps(data), encoding="utf-8")


def three_layer_chain(w: ChainWorld) -> None:
    """A (2 commits) on main, B (1 commit) on A, C (1 commit) on B; PRs 1, 2, 3."""
    w.branch("A", "main", [("a1.txt", "a1\n"), ("a2.txt", "a2\n")])
    w.branch("B", "A", [("b.txt", "b\n")])
    w.branch("C", "B", [("c.txt", "c\n")])
    w.add_pr(1, "A", "main")
    w.add_pr(2, "B", "A")
    w.add_pr(3, "C", "B")


@_POSIX
class ShapeFixturesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn149-shape-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ChainWorld(self.tmp)
        three_layer_chain(self.w)
        self.fence = fence(WORKFLOW, "shape")

    def shape(self, pr: int, base: str, branch: str) -> dict[str, str]:
        return self.w.run(self.fence, {"OWNER_REPO": "o/r", "PR_NUMBER": str(pr), "BASE_REF": base, "BRANCH_NAME": branch},
                          ["PR_SHAPE", "PARENT_PR", "PARENT_STATE", "CHAIN_BASE", "CHILD_COUNT", "STACK_NUMBER", "BASE_SHA"])

    def test_standalone_bottom_layer_has_a_child_and_no_parent(self) -> None:
        got = self.shape(1, "main", "A")
        self.assertEqual((got["PR_SHAPE"], got["PARENT_PR"], got["CHAIN_BASE"], got["CHILD_COUNT"]), ("standalone", "", "main", "1"))
        self.assertEqual(got["BASE_SHA"], self.w.origin_sha("main"))

    def test_plain_chain_layer_names_its_parent_and_the_chain_base(self) -> None:
        got = self.shape(3, "B", "C")
        self.assertEqual((got["PR_SHAPE"], got["PARENT_PR"], got["PARENT_STATE"], got["CHAIN_BASE"], got["CHILD_COUNT"]),
                         ("chain", "2", "OPEN", "main", "0"))

    def test_stacked_layer_reads_the_stack_object_and_stores_nothing(self) -> None:
        self.w.world["prs"]["2"]["stack"] = {"number": 11, "position": 2, "size": 3}
        self.w.save()
        got = self.shape(2, "A", "B")
        self.assertEqual((got["PR_SHAPE"], got["STACK_NUMBER"], got["CHILD_COUNT"]), ("stacked", "11", "1"))
        self.assertEqual(self.w.ledger_json(), {})

    def test_closed_parent_is_reported_for_the_chain_broken_rule(self) -> None:
        self.w.world["prs"]["2"]["state"] = "CLOSED"
        self.w.save()
        got = self.shape(3, "B", "C")
        self.assertEqual((got["PR_SHAPE"], got["PARENT_STATE"]), ("chain", "CLOSED"))

    def test_frontier_fence_names_the_lowest_open_layer(self) -> None:
        self.w.world["stacks"]["11"] = {"pull_requests": [{"number": 1, "state": "open"}, {"number": 2, "state": "open"}, {"number": 3, "state": "open"}]}
        self.w.save()
        got = self.w.run(fence(WORKFLOW, "frontier"), {"OWNER_REPO": "o/r", "STACK_NUMBER": "11", "PR_NUMBER": "3"}, ["FRONTIER", "LOWER_COUNT", "STACK_RC"])
        self.assertEqual((got["FRONTIER"], got["LOWER_COUNT"], got["STACK_RC"]), ("1", "2", "0"))
        got = self.w.run(fence(WORKFLOW, "frontier"), {"OWNER_REPO": "o/r", "STACK_NUMBER": "99", "PR_NUMBER": "3"}, ["FRONTIER", "STACK_RC"])
        self.assertEqual((got["FRONTIER"], got["STACK_RC"]), ("", "1"))


@_POSIX
class CascadeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn149-cascade-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ChainWorld(self.tmp)
        three_layer_chain(self.w)
        self.fence = fence(REFERENCE, "cascade")
        self.b_patch = self.w.patch_id("A", "B")
        self.c_patch = self.w.patch_id("B", "C")

    def cascade(self, parent: str, parent_pr: int) -> dict[str, str]:
        return self.w.run(self.fence, {"MERGED_PARENT": parent, "PARENT_PR": str(parent_pr), "CHAIN_BASE": "main", "OWNER_REPO": "o/r"},
                          ["CASCADE_VERDICT", "CASCADE_REASON"])

    def merge_a(self) -> None:
        self.w.squash_merge("A")
        self.w.world["prs"]["1"]["state"] = "MERGED"
        self.w.save()

    def test_a_then_b_squash_merged_keeps_c_boundary_and_diff(self) -> None:
        self.merge_a()
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertNotIn("cascade", self.w.ledger_json())
        self.assertEqual(self.w.boundary("B", "main"), self.w.origin_sha("main"))
        self.assertEqual(self.w.patch_id("main", "B"), self.b_patch)
        self.assertEqual(self.w.boundary("C", "B"), self.w.origin_sha("B"))
        self.assertEqual(self.w.patch_id("B", "C"), self.c_patch)
        self.assertEqual(self.w.reload()["prs"]["2"]["baseRefName"], "main")
        self.assertEqual(self.w.world["prs"]["3"]["baseRefName"], "B")
        self.assertEqual(git(self.w.land, "for-each-ref", "refs/flow-next/cascade/"), "")
        ledger = self.w.ledger_json()
        self.assertEqual(ledger["https://github.com/o/r/pull/2"]["land_pushed_sha"], self.w.origin_sha("B"))
        self.assertEqual(ledger["https://github.com/o/r/pull/3"]["land_pushed_sha"], self.w.origin_sha("C"))
        # merge B, cascade again: C lands on main with its own diff only
        self.w.squash_merge("B")
        self.w.world["prs"]["2"]["state"] = "MERGED"
        self.w.save()
        got = self.cascade("B", 2)
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertEqual(self.w.boundary("C", "main"), self.w.origin_sha("main"))
        self.assertEqual(self.w.patch_id("main", "C"), self.c_patch)
        self.assertEqual(self.w.reload()["prs"]["3"]["baseRefName"], "main")

    def test_conflict_during_prepare_publishes_nothing_and_writes_no_record(self) -> None:
        self.w.branch("B", "A", [("a1.txt", "b-changed\n")])
        self.w.branch("C", "B", [("c.txt", "c\n")])
        self.w.squash_merge("A")
        # main now changes a1.txt differently → B's rebase conflicts
        git(self.w.work, "checkout", "-q", "main")
        self.w.commit(self.w.work, "a1.txt", "main-changed\n", "main edit")
        git(self.w.work, "push", "-q", "origin", "main")
        self.w.world["prs"]["1"]["state"] = "MERGED"
        self.w.save()
        b_before, c_before = self.w.origin_sha("B"), self.w.origin_sha("C")
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "blocked", got)
        self.assertIn("a1.txt", got["CASCADE_REASON"])
        self.assertEqual((self.w.origin_sha("B"), self.w.origin_sha("C")), (b_before, c_before))
        self.assertNotIn("cascade", self.w.ledger_json())
        self.assertEqual(git(self.w.land, "for-each-ref", "refs/flow-next/cascade/"), "")
        self.assertEqual(git(self.w.land, "worktree", "list", "--porcelain").count("worktree "), 1)

    def test_lease_failure_on_c_resumes_from_the_record_without_a_second_rewrite(self) -> None:
        self.merge_a()
        self.w.reject_pushes_to("C")
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertIn("lease on C", got["CASCADE_REASON"])
        record = self.w.ledger_json()["cascade"]
        self.assertEqual([(l["branch"], l["published"]) for l in record["layers"]], [("B", True), ("C", False)])
        self.assertTrue(record["layers"][0]["base_edited"])
        b_after_first = self.w.origin_sha("B")
        self.assertEqual(self.w.reload()["prs"]["2"]["baseRefName"], "main")
        # later invocation: the record completes without manual rebasing
        self.w.reject_pushes_to(None)
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertNotIn("cascade", self.w.ledger_json())
        self.assertEqual(self.w.origin_sha("B"), b_after_first)
        self.assertEqual(self.w.boundary("C", "B"), self.w.origin_sha("B"))
        self.assertEqual(self.w.patch_id("B", "C"), self.c_patch)

    def test_c_moved_between_ticks_is_re_prepared_from_its_current_head(self) -> None:
        self.merge_a()
        self.w.reject_pushes_to("C")
        self.cascade("A", 1)
        self.w.reject_pushes_to(None)
        # someone commits on C's OLD history between ticks
        git(self.w.work, "fetch", "-q", "origin")
        git(self.w.work, "checkout", "-q", "-B", "C", "origin/C")
        self.w.commit(self.w.work, "c2.txt", "c2\n", "C: c2")
        git(self.w.work, "push", "-q", "origin", "C")
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertNotIn("cascade", self.w.ledger_json())
        self.assertEqual(self.w.boundary("C", "B"), self.w.origin_sha("B"))
        git(self.w.land, "fetch", "-q", "origin")
        self.assertIn("c2.txt", git(self.w.land, "diff", "--name-only", "origin/B...origin/C"))
        self.assertIn("c.txt", git(self.w.land, "diff", "--name-only", "origin/B...origin/C"))

    def test_stop_between_push_and_ledger_write_resumes_with_no_second_rewrite(self) -> None:
        self.merge_a()
        self.w.reject_pushes_to("C")
        self.cascade("A", 1)
        self.w.reject_pushes_to(None)
        # the push landed but the ledger write after it was lost: publish C's prepared tip by hand, leave the record saying unpublished
        record = self.w.ledger_json()["cascade"]
        c_new = record["layers"][1]["new_tip"]
        git(self.w.land, "push", "-q", "-f", "origin", f"{c_new}:refs/heads/C")
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertNotIn("cascade", self.w.ledger_json())
        self.assertEqual(self.w.origin_sha("C"), c_new)   # no second rewrite
        self.assertEqual(self.w.boundary("C", "B"), self.w.origin_sha("B"))

    def test_foreign_rewrite_of_a_layer_is_needs_human(self) -> None:
        self.merge_a()
        self.w.reject_pushes_to("C")
        self.cascade("A", 1)
        self.w.reject_pushes_to(None)
        self.w.branch("C", "main", [("z.txt", "z\n")])   # unrelated history under the same name
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "needs_human", got)
        self.assertIn("rewritten by someone else", got["CASCADE_REASON"])
        self.assertIn("cascade", self.w.ledger_json())

    def test_boundary_on_the_chain_base_refuses_before_any_push(self) -> None:
        # B forked from main directly (never contained A): the invariant is broken below
        self.w.branch("B", "main", [("b.txt", "b\n")])
        self.w.branch("C", "B", [("c.txt", "c\n")])
        self.merge_a()
        b_before = self.w.origin_sha("B")
        got = self.cascade("A", 1)
        self.assertEqual(got["CASCADE_VERDICT"], "needs_human", got)
        self.assertIn("does not contain its parent", got["CASCADE_REASON"])
        self.assertEqual(self.w.origin_sha("B"), b_before)
        self.assertNotIn("cascade", self.w.ledger_json())


@_POSIX
class MergeAndJanitorTicksTestCase(unittest.TestCase):
    """merge → janitor keeps → child retarget → janitor deletes, across four separate invocations."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn149-ticks-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ChainWorld(self.tmp)
        three_layer_chain(self.w)
        text = WORKFLOW.read_text(encoding="utf-8")
        m = re.search(r"^(  MERGE_CMD.*?\n  MERGE_ERR=.*?\n)", text, re.MULTILINE | re.DOTALL)
        assert m
        self.merge_fence = m.group(1)

    def merge(self, pr: int, branch: str, child_count: str, shape: str = "standalone") -> dict[str, str]:
        head = self.w.origin_sha(branch)
        return self.w.run(self.merge_fence, {"PR_NUMBER": str(pr), "HEAD_OID": head, "CHILD_COUNT": child_count, "PR_SHAPE": shape}, ["MERGE_RC", "MERGE_ERR"])

    def janitor(self, dry: str = "0") -> dict[str, str]:
        return self.w.run(fence(WORKFLOW, "janitor"), {"LAND_DRY_RUN": dry}, [])

    def test_standalone_with_children_merges_without_delete_and_the_janitor_finishes_it(self) -> None:
        # tick 1: merge the bottom layer without --delete-branch, record the branch
        got = self.merge(1, "A", "1")
        self.assertEqual(got["MERGE_RC"], "0", got)
        merge_call = self.w.calls("pr", "merge")[-1]
        self.assertNotIn("--delete-branch", merge_call)
        self.assertEqual(merge_call[:4], ["pr", "merge", "1", "--squash"])
        self.assertEqual(self.w.origin_sha("A") != "", True)
        self.w.run(fence(WORKFLOW, "pending-delete"), {"CHILD_COUNT": "1", "PR_SHAPE": "standalone", "BRANCH_NAME": "A", "PR_NUMBER": "1"}, [])
        self.assertEqual(self.w.ledger_json()["pending_branch_deletes"]["A"]["pr"], 1)
        # tick 2: the janitor keeps a branch a child still targets (and a dry run deletes nothing)
        self.janitor("1")
        self.assertEqual(self.w.calls("api", "--method", "DELETE"), [])
        got = self.janitor()
        self.assertIn("janitor: A kept (1 open child PR(s))", got["_stdout"])
        self.assertEqual(self.w.calls("api", "--method", "DELETE"), [])
        # tick 3: land retargets the child (the cascade), so nothing targets A any more
        self.w.squash_merge("A")
        got = self.w.run(fence(REFERENCE, "cascade"), {"MERGED_PARENT": "A", "PARENT_PR": "1", "CHAIN_BASE": "main", "OWNER_REPO": "o/r"}, ["CASCADE_VERDICT"])
        self.assertEqual(got["CASCADE_VERDICT"], "resolving", got)
        self.assertEqual(self.w.reload()["prs"]["2"]["baseRefName"], "main")
        self.assertIn("A", self.w.ledger_json()["pending_branch_deletes"])   # the cascade never touches the map
        # tick 4: the janitor deletes A and clears the entry
        got = self.janitor()
        self.assertIn("janitor: deleted A", got["_stdout"])
        self.assertEqual(self.w.origin_sha("A"), "")
        self.assertNotIn("A", self.w.ledger_json().get("pending_branch_deletes", {}))

    def test_standalone_without_children_keeps_todays_flags(self) -> None:
        self.w.world["prs"].pop("2"); self.w.world["prs"].pop("3"); self.w.save()
        got = self.merge(1, "A", "0")
        self.assertEqual(got["MERGE_RC"], "0", got)
        self.assertEqual(self.w.calls("pr", "merge")[-1][:5], ["pr", "merge", "1", "--squash", "--delete-branch"])
        self.assertEqual(self.w.origin_sha("A"), "")

    def test_janitor_403_keeps_and_422_removes(self) -> None:
        self.w.world["prs"]["2"]["baseRefName"] = "main"; self.w.save()
        self.w.write_ledger({"pending_branch_deletes": {"A": {"pr": 1, "merged_at": "x"}}})
        self.w.world["delete_mode"] = "403"; self.w.save()
        got = self.janitor()
        self.assertIn("403", got["_stdout"])
        self.assertIn("A", self.w.ledger_json()["pending_branch_deletes"])
        self.w.world["delete_mode"] = "422"; self.w.save()
        self.janitor()
        self.assertNotIn("A", self.w.ledger_json()["pending_branch_deletes"])
        self.assertNotEqual(self.w.origin_sha("A"), "")   # 422 removed the entry, deleted nothing


@_POSIX
class PatchIdCarryOverTestCase(unittest.TestCase):
    """Consecutive ticks and repeated equivalent rebases with ONE clean-review comment naming the original head."""

    PATTERN = "(Didn'?t find any( major)? issues|No( major)? issues found).*Reviewed commit|\\*\\*Code Review\\*\\*.*\\*\\*Completed\\*\\*"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn149-patchid-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ChainWorld(self.tmp)
        self.w.branch("A", "main", [("a.txt", "a\n")])
        self.w.add_pr(1, "A", "main")
        self.patchid = fence(WORKFLOW, "patchid")
        self.binding = fence(WORKFLOW, "binding")
        self.scan = scan_fence(WORKFLOW)

    def tick(self, satisfied_if_current: bool = True) -> dict[str, str]:
        head = self.w.origin_sha("A")
        env = {"BASE_REF": "main", "BRANCH_NAME": "A", "HEAD_OID": head, "PR_URL": "https://github.com/o/r/pull/1", "BASE_SHA": self.w.origin_sha("main"),
               "LAST_PUSH": "2026-09-13T01:00:00Z", "REVIEW_SIGNAL": "silence", "CLEAN_REVIEW_PATTERN": self.PATTERN, "AUTOMATED_REVIEWERS": "",
               "OWNER_REPO": "o/r", "PR_NUMBER": "1", "REVIEW_EVENT_AT": "", "AUTO_REVIEW_CURRENT": "0", "AUTO_REVIEW_SOURCE": "", "AUTO_REVIEW_EVIDENCE": ""}
        script = self.patchid + "\n" + self.scan + "\nSIGNAL_SATISFIED=$AUTO_REVIEW_CURRENT\n" + self.binding
        return self.w.run(script, env, ["CUR_PATCH_ID", "GATE_HEAD", "VERDICT_CARRIED", "BINDING_STALE", "AUTO_REVIEW_CURRENT", "V_ANCHOR"])

    def rebase_a_onto_new_main(self, file: str) -> None:
        git(self.w.work, "checkout", "-q", "main")
        self.w.commit(self.w.work, file, "x\n", f"main: {file}")
        git(self.w.work, "push", "-q", "origin", "main")
        git(self.w.work, "checkout", "-q", "A")
        git(self.w.work, "rebase", "-q", "main")
        git(self.w.work, "push", "-q", "-f", "origin", "A")

    def test_one_comment_carries_across_equivalent_rebases_and_clears_on_a_real_change(self) -> None:
        h0 = self.w.origin_sha("A")
        self.w.world["comments"]["1"] = [{"user": {"login": "chatgpt-codex-connector[bot]"}, "updated_at": "2026-09-13T01:30:00Z",
                                          "body": f"Didn't find any major issues. Reviewed commit: {h0}"}]
        self.w.save()
        # tick 1: gates satisfied at h0 → binding written
        got = self.tick()
        self.assertEqual((got["VERDICT_CARRIED"], got["GATE_HEAD"], got["AUTO_REVIEW_CURRENT"]), ("0", h0, "1"))
        binding = self.w.ledger_json()["https://github.com/o/r/pull/1"]
        self.assertEqual((binding["verdict_head"], binding["verdict_patch_id"], binding["verdict_window_anchor"]), (h0, got["CUR_PATCH_ID"], "2026-09-13T01:00:00Z"))
        # ticks 2 and 3: two equivalent rebases, same comment, no new review → still satisfied against h0
        for f in ("m1.txt", "m2.txt"):
            self.rebase_a_onto_new_main(f)
            self.assertNotEqual(self.w.origin_sha("A"), h0)
            got = self.tick()
            self.assertEqual((got["VERDICT_CARRIED"], got["GATE_HEAD"], got["AUTO_REVIEW_CURRENT"], got["V_ANCHOR"]), ("1", h0, "1", "2026-09-13T01:00:00Z"))
            self.assertEqual(self.w.ledger_json()["https://github.com/o/r/pull/1"]["verdict_head"], h0)   # an equivalent head move never rewrites the binding
        # a real code change: the binding clears, the old comment no longer satisfies
        git(self.w.work, "checkout", "-q", "A")
        self.w.commit(self.w.work, "a.txt", "a changed\n", "A: change")
        git(self.w.work, "push", "-q", "origin", "A")
        got = self.tick()
        self.assertEqual((got["VERDICT_CARRIED"], got["BINDING_STALE"], got["AUTO_REVIEW_CURRENT"]), ("0", "1", "0"))
        self.assertNotIn("verdict_head", self.w.ledger_json()["https://github.com/o/r/pull/1"])

    def test_unsatisfied_evaluation_writes_no_binding(self) -> None:
        got = self.tick()
        self.assertEqual(got["AUTO_REVIEW_CURRENT"], "0")
        self.assertEqual(self.w.ledger_json(), {})


@_POSIX
class MergeAsyncTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="fn149-async-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = ChainWorld(self.tmp)
        self.w.branch("A", "main", [("a.txt", "a\n")])
        self.w.branch("B", "A", [("b.txt", "b\n")])
        self.w.add_pr(1, "A", "main", stack={"number": 11, "position": 1, "size": 2})
        self.w.add_pr(2, "B", "A", stack={"number": 11, "position": 2, "size": 2})
        self.w.world["stacks"]["11"] = {"pull_requests": [{"number": 1, "state": "open"}, {"number": 2, "state": "open"}]}
        self.w.save()
        self.fence = fence(WORKFLOW, "merge-async")

    def submit(self, pr: int, sha: str) -> dict[str, str]:
        return self.w.run(self.fence, {"OWNER_REPO": "o/r", "STACK_NUMBER": "11", "PR_NUMBER": str(pr), "PR_URL": f"https://github.com/o/r/pull/{pr}", "HEAD_OID": sha},
                          ["MERGE_RC", "MERGE_ERR", "MERGE_ASYNC_VERDICT"])

    def test_stale_pin_is_refused_and_nothing_merges(self) -> None:
        got = self.submit(1, self.w.origin_sha("main"))
        self.assertEqual((got["MERGE_RC"], got["MERGE_ASYNC_VERDICT"]), ("1", "resolving"), got)
        self.assertIn("stale head pin", got["MERGE_ERR"])
        self.assertEqual(self.w.reload()["prs"]["1"]["state"], "OPEN")
        self.assertNotIn("merge_async_uuid", self.w.ledger_json().get("https://github.com/o/r/pull/1", {}))
        submit = [c for c in self.w.world["calls"] if "merge-async" in " ".join(c) and "PUT" in c]
        self.assertEqual(len(submit), 1)
        self.assertIn("merge_action=direct_merge", submit[0])

    def test_correct_pin_submits_polls_and_advances_only_on_merged(self) -> None:
        got = self.submit(1, self.w.origin_sha("A"))
        self.assertEqual((got["MERGE_RC"], got["MERGE_ASYNC_VERDICT"]), ("0", "merged"), got)
        self.assertEqual(self.w.reload()["prs"]["1"]["state"], "MERGED")
        self.assertNotIn("merge_async_uuid", self.w.ledger_json().get("https://github.com/o/r/pull/1", {}))
        self.assertNotEqual(self.w.origin_sha("A"), "")   # native merges leave the branch in place

    def test_second_stack_read_refuses_a_non_frontier_submit(self) -> None:
        got = self.submit(2, self.w.origin_sha("B"))
        self.assertEqual((got["MERGE_RC"], got["MERGE_ASYNC_VERDICT"]), ("1", "resolving"), got)
        self.assertEqual([c for c in self.w.reload()["calls"] if "PUT" in c], [])

    def test_pending_uuid_is_polled_never_resubmitted(self) -> None:
        self.w.write_ledger({"https://github.com/o/r/pull/1": {"merge_async_uuid": "u-1", "merge_async_expected_head": "x"}})
        self.w.world["pending"] = {"u-1": "1"}; self.w.save()
        got = self.submit(1, self.w.origin_sha("A"))
        self.assertEqual((got["MERGE_RC"], got["MERGE_ASYNC_VERDICT"]), ("0", "merged"), got)
        self.assertEqual([c for c in self.w.reload()["calls"] if "PUT" in c], [])


class ChainContractTokensTestCase(unittest.TestCase):
    """Shape tokens pinned on the canonical files and their codex mirror copies."""

    def copies(self, rel: str) -> list[Path]:
        return [LAND / rel, MIRROR_LAND / rel]

    def test_fences_exist_in_both_copies(self) -> None:
        for path in self.copies("workflow.md"):
            for name in ("janitor", "shape", "patchid", "frontier", "merge-async", "pending-delete", "binding"):
                fence(path, name)
        for path in self.copies("references/chains-and-stacks.md"):
            fence(path, "cascade")

    def test_disabled_submission_verdict_and_forbidden_list(self) -> None:
        for path in self.copies("workflow.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("NEEDS_HUMAN: merge-async does not enforce a head pin", text)
            self.assertIn("merge_action=direct_merge", text)
            self.assertNotIn("merge_action=merge_queue", text)
            self.assertIn('MERGE_FLAGS=(--squash --delete-branch); [[ "${CHILD_COUNT:-0}" -gt 0 ]] && MERGE_FLAGS=(--squash)', text)
        for path in self.copies("SKILL.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("references/chains-and-stacks.md", text)

    def test_no_config_key_added(self) -> None:
        for path in self.copies("workflow.md"):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("config get land --json"), 1)
            self.assertNotIn("lcfg stack", text)
            self.assertNotIn("lcfg chain", text)


if __name__ == "__main__":
    unittest.main()
