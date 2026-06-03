# Linear GraphQL rung (headless / CI / Ralph)

Rung 2 of the Linear transport ladder ([linear-ladder.md](linear-ladder.md)): the
**Linear GraphQL API** via `LINEAR_API_KEY`. The headless-robust path — no MCP
server, no interactive OAuth, a **version-stable wire contract**. Use it when
`LINEAR_API_KEY` is set and no Linear MCP server is registered (CI, cron, Ralph,
any non-interactive host). It is driven with plain `curl` (or any HTTP client) —
fully scriptable.

This rung needs **no tool-name pin** (unlike MCP — see
[linear-mcp.md](linear-mcp.md)): the GraphQL schema names below are stable.

## Connection facts (pin these — they have sharp edges)

- **Endpoint:** `https://api.linear.app/graphql`
- **Auth header:** `Authorization: <LINEAR_API_KEY>` — **NO `Bearer ` prefix** for
  a personal API key. This is an **asymmetry vs the MCP rung** (and vs OAuth
  access tokens, which DO use `Bearer`). Getting this wrong returns
  `authentication required`.
- **Mutations:** `issueCreate` / `issueUpdate` / `commentCreate`.
- **id vs identifier:**
  - `issueUpdate(id:…)` and `issue(id:…)` accept **either** the UUID **or** the
    human identifier `WOR-17`.
  - `commentCreate(input:{issueId:…})` needs the **UUID** — `WOR-17` is rejected.
  - **Always store the UUID** as the durable dedupe key (`sync set-tracker-id`);
    surface `identifier` to humans only.
- **Rate limit is complexity-based, NOT request-count:**
  - ~**3,000,000 complexity points / hour / user** (API-key auth); a single query
    is capped at ~**10,000** points.
  - Exceeding it returns **HTTP 400** with a **`RATELIMITED`** error code — **not
    HTTP 429**. Do not treat 400 as a hard failure without checking the code.
  - **Mitigate proactively:** set an explicit `first:` on **every** connection
    (never an unbounded list), order by `updatedAt` desc so you fetch the newest
    first, and request only the fields you map. **Back off** on `RATELIMITED`
    (exponential; honor any reset hint) rather than failing the run.

## Auth + a minimal call

```bash
# Headless probe — `viewer` is the cheapest authenticated query.
curl -sS https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: ${LINEAR_API_KEY}" \
  --data '{"query":"query { viewer { id name } }"}'
#                                    ^ NO "Bearer " prefix for a personal API key.
```

A `data.viewer` result confirms the key + header are correct; an
`errors[].extensions.code == "AUTHENTICATION_ERROR"` means the header is wrong
(usually a stray `Bearer`).

## Detecting `RATELIMITED` (HTTP 400, not 429)

```bash
RESP=$(curl -sS -w '\n%{http_code}' https://api.linear.app/graphql \
  -H "Content-Type: application/json" -H "Authorization: ${LINEAR_API_KEY}" \
  --data "$QUERY")
CODE=$(printf '%s' "$RESP" | tail -n1)
BODY=$(printf '%s' "$RESP" | sed '$d')
if [ "$CODE" = "400" ] && printf '%s' "$BODY" | grep -q '"RATELIMITED"'; then
  # back off (exponential) and retry — do NOT fail the run
  : # sleep $((2 ** attempt)); retry
fi
```

## The six interface methods over GraphQL

Mapping wire ↔ normalized happens here, at the adapter boundary. Reconcile never
sees a GraphQL shape. (`$KEY` = `LINEAR_API_KEY`; `EP` =
`https://api.linear.app/graphql`. Bodies passed as GraphQL `variables`, not
string-interpolated, to avoid escaping bugs.)

### `fetchIssue(trackerId)` → normalized `issue` | not-found

```graphql
query ($id: String!) {
  issue(id: $id) {
    id identifier title description url updatedAt
    priority
    state { name type }
    labels(first: 50) { nodes { name } }
  }
}
```
- `id` accepts UUID or `WOR-17`.
- Map: `description`→`body`; `state.name`→`status.raw`; `(state.type + config
  map)`→`status.normalized`; `labels.nodes[].name`→`labels`.
- **not-found:** `data.issue` is `null` (deleted/archived) or `errors[]` present
  ⇒ return `not-found` — never raise. The skeleton emits an `errored` receipt +
  prompts/queues unlink (see [linear-ladder.md](linear-ladder.md) error contract).

### `writeIssue(issue)` → `{id, identifier, url}` (upsert)

```graphql
# CREATE (no issue.id):
mutation ($input: IssueCreateInput!) {
  issueCreate(input: $input) { success issue { id identifier url } }
}
# variables: { "input": { "teamId": "<uuid>", "title": "...",
#                          "description": "<body>", "labelIds": ["..."],
#                          "stateId": "<uuid>", "priority": 2 } }

# UPDATE (issue.id present):
mutation ($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) { success issue { id identifier url } }
}
# id accepts UUID or WOR-17; input carries only changed fields.
```
Return `issueCreate.issue` / `issueUpdate.issue`. On create, include the
`flow:<id>` label (resolve the label name → `labelId` once at config time) and/or
a `[<id>]` title prefix for the flow back-reference.

### `setStatus(trackerId, status)` → ok | errored

```graphql
mutation ($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: { stateId: $stateId }) { success }
}
```
Resolve the normalized status → the team's concrete `stateId` via the status map
(below). A `stateId` not belonging to the team ⇒ `errors[]` ⇒ return `errored`
(don't crash).

### `listComments(trackerId)` → normalized `comment[]`

```graphql
query ($id: String!, $first: Int!, $after: String) {
  issue(id: $id) {
    comments(first: $first, after: $after, orderBy: updatedAt) {
      nodes { id body createdAt user { name } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
```
- **Always set `first:`** (e.g. 50) and page via `after`/`endCursor` — never
  unbounded (complexity-limit hygiene).
- Map each: `user.name`→`author`; detect the `flow-evt:<event>` marker in `body`
  → set `marker` (flow's own echo, skipped on pull); genuine tracker comments get
  `marker:null` and pull into the spec sync log.

### `postComment(trackerId, body)` → normalized `comment`

```graphql
mutation ($input: CommentCreateInput!) {
  commentCreate(input: $input) { success comment { id body createdAt user { name } } }
}
# variables: { "input": { "issueId": "<UUID — NOT WOR-17>", "body": "<markdown
#              with the flow-evt marker line>" } }
```
**`issueId` must be the UUID** — this is the one place `WOR-17` is rejected.

### `readStatus(trackerId)` → normalized `status`

Derived from the `fetchIssue` `state { name type }` — no separate call.

## Status map (GraphQL)

Build the team's name/type → `stateId` map **once at config time** so `setStatus`
can resolve a normalized status back to a concrete `stateId`:

```graphql
query ($team: String!) {
  workflowStates(first: 100, filter: { team: { name: { eq: $team } } }) {
    nodes { id name type }
  }
}
# type ∈ backlog | unstarted | started | completed | canceled
# `first: 100` — workflowStates IS a connection; bound it like every other
# connection (a team's workflow has far fewer than 100 states, so one page).
```
Fold into `tracker.perTracker.statusMap`. The default `state.type` → normalized
mapping (shared with the MCP rung) is the status table in
[linear-ladder.md](linear-ladder.md). Resolve the `teamId` once too
(`teams(first: 1, filter:{ key:{ eq:"WOR" } }){ nodes { id } }`) for `issueCreate`.

## Gotchas

- **No `Bearer` for a personal API key** — the single most common auth failure;
  the asymmetry vs MCP/OAuth is real.
- **`commentCreate` needs the UUID**, not `WOR-17` — unlike `issueUpdate`/`issue`,
  which accept either.
- **`RATELIMITED` is HTTP 400, not 429** — check the error `code`, back off, don't
  fail the run. Mitigate with `first:` on every connection + `updatedAt` desc.
- **Pass bodies as `variables`, not string interpolation** — avoids markdown
  newline/quote escaping bugs (a round-trip-spike failure mode).
- **Version-stable** — no tool-name pin needed; the schema names above are
  durable, which is exactly why this is the headless/Ralph-safe rung.
