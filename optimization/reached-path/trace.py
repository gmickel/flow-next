"""Parse Claude stream-json / tool traces for successful Read activations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def _collect_read_uses_and_results(
    stream_text: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Index Read tool_use and tool_result records by tool_use_id."""
    uses: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for line in (stream_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        for tool in _iter_tool_use(obj):
            if tool.get("name") != "Read":
                continue
            tid = tool.get("id")
            if not tid:
                continue
            inp = tool.get("input") or {}
            path = inp.get("file_path") or inp.get("path")
            if not path:
                continue
            uses[tid] = {
                "path": path,
                "offset": inp.get("offset"),
                "limit": inp.get("limit"),
                "tool_use_id": tid,
            }
        for tr in _iter_tool_result(obj):
            tid = tr.get("tool_use_id")
            if not tid:
                continue
            # Last result for an id wins (stream may repeat); keep is_error.
            results[tid] = {
                "tool_use_id": tid,
                "is_error": bool(tr.get("is_error")),
            }
    return uses, results


def parse_stream_json_reads(stream_text: str) -> list[dict[str, Any]]:
    """Extract successfully completed Read activations from a stream-json transcript.

    A Read is successful only when a matching ``tool_result`` exists for its
    ``tool_use_id`` and that result is not an error. Unpaired ``tool_use``
    (truncated/interrupted streams) and ``is_error`` results are excluded.
    Repeated successful Reads of the same path appear multiple times here —
    the character algorithm dedupes by path+hash when counting.
    """
    uses, results = _collect_read_uses_and_results(stream_text)
    reads: list[dict[str, Any]] = []
    # Preserve first-seen tool_use order from the stream index insertion order.
    for tid, use in uses.items():
        result = results.get(tid)
        if result is None:
            continue
        if result.get("is_error"):
            continue
        reads.append(dict(use))
    return reads


def parse_stream_json_failed_reads(stream_text: str) -> list[dict[str, Any]]:
    """Failed Read detections: matching tool_result with ``is_error`` true.

    Unpaired Read ``tool_use`` records are neither successful nor failed —
    they inflate neither activation metrics nor the failed-read list.
    """
    uses, results = _collect_read_uses_and_results(stream_text)
    failed: list[dict[str, Any]] = []
    for tid, result in results.items():
        if not result.get("is_error"):
            continue
        use = uses.get(tid)
        if not use:
            continue
        failed.append({"path": use["path"], "tool_use_id": tid})
    return failed


def parse_result_envelope(stream_text: str) -> Optional[dict[str, Any]]:
    """Return the final stream-json ``type=result`` object when present."""
    last = None
    for line in (stream_text or "").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            last = obj
    return last


def backend_telemetry(result_obj: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Extract backend token/cache/time telemetry as SEPARATE fields."""
    if not result_obj:
        return {
            "input_tokens": None,
            "output_tokens": None,
            "cache_creation_input_tokens": None,
            "cache_read_input_tokens": None,
            "duration_ms": None,
            "total_cost_usd": None,
            "model_usage": None,
            "note": "telemetry_absent",
        }
    usage = result_obj.get("usage") or {}
    return {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "duration_ms": result_obj.get("duration_ms"),
        "duration_api_ms": result_obj.get("duration_api_ms"),
        "total_cost_usd": result_obj.get("total_cost_usd"),
        "model_usage": result_obj.get("modelUsage"),
        "note": (
            "Backend cache counters are telemetry, not interchangeable with "
            "source bytes or billed input tokens."
        ),
    }


def successful_activations(
    reads: list[dict[str, Any]],
    failed: Optional[list[dict[str, Any]]] = None,
) -> list[str]:
    """Paths of successful Read activations (order-preserving, path-deduped).

    ``reads`` must already be success-filtered (see ``parse_stream_json_reads``).
    ``failed`` is accepted for call-site compatibility and is not used to drop
    paths — success is decided per ``tool_use_id``, not per path, so a later
    failed re-read of the same path does not erase an earlier success.
    """
    del failed  # API compat; success is per tool_use_id upstream.
    out: list[str] = []
    seen: set[str] = set()
    for r in reads:
        p = r["path"]
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _iter_tool_use(obj: dict) -> list[dict]:
    found: list[dict] = []
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                found.append(c)
    return found


def _iter_tool_result(obj: dict) -> list[dict]:
    found: list[dict] = []
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_result":
                found.append(c)
    return found


def rel_under(arena_skill: Path, abs_path: str) -> Optional[str]:
    """Return skill-relative posix path when abs_path is under arena_skill."""
    try:
        return Path(abs_path).resolve().relative_to(arena_skill.resolve()).as_posix()
    except ValueError:
        return None
