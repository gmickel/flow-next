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
from ..relate import relate
from ..resolve_verb import bound_executor
from ..syncbody import sync_body
from ..status.policy import validate_conflict_tiebreak
from ..types import ErrorClass, TrackerError
from ..wire import dispatch as wire_dispatch
from ..wire import link_pr as wire_link_pr
from ..wire import validate_pr_url
from .helpers import (collect_degraded, comments_have_marker,
                      comments_snapshot, format_marker, link_state_of,
                      live_comments_snapshot, load_tracker, local_spec_md,
                      locator_of,
                      require_evidence,
                      read_comments_file, read_text_file,
                      step_status_from_sync_body, strip_evidence_line,
                      worst_status, write_aggregate_receipt)
from .projections import project_readiness
from .steps import create_if_unlinked, fail_result, ok_result, run_status


def _relation_status(out: dict) -> str:
    return {
        "applied": "pushed",
        "noop": "noop",
        "queued": "queued",
    }.get(str(out.get("kind")), "updated")


def _project_relations(flow_dir: Path, spec_id: str, *, event: str,
                       execute: Execute, completed: list,
                       statuses: list) -> Result:
    """Project every linked depends_on_epics edge without granular receipts."""
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec, _tracker = loaded
    results = []
    for dep in spec.get("depends_on_epics") or []:
        if not isinstance(dep, str) or not dep or dep == spec_id:
            continue
        linked = load_tracker(flow_dir, dep)
        if isinstance(linked, TrackerError):
            results.append({
                "kind": "noop", "reason": "dependency_unresolved",
                "dep_spec": dep,
            })
            statuses.append("noop")
            continue
        dep_tracker = linked[2]
        if link_state_of(dep_tracker) != "linked":
            results.append({
                "kind": "noop", "reason": "dependency_unlinked",
                "dep_spec": dep,
            })
            statuses.append("noop")
            continue
        out = relate(
            flow_dir, spec_id, blocked_by=dep, event=event,
            execute=execute, write_receipt=False,
        )
        if isinstance(out, TrackerError):
            return out
        completed.append(f"relation:{dep}")
        statuses.append(_relation_status(out))
        results.append(out)
    completed.append("relations")
    if not results:
        statuses.append("noop")
    return {"kind": "projected", "relations": results}


def _fail_if_evidence(err: TrackerError, *, completed: list, statuses: list,
                      flow_dir: Path, spec_id: str, event: str,
                      transport: str,
                      tracker_id: Optional[str] = None,
                      degraded: Any = None) -> TrackerError:
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
    if degraded is None:
        degraded = (err.details or {}).get("degraded")
    return fail_result(
        err, completed=completed, statuses=statuses,
        flow_dir=flow_dir, spec_id=spec_id, event=event,
        tracker_id=tracker_id, transport=transport, degraded=degraded,
    )


def _facade_claim_path(flow_dir: Path, spec_id: str) -> Path:
    return Path(flow_dir) / "create-first" / f"facade-{spec_id}.json"


def _claim_facade(flow_dir: Path, spec_id: str, rec_path: Path,
                  provider: str, *, op: str) -> Optional[TrackerError]:
    """Reserve the WHOLE multi-step facade sequence under one spec-identity
    claim taken BEFORE the first step and released only when the sequence
    finishes. The inner per-step claims (`spec-<id>`, `syncbody-<id>`,
    `status-<id>`) each cover only their own step; BETWEEN steps no claim is
    live, so `sync set-tracker-id` - which honors live per-spec claims -
    could relink the spec after sync_body() returned but before run_status()
    acquired its claim. The body would then land on the OLD issue while the
    status step targets the NEW one, and the final receipt (which reloads the
    link) would record only the new id, presenting the split mutations as one
    successful push. This outer claim, keyed `facade-<spec-id>` (distinct
    from every inner key, so the nested step claims cannot self-refuse and
    config_lock is never held across steps), keeps the relink out of the
    entire sequence: flowctl's relink scan includes the facade key. Under the
    lock: a live claim from another process refuses (facade_in_flight,
    retryable), a stale claim (dead pid on this host past the stale window,
    _claim_is_stale's owner rules) is reclaimed by overwriting, and OUR
    pending claim lands durably before any remote I/O."""
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
                        f"a tracker facade operation for spec {spec_id!r} is "
                        "already in flight in another process; retry after "
                        "it finishes",
                        subtype=("comment_in_flight"
                                 if op == "facade-comment"
                                 else "facade_in_flight"),
                        details={"specId": spec_id,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OURS - same rule as create-first.
            claim = {"specId": spec_id, "status": "pending", "op": op,
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    return None


def op_push(flow_dir: Path, spec_id: str, *, flow_file: str, body_file: str,
            event: str, comment_file: Optional[str] = None,
            status_only: bool = False,
            execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    conflict_tiebreak = validate_conflict_tiebreak(config)
    if isinstance(conflict_tiebreak, TrackerError):
        return conflict_tiebreak
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    flow_body = read_text_file(flow_file, label="--flow-file")
    if isinstance(flow_body, TrackerError):
        return flow_body
    tracker_body = read_text_file(body_file, label="--body-file")
    if isinstance(tracker_body, TrackerError):
        return tracker_body
    comment_text = None
    comment_evidence = None
    if comment_file is not None:
        raw_comment = read_text_file(comment_file, label="--comment-file")
        if isinstance(raw_comment, TrackerError):
            return raw_comment
        comment_evidence = require_evidence(
            raw_comment, label="--comment-file")
        if isinstance(comment_evidence, TrackerError):
            return comment_evidence
        comment_text = strip_evidence_line(raw_comment)

    # One spec-identity claim across the whole create -> sync-body -> status
    # -> receipt sequence, so a relink cannot split the push across two
    # issues in a between-steps gap (see _claim_facade).
    rec_path = _facade_claim_path(flow_dir, spec_id)
    claimed = _claim_facade(flow_dir, spec_id, rec_path, provider,
                            op="facade-push")
    if claimed is not None:
        # Nothing landed: claim refusals stay receipt-less.
        return claimed
    try:
        return _push_sequence(
            flow_dir, spec_id, flow_body=flow_body,
            tracker_body=tracker_body, config=config, provider=provider,
            event=event, comment_text=comment_text,
            comment_evidence=comment_evidence,
            status_only=status_only, execute=execute)
    finally:
        # Release on every exit: the aggregate receipt, not the claim file,
        # is the durable record of what landed.
        _release_claim(rec_path)


def _push_sequence(flow_dir: Path, spec_id: str, *, flow_body: str,
                   tracker_body: str, config: dict, provider: str,
                   event: str, comment_text: Optional[str],
                   comment_evidence: Optional[str],
                   status_only: bool, execute: Execute) -> Result:
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
        flow_dir, spec_id, title=title, body=tracker_body,
        flow_body=flow_body, config=config,
        event=event, execute=execute, completed=completed, statuses=statuses,
    )
    if isinstance(created, TrackerError):
        return _fail_if_evidence(
            created, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    steps["create"] = created
    degraded = collect_degraded(created) or degraded

    if not status_only:
        body_out = sync_body(
            flow_dir, spec_id, flow_file_body=flow_body, direction="push",
            tracker_body=tracker_body, event=event, execute=execute,
            sync_title=True, write_receipt=False,
        )
        if isinstance(body_out, TrackerError):
            prior = list((body_out.details or {}).get("completed_steps") or [])
            if prior:
                completed.append("sync-body-partial")
            loaded_p = load_tracker(flow_dir, spec_id)
            tid = (loaded_p[2].get("id")
                   if not isinstance(loaded_p, TrackerError) else None)
            return fail_result(
                body_out, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=tid, transport=provider, degraded=degraded,
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
            tracker_id=tid, transport=provider, degraded=degraded,
        )
    steps["status"] = status_out
    degraded = collect_degraded(status_out) or degraded

    if not status_only:
        relations_out = _project_relations(
            flow_dir, spec_id, event=event, execute=execute,
            completed=completed, statuses=statuses,
        )
        if isinstance(relations_out, TrackerError):
            loaded_p = load_tracker(flow_dir, spec_id)
            tid = (loaded_p[2].get("id")
                   if not isinstance(loaded_p, TrackerError) else None)
            return fail_result(
                relations_out, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=tid, transport=provider, degraded=degraded,
            )
        steps["relations"] = relations_out
        degraded = collect_degraded(relations_out) or degraded

    if comment_text is not None and comment_evidence is not None:
        comment_out = _project_push_comment(
            flow_dir, spec_id, comment_text=comment_text,
            evidence=comment_evidence, config=config, provider=provider,
            event=event, execute=execute, completed=completed,
            statuses=statuses,
        )
        if isinstance(comment_out, TrackerError):
            loaded_p = load_tracker(flow_dir, spec_id)
            tid = (loaded_p[2].get("id")
                   if not isinstance(loaded_p, TrackerError) else None)
            return fail_result(
                comment_out, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=tid, transport=provider, degraded=degraded,
            )
        steps["comment"] = comment_out

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
        "status_only": status_only,
        "steps": steps,
        "tracker_id": tracker_id,
    }, statuses=statuses, completed=completed, degraded=degraded)


def op_pull(flow_dir: Path, spec_id: str, *, flow_file: str, body_file: str,
            comments_file: str, event: str,
            execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    conflict_tiebreak = validate_conflict_tiebreak(config)
    if isinstance(conflict_tiebreak, TrackerError):
        return conflict_tiebreak
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
    flow_body = read_text_file(flow_file, label="--flow-file")
    if isinstance(flow_body, TrackerError):
        return flow_body
    tracker_body = read_text_file(body_file, label="--body-file")
    if isinstance(tracker_body, TrackerError):
        return tracker_body
    expected_comments = read_comments_file(comments_file)
    if isinstance(expected_comments, TrackerError):
        return expected_comments
    expected_comments = comments_snapshot(expected_comments)
    if isinstance(expected_comments, TrackerError):
        return expected_comments

    # Hold one identity claim across the inner sync-body transaction AND the
    # aggregate receipt. Otherwise a relink can land after sync_body releases
    # its claim but before the event receipt is written, making sync check
    # treat old-issue work as having served the newly linked issue.
    rec_path = _facade_claim_path(flow_dir, spec_id)
    claimed = _claim_facade(flow_dir, spec_id, rec_path, provider,
                            op="facade-pull")
    if claimed is not None:
        return claimed
    try:
        return _pull_sequence(
            flow_dir, spec_id, event=event, config=config, provider=provider,
            durable=durable, flow_body=flow_body,
            tracker_body=tracker_body, expected_comments=expected_comments,
            execute=execute)
    finally:
        _release_claim(rec_path)


def _pull_sequence(flow_dir: Path, spec_id: str, *, event: str,
                   config: dict, provider: str, durable: str, flow_body: str,
                   tracker_body: str, expected_comments: list,
                   execute: Execute) -> Result:
    """Read, merge, and receipt one pull while the facade claim is live."""
    completed: list = []
    statuses: list = []
    ex = bound_executor(config, execute)
    degraded = None

    # The wire read runs INSIDE sync_body's claimed transaction, against the
    # transaction's own locator - a pre-claim read could pair an older
    # snapshot with a newer base (two pulls overlapping a remote edit) or,
    # after a set-tracker-id repoint in the gap, commit the old issue's body
    # under the new locator. The successful read result threads back out
    # through this holder so it is never re-read - and so does the
    # transaction's OWN locator: `durable` above was captured pre-claim, so
    # after a repoint in the gap it names the OLD issue while the read and
    # paired base target the NEW one. The receipt and the returned tracker_id
    # must record the identity the transaction actually used.
    read_holder: dict[str, Any] = {}

    def _tracker_read(txn_locator: dict) -> Any:
        read_holder["locator"] = dict(txn_locator)
        out = wire_dispatch("read", config, locator=txn_locator, execute=ex)
        if isinstance(out, TrackerError):
            return out
        read_holder["read"] = out

        readiness = project_readiness(
            flow_dir, spec_id, issue=out, config=config, provider=provider,
            locator=txn_locator, execute=ex,
        )
        read_holder["readiness"] = readiness

        comments_out = wire_dispatch(
            "comment-list", config, locator=txn_locator, execute=ex)
        if isinstance(comments_out, TrackerError):
            return comments_out
        current_comments = live_comments_snapshot(comments_out)
        if isinstance(current_comments, TrackerError):
            return current_comments
        read_holder["comments"] = comments_out
        if current_comments != expected_comments:
            return TrackerError(
                ErrorClass.CONFLICT,
                "tracker comments changed after the pull fold was prepared; "
                "refusing to commit a stale local form",
                subtype="comments_changed",
                details={
                    "expected": expected_comments,
                    "found": current_comments,
                },
                auto_retryable=True,
            )

        local_body = local_spec_md(flow_dir, spec_id)
        if isinstance(local_body, TrackerError):
            return local_body
        if local_body != flow_body:
            return TrackerError(
                ErrorClass.CONFLICT,
                "the final pull flow form has not been written to the local "
                "spec; write the agent-approved fold before committing its base",
                subtype="flow_form_not_applied",
                auto_retryable=True,
            )
        return out

    body_out = sync_body(
        flow_dir, spec_id, flow_file_body=flow_body, direction="pull",
        expected_tracker_body=tracker_body,
        event=event, execute=execute, write_receipt=False,
        tracker_read=_tracker_read,
    )
    read_out = read_holder.get("read")
    # Receipt identity = the transaction's locator (captured at the read,
    # post-claim). Fall back to the pre-claim durable only when the
    # transaction never reached its read - those paths landed no wire I/O
    # under any identity.
    txn_locator = read_holder.get("locator")
    txn_durable = (txn_locator or {}).get("durable") or durable
    if read_out is not None:
        completed.append("wire-read")
        statuses.append("pulled")
    readiness_out = read_holder.get("readiness")
    if isinstance(readiness_out, dict):
        completed.append("readiness")
        statuses.append(
            "updated" if readiness_out.get("kind") == "updated" else "noop")
        degraded = collect_degraded(readiness_out) or degraded
    comments_out = read_holder.get("comments")
    if isinstance(comments_out, dict):
        completed.append("comments")
        statuses.append("pulled")
    if isinstance(body_out, TrackerError):
        if read_out is None:
            # The claim refusal, the transaction's locator failure, or the
            # read itself failed: nothing landed, stay receipt-less.
            return body_out
        return fail_result(
            body_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=txn_durable, transport=provider,
            degraded=degraded,
        )
    completed.append("sync-body")
    statuses.append(step_status_from_sync_body(body_out))
    degraded = collect_degraded(body_out) or degraded

    status_out = run_status(
        flow_dir, spec_id, config=config, event=event, execute=execute,
        completed=completed, statuses=statuses,
    )
    if isinstance(status_out, TrackerError):
        return fail_result(
            status_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=txn_durable, transport=provider, degraded=degraded,
        )
    degraded = collect_degraded(status_out) or degraded

    receipt_status = worst_status(statuses)
    rerr = write_aggregate_receipt(
        flow_dir, spec_id=spec_id, event=event, status=receipt_status,
        tracker_id=txn_durable, transport=provider,
        note=f"facade pull ({', '.join(completed)})",
        degraded=degraded,
    )
    if rerr:
        return fail_result(
            rerr, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=txn_durable, transport=provider,
            degraded=degraded,
        )

    return ok_result({
        "op": "pull",
        "wire_read": {
            "id": read_out.get("id") if isinstance(read_out, dict) else None,
            "title": read_out.get("title") if isinstance(read_out, dict) else None,
            "body": read_out.get("body") if isinstance(read_out, dict) else None,
        },
        "comments": comments_out,
        "readiness": readiness_out,
        "status": status_out,
        "sync_body": body_out,
        "tracker_id": txn_durable,
    }, statuses=statuses, completed=completed,
        degraded=degraded)


def op_reconcile(flow_dir: Path, spec_id: str, *, flow_file: str,
                 body_file: str, comments_file: str,
                 source_body_file: str, event: str,
                 pr_url: Optional[str] = None,
                 execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    conflict_tiebreak = validate_conflict_tiebreak(config)
    if isinstance(conflict_tiebreak, TrackerError):
        return conflict_tiebreak
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    if pr_url is not None:
        invalid_pr_url = validate_pr_url(pr_url)
        if invalid_pr_url is not None:
            return invalid_pr_url

    flow_body = read_text_file(flow_file, label="--flow-file")
    if isinstance(flow_body, TrackerError):
        return flow_body
    tracker_body = read_text_file(body_file, label="--body-file")
    if isinstance(tracker_body, TrackerError):
        return tracker_body
    source_tracker_body = read_text_file(
        source_body_file, label="--source-body-file")
    if isinstance(source_tracker_body, TrackerError):
        return source_tracker_body
    expected_comments = read_comments_file(comments_file)
    if isinstance(expected_comments, TrackerError):
        return expected_comments
    expected_comments = comments_snapshot(expected_comments)
    if isinstance(expected_comments, TrackerError):
        return expected_comments

    # Same multi-step gap as op_push (identifier-only completion ->
    # wire-read -> sync-body -> status -> receipt): hold ONE spec-identity
    # claim across the whole sequence so a relink cannot split it across two
    # issues between steps (see _claim_facade).
    rec_path = _facade_claim_path(flow_dir, spec_id)
    claimed = _claim_facade(flow_dir, spec_id, rec_path, provider,
                            op="facade-reconcile")
    if claimed is not None:
        # Nothing landed: claim refusals stay receipt-less.
        return claimed
    try:
        return _reconcile_sequence(
            flow_dir, spec_id, flow_body=flow_body, tracker_body=tracker_body,
            source_tracker_body=source_tracker_body,
            expected_comments=expected_comments,
            config=config, provider=provider, event=event, pr_url=pr_url,
            execute=execute)
    finally:
        _release_claim(rec_path)


def _reconcile_sequence(flow_dir: Path, spec_id: str, *, flow_body: str,
                        tracker_body: str, source_tracker_body: str,
                        expected_comments: list,
                        config: dict, provider: str,
                        event: str, pr_url: Optional[str],
                        execute: Execute) -> Result:
    completed: list = []
    statuses: list = []
    steps: dict[str, Any] = {}
    degraded = None

    # Complete identifier_only BEFORE the sequence (single named entry point).
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    _path, spec_data, tracker = loaded
    title = str(spec_data.get("title") or spec_id)

    # Reconcile is also a first-touch lifecycle operation. Establish the
    # durable identity and paired ancestor before any require_durable/read
    # step; otherwise an unlinked spec fails without reaching the provider.
    created = create_if_unlinked(
        flow_dir, spec_id, title=title, body=tracker_body,
        flow_body=flow_body, config=config, event=event, execute=execute,
        completed=completed, statuses=statuses,
    )
    if isinstance(created, TrackerError):
        return _fail_if_evidence(
            created, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    steps["create"] = created
    degraded = collect_degraded(created) or degraded

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
                transport=provider, degraded=degraded,
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
            transport=provider, degraded=degraded,
        )
    _path, _spec, tracker = loaded
    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return _fail_if_evidence(
            durable, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
            degraded=degraded,
        )
    locator = locator_of(tracker)
    if isinstance(locator, TrackerError):
        return _fail_if_evidence(
            locator, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
            degraded=degraded,
        )

    ex = bound_executor(config, execute)
    read_out = wire_dispatch("read", config, locator=locator, execute=ex)
    if isinstance(read_out, TrackerError):
        return fail_result(
            read_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    completed.append("wire-read")
    steps["wire_read"] = {
        "id": read_out.get("id") if isinstance(read_out, dict) else None}

    readiness_out = project_readiness(
        flow_dir, spec_id, issue=read_out, config=config, provider=provider,
        locator=locator, execute=ex,
    )
    completed.append("readiness")
    statuses.append(
        "updated" if readiness_out.get("kind") == "updated" else "noop")
    steps["readiness"] = readiness_out
    degraded = collect_degraded(readiness_out) or degraded

    comments_out = wire_dispatch(
        "comment-list", config, locator=locator, execute=ex)
    if isinstance(comments_out, TrackerError):
        return fail_result(
            comments_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    current_comments = live_comments_snapshot(comments_out)
    if isinstance(current_comments, TrackerError):
        return fail_result(
            current_comments, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    if current_comments != expected_comments:
        return fail_result(
            TrackerError(
                ErrorClass.CONFLICT,
                "tracker comments changed after the reconcile fold was "
                "prepared; refusing to commit stale forms",
                subtype="comments_changed",
                details={"expected": expected_comments,
                         "found": current_comments},
                auto_retryable=True,
            ),
            completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    completed.append("comments")
    statuses.append("pulled")
    steps["comments"] = comments_out

    if pr_url is not None:
        pr_link_out = wire_link_pr(
            provider, config, locator, ex, url=pr_url)
        if isinstance(pr_link_out, TrackerError):
            return fail_result(
                pr_link_out, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider, degraded=degraded,
            )
        completed.append("pr-link")
        statuses.append(
            "updated" if pr_link_out.get("linked") else "noop")
        steps["pr_link"] = pr_link_out
        degraded = collect_degraded(pr_link_out) or degraded

    local_body = local_spec_md(flow_dir, spec_id)
    if isinstance(local_body, TrackerError):
        return fail_result(
            local_body, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    if local_body != flow_body:
        return fail_result(
            TrackerError(
                ErrorClass.CONFLICT,
                "the final reconcile flow form has not been written to the "
                "local spec; write the agent-approved merge before syncing",
                subtype="flow_form_not_applied",
                auto_retryable=True,
            ),
            completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )

    relations_out = _project_relations(
        flow_dir, spec_id, event=event, execute=execute,
        completed=completed, statuses=statuses,
    )
    if isinstance(relations_out, TrackerError):
        return fail_result(
            relations_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    steps["relations"] = relations_out
    degraded = collect_degraded(relations_out) or degraded

    body_out = sync_body(
        flow_dir, spec_id, flow_file_body=flow_body,
        tracker_body=tracker_body, direction="push",
        expected_tracker_body=source_tracker_body,
        sync_title=True, event=event, execute=execute, write_receipt=False,
    )
    if isinstance(body_out, TrackerError):
        prior = list((body_out.details or {}).get("completed_steps") or [])
        if prior:
            completed.append("sync-body-partial")
        return fail_result(
            body_out, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
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
            tracker_id=durable, transport=provider, degraded=degraded,
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


def _comment_claim_path(flow_dir: Path, *, issue: str, spec: str,
                        event: str, evidence: str) -> Path:
    """Claim record keyed on the dedup-marker identity - issue + spec +
    event + evidence, exactly the quadruple comments_have_marker matches on.
    Spec is part of the key so two specs sharing one issue (`sync
    set-tracker-id --force`) can claim concurrently without false back-off;
    the sha256 keeps the filename hex-safe regardless of the spec slug."""
    payload = "\0".join([issue, spec, event, evidence])
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


def _recheck_comment_identity(flow_dir: Path, spec_id: str,
                              locator: dict) -> Optional[TrackerError]:
    """Wave-11 revalidation, comment edition: the marker claim serializes
    sibling comment facades, NOT `sync set-tracker-id`. If a relink lands
    after this invocation loaded its locator, the dedup scan and comment-add
    below would validate and post against the OLD issue while the spec now
    points at a new one - and the aggregate receipt would record the old
    tracker id. Under the shared writer lock (the same lock the link writers
    hold - since PR #246 that includes `sync set-tracker-id` itself, whose
    reload-mutate-write runs entirely inside it), reload the tracker block
    and compare its durable/display identity against the locator this
    invocation loaded; on drift refuse with structured CONFLICT
    (identity_changed, the sibling subtype) BEFORE any wire call. Because the
    relink writer holds the same lock, a relink cannot interleave with this
    reload: it commits entirely before the recheck (detected here) or
    entirely after it. What is deliberately NOT guaranteed: the lock is
    released before the wire calls (locks never span network I/O anywhere in
    this codebase), so a relink landing after a passed recheck serializes
    strictly after it and the wire call targets the identity that was
    current at recheck time. The claim taken above is keyed on the OLD issue
    id, so the caller's finally releases it and no claim remains for the
    stale key."""
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            loaded = load_tracker(flow_dir, spec_id)
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    if isinstance(loaded, TrackerError):
        return loaded
    _path, _spec, tracker = loaded
    now = locator_of(tracker)
    if isinstance(now, TrackerError) or now != locator:
        now_id = tracker.get("id")
        now_display = tracker.get("identifier")
        return TrackerError(
            ErrorClass.CONFLICT,
            f"spec {spec_id!r} tracker identity changed while the comment "
            f"facade was in flight (invocation loaded "
            f"{locator.get('display')!r}/{locator.get('durable')!r}, spec "
            f"now has {now_display!r}/{now_id!r}); refusing to post to the "
            "old issue; re-run the comment against the new link",
            subtype="identity_changed",
            details={"specId": spec_id,
                     "transaction": dict(locator),
                     "current": {"durable": now_id,
                                 "display": now_display}})
    return None


def _project_push_comment(flow_dir: Path, spec_id: str, *,
                          comment_text: str, evidence: str,
                          config: dict, provider: str, event: str,
                          execute: Execute, completed: list,
                          statuses: list) -> Result:
    """Post/dedup one judgment-bearing comment inside the push facade claim.

    The caller already completed create/link and paired-base work. This helper
    adds only the marker-claimed list -> optional add sequence, leaving the
    push facade to write the single aggregate receipt for status, relations,
    and comment together.
    """
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

    marker = format_marker(
        issue=str(durable), spec_id=spec_id, event=event, evidence=evidence)
    marker_rec_path = _comment_claim_path(
        flow_dir, issue=str(durable), spec=spec_id, event=event,
        evidence=evidence)
    claimed = _claim_comment_marker(
        flow_dir, spec_id, marker_rec_path, provider, event=event,
        marker=marker)
    if claimed is not None:
        return claimed

    try:
        drift = _recheck_comment_identity(flow_dir, spec_id, locator)
        if drift is not None:
            return drift
        ex = bound_executor(config, execute)
        listed = wire_dispatch(
            "comment-list", config, locator=locator, execute=ex)
        if isinstance(listed, TrackerError):
            return listed
        comments = listed.get("comments") if isinstance(listed, dict) else None
        if not isinstance(comments, list):
            comments = []

        if comments_have_marker(
                comments, issue=str(durable), spec=spec_id,
                event=event, evidence=evidence):
            completed.append("comment-dedup")
            statuses.append("noop")
            return {
                "posted": False,
                "deduped": True,
                "marker": marker,
                "tracker_id": durable,
            }

        if isinstance(listed, dict) and listed.get("truncated"):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "comment dedup scan truncated at drain cap; "
                "marker absence unproven, refusing to post",
                subtype="dedup_truncated",
                details={
                    "truncated": True,
                    "event": event,
                    "issue": str(durable),
                },
            )

        drift = _recheck_comment_identity(flow_dir, spec_id, locator)
        if drift is not None:
            return drift
        posted_body = f"{marker}\n\n{comment_text}"
        added = wire_dispatch(
            "comment-add", config, locator=locator, body=posted_body,
            execute=ex)
        if isinstance(added, TrackerError):
            return added
        completed.append("comment-add")
        statuses.append("updated")
        return {
            "posted": True,
            "deduped": False,
            "marker": marker,
            "comment": added,
            "tracker_id": durable,
        }
    finally:
        _release_claim(marker_rec_path)


def op_comment(flow_dir: Path, spec_id: str, *, body_file: str, event: str,
               execute: Execute = default_execute) -> Result:
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    raw_body = read_text_file(body_file, label="--body-file")
    if isinstance(raw_body, TrackerError):
        return raw_body
    evidence = require_evidence(raw_body, label="--body-file")
    if isinstance(evidence, TrackerError):
        return evidence
    comment_text = strip_evidence_line(raw_body)

    # One spec-identity claim across the whole create -> marker scan ->
    # comment-add -> receipt sequence. The marker claim below is issue-keyed
    # and starts only after create_if_unlinked(), so it cannot prevent a
    # relink from redirecting the remainder of a newly-created comment facade
    # to another issue. The outer facade claim is spec-keyed and is honored by
    # set-tracker-id.
    facade_rec_path = _facade_claim_path(flow_dir, spec_id)
    claimed = _claim_facade(flow_dir, spec_id, facade_rec_path, provider,
                            op="facade-comment")
    if claimed is not None:
        return claimed
    try:
        return _comment_sequence(
            flow_dir, spec_id, comment_text=comment_text, evidence=evidence,
            config=config, provider=provider, event=event, execute=execute)
    finally:
        _release_claim(facade_rec_path)


def _comment_sequence(flow_dir: Path, spec_id: str, *, comment_text: str,
                      evidence: str, config: dict, provider: str, event: str,
                      execute: Execute) -> Result:
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
    degraded = None
    steps: dict[str, Any] = {}

    created = create_if_unlinked(
        flow_dir, spec_id, title=title, body=create_body,
        flow_body=create_body, config=config,
        event=event, execute=execute, completed=completed, statuses=statuses,
    )
    if isinstance(created, TrackerError):
        return _fail_if_evidence(
            created, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider,
        )
    steps["create"] = created
    degraded = collect_degraded(created) or degraded

    # After a landed create, the reload/durable/locator failures below are
    # partial successes too - the same receipt discipline applies.
    loaded = load_tracker(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return _fail_if_evidence(
            loaded, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, degraded=degraded,
        )
    _path, _spec, tracker = loaded

    # MCP create continuation persists the durable identity outside this
    # facade, so create_if_unlinked correctly no-ops on the retry but no body
    # ancestor exists yet. A comment must repair that explicit baseless state
    # before list/add; otherwise a later reconcile can overwrite an intervening
    # tracker edit through the no-base bootstrap.
    if (tracker.get("mergeBaseFlow") is None
            or tracker.get("mergeBaseTracker") is None):
        seeded = sync_body(
            flow_dir, spec_id, flow_file_body=create_body, direction="pull",
            event=event, execute=execute, write_receipt=False,
        )
        if isinstance(seeded, TrackerError):
            return fail_result(
                seeded, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=tracker.get("id"), transport=provider,
                degraded=degraded,
            )
        if "paired-base" not in completed:
            completed.append("paired-base")
            statuses.append(step_status_from_sync_body(seeded))
        steps["paired_base"] = seeded

    durable = require_durable(tracker)
    if isinstance(durable, TrackerError):
        return _fail_if_evidence(
            durable, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
            degraded=degraded,
        )
    locator = locator_of(tracker)
    if isinstance(locator, TrackerError):
        return _fail_if_evidence(
            locator, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            transport=provider, tracker_id=tracker.get("id"),
            degraded=degraded,
        )

    # Serialize the whole list-then-create sequence behind a local marker
    # claim taken BEFORE the scan: the providers do not make it atomic, so
    # two concurrent facades could both prove marker absence and both post.
    marker = format_marker(
        issue=str(durable), spec_id=spec_id, event=event, evidence=evidence)
    marker_rec_path = _comment_claim_path(
        flow_dir, issue=str(durable), spec=spec_id, event=event,
        evidence=evidence)
    claimed = _claim_comment_marker(
        flow_dir, spec_id, marker_rec_path, provider, event=event,
        marker=marker)
    if claimed is not None:
        return fail_result(
            claimed, completed=completed, statuses=statuses,
            flow_dir=flow_dir, spec_id=spec_id, event=event,
            tracker_id=durable, transport=provider, degraded=degraded,
        )
    try:
        # `sync set-tracker-id` can repoint the spec between the locator
        # load above and here; the marker claim does not coordinate with the
        # link writer. Revalidate the spec identity before any wire call so
        # the post (and the receipt's tracker id) never targets the old
        # issue; the finally below releases the now-stale-keyed claim. The
        # relink writer holds the same lock, so it cannot interleave with
        # this recheck - it lands wholly before (refused here) or wholly
        # after (re-checked again just before comment-add below).
        drift = _recheck_comment_identity(flow_dir, spec_id, locator)
        if drift is not None:
            return _fail_if_evidence(
                drift, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                transport=provider, tracker_id=str(durable),
                degraded=degraded,
            )
        ex = bound_executor(config, execute)
        listed = wire_dispatch(
            "comment-list", config, locator=locator, execute=ex)
        if isinstance(listed, TrackerError):
            return fail_result(
                listed, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider, degraded=degraded,
            )
        comments = listed.get("comments") if isinstance(listed, dict) else None
        if not isinstance(comments, list):
            comments = []

        if comments_have_marker(comments, issue=str(durable), spec=spec_id,
                                event=event, evidence=evidence):
            completed.append("comment-dedup")
            statuses.append("noop")
            receipt_status = worst_status(statuses)
            rerr = write_aggregate_receipt(
                flow_dir, spec_id=spec_id, event=event, status=receipt_status,
                tracker_id=durable, transport=provider, degraded=degraded,
                note=f"facade comment dedup ({event}/{evidence})",
            )
            if rerr:
                return fail_result(
                    rerr, completed=completed, statuses=statuses,
                    flow_dir=flow_dir, spec_id=spec_id, event=event,
                    tracker_id=durable, transport=provider,
                    degraded=degraded,
                )
            return ok_result({
                "op": "comment",
                "posted": False,
                "deduped": True,
                "marker": marker,
                "steps": steps,
                "tracker_id": durable,
            }, statuses=statuses, completed=completed, degraded=degraded)

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
                tracker_id=durable, transport=provider, degraded=degraded,
            )

        # Last locked recheck before the mutating wire call: the dedup scan
        # above is network I/O, so a relink can land while it runs. Re-read
        # the spec identity under the lock immediately before posting; the
        # residual window is recheck-to-add only (a relink there serializes
        # strictly after this check - locks never span network I/O).
        drift = _recheck_comment_identity(flow_dir, spec_id, locator)
        if drift is not None:
            return _fail_if_evidence(
                drift, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                transport=provider, tracker_id=str(durable),
                degraded=degraded,
            )

        posted_body = f"{marker}\n\n{comment_text}"
        added = wire_dispatch(
            "comment-add", config, locator=locator, body=posted_body,
            execute=ex)
        if isinstance(added, TrackerError):
            return fail_result(
                added, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider, degraded=degraded,
            )
        completed.append("comment-add")
        statuses.append("updated")
        steps["comment_add"] = added

        receipt_status = worst_status(statuses)
        rerr = write_aggregate_receipt(
            flow_dir, spec_id=spec_id, event=event, status=receipt_status,
            tracker_id=durable, transport=provider, degraded=degraded,
            note=f"facade comment ({event})",
        )
        if rerr:
            return fail_result(
                rerr, completed=completed, statuses=statuses,
                flow_dir=flow_dir, spec_id=spec_id, event=event,
                tracker_id=durable, transport=provider, degraded=degraded,
            )

        return ok_result({
            "op": "comment",
            "posted": True,
            "deduped": False,
            "marker": marker,
            "comment": added,
            "steps": steps,
            "tracker_id": durable,
        }, statuses=statuses, completed=completed, degraded=degraded)
    finally:
        # Release OUR pending claim on every exit (posted, dedup noop,
        # refusal, transport failure): the remote marker is the durable
        # dedup record, and a lingering claim would only force the next
        # invocation to wait out the stale window.
        _release_claim(marker_rec_path)
