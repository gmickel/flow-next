"""`tracker sync-body` - write/readback + paired merge base (fn-140.5).

Server readback is canonical for the tracker half. mergeBaseFlow stays the
exact --flow-file body (comparable to the local spec); mergeBaseTracker is
trackerBodyForMerge(readback). Both halves commit atomically under the shared
config_lock. Partial failure leaves the prior base untouched.

The WHOLE read/write/readback/commit transaction is serialized per spec via a
create-first claim (`syncbody-<spec-id>.json`) taken BEFORE any tracker I/O -
without it two overlapping invocations each finish their write/readback and
the OLDER one can acquire config_lock last, overwriting the newer paired base
with a stale pair (tracker holds body B, mergeBaseTracker records body A).
Every transaction additionally takes a provider + durable-issue keyed body claim,
shared with direct wire body updates and GitLab `relate`, because these paths
must not change the remote body between sync-body's read and paired-base commit.

<!-- flow:deps --> is stripped at the hash boundary (R10 half deferred from
.4) and carried forward on every push write so a full-body update cannot
self-delete the block.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
from pathlib import Path
from typing import Callable, Optional

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import (ACTIVE, Execute, Result, atomic_write_json,
                                 dict_, leaf_is_safe, load_spec,
                                 merged_tracker, now_iso, read_config,
                                 tracker_type, write_sync_receipt,
                                 write_tracker_block)
from ..lifecycle.linkstate import require_durable
from ..lifecycle.verbs import (_claim_body_mutation, _claim_is_stale,
                               _ensure_create_first_ignored, _release_claim)
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


def _deps_region_error(raw_body: str, *, label: str) -> Optional[TrackerError]:
    """Reject marker shapes that a whole-body rewrite cannot preserve safely."""
    text = raw_body or ""
    opens = text.count(FLOW_DEPS_OPEN)
    closes = text.count(FLOW_DEPS_CLOSE)
    if opens == closes == 0:
        return None
    valid = (
        opens == 1
        and closes == 1
        and text.find(FLOW_DEPS_OPEN) < text.find(FLOW_DEPS_CLOSE)
    )
    if valid:
        return None
    return TrackerError(
        ErrorClass.CONFLICT,
        f"{label} has multiple or unbalanced flow:deps regions; refusing "
        "lossy body normalization",
        subtype="deps_block",
        details={"openMarkers": opens, "closeMarkers": closes},
    )


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


def _raw_title(provider: str, parent: dict) -> str:
    """Extract the native issue title from a raw parent-read object."""
    if provider == "jira":
        fields = parent.get("fields") if isinstance(parent.get("fields"), dict) else {}
        title = fields.get("summary")
    else:
        title = parent.get("title")
    if title is None:
        return ""
    return title if isinstance(title, str) else str(title)


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
                        locator: dict,
                        flow_file_body: str, readback_body: str,
                        advance_synced: bool) -> Result:
    """Atomically write both merge-base halves (+ hashes, optional lastSyncedAt).

    Never writes one half alone (paired-snapshot invariant). ``locator`` is
    the durable/display identity the transaction's remote read/write used;
    the reloaded tracker block is re-checked against it INSIDE the critical
    section (linkstate's _complete pattern). The syncbody claim serializes
    sibling sync-body runs, NOT ``sync set-tracker-id`` - if that repoints
    the spec while our tracker I/O is in flight, committing bodies read from
    the OLD issue as the NEW issue's paired merge base makes every later
    reconcile merge against the wrong content. Refuse with structured
    CONFLICT and persist nothing.
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
            tracker = merged_tracker(spec_data)
            reloaded = _locator(tracker)
            if isinstance(reloaded, TrackerError) or reloaded != locator:
                now_id = tracker.get("id")
                now_display = tracker.get("identifier")
                return TrackerError(
                    ErrorClass.CONFLICT,
                    f"spec {spec_id!r} tracker identity changed while "
                    f"sync-body was in flight (transaction used "
                    f"{locator.get('display')!r}/{locator.get('durable')!r}, "
                    f"spec now has {now_display!r}/{now_id!r}); refusing to "
                    "commit merge base read from the old issue; re-run "
                    "sync-body against the new link",
                    subtype="identity_changed",
                    details={"specId": spec_id,
                             "transaction": dict(locator),
                             "current": {"durable": now_id,
                                         "display": now_display}})
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


def _claim_sync_body(flow_dir: Path, spec_id: str, rec_path: Path,
                     provider: str, *,
                     direction: str) -> Optional[TrackerError]:
    """Reserve the spec's sync-body transaction under the shared writer lock
    BEFORE any tracker read or write (create-first's claim pattern, keyed on
    the spec id). Two overlapping sync-body invocations for the same spec
    each perform write/readback before committing the paired base; without a
    claim the OLDER invocation can acquire config_lock last and overwrite the
    newer pair with a stale one - the tracker then holds body B while
    mergeBaseTracker records body A, so the next reconcile reports false
    divergence or merges against the wrong base. Under the lock: a live
    claim from another process refuses (syncbody_in_flight, retryable), a
    stale claim (dead pid on this host past the stale window,
    _claim_is_stale's owner rules) is reclaimed by overwriting, and OUR
    pending claim lands durably before any remote I/O. The claim is always
    released when the invocation finishes (success or failure): the paired
    base in the spec, not the claim file, is the durable record."""
    unsafe = leaf_is_safe(flow_dir / "create-first", rec_path)
    if unsafe:
        return unsafe
    secured = _ensure_create_first_ignored(flow_dir)
    if secured is not None:
        return secured
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            if rec_path.is_file():
                try:
                    prior = json.loads(rec_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    prior = None
                if (isinstance(prior, dict)
                        and prior.get("status") == "pending"
                        and not _claim_is_stale(prior, rec_path)):
                    return TrackerError(
                        ErrorClass.CONFLICT,
                        f"sync-body for spec {spec_id!r} is already in "
                        "flight in another process; retry after it finishes",
                        subtype="syncbody_in_flight",
                        details={"specId": spec_id,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OURS - same rule as create-first.
            claim = {"specId": spec_id, "status": "pending",
                     "op": "sync-body", "direction": direction,
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    return None


def sync_body(flow_dir, spec_id: str, *, flow_file_body: str,
              tracker_body: Optional[str] = None,
              expected_tracker_body: Optional[str] = None,
              tracker_read: Optional[Callable[[dict], Result]] = None,
              sync_title: bool = False,
              direction: str = "push",
              event: Optional[str] = None,
              execute: Execute = default_execute,
              write_receipt: bool = True) -> Result:
    """Write (optional) + readback + paired merge base. Never raises.

    Serialized per spec via a create-first claim taken before any tracker
    I/O; a live foreign claim refuses with structured CONFLICT
    (syncbody_in_flight, retryable) instead of interleaving to a mismatched
    pair. ``tracker_read`` is honored ONLY for ``direction="pull"``: when
    set, the transaction calls it with ITS OWN locator (loaded after the
    claim) instead of parent_read, and persists the returned wire-read body
    as the tracker half. The read therefore happens INSIDE the claimed
    transaction - a snapshot captured before the claim could pair an older
    read with a newer base, or commit the old issue's body under a
    repointed locator. ``sync_title`` is an internal facade seam:
    push/reconcile project the current spec title in the same update/readback
    transaction as the body; the standalone body verb keeps its body-only
    default.
    """
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

    rec_path = flow_dir / "create-first" / f"syncbody-{spec_id}.json"
    claimed = _claim_sync_body(flow_dir, spec_id, rec_path, provider,
                               direction=direction)
    if claimed is not None:
        return claimed
    claimed_spec = load_spec(flow_dir, spec_id)
    if isinstance(claimed_spec, TrackerError):
        _release_claim(rec_path)
        return claimed_spec
    _claimed_path, claimed_data = claimed_spec
    claimed_locator = _locator(merged_tracker(claimed_data))
    if isinstance(claimed_locator, TrackerError):
        _release_claim(rec_path)
        return claimed_locator
    body_claim = _claim_body_mutation(
        flow_dir, provider, claimed_locator,
        operation=f"sync-body-{direction}", spec_id=spec_id)
    if isinstance(body_claim, TrackerError):
        _release_claim(rec_path)
        return body_claim
    try:
        return _sync_body_txn(
            flow_dir, spec_id, config=config, provider=provider,
            flow_file_body=flow_file_body, tracker_body=tracker_body,
            expected_tracker_body=expected_tracker_body,
            tracker_read=tracker_read, sync_title=sync_title,
            direction=direction,
            event=event, execute=execute, write_receipt=write_receipt)
    finally:
        _release_claim(body_claim)
        _release_claim(rec_path)


def _sync_body_txn(flow_dir: Path, spec_id: str, *, config: dict,
                   provider: str, flow_file_body: str,
                   tracker_body: Optional[str],
                   expected_tracker_body: Optional[str],
                   tracker_read: Optional[Callable[[dict], Result]],
                   sync_title: bool,
                   direction: str, event: Optional[str],
                   execute: Execute, write_receipt: bool) -> Result:
    """The claimed transaction body: spec is (re)loaded AFTER the claim so
    the echo-fence/no-op checks see the base a just-finished sibling wrote,
    never a pre-claim snapshot."""
    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data = loaded
    tracker = merged_tracker(spec_data)
    desired_title = (
        str(spec_data.get("title") or spec_id) if sync_title else None)

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
    current_title = ""

    # Pull + caller-supplied reader: run the wire read HERE, inside the
    # claimed transaction and against the transaction's own locator. The
    # claim above and the identity guard in _commit_paired_base then cover
    # the read too: an overlapping pull cannot pair an older read with a
    # newer base, and a set-tracker-id repoint in the gap cannot commit the
    # old issue's body under the new locator.
    if direction == "pull" and tracker_read is not None:
        read_out = tracker_read(locator)
        if isinstance(read_out, TrackerError):
            return read_out
        raw = read_out.get("body") if isinstance(read_out, dict) else None
        if raw is None:
            current_body = ""
        elif isinstance(raw, str):
            current_body = raw
        else:
            current_body = str(raw)
    else:
        parent = parent_read(provider, config, locator, ex,
                             op="sync-body-parent-read")
        if isinstance(parent, TrackerError):
            return parent
        current_body = _raw_body(provider, parent)
        current_title = _raw_title(provider, parent)

    malformed = _deps_region_error(current_body, label="tracker body")
    if malformed is not None:
        return malformed
    if expected_tracker_body is not None:
        malformed = _deps_region_error(
            expected_tracker_body, label="expected tracker body")
        if malformed is not None:
            return malformed
    if tracker_body is not None:
        malformed = _deps_region_error(
            tracker_body, label="approved tracker body")
        if malformed is not None:
            return malformed

    if direction == "pull":
        if (expected_tracker_body is not None
                and trackerBodyForMerge(current_body)
                != trackerBodyForMerge(expected_tracker_body)):
            return TrackerError(
                ErrorClass.CONFLICT,
                "tracker body changed after the creating mutation; refusing "
                "to adopt the later readback as synchronized",
                subtype="readback_diverged",
                details={
                    "writtenHash": _content_hash(
                        trackerBodyForMerge(expected_tracker_body)),
                    "readbackHash": _content_hash(
                        trackerBodyForMerge(current_body)),
                },
            )
        committed = _commit_paired_base(
            flow_dir, spec_id, locator=locator,
            flow_file_body=flow_file_body,
            readback_body=current_body,
            advance_synced=True,
        )
        if isinstance(committed, TrackerError):
            return committed
        if write_receipt:
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
    if (expected_tracker_body is not None
            and trackerBodyForMerge(current_body)
            != trackerBodyForMerge(expected_tracker_body)):
        return TrackerError(
            ErrorClass.CONFLICT,
            "tracker body changed after the reconcile read; refusing to "
            "overwrite the newer remote edit; re-run reconcile",
            subtype="tracker_body_changed",
            details={"specId": spec_id, "recoverable": True},
            auto_retryable=True,
        )

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
    title_matches = desired_title is None or current_title == desired_title
    echo_fence = (
        tracker_body is None
        and has_base
        and flow_file_body == tracker.get("mergeBaseFlow")
        and trackerBodyForMerge(current_body) == tracker.get("mergeBaseTracker"))
    if title_matches and (matches_current or echo_fence):
        # No tracker write beyond the parent read. But the FLOW half may have
        # moved: a base whose mergeBaseFlow no longer equals the local body
        # must be re-committed (no mutation) or every later flow-side diff
        # against it is false.
        flow_unchanged = (
            has_base
            and flow_file_body == tracker.get("mergeBaseFlow")
            and trackerBodyForMerge(current_body) == tracker.get("mergeBaseTracker"))
        if flow_unchanged:
            if write_receipt:
                rerr = write_sync_receipt(
                    flow_dir, spec_id=spec_id, status="noop",
                    tracker_id=durable, event=event, transport=provider,
                    note="sync-body already converged")
                if rerr:
                    return rerr
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
            flow_dir, spec_id, locator=locator,
            flow_file_body=flow_file_body,
            readback_body=current_body,
            advance_synced=True,
        )
        if isinstance(committed, TrackerError):
            return committed
        if write_receipt:
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
        "update", config, locator=locator, title=desired_title, body=outgoing,
        execute=ex)
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

    updated_body = updated.get("body") if isinstance(updated, dict) else None
    if updated_body is None:
        updated_body = ""
    elif not isinstance(updated_body, str):
        updated_body = str(updated_body)
    if trackerBodyForMerge(updated_body) != trackerBodyForMerge(readback_body):
        # The mutation response is the server's acknowledgement of OUR write.
        # A different immediate readback means another remote edit won after
        # that acknowledgement. Never absorb it into the paired ancestor:
        # retain the prior base so the next pass surfaces real divergence.
        return TrackerError(
            ErrorClass.CONFLICT,
            "tracker body changed after wire update; refusing to adopt the "
            "later readback as synchronized",
            subtype="readback_diverged",
            details={
                "completed_steps": ["wire-update", "wire-read"],
                "writtenHash": _content_hash(
                    trackerBodyForMerge(updated_body)),
                "readbackHash": _content_hash(
                    trackerBodyForMerge(readback_body)),
            },
        )
    if desired_title is not None:
        updated_title = (
            updated.get("title") if isinstance(updated, dict) else None)
        readback_title = (
            readback.get("title") if isinstance(readback, dict) else None)
        if updated_title != desired_title or readback_title != desired_title:
            return TrackerError(
                ErrorClass.CONFLICT,
                "tracker title changed or was not applied after wire update; "
                "refusing to commit the paired base",
                subtype="title_readback_diverged",
                details={
                    "completed_steps": ["wire-update", "wire-read"],
                    "requestedTitle": desired_title,
                    "writtenTitle": updated_title,
                    "readbackTitle": readback_title,
                },
            )

    committed = _commit_paired_base(
        flow_dir, spec_id, locator=locator,
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

    if write_receipt:
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
    except (OSError, UnicodeDecodeError) as exc:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT, f"cannot read --flow-file: {exc}",
            subtype="flow_file"))

    tracker_body = None
    if tracker_body_file is not None:
        try:
            tracker_body = Path(tracker_body_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
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
