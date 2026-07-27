"""Spec-aware `tracker relate` verb (fn-140.4).

Reproduces fn-64's contract: depRelations ledger (same edge-key semantics as
flowctl), additive-only, completed-blocker skip, never-clobber-on-collision
(defer + receipt, never overwrite). <!-- flow:deps --> body writing / hashing
is task .5 - marker constants live in relate.ledger for import.

GitHub: native sub_issues + structured degraded hierarchy only; body-block
deferred to .5 (see relate.providers module docstring).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import (ACTIVE, Execute, Result, default_tracker, dict_,
                                 load_spec, read_config, tracker_type,
                                 write_sync_receipt, write_tracker_block)
from ..types import ErrorClass, TrackerError
from . import providers as P
from .ledger import (blocker_completed, caps_of, dep_relation_key, ledger_append,
                     ledger_has, require_linked_pair)

__all__ = [
    "FLOW_DEPS_CLOSE",
    "FLOW_DEPS_OPEN",
    "dep_relation_key",
    "relate",
    "run",
]

# Re-export marker constants for .5 consumers.
from .ledger import FLOW_DEPS_CLOSE, FLOW_DEPS_OPEN  # noqa: E402, F401


def _locator(tracker: dict) -> Result:
    durable = tracker.get("id")
    display = tracker.get("identifier")
    if not isinstance(durable, str) or not durable.strip():
        return TrackerError(ErrorClass.UNRESOLVED, "tracker.id missing",
                            subtype="durable")
    if not isinstance(display, str) or not display.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "tracker.identifier (display) required for relate",
                            subtype="locator")
    return {"durable": durable.strip(), "display": display.strip()}


def relate(flow_dir, spec_id: str, *, blocked_by: str,
           event: Optional[str] = None,
           execute: Execute = default_execute) -> Result:
    """Project A is-blocked-by B. Never raises across the boundary."""
    flow_dir = Path(flow_dir)
    if not spec_id or not blocked_by:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "relate requires <spec-id> --blocked-by <other-spec-id>",
                            subtype="args")
    if spec_id == blocked_by:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "a spec cannot be blocked by itself",
                            subtype="self_edge")

    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    loaded_a = load_spec(flow_dir, spec_id)
    if isinstance(loaded_a, TrackerError):
        return loaded_a
    path_a, spec_a = loaded_a
    loaded_b = load_spec(flow_dir, blocked_by)
    if isinstance(loaded_b, TrackerError):
        return loaded_b
    _path_b, spec_b = loaded_b

    tracker_a = {**default_tracker(), **dict_(spec_a.get("tracker"))}
    tracker_b = {**default_tracker(), **dict_(spec_b.get("tracker"))}

    pair_err = require_linked_pair(tracker_a, tracker_b,
                                   self_id=spec_id, other_id=blocked_by)
    if pair_err:
        return pair_err

    from_id = str(tracker_a["id"])
    to_id = str(tracker_b["id"])
    key = dep_relation_key(from_id, to_id)

    # Completed-blocker: local status of B - do NOT project.
    if blocker_completed(spec_b.get("status")):
        write_sync_receipt(
            flow_dir, spec_id=spec_id, status="noop",
            tracker_id=from_id, event=event, transport=provider,
            note="completed-blocker: dependency is done/closed; not projected",
        )
        return {
            "kind": "skipped",
            "reason": "completed_blocker",
            "from": spec_id,
            "to": blocked_by,
            "key": key,
            "lastSyncedAt": tracker_a.get("lastSyncedAt"),
        }

    # Idempotent ledger hit → no-op (do not bump updatedAt).
    if ledger_has(tracker_a, key):
        return {
            "kind": "noop",
            "reason": "already_recorded",
            "from": spec_id,
            "to": blocked_by,
            "key": key,
            "depRelations": tracker_a.get("depRelations") or [],
        }

    loc_a = _locator(tracker_a)
    if isinstance(loc_a, TrackerError):
        return loc_a
    loc_b = _locator(tracker_b)
    if isinstance(loc_b, TrackerError):
        return loc_b

    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)

    caps = caps_of(config)
    fn = P.PROVIDERS.get(provider)
    if fn is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    # Foreign-edge collision probe: provider reports already=True but we have
    # no ledger entry → never-clobber (defer), do not claim ownership.
    # Providers return already=True when the tracker-visible edge exists.
    # We call the provider; if already and not in ledger → defer.

    kwargs: dict = {
        "from_id": from_id, "to_id": to_id,
        "from_display": loc_a["display"], "to_display": loc_b["display"],
    }
    if provider == "gitlab":
        plan = None
        source = caps.get("_source") if isinstance(caps.get("_source"), dict) else {}
        plan = source.get("gitlabPlan")
        out = fn(config, ex, **kwargs, blocked_by=bool(caps.get("blockedBy")),
                 plan=plan)
    else:
        out = fn(config, ex, **kwargs)

    if isinstance(out, TrackerError):
        return out

    degraded = out.get("degraded")

    if out.get("already"):
        # Foreign edge - defer, never overwrite / never claim in ledger.
        # (Ledger hit already returned above, so already ⇒ not ours.)
        write_sync_receipt(
            flow_dir, spec_id=spec_id, status="deferred",
            tracker_id=from_id, event=event, transport=provider,
            note="foreign edge present; never-clobber collision",
            degraded=degraded,
        )
        return {
            "kind": "defer",
            "reason": "foreign_edge",
            "from": spec_id,
            "to": blocked_by,
            "key": key,
            "degraded": degraded,
            "lastSyncedAt": tracker_a.get("lastSyncedAt"),
        }

    # Applied: append ledger + receipt.
    tracker_a = ledger_append(
        tracker_a, key=key, dep_spec=blocked_by,
        from_tracker_id=from_id, to_tracker_id=to_id,
    )
    werr = write_tracker_block(path_a, spec_a, tracker_a)
    if werr:
        return werr
    rerr = write_sync_receipt(
        flow_dir, spec_id=spec_id, status="pushed",
        tracker_id=from_id, event=event, transport=provider,
        note=f"projected blocked-by {blocked_by} via {out.get('form')}",
        degraded=degraded,
    )
    if rerr:
        return rerr
    return {
        "kind": "applied",
        "from": spec_id,
        "to": blocked_by,
        "key": key,
        "form": out.get("form"),
        "degraded": degraded,
        "depRelations": tracker_a.get("depRelations") or [],
    }


def run(flow_dir, *, spec_id: Optional[str] = None,
        blocked_by: Optional[str] = None, event: Optional[str] = None,
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
    if not spec_id or not blocked_by:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT,
            "relate requires <spec-id> --blocked-by <other-spec-id>",
            subtype="args"))
    try:
        out = relate(flow_dir, spec_id, blocked_by=blocked_by, event=event,
                     execute=execute)
    except Exception as exc:  # noqa: BLE001
        return envelope.failure(TrackerError(
            ErrorClass.TRANSPORT, f"relate verb raised: {exc}",
            subtype="unexpected"))
    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
