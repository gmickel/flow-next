"""create / create-first / persist-external verbs (fn-140.2)."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path
from typing import Optional

from ..executor import execute as default_execute
from ..types import ErrorClass, TrackerError
from .helpers import (CREATE_FIRST_KEY_RE, Execute, Result, atomic_write_json,
                      leaf_is_safe,
                      load_spec, merged_tracker, now_iso,
                      read_config, tracker_type, write_sync_receipt)
from .helpers import locked_tracker_write as _locked_tracker_write
from .linkstate import derive_link_state, resolve_linear_uuid
from .providers import provider_create


def _claim_spec_create(flow_dir: Path, spec_id: str, rec_path: Path,
                       provider: str, title: str) -> Optional[TrackerError]:
    """Reserve an unlinked spec under the shared writer lock BEFORE the
    provider create (create-first's claim pattern, keyed on the spec id).
    Two concurrent creates against the same unlinked spec could both pass the
    unlocked linkState check and both reach the provider mutation - two
    remote issues, the later link write orphaning the first. Under the lock:
    the linkState is re-checked from a RELOADED spec, a live claim from
    another process refuses (create_in_flight), and OUR pending claim lands
    durably before any remote mutation. The CRASH window (claim written,
    create landed, process died before the link write) stays open by spec
    decision - this closes only the live concurrent race."""
    unsafe = leaf_is_safe(flow_dir / "create-first", rec_path)
    if unsafe:
        return unsafe
    secured = _ensure_create_first_ignored(flow_dir)
    if secured is not None:
        return secured
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            reloaded = load_spec(flow_dir, spec_id)
            if isinstance(reloaded, TrackerError):
                return reloaded
            _path, spec_data = reloaded
            state = derive_link_state(merged_tracker(spec_data))
            if state != "unlinked":
                return TrackerError(
                    ErrorClass.CONFLICT,
                    f"spec {spec_id!r} is already linked "
                    f"(linkState={state!r}); refuse bare create",
                    subtype="already_linked",
                )
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
                        f"create for spec {spec_id!r} is already in flight "
                        "in another process; retry after it finishes",
                        subtype="create_in_flight",
                        details={"specId": spec_id,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OUR claim below - same rule as
                # create_first.
            claim = {"specId": spec_id, "status": "pending",
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "title": title,
                     "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
    return None


def create(flow_dir, spec_id: str, *, title: str, body: str,
           event: Optional[str] = None,
           execute: Execute = default_execute,
           write_receipt: bool = True) -> Result:
    """Spec exists → provider create → atomic tracker block + sync receipt."""
    flow_dir = Path(flow_dir)
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    path, spec_data = loaded
    tracker = merged_tracker(spec_data)
    if derive_link_state(tracker) != "unlinked":
        return TrackerError(
            ErrorClass.CONFLICT,
            f"spec {spec_id!r} is already linked "
            f"(linkState={derive_link_state(tracker)!r}); refuse bare create",
            subtype="already_linked",
        )
    rec_path = flow_dir / "create-first" / f"spec-{spec_id}.json"
    claimed = _claim_spec_create(flow_dir, spec_id, rec_path, provider, title)
    if claimed is not None:
        return claimed
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    created = provider_create(config, ex, title=title, body=body)
    if isinstance(created, TrackerError):
        _release_claim(rec_path)
        return created
    link_fields = {
        "id": created["id"],
        "identifier": created["identifier"],
        "url": created.get("url"),
        "linkState": "linked",
        "lastSyncedAt": now_iso(),
    }

    def _link(t: dict):
        # An identity that appeared concurrently (e.g. persist-external, which
        # takes no create claim) must never be clobbered - replacing it is
        # exactly the orphan-duplicate the claim exists to prevent. The
        # created identity rides out via the completed-steps decoration below.
        state = derive_link_state(t)
        if state != "unlinked" and str(t.get("id") or "") != str(created["id"]):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"spec {spec_id!r} became {state} to "
                f"{t.get('identifier')!r} while the provider create was in "
                "flight; refusing to overwrite the existing link",
                subtype="already_linked",
                details={"linkState": state,
                         "identifier": t.get("identifier")})
        return {**t, **link_fields}

    # Persist ONLY the link-owned fields onto a spec RELOADED under the shared
    # writer lock - the pre-create snapshot must never be replayed wholesale
    # (a concurrent flowctl update to the same spec landed while the provider
    # request was in flight would be silently erased; status/relate/sync-body
    # follow the same reload-merge rule). The durable-collision scan runs
    # inside the same critical section (check-then-lock was a race).
    err = _locked_tracker_write(
        flow_dir, spec_id, _link, collision_id=created["id"])
    _release_claim(rec_path)
    if isinstance(err, TrackerError):
        # The issue exists but the spec is still unlinked - a bare failure
        # here reads as "nothing happened" and a retry would create a
        # duplicate (the crash window itself stays open by spec decision;
        # this is the OBSERVED-failure path, so the created identity is in
        # hand). TrackerError is frozen: rebuild with the completed-steps
        # detail so the caller can link the existing issue instead.
        import dataclasses  # noqa: PLC0415
        return dataclasses.replace(err, details={
            **(err.details or {}),
            "completed_steps": ["create"],
            "id": created["id"],
            "identifier": created["identifier"],
            "url": created.get("url")})
    if write_receipt:
        err = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="pushed",
            tracker_id=created["id"], event=event, transport=provider,
        )
        if err:
            # The issue exists and the link IS persisted - a bare failure here
            # would read as "nothing happened" and invite a duplicating retry.
            # TrackerError is frozen: rebuild with the completed-steps detail.
            import dataclasses  # noqa: PLC0415
            return dataclasses.replace(err, details={
                **(err.details or {}),
                "completed_steps": ["create", "link"],
                "id": created["id"],
                "identifier": created["identifier"]})
    return {"id": created["id"], "identifier": created["identifier"],
            "url": created.get("url"), "linkState": "linked"}


def compute_create_first_key(tracker_type_name: str, title: str, body: str) -> str:
    """Identical semantics to flowctl.compute_create_first_key (fn-134)."""
    normalized = (tracker_type_name or "").strip().lower()
    payload = "\0".join([normalized, title or "", body or ""])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _create_first_rule_active(gitignore_text: str) -> bool:
    """Real gitignore semantics, not a substring: `# create-first/` is a
    comment (reproduced committable), and a later `!create-first/` negates an
    earlier rule. Last matching line wins, exactly like git."""
    active = False
    for raw in gitignore_text.splitlines():
        line = raw.strip()
        if line in ("create-first/", "/create-first/", "create-first"):
            active = True
        elif line in ("!create-first/", "!/create-first/", "!create-first"):
            active = False
    return active


def _ensure_create_first_ignored(flow_dir: Path):
    """fn-134 cross-checkout safety: a COMMITTED recovery record makes another
    checkout resume onto someone else's issue. Repos initialized before the
    managed `create-first/` ignore pattern existed can commit it silently, so
    the verb secures storage BEFORE any remote mutation - and aborts when it
    cannot (a symlinked .gitignore is never written through).
    """
    gi = flow_dir / ".gitignore"
    unsafe = leaf_is_safe(flow_dir, gi)
    if unsafe:
        return unsafe
    try:
        existing = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    except OSError as exc:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"cannot read .flow/.gitignore: {exc}",
                            subtype="gitignore")
    if _create_first_rule_active(existing):
        return None
    try:
        # Appended BELOW flowctl's managed block: init's reconciliation
        # preserves user patterns after the footer, so this survives upgrades.
        with open(gi, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("create-first/\n")
    except OSError as exc:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"cannot secure .flow/.gitignore: {exc}; refusing "
                            "to create before storage is safe",
                            subtype="gitignore")
    return None


def _claim_is_stale(claim: dict, rec_path: Path) -> bool:
    """config_lock's owner rules applied to a pending create-first claim: a
    claim older than STALE_OWNER_S whose pid is dead ON THIS HOST is a crashed
    run's leftover and reclaimable. Another host's pid space is unknowable
    (shared/network checkout) - fail closed, exactly like the config lock."""
    from ..config_lock import STALE_OWNER_S, _pid_alive  # noqa: PLC0415
    now = time.time()
    try:
        claimed_at = float(claim["claimedAt"])
        pid = int(claim["pid"])
        host = str(claim["host"])
    except (KeyError, TypeError, ValueError):
        # Truncated/corrupt claim: fall back to file age (mirror config_lock's
        # ownerless-directory rule) - refusing forever would wedge the key.
        try:
            return (now - rec_path.stat().st_mtime) > STALE_OWNER_S
        except OSError:
            return False
    if (now - claimed_at) <= STALE_OWNER_S:
        return False
    if host != socket.gethostname():
        return False
    return not _pid_alive(pid)


def _release_claim(rec_path: Path) -> None:
    """Best-effort removal of OUR pending claim after an OBSERVED create
    failure, restoring the record-absent state so a retry may create again.
    Safe without the lock: while a live claim exists, every other process
    refuses (create_in_flight) rather than touch the record path."""
    try:
        cur = json.loads(rec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if (isinstance(cur, dict) and cur.get("status") == "pending"
            and cur.get("pid") == os.getpid()
            and cur.get("host") == socket.gethostname()):
        try:
            rec_path.unlink()
        except OSError:
            pass


def create_first(flow_dir, *, title: str, body: str, retry_key: str,
                 execute: Execute = default_execute) -> Result:
    """NO spec, NO receipt. Recovery record is the retry-dedupe guarantee."""
    flow_dir = Path(flow_dir)
    if not CREATE_FIRST_KEY_RE.fullmatch(retry_key or ""):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"invalid --retry-key {retry_key!r}: expected 16 hex",
                            subtype="retry_key")
    config = read_config(flow_dir)
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    rec_path = flow_dir / "create-first" / f"{retry_key}.json"
    unsafe = leaf_is_safe(flow_dir / "create-first", rec_path)
    if unsafe:
        return unsafe
    secured = _ensure_create_first_ignored(flow_dir)
    if secured is not None:
        return secured
    # Two concurrent create-first calls with the same retry key could both
    # observe the record absent and both run provider_create - two remote
    # issues, the last record write hiding the first. The retry key is CLAIMED
    # under the shared writer lock BEFORE the remote create (relate's
    # two-phase ledger pattern: intent lands durably first, the network call
    # runs OUTSIDE the lock). While OUR live claim exists no other process
    # writes the record path, so the finalize/release below need no lock.
    from ..config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
    try:
        with config_lock(flow_dir):
            if rec_path.is_file():
                try:
                    prior = json.loads(rec_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    prior = None
                if isinstance(prior, dict) and prior.get("id"):
                    return {"id": prior["id"],
                            "identifier": prior.get("identifier"),
                            "url": prior.get("url"), "retried": True}
                if (isinstance(prior, dict)
                        and prior.get("status") == "pending"
                        and not _claim_is_stale(prior, rec_path)):
                    return TrackerError(
                        ErrorClass.CONFLICT,
                        f"create-first for retry key {retry_key!r} is already "
                        "in flight in another process; retry after it "
                        "finishes to reuse its recorded issue",
                        subtype="create_in_flight",
                        details={"retryKey": retry_key,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OUR claim below. The duplicate window
                # this reopens (crash after the remote create landed but
                # before the record write) is exactly the pre-record window
                # that existed before claims - no new exposure.
            claim = {"retryKey": retry_key, "status": "pending",
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "title": title,
                     "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    created = provider_create(config, ex, title=title, body=body)
    if isinstance(created, TrackerError):
        _release_claim(rec_path)
        return created
    record = {
        "retryKey": retry_key,
        "id": created["id"],
        "identifier": created["identifier"],
        "url": created.get("url"),
        "title": title,
        "createdAt": now_iso(),
        "transport": provider,
    }
    err = atomic_write_json(rec_path, record)
    if err:
        # The issue exists but the claim is still pending - a bare failure
        # would leave retries refusing (create_in_flight) until the claim
        # goes stale, with the created identity lost. TrackerError is frozen:
        # rebuild with the completed-steps detail so the caller can link the
        # existing issue instead of waiting out the stale window.
        import dataclasses  # noqa: PLC0415
        return dataclasses.replace(err, details={
            **(err.details or {}),
            "completed_steps": ["create"],
            "id": created["id"],
            "identifier": created["identifier"],
            "url": created.get("url"),
            "retryKey": retry_key})
    return {"id": created["id"], "identifier": created["identifier"],
            "url": created.get("url"), "retried": False}


def persist_external(flow_dir, spec_id: str, *, identifier: str,
                     durable_id: Optional[str] = None, url: Optional[str] = None,
                     source: str,
                     execute: Execute = default_execute,
                     event: Optional[str] = None) -> Result:
    """Record an MCP-performed create. source must be mcp; provider=linear."""
    flow_dir = Path(flow_dir)
    if source != "mcp":
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"--source must be 'mcp', got {source!r}",
                            subtype="source")
    if not isinstance(identifier, str) or not identifier.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "--identifier is required", subtype="identifier")
    identifier = identifier.strip()
    config = read_config(flow_dir)
    if tracker_type(config) != "linear":
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "persist-external requires tracker.type=linear",
                            subtype="provider")
    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    path, spec_data = loaded
    tracker = merged_tracker(spec_data)

    # Existing-link guard: persist-external may (a) link an UNLINKED spec,
    # (b) idempotently complete/confirm the SAME identifier, and nothing else.
    # A retry against a linked spec must never repoint it, and a resolution
    # failure must never erase a durable id (reproduced by review: linked/old
    # silently became identifier_only/NEW).
    state = derive_link_state(tracker)
    if state != "unlinked" and tracker.get("identifier") != identifier:
        return TrackerError(
            ErrorClass.CONFLICT,
            f"spec {spec_id!r} is already {state} to "
            f"{tracker.get('identifier')!r}; refusing to repoint to "
            f"{identifier!r}",
            subtype="already_linked",
            details={"linkState": state,
                     "identifier": tracker.get("identifier")})
    if state == "linked":
        # Same identifier, durable already present: idempotent no-op success
        # (unless the caller asserts a DIFFERENT durable - that is a conflict).
        if durable_id and str(durable_id).strip() != str(tracker.get("id")):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"--id {durable_id!r} does not match the linked durable "
                f"{tracker.get('id')!r} for {identifier!r}",
                subtype="durable_mismatch")
        return {"id": tracker.get("id"), "identifier": tracker.get("identifier"),
                "url": tracker.get("url"), "linkState": "linked",
                "idempotent": True}

    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)

    resolved_id = (durable_id.strip()
                   if isinstance(durable_id, str) and durable_id.strip() else None)
    resolved_url = url
    degraded = None
    if resolved_id is None:
        resolved = resolve_linear_uuid(ex, identifier)
        if isinstance(resolved, TrackerError):
            # Degrade ONLY on reachability failures. A semantic answer -
            # not-found, auth, invalid input, conflict - is a real verdict
            # about this identifier and must propagate unchanged, never be
            # dressed up as "GraphQL unreachable".
            if resolved.cls not in (ErrorClass.TRANSPORT, ErrorClass.RATE_LIMITED):
                return resolved
            degraded = {"kind": "identifier_only",
                        "reason": resolved.cls.value,
                        "identifier": identifier, "url": url}
            tracker.update({
                "id": None, "identifier": identifier, "url": url,
                "linkState": "identifier_only", "lastSyncedAt": now_iso(),
            })
        else:
            resolved_id = resolved["id"]
            identifier = resolved["identifier"]
            resolved_url = resolved.get("url") or url
            tracker.update({
                "id": resolved_id, "identifier": identifier, "url": resolved_url,
                "linkState": "linked", "lastSyncedAt": now_iso(),
            })
    else:
        # A caller-supplied durable is VERIFIED against GraphQL when reachable:
        # persisting an unchecked id is how a typo becomes a wrong link. On
        # mismatch -> conflict; GraphQL unreachable -> trust the explicit id
        # (the caller asserted it; identifier_only would discard information).
        check = resolve_linear_uuid(ex, identifier)
        if isinstance(check, dict) and str(check["id"]) != str(resolved_id):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"--id {resolved_id!r} does not match the id GraphQL resolves "
                f"for {identifier!r} ({check['id']!r})",
                subtype="durable_mismatch",
                details={"normalized": "durable", "candidates": [
                    {"durable": resolved_id, "role": "caller"},
                    {"durable": check["id"], "role": "graphql"},
                ]})
        if isinstance(check, TrackerError) and check.cls not in (
                ErrorClass.TRANSPORT, ErrorClass.RATE_LIMITED):
            return check
        if isinstance(check, dict):
            resolved_url = check.get("url") or resolved_url
        tracker.update({
            "id": resolved_id, "identifier": identifier, "url": resolved_url,
            "linkState": "linked", "lastSyncedAt": now_iso(),
        })

    # Persist ONLY the link-owned fields onto a spec RELOADED under the shared
    # writer lock - the snapshot loaded before the UUID resolve/verify request
    # must never be replayed wholesale (a concurrent flowctl update to the
    # same spec landed while GraphQL was in flight would be silently erased;
    # status/relate/sync-body follow the same reload-merge rule). The
    # durable-collision scan runs INSIDE the same critical section via
    # collision_id: an unlocked pre-scan is a check-then-lock race - two
    # specs persisting the same durable id could both pass it, then both
    # serialized writes succeed.
    owned = {key: tracker.get(key)
             for key in ("id", "identifier", "url", "linkState", "lastSyncedAt")}

    def _persist(t: dict):
        # A link that appeared on THIS spec while GraphQL was in flight is
        # never repointed and never downgraded: overwriting it repeats the
        # existing-link-guard regression (linked/old silently became a new
        # identity), and a degraded identifier_only write would erase a
        # durable id.
        state = derive_link_state(t)
        if state != "unlinked" and (
                t.get("identifier") != owned.get("identifier")
                or (owned.get("id") is None and t.get("id"))):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"spec {spec_id!r} became {state} to "
                f"{t.get('identifier')!r} while persist-external was in "
                "flight; refusing to overwrite the existing link",
                subtype="already_linked",
                details={"linkState": state,
                         "identifier": t.get("identifier")})
        return {**t, **owned}

    persisted = _locked_tracker_write(
        flow_dir, spec_id, _persist, collision_id=resolved_id)
    if isinstance(persisted, TrackerError):
        return persisted

    note = None
    status = "pushed"
    if degraded is not None:
        note = (f"identifier_only: UUID resolution degraded for "
                f"identifier={identifier} url={resolved_url}")
        status = "updated"
    err = write_sync_receipt(
        flow_dir, spec_id=spec_id, status=status,
        tracker_id=resolved_id, event=event, transport="mcp", note=note,
        degraded=degraded,
    )
    if err:
        # The link IS persisted - a bare failure here reads as "nothing
        # happened", and a retry takes the state == linked idempotent return
        # above without ever reporting the partial success. TrackerError is
        # frozen: rebuild with the completed-steps detail so the caller holds
        # the linked identity (mirrors the create() receipt-failure branch).
        import dataclasses  # noqa: PLC0415
        return dataclasses.replace(err, details={
            **(err.details or {}),
            "completed_steps": ["link"],
            "id": tracker.get("id"),
            "identifier": tracker.get("identifier"),
            "linkState": tracker["linkState"]})
    return {"id": tracker.get("id"), "identifier": tracker.get("identifier"),
            "url": tracker.get("url"), "linkState": tracker["linkState"],
            "degraded": degraded}
