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
    "in_progress": "status:in-progress",
    "in_review": "status:in-review",
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


def _recognized_slot(name: str) -> Optional[str]:
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


def _slot_from_status_label(labels: Any) -> Union[Optional[str], TrackerError]:
    """Classify the issue's status:* labels into a single slot.

    The status:* namespace is single-valued (github.md/gitlab.md "Idempotent
    status: labels"). More than one recognized status:* label is a violated
    invariant: picking whichever the provider lists first would be arbitrary
    (order-dependent transitions) and can no-op into permanently leaving the
    namespace inconsistent — so it is a CONFLICT for the recovery surface,
    never a silent first-match. Unrecognized status:* labels are ignored.
    """
    recognized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in _status_labels(labels):
        slot = _recognized_slot(name)
        if slot is None or name in seen:
            continue
        seen.add(name)
        recognized.append((name, slot))
    if len(recognized) > 1:
        names = [n for n, _ in recognized]
        return TrackerError(
            ErrorClass.CONFLICT,
            f"ambiguous status labels {names!r}: status:* is single-valued",
            subtype="ambiguous-status-labels",
            details={"normalized": "status", "labels": names,
                     "slots": sorted({s for _, s in recognized})},
        )
    if recognized:
        return recognized[0][1]
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


def github_native_status(parent: dict) -> str:
    """Normalize only GitHub's authoritative native state.

    Used narrowly by the retry repair path when status labels are ambiguous.
    It does not guess a label target; callers must still prove the requested
    transition safe through merge evidence and the decision policy.
    """
    state = str(parent.get("state") or "").upper()
    reason = parent.get("state_reason") or parent.get("stateReason")
    if state == "CLOSED":
        return "cancelled" if str(reason or "").lower() == "not_planned" else "done"
    return "in_progress"


def _norm_github(parent: dict) -> Union[str, TrackerError]:
    state = str(parent.get("state") or "").upper()
    if state == "CLOSED":
        labeled = _slot_from_status_label(parent.get("labels"))
        if isinstance(labeled, TrackerError):
            return labeled
        return github_native_status(parent)
    # OPEN
    labeled = _slot_from_status_label(parent.get("labels"))
    if isinstance(labeled, TrackerError):
        return labeled
    # Native OPEN is authoritative over a stale terminal label. A manual
    # reopen must not be normalized back to done/cancelled by the label left
    # behind from the earlier close.
    if labeled in TERMINAL or labeled == "cancelled":
        return "in_progress"
    if labeled:
        return labeled
    return "in_progress"  # open + no status: label


def _norm_gitlab(parent: dict) -> Union[str, TrackerError]:
    # GitLab states are opened/closed (NOT open/closed).
    state = str(parent.get("state") or "").lower()
    if state == "closed":
        labeled = _slot_from_status_label(parent.get("labels"))
        if isinstance(labeled, TrackerError):
            return labeled
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
    if isinstance(labeled, TrackerError):
        return labeled
    # Native opened is authoritative over a stale terminal label, matching
    # GitHub's manual-reopen contract above.
    if labeled in TERMINAL or labeled == "cancelled":
        return "in_progress"
    if labeled:
        return labeled
    return "in_progress"


# Canonical progression order for READ-side disambiguation of aliased maps.
_READ_ORDER = ("backlog", "todo", "in_progress", "in_review", "done", "cancelled")


def _reverse_state_map(ids: dict) -> dict:
    """Invert a slot->id map deterministically for the read direction.

    validate_select (states.py) sanctions ALIASING: one live state id may
    serve multiple slots (e.g. in_review sharing in_progress's state on teams
    without a review column). The write direction is per-slot and unaffected,
    but inverting with a plain comprehension makes the read direction depend
    on JSON key order: the same issue could normalize as in_progress or
    in_review from serialization alone and flip the merge-gate decision
    (terminal x in_progress deadlocks; terminal x in_review applies).

    A duplicate id is therefore resolved to the EARLIEST aliased slot in the
    canonical progression order, not by dict order: the least-advanced
    reading never over-claims progress, and a terminal-vs-aliased pair routes
    through the deadlock conflict surface instead of an order-dependent
    silent apply. Erroring instead would make sanctioned aliases unreadable.
    """
    reverse: dict = {}
    for slot in _READ_ORDER:
        v = ids.get(slot)
        if v is not None and str(v) not in reverse:
            reverse[str(v)] = slot
    # Defensive: keys outside the canonical vocabulary still invert, in
    # sorted-key order (deterministic), and never shadow a canonical slot.
    for slot in sorted(k for k in ids if k not in _READ_ORDER):
        v = ids.get(slot)
        if v is not None and str(v) not in reverse:
            reverse[str(v)] = slot
    return reverse


def _norm_linear(parent: dict, dest: dict) -> Union[str, TrackerError]:
    state = parent.get("state")
    if not isinstance(state, dict):
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear parent carries no state",
                            subtype="malformed_body")
    sid = state.get("id")
    state_ids = dict_(dest.get("stateIds"))
    reverse = _reverse_state_map(state_ids)
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
    reverse = _reverse_state_map(status_ids)
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
        return _apply_linear(config, locator, parent, execute,
                             target_slot=target_slot)
    if provider == "jira":
        return _apply_jira(config, locator, execute, target_slot=target_slot)
    return TrackerError(ErrorClass.INVALID_INPUT, f"unknown provider {provider!r}",
                        subtype="provider")


def github_status_label(target_slot: str, *,
                        use_verified_label: bool = False) -> str:
    return ("status:verified"
            if target_slot == "done" and use_verified_label
            else _LABEL.get(target_slot, f"status:{target_slot}"))


def github_status_labels_match(parent: dict, *, target_slot: str,
                               use_verified_label: bool = False) -> bool:
    labels = _status_labels(parent.get("labels"))
    if len(labels) != 1:
        return False
    if use_verified_label:
        return labels[0] == "status:verified"
    return _recognized_slot(labels[0]) == target_slot


def repair_github_status_labels(config: dict, locator: dict, parent: dict,
                                execute: Execute, *, target_slot: str,
                                use_verified_label: bool = False) -> Result:
    """Repair only GitHub's status-label namespace, never native state.

    The status verb calls this only after the ordinary merge-evidence and
    decision policy prove a noop target. Failures remain retryable because a
    later invocation re-evaluates label consistency even when normalization
    succeeds from native state.
    """
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

    label = github_status_label(
        target_slot, use_verified_label=use_verified_label)
    failures: list[dict] = []
    for old in [x for x in _status_labels(parent.get("labels"))
                if x != label]:
        removed = _cli(
            execute, "github", config, "status-label-rm", "DELETE",
            f"repos/{repo}/issues/{number}/labels/{quote(old, safe='')}",
            idempotent=False)
        if isinstance(removed, TrackerError):
            failures.append({
                "op": "repair-remove", "label": old,
                "error": removed.message})
    added = _cli(
        execute, "github", config, "status-label-add", "POST",
        f"repos/{repo}/issues/{number}/labels", body={"labels": [label]})
    if isinstance(added, TrackerError):
        failures.append({
            "op": "repair-add", "label": label, "error": added.message})

    readback = _cli(
        execute, "github", config, "status-label-readback", "GET",
        f"repos/{repo}/issues/{number}/labels", idempotent=True)
    if isinstance(readback, list):
        present = [
            x.get("name") for x in readback
            if isinstance(x, dict) and isinstance(x.get("name"), str)
            and x["name"].startswith("status:")
        ]
        if present == [label]:
            return {
                "applied": target_slot,
                "label": label,
                "completed_steps": ["labels"],
                "repair": "labels-only",
                "degraded": None,
            }
        error_class = ErrorClass.CONFLICT
        detail = None
    else:
        present = _status_labels(parent.get("labels"))
        error_class = ErrorClass.TRANSPORT
        detail = (readback.message if isinstance(readback, TrackerError)
                  else "unexpected repair readback shape")
    if detail:
        failures.append({"op": "repair-readback", "error": detail})
    return TrackerError(
        error_class,
        "github status-label repair did not converge",
        subtype="status_labels_partial",
        details={
            "completed_steps": ([] if isinstance(added, TrackerError)
                                else ["label-add"]),
            "target": target_slot,
            "expected": [label],
            "present": present,
            "failures": failures,
        },
        auto_retryable=True,
    )


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
    label = github_status_label(
        target_slot, use_verified_label=use_verified_label)
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
    # Labels: status:* is single-valued. The STATE change above is the
    # operation and has ALREADY landed - every label failure from here on is
    # reported as explicit partial evidence, never a bare failure a retry
    # would misread as nothing-happened (the re-run would noop on the closed
    # issue and silently lose the label + receipt).
    label_failures: list = []
    for old in remove:
        rm = _cli(execute, "github", config, "status-label-rm", "DELETE",
                  f"repos/{repo}/issues/{number}/labels/{quote(old, safe='')}",
                  idempotent=False)
        if isinstance(rm, TrackerError):
            label_failures.append({"op": "remove", "label": old,
                                   "error": rm.message})
    add = _cli(execute, "github", config, "status-label-add", "POST",
               f"repos/{repo}/issues/{number}/labels",
               body={"labels": [label]})
    add_failed = isinstance(add, TrackerError)
    if add_failed:
        label_failures.append({"op": "add", "label": label, "error": add.message})
    # Read back and verify the single-valued invariant actually holds.
    labels_degraded = None
    readback = _cli(execute, "github", config, "status-label-readback", "GET",
                    f"repos/{repo}/issues/{number}/labels", idempotent=True)
    if isinstance(readback, list):
        present = [x.get("name") for x in readback
                   if isinstance(x, dict) and isinstance(x.get("name"), str)
                   and x["name"].startswith("status:")]
        if present != [label]:
            if add_failed:
                # The target label did not land. Preserve the earlier
                # partial-success contract; cleanup cannot manufacture the
                # requested target.
                labels_degraded = {
                    "kind": "status_labels_inconsistent",
                    "expected": [label], "present": present,
                    "failures": label_failures,
                }
            else:
                # A successful add plus a failed/stale remove leaves an
                # ambiguous namespace. Make one bounded cleanup pass over
                # every unexpected status label, then verify once more.
                # Never advance durable success while readback still proves
                # multiple status labels.
                for unexpected in [x for x in present if x != label]:
                    repaired = _cli(
                        execute, "github", config, "status-label-rm", "DELETE",
                        f"repos/{repo}/issues/{number}/labels/"
                        f"{quote(unexpected, safe='')}",
                        idempotent=False)
                    if isinstance(repaired, TrackerError):
                        label_failures.append({
                            "op": "repair-remove", "label": unexpected,
                            "error": repaired.message})
                repaired_readback = _cli(
                    execute, "github", config, "status-label-readback", "GET",
                    f"repos/{repo}/issues/{number}/labels", idempotent=True)
                if isinstance(repaired_readback, list):
                    repaired_present = [
                        x.get("name") for x in repaired_readback
                        if isinstance(x, dict)
                        and isinstance(x.get("name"), str)
                        and x["name"].startswith("status:")
                    ]
                    if repaired_present == [label]:
                        present = repaired_present
                        label_failures = []
                    else:
                        return TrackerError(
                            ErrorClass.CONFLICT,
                            "github state change landed but status labels "
                            "remain ambiguous after bounded repair",
                            subtype="status_labels_partial",
                            details={
                                "completed_steps": ["state", "label-add"],
                                "target": target_slot,
                                "expected": [label],
                                "present": repaired_present,
                                "failures": label_failures,
                            },
                            auto_retryable=True,
                        )
                else:
                    detail = (
                        repaired_readback.message
                        if isinstance(repaired_readback, TrackerError)
                        else "unexpected repair readback shape")
                    return TrackerError(
                        ErrorClass.TRANSPORT,
                        "github state change landed but status-label repair "
                        "could not be verified",
                        subtype="status_labels_partial",
                        details={
                            "completed_steps": ["state", "label-add"],
                            "target": target_slot,
                            "expected": [label],
                            "present": present,
                            "failures": label_failures
                            + [{"op": "repair-readback", "error": detail}],
                        },
                        auto_retryable=True,
                    )
    else:
        # Readback failed or returned an unusable shape: the invariant is
        # unverifiable even when every label op above succeeded.
        detail = (readback.message if isinstance(readback, TrackerError)
                  else "unexpected readback shape")
        labels_degraded = {"kind": "status_labels_unverified",
                           "failures": label_failures
                           + [{"op": "readback", "error": detail}]}
    return {"applied": target_slot, "state_reason": payload.get("state_reason"),
            "label": label,
            "completed_steps": ["state"] + ([] if label_failures else ["labels"]),
            "degraded": labels_degraded}


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


def _apply_linear(config, locator, parent, execute, *, target_slot) -> Result:
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
    # Already-current? Mirror the Jira writer's check. A sanctioned aliased
    # map (e.g. in_progress/in_review sharing one live state) reads back as
    # the EARLIEST slot, so the gate can request the exact state id the issue
    # already carries; writing it would report "applied", advance
    # lastSyncedAt, and repeat on every subsequent sync. The verb layer maps
    # a write-noop to kind=noop (no lastSyncedAt advance), which is honest:
    # the native state already satisfies the request. Parent is enriched with
    # state before apply (enrich_linear_parent); missing state falls through
    # to the mutation, never raises.
    cur_id = dict_(dict_(parent).get("state")).get("id")
    if cur_id is not None and str(cur_id) == str(state_id):
        return {"noop": True, "applied": target_slot, "stateId": str(state_id)}
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
