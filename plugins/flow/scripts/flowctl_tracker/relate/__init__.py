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

GitLab writes the <!-- flow:deps --> direction/provenance twin with every
native or degraded link and repairs it before finalizing an interrupted
create. Its whole-description read/replace is serialized with GitLab
sync-body and direct wire pushes by their shared remote-resource claim. Hash
exclusion remains sync-body's concern.

GitHub: native sub_issues is a HIERARCHY PROXY reported only in the structured
degraded field - never presented as a blocked-by relation; body-block
projection is .5's body machinery.
"""

from __future__ import annotations

import os
import socket
import time
import uuid
from pathlib import Path
from typing import Optional

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import (ACTIVE, Execute, Result, dict_, load_spec,
                                 merged_tracker, read_config, tracker_type,
                                 write_sync_receipt, write_tracker_block,
                                 atomic_write_json, leaf_is_safe)
from ..lifecycle.verbs import (_claim_body_mutation,
                               _ensure_create_first_ignored, _release_claim)
from ..types import ErrorClass, TrackerError
from . import providers as P
from .ledger import (blocker_completed, caps_of, claim_owner,
                     dep_relation_key, ledger_append, ledger_entry,
                     ledger_finalize, ledger_release, ledger_stamp_claim,
                     require_linked_pair)

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
    return None


def _ledger_write(flow_dir: Path, spec_id: str, mutate) -> Result:
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path, spec = reloaded
            tracker = merged_tracker(spec)
            tracker = mutate(tracker)
            werr = write_tracker_block(path, spec, tracker)
            if werr:
                return werr
            return tracker
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


#: TRANSPORT subtypes where the failed provider create is still KNOWN not to
#: have landed: the CLI process never spawned, or the server responded and
#: the parsed payload reported the mutation rejected (linear success!=true).
_TRANSPORT_NOT_LANDED = frozenset({"spawn", "mutation_failed"})


def _create_failure_not_landed(err: TrackerError) -> bool:
    """Did the failed provider create DEFINITELY not land?

    Non-TRANSPORT classes are parsed server rejections (auth, 4xx, rate
    limit, capability, not-found, conflict) or local pre-flight refusals -
    nothing was applied, so the pending claim may be released for an
    immediate retry. TRANSPORT is AMBIGUOUS (timeout / read / 5xx /
    malformed body: the request may have reached the server and the edge
    may exist) except the subtypes above - ambiguous failures must keep the
    pending entry so the repair path can finalize against the remote probe
    on retry instead of duplicating the create."""
    if "relate-create" in ((err.details or {}).get("completed_steps") or []):
        return False
    if err.cls is not ErrorClass.TRANSPORT:
        return True
    return err.subtype in _TRANSPORT_NOT_LANDED


def _ledger_release(flow_dir: Path, spec_id: str, *, key: str) -> None:
    """Best-effort removal of OUR pending claim after an OBSERVED provider
    create failure known not to have landed (mirrors lifecycle's
    _release_claim on the create-first record). Without this, the dead prior
    pid looked live for the full STALE_OWNER_S window and ordinary immediate
    retries failed as concurrent_claim. Never raises; on any failure the
    pending entry simply remains and the staleness rules recover as before."""
    out = _ledger_write(flow_dir, spec_id,
                        lambda t: ledger_release(t, key=key))
    # Best-effort by design: a TrackerError here is swallowed - the caller
    # is already returning the (more informative) create failure.
    del out


def _pending_claim_live(entry: dict) -> bool:
    """Is this pending entry owned by a LIVE concurrent invocation?

    The owner triple ({pid, host, claimedAt}) mirrors lifecycle create-first
    claims, judged by config_lock's owner rules: within STALE_OWNER_S the
    claim is live; past it, a dead pid ON THIS HOST is a crashed run's
    leftover (stale, reclaimable); another host's pid space is unknowable
    (shared/network checkout) so we fail closed (live). Our OWN pid+host is
    never a concurrent owner - it is this process's earlier failed attempt,
    free to retry. Entries without the triple (wave-1 shape, or written by an
    older version) fall back to updatedAt age: recent means possibly live,
    old or unparsable means stale (preserving the wave-1 interrupted-run
    retry semantics)."""
    import os  # noqa: PLC0415
    import socket  # noqa: PLC0415
    import time  # noqa: PLC0415
    from ..config_lock import STALE_OWNER_S, _pid_alive  # noqa: PLC0415
    now = time.time()
    try:
        claimed_at = float(entry["claimedAt"])
        pid = int(entry["pid"])
        host = str(entry["host"])
    except (KeyError, TypeError, ValueError):
        from datetime import datetime, timezone  # noqa: PLC0415
        raw = entry.get("updatedAt")
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return False
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt.timestamp()) <= STALE_OWNER_S
    if host == socket.gethostname() and pid == os.getpid():
        return False
    if (now - claimed_at) <= STALE_OWNER_S:
        return True
    if host != socket.gethostname():
        return True
    return _pid_alive(pid)


def _concurrent_claim_error(dep_spec: str, key: str) -> TrackerError:
    return TrackerError(
        ErrorClass.CONFLICT,
        f"a concurrent relate invocation claimed the blocked-by "
        f"edge to {dep_spec} first; no mutation performed by this "
        "invocation - re-run relate after it completes to verify "
        "or heal the ledger",
        subtype="concurrent_claim",
        details={"recoverable": True, "key": key})


def _relinked_error(spec_id: str, dep_spec: str, *, expected_from: str,
                    expected_to: str, current_from, current_to) -> TrackerError:
    return TrackerError(
        ErrorClass.CONFLICT,
        f"tracker link for {spec_id} or {dep_spec} changed while this relate "
        "invocation was in flight (a spec was relinked to a different "
        "issue); refusing to claim under the stale identity - nothing "
        "written, no mutation performed by this invocation; re-run relate "
        "against the current link state",
        subtype="relinked",
        details={"recoverable": True,
                 "expected": {"from": expected_from, "to": expected_to},
                 "current": {"from": current_from, "to": current_to}})


def _claim_identity_drift(flow_dir: Path, spec_id: str, dep_spec: str, *,
                          tracker: dict, from_id: str, to_id: str
                          ) -> Optional[TrackerError]:
    """Revalidate BOTH linked identities INSIDE the claim's critical section
    (the wave-10 complete_identifier_only pattern: re-check state under the
    lock, refuse and persist nothing on drift). The pair snapshot this
    invocation classified against was taken BEFORE the probe and guard ran;
    if either spec was relinked in that window, the key/from/to computed from
    the snapshot belong to the OLD issues - claiming would attach an old-ID
    ledger entry to the newly linked spec and then create the remote edge
    between the old issues (orphaned relation, ledger on the wrong identity).
    `tracker` is the caller's RELOADED tracker block for `spec_id` (already
    loaded under the same lock); the dep spec is reloaded here. Returns a
    CONFLICT/relinked TrackerError on drift, None when both durable ids still
    match - never raises."""
    current_from = tracker.get("id")
    reloaded_dep = load_spec(flow_dir, dep_spec)
    if isinstance(reloaded_dep, TrackerError):
        return reloaded_dep
    _dep_path, dep = reloaded_dep
    current_to = merged_tracker(dep).get("id")
    if (isinstance(current_from, str) and current_from.strip() == from_id
            and isinstance(current_to, str)
            and current_to.strip() == to_id):
        return None
    return _relinked_error(spec_id, dep_spec,
                           expected_from=from_id, expected_to=to_id,
                           current_from=current_from, current_to=current_to)


def _post_probe_identity_drift(flow_dir: Path, spec_id: str, dep_spec: str, *,
                               from_id: str, to_id: str
                               ) -> Optional[TrackerError]:
    """Revalidate both durable identities after the remote relation probe.

    Collision branches do not take a ledger claim, yet they emit durable
    local side effects (a deferred-review entry and a receipt). A relink can
    land while the probe is in flight, making its result and the pre-probe
    ledger snapshot belong to the old tracker IDs. Recheck under the shared
    writer lock before classification can emit those side effects.
    """
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            _path, spec = reloaded
            return _claim_identity_drift(
                flow_dir, spec_id, dep_spec, tracker=merged_tracker(spec),
                from_id=from_id, to_id=to_id)
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")


def _ledger_reclaim(flow_dir: Path, spec_id: str, *, key: str,
                    dep_spec: str, from_id: str, to_id: str) -> Result:
    """RECLAIM a stale pending entry (crashed run's leftover) by stamping OUR
    owner triple onto it under the shared writer lock. Re-checks liveness on
    the RELOADED entry inside the lock: if another invocation reclaimed (or
    finalized) it since our snapshot, this invocation backs off instead of
    issuing a duplicate create. Both linked identities are revalidated
    against from/to first - a relink since the pair load aborts
    (CONFLICT/relinked) rather than reclaiming a stale-identity entry.
    Returns the persisted tracker block, or a TrackerError - never raises."""
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir), spec_sidecar_lock(flow_dir, spec_id):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path, spec = reloaded
            tracker = merged_tracker(spec)
            derr = _claim_identity_drift(flow_dir, spec_id, dep_spec,
                                         tracker=tracker,
                                         from_id=from_id, to_id=to_id)
            if derr:
                return derr
            entry = ledger_entry(tracker, key)
            if (entry is None or entry.get("status") != "pending"
                    or _pending_claim_live(entry)):
                return _concurrent_claim_error(dep_spec, key)
            tracker = ledger_stamp_claim(tracker, key=key)
            werr = write_tracker_block(path, spec, tracker)
            if werr:
                return werr
            return tracker
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


def _ledger_finalize_guarded(flow_dir: Path, spec_id: str, dep_spec: str, *,
                             key: str, from_id: str, to_id: str,
                             form=None, repair: bool = False) -> Result:
    """FINALIZE the pending entry under the shared writer lock, revalidating
    both linked identities against the from/to this invocation claimed with
    (the wave-11 recheck, one step later: locks never span the provider
    mutation, so a relink can land between the claim's release and this
    finalize - without the recheck the old-ID entry would be finalized onto
    the newly linked spec). On drift the pending claim is REMOVED, never
    finalized, and the returned CONFLICT/relinked carries honest evidence:
    on the create path (repair=False) the landed remote mutation
    (details.completed_steps + edge identity, wave-8 decoration) - the
    create against the OLD issues cannot be un-sent, so the orphan edge is
    surfaced for a human instead of silently recorded under the wrong
    identity. On the REPAIR path (repair=True: a pending entry from an
    interrupted earlier run whose edge the probe found already on the
    tracker) THIS invocation performed no provider mutation, so the refusal
    carries the edge identity but NO completed_steps - the remote edge
    predates this run. Returns the persisted tracker block, or a
    TrackerError - never raises."""
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir), spec_sidecar_lock(flow_dir, spec_id):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path, spec = reloaded
            tracker = merged_tracker(spec)
            derr = _claim_identity_drift(flow_dir, spec_id, dep_spec,
                                         tracker=tracker,
                                         from_id=from_id, to_id=to_id)
            if derr is None:
                tracker = ledger_finalize(tracker, key=key)
                werr = write_tracker_block(path, spec, tracker)
                if werr:
                    return werr
                return tracker
            if derr.subtype != "relinked":
                # Dep spec unreadable etc. - keep the pending entry so the
                # repair path can finalize on retry; the caller wraps this
                # as the recoverable ledger_finalize partial success.
                return derr
            # Drift: drop the pending claim (keyed by the OLD ids, so no
            # future run of the new pair would ever match it). force=True:
            # on the repair path the entry was claimed by an earlier
            # interrupted run (different owner triple), and after the relink
            # it can never be validly finalized by anyone. Best-effort -
            # the drift evidence below is the primary outcome either way,
            # but the cleanup result is reported honestly: a failed
            # tracker-block write leaves the old-ID pending claim attached
            # to the relinked spec, and claiming it was removed would send
            # the operator hunting a ghost (mirrors the receipt_write_failed
            # decoration: the failure rides alongside, structured, never
            # masking the relink conflict).
            released = ledger_release(tracker, key=key, force=True)
            werr = write_tracker_block(path, spec, released)
            import dataclasses  # noqa: PLC0415
            extra: dict = {"recoverable": False, "key": key,
                           "from": spec_id, "to": dep_spec}
            if werr is None:
                claim_note = "pending claim removed"
                extra["cleanup"] = {"released": True}
            else:
                claim_note = (
                    "removing the pending claim FAILED - the stale old-ID "
                    "entry is still attached to the relinked spec")
                extra["cleanup"] = {
                    "released": False,
                    "error_class": werr.cls.value,
                    "subtype": werr.subtype,
                    "message": werr.message,
                }
            if repair:
                # No mutation was performed by THIS invocation: the remote
                # edge predates this run (interrupted earlier create). No
                # completed_steps - false mutation evidence would misattribute
                # the edge to this run.
                message = (
                    f"tracker link for {spec_id} or {dep_spec} changed while "
                    "the remote edge was being probed; the remote blocked-by "
                    "edge predates this run (no provider mutation was "
                    "performed) - the ledger was NOT finalized onto the "
                    f"relinked spec ({claim_note}); review the stale "
                    "edge between the OLD issues on the tracker")
            else:
                message = (
                    f"tracker link for {spec_id} or {dep_spec} changed "
                    "while the provider mutation was in flight; the "
                    "remote blocked-by edge WAS created between the OLD "
                    "issues and cannot be un-sent - the ledger was NOT "
                    "finalized onto the relinked spec "
                    f"({claim_note}); review the orphan edge on the tracker")
                extra["completed_steps"] = ["relate-create"]
                extra["form"] = form
            return dataclasses.replace(
                derr, message=message,
                details={**(derr.details or {}), **extra})
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


def _ledger_claim(flow_dir: Path, spec_id: str, *, key: str, dep_spec: str,
                  from_id: str, to_id: str) -> Result:
    """CLAIM the edge by inserting the pending entry under the shared .flow
    writer lock. Re-checks the RELOADED ledger inside the lock: an entry that
    appeared since the pre-classification snapshot belongs to a live
    concurrent relate invocation, so THIS invocation must not proceed to the
    provider mutation (only the inserter mutates - otherwise both workers
    probe the edge as absent and both create). Stale interrupted-run pending
    entries never reach this path: they existed at snapshot time and take the
    repair/retry classification branches instead. Also revalidates BOTH
    linked identities against the from/to ids this invocation loaded at
    start: a spec relinked after the pair load aborts (CONFLICT/relinked)
    instead of claiming under the stale identity. Returns the persisted
    tracker block on a successful claim, or a TrackerError - never raises."""
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir), spec_sidecar_lock(flow_dir, spec_id):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            path, spec = reloaded
            tracker = merged_tracker(spec)
            derr = _claim_identity_drift(flow_dir, spec_id, dep_spec,
                                         tracker=tracker,
                                         from_id=from_id, to_id=to_id)
            if derr:
                return derr
            if ledger_entry(tracker, key) is not None:
                return _concurrent_claim_error(dep_spec, key)
            tracker = ledger_append(
                tracker, key=key, dep_spec=dep_spec,
                from_tracker_id=from_id, to_tracker_id=to_id,
                status="pending", claim=claim_owner())
            werr = write_tracker_block(path, spec, tracker)
            if werr:
                return werr
            return tracker
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


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


def _claim_relate_pair(flow_dir: Path, spec_id: str, blocked_by: str,
                       provider: str) -> Result:
    """Claim both linked specs for the complete relate transaction."""
    token = uuid.uuid4().hex
    claim_paths = [
        flow_dir / "create-first" / f"relate-{sid}-{token}.json"
        for sid in sorted((spec_id, blocked_by))
    ]
    for rec_path in claim_paths:
        unsafe = leaf_is_safe(flow_dir / "create-first", rec_path)
        if unsafe:
            return unsafe
    secured = _ensure_create_first_ignored(flow_dir)
    if secured is not None:
        return secured

    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            owner = {
                "status": "pending",
                "op": "relate",
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "claimedAt": time.time(),
                "transport": provider,
                "specId": spec_id,
                "blockedBy": blocked_by,
            }
            written = []
            for rec_path in claim_paths:
                cerr = atomic_write_json(rec_path, owner)
                if cerr:
                    for prior_path in written:
                        _release_claim(prior_path)
                    return cerr
                written.append(rec_path)
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    return claim_paths


def _write_relate_receipt(enabled: bool, flow_dir: Path, **kwargs
                          ) -> Optional[TrackerError]:
    """Let facade composition suppress granular receipts."""
    if not enabled:
        return None
    return write_sync_receipt(flow_dir, **kwargs)


def relate(flow_dir, spec_id: str, *, blocked_by: str,
           event: Optional[str] = None,
           execute: Execute = default_execute,
           write_receipt: bool = True) -> Result:
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

    claimed = _claim_relate_pair(flow_dir, spec_id, blocked_by, provider)
    if isinstance(claimed, TrackerError):
        return claimed
    body_claim = None
    if provider == "gitlab":
        claimed_spec = load_spec(flow_dir, spec_id)
        if isinstance(claimed_spec, TrackerError):
            for rec_path in claimed:
                _release_claim(rec_path)
            return claimed_spec
        _claimed_path, claimed_data = claimed_spec
        claimed_locator = _locator(merged_tracker(claimed_data))
        if isinstance(claimed_locator, TrackerError):
            for rec_path in claimed:
                _release_claim(rec_path)
            return claimed_locator
        body_claim = _claim_body_mutation(
            flow_dir, provider, claimed_locator, operation="relate",
            spec_id=spec_id)
        if isinstance(body_claim, TrackerError):
            for rec_path in claimed:
                _release_claim(rec_path)
            return body_claim
    try:
        return _relate_txn(
            flow_dir, spec_id, blocked_by=blocked_by, event=event,
            execute=execute, write_receipt=write_receipt)
    finally:
        if body_claim is not None:
            _release_claim(body_claim)
        for rec_path in claimed:
            _release_claim(rec_path)


def _relate_txn(flow_dir: Path, spec_id: str, *, blocked_by: str,
                event: Optional[str], execute: Execute,
                write_receipt: bool, prepared: Optional[dict] = None) -> Result:
    """Run probe, mutation, and finalize while both spec claims are live."""
    config = prepared["config"] if prepared is not None else read_config(flow_dir)
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

    tracker_a = merged_tracker(spec_a)
    tracker_b = merged_tracker(spec_b)

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
    idea_err = P.jira_idea_guard(provider, config, ex, locators=(loc_a, loc_b))
    if idea_err:
        return idea_err

    # Resolve Jira's configurable blocking type once and share it between the
    # probe and mutation via the in-memory config. No blocks-semantics type is
    # a deferred capability decision, not permission to force stock "Blocks".
    if provider == "jira":
        blocks_type = P.jira_blocks_type(config, ex)
        if isinstance(blocks_type, TrackerError):
            if blocks_type.subtype != "blocks_link_type":
                return blocks_type
            qerr = _queue_conflict(
                flow_dir, spec_id,
                summary="Jira has no resolved blocks-semantics issue link type",
                reason="set tracker.perTracker.blocksLinkType, then retry")
            if qerr:
                return qerr
            rerr = _write_relate_receipt(
                write_receipt,
                flow_dir, spec_id=spec_id, status="queued",
                tracker_id=from_id, event=event, transport=provider,
                note="no Jira blocks link type; relation deferred")
            if rerr:
                return rerr
            return {
                "kind": "queued",
                "reason": "no_blocks_link_type",
                "from": spec_id,
                "to": blocked_by,
                "key": key,
                "lastSyncedAt": tracker_a.get("lastSyncedAt"),
            }

    caps = caps_of(config)
    fn = P.PROVIDERS.get(provider)
    probe = P.PROBES.get(provider)
    if fn is None or probe is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    kwargs: dict = {
        "from_id": from_id, "to_id": to_id,
        "from_display": loc_a["display"], "to_display": loc_b["display"],
    }

    # GitHub/GitLab relation paths address issues by display (number/IID):
    # validate display -> durable for BOTH ends BEFORE any probe or mutation
    # (wire write-verb parity), so a moved, repointed, or stale identifier
    # aborts instead of inspecting or relating unrelated issues.
    if prepared is not None:
        if (loc_a, loc_b) != prepared["locators"]:
            return _relinked_error(spec_id, blocked_by,
                                   expected_from=prepared["locators"][0]["durable"],
                                   expected_to=prepared["locators"][1]["durable"],
                                   current_from=from_id, current_to=to_id)
    else:
        verr = P.display_durable_guard(
            provider, config, ex, locators=(loc_a, loc_b))
        if verr:
            return verr

    # Read live relations from the tracker; no local ledger is stored.
    remote = prepared["remote"] if prepared is not None else probe(config, ex, **kwargs)
    if isinstance(remote, TrackerError):
        return remote

    if remote:
        if provider == "gitlab":
            body_out = P.gitlab_ensure_deps_block(
                config, ex, from_id=from_id,
                from_display=loc_a["display"], to_display=loc_b["display"])
            if isinstance(body_out, TrackerError):
                return body_out
            if body_out.get("written"):
                return {
                    "kind": "applied",
                    "reason": "deps_block_repaired",
                    "from": spec_id, "to": blocked_by, "key": key,
                    "form": None,
                    "completed_blocker": completed_blocker,
                    "degraded": None,
                }
        return {
            "kind": "noop",
            "reason": "already_present",
            "from": spec_id, "to": blocked_by, "key": key,
            "completed_blocker": completed_blocker,
        }

    if provider == "gitlab":
        source = caps.get("_source") if isinstance(caps.get("_source"), dict) else {}
        plan = source.get("gitlabPlan")
        out = fn(config, ex, **kwargs, blocked_by=bool(caps.get("blockedBy")),
                 plan=plan)
    else:
        out = fn(config, ex, **kwargs)

    if (provider == "github" and isinstance(out, TrackerError)
            and out.cls == ErrorClass.INVALID_INPUT and "422" in out.message):
        return {
            "kind": "queued",
            "reason": "github_single_parent",
            "from": spec_id, "to": blocked_by, "key": key,
        }

    if isinstance(out, TrackerError):
        if (out.details or {}).get("completed_steps"):
            import dataclasses  # noqa: PLC0415
            out = dataclasses.replace(out, details={
                **(out.details or {}),
                "key": key,
                "from": spec_id,
                "to": blocked_by,
            })
        return out

    return {
        "kind": "applied",
        "from": spec_id,
        "to": blocked_by,
        "key": key,
        "form": out.get("form"),
        "completed_blocker": completed_blocker,
        "degraded": out.get("degraded"),
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
