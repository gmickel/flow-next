"""Regression tests for the GitHub-backed land spec selector."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import subprocess
import unittest
from collections import defaultdict, deque
from unittest.mock import patch

from pathlib import Path
import sys

SELECTOR = Path(__file__).resolve().parents[1] / "skills" / "flow-next-land" / "select_specs.py"
sys.path.insert(0, str(SELECTOR.parent))
import select_specs


def oid(letter: str) -> str:
    return letter * 40


def entry(path: str, sha: str, kind: str = "blob") -> dict:
    mode = {"blob": "100644", "tree": "040000", "commit": "160000"}[kind]
    return {"path": path, "mode": mode, "type": kind, "sha": sha}


def tree(sha: str, entries: list[dict], truncated: bool = False) -> dict:
    return {"sha": sha, "truncated": truncated, "tree": entries}


def spec_blob(spec_id: str, status: str, branch: str | None = None, **fields) -> dict:
    return {"id": spec_id, "status": status, "branch_name": branch, **fields}


def pull(head_sha: str, *, head_repo: str = "julie/fork", head_ref: str = "feature", base_sha: str = "e") -> dict:
    return {
        "number": 7,
        "state": "open",
        "merged_at": None,
        "base": {
            "repo": {"full_name": "owner/project", "id": 10},
            "ref": "main",
            "sha": oid(base_sha),
        },
        "head": {
            "repo": {"full_name": head_repo, "id": 20},
            "ref": head_ref,
            "sha": oid(head_sha),
        },
    }


class FakeGitHub:
    """Serve immutable GitHub API objects and record request arguments."""

    def __init__(self):
        self.pulls: deque[dict] = deque()
        self.refs: dict[str, deque[dict]] = defaultdict(deque)
        self.trees: dict[tuple[str, str, bool], deque[dict]] = defaultdict(deque)
        self.blobs: dict[tuple[str, str], dict] = {}
        self.calls: list[list[str]] = []

    def add_tree(self, repo: str, sha: str, payload: dict, *, recursive: bool = False) -> None:
        self.trees[(repo, sha, recursive)].append(payload)

    def add_ref(self, repo: str, ref: str, sha: str) -> None:
        self.refs[f"repos/{repo}/git/ref/heads/{ref}"].append(
            {"ref": f"refs/heads/{ref}", "object": {"type": "commit", "sha": oid(sha)}}
        )

    def add_blob(self, repo: str, sha: str, data: dict) -> None:
        encoded = base64.encodebytes(json.dumps(data).encode("utf-8")).decode("ascii")
        self.blobs[(repo, oid(sha))] = {"sha": oid(sha), "encoding": "base64", "content": encoded}

    def run(self, args, **kwargs):
        self.calls.append(args)
        endpoint = args[args.index("GET") + 1]
        recursive = "recursive=1" in args
        try:
            if endpoint == "repos/owner/project/pulls/7":
                response = self.pulls.popleft()
            elif endpoint.startswith("repos/") and "/git/ref/" in endpoint:
                response = self.refs[endpoint].popleft()
            elif endpoint.startswith("repos/") and "/git/trees/" in endpoint:
                prefix, sha = endpoint.rsplit("/", 1)
                repo = prefix.removeprefix("repos/").removesuffix("/git/trees")
                response = self.trees[(repo, sha, recursive)].popleft()
            elif endpoint.startswith("repos/") and "/git/blobs/" in endpoint:
                prefix, sha = endpoint.rsplit("/", 1)
                repo = prefix.removeprefix("repos/").removesuffix("/git/blobs")
                response = self.blobs[(repo, sha)]
            else:
                return subprocess.CompletedProcess(args, 1, "", f"unexpected endpoint {endpoint}")
        except (KeyError, IndexError):
            return subprocess.CompletedProcess(args, 1, "", f"missing fixture for {endpoint}")
        if not isinstance(response, dict):
            return subprocess.CompletedProcess(args, 1, "", f"missing fixture for {endpoint}")
        return subprocess.CompletedProcess(args, 0, json.dumps(response), "")

    def add_pr_reads(self, *values: dict) -> None:
        self.pulls.extend(values)


def flow_tree_set(
    gh: FakeGitHub,
    repository: str,
    commit: str,
    specs: list[tuple[str, str, dict]],
    tasks: list[tuple[str, str, str]],
    *,
    recursive: dict | None = None,
) -> None:
    """Register recursive and subtree responses for a commit."""
    flow_oid, specs_oid, tasks_oid = oid("1"), oid("2"), oid("3")
    spec_entries = []
    for spec_id, blob_oid, data in specs:
        path = f"{spec_id}.json"
        spec_entries.append(entry(path, oid(blob_oid)))
        gh.add_blob(repository, blob_oid, data)
    task_entries = [
        entry(path.removeprefix(".flow/tasks/"), oid(blob_oid), kind)
        for path, blob_oid, kind in tasks
    ]
    root_entries = [entry(".flow", flow_oid, "tree")]
    flow_entries = [entry("specs", specs_oid, "tree"), entry("tasks", tasks_oid, "tree")]
    if recursive is None:
        full_entries = [
            entry(".flow", flow_oid, "tree"),
            entry(".flow/specs", specs_oid, "tree"),
            entry(".flow/tasks", tasks_oid, "tree"),
            *[dict(item, path=f".flow/specs/{item['path']}") for item in spec_entries],
            *[dict(item, path=f".flow/tasks/{item['path']}") for item in task_entries],
        ]
        recursive = tree(commit, full_entries)
    gh.add_tree(repository, commit, recursive, recursive=True)
    gh.add_tree(repository, commit, tree(commit, root_entries))
    gh.add_tree(repository, flow_oid, tree(flow_oid, flow_entries))
    gh.add_tree(repository, specs_oid, tree(specs_oid, spec_entries))
    gh.add_tree(repository, tasks_oid, tree(tasks_oid, task_entries))


def run_selector(gh: FakeGitHub, expected: dict | None = None) -> dict:
    args = ["--url", "https://github.com/owner/project/pull/7"]
    if expected is not None:
        args.extend(["--expected-snapshot", json.dumps(expected)])
    stdout = io.StringIO()
    with patch.object(select_specs.subprocess, "run", gh.run), contextlib.redirect_stdout(stdout):
        code = select_specs.main(args)
    result = json.loads(stdout.getvalue())
    result["_exit_code"] = code
    return result


class LandGitHubSpecSelectorTest(unittest.TestCase):
    def configure_pull(self, gh: FakeGitHub, head: str = "a") -> None:
        gh.add_pr_reads(pull(head), pull(head))

    def test_truncated_head_omitting_open_task_falls_back_and_blocks(self):
        task_path = ".flow/tasks/fn-12.1.json"
        spec_data = spec_blob("fn-12", "open", "other-branch")

        def configured(recursive: dict) -> FakeGitHub:
            gh = FakeGitHub()
            self.configure_pull(gh)
            flow_tree_set(
                gh,
                "julie/fork",
                oid("a"),
                [("fn-12", "b", spec_data)],
                [(task_path, "c", "blob")],
                recursive=recursive,
            )
            gh.add_ref("owner/project", "main", "d")
            gh.add_ref("owner/project", "main", "d")
            flow_tree_set(gh, "owner/project", oid("d"), [], [])
            return gh

        full_result = run_selector(configured(None))
        truncated_head = tree(oid("a"), [entry(".flow", oid("1"), "tree")], truncated=True)
        fallback_gh = configured(truncated_head)
        fallback_result = run_selector(fallback_gh)
        for result in (full_result, fallback_result):
            self.assertEqual(result["verdict"], "BLOCKED")
            self.assertEqual([record["id"] for record in result["selected"]], ["fn-12"])
            self.assertEqual(result["selected"][0]["sha"], oid("b"))
            self.assertEqual(result["open_spec_ids"], ["fn-12"])
        self.assertEqual(
            [record["id"] for record in full_result["selected"]],
            [record["id"] for record in fallback_result["selected"]],
        )
        nonrecursive_calls = [
            call for call in fallback_gh.calls
            if "/git/trees/" in " ".join(call) and "recursive=1" not in call
        ]
        self.assertTrue(nonrecursive_calls)
        self.assertFalse(any("recursive=false" in call for call in fallback_gh.calls))

        unreadable_gh = configured(truncated_head)
        del unreadable_gh.trees[("julie/fork", oid("3"), False)]
        unreadable_result = run_selector(unreadable_gh)
        self.assertEqual(unreadable_result["verdict"], "NEEDS_HUMAN")
        self.assertNotIn("selected", unreadable_result)

    def test_truncated_base_does_not_turn_omitted_unchanged_task_into_a_change(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"), pull("a"))
        task_path = ".flow/tasks/fn-14.1.json"
        spec = spec_blob("fn-14", "done", "different-branch")
        flow_tree_set(gh, "julie/fork", oid("a"), [("fn-14", "b", spec)], [(task_path, "c", "blob")])
        gh.add_ref("owner/project", "main", "d")
        gh.add_ref("owner/project", "main", "d")
        base_recursive = tree(oid("d"), [entry(".flow", oid("4"), "tree")], truncated=True)
        flow_tree_set(
            gh,
            "owner/project",
            oid("d"),
            [("fn-14", "e", spec_blob("fn-14", "done", "different-branch"))],
            [(task_path, "c", "blob")],
            recursive=base_recursive,
        )
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["snapshot"]["base"]["sha"], oid("d"))

    def test_closed_spec_with_task_is_selected_but_allows_later_gates(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a", head_ref="topic"), pull("a", head_ref="topic"))
        flow_tree_set(
            gh,
            "julie/fork",
            oid("a"),
            [
                ("fn-16", "b", spec_blob("fn-16", "done", "topic")),
                (
                    "fn-16-retired",
                    "f",
                    spec_blob("fn-16-retired", "done", "topic", retired={"reason": "superseded"}),
                ),
            ],
            [(".flow/tasks/fn-16.1.json", "c", "blob")],
            recursive=tree(
                oid("a"),
                [
                    entry(".flow", oid("1"), "tree"),
                    entry(".flow/specs/fn-16.json", oid("b")),
                    entry(".flow/specs/fn-16-retired.json", oid("f")),
                    entry(".flow/tasks/fn-16.1.json", oid("c")),
                ],
            ),
        )
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual([item["id"] for item in result["selected"]], ["fn-16", "fn-16-retired"])
        self.assertEqual(result["selected"][0], {"id": "fn-16", "sha": oid("b"), "status": "done"})

    def test_closed_fallback_uses_changed_task_path_and_base_spec_status(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"), pull("a"))
        task = ".flow/tasks/fn-17.1.json"
        flow_tree_set(
            gh,
            "julie/fork",
            oid("a"),
            [("fn-17", "b", spec_blob("fn-17", "done", "other"))],
            [(task, "c", "blob")],
        )
        gh.add_ref("owner/project", "main", "d")
        gh.add_ref("owner/project", "main", "d")
        flow_tree_set(
            gh,
            "owner/project",
            oid("d"),
            [("fn-17", "e", spec_blob("fn-17", "open", "other"))],
            [(task, "f", "blob")],
        )
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["selected"], [{"id": "fn-17", "sha": oid("b"), "status": "done"}])

    def test_branch_name_selects_every_match_without_reading_base(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a", head_ref="topic"), pull("a", head_ref="topic"))
        flow_tree_set(
            gh,
            "julie/fork",
            oid("a"),
            [
                ("fn-20", "b", spec_blob("fn-20", "open", "topic")),
                ("fn-21", "c", spec_blob("fn-21", "done", "topic")),
            ],
            [(".flow/tasks/fn-21.1.json", "d", "blob")],
        )
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "BLOCKED")
        self.assertEqual([item["id"] for item in result["selected"]], ["fn-20", "fn-21"])
        self.assertFalse(any("repos/owner/project/git/ref/" in call for call in gh.calls))

    def test_established_absence_is_pass_and_does_not_read_a_base(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"), pull("a"))
        gh.add_tree("julie/fork", oid("a"), tree(oid("a"), []), recursive=True)
        gh.add_tree("julie/fork", oid("a"), tree(oid("a"), []))
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["selected"], [])
        self.assertIsNone(result["snapshot"]["base"]["sha"])
        self.assertFalse(any("repos/owner/project/git/ref/" in call for call in gh.calls))

    def test_base_ref_change_during_selection_requests_revalidation(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"), pull("a"))
        flow_tree_set(
            gh,
            "julie/fork",
            oid("a"),
            [("fn-19", "b", spec_blob("fn-19", "done", "other"))],
            [(".flow/tasks/fn-19.1.json", "c", "blob")],
        )
        gh.add_ref("owner/project", "main", "d")
        gh.add_ref("owner/project", "main", "f")
        flow_tree_set(gh, "owner/project", oid("d"), [], [])
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "RESOLVING")

    def test_pr_head_change_during_selection_requests_revalidation(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"), pull("f"))
        flow_tree_set(gh, "julie/fork", oid("a"), [], [])
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "RESOLVING")

    def test_incomplete_required_tree_or_unreadable_spec_is_needs_human(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"))
        gh.add_tree("julie/fork", oid("a"), tree(oid("a"), [], True), recursive=True)
        gh.add_tree("julie/fork", oid("a"), tree(oid("a"), [], True))
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "NEEDS_HUMAN")

        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"), pull("a"))
        flow_tree_set(gh, "julie/fork", oid("a"), [("fn-18", "b", spec_blob("fn-18", "done"))], [])
        del gh.blobs[("julie/fork", oid("b"))]
        result = run_selector(gh)
        self.assertEqual(result["verdict"], "NEEDS_HUMAN")

    def test_expected_snapshot_change_stops_before_reading_trees(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("f"))
        expected = {
            "head": {"repo": "julie/fork", "repo_id": 20, "ref": "feature", "sha": oid("a")},
            "base": {"repo": "owner/project", "repo_id": 10, "ref": "main", "sha": oid("d")},
            "state": "open",
        }
        result = run_selector(gh, expected)
        self.assertEqual(result["verdict"], "RESOLVING")
        self.assertFalse(any("/git/trees/" in " ".join(call) for call in gh.calls))

    def test_expected_snapshot_revalidation_reads_only_pr_and_required_base_ref(self):
        gh = FakeGitHub()
        gh.add_pr_reads(pull("a"))
        gh.add_ref("owner/project", "main", "d")
        expected = {
            "head": {"repo": "julie/fork", "repo_id": 20, "ref": "feature", "sha": oid("a")},
            "base": {"repo": "owner/project", "repo_id": 10, "ref": "main", "sha": oid("d")},
            "state": "open",
        }
        result = run_selector(gh, expected)
        self.assertEqual(result["verdict"], "PASS")
        self.assertTrue(result["unchanged"])
        self.assertEqual(result["snapshot"], expected)
        self.assertEqual(len(gh.calls), 2)
        self.assertFalse(any("/git/trees/" in " ".join(call) for call in gh.calls))
        self.assertFalse(any("/git/blobs/" in " ".join(call) for call in gh.calls))


if __name__ == "__main__":
    unittest.main()
