"""Spec-aware `tracker status` verb (fn-140.3).

Thin envelope shell over `status.verb`. Embeds fn-66's merge-evidence gate
and the who-wins ladder (deadlock first). Never raises across the boundary.
"""

from __future__ import annotations

from typing import Optional

from .. import envelope
from ..executor import execute as default_execute
from ..lifecycle.helpers import ACTIVE, Execute, dict_, read_config, tracker_type
from ..types import ErrorClass, TrackerError
from .policy import (Decision, decide, flow_to_normalized, is_deadlock,
                     merge_evidence, terminal_wins_matches,
                     in_progress_wins_matches, validate_to_reason)
from .verb import status

__all__ = [
    "Decision",
    "decide",
    "flow_to_normalized",
    "in_progress_wins_matches",
    "is_deadlock",
    "merge_evidence",
    "run",
    "status",
    "terminal_wins_matches",
    "validate_to_reason",
]


def run(flow_dir, *, spec_id: Optional[str] = None, to: Optional[str] = None,
        reason: Optional[str] = None, event: Optional[str] = None,
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

    if not spec_id or not to:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT,
            "status requires <spec-id> --to <slot>",
            subtype="args"))

    try:
        out = status(flow_dir, spec_id, to=to, reason=reason, event=event,
                     execute=execute)
    except Exception as exc:  # noqa: BLE001 - boundary must never raise
        return envelope.failure(TrackerError(
            ErrorClass.TRANSPORT, f"status verb raised: {exc}",
            subtype="unexpected"))

    if isinstance(out, TrackerError):
        if out.cls is ErrorClass.INACTIVE:
            return envelope.inactive()
        return envelope.failure(out)
    return envelope.success(out)
