"""Chart lifecycle projection through the deterministic tracker facade (fn-135.5).

Local chart state is always canonical. When tracker.charts is on and the bridge
is active, each committed local revision projects parent/child issues, type/
attendance/status/safe evidence, native blocking (where supported), and a
compact parent rollup. Partial/failed/reordered remote work persists completed
steps + one aggregate receipt + revision so retry/reconcile converges without
duplicates and never rolls back local chart state.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from ..executor import execute as default_execute
from ..lifecycle.helpers import (Execute, Result, atomic_write_json, dict_,
                                 now_iso, read_config, tracker_type)
from ..lifecycle.providers import provider_create
from ..relate.ledger import (dep_relation_key, ledger_append, ledger_drop,
                             ledger_finalize, ledger_has)
from ..subjects import (caps_of, chart_projection_lock, load_subject,
                        locked_subject_write, parse_decision_id,
                        projection_gate, subject_collision,
                        subject_marker_token)
from ..types import ErrorClass, TrackerError
from .helpers import (collect_degraded, locator_of,
                      write_aggregate_receipt)
from .steps import fail_result, ok_result

# Lifecycle events projected from chart transitions (receipt event tokens).
CHART_EVENTS = frozenset({
    "chart.create",
    "chart.wire",
    "chart.claim",
    "chart.release",
    "chart.resolve",
    "chart.supersede",
    "chart.outOfScope",
    "chart.attachAsset",
    "chart.briefing",
    "chart.abandon",
    "chart.reopen",
    "chart.staleLink",
})

CHART_ROLLUP_OPEN = "<!-- flow-next:chart-rollup -->"
CHART_ROLLUP_CLOSE = "<!-- /flow-next:chart-rollup -->"
DECISION_BLOCK_OPEN = "<!-- flow-next:decision -->"
DECISION_BLOCK_CLOSE = "<!-- /flow-next:decision -->"

# URL host allowlists keyed by provider (normalized lowercase host).
_DEFAULT_HOSTS = {
    "github": ("github.com",),
    "gitlab": ("gitlab.com",),
    "linear": ("linear.app",),
    "jira": (),  # host comes from perTracker.baseUrl
}


#: Bounded holder-drain passes per project_chart call: how many times the lock
#: holder re-projects state that other chart commands committed while it was
#: mid-remote-span (see project_chart's drain loop).
_PROJECTION_DRAIN_LIMIT = 3


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _event_marker_key(event: str, revision: str, evidence: str) -> str:
    return _sha(f"{event}\x00{revision}\x00{evidence}")[:16]


def _parked_keys(chart: dict) -> list[str]:
    """Stable identity of the chart's parked-question set."""
    return sorted(
        str(q.get("key") or q.get("body") or "")
        for q in (chart.get("parked_questions") or [])
        if isinstance(q, dict)
    )


def _chart_lifecycle_entry(chart: dict) -> dict:
    """Chart-only transition identity (status, briefings, abandon/reopen).

    abandon/reopen/final-briefing mutate ONLY the chart sidecar - no
    decision sidecar and no parked key changes - so neither a supplied
    chart_decision_revision nor the decision digest distinguishes the
    state before and after such a commit. Without these fields the drain
    pass recomputes the first pass's marker key and dedupes, leaving the
    parent status stale. The success-marker write never touches any of
    these fields, so identical-retry dedupe holds.
    """
    return {
        "status": chart.get("status"),
        "abandoned_at": chart.get("abandoned_at"),
        "reopened_at": chart.get("reopened_at"),
        "briefings": sorted(
            (str(b.get("id") or ""), str(b.get("status") or ""))
            for b in (chart.get("briefings") or [])
            if isinstance(b, dict)
        ),
    }


def _mutation_state_digest(chart: dict, decisions: list) -> str:
    """Projection-side marker digest: claim/asset state + mutation identity.

    The supplied chart revision (chart_decision_revision, the briefing-
    fingerprint base - never change that hash) is content-based: a chart
    wired back to a prior graph state (D1 blocked_by D2 -> D3 -> D2) reuses
    the first event's revision, and claims/assets/timestamps are omitted
    entirely. Fold in each decision sidecar's updated_at (every committed
    chart mutation stamps it) so a returned-to-prior state still mints a
    distinct marker, while a pure retry of the same committed mutation
    (same sidecar bytes) still dedupes. The chart's own updated_at is
    deliberately excluded: the success-marker write bumps it, which would
    break retry dedupe.

    Parked-question keys fold in for the same reason: park-question /
    remove-question mutate ONLY the chart sidecar (no decision status or
    digest changes), yet the parent rollup's parked count depends on them.
    The marker write never touches parked state, so retry dedupe holds.

    Chart-only lifecycle transitions (abandon/reopen/final-briefing) fold
    in via _chart_lifecycle_entry for the same reason again.
    """
    return _sha(json.dumps({
        "decisions": _digest_entries(decisions),
        "parked": _parked_keys(chart),
        "chart": _chart_lifecycle_entry(chart),
    }, sort_keys=True, default=str))


def _digest_entries(decisions: list) -> list[dict]:
    """Per-decision mutation-identity entries backing _mutation_state_digest."""
    return sorted(
        (
            {
                "id": d.get("id"),
                "updated_at": d.get("updated_at"),
                "claimed_by": d.get("claimed_by"),
                "claimed_at": d.get("claimed_at"),
                "assets": _safe_assets(d.get("assets")),
            }
            for d in decisions if isinstance(d, dict)
        ),
        key=lambda x: str(x.get("id") or ""),
    )


def _chart_base_revision(chart: dict, decisions: list) -> str:
    """Fallback marker base when the caller supplied no revision."""
    return _sha(json.dumps({
        "id": chart.get("id"),
        "status": chart.get("status"),
        "decisions": [
            {"id": d.get("id"), "status": d.get("status")}
            for d in decisions if isinstance(d, dict)
        ],
        # Parked-only mutations (park-question / remove-question) change no
        # decision status or digest; without the parked set here the drain's
        # foreign-change predicate never fires and the parent rollup keeps a
        # stale parked count until an unrelated event.
        "parked": _parked_keys(chart),
        # Same for chart-only lifecycle transitions (abandon/reopen/
        # final-briefing): they must trip the foreign-change predicate so
        # the holder drains them before releasing the lock.
        "lifecycle": _chart_lifecycle_entry(chart),
    }, sort_keys=True, default=str))


def _projection_state(tracker: dict) -> dict:
    raw = dict_(tracker.get("projection"))
    markers = raw.get("event_markers")
    if not isinstance(markers, list):
        markers = []
    return {
        "revision": raw.get("revision"),
        "event_markers": list(markers),
        "completed_steps": list(raw.get("completed_steps") or []),
        "degraded": raw.get("degraded"),
    }


def _find_event_marker(tracker: dict, key: str) -> Optional[dict]:
    for entry in _projection_state(tracker).get("event_markers") or []:
        if isinstance(entry, dict) and entry.get("key") == key:
            return entry
    return None


def _has_event_marker(tracker: dict, key: str) -> bool:
    return _find_event_marker(tracker, key) is not None


def _has_event_receipt(flow_dir: Path, chart_id: str, event: str,
                       revision: str) -> bool:
    """True when a sync receipt already records this event+revision.

    Success receipts (and the repair receipt written on the marker-dedupe
    path) carry details.revision, so repair itself is idempotent. Fails
    open (False) on unreadable state: an extra repair receipt is harmless;
    a permanently missing one is not.
    """
    token_fname = subject_marker_token("chart", chart_id).replace(":", "-")
    runs = Path(flow_dir) / "sync-runs"
    try:
        paths = list(runs.glob(f"sync-{token_fname}-*.json"))
    except OSError:
        return False
    for p in paths:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(obj, dict) or obj.get("event") != event:
            continue
        details = obj.get("details")
        if isinstance(details, dict) and details.get("revision") == revision:
            return True
    return False


def _append_event_marker(
    tracker: dict,
    *,
    event: str,
    revision: str,
    evidence: str,
    completed_steps: list,
    status: str,
) -> dict:
    key = _event_marker_key(event, revision, evidence)
    if _has_event_marker(tracker, key):
        return tracker
    state = _projection_state(tracker)
    markers = list(state["event_markers"])
    markers.append({
        "key": key,
        "event": event,
        "revision": revision,
        "evidence": evidence,
        "completed_steps": list(completed_steps),
        "status": status,
        "at": now_iso(),
    })
    tracker = dict(tracker)
    tracker["projection"] = {
        "revision": revision,
        "event_markers": markers,
        "completed_steps": list(completed_steps),
        "degraded": state.get("degraded"),
    }
    return tracker


def _safe_gist(answer: Any, *, max_len: int = 240) -> str:
    """One-line safe gist; never copy credentials or destructive command strings."""
    if answer is None:
        return ""
    if isinstance(answer, dict):
        text = str(answer.get("gist") or answer.get("summary") or answer.get("body") or "")
    else:
        text = str(answer)
    text = " ".join(text.split())
    # Redact obvious secrets / guard-triggering patterns by reference only.
    lowered = text.lower()
    if any(
        tok in lowered
        for tok in (
            "password=",
            "api_key=",
            "secret=",
            "authorization:",
            "rm -rf",
            "curl | sh",
        )
    ):
        return "[redacted - see local decision record]"
    if len(text) > max_len:
        return text[: max_len - 1] + "..."
    return text


def _safe_assets(assets: Any) -> list[dict]:
    out = []
    if not isinstance(assets, list):
        return out
    for a in assets:
        if not isinstance(a, dict):
            continue
        kind = a.get("kind")
        ref = a.get("reference") or a.get("path") or a.get("url")
        summary = a.get("summary") or a.get("display") or ""
        if not ref:
            continue
        ref_s = str(ref)
        if any(x in ref_s.lower() for x in ("password=", "token=", "secret=")):
            continue
        out.append({
            "kind": kind,
            "reference": ref_s,
            "summary": _safe_gist(summary, max_len=120),
        })
    return out


def build_decision_body(decision: dict) -> str:
    """Owned body block for a decision child issue."""
    did = decision.get("id") or ""
    title = decision.get("title") or ""
    dtype = decision.get("type") or ""
    attendance = decision.get("attendance") or ""
    status = decision.get("status") or "open"
    gist = _safe_gist(decision.get("answer"))
    assets = _safe_assets(decision.get("assets"))
    lines = [
        DECISION_BLOCK_OPEN,
        f"**Decision:** {did} - {title}",
        f"**Type:** {dtype}",
        f"**Attendance:** {attendance}",
        f"**Local status:** {status}",
    ]
    if decision.get("claimed_by"):
        lines.append(f"**Claimed by:** {decision.get('claimed_by')} (local claim; not provider workflow)")
    if gist:
        lines.append(f"**Gist:** {gist}")
    if assets:
        lines.append("**Evidence:**")
        for a in assets:
            lines.append(f"- [{a.get('kind') or 'ref'}] {a['reference']}"
                         + (f" - {a['summary']}" if a.get("summary") else ""))
    blocked = decision.get("blocked_by") or []
    if blocked:
        lines.append(f"**Blocked by (local):** {', '.join(str(x) for x in blocked)}")
    # depends_on stays local provenance - never projected as blocking edge.
    depends = decision.get("depends_on") or []
    if depends:
        lines.append(
            f"**Depends on (local provenance only; not a blocking edge):** "
            f"{', '.join(str(x) for x in depends)}"
        )
    lines.append(DECISION_BLOCK_CLOSE)
    return "\n".join(lines) + "\n"


def _count_decisions(chart: dict, decisions: list[dict]) -> dict:
    status_index = {
        d["id"]: d.get("status")
        for d in decisions
        if isinstance(d, dict) and d.get("id")
    }
    open_decs = [d for d in decisions if isinstance(d, dict) and d.get("status") == "open"]

    def is_blocked(d: dict) -> bool:
        for b in d.get("blocked_by") or []:
            st = status_index.get(b)
            if st is None or st == "open":
                return True
        return False

    blocked = [d for d in open_decs if is_blocked(d)]
    claimed = [d for d in open_decs if d.get("claimed_by")]
    actionable = [d for d in open_decs if not is_blocked(d) and not d.get("claimed_by")]
    resolved = [d for d in decisions if isinstance(d, dict) and d.get("status") == "resolved"]
    superseded = [d for d in decisions if isinstance(d, dict) and d.get("status") == "superseded"]
    oos = [d for d in decisions if isinstance(d, dict) and d.get("status") == "out-of-scope"]
    parked = chart.get("parked_questions") or []
    if not isinstance(parked, list):
        parked = []
    return {
        "actionable": len(actionable),
        "blocked": len(blocked),
        "claimed": len(claimed),
        "resolved": len(resolved),
        "superseded": len(superseded),
        "out_of_scope": len(oos),
        "parked": len(parked),
        "frontier": [
            {"id": d.get("id"), "title": d.get("title")}
            for d in actionable
        ],
        "latest_resolved": None,
    }


def build_parent_rollup(chart: dict, decisions: list[dict]) -> str:
    counts = _count_decisions(chart, decisions)
    resolved = [
        d for d in decisions
        if isinstance(d, dict) and d.get("status") == "resolved"
    ]
    latest = None
    if resolved:
        # Prefer updated_at / created order; fall back to id order.
        def sort_key(d: dict) -> str:
            return str(d.get("updated_at") or d.get("created") or d.get("id") or "")

        latest = max(resolved, key=sort_key)
        counts["latest_resolved"] = {
            "id": latest.get("id"),
            "title": latest.get("title"),
            "gist": _safe_gist(latest.get("answer")),
        }
    lines = [
        CHART_ROLLUP_OPEN,
        f"**Chart:** {chart.get('id')} - {chart.get('title')}",
        f"**Outcome:** {chart.get('outcome') or ''}",
        f"**Status:** {chart.get('status') or 'open'}",
        (
            f"**Counts:** actionable={counts['actionable']} "
            f"blocked={counts['blocked']} claimed={counts['claimed']} "
            f"resolved={counts['resolved']} superseded={counts['superseded']} "
            f"out-of-scope={counts['out_of_scope']} parked={counts['parked']}"
        ),
    ]
    lr = counts.get("latest_resolved")
    if lr:
        lines.append(
            f"**Latest resolved:** {lr['id']} - {lr['title']}"
            + (f" - {lr['gist']}" if lr.get("gist") else "")
        )
    frontier = counts.get("frontier") or []
    if frontier:
        lines.append("**Frontier:**")
        for f in frontier:
            lines.append(f"- {f.get('id')} - {f.get('title')}")
    else:
        lines.append("**Frontier:** (empty)")
    lines.append(CHART_ROLLUP_CLOSE)
    return "\n".join(lines) + "\n"


def _upsert_owned_block(body: str, open_m: str, close_m: str, content: str) -> str:
    body = body or ""
    if open_m in body and close_m in body:
        start = body.index(open_m)
        end = body.index(close_m) + len(close_m)
        return body[:start] + content.rstrip("\n") + body[end:]
    if body and not body.endswith("\n"):
        body += "\n"
    return body + content


def _load_chart_bundle(flow_dir: Path, chart_id: str) -> Result:
    loaded = load_subject(flow_dir, "chart", chart_id)
    if isinstance(loaded, TrackerError):
        return loaded
    path, chart, tracker = loaded
    decisions: list[dict] = []
    for entry in chart.get("decisions") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        did = entry["id"]
        dloaded = load_subject(flow_dir, "decision", did)
        if isinstance(dloaded, TrackerError):
            # Compact entry only if full sidecar missing.
            decisions.append(dict(entry))
            continue
        _dp, ddata, _dt = dloaded
        # Merge compact claim fields if sidecar lags.
        for k in ("claimed_by", "claimed_at", "status", "title", "type", "attendance"):
            if entry.get(k) is not None and ddata.get(k) is None:
                ddata[k] = entry.get(k)
        decisions.append(ddata)
    return path, chart, tracker, decisions


def _link_fields(created: dict) -> dict:
    return {
        "id": created["id"],
        "identifier": created.get("identifier"),
        "url": created.get("url"),
        "linkState": "linked",
    }


# ---------------------------------------------------------------------------
# Created-but-unlinked identity recovery (create-first home, verbs.py pattern):
# a remote create that lands but whose local link write fails must leave a
# durable, reconcileable identity - otherwise the next projection re-creates
# a duplicate remote issue.
# ---------------------------------------------------------------------------

def _pending_identity_path(flow_dir: Path, kind: str, subject_id: str) -> Path:
    return Path(flow_dir) / "create-first" / f"chart-{kind}-{subject_id}.json"


def _record_pending_identity(flow_dir: Path, kind: str, subject_id: str,
                             fields: dict) -> Optional[TrackerError]:
    """Durable identity record, ONE retry on write failure.

    Returns the write error when the record could not be persisted; the
    caller then decides whether the failure receipt still covers recovery
    (see _receipt_identity_fields) or must refuse retryably-unsafe state."""
    path = _pending_identity_path(flow_dir, kind, subject_id)
    payload = {
        "kind": kind,
        "subjectId": subject_id,
        "id": fields.get("id"),
        "identifier": fields.get("identifier"),
        "url": fields.get("url"),
        "recordedAt": now_iso(),
    }
    err = atomic_write_json(path, payload)
    if err is not None:
        err = atomic_write_json(path, payload)
    return err


def _clear_pending_identity(flow_dir: Path, kind: str, subject_id: str) -> None:
    with contextlib.suppress(OSError):
        _pending_identity_path(flow_dir, kind, subject_id).unlink()


def _tombstone_pending_identity(flow_dir: Path, kind: str,
                                subject_id: str) -> None:
    """Retire a recorded identity after a durable collision.

    An EXISTING pending file with a null id suppresses BOTH adoption
    sources (file and receipt fallback), so the next projection creates
    fresh instead of re-adopting the collided identity from an immutable
    failure receipt forever. Best-effort: an unwritable tombstone means the
    next projection collides loudly again - never silently duplicates."""
    atomic_write_json(_pending_identity_path(flow_dir, kind, subject_id), {
        "kind": kind,
        "subjectId": subject_id,
        "id": None,
        "reason": "durable_collision",
        "supersededAt": now_iso(),
    })


def _receipt_identity_fields(flow_dir: Path, kind: str,
                             subject_id: str) -> Optional[dict]:
    """Failure-receipt fallback when no pending-identity file exists.

    The create-ok/link-fail receipt carries the created identity in its
    details (id/identifier/url plus the create-*-remote step). Only the
    LATEST receipt for the chart token is consulted: every later projection
    - success or a different failure - writes a newer receipt without that
    step, so a stale identity is never adopted after the subject moved on
    (e.g. a deliberate unlink)."""
    chart_id = subject_id if kind == "chart" else subject_id.rsplit(".D", 1)[0]
    token_fname = subject_marker_token("chart", chart_id).replace(":", "-")
    runs = Path(flow_dir) / "sync-runs"
    try:
        paths = list(runs.glob(f"sync-{token_fname}-*.json"))
    except OSError:
        return None
    latest: Optional[dict] = None
    latest_key = ("", "")
    for p in sorted(paths):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        key = (str(obj.get("timestamp") or ""), p.name)
        if key >= latest_key:
            latest_key = key
            latest = obj
    if latest is None:
        return None
    details = latest.get("details")
    if not isinstance(details, dict):
        return None
    step = ("create-parent-remote" if kind == "chart"
            else f"create-child-remote:{subject_id}")
    if step not in (details.get("completed_steps") or []):
        return None
    rid = details.get("id")
    if not isinstance(rid, str) or not rid.strip():
        return None
    return {
        "id": rid,
        "identifier": details.get("identifier"),
        "url": details.get("url"),
        "linkState": "linked",
    }


def _pending_identity_fields(flow_dir: Path, kind: str,
                             subject_id: str) -> Optional[dict]:
    path = _pending_identity_path(flow_dir, kind, subject_id)
    if path.exists():
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(obj, dict):
            return None
        rid = obj.get("id")
        if not isinstance(rid, str) or not rid.strip():
            # Tombstone (durable-collision supersession): suppress the
            # receipt fallback too - the next projection creates fresh.
            return None
        return {
            "id": rid,
            "identifier": obj.get("identifier"),
            "url": obj.get("url"),
            "linkState": "linked",
        }
    # No pending file at all (its write may itself have failed): fall back
    # to the last failure receipt's recorded created identity.
    return _receipt_identity_fields(flow_dir, kind, subject_id)


def _link_subject(flow_dir: Path, kind: str, subject_id: str, mutate, *,
                  collision_id: str) -> Result:
    """Link write with ONE transient-failure retry: the write contends with
    chart WAL/config locks, so a lock timeout is often momentary."""
    linked = locked_subject_write(
        flow_dir, kind, subject_id, mutate, collision_id=collision_id,
    )
    if isinstance(linked, TrackerError):
        linked = locked_subject_write(
            flow_dir, kind, subject_id, mutate, collision_id=collision_id,
        )
    return linked


def _identity_error(err: TrackerError, fields: dict) -> TrackerError:
    """Ride the created identity into the error details (verbs.py pattern)."""
    return dataclasses.replace(err, details={
        **(err.details or {}),
        "id": fields.get("id"),
        "identifier": fields.get("identifier"),
        "url": fields.get("url"),
    })


def _refuse_unpersisted_identity(err: TrackerError, *, kind: str,
                                 subject_id: str, fields: dict,
                                 pend_err: Optional[TrackerError]
                                 ) -> TrackerError:
    """Escalate when NOTHING durable names a created remote issue.

    The pending-identity write failed (twice) AND the failure receipt could
    not be written (fail_result marked receipt_status "unwritten"): a retry
    would see an unlinked subject and create a duplicate. Refuse retry;
    the identity rides the error message and details as the last copy."""
    if pend_err is None:
        return err
    if (err.details or {}).get("receipt_status") != "unwritten":
        return err
    ident = fields.get("identifier") or fields.get("id")
    return dataclasses.replace(
        err,
        subtype="created_identity_unpersisted",
        auto_retryable=False,
        message=(
            f"remote issue {ident} was created for {kind} {subject_id} but "
            "neither the local link, the pending-identity record, nor the "
            "failure receipt could be written; link it manually "
            f"({fields.get('url') or ident}) before retrying - a blind "
            "retry would create a duplicate"
        ),
        details={
            **(err.details or {}),
            "pending_write_failed": {
                "class": pend_err.cls.value,
                "subtype": pend_err.subtype,
                "message": pend_err.message,
            },
        },
    )


def _create_issue(
    config: dict,
    execute: Execute,
    *,
    title: str,
    body: str,
) -> Result:
    return provider_create(config, execute, title=title, body=body)


def _wire_read(
    config: dict,
    execute: Execute,
    locator: dict,
) -> Result:
    from ..wire import dispatch as wire_dispatch  # noqa: PLC0415

    return wire_dispatch("read", config, locator=locator, execute=execute)


def _wire_update(
    config: dict,
    execute: Execute,
    locator: dict,
    *,
    title: Optional[str] = None,
    body: Optional[str] = None,
) -> Result:
    from ..wire import dispatch as wire_dispatch  # noqa: PLC0415

    return wire_dispatch(
        "update", config, locator=locator, title=title, body=body,
        execute=execute,
    )


def _project_hierarchy(
    config: dict,
    execute: Execute,
    *,
    parent_loc: dict,
    child_loc: dict,
    caps: dict,
) -> Result:
    """Parent/child hierarchy where subIssues is supported; else degraded flat.

    GitHub: chart parent + decision child via sub_issues (hierarchy, not
    blocked-by). Linear/GitLab/Jira: no subIssues we consume - labelled/linked
    flat issues with explicit degradation.
    """
    if not caps.get("subIssues"):
        return {
            "projected": False,
            "degraded": {
                "capability": "subIssues",
                "form": "flat_linked",
                "note": (
                    "provider has no native parent/child hierarchy; "
                    "chart parent and decision children remain labelled/linked flat issues"
                ),
            },
        }
    provider = tracker_type(config)
    if provider != "github":
        return {
            "projected": False,
            "degraded": {
                "capability": "subIssues",
                "form": "flat_linked",
                "note": f"{provider} hierarchy not implemented; flat linked issues",
            },
        }
    from ..relate.providers import github_set  # noqa: PLC0415

    # github_set treats to=parent (blocker in dep terms) and from=child.
    # For chart hierarchy we want chart=parent, decision=child.
    out = github_set(
        config,
        execute,
        from_id=str(child_loc["durable"]),
        to_id=str(parent_loc["durable"]),
        from_display=str(child_loc["display"]),
        to_display=str(parent_loc["display"]),
    )
    if isinstance(out, TrackerError):
        return out
    # Hierarchy form is intentional for chart parent/child - strip the
    # blocked-by degradation note github_set attaches for dep projection.
    if isinstance(out, dict):
        out = dict(out)
        out["form"] = "sub_issues"
        out["kind"] = "hierarchy"
        out.pop("degraded", None)
    return out


def _hierarchy_marker_key(parent_loc: dict, child_loc: dict) -> str:
    """Durable per-child hierarchy-step key on the decision's relation ledger."""
    return "hier:" + dep_relation_key(
        str(child_loc["durable"]), str(parent_loc["durable"]),
    )


def _ensure_hierarchy(
    flow_dir: Path,
    config: dict,
    execute: Execute,
    *,
    chart_id: str,
    did: str,
    dtracker: dict,
    parent_loc: dict,
    child_loc: dict,
    caps: dict,
) -> Result:
    """Idempotently assert parent/child hierarchy for a linked child.

    A ledger marker records completion, so a create-ok/hierarchy-fail retry
    re-attempts hierarchy for already-linked children instead of silently
    taking the body-update-only branch and orphaning the child.
    """
    key = _hierarchy_marker_key(parent_loc, child_loc)
    if ledger_has(dtracker, key):
        return {"projected": True, "already": True, "form": "sub_issues"}
    hier = _project_hierarchy(
        config, execute, parent_loc=parent_loc, child_loc=child_loc, caps=caps,
    )
    if isinstance(hier, dict) and hier.get("projected"):
        def _mark_hier(t: dict, _key=key):
            t = ledger_append(
                t, key=_key, dep_spec=chart_id,
                from_tracker_id=str(child_loc["durable"]),
                to_tracker_id=str(parent_loc["durable"]),
                rel_type="hierarchy", source="flow",
            )
            return ledger_finalize(t, key=_key)

        # Marker write failure is non-fatal: hierarchy is idempotent and the
        # unmarked step is simply re-asserted on the next projection.
        locked_subject_write(flow_dir, "decision", did, _mark_hier)
    return hier


def _project_blocking(
    config: dict,
    execute: Execute,
    *,
    from_loc: dict,
    to_loc: dict,
    caps: dict,
    dep_subject: str,
) -> Result:
    """Project blocked_by only. depends_on is NEVER an indistinguishable block."""
    provider = tracker_type(config)
    if provider == "github" or not caps.get("blockedBy"):
        return {
            "projected": False,
            "degraded": {
                "capability": "blockedBy",
                "form": "local_provenance",
                "note": (
                    "native blocking unsupported or github hierarchy-only; "
                    "blocked_by kept as local provenance and owned body text only"
                ),
            },
        }
    from ..relate import providers as RP  # noqa: PLC0415

    from_id = str(from_loc["durable"])
    to_id = str(to_loc["durable"])
    from_display = str(from_loc["display"])
    to_display = str(to_loc["display"])

    if provider == "linear":
        present = RP.linear_probe(config, execute, from_id=from_id, to_id=to_id)
        if isinstance(present, TrackerError):
            return present
        if present is True:
            return {"projected": True, "already": True, "form": "blocks"}
        return RP.linear_set(
            config, execute,
            from_id=from_id, to_id=to_id,
            from_display=from_display, to_display=to_display,
        )
    if provider == "jira":
        present = RP.jira_probe(config, execute, from_id=from_id, to_id=to_id)
        if isinstance(present, TrackerError):
            return present
        if present is True:
            return {"projected": True, "already": True, "form": "blocks"}
        return RP.jira_set(
            config, execute,
            from_id=from_id, to_id=to_id,
            from_display=from_display, to_display=to_display,
        )
    if provider == "gitlab":
        # Probe first (linear/jira parity): a ledger-write-failure retry
        # re-asserts an edge the previous run already created, and GitLab's
        # link create is not idempotent (409 on duplicates).
        present = RP.gitlab_probe_pair(
            config, execute,
            from_display=from_display, to_display=to_display,
        )
        if isinstance(present, TrackerError):
            return present
        if present is True:
            return {"projected": True, "already": True, "form": "blocks"}
        return RP.gitlab_set(
            config, execute,
            from_id=from_id, to_id=to_id,
            from_display=from_display, to_display=to_display,
            blocked_by=True, plan=None,
        )
    return {
        "projected": False,
        "degraded": {
            "capability": "blockedBy",
            "form": "local_provenance",
            "note": f"unknown provider {provider!r} for blocking projection",
        },
    }


def _remove_blocking(
    config: dict,
    execute: Execute,
    *,
    from_loc: dict,
    to_id: str,
    caps: dict,
) -> Result:
    """Remove one stale flow-owned native blocks edge (from was blocked by to).

    GitHub never projects native blocking (local provenance only), so there is
    nothing remote to remove - the ledger entry alone is stale. Providers
    without removal support report explicit degradation and KEEP the ledger
    entry (dropping it would silently disown a live stale relation).
    """
    provider = tracker_type(config)
    if provider == "github":
        return {"removed": False, "already_absent": True}
    from ..relate import providers as RP  # noqa: PLC0415

    from_id = str(from_loc["durable"])
    if caps.get("blockedBy"):
        if provider == "linear":
            return RP.linear_remove(config, execute, from_id=from_id,
                                    to_id=to_id)
        if provider == "jira":
            return RP.jira_remove(config, execute, from_id=from_id,
                                  to_id=to_id)
        if provider == "gitlab":
            return RP.gitlab_remove(
                config, execute, from_id=from_id,
                from_display=str(from_loc["display"]), to_id=to_id,
            )
    return {
        "removed": False,
        "degraded": {
            "capability": "blockedBy",
            "form": "stale_native_relation",
            "note": (
                f"{provider!r} native blocking removal unavailable; "
                "stale flow-owned relation remains remotely"
            ),
        },
    }


def _decision_title(decision: dict) -> str:
    did = decision.get("id") or ""
    title = decision.get("title") or did
    return f"{did}: {title}"[:200]


def _chart_title(chart: dict) -> str:
    cid = chart.get("id") or ""
    title = chart.get("title") or cid
    return f"[chart] {cid}: {title}"[:200]


def project_chart(
    flow_dir: Path,
    chart_id: str,
    *,
    event: str,
    revision: Optional[str] = None,
    evidence: Optional[str] = None,
    execute: Execute = default_execute,
) -> Result:
    """Project one chart lifecycle event. Local state already committed.

    The whole remote read/update span runs under a dedicated cross-process
    projection lock (chart_projection_lock - NOT the chart WAL lock, which
    local mutations must never wait on across network latency). Chart +
    decision state is reloaded INSIDE the lock, so two overlapping chart
    commands cannot interleave a stale projection over a newer one: the
    later entrant re-projects the newest committed state (convergent).
    Best-effort: lock timeout is a CONFLICT/lock_timeout TrackerError; it
    never blocks or fails the local mutation result.

    Returns a data dict (success/skip/partial) or TrackerError with completed_steps.
    Never raises. Never rolls back local chart files.
    """
    flow_dir = Path(flow_dir)
    config = read_config(flow_dir)
    gate = projection_gate(config)
    if not gate["active"]:
        return {
            "projected": False,
            "skipped": gate["skipped"],
            "reason": gate["reason"],
            "chart_id": chart_id,
            "event": event,
            "completed_steps": [],
        }

    if event not in CHART_EVENTS and not event.startswith("chart."):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"unknown chart projection event {event!r}",
            subtype="event",
        )

    from ..config_lock import ConfigLockTimeout  # noqa: PLC0415

    try:
        with chart_projection_lock(flow_dir):
            result: Result = {}
            for _ in range(_PROJECTION_DRAIN_LIMIT):
                result = _project_chart_locked(
                    flow_dir, config, gate, chart_id,
                    event=event, revision=revision, evidence=evidence,
                    execute=execute,
                )
                if not (isinstance(result, dict)
                        and result.get("stale_revision")):
                    return result
                # Holder drain: a chart mutation committed locally while this
                # holder was mid-remote-span (the mutation's own projection
                # attempt may have timed out on this very lock). Re-project
                # the newer persisted state before releasing the lock - the
                # marker was keyed on the state actually pushed, so the
                # re-entry projects instead of deduping. This is what keeps
                # contended projections convergent even when a waiter gives
                # up: whatever it committed, the holder drains it here.
            # Drains exhausted under sustained mutation pressure: return the
            # last successful projection, naming the remaining unprojected
            # revision (stale_revision) so the caller can see the tracker is
            # one step behind; the next projection event picks it up.
            result = dict(result)
            result["drain_exhausted"] = True
            return result
    except ConfigLockTimeout as exc:
        return TrackerError(
            ErrorClass.CONFLICT, str(exc), subtype="lock_timeout",
            details={"completed_steps": []},
        )


def _project_chart_locked(
    flow_dir: Path,
    config: dict,
    gate: dict,
    chart_id: str,
    *,
    event: str,
    revision: Optional[str],
    evidence: Optional[str],
    execute: Execute,
) -> Result:
    """project_chart body; caller holds chart_projection_lock."""
    bundle = _load_chart_bundle(flow_dir, chart_id)
    if isinstance(bundle, TrackerError):
        return bundle
    chart_path, chart, chart_tracker, decisions = bundle
    supplied_revision = revision
    start_skeleton = _chart_base_revision(chart, decisions)
    base_revision = revision or start_skeleton
    # Extend the marker revision with the projection-side state digest
    # (claims, assets, per-decision mutation identity - see
    # _mutation_state_digest for why the base revision alone dedupes wrongly).
    revision = _sha(
        f"{base_revision}\x00{_mutation_state_digest(chart, decisions)}"
    )
    evidence_supplied = evidence is not None
    evidence = evidence or revision[:16]
    marker_key = _event_marker_key(event, revision, evidence)

    marker = _find_event_marker(chart_tracker, marker_key)
    if marker is not None:
        deduped: dict[str, Any] = {
            "projected": True,
            "deduped": True,
            "chart_id": chart_id,
            "event": event,
            "revision": revision,
            "completed_steps": list(
                _projection_state(chart_tracker).get("completed_steps") or []
            ),
            "tracker_id": chart_tracker.get("id"),
        }
        # Receipt repair: the success marker persists BEFORE the aggregate
        # receipt, so a receipt write that failed after the marker landed
        # would otherwise never be retried - every retry exits here. Write
        # the missing receipt from the marker's recorded outcome; idempotent
        # because the repair receipt carries details.revision, which the
        # next dedupe finds. A failed repair write leaves the state as-is
        # for the next retry to converge.
        if not _has_event_receipt(flow_dir, chart_id, event, revision):
            rerr = write_aggregate_receipt(
                flow_dir,
                spec_id=subject_marker_token("chart", chart_id),
                event=event,
                status=str(marker.get("status") or "pushed"),
                tracker_id=chart_tracker.get("id"),
                transport=gate["provider"],
                note="chart projection receipt repaired on marker dedupe",
                details={
                    "revision": revision,
                    "evidence": marker.get("evidence") or evidence,
                    "repaired": True,
                },
            )
            if rerr is None:
                deduped["receipt_repaired"] = True
        return deduped

    provider = gate["provider"]
    caps = caps_of(config)
    completed: list = []
    statuses: list = []
    degraded_parts: list = []
    steps: dict[str, Any] = {}
    # Decision ids whose sidecar THIS holder wrote (link adoption, hierarchy
    # marker, relation ledger). The end-of-pass marker recompute absorbs only
    # these self-inflicted updated_at bumps; any other digest change is a
    # foreign mutation the drain loop must re-project.
    self_wrote: set[str] = set()

    parent_body = build_parent_rollup(chart, decisions)
    parent_title = _chart_title(chart)

    # --- parent create-if-unlinked ---
    parent_state = chart_tracker.get("linkState") or (
        "linked" if chart_tracker.get("id") else "unlinked"
    )
    if parent_state == "unlinked" or not chart_tracker.get("id"):
        # A prior run may have created the remote issue and failed only the
        # local link write - adopt that identity instead of re-creating.
        adopted = _pending_identity_fields(flow_dir, "chart", chart_id)
        if adopted is not None:
            fields = adopted
        else:
            created = _create_issue(
                config, execute, title=parent_title, body=parent_body,
            )
            if isinstance(created, TrackerError):
                # Persist nothing remote; still write partial receipt intent
                # locally only if something already completed (nothing yet).
                return created
            fields = _link_fields(created)

        def _link_parent(t: dict):
            hit = subject_collision(
                flow_dir, fields["id"], except_kind="chart", except_id=chart_id,
            )
            if hit:
                return hit
            t = dict(t)
            t.update(fields)
            return t

        linked = _link_subject(
            flow_dir, "chart", chart_id, _link_parent, collision_id=fields["id"],
        )
        if isinstance(linked, TrackerError):
            pend_err: Optional[TrackerError] = None
            if adopted is not None and linked.subtype == "durable_collision":
                # The recorded identity now belongs to another subject; a
                # tombstone (not a bare clear) retires receipt evidence
                # too, so the next projection creates fresh.
                _tombstone_pending_identity(flow_dir, "chart", chart_id)
            else:
                # Remote create succeeded; persist the identity durably so
                # the NEXT projection adopts it instead of duplicating.
                pend_err = _record_pending_identity(
                    flow_dir, "chart", chart_id, fields,
                )
            err = fail_result(
                _identity_error(linked, fields),
                completed=(["create-parent-remote"] if adopted is None else []),
                statuses=(["pushed"] if adopted is None else []),
                flow_dir=flow_dir,
                spec_id=subject_marker_token("chart", chart_id),
                event=event,
                tracker_id=fields.get("id"),
                transport=provider,
                degraded=None,
            )
            return _refuse_unpersisted_identity(
                err, kind="chart", subject_id=chart_id, fields=fields,
                pend_err=pend_err,
            )
        _clear_pending_identity(flow_dir, "chart", chart_id)
        chart_tracker = linked
        completed.append("create-parent" if adopted is None else "adopt-parent")
        statuses.append("pushed")
        steps["create_parent"] = {
            "kind": "created" if adopted is None else "adopted", **fields,
        }
    else:
        # Hygiene: a pending identity must never outlive a completed link
        # (it could be wrongly adopted after a later staleLink unlink).
        _clear_pending_identity(flow_dir, "chart", chart_id)
        steps["create_parent"] = {
            "kind": "already_linked",
            "id": chart_tracker.get("id"),
            "identifier": chart_tracker.get("identifier"),
        }

    parent_loc = locator_of(chart_tracker)
    if isinstance(parent_loc, TrackerError):
        return fail_result(
            parent_loc, completed=completed, statuses=statuses,
            flow_dir=flow_dir,
            spec_id=subject_marker_token("chart", chart_id),
            event=event, tracker_id=chart_tracker.get("id"),
            transport=provider,
        )

    # --- children create/update (pass one: every child gets a locator) ---
    child_results = []
    edge_children: list[str] = []
    for decision in decisions:
        if not isinstance(decision, dict) or not decision.get("id"):
            continue
        did = decision["id"]
        dloaded = load_subject(flow_dir, "decision", did)
        if isinstance(dloaded, TrackerError):
            # Ensure tracker block exists on compact-only entries by skipping remote.
            child_results.append({"id": did, "skipped": "decision_missing"})
            continue
        dpath, ddata, dtracker = dloaded
        dbody = build_decision_body(ddata)
        dtitle = _decision_title(ddata)
        dstate = dtracker.get("linkState") or (
            "linked" if dtracker.get("id") else "unlinked"
        )
        if dstate == "unlinked" or not dtracker.get("id"):
            adopted = _pending_identity_fields(flow_dir, "decision", did)
            if adopted is not None:
                fields = adopted
            else:
                created = _create_issue(
                    config, execute, title=dtitle, body=dbody,
                )
                if isinstance(created, TrackerError):
                    return fail_result(
                        created, completed=completed, statuses=statuses,
                        flow_dir=flow_dir,
                        spec_id=subject_marker_token("chart", chart_id),
                        event=event, tracker_id=chart_tracker.get("id"),
                        transport=provider,
                        degraded=collect_degraded(*degraded_parts),
                    )
                fields = _link_fields(created)

            def _link_child(t: dict, _fields=fields, _did=did):
                hit = subject_collision(
                    flow_dir, _fields["id"],
                    except_kind="decision", except_id=_did,
                )
                if hit:
                    return hit
                t = dict(t)
                t.update(_fields)
                return t

            linked = _link_subject(
                flow_dir, "decision", did, _link_child, collision_id=fields["id"],
            )
            if isinstance(linked, TrackerError):
                pend_err = None
                if adopted is not None and linked.subtype == "durable_collision":
                    _tombstone_pending_identity(flow_dir, "decision", did)
                else:
                    pend_err = _record_pending_identity(
                        flow_dir, "decision", did, fields,
                    )
                extra = [] if adopted is not None else [
                    f"create-child-remote:{did}",
                ]
                err = fail_result(
                    _identity_error(linked, fields),
                    completed=completed + extra,
                    statuses=statuses + (["pushed"] if extra else []),
                    flow_dir=flow_dir,
                    spec_id=subject_marker_token("chart", chart_id),
                    event=event, tracker_id=fields.get("id"),
                    transport=provider,
                )
                return _refuse_unpersisted_identity(
                    err, kind="decision", subject_id=did, fields=fields,
                    pend_err=pend_err,
                )
            _clear_pending_identity(flow_dir, "decision", did)
            dtracker = linked
            self_wrote.add(did)
            completed.append(
                f"create-child:{did}" if adopted is None
                else f"adopt-child:{did}"
            )
            statuses.append("pushed")
            # hierarchy after both sides linked
            child_loc = locator_of(dtracker)
            if not isinstance(child_loc, TrackerError):
                hier = _ensure_hierarchy(
                    flow_dir, config, execute,
                    chart_id=chart_id, did=did, dtracker=dtracker,
                    parent_loc=parent_loc, child_loc=child_loc, caps=caps,
                )
                if isinstance(hier, TrackerError):
                    return fail_result(
                        hier, completed=completed, statuses=statuses,
                        flow_dir=flow_dir,
                        spec_id=subject_marker_token("chart", chart_id),
                        event=event, tracker_id=chart_tracker.get("id"),
                        transport=provider,
                    )
                if isinstance(hier, dict) and hier.get("degraded"):
                    degraded_parts.append(hier["degraded"])
                elif isinstance(hier, dict) and hier.get("projected"):
                    if not hier.get("already"):
                        self_wrote.add(did)
                    completed.append(f"hierarchy:{did}")
            child_results.append({
                "id": did,
                "kind": "created" if adopted is None else "adopted",
                **fields,
            })
            edge_children.append(did)
        else:
            # Update owned body block (claim/release/resolve refresh).
            _clear_pending_identity(flow_dir, "decision", did)
            child_loc = locator_of(dtracker)
            if isinstance(child_loc, TrackerError):
                return fail_result(
                    child_loc, completed=completed, statuses=statuses,
                    flow_dir=flow_dir,
                    spec_id=subject_marker_token("chart", chart_id),
                    event=event, tracker_id=chart_tracker.get("id"),
                    transport=provider,
                )
            # Read current body first; a failed read must abort this step -
            # updating on top of an unread body would replace real remote
            # content with only the flow-owned block.
            current = _wire_read(config, execute, child_loc)
            if isinstance(current, TrackerError):
                return fail_result(
                    current, completed=completed, statuses=statuses,
                    flow_dir=flow_dir,
                    spec_id=subject_marker_token("chart", chart_id),
                    event=event, tracker_id=chart_tracker.get("id"),
                    transport=provider,
                )
            cur_body = ""
            if isinstance(current, dict):
                cur_body = current.get("body") or ""
            new_body = _upsert_owned_block(
                cur_body, DECISION_BLOCK_OPEN, DECISION_BLOCK_CLOSE, dbody,
            )
            updated = _wire_update(
                config, execute, child_loc, title=dtitle, body=new_body,
            )
            if isinstance(updated, TrackerError):
                return fail_result(
                    updated, completed=completed, statuses=statuses,
                    flow_dir=flow_dir,
                    spec_id=subject_marker_token("chart", chart_id),
                    event=event, tracker_id=chart_tracker.get("id"),
                    transport=provider,
                )
            completed.append(f"update-child:{did}")
            statuses.append("updated")
            # Re-assert hierarchy for linked children whose hierarchy step is
            # not marked complete (create-ok/hierarchy-fail retry path). Only
            # attempted where the provider supports it; degraded providers
            # already reported flat_linked at create.
            if caps.get("subIssues"):
                hier = _ensure_hierarchy(
                    flow_dir, config, execute,
                    chart_id=chart_id, did=did, dtracker=dtracker,
                    parent_loc=parent_loc, child_loc=child_loc, caps=caps,
                )
                if isinstance(hier, TrackerError):
                    return fail_result(
                        hier, completed=completed, statuses=statuses,
                        flow_dir=flow_dir,
                        spec_id=subject_marker_token("chart", chart_id),
                        event=event, tracker_id=chart_tracker.get("id"),
                        transport=provider,
                    )
                if isinstance(hier, dict) and hier.get("degraded"):
                    degraded_parts.append(hier["degraded"])
                elif (
                    isinstance(hier, dict)
                    and hier.get("projected")
                    and not hier.get("already")
                ):
                    self_wrote.add(did)
                    completed.append(f"hierarchy:{did}")
                    statuses.append("pushed")
            child_results.append({
                "id": did, "kind": "updated",
                "id_tracker": dtracker.get("id"),
                "identifier": dtracker.get("identifier"),
            })
            edge_children.append(did)

    steps["children"] = child_results

    # --- blocking edges (pass two: every child linked before any edge) ---
    # A single interleaved pass silently skips an edge whose blocker comes
    # LATER in D-number order (D1 blocked_by D2 on an initial map) and then
    # records the event marker anyway - the retry dedupes instead of
    # converging. Projecting after pass one guarantees both locators exist.
    for did in edge_children:
        dloaded2 = load_subject(flow_dir, "decision", did)
        if isinstance(dloaded2, TrackerError):
            continue
        _p2, ddata2, dtr = dloaded2
        from_loc = locator_of(dtr)
        if isinstance(from_loc, TrackerError):
            continue
        desired_keys: set[str] = set()
        blockers_resolved = True
        for blocker in ddata2.get("blocked_by") or []:
            b_loaded = load_subject(flow_dir, "decision", str(blocker))
            if isinstance(b_loaded, TrackerError):
                blockers_resolved = False
                continue
            _bp, _bd, btr = b_loaded
            to_loc = locator_of(btr)
            if isinstance(to_loc, TrackerError):
                blockers_resolved = False
                continue
            key = dep_relation_key(
                str(from_loc["durable"]), str(to_loc["durable"]),
            )
            desired_keys.add(key)
            if ledger_has(dtr, key):
                continue
            rel = _project_blocking(
                config, execute,
                from_loc=from_loc, to_loc=to_loc, caps=caps,
                dep_subject=str(blocker),
            )
            if isinstance(rel, TrackerError):
                return fail_result(
                    rel, completed=completed, statuses=statuses,
                    flow_dir=flow_dir,
                    spec_id=subject_marker_token("chart", chart_id),
                    event=event, tracker_id=chart_tracker.get("id"),
                    transport=provider,
                    degraded=collect_degraded(*degraded_parts),
                )
            if isinstance(rel, dict) and rel.get("degraded"):
                degraded_parts.append(rel["degraded"])
            elif isinstance(rel, dict) and rel.get("projected"):
                completed.append(f"blocks:{did}->{blocker}")
                statuses.append("pushed")

                def _ledger(t: dict, _key=key, _blocker=blocker,
                            _from=from_loc, _to=to_loc):
                    t = ledger_append(
                        t, key=_key, dep_spec=str(_blocker),
                        from_tracker_id=str(_from["durable"]),
                        to_tracker_id=str(_to["durable"]),
                        rel_type="blocks", source="flow",
                    )
                    return ledger_finalize(t, key=_key)

                ledgered = locked_subject_write(
                    flow_dir, "decision", did, _ledger,
                )
                self_wrote.add(did)
                if isinstance(ledgered, TrackerError):
                    # The native edge landed but flow ownership did not
                    # persist. Without the ledger entry a later rewire cannot
                    # attribute (and remove) the remote edge - swallowing the
                    # failure while the event marker records success would
                    # orphan it permanently. Partial failure instead: no
                    # marker, so the retry re-asserts the relation (the
                    # provider probe reports it already present) and lands
                    # the ledger entry.
                    return fail_result(
                        ledgered, completed=completed, statuses=statuses,
                        flow_dir=flow_dir,
                        spec_id=subject_marker_token("chart", chart_id),
                        event=event, tracker_id=chart_tracker.get("id"),
                        transport=provider,
                        degraded=collect_degraded(*degraded_parts),
                    )

        # Reconcile stale flow-owned native blocking (wire-decision repoint
        # or clear): entries the ledger attributes to flow whose edge is no
        # longer in blocked_by are removed remotely, then dropped from the
        # ledger. Relations the ledger does not attribute to flow are never
        # touched. Skipped when any listed blocker failed to resolve - a
        # desired key we could not compute must not be judged stale.
        if not blockers_resolved:
            continue
        for entry in list(dtr.get("depRelations") or []):
            if not isinstance(entry, dict):
                continue
            if entry.get("source") != "flow" or entry.get("type") != "blocks":
                continue
            if entry.get("status") == "pending":
                continue
            key = entry.get("key")
            if not key or key in desired_keys:
                continue
            to_id = str(entry.get("to_tracker_id") or "")
            if not to_id:
                continue
            if str(entry.get("from_tracker_id") or "") != str(from_loc["durable"]):
                # Identity drift: never address remote relations by an old
                # (relinked-away) identity.
                continue
            rem = _remove_blocking(
                config, execute, from_loc=from_loc, to_id=to_id, caps=caps,
            )
            if isinstance(rem, TrackerError):
                return fail_result(
                    rem, completed=completed, statuses=statuses,
                    flow_dir=flow_dir,
                    spec_id=subject_marker_token("chart", chart_id),
                    event=event, tracker_id=chart_tracker.get("id"),
                    transport=provider,
                    degraded=collect_degraded(*degraded_parts),
                )
            if isinstance(rem, dict) and rem.get("degraded"):
                # Keep the ledger entry: the stale native edge remains and
                # flow still owns it.
                degraded_parts.append(rem["degraded"])
                continue
            if isinstance(rem, dict):
                if rem.get("removed"):
                    completed.append(f"unblock:{did}-x>{entry.get('dep_spec')}")
                    statuses.append("pushed")

                def _drop(t: dict, _key=key):
                    return ledger_drop(t, key=_key)

                dropped = locked_subject_write(flow_dir, "decision", did, _drop)
                self_wrote.add(did)
                if isinstance(dropped, TrackerError):
                    # The native edge is gone but the ledger entry survived.
                    # Recording success would freeze the stale entry: a later
                    # re-add of the same edge is suppressed by ledger_has and
                    # never re-created remotely. Partial failure instead: no
                    # marker, so the retry re-runs removal (the provider
                    # reports already_absent) and lands the ledger drop.
                    return fail_result(
                        dropped, completed=completed, statuses=statuses,
                        flow_dir=flow_dir,
                        spec_id=subject_marker_token("chart", chart_id),
                        event=event, tracker_id=chart_tracker.get("id"),
                        transport=provider,
                        degraded=collect_degraded(*degraded_parts),
                    )

    # --- parent rollup refresh ---
    # Claim/release may refresh owned block/counts but never masquerade as
    # provider workflow status.
    parent_current = _wire_read(config, execute, parent_loc)
    if isinstance(parent_current, TrackerError):
        # Never rebuild the parent body from an unread remote state.
        return fail_result(
            parent_current, completed=completed, statuses=statuses,
            flow_dir=flow_dir,
            spec_id=subject_marker_token("chart", chart_id),
            event=event, tracker_id=chart_tracker.get("id"),
            transport=provider,
            degraded=collect_degraded(*degraded_parts),
        )
    parent_cur_body = ""
    if isinstance(parent_current, dict):
        parent_cur_body = parent_current.get("body") or ""
    parent_new_body = _upsert_owned_block(
        parent_cur_body, CHART_ROLLUP_OPEN, CHART_ROLLUP_CLOSE, parent_body,
    )
    # Skip status/workflow transitions for claim/release events.
    parent_upd = _wire_update(
        config, execute, parent_loc, title=parent_title, body=parent_new_body,
    )
    if isinstance(parent_upd, TrackerError):
        return fail_result(
            parent_upd, completed=completed, statuses=statuses,
            flow_dir=flow_dir,
            spec_id=subject_marker_token("chart", chart_id),
            event=event, tracker_id=chart_tracker.get("id"),
            transport=provider,
            degraded=collect_degraded(*degraded_parts),
        )
    completed.append("parent-rollup")
    statuses.append("updated")
    steps["parent_rollup"] = {"kind": "updated"}

    degraded = collect_degraded(*degraded_parts)
    receipt_status = (
        "pushed" if any(s in ("pushed", "updated") for s in statuses) else "noop"
    )
    # Worst-status ranking via helpers
    from .helpers import worst_status  # noqa: PLC0415

    receipt_status = worst_status(statuses) if statuses else "noop"

    # Projection-side sidecar writes (link adoption, ledger entries) bump the
    # decision sidecars' updated_at AFTER the entry digest was computed. Key
    # the success marker on the post-projection state instead: an identical
    # retry (same sidecar bytes) recomputes the same key and dedupes, while
    # any committed mutation since - including one returning the graph to a
    # prior state - mints a fresh marker.
    # ONLY this holder's own writes may be absorbed that way. A foreign chart
    # mutation committed during the remote span must not be folded into the
    # marker: the pushed remote content predates it, so absorbing it would
    # make that mutation's own projection (or any retry) dedupe against
    # content that was never pushed - the tracker stays stale indefinitely.
    # On foreign change the marker stays keyed on the state actually
    # projected, and stale_revision names the remaining state so
    # project_chart's drain loop re-projects it before releasing the lock.
    stale_revision = None
    end_bundle = _load_chart_bundle(flow_dir, chart_id)
    if not isinstance(end_bundle, TrackerError):
        _ep, end_chart, _et, end_decisions = end_bundle
        start_by_id = {
            str(e.get("id")): e for e in _digest_entries(decisions)
        }
        end_by_id = {
            str(e.get("id")): e for e in _digest_entries(end_decisions)
        }
        foreign = (
            _chart_base_revision(end_chart, end_decisions) != start_skeleton
            or set(end_by_id) != set(start_by_id)
            or any(
                did not in self_wrote and entry != start_by_id[did]
                for did, entry in end_by_id.items()
            )
        )
        if foreign:
            stale_revision = _sha(
                f"{supplied_revision or _chart_base_revision(end_chart, end_decisions)}"
                f"\x00{_mutation_state_digest(end_chart, end_decisions)}"
            )
        else:
            revision = _sha(
                f"{base_revision}"
                f"\x00{_mutation_state_digest(end_chart, end_decisions)}"
            )
            if not evidence_supplied:
                evidence = revision[:16]

    def _mark(t: dict):
        t = _append_event_marker(
            t, event=event, revision=revision, evidence=evidence,
            completed_steps=completed, status=receipt_status,
        )
        if degraded is not None:
            proj = dict_(t.get("projection"))
            proj["degraded"] = degraded
            t = dict(t)
            t["projection"] = proj
        return t

    marked = locked_subject_write(flow_dir, "chart", chart_id, _mark)
    if isinstance(marked, TrackerError):
        # Remote work done; still try aggregate receipt with completed steps.
        rerr = write_aggregate_receipt(
            flow_dir,
            spec_id=subject_marker_token("chart", chart_id),
            event=event,
            status=receipt_status,
            tracker_id=chart_tracker.get("id"),
            transport=provider,
            degraded=degraded,
            note=f"chart projection partial marker-fail ({', '.join(completed)})",
            details={"completed_steps": completed, "marker_error": marked.message},
        )
        return fail_result(
            marked, completed=completed, statuses=statuses,
            flow_dir=flow_dir,
            spec_id=subject_marker_token("chart", chart_id),
            event=event, tracker_id=chart_tracker.get("id"),
            transport=provider, degraded=degraded,
        )

    rerr = write_aggregate_receipt(
        flow_dir,
        spec_id=subject_marker_token("chart", chart_id),
        event=event,
        status=receipt_status,
        tracker_id=(marked.get("id") if isinstance(marked, dict) else None),
        transport=provider,
        degraded=degraded,
        note=f"chart projection ({', '.join(completed)})",
        details={"revision": revision, "evidence": evidence},
    )
    if rerr:
        return fail_result(
            rerr, completed=completed, statuses=statuses,
            flow_dir=flow_dir,
            spec_id=subject_marker_token("chart", chart_id),
            event=event,
            tracker_id=marked.get("id") if isinstance(marked, dict) else None,
            transport=provider, degraded=degraded,
        )

    data = {
        "op": "chart_project",
        "projected": True,
        "chart_id": chart_id,
        "event": event,
        "revision": revision,
        "steps": steps,
        "tracker_id": marked.get("id") if isinstance(marked, dict) else None,
    }
    if stale_revision is not None:
        data["stale_revision"] = stale_revision
    return ok_result(data, statuses=statuses, completed=completed,
                     degraded=degraded)


# ---------------------------------------------------------------------------
# Locator / URL re-entry (strictly local)
# ---------------------------------------------------------------------------

def _normalize_url(raw: str) -> Optional[str]:
    """Normalize scheme/host case; strip provider-approved cosmetic suffixes.

    Rejects credential-bearing URLs. Returns None when unusable.
    """
    text = (raw or "").strip()
    if not text:
        return None
    # Bare identifiers are not URLs.
    if "://" not in text and not text.startswith("//"):
        return None
    if "://" not in text:
        text = "https:" + text
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.scheme and parsed.scheme.lower() not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    path = unquote(parsed.path or "")
    # Provider-approved cosmetic suffixes: trailing slash, .html
    while path.endswith("/"):
        path = path[:-1]
    if path.endswith(".html"):
        path = path[:-5]
    # Drop fragments and query for ledger match (cosmetic).
    return f"https://{host}{path}"


def _configured_hosts(config: dict, provider: Optional[str]) -> set[str]:
    hosts: set[str] = set()
    if provider in _DEFAULT_HOSTS:
        hosts.update(_DEFAULT_HOSTS[provider])
    per = dict_(dict_(config.get("tracker")).get("perTracker"))
    for key in ("host", "baseUrl"):
        raw = per.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                p = urlparse(raw if "://" in raw else f"https://{raw}")
                if p.hostname:
                    hosts.add(p.hostname.lower())
            except ValueError:
                continue
    # Also accept resolved destination hosts.
    dest = dict_(dict_(dict_(config.get("tracker")).get("resolved")).get("destination"))
    for key in ("host", "baseUrl"):
        raw = dest.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                p = urlparse(raw if "://" in raw else f"https://{raw}")
                if p.hostname:
                    hosts.add(p.hostname.lower())
            except ValueError:
                continue
    return hosts


def _host_allowed(url: str, config: dict) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    provider = tracker_type(config)
    allowed = _configured_hosts(config, provider)
    if not allowed:
        # No tracker configured: still allow known public hosts for local ledger
        # matches (host check is secondary to ledger membership).
        allowed = set()
        for hs in _DEFAULT_HOSTS.values():
            allowed.update(hs)
    return host in allowed


def _ledger_entries(flow_dir: Path) -> list[dict]:
    """Build local provenance ledger rows from chart/decision tracker blocks."""
    from ..subjects import iter_all_subject_trackers  # noqa: PLC0415

    rows = []
    for kind, sid, tracker in iter_all_subject_trackers(flow_dir):
        if kind == "spec":
            continue
        if not isinstance(tracker, dict):
            continue
        durable = tracker.get("id")
        ident = tracker.get("identifier")
        url = tracker.get("url")
        if not durable and not ident and not url:
            continue
        rows.append({
            "kind": kind,
            "subject_id": sid,
            "id": durable,
            "identifier": ident,
            "url": url,
            "normalized_url": _normalize_url(str(url)) if url else None,
            "linkState": tracker.get("linkState"),
        })
    return rows


def locate_selector(flow_dir: Path, selector: str, *, config: Optional[dict] = None
                    ) -> Result:
    """Resolve chart/D-ID, stored identifier, or stored URL via local ledger only.

    Zero mutation. No network. Structured failures for unsafe/unknown cases.
    """
    flow_dir = Path(flow_dir)
    config = config if config is not None else read_config(flow_dir)
    sel = (selector or "").strip()
    if not sel:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "selector required",
            subtype="selector",
            details={"code": "unresolved_locator"},
        )

    # Credential-bearing URL rejection before any ledger work.
    if "://" in sel or sel.startswith("//"):
        try:
            parsed = urlparse(sel if "://" in sel else "https:" + sel)
        except ValueError:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                "malformed selector URL",
                subtype="selector",
                details={"code": "unresolved_locator"},
            )
        if parsed.username or parsed.password:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                "credential-bearing URLs are rejected",
                subtype="credentials",
                details={"code": "unresolved_locator"},
            )

    # Canonical chart / decision ids resolve without ledger.
    if re.fullmatch(r"fn-\d+", sel, re.I):
        loaded = load_subject(flow_dir, "chart", sel.lower())
        if isinstance(loaded, TrackerError):
            return TrackerError(
                ErrorClass.NOT_FOUND,
                f"chart {sel!r} not found",
                subtype="chart",
                details={"code": "unresolved_locator"},
            )
        _p, chart, _t = loaded
        return {
            "kind": "chart",
            "chart_id": chart.get("id"),
            "title": chart.get("title"),
            "status": chart.get("status"),
            "record_path": f".flow/charts/{chart.get('id')}.md",
            "decision_id": None,
            "history": None,
        }

    dparse = parse_decision_id(sel)
    if dparse:
        chart_id, n = dparse
        did = f"{chart_id}.D{n}"
        loaded = load_subject(flow_dir, "decision", did)
        if isinstance(loaded, TrackerError):
            return TrackerError(
                ErrorClass.NOT_FOUND,
                f"decision {did!r} not found",
                subtype="decision",
                details={"code": "unresolved_locator"},
            )
        _p, dec, _t = loaded
        return _decision_locate_result(flow_dir, dec)

    rows = _ledger_entries(flow_dir)
    if not rows:
        return TrackerError(
            ErrorClass.UNRESOLVED,
            "no stored tracker locators in chart ledger",
            subtype="locator",
            details={"code": "unresolved_locator"},
        )

    matches: list[dict] = []
    norm_url = _normalize_url(sel)
    for row in rows:
        if row.get("id") and str(row["id"]) == sel:
            matches.append(row)
            continue
        if row.get("identifier") and str(row["identifier"]) == sel:
            matches.append(row)
            continue
        if norm_url and row.get("normalized_url") == norm_url:
            matches.append(row)
            continue
        # Identifier case-fold for display keys like WOR-17
        if row.get("identifier") and str(row["identifier"]).casefold() == sel.casefold():
            matches.append(row)

    if norm_url and not _host_allowed(norm_url, config):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "URL host/project is not the configured tracker host",
            subtype="wrong_host",
            details={"code": "unresolved_locator", "url": norm_url},
        )

    # Dedup matches by subject
    uniq: dict[tuple, dict] = {}
    for m in matches:
        uniq[(m["kind"], m["subject_id"])] = m
    matches = list(uniq.values())

    if not matches:
        return TrackerError(
            ErrorClass.UNRESOLVED,
            "selector not found in local chart provenance ledger",
            subtype="locator",
            details={"code": "unresolved_locator"},
        )
    if len(matches) > 1:
        return TrackerError(
            ErrorClass.CONFLICT,
            "selector matches multiple chart/decision locators",
            subtype="ambiguous",
            details={
                "code": "unresolved_locator",
                "matches": [
                    {"kind": m["kind"], "subject_id": m["subject_id"]}
                    for m in matches
                ],
            },
        )

    row = matches[0]
    # Stale parent: durable id present but linkState not linked / missing parent chart
    if row.get("linkState") == "identifier_only":
        return TrackerError(
            ErrorClass.STALE_ID,
            "stored locator is identifier-only (stale/incomplete link)",
            subtype="stale_id",
            details={"code": "stale_id", "subject_id": row["subject_id"]},
        )

    if row["kind"] == "chart":
        loaded = load_subject(flow_dir, "chart", row["subject_id"])
        if isinstance(loaded, TrackerError):
            return TrackerError(
                ErrorClass.STALE_ID,
                "chart parent for stored locator is missing",
                subtype="stale_parent",
                details={"code": "stale_id", "subject_id": row["subject_id"]},
            )
        _p, chart, _t = loaded
        return {
            "kind": "chart",
            "chart_id": chart.get("id"),
            "title": chart.get("title"),
            "status": chart.get("status"),
            "record_path": f".flow/charts/{chart.get('id')}.md",
            "decision_id": None,
            "history": None,
            "locator": {
                "id": row.get("id"),
                "identifier": row.get("identifier"),
                "url": row.get("url"),
            },
        }

    # decision
    loaded = load_subject(flow_dir, "decision", row["subject_id"])
    if isinstance(loaded, TrackerError):
        return TrackerError(
            ErrorClass.STALE_ID,
            "decision for stored locator is missing",
            subtype="stale_id",
            details={"code": "stale_id", "subject_id": row["subject_id"]},
        )
    _p, dec, _t = loaded
    result = _decision_locate_result(flow_dir, dec)
    if isinstance(result, dict):
        result["locator"] = {
            "id": row.get("id"),
            "identifier": row.get("identifier"),
            "url": row.get("url"),
        }
    return result


def _decision_locate_result(flow_dir: Path, dec: dict) -> Result:
    did = dec.get("id")
    chart_id = dec.get("chart")
    status = dec.get("status") or "open"
    record = dec.get("record_path") or (
        f".flow/charts/{chart_id}/{dec.get('n')}.md" if chart_id else None
    )
    base = {
        "kind": "decision",
        "chart_id": chart_id,
        "decision_id": did,
        "title": dec.get("title"),
        "status": status,
        "record_path": record,
        "history": None,
        "replacement": None,
        "frontier": None,
    }
    if status in ("resolved", "superseded", "out-of-scope"):
        # Historical: never silently select replacement work.
        replacement = dec.get("superseded_by")
        frontier = None
        if chart_id:
            cl = load_subject(flow_dir, "chart", chart_id)
            if not isinstance(cl, TrackerError):
                _cp, chart, _ct = cl
                # Compact frontier from chart decisions list, using the same
                # actionable predicate as the canonical frontier computation:
                # open AND unblocked AND unclaimed (blocked decisions are not
                # selectable frontier options).
                compact = [
                    d for d in (chart.get("decisions") or [])
                    if isinstance(d, dict)
                ]
                frontier = _count_decisions(chart, compact)["frontier"]
        base["history"] = {
            "status": status,
            "gist": _safe_gist(dec.get("answer")),
            "superseded_by": replacement,
        }
        base["replacement"] = replacement
        base["frontier"] = frontier
    return base
