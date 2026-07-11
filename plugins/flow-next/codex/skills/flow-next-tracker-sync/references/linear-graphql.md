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
- **Mutations:** `issueCreate` / `issueUpdate` / `commentCreate`; for the `makePr` event, `attachmentLinkURL`; for dependency projection (fn-64.3), `issueRelationCreate`.
- **PR linkage (`makePr` → Linear Diffs):** attach the PR as a *rich* GitHub attachment with `attachmentLinkURL(issueId: <uuid>, url: <pr-url>)` — Linear auto-detects the GitHub URL and creates a status-syncing attachment. (The dedicated `attachmentLinkGitHubPR(issueId, url)` exists too; `attachmentLinkURL` is the safer public surface.) Do **NOT** use a plain `attachmentCreate` — that makes a dumb link with no status sync / diff. **The diff view itself is rendered by Linear from the GitHub PR — you cannot create a diff via API**; it appears once the PR is auto-linked by identifier (make-pr §4.6a puts a non-closing `Ref WOR-N` in the PR body) AND the workspace has the GitHub integration with code access + the user's personal GitHub connection. The attachment is the belt; the body `Ref` is the suspenders.
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
# ^ NO "Bearer " prefix for a personal API key.
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

## The core interface methods over GraphQL

The original **six** core methods plus the enumeration method `listOpenIssues`
(fn-68.2); the dependency-projection pair (`listIssueRelations` /
`setIssueRelation`, fn-64.3) is its own section below — together the **nine-method**
interface ([adapter-interface.md](adapter-interface.md)). Mapping wire ↔ normalized
happens here, at the adapter boundary. Reconcile never sees a GraphQL shape.
(`$KEY` = `LINEAR_API_KEY`; `EP` = `https://api.linear.app/graphql`. Bodies passed
as GraphQL `variables`, not string-interpolated, to avoid escaping bugs.)

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
# "description": "<body>", "labelIds": ["..."],
# "stateId": "<uuid>", "priority": 2 } }

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
 nodes { id body createdAt user { id name } botActor { id name } parent { id } }
 pageInfo { hasNextPage endCursor }
 }
 }
}
```
- **Always set `first:`** (e.g. 50) and page via `after`/`endCursor` — never
 unbounded (complexity-limit hygiene).
- **`authorAuthority` (fn-68 R15 security — populate it here, the producer):**
 `botActor` present ⇒ `bot`; else the `user` maps to `writer` when a workspace
 **member** (the user's `admin`/`member` role / workspace membership), `outsider`
 for a guest, and `unknown` when membership can't be resolved (⇒ the answer valve
 fails closed). This is why the query fetches `user { id name }` + `botActor`.
- Map each: `user.name`→`author`; detect the **closed flow-owned marker set** in
 `body` → set `marker` (flow's own echo, skipped on pull): `flow-next:sync`→
 `flow-evt:<event>`, `flow-next:question`→`flow-evt:question`, rolling
 `flow-next:status`→`flow-evt:status` ([adapter-interface.md](adapter-interface.md)
 § `comment` marker-vocabulary table). **`flow-next:answer` is the human reply —
 `marker` stays `null`, but surface its `id`** for the answer round-trip. Genuine
 tracker comments get `marker:null` and pull into the spec sync log.
- **`parent { id }` → the optional `comment.parentId`** (fn-68 R15): Linear threads
 replies, so a human's answer posted *under* a `flow-next:question` comment carries
 that question comment's id. The question-valve answer round-trip ([adapter-interface.md](adapter-interface.md)
 § `comment`; [steps.md](../steps.md) Phase 7) matches the `<!-- flow-next:answer id=… -->`
 reply to its question by **thread (parentId) + id**. A top-level comment has
 `parent == null` → `parentId: null` (matched by the body `id` marker alone, like
 the flat-tracker rung).

### `postComment(trackerId, body)` → normalized `comment`

```graphql
mutation ($input: CommentCreateInput!) {
 commentCreate(input: $input) { success comment { id body createdAt user { name } } }
}
# variables: { "input": { "issueId": "<UUID — NOT WOR-17>", "body": "<markdown
# with the flow-evt marker line>" } }
```
**`issueId` must be the UUID** — this is the one place `WOR-17` is rejected.

### `readStatus(trackerId)` → normalized `status`

Derived from the `fetchIssue` `state { name type }` — no separate call.

### `listOpenIssues(filter) → issue[]` (fn-68 — enumeration)

Enumerate the **promoted lane** — open issues at the **exact** `tracker.readyState`
workflow-state name. Filter on the state **name** (not `state.type`), the same exact
match the readiness projection uses ([status-sync.md](status-sync.md)). Bound the
team to `tracker.perTracker.teamId` when set.

The skill **builds the `$filter` object** and passes it whole — it includes the
`team` key ONLY when `tracker.perTracker.teamId` is set, `state` always. The
template never hardcodes a `team` predicate, so a null team is never sent (an
inline `team: { id: { eq: null } }` mis-filters to teamless issues):

```graphql
query ($filter: IssueFilter!, $first: Int!, $after: String) {
 issues(first: $first, after: $after, filter: $filter) {
 nodes { id identifier title description url updatedAt
 state { name type } labels(first: 25) { nodes { name } } priority }
 pageInfo { hasNextPage endCursor }
 }
}
# $filter — built by the skill (state always; team ONLY when teamId is set):
# teamId set → { "state": { "name": { "eqIgnoreCase": "<readyState>" } },
# "team": { "id": { "eq": "<teamId>" } } }
# no teamId → { "state": { "name": { "eqIgnoreCase": "<readyState>" } } } # team key OMITTED
# $first: 50
```

- **`state: { name: { eqIgnoreCase } }` is the exact-lane filter** — no `type`
 predicate, no ordering, no "and-later" states. `readyState` matching is exact
 (adapter-interface.md § Enumeration transport); an ordered promoted-set is a
 future config, never inferred here.
- **Map each node into the normalized `issue` struct** via the same firewall table
 the `fetchIssue` map uses ([linear-ladder.md](linear-ladder.md) § Normalized
 mapping) — `description`→`body`, `state.name`→`status.raw`, `labels.nodes[].name`
 →`labels`, etc. A tracker-only ticket (no `flow:<id>` label) maps identically.
 **Linkage is decided authoritatively by the local sync state** (the linked
 tracker-ids the skill recorded), with the `flow:<id>` label only a corroborating
 hint — a **truncated** label set (one that hit the `labels(first:)` bound) is
 **never** read as "unlinked": a many-label issue could carry the back-reference
 past the bound, so a *linked* issue is never mis-classified as a tracker-only one.
- **Always set `first:`** and page via `after`/`endCursor` — never unbounded
 (complexity-limit hygiene), same as `listComments`. **Nested connections are
 bounded too** — `labels(first: 25)` (generous headroom for the `flow:<id>`
 back-reference + readyState label; and linkage is confirmed from the local sync
 state regardless of the bound, per the mapping note above).
- **Omit the `team` predicate when `tracker.perTracker.teamId` is unset.** Build
 the `filter` object conditionally — include `team: { id: { eq: $team } }` ONLY
 when a teamId is configured; with no team, the filter carries `state` alone. A
 literal `team: { id: { eq: null } }` mis-filters (matches teamless issues / errors),
 so the predicate is *added*, never *nulled*.
- **`tracker.readyState` unset ⇒ the skill never calls this** (steps.md Phase 7a
 short-circuits to a `noop` + note); reached with an empty `$state` it returns
 `[]` + `noop`. No transport reachable ⇒ `noop` + receipt note, `[]`.

## Relation transport (dependency projection, fn-64.3)

The two relation methods from [adapter-interface.md](adapter-interface.md) over
GraphQL. **Direction convention** (stated once there): `from` is-blocked-by `to`;
flow's `depends_on_epics:[B]` on spec A projects to
`setIssueRelation(issue=A, blockedBy=B)`.

> **Enum is lowercase `blocks` / `related` / `duplicate`** (`IssueRelationType`) —
> there is **no `blocked_by` enum value**. "A blocked by B" is a `blocks` edge
> pointing the other way: the **blocker** blocks the **blocked**, i.e.
> `issueId: B` (blocker), `relatedIssueId: A` (blocked), `type: blocks`. flow
> projects exactly this one edge kind — never emit `related` / `duplicate`.

### `listIssueRelations(issue)` → normalized `relation[]` | errored

A blocked-by edge can appear from **either** endpoint: as a `relations` node on
the blocked issue OR as an `inverseRelations` node on the blocking issue. **Query
BOTH** (each connection REQUIRES an explicit `first:` — Linear rejects an unbounded
connection and it counts against the complexity budget; see the rate-limit note
above and memory `linear-graphql-every-nodes-connection`):

```graphql
query ($id: String!, $first: Int!) {
 issue(id: $id) {
 id identifier
 relations(first: $first) {
 nodes { type relatedIssue { id identifier } }
 }
 inverseRelations(first: $first) {
 nodes { type issue { id identifier } }
 }
 }
}
# $first e.g. 50 — bound BOTH connections; page via pageInfo if an issue ever
# carries more than $first relations of a kind.
```

- Keep only `type == "blocks"` nodes (drop `related` / `duplicate`).
- **Canonicalize each edge to one direction before comparing.** A `blocks` node
 in `relations` means *this issue blocks relatedIssue* → canonical
 `{from: relatedIssue, to: this}` (relatedIssue is-blocked-by this). A `blocks`
 node in `inverseRelations` means *the node's `issue` blocks this issue* →
 canonical `{from: this, to: node.issue}` (this is-blocked-by node.issue). Map
 both into the normalized `{from, to, type:"blocks", source:"unknown", linkPresent:true}`
 so the same edge seen from either endpoint dedupes to one entry — otherwise an
 inverse-duplicate slips past read-before-write. `linkPresent` is always `true` — a
 Linear native relation **is** the tracker-visible link (no separate-block split like
 GitLab; Linear never emits `linkPresent:false`).
- `source` is `"unknown"` — Linear records no relation authorship; the flow-side
 `depRelations` ledger (fn-64.1) is the provenance authority.
- On `data.issue == null` / `errors[]`: return `errored` — never raise.

### `setIssueRelation(issue, blockedBy)` → ok | errored | noop

```graphql
# READ-BEFORE-WRITE (mandatory): listIssueRelations(issue) first; if the
# (issue is-blocked-by blockedBy) edge already exists (in EITHER relations or
# inverseRelations, after canonicalization) → return noop, skip the mutation.
mutation ($issueId: String!, $relatedIssueId: String!) {
 issueRelationCreate(input: {
 issueId: $relatedIssueId, # the BLOCKER (= flow `to` / blockedBy)
 relatedIssueId: $issueId, # the BLOCKED (= flow `from` / issue)
 type: blocks
 }) { success issueRelation { id } }
}
# "A blocked by B": issueId=B (blocker), relatedIssueId=A (blocked), type: blocks.
# (Variable names above bind to the flow operands: $issueId = A = the blocked
# issue passed as `issue`; $relatedIssueId = B = `blockedBy`. The mutation's
# OWN fields invert them — issueId:B, relatedIssueId:A — because Linear's
# `blocks` edge points blocker→blocked.)
```

- `issueRelationCreate` is **not reliably idempotent** (a second call can create a
 duplicate relation), which is exactly why the read-before-write pre-check is
 mandatory on this rung — unlike the MCP rung's append-only `blockedBy`.
- `issueId` / `relatedIssueId` accept UUID or `WOR-17`. Prefer the stored UUIDs.
- On success → ok (skill records the edge in the `depRelations` ledger). On
 `errors[]` / `success:false` → `errored`, never raise. `issueRelationCreate`
 only ever **adds** — it cannot remove a human's manual relation (R6).

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
- **`IssueRelationType` is lowercase `blocks`** — there is no `blocked_by` enum.
 "A blocked by B" = `issueRelationCreate(issueId:B, relatedIssueId:A, type:blocks)`
 (blocker→blocked). Get the operands backwards and the board shows the block the
 wrong way round.
- **Dedup needs BOTH `relations` AND `inverseRelations`**, each with an explicit
 `first:`, canonicalized to one direction — the same edge is visible from either
 endpoint, and `issueRelationCreate` is not idempotent, so a one-sided read
 silently duplicates the relation on re-run.
- **Linear normalizes markdown on save - the stored `description` is NOT the string
 you sent** (confirmed live 2026-07-11): slash-joined filenames like
 `CLAUDE.md/AGENTS.md` get auto-linkified into `[..](<http://...>)` links, blank
 lines are inserted before list blocks, and a list item whose text starts with `>`
 is rewritten into a blockquote. Consequence: after every `issueCreate`/`issueUpdate`
 that a merge-base snapshot follows, re-`fetchIssue` and snapshot the STORED body,
 never the sent render — body-merge.md Step 5 § Fetch-back rule (a sent-render base
 produced a 149-line false divergence with zero human edits).
