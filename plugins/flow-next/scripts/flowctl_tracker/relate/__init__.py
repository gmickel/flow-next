"""Spec-aware `tracker relate` verb (fn-140.4).

Reproduces fn-64's contract: depRelations ledger (same edge-key semantics as
flowctl), additive-only, never-clobber-on-collision (queued + receipt, never
overwrite). Completed blockers are PROJECTED - the relation stays visible on
the tracker as the historical ordering (docs/tracker-sync.md fn-64 rule);
only readiness gating excludes done deps, and that lives in flowctl's ready
computation, not here. The 4-way ledger x remote classification runs BEFORE
any mutation: ledger+remote noop, ledger+missing = human removal collision
(queued, default NOT re-created), unledgered+remote = foreign-edge collision
(queued), neither = create.

<!-- flow:deps --> body writing / hashing is task .5 - marker constants live
in relate.ledger for import (the spec's flow:deps-exclusion R-ID completes
there, where body hashing exists).

GitHub: native sub_issues is a HIERARCHY PROXY reported only in the structured
degraded field - never presented as a blocked-by relation; body-block
projection is .5's body machinery.
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


def _queue_conflict(flow_dir: Path, spec_id: str, *, summary: str,
                    reason: str) -> Optional[TrackerError]:
    """Append to the canonical deferred-decisions sink
    (.flow/review-deferred/<slug>.md) - the same queue `flowctl sync defer`
    uses, so relate collisions land where humans already look."""
    from datetime import datetime, timezone  # noqa: PLC0415
    sink_dir = Path(flow_dir) / "review-deferred"
    try:
        sink_dir.mkdir(parents=True, exist_ok=True)
        sink = sink_dir / "tracker-relate.md"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        lines = []
        if not sink.exists():
            lines.append("# Deferred review findings - tracker-relate\n")
        lines.append(f"\n## {ts} - tracker-sync conflict {spec_id}\n")
        lines.append(f"- **{summary}**\n  - reason: {reason}\n"
                     f"  - file: specs/{spec_id}.md\n")
        with open(sink, "a", encoding="utf-8") as f:
            f.write("".join(lines))
    except OSError as exc:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"cannot queue conflict: {exc}", subtype="queue")
    return None


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

    completed_blocker = blocker_completed(spec_b.get("status"))

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
    probe = P.PROBES.get(provider)
    if fn is None or probe is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    kwargs: dict = {
        "from_id": from_id, "to_id": to_id,
        "from_display": loc_a["display"], "to_display": loc_b["display"],
    }

    # 4-way ledger x remote classification BEFORE any mutation (fn-64):
    remote = probe(config, ex, **kwargs)
    if isinstance(remote, TrackerError):
        return remote
    in_ledger = ledger_has(tracker_a, key)

    if in_ledger and remote:
        return {
            "kind": "noop",
            "reason": "already_recorded",
            "from": spec_id, "to": blocked_by, "key": key,
            "completed_blocker": completed_blocker,
            "depRelations": tracker_a.get("depRelations") or [],
        }

    if in_ledger and not remote:
        # A human removed OUR tracker-visible edge: a deliberate decision.
        # Queued, default NOT re-created (adapter-interface.md linkPresent).
        qerr = _queue_conflict(
            flow_dir, spec_id,
            summary=f"flow-created blocked-by edge to {blocked_by} was removed "
                    "on the tracker",
            reason="human-removal collision; default NOT re-created")
        if qerr:
            return qerr
        rerr = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="queued",
            tracker_id=from_id, event=event, transport=provider,
            note="human-removal collision queued; edge not re-created")
        if rerr:
            return rerr
        return {
            "kind": "queued",
            "reason": "human_removed_edge",
            "from": spec_id, "to": blocked_by, "key": key,
            "lastSyncedAt": tracker_a.get("lastSyncedAt"),
        }

    if not in_ledger and remote:
        # Foreign edge - never clobber, never claim ownership.
        qerr = _queue_conflict(
            flow_dir, spec_id,
            summary=f"a blocked-by edge to {blocked_by} exists on the tracker "
                    "but is not flow's",
            reason="foreign-edge collision; never clobbered")
        if qerr:
            return qerr
        rerr = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="queued",
            tracker_id=from_id, event=event, transport=provider,
            note="foreign edge present; never-clobber collision queued")
        if rerr:
            return rerr
        return {
            "kind": "queued",
            "reason": "foreign_edge",
            "from": spec_id, "to": blocked_by, "key": key,
            "lastSyncedAt": tracker_a.get("lastSyncedAt"),
        }

    # Neither ledgered nor remote: CREATE. Completed blockers project too -
    # the relation is the board's historical ordering; readiness gating alone
    # treats done deps as satisfied (docs/tracker-sync.md fn-64 rule).
    if provider == "gitlab":
        source = caps.get("_source") if isinstance(caps.get("_source"), dict) else {}
        plan = source.get("gitlabPlan")
        out = fn(config, ex, **kwargs, blocked_by=bool(caps.get("blockedBy")),
                 plan=plan)
    else:
        out = fn(config, ex, **kwargs)

    if isinstance(out, TrackerError):
        return out

    degraded = out.get("degraded")

    # Applied: SERIALIZE the reload+append+persist under the shared .flow
    # writer lock - reload alone narrowed but did not close the lost-update
    # window (two relates could still reload the same pre-write state and the
    # second atomic replace dropped the first edge, which the next run then
    # misclassified as foreign).
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path_a, spec_a = reloaded
            tracker_a = {**default_tracker(), **dict_(spec_a.get("tracker"))}
            tracker_a = ledger_append(
                tracker_a, key=key, dep_spec=blocked_by,
                from_tracker_id=from_id, to_tracker_id=to_id,
            )
            werr = write_tracker_block(path_a, spec_a, tracker_a)
            if werr:
                return werr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
    # GitHub's sub_issues form is a HIERARCHY PROXY, never a blocked-by (R15).
    form = out.get("form")
    if form == "sub_issues":
        note = (f"hierarchy proxy recorded for {blocked_by} via sub_issues "
                "(degraded form - NOT a blocked-by relation)")
    else:
        note = f"projected blocked-by {blocked_by} via {form}"
    rerr = write_sync_receipt(
        flow_dir, spec_id=spec_id, status="pushed",
        tracker_id=from_id, event=event, transport=provider,
        note=note,
        degraded=degraded,
    )
    if rerr:
        return rerr
    return {
        "kind": "applied",
        "from": spec_id,
        "to": blocked_by,
        "key": key,
        "form": form,
        "completed_blocker": completed_blocker,
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
