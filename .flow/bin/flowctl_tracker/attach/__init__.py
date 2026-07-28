"""Wire attach / attach-get (fn-140.4).

Capability-gated uploads with byte-identical retrieval. attach takes a locator;
attach-get is context-free (attachment id only). Never raises across the boundary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import ACTIVE, Execute, dict_, read_config, tracker_type
from ..types import ErrorClass, TrackerError
from . import providers

Result = Union[dict, TrackerError]


def _caps(config: dict) -> dict:
    caps = dict_(dict_(dict_(config.get("tracker")).get("resolved")).get("capabilities"))
    if caps:
        return caps
    from ..resolved_cache import STATIC_CAPABILITIES  # noqa: PLC0415
    t = tracker_type(config)
    return dict(STATIC_CAPABILITIES.get(t) or {})


def attach(config: dict, locator: Any, *, file_path: str,
           execute: Execute) -> Result:
    """Upload a file to the locator's issue. Returns {id, url, size, sha256}."""
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    caps = _caps(config)
    if caps.get("attachments") is False:
        return TrackerError(
            ErrorClass.CAPABILITY,
            "attachments are not available on this tracker; GitHub has no "
            "attachment API (POST /issues/:n/uploads returns 404). Workaround: "
            "commit the file and link it (private-repo URLs carry expiring tokens)",
            subtype="attachments",
            details={"capability": "attachments",
                     "workaround": "commit-and-link"},
        )
    from ..wire import parse_locator  # noqa: PLC0415
    parsed = parse_locator(locator)
    if isinstance(parsed, TrackerError):
        return parsed
    path = Path(file_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"cannot read --file: {exc}", subtype="file")
    mod = providers.PROVIDERS.get(provider)
    if mod is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    return mod.upload(config, parsed, execute, path=path, data=raw)


def attach_get(config: dict, *, attachment_id: str, out_path: str,
               execute: Execute) -> Result:
    """Retrieve bytes by attachment id (no locator). Writes --out; returns sha256."""
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    caps = _caps(config)
    if caps.get("attachments") is False:
        return TrackerError(
            ErrorClass.CAPABILITY,
            "attachments are not available on this tracker",
            subtype="attachments",
            details={"capability": "attachments"},
        )
    if not attachment_id or not str(attachment_id).strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "attach-get requires <attachment-id>",
                            subtype="attachment_id")
    if not out_path:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "attach-get requires --out", subtype="out")
    mod = providers.PROVIDERS.get(provider)
    if mod is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    return mod.download(config, execute, attachment_id=str(attachment_id).strip(),
                        out_path=out_path)


def run(flow_dir, verb: str, *, locator: Any = None, file_path: Optional[str] = None,
        attachment_id: Optional[str] = None, out_path: Optional[str] = None,
        execute: Execute = default_execute) -> tuple[str, int]:
    """CLI entry for wire attach / attach-get."""
    config = read_config(flow_dir)
    if tracker_type(config) is None:
        t = dict_(config.get("tracker")).get("type")
        if t is not None and t not in ACTIVE:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown tracker type {t!r}",
                subtype="provider"))
        return envelope.inactive()
    from ..resolve_verb import bound_executor  # noqa: PLC0415
    ex = bound_executor(config, execute)
    try:
        if verb == "attach":
            if not file_path:
                return envelope.failure(TrackerError(
                    ErrorClass.INVALID_INPUT, "attach requires --file",
                    subtype="file"))
            out = attach(config, locator, file_path=file_path, execute=ex)
        elif verb == "attach-get":
            out = attach_get(config, attachment_id=attachment_id or "",
                             out_path=out_path or "", execute=ex)
        else:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown attach verb {verb!r}",
                subtype="verb"))
    except Exception as exc:  # noqa: BLE001 - boundary must never raise
        return envelope.failure(TrackerError(
            ErrorClass.TRANSPORT, f"attach verb raised: {exc}",
            subtype="unexpected"))
    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
