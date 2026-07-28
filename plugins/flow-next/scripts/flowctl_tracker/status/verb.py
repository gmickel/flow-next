"""`tracker status` verb orchestration (fn-140.3).

require_durable → wire parent_read → merge_evidence → flow_to_normalized →
decide → provider write. Applied advances lastSyncedAt (+ receipt);
noop/conflict do not; defer writes a receipt (status deferred) without
advancing lastSyncedAt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..executor import execute as default_execute
from ..lifecycle.helpers import (Execute, Result, dict_, load_spec,
                                 merged_tracker, now_iso, read_config,
                                 tracker_type, write_sync_receipt,
                                 write_tracker_block)
from ..lifecycle.linkstate import require_durable
from ..types import ErrorClass, TrackerError
from .policy import (Decision, decide, decision_as_error, flow_to_normalized,
                     merge_evidence, validate_to_reason)
from .providers import (apply_status, enrich_linear_parent,
                        tracker_norm_from_parent)


def _completion_review_configured(config: dict) -> bool:
    review = dict_(config.get("review")).get("backend")
    if review is None:
        return False
    if isinstance(review, str) and review.strip().lower() in ("", "none", "off"):
        return False
    return True


def _load_tasks(flow_dir: Path, spec_id: str) -> list:
    tasks_dir = flow_dir / "tasks"
    if not tasks_dir.is_dir():
        return []
    out = []
    for path in sorted(tasks_dir.glob(f"{spec_id}.*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            out.append({"id": data.get("id"), "status": data.get("status") or "todo"})
    return out


def _locator(tracker: dict) -> Result:
    durable = tracker.get("id")
    display = tracker.get("identifier")
    if not isinstance(durable, str) or not durable.strip():
        return TrackerError(ErrorClass.UNRESOLVED, "tracker.id missing",
                            subtype="durable")
    if not isinstance(display, str) or not display.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "tracker.identifier (display) required for status",
                            subtype="locator")
    return {"durable": durable.strip(), "display": display.strip()}


def _persist_applied_state(flow_dir: Path, spec_id: str, *,
                           fold_local_done: bool,
                           expected_durable: Optional[str] = None,
                           expected_display: Optional[str] = None) -> Result:
    """Reload + merge ONLY status-owned fields + persist, serialized under the
    shared .flow writer lock (same pattern as relate._ledger_write and
    syncbody._commit_paired_base). The spec snapshot loaded before the parent,
    PR-evidence, and provider requests must never be written back wholesale -
    that would silently erase a concurrent update to the same spec.

    Identity guard (linkstate._complete pattern): the parent read, PR probe,
    and provider status write all ran against the identity captured BEFORE
    this lock. If the spec was repointed to a different issue while those
    were in flight, an unconditional merge would advance lastSyncedAt on the
    NEW link after mutating the OLD issue (and apply_local would fold done
    from the old issue's terminal state). Compare the reloaded block's
    durable/display identity inside the lock; on drift return a structured
    CONFLICT and persist nothing. Returns the persisted tracker block, or a
    TrackerError - never raises."""
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path, spec = reloaded
            tracker = merged_tracker(spec)
            if expected_durable is not None or expected_display is not None:
                got_durable = tracker.get("id")
                got_display = tracker.get("identifier")
                if got_durable != expected_durable or got_display != expected_display:
                    return TrackerError(
                        ErrorClass.CONFLICT,
                        f"spec {spec_id!r} tracker identity changed while the "
                        f"status write was in flight (evaluated "
                        f"{expected_display!r}/{expected_durable!r}, now "
                        f"{got_display!r}/{got_durable!r}); refusing to "
                        "persist; re-run status against the new link",
                        subtype="identity_drift",
                        details={
                            "expected": {"id": expected_durable,
                                         "identifier": expected_display},
                            "found": {"id": got_durable,
                                      "identifier": got_display},
                        },
                    )
            if fold_local_done:
                spec = dict(spec)
                spec["status"] = "done"
            tracker["lastSyncedAt"] = now_iso()
            werr = write_tracker_block(path, spec, tracker)
            if werr:
                return werr
            return tracker
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


def status(flow_dir, spec_id: str, *, to: str, reason: Optional[str] = None,
           event: Optional[str] = None,
           execute: Execute = default_execute,
           write_receipt: bool = True) -> Result:
    """Spec-aware status verb. Never raises across the boundary."""
    flow_dir = Path(flow_dir)
    # Validate --to/--reason BEFORE any mutation / network (garbage reason).
    bad = validate_to_reason(to, reason)
    if bad:
        return bad

    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    path, spec_data = loaded
    tracker = merged_tracker(spec_data)

    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return durable

    locator = _locator(tracker)
    if isinstance(locator, TrackerError):
        return locator

    from ..resolve_verb import bound_executor  # noqa: PLC0415
    from ..wire import parent_read  # noqa: PLC0415
    ex = bound_executor(config, execute)

    # Wire-style pre-mutation parent read + durable check.
    parent = parent_read(provider, config, locator, ex, op="status-parent-read")
    if isinstance(parent, TrackerError):
        return parent
    if provider == "linear":
        parent = enrich_linear_parent(ex, locator, parent)
        if isinstance(parent, TrackerError):
            return parent

    from ..lifecycle.helpers import destination as dest_of  # noqa: PLC0415
    dest = dest_of(config)
    if isinstance(dest, TrackerError):
        return dest

    tracker_norm = tracker_norm_from_parent(provider, parent, dest)
    if isinstance(tracker_norm, TrackerError):
        return tracker_norm

    pr_evidence = merge_evidence(config, spec_data, ex)
    tasks = _load_tasks(flow_dir, spec_id)
    flow_norm = flow_to_normalized(
        spec_data, pr_evidence, _completion_review_configured(config),
        tasks=tasks,
    )

    decision: Decision = decide(to, reason, flow_norm, tracker_norm, pr_evidence)
    err = decision_as_error(decision)
    if err:
        return err

    prior_synced = tracker.get("lastSyncedAt")

    if decision.kind == "noop":
        return {
            "kind": "noop",
            "to": to,
            "flow": flow_norm,
            "tracker": tracker_norm,
            "pr_evidence": pr_evidence,
            "lastSyncedAt": prior_synced,
        }

    if decision.kind == "apply_local":
        # Tracker-terminal wins: fold into the LOCAL spec (status + lastSyncedAt),
        # never issue a tracker mutation. A PM closing the issue is authoritative.
        persisted = _persist_applied_state(
            flow_dir, spec_id, fold_local_done=True,
            expected_durable=locator["durable"],
            expected_display=locator["display"])
        if isinstance(persisted, TrackerError):
            return persisted
        tracker = persisted
        if write_receipt:
            rerr = write_sync_receipt(
                flow_dir, spec_id=spec_id, status="pulled",
                tracker_id=durable, event=event, transport=provider,
                note=f"tracker-terminal folded locally ({tracker_norm})",
            )
            if rerr:
                import dataclasses  # noqa: PLC0415
                return dataclasses.replace(rerr, details={
                    **(rerr.details or {}),
                    "completed_steps": ["local-status", "lastSyncedAt"]})
        return {
            "kind": "applied_local",
            "to": to,
            "applied": decision.target_slot,
            "flow": flow_norm,
            "tracker": tracker_norm,
            "pr_evidence": pr_evidence,
            "lastSyncedAt": tracker["lastSyncedAt"],
        }

    if decision.kind == "defer":
        if write_receipt:
            rerr = write_sync_receipt(
                flow_dir, spec_id=spec_id, status="deferred",
                tracker_id=durable, event=event, transport=provider,
                note=f"status deferred ({decision.reason})",
                degraded=None,
            )
            if rerr:
                import dataclasses  # noqa: PLC0415
                return dataclasses.replace(rerr, details={
                    **(rerr.details or {}), "defer_reason": decision.reason,
                    "defer_details": decision.details})
        return {
            "kind": "defer",
            "reason": decision.reason,
            "to": to,
            "flow": flow_norm,
            "tracker": tracker_norm,
            "pr_evidence": pr_evidence,
            "lastSyncedAt": prior_synced,
            "details": decision.details,
        }

    # apply
    if decision.kind != "apply" or not decision.target_slot:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unhandled decision kind {decision.kind!r}",
                            subtype="decision")
    use_verified = (
        decision.target_slot == "done"
        and str(spec_data.get("completion_review_status") or "") == "ship"
        and pr_evidence == "merged"
    )
    written = apply_status(
        provider, config, locator, parent, ex,
        target_slot=decision.target_slot,
        close_reason=decision.close_reason or reason,
        use_verified_label=use_verified,
    )
    if isinstance(written, TrackerError):
        return written

    # Jira defer-from-apply (no legal transition) — receipt, no lastSyncedAt.
    if isinstance(written, dict) and written.get("defer"):
        if write_receipt:
            rerr = write_sync_receipt(
                flow_dir, spec_id=spec_id, status="deferred",
                tracker_id=durable, event=event, transport=provider,
                note=f"status deferred ({written.get('reason')})",
            )
            if rerr:
                import dataclasses  # noqa: PLC0415
                return dataclasses.replace(rerr, details={
                    **(rerr.details or {}), "defer_reason": written.get("reason"),
                    "defer_details": written})
        return {
            "kind": "defer",
            "reason": written.get("reason"),
            "to": to,
            "target": decision.target_slot,
            "flow": flow_norm,
            "tracker": tracker_norm,
            "pr_evidence": pr_evidence,
            "lastSyncedAt": prior_synced,
            "details": written,
        }

    if isinstance(written, dict) and written.get("noop"):
        return {
            "kind": "noop",
            "to": to,
            "flow": flow_norm,
            "tracker": tracker_norm,
            "pr_evidence": pr_evidence,
            "lastSyncedAt": prior_synced,
        }

    # Applied — advance lastSyncedAt + receipt.
    persisted = _persist_applied_state(
        flow_dir, spec_id, fold_local_done=False,
        expected_durable=locator["durable"],
        expected_display=locator["display"])
    if isinstance(persisted, TrackerError):
        # Provider mutation LANDED; only local persistence failed. Report the
        # completed write in the error details (mirrors the syncbody
        # post-write pattern) so receipts reflect the landed mutation and a
        # retry that sees the remote no-op is explainable. lastSyncedAt stays
        # behind on purpose - it advances only on fully applied.
        return TrackerError(
            persisted.cls,
            f"status persist failed after tracker write: {persisted.message}",
            subtype=persisted.subtype,
            details={**(persisted.details or {}),
                     "completed_steps": ["status-write"],
                     "target": decision.target_slot,
                     "write": written if isinstance(written, dict) else None},
            auto_retryable=persisted.auto_retryable,
        )
    tracker = persisted
    if write_receipt:
        rerr = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="updated",
            tracker_id=durable, event=event, transport=provider,
            note=f"status applied → {decision.target_slot}",
            degraded=written.get("degraded") if isinstance(written, dict) else None,
        )
        if rerr:
            import dataclasses  # noqa: PLC0415
            return dataclasses.replace(rerr, details={
                **(rerr.details or {}),
                "completed_steps": ["status-write", "lastSyncedAt"],
                "target": decision.target_slot,
            })
    return {
        "kind": "applied",
        "to": to,
        "applied": decision.target_slot,
        "flow": flow_norm,
        "tracker": tracker_norm,
        "pr_evidence": pr_evidence,
        "lastSyncedAt": tracker["lastSyncedAt"],
        "write": written,
    }
