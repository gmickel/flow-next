"""create / create-first / persist-external verbs (fn-140.2)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from ..executor import execute as default_execute
from ..types import ErrorClass, TrackerError
from .helpers import (CREATE_FIRST_KEY_RE, Execute, Result, atomic_write_json,
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
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)

    resolved_id = (durable_id.strip()
                   if isinstance(durable_id, str) and durable_id.strip() else None)
    resolved_url = url
    warning = False
    if resolved_id is None:
        resolved = resolve_linear_uuid(ex, identifier)
        if isinstance(resolved, TrackerError):
            warning = True
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
    if warning:
        note = (f"WARNING: identifier_only; GraphQL unreachable for "
                f"identifier={identifier} url={resolved_url}")
        status = "updated"
    err = write_sync_receipt(
        flow_dir, spec_id=spec_id, status=status,
        tracker_id=resolved_id, event=event, transport="mcp", note=note,
    )
    if err:
        return err
    return {"id": tracker.get("id"), "identifier": tracker.get("identifier"),
            "url": tracker.get("url"), "linkState": tracker["linkState"]}
