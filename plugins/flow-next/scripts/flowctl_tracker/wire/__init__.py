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

Per-provider verb bodies live in `wire/{github,gitlab,linear,jira}.py`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional, Union

from .. import envelope
from ..executor import execute as default_execute
from ..types import ErrorClass, Request, Response, TrackerError

#: Jira project / issue-key grammars from jira.md (listOpenIssues JQL safety).
#: Underscores and keys longer than Cloud's 10-char alnum cap are intentional:
#: Data Center admins can configure them. Cloud cannot reproduce that shape.
#: UNVERIFIED on live Jira Data Center (Cloud cannot reproduce custom keys - fn-140 R17); verified against prose only.
_JIRA_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_JIRA_ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-[1-9][0-9]*$")

#: Verbs this module owns. `attach` / `attach-get` delegate to attach/ (fn-140.4).
WIRE_VERBS = (
    "read", "update", "comment-add", "comment-list", "comment-update",
    "comment-delete", "label", "assign", "list-open", "attach", "attach-get",
)
WRITE_VERBS = frozenset({
    "update", "comment-add", "comment-update", "comment-delete", "label", "assign",
    "attach",
})
#: Verbs that require a parent locator. attach-get and list-open are context-free.
LOCATOR_VERBS = frozenset(v for v in WIRE_VERBS if v not in ("list-open", "attach-get"))

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


def _jira_issue_key(display: str) -> Union[str, TrackerError]:
    """Parse a Jira issue display key (PROJ-1 or DC custom MY_LONG_PROJECT_KEY-7).

    UNVERIFIED on live Jira Data Center (Cloud cannot reproduce custom keys - fn-140 R17); verified against prose only.
    """
    s = (display or "").strip()
    if not _JIRA_ISSUE_KEY_RE.fullmatch(s):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"jira display must be KEY-N (A-Z / digits / underscore), got {display!r}",
            subtype="display",
        )
    return s


def _jira_project_key(key: str) -> Union[str, TrackerError]:
    """Validate a Jira projectKey before JQL interpolation (injection-safe).

    UNVERIFIED on live Jira Data Center (Cloud cannot reproduce custom keys - fn-140 R17); verified against prose only.
    """
    s = (key or "").strip() if isinstance(key, str) else ""
    if not _JIRA_PROJECT_KEY_RE.fullmatch(s):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"jira projectKey {key!r} is not a Jira key (expected ^[A-Z][A-Z0-9_]+$)",
            subtype="project_key",
        )
    return s


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
    from ..providers import jira as jira_mod  # noqa: PLC0415 - keep providers lazy
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


def _comment_parent_mismatch(comment_id: str, detail: str) -> TrackerError:
    return TrackerError(
        ErrorClass.CONFLICT,
        f"comment {comment_id!r} does not belong to locator parent ({detail})",
        subtype="comment_parent_mismatch",
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


# Provider modules imported after helpers so `from . import _cli` works mid-load.
from . import github, gitlab, jira, linear  # noqa: E402

_PROVIDERS = {
    "github": github,
    "gitlab": gitlab,
    "linear": linear,
    "jira": jira,
}


def parent_read(provider: str, config: dict, locator: dict, execute: Execute, *,
                op: str = "wire-parent-read") -> Union[dict, TrackerError]:
    """One parent fetch addressed by display. Returns the raw provider issue
    object (already durable-checked against the locator)."""
    mod = _PROVIDERS.get(provider)
    if mod is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    return mod.parent_read(config, locator, execute, op=op)


# ---------------------------------------------------------------------------
# Dispatch + CLI entry
# ---------------------------------------------------------------------------

def dispatch(verb: str, config: dict, *, locator: Any = None,
             title: Optional[str] = None, body: Optional[str] = None,
             comment_id: Optional[str] = None,
             add: Optional[list] = None, remove: Optional[list] = None,
             file_path: Optional[str] = None,
             attachment_id: Optional[str] = None,
             out_path: Optional[str] = None,
             execute: Execute = default_execute) -> Result:
    """Run one wire verb. Returns data dict or TrackerError — never raises."""
    if verb not in WIRE_VERBS:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unknown wire verb {verb!r}", subtype="verb")
    provider = _tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    # attach / attach-get live in the attach package (capability gates, R9).
    if verb in ("attach", "attach-get"):
        from .. import attach as attach_mod  # noqa: PLC0415
        if verb == "attach":
            if not file_path:
                return TrackerError(ErrorClass.INVALID_INPUT,
                                    "attach requires --file", subtype="file")
            return attach_mod.attach(config, locator, file_path=file_path,
                                     execute=execute)
        return attach_mod.attach_get(config, attachment_id=attachment_id or "",
                                     out_path=out_path or "", execute=execute)

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

    mod = _PROVIDERS[provider]
    if verb == "read":
        return mod.read(config, parsed, execute)  # type: ignore[arg-type]
    if verb == "update":
        return mod.update(config, parsed, execute, title=title, body=body)  # type: ignore[arg-type]
    if verb == "comment-add":
        if body is None:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                "comment-add requires --body-file", subtype="body")
        return mod.comment_add(config, parsed, execute, body=body)  # type: ignore[arg-type]
    if verb == "comment-list":
        return mod.comment_list(config, parsed, execute)  # type: ignore[arg-type]
    if verb == "comment-update":
        if body is None:
            return TrackerError(ErrorClass.INVALID_INPUT,
                                "comment-update requires --body-file", subtype="body")
        return mod.comment_update(config, parsed, execute,  # type: ignore[arg-type]
                                  comment_id=str(comment_id), body=body)
    if verb == "comment-delete":
        return mod.comment_delete(config, parsed, execute,  # type: ignore[arg-type]
                                  comment_id=str(comment_id))
    if verb == "label":
        return mod.label(config, parsed, execute, add=add, remove=remove)  # type: ignore[arg-type]
    if verb == "assign":
        return mod.assign(config, parsed, execute, add=add, remove=remove)  # type: ignore[arg-type]
    if verb == "list-open":
        return mod.list_open(config, execute)
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
        file_path: Optional[str] = None, attachment_id: Optional[str] = None,
        out_path: Optional[str] = None,
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
        except (OSError, UnicodeDecodeError) as exc:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"cannot read --body-file: {exc}",
                subtype="body_file"))

    # Bind transport policy for the real executor; injected fakes pass through.
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    out = dispatch(verb, config, locator=locator, title=title, body=body,
                   comment_id=comment_id, add=add, remove=remove,
                   file_path=file_path, attachment_id=attachment_id,
                   out_path=out_path, execute=ex)
    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
