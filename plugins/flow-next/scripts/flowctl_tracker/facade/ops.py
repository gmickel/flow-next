"""Four facade ops: push / pull / reconcile / comment (fn-140.7).

Compose lifecycle + syncbody + status + wire. Never compose judgment content.
Internal granular calls suppress receipts; this module writes one aggregate.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Optional

from ..executor import execute as default_execute
from ..lifecycle.helpers import (Execute, Result, atomic_write_json,
                                 leaf_is_safe, read_config, tracker_type)
from ..lifecycle.linkstate import complete_identifier_only, require_durable
from ..lifecycle.verbs import (_claim_is_stale, _ensure_create_first_ignored,
                               _release_claim)
from ..resolve_verb import bound_executor
from ..syncbody import sync_body
from ..types import ErrorClass, TrackerError
from ..wire import dispatch as wire_dispatch
from .helpers import (collect_degraded, comments_have_marker, format_marker,
                      link_state_of, load_tracker, local_spec_md, locator_of,
                      parse_evidence, read_text_file,
                      step_status_from_sync_body, strip_evidence_line,
                      worst_status, write_aggregate_receipt)
from .steps import create_if_unlinked, fail_result, ok_result, run_status


def _fail_if_evidence(err: TrackerError, *, completed: list, statuses: list,
                      flow_dir: Path, spec_id: str, event: str,
                      transport: str,
                      tracker_id: Optional[str] = None) -> TrackerError:
    """Route through fail_result whenever remote-mutation evidence exists -
    either facade-level completed steps or verb-level completed_steps riding
    the error's details (lifecycle_create's partial-failure shape: the issue
    exists but the locked link write failed). A direct return there writes no
    event-tagged aggregate receipt, so sync check reports the lifecycle event
    missing and an automated caller may retry without durable evidence of
    what landed. Failures with NOTHING landed (pre-flight, claim conflicts,
    the MCP external-action instruction) stay receipt-less: there is no
    remote mutation for a receipt to evidence."""
    prior = (err.details or {}).get("completed_steps")
    if not completed and not prior:
        return err
    if tracker_id is None:
        tracker_id = (err.details or {}).get("id")
    tracker_id = None if tracker_id is None else str(tracker_id)
    return fail_result(
        err, completed=completed, statuses=statuses,
        flow_dir=flow_dir, spec_id=spec_id, event=event,
        tracker_id=tracker_id, transport=transport,
    )


def op_push(flow_dir: Path, spec_id: str, *, flow_file: str, event: str,
            execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    flow_body = read_text_file(flow_file, label="--flow-file")
    if isinstance(flow_body, TrackerError):
        return flow_body

    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data, tracker = loaded
    title = str(spec_data.get("title") or spec_id)

    completed: list = []
    statuses: list = []
    degraded = None
    steps: dict[str, Any] = {}

    created = create_if_unlinked(
        flow_dir, spec_id, title=title, body=flow_body, config=config,
        event=event, execute=execute, completed=completed, statuses=statuses,
    )
    if isinstance(created, TrackerError):
        return _fail_if_evidence(
            created, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    steps["create"] = created

    body_out = sync_body(
        flow_dir, spec_id, flow_file_body=flow_body, direction="push",
        event=event, execute=execute, write_receipt=False,
    )
    if isinstance(body_out, TrackerError):
        prior = list((body_out.details or {}).get("completed_steps") or [])
        if prior:
            completed.append("sync-body-partial")
        loaded_p = load_tracker(flow_dir, spec_id)
        tid = loaded_p[2].get("id") if not isinstance(loaded_p, TrackerError) else None
        return fail_result(
            body_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=tid, transport=provider,
        )
    completed.append("sync-body")
    statuses.append(step_status_from_sync_body(body_out))
    steps["sync_body"] = body_out
    degraded = collect_degraded(body_out) or degraded

    status_out = run_status(
        flow_dir, spec_id, config=config, event=event, execute=execute,
        completed=completed, statuses=statuses,
    )
    if isinstance(status_out, TrackerError):
        loaded_p = load_tracker(flow_dir, spec_id)
        tid = loaded_p[2].get("id") if not isinstance(loaded_p, TrackerError) else None
        return fail_result(
            status_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=tid, transport=provider,
        )
    steps["status"] = status_out
    degraded = collect_degraded(status_out) or degraded

    loaded2 = load_tracker(flow_dir, spec_id)
    tracker_id = None
    if not isinstance(loaded2, TrackerError):
        tracker_id = loaded2[2].get("id")

    receipt_status = worst_status(statuses)
    rerr = write_aggregate_receipt(
        flow_dir, spec_id=spec_id, event=event, status=receipt_status,
        tracker_id=tracker_id, transport=provider, degraded=degraded,
        note=f"facade push ({', '.join(completed)})",
    )
    if rerr:
        return fail_result(
            rerr, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=tracker_id, transport=provider, degraded=degraded,
        )

    return ok_result({
        "op": "push",
        "steps": steps,
        "tracker_id": tracker_id,
    }, statuses=statuses, completed=completed, degraded=degraded)


def op_pull(flow_dir: Path, spec_id: str, *, event: str,
            execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, _spec, tracker = loaded
    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return durable
    locator = locator_of(tracker)
    if isinstance(locator, TrackerError):
        return locator

    completed: list = []
    statuses: list = []
    ex = bound_executor(config, execute)

    read_out = wire_dispatch("read", config, locator=locator, execute=ex)
    if isinstance(read_out, TrackerError):
        return read_out
    completed.append("wire-read")
    statuses.append("pulled")

    flow_body = local_spec_md(flow_dir, spec_id)
    if isinstance(flow_body, TrackerError):
        return fail_result(
            flow_body, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )

    # Pair the returned wire body with the stored mergeBaseTracker: pass the
    # already-validated read into sync_body so it does not re-read the parent.
    snapshot = ""
    if isinstance(read_out, dict):
        raw = read_out.get("body")
        if raw is None:
            snapshot = ""
        elif isinstance(raw, str):
            snapshot = raw
        else:
            snapshot = str(raw)

    body_out = sync_body(
        flow_dir, spec_id, flow_file_body=flow_body, direction="pull",
        event=event, execute=execute, write_receipt=False,
        tracker_snapshot_body=snapshot,
    )
    if isinstance(body_out, TrackerError):
        return fail_result(
            body_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )
    completed.append("sync-body")
    statuses.append(step_status_from_sync_body(body_out))

    receipt_status = worst_status(statuses)
    rerr = write_aggregate_receipt(
        flow_dir, spec_id=spec_id, event=event, status=receipt_status,
        tracker_id=durable, transport=provider,
        note=f"facade pull ({', '.join(completed)})",
        degraded=collect_degraded(body_out),
    )
    if rerr:
        return fail_result(
            rerr, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )

    return ok_result({
        "op": "pull",
        "wire_read": {
            "id": read_out.get("id") if isinstance(read_out, dict) else None,
            "title": read_out.get("title") if isinstance(read_out, dict) else None,
            "body": read_out.get("body") if isinstance(read_out, dict) else None,
        },
        "sync_body": body_out,
        "tracker_id": durable,
    }, statuses=statuses, completed=completed,
        degraded=collect_degraded(body_out))


def op_reconcile(flow_dir: Path, spec_id: str, *, flow_file: str,
                 body_file: str, event: str,
                 execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    flow_body = read_text_file(flow_file, label="--flow-file")
    if isinstance(flow_body, TrackerError):
        return flow_body
    tracker_body = read_text_file(body_file, label="--body-file")
    if isinstance(tracker_body, TrackerError):
        return tracker_body

    completed: list = []
    statuses: list = []
    steps: dict[str, Any] = {}
    degraded = None

    # Complete identifier_only BEFORE the sequence (single named entry point).
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, _spec, tracker = loaded
    if link_state_of(tracker) == "identifier_only":
        done = complete_identifier_only(flow_dir, spec_id, execute=execute)
        if isinstance(done, TrackerError):
            # No remote mutation lands on this path today (read-only resolve
            # + local link write), so this stays a direct return - but the
            # helper keeps the receipt invariant self-enforcing should the
            # verb ever grow partial-success evidence.
            return _fail_if_evidence(
                done, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                transport=provider,
            )
        completed.append("complete-identifier-only")
        statuses.append("updated")
        steps["complete_identifier_only"] = done

    # After a completed identifier_only upgrade, the reload/durable/locator
    # failures below are partial successes - same receipt discipline.
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return _fail_if_evidence(
            loaded, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    _path, _spec, tracker = loaded
    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return _fail_if_evidence(
            durable, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
        )
    locator = locator_of(tracker)
    if isinstance(locator, TrackerError):
        return _fail_if_evidence(
            locator, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
        )

    ex = bound_executor(config, execute)
    read_out = wire_dispatch("read", config, locator=locator, execute=ex)
    if isinstance(read_out, TrackerError):
        return fail_result(
            read_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )
    completed.append("wire-read")
    steps["wire_read"] = {
        "id": read_out.get("id") if isinstance(read_out, dict) else None}

    body_out = sync_body(
        flow_dir, spec_id, flow_file_body=flow_body,
        tracker_body=tracker_body, direction="push",
        event=event, execute=execute, write_receipt=False,
    )
    if isinstance(body_out, TrackerError):
        prior = list((body_out.details or {}).get("completed_steps") or [])
        if prior:
            completed.append("sync-body-partial")
        return fail_result(
            body_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )
    completed.append("sync-body")
    statuses.append(step_status_from_sync_body(body_out))
    steps["sync_body"] = body_out
    degraded = collect_degraded(body_out) or degraded

    status_out = run_status(
        flow_dir, spec_id, config=config, event=event, execute=execute,
        completed=completed, statuses=statuses,
    )
    if isinstance(status_out, TrackerError):
        return fail_result(
            status_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )
    steps["status"] = status_out
    degraded = collect_degraded(status_out) or degraded

    receipt_status = worst_status(statuses)
    rerr = write_aggregate_receipt(
        flow_dir, spec_id=spec_id, event=event, status=receipt_status,
        tracker_id=durable, transport=provider, degraded=degraded,
        note=f"facade reconcile ({', '.join(completed)})",
    )
    if rerr:
        return fail_result(
            rerr, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )

    return ok_result({
        "op": "reconcile",
        "steps": steps,
        "tracker_id": durable,
    }, statuses=statuses, completed=completed, degraded=degraded)


def _comment_claim_path(flow_dir: Path, *, issue: str, event: str,
                        evidence: str) -> Path:
    """Claim record keyed on the dedup-marker identity - issue + event +
    evidence, exactly the triple comments_have_marker matches on."""
    payload = "\0".join([issue, event, evidence])
    key = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return Path(flow_dir) / "create-first" / f"comment-{key}.json"


def _claim_comment_marker(flow_dir: Path, spec_id: str, rec_path: Path,
                          provider: str, *, event: str,
                          marker: str) -> Optional[TrackerError]:
    """Reserve the dedup marker under the shared writer lock BEFORE the
    marker scan and comment-add (create-first's claim pattern, keyed on the
    marker identity). Two concurrent comment facades for the same issue,
    event and evidence could both finish the scan before either posts - the
    providers do not make list-then-create atomic - so both would add the
    same marked comment. Under the lock: a live claim from another process
    refuses (comment_in_flight, retryable - after the winner posts, the
    retry's scan sees the marker and dedups to a noop), a stale claim (dead
    pid on this host past the stale window, _claim_is_stale's owner rules)
    is reclaimed by overwriting, and OUR pending claim lands durably before
    any remote read or mutation. The claim is always released when the
    invocation finishes (success or failure): the marker on the remote
    issue, not the claim file, is the durable dedup record."""
    flow_dir = Path(flow_dir)
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
                        f"comment for this marker ({event}) is already in "
                        "flight in another process; retry after it finishes "
                        "(the dedup scan then sees the winner's marker)",
                        subtype="comment_in_flight",
                        details={"specId": spec_id, "marker": marker,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OURS - same rule as create-first.
            claim = {"specId": spec_id, "status": "pending",
                     "marker": marker, "event": event,
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    return None


def op_comment(flow_dir: Path, spec_id: str, *, body_file: str, event: str,
               execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    raw_body = read_text_file(body_file, label="--body-file")
    if isinstance(raw_body, TrackerError):
        return raw_body
    evidence = parse_evidence(raw_body)
    comment_text = strip_evidence_line(raw_body)

    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data, tracker = loaded
    title = str(spec_data.get("title") or spec_id)

    # Create body: local md when present, else the comment text (never compose).
    create_body = local_spec_md(flow_dir, spec_id)
    if isinstance(create_body, TrackerError):
        create_body = comment_text

    completed: list = []
    statuses: list = []
    steps: dict[str, Any] = {}

    created = create_if_unlinked(
        flow_dir, spec_id, title=title, body=create_body, config=config,
        event=event, execute=execute, completed=completed, statuses=statuses,
    )
    if isinstance(created, TrackerError):
        return _fail_if_evidence(
            created, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    steps["create"] = created

    # After a landed create, the reload/durable/locator failures below are
    # partial successes too - the same receipt discipline applies.
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return _fail_if_evidence(
            loaded, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    _path, _spec, tracker = loaded
    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return _fail_if_evidence(
            durable, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
        )
    locator = locator_of(tracker)
    if isinstance(locator, TrackerError):
        return _fail_if_evidence(
            locator, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
        )

    # Serialize the whole list-then-create sequence behind a local marker
    # claim taken BEFORE the scan: the providers do not make it atomic, so
    # two concurrent facades could both prove marker absence and both post.
    marker = format_marker(
        issue=str(durable), spec_id=spec_id, event=event, evidence=evidence)
    rec_path = _comment_claim_path(
        flow_dir, issue=str(durable), event=event, evidence=evidence)
    claimed = _claim_comment_marker(
        flow_dir, spec_id, rec_path, provider, event=event, marker=marker)
    if claimed is not None:
        return fail_result(
            claimed, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider,
        )
    try:
        ex = bound_executor(config, execute)
        listed = wire_dispatch(
            "comment-list", config, locator=locator, execute=ex)
        if isinstance(listed, TrackerError):
            return fail_result(
                listed, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider,
            )
        comments = listed.get("comments") if isinstance(listed, dict) else None
        if not isinstance(comments, list):
            comments = []

        if comments_have_marker(comments, issue=str(durable), event=event,
                                evidence=evidence):
            completed.append("comment-dedup")
            statuses.append("noop")
            receipt_status = worst_status(statuses)
            rerr = write_aggregate_receipt(
                flow_dir, spec_id=spec_id, event=event, status=receipt_status,
                tracker_id=durable, transport=provider,
                note=f"facade comment dedup ({event}/{evidence})",
            )
            if rerr:
                return fail_result(
                    rerr, completed=completed, statuses=statuses,
                    flow_dir=flow_dir, spec_id=spec_id, event=event,
                    tracker_id=durable, transport=provider,
                )
            return ok_result({
                "op": "comment",
                "posted": False,
                "deduped": True,
                "marker": marker,
                "steps": steps,
                "tracker_id": durable,
            }, statuses=statuses, completed=completed)

        # Marker not found - but a truncated scan proves nothing about
        # absence. Posting here would duplicate on high-comment issues;
        # refuse instead (same contract as relate's truncated drain:
        # absence unproven).
        if isinstance(listed, dict) and listed.get("truncated"):
            return fail_result(
                TrackerError(
                    ErrorClass.TRANSPORT,
                    "comment dedup scan truncated at drain cap; "
                    "marker absence unproven, refusing to post",
                    subtype="dedup_truncated",
                    details={"truncated": True, "event": event,
                             "issue": str(durable)},
                ),
                completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider,
            )

        posted_body = f"{marker}\n\n{comment_text}"
        added = wire_dispatch(
            "comment-add", config, locator=locator, body=posted_body,
            execute=ex)
        if isinstance(added, TrackerError):
            return fail_result(
                added, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider,
            )
        completed.append("comment-add")
        statuses.append("updated")
        steps["comment_add"] = added

        receipt_status = worst_status(statuses)
        rerr = write_aggregate_receipt(
            flow_dir, spec_id=spec_id, event=event, status=receipt_status,
            tracker_id=durable, transport=provider,
            note=f"facade comment ({event})",
        )
        if rerr:
            return fail_result(
                rerr, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider,
            )

        return ok_result({
            "op": "comment",
            "posted": True,
            "deduped": False,
            "marker": marker,
            "comment": added,
            "steps": steps,
            "tracker_id": durable,
        }, statuses=statuses, completed=completed)
    finally:
        # Release OUR pending claim on every exit (posted, dedup noop,
        # refusal, transport failure): the remote marker is the durable
        # dedup record, and a lingering claim would only force the next
        # invocation to wait out the stale window.
        _release_claim(rec_path)
