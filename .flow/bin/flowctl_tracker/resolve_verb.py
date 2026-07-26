"""`flowctl tracker resolve` orchestration (fn-139.6, R9/R11/R12).

The EXPLICIT backfill: `resolve` populates an absent `tracker.resolved` block
(destination + ids scope + capabilities per provider). This is deliberately
distinct from a consuming verb meeting an absent block - that returns
`class: unresolved` and never resolves implicitly mid-operation.

`--scope` re-resolves only the named nested path (its own timestamp).
`--refresh` forces re-resolution of already-fresh scopes.
`--select slot=id` persists ONE human tiebreak, validated against live
candidates; repeatable; re-select overwrites.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional, Union

from . import envelope
from .credentials import redact
from .executor import execute as default_execute
from .providers import resolver_for
from .resolved_cache import (SCOPES, apply_capability_probe, capabilities_stale,
                             resolve_transaction)
from .states import Assignment, is_alias, validate_select
from .types import ErrorClass, TrackerError

#: Scopes each provider resolves, in dependency order (destination first: the
#: ids scopes and the GitLab tier probe consume pinned destination fields).
SCOPES_BY_PROVIDER = {
    "github": ("destination", "capabilities"),
    "gitlab": ("destination", "capabilities"),
    "linear": ("destination", "destination.stateIds", "capabilities"),
    "jira": ("destination", "destination.statusIds", "capabilities"),
}

_IDS_SCOPE = {"linear": "destination.stateIds", "jira": "destination.statusIds"}

_ACTIVE_TYPES = {"github", "gitlab", "linear", "jira"}


def _dict(value) -> dict:
    """Malformed-but-valid config shapes must produce the JSON error envelope,
    never an AttributeError - `{"tracker": "bad"}` is a thing users write."""
    return value if isinstance(value, dict) else {}


def _tracker_type(config: dict) -> Optional[str]:
    t = _dict(config.get("tracker")).get("type")
    return t if t in _ACTIVE_TYPES else None


def _stderr_sink(message: str) -> None:
    """R-observability: every attempt/backoff/scope/downgrade/probe event lands
    on stderr, redacted. stdout stays reserved for the single JSON envelope."""
    print(redact(str(message)), file=sys.stderr)


def _float_or_none(value, lo: float, hi: float) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if lo < f <= hi else None


def bound_executor(config: dict, execute: Callable,
                   on_event: Callable[[str], None] = _stderr_sink) -> Callable:
    """Bind the PERSISTED transport policy onto the raw executor.

    This is the wiring the completion review caught missing: `authScheme`
    decided at the discovery ceremony, `sslVerify` (+ `JIRA_SSL_VERIFY` env
    override), the stderr event sink, and the R7 config-overridable bounds
    (`tracker.transport.timeoutS/maxRetries/backoffCapS/concurrency`) - none
    of which reached a real request when adapters called `execute` bare.
    """
    tracker = _dict(config.get("tracker"))
    per = _dict(tracker.get("perTracker"))
    transport = _dict(tracker.get("transport"))

    auth_scheme = per.get("authScheme")
    verify_tls = per.get("sslVerify")
    verify_tls = True if verify_tls is None else bool(verify_tls)
    env_ssl = os.environ.get("JIRA_SSL_VERIFY")
    if tracker.get("type") == "jira" and env_ssl is not None:
        verify_tls = env_ssl.strip().lower() not in ("false", "0", "no")

    timeout_s = _float_or_none(transport.get("timeoutS"), 0, 600)
    backoff_cap = _float_or_none(transport.get("backoffCapS"), 0, 300)
    retries = transport.get("maxRetries")
    retries = retries if isinstance(retries, int) and 0 <= retries <= 5 else None
    concurrency = transport.get("concurrency")
    concurrency = (concurrency if isinstance(concurrency, int)
                   and 1 <= concurrency <= 16 else None)

    if execute is not default_execute:
        # Injected fake (tests): policy kwargs would explode a plain callable.
        return execute

    def bound(request):
        if timeout_s is not None and request.timeout_s == type(request).__dataclass_fields__["timeout_s"].default:
            import dataclasses
            request = dataclasses.replace(request, timeout_s=timeout_s)
        return default_execute(request, auth_scheme=auth_scheme,
                               verify_tls=verify_tls, on_event=on_event,
                               max_retries=retries, backoff_cap_s=backoff_cap,
                               concurrency=concurrency)
    return bound


def _config_shape_error(config: dict) -> Optional[TrackerError]:
    tracker = config.get("tracker")
    if tracker is not None and not isinstance(tracker, dict):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"tracker config is {type(tracker).__name__}, not an "
                            "object", subtype="config")
    per = _dict(tracker).get("perTracker")
    if per is not None and not isinstance(per, dict):
        return TrackerError(ErrorClass.INVALID_INPUT,
                            f"tracker.perTracker is {type(per).__name__}, not an "
                            "object", subtype="config")
    return None


def _read_raw(flow_dir: Path) -> dict:
    import json
    try:
        data = json.loads((Path(flow_dir) / "config.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _assignment_to_data(assignment: Assignment) -> Union[dict, TrackerError]:
    if assignment.conflict is not None:
        return TrackerError(
            ErrorClass.CONFLICT,
            f"slot {assignment.conflict['normalized']!r} is ambiguous; pick one "
            "with `flowctl tracker resolve --select <slot>=<id>`",
            subtype="ambiguous_slot", details=assignment.conflict)
    if assignment.missing_required:
        slot = assignment.missing_required[0]
        return TrackerError(
            ErrorClass.CONFLICT,
            f"required slot {slot!r} has no live candidate in this workflow; "
            "alias it explicitly with `--select {slot}=<id>`".format(slot=slot),
            subtype="missing_slot",
            details={"normalized": slot, "candidates": []})
    return dict(assignment.mapping)


def _ids_resolver(provider_mod, provider: str) -> Callable:
    return (provider_mod.resolve_state_ids if provider == "linear"
            else provider_mod.resolve_status_ids)


def _fetch_pools(provider_mod, provider: str, config: dict, execute: Callable):
    return (provider_mod.fetch_states(config, execute) if provider == "linear"
            else provider_mod.fetch_statuses(config, execute))


def run(flow_dir: Path, *, scope: Optional[str] = None, refresh: bool = False,
        select: Optional[str] = None,
        execute: Callable = default_execute) -> tuple[str, int]:
    """Returns (stdout payload, exit code) - the single result envelope."""
    config = _read_raw(flow_dir)
    shape_error = _config_shape_error(config)
    if shape_error is not None:
        return envelope.failure(shape_error)
    provider = _tracker_type(config)
    if provider is None:
        return envelope.inactive()
    try:
        mod = resolver_for(provider)
    except KeyError as exc:
        return envelope.failure(TrackerError(ErrorClass.INVALID_INPUT, str(exc),
                                             subtype="provider"))

    warnings: list = []
    aliases: dict = {}

    if select is not None:
        return _run_select(flow_dir, config, mod, provider, select, execute)

    if scope is not None:
        if scope not in SCOPES:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT,
                f"unknown scope {scope!r}; canonical scopes are {SCOPES}",
                subtype="scope"))
        if scope not in SCOPES_BY_PROVIDER[provider]:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT,
                f"scope {scope!r} does not apply to provider {provider!r}",
                subtype="scope"))
        scopes = (scope,)
    else:
        scopes = SCOPES_BY_PROVIDER[provider]

    probe_field = None
    degraded_field = None
    for s in scopes:
        current = _read_raw(flow_dir)
        already = _dict(_dict(_dict(_dict(current.get("tracker"))
                                    .get("resolved")).get("scopeResolvedAt")))
        if s in already and not refresh and scope is None:
            # Backfill touches only what is absent - EXCEPT the one dynamic
            # capability: GitLab's plan-gated blockedBy re-probes when its
            # scope timestamp is older than the TTL (24h). This is the wiring
            # that makes `capabilities_stale` reachable in production.
            if (s == "capabilities" and provider == "gitlab"
                    and capabilities_stale(current)):
                _stderr_sink(f"scope={s} provider={provider} ttl-reprobe")
                outcome = _ttl_reprobe(flow_dir, current, mod, execute)
                if isinstance(outcome, TrackerError):
                    return envelope.failure(outcome)
                probe_field, degraded_field = outcome
            continue

        _stderr_sink(f"scope={s} provider={provider} resolving")

        def network_fn(cfg: dict, _s: str = s) -> Union[dict, TrackerError]:
            ex = bound_executor(cfg, execute)
            if _s == "destination":
                return mod.resolve_destination(cfg, ex)
            if _s in ("destination.stateIds", "destination.statusIds"):
                out = _ids_resolver(mod, provider)(cfg, ex)
                if isinstance(out, TrackerError):
                    return out
                warnings.extend(out.warnings)
                aliases.update(out.aliases)
                return _assignment_to_data(out)
            return mod.resolve_capabilities(cfg, ex)

        result = resolve_transaction(flow_dir, s, network_fn)
        if isinstance(result, TrackerError):
            return envelope.failure(result)

    final = _read_raw(flow_dir)
    resolved = _dict(_dict(final.get("tracker")).get("resolved"))
    data = {"resolved": resolved, "warnings": warnings, "aliases": aliases}
    return envelope.success(data, degraded=degraded_field, probe=probe_field)


_PROBE_FAILED = "ttl_probe_failed_keep_prior"


def _ttl_reprobe(flow_dir: Path, config: dict, mod, execute: Callable):
    """One synchronous, bounded re-probe; a FAILED probe keeps the prior value
    and reports via `probe`, never `degraded`. Returns (probe, degraded).

    The probe runs INSIDE the transaction's `network_fn`, so the R8 discovery
    fingerprint covers the exact config it queried: probing before the
    transaction let a mid-probe repoint commit project A's plan under
    project B (reproduced by the completion review).
    """
    outcome_box = {}

    def network_fn(cfg: dict):
        ex = bound_executor(cfg, execute)
        ok, plan, reason = mod.probe_plan(cfg, ex)
        staged = {"tracker": {"type": "gitlab",
                              "resolved": _dict(_dict(cfg.get("tracker"))
                                                .get("resolved"))}}
        outcome_box.clear()
        outcome_box.update(apply_capability_probe(staged, ok=ok, plan=plan,
                                                  reason=reason))
        if not ok:
            _stderr_sink(f"probe scope=capabilities ok=false reason={reason}")
            # No write on a failed probe - but not a failed COMMAND either.
            # The sentinel aborts the transaction; the caller maps it back to
            # success-with-probe-field.
            return TrackerError(ErrorClass.TRANSPORT, "ttl probe failed",
                                subtype=_PROBE_FAILED)
        return _dict(_dict(staged["tracker"]["resolved"]).get("capabilities"))

    result = resolve_transaction(flow_dir, "capabilities", network_fn)
    if isinstance(result, TrackerError):
        if result.subtype == _PROBE_FAILED:
            return outcome_box.get("probe"), None
        return result
    if outcome_box.get("degraded"):
        _stderr_sink(f"capability degraded: {outcome_box['degraded']}")
    return outcome_box.get("probe"), outcome_box.get("degraded")


def _run_select(flow_dir: Path, config: dict, mod, provider: str,
                select: str, execute: Callable) -> tuple[str, int]:
    if provider not in _IDS_SCOPE:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT,
            f"--select applies to linear/jira slot resolution, not {provider!r}",
            subtype="select"))
    if "=" not in select:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT,
            "--select takes <normalized>=<id> (exactly one slot per call)",
            subtype="select"))
    slot, chosen = select.split("=", 1)
    slot, chosen = slot.strip(), chosen.strip()

    ids_scope = _IDS_SCOPE[provider]
    key = ids_scope.split(".", 1)[1]
    seen = {}  # pools captured by network_fn for the alias verdict

    def network_fn(cfg: dict) -> object:
        # Fetch + validate INSIDE the transaction's network step, against the
        # config the transaction fingerprints: fetching before the transaction
        # let a concurrent destination repoint slip between validation and the
        # merge - team A's state id written into team B's config.
        fetched = _fetch_pools(mod, provider, cfg, bound_executor(cfg, execute))
        if isinstance(fetched, TrackerError):
            return fetched
        pools, live = fetched
        error = validate_select(slot, chosen, pools, live)
        if error:
            return TrackerError(ErrorClass.INVALID_INPUT, error, subtype="select")
        seen["pools"] = pools
        return {slot: chosen}

    def finalize_fn(current_cfg: dict, data: dict) -> dict:
        # Merge INSIDE the lock so a concurrent select of another slot is not
        # clobbered by a whole-map replace computed from a stale read.
        existing = _dict(_dict(_dict(_dict(current_cfg.get("tracker"))
                                     .get("resolved")).get("destination")).get(key))
        return {**existing, **data}

    result = resolve_transaction(flow_dir, ids_scope, network_fn,
                                 finalize_fn=finalize_fn)
    if isinstance(result, TrackerError):
        return envelope.failure(result)
    aliased = is_alias(slot, chosen, seen.get("pools", {}))
    final_map = _dict(_dict(_dict(_dict(result.get("tracker"))
                                 .get("resolved")).get("destination")).get(key))
    return envelope.success({
        "selected": {slot: chosen},
        "alias": aliased,
        key: final_map,
        "warnings": ([f"{slot!r} aliases a state outside its natural candidates "
                      f"(recorded, not silent)"] if aliased else []),
    })
