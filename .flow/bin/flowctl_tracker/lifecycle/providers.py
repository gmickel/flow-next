"""Per-provider create → normalized {id, identifier, url} (fn-140.2)."""

from __future__ import annotations

from ..types import ErrorClass, TrackerError
from .helpers import Execute, Result, destination, tracker_type


def create_github(config: dict, execute: Execute, *, title: str, body: str
                  ) -> Result:
    from ..wire import _cli, _gh_repo, _github_durable  # noqa: PLC0415
    dest = destination(config)
    if isinstance(dest, TrackerError):
        return dest
    repo = _gh_repo(dest)
    if isinstance(repo, TrackerError):
        return repo
    raw = _cli(execute, "github", config, "lifecycle-create", "POST",
               f"repos/{repo}/issues", body={"title": title, "body": body})
    if isinstance(raw, TrackerError):
        return raw
    if not isinstance(raw, dict):
        return TrackerError(ErrorClass.TRANSPORT, "github create returned no object",
                            subtype="malformed_body")
    durable = _github_durable(raw)
    number = raw.get("number")
    if durable is None or number is None:
        return TrackerError(ErrorClass.TRANSPORT,
                            "github create missing node_id/number",
                            subtype="malformed_body")
    acknowledged = raw.get("body")
    if not isinstance(acknowledged, str):
        acknowledged = body
    return {"id": durable, "identifier": f"#{number}",
            "url": raw.get("html_url") or raw.get("url"),
            "bodyWritten": acknowledged}


def create_gitlab(config: dict, execute: Execute, *, title: str, body: str
                  ) -> Result:
    from ..wire import _cli, _gl_project, _gitlab_durable  # noqa: PLC0415
    dest = destination(config)
    if isinstance(dest, TrackerError):
        return dest
    pid = _gl_project(dest)
    if isinstance(pid, TrackerError):
        return pid
    raw = _cli(execute, "gitlab", config, "lifecycle-create", "POST",
               f"projects/{pid}/issues",
               body={"title": title, "description": body})
    if isinstance(raw, TrackerError):
        return raw
    if not isinstance(raw, dict):
        return TrackerError(ErrorClass.TRANSPORT, "gitlab create returned no object",
                            subtype="malformed_body")
    durable = _gitlab_durable(raw)
    iid = raw.get("iid")
    if durable is None or iid is None:
        return TrackerError(ErrorClass.TRANSPORT,
                            "gitlab create missing id/iid",
                            subtype="malformed_body")
    refs = raw.get("references")
    full = refs.get("full") if isinstance(refs, dict) else None
    if isinstance(full, str) and full:
        ident = full
    else:
        path = dest.get("projectPath")
        ident = f"{path}#{iid}" if isinstance(path, str) and path else f"#{iid}"
    acknowledged = raw.get("description")
    if not isinstance(acknowledged, str):
        acknowledged = body
    return {"id": durable, "identifier": ident, "url": raw.get("web_url"),
            "bodyWritten": acknowledged}


def create_linear(config: dict, execute: Execute, *, title: str, body: str
                  ) -> Result:
    from ..wire import _gql  # noqa: PLC0415
    dest = destination(config)
    if isinstance(dest, TrackerError):
        return dest
    team_id = dest.get("teamId")
    if not isinstance(team_id, str) or not team_id:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "linear destination missing teamId",
                            subtype="destination")
    data = _gql(execute, "lifecycle-create",
                "mutation($input: IssueCreateInput!) { "
                "issueCreate(input: $input) { success "
                "issue { id identifier url description } } }",
                {"input": {"teamId": team_id, "title": title, "description": body}})
    if isinstance(data, TrackerError):
        return data
    payload = data.get("issueCreate")
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return TrackerError(ErrorClass.TRANSPORT, "linear issueCreate reported failure",
                            subtype="mutation_failed")
    issue = payload.get("issue")
    if not isinstance(issue, dict) or not issue.get("id"):
        return TrackerError(ErrorClass.TRANSPORT,
                            "linear issueCreate missing issue.id",
                            subtype="malformed_body")
    acknowledged = issue.get("description")
    if not isinstance(acknowledged, str):
        acknowledged = body
    return {"id": issue["id"], "identifier": issue.get("identifier"),
            "url": issue.get("url"), "bodyWritten": acknowledged}


def create_jira(config: dict, execute: Execute, *, title: str, body: str
                ) -> Result:
    from ..wire import _jira, _jira_base, _jira_issue_key  # noqa: PLC0415
    dest = destination(config)
    if isinstance(dest, TrackerError):
        return dest
    base = _jira_base(config, dest)
    if isinstance(base, TrackerError):
        return base
    project_id = dest.get("projectId")
    issue_type_id = dest.get("issueTypeId")
    if not project_id or not issue_type_id:
        return TrackerError(ErrorClass.UNRESOLVED,
                            "jira destination missing projectId/issueTypeId",
                            subtype="destination")
    # fn-140 R16 intentionally pins Jira Cloud and DC body operations to v2:
    # resolved_cache migrates perTracker apiVersion 3 -> 2 and destination
    # resolution emits 2. This avoids an ADF boundary in the deterministic
    # verb surface and gives byte-identical plain-string round trips.
    #
    # Jira rejects fields omitted from the selected issue type's CREATE
    # screen. Include Description by default, but omit it when createmeta
    # positively reports a non-empty field map without `description`.
    # Unavailable/legacy createmeta keeps the common include behavior.
    description_settable = True
    meta = _jira(
        execute, "lifecycle-create-meta", "GET",
        f"{base}/rest/api/2/issue/createmeta"
        f"?projectIds={project_id}&issuetypeIds={issue_type_id}"
        "&expand=projects.issuetypes.fields",
        idempotent=True,
    )
    if isinstance(meta, dict):
        for project in meta.get("projects") or []:
            if not isinstance(project, dict):
                continue
            for issue_type in project.get("issuetypes") or []:
                if (not isinstance(issue_type, dict)
                        or str(issue_type.get("id")) != str(issue_type_id)):
                    continue
                fields = issue_type.get("fields")
                if isinstance(fields, dict) and fields and "description" not in fields:
                    description_settable = False
                break
    fields = {
        "project": {"id": str(project_id)},
        "issuetype": {"id": str(issue_type_id)},
        "summary": title,
    }
    if description_settable:
        fields["description"] = body
    raw = _jira(execute, "lifecycle-create", "POST",
                f"{base}/rest/api/2/issue",
                body={"fields": fields})
    if isinstance(raw, TrackerError):
        return raw
    if not isinstance(raw, dict) or raw.get("id") is None or not raw.get("key"):
        return TrackerError(ErrorClass.TRANSPORT,
                            "jira create missing id/key",
                            subtype="malformed_body")
    # Persist the server key verbatim, including DC custom keys
    # (MY_LONG_PROJECT_KEY-7: underscores, >10 chars). UNVERIFIED on live Jira
    # Data Center (Cloud cannot reproduce custom keys - fn-140 R17); verified
    # against prose only.
    key = _jira_issue_key(str(raw["key"]))
    if isinstance(key, TrackerError):
        return key
    out = {"id": str(raw["id"]), "identifier": key,
           "url": f"{base}/browse/{key}",
           # The paired-base seed must describe what CREATE actually wrote,
           # not what the caller asked to write. When Description is absent
           # from the create screen, the local body remains a pending change
           # for the following sync-body push.
           "bodyWritten": body if description_settable else ""}
    if not description_settable:
        out["seedFlowBody"] = ""
        out["degraded"] = {
            "kind": "jira_create_field_omitted",
            "field": "description",
            "reason": "not_on_create_screen",
        }
    return out


_CREATE = {
    "github": create_github,
    "gitlab": create_gitlab,
    "linear": create_linear,
    "jira": create_jira,
}


def provider_create(config: dict, execute: Execute, *, title: str, body: str
                    ) -> Result:
    provider = tracker_type(config)
    if provider is None:
        return TrackerError(ErrorClass.INACTIVE, "tracker bridge is inactive")
    return _CREATE[provider](config, execute, title=title, body=body)
