"""Forge origin classification and PR/MR adapters (GitHub, GitLab, Bitbucket)."""

from __future__ import annotations

import functools
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, NamedTuple, Optional


def get_repo_root() -> Path:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return Path(res.stdout.strip())
    except (subprocess.CalledProcessError, OSError):
        return Path.cwd()

# gh's own answers when no remote is a GitHub host it knows (GitLab, a local
# repo): no PR can exist there, so a PR probe saw none rather than failing (#583).
_GH_NO_PR_FORGE_MARKERS = ("point to a known GitHub host", "no git remotes found")


def _gh_no_pr_forge(stderr: Optional[str]) -> bool:
    return any(marker in (stderr or "") for marker in _GH_NO_PR_FORGE_MARKERS)


def _gh_pr_rows(head: str, repo: Path) -> tuple[Optional[list], str]:
    """All PRs with head branch `head`, or (None, reason) when the forge cannot be read."""
    try:
        proc = subprocess.run(
            ["gh", "pr", "list", "--head", head, "--state", "all", "--limit", "50",
             "--json", "number,url,state,mergedAt,mergedBy,reviews"],
            cwd=repo, capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"forge unreachable: {exc}"
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or [f"gh exit {proc.returncode}"])[0]
        return None, f"forge unreachable: {detail}"
    try:
        rows = json.loads(proc.stdout)
    except ValueError:
        return None, "forge unreachable: unreadable gh output"
    if not isinstance(rows, list) or not all(
        isinstance(row, dict) and row.get("state") in {"OPEN", "MERGED", "CLOSED"}
        and isinstance(row.get("number"), int) for row in rows
    ):
        return None, "forge unreachable: unexpected gh output"
    return rows, ""


# --- Forge adapters: which code host the origin remote is, and its PR/MR reads. ---
# A listing answers in gh's row keys (number, url, state OPEN/MERGED/CLOSED,
# headRefName, headRefOid, mergedAt), or None when the read failed: None is never
# "no PR". A listing of `limit` rows or more may be truncated; callers reject it.
_FORGE_PROBE_TIMEOUT_S = 10


def _github_owns_host(host: str) -> Optional[bool]:
    try:
        # The token goes to /dev/null: only the exit code says whether gh knows the host.
        proc = subprocess.run(["gh", "auth", "token", "--hostname", host], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return False
    return proc.returncode == 0


def _github_list_prs(repo: Path, origin: "ForgeOrigin", head: Optional[str], *,
                     state: str, limit: int) -> Optional[list]:
    selector = ["--head", head] if head else []
    try:
        probe = subprocess.run(
            ["gh", "pr", "list", *selector, "--state", state, "--limit", str(limit), "--json",
             "number,url,state,headRefName,headRefOid,mergedAt"],
            cwd=repo, capture_output=True, text=True, timeout=_FORGE_PROBE_TIMEOUT_S, check=False)
        if probe.returncode != 0 and _gh_no_pr_forge(probe.stderr):
            return []
        return json.loads(probe.stdout) if probe.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _gitlab_owns_host(host: str) -> Optional[bool]:
    try:
        proc = subprocess.run(["glab", "auth", "status", "--hostname", host], stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True, timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return False
    if proc.returncode == 0:
        return True
    # Only glab's logged-out answer is a no; a failed API call (offline host) is unknown.
    return False if "has not been authenticated" in " ".join((proc.stderr or "").split()) else None


# GitLab caps a page at 100. A locked MR is mid-merge and still open.
_GITLAB_PER_PAGE = 100
_GITLAB_MR_STATES = {"opened": "OPEN", "locked": "OPEN", "merged": "MERGED", "closed": "CLOSED"}


def _gitlab_mr_row(mr: Any) -> Optional[dict]:
    if not (isinstance(mr, dict) and isinstance(mr.get("state"), str) and mr["state"] in _GITLAB_MR_STATES
            and "sha" in mr and "merged_at" in mr and isinstance(mr.get("iid"), int)
            and isinstance(mr.get("web_url"), str) and mr["web_url"]
            and isinstance(mr.get("source_branch"), str) and mr["source_branch"]
            and isinstance(mr.get("source_project_id"), int) and isinstance(mr.get("project_id"), int)
            and all(isinstance(mr.get(key), (str, type(None))) for key in ("sha", "merged_at"))):
        return None
    return {"number": mr["iid"], "url": mr["web_url"], "state": _GITLAB_MR_STATES[mr["state"]],
            "headRefName": mr["source_branch"], "headRefOid": mr["sha"], "mergedAt": mr["merged_at"],
            "isDraft": mr.get("draft") is True}


def _glab_get(origin: "ForgeOrigin", endpoint: str, deadline: float) -> Optional[Any]:
    """One `glab api` GET on the origin project's host, parsed; None when it failed."""
    try:
        from flowctl_tracker.executor import execute  # noqa: PLC0415
        from flowctl_tracker.types import Request, Response  # noqa: PLC0415
    except ImportError:
        here = Path(__file__).resolve().parent
        if (here / "flowctl_tracker").is_dir():
            sys.path.insert(0, str(here))
        try:
            from flowctl_tracker.executor import execute  # noqa: PLC0415
            from flowctl_tracker.types import Request, Response  # noqa: PLC0415
        except ImportError:
            return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    # GITLAB_HOST may carry host:port, which `glab api --hostname` rejects.
    result = execute(Request(
        provider="gitlab", op="forge-read", method="GET", idempotent=True,
        url_or_argv=["glab", "api", endpoint], timeout_s=remaining,
        env={"GITLAB_HOST": origin.host}), max_retries=0)
    if not isinstance(result, Response):
        return None
    try:
        return json.loads(result.body)
    except ValueError:
        return None


def _gitlab_project(origin: "ForgeOrigin") -> str:
    return f"projects/{urllib.parse.quote(origin.project or '', safe='')}"


def _gitlab_list_prs(repo: Path, origin: "ForgeOrigin", head: Optional[str], *,
                     state: str, limit: int) -> Optional[list]:
    """MRs opened from the origin project itself (a fork's MR may share the branch name)."""
    if not origin.project:
        return None
    endpoint = f"{_gitlab_project(origin)}/merge_requests"
    branch = f"&source_branch={urllib.parse.quote(head, safe='')}" if head else ""
    deadline = time.monotonic() + _FORGE_PROBE_TIMEOUT_S
    rows = []
    for mr_state in ["all"] if state == "all" else ["opened", "locked"]:
        page = 1
        while True:
            listed = _glab_get(origin, f"{endpoint}?state={mr_state}{branch}"
                                       f"&per_page={_GITLAB_PER_PAGE}&page={page}", deadline)
            if not isinstance(listed, list):
                return None
            for mr in listed:
                row = _gitlab_mr_row(mr)
                if row is None:
                    return None
                if mr["source_project_id"] == mr["project_id"]:
                    rows.append(row)
            if len(listed) < _GITLAB_PER_PAGE:
                break
            if len(rows) >= limit:
                return rows
            page += 1
    return rows


# detailed_merge_status values that wait on approvals. GitLab reports one blocking
# check at a time, so any other value but `mergeable` leaves approval unknown.
_GITLAB_APPROVAL_PENDING = {"not_approved", "approvals_syncing", "requested_changes"}


def _gitlab_readiness(repo: Path, origin: "ForgeOrigin", number: int) -> dict:
    """Whether merge request `number` can merge now, in GitLab's own terms.

    `pipeline` is the head pipeline's status for the current head only, and
    `approval` is approved, required or unknown. Anything unreadable is not
    green, not approved and not ready.
    """
    unread = {"head_sha": None, "pipeline": None, "merge_status": None, "approval": "unknown",
              "squash_allowed": None, "green": False, "ready": False}
    if not origin.project:
        return unread
    deadline = time.monotonic() + _FORGE_PROBE_TIMEOUT_S
    mr = _glab_get(origin, f"{_gitlab_project(origin)}/merge_requests/{number}", deadline)
    project = _glab_get(origin, _gitlab_project(origin), deadline)
    if not (isinstance(mr, dict) and isinstance(mr.get("sha"), str) and mr["sha"]
            and isinstance(mr.get("detailed_merge_status"), str)
            and isinstance(mr.get("head_pipeline"), (dict, type(None)))
            and isinstance(project, dict) and isinstance(project.get("squash_option"), str)):
        return unread
    head, status = mr["sha"], mr["detailed_merge_status"]
    # GitLab leaves `head_pipeline` out when the caller cannot see pipelines.
    pipeline = mr.get("head_pipeline") or {}
    # A pipeline for an earlier head says nothing about this one.
    ran = pipeline.get("status") if pipeline.get("sha") == head else None
    if (ran is None and isinstance(pipeline.get("sha"), str)
            and pipeline.get("ref") == f"refs/merge-requests/{number}/merge"):
        # A merged-results pipeline runs on GitLab's merge commit of this head into the target.
        commit = _glab_get(origin, f"{_gitlab_project(origin)}/repository/commits/"
                                   f"{urllib.parse.quote(pipeline['sha'], safe='')}", deadline)
        if (isinstance(commit, dict) and isinstance(commit.get("parent_ids"), list)
                and head in commit["parent_ids"]):
            ran = pipeline.get("status")
    ran = ran if isinstance(ran, str) else None
    approval = ("approved" if status == "mergeable"
                else "required" if status in _GITLAB_APPROVAL_PENDING else "unknown")
    squash = project["squash_option"] != "never"
    return {"head_sha": head, "pipeline": ran, "merge_status": status, "approval": approval,
            "squash_allowed": squash, "green": ran == "success",
            "ready": ran == "success" and status == "mergeable" and squash}


def _gitlab_merge_rows(repo: Path, origin: "ForgeOrigin", branch: str) -> Optional[tuple]:
    """Merge evidence: the branch's merge requests, and each merged one's changed paths
    (old and new, so a move out of a directory counts there too). None when a read failed."""
    rows = _gitlab_list_prs(repo, origin, branch, state="all", limit=100)
    if rows is None or len(rows) >= 100:
        return None
    deadline = time.monotonic() + _FORGE_PROBE_TIMEOUT_S
    files = {}
    for row in rows:
        if row["state"] != "MERGED":
            continue
        paths, page = [], 1
        while True:
            diffs = _glab_get(origin, f"{_gitlab_project(origin)}/merge_requests/{row['number']}/diffs"
                                      f"?per_page={_GITLAB_PER_PAGE}&page={page}", deadline)
            if not isinstance(diffs, list) or not all(
                    isinstance(d, dict) and isinstance(d.get("old_path"), str)
                    and isinstance(d.get("new_path"), str) for d in diffs):
                return None
            paths += [path for d in diffs for path in dict.fromkeys((d["old_path"], d["new_path"]))]
            if len(diffs) < _GITLAB_PER_PAGE:
                break
            page += 1
        files[row["number"]] = paths
    return rows, files


# Bitbucket Cloud answers on one API host whatever the clone host. bkt resolves that host
# only through a context, so each read names a Cloud context rather than the active one.
_BITBUCKET_API = "https://api.bitbucket.org/2.0"
_BITBUCKET_PAGELEN = 50   # Bitbucket's cap for pull request listings
_BITBUCKET_PR_STATES = {"OPEN": "OPEN", "MERGED": "MERGED", "DECLINED": "CLOSED", "SUPERSEDED": "CLOSED"}


def _field(value: Any, *keys: str) -> Any:
    """A nested value of a parsed Bitbucket answer, or None when any level is not an object."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _bkt(argv: list, deadline: float) -> Optional[Any]:
    """One bkt call, its stdout parsed as JSON; None when it failed."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    try:
        proc = subprocess.run(["bkt", *argv], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=remaining, check=False)
        return json.loads(proc.stdout) if proc.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _bkt_context(deadline: float) -> Optional[str]:
    """A bkt context on Bitbucket Cloud, the active one first; None when there is none."""
    listed = _bkt(["context", "list", "--json"], deadline)
    contexts = listed.get("contexts") if isinstance(listed, dict) else None
    cloud = [c["name"] for c in sorted(contexts or [], key=lambda c: c.get("active") is not True)
             if isinstance(c, dict) and isinstance(c.get("name"), str) and c["name"]
             and c.get("host") == urllib.parse.urlsplit(_BITBUCKET_API).hostname]
    return cloud[0] if cloud else None


def _bkt_pages(context: str, endpoint: str, deadline: float) -> Optional[list]:
    """Every value of a paged listing, following `next`; None unless the listing is complete."""
    values: list = []
    while endpoint is not None:
        page = _bkt(["--context", context, "api", endpoint], deadline)
        if not (isinstance(page, dict) and isinstance(page.get("values"), list)):
            return None
        values += page["values"]
        following = page.get("next")
        if following is not None and not (isinstance(following, str) and following.startswith(_BITBUCKET_API + "/")):
            return None
        endpoint = following[len(_BITBUCKET_API):] if following else None
        if endpoint is None and isinstance(page.get("size"), int) and page["size"] != len(values):
            return None   # the listing changed while it was read
    return values


def _bitbucket_pr_row(pr: Any) -> Optional[dict]:
    if not (isinstance(pr, dict) and isinstance(pr.get("id"), int) and pr.get("state") in _BITBUCKET_PR_STATES
            and isinstance(pr.get("draft", False), bool)
            and isinstance(pr.get("links"), dict) and isinstance(pr["links"].get("html"), dict)
            and isinstance(pr["links"]["html"].get("href"), str) and pr["links"]["html"]["href"]
            and isinstance(pr.get("source"), dict) and isinstance(pr["source"].get("branch"), dict)
            and isinstance(pr["source"]["branch"].get("name"), str) and pr["source"]["branch"]["name"]
            and isinstance(pr["source"].get("commit"), dict)
            and re.fullmatch(r"[0-9a-f]{7,40}", str(pr["source"]["commit"].get("hash")))
            # A deleted fork leaves `repository` null; any other unreadable identity is malformed.
            and "repository" in pr["source"] and (pr["source"]["repository"] is None or (
                isinstance(pr["source"]["repository"], dict)
                and isinstance(pr["source"]["repository"].get("full_name"), str)))
            and isinstance(pr.get("destination"), dict) and isinstance(pr["destination"].get("repository"), dict)
            and isinstance(pr["destination"]["repository"].get("full_name"), str)):
        return None
    return {"number": pr["id"], "url": pr["links"]["html"]["href"], "state": _BITBUCKET_PR_STATES[pr["state"]],
            "headRefName": pr["source"]["branch"]["name"], "headRefOid": pr["source"]["commit"]["hash"],
            "mergedAt": None, "isDraft": pr.get("draft") is True}


def _bitbucket_full_shas(repo: Path, context: str, origin: "ForgeOrigin", shorts: set, deadline: float) -> Optional[dict]:
    """Bitbucket's short hashes as full SHAs: the local clone first, then the origin repository."""
    try:
        local = subprocess.run(["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"], cwd=repo,
                               input="".join(f"{short}\n" for short in sorted(shorts)), capture_output=True,
                               text=True, timeout=5, check=False).stdout.splitlines()
    except (OSError, subprocess.TimeoutExpired):
        local = []
    full = {}
    for short, line in zip(sorted(shorts), local, strict=False):   # a failed git answers no lines
        sha, _, kind = line.partition(" ")
        if kind == "commit" and sha.startswith(short):
            full[short] = sha
    for short in sorted(shorts - set(full)):
        commit = _bkt(["--context", context, "api", f"/repositories/{origin.project}/commit/{short}"], deadline)
        sha = commit.get("hash") if isinstance(commit, dict) else None
        if not (isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha) and sha.startswith(short)):
            return None
        full[short] = sha
    return full


def _bitbucket_merged_at(context: str, origin: "ForgeOrigin", number: int, deadline: float) -> Optional[str]:
    """When pull request `number` merged, from its activity: Bitbucket's own reads of a merged
    pull request leave `closed_on` empty, and `updated_on` moves with later activity."""
    activity = _bkt_pages(context, f"/repositories/{origin.project}/pullrequests/{number}/activity"
                                   f"?pagelen={_BITBUCKET_PAGELEN}", deadline)
    for entry in activity or []:
        update = entry.get("update") if isinstance(entry, dict) else None
        if isinstance(update, dict) and update.get("state") == "MERGED" and isinstance(update.get("date"), str):
            return update["date"]
    return None


def _bitbucket_list_prs(repo: Path, origin: "ForgeOrigin", head: Optional[str], *,
                        state: str, limit: int) -> Optional[list]:
    """Pull requests opened from the origin repository itself (a fork's may share the branch name).

    A branch's own pull requests carry their full head SHA and merge time; the open
    listing, which only names branches, carries the short head Bitbucket reports.
    """
    if not (origin.project and re.fullmatch(r"[^/\s?#%]+/[^/\s?#%]+", origin.project)):
        return None
    deadline = time.monotonic() + _FORGE_PROBE_TIMEOUT_S
    context = _bkt_context(deadline)
    if context is None:
        return None
    states = list(_BITBUCKET_PR_STATES) if state == "all" else ["OPEN"]
    query = "".join(f"state={s}&" for s in states)
    if head:
        quoted = head.replace("\\", "\\\\").replace('"', '\\"')   # a branch name may hold a double quote
        query += "q=" + urllib.parse.quote(f'source.branch.name="{quoted}"', safe="") + "&"
    listed = _bkt_pages(context, f"/repositories/{origin.project}/pullrequests?{query}"
                                 f"pagelen={_BITBUCKET_PAGELEN}&page=1", deadline)
    if listed is None:
        return None
    rows = []
    for pr in listed:
        row = _bitbucket_pr_row(pr)
        if row is None:
            return None
        source = (pr["source"].get("repository") or {}).get("full_name")
        # Beside `q`, Bitbucket ignores the `state` parameters and lists every state (measured).
        if (isinstance(source, str) and source.lower() == pr["destination"]["repository"]["full_name"].lower()
                and pr["state"] in states):
            rows.append(row)
    if not head or len(rows) >= limit:
        return rows
    full = _bitbucket_full_shas(repo, context, origin, {row["headRefOid"] for row in rows}, deadline)
    if full is None:
        return None
    for row in rows:
        row["headRefOid"] = full[row["headRefOid"]]
        if row["state"] == "MERGED":
            row["mergedAt"] = _bitbucket_merged_at(context, origin, row["number"], deadline)
            if row["mergedAt"] is None:
                return None
    return rows


# A head's build statuses, worst first; Bitbucket keeps one status per key, the latest.
_BITBUCKET_BUILD_ORDER = ("FAILED", "STOPPED", "INPROGRESS", "SUCCESSFUL")


def _bitbucket_readiness(repo: Path, origin: "ForgeOrigin", number: int) -> dict:
    """Whether pull request `number` can merge now, in Bitbucket's own terms.

    `build` is the worst build status reported on the current head (null when none is),
    `approval` is approved, changes_requested, none or unknown, and `merge_status` is clean
    or the first of Bitbucket's own merge checks that fails. Anything unreadable is not
    green, not approved and not ready; requested changes, a draft or a merge strategy list
    without squash are never ready.
    """
    unread = {"head_sha": None, "build": None, "merge_status": None, "approval": "unknown",
              "squash_allowed": None, "green": False, "ready": False}
    if not (origin.project and re.fullmatch(r"[^/\s?#%]+/[^/\s?#%]+", origin.project)):
        return unread
    deadline = time.monotonic() + _FORGE_PROBE_TIMEOUT_S
    context = _bkt_context(deadline)
    if context is None:
        return unread
    pulls = f"/repositories/{origin.project}/pullrequests/{number}"
    pr = _bkt(["--context", context, "api", f"{pulls}?fields=%2Bdestination.branch.merge_strategies"], deadline)
    strategies = _field(pr, "destination", "branch", "merge_strategies")
    people = _field(pr, "participants")
    if not (_field(pr, "state") == "OPEN" and isinstance(_field(pr, "draft"), bool)
            and isinstance(strategies, list) and all(isinstance(s, str) for s in strategies)
            and isinstance(people, list) and all(isinstance(p, dict) for p in people)
            and re.fullmatch(r"[0-9a-f]{7,40}", str(_field(pr, "source", "commit", "hash")))):
        return unread
    short = pr["source"]["commit"]["hash"]
    full = _bitbucket_full_shas(repo, context, origin, {short}, deadline)
    if full is None:
        return unread
    head = full[short]
    statuses = _bkt_pages(context, f"/repositories/{origin.project}/commit/{head}/statuses?pagelen=100", deadline)
    # A complete listing that holds Bitbucket's git mergeability answer; anything less is unread.
    checks = _bkt_pages(context, f"{pulls}/mergeability/checks", deadline)
    if statuses is None or checks is None or not all(
            _field(s, "commit", "hash") == head and _field(s, "state") in _BITBUCKET_BUILD_ORDER for s in statuses) or not all(
            isinstance(_field(c, "status"), str) and isinstance(_field(c, "blocking"), bool) for c in checks) or not any(
            c["type"] == "git_mergeability_check" for c in checks if isinstance(c.get("type"), str)):
        return {**unread, "head_sha": head}
    build = next((state for state in _BITBUCKET_BUILD_ORDER if any(s["state"] == state for s in statuses)), None)
    failing = next((c for c in checks if c["blocking"] or c["status"] != "PASSED"), None)
    merge_status = "clean" if failing is None else str(failing.get("reason") or failing.get("type") or "blocked")
    if not all("state" in p and p["state"] in {"approved", "changes_requested", None}
               and isinstance(p.get("approved"), bool) for p in people):
        approval = "unknown"
    elif any(p["state"] == "changes_requested" for p in people):
        approval = "changes_requested"
    else:
        approval = "approved" if any(p["approved"] for p in people) else "none"
    squash = "squash" in strategies
    green = build == "SUCCESSFUL"
    return {"head_sha": head, "build": build, "merge_status": merge_status, "approval": approval,
            "squash_allowed": squash, "green": green,
            "ready": green and merge_status == "clean" and squash and not pr["draft"]
                     and approval in {"approved", "none"}}


def _bitbucket_merge_rows(repo: Path, origin: "ForgeOrigin", branch: str) -> Optional[tuple]:
    """Merge evidence: the branch's pull requests, and each merged one's changed paths
    (old and new, so a move out of a directory counts there too). None when a read failed."""
    rows = _bitbucket_list_prs(repo, origin, branch, state="all", limit=100)
    if rows is None or len(rows) >= 100:
        return None
    deadline = time.monotonic() + _FORGE_PROBE_TIMEOUT_S
    context = _bkt_context(deadline)
    files = {}
    for row in rows:
        if row["state"] != "MERGED":
            continue
        diffstat = _bkt_pages(context, f"/repositories/{origin.project}/pullrequests/{row['number']}"
                                       f"/diffstat?pagelen=100", deadline) if context else None
        if diffstat is None:
            return None
        paths = []
        for entry in diffstat:
            # Each side is an object naming a path, or null (added or deleted); anything else is unreadable.
            sides = [_field(entry, side) for side in ("old", "new")]
            named = [_field(side, "path") for side in sides if side is not None]
            if not isinstance(entry, dict) or not all(side is None or isinstance(side, dict) for side in sides) \
                    or not named or not all(isinstance(path, str) and path for path in named):
                return None
            paths += list(dict.fromkeys(named))
        files[row["number"]] = paths
    return rows, files


# Forge name -> its reads. A forge claims an origin host through `owns_host`;
# an adapter may lack a read, and its callers then report that read as
# unsupported on this forge.
FORGE_ADAPTERS: dict[str, dict[str, Any]] = {
    "github": {"owns_host": _github_owns_host, "list_prs": _github_list_prs,
               "approval_rows": _gh_pr_rows},
    "gitlab": {"owns_host": _gitlab_owns_host, "list_prs": _gitlab_list_prs,
               "readiness": _gitlab_readiness, "merge_rows": _gitlab_merge_rows},
    "bitbucket": {"list_prs": _bitbucket_list_prs, "readiness": _bitbucket_readiness,
                  "merge_rows": _bitbucket_merge_rows},
}
_FORGE_HOSTS = {"github.com": "github", "ssh.github.com": "github", "gitlab.com": "gitlab",
                "bitbucket.org": "bitbucket", "ssh.bitbucket.org": "bitbucket", "altssh.bitbucket.org": "bitbucket"}


class ForgeOrigin(NamedTuple):
    forge: Optional[str]    # FORGE_ADAPTERS key, or None when no adapter claims the origin
    host: Optional[str]     # API host; an http(s) port is kept unless glab's login names none
    project: Optional[str]  # owner/repo path on that host


def _ssh_hostname(alias: str) -> str:
    try:
        proc = subprocess.run(["ssh", "-G", alias], stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return alias
    found = re.search(r"^hostname (\S+)$", proc.stdout if proc.returncode == 0 else "", re.M)
    return found.group(1).lower() if found else alias


@functools.lru_cache(maxsize=None)
def repo_forge(repo: str) -> ForgeOrigin:
    """The forge of `repo`'s origin remote; tests reset it with `repo_forge.cache_clear()`."""
    try:
        proc = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo, capture_output=True,
                              text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ForgeOrigin(None, None, None)
    return _origin_forge(proc.stdout.strip() if proc.returncode == 0 else "")


def _origin_forge(url: str) -> ForgeOrigin:
    """The forge, host and project an origin remote URL names."""
    if "://" in url:
        try:
            parsed = urllib.parse.urlsplit(url)
            port = parsed.port
        except ValueError:
            return ForgeOrigin(None, None, None)
        if parsed.scheme not in {"http", "https", "ssh", "git+ssh"} or not parsed.hostname:
            return ForgeOrigin(None, None, None)
        host, path, ssh = parsed.hostname.lower(), parsed.path, parsed.scheme.endswith("ssh")
        if port and not ssh and port != {"http": 80, "https": 443}[parsed.scheme]:
            host = f"{host}:{port}"
    else:
        # scp-like `[user@]host:path`; a Windows drive path is local.
        scp = re.fullmatch(r"(?:[^@/\s]+@)?([A-Za-z0-9._-]{2,}):(.+)", url)
        if not scp:
            return ForgeOrigin(None, None, None)
        host, path, ssh = scp.group(1).lower(), scp.group(2), True
    if ssh and host not in _FORGE_HOSTS:
        host = _ssh_hostname(host)  # an alias may hold characters a hostname may not
    # An SSH origin names no web port; glab's own GITLAB_HOST does when it names the same host.
    gitlab_host = re.sub(r"^https?://", "", os.environ.get("GITLAB_HOST", "").strip().lower()).rstrip("/")
    if ssh and host not in _FORGE_HOSTS and gitlab_host and gitlab_host.split(":")[0] == host:
        host = gitlab_host
    if not re.fullmatch(r"[a-z0-9.-]+(?::\d+)?", host):
        return ForgeOrigin(None, None, None)
    project = path.strip("/").removesuffix(".git") or None
    ci_host = os.environ.get("CI_SERVER_HOST", "").strip().lower()
    forge = _FORGE_HOSTS.get(host) or ("gitlab" if ci_host and host.split(":")[0] == ci_host else None)
    if forge is None:
        names = list(FORGE_ADAPTERS)
        if os.environ.get("GH_ENTERPRISE_TOKEN") or os.environ.get("GITHUB_ENTERPRISE_TOKEN"):
            # gh then claims every host, so every other forge answers first.
            names.sort(key=lambda name: name == "github")
        for name in names:
            owns = FORGE_ADAPTERS[name].get("owns_host")
            claim = owns(host) if owns else False
            if claim is False and name == "gitlab" and ":" in host:
                # glab keys a login made without the web port by the bare hostname.
                claim = owns(host.split(":")[0])
                if claim:
                    host = host.split(":")[0]
            if claim is None:
                break  # An offline or slow answer is unknown, never the next forge's.
            if claim:
                forge = name
                break
    return ForgeOrigin(forge, host, project)


def _forge_read(repo: Path, read: str) -> tuple[Optional[Any], str, ForgeOrigin]:
    """The origin forge's `read`, or None when its adapter lacks it. An origin no
    adapter claims reads through the GitHub adapter, whose no-forge answer is "no PR"."""
    origin = repo_forge(str(repo))
    forge = origin.forge or "github"
    return FORGE_ADAPTERS.get(forge, {}).get(read), forge, origin


def forge_list_prs(repo: Path, head: Optional[str] = None, *, state: str, limit: int) -> Optional[list]:
    """PRs or MRs with head branch `head` (every open one when None); None is a probe failure."""
    read, _, origin = _forge_read(repo, "list_prs")
    return read(repo, origin, head, state=state, limit=limit) if read else None


def forge_readiness(repo: Path, number: int) -> Optional[dict]:
    """Whether open PR/MR `number` can merge now; None when the forge has no such read."""
    read, _, origin = _forge_read(repo, "readiness")
    return read(repo, origin, number) if read else None


def _forge_merge_read(branch: str) -> Any:
    """The tracker's merge-evidence read (flowctl_tracker.status.policy.forge_merge_read).
    NotImplemented on GitHub, which the tracker reads through gh itself."""
    repo = get_repo_root()
    read, forge, origin = _forge_read(repo, "merge_rows")
    if forge == "github":
        return NotImplemented
    return read(repo, origin, branch) if read else None


def forge_approval_rows(head: str, repo: Path) -> tuple[Optional[list], str]:
    read, forge, _ = _forge_read(repo, "approval_rows")
    return read(head, repo) if read else (None, f"spec approval is unsupported on this forge ({forge})")


def _pr_approval(row: dict) -> dict:
    """Approvers and merge identity of one PR row, as the forge reports them."""
    approvers = [
        {"login": (review.get("author") or {}).get("login") or "unknown",
         "approved_at": review.get("submittedAt") or "unknown"}
        for review in row.get("reviews") or []
        if isinstance(review, dict) and review.get("state") == "APPROVED"
    ]
    return {
        "pr": row.get("url"), "number": row["number"], "state": row["state"],
        "approvers": approvers,
        "merged_by": (row.get("mergedBy") or {}).get("login") or "unknown",
        "merged_at": row.get("mergedAt") or "unknown",
    }
