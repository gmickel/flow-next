"""GitLab wire verb implementations."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

from ..types import ErrorClass, TrackerError
from . import (
    Execute,
    Result,
    _gitlab_durable,
    _check_durable,
    _cli,
    _conflict,
    _destination,
    _gl_project,
    _gitlab_iid,
    _PAGE_SIZE,
    _ready_state,
    _rest_drain,
)



def _issue_out(raw: dict, *, parent_identity: str = "validated") -> dict:
    path = raw.get("references", {})
    refs = path.get("full") if isinstance(path, dict) else None
    ident = refs or f"#{raw.get('iid')}"
    return {
        "id": _gitlab_durable(raw),
        "identifier": ident if isinstance(ident, str) else f"#{raw.get('iid')}",
        "title": raw.get("title"),
        "body": raw.get("description"),
        "url": raw.get("web_url"),
        "labels": list(raw.get("labels") or []),
        "raw": raw,
        "parent_identity": parent_identity,
    }


def _comment_out(raw: dict, *, parent_identity: str) -> dict:
    return {"id": raw.get("id"), "body": raw.get("body"),
            "url": raw.get("web_url"),
            "created_at": raw.get("created_at"),
            "raw": raw, "parent_identity": parent_identity}

def parent_read(config: dict, locator: dict, execute: Execute, *,
                op: str = "wire-parent-read") -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    if isinstance(iid, TrackerError):
        return iid
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    data = _cli(execute, "gitlab", config, op, "GET",
                f"projects/{pid}/issues/{iid}", idempotent=True)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab issue is not an object",
                            subtype="malformed_body")
    err = _check_durable("gitlab", locator, data)
    return err if err else data


def _require_parent(config: dict, locator: dict, execute: Execute) -> Result:
    return parent_read(config, locator, execute, op="wire-parent-read")


def read(config: dict, locator: dict, execute: Execute) -> Result:
    parent = parent_read(config, locator, execute, op="wire-read")
    if isinstance(parent, TrackerError):
        return parent
    return _issue_out(parent, parent_identity="validated")


def pr_link(config: dict, locator: dict, execute: Execute, *, url: str) -> Result:
    """Post one non-closing PR URL note, deduplicated by the exact URL."""
    parent = parent_read(config, locator, execute, op="wire-pr-link-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    listed = comment_list(config, locator, execute)
    if isinstance(listed, TrackerError):
        return listed
    comments = listed.get("comments")
    if not isinstance(comments, list):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab PR-link comment list is malformed",
            subtype="malformed_body",
        )
    expected = f"Flow-Next PR: {url}"
    for comment in comments:
        body = comment.get("body") if isinstance(comment, dict) else None
        if isinstance(body, str) and body.strip() == expected:
            return {
                "linked": False,
                "deduped": True,
                "kind": "note",
                "url": url,
                "comment": comment,
            }
    if listed.get("truncated"):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "gitlab PR-link dedup scan truncated; refusing to post",
            subtype="dedup_truncated",
        )
    added = comment_add(config, locator, execute, body=expected)
    if isinstance(added, TrackerError):
        return added
    return {
        "linked": True,
        "deduped": False,
        "kind": "note",
        "url": url,
        "comment": added,
    }


def update(config: dict, locator: dict, execute: Execute, *,
           title: Optional[str], body: Optional[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    payload: dict = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["description"] = body
    if not payload:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "update requires --title and/or --body-file",
                            subtype="update")
    data = _cli(execute, "gitlab", config, "wire-update", "PUT",
                f"projects/{pid}/issues/{iid}", body=payload)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab update returned no object",
                            subtype="malformed_body")
    err = _check_durable("gitlab", locator, data)
    if err:
        return err
    return _issue_out(data)


def comment_add(config: dict, locator: dict, execute: Execute, *, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    data = _cli(execute, "gitlab", config, "wire-comment-add", "POST",
                f"projects/{pid}/issues/{iid}/notes", body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab comment-add returned no object",
                            subtype="malformed_body")
    # noteable_id IS the global issue id — validate when present.
    noteable = data.get("noteable_id")
    if noteable is not None and str(noteable) != str(locator["durable"]):
        return _conflict(locator["durable"], noteable)
    identity = "validated" if noteable is not None else "not_available"
    return _comment_out(data, parent_identity=identity)


def comment_list(config: dict, locator: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    if isinstance(iid, TrackerError):
        return iid
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    drained = _rest_drain(lambda page: _cli(
        execute, "gitlab", config, "wire-comment-list", "GET",
        f"projects/{pid}/issues/{iid}/notes"
        f"?per_page={_PAGE_SIZE}&page={page}", idempotent=True))
    if isinstance(drained, TrackerError):
        return drained
    data, truncated = drained
    # MUST filter system notes (measured: label/state events are system:true).
    human = [n for n in data if isinstance(n, dict) and not n.get("system")]
    out = []
    for n in human:
        noteable = n.get("noteable_id")
        if noteable is not None and str(noteable) != str(locator["durable"]):
            return _conflict(locator["durable"], noteable)
        identity = "validated" if noteable is not None else "not_available"
        out.append(_comment_out(n, parent_identity=identity))
    # Aggregate: "validated" only when ≥1 human note AND every one had
    # noteable_id checked; empty list or any missing noteable_id → not_available.
    if human and all(n.get("noteable_id") is not None for n in human):
        aggregate = "validated"
    else:
        aggregate = "not_available"
    return {"comments": out, "truncated": truncated, "parent_identity": aggregate}


def comment_update(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    # Intrinsically parent-scoped: issue iid is in the path, so no comment
    # pre-fetch is required (unlike GitHub/Linear which address by comment id alone).
    data = _cli(execute, "gitlab", config, "wire-comment-update", "PUT",
                f"projects/{pid}/issues/{iid}/notes/{comment_id}",
                body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab comment-update returned no object",
                            subtype="malformed_body")
    noteable = data.get("noteable_id")
    if noteable is not None and str(noteable) != str(locator["durable"]):
        return _conflict(locator["durable"], noteable)
    identity = "validated" if noteable is not None else "not_available"
    return _comment_out(data, parent_identity=identity)


def comment_delete(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    # Intrinsically parent-scoped: issue iid is in the path, so no comment
    # pre-fetch is required (unlike GitHub/Linear which address by comment id alone).
    data = _cli(execute, "gitlab", config, "wire-comment-delete", "DELETE",
                f"projects/{pid}/issues/{iid}/notes/{comment_id}")
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
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    payload: dict = {}
    if add:
        payload["add_labels"] = ",".join(add)
    if remove:
        payload["remove_labels"] = ",".join(remove)
    data = _cli(execute, "gitlab", config, "wire-label", "PUT",
                f"projects/{pid}/issues/{iid}", body=payload)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab label returned no object",
                            subtype="malformed_body")
    err = _check_durable("gitlab", locator, data)
    if err:
        return err
    return _issue_out(data)


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
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    # GitLab takes numeric user ids. Callers pass ids as strings.
    current = []
    for a in (parent.get("assignees") or []):
        if isinstance(a, dict) and a.get("id") is not None:
            current.append(int(a["id"]))
    cur = set(current)
    for u in add:
        if not str(u).isdigit():
            return TrackerError(ErrorClass.INVALID_INPUT,
                                f"gitlab assignee must be a numeric user id, got {u!r}",
                                subtype="assign")
        cur.add(int(u))
    for u in remove:
        if str(u).isdigit():
            cur.discard(int(u))
    data = _cli(execute, "gitlab", config, "wire-assign", "PUT",
                f"projects/{pid}/issues/{iid}",
                body={"assignee_ids": sorted(cur)})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab assign returned no object",
                            subtype="malformed_body")
    err = _check_durable("gitlab", locator, data)
    if err:
        return err
    return _issue_out(data)


def list_open(config: dict, execute: Execute) -> Result:
    ready_state = _ready_state(config)
    if ready_state is None:
        return {"issues": [], "truncated": False}
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    # GitLab states are opened/closed (not open/closed).
    qs = urlencode({
        "state": "opened",
        "labels": ready_state,
        "per_page": _PAGE_SIZE,
    })
    drained = _rest_drain(lambda page: _cli(
        execute, "gitlab", config, "wire-list-open", "GET",
        f"projects/{pid}/issues?{qs}&page={page}",
        idempotent=True))
    if isinstance(drained, TrackerError):
        return drained
    data, truncated = drained
    return {"issues": [_issue_out(i, parent_identity="not_available")
                       for i in data if isinstance(i, dict)],
            "truncated": truncated}
