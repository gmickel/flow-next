# Linear MCP rung (interactive default)

Rung 1 of the Linear transport ladder ([linear-ladder.md](linear-ladder.md)): the
**Linear MCP server** registered on the host. The interactive convenience path —
the server handles OAuth/token, so there is no key to manage. Use it when a
Linear MCP server is present in the host's tool list; otherwise the ladder falls
to the GraphQL rung ([linear-graphql.md](linear-graphql.md)).

The MCP tool surface is host-agent-visible: the agent calls the tools directly
(`save_issue`, `get_issue`, …) — there is no shell command. Pass markdown bodies
**literally** (real newlines, no `\n` escape sequences — the server's own
instruction).

## Tool-name pin (verified — re-verify at build; MCP tool names drift)

> **CLAUDE.md-style breadcrumb.** Linear's official MCP server uses **upsert
> verbs** — `save_*`, NOT `create_*`/`update_*`. The same verb creates or
> updates depending on whether an `id` is passed. These names drift across server
> versions; the table below was **verified 2026-06-03** against the registered
> Linear MCP server in this environment (tool prefix
> `mcp__claude_ai_Linear__*`). Re-verify by inspecting the host tool list before
> relying on them on a different host/version. The GraphQL rung needs no pin (its
> wire contract is version-stable).

| Interface method | Linear MCP tool (verified 2026-06-03) | Key params |
|---|---|---|
| `writeIssue` (upsert) | **`save_issue`** | create: `team`+`title` required, `description` (body, markdown). update: pass `id` (UUID **or** identifier `WOR-17`) + changed fields. `state` (state type/name/ID) sets status. `labels`, `priority` (0=None,1=Urgent,2=High,3=Medium,4=Low). `assignee` (NOT `assigneeId`). **Returns the identifier (`WOR-17`-form) as `id` — never the UUID** (verified 2026-06-09). |
| `fetchIssue` | **`get_issue`** | `id` (UUID or identifier). `includeRelations:true` for blocking/related. Returns title, `description`, `state`, `priority`, `labels`, `url`, `updatedAt`, git branch name. **The returned `id` is the identifier, not the UUID** (verified 2026-06-09). |
| `listComments` | **`list_comments`** | `issueId` (UUID or identifier). `orderBy: createdAt|updatedAt`, `limit` (default 50, max 250), `cursor` for paging. |
| `postComment` | **`save_comment`** | create top-level: `issueId` + `body`. update: `id` + `body`. reply: `parentId` + `body`. |
| `listIssueRelations` | **`get_issue`** + `includeRelations:true` | `id` (UUID or identifier). Returns the issue's blocking/related/duplicate relations (fn-64.3). |
| `setIssueRelation` | **`save_issue`** + `blockedBy:[…]` | update form: `id` = the **blocked** issue + `blockedBy:[<blocker id/identifier>]`. **Append-only** — server doc: "existing relations are never removed" (fn-64.3). |
| status map build | **`list_issue_statuses`** | `team` (name or ID) → the team's workflow states (name + type + id) for the normalized-status map. |

Supporting tools used during the discovery/link ceremony (not part of the six
interface methods, but verified present): `list_teams`, `get_team`,
`list_issue_labels` / `create_issue_label`, `list_projects`, `list_users`, and
`get_issue_status` (validates the chosen `tracker.readyState` state resolves —
fn-58 ceremony, steps.md Phase 1 step 5; `list_issue_statuses` feeds the same
question's state discovery).

**`makePr` (PR link → Linear Diffs) on the MCP rung.** The MCP exposes **no
URL-attach tool** — `create_attachment` / `prepare_attachment_upload` are for
*file* uploads, not for linking a GitHub PR. So on this rung the PR linkage relies
entirely on **make-pr §4.6a** putting a non-closing `Ref WOR-N` in the PR body:
Linear's GitHub integration auto-links the PR on the identifier, which is what
makes **Linear Diffs** render it inside the issue. (The rich `attachmentLinkURL`
belt-and-suspenders is GraphQL-rung only — [linear-graphql.md](linear-graphql.md).)
The MCP *does* expose **read-only diff tools** — `list_diffs`, `get_diff`,
`get_diff_threads` (resolve by GitHub PR URL) — handy for a future `resolvePr`
touchpoint that folds Linear review threads back into flow; out of scope for the
`makePr` link itself.

**Asymmetry to remember vs the GraphQL rung:** MCP accepts the **identifier**
(`WOR-17`) interchangeably with the UUID on most inputs (`get_issue`,
`save_comment`'s `issueId`, `save_issue`'s update `id`) — but it **returns
identifiers, never UUIDs**: create AND fetch both come back with the
`WOR-17`-form key as `id` (verified live 2026-06-09 — `get_issue` /
`list_issues` / `save_issue` all did). The GraphQL rung is the mirror image:
stricter on inputs (`commentCreate` needs the **UUID**) and the only rung whose
responses carry the UUID. Either way, **store the UUID as the durable dedupe
key** (`sync set-tracker-id`) and surface the `identifier` to humans; never
persist `WOR-17` as the primary key — which means **first-link needs the GraphQL
rung to obtain that UUID** (see Gotchas).

## The six interface methods over MCP

Mapping wire ↔ normalized happens here, at the adapter boundary. Reconcile never
sees an MCP shape.

### `fetchIssue(trackerId)` → normalized `issue` | not-found

```
get_issue(id: <uuid or identifier>)
 → map: identifier, title, description→body, state.name→status.raw,
 (state.type + config map)→status.normalized, priority, labels[].name,
 url, updatedAt
 → the wire `id` IS the identifier (`WOR-17`-form), never the UUID — populate
 the normalized `issue.id` (UUID) from the stored sync state of the linked
 spec (`sync get-state`), not from the MCP response (see Gotchas).
 → on missing/archived/deleted: the call errors or returns nothing ⇒ return
 `not-found` (NEVER raise out of the adapter). The skeleton then emits an
 `errored` receipt + prompts/queues unlink (see linear-ladder.md error contract).
```

### `writeIssue(issue)` → `{id, identifier, url}` (upsert)

```
no issue.id ⇒ CREATE: save_issue(team:<team>, title:<title>, description:<body>,
 labels:[...,"flow:<id>"], priority:<0-4>)
issue.id set ⇒ UPDATE: save_issue(id:<uuid>, description:<body>, title:<title>,
 labels:[...], priority:<0-4>) # changed fields only
 → return { identifier, url } from the result; the interface's `id` (UUID) slot
 CANNOT be filled on this rung — the wire `id` field IS the identifier
 (`WOR-17`-form), NOT the UUID. On create, the durable UUID for
 `sync set-tracker-id` must be fetched via the GraphQL rung (see Gotchas).
```

Write the flow back-reference on create/first-link: a `flow:<id>` label and/or a
`[<id>]` title prefix (Phase 2a/2b of [steps.md](../steps.md)) so the issue
points back at the spec.

### `setStatus(trackerId, status)` → ok | errored

```
# Resolve normalized status → the team's concrete state.
# save_issue's `state` accepts a state type/name/ID, so either:
save_issue(id:<uuid>, state:<state-name-or-id from the config status map>)
 → on a state that doesn't exist for the team: return `errored` (don't crash).
```

### `listComments(trackerId)` → normalized `comment[]`

```
list_comments(issueId:<uuid>, orderBy:createdAt, limit:250)
 → map each: id, user→author, body, createdAt, and DETECT the flow marker
 (a `flow-evt:<event>` token flow itself posted) → set `marker`; genuine
 tracker-side comments get `marker:null` and pull into the spec sync log.
 → page via `cursor` if the issue has >250 comments.
```

### `postComment(trackerId, body)` → normalized `comment`

```
save_comment(issueId:<uuid>, body:<markdown, with the flow-evt marker line>)
 → map the result back to a normalized `comment`.
```

### `readStatus(trackerId)` → normalized `status`

```
# Derived from the issue fetch — no separate call.
get_issue(id:<uuid>).state → { raw: state.name,
 normalized: map(state.type, config) }
```

## Relation transport (dependency projection, fn-64.3)

The two relation methods from [adapter-interface.md](adapter-interface.md) over MCP.
**Direction convention** (stated once there): `from` is-blocked-by `to`; flow's
`depends_on_epics:[B]` on spec A projects to `setIssueRelation(issue=A, blockedBy=B)`.

> **MCP schema re-verify (fn-64.3, verified live 2026-06-17).** `save_issue` DOES
> expose `blockedBy` / `blocks` (append-only — "existing relations are never
> removed") and `removeBlockedBy` / `removeBlocks`; `get_issue` DOES expose
> `includeRelations:true`. The schema drifts, so **re-inspect the host tool list
> before relying on these** — if a future server drops `blockedBy`, the ladder
> falls to the GraphQL rung when `LINEAR_API_KEY` is set, else writes a `noop`
> receipt ([linear-ladder.md](linear-ladder.md)). flow projects **only the
> blocked-by edge** — never touch `blocks` / `relatedTo` / `duplicateOf` here.

### `listIssueRelations(issue)` → normalized `relation[]` | errored

```
get_issue(id:<uuid or identifier>, includeRelations:true)
 → read the returned relations (the blocking set: this issue's "blocked by"
 edges). For each blocker B, emit a normalized relation:
 { from: <this issue>, to: B, type: "blocks", source: "unknown" }
 → `source` is "unknown" on MCP — Linear stores no relation authorship; the
 flow-side depRelations ledger (fn-64.1) is the provenance authority.
 → return ONLY the blocked-by view. Drop related/duplicate edges so the skill's
 read-before-write dedup never trips over an unrelated relation kind.
 → on error / missing issue: return `errored` — never raise.
```

### `setIssueRelation(issue, blockedBy)` → ok | errored | noop

```
# READ-BEFORE-WRITE (mandatory): listIssueRelations(issue) first; if the
# (issue is-blocked-by blockedBy) edge already exists → return noop, skip write.
save_issue(id:<the BLOCKED issue>, blockedBy:[<the BLOCKING issue>])
 → save_issue's blockedBy is append-only (the server never removes existing
 relations), so this only ever ADDS the edge — it can never clobber a human's
 manual relation (R6). Pass id/identifier interchangeably.
 → on success: return ok (the skill records the edge in the depRelations ledger).
 → on error (issue not found, etc.): return `errored` — never raise.
```

**Why read-before-write even though `blockedBy` is append-only.** The MCP rung's
append-only semantics mean a duplicate `save_issue(blockedBy:…)` is harmless on
the wire, but the contract still requires the pre-check ([adapter-interface.md](adapter-interface.md))
for parity with the GraphQL rung (where `issueRelationCreate` is **not** reliably
idempotent) and so the skill can record "no new edge created" accurately. Skip
the write when the edge is already present.

## Status map (MCP)

Build the team's name/type → state map **once at config time** so `setStatus`
can resolve a normalized status back to a concrete state:

```
list_issue_statuses(team:<team>)
 → for each state: { id, name, type } # type ∈ backlog|unstarted|started|completed|canceled
 → fold into tracker.perTracker.statusMap (config-driven name overrides, e.g. a
 "Verified" completed-state → normalized `verified`).
```

The default `state.type` → normalized mapping is shared with the GraphQL rung —
see the status table in [linear-ladder.md](linear-ladder.md).

## Gotchas

- **Literal markdown, no escapes.** The server expects real newlines in
 `description`/`body` — never `\n` escape sequences (a round-trip-spike failure
 mode: escaped newlines come back as literal backslash-n).
- **MCP create/fetch returns an identifier, not a UUID** — `get_issue` /
 `list_issues` / `save_issue` all return the `WOR-17`-form key as `id`
 (verified live 2026-06-09). **First-link therefore requires the GraphQL rung
 (`LINEAR_API_KEY`) to obtain the UUID** for `sync set-tracker-id` — a pure-MCP
 environment cannot populate the durable dedupe key on a fresh link.
- **UUID is the key, identifier is for humans.** MCP's leniency about accepting
 `WOR-17` does not make it a safe dedupe key — a deleted+recreated issue can
 reuse an identifier but never the UUID.
- **Tool names drift** — the pin above is dated; re-verify on a new host/server
 version. The ladder probes for *a* Linear server, but the exact verbs are what
 the round-trip spike confirms before fn-52.4 builds on them.
- **Rate limits still apply** — even though the server manages auth, it can
 surface a rate-limit error; back off (don't fail) per the
 [linear-ladder.md](linear-ladder.md) error contract.
- **MCP is interactive-only in practice** — treat it as absent on headless / CI /
 cron / Ralph paths; those fall through to the GraphQL rung, which is why parity
 (linear-ladder.md) matters.
