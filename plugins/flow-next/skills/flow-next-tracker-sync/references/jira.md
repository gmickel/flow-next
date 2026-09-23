# Jira tracker transport shape

Flowctl uses Jira REST through the deterministic HTTP executor. It supports
Cloud and Data Center/Server deployment shapes selected during discovery.
Skill prose never constructs Jira requests.

## Deployment and addressing

| Shape | Authentication | API version | Body form |
|---|---|---|---|
| Cloud | email plus API token | 2 by default | wiki markup, converted from and to Markdown |
| Data Center/Server | bearer PAT | 2 by default | wiki markup, converted from and to Markdown |

The resolved destination stores base URL, project key, API version,
authentication scheme, issue type, status ids, and capabilities. Custom-domain
ambiguity is resolved in the discovery ceremony and persisted. Runtime never
re-races credentials to change deployment shape.

- durable issue identity: Jira numeric/string id;
- display identity: `KEY-N`;
- project keys accept upper-case letters, digits, and underscore;
- issue and comment bodies are converted to wiki markup on write and
  decoded back to Markdown on read;
- comment responses do not expose parent issue id, so response-side parent
  identity is unavailable.

## Operation mapping

| Normalized operation | Jira shape |
|---|---|
| issue read/update | issue resource with selected fields |
| comments | paginated issue comments |
| labels | issue label array |
| assignees | account/user identifiers appropriate to deployment |
| status | transition id resolved for normalized slot |
| list-open | injection-safe JQL scoped to project and exact ready status |
| list-states | v2 project statuses endpoint, scoped to the resolved issue type, deduped by id; read-only |
| relation | native issue link using configured blocking type |
| attachment | multipart attachment endpoint |

Cloud list-open uses cursor-style search; Data Center/Server uses start-offset
search. Pagination is hidden by the adapter.

## Body fidelity

A version 2 text field holds Jira wiki markup and never interprets Markdown.
Flowctl converts every issue and comment body from Markdown to wiki markup
before the write, and decodes the stored wiki markup back to Markdown once,
where a read extracts it. Merge bases, the echo fence, and comment dedup all
compare the decoded Markdown. Decoding yields stable canonical Markdown, not
the original spelling. Constructs outside the supported subset (headings,
bold, italic, inline code, links, fenced code, simple pipe tables,
blockquotes, nested lists) stay literal text, and wiki fragments added in
Jira decode unchanged. Sync markers pass through verbatim and stay visible in
Jira, because wiki markup has no comment syntax.

Correct display requires the Wiki Style Renderer on the description and
comment fields. The Default Text Renderer shows the markup literally.
Flowctl does not detect the renderer.

Version 2 stays the resolved version for both deployment shapes, with this
conversion. The byte-exact round trip of the stored string does not show
that the body renders correctly. Version 3 would need ADF, and Data
Center has no ADF.

An issue linked before this conversion still holds raw Markdown. When its
stored body still equals the recorded tracker base, push and reconcile
convert it in place. Pull refuses it with a `jira_body_unconverted` conflict
until a push or reconcile has run. A body edited since the base takes the
normal edit or conflict path.

## Status and relations

Status changes use resolved transition ids. An absent or ambiguous mapping is a
structured unresolved/conflict result, not a guessed transition.

Blocked-by uses Jira's directional issue-link shape with the configured link
type. The blocker and blocked operands follow the normalized contract in
`adapter-interface.md`; no body-block fallback is used.
