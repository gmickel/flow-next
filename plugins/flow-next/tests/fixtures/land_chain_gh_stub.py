#!/usr/bin/env python3
"""Stubbed `gh` for the land chain/stack fixtures (fn-149 R16).

Answers the exact gh calls the land fences make from a JSON "world" file
named by GH_WORLD, mutates it where GitHub would (base edits, merges, branch
deletes), and appends every argv to world["calls"]. Branch SHAs are read from
the bare origin at world["origin"], so the stub never invents a head.

The `--jq` flag is delegated to the real `jq` binary (gh's `--jq` output is
raw, like `jq -r`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid


def load() -> dict:
    with open(os.environ["GH_WORLD"], encoding="utf-8") as fh:
        return json.load(fh)


def save(world: dict) -> None:
    tmp = os.environ["GH_WORLD"] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(world, fh)
    os.replace(tmp, os.environ["GH_WORLD"])


def ref_sha(world: dict, branch: str) -> str:
    out = subprocess.run(
        ["git", "--git-dir", world["origin"], "rev-parse", "-q", "--verify", f"refs/heads/{branch}"],
        capture_output=True, text=True,
    )
    return out.stdout.strip()


def delete_ref(world: dict, branch: str) -> None:
    subprocess.run(["git", "--git-dir", world["origin"], "update-ref", "-d", f"refs/heads/{branch}"], check=False)


def emit(payload, jq: str | None) -> None:
    text = json.dumps(payload)
    if jq is None:
        sys.stdout.write(text + "\n")
        return
    out = subprocess.run(["jq", "-r", jq], input=text, capture_output=True, text=True)
    sys.stdout.write(out.stdout)


def pr_view_obj(world: dict, pr: dict) -> dict:
    obj = dict(pr)
    obj["headRefOid"] = ref_sha(world, pr["headRefName"])
    obj.setdefault("mergedAt", None)
    obj.setdefault("reviewDecision", "")
    obj.setdefault("isDraft", False)
    return obj


def opt(argv: list[str], name: str) -> str | None:
    if name in argv:
        return argv[argv.index(name) + 1]
    return None


def main(argv: list[str]) -> int:
    world = load()
    world.setdefault("calls", []).append(argv)
    save(world)
    jq = opt(argv, "--jq")
    prs = world["prs"]

    if argv[:2] == ["repo", "view"]:
        owner, name = world["owner_repo"].split("/")
        emit({"owner": {"login": owner}, "name": name, "defaultBranchRef": {"name": world.get("default_branch", "main")}}, jq)
        return 0

    if argv[:2] == ["pr", "list"]:
        rows = list(prs.values())
        if (base := opt(argv, "--base")) is not None:
            if base in world.get("fail_children_of", []):
                sys.stderr.write("gh: connection reset (HTTP 502)\n")
                return 1
            rows = [p for p in rows if p["baseRefName"] == base]
        if (head := opt(argv, "--head")) is not None:
            if world.get("fail_parent_reads"):
                sys.stderr.write("gh: connection reset (HTTP 502)\n")
                return 1
            rows = [p for p in rows if p["headRefName"] == head]
        state = opt(argv, "--state") or "open"
        if state != "all":
            rows = [p for p in rows if p["state"] == state.upper()]
        emit([pr_view_obj(world, p) for p in rows], jq)
        return 0

    if argv[:2] == ["pr", "view"]:
        pr = prs[argv[2]]
        emit(pr_view_obj(world, pr), jq)
        return 0

    if argv[:2] == ["pr", "edit"]:
        pr = prs[argv[2]]
        if (base := opt(argv, "--base")) is not None:
            pr["baseRefName"] = base
        save(world)
        return 0

    if argv[:2] == ["pr", "merge"]:
        pr = prs[argv[2]]
        pin = opt(argv, "--match-head-commit")
        head = ref_sha(world, pr["headRefName"])
        if pin != head:
            sys.stderr.write(f"X Pull request {argv[2]} head ({head}) does not match expected ({pin})\n")
            return 1
        pr["state"] = "MERGED"
        pr["mergedAt"] = "2026-09-13T00:00:00Z"
        if "--delete-branch" in argv:
            delete_ref(world, pr["headRefName"])
        save(world)
        return 0

    if argv[0] == "api":
        method = opt(argv, "--method") or "GET"
        path = next(a for a in argv[1:] if a.startswith("repos/"))
        parts = path.split("/")
        # repos/o/r/<kind>/...
        kind = parts[3]
        if kind == "pulls" and len(parts) == 5:
            pr = prs[parts[4]]
            payload = {
                "number": pr["number"],
                "state": pr["state"].lower(),
                "stack": pr.get("stack"),
                "base": {"ref": pr["baseRefName"], "sha": ref_sha(world, pr["baseRefName"])},
                "head": {"sha": ref_sha(world, pr["headRefName"])},
            }
            emit(payload, jq)
            return 0
        if kind == "stacks":
            if world.get("stack_read_error"):
                sys.stderr.write(f"gh: server error (HTTP {world['stack_read_error']})\n")
                return 1
            stack = world.get("stacks", {}).get(parts[4])
            if stack is None:
                sys.stderr.write("gh: Not Found (HTTP 404)\n")
                return 1
            emit(stack, jq)
            return 0
        if kind == "pulls" and parts[5] == "merge-async" and method == "PUT":
            pr = prs[parts[4]]
            pin = opt(argv, "-f") and next(a for a in argv if a.startswith("sha="))[4:]
            head = ref_sha(world, pr["headRefName"])
            if pin != head and world.get("pin_enforced", True):
                emit({"status": "failed", "details": {"message": "Pull request head branch was modified."}}, None)
                sys.stderr.write("gh: Unprocessable (HTTP 400)\n")
                return 1
            u = str(uuid.uuid4())
            world.setdefault("pending", {})[u] = parts[4]
            save(world)
            emit({"status": "pending", "details": {"uuid": u, "expected_head_sha": pin}}, None)
            return 0
        if kind == "pulls" and parts[5] == "merge-async" and method == "GET":
            u = parts[6]
            n = world.get("pending", {}).pop(u, None)
            if n is None:
                sys.stderr.write("gh: Not Found (HTTP 404)\n")
                return 1
            pr = prs[n]
            pr["state"] = "MERGED"
            pr["mergedAt"] = "2026-09-13T00:00:00Z"
            save(world)
            emit({"status": "merged", "details": {"sha": ref_sha(world, pr["baseRefName"])}}, None)
            return 0
        if kind == "git" and method == "DELETE":
            branch = "/".join(parts[6:])
            mode = world.get("delete_mode", "ok")
            if mode == "403":
                sys.stderr.write("gh: Resource not accessible by integration (HTTP 403)\n")
                return 1
            if mode == "422":
                sys.stderr.write("gh: Reference does not exist (HTTP 422)\n")
                return 1
            delete_ref(world, branch)
            return 0
        if kind == "issues" and parts[5] == "comments":
            emit(world.get("comments", {}).get(parts[4], []), jq)
            return 0
    sys.stderr.write(f"gh stub: unhandled argv {argv}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
