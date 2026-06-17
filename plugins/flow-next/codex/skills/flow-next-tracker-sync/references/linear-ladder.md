# Linear adapter — transport ladder (MCP / GraphQL / no-op)

The Linear implementation of the eight-method transport interface
([adapter-interface.md](adapter-interface.md)) — the original six plus the
dependency-projection pair (`listIssueRelations` / `setIssueRelation`, fn-64.3).
It is a **detect-best-available
ladder**, the exact shape as `flow-next-drive`'s driver ladder (SKILL.md Step 3 +
`references/agent-browser.md`): probe top-down, use the **highest rung that
passes**, fail soft to the next, terminal rung is a documented no-op. **Neither
transport is a hard dependency.** A pass must succeed with whatever the
environment actually has — interactive desktop (MCP), headless / CI / Ralph
(GraphQL via `LINEAR_API_KEY`), or neither (no-op + receipt note). Probe — never
assume; never crash when both are absent.

This file is the rung router and the seam that makes reconcile transport-blind.
The per-rung command detail lives in the rung references:

| Rung | Transport | Use when | Reference |
|------|-----------|----------|-----------|
| 1 (interactive default) | **Linear MCP** (host tool, e.g. `save_issue`) | A Linear MCP server is registered on the host. Interactive convenience — OAuth/token handled by the server; the dominant interactive mode. | [linear-mcp.md](linear-mcp.md) |
| 2 (headless) | **Linear GraphQL** via `LINEAR_API_KEY` | No MCP, but `LINEAR_API_KEY` is set — headless / CI / Ralph-safe, version-stable wire contract. | [linear-graphql.md](linear-graphql.md) |
| 3 (terminal) | **no-op + receipt note** | Neither MCP registered NOR `LINEAR_API_KEY` set — the bridge is configured but no Linear transport is reachable. | — (this file) |

The chosen rung is recorded on every receipt: `sync receipt … --transport mcp|graphql|none`
— plus, on a lifecycle run, the touchpoint it served: `${EVENT:+--event "$EVENT"}`
(`$EVENT` is set in steps.md Phase 0; empty on manual runs, so the flag is omitted).
The agentic reconciliation (fn-52.4 body merge, fn-52.5 status/comments) is
**identical regardless of rung** — that is the R13 guarantee, and the parity
check below is how it is verified.

## Rung detection (probe, don't assume)

Mirror fn-51's driver-ladder detection — detection lives in the skill (host
agent), not in flowctl. Probe top-down; take the first rung that passes:

```bash
# Rung 1 — Linear MCP: inspect the host's MCP/tool list for a Linear server.
# Host-agent introspection (the tool list IS visible to the agent) — there is
# no shell probe. A registered Linear server exposes upsert verbs like
# save_issue / save_comment / list_comments / get_issue / list_issue_statuses.
# If present → TRANSPORT=mcp (read linear-mcp.md)

# Rung 2 — GraphQL via API key (only if no MCP):
if [ -n "${LINEAR_API_KEY:-}" ]; then TRANSPORT=graphql; fi # read linear-graphql.md

# Rung 3 — neither reachable:
# TRANSPORT=none → every interface method is a documented no-op + receipt note.
TRANSPORT="${TRANSPORT:-none}"
```

Rule of order: **MCP beats GraphQL when both are available** (interactive
convenience, OAuth already handled), but a headless/Ralph run that has no MCP
registered falls straight through to GraphQL — exactly the surface-aware degrade
in fn-51. Treat the MCP rung as *probably absent* on any headless/CI/cron path
(MCP servers are an interactive-host feature); GraphQL is the headless-robust
path, which is why the GraphQL parity check (below) is load-bearing, not optional.

## No-op rung (terminal) — never crash

When `TRANSPORT=none`, the configured bridge cannot reach Linear this run. Every
one of the eight interface methods becomes a documented no-op:

- `fetchIssue` / `listComments` / `readStatus` / `listIssueRelations` → return
 nothing actionable (treated as "no remote view available this run"); the spec's
 flow-side state is left untouched and the merge base is NOT advanced.
- `writeIssue` / `postComment` / `setStatus` / `setIssueRelation` → perform no
 remote write. Dependency projection is skipped with a `noop` receipt — never a
 crash, never a lifecycle block (fn-64.3).
- The run emits `sync receipt … --status noop --transport none ${EVENT:+--event "$EVENT"}
 --note "no Linear transport reachable (MCP not registered, LINEAR_API_KEY unset)"`.
- `lastSyncedAt` is never advanced on a no-op (no real reconciliation happened).

This is the same fail-soft contract as fn-51's terminal manual rung: the pass
still completes, the limitation is recorded, nothing crashes.

## Normalized mapping — the firewall

Both rungs map Linear's wire shape **to/from** the normalized structs in
[adapter-interface.md](adapter-interface.md) (`issue` / `comment` / `status
{raw, normalized}`) **at the adapter boundary**. Reconcile (fn-52.4/.5) only
ever sees the normalized form. A transport bug stays in the rung file; a merge
bug stays in reconcile.

The per-field mapping (Linear wire → normalized `issue`) is identical in intent
across rungs; only the fetch/write mechanism differs:

| normalized `issue` field | Linear source (MCP `get_issue` / GraphQL `issue{}`) | Notes |
|---|---|---|
| `id` | `id` (UUID) | **durable dedupe key** — stored via `sync set-tracker-id`. Never the `identifier`. |
| `identifier` | `identifier` (e.g. `WOR-17`) | display only; surfaced in listings. |
| `title` | `title` | |
| `body` | `description` (MCP) / `description` (GraphQL) | free-form markdown. |
| `status.raw` | `state.name` | the team's literal workflow-state name. |
| `status.normalized` | derived from `state.type` + the config name-map | see status mapping below. |
| `priority` | `priority` (0–4) | folded, never auto-changed (R7). |
| `labels` | `labels[].name` | includes the `flow:<id>` back-reference label. |
| `url` | `url` | |
| `updatedAt` | `updatedAt` | drives staleness + echo-suppression. |

**Status normalization (both rungs share one map).** Linear workflow-state names
are team-specific, so the stable middle is built from `state.type` (`backlog` /
`unstarted` / `started` / `completed` / `canceled` — Linear's fixed type
taxonomy) plus an optional config name-override (`tracker.perTracker.statusMap`):

| Linear `state.type` | default normalized | who-wins ([status-sync.md](status-sync.md)) |
|---|---|---|
| `backlog` | `backlog` | — |
| `unstarted` | `planned` | — |
| `started` | `in-progress` | flow wins |
| `completed` | `done` (or `verified` via name-map, e.g. a "Verified" state) | tracker wins |
| `canceled` | `wontfix` (or `deferred` via name-map) | surface to user, never auto-change |

Build the **name/type → `stateId` map once at config time** (MCP:
`list_issue_statuses`; GraphQL: `workflowStates(first:100, filter:{team:…}){ id name type }`)
so `setStatus` can resolve a normalized status back to the team's concrete
`stateId`. Both rungs produce the same normalized `status` struct — that is what
the parity check verifies.

## Relation transport (dependency projection, fn-64.3)

The `listIssueRelations` / `setIssueRelation` pair routes through the same rung
ladder as the other six methods, with one extra wrinkle: the MCP rung's relation
params can drift out of the pinned schema, so the rung selection has a **relation-
specific fallback** layered on top of the normal probe.

| Rung | `listIssueRelations` | `setIssueRelation` | Reference |
|------|----------------------|--------------------|-----------|
| 1 MCP | `get_issue(id, includeRelations:true)` | `save_issue(id, blockedBy:[…])` — append-only | [linear-mcp.md](linear-mcp.md) |
| 2 GraphQL | `issue{ relations + inverseRelations }` (both `first:`-bounded) | `issueRelationCreate(type:blocks)` — read-before-write | [linear-graphql.md](linear-graphql.md) |
| 3 none | no-op + `noop` receipt | no-op + `noop` receipt | (this file) |

**MCP schema re-verify + fallback (acceptance #1).** The MCP `blockedBy` /
`includeRelations` params were verified live 2026-06-17, but the server schema
drifts. At impl/run time, **inspect the host tool list**: if the Linear MCP server
no longer exposes `save_issue.blockedBy` (or `get_issue.includeRelations`), do NOT
fail — degrade the relation pair specifically:

```
if MCP relation params present → use the MCP rung (rung 1)
elif LINEAR_API_KEY set → use the GraphQL rung for relations (rung 2)
else → noop receipt (rung 3)
```

This is a **per-capability** fall-through: the rest of the adapter can still run
on MCP while only the relation pair drops to GraphQL when the MCP relation surface
is missing. Everything else (the six core methods) keeps the standard whole-rung
probe above.

**Read-before-write on every rung.** Both rungs MUST `listIssueRelations` and skip
the write when the (issue is-blocked-by blockedBy) edge already exists — append-
only on MCP, mandatory on GraphQL (`issueRelationCreate` is not idempotent). The
GraphQL read canonicalizes across `relations` + `inverseRelations` so an inverse-
duplicate cannot slip through. **Never-delete-non-ours:** both `setIssueRelation`
forms only ever ADD the blocked-by edge; provenance for safe removal lives in the
flow-side `depRelations` ledger (fn-64.1), never inferred from the wire (R6).

## Capability parity (MCP ↔ GraphQL) — the R13 guarantee

Reconcile is genuinely transport-blind only if the GraphQL rung covers
**everything** the MCP rung does. Verify per interface method that both rungs map
the same fields into/out of the normalized structs:

| Interface method | MCP rung | GraphQL rung | Parity target |
|---|---|---|---|
| `fetchIssue` | `get_issue(id)` → `issue` | `query{ issue(id){…} }` | same `issue` struct (title/body/status/priority/labels/url/updatedAt) |
| `writeIssue` (upsert) | `save_issue` (no `id`=create, `id`=update) | `issueCreate` / `issueUpdate` | same `{id, identifier, url}` |
| `listComments` | `list_comments(issueId)` | `query{ issue{ comments(first:N){…} } }` | same `comment[]` (author/body/createdAt/marker) |
| `postComment` | `save_comment(issueId, body)` | `commentCreate(issueId:UUID, body)` | same `comment` |
| `readStatus` | from `get_issue.state` | from `issue.state` | same `status{raw,normalized}` |
| `setStatus` | `save_issue(id, state)` | `issueUpdate(id, stateId)` | ok / `errored` |
| `listIssueRelations` | `get_issue(id, includeRelations:true)` | `issue{ relations(first:N) + inverseRelations(first:N) }` | same blocked-by `relation[]` (`{from,to,type:"blocks",source}`) |
| `setIssueRelation` | `save_issue(id, blockedBy:[…])` (append-only) | `issueRelationCreate(issueId:B, relatedIssueId:A, type:blocks)` | ok / `errored` / `noop`; read-before-write on both |
| status map build | `list_issue_statuses(team)` | `workflowStates(first:100, filter:{team}){type}` | same name/type → stateId map |

If a field is reachable on one rung but not the other, that is a parity gap —
fix it in the rung file before relying on reconcile being transport-blind. The
**round-trip spike below is run on BOTH rungs** (whichever the environment
provides) precisely to catch parity gaps early.

## Round-trip spike (acceptance #1 — run FIRST, before fn-52.4)

A de-risking spike that exercises the transport in isolation: **push a flow body
to a real Linear issue, then pull it back unchanged** — format translation only,
**no merge**. It surfaces transport bugs (OAuth, tool-name drift, GraphQL
auth/asymmetry, identifier-vs-UUID, complexity rate limits) BEFORE the .4 merge
engine is built on top.

> **Live-verification status (this environment).** A live Linear round-trip needs
> real credentials (a registered MCP server OR a `LINEAR_API_KEY` against a real
> workspace). Those are unavailable in the build environment, so the **live
> execution is deferred to the post-PR smoke-testing phase** the maintainer
> drives. The spike below is a complete, runnable procedure with an explicit
> success/fail oracle; the MCP tool names + GraphQL wire facts it depends on are
> verified and pinned (see linear-mcp.md / linear-graphql.md). Run it once per
> rung the target environment exposes.

### Spike procedure (per rung)

Fixture: a small canonical flow body the round-trip must preserve byte-for-byte
after a normalize→render cycle (headings, a checklist, a fenced block, a link —
the structures most likely to be mangled by a markdown round-trip):

~~~markdown
## Goal
Round-trip fixture for the Linear transport spike.

## Acceptance
- [ ] item one
- [x] item two (done)

## Notes
A fenced block:

```
exact text — must survive verbatim
```

A [link](https://example.com) and an inline `code` span.
~~~

Steps:

1. **Build the body** — write the fixture above to `/tmp/spike-flow-body.md`.
2. **Push (create)** via the active rung's `writeIssue` (no `id` ⇒ create):
 - MCP: `save_issue(team:<team>, title:"flow spike", description:<body>)`
 - GraphQL: `issueCreate(input:{teamId:<uuid>, title:"flow spike",
 description:<body>})`
 Capture the returned `{ id (UUID), identifier (WOR-N), url }`.
3. **Pull back** via `fetchIssue(id)` (use the **UUID**, not `WOR-N`):
 - MCP: `get_issue(id:<uuid>)` → `.description`
 - GraphQL: `query{ issue(id:<uuid>){ description } }`
 Write the returned body to `/tmp/spike-pulled-body.md`.
4. **Oracle (success/fail):**
 ```bash
 # Idempotent format translation ⇒ byte-identical round-trip.
 if diff -u /tmp/spike-flow-body.md /tmp/spike-pulled-body.md; then
 echo "SPIKE PASS — round-trip preserved the body"
 else
 echo "SPIKE FAIL — transport mangled the body; see diff above"
 fi
 ```
 A non-empty diff is a transport bug to fix in the rung file BEFORE fn-52.4 —
 e.g. Linear normalizing list markers, collapsing blank lines, or rewriting the
 fenced block. (If Linear's renderer canonicalizes markdown in a stable,
 loss-less way, record the exact canonical form as the fixture's expected
 output so .4 reconciles against *that*, not the raw input.)
5. **Repeat on the second rung** if the environment exposes both — the two pulled
 bodies must match each other (parity), not just their own inputs.
6. **Cleanup:** delete or archive the spike issue (MCP: `save_issue(id, state:
 "Canceled")` or the workspace's archive; GraphQL: `issueArchive(id)`).

The spike writes a receipt like any sync run:
`sync receipt <spec> --status noop --transport <rung> --note "round-trip spike: PASS|FAIL"`
(status `noop` because the spike performs no real reconciliation — it is a
transport probe, not a sync of a tracked spec; no `--event` either — the spike is
a manual diagnostic, never a lifecycle touchpoint).

## Error contract (acceptance #5) — never crash, never corrupt state

The ladder honors the [adapter-interface.md](adapter-interface.md) contract rules.
The failure modes that MUST be non-destructive:

- **Missing / deleted / archived / 404 linked issue** — `fetchIssue` returns
 `not-found` (MCP: `get_issue` errors or returns nothing; GraphQL: `issue`
 resolves `null` or an `errors[]` entry). The skeleton then:
 - emits `sync receipt … --status errored --transport <rung> ${EVENT:+--event "$EVENT"}`,
 - does **NOT** crash, does **NOT** clear state, does **NOT** advance
 `lastSyncedAt` (a failed fetch must never corrupt the merge base),
 - prompts the user to unlink (interactive) or queues an unlink decision
 (`sync defer`, Ralph) — never silent `sync clear`.
- **Rate limit** — Linear's limit is **complexity-based**, returned as **HTTP
 400 with a `RATELIMITED` error code (NOT HTTP 429)**. On `RATELIMITED`: **back
 off and retry** (exponential, respecting any `retryAfter`/reset hint) rather
 than failing the run. Mitigate proactively on the GraphQL rung — explicit
 `first:` on every connection, order by `updatedAt` desc — see
 [linear-graphql.md](linear-graphql.md). The MCP rung's server manages its own
 budget but can still surface a rate-limit error; treat it the same (back off,
 don't fail).
- **Batch sync is item-level** — one spec's `errored`/rate-limit does not abort
 the batch: that spec gets its own `errored` receipt + no state write, and the
 run continues to the next spec.
- **Echo suppression** — after a push, the resulting tracker-side body hash is
 recorded (rides on the merge-base snapshot, fn-52.4); the next pull's matching
 hash ⇒ flow's own echo ⇒ `noop`, never a phantom conflict. `updatedAt` from
 the wire helps distinguish a real tracker-side edit from an echo.

## Boundaries

- **This is the transport, not the merge.** The ladder maps wire ↔ normalized and
 routes rungs. The 3-way body merge ([body-merge.md](body-merge.md), fn-52.4),
 the status who-wins ([status-sync.md](status-sync.md), fn-52.5), and the
 comments/evidence append + dedup ([comments-sync.md](comments-sync.md), fn-52.5)
 consume the normalized structs and live in those tasks.
- **No new hard dependency.** Neither the MCP server nor `LINEAR_API_KEY` is
 required; the terminal rung is a documented no-op. The zero-dep base install is
 untouched (spec Boundaries / STRATEGY opt-in carve-out).
- **One Linear team / workspace per repo** (spec Boundaries) — the status map and
 `WOR-` key resolution assume a single team.
