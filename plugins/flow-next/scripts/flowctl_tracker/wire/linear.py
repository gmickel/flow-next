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
    _ready_state,
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
        "status": (
            {"raw": raw["state"].get("name"),
             "type": raw["state"].get("type")}
            if isinstance(raw.get("state"), dict) else None
        ),
        "raw": raw,
        "parent_identity": parent_identity,
    }


def _comment_out(raw: dict, *, parent_identity: str) -> dict:
    return {"id": raw.get("id"), "body": raw.get("body"),
            "url": raw.get("url"),
            "created_at": raw.get("createdAt"),
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
                "state { id name type } "
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


def _pr_attachments(locator: dict, execute: Execute) -> Result:
    """Drain the PR-link dedup surface; absence is valid only when complete."""
    def pluck(data: dict) -> Union[dict, TrackerError]:
        issue = data.get("issue")
        conn = issue.get("attachments") if isinstance(issue, dict) else None
        if not isinstance(conn, dict):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "linear attachments connection is malformed",
                subtype="malformed_body",
            )
        return conn

    drained = _gql_connection_drain(
        execute,
        "wire-pr-link-list",
        "query($id: String!, $after: String) { issue(id: $id) { "
        f"attachments(first: {_PAGE_SIZE}, after: $after) "
        "{ nodes { id url } pageInfo { hasNextPage endCursor } } } }",
        {"id": locator["durable"]},
        pluck,
    )
    if isinstance(drained, TrackerError):
        return drained
    nodes, truncated = drained
    return {"attachments": nodes, "truncated": truncated}


def _matching_pr_attachment(listed: dict, url: str) -> Optional[dict]:
    attachments = listed.get("attachments")
    if not isinstance(attachments, list):
        return None
    return next(
        (
            attachment
            for attachment in attachments
            if isinstance(attachment, dict) and attachment.get("url") == url
        ),
        None,
    )


def pr_link(config: dict, locator: dict, execute: Execute, *, url: str) -> Result:
    """Create Linear's rich URL attachment for PR status/diff integration."""
    parent = parent_read(config, locator, execute, op="wire-pr-link-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    listed = _pr_attachments(locator, execute)
    if isinstance(listed, TrackerError):
        return listed
    existing = _matching_pr_attachment(listed, url)
    if existing is not None:
        return {
            "linked": False,
            "deduped": True,
            "kind": "rich-attachment",
            "url": url,
            "attachment": existing,
        }
    if listed.get("truncated"):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "linear PR-link dedup scan truncated; refusing to attach",
            subtype="dedup_truncated",
        )
    data = _gql(
        execute,
        "wire-pr-link",
        "mutation($issueId: String!, $url: String!) { "
        "attachmentLinkURL(issueId: $issueId, url: $url) { "
        "success attachment { id url } } }",
        {"issueId": locator["durable"], "url": url},
    )
    if isinstance(data, TrackerError):
        # Another make-pr process may have attached the same URL after our
        # complete absence scan. Re-read once before surfacing the mutation
        # error so that the race remains idempotent without hiding other errors.
        raced = _pr_attachments(locator, execute)
        if not isinstance(raced, TrackerError):
            existing = _matching_pr_attachment(raced, url)
            if existing is not None:
                return {
                    "linked": False,
                    "deduped": True,
                    "kind": "rich-attachment",
                    "url": url,
                    "attachment": existing,
                }
        return data
    payload = _require_success(data, "attachmentLinkURL")
    if isinstance(payload, TrackerError):
        return payload
    return {
        "linked": True,
        "deduped": False,
        "kind": "rich-attachment",
        "url": url,
        "attachment": payload.get("attachment"),
    }


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
                "comment { id body url createdAt issue { id } } } }",
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
        "{ nodes { id body url createdAt } "
        "pageInfo { hasNextPage endCursor } } } }",
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
                "comment { id body url createdAt issue { id } } } }",
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


def _team_label_lookup(execute: Execute, team_id: str, name: str
                       ) -> Union[Optional[str], TrackerError]:
    """Resolve `name` against the team's LIVE label connection.

    A label auto-created while updating a DIFFERENT issue exists on the team
    but appears in neither the pinned config labelIds nor this issue's parent
    read; creating again would fail (name already exists) or duplicate. The
    server-side name filter (`eqIgnoreCase` - label names are case-insensitively
    unique per team) avoids pagination entirely, but the connection shape is
    still validated: unproven absence is never absence, so a malformed or
    truncated listing returns a TrackerError instead of falling through to
    issueLabelCreate.
    """
    data = _gql(execute, "wire-label-team-lookup",
                "query($teamId: String!, $name: String!) { team(id: $teamId) { "
                "labels(filter: { name: { eqIgnoreCase: $name } }, first: 50) "
                "{ nodes { id name } pageInfo { hasNextPage endCursor } } } }",
                {"teamId": team_id, "name": name}, idempotent=True)
    if isinstance(data, TrackerError):
        return data
    team = data.get("team")
    conn = team.get("labels") if isinstance(team, dict) else None
    nodes = conn.get("nodes") if isinstance(conn, dict) else None
    if not isinstance(nodes, list):
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear team labels connection is malformed",
                            subtype="malformed_body")
    for n in nodes:
        if (isinstance(n, dict) and isinstance(n.get("id"), str) and n["id"]
                and isinstance(n.get("name"), str)
                and n["name"].lower() == name.lower()):
            return n["id"]
    if _dict(conn.get("pageInfo")).get("hasNextPage"):
        # Name-filtered yet truncated: the match could sit on an unread page,
        # so absence is unproven and auto-create must not proceed.
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear team labels listing is truncated; "
                            "cannot prove label absence before create",
                            subtype="truncated")
    return None


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
    label_ids = dict(_dict(dest.get("labelIds")))
    team_id = dest.get("teamId")
    current = []
    labels = parent.get("labels")
    nodes = (labels.get("nodes") if isinstance(labels, dict) else labels) or []
    # Label names are case-insensitively unique per Linear team; the resolved
    # labelIds map is keyed lowercased (providers/linear.py). Fold the labels
    # the parent read just returned into the lookup so a label auto-created by
    # an earlier invocation (present on the issue but absent from the pinned
    # config) resolves to its live id instead of a second issueLabelCreate.
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            current.append(n["id"])
            if isinstance(n.get("name"), str) and n["name"]:
                label_ids.setdefault(n["name"].lower(), n["id"])
    current_set = set(current)
    created: list[str] = []
    for name in add:
        key = str(name).lower()
        lid = label_ids.get(key)
        if not lid:
            # R15: unknown Linear label AUTO-CREATES (matches GitHub/GitLab
            # create-on-demand). issueLabelCreate then attach via labelIds.
            if not team_id:
                return TrackerError(ErrorClass.UNRESOLVED,
                                    "linear teamId required to auto-create label",
                                    subtype="destination")
            # The parent-read fold above only covers labels already on THIS
            # issue; a label auto-created via another issue is still unknown
            # here. Prove absence against the team's live labels first.
            found = _team_label_lookup(execute, team_id, str(name))
            if isinstance(found, TrackerError):
                return found
            if found:
                label_ids[key] = found
                current_set.add(found)
                continue
            created_data = _gql(
                execute, "wire-label-create",
                "mutation($input: IssueLabelCreateInput!) { "
                "issueLabelCreate(input: $input) { success "
                "issueLabel { id name } } }",
                {"input": {"name": str(name), "teamId": team_id}},
            )
            if isinstance(created_data, TrackerError):
                return created_data
            payload = created_data.get("issueLabelCreate")
            if not isinstance(payload, dict) or payload.get("success") is not True:
                return TrackerError(ErrorClass.TRANSPORT,
                                    "linear issueLabelCreate failed",
                                    subtype="mutation_failed")
            lab = payload.get("issueLabel") if isinstance(payload.get("issueLabel"), dict) else {}
            lid = lab.get("id")
            if not isinstance(lid, str) or not lid:
                return TrackerError(ErrorClass.TRANSPORT,
                                    "linear issueLabelCreate returned no id",
                                    subtype="malformed_body")
            label_ids[key] = lid
            created.append(str(name))
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
    out = _issue_out(issue)
    if created:
        out["labels_created"] = created
    return out


def assign(config: dict, locator: dict, execute: Execute, *,
           add: list[str], remove: list[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    if not add and not remove:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "assign requires --add and/or --remove", subtype="assign")
    # Single-assignee: last --add REPLACES; report prior in degraded (R15).
    previous = None
    current = parent.get("assignee") if isinstance(parent.get("assignee"), dict) else None
    current_id = current.get("id") if current else None
    assignee_id = None
    if add:
        assignee_id = add[-1]
        if current_id and current_id != assignee_id:
            previous = current_id
    elif remove:
        if current_id in remove:
            assignee_id = None
            previous = current_id
        else:
            assignee_id = current_id
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
    out = _issue_out(issue)
    if previous is not None and add:
        out["degraded"] = {
            "kind": "assignee_replaced",
            "previous": previous,
            "applied": assignee_id,
        }
    return out


def list_open(config: dict, execute: Execute) -> Result:
    ready_state = _ready_state(config)
    if ready_state is None:
        return {"issues": [], "truncated": False}
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    team_id = dest.get("teamId")
    filt: dict = {"state": {"name": {"eqIgnoreCase": ready_state}}}
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
