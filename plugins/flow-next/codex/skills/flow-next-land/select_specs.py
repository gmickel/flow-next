#!/usr/bin/env python3
"""Select landing specs from immutable GitHub pull request objects."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import quote, urlparse


OID_RE = re.compile(r"^[0-9a-fA-F]{40}$")
TREE_MODES = {"040000", "40000"}
BLOB_MODES = {"100644", "100755", "120000"}


class SelectorError(Exception):
    """GitHub returned data that cannot establish the selection."""


class ReferenceMoved(Exception):
    """A pull request or relevant branch changed during selection."""


@dataclass
class Spec:
    path: str
    oid: str
    data: dict
    has_task_blob: bool = False

    @property
    def spec_id(self) -> str:
        return self.path.removeprefix(".flow/specs/").removesuffix(".json")

    @property
    def is_closed(self) -> bool:
        return self.data.get("status") == "done" and (
            isinstance(self.data.get("retired"), dict)
            or self.has_task_blob
        )

    def result(self) -> dict:
        return {"id": self.spec_id, "sha": self.oid, "status": self.data["status"]}


class GitHub:
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.blobs: dict[tuple[str, str], dict] = {}

    def api(self, endpoint: str, *, recursive: bool = False) -> dict:
        args = ["gh", "api", "--hostname", self.hostname, "-X", "GET", endpoint]
        if recursive:
            args.extend(["-f", "recursive=1"])
        try:
            process = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
            raise SelectorError(f"GitHub API request failed for {endpoint}: {exc}") from exc
        if process.returncode:
            detail = process.stderr.strip() or f"gh exited {process.returncode}"
            raise SelectorError(f"GitHub API request failed for {endpoint}: {detail}")
        try:
            payload = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise SelectorError(f"GitHub API returned invalid JSON for {endpoint}") from exc
        if not isinstance(payload, dict):
            raise SelectorError(f"GitHub API returned an invalid object for {endpoint}")
        return payload

    def get_tree(self, repository: str, oid: str, *, recursive: bool = False) -> dict:
        endpoint = f"repos/{repository}/git/trees/{oid}"
        return self.api(endpoint, recursive=recursive)

    def get_blob(self, repository: str, oid: str) -> dict:
        key = repository, oid.lower()
        if key not in self.blobs:
            self.blobs[key] = self.api(f"repos/{repository}/git/blobs/{oid}")
        payload = self.blobs[key]
        if require_oid(payload.get("sha"), "blob response") != oid.lower():
            raise SelectorError(f"GitHub returned the wrong blob object for {oid}")
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            raise SelectorError(f"GitHub did not return readable blob content for {oid}")
        try:
            encoded = re.sub(r"\s+", "", payload["content"])
            raw = base64.b64decode(encoded, validate=True)
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SelectorError(f"GitHub returned an unreadable JSON blob for {oid}") from exc
        if not isinstance(data, dict):
            raise SelectorError(f"GitHub returned a non-object spec blob for {oid}")
        return data


def require_oid(value: object, label: str) -> str:
    if not isinstance(value, str) or not OID_RE.fullmatch(value):
        raise SelectorError(f"Missing or invalid full object ID for {label}")
    return value.lower()


def repository_name(value: object, label: str) -> tuple[str, object]:
    if not isinstance(value, dict):
        raise SelectorError(f"GitHub did not identify the {label} repository")
    full_name = value.get("full_name")
    repo_id = value.get("id")
    if (
        not isinstance(full_name, str)
        or full_name.count("/") != 1
        or not all(full_name.split("/"))
        or not isinstance(repo_id, (int, str))
    ):
        raise SelectorError(f"GitHub returned an invalid {label} repository")
    return full_name, repo_id


def ref_endpoint(repository: str, ref: str) -> str:
    encoded_ref = quote(f"heads/{ref}", safe="/")
    return f"repos/{repository}/git/ref/{encoded_ref}"


def branch_oid(gh: GitHub, repository: str, ref: str, label: str) -> str:
    data = gh.api(ref_endpoint(repository, ref))
    target = data.get("object")
    if data.get("ref") != f"refs/heads/{ref}" or not isinstance(target, dict) or target.get("type") != "commit":
        raise SelectorError(f"GitHub did not return the {label} branch commit")
    return require_oid(target.get("sha"), f"{label} branch")


def tree_entries(payload: dict, expected_oid: str, *, recursive: bool) -> list[dict]:
    if require_oid(payload.get("sha"), "tree response") != expected_oid.lower():
        raise SelectorError(f"GitHub returned the wrong tree object for {expected_oid}")
    if payload.get("truncated") is not False:
        raise SelectorError(f"Git tree {expected_oid} is incomplete")
    entries = payload.get("tree")
    if not isinstance(entries, list):
        raise SelectorError(f"GitHub returned an invalid tree for {expected_oid}")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SelectorError(f"GitHub returned an invalid entry in tree {expected_oid}")
        path = entry.get("path")
        kind = entry.get("type")
        mode = entry.get("mode")
        if not isinstance(path, str) or not path or path in seen:
            raise SelectorError(f"GitHub returned an invalid path in tree {expected_oid}")
        if not recursive and "/" in path:
            raise SelectorError(f"GitHub returned a non-immediate path in tree {expected_oid}")
        if not isinstance(kind, str) or kind not in {"blob", "tree", "commit"}:
            raise SelectorError(f"GitHub returned an invalid entry type in tree {expected_oid}")
        if not isinstance(mode, str):
            raise SelectorError(f"GitHub returned an invalid entry mode in tree {expected_oid}")
        entry["sha"] = require_oid(entry.get("sha"), f"tree entry {path}")
        if kind == "tree" and mode not in TREE_MODES:
            raise SelectorError(f"GitHub returned an invalid tree mode for {path}")
        if kind == "blob" and mode not in BLOB_MODES:
            raise SelectorError(f"GitHub returned an invalid blob mode for {path}")
        if kind == "commit" and mode != "160000":
            raise SelectorError(f"GitHub returned an invalid submodule mode for {path}")
        seen.add(path)
    return entries


def tree_map(gh: GitHub, repository: str, commit_oid: str) -> dict[str, dict]:
    """Read the recursive fast path, falling back to only the .flow subtrees."""
    recursive_payload = gh.get_tree(repository, commit_oid, recursive=True)
    if require_oid(recursive_payload.get("sha"), "recursive tree response") != commit_oid.lower():
        raise SelectorError(f"GitHub returned the wrong tree object for {commit_oid}")
    if recursive_payload.get("truncated") is False:
        return {
            entry["path"]: entry
            for entry in tree_entries(recursive_payload, commit_oid, recursive=True)
        }
    if recursive_payload.get("truncated") is not True:
        raise SelectorError(f"GitHub returned an incomplete tree response for {commit_oid}")

    root = tree_entries(gh.get_tree(repository, commit_oid), commit_oid, recursive=False)
    flow_entry = {entry["path"]: entry for entry in root}.get(".flow")
    if flow_entry is None:
        return {}
    if flow_entry["type"] != "tree":
        raise SelectorError("The .flow entry is not a tree")
    flow_oid = require_oid(flow_entry["sha"], ".flow tree")
    flow = tree_entries(gh.get_tree(repository, flow_oid), flow_oid, recursive=False)
    flow_index = {entry["path"]: entry for entry in flow}
    result = {".flow": flow_entry}
    for directory in ("specs", "tasks"):
        directory_entry = flow_index.get(directory)
        if directory_entry is None:
            continue
        if directory_entry["type"] != "tree":
            raise SelectorError(f"The .flow/{directory} entry is not a tree")
        directory_oid = require_oid(directory_entry["sha"], f".flow/{directory} tree")
        children = tree_entries(
            gh.get_tree(repository, directory_oid), directory_oid, recursive=False
        )
        prefix = f".flow/{directory}/"
        result[prefix[:-1]] = directory_entry
        result.update({prefix + entry["path"]: entry for entry in children})
    return result


def relevant_specs(entries: dict[str, dict]) -> dict[str, dict]:
    for path in (".flow", ".flow/specs", ".flow/tasks"):
        if path in entries and entries[path].get("type") != "tree":
            raise SelectorError(f"{path} is not a tree")
    result = {}
    for path, entry in entries.items():
        if not path.startswith(".flow/specs/") or "/" in path.removeprefix(".flow/specs/"):
            continue
        if not path.endswith(".json"):
            continue
        if entry.get("type") != "blob":
            raise SelectorError(f"Spec path {path} is not a blob")
        result[path] = entry
    return result


def relevant_tasks(entries: dict[str, dict]) -> dict[str, dict]:
    result = {}
    for path, entry in entries.items():
        if not path.startswith(".flow/tasks/") or "/" in path.removeprefix(".flow/tasks/"):
            continue
        if entry.get("type") not in {"blob", "tree", "commit"}:
            raise SelectorError(f"Task path {path} has an invalid type")
        result[path] = entry
    return result


def load_specs(gh: GitHub, repository: str, entries: dict[str, dict]) -> dict[str, Spec]:
    result = {}
    for path, entry in relevant_specs(entries).items():
        oid = entry["sha"]
        data = gh.get_blob(repository, oid)
        spec_id = path.removeprefix(".flow/specs/").removesuffix(".json")
        if data.get("id") != spec_id:
            raise SelectorError(f"Spec blob {path} has a missing or mismatched id")
        status = data.get("status")
        if not isinstance(status, str) or status not in {"open", "done"}:
            raise SelectorError(f"Spec blob {path} has a missing or invalid status")
        branch_name = data.get("branch_name")
        if branch_name is not None and not isinstance(branch_name, str):
            raise SelectorError(f"Spec blob {path} has an invalid branch_name")
        result[spec_id] = Spec(path=path, oid=oid, data=data)
    return result


def task_paths_for(spec_id: str, tasks: dict[str, dict]) -> list[str]:
    prefix = f".flow/tasks/{spec_id}."
    return [path for path in tasks if path.startswith(prefix)]


def task_changes(spec_id: str, head_tasks: dict[str, dict], base_tasks: dict[str, dict]) -> bool:
    for path in task_paths_for(spec_id, head_tasks):
        head_oid = head_tasks[path]["sha"]
        base_entry = base_tasks.get(path)
        if base_entry is None or base_entry["sha"] != head_oid:
            return True
    return False


def pull_snapshot(payload: dict, repo: str, number: int) -> tuple[dict, dict]:
    if payload.get("number") != number:
        raise SelectorError("GitHub returned a different pull request")
    base = payload.get("base")
    head = payload.get("head")
    if not isinstance(base, dict) or not isinstance(head, dict):
        raise SelectorError("GitHub returned incomplete pull request refs")
    base_repo, base_id = repository_name(base.get("repo"), "base")
    head_repo, head_id = repository_name(head.get("repo"), "head")
    if base_repo.lower() != repo.lower():
        raise SelectorError("Pull request base repository does not match its URL")
    head_ref, base_ref = head.get("ref"), base.get("ref")
    if not isinstance(head_ref, str) or not head_ref or not isinstance(base_ref, str) or not base_ref:
        raise SelectorError("GitHub returned an invalid pull request branch name")
    head_oid = require_oid(head.get("sha"), "pull request head")
    state = payload.get("state")
    merged_at = payload.get("merged_at")
    if not isinstance(state, str) or state not in {"open", "closed"}:
        raise SelectorError("GitHub returned an invalid pull request state")
    if state == "open" and merged_at is not None:
        raise SelectorError("GitHub returned inconsistent pull request merge state")
    snapshot = {
        "head": {"repo": head_repo, "repo_id": head_id, "ref": head_ref, "sha": head_oid},
        "base": {"repo": base_repo, "repo_id": base_id, "ref": base_ref, "sha": None},
        "state": "merged" if merged_at is not None else state,
    }
    return snapshot, payload


def read_pr(gh: GitHub, repo: str, number: int) -> dict:
    payload = gh.api(f"repos/{repo}/pulls/{number}")
    return pull_snapshot(payload, repo, number)[0]


def select(gh: GitHub, repo: str, number: int, expected_snapshot: dict | None = None) -> dict:
    snapshot = read_pr(gh, repo, number)
    if expected_snapshot is not None:
        if not isinstance(expected_snapshot.get("head"), dict) or not isinstance(
            expected_snapshot.get("base"), dict
        ):
            raise SelectorError("Expected snapshot is missing head or base refs")
        expected_refs = {
            "head": {key: expected_snapshot.get("head", {}).get(key) for key in ("repo", "repo_id", "ref", "sha")},
            "base": {key: expected_snapshot.get("base", {}).get(key) for key in ("repo", "repo_id", "ref")},
            "state": expected_snapshot.get("state"),
        }
        current_refs = {
            "head": snapshot["head"],
            "base": {key: snapshot["base"][key] for key in ("repo", "repo_id", "ref")},
            "state": snapshot["state"],
        }
        if current_refs != expected_refs:
            return {"verdict": "RESOLVING", "reason": "pull request refs changed", "snapshot": snapshot}
        expected_base_oid = expected_snapshot["base"].get("sha")
        if expected_base_oid is not None:
            expected_base_oid = require_oid(expected_base_oid, "expected base snapshot")
            snapshot["base"]["sha"] = branch_oid(
                gh, snapshot["base"]["repo"], snapshot["base"]["ref"], "base"
            )
            if snapshot != expected_snapshot:
                return {"verdict": "RESOLVING", "reason": "pull request or base ref changed", "snapshot": snapshot}
        elif snapshot != expected_snapshot:
            return {"verdict": "RESOLVING", "reason": "pull request refs changed", "snapshot": snapshot}
        return {
            "verdict": "PASS",
            "reason": "pull request snapshot unchanged",
            "snapshot": snapshot,
            "unchanged": True,
        }
    if snapshot["state"] == "closed":
        return {"verdict": "NO_WORK", "reason": "closed unmerged", "snapshot": snapshot}

    head_repo = snapshot["head"]["repo"]
    head_oid = snapshot["head"]["sha"]
    head_entries = tree_map(gh, head_repo, head_oid)
    head_specs = load_specs(gh, head_repo, head_entries)
    head_tasks = relevant_tasks(head_entries)

    branch_matches = sorted(
        spec_id
        for spec_id, spec in head_specs.items()
        if spec.data.get("branch_name") == snapshot["head"]["ref"]
    )
    selected: list[Spec]
    if branch_matches:
        selected = [head_specs[spec_id] for spec_id in branch_matches]
    elif not head_specs:
        selected = []
    else:
        base_repo = snapshot["base"]["repo"]
        base_ref = snapshot["base"]["ref"]
        base_oid = branch_oid(gh, base_repo, base_ref, "base")
        snapshot["base"]["sha"] = base_oid
        base_entries = tree_map(gh, base_repo, base_oid)
        base_specs_index = relevant_specs(base_entries)
        base_tasks = relevant_tasks(base_entries)
        candidates = []
        for spec_id, spec in head_specs.items():
            changed = task_changes(spec_id, head_tasks, base_tasks)
            if spec.data["status"] != "done":
                if changed:
                    candidates.append(spec)
                continue
            retired = isinstance(spec.data.get("retired"), dict)
            if not retired and not changed:
                continue
            base_path = f".flow/specs/{spec_id}.json"
            base_entry = base_specs_index.get(base_path)
            if base_entry is None:
                candidates.append(spec)
                continue
            base_oid_for_spec = base_entry["sha"]
            base_data = gh.get_blob(base_repo, base_oid_for_spec)
            base_status = base_data.get("status")
            if base_data.get("id") != spec_id or not isinstance(base_status, str) or base_status not in {"open", "done"}:
                raise SelectorError(f"Base spec blob {base_path} is missing valid status data")
            if base_status != "done":
                candidates.append(spec)
        selected = candidates

    for spec in selected:
        spec.has_task_blob = any(
            path.endswith(".json") and entry["type"] == "blob"
            for path, entry in head_tasks.items()
            if path.startswith(f".flow/tasks/{spec.spec_id}.")
        )
    open_specs = [spec for spec in selected if not spec.is_closed]

    final_snapshot = read_pr(gh, repo, number)
    if not branch_matches and head_specs:
        final_snapshot["base"]["sha"] = branch_oid(
            gh, final_snapshot["base"]["repo"], final_snapshot["base"]["ref"], "base"
        )
    if final_snapshot != snapshot:
        raise ReferenceMoved("pull request or a relevant branch moved during spec selection")
    selected_records = [spec.result() for spec in sorted(selected, key=lambda item: item.spec_id)]
    open_ids = sorted(spec.spec_id for spec in open_specs)
    return {
        "verdict": "BLOCKED" if open_ids else "PASS",
        "reason": "work not finished" if open_ids else "spec selection complete",
        "snapshot": snapshot,
        "selected": selected_records,
        "open_spec_ids": open_ids,
    }


def parse_url(value: str) -> tuple[str, str, int]:
    parsed = urlparse(value)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or len(parts) != 4 or parts[2] != "pull":
        raise SelectorError("Expected a GitHub pull request URL")
    if not parts[3].isdigit():
        raise SelectorError("Pull request URL has an invalid number")
    return parsed.hostname, f"{parts[0]}/{parts[1]}", int(parts[3])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="the exact named pull request URL")
    parser.add_argument("--expected-snapshot", help="snapshot JSON from an earlier selector run")
    args = parser.parse_args(argv)
    try:
        hostname, repo, number = parse_url(args.url)
        expected = None
        if args.expected_snapshot:
            expected = json.loads(args.expected_snapshot)
            if not isinstance(expected, dict):
                raise SelectorError("Expected snapshot must be a JSON object")
        result = select(GitHub(hostname), repo, number, expected_snapshot=expected)
    except ReferenceMoved as exc:
        result = {"verdict": "RESOLVING", "reason": str(exc)}
    except (SelectorError, json.JSONDecodeError) as exc:
        result = {"verdict": "NEEDS_HUMAN", "reason": str(exc)}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result.get("verdict") in {"PASS", "BLOCKED", "NO_WORK", "RESOLVING"} else 1


if __name__ == "__main__":
    sys.exit(main())
