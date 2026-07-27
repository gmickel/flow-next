"""Per-provider blocked-by projection (fn-140.4).

GitHub body-block writing is deferred to task .5 (sync-body). This module
implements the native sub_issues call + structured degraded hierarchy
reporting only - never presents sub_issues as blocked-by.

Direction (fn-64): A is-blocked-by B ⇔ from=A to=B type=blocks.
"""

from __future__ import annotations

from typing import Optional, Union
from urllib.parse import quote

from ..types import ErrorClass, TrackerError
from ..wire import (
    Execute,
    Result,
    _cli,
    _destination,
    _github_number,
    _gitlab_iid,
    _gl_project,
    _gql,
    _gh_repo,
    _jira,
    _jira_base,
)

# ---------------------------------------------------------------------------
# Linear
# ---------------------------------------------------------------------------

def _linear_edge_exists(execute: Execute, from_id: str, to_id: str
                        ) -> Union[bool, TrackerError]:
    """Canonicalize relations + inverseRelations (fn-64 read-before-write)."""
    data = _gql(
        execute, "relate-list",
        "query($id: String!) { issue(id: $id) { id "
        "relations(first: 50) { nodes { type relatedIssue { id } } } "
        "inverseRelations(first: 50) { nodes { type issue { id } } } } }",
        {"id": from_id}, idempotent=True,
    )
    if isinstance(data, TrackerError):
        return data
    issue = data.get("issue")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear relate list malformed",
                            subtype="malformed_body")
    # relations: this blocks relatedIssue → from=related, to=this
    # inverseRelations: node.issue blocks this → from=this, to=node.issue
    for n in ((issue.get("relations") or {}).get("nodes") or []):
        if not isinstance(n, dict) or n.get("type") != "blocks":
            continue
        related = n.get("relatedIssue") if isinstance(n.get("relatedIssue"), dict) else {}
        if related.get("id") == from_id and issue.get("id") == to_id:
            return True
    for n in ((issue.get("inverseRelations") or {}).get("nodes") or []):
        if not isinstance(n, dict) or n.get("type") != "blocks":
            continue
        blocker = n.get("issue") if isinstance(n.get("issue"), dict) else {}
        if issue.get("id") == from_id and blocker.get("id") == to_id:
            return True
    return False


def linear_set(config: dict, execute: Execute, *, from_id: str, to_id: str,
               from_display: str, to_display: str) -> Result:
    exists = _linear_edge_exists(execute, from_id, to_id)
    if isinstance(exists, TrackerError):
        return exists
    if exists:
        return {"projected": False, "already": True, "form": "blocks"}
    data = _gql(
        execute, "relate-create",
        "mutation($issueId: String!, $relatedIssueId: String!) { "
        "issueRelationCreate(input: {issueId: $issueId, "
        "relatedIssueId: $relatedIssueId, type: blocks}) { "
        "success issueRelation { id } } }",
        # issueId=BLOCKER (to), relatedIssueId=BLOCKED (from)
        {"issueId": to_id, "relatedIssueId": from_id},
    )
    if isinstance(data, TrackerError):
        return data
    mut = data.get("issueRelationCreate")
    if not isinstance(mut, dict) or mut.get("success") is not True:
        return TrackerError(ErrorClass.TRANSPORT, "linear issueRelationCreate failed",
                            subtype="mutation_failed")
    return {"projected": True, "already": False, "form": "blocks"}


# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------

def _jira_edge_exists(config: dict, execute: Execute, *, from_id: str,
                      to_id: str) -> Union[bool, TrackerError]:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    data = _jira(
        execute, "relate-list", "GET",
        f"{base}/rest/api/2/issue/{quote(str(from_id), safe='')}"
        f"?fields=issuelinks",
        idempotent=True,
    )
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "jira relate list malformed",
                            subtype="malformed_body")
    fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    for link in fields.get("issuelinks") or []:
        if not isinstance(link, dict):
            continue
        typ = link.get("type") if isinstance(link.get("type"), dict) else {}
        if str(typ.get("name") or "").lower() != "blocks":
            continue
        # A is blocked by B: link carries outwardIssue=B (B blocks A).
        outward = link.get("outwardIssue") if isinstance(link.get("outwardIssue"), dict) else {}
        inward = link.get("inwardIssue") if isinstance(link.get("inwardIssue"), dict) else {}
        if outward.get("id") is not None and str(outward.get("id")) == str(to_id):
            return True
        if (inward.get("id") is not None and str(inward.get("id")) == str(from_id)
                and outward.get("id") is not None and str(outward.get("id")) == str(to_id)):
            return True
    return False


def jira_set(config: dict, execute: Execute, *, from_id: str, to_id: str,
             from_display: str, to_display: str) -> Result:
    exists = _jira_edge_exists(config, execute, from_id=from_id, to_id=to_id)
    if isinstance(exists, TrackerError):
        return exists
    if exists:
        return {"projected": False, "already": True, "form": "blocks"}
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    # outwardIssue=B (blocks), inwardIssue=A (is blocked by)
    data = _jira(
        execute, "relate-create", "POST",
        f"{base}/rest/api/2/issueLink",
        body={"type": {"name": "Blocks"},
              "inwardIssue": {"id": str(from_id)},
              "outwardIssue": {"id": str(to_id)}},
    )
    if isinstance(data, TrackerError):
        return data
    return {"projected": True, "already": False, "form": "blocks"}


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

def _gitlab_links(config: dict, execute: Execute, *, iid: int
                  ) -> Union[list, TrackerError]:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    data = _cli(execute, "gitlab", config, "relate-list", "GET",
                f"projects/{pid}/issues/{iid}/links", idempotent=True)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, list):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab links is not a list",
                            subtype="malformed_body")
    return data


def _gitlab_pair_present(links: list, *, target_iid: int,
                         link_types: set) -> bool:
    for link in links:
        if not isinstance(link, dict):
            continue
        if link.get("iid") == target_iid and link.get("link_type") in link_types:
            return True
    return False


def gitlab_set(config: dict, execute: Execute, *, from_id: str, to_id: str,
               from_display: str, to_display: str, blocked_by: bool,
               plan: Optional[str]) -> Result:
    from_iid = _gitlab_iid(from_display)
    to_iid = _gitlab_iid(to_display)
    if isinstance(from_iid, TrackerError):
        return from_iid
    if isinstance(to_iid, TrackerError):
        return to_iid
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    links = _gitlab_links(config, execute, iid=from_iid)
    if isinstance(links, TrackerError):
        return links

    degraded = None
    if blocked_by:
        link_type = "is_blocked_by"
        form = "is_blocked_by"
        if _gitlab_pair_present(links, target_iid=to_iid,
                                link_types={"is_blocked_by", "relates_to"}):
            return {"projected": False, "already": True, "form": form}
    else:
        link_type = "relates_to"
        form = "relates_to"
        degraded = {
            "kind": "relates_to",
            "capability": "blockedBy",
            "reason": "blockedBy unavailable on this GitLab tier",
            "plan": plan,
        }
        if _gitlab_pair_present(links, target_iid=to_iid,
                                link_types={"is_blocked_by", "relates_to"}):
            return {"projected": False, "already": True, "form": form,
                    "degraded": degraded}

    target_project = dest.get("projectId")
    body = {
        "target_project_id": target_project,
        "target_issue_iid": to_iid,
        "link_type": link_type,
    }
    data = _cli(execute, "gitlab", config, "relate-create", "POST",
                f"projects/{pid}/issues/{from_iid}/links", body=body)
    if isinstance(data, TrackerError):
        return data
    out = {"projected": True, "already": False, "form": form}
    if degraded:
        out["degraded"] = degraded
    return out


# ---------------------------------------------------------------------------
# GitHub - sub_issues hierarchy ONLY (never blocked-by)
# ---------------------------------------------------------------------------

def github_set(config: dict, execute: Execute, *, from_id: str, to_id: str,
               from_display: str, to_display: str) -> Result:
    """Degraded hierarchy: B (blocker) is parent, A (blocked) is sub-issue.

    Body-block (<!-- flow:deps -->) writing is owned by task .5 - not here.
    """
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    parent_num = _github_number(to_display)  # blocker = parent
    child_num = _github_number(from_display)
    if isinstance(parent_num, TrackerError):
        return parent_num
    if isinstance(child_num, TrackerError):
        return child_num

    # Need child's numeric DB id (not node_id, not number).
    child = _cli(execute, "github", config, "relate-child-read", "GET",
                 f"repos/{repo}/issues/{child_num}", idempotent=True)
    if isinstance(child, TrackerError):
        return child
    if not isinstance(child, dict) or not isinstance(child.get("id"), int):
        return TrackerError(ErrorClass.TRANSPORT,
                            "github child issue carries no numeric id",
                            subtype="malformed_body")
    child_db_id = child["id"]

    # Read-before-write: list existing sub-issues of the parent.
    existing = _cli(execute, "github", config, "relate-list", "GET",
                    f"repos/{repo}/issues/{parent_num}/sub_issues",
                    idempotent=True)
    if isinstance(existing, TrackerError):
        return existing
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and item.get("id") == child_db_id:
                return {
                    "projected": False, "already": True,
                    "form": "sub_issues",
                    "degraded": {
                        "kind": "hierarchy",
                        "form": "sub_issues",
                        "note": "GitHub sub_issues is hierarchy, never blocked-by",
                    },
                }

    data = _cli(execute, "github", config, "relate-create", "POST",
                f"repos/{repo}/issues/{parent_num}/sub_issues",
                body={"sub_issue_id": child_db_id})
    if isinstance(data, TrackerError):
        return data
    return {
        "projected": True, "already": False, "form": "sub_issues",
        "degraded": {
            "kind": "hierarchy",
            "form": "sub_issues",
            "note": "GitHub sub_issues is hierarchy, never blocked-by",
        },
    }


PROVIDERS = {
    "linear": linear_set,
    "jira": jira_set,
    "gitlab": gitlab_set,
    "github": github_set,
}
