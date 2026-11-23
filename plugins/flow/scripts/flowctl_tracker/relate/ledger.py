"""depRelations ledger helpers + flow:deps marker constants (fn-140.4 / fn-64).

Edge-key semantics match flowctl._dep_relation_key: sha256 of the directed
(from_tracker_id \\x00 to_tracker_id) pair, truncated to 16 hex chars.

The <!-- flow:deps --> marker is importable for .5 body hashing (exclusion is a
HASHING concern there - this module does not hash bodies).
"""

from __future__ import annotations

import hashlib
import os
import socket
import time
from typing import Any, Optional

from ..lifecycle.helpers import dict_, now_iso
from ..types import TrackerError

#: Provenance fence for GitHub fenced fallback / GitLab dual-write body block.
#: Importable by sync-body (.5); do not strip or rewrite here.
FLOW_DEPS_OPEN = "<!-- flow:deps -->"
FLOW_DEPS_CLOSE = "<!-- /flow:deps -->"

#: Fields present ONLY on a pending entry (dropped at finalize so applied
#: entries stay byte-shaped like pre-existing fn-64 entries). The owner triple
#: mirrors lifecycle create-first claims: it lets a later invocation tell a
#: LIVE concurrent owner from a crashed run's leftover.
CLAIM_FIELDS = ("status", "pid", "host", "claimedAt")


def claim_owner() -> dict:
    """Owner triple recorded on a pending claim (create-first claim shape)."""
    return {"pid": os.getpid(), "host": socket.gethostname(),
            "claimedAt": time.time()}


def dep_relation_key(from_tracker_id: str, to_tracker_id: str) -> str:
    """Opaque stable edge key - same semantics as flowctl._dep_relation_key."""
    return hashlib.sha256(
        f"{from_tracker_id}\x00{to_tracker_id}".encode("utf-8")
    ).hexdigest()[:16]


def ledger_has(tracker: dict, key: str) -> bool:
    for entry in tracker.get("depRelations") or []:
        if isinstance(entry, dict) and entry.get("key") == key:
            return True
    return False


def ledger_entry(tracker: dict, key: str) -> Optional[dict]:
    """The ledger entry for `key`, or None. An entry WITHOUT a `status` field
    is applied (the fn-64 schema); `status: "pending"` marks recorded intent
    whose provider create + finalize has not completed yet (crash-safe
    two-phase write - ownership is durable before the remote mutation)."""
    for entry in tracker.get("depRelations") or []:
        if isinstance(entry, dict) and entry.get("key") == key:
            return entry
    return None


def ledger_append(tracker: dict, *, key: str, dep_spec: str,
                  from_tracker_id: str, to_tracker_id: str,
                  rel_type: str = "blocks", source: str = "flow",
                  status: Optional[str] = None,
                  claim: Optional[dict] = None) -> dict:
    """Idempotent append. Returns the (possibly unchanged) tracker block.
    `status="pending"` records ownership INTENT before the provider mutation;
    omitted means applied (field absent, matching existing fn-64 entries).
    `claim` (the `claim_owner()` triple) stamps ownership onto a pending
    entry so later invocations can classify it live vs stale."""
    ledger = list(tracker.get("depRelations") or [])
    for entry in ledger:
        if isinstance(entry, dict) and entry.get("key") == key:
            tracker = dict(tracker)
            tracker["depRelations"] = ledger
            return tracker
    new: dict = {
        "key": key,
        "dep_spec": dep_spec,
        "from_tracker_id": from_tracker_id,
        "to_tracker_id": to_tracker_id,
        "type": rel_type,
        "source": source,
        "updatedAt": now_iso(),
    }
    if status is not None:
        new["status"] = status
        if claim:
            new.update(claim)
    ledger.append(new)
    tracker = dict(tracker)
    tracker["depRelations"] = ledger
    return tracker


def ledger_finalize(tracker: dict, *, key: str) -> dict:
    """Mark a pending entry applied by DROPPING its status field (and the
    claim-owner triple), so finalized entries are byte-shaped like
    pre-existing fn-64 entries. Idempotent."""
    ledger = []
    for entry in tracker.get("depRelations") or []:
        if (isinstance(entry, dict) and entry.get("key") == key
                and entry.get("status") == "pending"):
            entry = {k: v for k, v in entry.items() if k not in CLAIM_FIELDS}
            entry["updatedAt"] = now_iso()
        ledger.append(entry)
    tracker = dict(tracker)
    tracker["depRelations"] = ledger
    return tracker


def ledger_drop(tracker: dict, *, key: str) -> dict:
    """DROP an APPLIED entry after its native relation has been removed (or
    proven absent) remotely - the reconcile counterpart of append+finalize.
    Pending entries are ownership claims and stay untouched (ledger_release
    owns those). Idempotent on missing keys."""
    ledger = [
        entry
        for entry in tracker.get("depRelations") or []
        if not (isinstance(entry, dict) and entry.get("key") == key
                and entry.get("status") != "pending")
    ]
    tracker = dict(tracker)
    tracker["depRelations"] = ledger
    return tracker


def ledger_release(tracker: dict, *, key: str, force: bool = False) -> dict:
    """DROP a pending entry owned by THIS process (call under the shared
    writer lock, after an OBSERVED provider create failure that definitely
    did NOT land). Restores the entry-absent state so an immediate retry -
    typically a new pid - can claim and create again instead of failing
    concurrent_claim for the full stale window. Entries that are applied,
    missing, or owned by another process are left untouched (idempotent).

    force=True drops the pending entry regardless of its owner triple - for
    the finalize-time identity-drift refusal ONLY (call under the lock,
    after the drift is established): a pending entry keyed by the OLD
    tracker ids can never be validly finalized after a relink (no future
    run of the new pair computes its key), so it must not linger on the
    relinked spec even when it was claimed by an earlier interrupted run."""
    me = claim_owner()
    ledger = []
    for entry in tracker.get("depRelations") or []:
        if (isinstance(entry, dict) and entry.get("key") == key
                and entry.get("status") == "pending"
                and (force or (entry.get("pid") == me["pid"]
                               and entry.get("host") == me["host"]))):
            continue
        ledger.append(entry)
    tracker = dict(tracker)
    tracker["depRelations"] = ledger
    return tracker


def ledger_stamp_claim(tracker: dict, *, key: str) -> dict:
    """RECLAIM a stale pending entry: overwrite its owner triple with OURS
    (call under the shared writer lock, after re-checking staleness).
    Idempotent on non-pending / missing entries."""
    ledger = []
    for entry in tracker.get("depRelations") or []:
        if (isinstance(entry, dict) and entry.get("key") == key
                and entry.get("status") == "pending"):
            entry = dict(entry)
            entry.update(claim_owner())
            entry["updatedAt"] = now_iso()
        ledger.append(entry)
    tracker = dict(tracker)
    tracker["depRelations"] = ledger
    return tracker


def blocker_completed(status: Any) -> bool:
    """Completed-blocker rule: local dep-spec status done/closed is NOT projected."""
    if not isinstance(status, str):
        return False
    return status.strip().lower() in {"done", "closed"}


def require_linked_pair(self_tracker: dict, other_tracker: dict, *,
                       self_id: str, other_id: str
                       ) -> Optional[TrackerError]:
    """Both sides must be durable-linked; identifier_only/unlinked → unresolved."""
    from ..lifecycle.linkstate import require_durable  # noqa: PLC0415
    a = require_durable(self_tracker)
    if isinstance(a, TrackerError):
        return TrackerError(
            a.cls, f"spec {self_id}: {a.message}", subtype=a.subtype,
            details=a.details)
    b = require_durable(other_tracker)
    if isinstance(b, TrackerError):
        return TrackerError(
            b.cls, f"spec {other_id}: {b.message}", subtype=b.subtype,
            details=b.details)
    return None


def caps_of(config: dict) -> dict:
    caps = dict_(dict_(dict_(config.get("tracker")).get("resolved")).get("capabilities"))
    if caps:
        return caps
    from ..resolved_cache import STATIC_CAPABILITIES  # noqa: PLC0415
    t = dict_(config.get("tracker")).get("type")
    return dict(STATIC_CAPABILITIES.get(t) or {})
