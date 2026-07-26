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

from .types import EXIT_CODES, ErrorClass, TrackerError


def success(data: Any, *, degraded: Optional[dict] = None,
            probe: Optional[dict] = None) -> tuple[str, int]:
    return json.dumps({
        "success": True, "data": data,
        "degraded": degraded, "probe": probe,
    }, sort_keys=True), 0


def failure(err: TrackerError, *, retryable: Optional[bool] = None) -> tuple[str, int]:
    payload = {
        "success": False,
        "class": err.cls.value,
        "error": err.message,
        # Distinct from `auto_retryable`, which governs the executor's internal
        # retry. This answers a different question: would re-invoking help?
        "retryable": bool(err.auto_retryable if retryable is None else retryable),
        "details": err.details,
    }
    return json.dumps(payload, sort_keys=True), EXIT_CODES[err.cls]


def emit(payload_and_code: tuple[str, int], *, note: Optional[str] = None) -> int:
    if note:
        print(note, file=sys.stderr)
    payload, code = payload_and_code
    print(payload)
    return code


def inactive() -> tuple[str, int]:
    """Bridge off: a no-op, not an error the caller must handle."""
    return failure(TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive"))
