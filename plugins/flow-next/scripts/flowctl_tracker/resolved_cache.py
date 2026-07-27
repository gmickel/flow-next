"""`tracker.resolved`: resolve once, consume deterministically (fn-139.3).

This module owns the cache schema, the scoped-timestamp rules, the resolve
TRANSACTION, the cache state machine (behind a seam - spec B wires the real
verbs), and the `apiVersion: 3 -> 2` migration.

The transaction is the hard part. Atomic write plus a lock does NOT prevent
stale resolution: a resolver can query project A, then a `config set` repoints
the tracker to project B, and the resolver merges A's ids into B's config.
Required order, implemented in `resolve_transaction`:

    network work OUTSIDE the lock
    acquire the lock shared by every .flow/config.json writer
    re-read INSIDE
    compare the discovery-input FINGERPRINT
    merge ONLY the resolved scope
    validate
    atomically replace

Fingerprint mismatch has ONE bounded behavior: discard and re-resolve once; a
second mismatch returns `class: conflict` rather than looping.
"""

from __future__ import annotations

import enum
import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from .config_lock import ConfigLockTimeout, ConfigLockUnsafe, config_lock
from .types import ErrorClass, TrackerError

#: Canonical scope paths - the ONLY keys `scopeResolvedAt` may contain.
SCOPES = ("destination", "destination.statusIds", "destination.stateIds", "capabilities")

#: Only GitLab has a dynamic capability (plan-gated blockedBy); everyone else
#: is static and never re-probed.
CAPABILITY_TTL_HOURS = 24.0

CAPABILITY_KEYS = ("attachments", "blockedBy", "subIssues", "deleteIssue")

#: Fields `resolvedAt` requires per tracker (spec A resolved-fields table).
#: `resolvedAt` is a completeness statement, never a TTL input.
REQUIRED_DESTINATION_FIELDS = {
    "github": ("owner", "repo"),
    "gitlab": ("projectId", "projectPath", "host", "namespaceId"),
    "linear": ("teamId", "teamKey", "stateIds", "labelIds"),
    "jira": ("baseUrl", "projectKey", "projectId", "issueTypeId",
             "apiVersion", "style", "statusIds"),
}

#: Capability truth table, decided in spec A so B cannot leave it open. GitLab
#: `blockedBy` is plan-dependent and filled by the tier probe, not this table.
STATIC_CAPABILITIES = {
    "github": {"attachments": False, "blockedBy": False, "subIssues": True, "deleteIssue": False},
    "gitlab": {"attachments": True, "subIssues": False, "deleteIssue": True},
    "linear": {"attachments": True, "blockedBy": True, "subIssues": False, "deleteIssue": True},
    "jira": {"attachments": True, "blockedBy": True, "subIssues": False, "deleteIssue": True},
}

#: GitLab plans that unlock `blockedBy` (measured: Free rejects, Ultimate
#: accepts; trials are group-scoped).
_GITLAB_BLOCKEDBY_PLANS = frozenset({
    "premium", "premium_trial", "ultimate", "ultimate_trial", "gold", "silver",
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Discovery fingerprint (R8)
# ---------------------------------------------------------------------------

#: Every discovery input the network work depends on. A resolver that queried
#: with one set of these must not merge its answer into a config where any of
#: them changed.
_FINGERPRINT_KEYS = ("type", "host", "baseUrl", "project", "projectId",
                     "projectKey", "teamId", "owner", "repo")


def discovery_fingerprint(config: dict) -> str:
    tracker = config.get("tracker") or {}
    per = tracker.get("perTracker") or {}
    material = {"type": tracker.get("type")}
    for k in _FINGERPRINT_KEYS[1:]:
        material[k] = per.get(k)
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Timestamp + merge rules (R10, R12-partial)
# ---------------------------------------------------------------------------

def _required_complete(resolved: dict, tracker_type: str) -> bool:
    dest = resolved.get("destination")
    caps = resolved.get("capabilities")
    if not isinstance(dest, dict) or not isinstance(caps, dict):
        return False
    required = REQUIRED_DESTINATION_FIELDS.get(tracker_type)
    if required is None:
        return False
    for f in required:
        value = dest.get(f)
        if value is None or value == "":
            # NOTE: an empty dict is PRESENT (a team with zero labels has
            # labelIds {}); slot-level completeness below is what guards the
            # ids maps, not container non-emptiness.
            return False
    # Slot-level rule: resolution completes only when every REQUIRED normalized
    # slot is filled (todo / in_progress / done - fn-139.6 vocabulary).
    ids_key = {"linear": "stateIds", "jira": "statusIds"}.get(tracker_type)
    if ids_key:
        from .states import REQUIRED_SLOTS
        ids = dest.get(ids_key)
        if not isinstance(ids, dict) or not all(s in ids for s in REQUIRED_SLOTS):
            return False
    return all(isinstance(caps.get(k), bool) for k in CAPABILITY_KEYS)


def _recompute_resolved_at(resolved: dict, tracker_type: str, now: str) -> None:
    """`resolvedAt` rule, verbatim from the epic:

    set ONLY when every required field is present; PRESERVED across a partial
    refresh; CLEARED if a refresh reveals a now-missing required field.
    """
    if _required_complete(resolved, tracker_type):
        if not resolved.get("resolvedAt"):
            resolved["resolvedAt"] = now
        # else: preserved - a partial refresh never bumps it.
    else:
        resolved["resolvedAt"] = None


def apply_scope_result(config: dict, scope: str, data: Any, *,
                       now: Optional[str] = None) -> dict:
    """Pure scope merge: stamp exactly one `scopeResolvedAt` entry and touch
    ONLY that scope's data. Returns the same config object, mutated.

    A destination refresh must not clobber `statusIds`/`stateIds` (their own
    scopes) and must not make capabilities look fresh - scope isolation is the
    reason the map exists.
    """
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; canonical scopes are {SCOPES}")
    now = now or _now_iso()
    tracker = config.setdefault("tracker", {})
    resolved = tracker.setdefault("resolved", {})
    sra = resolved.setdefault("scopeResolvedAt", {})

    if scope == "destination":
        if not isinstance(data, dict):
            raise ValueError("destination scope data must be a mapping")
        dest = resolved.setdefault("destination", {})
        for k, v in data.items():
            if k in ("statusIds", "stateIds"):
                raise ValueError(
                    f"{k} belongs to scope 'destination.{k}'; a destination "
                    "refresh must not write it"
                )
            dest[k] = v
    elif scope in ("destination.statusIds", "destination.stateIds"):
        key = scope.split(".", 1)[1]
        if not isinstance(data, dict):
            raise ValueError(f"{scope} data must be a mapping of normalized -> id")
        resolved.setdefault("destination", {})[key] = dict(data)
    else:  # capabilities
        if not isinstance(data, dict) or not all(
                isinstance(data.get(k), bool) for k in CAPABILITY_KEYS):
            raise ValueError(
                f"capabilities data must carry booleans for all of {CAPABILITY_KEYS}")
        allowed = set(CAPABILITY_KEYS) | {"_source"}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown capability keys: {sorted(unknown)}")
        resolved["capabilities"] = dict(data)

    sra[scope] = now
    _recompute_resolved_at(resolved, (tracker.get("type") or ""), now)
    return config


def validate_resolved_block(resolved: dict) -> None:
    """Schema guard run inside the transaction, before the atomic replace."""
    if not isinstance(resolved, dict):
        raise ValueError("tracker.resolved must be an object")
    sra = resolved.get("scopeResolvedAt", {})
    if not isinstance(sra, dict):
        raise ValueError("scopeResolvedAt must be an object")
    unknown = set(sra) - set(SCOPES)
    if unknown:
        raise ValueError(f"scopeResolvedAt has non-canonical keys: {sorted(unknown)}")
    for legacy in ("destinationResolvedAt", "capabilitiesCheckedAt"):
        if legacy in resolved:
            raise ValueError(f"legacy field {legacy!r} is not part of the schema")


def capabilities_stale(config: dict, *, ttl_hours: float = CAPABILITY_TTL_HOURS,
                       now_ts: Optional[float] = None) -> bool:
    """TTL re-probe eligibility. ONLY GitLab has a dynamic capability; every
    other tracker returns False unconditionally (static, never re-probed)."""
    tracker = config.get("tracker") or {}
    if tracker.get("type") != "gitlab":
        return False
    stamp = ((tracker.get("resolved") or {}).get("scopeResolvedAt") or {}).get("capabilities")
    if not stamp:
        return True
    try:
        parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return True
    now_ts = time.time() if now_ts is None else now_ts
    return (now_ts - parsed) > ttl_hours * 3600.0


# ---------------------------------------------------------------------------
# Migration (task: apiVersion 3 -> 2)
# ---------------------------------------------------------------------------

def migrate_config(config: dict) -> bool:
    """`perTracker.apiVersion: 3` -> `2`. Measured: v2 round-trips plain
    strings byte-exact on Cloud AND DC; v3 forces ADF. Returns True if changed.
    """
    per = (config.get("tracker") or {}).get("perTracker")
    if isinstance(per, dict) and per.get("apiVersion") == 3:
        per["apiVersion"] = 2
        return True
    return False


# ---------------------------------------------------------------------------
# The resolve transaction (R8 / R8b)
# ---------------------------------------------------------------------------

def _read_config(config_path: Path) -> dict:
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ValueError(f"unreadable config at {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        # A present-but-non-object config is CORRUPT, not absent. Treating it
        # as {} made the transaction atomically overwrite the file with a fresh
        # document - silently destroying whatever the user had.
        raise ValueError(
            f"config at {config_path} is valid JSON but not an object; "
            "refusing to overwrite it")
    return data


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def resolve_transaction(
    flow_dir: Path,
    scope: str,
    network_fn: Callable[[dict], Union[dict, TrackerError]],
    *,
    now: Optional[str] = None,
    finalize_fn: Optional[Callable[[dict, dict], dict]] = None,
) -> Union[dict, TrackerError]:
    """Run one scoped resolve with the R8 ordering. Returns the merged config,
    or a TrackerError (never raises for the specified failure modes).

    `network_fn(config)` performs the provider round-trip OUTSIDE the lock and
    returns the scope data (or a TrackerError to propagate verbatim).

    `finalize_fn(current_config, data)`, when given, recomputes the scope data
    INSIDE the lock against the just-re-read config. `--select` needs it: its
    data is one slot merged into the current map, and computing that merge from
    the pre-lock read would let two concurrent selects clobber each other with
    whole-map replaces.
    """
    if scope not in SCOPES:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"unknown scope {scope!r}", subtype="scope")
    config_path = Path(flow_dir) / "config.json"
    for _attempt in (1, 2):
        try:
            before = _read_config(config_path)
        except ValueError as exc:
            return TrackerError(ErrorClass.INVALID_INPUT, str(exc), subtype="config")
        fingerprint = discovery_fingerprint(before)

        data = network_fn(before)  # network work OUTSIDE the lock
        if isinstance(data, TrackerError):
            return data

        try:
            with config_lock(flow_dir):
                current = _read_config(config_path)  # re-read INSIDE
                if discovery_fingerprint(current) != fingerprint:
                    # Discovery inputs changed mid-resolve (e.g. a repoint to
                    # another project). Merging would write the OLD project's
                    # ids into the NEW project's config. Bounded: retry once.
                    continue
                migrate_config(current)
                final_data = finalize_fn(current, data) if finalize_fn else data
                apply_scope_result(current, scope, final_data, now=now)
                validate_resolved_block(current["tracker"]["resolved"])
                _atomic_write_json(config_path, current)
                return current
        except ConfigLockTimeout as exc:
            return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
        except ConfigLockUnsafe as exc:
            return TrackerError(ErrorClass.INVALID_INPUT, str(exc), subtype="lock_unsafe")
        except ValueError as exc:
            return TrackerError(ErrorClass.INVALID_INPUT, str(exc), subtype="validate")
    return TrackerError(
        ErrorClass.CONFLICT,
        "discovery inputs changed twice during resolve; refusing to merge "
        "a resolution computed against a repointed tracker",
        subtype="fingerprint",
        details={"scope": scope},
    )


# ---------------------------------------------------------------------------
# Cache state machine, behind a seam (R10, spec-B rows unit-tested here)
# ---------------------------------------------------------------------------

class Trigger(str, enum.Enum):
    ABSENT_BLOCK = "absent_block"            # consuming verb met no cache
    ABSENT_FIELD = "absent_field"            # partial prior resolution
    STALE_ID = "stale_id"                    # write rejected stale_id (spec B)
    CAPABILITY_REJECTED = "capability_rejected"  # write rejected capability (spec B)
    CAPABILITY_TTL = "capability_ttl"        # capabilities scope older than TTL
    AMBIGUOUS_STATE = "ambiguous_state"      # cached stateId gone, >1 candidate
    AUTH_FAILURE = "auth_failure"            # 401/403
    RETRY_EXHAUSTED = "retry_exhausted"      # both attempts failed (spec B)


@dataclass(frozen=True)
class Action:
    """What a trigger requires. Spec B's verbs execute these; A tests them."""

    kind: str                                # "fail" | "resolve_scope" | "degrade" | "probe"
    error_class: Optional[ErrorClass] = None
    scope: Optional[str] = None
    retry_operation: bool = False
    needs_human: bool = False
    note: Optional[str] = None


#: Max scoped re-resolve attempts for a stale id: attempt 1 and attempt 2, then
#: retry-exhausted. From the state table, not tunable.
STALE_ID_MAX_ATTEMPTS = 2


def plan_transition(trigger: Trigger, *, attempt: int = 1,
                    scope: Optional[str] = None) -> Action:
    """The state table as one total function. No trigger falls through."""
    if trigger is Trigger.ABSENT_BLOCK:
        # A consuming verb NEVER resolves implicitly mid-operation and NEVER
        # invents a false capability `false`. Backfill is `resolve`'s job (R9).
        return Action(kind="fail", error_class=ErrorClass.UNRESOLVED,
                      note="run `flowctl tracker resolve` to backfill")
    if trigger is Trigger.ABSENT_FIELD:
        return Action(kind="resolve_scope", scope=scope, retry_operation=True)
    if trigger is Trigger.STALE_ID:
        if attempt <= STALE_ID_MAX_ATTEMPTS:
            return Action(kind="resolve_scope", scope=scope, retry_operation=True)
        return plan_transition(Trigger.RETRY_EXHAUSTED)
    if trigger is Trigger.CAPABILITY_REJECTED:
        # Degrade with a structured `degraded` field; existing relations are
        # left intact (removal would be data loss on a plan downgrade).
        return Action(kind="degrade", scope="capabilities")
    if trigger is Trigger.CAPABILITY_TTL:
        # Synchronous, bounded re-probe - one request, own timeout, no daemon.
        return Action(kind="probe", scope="capabilities")
    if trigger is Trigger.AMBIGUOUS_STATE:
        return Action(kind="fail", error_class=ErrorClass.CONFLICT, needs_human=True,
                      note="surface both candidates; a human picks the slot")
    if trigger is Trigger.AUTH_FAILURE:
        # No retry and NO degradation: a 401/403 must never be misread as a
        # tier downgrade.
        return Action(kind="fail", error_class=ErrorClass.AUTH, needs_human=True)
    if trigger is Trigger.RETRY_EXHAUSTED:
        # Operation fails cleanly, cache untouched.
        return Action(kind="fail", error_class=ErrorClass.UNRESOLVED, needs_human=True,
                      note="cache untouched")
    raise ValueError(f"unknown trigger: {trigger!r}")  # pragma: no cover - enum-total


# ---------------------------------------------------------------------------
# GitLab tier probe application (R10: transient 403 never flips a capability)
# ---------------------------------------------------------------------------

def apply_capability_probe(config: dict, *, ok: bool, plan: Optional[str] = None,
                           reason: Optional[str] = None,
                           now: Optional[str] = None) -> dict:
    """Fold one tier-probe outcome into the cache.

    A FAILED probe is not a capability change: the prior value stays, nothing
    is re-stamped, and the outcome is reported via the returned `probe` field
    `{scope, at, ok, reason}` - distinct from `degraded`, which means an actual
    transition. Returns `{"probe": ..., "degraded": ...}` for the envelope.
    """
    now = now or _now_iso()
    probe = {"scope": "capabilities", "at": now, "ok": bool(ok),
             "reason": None if ok else (reason or "probe failed")}
    if not ok:
        return {"probe": probe, "degraded": None}

    tracker = config.setdefault("tracker", {})
    resolved = tracker.setdefault("resolved", {})
    caps = resolved.get("capabilities")
    prior = caps.get("blockedBy") if isinstance(caps, dict) else None
    new_blocked_by = (plan or "").lower() in _GITLAB_BLOCKEDBY_PLANS

    merged = dict(caps) if isinstance(caps, dict) else {
        **STATIC_CAPABILITIES["gitlab"], "blockedBy": new_blocked_by}
    merged["blockedBy"] = new_blocked_by
    source = dict(merged.get("_source") or {})
    source["gitlabPlan"] = plan
    merged["_source"] = source
    apply_scope_result(config, "capabilities", merged, now=now)

    degraded = None
    if prior is True and new_blocked_by is False:
        degraded = {"capability": "blockedBy", "from": True, "to": False,
                    "reason": f"gitlab plan is {plan!r}"}
    return {"probe": probe, "degraded": degraded}
