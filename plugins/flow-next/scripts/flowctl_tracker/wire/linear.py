"""Linear wire verb implementations."""

from __future__ import annotations

from typing import Optional, Union

from ..types import ErrorClass, TrackerError
from . import (
    Execute,
    Result,
    _check_durable,
    _comment_parent_mismatch,
    _destination,
    _dict,
    _gql,
    _gql_connection_drain,
    _PAGE_SIZE,
)


def _require_success(data: dict, field: str) -> Union[dict, TrackerError]:
    """Linear mutations that carry `success` must report success is True."""
    payload = data.get(field)
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"linear {field} reported failure",
                            subtype="mutation_failed")
    return payload



def _issue_out(raw: dict, *, parent_identity: str = "validated") -> dict:
    labels = ((((raw.get("labels") or {}).get("nodes"))
               if isinstance(raw.get("labels"), dict) else raw.get("labels")) or [])
    names = [n.get("name") for n in labels if isinstance(n, dict)]
    return {
        "id": raw.get("id"),
        "identifier": raw.get("identifier"),
        "title": raw.get("title"),
        "body": raw.get("description"),
        "url": raw.get("url"),
        "labels": names,
        "raw": raw,
        "parent_identity": parent_identity,
    }


def _comment_out(raw: dict, *, parent_identity: str) -> dict:
    return {"id": raw.get("id"), "body": raw.get("body"),
            "url": raw.get("url"),
            "raw": raw, "parent_identity": parent_identity}

def parent_read(config: dict, locator: dict, execute: Execute, *,
                op: str = "wire-parent-read") -> Result:
    # Address by DISPLAY identifier (issue(id:) accepts both) and compare
    # the returned UUID to locator.durable. Reading by durable would make
    # the check vacuous - durable compared to itself always passes, and a
    # moved/renumbered identifier would go unnoticed.
    data = _gql(execute, op,
                "query($id: String!) { issue(id: $id) { id identifier title "
                "description url updatedAt "
                "labels { nodes { id name } } "
                "assignee { id name } } }",
                {"id": locator["display"]}, idempotent=True)
    if isinstance(data, TrackerError):
        return data
    issue = data.get("issue")
    if issue is None:
        return TrackerError(ErrorClass.NOT_FOUND, "linear issue not found",
                            subtype="parent")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear issue is not an object",
                            subtype="malformed_body")
    err = _check_durable("linear", locator, issue)
    return err if err else issue


def _require_parent(config: dict, locator: dict, execute: Execute) -> Result:
    return parent_read(config, locator, execute, op="wire-parent-read")


def _comment_belongs(locator: dict, execute: Execute, *,
                     comment_id: str) -> Optional[TrackerError]:
    """Verify comment.issue.id matches locator.durable before mutating.

    Linear comment-update/delete address by comment_id alone; without this
    pre-fetch a valid-but-unrelated parent locator could mutate another issue's
    comment.
    """
    data = _gql(execute, "wire-comment-belong",
                "query($id: String!) { comment(id: $id) { id issue { id } } }",
                {"id": comment_id}, idempotent=True)
    if isinstance(data, TrackerError):
        return data
    comment = data.get("comment")
    if comment is None:
        return TrackerError(ErrorClass.NOT_FOUND, "linear comment not found",
                            subtype="comment")
    if not isinstance(comment, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear comment is not an object",
                            subtype="malformed_body")
    issue = comment.get("issue") if isinstance(comment.get("issue"), dict) else None
    issue_id = issue.get("id") if issue else None
    if issue_id is None or str(issue_id) != str(locator["durable"]):
        return _comment_parent_mismatch(
            comment_id, f"issue.id {issue_id!r} vs locator.durable {locator['durable']!r}")
    return None


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
    inp: dict = {}
    if title is not None:
        inp["title"] = title
    if body is not None:
        inp["description"] = body
    if not inp:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "update requires --title and/or --body-file",
                            subtype="update")
    data = _gql(execute, "wire-update",
                "mutation($id: String!, $input: IssueUpdateInput!) { "
                "issueUpdate(id: $id, input: $input) { success "
                "issue { id identifier title description url } } }",
                {"id": locator["durable"], "input": inp})
    if isinstance(data, TrackerError):
        return data
    mut = _require_success(data, "issueUpdate")
    if isinstance(mut, TrackerError):
        return mut
    issue = mut.get("issue")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear update returned no issue",
                            subtype="malformed_body")
    err = _check_durable("linear", locator, issue)
    if err:
        return err
    return _issue_out(issue)


def comment_add(config: dict, locator: dict, execute: Execute, *, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    data = _gql(execute, "wire-comment-add",
                "mutation($input: CommentCreateInput!) { "
                "commentCreate(input: $input) { success "
                "comment { id body url issue { id } } } }",
                {"input": {"issueId": locator["durable"], "body": body}})
    if isinstance(data, TrackerError):
        return data
    mut = _require_success(data, "commentCreate")
    if isinstance(mut, TrackerError):
        return mut
    comment = mut.get("comment")
    if not isinstance(comment, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear comment-add returned no comment",
                            subtype="malformed_body")
    issue = comment.get("issue") if isinstance(comment.get("issue"), dict) else None
    if issue is not None:
        err = _check_durable("linear", locator, issue)
        if err:
            return err
        return _comment_out(comment, parent_identity="validated")
    return _comment_out(comment, parent_identity="not_available")


def comment_list(config: dict, locator: dict, execute: Execute) -> Result:
    """Display-addressed (real durable validation) + fully drained connection."""
    probe = _gql(execute, "wire-comment-list",
                 "query($id: String!) { issue(id: $id) { id } }",
                 {"id": locator["display"]}, idempotent=True)
    if isinstance(probe, TrackerError):
        return probe
    issue = probe.get("issue")
    if issue is None:
        return TrackerError(ErrorClass.NOT_FOUND, "linear issue not found",
                            subtype="parent")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear issue is not an object",
                            subtype="malformed_body")
    err = _check_durable("linear", locator, issue)
    if err:
        return err

    def pluck(data: dict) -> Union[dict, TrackerError]:
        iss = data.get("issue")
        conn = (iss.get("comments") if isinstance(iss, dict) else None)
        if not isinstance(conn, dict):
            return TrackerError(ErrorClass.TRANSPORT,
                                "linear comments connection is malformed",
                                subtype="malformed_body")
        return conn

    drained = _gql_connection_drain(
        execute, "wire-comment-list",
        "query($id: String!, $after: String) { issue(id: $id) { "
        f"comments(first: {_PAGE_SIZE}, after: $after) "
        "{ nodes { id body url } pageInfo { hasNextPage endCursor } } } }",
        {"id": locator["display"]}, pluck)
    if isinstance(drained, TrackerError):
        return drained
    nodes, truncated = drained
    return {"comments": [_comment_out(c, parent_identity="validated")
                         for c in nodes],
            "truncated": truncated, "parent_identity": "validated"}


def comment_update(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    belong = _comment_belongs(locator, execute, comment_id=comment_id)
    if belong is not None:
        return belong
    data = _gql(execute, "wire-comment-update",
                "mutation($id: String!, $input: CommentUpdateInput!) { "
                "commentUpdate(id: $id, input: $input) { success "
                "comment { id body url issue { id } } } }",
                {"id": comment_id, "input": {"body": body}})
    if isinstance(data, TrackerError):
        return data
    mut = _require_success(data, "commentUpdate")
    if isinstance(mut, TrackerError):
        return mut
    comment = mut.get("comment")
    if not isinstance(comment, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear comment-update returned no comment",
                            subtype="malformed_body")
    issue = comment.get("issue") if isinstance(comment.get("issue"), dict) else None
    if issue is not None:
        err = _check_durable("linear", locator, issue)
        if err:
            return err
        return _comment_out(comment, parent_identity="validated")
    return _comment_out(comment, parent_identity="not_available")


def comment_delete(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    belong = _comment_belongs(locator, execute, comment_id=comment_id)
    if belong is not None:
        return belong
    data = _gql(execute, "wire-comment-delete",
                "mutation($id: String!) { commentDelete(id: $id) { success } }",
                {"id": comment_id})
    if isinstance(data, TrackerError):
        return data
    mut = _require_success(data, "commentDelete")
    if isinstance(mut, TrackerError):
        return mut
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
    label_ids = _dict(dest.get("labelIds"))
    current = []
    labels = parent.get("labels")
    nodes = (labels.get("nodes") if isinstance(labels, dict) else labels) or []
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            current.append(n["id"])
    current_set = set(current)
    for name in add:
        lid = label_ids.get(str(name).lower())
        if not lid:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                f"unknown linear label {name!r}; resolve labels "
                                "or create it first", subtype="label")
        current_set.add(lid)
    for name in remove:
        lid = label_ids.get(str(name).lower())
        if lid:
            current_set.discard(lid)
    data = _gql(execute, "wire-label",
                "mutation($id: String!, $input: IssueUpdateInput!) { "
                "issueUpdate(id: $id, input: $input) { success "
                "issue { id identifier title description url "
                "labels { nodes { id name } } } } }",
                {"id": locator["durable"],
                 "input": {"labelIds": sorted(current_set)}})
    if isinstance(data, TrackerError):
        return data
    mut = _require_success(data, "issueUpdate")
    if isinstance(mut, TrackerError):
        return mut
    issue = mut.get("issue")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear label returned no issue",
                            subtype="malformed_body")
    err = _check_durable("linear", locator, issue)
    if err:
        return err
    return _issue_out(issue)


def assign(config: dict, locator: dict, execute: Execute, *,
           add: list[str], remove: list[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    if not add and not remove:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "assign requires --add and/or --remove", subtype="assign")
    # Single-assignee: last --add wins; --remove clears when it matches.
    assignee_id = None
    if add:
        assignee_id = add[-1]
    elif remove:
        current = parent.get("assignee") if isinstance(parent.get("assignee"), dict) else None
        if current and current.get("id") in remove:
            assignee_id = None
        else:
            assignee_id = current.get("id") if current else None
    data = _gql(execute, "wire-assign",
                "mutation($id: String!, $input: IssueUpdateInput!) { "
                "issueUpdate(id: $id, input: $input) { success "
                "issue { id identifier title description url assignee { id name } } } }",
                {"id": locator["durable"],
                 "input": {"assigneeId": assignee_id}})
    if isinstance(data, TrackerError):
        return data
    mut = _require_success(data, "issueUpdate")
    if isinstance(mut, TrackerError):
        return mut
    issue = mut.get("issue")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.TRANSPORT, "linear assign returned no issue",
                            subtype="malformed_body")
    err = _check_durable("linear", locator, issue)
    if err:
        return err
    return _issue_out(issue)


def list_open(config: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    team_id = dest.get("teamId")
    filt: dict = {"state": {"type": {"nin": ["completed", "canceled"]}}}
    if team_id:
        filt["team"] = {"id": {"eq": team_id}}

    def pluck(data: dict) -> Union[dict, TrackerError]:
        conn = data.get("issues")
        if not isinstance(conn, dict):
            return TrackerError(ErrorClass.TRANSPORT,
                                "linear issues connection is malformed",
                                subtype="malformed_body")
        return conn

    drained = _gql_connection_drain(
        execute, "wire-list-open",
        "query($filter: IssueFilter!, $after: String) { "
        f"issues(first: {_PAGE_SIZE}, filter: $filter, after: $after) "
        "{ nodes { id identifier title description url } "
        "pageInfo { hasNextPage endCursor } } }",
        {"filter": filt}, pluck)
    if isinstance(drained, TrackerError):
        return drained
    nodes, truncated = drained
    return {"issues": [_issue_out(i, parent_identity="not_available")
                       for i in nodes],
            "truncated": truncated}
