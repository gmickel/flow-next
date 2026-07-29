"""GitHub wire verb implementations."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote, urlencode

from ..types import ErrorClass, TrackerError
from . import (
    Execute,
    Result,
    _github_durable,
    _check_durable,
    _cli,
    _comment_parent_mismatch,
    _destination,
    _gh_repo,
    _github_number,
    _PAGE_SIZE,
    _ready_state,
    _rest_drain,
)



def _issue_out(raw: dict, *, parent_identity: str = "validated") -> dict:
    labels = raw.get("labels") or []
    label_names = [x.get("name") if isinstance(x, dict) else x for x in labels]
    return {
        "id": _github_durable(raw),
        "identifier": f"#{raw.get('number')}",
        "title": raw.get("title"),
        "body": raw.get("body"),
        "url": raw.get("html_url") or raw.get("url"),
        "labels": label_names,
        "raw": raw,
        "parent_identity": parent_identity,
    }


def _comment_out(raw: dict, *, parent_identity: str) -> dict:
    return {"id": raw.get("id"), "body": raw.get("body"),
            "url": raw.get("html_url") or raw.get("url"),
            "created_at": raw.get("created_at"),
            "raw": raw, "parent_identity": parent_identity}

def parent_read(config: dict, locator: dict, execute: Execute, *,
                op: str = "wire-parent-read") -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    number = _github_number(locator["display"])
    if isinstance(number, TrackerError):
        return number
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    data = _cli(execute, "github", config, op, "GET",
                f"repos/{repo}/issues/{number}", idempotent=True)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "github issue is not an object",
                            subtype="malformed_body")
    err = _check_durable("github", locator, data)
    return err if err else data


def _require_parent(config: dict, locator: dict, execute: Execute) -> Result:
    return parent_read(config, locator, execute, op="wire-parent-read")


def _comment_belongs(config: dict, locator: dict, dest: dict, execute: Execute, *,
                     comment_id: str) -> Optional[TrackerError]:
    """Verify the comment's issue_url matches the locator display number.

    GitHub comment-update/delete address by comment_id alone; without this
    pre-fetch a valid-but-unrelated parent locator could mutate another issue's
    comment.
    """
    number = _github_number(locator["display"])
    if isinstance(number, TrackerError):
        return number
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    data = _cli(execute, "github", config, "wire-comment-belong", "GET",
                f"repos/{repo}/issues/comments/{comment_id}", idempotent=True)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "github comment is not an object",
                            subtype="malformed_body")
    issue_url = data.get("issue_url")
    if not isinstance(issue_url, str) or not issue_url.endswith(f"/issues/{number}"):
        return _comment_parent_mismatch(
            comment_id, f"issue_url {issue_url!r} vs expected /issues/{number}")
    return None


def read(config: dict, locator: dict, execute: Execute) -> Result:
    parent = parent_read(config, locator, execute, op="wire-read")
    if isinstance(parent, TrackerError):
        return parent
    return _issue_out(parent, parent_identity="validated")


def pr_link(config: dict, locator: dict, execute: Execute, *, url: str) -> Result:
    """GitHub linkage already lives in the PR body's non-closing `Refs #N`."""
    parent = parent_read(config, locator, execute, op="wire-pr-link-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    return {
        "linked": False,
        "deduped": True,
        "kind": "native-pr-body-ref",
        "url": url,
    }


def update(config: dict, locator: dict, execute: Execute, *,
           title: Optional[str], body: Optional[str]) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    number = _github_number(locator["display"])
    repo = _gh_repo(dest)
    if isinstance(number, TrackerError):
        return number
    if isinstance(repo, TrackerError):
        return repo
    payload: dict = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if not payload:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "update requires --title and/or --body-file",
                            subtype="update")
    data = _cli(execute, "github", config, "wire-update", "PATCH",
                f"repos/{repo}/issues/{number}", body=payload)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "github update returned no object",
                            subtype="malformed_body")
    err = _check_durable("github", locator, data)
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
    number = _github_number(locator["display"])
    repo = _gh_repo(dest)
    if isinstance(number, TrackerError):
        return number
    if isinstance(repo, TrackerError):
        return repo
    data = _cli(execute, "github", config, "wire-comment-add", "POST",
                f"repos/{repo}/issues/{number}/comments", body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "github comment-add returned no object",
                            subtype="malformed_body")
    # REST comment has issue_url, not parent node_id — do not fake a check.
    return _comment_out(data, parent_identity="not_available")


def comment_list(config: dict, locator: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    number = _github_number(locator["display"])
    if isinstance(number, TrackerError):
        return number
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    drained = _rest_drain(lambda page: _cli(
        execute, "github", config, "wire-comment-list", "GET",
        f"repos/{repo}/issues/{number}/comments"
        f"?per_page={_PAGE_SIZE}&page={page}", idempotent=True))
    if isinstance(drained, TrackerError):
        return drained
    data, truncated = drained
    # Comment list items carry no parent node_id.
    return {"comments": [_comment_out(c, parent_identity="not_available")
                         for c in data if isinstance(c, dict)],
            "truncated": truncated,
            "parent_identity": "not_available"}


def comment_update(config: dict, locator: dict, execute: Execute, *,
                   comment_id: str, body: str) -> Result:
    parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    belong = _comment_belongs(config, locator, dest, execute, comment_id=comment_id)
    if belong is not None:
        return belong
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    # Path takes the comment id alone, but the contract still requires the
    # parent locator (pre-mutation gate + belong check above). Response has no
    # parent node_id.
    data = _cli(execute, "github", config, "wire-comment-update", "PATCH",
                f"repos/{repo}/issues/comments/{comment_id}", body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "github comment-update returned no object",
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
    belong = _comment_belongs(config, locator, dest, execute, comment_id=comment_id)
    if belong is not None:
        return belong
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    data = _cli(execute, "github", config, "wire-comment-delete", "DELETE",
                f"repos/{repo}/issues/comments/{comment_id}")
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
    number = _github_number(locator["display"])
    repo = _gh_repo(dest)
    if isinstance(number, TrackerError):
        return number
    if isinstance(repo, TrackerError):
        return repo
    data: Any = parent
    if add:
        data = _cli(execute, "github", config, "wire-label", "POST",
                    f"repos/{repo}/issues/{number}/labels", body={"labels": add})
        if isinstance(data, TrackerError):
            return data
    for name in remove:
        data = _cli(execute, "github", config, "wire-label", "DELETE",
                    f"repos/{repo}/issues/{number}/labels/{quote(name, safe='')}")
        if isinstance(data, TrackerError):
            return data
    # Re-read so the durable check lands on an issue-shaped response.
    refreshed = parent_read(config, locator, execute, op="wire-label-readback")
    if isinstance(refreshed, TrackerError):
        return refreshed
    return _issue_out(refreshed)


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
    number = _github_number(locator["display"])
    repo = _gh_repo(dest)
    if isinstance(number, TrackerError):
        return number
    if isinstance(repo, TrackerError):
        return repo
    if add:
        data = _cli(execute, "github", config, "wire-assign", "POST",
                    f"repos/{repo}/issues/{number}/assignees",
                    body={"assignees": add})
        if isinstance(data, TrackerError):
            return data
    if remove:
        data = _cli(execute, "github", config, "wire-assign", "DELETE",
                    f"repos/{repo}/issues/{number}/assignees",
                    body={"assignees": remove})
        if isinstance(data, TrackerError):
            return data
    refreshed = parent_read(config, locator, execute, op="wire-assign-readback")
    if isinstance(refreshed, TrackerError):
        return refreshed
    return _issue_out(refreshed)


def list_open(config: dict, execute: Execute) -> Result:
    ready_state = _ready_state(config)
    if ready_state is None:
        return {"issues": [], "truncated": False}
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    qs = urlencode({
        "state": "open",
        "labels": ready_state,
        "per_page": _PAGE_SIZE,
    })
    drained = _rest_drain(lambda page: _cli(
        execute, "github", config, "wire-list-open", "GET",
        f"repos/{repo}/issues?{qs}&page={page}",
        idempotent=True))
    if isinstance(drained, TrackerError):
        return drained
    data, truncated = drained
    # MEASURED: GET /issues returns pull requests too - filter on pull_request.
    issues = [i for i in data if isinstance(i, dict) and "pull_request" not in i]
    return {"issues": [_issue_out(i, parent_identity="not_available")
                       for i in issues],
            "truncated": truncated}
