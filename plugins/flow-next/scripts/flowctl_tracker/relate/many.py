"""Batch dependency projection: parallel read probes, serialized mutations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..lifecycle.helpers import Execute, load_spec, merged_tracker, read_config, tracker_type
from ..lifecycle.verbs import _claim_body_mutation, _release_claim
from ..resolve_verb import bound_executor
from ..types import CONCURRENCY_CAP, TrackerError
from . import _claim_relate_pair, _locator, _relate_txn
from . import providers as P


def relate_many(flow_dir: Path, spec_id: str, dependencies: list[str], *,
                event: str, execute: Execute) -> list:
    """Parallel read probes under pair claims; ordered, serialized mutations."""
    if not dependencies:
        return []
    config = read_config(flow_dir)
    provider = tracker_type(config)
    ex = bound_executor(config, execute)
    claims = []
    body_claim = None
    try:
        for dep in dependencies:
            claim = _claim_relate_pair(flow_dir, spec_id, dep, provider)
            if isinstance(claim, TrackerError):
                return [claim]
            claims.extend(claim)
        source = load_spec(flow_dir, spec_id)
        if isinstance(source, TrackerError):
            return [source]
        loc_a = _locator(merged_tracker(source[1]))
        if isinstance(loc_a, TrackerError):
            return [loc_a]
        if provider == "gitlab":
            body_claim = _claim_body_mutation(
                flow_dir, provider, loc_a, operation="relate", spec_id=spec_id)
            if isinstance(body_claim, TrackerError):
                return [body_claim]
        guard = P.display_durable_guard(provider, config, ex, locators=(loc_a,))
        if guard:
            return [guard]
        if provider == "jira":
            resolved = P.jira_blocks_type(config, ex)
            if isinstance(resolved, TrackerError):
                # Preserve the normal queued-capability behavior.
                return [_relate_txn(flow_dir, spec_id, blocked_by=dep,
                                    event=event, execute=execute, write_receipt=False)
                        for dep in dependencies]

        def prepare_dep(dep):
            loaded = load_spec(flow_dir, dep)
            if isinstance(loaded, TrackerError):
                return loaded
            loc_b = _locator(merged_tracker(loaded[1]))
            if isinstance(loc_b, TrackerError):
                return loc_b
            err = P.display_durable_guard(provider, config, ex, locators=(loc_b,))
            if err:
                return err
            remote = P.PROBES[provider](
                config, ex, from_id=loc_a["durable"], to_id=loc_b["durable"],
                from_display=loc_a["display"], to_display=loc_b["display"])
            return {"config": config, "locators": (loc_a, loc_b), "remote": remote}

        with ThreadPoolExecutor(max_workers=CONCURRENCY_CAP) as pool:
            prepared = list(pool.map(prepare_dep, dependencies))
        results = []
        for dep, inputs in zip(dependencies, prepared, strict=True):
            out = inputs if isinstance(inputs, TrackerError) else _relate_txn(
                flow_dir, spec_id, blocked_by=dep, event=event, execute=execute,
                write_receipt=False, prepared=inputs)
            results.append(out)
            if isinstance(out, TrackerError):
                break
        return results
    finally:
        if body_claim is not None and not isinstance(body_claim, TrackerError):
            _release_claim(body_claim)
        for path in claims:
            _release_claim(path)
