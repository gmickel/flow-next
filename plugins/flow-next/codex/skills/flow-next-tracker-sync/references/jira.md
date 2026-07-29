# Jira tracker transport shape

Flowctl uses Jira REST through the deterministic HTTP executor. It supports
Cloud and Data Center/Server deployment shapes selected during discovery.
Skill prose never constructs Jira requests.

## Deployment and addressing

| Shape | Authentication | API version | Body form |
|---|---|---|---|
| Cloud | email plus API token | 2 by default | plain string/renderer form normalized to Markdown |
| Data Center/Server | bearer PAT | 2 by default | plain string/renderer form normalized to Markdown |

The resolved destination stores base URL, project key, API version,
authentication scheme, issue type, status ids, and capabilities. Custom-domain
ambiguity is resolved in the discovery ceremony and persisted. Runtime never
re-races credentials to change deployment shape.

- durable issue identity: Jira numeric/string id;
- display identity: `KEY-N`;
- project keys accept upper-case letters, digits, and underscore;
- issue and comment bodies normalize to Markdown;
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
| relation | native issue link using configured blocking type |
| attachment | multipart attachment endpoint |

Cloud list-open uses cursor-style search; Data Center/Server uses start-offset
search. Pagination is hidden by the adapter.

## Body fidelity

Resolution and migration converge on version 2 for both deployment shapes
because plain string bodies round-trip byte-exact in the measured shape.
ADF is therefore not selected as the resolved body format.

## Status and relations

Status changes use resolved transition ids. An absent or ambiguous mapping is a
structured unresolved/conflict result, not a guessed transition.

Blocked-by uses Jira's directional issue-link shape with the configured link
type. The blocker and blocked operands follow the normalized contract in
`adapter-interface.md`; no body-block fallback is used.
