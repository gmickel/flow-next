"""Parse Claude stream-json / tool traces for successful Read activations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def parse_stream_json_reads(stream_text: str) -> list[dict[str, Any]]:
    """Extract Read tool_use inputs from a stream-json transcript.

    Only successful tool_use records are returned; tool_result errors are
    tracked separately via ``parse_stream_json_failed_reads``. Repeated Read
    of the same path appear multiple times here — the character algorithm
    dedupes by path+hash when counting.
    """
    reads: list[dict[str, Any]] = []
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
            inp = tool.get("input") or {}
            path = inp.get("file_path") or inp.get("path")
            if not path:
                continue
            reads.append(
                {
                    "path": path,
                    "offset": inp.get("offset"),
                    "limit": inp.get("limit"),
                    "tool_use_id": tool.get("id"),
                }
            )
    return reads


def parse_stream_json_failed_reads(stream_text: str) -> list[dict[str, Any]]:
    """Best-effort failed Read detection from tool_result is_error flags."""
    # Map tool_use_id -> path from Read tool_use events.
    id_to_path: dict[str, str] = {}
    for line in (stream_text or "").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        for tool in _iter_tool_use(obj):
            if tool.get("name") == "Read" and tool.get("id"):
                inp = tool.get("input") or {}
                id_to_path[tool["id"]] = inp.get("file_path") or inp.get("path") or ""
    failed: list[dict[str, Any]] = []
    for line in (stream_text or "").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        for tr in _iter_tool_result(obj):
            if not tr.get("is_error"):
                continue
            tid = tr.get("tool_use_id")
            path = id_to_path.get(tid or "", "")
            if path:
                failed.append({"path": path, "tool_use_id": tid})
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
    failed: list[dict[str, Any]],
) -> list[str]:
    """Paths of successful Read activations (failed excluded)."""
    failed_paths = {f["path"] for f in failed}
    out: list[str] = []
    seen: set[str] = set()
    for r in reads:
        p = r["path"]
        if p in failed_paths:
            continue
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
