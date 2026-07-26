"""The single result envelope every `flowctl tracker` command emits (fn-139.2).

One JSON object on **stdout**; human-readable notes go to **stderr**. Callers
therefore parse without branching, and `--json` is accepted-and-ignored rather
than switching the shape.

`degraded` means a real capability transition. A failed TTL re-probe is NOT a
degradation - it reports through `probe`, because conflating "we could not
check" with "the capability changed" is how a transient 403 becomes a permanent
silent downgrade.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

from .credentials import redact
from .types import EXIT_CODES, ErrorClass, TrackerError


def success(data: Any, *, degraded: Optional[dict] = None,
            probe: Optional[dict] = None) -> tuple[str, int]:
    return json.dumps({
        "success": True, "data": data,
        "degraded": degraded, "probe": probe,
    }, sort_keys=True), 0


def _scrub(obj: Any) -> Any:
    """Redact every string reachable in an outbound payload, at any depth.

    Redacting only `err.message` was a hole with a concrete exploit: a provider
    echoes the credential back, the classifier files it under
    `conflict.candidates` or a capability payload, and `details` serialized it
    verbatim. The keys that carry provider text are exactly the ones a caller is
    meant to act on, so they cannot be excluded.
    """
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        # Keys too: a provider that echoes the token back as a mapping KEY
        # (e.g. a per-credential error index) would otherwise leak it.
        return {_scrub(k): _scrub(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(v) for v in obj]
    return obj


def _details_for(err: TrackerError) -> Optional[dict]:
    """Typed variant keyed by class - NOT free-form.

    A caller that must act on a failure needs the actionable field in a known
    place: how long to wait, which capability is missing, which candidates an
    ambiguity is between. Emitting `err.details` verbatim left `rate_limited`
    with a null payload because `retry_after_s` lives on its own attribute.
    """
    base = dict(err.details or {})
    if err.cls is ErrorClass.RATE_LIMITED:
        return {"retry_after_s": err.retry_after_s, **base}
    if err.cls is ErrorClass.CAPABILITY:
        return {"capability": base.get("capability"),
                "required_plan": base.get("required_plan"), **base}
    if err.cls is ErrorClass.CONFLICT:
        return {"normalized": base.get("normalized"),
                "candidates": base.get("candidates", []), **base}
    if err.cls is ErrorClass.EXTERNAL_ACTION_REQUIRED:
        return {"action": base.get("action"), "payload": base.get("payload"), **base}
    return base or None


def failure(err: TrackerError, *, retryable: Optional[bool] = None) -> tuple[str, int]:
    payload = {
        "success": False,
        "class": err.cls.value,
        # Last line of defence: provider error text is untrusted and has been
        # observed to echo credentials back. Redacting only at the classifier
        # would leave any other TrackerError source unprotected.
        "error": redact(err.message),
        # Distinct from `auto_retryable`, which governs the executor's internal
        # retry. This answers a different question: would re-invoking help?
        "retryable": bool(err.auto_retryable if retryable is None else retryable),
        "details": _scrub(_details_for(err)),
    }
    return json.dumps(payload, sort_keys=True), EXIT_CODES[err.cls]


def emit(payload_and_code: tuple[str, int], *, note: Optional[str] = None) -> int:
    if note:
        # stderr is not a safe channel for an unredacted note: it is captured in
        # CI logs and Ralph receipts exactly like stdout.
        print(redact(note), file=sys.stderr)
    payload, code = payload_and_code
    print(payload)
    return code


def inactive() -> tuple[str, int]:
    """Bridge off: a no-op, not an error the caller must handle."""
    return failure(TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive"))
