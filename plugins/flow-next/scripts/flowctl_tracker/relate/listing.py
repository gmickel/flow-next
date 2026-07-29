"""Per-provider relation reads for tracker wire."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import quote

from ..types import ErrorClass, TrackerError
from ..wire import (
    _MAX_PAGES,
    _PAGE_SIZE,
    Execute,
    Result,
    _check_durable,
    _destination,
    _gitlab_iid,
    _gql,
    _jira,
    _jira_base,
)
from . import providers
from .ledger import FLOW_DEPS_CLOSE, FLOW_DEPS_OPEN


def _relation(from_display: str, to_display: str, *,
              source: str = "unknown", link_present: bool = True,
              degraded: Optional[dict] = None) -> dict:
    out = {
        "from": from_display,
        "to": to_display,
        "type": "blocks",
        "source": source,
        "linkPresent": link_present,
    }
    if degraded is not None:
        out["degraded"] = degraded
    return out


def _dedupe_relations(rows: list) -> list:
    """Stable directed-pair dedup; provenance-bearing rows win."""
    by_pair: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row.get("from") or ""), str(row.get("to") or ""))
        prior = by_pair.get(key)
        if prior is None or (
            row.get("source") in {"flow", "block-only"}
            and prior.get("source") not in {"flow", "block-only"}
        ):
            by_pair[key] = row
    return list(by_pair.values())


def _truncated_error(provider: str) -> TrackerError:
    return TrackerError(
        ErrorClass.TRANSPORT,
        f"{provider} relation pages truncated at drain cap; "
        "dependency graph completeness unproven",
        subtype="truncated",
    )


def linear_list(config: dict, execute: Execute, *, locator: dict) -> Result:
    """List every direct blocked-by edge touching one Linear issue."""
    query = (
        "query($id: String!, $afterRel: String, $afterInv: String) { "
        "issue(id: $id) { id identifier "
        f"relations(first: {_PAGE_SIZE}, after: $afterRel) "
        "{ nodes { type relatedIssue { id identifier } } "
        "pageInfo { hasNextPage endCursor } } "
        f"inverseRelations(first: {_PAGE_SIZE}, after: $afterInv) "
        "{ nodes { type issue { id identifier } } "
        "pageInfo { hasNextPage endCursor } } } }"
    )
    rel_cursor: Optional[str] = None
    inv_cursor: Optional[str] = None
    rows: list = []
    seen: set = set()
    for _ in range(_MAX_PAGES):
        data = _gql(
            execute, "wire-relation-list", query,
            {"id": locator["durable"], "afterRel": rel_cursor,
             "afterInv": inv_cursor},
            idempotent=True,
        )
        if isinstance(data, TrackerError):
            return data
        issue = data.get("issue")
        if issue is None:
            return TrackerError(
                ErrorClass.NOT_FOUND, "linear issue not found", subtype="issue")
        if not isinstance(issue, dict):
            return TrackerError(
                ErrorClass.TRANSPORT, "linear relation list malformed",
                subtype="malformed_body")
        err = _check_durable("linear", locator, issue)
        if err:
            return err
        current = str(issue.get("identifier") or locator["display"])
        rel = issue.get("relations") if isinstance(issue.get("relations"), dict) else {}
        inv = (issue.get("inverseRelations")
               if isinstance(issue.get("inverseRelations"), dict) else {})
        for node in rel.get("nodes") or []:
            if not isinstance(node, dict) or node.get("type") != "blocks":
                continue
            related = (node.get("relatedIssue")
                       if isinstance(node.get("relatedIssue"), dict) else {})
            display = related.get("identifier")
            if isinstance(display, str) and display:
                rows.append(_relation(display, current))
        for node in inv.get("nodes") or []:
            if not isinstance(node, dict) or node.get("type") != "blocks":
                continue
            blocker = node.get("issue") if isinstance(node.get("issue"), dict) else {}
            display = blocker.get("identifier")
            if isinstance(display, str) and display:
                rows.append(_relation(current, display))
        rel_info = rel.get("pageInfo") if isinstance(rel.get("pageInfo"), dict) else {}
        inv_info = inv.get("pageInfo") if isinstance(inv.get("pageInfo"), dict) else {}
        rel_more = bool(rel_info.get("hasNextPage"))
        inv_more = bool(inv_info.get("hasNextPage"))
        if not rel_more and not inv_more:
            break
        next_rel = rel_info.get("endCursor") if rel_more else rel_cursor
        next_inv = inv_info.get("endCursor") if inv_more else inv_cursor
        step = (next_rel, next_inv)
        if (rel_more and not next_rel) or (inv_more and not next_inv) or step in seen:
            return TrackerError(
                ErrorClass.TRANSPORT, "pagination made no progress",
                subtype="malformed_body")
        seen.add(step)
        rel_cursor, inv_cursor = next_rel, next_inv
    else:
        return _truncated_error("linear")
    return {
        "relations": _dedupe_relations(rows),
        "truncated": False,
        "parent_identity": "validated",
    }


def jira_list(config: dict, execute: Execute, *, locator: dict) -> Result:
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    blocks_type = providers.jira_blocks_type(config, execute)
    if isinstance(blocks_type, TrackerError):
        return blocks_type
    data = _jira(
        execute, "wire-relation-list", "GET",
        f"{base}/rest/api/2/issue/{quote(locator['durable'], safe='')}"
        "?fields=issuelinks",
        idempotent=True,
    )
    if isinstance(data, TrackerError):
        return data
    if not isinstance(data, dict):
        return TrackerError(
            ErrorClass.TRANSPORT, "jira relation list malformed",
            subtype="malformed_body")
    err = _check_durable("jira", locator, data)
    if err:
        return err
    current = str(data.get("key") or locator["display"])
    fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
    rows: list = []
    for link in fields.get("issuelinks") or []:
        if not isinstance(link, dict):
            continue
        typ = link.get("type") if isinstance(link.get("type"), dict) else {}
        if str(typ.get("name") or "").casefold() != blocks_type.casefold():
            continue
        inward = link.get("inwardIssue")
        if isinstance(inward, dict):
            blocker = inward.get("key") or inward.get("id")
            if blocker is not None:
                rows.append(_relation(current, str(blocker)))
        outward = link.get("outwardIssue")
        if isinstance(outward, dict):
            blocked = outward.get("key") or outward.get("id")
            if blocked is not None:
                rows.append(_relation(str(blocked), current))
    return {
        "relations": _dedupe_relations(rows),
        "truncated": False,
        "parent_identity": "validated",
    }


def _gitlab_link_display(link: dict, current_display: str) -> Optional[str]:
    refs = link.get("references") if isinstance(link.get("references"), dict) else {}
    full = refs.get("full")
    if isinstance(full, str) and full.strip():
        return full.strip()
    relative = refs.get("relative")
    if isinstance(relative, str) and relative.strip():
        value = relative.strip()
        if value.startswith("#") and "#" in current_display:
            return f"{current_display.rsplit('#', 1)[0]}{value}"
        return value
    iid = link.get("iid")
    if isinstance(iid, int) and "#" in current_display:
        return f"{current_display.rsplit('#', 1)[0]}#{iid}"
    return None


_FLOW_DEPS_RE = re.compile(
    re.escape(FLOW_DEPS_OPEN) + r".*?" + re.escape(FLOW_DEPS_CLOSE),
    re.DOTALL,
)
_BLOCKED_BY_RE = re.compile(r"(?m)^\*\*Blocked by:\*\*[ \t]*(.*)$")


def _gitlab_blocked_refs(description: object) -> list[str]:
    if not isinstance(description, str):
        return []
    match = _FLOW_DEPS_RE.search(description)
    if match is None:
        return []
    blocked = _BLOCKED_BY_RE.search(match.group(0))
    if blocked is None:
        return []
    return [ref.strip() for ref in blocked.group(1).split(",") if ref.strip()]


def gitlab_list(config: dict, execute: Execute, *, locator: dict) -> Result:
    """List native directional links plus flow-owned degraded dependency rows."""
    from ..wire import gitlab as wire_gitlab  # noqa: PLC0415

    parent = wire_gitlab.parent_read(
        config, locator, execute, op="wire-relation-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    iid = _gitlab_iid(locator["display"])
    if isinstance(iid, TrackerError):
        return iid
    drained = providers._gitlab_links(config, execute, iid=iid)
    if isinstance(drained, TrackerError):
        return drained
    links, truncated = drained
    if truncated:
        return _truncated_error("gitlab")
    current = locator["display"]
    rows: list = []
    visible_blockers: set[str] = set()
    native_blockers: set[str] = set()
    for link in links:
        if not isinstance(link, dict):
            continue
        target = _gitlab_link_display(link, current)
        if target is None:
            continue
        kind = link.get("link_type")
        if kind == "is_blocked_by":
            rows.append(_relation(current, target))
            visible_blockers.add(target)
            native_blockers.add(target)
        elif kind == "blocks":
            rows.append(_relation(target, current))
        elif kind == "relates_to":
            visible_blockers.add(target)

    for blocker in _gitlab_blocked_refs(parent.get("description")):
        # A native directional row is already the stronger representation.
        # Do not let the body-owned fallback duplicate win _dedupe_relations()
        # and relabel a real is_blocked_by link as degraded relates_to.
        if blocker in native_blockers:
            continue
        present = blocker in visible_blockers
        rows.append(_relation(
            current,
            blocker,
            source="flow" if present else "block-only",
            link_present=present,
            degraded={
                "kind": "relates_to",
                "capability": "blockedBy",
                "reason": "direction is carried by the flow:deps block",
            },
        ))
    return {
        "relations": _dedupe_relations(rows),
        "truncated": False,
        "parent_identity": "validated",
    }


def github_list(config: dict, execute: Execute, *, locator: dict) -> Result:
    """Validate the issue, but never reinterpret hierarchy as dependency."""
    from ..wire import github as wire_github  # noqa: PLC0415

    parent_issue = wire_github.parent_read(
        config, locator, execute, op="wire-relation-parent-read")
    if isinstance(parent_issue, TrackerError):
        return parent_issue
    return {
        "relations": [],
        "truncated": False,
        "parent_identity": "validated",
    }


LISTERS = {
    "linear": linear_list,
    "jira": jira_list,
    "gitlab": gitlab_list,
    "github": github_list,
}


def list_relations(provider: str, config: dict, execute: Execute, *,
                   locator: dict) -> Result:
    handler = LISTERS.get(provider)
    if handler is None:
        return TrackerError(
            ErrorClass.INVALID_INPUT, f"unknown tracker provider {provider!r}",
            subtype="provider")
    return handler(config, execute, locator=locator)
