"""Spec-aware `tracker relate` verb.

Additive-only blocked-by projection backed by a live remote relation probe
(no local ledger): if the relation is already present on the tracker it no-ops
(repairing a missing GitLab `<!-- flow:deps -->` block when needed); otherwise
it creates the relation. Completed blockers stay projected as historical
ordering. GitHub's single-parent 422 rejection and an unresolved Jira
`blocksLinkType` return structured `queued` results rather than failing.
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
                                 atomic_write_json, leaf_is_safe)
from ..lifecycle.verbs import (_claim_body_mutation,
                               _ensure_create_first_ignored, _release_claim)
from ..types import ErrorClass, TrackerError
from . import providers as P
from .ledger import (blocker_completed, caps_of, dep_relation_key,
                     require_linked_pair)

__all__ = [
    "FLOW_DEPS_CLOSE",
    "FLOW_DEPS_OPEN",
    "dep_relation_key",
    "relate",
    "run",
]

# Re-export marker constants for consumers.
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
            execute=execute)
    finally:
        if body_claim is not None:
            _release_claim(body_claim)
        for rec_path in claimed:
            _release_claim(rec_path)


def _relate_txn(flow_dir: Path, spec_id: str, *, blocked_by: str,
                event: Optional[str], execute: Execute) -> Result:
    """Run probe and additive mutation while both spec claims are live."""
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")

    loaded_a = load_spec(flow_dir, spec_id)
    if isinstance(loaded_a, TrackerError):
        return loaded_a
    _path_a, spec_a = loaded_a
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
    verr = P.display_durable_guard(
        provider, config, ex, locators=(loc_a, loc_b))
    if verr:
        return verr

    # Read live relations from the tracker; no local ledger is stored.
    remote = probe(config, ex, **kwargs)
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
