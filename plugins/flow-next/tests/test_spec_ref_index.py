"""`flowctl specs --refs`: the cross-branch spec index (fn-284).

Disposable git fixtures replay the capture-time experiment: a spec on an
unpushed or pushed branch, edits on two branches, squash merges, a spec
deleted on base, and the R1/R2/R4 error cases.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from flowctl_test_support import FLOWCTL_CMD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec =importlib.util.spec_from_file_location("flowctl", ROOT / "scripts" / "flowctl.py")
flowctl = importlib.util.module_from_spec(_spec)
sys.modules["flowctl"] = flowctl
_spec.loader.exec_module(flowctl)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _init(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(repo, "config", key, value)


def _clone(origin: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(origin), str(dest)], capture_output=True, check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(dest, "config", key, value)
    return dest


def _write_spec(repo: Path, spec_id: str, body: str, *, title: str = "T", sidecar: str | None = None) -> None:
    specs = repo / ".flow" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"{spec_id}.md").write_text(body, encoding="utf-8")
    (specs / f"{spec_id}.json").write_text(
        sidecar if sidecar is not None else json.dumps({"id": spec_id, "title": title, "status": "open"}),
        encoding="utf-8",
    )


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _index(repo: Path, *, fetch: bool = False) -> dict:
    return flowctl.build_spec_ref_index(repo, fetch=fetch)


def _row(index: dict, spec_id: str) -> dict:
    return next(s for s in index["specs"] if s["id"] == spec_id)


BODY = "# Login\n\nline one\nline two\nline three\nline four\nline five\n"


class SpecRefIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = self.tmp / "repo"
        _init(self.repo)
        (self.repo / ".flow").mkdir()
        (self.repo / ".flow" / "keep").write_text("", encoding="utf-8")
        _commit(self.repo, "init")

    def test_branch_only_spec_on_local_branch_is_live(self) -> None:
        _git(self.repo, "switch", "-q", "-c", "feat/login")
        _write_spec(self.repo, "fn-1-login", BODY, title="Login")
        _commit(self.repo, "spec")
        _git(self.repo, "switch", "-q", "main")
        index = _index(self.repo)
        self.assertEqual(index["base"], "refs/heads/main")
        self.assertEqual(index["summary"]["branch_only"], ["fn-1-login"])
        row = _row(index, "fn-1-login")
        self.assertEqual(row["title"], "Login")
        self.assertFalse(row["on_base"])
        self.assertEqual([c["ref"] for c in row["live"]], ["refs/heads/feat/login"])
        self.assertFalse(row["live"][0]["conflict"])

    def test_edits_on_two_branches_are_two_live_versions(self) -> None:
        _write_spec(self.repo, "fn-1-login", BODY)
        _commit(self.repo, "spec on main")
        for branch, old, new in (("feat/a", "line two", "line two A"), ("feat/b", "line four", "line four B")):
            _git(self.repo, "switch", "-q", "-c", branch, "main")
            (self.repo / ".flow/specs/fn-1-login.md").write_text(BODY.replace(old, new), encoding="utf-8")
            _commit(self.repo, f"edit {branch}")
        _git(self.repo, "switch", "-q", "main")
        index = _index(self.repo)
        self.assertEqual(index["summary"]["ahead_of_base"], ["fn-1-login"])
        self.assertEqual(index["summary"]["concurrent_edits"], ["fn-1-login"])
        self.assertEqual(index["summary"]["would_conflict"], [])

    def test_squash_merged_copy_is_stale_and_unmerged_edit_stays_live(self) -> None:
        _write_spec(self.repo, "fn-1-login", BODY)
        _commit(self.repo, "spec on main")
        _git(self.repo, "switch", "-q", "-c", "feat/merged")
        (self.repo / ".flow/specs/fn-1-login.md").write_text(BODY.replace("line one", "line one merged"), encoding="utf-8")
        _commit(self.repo, "merged edit")
        _git(self.repo, "switch", "-q", "-c", "feat/live", "main")
        (self.repo / ".flow/specs/fn-1-login.md").write_text(BODY.replace("line five", "line five live"), encoding="utf-8")
        _commit(self.repo, "live edit")
        _git(self.repo, "switch", "-q", "main")
        _git(self.repo, "merge", "-q", "--squash", "feat/merged")
        _commit(self.repo, "squash feat/merged")
        # Base then edits another region of the spec.
        path = self.repo / ".flow/specs/fn-1-login.md"
        path.write_text(path.read_text(encoding="utf-8").replace("line three", "line three base"), encoding="utf-8")
        _commit(self.repo, "base edit")
        row = _row(_index(self.repo), "fn-1-login")
        self.assertEqual(row["stale_refs"], ["refs/heads/feat/merged"])
        self.assertEqual([(c["ref"], c["conflict"]) for c in row["live"]], [("refs/heads/feat/live", False)])
        # Base now edits the same line the live branch edited: still live, now conflicting.
        path.write_text(path.read_text(encoding="utf-8").replace("line five", "line five base"), encoding="utf-8")
        _commit(self.repo, "base edit same line")
        row = _row(_index(self.repo), "fn-1-login")
        self.assertEqual([(c["ref"], c["conflict"]) for c in row["live"]], [("refs/heads/feat/live", True)])

    def test_untouched_older_copy_is_stale(self) -> None:
        _write_spec(self.repo, "fn-1-login", BODY)
        _commit(self.repo, "spec on main")
        _git(self.repo, "branch", "feat/old")
        (self.repo / ".flow/specs/fn-1-login.md").write_text(BODY + "more\n", encoding="utf-8")
        _commit(self.repo, "base moves on")
        row = _row(_index(self.repo), "fn-1-login")
        self.assertEqual((row["live"], row["stale_refs"]), ([], ["refs/heads/feat/old"]))

    def test_spec_merged_then_deleted_on_base_is_not_branch_only(self) -> None:
        _git(self.repo, "switch", "-q", "-c", "feat/export")
        _write_spec(self.repo, "fn-2-export", BODY)
        _commit(self.repo, "spec")
        _git(self.repo, "switch", "-q", "main")
        _git(self.repo, "merge", "-q", "--squash", "feat/export")
        _commit(self.repo, "squash")
        _git(self.repo, "rm", "-q", ".flow/specs/fn-2-export.md", ".flow/specs/fn-2-export.json")
        _commit(self.repo, "drop spec")
        index = _index(self.repo)
        self.assertEqual(index["summary"]["branch_only"], [])
        self.assertEqual(_row(index, "fn-2-export")["stale_refs"], ["refs/heads/feat/export"])

    def test_task_shaped_stem_and_malformed_sidecar(self) -> None:
        _write_spec(self.repo, "fn-1-login", BODY, sidecar="{not json")
        (self.repo / ".flow/specs/fn-1-login.1.md").write_text("task-shaped\n", encoding="utf-8")
        _commit(self.repo, "spec")
        index = _index(self.repo)
        self.assertEqual([s["id"] for s in index["specs"]], ["fn-1-login"])
        self.assertEqual((_row(index, "fn-1-login")["title"], _row(index, "fn-1-login")["status"]), (None, None))

    def test_unrelated_history_counts_as_live_without_conflict(self) -> None:
        _write_spec(self.repo, "fn-1-login", BODY)
        _commit(self.repo, "spec on main")
        _git(self.repo, "switch", "-q", "--orphan", "island")
        _write_spec(self.repo, "fn-1-login", "# Other\n")
        _commit(self.repo, "orphan copy")
        _git(self.repo, "switch", "-q", "main")
        row = _row(_index(self.repo), "fn-1-login")
        self.assertEqual([(c["ref"], c["conflict"]) for c in row["live"]], [("refs/heads/island", False)])

    def test_pushed_spec_needs_fetch_and_prune_drops_deleted_branch(self) -> None:
        origin = self.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        _git(self.repo, "remote", "add", "origin", str(origin))
        _git(self.repo, "push", "-q", "-u", "origin", "main")
        _git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
        other = _clone(origin, self.tmp / "other")
        _git(self.repo, "switch", "-q", "-c", "feat/login")
        _write_spec(self.repo, "fn-1-login", BODY)
        _commit(self.repo, "spec")
        _git(self.repo, "push", "-q", "origin", "feat/login")
        self.assertEqual(_index(other)["summary"]["branch_only"], [])
        fetched = _index(other, fetch=True)
        self.assertTrue(fetched["fetched"])
        self.assertEqual(fetched["base"], "refs/remotes/origin/main")
        self.assertEqual([c["ref"] for c in _row(fetched, "fn-1-login")["live"]], ["refs/remotes/origin/feat/login"])
        _git(self.repo, "push", "-q", "origin", "--delete", "feat/login")
        self.assertEqual(_index(other, fetch=True)["summary"]["branch_only"], [])


class SpecRefIndexCliTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        _init(self.repo)
        _write_spec(self.repo, "fn-1-login", BODY)
        _commit(self.repo, "spec on main")
        _git(self.repo, "switch", "-q", "-c", "feat/other")
        _write_spec(self.repo, "fn-2-other", BODY)
        _commit(self.repo, "branch spec")
        _git(self.repo, "switch", "-q", "main")

    def _run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [*FLOWCTL_CMD, *args], cwd=cwd or self.repo, capture_output=True, text=True, encoding="utf-8"
        )

    def test_plain_specs_lists_only_the_checkout(self) -> None:
        result = self._run("specs", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(sorted(payload), ["count", "specs", "success"])
        self.assertEqual([s["id"] for s in payload["specs"]], ["fn-1-login"])

    def test_refs_without_fetch_writes_nothing(self) -> None:
        def snapshot() -> tuple:
            refs = _git(self.repo, "for-each-ref", "--format=%(refname) %(objectname)")
            objects = _git(self.repo, "count-objects", "-v")
            files = sorted(str(p.relative_to(self.repo)) for p in (self.repo / ".flow").rglob("*"))
            return refs, objects, files

        before = snapshot()
        first = self._run("specs", "--refs", "--json")
        second = self._run("specs", "--refs", "--json")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(json.loads(first.stdout)["summary"]["branch_only"], ["fn-2-other"])
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(snapshot(), before)

    def test_fetch_failure_still_indexes_local_refs(self) -> None:
        result = self._run("specs", "--refs", "--fetch", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["fetched"])
        self.assertTrue(payload["fetch_error"])
        self.assertEqual(payload["summary"]["branch_only"], ["fn-2-other"])

    def test_no_base_ref_fails_naming_candidates(self) -> None:
        _git(self.repo, "branch", "-q", "-m", "main", "trunk")
        result = self._run("specs", "--refs", "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["success"])
        self.assertIn("origin/main", payload["error"])
        self.assertIn("master", payload["error"])

    def test_fetch_requires_refs(self) -> None:
        result = self._run("specs", "--fetch", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--fetch requires --refs", json.loads(result.stdout)["error"])

    def test_not_a_git_repository(self) -> None:
        plain = Path(self.repo.parent) / "plain"
        (plain / ".flow" / "specs").mkdir(parents=True)
        result = self._run("specs", "--refs", "--json", cwd=plain)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a git repository", json.loads(result.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
