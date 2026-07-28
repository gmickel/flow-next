"""Shared helpers for the lifecycle facade (fn-140.7)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from ..lifecycle.helpers import (Execute, Result, dict_, load_spec,
                                 merged_tracker, tracker_type,
                                 write_sync_receipt)
from ..lifecycle.linkstate import derive_link_state
from ..types import ErrorClass, TrackerError

OPS = frozenset({"push", "pull", "reconcile", "comment"})

# required / forbidden input names (flow_file / body_file) per op — epic table.
OP_INPUTS = {
    "push": {"require": frozenset({"flow_file"}), "forbid": frozenset({"body_file"})},
    "pull": {"require": frozenset(), "forbid": frozenset({"flow_file"})},
    "reconcile": {"require": frozenset({"flow_file", "body_file"}), "forbid": frozenset()},
    "comment": {"require": frozenset({"body_file"}), "forbid": frozenset({"flow_file"})},
}

# Aggregate receipt status severity — higher = worse.
_STATUS_RANK = {
    "errored": 100,
    "diverged": 90,
    "deferred": 80,
    "queued": 70,
    "updated": 50,
    "merged": 45,
    "pushed": 40,
    "pulled": 40,
    "noop": 10,
}

_MARKER_RE = re.compile(
    r"<!--\s*flow-next:sync\s+"
    r"issue=(?P<issue>\S+)\s+"
    r"spec=(?P<spec>\S+)\s+"
    r"evt=(?P<evt>\S+)\s+"
    r"evidence=(?P<evidence>\S+)\s*-->"
)

# Strip Linear/GitHub mention markup before marker parse (comments-sync.md).
_MENTION_RE = re.compile(r"<issue[^>]*>|</issue>")

# One marker field: exactly what _MARKER_RE's field classes accept (\S+).
_MARKER_FIELD_RE = re.compile(r"\S+")


def marker_component_error(name: str, value: Any) -> Optional[TrackerError]:
    """Reject marker components the emitted marker cannot round-trip through
    _MARKER_RE. Marker fields are single whitespace-free tokens; a value with
    embedded whitespace posts fine the first time, but every retry fails
    comments_have_marker() and posts another copy - the idempotency guarantee
    breaks silently. Reject rather than encode: the marker is a dedup
    identity, and encoding would change the identity of markers already
    posted by earlier flow-next versions."""
    if isinstance(value, str) and _MARKER_FIELD_RE.fullmatch(value):
        return None
    return TrackerError(
        ErrorClass.INVALID_INPUT,
        f"{name} {value!r} cannot round-trip the sync dedup marker: marker "
        "fields must be a single whitespace-free token (no spaces, tabs, or "
        "newlines); pass one token, e.g. a sha or dotted event name",
        subtype=name,
        details={"field": name, "value": value},
    )


def validate_inputs(op: str, *, flow_file: Optional[str],
                    body_file: Optional[str], event: Optional[str]
                    ) -> Optional[TrackerError]:
    if op not in OPS:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"--op must be one of {sorted(OPS)}, got {op!r}",
                            subtype="op")
    if not event or not str(event).strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "--event is required", subtype="event")
    # The event is a marker field (and a receipt/claim key): reject values
    # the emitted marker could not round-trip BEFORE any wire call.
    bad_event = marker_component_error("event", str(event))
    if bad_event:
        return bad_event
    rules = OP_INPUTS[op]
    present = {
        "flow_file": flow_file is not None,
        "body_file": body_file is not None,
    }
    for name in rules["forbid"]:
        if present[name]:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"--op {op} forbids --{name.replace('_', '-')}",
                subtype="args",
            )
    for name in rules["require"]:
        if not present[name]:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"--op {op} requires --{name.replace('_', '-')}",
                subtype="args",
            )
    return None


def read_text_file(path: Optional[str], *, label: str) -> Result:
    if path is None:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"{label} is required", subtype="args")
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"cannot read {label}: {exc}", subtype=label)


def local_spec_md(flow_dir: Path, spec_id: str) -> Result:
    """Read `.flow/specs/<id>.md` (flow half for pull). Never composes content."""
    path = Path(flow_dir) / "specs" / f"{spec_id}.md"
    if not path.is_file():
        return TrackerError(ErrorClass.NOT_FOUND,
                            f"spec markdown {spec_id!r} not found at {path}",
                            subtype="spec_md")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT,
                            f"cannot read spec markdown: {exc}",
                            subtype="spec_md")


def on_mcp_rung(config: dict) -> bool:
    """Linear MCP create rung: flowctl cannot create; agent must via persist-external.

    Prefer an explicit perTracker transport preference when present; else
    detect as linear + no LINEAR_API_KEY (no shell-reachable GraphQL).
    """
    if tracker_type(config) != "linear":
        return False
    per = dict_(dict_(config.get("tracker")).get("perTracker"))
    preferred = per.get("preferredTransport") or per.get("transport")
    if isinstance(preferred, str):
        low = preferred.strip().lower()
        if low == "mcp":
            return True
        if low in ("graphql", "http", "api", "linear-graphql"):
            return False
    return not bool(os.environ.get("LINEAR_API_KEY", "").strip())


def locator_of(tracker: dict) -> Result:
    durable = tracker.get("id")
    display = tracker.get("identifier")
    if not isinstance(durable, str) or not durable.strip():
        return TrackerError(ErrorClass.UNRESOLVED, "tracker.id missing",
                            subtype="durable")
    if not isinstance(display, str) or not display.strip():
        return TrackerError(ErrorClass.INVALID_INPUT,
                            "tracker.identifier (display) required",
                            subtype="locator")
    return {"durable": durable.strip(), "display": display.strip()}


def load_tracker(flow_dir: Path, spec_id: str) -> Result:
    loaded = load_spec(flow_dir, spec_id)
    if isinstance(loaded, TrackerError):
        return loaded
    path, spec_data = loaded
    tracker = merged_tracker(spec_data)
    return path, spec_data, tracker


def format_marker(*, issue: str, spec_id: str, event: str,
                  evidence: str = "none") -> str:
    return (f"<!-- flow-next:sync issue={issue} spec={spec_id} "
            f"evt={event} evidence={evidence} -->")


def normalize_comment_body(body: str) -> str:
    return _MENTION_RE.sub("", body or "")


def marker_match(body: str, *, issue: str, spec: str, event: str,
                 evidence: str) -> bool:
    """Match on the FULL marker identity: issue + spec + event + evidence.
    Two specs may intentionally share one issue (`sync set-tracker-id
    --force`); ignoring the captured spec field would treat spec A's marker
    as spec B's and silently drop B's comment as a false dedup. Markers have
    carried spec= since the wave-1 shape, so matching on it does not orphan
    markers already posted."""
    text = normalize_comment_body(body)
    m = _MARKER_RE.search(text)
    if not m:
        return False
    return (m.group("issue") == issue
            and m.group("spec") == spec
            and m.group("evt") == event
            and m.group("evidence") == evidence)


def comments_have_marker(comments: list, *, issue: str, spec: str,
                         event: str, evidence: str) -> bool:
    for c in comments:
        if not isinstance(c, dict):
            continue
        if marker_match(c.get("body") or "", issue=issue, spec=spec,
                        event=event, evidence=evidence):
            return True
    return False


def parse_evidence(body: str) -> str:
    """Optional leading `evidence=<sha>` line; else `none`."""
    if not body:
        return "none"
    first = body.splitlines()[0].strip() if body.splitlines() else ""
    if first.lower().startswith("evidence="):
        val = first.split("=", 1)[1].strip()
        return val or "none"
    return "none"


def strip_evidence_line(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].strip().lower().startswith("evidence="):
        return "\n".join(lines[1:]).lstrip("\n")
    return body


def worst_status(statuses: list[str]) -> str:
    if not statuses:
        return "noop"
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, 0))


def step_status_from_sync_body(out: dict) -> str:
    kind = out.get("kind")
    if kind == "pulled":
        return "pulled"
    if kind == "noop":
        return "noop"
    return "pushed"


def step_status_from_status(out: dict) -> str:
    kind = out.get("kind")
    if kind == "defer":
        return "deferred"
    if kind == "noop":
        return "noop"
    if kind == "applied_local":
        return "pulled"
    if kind == "applied":
        return "updated"
    return "updated"


def write_aggregate_receipt(flow_dir: Path, *, spec_id: str, event: str,
                            status: str, tracker_id: Optional[str],
                            transport: Optional[str],
                            degraded: Optional[dict] = None,
                            note: Optional[str] = None,
                            details: Optional[dict] = None
                            ) -> Optional[TrackerError]:
    return write_sync_receipt(
        flow_dir, spec_id=spec_id, status=status,
        tracker_id=tracker_id, event=event, transport=transport,
        note=note, degraded=degraded, details=details,
    )


def completion_review_configured(config: dict) -> bool:
    review = dict_(config.get("review")).get("backend")
    if review is None:
        return False
    if isinstance(review, str) and review.strip().lower() in ("", "none", "off"):
        return False
    return True


def load_tasks(flow_dir: Path, spec_id: str) -> list:
    tasks_dir = Path(flow_dir) / "tasks"
    if not tasks_dir.is_dir():
        return []
    out = []
    for path in sorted(tasks_dir.glob(f"{spec_id}.*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            out.append({"id": data.get("id"), "status": data.get("status") or "todo"})
    return out


def compute_status_to(flow_dir: Path, spec_id: str, config: dict,
                      spec_data: dict, execute: Execute) -> str:
    from ..status.policy import flow_to_normalized, merge_evidence  # noqa: PLC0415
    pr = merge_evidence(config, spec_data, execute)
    return flow_to_normalized(
        spec_data, pr, completion_review_configured(config),
        tasks=load_tasks(flow_dir, spec_id),
    )


def link_state_of(tracker: dict) -> str:
    return derive_link_state(tracker)


def collect_degraded(*parts: Any) -> Optional[dict]:
    """First structured degradation across step results - including the
    NESTED write payload: the status verb reports label degradation under
    result["write"]["degraded"], which the top-level check silently lost."""
    for p in parts:
        if not isinstance(p, dict):
            continue
        if p.get("degraded"):
            return p["degraded"]
        write = p.get("write")
        if isinstance(write, dict) and write.get("degraded"):
            return write["degraded"]
    return None
