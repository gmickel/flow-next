# Linear transport shape

Linear has two reachable shapes:

1. **MCP:** host-visible OAuth tools, used only for discovery or an explicitly
 authorized create when shell credentials are unavailable.
2. **GraphQL:** deterministic flowctl transport for normal lifecycle and wire
 verbs.

MCP is not a general runtime fallback. After an MCP create, pass its identifier,
durable id when available, and URL to `tracker persist-external`. Flowctl
resolves missing durable identity through GraphQL before writing local state.

The GraphQL destination records the team id, team key, workflow state ids, and
capabilities under `tracker.resolved`. All operations use variables, never
string interpolation of user content.

## Shapes

| Normalized operation | Linear shape |
|---|---|
| read | issue by durable UUID |
| create/update | issue create or update mutation |
| comments | paginated issue comments |
| labels | issue label ids |
| assignees | issue assignee ids |
| status | workflow state id |
| relation | native issue relation |
| list-open | team plus configured ready-state filter; unset `tracker.readyState` = explicit `unresolved`/`ready_state` refusal, never a silent empty (fn-182, #311) |
| attachment | upload negotiation followed by anonymous presigned upload |

Linear bodies are Markdown. Comment responses expose parent issue identity only
when the selection includes `issue { id }`. Native relations and attachments
are capability-supported.

Read [linear-mcp.md](linear-mcp.md) only for an MCP continuation. Read
[linear-graphql.md](linear-graphql.md) for deterministic transport review.
