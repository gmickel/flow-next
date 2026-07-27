"""create / create-first / persist-external verbs (fn-140.2)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from ..executor import execute as default_execute
from ..types import ErrorClass, TrackerError
from .helpers import (CREATE_FIRST_KEY_RE, Execute, Result, atomic_write_json,
                      leaf_is_safe,
                      collision, default_tracker, dict_, load_spec, now_iso,
                      read_config, tracker_type, write_sync_receipt,
                      write_tracker_block)
from .linkstate import derive_link_state, resolve_linear_uuid
from .providers import provider_create


def create(flow_dir, spec_id: str, *, title: str, body: str,
           event: Optional[str] = None,
           execute: Execute = default_execute) -> Result:
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
    tracker = {**default_tracker(), **dict_(spec_data.get("tracker"))}
    if derive_link_state(tracker) != "unlinked":
        return TrackerError(
            ErrorClass.CONFLICT,
            f"spec {spec_id!r} is already linked "
            f"(linkState={derive_link_state(tracker)!r}); refuse bare create",
            subtype="already_linked",
        )
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    created = provider_create(config, ex, title=title, body=body)
    if isinstance(created, TrackerError):
        return created
    hit = collision(flow_dir, created["id"], except_spec=spec_id)
    if hit:
        return hit
    tracker.update({
        "id": created["id"],
        "identifier": created["identifier"],
        "url": created.get("url"),
        "linkState": "linked",
        "lastSyncedAt": now_iso(),
    })
    err = write_tracker_block(path, spec_data, tracker)
    if err:
        return err
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
    if rec_path.is_file():
        try:
            prior = json.loads(rec_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prior = None
        if isinstance(prior, dict) and prior.get("id"):
            return {"id": prior["id"], "identifier": prior.get("identifier"),
                    "url": prior.get("url"), "retried": True}
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    created = provider_create(config, ex, title=title, body=body)
    if isinstance(created, TrackerError):
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
        return err
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
    tracker = {**default_tracker(), **dict_(spec_data.get("tracker"))}

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

    if resolved_id is not None:
        hit = collision(flow_dir, resolved_id, except_spec=spec_id)
        if hit:
            return hit

    err = write_tracker_block(path, spec_data, tracker)
    if err:
        return err

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
        return err
    return {"id": tracker.get("id"), "identifier": tracker.get("identifier"),
            "url": tracker.get("url"), "linkState": tracker["linkState"],
            "degraded": degraded}
