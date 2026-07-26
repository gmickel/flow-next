"""Jira resolution (fn-139.6).

Destination pins `baseUrl`, `projectKey`, `projectId`, `issueTypeId`,
`apiVersion: 2`, `style`; `statusIds` is its own scope and holds **status ids
ONLY** - transition ids are NEVER cached (`jira.md:738`: valid only FROM the
current status, verified live: To Do / In Progress / Done each surfaced
different transition ids). Transition re-fetch is spec B's concern.

`apiVersion` resolves to **2** by decision: v2 round-trips a plain-string body
byte-exact on Cloud AND DC (measured), while v3 forces ADF.
"""

from __future__ import annotations

import json
import os
from typing import Callable, Optional, Union
from urllib.parse import quote

from ..states import Assignment, assign_slots
from ..types import ErrorClass, Request, TrackerError

#: Truth-table row: everything static (attachments need the XSRF header, Blocks
#: links work on the free tier, no sub-issues we consume, real delete).
CAPABILITIES = {"attachments": True, "blockedBy": True,
                "subIssues": False, "deleteIssue": True}

#: statusCategory.key -> normalized slots it naturally fills. Only 3 buckets
#: (vs Linear's 6 types), so name hints carry more weight here.
CATEGORY_TO_SLOTS = {
    "new": ("todo", "backlog"),
    "indeterminate": ("in_progress", "in_review"),
    "done": ("done", "cancelled"),
}

API_VERSION = 2

#: Legacy `statusMap` normalized vocabulary (status-sync.md: `backlog, planned,
#: in-progress, in-review, done, verified, deferred, wontfix`) -> fn-139 slots.
#: `verified` (a second done-category status) has no slot of its own: it fills
#: `done` only when the legacy map has no `done` entry, else it is dropped with
#: a warning. `deferred` has no equivalent at all.
LEGACY_KEY_MAP = {
    "backlog": "backlog",
    "planned": "todo",
    "in-progress": "in_progress",
    "in-review": "in_review",
    "done": "done",
    "wontfix": "cancelled",
    # new-form keys pass through unchanged
    "todo": "todo", "in_progress": "in_progress", "in_review": "in_review",
    "cancelled": "cancelled", "canceled": "cancelled",
}


def base_url(config: dict) -> Optional[str]:
    """`JIRA_BASE_URL` overrides the persisted value at runtime (fn-70 R8)."""
    env = os.environ.get("JIRA_BASE_URL")
    if env:
        return env.rstrip("/")
    per = (config.get("tracker") or {}).get("perTracker") or {}
    persisted = per.get("baseUrl")
    return str(persisted).rstrip("/") if persisted else None


def _get(execute: Callable, op: str, url: str) -> Union[object, TrackerError]:
    result = execute(Request(provider="jira", op=op, method="GET",
                             url_or_argv=url, idempotent=True))
    if isinstance(result, TrackerError):
        return result
    try:
        return json.loads(result.body or b"null")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"malformed jira body: {exc}",
                            subtype="malformed_body")


def _project_inputs(config: dict) -> Union[tuple, TrackerError]:
    per = (config.get("tracker") or {}).get("perTracker") or {}
    base = base_url(config)
    key = per.get("projectKey")
    if not base or not key:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "tracker.perTracker.baseUrl/projectKey are not set; "
                            "run the discovery ceremony first", subtype="destination")
    return base, str(key)


def _resolve_issue_type(config: dict, issue_types: list) -> Union[str, TrackerError]:
    """Precedence, matching the existing prose: configured `perTracker.issueType`
    -> a type named `Task` -> the project's first non-subtask type. A configured
    value that does not resolve against the LIVE project is an ERROR, never a
    silent fallback."""
    types = [t for t in issue_types if isinstance(t, dict) and t.get("id")]
    per = (config.get("tracker") or {}).get("perTracker") or {}
    configured = per.get("issueType")
    if configured:
        want = str(configured).lower()
        for t in types:
            if str(t.get("id")) == str(configured) or str(t.get("name", "")).lower() == want:
                return str(t["id"])
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"configured issueType {configured!r} does not resolve against the "
            f"live project (types: {[t.get('name') for t in types]})",
            subtype="issue_type")
    for t in types:
        if str(t.get("name", "")).lower() == "task" and not t.get("subtask"):
            return str(t["id"])
    for t in types:
        if not t.get("subtask"):
            return str(t["id"])
    return TrackerError(ErrorClass.UNRESOLVED,
                        "project has no non-subtask issue type", subtype="issue_type")


def resolve_destination(config: dict, execute: Callable) -> Union[dict, TrackerError]:
    inputs = _project_inputs(config)
    if isinstance(inputs, TrackerError):
        return inputs
    base, key = inputs
    data = _get(execute, "resolve-destination",
                f"{base}/rest/api/2/project/{quote(key, safe='')}")
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict) or not data.get("id"):
        return TrackerError(ErrorClass.UNRESOLVED,
                            f"jira project {key!r} did not resolve",
                            subtype="destination")
    issue_type = _resolve_issue_type(config, data.get("issueTypes") or [])
    if isinstance(issue_type, TrackerError):
        return issue_type
    # Cloud team-managed reports style "next-gen" / simplified true; classic
    # company-managed differs in workflow/field APIs, so the enum is pinned.
    style = "next-gen" if (data.get("style") == "next-gen"
                           or data.get("simplified") is True) else "classic"
    return {
        "baseUrl": base,
        "projectKey": key,
        "projectId": str(data["id"]),
        "issueTypeId": issue_type,
        "apiVersion": API_VERSION,
        "style": style,
    }


def fetch_statuses(config: dict, execute: Callable) -> Union[tuple, TrackerError]:
    """Live statuses for the resolved issue type -> (pools, live)."""
    inputs = _project_inputs(config)
    if isinstance(inputs, TrackerError):
        return inputs
    base, key = inputs
    data = _get(execute, "resolve-statuses",
                f"{base}/rest/api/2/project/{quote(key, safe='')}/statuses")
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, list):
        return TrackerError(ErrorClass.TRANSPORT,
                            "project statuses response is not a list",
                            subtype="malformed_body")
    resolved = ((config.get("tracker") or {}).get("resolved") or {})
    issue_type_id = (resolved.get("destination") or {}).get("issueTypeId")
    if not issue_type_id:
        # NEVER "first entry": without the resolved issue type a Task project
        # would happily cache the first (e.g. Story) workflow's status ids -
        # bypassing the configured -> Task -> first-non-subtask precedence.
        return TrackerError(ErrorClass.UNRESOLVED,
                            "no resolved issueTypeId; resolve destination first "
                            "(statusIds is scoped to the pinned issue type)",
                            subtype="statusIds")
    entry = None
    for t in data:
        if isinstance(t, dict) and str(t.get("id")) == str(issue_type_id):
            entry = t
            break
    if entry is None:
        return TrackerError(ErrorClass.UNRESOLVED,
                            f"no status set for issue type {issue_type_id!r}; "
                            "resolve destination first", subtype="statusIds")
    pools: dict = {}
    live: dict = {}
    for s in entry.get("statuses") or []:
        if not isinstance(s, dict) or not s.get("id"):
            continue
        sid = str(s["id"])
        category = str(((s.get("statusCategory") or {}) if
                        isinstance(s.get("statusCategory"), dict) else {}).get("key", ""))
        live[sid] = {"id": sid, "name": s.get("name"), "category": category}
        for slot in CATEGORY_TO_SLOTS.get(category, ()):
            pools.setdefault(slot, []).append(
                {"id": sid, "name": s.get("name"), "category": category})
    return pools, live


def _migrated_status_map(config: dict, live: dict) -> tuple[dict, list]:
    """Existing `perTracker.statusMap` entries ({name}/{id}) migrate into
    `statusIds` where they resolve to a LIVE status; dead entries are dropped
    WITH A WARNING, never carried forward silently."""
    per = (config.get("tracker") or {}).get("perTracker") or {}
    status_map = per.get("statusMap")
    if not isinstance(status_map, dict):
        return {}, ([f"perTracker.statusMap is malformed ({type(status_map).__name__}); ignored"]
                    if status_map not in (None, {}) else [])
    by_name = {str(v.get("name", "")).lower(): k for k, v in live.items()
               for v in [live[k]]}
    migrated: dict = {}
    warnings: list = []
    for legacy_key, spec in status_map.items():
        # Legacy keys use the OLD normalized vocabulary (`planned`,
        # `in-progress`, `verified`, ...) - copying them verbatim silently
        # ignored every real existing mapping.
        slot = LEGACY_KEY_MAP.get(str(legacy_key))
        if slot is None and str(legacy_key) == "verified":
            if "done" in status_map:
                warnings.append(
                    "dropped statusMap entry 'verified': the fn-139 vocabulary "
                    "has no verified slot and 'done' is already mapped")
                continue
            slot = "done"
        if slot is None:
            warnings.append(
                f"dropped statusMap entry {legacy_key!r}: no equivalent slot in "
                f"the fn-139 vocabulary")
            continue
        if not isinstance(spec, dict):
            warnings.append(f"statusMap[{legacy_key!r}] is malformed; dropped")
            continue
        sid = spec.get("id")
        if sid is not None and str(sid) in live:
            migrated[slot] = str(sid)
            continue
        name = str(spec.get("name", "")).lower()
        if name and name in by_name:
            migrated[slot] = by_name[name]
            continue
        warnings.append(
            f"dropped statusMap entry {legacy_key!r}: {spec!r} no longer "
            "resolves to a live status")
    return migrated, warnings


def resolve_status_ids(config: dict, execute: Callable) -> Union[Assignment, TrackerError]:
    fetched = fetch_statuses(config, execute)
    if isinstance(fetched, TrackerError):
        return fetched
    pools, live = fetched
    resolved = ((config.get("tracker") or {}).get("resolved") or {})
    existing = (resolved.get("destination") or {}).get("statusIds") or {}
    migrated, warnings = _migrated_status_map(config, live)
    # Prior cache entries win over the legacy statusMap (they are newer intent);
    # both are validated against live by assign_slots.
    seed = {**migrated, **(existing if isinstance(existing, dict) else {})}
    assignment = assign_slots(pools, live, seed)
    assignment.warnings = warnings + assignment.warnings
    return assignment


def resolve_capabilities(config: dict, execute: Callable) -> dict:
    """Static table copy - no network, no probe, never TTL-reprobed."""
    return dict(CAPABILITIES)
