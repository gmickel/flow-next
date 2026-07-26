"""GitLab resolution + the tier probe (fn-139.4).

Destination pins the **numeric** `projectId` (API paths take the id and the
path changes on rename), `projectPath`, `host`, and **`namespaceId`** - the
tier probe is `GET /namespaces/:id`, so pinning the namespace id keeps the TTL
re-probe at exactly ONE request instead of paying a project lookup first.

`blockedBy` is plan-dependent and **trials are GROUP-scoped** (measured both
ways): a personal-namespace project stays Free even while the same user's
group is on Ultimate, which is exactly the misleading case that produced the
earlier "blocked issues unavailable" misdiagnosis.
"""

from __future__ import annotations

import json
from typing import Callable, Optional, Union
from urllib.parse import quote

from ..resolved_cache import STATIC_CAPABILITIES, apply_capability_probe
from ..types import ErrorClass, Request, Response, TrackerError

#: Plans that unlock `is_blocked_by` (Free degrades to `relates_to` in B).
BLOCKEDBY_PLANS = frozenset({
    "premium", "premium_trial", "ultimate", "ultimate_trial", "gold", "silver",
})


def _json_body(resp: Response) -> Union[dict, TrackerError]:
    try:
        data = json.loads(resp.body or b"{}")
    except (ValueError, TypeError) as exc:
        return TrackerError(ErrorClass.TRANSPORT, f"malformed glab output: {exc}",
                            subtype="malformed_body")
    if not isinstance(data, dict):
        return TrackerError(ErrorClass.TRANSPORT, "glab output is not an object",
                            subtype="malformed_body")
    return data


def _argv(config: dict, endpoint: str) -> list[str]:
    host = ((config.get("tracker") or {}).get("perTracker") or {}).get("host")
    argv = ["glab", "api", endpoint]
    if host:
        argv += ["--hostname", str(host)]
    return argv


def resolve_destination(config: dict, execute: Callable) -> Union[dict, TrackerError]:
    """`GET /projects/:url-encoded-path` -> numeric id, path, host, namespaceId."""
    per = (config.get("tracker") or {}).get("perTracker") or {}
    path = per.get("project")
    if not path:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "tracker.perTracker.project is not set; run the "
                            "discovery ceremony first", subtype="destination")
    result = execute(Request(
        provider="gitlab", op="resolve-destination", method="GET",
        url_or_argv=_argv(config, f"projects/{quote(str(path), safe='')}"),
        idempotent=True,
    ))
    if isinstance(result, TrackerError):
        return result
    data = _json_body(result)
    if isinstance(data, TrackerError):
        return data
    project_id = data.get("id")
    namespace_id = (data.get("namespace") or {}).get("id")
    if not isinstance(project_id, int) or not isinstance(namespace_id, int):
        return TrackerError(ErrorClass.UNRESOLVED,
                            "gitlab project lookup returned no numeric "
                            "id/namespace id", subtype="destination")
    return {
        "projectId": project_id,
        "projectPath": data.get("path_with_namespace") or str(path),
        "host": per.get("host") or "gitlab.com",
        "namespaceId": namespace_id,
    }


def probe_plan(config: dict, execute: Callable,
               namespace_id: Optional[int] = None) -> tuple[bool, Optional[str], Optional[str]]:
    """ONE request: `GET /namespaces/:id` -> plan. Returns (ok, plan, reason).

    The namespace id comes from the PINNED destination unless the caller (a
    fresh backfill that just resolved it) passes it directly - either way the
    TTL re-probe never pays a project lookup.
    """
    if namespace_id is None:
        resolved = ((config.get("tracker") or {}).get("resolved") or {})
        namespace_id = (resolved.get("destination") or {}).get("namespaceId")
    if not isinstance(namespace_id, int):
        return False, None, "no pinned namespaceId; resolve destination first"
    result = execute(Request(
        provider="gitlab", op="probe-plan", method="GET",
        url_or_argv=_argv(config, f"namespaces/{namespace_id}"),
        idempotent=True,
    ))
    if isinstance(result, TrackerError):
        # A transient failure (403 included) is a FAILED PROBE, never a
        # capability change - the caller reports it via `probe`.
        return False, None, f"{result.cls.value}: {result.message}"
    data = _json_body(result)
    if isinstance(data, TrackerError):
        return False, None, data.message
    plan = data.get("plan")
    return True, (str(plan) if plan is not None else None), None


def resolve_capabilities(config: dict, execute: Callable,
                         namespace_id: Optional[int] = None) -> Union[dict, TrackerError]:
    """Static rows + the plan-dependent `blockedBy`, from one tier probe.

    Unlike a TTL re-probe (best-effort, prior value kept), a fresh CAPABILITY
    RESOLUTION has no prior value to keep - a failed probe here is a failed
    resolve, not a silent `blockedBy: false` (that would be exactly the false
    `false` the absent-block rule forbids).
    """
    ok, plan, reason = probe_plan(config, execute, namespace_id=namespace_id)
    if not ok:
        return TrackerError(ErrorClass.UNRESOLVED,
                            f"gitlab tier probe failed: {reason}",
                            subtype="capabilities")
    caps = dict(STATIC_CAPABILITIES["gitlab"])
    caps["blockedBy"] = (plan or "").lower() in BLOCKEDBY_PLANS
    caps["_source"] = {"gitlabPlan": plan}
    return caps


def ttl_reprobe(config: dict, execute: Callable, *, now: Optional[str] = None) -> dict:
    """Synchronous, bounded TTL re-probe - one request, then fold the outcome
    through `apply_capability_probe` (failed probe -> prior capability kept,
    reported via `probe`, never `degraded`)."""
    ok, plan, reason = probe_plan(config, execute)
    return apply_capability_probe(config, ok=ok, plan=plan, reason=reason, now=now)
