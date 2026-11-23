"""Transient claim for concurrency-safe stable tracker questions."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path
from typing import Optional

from .lifecycle.helpers import atomic_write_json, leaf_is_safe
from .lifecycle.verbs import (
    _claim_is_stale,
    _ensure_create_first_ignored,
    _release_claim,
)
from .types import ErrorClass, TrackerError


def question_claim_path(flow_dir: Path, *, provider: str,
                        durable: str, question_id: str) -> Path:
    """Return the stable claim path for one provider issue + question key."""
    payload = "\0".join([provider, durable, question_id])
    key = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return Path(flow_dir) / "create-first" / f"question-{key}.json"


def claim_question(flow_dir: Path, rec_path: Path, *, provider: str,
                   durable: str, question_id: str,
                   subject_id: str) -> Optional[TrackerError]:
    """Serialize question list -> optional add before any remote read."""
    unsafe = leaf_is_safe(flow_dir / "create-first", rec_path)
    if unsafe:
        return unsafe
    secured = _ensure_create_first_ignored(flow_dir)
    if secured is not None:
        return secured
    from .config_lock import ConfigLockTimeout, config_lock  # noqa: PLC0415
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
                        "this stable tracker question is already in flight; "
                        "retry after it finishes so the dedup scan sees the "
                        "winner's marker",
                        subtype="question_in_flight",
                        details={
                            "question_id": question_id,
                            "durable": durable,
                            "claim": {
                                "pid": prior.get("pid"),
                                "host": prior.get("host"),
                                "claimedAt": prior.get("claimedAt"),
                            },
                        },
                        auto_retryable=True,
                    )
            claim = {
                "status": "pending",
                "op": "question",
                "provider": provider,
                "durable": durable,
                "question_id": question_id,
                "subject_id": subject_id,
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "claimedAt": time.time(),
            }
            cerr = atomic_write_json(rec_path, claim)
            if cerr:
                return cerr
    except ConfigLockTimeout as exc:
        return TrackerError(
            ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")
    return None


def release_question_claim(rec_path: Path) -> None:
    """Release the transient claim; the remote marker is durable evidence."""
    _release_claim(rec_path)
