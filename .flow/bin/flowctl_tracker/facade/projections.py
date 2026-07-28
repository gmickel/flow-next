"""Deterministic pull-side projections owned by the lifecycle facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from ..config_lock import ConfigLockTimeout, config_lock
from ..lifecycle.helpers import (Execute, Result, atomic_write_json, dict_,
                                 load_spec, merged_tracker, now_iso)
from ..types import ErrorClass, TrackerError
from ..wire import (_PAGE_SIZE, _destination, _gh_repo, _gl_project, _jira,
                    _jira_base, _rest_drain, github, gitlab, linear)


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _error_data(err: TrackerError) -> dict:
    return {
        "class": err.cls.value,
        "subtype": err.subtype,
        "message": err.message,
        "details": err.details,
    }


def _ready_state(config: dict) -> str | None:
    value = dict_(config.get("tracker")).get("readyState")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _status_name(provider: str, issue: dict) -> str | None:
    raw = issue.get("raw") if isinstance(issue.get("raw"), dict) else {}
    if provider == "linear":
        state = raw.get("state") if isinstance(raw.get("state"), dict) else {}
        value = state.get("name")
    elif provider == "jira":
        fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
        status = fields.get("status") if isinstance(fields.get("status"), dict) else {}
        value = status.get("name")
    else:
        value = None
    return str(value) if value is not None else None


def _desired(provider: str, issue: dict, ready_state: str
             ) -> bool | TrackerError:
    if provider in {"github", "gitlab"}:
        labels = issue.get("labels")
        if not isinstance(labels, list):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "normalized issue labels are malformed; readiness untouched",
                subtype="readiness_shape",
            )
        return _norm(ready_state) in {_norm(label) for label in labels}
    status_name = _status_name(provider, issue)
    if status_name is None:
        return TrackerError(
            ErrorClass.TRANSPORT,
            "normalized issue status is missing; readiness untouched",
            subtype="readiness_shape",
        )
    return _norm(status_name) == _norm(ready_state)


def _config_exists(provider: str, config: dict, ready_state: str,
                   execute: Execute) -> bool | TrackerError:
    """Prove a false match is genuine, not stale readyState config."""
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest

    if provider == "github":
        repo = _gh_repo(dest)
        if isinstance(repo, TrackerError):
            return repo
        out = github._cli(  # noqa: SLF001 - same package transport primitive
            execute, "github", config, "facade-readiness-exists", "GET",
            f"repos/{repo}/labels/{quote(ready_state, safe='')}",
            idempotent=True,
        )
        if isinstance(out, TrackerError):
            if out.cls is ErrorClass.NOT_FOUND:
                return False
            return out
        return isinstance(out, dict) and _norm(out.get("name")) == _norm(ready_state)

    if provider == "gitlab":
        project = _gl_project(dest)
        if isinstance(project, TrackerError):
            return project
        def fetch_labels_page(page: int) -> Result:
            query = urlencode({
                'search': ready_state,
                'per_page': _PAGE_SIZE,
                'page': page,
            })
            return gitlab._cli(  # noqa: SLF001 - package transport primitive
                execute, "gitlab", config, "facade-readiness-exists", "GET",
                f"projects/{project}/labels?{query}", idempotent=True,
            )

        drained = _rest_drain(fetch_labels_page)
        if isinstance(drained, TrackerError):
            return drained
        labels, truncated = drained
        exists = any(
            isinstance(label, dict)
            and _norm(label.get("name")) == _norm(ready_state)
            for label in labels
        )
        if exists:
            return True
        if truncated:
            return TrackerError(
                ErrorClass.TRANSPORT,
                "gitlab labels pages truncated at drain cap; readyState "
                "absence unproven",
                subtype="readiness_truncated",
            )
        return False

    if provider == "linear":
        team_id = dest.get("teamId")
        if not isinstance(team_id, str) or not team_id:
            return TrackerError(
                ErrorClass.UNRESOLVED, "linear destination missing teamId",
                subtype="destination")
        out = linear._gql(  # noqa: SLF001 - same package transport primitive
            execute, "facade-readiness-exists",
            "query($team: ID!) { workflowStates(first: 100, "
            "filter: { team: { id: { eq: $team } } }) { "
            "nodes { name } pageInfo { hasNextPage } } }",
            {"team": team_id}, idempotent=True,
        )
        if isinstance(out, TrackerError):
            return out
        conn = out.get("workflowStates") if isinstance(out, dict) else None
        if not isinstance(conn, dict) or not isinstance(conn.get("nodes"), list):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "linear workflow states response is malformed",
                subtype="readiness_shape")
        page = conn.get("pageInfo") if isinstance(conn.get("pageInfo"), dict) else {}
        if page.get("hasNextPage"):
            return TrackerError(
                ErrorClass.TRANSPORT,
                "linear workflow states listing is truncated; readiness untouched",
                subtype="readiness_truncated")
        return any(
            isinstance(state, dict)
            and _norm(state.get("name")) == _norm(ready_state)
            for state in conn["nodes"]
        )

    if provider == "jira":
        project = dest.get("projectKey")
        if not isinstance(project, str) or not project:
            return TrackerError(
                ErrorClass.UNRESOLVED, "jira destination missing projectKey",
                subtype="destination")
        base = _jira_base(config, dest)
        if isinstance(base, TrackerError):
            return base
        api_version = dest.get("apiVersion") or 2
        out = _jira(
            execute, "facade-readiness-exists", "GET",
            f"{base}/rest/api/{api_version}/project/"
            f"{quote(project, safe='')}/statuses",
            idempotent=True,
        )
        if isinstance(out, TrackerError):
            return out
        if not isinstance(out, list):
            return TrackerError(
                ErrorClass.TRANSPORT, "jira project statuses response is malformed",
                subtype="readiness_shape")
        names = {
            _norm(status.get("name"))
            for issue_type in out if isinstance(issue_type, dict)
            for status in (
                issue_type.get("statuses")
                if isinstance(issue_type.get("statuses"), list) else []
            )
            if isinstance(status, dict)
        }
        return _norm(ready_state) in names

    return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")


def _persist_ready(flow_dir: Path, spec_id: str, *, desired: bool,
                   expected_id: str | None, expected_identifier: str | None
                   ) -> Result:
    try:
        with config_lock(flow_dir):
            loaded = load_spec(flow_dir, spec_id)
            if isinstance(loaded, TrackerError):
                return loaded
            path, spec = loaded
            tracker = merged_tracker(spec)
            if (tracker.get("id") != expected_id
                    or tracker.get("identifier") != expected_identifier):
                return TrackerError(
                    ErrorClass.CONFLICT,
                    "tracker identity changed during readiness projection",
                    subtype="identity_drift",
                    details={
                        "expected": {
                            "id": expected_id,
                            "identifier": expected_identifier,
                        },
                        "found": {
                            "id": tracker.get("id"),
                            "identifier": tracker.get("identifier"),
                        },
                    },
                )
            changed = bool(spec.get("ready", False)) != desired
            if changed:
                spec = dict(spec)
                spec["ready"] = desired
                spec["updated_at"] = now_iso()
                err = atomic_write_json(path, spec)
                if err:
                    return err
            return {"kind": "updated" if changed else "noop",
                    "ready": desired, "changed": changed}
    except ConfigLockTimeout as exc:
        return TrackerError(ErrorClass.CONFLICT, str(exc), subtype="lock_timeout")


def project_readiness(flow_dir: Path, spec_id: str, *, issue: dict,
                      config: dict, provider: str, locator: dict,
                      execute: Execute) -> dict:
    """Project readyState without aborting body/status/comment reconciliation."""
    ready_state = _ready_state(config)
    if ready_state is None:
        return {"kind": "skipped", "reason": "readyState_unset"}

    desired = _desired(provider, issue, ready_state)
    if isinstance(desired, TrackerError):
        return {"kind": "noop", "reason": "unreadable_issue",
                "degraded": _error_data(desired)}

    if not desired:
        exists = _config_exists(provider, config, ready_state, execute)
        if isinstance(exists, TrackerError):
            return {"kind": "noop", "reason": "readiness_probe_failed",
                    "degraded": _error_data(exists)}
        if not exists:
            return {
                "kind": "noop",
                "reason": "stale_readyState",
                "readyState": ready_state,
                "degraded": {
                    "kind": "stale_readyState",
                    "message": (
                        f"configured readyState {ready_state!r} was not found; "
                        "local ready flag untouched"
                    ),
                },
            }

    out = _persist_ready(
        flow_dir, spec_id, desired=bool(desired),
        expected_id=locator.get("durable"),
        expected_identifier=locator.get("display"),
    )
    if isinstance(out, TrackerError):
        return {"kind": "noop", "reason": "readiness_write_failed",
                "degraded": _error_data(out)}
    return {**out, "readyState": ready_state}
