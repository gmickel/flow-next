"""`tracker status` verb orchestration (fn-140.3).

require_durable → wire parent_read → merge_evidence → flow_to_normalized →
decide → provider write. Applied advances lastSyncedAt (+ receipt);
noop/conflict do not; defer writes a receipt (status deferred) without
advancing lastSyncedAt.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from ..executor import execute as default_execute
from ..lifecycle.helpers import (Execute, Result, atomic_write_json, dict_,
                                 leaf_is_safe, load_spec, merged_tracker,
                                 now_iso, read_config, tracker_type,
                                 write_sync_receipt, write_tracker_block)
from ..lifecycle.linkstate import require_durable
from ..lifecycle.verbs import (_claim_is_stale, _ensure_create_first_ignored,
                               _release_claim)
from ..types import ErrorClass, TrackerError
from .policy import (Decision, decide, decision_as_error, flow_to_normalized,
                     merge_evidence, validate_conflict_tiebreak,
                     validate_to_reason)
from .providers import (apply_status, enrich_linear_parent, github_native_status,
                        github_status_labels_match, repair_github_status_labels,
                        tracker_norm_from_parent)


def _backend_off(value: str) -> bool:
    """A backend spec is backend[:model[:effort]]; only the backend part
    decides configured-ness."""
    return value.split(":", 1)[0].strip().lower() in ("", "none", "off")


def _completion_review_configured(config: dict,
                                  spec_data: Optional[dict] = None) -> bool:
    """Effective review backend with resolve_review_spec's precedence:
    spec default_review > FLOW_REVIEW_BACKEND env > config review.backend.
    Reading only the config half made a spec pinned to codex (or an env
    override) project as review-ungated - a merged spec folded to done with
    no shipped completion review - and vice versa."""
    per = (spec_data or {}).get("default_review")
    if isinstance(per, str) and per.strip():
        return not _backend_off(per)
    env = os.environ.get("FLOW_REVIEW_BACKEND")
    if isinstance(env, str) and env.strip():
        return not _backend_off(env)
    review = dict_(config.get("review")).get("backend")
    if review is None:
        return False
    if isinstance(review, str):
        return not _backend_off(review)
    return True


def _state_dir(flow_dir: Path) -> Path:
    """Mirror flowctl's get_state_dir: FLOW_STATE_DIR env, then the git
    common-dir (shared across worktrees), then .flow/state for non-git."""
    env = os.environ.get("FLOW_STATE_DIR")
    if env:
        return Path(env).resolve()
    try:
        # --path-format modifies only the options AFTER it (PR #246 wave-14
        # P1): trailing placement returned a cwd-relative ".git", which broke
        # as soon as the caller's cwd differed from flow_dir.parent.
        result = subprocess.run(  # noqa: S603 - fixed argv, shell=False
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, encoding="utf-8", check=True,
            cwd=flow_dir.parent,
        )
        return Path(result.stdout.strip()) / "flow-state"
    except (subprocess.CalledProcessError, OSError):
        return flow_dir / "state"


def _load_tasks(flow_dir: Path, spec_id: str) -> list:
    """Task definitions overlaid with runtime state. Since the fn-111 storage
    split, .flow/tasks/<id>.json is the DEFINITION (status is the scaffold
    value); the live status (claimed/in_progress/done) lives in the runtime
    store at <state-dir>/tasks/<id>.state.json. Reading only the definition
    made every started spec normalize as todo (measured live 2026-07-28)."""
    tasks_dir = flow_dir / "tasks"
    if not tasks_dir.is_dir():
        return []
    runtime_dir = _state_dir(flow_dir) / "tasks"
    out = []
    for path in sorted(tasks_dir.glob(f"{spec_id}.*.json")):
        if path.name.endswith(".state.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        status = data.get("status") or "todo"
        state_path = runtime_dir / f"{path.name[:-len('.json')]}.state.json"
        try:
            runtime = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(runtime, dict) and runtime.get("status"):
                status = runtime["status"]
        except (OSError, ValueError):
            pass
        out.append({"id": data.get("id"), "status": status})
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


def _claim_status(flow_dir: Path, spec_id: str, rec_path: Path,
                  provider: str, *, to: str) -> Optional[TrackerError]:
    """Reserve the spec's status transaction under the shared writer lock
    BEFORE the parent read / PR probe / provider mutation (syncbody's claim
    pattern, keyed on the spec id). The identity guard in
    _persist_applied_state can only DETECT a relink after the provider
    mutation has landed on the old issue; the claim makes the whole window
    exclusive instead: `sync set-tracker-id` honors live per-spec claims and
    refuses to relink while one exists, so a repoint can no longer land
    between the initial reads and the locked persistence. Under the lock: a
    live claim from another process refuses (status_in_flight, retryable), a
    stale claim (dead pid on this host past the stale window,
    _claim_is_stale's owner rules) is reclaimed by overwriting, and OUR
    pending claim lands durably before any remote I/O. The claim is always
    released when the invocation finishes (success or failure): the spec's
    tracker block, not the claim file, is the durable record."""
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
                        f"status for spec {spec_id!r} is already in flight "
                        "in another process; retry after it finishes",
                        subtype="status_in_flight",
                        details={"specId": spec_id,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OURS - same rule as create-first.
            claim = {"specId": spec_id, "status": "pending",
                     "op": "status", "to": to,
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    return None


def status(flow_dir, spec_id: str, *, to: str, reason: Optional[str] = None,
           event: Optional[str] = None,
           execute: Execute = default_execute,
           write_receipt: bool = True) -> Result:
    """Spec-aware status verb. Never raises across the boundary.

    Serialized per spec via a create-first claim (`status-<spec-id>.json`)
    taken before any spec read or tracker I/O; a live foreign claim refuses
    with structured CONFLICT (status_in_flight, retryable). The same claim is
    honored by `sync set-tracker-id`, so a relink cannot land anywhere inside
    the claimed window.
    """
    flow_dir = Path(flow_dir)
    # Validate --to/--reason BEFORE any mutation / network (garbage reason).
    bad = validate_to_reason(to, reason)
    if bad:
        return bad
    if not spec_id:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "status requires <spec-id>", subtype="args")

    config = read_config(flow_dir)
    conflict_tiebreak = validate_conflict_tiebreak(config)
    if isinstance(conflict_tiebreak, TrackerError):
        return conflict_tiebreak
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    rec_path = flow_dir / "create-first" / f"status-{spec_id}.json"
    claimed = _claim_status(flow_dir, spec_id, rec_path, provider, to=to)
    if claimed is not None:
        return claimed
    try:
        return _status_txn(
            flow_dir, spec_id, config=config, provider=provider,
            conflict_tiebreak=conflict_tiebreak,
            to=to, reason=reason, event=event, execute=execute,
            write_receipt=write_receipt)
    finally:
        _release_claim(rec_path)


def _status_txn(flow_dir: Path, spec_id: str, *, config: dict, provider: str,
                conflict_tiebreak: str,
                to: str, reason: Optional[str], event: Optional[str],
                execute: Execute, write_receipt: bool) -> Result:
    """The claimed transaction body: spec loaded AFTER the claim, so every
    read (spec snapshot, parent, PR evidence) and the provider mutation run
    inside the relink-excluded window."""
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

    # PR evidence belongs to the source Git checkout, not the configured
    # tracker transport. In particular, Jira DC sslVerify=false is valid for
    # Jira HTTP but cannot be applied to the independent gh CLI route.
    pr_evidence = merge_evidence(config, spec_data, execute)
    tasks = _load_tasks(flow_dir, spec_id)
    flow_norm = flow_to_normalized(
        spec_data, pr_evidence,
        _completion_review_configured(config, spec_data),
        tasks=tasks,
    )

    tracker_norm = tracker_norm_from_parent(provider, parent, dest)
    repair_retry = False
    if isinstance(tracker_norm, TrackerError):
        # A prior GitHub write may have landed native state + target label but
        # failed to remove the old label even after its bounded repair. On a
        # later invocation normalization sees an ambiguous namespace before
        # the ordinary decision ladder. Recover only when native state,
        # requested target, merge evidence, and the policy all prove the
        # requested transition is already the intended state. Then replay the
        # idempotent provider write as an APPLY so repaired convergence earns
        # lastSyncedAt + receipt instead of being mistaken for a noop.
        if (provider == "github"
                and tracker_norm.subtype == "ambiguous-status-labels"):
            native_norm = github_native_status(parent)
            repair_decision = decide(
                to, reason, flow_norm, native_norm, pr_evidence,
                conflict_tiebreak)
            if repair_decision.kind == "noop" and native_norm == to:
                tracker_norm = native_norm
                repair_retry = True
                decision = repair_decision
            elif (repair_decision.kind == "apply"
                  and repair_decision.target_slot):
                tracker_norm = native_norm
                repair_retry = True
                decision = repair_decision
            else:
                return tracker_norm
        else:
            return tracker_norm
    if not repair_retry:
        decision = decide(
            to, reason, flow_norm, tracker_norm, pr_evidence,
            conflict_tiebreak)
    err = decision_as_error(decision)
    if err:
        return err

    verified_target = decision.target_slot or to
    use_verified = (
        verified_target == "done"
        and str(spec_data.get("completion_review_status") or "") == "ship"
        and pr_evidence == "merged"
    )
    label_only_repair = False
    if (provider == "github" and decision.kind == "noop"
            and github_native_status(parent) == to
            and not github_status_labels_match(
                parent, target_slot=to,
                use_verified_label=use_verified)):
        # Native state + flow policy + requested target already agree. Repair
        # only the reduced-fidelity label namespace; replaying PATCH state
        # here could overwrite an authoritative close reason such as
        # `duplicate`. Promoting to APPLY ensures repaired convergence earns
        # lastSyncedAt and a receipt.
        decision = Decision(
            "apply", target_slot=to, reason="status-label-repair")
        label_only_repair = True

    prior_synced = tracker.get("lastSyncedAt")

    def noop_result(*, noop_reason: Optional[str] = None) -> Result:
        # A prior applied run may have landed its state/base but failed only
        # while writing the lifecycle receipt. Re-emit event evidence from
        # the converged retry without mutating or advancing lastSyncedAt.
        if write_receipt:
            rerr = write_sync_receipt(
                flow_dir, spec_id=spec_id, status="noop",
                tracker_id=durable, event=event, transport=provider,
                note=(
                    f"status already converged ({noop_reason})"
                    if noop_reason else "status already converged"),
            )
            if rerr:
                return rerr
        result = {
            "kind": "noop",
            "to": to,
            "flow": flow_norm,
            "tracker": tracker_norm,
            "pr_evidence": pr_evidence,
            "lastSyncedAt": prior_synced,
        }
        if noop_reason:
            result["reason"] = noop_reason
        return result

    if decision.kind == "noop":
        return noop_result()

    if decision.kind == "apply_local":
        # Convergence: the fold writes RAW spec.status=done. When a
        # completion-review backend is configured and no ship is recorded,
        # flow_to_normalized keeps deriving in_review from that done, so the
        # same terminal disagreement re-classifies as apply_local on every
        # run - each pass rewriting the identical status and advancing
        # lastSyncedAt for a sync that changed nothing. The raw local status
        # is the honest convergence check: already folded -> noop, no write,
        # no lastSyncedAt advance (the residual review gate is derived
        # state, not sync work).
        if spec_data.get("status") == "done":
            return noop_result(noop_reason="already_folded")
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
    if label_only_repair:
        written = repair_github_status_labels(
            config, locator, parent, ex,
            target_slot=decision.target_slot,
            use_verified_label=use_verified)
    else:
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
        return noop_result(noop_reason=str(
            written.get("reason") or "provider_already_current"))

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
