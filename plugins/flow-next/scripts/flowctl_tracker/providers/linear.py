"""Linear resolution (fn-139.6).

Destination pins `teamId`, `teamKey` and `labelIds` (label NAME, lowercased ->
id); `stateIds` is its own scope (`destination.stateIds`) because status
writes need a `stateId` and `type: started` maps to TWO states (In Progress,
In Review) - a human decides that tiebreak once, via `--select`.

Everything GraphQL is PAGINATED and fully drained (`pageInfo.hasNextPage`) -
first-page-only silently loses labels/states on real workspaces.
"""

from __future__ import annotations

import json
from typing import Callable, Optional, Union

from ..states import Assignment, assign_slots
from ..types import ErrorClass, Request, TrackerError

GRAPHQL_URL = "https://api.linear.app/graphql"

#: Truth-table row: everything static (uploads are presigned two-step, blockedBy
#: native, no sub-issues concept we consume, real delete). Never TTL-reprobed.
CAPABILITIES = {"attachments": True, "blockedBy": True,
                "subIssues": False, "deleteIssue": True}

#: Linear `state.type` -> normalized slots it naturally fills. `started` is the
#: measured one-to-many (In Progress AND In Review).
TYPE_TO_SLOTS = {
    "backlog": ("backlog",),
    "unstarted": ("todo",),
    "started": ("in_progress", "in_review"),
    "completed": ("done",),
    "canceled": ("cancelled",),
}

_PAGE = 100
_MAX_PAGES = 50  # 5000 items; a generous ceiling, not a tunable


def _gql(execute: Callable, op: str, query: str,
         variables: dict) -> Union[dict, TrackerError]:
    result = execute(Request(
        provider="linear", op=op, method="POST", url_or_argv=GRAPHQL_URL,
        headers={"Content-Type": "application/json"},
        body=json.dumps({"query": query, "variables": variables}).encode(),
        idempotent=True,
    ))
    if isinstance(result, TrackerError):
        return result
    try:
        payload = json.loads(result.body or b"{}")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"malformed GraphQL body: {exc}",
                            subtype="malformed_body")
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "GraphQL response carries no data",
                            subtype="malformed_body")
    return data


def _drain(execute: Callable, op: str, query: str, team_id: str,
           connection: str) -> Union[list, TrackerError]:
    """Fully drain one paginated team connection - never first-page-only."""
    nodes: list = []
    cursor: Optional[str] = None
    seen_cursors: set = set()
    pages = 0
    while True:
        pages += 1
        if pages > _MAX_PAGES:
            return TrackerError(ErrorClass.TRANSPORT,
                                f"{connection} pagination exceeded {_MAX_PAGES} pages",
                                subtype="malformed_body")
        data = _gql(execute, op, query, {"teamId": team_id, "after": cursor})
        if isinstance(data, TrackerError):
            return data
        team = data.get("team")
        conn = (team or {}).get(connection) if isinstance(team, dict) else None
        if not isinstance(conn, dict) or not isinstance(conn.get("nodes"), list):
            return TrackerError(ErrorClass.TRANSPORT,
                                f"GraphQL {connection} connection is malformed",
                                subtype="malformed_body")
        nodes.extend(n for n in conn["nodes"] if isinstance(n, dict))
        page = conn.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return nodes
        cursor = page.get("endCursor")
        if not cursor:
            return TrackerError(ErrorClass.TRANSPORT,
                                "hasNextPage without an endCursor",
                                subtype="malformed_body")
        if cursor in seen_cursors:
            # A provider looping the same cursor would otherwise drive an
            # unbounded request loop with growing memory - progress or fail.
            return TrackerError(ErrorClass.TRANSPORT,
                                f"pagination repeated cursor {cursor!r}",
                                subtype="malformed_body")
        seen_cursors.add(cursor)


_TEAM_QUERY = "query($teamId: String!) { team(id: $teamId) { id key } }"
_STATES_QUERY = (
    "query($teamId: String!, $after: String) { team(id: $teamId) { "
    f"states(first: {_PAGE}, after: $after) "
    "{ nodes { id name type } pageInfo { hasNextPage endCursor } } } }"
)
_LABELS_QUERY = (
    "query($teamId: String!, $after: String) { team(id: $teamId) { "
    f"labels(first: {_PAGE}, after: $after) "
    "{ nodes { id name } pageInfo { hasNextPage endCursor } } } }"
)


def _team_id(config: dict) -> Optional[str]:
    per = (config.get("tracker") or {}).get("perTracker") or {}
    return per.get("teamId")


def resolve_destination(config: dict, execute: Callable) -> Union[dict, TrackerError]:
    team_id = _team_id(config)
    if not team_id:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "tracker.perTracker.teamId is not set; run the "
                            "discovery ceremony first", subtype="destination")
    data = _gql(execute, "resolve-destination", _TEAM_QUERY, {"teamId": team_id})
    if isinstance(data, TrackerError):
        return data
    team = data.get("team")
    if not isinstance(team, dict) or not team.get("id") or not team.get("key"):
        return TrackerError(ErrorClass.UNRESOLVED,
                            f"linear team {team_id!r} did not resolve",
                            subtype="destination")
    labels = _drain(execute, "resolve-labels", _LABELS_QUERY, team_id, "labels")
    if isinstance(labels, TrackerError):
        return labels
    label_ids = {str(lbl["name"]).lower(): lbl["id"]
                 for lbl in labels if lbl.get("name") and lbl.get("id")}
    return {"teamId": team["id"], "teamKey": team["key"], "labelIds": label_ids}


def fetch_states(config: dict, execute: Callable) -> Union[tuple, TrackerError]:
    """Live states -> (pools, live). Shared by resolve and `--select` so a
    selection is always validated against CURRENT candidates."""
    team_id = _team_id(config)
    if not team_id:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "tracker.perTracker.teamId is not set",
                            subtype="stateIds")
    states = _drain(execute, "resolve-states", _STATES_QUERY, team_id, "states")
    if isinstance(states, TrackerError):
        return states
    pools: dict = {}
    live: dict = {}
    for s in states:
        sid, name, stype = s.get("id"), s.get("name"), s.get("type")
        if not sid:
            continue
        live[sid] = {"id": sid, "name": name, "type": stype}
        for slot in TYPE_TO_SLOTS.get(str(stype), ()):
            pools.setdefault(slot, []).append({"id": sid, "name": name, "type": stype})
    return pools, live


def resolve_state_ids(config: dict, execute: Callable) -> Union[Assignment, TrackerError]:
    fetched = fetch_states(config, execute)
    if isinstance(fetched, TrackerError):
        return fetched
    pools, live = fetched
    existing = (((config.get("tracker") or {}).get("resolved") or {})
                .get("destination") or {}).get("stateIds") or {}
    return assign_slots(pools, live, existing if isinstance(existing, dict) else {},
                        policy="linear")


def resolve_capabilities(config: dict, execute: Callable) -> dict:
    """Static table copy - no network, no probe, never TTL-reprobed."""
    return dict(CAPABILITIES)
