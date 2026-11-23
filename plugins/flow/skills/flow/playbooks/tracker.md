# Tracker

Trackers are optional and linking is explicit: do nothing here unless configured or asked. Run tracker calls through the `edge` launcher the router names (`--help` lists flags), or use the host's tracker connection when `edge` cannot reach it.

## Ownership and writes

Before build start, the issue is the source where people discuss. At build start, snapshot it into the spec (`spec.md`); the spec file is the contract from then on. To link an existing issue, read it and write its durable `id`, `identifier`, and `url` into spec frontmatter. If the issue changes after the snapshot, ask the person—never merge them. Direct changes have no spec file; the issue is the request.

Flow writes back only status moves, owner questions, un-readying when a person is needed, a short merge summary, and an optional one-way spec push at handover. Large specs exceed description limits, so deliver them via PR or `wire attach`.

## Verbs (`edge tracker ...`)

- `resolve`: fill in and check `tracker.resolved`.
- `wire read` / `wire comment-list`: read an issue (`snapshot` hash included) and comments.
- `wire list-open`: list ready (or all open) issues.
- `status`: move a linked spec's status (`in_progress`, `in_review`, `done`; pass `--branch` after merge since the session may have left it).
- `wire link-pr`: link a PR URL.
- `wire question`: post a deduplicated owner question.
- `wire unready`: move out of `tracker.readyState`.
- `wire comment-add`: post a comment (such as a merge summary).
- `wire update`: optional one-way spec push.
- `create` / `create-first`: create and link an issue (optional `--parent`), or before a local spec.
- `relate`: relate two linked specs (`blocked-by`).
- `idea read` / `idea parent` / `idea link`: discovery ideas (below).

## Discovery ideas

Items in `tracker.perTracker.ideaProjectKeys` are upstream discovery ideas—attended-only (stop `NEEDS_HUMAN` if unattended) and read-only: never edit, comment on, or link a spec to them. Run `idea read` for body, comments (warn if truncated or empty), and delivery links; write local specs citing the idea first. Run `idea parent` to reuse or create one delivery parent linked to the idea (on `several_parents`, ask and rerun with `--use`; retry failed links with `idea link`), then create child issues with `create --parent` and `relate`.

## Configuration

In `.flow/config.json`, set `tracker.type` (`github`, `gitlab`, `linear`, `jira`), optional `tracker.readyState`, and `tracker.perTracker`: none for GitHub; `project` (optional `host`) for GitLab; `teamId` for Linear; `baseUrl`, `projectKey` (optional `issueType`, `authScheme: "bearer-pat"`, `ideaProjectKeys`) for Jira. Credentials come from `gh`/`glab` (or `GH_TOKEN`/`GITLAB_TOKEN`), `LINEAR_API_KEY`, or `JIRA_EMAIL` + `JIRA_API_TOKEN` (`JIRA_PAT` for `bearer-pat`), plus `FLOW_TRACKER_TOKEN_COMMAND_<PROVIDER>` or `tracker.perTracker.tokenCommand` for Linear/Jira. Run `edge tracker resolve` to populate and check the rest.
