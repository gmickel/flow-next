"""Lifecycle facade: `tracker sync --op push|pull|reconcile|comment` (fn-140.7).

Callers invoke one op; the facade owns create-if-unlinked, granular sequence,
comment marker + dedup, one aggregate event-tagged receipt, and structured
conflict/degradation. Judgment-bearing content is always an input file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import ACTIVE, Execute, dict_, read_config, tracker_type
from ..types import ErrorClass, TrackerError
from .helpers import validate_inputs
from .ops import op_comment, op_pull, op_push, op_reconcile

__all__ = ["run", "sync"]


def sync(flow_dir, spec_id: str, *, op: str, event: str,
         flow_file: Optional[str] = None, body_file: Optional[str] = None,
         comments_file: Optional[str] = None,
         source_body_file: Optional[str] = None,
         comment_file: Optional[str] = None,
         pr_url: Optional[str] = None,
         status_only: bool = False,
         execute: Execute = default_execute):
    """Compose one facade op. Returns data dict or TrackerError — never raises."""
    flow_dir = Path(flow_dir)
    bad = validate_inputs(
        op, flow_file=flow_file, body_file=body_file,
        comments_file=comments_file, source_body_file=source_body_file,
        comment_file=comment_file, pr_url=pr_url,
        event=event, status_only=status_only)
    if bad:
        return bad

    config = read_config(flow_dir)
    if tracker_type(config) is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    try:
        if op == "push":
            return op_push(
                flow_dir, spec_id, flow_file=flow_file or "",
                body_file=body_file or "", event=event,
                comment_file=comment_file, status_only=status_only,
                execute=execute)
        if op == "pull":
            return op_pull(
                flow_dir, spec_id, flow_file=flow_file or "",
                body_file=body_file or "", comments_file=comments_file or "",
                event=event, execute=execute)
        if op == "reconcile":
            return op_reconcile(
                flow_dir, spec_id, flow_file=flow_file or "",
                body_file=body_file or "", comments_file=comments_file or "",
                source_body_file=source_body_file or "",
                event=event, pr_url=pr_url, execute=execute)
        if op == "comment":
            return op_comment(
                flow_dir, spec_id, body_file=body_file or "",
                event=event, execute=execute)
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unknown op {op!r}", subtype="op")
    except Exception as exc:  # noqa: BLE001 - boundary must never raise
        return TrackerError(ErrorClass.TRANSPORT,
                            f"facade raised: {exc}", subtype="unexpected")


def _partial_failure(err: TrackerError) -> tuple[str, int]:
    """success:false + data.completed_steps (partial-success resume surface)."""
    details = dict(err.details or {})
    completed = details.pop("completed_steps", None) or []
    receipt_status = details.pop("receipt_status", None)
    base_payload, code = envelope.failure(err)
    try:
        payload = json.loads(base_payload)
    except (ValueError, TypeError):
        return base_payload, code
    data = {"completed_steps": completed}
    if receipt_status is not None:
        data["receipt_status"] = receipt_status
    # Keep remaining details under details; surface completed_steps on data.
    payload["data"] = data
    if isinstance(payload.get("details"), dict):
        # Avoid duplicating the same list under details once moved to data.
        payload["details"].pop("completed_steps", None)
        payload["details"].pop("receipt_status", None)
        if not payload["details"]:
            payload["details"] = None
    return json.dumps(payload, sort_keys=True), code


def run(flow_dir, *, spec_id: Optional[str] = None, op: Optional[str] = None,
        event: Optional[str] = None, flow_file: Optional[str] = None,
        body_file: Optional[str] = None,
        comments_file: Optional[str] = None,
        source_body_file: Optional[str] = None,
        comment_file: Optional[str] = None,
        pr_url: Optional[str] = None,
        status_only: bool = False,
        execute: Execute = default_execute) -> tuple[str, int]:
    """Thin envelope shell — never raises across the boundary."""
    config = read_config(flow_dir)
    if tracker_type(config) is None:
        t = dict_(config.get("tracker")).get("type")
        if t is not None and t not in ACTIVE:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown tracker type {t!r}",
                subtype="provider"))
        return envelope.inactive()

    if not spec_id or not op:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT,
            "tracker sync requires <spec-id> --op",
            subtype="args"))

    out = sync(flow_dir, spec_id, op=op, event=event or "",
               flow_file=flow_file, body_file=body_file,
               comments_file=comments_file,
               source_body_file=source_body_file,
               comment_file=comment_file, pr_url=pr_url,
               status_only=status_only,
               execute=execute)
    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        # Partial success: completed_steps present → include data.
        if out.details and out.details.get("completed_steps"):
            # Also write the aggregate receipt for partial success when the
            # ops layer already recorded receipt_status on the error.
            return _partial_failure(out)
        return envelope.failure(out)
    return envelope.success(out)
