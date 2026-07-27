"""Provider status writes + tracker-norm reads (fn-140.3).

GitHub: PATCH issue {state, state_reason}; duplicate accepted, garbage rejected
upstream of this module. GitLab: PUT {state_event: close|reopen}; states are
opened/closed. Linear: issueUpdate {stateId} from destination.stateIds. Jira:
GET …/transitions, match to.id == cached destination.statusIds[slot], POST;
never a cached transition id.
"""

from __future__ import annotations

from typing import Any, Optional, Union
from urllib.parse import quote

from ..lifecycle.helpers import Execute, Result, destination, dict_
from ..types import ErrorClass, TrackerError
from .policy import TERMINAL

# Slot → status: label token (github/gitlab reduced-fidelity recovery).
_LABEL = {
    "backlog": "status:backlog",
    "todo": "status:todo",
    "in_progress": "status:in_progress",
    "in_review": "status:in_review",
    "done": "status:done",
}


def _status_labels(labels: Any) -> list[str]:
    names: list[str] = []
    for x in labels or []:
        if isinstance(x, dict):
            n = x.get("name")
        else:
            n = x
        if isinstance(n, str) and n.startswith("status:"):
            names.append(n)
    return names


def _slot_from_status_label(labels: Any) -> Optional[str]:
    for name in _status_labels(labels):
        token = name.split(":", 1)[-1].strip().lower().replace("-", "_")
        # legacy planned → todo
        if token == "planned":
            return "todo"
        if token in {"backlog", "todo", "in_progress", "in_review", "done"}:
            return token
        if token in {"verified"}:
            return "done"
        if token in {"deferred", "wontfix", "cancelled", "canceled"}:
            return "cancelled"
    return None


def tracker_norm_from_parent(provider: str, parent: dict, dest: dict
                             ) -> Union[str, TrackerError]:
    """Map a parent-read payload to a CLI slot. Unmapped → conflict."""
    if provider == "github":
        return _norm_github(parent)
    if provider == "gitlab":
        return _norm_gitlab(parent)
    if provider == "linear":
        return _norm_linear(parent, dest)
    if provider == "jira":
        return _norm_jira(parent, dest)
    return TrackerError(ErrorClass.INVALID_INPUT, f"unknown provider {provider!r}",
                        subtype="provider")


def _norm_github(parent: dict) -> Union[str, TrackerError]:
    state = str(parent.get("state") or "").upper()
    reason = parent.get("state_reason") or parent.get("stateReason")
    reason_s = str(reason).lower() if reason else ""
    if state == "CLOSED":
        if reason_s in {"not_planned"}:
            return "cancelled"
        return "done"
    # OPEN
    labeled = _slot_from_status_label(parent.get("labels"))
    if labeled == "cancelled":
        return "cancelled"
    if labeled:
        return labeled
    return "in_progress"  # open + no status: label


def _norm_gitlab(parent: dict) -> Union[str, TrackerError]:
    # GitLab states are opened/closed (NOT open/closed).
    state = str(parent.get("state") or "").lower()
    if state == "closed":
        labeled = _slot_from_status_label(parent.get("labels"))
        if labeled == "cancelled":
            return "cancelled"
        return "done"
    if state != "opened":
        return TrackerError(
            ErrorClass.CONFLICT,
            f"unmapped gitlab state {state!r}",
            subtype="unmapped-state",
            details={"normalized": "status", "raw": state},
        )
    labeled = _slot_from_status_label(parent.get("labels"))
    if labeled == "cancelled":
        return "cancelled"
    if labeled:
        return labeled
    return "in_progress"


def _norm_linear(parent: dict, dest: dict) -> Union[str, TrackerError]:
    state = parent.get("state")
    if not isinstance(state, dict):
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear parent carries no state",
                            subtype="malformed_body")
    sid = state.get("id")
    state_ids = dict_(dest.get("stateIds"))
    reverse = {str(v): k for k, v in state_ids.items() if v is not None}
    if sid is not None and str(sid) in reverse:
        slot = reverse[str(sid)]
        return slot if slot in {"backlog", "todo", "in_progress", "in_review",
                                "done", "cancelled"} else "done"
    # Fall back to Linear type taxonomy
    stype = str(state.get("type") or "").lower()
    name = str(state.get("name") or "").lower()
    if stype in {"triage", "backlog"}:
        return "backlog"
    if stype == "unstarted":
        return "todo"
    if stype == "started":
        if "review" in name:
            return "in_review"
        return "in_progress"
    if stype == "completed":
        return "done"
    if stype == "canceled":
        return "cancelled"
    return TrackerError(
        ErrorClass.CONFLICT,
        f"unmapped linear state {state.get('name')!r} (type {stype!r})",
        subtype="unmapped-state",
        details={"normalized": "status", "raw": state.get("name"), "type": stype},
    )


def _norm_jira(parent: dict, dest: dict) -> Union[str, TrackerError]:
    fields = dict_(parent.get("fields"))
    status = dict_(fields.get("status"))
    sid = status.get("id")
    status_ids = dict_(dest.get("statusIds"))
    reverse = {str(v): k for k, v in status_ids.items() if v is not None}
    if sid is not None and str(sid) in reverse:
        return reverse[str(sid)]
    cat = dict_(status.get("statusCategory")).get("key")
    if cat == "done":
        return "done"
    if cat == "new":
        return "todo"
    if cat == "indeterminate":
        name = str(status.get("name") or "").lower()
        if "review" in name:
            return "in_review"
        return "in_progress"
    return TrackerError(
        ErrorClass.CONFLICT,
        f"unmapped jira status {status.get('name')!r}",
        subtype="unmapped-state",
        details={"normalized": "status", "raw": status.get("name")},
    )


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def apply_status(provider: str, config: dict, locator: dict, parent: dict,
                 execute: Execute, *, target_slot: str,
                 close_reason: Optional[str] = None,
                 use_verified_label: bool = False) -> Result:
    if provider == "github":
        return _apply_github(config, locator, parent, execute,
                             target_slot=target_slot, close_reason=close_reason,
                             use_verified_label=use_verified_label)
    if provider == "gitlab":
        return _apply_gitlab(config, locator, parent, execute,
                             target_slot=target_slot,
                             use_verified_label=use_verified_label)
    if provider == "linear":
        return _apply_linear(config, locator, execute, target_slot=target_slot)
    if provider == "jira":
        return _apply_jira(config, locator, execute, target_slot=target_slot)
    return TrackerError(ErrorClass.INVALID_INPUT, f"unknown provider {provider!r}",
                        subtype="provider")


def _apply_github(config, locator, parent, execute, *, target_slot, close_reason,
                  use_verified_label) -> Result:
    from ..wire import _cli, _destination, _gh_repo, _github_number  # noqa: PLC0415
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    number = _github_number(locator["display"])
    repo = _gh_repo(dest)
    if isinstance(number, TrackerError):
        return number
    if isinstance(repo, TrackerError):
        return repo
    label = ("status:verified" if (target_slot == "done" and use_verified_label)
             else _LABEL.get(target_slot, f"status:{target_slot}"))
    remove = [x for x in _status_labels(parent.get("labels")) if x != label]
    # Native open/close
    if target_slot in TERMINAL:
        payload = {"state": "closed",
                   "state_reason": close_reason or "completed"}
    else:
        payload = {"state": "open"}
        if close_reason == "reopened":
            payload["state_reason"] = "reopened"
    data = _cli(execute, "github", config, "status-set", "PATCH",
                f"repos/{repo}/issues/{number}", body=payload)
    if isinstance(data, TrackerError):
        return data
    # Labels: status:* is single-valued — remove others, then add target.
    if remove:
        for old in remove:
            _cli(execute, "github", config, "status-label-rm", "DELETE",
                 f"repos/{repo}/issues/{number}/labels/{quote(old, safe='')}",
                 idempotent=False)
            # Best-effort: missing/forbidden label must not block the status write.
    add = _cli(execute, "github", config, "status-label-add", "POST",
               f"repos/{repo}/issues/{number}/labels",
               body={"labels": [label]})
    if isinstance(add, TrackerError):
        return add
    return {"applied": target_slot, "state_reason": payload.get("state_reason"),
            "label": label}


def _apply_gitlab(config, locator, parent, execute, *, target_slot,
                  use_verified_label) -> Result:
    from ..wire import _cli, _destination, _gl_project, _gitlab_iid  # noqa: PLC0415
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    iid = _gitlab_iid(locator["display"])
    pid = _gl_project(dest)
    if isinstance(iid, TrackerError):
        return iid
    if isinstance(pid, TrackerError):
        return pid
    label = ("status:verified" if (target_slot == "done" and use_verified_label)
             else _LABEL.get(target_slot, f"status:{target_slot}"))
    remove = [x for x in _status_labels(parent.get("labels")) if x != label]
    if target_slot in TERMINAL:
        state_event = "close"
    else:
        state_event = "reopen"
    body: dict = {"state_event": state_event, "add_labels": label}
    if remove:
        body["remove_labels"] = ",".join(remove)
    data = _cli(execute, "gitlab", config, "status-set", "PUT",
                f"projects/{pid}/issues/{iid}", body=body)
    if isinstance(data, TrackerError):
        return data
    # Readback must understand opened/closed
    state = None
    if isinstance(data, dict):
        state = data.get("state")
    return {"applied": target_slot, "state_event": state_event,
            "state": state, "label": label}


def _apply_linear(config, locator, execute, *, target_slot) -> Result:
    from ..wire import _gql  # noqa: PLC0415
    dest = destination(config)
    if isinstance(dest, TrackerError):
        return dest
    state_ids = dict_(dest.get("stateIds"))
    state_id = state_ids.get(target_slot)
    if not state_id:
        return TrackerError(
            ErrorClass.UNRESOLVED,
            f"destination.stateIds missing slot {target_slot!r}",
            subtype="stateIds",
        )
    data = _gql(execute, "status-set",
                "mutation($id: String!, $stateId: String!) { "
                "issueUpdate(id: $id, input: { stateId: $stateId }) "
                "{ success issue { id } } }",
                {"id": locator["durable"], "stateId": str(state_id)})
    if isinstance(data, TrackerError):
        return data
    payload = data.get("issueUpdate") if isinstance(data, dict) else None
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear issueUpdate reported failure",
                            subtype="mutation_failed")
    return {"applied": target_slot, "stateId": str(state_id)}


def _apply_jira(config, locator, execute, *, target_slot) -> Result:
    """GET legal transitions; match to.id == cached statusIds[slot]; POST.

    No legal transition → returns a defer sentinel dict (not a forced jump).
    Never uses a cached transition id.
    """
    from ..wire import _destination, _jira, _jira_base  # noqa: PLC0415
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    status_ids = dict_(dest.get("statusIds"))
    target_id = status_ids.get(target_slot)
    if target_id is None:
        return {"defer": True, "reason": "status-unmapped",
                "target_slot": target_slot}
    issue_key = locator["display"]  # transitions addressed by key/id
    # Prefer durable id for mutation path; transitions accept either.
    issue_ref = locator.get("durable") or issue_key
    # Already-current? Read status from a cheap GET (parent may be stale).
    cur = _jira(execute, "status-current", "GET",
                f"{base}/rest/api/2/issue/{quote(str(issue_ref), safe='')}"
                f"?fields=status", idempotent=True)
    if isinstance(cur, TrackerError):
        return cur
    cur_status = dict_(dict_(dict_(cur).get("fields")).get("status"))
    if str(cur_status.get("id")) == str(target_id):
        return {"noop": True, "applied": target_slot}
    trs = _jira(execute, "status-transitions", "GET",
                f"{base}/rest/api/2/issue/{quote(str(issue_ref), safe='')}"
                f"/transitions", idempotent=True)
    if isinstance(trs, TrackerError):
        return trs
    transitions = list(dict_(trs).get("transitions") or [])
    tid = None
    for t in transitions:
        if not isinstance(t, dict):
            continue
        to = dict_(t.get("to"))
        if str(to.get("id")) == str(target_id):
            tid = t.get("id")
            break
    if tid is None:
        return {"defer": True, "reason": "transition-unreachable",
                "target_slot": target_slot, "target_status_id": str(target_id)}
    posted = _jira(execute, "status-set", "POST",
                   f"{base}/rest/api/2/issue/{quote(str(issue_ref), safe='')}"
                   f"/transitions",
                   body={"transition": {"id": str(tid)}})
    if isinstance(posted, TrackerError):
        return posted
    return {"applied": target_slot, "transition_id": str(tid),
            "target_status_id": str(target_id)}


def enrich_linear_parent(execute: Execute, locator: dict, parent: dict
                         ) -> Union[dict, TrackerError]:
    """Parent-read for wire omits state; fetch it for norm extraction."""
    if isinstance(parent.get("state"), dict) and parent["state"].get("id"):
        return parent
    from ..wire import _gql  # noqa: PLC0415
    data = _gql(execute, "status-state-read",
                "query($id: String!) { issue(id: $id) { id "
                "state { id name type } } }",
                {"id": locator["display"]}, idempotent=True)
    if isinstance(data, TrackerError):
        return data
    issue = data.get("issue")
    if not isinstance(issue, dict):
        return TrackerError(ErrorClass.NOT_FOUND, "linear issue not found",
                            subtype="parent")
    merged = dict(parent)
    merged["state"] = issue.get("state")
    return merged
