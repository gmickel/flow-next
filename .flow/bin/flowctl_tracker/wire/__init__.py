"""Wire verbs: locator-addressed tracker operations (fn-140.1).

Wire verbs take a locator `{durable, display}` (except `list-open`), touch no
config / receipt, and every WRITE validates the parent BEFORE mutating.
`question` additionally uses one transient local claim to serialize its
list-then-add dedup transaction; the claim is always released and is not a
receipt.

Every write validates the parent before mutating:

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

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union
from urllib.parse import urlparse

from .. import envelope
from ..executor import execute as default_execute
from ..question_claim import (
    claim_question,
    question_claim_path,
    release_question_claim,
)
from ..types import (ErrorClass, Request, Response, TrackerError,
                     gitlab_cli_hostname)

#: Jira project / issue-key grammars from jira.md (listOpenIssues JQL safety).
#: Underscores and keys longer than Cloud's 10-char alnum cap are intentional:
#: Data Center admins can configure them. Cloud cannot reproduce that shape.
#: UNVERIFIED on live Jira Data Center (Cloud cannot reproduce custom keys - fn-140 R17); verified against prose only.
_JIRA_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_JIRA_ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-[1-9][0-9]*$")

#: Verbs this module owns. `attach` / `attach-get` delegate to attach/ (fn-140.4).
WIRE_VERBS = (
    "read", "update", "comment-add", "comment-list", "comment-update",
    "comment-delete", "label", "assign", "list-open", "relation-list",
    "question", "attach", "attach-get",
)
WRITE_VERBS = frozenset({
    "update", "comment-add", "comment-update", "comment-delete", "label", "assign",
    "question", "attach",
})
#: Verbs that require a parent locator. attach-get and list-open are context-free.
LOCATOR_VERBS = frozenset(v for v in WIRE_VERBS if v not in ("list-open", "attach-get"))

_ACTIVE = frozenset({"github", "gitlab", "linear", "jira"})
LINEAR_GQL = "https://api.linear.app/graphql"

Result = Union[dict, TrackerError]
Execute = Callable[[Request], Union[Response, TrackerError]]


def _created_at(comment: dict) -> Optional[datetime]:
    """Parse one normalized immutable comment timestamp."""
    raw = comment.get("created_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip()
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


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


def _ready_state(config: dict) -> Optional[str]:
    value = _dict(config.get("tracker")).get("readyState")
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


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
            argv += ["--hostname", gitlab_cli_hostname(str(host))]
    if method.upper() != "GET":
        argv += ["--method", method.upper()]
    argv.append(endpoint)
    if body is not None:
        if provider != "github":
            # glab api sends NO Content-Type with --input (measured live:
            # GitLab replies 415 "provided content-type '' is not supported"
            # on every JSON mutation); gh api defaults to JSON already.
            argv += ["-H", "Content-Type: application/json"]
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


def validate_pr_url(url: Any) -> Optional[TrackerError]:
    """Reject malformed link content before a facade claim or provider read."""
    if not isinstance(url, str):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "PR URL must be an absolute http(s) URL up to 2048 characters",
            subtype="pr_url",
        )
    value = url.strip()
    parsed = urlparse(value)
    if (parsed.scheme not in ("http", "https") or not parsed.netloc
            or any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7f
                   for ch in value)
            or len(url) > 2048):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "PR URL must be an absolute http(s) URL up to 2048 characters",
            subtype="pr_url",
        )
    return None


def link_pr(provider: str, config: dict, locator: dict, execute: Execute, *,
            url: str) -> Result:
    """Project one PR URL through the provider's native non-closing link."""
    invalid = validate_pr_url(url)
    if invalid is not None:
        return invalid
    mod = _PROVIDERS.get(provider)
    if mod is None:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"unknown tracker type {provider!r}",
            subtype="provider",
        )
    return mod.pr_link(config, locator, execute, url=url.strip())


def _dispatch_question(*, mod: Any, provider: str, config: dict,
                       locator: dict, execute: Execute, body: str,
                       question_id: str) -> Result:
    """Read the current semantic round and post only when no round is open."""
    marker = f"<!-- flow-next:question id={question_id} status=open -->"
    listed = mod.comment_list(config, locator, execute)
    if isinstance(listed, TrackerError):
        return listed
    comments = listed.get("comments")
    if not isinstance(comments, list):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "question comment list is malformed",
            subtype="malformed_body")
    if listed.get("truncated"):
        return TrackerError(
            ErrorClass.TRANSPORT,
            "question comment pages truncated; latest round is unproven",
            subtype="truncated")
    question_pattern = re.compile(
        rf"<!--\s*flow-next:question\s+id={re.escape(question_id)}"
        r"(?:\s+status=[A-Za-z0-9_-]+)?\s*-->")
    answer_pattern = re.compile(
        rf"<!--\s*flow-next:answer\s+id={re.escape(question_id)}\s*-->")
    questions = []
    answers = []
    for comment in comments:
        comment_body = comment.get("body") if isinstance(comment, dict) else None
        if not isinstance(comment_body, str):
            continue
        if question_pattern.search(comment_body):
            questions.append(comment)
        if answer_pattern.search(comment_body):
            answers.append(comment)

    current_question = questions[-1] if questions else None
    reopen = False
    if questions and answers:
        timed_questions = [(_created_at(c), c) for c in questions]
        timed_answers = [(_created_at(c), c) for c in answers]
        if (any(stamp is None for stamp, _ in timed_questions)
                or any(stamp is None for stamp, _ in timed_answers)):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "question and answer markers need immutable created_at "
                "timestamps to determine the latest round",
                subtype="malformed_body")
        latest_question = max(timed_questions, key=lambda row: row[0])
        latest_answer = max(timed_answers, key=lambda row: row[0])
        if latest_question[0] == latest_answer[0]:
            return TrackerError(
                ErrorClass.TRANSPORT,
                "question and answer chronology is ambiguous",
                subtype="malformed_body")
        current_question = latest_question[1]
        reopen = latest_answer[0] > latest_question[0]

    if current_question is not None and not reopen:
        # GitHub and GitLab comment-list routes address the parent by
        # display number/IID. Accept a dedup match only after durable
        # identity is proven, either by the comment payload itself or
        # by an explicit display-addressed parent read.
        if (provider in ("github", "gitlab")
                and current_question.get("parent_identity") != "validated"):
            parent = mod.parent_read(
                config, locator, execute,
                op="wire-question-parent-read")
            if isinstance(parent, TrackerError):
                return parent
        return {
            "posted": False,
            "question_id": question_id,
            "comment": current_question,
        }
    rendered = f"{marker}\n\n{body.lstrip()}"
    added = mod.comment_add(
        config, locator, execute, body=rendered)
    if isinstance(added, TrackerError):
        return added
    return {
        "posted": True,
        "reopened": reopen,
        "question_id": question_id,
        "comment": added,
    }


# ---------------------------------------------------------------------------
# Dispatch + CLI entry
# ---------------------------------------------------------------------------

def dispatch(verb: str, config: dict, *, locator: Any = None,
             title: Optional[str] = None, body: Optional[str] = None,
             comment_id: Optional[str] = None,
             subject_id: Optional[str] = None,
             blocked_stage: Optional[str] = None,
             reason_code: Optional[str] = None,
             question_slug: Optional[str] = None,
             add: Optional[list] = None, remove: Optional[list] = None,
             file_path: Optional[str] = None,
             attachment_id: Optional[str] = None,
             out_path: Optional[str] = None,
             flow_dir: Optional[Path] = None,
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
    if verb == "relation-list":
        from ..relate import listing as relation_listing  # noqa: PLC0415
        return relation_listing.list_relations(
            provider, config, execute, locator=parsed)  # type: ignore[arg-type]
    if verb == "question":
        if body is None:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                "question requires --body-file",
                subtype="body")
        identity = {
            "subject-id": subject_id,
            "blocked-stage": blocked_stage,
            "reason-code": reason_code,
            "question-slug": question_slug,
        }
        for name, value in identity.items():
            if (not isinstance(value, str) or not value.strip()
                    or "\0" in value or len(value) > 256):
                return TrackerError(
                    ErrorClass.INVALID_INPUT,
                    f"question requires --{name} (1-256 non-NUL characters)",
                    subtype=name.replace("-", "_"))
        stable = "\0".join(str(value).strip() for value in identity.values())
        question_id = hashlib.sha256(stable.encode()).hexdigest()[:16]
        if flow_dir is None:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                "question requires the .flow directory for concurrency-safe "
                "deduplication",
                subtype="flow_dir")
        if parsed is None:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                "question requires the parent locator",
                subtype="locator")
        rec_path = question_claim_path(
            Path(flow_dir), provider=provider,
            durable=str(parsed["durable"]), question_id=question_id)
        claimed = claim_question(
            Path(flow_dir), rec_path, provider=provider,
            durable=str(parsed["durable"]), question_id=question_id,
            subject_id=str(subject_id))
        if claimed is not None:
            return claimed
        try:
            return _dispatch_question(
                mod=mod, provider=provider, config=config, locator=parsed,
                execute=execute, body=body, question_id=question_id)
        finally:
            release_question_claim(rec_path)
    return TrackerError(ErrorClass.INVALID_INPUT, f"unhandled verb {verb!r}", subtype="verb")


def _read_config(flow_dir) -> dict:
    try:
        data = json.loads((Path(flow_dir) / "config.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def run(flow_dir, verb: str, *, locator: Any = None, title: Optional[str] = None,
        body_file: Optional[str] = None, comment_id: Optional[str] = None,
        subject_id: Optional[str] = None, blocked_stage: Optional[str] = None,
        reason_code: Optional[str] = None, question_slug: Optional[str] = None,
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
        try:
            body = Path(body_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"cannot read --body-file: {exc}",
                subtype="body_file"))

    # Bind transport policy for the real executor; injected fakes pass through.
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    body_claim = None
    if verb == "update" and body is not None:
        claimed_locator = parse_locator(locator)
        if isinstance(claimed_locator, TrackerError):
            return envelope.failure(claimed_locator)
        from ..lifecycle.verbs import (  # noqa: PLC0415
            _claim_body_mutation, _release_claim,
        )
        body_claim = _claim_body_mutation(
            Path(flow_dir), _tracker_type(config) or "", claimed_locator,
            operation="wire-update")
        if isinstance(body_claim, TrackerError):
            return envelope.failure(body_claim)
    # Never-raises boundary: a provider that returns syntactically valid JSON
    # with an unexpected field shape (e.g. gitlab `labels: 1`) can raise deep
    # inside an adapter (`list(raw.get("labels"))` -> TypeError). The promise
    # of this entry point is the structured envelope, never a traceback.
    try:
        try:
            out = dispatch(verb, config, locator=locator, title=title, body=body,
                           comment_id=comment_id, subject_id=subject_id,
                           blocked_stage=blocked_stage,
                           reason_code=reason_code, question_slug=question_slug,
                           add=add, remove=remove,
                           file_path=file_path, attachment_id=attachment_id,
                           out_path=out_path, flow_dir=Path(flow_dir),
                           execute=ex)
        except Exception as exc:  # noqa: BLE001 - envelope boundary
            out = TrackerError(
                ErrorClass.TRANSPORT,
                f"provider adapter failed on malformed response shape: "
                f"{type(exc).__name__}: {exc}",
                subtype="malformed_body",
                details={"subtype": "malformed_body", "verb": verb})
    finally:
        if body_claim is not None:
            _release_claim(body_claim)
    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
