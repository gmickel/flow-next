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
    return {"id": durable, "identifier": f"#{number}",
            "url": raw.get("html_url") or raw.get("url")}


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
    return {"id": durable, "identifier": ident, "url": raw.get("web_url")}


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
                "issueCreate(input: $input) { success issue { id identifier url } } }",
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
    return {"id": issue["id"], "identifier": issue.get("identifier"),
            "url": issue.get("url")}


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
    raw = _jira(execute, "lifecycle-create", "POST",
                f"{base}/rest/api/2/issue",
                body={"fields": {
                    "project": {"id": str(project_id)},
                    "issuetype": {"id": str(issue_type_id)},
                    "summary": title,
                    "description": body,
                }})
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
    return {"id": str(raw["id"]), "identifier": key,
            "url": f"{base}/browse/{key}"}


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
