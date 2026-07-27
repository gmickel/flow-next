"""`tracker sync-body` - write/readback + paired merge base (fn-140.5).

Server readback is canonical for the tracker half. mergeBaseFlow stays the
exact --flow-file body (comparable to the local spec); mergeBaseTracker is
trackerBodyForMerge(readback). Both halves commit atomically under the shared
config_lock. Partial failure leaves the prior base untouched.

<!-- flow:deps --> is stripped at the hash boundary (R10 half deferred from
.4) and carried forward on every push write so a full-body update cannot
self-delete the block.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import (ACTIVE, Execute, Result, default_tracker, dict_,
                                 load_spec, now_iso, read_config, tracker_type,
                                 write_sync_receipt, write_tracker_block)
from ..lifecycle.linkstate import require_durable
from ..relate.ledger import FLOW_DEPS_CLOSE, FLOW_DEPS_OPEN
from ..types import ErrorClass, TrackerError

__all__ = [
    "FLOW_DEPS_CLOSE",
    "FLOW_DEPS_OPEN",
    "run",
    "sync_body",
    "trackerBodyForMerge",
]

# Region match is DOTALL so multi-line dep blocks strip as one unit.
_DEPS_RE = re.compile(
    re.escape(FLOW_DEPS_OPEN) + r".*?" + re.escape(FLOW_DEPS_CLOSE),
    re.DOTALL,
)


def trackerBodyForMerge(raw_body) -> str:
    """Hash-boundary transform: strip flow:deps + trailing-newline only.

    Does NOT predict Linear's markdown rewriting. Markers are included in the
    strip so the block never differs hashes or folds into the spec.
    """
    if raw_body is None:
        text = ""
    elif isinstance(raw_body, str):
        text = raw_body
    else:
        text = str(raw_body)
    text = _DEPS_RE.sub("", text)
    return text.rstrip("\n")


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_deps_region(raw_body: str) -> Optional[str]:
    m = _DEPS_RE.search(raw_body or "")
    return m.group(0) if m else None


def _carry_deps_forward(outgoing: str, current: str) -> str:
    """Write-side rule: preserve the existing flow:deps region on full-body update.

    renderFlowToTracker does not emit the block; without carry-forward a push
    self-deletes it and the next relate misreads that as human removal.
    """
    base = _DEPS_RE.sub("", outgoing or "")
    region = _extract_deps_region(current or "")
    if region is None:
        return base
    base = base.rstrip("\n")
    return f"{base}\n\n{region}\n"


def _raw_body(provider: str, parent: dict) -> str:
    """Extract issue body from a raw parent_read object (provider-shaped)."""
    if provider == "github":
        body = parent.get("body")
    elif provider == "jira":
        fields = parent.get("fields") if isinstance(parent.get("fields"), dict) else {}
        body = fields.get("description")
    else:
        # gitlab + linear store the body as description
        body = parent.get("description")
    if body is None:
        return ""
    return body if isinstance(body, str) else str(body)


def _locator(tracker: dict) -> Result:
    durable = tracker.get("id")
    display = tracker.get("identifier")
    if not isinstance(durable, str) or not durable.strip():
        return TrackerError(ErrorClass.UNRESOLVED, "tracker.id missing",
                            subtype="durable")
    if not isinstance(display, str) or not display.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "tracker.identifier (display) required for sync-body",
                            subtype="locator")
    return {"durable": durable.strip(), "display": display.strip()}


def _has_paired_base(tracker: dict) -> bool:
    return (tracker.get("mergeBaseFlow") is not None
            and tracker.get("mergeBaseTracker") is not None)


def _commit_paired_base(flow_dir: Path, spec_id: str, *,
                        flow_file_body: str, readback_body: str,
                        advance_synced: bool) -> Result:
    """Atomically write both merge-base halves (+ hashes, optional lastSyncedAt).

    Never writes one half alone (paired-snapshot invariant).
    """
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415

    merge_tracker = trackerBodyForMerge(readback_body)
    base_flow = flow_file_body if isinstance(flow_file_body, str) else str(flow_file_body)
    hash_flow = _content_hash(base_flow)
    hash_tracker = _content_hash(merge_tracker)
    try:
        with config_lock(flow_dir):
            loaded = load_spec(flow_dir, spec_id)
            if isinstance(loaded, TrackerError):
                return loaded
            path, spec_data = loaded
            tracker = {**default_tracker(), **dict_(spec_data.get("tracker"))}
            tracker["mergeBaseFlow"] = base_flow
            tracker["mergeBaseTracker"] = merge_tracker
            tracker["baseHashFlow"] = hash_flow
            tracker["baseHashTracker"] = hash_tracker
            if advance_synced:
                tracker["lastSyncedAt"] = now_iso()
            werr = write_tracker_block(path, spec_data, tracker)
            if werr:
                return werr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
    return {
        "mergeBaseFlow": base_flow,
        "mergeBaseTracker": merge_tracker,
        "baseHashFlow": hash_flow,
        "baseHashTracker": hash_tracker,
        "lastSyncedAt": tracker.get("lastSyncedAt"),
        "tracker": tracker,
    }


def sync_body(flow_dir, spec_id: str, *, flow_file_body: str,
              tracker_body: Optional[str] = None,
              direction: str = "push",
              event: Optional[str] = None,
              execute: Execute = default_execute) -> Result:
    """Write (optional) + readback + paired merge base. Never raises."""
    flow_dir = Path(flow_dir)
    if not spec_id:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "sync-body requires <spec-id>", subtype="args")
    if flow_file_body is None:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "sync-body requires --flow-file", subtype="args")
    if direction not in ("push", "pull"):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "direction must be push or pull", subtype="direction")

    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data = loaded
    tracker = {**default_tracker(), **dict_(spec_data.get("tracker"))}

    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return durable

    locator = _locator(tracker)
    if isinstance(locator, TrackerError):
        return locator

    from ..resolve_verb import bound_executor  # noqa: PLC0415
    from ..wire import dispatch as wire_dispatch  # noqa: PLC0415
    from ..wire import parent_read  # noqa: PLC0415
    ex = bound_executor(config, execute)

    parent = parent_read(provider, config, locator, ex, op="sync-body-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    current_body = _raw_body(provider, parent)

    if direction == "pull":
        committed = _commit_paired_base(
            flow_dir, spec_id,
            flow_file_body=flow_file_body,
            readback_body=current_body,
            advance_synced=True,
        )
        if isinstance(committed, TrackerError):
            return committed
        rerr = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="pulled",
            tracker_id=durable, event=event, transport=provider,
            note="sync-body pull seeded paired merge base",
        )
        if rerr:
            return TrackerError(
                rerr.cls, rerr.message, subtype=rerr.subtype,
                details={**(rerr.details or {}),
                         "completed_steps": ["paired-base"]},
                auto_retryable=rerr.auto_retryable)
        return {
            "kind": "pulled",
            "direction": "pull",
            "side_written": "none",
            "mergeBaseFlow": committed["mergeBaseFlow"],
            "mergeBaseTracker": committed["mergeBaseTracker"],
            "baseHashFlow": committed["baseHashFlow"],
            "baseHashTracker": committed["baseHashTracker"],
            "lastSyncedAt": committed["lastSyncedAt"],
            "degraded": None,
        }

    # --- push ---
    outgoing_src = tracker_body if tracker_body is not None else flow_file_body
    outgoing = _carry_deps_forward(outgoing_src, current_body)

    # No-write classification considers ALL THREE values (flow body, current
    # tracker body, and any explicitly supplied tracker body):
    #   * matches_current - the outgoing body already equals the tracker at
    #     the hash boundary: nothing to write.
    #   * echo fence - ONLY when no explicit tracker body was supplied: the
    #     flow side equals mergeBaseFlow and the tracker equals
    #     mergeBaseTracker, so Linear's rewrite of the last push must not look
    #     like divergence. An explicitly supplied --tracker-body-file is a
    #     newly APPROVED reconcile result and must never be suppressed by it.
    has_base = _has_paired_base(tracker)
    matches_current = (
        trackerBodyForMerge(outgoing) == trackerBodyForMerge(current_body))
    echo_fence = (
        tracker_body is None
        and has_base
        and flow_file_body == tracker.get("mergeBaseFlow")
        and trackerBodyForMerge(current_body) == tracker.get("mergeBaseTracker"))
    if matches_current or echo_fence:
        # No tracker write beyond the parent read. But the FLOW half may have
        # moved: a base whose mergeBaseFlow no longer equals the local body
        # must be re-committed (no mutation) or every later flow-side diff
        # against it is false.
        flow_unchanged = (
            has_base
            and flow_file_body == tracker.get("mergeBaseFlow")
            and trackerBodyForMerge(current_body) == tracker.get("mergeBaseTracker"))
        if flow_unchanged:
            return {
                "kind": "noop",
                "direction": "push",
                "side_written": "none",
                "reason": "unchanged",
                "mergeBaseFlow": tracker.get("mergeBaseFlow"),
                "mergeBaseTracker": tracker.get("mergeBaseTracker"),
                "baseHashFlow": tracker.get("baseHashFlow"),
                "baseHashTracker": tracker.get("baseHashTracker"),
                "lastSyncedAt": tracker.get("lastSyncedAt"),
                "degraded": None,
            }
        # No base yet: seed from current readback without writing.
        committed = _commit_paired_base(
            flow_dir, spec_id,
            flow_file_body=flow_file_body,
            readback_body=current_body,
            advance_synced=True,
        )
        if isinstance(committed, TrackerError):
            return committed
        rerr = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="pushed",
            tracker_id=durable, event=event, transport=provider,
            note="sync-body no-op seeded paired merge base",
        )
        if rerr:
            return TrackerError(
                rerr.cls, rerr.message, subtype=rerr.subtype,
                details={**(rerr.details or {}),
                         "completed_steps": ["paired-base"]},
                auto_retryable=rerr.auto_retryable)
        return {
            "kind": "seeded",
            "direction": "push",
            "side_written": "none",
            "mergeBaseFlow": committed["mergeBaseFlow"],
            "mergeBaseTracker": committed["mergeBaseTracker"],
            "baseHashFlow": committed["baseHashFlow"],
            "baseHashTracker": committed["baseHashTracker"],
            "lastSyncedAt": committed["lastSyncedAt"],
            "degraded": None,
        }

    updated = wire_dispatch(
        "update", config, locator=locator, title=None, body=outgoing, execute=ex)
    if isinstance(updated, TrackerError):
        return updated

    readback = wire_dispatch("read", config, locator=locator, execute=ex)
    if isinstance(readback, TrackerError):
        # Write succeeded but readback failed: prior merge base untouched.
        return TrackerError(
            readback.cls,
            f"sync-body readback failed after write: {readback.message}",
            subtype=readback.subtype or "readback",
            details={**(readback.details or {}),
                     "completed_steps": ["wire-update"]},
            auto_retryable=readback.auto_retryable,
        )
    readback_body = readback.get("body") if isinstance(readback, dict) else None
    if readback_body is None:
        readback_body = ""
    elif not isinstance(readback_body, str):
        readback_body = str(readback_body)

    committed = _commit_paired_base(
        flow_dir, spec_id,
        flow_file_body=flow_file_body,
        readback_body=readback_body,
        advance_synced=True,
    )
    if isinstance(committed, TrackerError):
        return TrackerError(
            committed.cls, committed.message, subtype=committed.subtype,
            details={**(committed.details or {}),
                     "completed_steps": ["wire-update", "wire-read"]},
            auto_retryable=committed.auto_retryable,
        )

    rerr = write_sync_receipt(
        flow_dir, spec_id=spec_id, status="pushed",
        tracker_id=durable, event=event, transport=provider,
        note="sync-body push wrote body + paired merge base",
    )
    if rerr:
        return TrackerError(
            rerr.cls, rerr.message, subtype=rerr.subtype,
            details={**(rerr.details or {}),
                     "completed_steps": ["wire-update", "wire-read", "paired-base"]},
            auto_retryable=rerr.auto_retryable)

    return {
        "kind": "pushed",
        "direction": "push",
        "side_written": "tracker",
        "mergeBaseFlow": committed["mergeBaseFlow"],
        "mergeBaseTracker": committed["mergeBaseTracker"],
        "baseHashFlow": committed["baseHashFlow"],
        "baseHashTracker": committed["baseHashTracker"],
        "lastSyncedAt": committed["lastSyncedAt"],
        "degraded": None,
    }


def run(flow_dir, *, spec_id: Optional[str] = None,
        flow_file: Optional[str] = None,
        tracker_body_file: Optional[str] = None,
        direction: str = "push",
        event: Optional[str] = None,
        execute: Execute = default_execute) -> tuple[str, int]:
    """Thin envelope shell - never raises across the boundary."""
    config = read_config(flow_dir)
    if tracker_type(config) is None:
        t = dict_(config.get("tracker")).get("type")
        if t is not None and t not in ACTIVE:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown tracker type {t!r}",
                subtype="provider"))
        return envelope.inactive()

    if not spec_id or not flow_file:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT,
            "sync-body requires <spec-id> --flow-file",
            subtype="args"))

    try:
        flow_file_body = Path(flow_file).read_text(encoding="utf-8")
    except OSError as exc:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT, f"cannot read --flow-file: {exc}",
            subtype="flow_file"))

    tracker_body = None
    if tracker_body_file is not None:
        try:
            tracker_body = Path(tracker_body_file).read_text(encoding="utf-8")
        except OSError as exc:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT,
                f"cannot read --tracker-body-file: {exc}",
                subtype="tracker_body_file"))

    try:
        out = sync_body(
            flow_dir, spec_id, flow_file_body=flow_file_body,
            tracker_body=tracker_body, direction=direction or "push",
            event=event, execute=execute)
    except Exception as exc:  # noqa: BLE001 - boundary must never raise
        return envelope.failure(TrackerError(
            ErrorClass.TRANSPORT, f"sync-body verb raised: {exc}",
            subtype="unexpected"))

    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
