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


def _claim_spec_operation(flow_dir: Path, spec_id: str, rec_path: Path,
                          provider: str, *, operation: str,
                          require_unlinked: bool,
                          title: Optional[str] = None
                          ) -> Optional[TrackerError]:
    """Reserve a spec identity operation under the shared writer lock.

    Create requires an unlinked spec. Persist-external also uses this same
    spec-keyed claim but permits an idempotent linked state, holding the claim
    through its receipt so relink/clear cannot split persistence from evidence.

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
            if require_unlinked and state != "unlinked":
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
                        f"{prior.get('op') or operation} for spec "
                        f"{spec_id!r} is already in flight "
                        "in another process; retry after it finishes",
                        subtype=("create_in_flight"
                                 if operation == "create"
                                 else "spec_operation_in_flight"),
                        details={"specId": spec_id,
                                 "claim": {"pid": prior.get("pid"),
                                           "host": prior.get("host"),
                                           "claimedAt": prior.get("claimedAt")}},
                        auto_retryable=True)
                # A STALE pending claim (crashed run) is reclaimed by
                # overwriting it with OUR claim below - same rule as
                # create_first.
            claim = {"specId": spec_id, "status": "pending",
                     "op": operation,
                     "pid": os.getpid(), "host": socket.gethostname(),
                     "claimedAt": time.time(), "title": title,
                     "transport": provider}
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
    return None


def _claim_spec_create(flow_dir: Path, spec_id: str, rec_path: Path,
                       provider: str, title: str) -> Optional[TrackerError]:
    return _claim_spec_operation(
        flow_dir, spec_id, rec_path, provider,
        operation="create", require_unlinked=True, title=title)


def _create_transaction(flow_dir, spec_id: str, *, title: str, body: str,
                        flow_body: Optional[str] = None,
                        event: Optional[str] = None,
                        execute: Execute = default_execute,
                        write_receipt: bool = True) -> Result:
    """Create, link, fresh-read, seed the paired base, then write one receipt."""
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
    if isinstance(err, TrackerError):
        # The issue exists but the spec is still unlinked - a bare failure
        # here reads as "nothing happened" and a retry would create a
        # duplicate (the crash window itself stays open by spec decision;
        # this is the OBSERVED-failure path, so the created identity is in
        # hand). TrackerError is frozen: rebuild with the completed-steps
        # detail so the caller can link the existing issue instead.
        import dataclasses  # noqa: PLC0415
        details = {
            **(err.details or {}),
            "completed_steps": ["create"],
            "id": created["id"],
            "identifier": created["identifier"],
            "url": created.get("url"),
        }
        if created.get("degraded") is not None:
            details["degraded"] = created["degraded"]
        failed = dataclasses.replace(err, details=details)
        _release_claim(rec_path)
        return failed

    # A durable link is not a completed create lifecycle until both base forms
    # reflect one real sync point. Import locally to avoid the intentional
    # lifecycle.verbs <-> syncbody module dependency at import time.
    from ..syncbody import sync_body  # noqa: PLC0415
    seed_flow_body = (
        created.get("seedFlowBody")
        if "seedFlowBody" in created
        else (body if flow_body is None else flow_body)
    )
    seeded = sync_body(
        flow_dir, spec_id,
        flow_file_body=seed_flow_body,
        expected_tracker_body=created.get("bodyWritten"),
        direction="pull", event=event, execute=execute, write_receipt=False,
    )
    if isinstance(seeded, TrackerError):
        import dataclasses  # noqa: PLC0415
        details = {
            **(seeded.details or {}),
            "completed_steps": ["create", "link"],
            "id": created["id"],
            "identifier": created["identifier"],
            "url": created.get("url"),
        }
        if created.get("degraded") is not None:
            details["degraded"] = created["degraded"]
        failed = dataclasses.replace(seeded, details=details)
        if write_receipt:
            rerr = write_sync_receipt(
                flow_dir, spec_id=spec_id, status="errored",
                tracker_id=created["id"], event=event, transport=provider,
                note="create linked; paired-base seed failed",
                degraded=created.get("degraded"),
                details=details,
            )
            if rerr is not None:
                details["receipt_status"] = "unwritten"
                details["receipt_write_failed"] = {
                    "class": rerr.cls.value,
                    "subtype": rerr.subtype,
                    "message": rerr.message,
                }
                failed = dataclasses.replace(failed, details=details)
        _release_claim(rec_path)
        return failed

    if write_receipt:
        err = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="pushed",
            tracker_id=created["id"], event=event, transport=provider,
            degraded=created.get("degraded"),
        )
        if err:
            # The issue exists and the link IS persisted - a bare failure here
            # would read as "nothing happened" and invite a duplicating retry.
            # TrackerError is frozen: rebuild with the completed-steps detail.
            import dataclasses  # noqa: PLC0415
            details = {
                **(err.details or {}),
                "completed_steps": ["create", "link", "paired-base"],
                "id": created["id"],
                "identifier": created["identifier"],
            }
            if created.get("degraded") is not None:
                details["degraded"] = created["degraded"]
            failed = dataclasses.replace(err, details=details)
            _release_claim(rec_path)
            return failed
    result = {"id": created["id"], "identifier": created["identifier"],
              "url": created.get("url"), "linkState": "linked",
              "paired_base": seeded}
    if created.get("degraded") is not None:
        result["degraded"] = created["degraded"]
    _release_claim(rec_path)
    return result


def create(flow_dir, spec_id: str, *, title: str, body: str,
           flow_body: Optional[str] = None,
           event: Optional[str] = None,
           execute: Execute = default_execute,
           write_receipt: bool = True) -> Result:
    """Create transaction with exception-safe release of its spec claim."""
    flow_dir = Path(flow_dir)
    rec_path = flow_dir / "create-first" / f"spec-{spec_id}.json"
    completed = False
    try:
        result = _create_transaction(
            flow_dir, spec_id, title=title, body=body, flow_body=flow_body,
            event=event, execute=execute, write_receipt=write_receipt)
        completed = True
        return result
    finally:
        # Normal branches release themselves. Only an unexpected raise can
        # strand OUR claim; a normal create_in_flight result may describe a
        # same-process nested contender and must not delete the winner's claim.
        if not completed:
            _release_claim(rec_path)


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


def _claim_body_mutation(flow_dir: Path, provider: str, locator: dict, *,
                         operation: str,
                         spec_id: Optional[str] = None) -> Path | TrackerError:
    """Serialize whole issue-body read/replace transactions per remote issue.

    ``sync-body``, direct wire body updates, and GitLab ``relate`` can all read
    the current body and later replace it wholesale. Their operation/identity
    claims have different purposes and deliberately do not exclude one another,
    so none protects this shared remote resource. Key by provider + durable id,
    not spec id: two force-aliased specs targeting one issue must serialize,
    while unrelated issues remain concurrent.

    The claim is additive: spec-aware callers retain their existing claims,
    then take this one before the first relevant remote read and hold it through
    readback/finalization. It is fail-fast (never waits while holding another
    claim) and uses the same stale-owner rules as every create-first claim.
    """
    durable = locator.get("durable") if isinstance(locator, dict) else None
    display = locator.get("display") if isinstance(locator, dict) else None
    if not isinstance(durable, str) or not durable.strip():
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "body mutation claim requires locator.durable",
            subtype="locator",
        )
    durable = durable.strip()
    resource_hash = hashlib.sha256(
        f"{provider}\0{durable}".encode("utf-8")).hexdigest()
    rec_path = flow_dir / "create-first" / f"body-{resource_hash}.json"
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
                        f"{provider} body mutation for issue "
                        f"{(display or durable)!r} is already in flight; retry "
                        "after it finishes",
                        subtype="body_mutation_in_flight",
                        details={
                            "specId": spec_id,
                            "resource": {
                                "provider": provider,
                                "durable": durable,
                                "display": display,
                            },
                            "claim": {
                                "operation": prior.get("operation"),
                                "pid": prior.get("pid"),
                                "host": prior.get("host"),
                                "claimedAt": prior.get("claimedAt"),
                            },
                        },
                        auto_retryable=True,
                    )
            claim = {
                "specId": spec_id,
                "status": "pending",
                "op": "body-mutation",
                "operation": operation,
                "resource": {
                    "provider": provider,
                    "durable": durable,
                    "display": display,
                },
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "claimedAt": time.time(),
                "transport": provider,
            }
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc),
                            subtype="lock_timeout")
    return rec_path


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


def _create_first_transaction(flow_dir, *, title: str, body: str,
                              retry_key: str,
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
                    out = {"id": prior["id"],
                           "identifier": prior.get("identifier"),
                           "url": prior.get("url"), "retried": True}
                    if prior.get("degraded") is not None:
                        out["degraded"] = prior["degraded"]
                    return out
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
    if created.get("degraded") is not None:
        record["degraded"] = created["degraded"]
    err = atomic_write_json(rec_path, record)
    if err:
        # The issue exists but the claim is still pending - a bare failure
        # would leave retries refusing (create_in_flight) until the claim
        # goes stale, with the created identity lost. TrackerError is frozen:
        # rebuild with the completed-steps detail so the caller can link the
        # existing issue instead of waiting out the stale window.
        import dataclasses  # noqa: PLC0415
        details = {
            **(err.details or {}),
            "completed_steps": ["create"],
            "id": created["id"],
            "identifier": created["identifier"],
            "url": created.get("url"),
            "retryKey": retry_key,
        }
        if created.get("degraded") is not None:
            details["degraded"] = created["degraded"]
        return dataclasses.replace(err, details=details)
    out = {"id": created["id"], "identifier": created["identifier"],
           "url": created.get("url"), "retried": False}
    if created.get("degraded") is not None:
        out["degraded"] = created["degraded"]
    return out


def create_first(flow_dir, *, title: str, body: str, retry_key: str,
                 execute: Execute = default_execute) -> Result:
    """Create-first with cleanup only when an exception aborts finalization."""
    flow_dir = Path(flow_dir)
    rec_path = flow_dir / "create-first" / f"{retry_key}.json"
    completed = False
    try:
        result = _create_first_transaction(
            flow_dir, title=title, body=body, retry_key=retry_key,
            execute=execute)
        completed = True
        return result
    finally:
        # A normal success replaces the pending claim with the durable retry
        # record and must retain it. Normal error paths release themselves.
        # Only an unexpected raise needs this final escape-hatch cleanup.
        if not completed:
            _release_claim(rec_path)


def persist_external(flow_dir, spec_id: str, *, identifier: str,
                     durable_id: Optional[str] = None, url: Optional[str] = None,
                     source: str,
                     execute: Execute = default_execute,
                     event: Optional[str] = None) -> Result:
    """Record an MCP create while holding the spec identity through receipt."""
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
    rec_path = flow_dir / "create-first" / f"spec-{spec_id}.json"
    claimed = _claim_spec_operation(
        flow_dir, spec_id, rec_path, "linear",
        operation="persist-external", require_unlinked=False)
    if claimed is not None:
        return claimed
    try:
        return _persist_external_claimed(
            flow_dir, spec_id, identifier=identifier,
            durable_id=durable_id, url=url, execute=execute, event=event)
    finally:
        _release_claim(rec_path)


def _persist_external_claimed(flow_dir: Path, spec_id: str, *,
                              identifier: str,
                              durable_id: Optional[str],
                              url: Optional[str],
                              execute: Execute,
                              event: Optional[str]) -> Result:
    """Claimed persist transaction; caller owns the spec claim."""
    config = read_config(flow_dir)
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
        rerr = write_sync_receipt(
            flow_dir, spec_id=spec_id, status="pushed",
            tracker_id=tracker.get("id"), event=event, transport="mcp",
        )
        if rerr:
            return rerr
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
                or (t.get("id") is not None
                    and str(t.get("id")) != str(owned.get("id")))):
            return TrackerError(
                ErrorClass.CONFLICT,
                f"spec {spec_id!r} became {state} to "
                f"{t.get('identifier')!r} while persist-external was in "
                "flight; refusing to overwrite the existing link",
                subtype="already_linked",
                details={"linkState": state,
                         "identifier": t.get("identifier"),
                         "id": t.get("id")})
        return {**t, **owned}

    persisted = _locked_tracker_write(
        flow_dir, spec_id, _persist, collision_id=resolved_id)
    if isinstance(persisted, TrackerError):
        return persisted

    # Degradation context lives EXCLUSIVELY in the structured `degraded`
    # field (epic contract: never a sentence in `note`).
    status = "pushed" if degraded is None else "updated"
    err = write_sync_receipt(
        flow_dir, spec_id=spec_id, status=status,
        tracker_id=resolved_id, event=event, transport="mcp",
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
