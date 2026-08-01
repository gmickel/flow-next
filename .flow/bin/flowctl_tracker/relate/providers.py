"""Per-provider blocked-by projection (fn-140.4).

GitLab projects both the issue link and flow-owned dependency body block.
GitHub implements the native sub_issues call + structured degraded hierarchy
reporting only - never presents sub_issues as blocked-by.

Direction (fn-64): A is-blocked-by B ⇔ from=A to=B type=blocks.
"""

from __future__ import annotations

import re
from typing import Optional, Union
from urllib.parse import quote

from ..types import ErrorClass, TrackerError
from ..wire import (
    _MAX_PAGES,
    _PAGE_SIZE,
    Execute,
    Result,
    _check_durable,
    _cli,
    _destination,
    _github_number,
    _gitlab_iid,
    _gl_project,
    _gql,
    _gql_connection_drain,
    _gh_repo,
    _rest_drain,
    _jira,
    _jira_base,
)
from .ledger import FLOW_DEPS_CLOSE, FLOW_DEPS_OPEN


# ---------------------------------------------------------------------------
# Linear
# ---------------------------------------------------------------------------

def _linear_edge_exists(execute: Execute, from_id: str, to_id: str
                        ) -> Union[bool, TrackerError]:
    """Canonicalize relations + inverseRelations (fn-64 read-before-write).

    Drains BOTH connections cursor-by-cursor (one query per round trip, each
    connection with its own cursor) up to the shared wire page cap. A probe
    that cannot prove absence must not report absence: hitting the cap with
    pages still remaining returns a TrackerError, never False.
    """
    query = (
        "query($id: String!, $afterRel: String, $afterInv: String) { "
        "issue(id: $id) { id "
        f"relations(first: {_PAGE_SIZE}, after: $afterRel) "
        "{ nodes { type relatedIssue { id } } "
        "pageInfo { hasNextPage endCursor } } "
        f"inverseRelations(first: {_PAGE_SIZE}, after: $afterInv) "
        "{ nodes { type issue { id } } "
        "pageInfo { hasNextPage endCursor } } } }"
    )
    rel_cursor: Optional[str] = None
    inv_cursor: Optional[str] = None
    seen: set = set()
    for _ in range(_MAX_PAGES):
        data = _gql(
            execute, "relate-list", query,
            {"id": from_id, "afterRel": rel_cursor, "afterInv": inv_cursor},
            idempotent=True,
        )
        if isinstance(data, TrackerError):
            return data
        issue = data.get("issue")
        if not isinstance(issue, dict):
            return TrackerError(ErrorClass.TRANSPORT, "linear relate list malformed",
                                subtype="malformed_body")
        rel = issue.get("relations") if isinstance(issue.get("relations"), dict) else {}
        inv = (issue.get("inverseRelations")
               if isinstance(issue.get("inverseRelations"), dict) else {})
        # relations: this blocks relatedIssue → from=related, to=this
        # inverseRelations: node.issue blocks this → from=this, to=node.issue
        for n in (rel.get("nodes") or []):
            if not isinstance(n, dict) or n.get("type") != "blocks":
                continue
            related = n.get("relatedIssue") if isinstance(n.get("relatedIssue"), dict) else {}
            if related.get("id") == from_id and issue.get("id") == to_id:
                return True
        for n in (inv.get("nodes") or []):
            if not isinstance(n, dict) or n.get("type") != "blocks":
                continue
            blocker = n.get("issue") if isinstance(n.get("issue"), dict) else {}
            if issue.get("id") == from_id and blocker.get("id") == to_id:
                return True
        rel_info = rel.get("pageInfo") or {}
        inv_info = inv.get("pageInfo") or {}
        rel_more = bool(rel_info.get("hasNextPage"))
        inv_more = bool(inv_info.get("hasNextPage"))
        if not rel_more and not inv_more:
            return False
        # An exhausted connection keeps its last cursor (yields empty pages).
        next_rel = rel_info.get("endCursor") if rel_more else rel_cursor
        next_inv = inv_info.get("endCursor") if inv_more else inv_cursor
        step = (next_rel, next_inv)
        if (rel_more and not next_rel) or (inv_more and not next_inv) or step in seen:
            return TrackerError(ErrorClass.TRANSPORT,
                                "pagination made no progress",
                                subtype="malformed_body")
        seen.add(step)
        rel_cursor, inv_cursor = next_rel, next_inv
    return TrackerError(
        ErrorClass.TRANSPORT,
        "linear relation pages truncated at drain cap; edge absence unproven",
        subtype="truncated")


def linear_set(config: dict, execute: Execute, *, from_id: str, to_id: str,
               from_display: str, to_display: str) -> Result:
    # Presence classification is relate.__init__'s job (4-way probe) -
    # set() performs the mutation only.
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

def jira_blocks_type(config: dict, execute: Execute) -> Union[str, TrackerError]:
    """Resolve the site's blocking link type once per relate invocation.

    A configured name wins. Otherwise discover a type whose outward phrase
    carries "block" semantics. Cache only on the in-memory config object so the
    probe and mutation use the exact same resolved name without persisting
    runtime state behind the discovery transaction.
    """
    tracker = config.get("tracker") if isinstance(config.get("tracker"), dict) else {}
    per = tracker.get("perTracker") if isinstance(tracker.get("perTracker"), dict) else {}
    configured = per.get("blocksLinkType")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    cached = dest.get("_runtimeBlocksLinkType")
    if isinstance(cached, str) and cached:
        return cached
    if cached is False:
        return TrackerError(
            ErrorClass.CAPABILITY,
            "no Jira blocks link type; set tracker.perTracker.blocksLinkType",
            subtype="blocks_link_type",
        )
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    data = _jira(
        execute, "relate-link-types", "GET",
        f"{base}/rest/api/2/issueLinkType", idempotent=True)
    if isinstance(data, TrackerError):
        return data
    rows = data.get("issueLinkTypes") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "jira issueLinkType response is malformed",
            subtype="malformed_body",
        )
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        outward = row.get("outward")
        if (isinstance(name, str) and name.strip()
                and isinstance(outward, str)
                and "block" in outward.lower()):
            dest["_runtimeBlocksLinkType"] = name.strip()
            return name.strip()
    dest["_runtimeBlocksLinkType"] = False
    return TrackerError(
        ErrorClass.CAPABILITY,
        "no Jira blocks link type; set tracker.perTracker.blocksLinkType",
        subtype="blocks_link_type",
    )


def _jira_edge_exists(config: dict, execute: Execute, *, from_id: str,
                      to_id: str) -> Union[bool, TrackerError]:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    blocks_type = jira_blocks_type(config, execute)
    if isinstance(blocks_type, TrackerError):
        return blocks_type
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
        if str(typ.get("name") or "").casefold() != blocks_type.casefold():
            continue
        # Querying the blocked issue A: "A is blocked by B" carries the
        # blocker B in inwardIssue (jira.md listIssueRelations - the entry
        # holds outwardIssue XOR inwardIssue from A's perspective). An
        # outwardIssue=B entry means "A blocks B" - the REVERSE edge, which
        # must NOT match (mirrors gitlab_probe_pair direction handling).
        inward = link.get("inwardIssue") if isinstance(link.get("inwardIssue"), dict) else {}
        if inward.get("id") is not None and str(inward.get("id")) == str(to_id):
            return True
    return False


def jira_set(config: dict, execute: Execute, *, from_id: str, to_id: str,
             from_display: str, to_display: str) -> Result:
    # Presence classification is relate.__init__'s job (4-way probe) -
    # set() performs the mutation only.
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    blocks_type = jira_blocks_type(config, execute)
    if isinstance(blocks_type, TrackerError):
        return blocks_type
    # Measured live 2026-07-28 (JQL linkedIssues tiebreak): POST
    # {inwardIssue: X, outwardIssue: Y} creates "X blocks Y". For
    # "A blocked-by B" the blocker B goes in inwardIssue and the blocked
    # A in outwardIssue; the readback on A then shows B in inwardIssue,
    # which is exactly what _jira_edge_exists matches.
    data = _jira(
        execute, "relate-create", "POST",
        f"{base}/rest/api/2/issueLink",
        body={"type": {"name": blocks_type},
              "inwardIssue": {"id": str(to_id)},
              "outwardIssue": {"id": str(from_id)}},
    )
    if isinstance(data, TrackerError):
        return data
    return {"projected": True, "already": False, "form": "blocks"}


# ---------------------------------------------------------------------------
# GitLab
# ---------------------------------------------------------------------------

def _gitlab_links(config: dict, execute: Execute, *, iid: int
                  ) -> Union[tuple, TrackerError]:
    """Drain issue links to the shared wire cap. Returns (links, truncated).

    Mirror of the GitHub sub_issues probe drain (fn-64 read-before-write): a
    single-page probe would report a later-page link ABSENT, falsely queueing
    a ledgered edge as a human removal (or duplicating the create on an
    unledgered one). Truncation is unproven absence, never absence.
    """
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    drained = _rest_drain(lambda page: _cli(
        execute, "gitlab", config, "relate-list", "GET",
        f"projects/{pid}/issues/{iid}/links"
        f"?per_page={_PAGE_SIZE}&page={page}", idempotent=True))
    return drained


def _gitlab_pair_present(links: list, *, target_iid: int,
                         link_types: set) -> bool:
    for link in links:
        if not isinstance(link, dict):
            continue
        if link.get("iid") == target_iid and link.get("link_type") in link_types:
            return True
    return False


# GitHub and GitLab relation paths address issues by DISPLAY (issue number /
# IID); Linear and Jira address by durable id and need no guard.
_DISPLAY_ADDRESSED = ("github", "gitlab")


def display_durable_guard(provider: str, config: dict, execute: Execute, *,
                          locators: tuple) -> Optional[TrackerError]:
    """Pre-mutation display -> durable identity check (wire-verb parity).

    GitHub/GitLab probes and setters address issues by display; a destination
    move, repoint, or stale stored identifier would otherwise inspect and then
    relate UNRELATED issues. Mirror the wire write verbs: read each display
    locator and compare the returned durable id against the linked durable id
    (`_check_durable`), aborting as CONFLICT/durable_mismatch on drift. Never
    raises - returns a TrackerError or None.
    """
    if provider not in _DISPLAY_ADDRESSED:
        return None
    from ..wire import github as _wire_github  # noqa: PLC0415
    from ..wire import gitlab as _wire_gitlab  # noqa: PLC0415
    mod = _wire_github if provider == "github" else _wire_gitlab
    for locator in locators:
        got = mod.parent_read(config, locator, execute,
                              op="relate-parent-read")
        if isinstance(got, TrackerError):
            return got
    return None


_FLOW_DEPS_RE = re.compile(
    re.escape(FLOW_DEPS_OPEN) + r".*?" + re.escape(FLOW_DEPS_CLOSE),
    re.DOTALL,
)
_BLOCKED_BY_RE = re.compile(r"(?m)^\*\*Blocked by:\*\*[ \t]*(.*)$")


def _gitlab_deps_body(description: object, blocker_ref: str
                      ) -> Union[str, TrackerError]:
    """Add one exact blocker ref inside flow's fenced dependency block."""
    if description is None:
        text = ""
    elif isinstance(description, str):
        text = description
    else:
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab issue description is not text",
            subtype="malformed_body")
    opens = text.count(FLOW_DEPS_OPEN)
    closes = text.count(FLOW_DEPS_CLOSE)
    if (opens != closes or opens > 1
            or (opens == 1
                and text.find(FLOW_DEPS_OPEN) > text.find(FLOW_DEPS_CLOSE))):
        return TrackerError(
            ErrorClass.CONFLICT,
            "gitlab flow:deps block is malformed; refusing to rewrite issue body",
            subtype="deps_block")
    match = _FLOW_DEPS_RE.search(text)
    if match is None:
        prefix = text.rstrip("\n")
        block = (
            f"{FLOW_DEPS_OPEN}\n"
            f"**Blocked by:** {blocker_ref}\n"
            f"{FLOW_DEPS_CLOSE}"
        )
        return f"{prefix}\n\n{block}" if prefix else block

    region = match.group(0)
    blocked = _BLOCKED_BY_RE.search(region)
    if blocked is not None:
        refs = [ref.strip() for ref in blocked.group(1).split(",") if ref.strip()]
        if blocker_ref in refs:
            return text
        replacement = f"**Blocked by:** {', '.join([*refs, blocker_ref])}"
        updated_region = (
            region[:blocked.start()] + replacement + region[blocked.end():])
    else:
        updated_region = region.replace(
            FLOW_DEPS_CLOSE, f"**Blocked by:** {blocker_ref}\n{FLOW_DEPS_CLOSE}",
            1)
    return text[:match.start()] + updated_region + text[match.end():]


def gitlab_ensure_deps_block(config: dict, execute: Execute, *,
                             from_id: str, from_display: str,
                             to_display: str) -> Result:
    """Idempotently write GitLab's direction/provenance body twin."""
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    iid = _gitlab_iid(from_display)
    if isinstance(pid, TrackerError):
        return pid
    if isinstance(iid, TrackerError):
        return iid
    locator = {"durable": from_id, "display": from_display}
    parent = _cli(
        execute, "gitlab", config, "relate-body-read", "GET",
        f"projects/{pid}/issues/{iid}", idempotent=True)
    if isinstance(parent, TrackerError):
        return parent
    if not isinstance(parent, dict):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab dependency body read returned no object",
            subtype="malformed_body")
    err = _check_durable("gitlab", locator, parent)
    if err:
        return err
    current = parent.get("description")
    body = _gitlab_deps_body(current, to_display)
    if isinstance(body, TrackerError):
        return body
    current = "" if current is None else current
    if body == current:
        return {"written": False, "body": body}
    data = _cli(
        execute, "gitlab", config, "relate-body-write", "PUT",
        f"projects/{pid}/issues/{iid}", body={"description": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab dependency body update returned no object",
            subtype="malformed_body")
    err = _check_durable("gitlab", locator, data)
    if err:
        return err
    if data.get("description") != body:
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab dependency body readback did not match requested body",
            subtype="readback_mismatch")
    return {"written": True, "body": body}


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
    # Presence classification is relate.__init__'s job (4-way probe).
    degraded = None
    if blocked_by:
        link_type = "is_blocked_by"
        form = "is_blocked_by"
    else:
        link_type = "relates_to"
        form = "relates_to"
        degraded = {
            "kind": "relates_to",
            "capability": "blockedBy",
            "reason": "blockedBy unavailable on this GitLab tier",
            "plan": plan,
        }

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
    body_out = gitlab_ensure_deps_block(
        config, execute, from_id=from_id, from_display=from_display,
        to_display=to_display)
    if isinstance(body_out, TrackerError):
        import dataclasses  # noqa: PLC0415
        return dataclasses.replace(body_out, details={
            **(body_out.details or {}),
            "recoverable": True,
            "completed_steps": ["relate-create"],
            "form": form,
        })
    out = {"projected": True, "already": False, "form": form}
    if degraded:
        out["degraded"] = degraded
    return out


# ---------------------------------------------------------------------------
# GitHub - sub_issues hierarchy ONLY (never blocked-by)
# ---------------------------------------------------------------------------

_GITHUB_HIERARCHY_DEGRADED = {
    "kind": "hierarchy",
    "form": "sub_issues",
    "note": "GitHub sub_issues is hierarchy, never blocked-by",
}


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

    # Presence classification is relate.__init__'s job (4-way probe).
    data = _cli(execute, "github", config, "relate-create", "POST",
                f"repos/{repo}/issues/{parent_num}/sub_issues",
                body={"sub_issue_id": child_db_id})
    if isinstance(data, TrackerError):
        return data
    return {
        "projected": True, "already": False, "form": "sub_issues",
        "degraded": dict(_GITHUB_HIERARCHY_DEGRADED),
    }


# ---------------------------------------------------------------------------
# Removal - reconcile stale flow-owned blocking edges (fn-135 chart repoint).
# Absence remotely is convergence, never an error; truncation is unproven
# absence (same read-before-write discipline as the probes above).
# ---------------------------------------------------------------------------

def linear_remove(config: dict, execute: Execute, *, from_id: str,
                  to_id: str) -> Result:
    """Delete the native blocks relation `from is-blocked-by to`."""
    def pluck(data: dict) -> Union[dict, TrackerError]:
        issue = data.get("issue")
        conn = (issue.get("inverseRelations")
                if isinstance(issue, dict) else None)
        if not isinstance(conn, dict):
            return TrackerError(ErrorClass.TRANSPORT,
                                "linear relate list malformed",
                                subtype="malformed_body")
        return conn

    drained = _gql_connection_drain(
        execute, "relate-list",
        "query($id: String!, $after: String) { issue(id: $id) { id "
        f"inverseRelations(first: {_PAGE_SIZE}, after: $after) "
        "{ nodes { id type issue { id } } "
        "pageInfo { hasNextPage endCursor } } } }",
        {"id": from_id}, pluck)
    if isinstance(drained, TrackerError):
        return drained
    nodes, truncated = drained
    rel_id = None
    for n in nodes:
        if n.get("type") != "blocks":
            continue
        blocker = n.get("issue") if isinstance(n.get("issue"), dict) else {}
        if blocker.get("id") == to_id and n.get("id"):
            rel_id = str(n["id"])
            break
    if rel_id is None:
        if truncated:
            return TrackerError(
                ErrorClass.TRANSPORT,
                "linear relation pages truncated at drain cap; edge absence "
                "unproven",
                subtype="truncated")
        return {"removed": False, "already_absent": True, "form": "blocks"}
    data = _gql(
        execute, "relate-delete",
        "mutation($id: String!) { issueRelationDelete(id: $id) { success } }",
        {"id": rel_id})
    if isinstance(data, TrackerError):
        return data
    mut = data.get("issueRelationDelete")
    if not isinstance(mut, dict) or mut.get("success") is not True:
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear issueRelationDelete failed",
                            subtype="mutation_failed")
    return {"removed": True, "form": "blocks"}


def jira_remove(config: dict, execute: Execute, *, from_id: str,
                to_id: str) -> Result:
    """Delete the site's blocks link carrying `from is-blocked-by to`."""
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    blocks_type = jira_blocks_type(config, execute)
    if isinstance(blocks_type, TrackerError):
        return blocks_type
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
    link_id = None
    for link in fields.get("issuelinks") or []:
        if not isinstance(link, dict):
            continue
        typ = link.get("type") if isinstance(link.get("type"), dict) else {}
        if str(typ.get("name") or "").casefold() != blocks_type.casefold():
            continue
        # Same direction rule as _jira_edge_exists: the blocker rides in
        # inwardIssue from the blocked issue's perspective.
        inward = (link.get("inwardIssue")
                  if isinstance(link.get("inwardIssue"), dict) else {})
        if (inward.get("id") is not None and str(inward.get("id")) == str(to_id)
                and link.get("id") is not None):
            link_id = str(link["id"])
            break
    if link_id is None:
        return {"removed": False, "already_absent": True, "form": "blocks"}
    out = _jira(
        execute, "relate-delete", "DELETE",
        f"{base}/rest/api/2/issueLink/{quote(link_id, safe='')}")
    if isinstance(out, TrackerError):
        return out
    return {"removed": True, "form": "blocks"}


def _gitlab_deps_body_remove(description: object, drop_refs: set
                             ) -> Union[str, TrackerError]:
    """Drop stale blocker refs from flow's fenced dependency block."""
    if description is None:
        return ""
    if not isinstance(description, str):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab issue description is not text",
            subtype="malformed_body")
    text = description
    match = _FLOW_DEPS_RE.search(text)
    if match is None:
        return text
    region = match.group(0)
    blocked = _BLOCKED_BY_RE.search(region)
    if blocked is None:
        return text
    refs = [ref.strip() for ref in blocked.group(1).split(",") if ref.strip()]
    kept = [ref for ref in refs if ref not in drop_refs]
    if kept == refs:
        return text
    if kept:
        replacement = f"**Blocked by:** {', '.join(kept)}"
        updated_region = (
            region[:blocked.start()] + replacement + region[blocked.end():])
    else:
        # Drop the whole line (and one trailing newline) - an empty
        # Blocked-by line would read as malformed provenance.
        updated_region = (
            region[:blocked.start()]
            + region[blocked.end():].lstrip("\n"))
    return text[:match.start()] + updated_region + text[match.end():]


def _gitlab_absent_body_reconcile(config: dict, execute: Execute, *, pid,
                                  from_iid: int, to_id: str
                                  ) -> Optional[TrackerError]:
    """Scrub body refs to `to_id` when the native link is already absent.

    An earlier attempt may have landed the native DELETE and then failed the
    flow:deps body-twin write; the retry reaches absence here, so absence
    alone must not report success while the body still claims the removed
    blocker. Each blocked-by ref in flow's owned block resolves through the
    destination project (the only project gitlab_set links against); a ref
    whose issue read proves durable id == to_id is dropped. Returns None when
    the twin no longer references the removed edge, else the retryable error.
    """
    parent = _cli(execute, "gitlab", config, "relate-body-read", "GET",
                  f"projects/{pid}/issues/{from_iid}", idempotent=True)
    if isinstance(parent, TrackerError):
        return parent
    if not isinstance(parent, dict):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab dependency body read returned no object",
            subtype="malformed_body")
    current = parent.get("description")
    if not isinstance(current, str):
        return None
    match = _FLOW_DEPS_RE.search(current)
    if match is None:
        return None
    blocked = _BLOCKED_BY_RE.search(match.group(0))
    if blocked is None:
        return None
    drop_refs = set()
    for ref in [r.strip() for r in blocked.group(1).split(",") if r.strip()]:
        iid = _gitlab_iid(ref)
        if isinstance(iid, TrackerError):
            continue  # not an issue ref the set path writes; leave it
        issue = _cli(execute, "gitlab", config, "relate-body-target-read",
                     "GET", f"projects/{pid}/issues/{iid}", idempotent=True)
        if isinstance(issue, TrackerError):
            if issue.cls is ErrorClass.NOT_FOUND:
                continue  # issue gone; unprovable as to_id, leave the ref
            return issue
        if isinstance(issue, dict) and str(issue.get("id")) == str(to_id):
            drop_refs.add(ref)
    if not drop_refs:
        return None
    body = _gitlab_deps_body_remove(current, drop_refs)
    if isinstance(body, TrackerError):
        return body
    if body != current:
        data = _cli(
            execute, "gitlab", config, "relate-body-write", "PUT",
            f"projects/{pid}/issues/{from_iid}", body={"description": body})
        if isinstance(data, TrackerError):
            return data
    return None


def gitlab_remove(config: dict, execute: Execute, *, from_id: str,
                  from_display: str, to_id: str) -> Result:
    """Delete the native issue link AND the flow:deps body ref twin."""
    from_iid = _gitlab_iid(from_display)
    if isinstance(from_iid, TrackerError):
        return from_iid
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    guard = display_durable_guard(
        "gitlab", config, execute,
        locators=({"durable": from_id, "display": from_display},))
    if guard:
        return guard
    drained = _gitlab_links(config, execute, iid=from_iid)
    if isinstance(drained, TrackerError):
        return drained
    links, truncated = drained
    target = None
    for link in links:
        if not isinstance(link, dict):
            continue
        if (str(link.get("id")) == str(to_id)
                and link.get("link_type") in ("is_blocked_by", "relates_to")
                and link.get("issue_link_id") is not None):
            target = link
            break
    if target is None:
        if truncated:
            return TrackerError(
                ErrorClass.TRANSPORT,
                "gitlab issue link pages truncated at drain cap; edge absence "
                "unproven",
                subtype="truncated")
        # A prior attempt may have deleted the link and failed only the body
        # twin - never report absence as success while the flow:deps block
        # still claims the removed blocker.
        err = _gitlab_absent_body_reconcile(
            config, execute, pid=pid, from_iid=from_iid, to_id=to_id)
        if err is not None:
            return _removal_body_failure(err)
        return {"removed": False, "already_absent": True, "form": "blocks"}
    data = _cli(execute, "gitlab", config, "relate-delete", "DELETE",
                f"projects/{pid}/issues/{from_iid}/links/"
                f"{target['issue_link_id']}")
    if isinstance(data, TrackerError):
        return data
    # Body twin: drop the blocker ref gitlab_set recorded. Candidate refs
    # cover both identifier shapes the set path may have written.
    drop_refs = set()
    refs = target.get("references")
    if isinstance(refs, dict):
        for key in ("full", "relative", "short"):
            if isinstance(refs.get(key), str) and refs[key]:
                drop_refs.add(refs[key])
    if target.get("iid") is not None:
        drop_refs.add(f"#{target['iid']}")
    parent = _cli(
        execute, "gitlab", config, "relate-body-read", "GET",
        f"projects/{pid}/issues/{from_iid}", idempotent=True)
    if isinstance(parent, TrackerError):
        return _removal_body_failure(parent)
    if not isinstance(parent, dict):
        return _removal_body_failure(TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab dependency body read returned no object",
            subtype="malformed_body"))
    current = parent.get("description")
    body = _gitlab_deps_body_remove(current, drop_refs)
    if isinstance(body, TrackerError):
        return _removal_body_failure(body)
    if body != ("" if current is None else current):
        data = _cli(
            execute, "gitlab", config, "relate-body-write", "PUT",
            f"projects/{pid}/issues/{from_iid}", body={"description": body})
        if isinstance(data, TrackerError):
            return _removal_body_failure(data)
    return {"removed": True, "form": "blocks"}


def _removal_body_failure(err: TrackerError) -> TrackerError:
    """Native link removal landed; the deps-body twin update did not."""
    import dataclasses  # noqa: PLC0415
    return dataclasses.replace(err, details={
        **(err.details or {}),
        "recoverable": True,
        "completed_steps": ["relate-delete"],
        "form": "blocks",
    })


PROVIDERS = {
    "linear": linear_set,
    "jira": jira_set,
    "gitlab": gitlab_set,
    "github": github_set,
}

# ---------------------------------------------------------------------------
# Probe-only presence (read, never mutate) - the 4-way ledger x remote
# classification in relate.__init__ needs presence WITHOUT a write attempt.
# ---------------------------------------------------------------------------

def linear_probe(config, execute, *, from_id, to_id, **_kw):
    return _linear_edge_exists(execute, from_id, to_id)


def jira_probe(config, execute, *, from_id, to_id, **_kw):
    return _jira_edge_exists(config, execute, from_id=from_id, to_id=to_id)


def gitlab_probe_pair(config, execute, *, from_display, to_display, **_kw):
    from ..wire import _gitlab_iid  # noqa: PLC0415
    self_iid = _gitlab_iid(from_display)
    if isinstance(self_iid, TrackerError):
        return self_iid
    target_iid = _gitlab_iid(to_display)
    if isinstance(target_iid, TrackerError):
        return target_iid
    drained = _gitlab_links(config, execute, iid=self_iid)
    if isinstance(drained, TrackerError):
        return drained
    links, truncated = drained
    # link_type is expressed relative to the QUERIED issue (from):
    # "is_blocked_by" is the requested edge (from blocked by target);
    # "blocks" is the REVERSE direction (from blocks target) and must NOT
    # match - a reverse edge is not the requested one. "relates_to" stays:
    # it is flow's own degraded projection form on tiers without blockedBy
    # (symmetric, direction-free).
    if _gitlab_pair_present(links, target_iid=target_iid,
                            link_types={"is_blocked_by", "relates_to"}):
        return True
    if truncated:
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab issue link pages truncated at drain cap; edge absence "
            "unproven",
            subtype="truncated")
    return False


def github_probe(config, execute, *, from_display, to_display, **_kw):
    # Direction matches github_set: the PARENT is the BLOCKER (to_display);
    # the blocked issue (from_display) appears among its sub_issues.
    from ..wire import (_cli, _destination, _gh_repo,  # noqa: PLC0415
                        _github_number, _rest_drain)
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    parent = _github_number(to_display)
    if isinstance(parent, TrackerError):
        return parent
    child = _github_number(from_display)
    if isinstance(child, TrackerError):
        return child
    # Drain every page to the shared wire cap (fn-64 read-before-write): a
    # single-page probe would report a later-page child ABSENT, falsely
    # queueing a ledgered edge as a human removal (or duplicating the create
    # on an unledgered one). Truncation is unproven absence, never absence.
    drained = _rest_drain(lambda page: _cli(
        execute, "github", config, "wire-relate-probe", "GET",
        f"repos/{repo}/issues/{parent}/sub_issues"
        f"?per_page={_PAGE_SIZE}&page={page}", idempotent=True))
    if isinstance(drained, TrackerError):
        return drained
    subs, truncated = drained
    if any(isinstance(x, dict) and x.get("number") == child for x in subs):
        return True
    if truncated:
        return TrackerError(
            ErrorClass.TRANSPORT,
            "github sub_issues pages truncated at drain cap; edge absence "
            "unproven",
            subtype="truncated")
    return False


PROBES = {
    "linear": linear_probe,
    "jira": jira_probe,
    "gitlab": gitlab_probe_pair,
    "github": github_probe,
}
