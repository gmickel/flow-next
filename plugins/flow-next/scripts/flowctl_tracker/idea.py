"""Idea intake: Jira Product Discovery ideas as a starting point (fn-330).

Off until `tracker.perTracker.ideaProjectKeys` lists the discovery projects.
An issue key in a listed project is an idea; deciding that costs no request.
Three operations, each reading before it writes so a repeat is safe:

- `read`: the idea's text, comments and delivery links.
- `settle_parent`: reuse the idea's delivery-linked parent-level issue in the
  delivery project, or create one and link it.
- `link`: the delivery link from a parent to the idea (the retry path).

flow-next stores no idea state. Which parent serves an idea is read from the
idea's delivery links every time, and a parent it creates carries a label
naming the idea, so a rerun finds one whose link failed. The only write to an
idea is the link.

The delivery link is the discovery product's own issue link type, found by
listing the site's link types: its name contains `Polaris` and its
descriptions are `implements` / `is implemented by`. The parent is the inward
issue and the idea the outward one, so the idea reads "is implemented by" the
parent. The type's id differs per site and its name has changed before, so
neither is hard-coded.

This module loads only when one of those operations runs. Deciding that an
issue is an idea, and the wire read's pointer, live in `wire/jira.py`.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urlencode, urlparse

from .types import ErrorClass, TrackerError
from .wire.jira import idea_reference, is_idea_key, key_from_url

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-[1-9][0-9]*$")
_IDEA_FIELDS = "summary,description,status,project,issuelinks"
#: Jira's colour markup, opening `{color:#97a0af}` or closing `{color}`.
_COLOR_TAG_RE = re.compile(r"\{color(?::[^{}]*)?\}")
#: Text kept byte for byte: a fenced block (how a `{code}` or `{noformat}`
#: block decodes) and a `{noformat}` span left inline.
_VERBATIM_RE = re.compile(r"^(`{3,})[^\n]*\n.*?^\1[ \t]*$|\{noformat\}.*?\{noformat\}",
                          re.M | re.S)


def _plain(text: Any) -> Any:
    """Idea text without colour tags outside code. Ideas are never written
    back, so this loses nothing; a linked issue's text keeps its markup."""
    if not isinstance(text, str):
        return text
    out, pos = [], 0
    for m in _VERBATIM_RE.finditer(text):
        out += [_COLOR_TAG_RE.sub("", text[pos:m.start()]), m.group(0)]
        pos = m.end()
    return "".join(out) + _COLOR_TAG_RE.sub("", text[pos:])


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _per(config: dict) -> dict:
    return _dict(_dict(config.get("tracker")).get("perTracker"))


def _delivery_project(config: dict) -> Optional[str]:
    dest = _dict(_dict(_dict(config.get("tracker")).get("resolved")).get("destination"))
    key = dest.get("projectKey")
    return key if isinstance(key, str) and key else None


def _project_of(key: str) -> str:
    return key.rsplit("-", 1)[0]


# ---------------------------------------------------------------------------
# Preconditions (no request)
# ---------------------------------------------------------------------------

def _check(config: dict, ref: Any) -> Any:
    """Return the idea key, or the refusal. Never makes a request."""
    tracker = _dict(config.get("tracker"))
    if tracker.get("type") != "jira":
        return TrackerError(
            ErrorClass.CAPABILITY,
            "idea intake supports Jira Product Discovery on Jira Cloud only; "
            f"tracker type is {tracker.get('type')!r}",
            subtype="idea_source", details={"capability": "idea_source"})
    per = _per(config)
    if per.get("authScheme") == "bearer-pat":
        return TrackerError(
            ErrorClass.CAPABILITY,
            "idea intake supports Jira Product Discovery on Jira Cloud only; "
            "this is Jira Data Center or Server",
            subtype="idea_source", details={"capability": "idea_source"})
    keys = per.get("ideaProjectKeys")
    if keys is None or keys == []:
        return TrackerError(
            ErrorClass.UNRESOLVED,
            "no idea source configured; set tracker.perTracker.ideaProjectKeys "
            "to the discovery project keys, e.g. "
            "flowctl config set tracker.perTracker.ideaProjectKeys '[\"IDEAS\"]'",
            subtype="idea_source", details={"key": "tracker.perTracker.ideaProjectKeys"})
    if not isinstance(keys, list) or not all(isinstance(k, str) and k for k in keys):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "tracker.perTracker.ideaProjectKeys must be a JSON list of project "
            f"keys, e.g. [\"IDEAS\"]; got {keys!r}",
            subtype="idea_source")
    key = _key_from_ref(config, ref)
    if isinstance(key, TrackerError):
        return key
    if not is_idea_key(config, key):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"{key} is not in a configured idea project "
            f"(tracker.perTracker.ideaProjectKeys: {keys})",
            subtype="not_an_idea")
    return key


def _base(config: dict) -> Any:
    from .wire import _destination, _jira_base  # noqa: PLC0415
    dest = _destination(config)
    if isinstance(dest, TrackerError):
        return dest
    return _jira_base(config, dest)


def _key_from_ref(config: dict, ref: Any) -> Any:
    """`IDEAS-7`, a `/browse/IDEAS-7` URL, or a discovery view URL carrying
    `selectedIssue=IDEAS-7`, on the configured site."""
    text = ref.strip() if isinstance(ref, str) else ""
    if _KEY_RE.fullmatch(text):
        return text
    parsed = urlparse(text)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        base = _base(config)
        if isinstance(base, TrackerError):
            return base
        if parsed.netloc.lower() != urlparse(base).netloc.lower():
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"idea URL is not on {base}", subtype="idea_url")
        key = key_from_url(base, text)
        if key:
            return key
    return TrackerError(
        ErrorClass.INVALID_INPUT,
        f"cannot read an idea key from {ref!r}; give the key (IDEAS-7) or its URL",
        subtype="idea_ref")


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def _is_delivery_type(link_type: Any) -> bool:
    t = _dict(link_type)
    return ("polaris" in str(t.get("name") or "").lower()
            and str(t.get("inward") or "").strip().lower() == "is implemented by"
            and str(t.get("outward") or "").strip().lower() == "implements")


def _get_idea(config: dict, key: str, execute) -> Any:
    from .wire import _jira  # noqa: PLC0415
    base = _base(config)
    if isinstance(base, TrackerError):
        return base
    raw = _jira(execute, "idea-read", "GET",
                f"{base}/rest/api/2/issue/{quote(key, safe='')}?fields={_IDEA_FIELDS}",
                idempotent=True)
    if isinstance(raw, TrackerError):
        return raw
    if not isinstance(raw, dict) or raw.get("id") is None or not raw.get("key"):
        return TrackerError(ErrorClass.TRANSPORT, "jira idea read missing id/key",
                            subtype="malformed_body")
    if not is_idea_key(config, raw["key"]):
        # Moved out of the discovery projects: delivery work now, not an idea.
        return TrackerError(
            ErrorClass.CAPABILITY,
            f"{key} is now {raw['key']}, outside the discovery projects "
            "(tracker.perTracker.ideaProjectKeys); it is no longer an idea, so "
            "idea intake does not apply. Work from it as an ordinary issue",
            subtype="not_an_idea",
            details={"capability": "idea_source", "identifier": raw["key"]})
    return raw


def _delivery_links(raw: dict, type_id: Optional[str] = None) -> list:
    """Issues linked to the idea as its delivery (the idea is the outward side).

    With `type_id` (the type found by listing), match that id; without it,
    match the type by the same name and description rule."""
    out = []
    for link in _dict(raw.get("fields")).get("issuelinks") or []:
        link = _dict(link)
        link_type = _dict(link.get("type"))
        if type_id is not None:
            if str(link_type.get("id")) != str(type_id):
                continue
        elif not _is_delivery_type(link_type):
            continue
        other = _dict(link.get("inwardIssue"))
        if other.get("key"):
            out.append(_candidate(other, link.get("id")))
    return out


def _candidate(issue: dict, link_id: Any = None) -> dict:
    fields = _dict(issue.get("fields"))
    issue_type = _dict(fields.get("issuetype"))
    return {
        "linkId": link_id,
        "id": str(issue.get("id")) if issue.get("id") is not None else None,
        "key": issue["key"],
        "title": fields.get("summary"),
        "status": _dict(fields.get("status")).get("name"),
        "issueType": issue_type.get("name"),
        "hierarchyLevel": issue_type.get("hierarchyLevel"),
        "project": _project_of(issue["key"]),
    }


def _marker(key: str) -> str:
    """The label a parent created for idea `key` carries."""
    return f"flow-next-idea-{key}"


def _marked_parents(config: dict, execute, key: str, level: dict) -> Any:
    """Parent-level issues in the delivery project carrying the idea's marker:
    a parent an earlier run created whose delivery link then failed."""
    from .wire import _MAX_PAGES, _PAGE_SIZE, _jira  # noqa: PLC0415
    base = _base(config)
    if isinstance(base, TrackerError):
        return base
    query = {"jql": f'project = "{level["project"]}" AND labels = "{_marker(key)}"',
             "fields": "summary,status,issuetype", "maxResults": _PAGE_SIZE}
    found, seen = [], set()
    for _ in range(_MAX_PAGES):
        raw = _jira(execute, "idea-marker-search", "GET",
                    f"{base}/rest/api/2/search/jql?" + urlencode(query), idempotent=True)
        if isinstance(raw, TrackerError):
            return raw
        found += [_candidate(i) for i in _dict(raw).get("issues") or []
                  if isinstance(i, dict) and i.get("key")]
        if _dict(raw).get("isLast") is not False:
            return [c for c in found if c["hierarchyLevel"] == level["level"]]
        token = _dict(raw).get("nextPageToken")
        if not isinstance(token, str) or not token or token in seen:
            break
        seen.add(token)
        query["nextPageToken"] = token
    # Every candidate decides between reuse, a conflict and a create.
    return TrackerError(ErrorClass.TRANSPORT,
                        "jira marker search did not finish; nothing was created",
                        subtype="truncated")


def _idea_out(config: dict, raw: dict) -> dict:
    from .wire.jira import from_wire  # noqa: PLC0415
    fields = _dict(raw.get("fields"))
    base = _base(config)
    return {
        "id": str(raw["id"]),
        "identifier": raw["key"],
        "url": f"{base}/browse/{raw['key']}" if isinstance(base, str) else None,
        "title": fields.get("summary"),
        "body": _plain(from_wire(fields.get("description"))),
        "status": _dict(fields.get("status")).get("name"),
    }


def read(config: dict, ref: Any, execute) -> Any:
    """The idea's summary, description, comments and delivery links."""
    key = _check(config, ref)
    if isinstance(key, TrackerError):
        return key
    raw = _get_idea(config, key, execute)
    if isinstance(raw, TrackerError):
        return raw
    from .wire import jira as wire_jira  # noqa: PLC0415
    listed = wire_jira.comment_list(
        config, {"durable": str(raw["id"]), "display": raw["key"]}, execute)
    if isinstance(listed, TrackerError):
        return listed
    return {
        "idea": _idea_out(config, raw),
        "comments": [{"id": c.get("id"), "body": _plain(c.get("body")),
                      "created_at": c.get("created_at")}
                     for c in listed.get("comments") or []],
        "commentsTruncated": bool(listed.get("truncated")),
        "deliveryLinks": _delivery_links(raw),
        "reference": idea_reference(),
    }


def _link_type(config: dict, execute) -> Any:
    """Exactly one delivery link type on the site, or a stop naming what exists."""
    from .wire import _jira  # noqa: PLC0415
    base = _base(config)
    if isinstance(base, TrackerError):
        return base
    raw = _jira(execute, "idea-link-types", "GET",
                f"{base}/rest/api/2/issueLinkType", idempotent=True)
    if isinstance(raw, TrackerError):
        return raw
    types = [t for t in _dict(raw).get("issueLinkTypes") or [] if isinstance(t, dict)]
    matches = [t for t in types if _is_delivery_type(t)]
    if len(matches) == 1:
        return {"id": str(matches[0].get("id")), "name": matches[0].get("name")}
    found = matches or types
    return TrackerError(
        ErrorClass.UNRESOLVED,
        ("several issue link types look like the discovery delivery link"
         if matches else
         "no issue link type on this site is the discovery delivery link "
         "(name containing Polaris, implements / is implemented by)")
        + "; nothing was created",
        subtype="delivery_link_type",
        details={"found": [{"id": t.get("id"), "name": t.get("name"),
                            "inward": t.get("inward"), "outward": t.get("outward")}
                           for t in found]})


def _parent_level(config: dict, execute) -> Any:
    """The parent level (one above the configured issue type) and its types."""
    from .wire import _jira  # noqa: PLC0415
    base = _base(config)
    if isinstance(base, TrackerError):
        return base
    project_key = _delivery_project(config)
    dest = _dict(_dict(_dict(config.get("tracker")).get("resolved")).get("destination"))
    type_id = dest.get("issueTypeId")
    if not project_key or not type_id:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "jira destination missing projectKey/issueTypeId; "
                            "run flowctl tracker resolve",
                            subtype="destination")
    raw = _jira(execute, "idea-project", "GET",
                f"{base}/rest/api/2/project/{quote(project_key, safe='')}",
                idempotent=True)
    if isinstance(raw, TrackerError):
        return raw
    types = [t for t in _dict(raw).get("issueTypes") or [] if isinstance(t, dict)]
    own = next((t for t in types if str(t.get("id")) == str(type_id)), None)
    if own is None or not isinstance(own.get("hierarchyLevel"), int):
        return TrackerError(
            ErrorClass.UNRESOLVED,
            f"issue type {type_id} has no hierarchy level in project {project_key}",
            subtype="parent_type")
    level = own["hierarchyLevel"] + 1
    above = [t for t in types if t.get("hierarchyLevel") == level and not t.get("subtask")]
    return {"project": project_key, "level": level, "own": own.get("name"),
            "types": above}


def _creation_type(level: dict) -> Any:
    """The one issue type a new parent is created as; only creating needs it."""
    above = level["types"]
    if not above:
        return TrackerError(
            ErrorClass.CAPABILITY,
            f"project {level['project']} has no issue type above {level['own']!r}",
            subtype="parent_type", details={"capability": "parent_type"})
    if len(above) > 1:
        return TrackerError(
            ErrorClass.UNRESOLVED,
            f"project {level['project']} has several issue types above "
            f"{level['own']!r}: {[t.get('name') for t in above]}; nothing was created",
            subtype="parent_type",
            details={"found": [{"id": t.get("id"), "name": t.get("name")} for t in above]})
    return str(above[0]["id"])


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def _post_link(config: dict, execute, *, type_id: str, parent_key: str,
               idea_key: str) -> Any:
    from .wire import _jira  # noqa: PLC0415
    base = _base(config)
    if isinstance(base, TrackerError):
        return base
    return _jira(execute, "idea-link", "POST", f"{base}/rest/api/2/issueLink",
                 body={"type": {"id": type_id},
                       "inwardIssue": {"key": parent_key},
                       "outwardIssue": {"key": idea_key}})


def _retry(idea_key: str, parent_key: str) -> str:
    return f"flowctl tracker idea link {idea_key} {parent_key}"


def link(config: dict, ref: Any, parent_key: Any, execute) -> Any:
    """Link `parent_key` to the idea as its delivery, unless already linked."""
    key = _check(config, ref)
    if isinstance(key, TrackerError):
        return key
    parent_key = parent_key.strip() if isinstance(parent_key, str) else ""
    if not _KEY_RE.fullmatch(parent_key) or is_idea_key(config, parent_key):
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"parent {parent_key!r} must be a delivery issue key, not an idea",
            subtype="parent")
    link_type = _link_type(config, execute)
    if isinstance(link_type, TrackerError):
        return link_type
    raw = _get_idea(config, key, execute)
    if isinstance(raw, TrackerError):
        return raw
    if any(d["key"] == parent_key for d in _delivery_links(raw, link_type["id"])):
        return {"idea": key, "parent": parent_key, "linkType": link_type,
                "created": False, "existing": True}
    posted = _post_link(config, execute, type_id=link_type["id"],
                        parent_key=parent_key, idea_key=key)
    if isinstance(posted, TrackerError):
        return posted
    return {"idea": key, "parent": parent_key, "linkType": link_type,
            "created": True, "existing": False}


def settle_parent(config: dict, ref: Any, execute, *, body: str,
                  use: Optional[str] = None) -> Any:
    """One parent for the idea: reuse the delivery-linked one, or create and link.

    Several candidates come back as a conflict for the person to choose from
    (`use` names the choice). The link type is checked before anything is
    created; a failed link after a create returns the parent and the retry.
    """
    key = _check(config, ref)
    if isinstance(key, TrackerError):
        return key
    link_type = _link_type(config, execute)
    if isinstance(link_type, TrackerError):
        return link_type
    raw = _get_idea(config, key, execute)
    if isinstance(raw, TrackerError):
        return raw
    level = _parent_level(config, execute)
    if isinstance(level, TrackerError):
        return level
    candidates, not_reused = [], []
    for d in _delivery_links(raw, link_type["id"]):
        if d["project"] != level["project"]:
            not_reused.append({"key": d["key"], "reason":
                               f"outside the delivery project {level['project']}"})
        elif d["hierarchyLevel"] != level["level"]:
            not_reused.append({"key": d["key"], "reason":
                               f"not at the parent level (one above {level['own']})"})
        else:
            candidates.append(d)
    base = _base(config)
    idea_ref = {"identifier": key,
                "url": f"{base}/browse/{key}" if isinstance(base, str) else None}

    def settled(parent: dict, *, linked: bool) -> dict:
        """The result; an unlinked parent gets its delivery link now."""
        out = {"idea": idea_ref, "linkType": link_type, "notReused": not_reused,
               "parent": parent}
        if linked:
            out["link"] = {"created": False, "existing": True}
            return out
        posted = _post_link(config, execute, type_id=link_type["id"],
                            parent_key=parent["key"], idea_key=key)
        if isinstance(posted, TrackerError):
            out["link"] = {"created": False,
                           "error": {"class": posted.cls.value, "message": posted.message},
                           "retry": _retry(key, parent["key"])}
        else:
            out["link"] = {"created": True, "existing": False}
        return out

    def reuse(c: dict) -> dict:
        return settled({"id": c["id"], "key": c["key"], "title": c["title"],
                        "url": f"{base}/browse/{c['key']}" if isinstance(base, str) else None,
                        "created": False}, linked=bool(candidates))

    marked: Any = []
    if not candidates:
        # Nothing linked: an earlier run may have created the parent and
        # failed to link it. Its marker finds it, with no local record.
        marked = _marked_parents(config, execute, key, level)
        if isinstance(marked, TrackerError):
            return marked
    pool = candidates or marked
    if use is not None:
        chosen = next((c for c in pool if c["key"] == use.strip()), None)
        if chosen is None:
            return TrackerError(
                ErrorClass.INVALID_INPUT,
                f"--use {use!r} is not one of the idea's parents: "
                f"{[c['key'] for c in pool]}",
                subtype="use", details={"candidates": pool})
        return reuse(chosen)
    if len(pool) == 1:
        return reuse(pool[0])
    if len(pool) > 1:
        return TrackerError(
            ErrorClass.CONFLICT,
            f"idea {key} has several "
            + ("delivery-linked parents" if candidates else
               "parent-level issues carrying its marker label")
            + "; choose one and rerun with --use <key>",
            subtype="several_parents",
            details={"normalized": "parent", "candidates": pool,
                     "notReused": not_reused})

    type_id = _creation_type(level)
    if isinstance(type_id, TrackerError):
        return type_id
    from .lifecycle.providers import create_jira  # noqa: PLC0415
    create_config = copy.deepcopy(config)
    create_config["tracker"]["resolved"]["destination"]["issueTypeId"] = type_id
    title = _dict(raw.get("fields")).get("summary") or key
    made = create_jira(create_config, execute, title=title, body=body,
                       labels=[_marker(key)])
    if isinstance(made, TrackerError):
        return made
    out = settled({"id": made["id"], "key": made["identifier"], "title": title,
                   "url": made.get("url"), "created": True}, linked=False)
    if made.get("degraded") is not None:
        out["degraded"] = made["degraded"]
    return out


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def run(flow_dir, verb: str, *, idea: Optional[str] = None,
        parent: Optional[str] = None, use: Optional[str] = None,
        body_file: Optional[str] = None, execute=None) -> tuple[str, int]:
    """`flowctl tracker idea read|parent|link`: one envelope, never raises."""
    from . import envelope  # noqa: PLC0415
    from .config_io import load_raw_config  # noqa: PLC0415
    from .executor import execute as default_execute  # noqa: PLC0415
    from .resolve_verb import bound_executor  # noqa: PLC0415

    config = load_raw_config(Path(flow_dir) / "config.json") or {}
    if _dict(config.get("tracker")).get("type") is None:
        return envelope.inactive()
    body = None
    if verb == "parent":
        try:
            body = Path(body_file or "").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return envelope.failure(TrackerError(
                ErrorClass.INVALID_INPUT, f"cannot read --body-file: {exc}",
                subtype="body_file"))
    ex = bound_executor(config, execute or default_execute)
    try:
        if verb == "read":
            out = read(config, idea, ex)
        elif verb == "parent":
            out = settle_parent(config, idea, ex, body=body or "", use=use)
        elif verb == "link":
            out = link(config, idea, parent, ex)
        else:
            out = TrackerError(ErrorClass.INVALID_INPUT,
                               f"unknown idea verb {verb!r}", subtype="verb")
    except Exception as exc:  # noqa: BLE001 - envelope boundary
        out = TrackerError(
            ErrorClass.TRANSPORT,
            f"idea {verb} failed on a malformed response: {type(exc).__name__}: {exc}",
            subtype="malformed_body")
    if isinstance(out, TrackerError):
        return envelope.failure(out)
    return envelope.success(out)
