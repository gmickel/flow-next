"""linkState enum + legacy migration + UUID completion helper (fn-140.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

from ..executor import execute as default_execute
from ..types import ErrorClass, TrackerError
# derive_link_state lives in helpers (merged_tracker needs it below the
# defaults); re-exported here because this module is its public home.
from .helpers import (Execute, Result, derive_link_state, dict_,
                      load_spec, locked_tracker_write, merged_tracker,
                      now_iso, read_config, tracker_type)


def require_durable(tracker_block: Any) -> Union[str, TrackerError]:
    """Messages distinguish identifier_only from unlinked."""
    block = dict_(tracker_block)
    state = derive_link_state(block)
    if state == "linked":
        durable = block.get("id")
        if isinstance(durable, str) and durable.strip():
            return durable.strip()
        if durable is not None and str(durable).strip():
            return str(durable)
        return TrackerError(ErrorClass.UNRESOLVED,
                            "linkState is linked but tracker.id is empty",
                            subtype="durable")
    if state == "identifier_only":
        return TrackerError(
            ErrorClass.UNRESOLVED,
            "tracker linkState is identifier_only (display identifier present, "
            "durable id missing); run `flowctl tracker sync <spec-id> "
            "--op reconcile` to complete the UUID",
            subtype="identifier_only",
        )
    return TrackerError(
        ErrorClass.UNRESOLVED,
        "tracker is unlinked (no durable id and no display identifier)",
        subtype="unlinked",
    )


def resolve_linear_uuid(execute: Execute, identifier: str
                        ) -> Union[dict, TrackerError]:
    """GraphQL issue(id:) → {id, identifier, url}. Never fabricates a UUID."""
    from ..wire import _gql  # noqa: PLC0415
    data = _gql(execute, "lifecycle-resolve-uuid",
                "query($id: String!) { issue(id: $id) { id identifier url } }",
                {"id": identifier}, idempotent=True)
    if isinstance(data, TrackerError):
        return data
    issue = data.get("issue")
    if issue is None:
        return TrackerError(ErrorClass.NOT_FOUND,
                            f"linear issue {identifier!r} not found",
                            subtype="issue")
    if not isinstance(issue, dict) or not isinstance(issue.get("id"), str) or not issue["id"]:
        return TrackerError(ErrorClass.TRANSPORT,
                            "GraphQL issue carries no durable id",
                            subtype="malformed_body")
    return {
        "id": issue["id"],
        "identifier": issue.get("identifier") or identifier,
        "url": issue.get("url"),
    }


def complete_identifier_only(flow_dir, spec_id: str, *,
                             execute: Execute = default_execute) -> Result:
    """Resolve UUID via GraphQL; atomically set id + linkState linked.

    Helper for the .7 `tracker sync --op reconcile` facade — NOT a CLI verb.
    """
    flow_dir = Path(flow_dir)
    config = read_config(flow_dir)
    if tracker_type(config) != "linear":
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "complete_identifier_only requires tracker.type=linear",
                            subtype="provider")
    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data = loaded
    tracker = merged_tracker(spec_data)
    state = derive_link_state(tracker)
    if state == "linked" and tracker.get("id"):
        return {"id": tracker["id"], "identifier": tracker.get("identifier"),
                "url": tracker.get("url"), "linkState": "linked",
                "completed": False}
    if state != "identifier_only":
        return TrackerError(
            ErrorClass.UNRESOLVED,
            f"complete_identifier_only requires identifier_only, got {state}",
            subtype=state,
        )
    identifier = tracker.get("identifier")
    if not isinstance(identifier, str) or not identifier.strip():
        return TrackerError(ErrorClass.UNRESOLVED,
                            "identifier_only record has empty identifier",
                            subtype="identifier")
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    resolved = resolve_linear_uuid(ex, identifier.strip())
    if isinstance(resolved, TrackerError):
        return resolved
    link_fields = {
        "id": resolved["id"],
        "identifier": resolved["identifier"],
        "linkState": "linked",
        "lastSyncedAt": now_iso(),
    }
    if resolved.get("url"):
        link_fields["url"] = resolved["url"]
    # Persist ONLY the link-owned fields onto a spec RELOADED under the shared
    # writer lock - the pre-resolve snapshot must never be replayed wholesale
    # (a concurrent flowctl update to the same spec landing while the GraphQL
    # request was in flight would be silently erased; create/persist_external
    # follow the same reload-merge rule). The durable-collision scan runs
    # INSIDE the same critical section via collision_id: an unlocked pre-scan
    # is a check-then-lock race - two specs completing/persisting the same
    # durable id could both pass it, then both serialized writes succeed.
    def _complete(t: dict):
        # Re-check the link state INSIDE the lock (persist_external pattern):
        # if the tracker identity changed while the GraphQL resolve was in
        # flight (e.g. sync set-tracker-id wrote a durable id), an
        # unconditional merge would silently repoint the spec to the
        # resolution result for the OLD identifier. Refuse and persist
        # nothing; the caller re-runs against the new state.
        state = derive_link_state(t)
        if state == "identifier_only" and t.get("identifier") == identifier:
            return {**t, **link_fields}
        return TrackerError(
            ErrorClass.CONFLICT,
            f"spec {spec_id!r} tracker changed while UUID resolution was in "
            f"flight (now {state}, identifier={t.get('identifier')!r}); "
            "refusing to overwrite; re-run reconcile against the new state",
            subtype="unlinked" if state == "unlinked" else "already_linked",
            details={"linkState": state, "identifier": t.get("identifier"),
                     "id": t.get("id")})

    persisted = locked_tracker_write(
        flow_dir, spec_id, _complete, collision_id=resolved["id"])
    if isinstance(persisted, TrackerError):
        return persisted
    return {"id": persisted["id"], "identifier": persisted["identifier"],
            "url": persisted.get("url"), "linkState": "linked",
            "completed": True}
