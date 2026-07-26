"""GitHub resolution (fn-139.4).

Destination is `owner` + `repo` - stable, resolved once from `gh repo view`
(the CLI route already carries host + auth resolution this repo depends on).

Capabilities are STATIC and never re-probed: GitHub has no attachment API
(measured: `/issues/:n/uploads` -> 404), no issue-level blocked-by, a real
`sub_issues` hierarchy API, and no issue delete (close `not_planned` only).
"""

from __future__ import annotations

import json
from typing import Callable, Union

from ..types import ErrorClass, Request, Response, TrackerError

#: The truth-table row, verbatim from the spec. Static: resolving capabilities
#: is a table copy, not a network call, and there is no TTL re-probe.
CAPABILITIES = {"attachments": False, "blockedBy": False,
                "subIssues": True, "deleteIssue": False}


def _json_body(resp: Response) -> Union[dict, TrackerError]:
    try:
        data = json.loads(resp.body or b"{}")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"malformed gh output: {exc}",
                            subtype="malformed_body")
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gh output is not an object",
                            subtype="malformed_body")
    return data


def resolve_destination(config: dict, execute: Callable) -> Union[dict, TrackerError]:
    """`gh repo view` on the current repo -> {owner, repo}."""
    result = execute(Request(
        provider="github", op="resolve-destination", method="GET",
        url_or_argv=["gh", "repo", "view", "--json", "owner,name"],
        idempotent=True,
    ))
    if isinstance(result, TrackerError):
        return result
    data = _json_body(result)
    if isinstance(data, TrackerError):
        return data
    owner_obj = data.get("owner")
    owner = owner_obj.get("login") if isinstance(owner_obj, dict) else None
    owner = owner if isinstance(owner, str) else None
    repo = data.get("name")
    repo = repo if isinstance(repo, str) else None
    if not owner or not repo:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "gh repo view returned no owner/name; is this a "
                            "GitHub repo with gh authenticated?",
                            subtype="destination")
    return {"owner": owner, "repo": repo}


def resolve_capabilities(config: dict, execute: Callable) -> dict:
    """Static table copy - deliberately NO network and NO `execute` use, which
    is itself the tested contract (GitHub is never probed)."""
    return dict(CAPABILITIES)
