"""Wire verbs: locator-addressed tracker operations with no local state (fn-140.1).

Wire verbs take a locator `{durable, display}` (except `list-open`), touch no
config / receipt, and every WRITE validates the parent BEFORE mutating:

    1. resolve the display address → one parent read
    2. compare the returned durable id to `locator.durable`
    3. mismatch → `class: conflict`, and the mutation request is never issued

Response-side validation is a cheaper second check, applied ONLY where the
provider response actually carries parent identity. Several comment responses
do not - those are marked `parent_identity: "not_available"`, never faked.

Parent-identity availability (measured; do not invent checks against absent
fields):

  github  issue responses: YES (`node_id` / GraphQL `id`)
          comment responses: NO (REST comment has `issue_url`, not parent node_id)
  gitlab  issue responses: YES (`id` = global issue id)
          note responses: YES (`noteable_id` = global issue id)
  linear  issue responses: YES (`id` UUID)
          comment responses: YES when the selection set includes `issue { id }`
  jira    issue responses: YES (`id`)
          comment responses: NO (comment object carries no parent issue id)

Transport routing matches spec A: github/gitlab via CLI argv (`gh api` /
`glab api`), linear via GraphQL HTTP, jira via REST HTTP. Every request goes
through the injected `execute` callable.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional, Union
from urllib.parse import quote, urlencode

from . import envelope
from .executor import execute as default_execute
from .types import ErrorClass, Request, Response, TrackerError

#: Verbs this module owns. `attach` / `attach-get` are task .4.
WIRE_VERBS = (
    "read", "update", "comment-add", "comment-list", "comment-update",
    "comment-delete", "label", "assign", "list-open",
)
WRITE_VERBS = frozenset({
    "update", "comment-add", "comment-update", "comment-delete", "label", "assign",
})
#: Verbs that require a parent locator (comment-update/delete always; others too
#: except list-open). Kept explicit so the CLI and the dispatcher share one set.
LOCATOR_VERBS = frozenset(v for v in WIRE_VERBS if v != "list-open")

_ACTIVE = frozenset({"github", "gitlab", "linear", "jira"})
LINEAR_GQL = "https://api.linear.app/graphql"

Result = Union[dict, TrackerError]
Execute = Callable[[Request], Union[Response, TrackerError]]


# ---------------------------------------------------------------------------
# Config / locator
# ---------------------------------------------------------------------------

def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _tracker_type(config: dict) -> Optional[str]:
    t = _dict(config.get("tracker")).get("type")
    return t if t in _ACTIVE else None


def _destination(config: dict) -> Union[dict, TrackerError]:
    dest = _dict(_dict(_dict(config.get("tracker")).get("resolved")).get("destination"))
    if not dest:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "no resolved destination; run `flowctl tracker resolve` first",
                            subtype="destination")
    return dest


def parse_locator(raw: Any) -> Union[dict, TrackerError]:
    """Accept a dict or a JSON string → `{durable, display}` both non-empty str."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError) as exc:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                f"locator is not valid JSON: {exc}", subtype="locator")
    if not isinstance(raw, dict):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "locator must be an object {durable, display}",
                            subtype="locator")
    durable = raw.get("durable")
    display = raw.get("display")
    if not isinstance(durable, str) or not durable.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "locator.durable must be a non-empty string",
                            subtype="locator")
    if not isinstance(display, str) or not display.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "locator.display must be a non-empty string",
                            subtype="locator")
    return {"durable": durable.strip(), "display": display.strip()}


def _github_number(display: str) -> Union[int, TrackerError]:
    s = display.strip().lstrip("#")
    if not s.isdigit():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"github display must be #N, got {display!r}",
                            subtype="display")
    return int(s)


def _gitlab_iid(display: str) -> Union[int, TrackerError]:
    part = display.rsplit("#", 1)[-1].strip()
    if not part.isdigit():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"gitlab display must be <project>#<iid>, got {display!r}",
                            subtype="display")
    return int(part)


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------

def _json_loads(resp: Response, *, what: str) -> Union[Any, TrackerError]:
    try:
        return json.loads(resp.body or b"null")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"malformed {what}: {exc}", subtype="malformed_body")


def _cli_argv(provider: str, config: dict, method: str, endpoint: str,
              *, body: Optional[bytes] = None) -> list:
    if provider == "github":
        argv = ["gh", "api"]
    else:
        argv = ["glab", "api"]
        host = _dict(_dict(config.get("tracker")).get("perTracker")).get("host")
        if host:
            argv += ["--hostname", str(host)]
    if method.upper() != "GET":
        argv += ["--method", method.upper()]
    argv.append(endpoint)
    if body is not None:
        argv += ["--input", "-"]
    return argv


def _cli(execute: Execute, provider: str, config: dict, op: str, method: str,
         endpoint: str, *, body: Optional[dict] = None,
         idempotent: bool = False) -> Union[Any, TrackerError]:
    raw = None if body is None else json.dumps(body).encode()
    result = execute(Request(
        provider=provider, op=op, method=method.upper(),
        url_or_argv=_cli_argv(provider, config, method, endpoint, body=raw),
        body=raw, idempotent=idempotent,
    ))
    if isinstance(result, TrackerError):
        return result
    # DELETE often returns empty body (204).
    if not (result.body or b"").strip():
        return None
    return _json_loads(result, what=f"{provider} {op}")


def _gql(execute: Execute, op: str, query: str, variables: dict, *,
         idempotent: bool = False) -> Union[dict, TrackerError]:
    result = execute(Request(
        provider="linear", op=op, method="POST", url_or_argv=LINEAR_GQL,
        headers={"Content-Type": "application/json"},
        body=json.dumps({"query": query, "variables": variables}).encode(),
        idempotent=idempotent,
    ))
    if isinstance(result, TrackerError):
        return result
    payload = _json_loads(result, what="linear graphql")
    if isinstance(payload, TrackerError):
        return payload
    if not isinstance(payload, dict):
        return TrackerError(ErrorClass.TRANSPORT, "GraphQL payload is not an object",
                            subtype="malformed_body")
    data = payload.get("data")
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "GraphQL response carries no data",
                            subtype="malformed_body")
    return data


def _jira_base(config: dict, dest: dict) -> Union[str, TrackerError]:
    # Prefer the resolved pin; fall back to the provider helper's env/perTracker
    # precedence so a runtime JIRA_BASE_URL override still works.
    from .providers import jira as jira_mod  # noqa: PLC0415 - keep providers lazy
    base = dest.get("baseUrl") or jira_mod.base_url(config)
    if not base:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "jira baseUrl is not resolved", subtype="destination")
    return str(base).rstrip("/")


def _jira(execute: Execute, op: str, method: str, url: str, *,
          body: Optional[dict] = None, idempotent: bool = False
          ) -> Union[Any, TrackerError]:
    raw = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"} if raw else {
        "Accept": "application/json",
    }
    result = execute(Request(
        provider="jira", op=op, method=method.upper(), url_or_argv=url,
        headers=headers, body=raw, idempotent=idempotent,
    ))
    if isinstance(result, TrackerError):
        return result
    if not (result.body or b"").strip():
        return None
    return _json_loads(result, what=f"jira {op}")


# ---------------------------------------------------------------------------
# Pagination (no silent caps: drain up to _MAX_PAGES, then say so)
# ---------------------------------------------------------------------------

_PAGE_SIZE = 100
_MAX_PAGES = 20  # 2000 items; a ceiling with an honest `truncated` flag, not a silent cap


def _rest_drain(fetch_page: Callable[[int], Union[list, TrackerError]]
                ) -> Union[tuple, TrackerError]:
    """Drain page=1.. until a short page. Returns (items, truncated)."""
    items: list = []
    for page in range(1, _MAX_PAGES + 1):
        data = fetch_page(page)
        if isinstance(data, TrackerError):
            return data
        if not isinstance(data, list):
            return TrackerError(ErrorClass.TRANSPORT, "page is not a list",
                                subtype="malformed_body")
        items.extend(data)
        if len(data) < _PAGE_SIZE:
            return items, False
    return items, True


def _gql_connection_drain(execute: Execute, op: str, query: str,
                          base_vars: dict, pluck: Callable[[dict], Union[dict, TrackerError]]
                          ) -> Union[tuple, TrackerError]:
    """Drain one GraphQL connection ({nodes, pageInfo}). Returns (nodes, truncated)."""
    nodes: list = []
    cursor = None
    seen: set = set()
    for _ in range(_MAX_PAGES):
        data = _gql(execute, op, query, {**base_vars, "after": cursor}, idempotent=True)
        if isinstance(data, TrackerError):
            return data
        conn = pluck(data)
        if isinstance(conn, TrackerError):
            return conn
        page_nodes = conn.get("nodes")
        if not isinstance(page_nodes, list):
            return TrackerError(ErrorClass.TRANSPORT, "connection carries no nodes",
                                subtype="malformed_body")
        nodes.extend(n for n in page_nodes if isinstance(n, dict))
        info = conn.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return nodes, False
        cursor = info.get("endCursor")
        if not cursor or cursor in seen:
            return TrackerError(ErrorClass.TRANSPORT,
                                "pagination made no progress", subtype="malformed_body")
        seen.add(cursor)
    return nodes, True


# ---------------------------------------------------------------------------
# Durable extraction + conflict
# ---------------------------------------------------------------------------

def _conflict(expected: str, got: Any) -> TrackerError:
    return TrackerError(
        ErrorClass.CONFLICT,
        f"locator.durable {expected!r} does not match parent durable {got!r}",
        subtype="durable_mismatch",
        details={"normalized": "durable", "candidates": [
            {"durable": expected, "role": "locator"},
            {"durable": got, "role": "parent"},
        ]},
    )


def _github_durable(issue: dict) -> Optional[str]:
    # REST via `gh api` returns `node_id`; `gh issue view --json id` also uses
    # the node id under `id`. Accept either.
    for key in ("node_id", "id"):
        v = issue.get(key)
        if isinstance(v, str) and v.startswith(("I_", "MDE")):
            return v
        if isinstance(v, str) and key == "node_id" and v:
            return v
    # Numeric `id` is the DB id, NOT the durable key - never treat it as durable.
    v = issue.get("node_id")
    return v if isinstance(v, str) and v else None


def _gitlab_durable(issue: dict) -> Optional[str]:
    v = issue.get("id")
    return str(v) if isinstance(v, int) or (isinstance(v, str) and v.isdigit()) else None


def _linear_durable(issue: dict) -> Optional[str]:
    v = issue.get("id")
    return v if isinstance(v, str) and v else None


def _jira_durable(issue: dict) -> Optional[str]:
    v = issue.get("id")
    return str(v) if v is not None and str(v) else None


_DURABLE_OF = {
    "github": _github_durable,
    "gitlab": _gitlab_durable,
    "linear": _linear_durable,
    "jira": _jira_durable,
}


def _check_durable(provider: str, locator: dict, entity: dict
                   ) -> Optional[TrackerError]:
    got = _DURABLE_OF[provider](entity)
    if got is None:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"{provider} response carries no durable id",
                            subtype="malformed_body")
    if str(got) != str(locator["durable"]):
        return _conflict(locator["durable"], got)
    return None


# ---------------------------------------------------------------------------
# Parent read (the load-bearing write gate)
# ---------------------------------------------------------------------------

def _gh_repo(dest: dict) -> Union[str, TrackerError]:
    owner, repo = dest.get("owner"), dest.get("repo")
    if not isinstance(owner, str) or not isinstance(repo, str):
        return TrackerError(ErrorClass.UNRESOLVED,
                            "github destination missing owner/repo",
                            subtype="destination")
    return f"{owner}/{repo}"


def _gl_project(dest: dict) -> Union[int, TrackerError]:
    pid = dest.get("projectId")
    if not isinstance(pid, int):
        return TrackerError(ErrorClass.UNRESOLVED,
                            "gitlab destination missing numeric projectId",
                            subtype="destination")
    return pid


def parent_read(provider: str, config: dict, locator: dict, execute: Execute, *,
                op: str = "wire-parent-read") -> Union[dict, TrackerError]:
    """One parent fetch addressed by display. Returns the raw provider issue
    object (already durable-checked against the locator)."""
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
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

    if provider == "gitlab":
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

    if provider == "linear":
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


def _require_parent(provider: str, config: dict, locator: dict,
                    execute: Execute) -> Union[dict, TrackerError]:
    """Write-verb gate: parent read + durable check. On conflict the caller
    must not issue any further execute() call."""
    return parent_read(provider, config, locator, execute, op="wire-parent-read")


# ---------------------------------------------------------------------------
# Normalized success payloads
# ---------------------------------------------------------------------------

def _issue_out(provider: str, raw: dict, *, parent_identity: str = "validated") -> dict:
    if provider == "github":
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
    if provider == "gitlab":
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
    if provider == "linear":
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
    # jira
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


def _comment_out(provider: str, raw: dict, *, parent_identity: str) -> dict:
    if provider == "github":
        return {"id": raw.get("id"), "body": raw.get("body"),
                "url": raw.get("html_url") or raw.get("url"),
                "raw": raw, "parent_identity": parent_identity}
    if provider == "gitlab":
        return {"id": raw.get("id"), "body": raw.get("body"),
                "url": raw.get("web_url"),
                "raw": raw, "parent_identity": parent_identity}
    if provider == "linear":
        return {"id": raw.get("id"), "body": raw.get("body"),
                "url": raw.get("url"),
                "raw": raw, "parent_identity": parent_identity}
    return {"id": raw.get("id"), "body": raw.get("body"),
            "url": None, "raw": raw, "parent_identity": parent_identity}


# ---------------------------------------------------------------------------
# Per-verb: read
# ---------------------------------------------------------------------------

def _read(provider: str, config: dict, locator: dict, execute: Execute) -> Result:
    # Read-only: validate on response alone (parent_read already checks durable).
    parent = parent_read(provider, config, locator, execute, op="wire-read")
    if isinstance(parent, TrackerError):
        return parent
    return _issue_out(provider, parent, parent_identity="validated")


# ---------------------------------------------------------------------------
# Per-verb: update
# ---------------------------------------------------------------------------

def _update(provider: str, config: dict, locator: dict, execute: Execute, *,
            title: Optional[str], body: Optional[str]) -> Result:
    parent = _require_parent(provider, config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
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
        return _issue_out("github", data)

    if provider == "gitlab":
        iid = _gitlab_iid(locator["display"])
        pid = _gl_project(dest)
        if isinstance(iid, TrackerError):
            return iid
        if isinstance(pid, TrackerError):
            return pid
        payload = {}
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
        return _issue_out("gitlab", data)

    if provider == "linear":
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
        issue = ((data.get("issueUpdate") or {}).get("issue")
                 if isinstance(data.get("issueUpdate"), dict) else None)
        if not isinstance(issue, dict):
            return TrackerError(ErrorClass.TRANSPORT, "linear update returned no issue",
                                subtype="malformed_body")
        err = _check_durable("linear", locator, issue)
        if err:
            return err
        return _issue_out("linear", issue)

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
    return _issue_out("jira", parent, parent_identity="validated")


# ---------------------------------------------------------------------------
# Per-verb: comments
# ---------------------------------------------------------------------------

def _comment_add(provider: str, config: dict, locator: dict, execute: Execute, *,
                 body: str) -> Result:
    parent = _require_parent(provider, config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
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
        return _comment_out("github", data, parent_identity="not_available")

    if provider == "gitlab":
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
        return _comment_out("gitlab", data, parent_identity=identity)

    if provider == "linear":
        data = _gql(execute, "wire-comment-add",
                    "mutation($input: CommentCreateInput!) { "
                    "commentCreate(input: $input) { success "
                    "comment { id body url issue { id } } } }",
                    {"input": {"issueId": locator["durable"], "body": body}})
        if isinstance(data, TrackerError):
            return data
        comment = ((data.get("commentCreate") or {}).get("comment")
                   if isinstance(data.get("commentCreate"), dict) else None)
        if not isinstance(comment, dict):
            return TrackerError(ErrorClass.TRANSPORT, "linear comment-add returned no comment",
                                subtype="malformed_body")
        issue = comment.get("issue") if isinstance(comment.get("issue"), dict) else None
        if issue is not None:
            err = _check_durable("linear", locator, issue)
            if err:
                return err
            return _comment_out("linear", comment, parent_identity="validated")
        return _comment_out("linear", comment, parent_identity="not_available")

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
    return _comment_out("jira", data, parent_identity="not_available")


def _comment_list(provider: str, config: dict, locator: dict,
                  execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
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
        return {"comments": [_comment_out("github", c, parent_identity="not_available")
                             for c in data if isinstance(c, dict)],
                "truncated": truncated,
                "parent_identity": "not_available"}

    if provider == "gitlab":
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
            out.append(_comment_out("gitlab", n, parent_identity=identity))
        return {"comments": out, "truncated": truncated, "parent_identity": "validated"}

    if provider == "linear":
        return _linear_comment_list(config, locator, execute)

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
    return {"comments": [_comment_out("jira", c, parent_identity="not_available")
                         for c in collected],
            "truncated": truncated, "parent_identity": "not_available"}


def _linear_comment_list(config: dict, locator: dict, execute: Execute) -> Result:
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
    return {"comments": [_comment_out("linear", c, parent_identity="validated")
                         for c in nodes],
            "truncated": truncated, "parent_identity": "validated"}


def _comment_update(provider: str, config: dict, locator: dict, execute: Execute, *,
                    comment_id: str, body: str) -> Result:
    parent = _require_parent(provider, config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
        repo = _gh_repo(dest)
        if isinstance(repo, TrackerError):
            return repo
        # Path takes the comment id alone, but the contract still requires the
        # parent locator (pre-mutation gate above). Response has no parent node_id.
        data = _cli(execute, "github", config, "wire-comment-update", "PATCH",
                    f"repos/{repo}/issues/comments/{comment_id}", body={"body": body})
        if isinstance(data, TrackerError):
            return data
        if not isinstance(data, dict):
            return TrackerError(ErrorClass.TRANSPORT, "github comment-update returned no object",
                                subtype="malformed_body")
        return _comment_out("github", data, parent_identity="not_available")

    if provider == "gitlab":
        iid = _gitlab_iid(locator["display"])
        pid = _gl_project(dest)
        if isinstance(iid, TrackerError):
            return iid
        if isinstance(pid, TrackerError):
            return pid
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
        return _comment_out("gitlab", data, parent_identity=identity)

    if provider == "linear":
        data = _gql(execute, "wire-comment-update",
                    "mutation($id: String!, $input: CommentUpdateInput!) { "
                    "commentUpdate(id: $id, input: $input) { success "
                    "comment { id body url issue { id } } } }",
                    {"id": comment_id, "input": {"body": body}})
        if isinstance(data, TrackerError):
            return data
        comment = ((data.get("commentUpdate") or {}).get("comment")
                   if isinstance(data.get("commentUpdate"), dict) else None)
        if not isinstance(comment, dict):
            return TrackerError(ErrorClass.TRANSPORT, "linear comment-update returned no comment",
                                subtype="malformed_body")
        issue = comment.get("issue") if isinstance(comment.get("issue"), dict) else None
        if issue is not None:
            err = _check_durable("linear", locator, issue)
            if err:
                return err
            return _comment_out("linear", comment, parent_identity="validated")
        return _comment_out("linear", comment, parent_identity="not_available")

    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    data = _jira(execute, "wire-comment-update", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}"
                 f"/comment/{quote(str(comment_id), safe='')}",
                 body={"body": body})
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "jira comment-update returned no object",
                            subtype="malformed_body")
    return _comment_out("jira", data, parent_identity="not_available")


def _comment_delete(provider: str, config: dict, locator: dict, execute: Execute, *,
                    comment_id: str) -> Result:
    parent = _require_parent(provider, config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
        repo = _gh_repo(dest)
        if isinstance(repo, TrackerError):
            return repo
        data = _cli(execute, "github", config, "wire-comment-delete", "DELETE",
                    f"repos/{repo}/issues/comments/{comment_id}")
        if isinstance(data, TrackerError):
            return data
        return {"deleted": comment_id, "parent_identity": "not_available"}

    if provider == "gitlab":
        iid = _gitlab_iid(locator["display"])
        pid = _gl_project(dest)
        if isinstance(iid, TrackerError):
            return iid
        if isinstance(pid, TrackerError):
            return pid
        data = _cli(execute, "gitlab", config, "wire-comment-delete", "DELETE",
                    f"projects/{pid}/issues/{iid}/notes/{comment_id}")
        if isinstance(data, TrackerError):
            return data
        return {"deleted": comment_id, "parent_identity": "not_available"}

    if provider == "linear":
        data = _gql(execute, "wire-comment-delete",
                    "mutation($id: String!) { commentDelete(id: $id) { success } }",
                    {"id": comment_id})
        if isinstance(data, TrackerError):
            return data
        return {"deleted": comment_id, "parent_identity": "not_available"}

    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    data = _jira(execute, "wire-comment-delete", "DELETE",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}"
                 f"/comment/{quote(str(comment_id), safe='')}")
    if isinstance(data, TrackerError):
        return data
    return {"deleted": comment_id, "parent_identity": "not_available"}


# ---------------------------------------------------------------------------
# Per-verb: label / assign
# ---------------------------------------------------------------------------

def _label(provider: str, config: dict, locator: dict, execute: Execute, *,
           add: list[str], remove: list[str]) -> Result:
    parent = _require_parent(provider, config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    if not add and not remove:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "label requires --add and/or --remove", subtype="label")

    if provider == "github":
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
        refreshed = parent_read(provider, config, locator, execute, op="wire-label-readback")
        if isinstance(refreshed, TrackerError):
            return refreshed
        return _issue_out("github", refreshed)

    if provider == "gitlab":
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
        return _issue_out("gitlab", data)

    if provider == "linear":
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
        issue = ((data.get("issueUpdate") or {}).get("issue")
                 if isinstance(data.get("issueUpdate"), dict) else None)
        if not isinstance(issue, dict):
            return TrackerError(ErrorClass.TRANSPORT, "linear label returned no issue",
                                subtype="malformed_body")
        err = _check_durable("linear", locator, issue)
        if err:
            return err
        return _issue_out("linear", issue)

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
    return _issue_out("jira", parent)


def _assign(provider: str, config: dict, locator: dict, execute: Execute, *,
            add: list[str], remove: list[str]) -> Result:
    parent = _require_parent(provider, config, locator, execute)
    if isinstance(parent, TrackerError):
        return parent
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    if not add and not remove:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "assign requires --add and/or --remove", subtype="assign")

    if provider == "github":
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
        refreshed = parent_read(provider, config, locator, execute, op="wire-assign-readback")
        if isinstance(refreshed, TrackerError):
            return refreshed
        return _issue_out("github", refreshed)

    if provider == "gitlab":
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
        return _issue_out("gitlab", data)

    if provider == "linear":
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
        issue = ((data.get("issueUpdate") or {}).get("issue")
                 if isinstance(data.get("issueUpdate"), dict) else None)
        if not isinstance(issue, dict):
            return TrackerError(ErrorClass.TRANSPORT, "linear assign returned no issue",
                                subtype="malformed_body")
        err = _check_durable("linear", locator, issue)
        if err:
            return err
        return _issue_out("linear", issue)

    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    # Single-assignee: --add sets accountId/name; --remove with no add clears.
    if add:
        # Cloud prefers accountId; DC may use name. Pass through as accountId when
        # it looks like one, else as name.
        user = add[-1]
        assignee = {"accountId": user} if len(user) > 20 or "-" in user else {"name": user}
    else:
        assignee = None
    data = _jira(execute, "wire-assign", "PUT",
                 f"{base}/rest/api/2/issue/{quote(str(locator['durable']), safe='')}",
                 body={"fields": {"assignee": assignee}})
    if isinstance(data, TrackerError):
        return data
    fields = parent.get("fields") if isinstance(parent.get("fields"), dict) else {}
    parent["fields"] = {**fields, "assignee": assignee}
    return _issue_out("jira", parent)


# ---------------------------------------------------------------------------
# Per-verb: list-open (locator-free)
# ---------------------------------------------------------------------------

def _list_open(provider: str, config: dict, execute: Execute) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
        repo = _gh_repo(dest)
        if isinstance(repo, TrackerError):
            return repo
        drained = _rest_drain(lambda page: _cli(
            execute, "github", config, "wire-list-open", "GET",
            f"repos/{repo}/issues?state=open&per_page={_PAGE_SIZE}&page={page}",
            idempotent=True))
        if isinstance(drained, TrackerError):
            return drained
        data, truncated = drained
        # MEASURED: GET /issues returns pull requests too - filter on pull_request.
        issues = [i for i in data if isinstance(i, dict) and "pull_request" not in i]
        return {"issues": [_issue_out("github", i, parent_identity="not_available")
                           for i in issues],
                "truncated": truncated}

    if provider == "gitlab":
        pid = _gl_project(dest)
        if isinstance(pid, TrackerError):
            return pid
        # GitLab states are opened/closed (not open/closed).
        drained = _rest_drain(lambda page: _cli(
            execute, "gitlab", config, "wire-list-open", "GET",
            f"projects/{pid}/issues?state=opened&per_page={_PAGE_SIZE}&page={page}",
            idempotent=True))
        if isinstance(drained, TrackerError):
            return drained
        data, truncated = drained
        return {"issues": [_issue_out("gitlab", i, parent_identity="not_available")
                           for i in data if isinstance(i, dict)],
                "truncated": truncated}

    if provider == "linear":
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
        return {"issues": [_issue_out("linear", i, parent_identity="not_available")
                           for i in nodes],
                "truncated": truncated}

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
    return {"issues": [_issue_out("jira", i, parent_identity="not_available")
                       for i in collected],
            "truncated": truncated}


# ---------------------------------------------------------------------------
# Dispatch + CLI entry
# ---------------------------------------------------------------------------

def dispatch(verb: str, config: dict, *, locator: Any = None,
             title: Optional[str] = None, body: Optional[str] = None,
             comment_id: Optional[str] = None,
             add: Optional[list] = None, remove: Optional[list] = None,
             execute: Execute = default_execute) -> Result:
    """Run one wire verb. Returns data dict or TrackerError — never raises."""
    if verb not in WIRE_VERBS:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unknown wire verb {verb!r}", subtype="verb")
    provider = _tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    add = list(add or [])
    remove = list(remove or [])

    parsed: Optional[dict] = None
    if verb in LOCATOR_VERBS:
        parsed_or_err = parse_locator(locator)
        if isinstance(parsed_or_err, TrackerError):
            return parsed_or_err
        parsed = parsed_or_err

    if verb in ("comment-update", "comment-delete"):
        if not comment_id:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                f"{verb} requires <comment-id> and the parent locator",
                                subtype="comment_id")
        if parsed is None:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                f"{verb} requires the parent locator",
                                subtype="locator")

    if verb == "read":
        return _read(provider, config, parsed, execute)  # type: ignore[arg-type]
    if verb == "update":
        return _update(provider, config, parsed, execute, title=title, body=body)  # type: ignore[arg-type]
    if verb == "comment-add":
        if body is None:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                "comment-add requires --body-file", subtype="body")
        return _comment_add(provider, config, parsed, execute, body=body)  # type: ignore[arg-type]
    if verb == "comment-list":
        return _comment_list(provider, config, parsed, execute)  # type: ignore[arg-type]
    if verb == "comment-update":
        if body is None:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                "comment-update requires --body-file", subtype="body")
        return _comment_update(provider, config, parsed, execute,  # type: ignore[arg-type]
                               comment_id=str(comment_id), body=body)
    if verb == "comment-delete":
        return _comment_delete(provider, config, parsed, execute,  # type: ignore[arg-type]
                               comment_id=str(comment_id))
    if verb == "label":
        return _label(provider, config, parsed, execute, add=add, remove=remove)  # type: ignore[arg-type]
    if verb == "assign":
        return _assign(provider, config, parsed, execute, add=add, remove=remove)  # type: ignore[arg-type]
    if verb == "list-open":
        return _list_open(provider, config, execute)
    return TrackerError(ErrorClass.INVALID_INPUT, f"unhandled verb {verb!r}", subtype="verb")


def _read_config(flow_dir) -> dict:
    from pathlib import Path
    try:
        data = json.loads((Path(flow_dir) / "config.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def run(flow_dir, verb: str, *, locator: Any = None, title: Optional[str] = None,
        body_file: Optional[str] = None, comment_id: Optional[str] = None,
        add: Optional[list] = None, remove: Optional[list] = None,
        execute: Execute = default_execute) -> tuple[str, int]:
    """CLI entry: return (stdout payload, exit code) — the single result envelope."""
    config = _read_config(flow_dir)
    if _tracker_type(config) is None and _dict(config.get("tracker")).get("type") not in _ACTIVE:
        # Distinguish malformed vs inactive: a missing/off type is inactive.
        t = _dict(config.get("tracker")).get("type")
        if t is not None and t not in _ACTIVE:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown tracker type {t!r}", subtype="provider"))
        return envelope.inactive()

    body = None
    if body_file is not None:
        from pathlib import Path
        try:
            body = Path(body_file).read_text(encoding="utf-8")
        except OSError as exc:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"cannot read --body-file: {exc}",
                subtype="body_file"))

    # Bind transport policy for the real executor; injected fakes pass through.
    from .resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    out = dispatch(verb, config, locator=locator, title=title, body=body,
                   comment_id=comment_id, add=add, remove=remove, execute=ex)
    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
