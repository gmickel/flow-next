"""Jira wire verb implementations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, quote, urlencode, urlparse

from ..providers.jira_markup import markdown_to_wiki, wiki_to_markdown
from ..types import ErrorClass, TrackerError
from . import (
    _JIRA_ISSUE_KEY_RE,
    Execute,
    Result,
    _check_durable,
    _destination,
    _dict,
    _jira,
    _jira_base,
    _jira_issue_key,
    _jira_project_key,
    _MAX_PAGES,
    _PAGE_SIZE,
    _ready_state,
)


#: Read by the agent only on the idea-intake path (fn-330).
IDEA_REFERENCE = Path(__file__).resolve().parents[3] / "skills" / "flow" / "playbooks" / "tracker.md"


def idea_reference() -> str:
    """The reference's absolute path when it sits beside `scripts/`, else its
    path under the plugin root: the output never names a missing file."""
    return str(IDEA_REFERENCE) if IDEA_REFERENCE.is_file() else "skills/flow/playbooks/tracker.md"


def has_idea_source(config: dict) -> bool:
    """`tracker.perTracker.ideaProjectKeys` lists at least one project."""
    keys = _dict(_dict(config.get("tracker")).get("perTracker")).get("ideaProjectKeys")
    return bool(keys) and isinstance(keys, list)


def is_idea_key(config: dict, key: str) -> bool:
    """A key in a project `tracker.perTracker.ideaProjectKeys` lists, never the
    delivery project. Costs no request; absent or empty config is always False."""
    keys = _dict(_dict(config.get("tracker")).get("perTracker")).get("ideaProjectKeys")
    if not has_idea_source(config) or not isinstance(key, str) or "-" not in key:
        return False
    project = key.strip().rsplit("-", 1)[0].upper()
    delivery = _dict(_dict(_dict(config.get("tracker")).get("resolved")).get("destination"))
    return (project in {str(k).upper() for k in keys}
            and project != str(delivery.get("projectKey") or "").upper())


def _idea_write_refusal(key: str, requested: Optional[str] = None) -> TrackerError:
    """`requested`: the key the caller asked for, when Jira now files the
    issue under `key` (it moved into a discovery project)."""
    named = f"{requested} (now {key})" if requested and requested != key else key
    return TrackerError(
        ErrorClass.CAPABILITY,
        f"{named} is an idea in a discovery project (tracker.perTracker."
        "ideaProjectKeys); flow-next never writes to an idea except its "
        f"delivery link (flowctl tracker idea link). Read {idea_reference()} "
        "for the idea-intake steps",
        subtype="idea_read_only",
        details={"capability": "idea_read_only", "reference": idea_reference()})


def moved_to_idea(config: dict, requested: str, raw) -> Optional[TrackerError]:
    """The refusal when the issue Jira returned is filed under an idea key."""
    current = raw.get("key") if isinstance(raw, dict) else None
    if isinstance(current, str) and is_idea_key(config, current):
        return _idea_write_refusal(current, requested)
    return None


def key_from_url(base: str, text: str) -> Optional[str]:
    """The issue key in a `/browse/KEY` URL, or a view URL's `selectedIssue=KEY`,
    on the configured site; None for anything else."""
    parsed = urlparse(text)
    if (parsed.scheme not in ("http", "https")
            or parsed.netloc.lower() != urlparse(base).netloc.lower()):
        return None
    selected = parse_qs(parsed.query).get("selectedIssue", [])
    if selected and _JIRA_ISSUE_KEY_RE.fullmatch(selected[0]):
        return selected[0]
    browse = re.search(r"/browse/([^/?#]+)/?$", parsed.path)
    if browse and _JIRA_ISSUE_KEY_RE.fullmatch(browse.group(1)):
        return browse.group(1)
    return None


def to_wire(body: str) -> Result:
    """Markdown -> the wiki markup a v2 text field stores (fn-253).

    A converter failure is a structured error: the unconverted Markdown is
    never sent in its place."""
    try:
        return markdown_to_wiki(body)
    except Exception as exc:  # noqa: BLE001 - surface, never send raw
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"jira wiki conversion failed: {exc}",
                            subtype="wiki_conversion")


def from_wire(body):
    """Decode a stored v2 body to Markdown; the single read-side decode."""
    if body is None:
        return None
    return wiki_to_markdown(body if isinstance(body, str) else str(body))


def _issue_out(raw: dict, *, parent_identity: str = "not_available") -> dict:
    fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    return {
        "id": str(raw.get("id")),
        "identifier": raw.get("key"),
        "title": fields.get("summary"),
        "body": from_wire(fields.get("description")),
        "url": None,
        "labels": list(fields.get("labels") or []),
        "status": (
            {"raw": fields["status"].get("name"),
             "type": (
                 fields["status"].get("statusCategory", {}).get("key")
                 if isinstance(fields["status"].get("statusCategory"), dict)
                 else None
             )}
            if isinstance(fields.get("status"), dict) else None
        ),
        "raw": raw,
        "parent_identity": parent_identity,
    }


def _comment_out(raw: dict, *, parent_identity: str) -> dict:
    return {"id": raw.get("id"), "body": from_wire(raw.get("body")),
            "url": None, "created_at": raw.get("created"),
            "raw": raw, "parent_identity": parent_identity}

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
    #
    # Display grammar accepts DC custom keys (underscores, >10 chars), e.g.
    # MY_LONG_PROJECT_KEY-7. UNVERIFIED on live Jira Data Center (Cloud cannot
    # reproduce custom keys - fn-140 R17); verified against prose only.
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    key = _jira_issue_key(locator["display"])
    if isinstance(key, TrackerError):
        return key
    # Every write validates its parent here first; an idea is read-only, even
    # for a spec linked to it before the idea source was configured.
    if op != "wire-read" and is_idea_key(config, key):
        return _idea_write_refusal(key)
    data = _jira(execute, op, "GET",
                 f"{base}/rest/api/2/issue/{quote(str(key), safe='')}"
                 f"?fields=summary,description,status,priority,labels,assignee,updated",
                 idempotent=True)
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "jira issue is not an object",
                            subtype="malformed_body")
    if locator["durable"] is None:  # a read by key alone learns the id here
        return data
    err = _check_durable("jira", locator, data)
    if err:
        return err
    # The key Jira files the issue under now decides: an issue moved into a
    # discovery project is an idea, whatever key the caller holds.
    return (moved_to_idea(config, key, data) if op != "wire-read" else None) or data


def _require_parent(config: dict, locator: dict, execute: Execute) -> Result:
    return parent_read(config, locator, execute, op="wire-parent-read")


def read(config: dict, locator: dict, execute: Execute) -> Result:
    if locator["durable"] is None:
        # Read by key or URL alone (parse_locator allows it for this verb).
        dest = _destination(config)
        if isinstance(dest, TrackerError):
            return dest
        base = _jira_base(config, dest)
        if isinstance(base, TrackerError):
            return base
        locator = {"durable": None,
                   "display": key_from_url(base, locator["display"]) or locator["display"]}
    parent = parent_read(config, locator, execute, op="wire-read")
    if isinstance(parent, TrackerError):
        return parent
    out = _issue_out(parent, parent_identity=(
        "validated" if locator["durable"] is not None else "not_available"))
    # An idea source is configured: an issue in a discovery project is an idea,
    # and the read names the reference that handles it (no extra request).
    if is_idea_key(config, out["identifier"] or locator["display"]):
        out["idea"] = {
            "reference": idea_reference(),
            "note": "This issue is an idea in a discovery project, not delivery "
                    "work. Read the reference before routing it.",
        }
    return out


def pr_link(config: dict, locator: dict, execute: Execute, *, url: str) -> Result:
    """Upsert a Jira remote link, falling back to a deduplicated URL comment."""
    parent = parent_read(config, locator, execute, op="wire-pr-link-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    endpoint = (
        f"{base}/rest/api/2/issue/"
        f"{quote(str(locator['durable']), safe='')}/remotelink"
    )
    linked = _jira(
        execute,
        "wire-pr-link",
        "POST",
        endpoint,
        body={
            "globalId": f"flow-next:pr:{url}",
            "object": {
                "url": url,
                "title": "Flow-Next pull request",
            },
        },
        idempotent=True,
    )
    if not isinstance(linked, TrackerError):
        return {
            "linked": True,
            "deduped": False,
            "kind": "remote-link",
            "url": url,
        }

    listed = comment_list(config, locator, execute)
    if isinstance(listed, TrackerError):
        return linked
    comments = listed.get("comments")
    if not isinstance(comments, list):
        return linked
    expected = f"Flow-Next PR: {url}"
    for comment in comments:
        body = comment.get("body") if isinstance(comment, dict) else None
        if isinstance(body, str) and body.strip() == expected:
            return {
                "linked": False,
                "deduped": True,
                "kind": "comment-fallback",
                "url": url,
                "comment": comment,
                "degraded": {
                    "capability": "remote-link",
                    "reason": linked.message,
                },
            }
    if listed.get("truncated"):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "jira PR-link fallback dedup scan truncated; refusing to post",
            subtype="dedup_truncated",
            details={"remote_link_error": linked.message},
        )
    added = comment_add(config, locator, execute, body=expected)
    if isinstance(added, TrackerError):
        return linked
    return {
        "linked": True,
        "deduped": False,
        "kind": "comment-fallback",
        "url": url,
        "comment": added,
        "degraded": {
            "capability": "remote-link",
            "reason": linked.message,
        },
    }


def update(config: dict, locator: dict, execute: Execute, *,
           title: Optional[str], body: Optional[str],
           parent: Optional[dict] = None) -> Result:
    # sync-body already read this parent inside its claimed transaction.
    if parent is None:
        parent = _require_parent(config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    identity_error = _check_durable("jira", locator, parent)
    if identity_error:
        return identity_error
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
        wire_body = to_wire(body)
        if isinstance(wire_body, TrackerError):
            return wire_body
        fields["description"] = wire_body
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
    wire_body = to_wire(body)
    if isinstance(wire_body, TrackerError):
        return wire_body
    data = _jira(execute, "wire-comment-add", "POST",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}/comment",
                 body={"body": wire_body})
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
    wire_body = to_wire(body)
    if isinstance(wire_body, TrackerError):
        return wire_body
    data = _jira(execute, "wire-comment-update", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}"
                 f"/comment/{quote(str(comment_id), safe='')}",
                 body={"body": wire_body})
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
        # Cloud assigns by accountId; DC/Server assigns by name. Select the
        # field from the PERSISTED deployment shape (perTracker.authScheme,
        # decided once at the discovery ceremony) - never from the shape of
        # the identifier itself, which misclassifies valid DC usernames like
        # `john-doe`. Absent authScheme means cloud-basic, matching how
        # credentials.resolve() treats every non-"bearer-pat" value.
        scheme = _dict(_dict(config.get("tracker")).get("perTracker")).get("authScheme")
        user = add[-1]
        assignee = {"name": user} if scheme == "bearer-pat" else {"accountId": user}
        applied = user
    else:
        # Remove-only: clear the single assignee ONLY when the current identity
        # matches a requested removal (accountId on Cloud; name/key on DC).
        # Otherwise preserve the unrelated assignee and no-op.
        current_ids = set()
        if prior:
            for k in ("accountId", "name", "key"):
                v = prior.get(k)
                if isinstance(v, str) and v:
                    current_ids.add(v)
        if not current_ids.intersection(remove):
            out = _issue_out(parent)
            out["degraded"] = {
                "kind": "assignee_remove_skipped",
                "requested": list(remove),
                "current": previous,
            }
            return out
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


def list_open(config: dict, execute: Execute, *, any_lane: bool = False) -> Result:
    ready_state = _ready_state(config)
    if ready_state is None and not any_lane:
        return {"issues": [], "truncated": False}
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    raw_key = dest.get("projectKey") or _dict(_dict(config.get("tracker")).get("perTracker")).get("projectKey")
    if not raw_key:
        return TrackerError(ErrorClass.UNRESOLVED, "jira projectKey is not resolved",
                            subtype="destination")
    # Sanitize before JQL interpolation. Grammar allows DC underscores / long
    # keys (^[A-Z][A-Z0-9_]+$). UNVERIFIED on live Jira Data Center (Cloud cannot
    # reproduce custom keys - fn-140 R17); verified against prose only.
    key = _jira_project_key(str(raw_key))
    if isinstance(key, TrackerError):
        return key
    if any_lane:
        jql = f"project = {key} AND statusCategory != Done"
    else:
        escaped_state = ready_state.replace("\\", "\\\\").replace('"', '\\"')
        jql = f'project = {key} AND status = "{escaped_state}"'

    collected: list = []
    truncated = False
    fields = ["summary", "description", "status", "priority", "labels", "updated"]
    version = "3" if str(dest.get("apiVersion")) == "3" else "2"
    scheme = _dict(_dict(config.get("tracker")).get("perTracker")).get("authScheme")
    # Cloud answers 410 Gone on GET /rest/api/2/search (measured 2026-11-15);
    # its cursor search serves v2 and v3. Data Center keeps the classic search.
    if version == "3" or scheme != "bearer-pat":
        next_page = None
        seen = set()
        for _ in range(_MAX_PAGES):
            body = {"jql": jql, "maxResults": _PAGE_SIZE, "fields": fields}
            if next_page is not None:
                body["nextPageToken"] = next_page
            data = _jira(execute, "wire-list-open", "POST",
                         f"{base}/rest/api/{version}/search/jql", body=body,
                         idempotent=True)
            if isinstance(data, TrackerError):
                return data
            if not isinstance(data, dict):
                return TrackerError(ErrorClass.TRANSPORT, "jira search is not an object",
                                    subtype="malformed_body")
            issues = data.get("issues") or []
            if not isinstance(issues, list):
                return TrackerError(ErrorClass.TRANSPORT,
                                    "jira search.issues is not a list",
                                    subtype="malformed_body")
            collected.extend(i for i in issues if isinstance(i, dict))
            if data.get("isLast") is not False:
                break
            token = data.get("nextPageToken")
            if not isinstance(token, str) or not token or token in seen:
                return TrackerError(ErrorClass.TRANSPORT,
                                    "jira search cursor made no progress",
                                    subtype="malformed_body")
            seen.add(token)
            next_page = token
        else:
            truncated = True
        return {"issues": [_issue_out(i, parent_identity="not_available")
                           for i in collected],
                "truncated": truncated}

    # Data Center / Server v2 retains classic offset pagination.
    start_at = 0
    for _ in range(_MAX_PAGES):
        qs = urlencode({"jql": jql, "startAt": start_at, "maxResults": _PAGE_SIZE,
                        "fields": ",".join(fields)})
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


def list_states(config: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    raw_key = dest.get("projectKey") or _dict(_dict(config.get("tracker")).get("perTracker")).get("projectKey")
    if not raw_key:
        return TrackerError(ErrorClass.UNRESOLVED, "jira projectKey is not resolved",
                            subtype="destination")
    key = _jira_project_key(str(raw_key))
    if isinstance(key, TrackerError):
        return key
    # Scoped to the resolved issue type, mirroring providers/jira.py
    # fetch_statuses: destination.statusIds is pinned to issueTypeId, so an
    # all-types flatten would let the documented liveness check validate a
    # status that never applied to the pinned type. NEVER "first entry":
    # without the resolved issue type a Task project would happily report
    # the first (e.g. Story) workflow's status ids.
    issue_type_id = dest.get("issueTypeId")
    if not issue_type_id:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "no resolved issueTypeId; resolve destination first "
                            "(statusIds is scoped to the pinned issue type)",
                            subtype="statusIds")
    # /rest/api/2 hardcoded: the statuses endpoint is stable on v2 for both
    # Cloud and DC; only list_open needs the v3 search fork.
    out = _jira(execute, "wire-list-states", "GET",
                f"{base}/rest/api/2/project/{quote(key, safe='')}/statuses",
                idempotent=True)
    if isinstance(out, TrackerError):
        return out
    if not isinstance(out, list):
        return TrackerError(ErrorClass.TRANSPORT,
                            "jira project statuses response is malformed",
                            subtype="malformed_body")
    malformed = TrackerError(ErrorClass.TRANSPORT,
                             "jira project statuses response is malformed",
                             subtype="malformed_body")
    entry = None
    for issue_type in out:
        # A shape-broken entry fails loudly - a quietly shrunken list
        # flagged complete:true is the exact failure `complete` guards.
        if not isinstance(issue_type, dict):
            return malformed
        if str(issue_type.get("id")) == str(issue_type_id):
            entry = issue_type
            break
    if entry is None:
        return TrackerError(ErrorClass.UNRESOLVED,
                            f"no status set for issue type {issue_type_id!r}; "
                            "resolve destination first", subtype="statusIds")
    statuses = entry.get("statuses")
    if not isinstance(statuses, list):
        return malformed
    states = []
    seen = set()
    for status in statuses:
        if not isinstance(status, dict) or not status.get("id"):
            return malformed
        sid = str(status["id"])
        if sid in seen:
            continue
        seen.add(sid)
        cat = status.get("statusCategory")
        states.append({
            "id": sid,
            "name": status.get("name"),
            "type": cat.get("key") if isinstance(cat, dict) else None,
        })
    return {"states": states, "complete": True}
