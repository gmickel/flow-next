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

from pathlib import Path
from typing import Callable, Optional, Union

from . import envelope
from .executor import execute as default_execute
from .providers import resolver_for
from .resolved_cache import SCOPES, resolve_transaction
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


def _tracker_type(config: dict) -> Optional[str]:
    t = (config.get("tracker") or {}).get("type")
    return t if t in _ACTIVE_TYPES else None


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

    for s in scopes:
        current = _read_raw(flow_dir)
        already = (((current.get("tracker") or {}).get("resolved") or {})
                   .get("scopeResolvedAt") or {})
        if s in already and not refresh and scope is None:
            continue  # backfill touches only what is absent; --refresh forces

        def network_fn(cfg: dict, _s: str = s) -> Union[dict, TrackerError]:
            if _s == "destination":
                return mod.resolve_destination(cfg, execute)
            if _s in ("destination.stateIds", "destination.statusIds"):
                out = _ids_resolver(mod, provider)(cfg, execute)
                if isinstance(out, TrackerError):
                    return out
                warnings.extend(out.warnings)
                aliases.update(out.aliases)
                return _assignment_to_data(out)
            return mod.resolve_capabilities(cfg, execute)

        result = resolve_transaction(flow_dir, s, network_fn)
        if isinstance(result, TrackerError):
            return envelope.failure(result)

    final = _read_raw(flow_dir)
    resolved = (final.get("tracker") or {}).get("resolved") or {}
    data = {"resolved": resolved, "warnings": warnings, "aliases": aliases}
    return envelope.success(data)


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

    fetched = _fetch_pools(mod, provider, config, execute)
    if isinstance(fetched, TrackerError):
        return envelope.failure(fetched)
    pools, live = fetched
    error = validate_select(slot, chosen, pools, live)
    if error:
        return envelope.failure(TrackerError(
            ErrorClass.INVALID_INPUT, error, subtype="select"))

    ids_scope = _IDS_SCOPE[provider]
    key = ids_scope.split(".", 1)[1]

    def network_fn(cfg: dict) -> dict:
        return {slot: chosen}

    def finalize_fn(current_cfg: dict, data: dict) -> dict:
        # Merge INSIDE the lock so a concurrent select of another slot is not
        # clobbered by a whole-map replace computed from a stale read.
        existing = ((((current_cfg.get("tracker") or {}).get("resolved") or {})
                     .get("destination") or {}).get(key)) or {}
        return {**(existing if isinstance(existing, dict) else {}), **data}

    result = resolve_transaction(flow_dir, ids_scope, network_fn,
                                 finalize_fn=finalize_fn)
    if isinstance(result, TrackerError):
        return envelope.failure(result)
    aliased = is_alias(slot, chosen, pools)
    final_map = (((result.get("tracker") or {}).get("resolved") or {})
                 .get("destination") or {}).get(key) or {}
    return envelope.success({
        "selected": {slot: chosen},
        "alias": aliased,
        key: final_map,
        "warnings": ([f"{slot!r} aliases a state outside its natural candidates "
                      f"(recorded, not silent)"] if aliased else []),
    })
