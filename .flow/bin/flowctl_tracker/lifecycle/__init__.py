"""Spec-aware create / create-first / persist-external verbs (fn-140.2).

Wire verbs touch no local state. These three do: they write the spec-json
tracker block and (except create-first) an event-tagged sync receipt under
`.flow/sync-runs/`. create-first is the fn-134 exception — no spec yet, so
recovery lives at `.flow/create-first/<key>.json` and there is no receipt.

`linkState` is the exhaustive enum that replaces today's ambiguous
`tracker.id: null` (= unlinked). Legacy records without the field migrate on
read via `derive_link_state`. Commands that need a durable id call
`require_durable`; the .7 facade's `--op reconcile` calls
`complete_identifier_only` — there is no separate `tracker reconcile` verb.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .. import envelope
from ..executor import execute as default_execute
from ..types import ErrorClass, TrackerError
from .helpers import ACTIVE, Execute, dict_, read_config, tracker_type
from .linkstate import (complete_identifier_only, derive_link_state,
                        require_durable)
from .verbs import (compute_create_first_key, create, create_first,
                    persist_external)

__all__ = [
    "complete_identifier_only",
    "compute_create_first_key",
    "create",
    "create_first",
    "derive_link_state",
    "persist_external",
    "require_durable",
    "run",
]


def run(flow_dir, verb: str, *, spec_id: Optional[str] = None,
        title: Optional[str] = None, body_file: Optional[str] = None,
        event: Optional[str] = None, retry_key: Optional[str] = None,
        identifier: Optional[str] = None, durable_id: Optional[str] = None,
        url: Optional[str] = None, source: Optional[str] = None,
        execute: Execute = default_execute) -> tuple[str, int]:
    """Thin envelope shell — never raises across the boundary."""
    config = read_config(flow_dir)
    if tracker_type(config) is None:
        t = dict_(config.get("tracker")).get("type")
        if t is not None and t not in ACTIVE:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown tracker type {t!r}",
                subtype="provider"))
        return envelope.inactive()

    body = None
    if body_file is not None:
        try:
            body = Path(body_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"cannot read --body-file: {exc}",
                subtype="body_file"))

    try:
        if verb == "create":
            if not spec_id or title is None or body is None:
                return envelope.failure(TrackerError(
                    ErrorClass.INVALID_INPUT,
                    "create requires <spec-id> --title --body-file",
                    subtype="args"))
            out = create(flow_dir, spec_id, title=title, body=body,
                         event=event, execute=execute)
        elif verb == "create-first":
            if title is None or body is None or not retry_key:
                return envelope.failure(TrackerError(
                    ErrorClass.INVALID_INPUT,
                    "create-first requires --title --body-file --retry-key",
                    subtype="args"))
            out = create_first(flow_dir, title=title, body=body,
                               retry_key=retry_key, execute=execute)
        elif verb == "persist-external":
            if not spec_id or not identifier or not source:
                return envelope.failure(TrackerError(
                    ErrorClass.INVALID_INPUT,
                    "persist-external requires <spec-id> --identifier --source",
                    subtype="args"))
            out = persist_external(
                flow_dir, spec_id, identifier=identifier,
                durable_id=durable_id, url=url, source=source,
                execute=execute, event=event)
        else:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"unknown lifecycle verb {verb!r}",
                subtype="verb"))
    except Exception as exc:  # noqa: BLE001 - boundary must never raise
        return envelope.failure(TrackerError(
            ErrorClass.TRANSPORT, f"lifecycle verb raised: {exc}",
            subtype="unexpected"))

    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
