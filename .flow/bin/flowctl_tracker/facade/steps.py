"""Shared step helpers for facade ops (fn-140.7)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..lifecycle.helpers import Execute, Result
from ..lifecycle.verbs import create as lifecycle_create
from ..status.verb import status as status_verb
from ..types import ErrorClass, TrackerError
from .helpers import (compute_status_to, link_state_of, load_tracker,
                      on_mcp_rung, step_status_from_status, worst_status,
                      write_aggregate_receipt)


def ok_result(data: dict, *, statuses: list, completed: list,
              degraded: Optional[dict] = None) -> dict:
    data = dict(data)
    data["completed_steps"] = list(completed)
    data["receipt_status"] = worst_status(statuses)
    if degraded is not None:
        data["degraded"] = degraded
    return data


def fail_result(err: TrackerError, *, completed: list,
                statuses: Optional[list] = None,
                flow_dir: Optional[Path] = None, spec_id: Optional[str] = None,
                event: Optional[str] = None, tracker_id: Optional[str] = None,
                transport: Optional[str] = None,
                degraded: Optional[dict] = None) -> TrackerError:
    """Attach completed_steps; write ONE aggregate receipt on partial success."""
    details = dict(err.details or {})
    prior = list(details.get("completed_steps") or [])
    merged = list(completed)
    for step in prior:
        if step not in merged:
            merged.append(step)
    details["completed_steps"] = merged
    rank_statuses = list(statuses or []) + ["errored"]
    receipt_status = worst_status(rank_statuses)
    details["receipt_status"] = receipt_status
    if flow_dir is not None and spec_id and event:
        rerr = write_aggregate_receipt(
            flow_dir, spec_id=spec_id, event=event, status=receipt_status,
            tracker_id=tracker_id, transport=transport, degraded=degraded,
            note=f"facade partial ({', '.join(merged)})",
            # The error's structured details ride into the receipt verbatim
            # (completed_steps, created identity) - durable evidence of what
            # landed, so an automated retry is not flying blind.
            details=details,
        )
        if rerr is not None:
            # The remote mutation landed but the receipt write itself failed:
            # ZERO receipts exist for this event, so sync check will report
            # the lifecycle event missing. Say so honestly - receipt_status
            # "errored" would claim an errored receipt was written. The
            # original error, completed_steps and identity evidence stay
            # verbatim; the write failure rides alongside, structured.
            details["receipt_status"] = "unwritten"
            details["receipt_write_failed"] = {
                "class": rerr.cls.value,
                "subtype": rerr.subtype,
                "message": rerr.message,
            }
    return TrackerError(
        err.cls, err.message, subtype=err.subtype,
        details=details, auto_retryable=err.auto_retryable,
        retry_after_s=err.retry_after_s,
    )


def create_if_unlinked(flow_dir: Path, spec_id: str, *, title: str, body: str,
                       flow_body: str,
                       config: dict, event: str, execute: Execute,
                       completed: list, statuses: list) -> Result:
    """No-op when linked/identifier_only; create + seed when unlinked.

    MCP rung + unlinked → external_action_required (no tracker request).

    A landed create is not complete until a fresh server readback seeds both
    merge-base halves atomically. In particular, comment-first and
    reconcile-first have no later body write that can safely establish the
    ancestor before a tracker-side edit occurs.
    """
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, _spec, tracker = loaded
    state = link_state_of(tracker)
    if state != "unlinked":
        return {"kind": "already_linked", "linkState": state,
                "id": tracker.get("id"), "identifier": tracker.get("identifier")}

    if on_mcp_rung(config):
        return TrackerError(
            ErrorClass.EXTERNAL_ACTION_REQUIRED,
            "Linear MCP rung: agent must create the issue, then "
            "persist-external",
            subtype="mcp_create",
            details={
                "action": "create",
                "payload": {"title": title, "body": body},
            },
        )

    out = lifecycle_create(
        flow_dir, spec_id, title=title, body=body, event=event,
        flow_body=flow_body, execute=execute, write_receipt=False,
    )
    if isinstance(out, TrackerError):
        return out
    completed.append("create")
    completed.append("paired-base")
    statuses.append("pushed")
    return {"kind": "created", **out}


def run_status(flow_dir: Path, spec_id: str, *, config: dict, event: str,
               execute: Execute, completed: list, statuses: list) -> Result:
    """Call status with --to from flow_to_normalized. noop/defer non-fatal."""
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data, _tracker = loaded
    to = compute_status_to(flow_dir, spec_id, config, spec_data, execute)
    out = status_verb(
        flow_dir, spec_id, to=to, event=event, execute=execute,
        write_receipt=False,
    )
    if isinstance(out, TrackerError):
        return out
    completed.append("status")
    statuses.append(step_status_from_status(out))
    return out
