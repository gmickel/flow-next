"""Jira wire verb implementations."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote, urlencode

from ..types import ErrorClass, TrackerError
from . import (
    Execute,
    Result,
    _check_durable,
    _destination,
    _dict,
    _jira,
    _jira_base,
    _MAX_PAGES,
    _PAGE_SIZE,
)



def _issue_out(raw: dict, *, parent_identity: str = "not_available") -> dict:
    fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    return {
        "id": str(raw.get("id")),
        "identifier": raw.get("key"),
        "title": fields.get("summary"),
        "body": fields.get("description"),
        "url": None,
        "labels": list(fields.get("labels") or []),
        "raw": raw,
        "parent_identity": parent_identity,
    }


def _comment_out(raw: dict, *, parent_identity: str) -> dict:
    return {"id": raw.get("id"), "body": raw.get("body"),
            "url": None, "raw": raw, "parent_identity": parent_identity}

def parent_read(config: dict, locator: dict, execute: Execute, *,
                op: str = "wire-parent-read") -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    # jira - the PARENT READ addresses by the DISPLAY key and compares the
    # returned immutable id to locator.durable. The key is the mutable half
    # (project moves renumber it), so key->id comparison is the check that
    # actually catches a move; reading by durable would compare durable to
    # itself and always pass. Mutations still address by durable (immutable).
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    key = locator["display"]
    data = _jira(execute, op, "GET",
                 f"{base}/rest/api/2/issue/{quote(str(key), safe='')}"
                 f"?fields=summary,description,status,priority,labels,assignee,updated",
                 idempotent=True)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "jira issue is not an object",
                            subtype="malformed_body")
    err = _check_durable("jira", locator, data)
    return err if err else data


def _require_parent(config: dict, locator: dict, execute: Execute) -> Result:
    return parent_read(config, locator, execute, op="wire-parent-read")


def read(config: dict, locator: dict, execute: Execute) -> Result:
    parent = parent_read(config, locator, execute, op="wire-read")
    if isinstance(parent, TrackerError):
        return parent
    return _issue_out(parent, parent_identity="validated")


def update(config: dict, locator: dict, execute: Execute, *,
           title: Optional[str], body: Optional[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    fields: dict = {}
    if title is not None:
        fields["summary"] = title
    if body is not None:
        fields["description"] = body
    if not fields:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "update requires --title and/or --body-file",
                            subtype="update")
    key = locator["durable"]
    data = _jira(execute, "wire-update", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(key), safe='')}",
                 body={"fields": fields})
    if isinstance(data, TrackerError):
        return data
    # PUT returns 204 (no body), so response-side parent identity is not
    # available on the write itself - the pre-mutation gate already checked.
    # Fold the applied fields into the parent snapshot so the caller sees the
    # POST-update state, not the stale pre-update body.
    prior = parent.get("fields") if isinstance(parent.get("fields"), dict) else {}
    parent["fields"] = {**prior, **fields}
    # 204 carries no body: response-side parent identity is NOT available on
    # this synthesized post-state - the pre-mutation gate is the protection.
    return _issue_out(parent, parent_identity="not_available")


def comment_add(config: dict, locator: dict, execute: Execute, *, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    data = _jira(execute, "wire-comment-add", "POST",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}/comment",
                 body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "jira comment-add returned no object",
                            subtype="malformed_body")
    return _comment_out(data, parent_identity="not_available")


def comment_list(config: dict, locator: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    collected: list = []
    truncated = False
    start_at = 0
    for _ in range(_MAX_PAGES):
        data = _jira(execute, "wire-comment-list", "GET",
                     f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}"
                     f"/comment?startAt={start_at}&maxResults={_PAGE_SIZE}",
                     idempotent=True)
        if isinstance(data, TrackerError):
            return data
        if not isinstance(data, dict):
            return TrackerError(ErrorClass.TRANSPORT, "jira comment list is not an object",
                                subtype="malformed_body")
        comments = data.get("comments") or []
        if not isinstance(comments, list):
            return TrackerError(ErrorClass.TRANSPORT, "jira comments is not a list",
                                subtype="malformed_body")
        collected.extend(c for c in comments if isinstance(c, dict))
        total = data.get("total")
        start_at += len(comments)
        if not comments or not isinstance(total, int) or start_at >= total:
            break
    else:
        truncated = True
    return {"comments": [_comment_out(c, parent_identity="not_available")
                         for c in collected],
            "truncated": truncated, "parent_identity": "not_available"}


def comment_update(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    # Intrinsically parent-scoped: issue key/id is in the path, so no comment
    # pre-fetch is required (unlike GitHub/Linear which address by comment id alone).
    data = _jira(execute, "wire-comment-update", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}"
                 f"/comment/{quote(str(comment_id), safe='')}",
                 body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "jira comment-update returned no object",
                            subtype="malformed_body")
    return _comment_out(data, parent_identity="not_available")


def comment_delete(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    # Intrinsically parent-scoped: issue key/id is in the path, so no comment
    # pre-fetch is required (unlike GitHub/Linear which address by comment id alone).
    data = _jira(execute, "wire-comment-delete", "DELETE",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}"
                 f"/comment/{quote(str(comment_id), safe='')}")
    if isinstance(data, TrackerError):
        return data
    return {"deleted": comment_id, "parent_identity": "not_available"}


def label(config: dict, locator: dict, execute: Execute, *,
          add: list[str], remove: list[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    if not add and not remove:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "label requires --add and/or --remove", subtype="label")
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    fields = parent.get("fields") if isinstance(parent.get("fields"), dict) else {}
    current_labels = list(fields.get("labels") or [])
    for name in add:
        if name not in current_labels:
            current_labels.append(name)
    for name in remove:
        current_labels = [x for x in current_labels if x != name]
    data = _jira(execute, "wire-label", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}",
                 body={"fields": {"labels": current_labels}})
    if isinstance(data, TrackerError):
        return data
    parent["fields"] = {**fields, "labels": current_labels}
    return _issue_out(parent)


def assign(config: dict, locator: dict, execute: Execute, *,
           add: list[str], remove: list[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    if not add and not remove:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "assign requires --add and/or --remove", subtype="assign")
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    fields = parent.get("fields") if isinstance(parent.get("fields"), dict) else {}
    prior = fields.get("assignee") if isinstance(fields.get("assignee"), dict) else None
    previous = None
    if prior:
        previous = prior.get("accountId") or prior.get("name")
    # Single-assignee: last --add REPLACES; report prior in degraded (R15).
    if add:
        # Cloud prefers accountId; DC may use name. Pass through as accountId when
        # it looks like one, else as name.
        user = add[-1]
        assignee = {"accountId": user} if len(user) > 20 or "-" in user else {"name": user}
        applied = user
    else:
        assignee = None
        applied = None
    data = _jira(execute, "wire-assign", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}",
                 body={"fields": {"assignee": assignee}})
    if isinstance(data, TrackerError):
        return data
    parent["fields"] = {**fields, "assignee": assignee}
    out = _issue_out(parent)
    if add and previous is not None and previous != applied:
        out["degraded"] = {
            "kind": "assignee_replaced",
            "previous": previous,
            "applied": applied,
        }
    return out


def list_open(config: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    key = dest.get("projectKey") or _dict(_dict(config.get("tracker")).get("perTracker")).get("projectKey")
    if not key:
        return TrackerError(ErrorClass.UNRESOLVED, "jira projectKey is not resolved",
                            subtype="destination")
    jql = f"project = {key} AND resolution = Unresolved ORDER BY updated DESC"
    # apiVersion 2 (pinned): classic /search with offset pagination, drained.
    collected: list = []
    truncated = False
    start_at = 0
    for _ in range(_MAX_PAGES):
        qs = urlencode({"jql": jql, "startAt": start_at, "maxResults": _PAGE_SIZE,
                        "fields": "summary,description,status,priority,labels,updated"})
        data = _jira(execute, "wire-list-open", "GET",
                     f"{base}/rest/api/2/search?{qs}", idempotent=True)
        if isinstance(data, TrackerError):
            return data
        if not isinstance(data, dict):
            return TrackerError(ErrorClass.TRANSPORT, "jira search is not an object",
                                subtype="malformed_body")
        issues = data.get("issues") or []
        if not isinstance(issues, list):
            return TrackerError(ErrorClass.TRANSPORT, "jira search.issues is not a list",
                                subtype="malformed_body")
        collected.extend(i for i in issues if isinstance(i, dict))
        total = data.get("total")
        start_at += len(issues)
        if not issues or not isinstance(total, int) or start_at >= total:
            break
    else:
        truncated = True
    return {"issues": [_issue_out(i, parent_identity="not_available")
                       for i in collected],
            "truncated": truncated}
