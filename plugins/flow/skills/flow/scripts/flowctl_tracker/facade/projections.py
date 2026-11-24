"""Deterministic pull-side projections shared by wire and status."""

from __future__ import annotations

from typing import Any

from ..lifecycle.helpers import dict_
from ..types import ErrorClass, TrackerError


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _ready_state(config: dict) -> str | None:
    value = dict_(config.get("tracker")).get("readyState")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _status_name(provider: str, issue: dict) -> str | None:
    raw = issue.get("raw") if isinstance(issue.get("raw"), dict) else {}
    if provider == "linear":
        state = raw.get("state") if isinstance(raw.get("state"), dict) else {}
        value = state.get("name")
    elif provider == "jira":
        fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
        status = fields.get("status") if isinstance(fields.get("status"), dict) else {}
        value = status.get("name")
    else:
        value = None
    return str(value) if value is not None else None


def _desired(provider: str, issue: dict, ready_state: str
             ) -> bool | TrackerError:
    if provider in {"github", "gitlab"}:
        labels = issue.get("labels")
        if not isinstance(labels, list):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "normalized issue labels are malformed; readiness untouched",
                subtype="readiness_shape",
            )
        return _norm(ready_state) in {_norm(label) for label in labels}
    status_name = _status_name(provider, issue)
    if status_name is None:
        return TrackerError(
            ErrorClass.TRANSPORT,
            "normalized issue status is missing; readiness untouched",
            subtype="readiness_shape",
        )
    return _norm(status_name) == _norm(ready_state)
