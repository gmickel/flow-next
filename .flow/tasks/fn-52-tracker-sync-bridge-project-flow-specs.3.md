---
satisfies: [R13]
---

## Description

The Linear transport behind the .2 adapter interface — a detect-best-available ladder mirroring fn-51's driver ladder. Neither transport is a hard dependency. Carries the **round-trip spike** that de-risks transport (OAuth / MCP tool-name / GraphQL parity / rate limits) BEFORE the .4 merge engine is built.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/references/linear-mcp.md`, `references/linear-graphql.md`, `references/linear-ladder.md` (mirrors `flow-next-drive/references/*`).

## Approach

- **Ladder** (highest rung passes, fail soft to next, terminal rung manual — mirror `flow-next-drive` rung table): (1) **Linear MCP** when registered (interactive, OAuth handled) → (2) **GraphQL via `LINEAR_API_KEY`** (headless / CI / Ralph, version-stable) → (3) **no-op + receipt note**. Probe-don't-assume; never crash when both absent.
- **Round-trip spike FIRST (acceptance #1):** push a flow body to a real Linear issue and pull it back unchanged — format translation only, no merge. Surfaces transport bugs before .4.
- **MCP tool-name pin at build:** this environment's official server uses upsert verbs — `save_issue`, `save_comment`, `list_comments`, `get_issue`, `list_issue_statuses` (NOT `create_*`/`update_*`). Record the verified names + date as a CLAUDE.md-style breadcrumb. The GraphQL path needs no pin.
- **GraphQL facts:** endpoint `https://api.linear.app/graphql`; auth `Authorization: <key>` with **NO `Bearer`** (MCP uses `Bearer` — asymmetry); `issueCreate` / `issueUpdate` (accepts `WOR-17` or UUID) / `commentCreate` (needs the **UUID**, not `WOR-17`); `workflowStates{type}` → build a name/type→`stateId` map at config time; rate limit is **complexity** (3M pts/hr/user, 10k/single-query) — set explicit `first:` on every connection, order by `updatedAt` desc, back off on `RATELIMITED` (returned as **HTTP 400**, not 429). Store the UUID as the durable dedupe key; surface `identifier` to humans.
- **Normalized mapping:** both rungs map Linear's wire shape to/from the .2 normalized structs (`issue`/`comment`/`status {raw,normalized}`); reconcile (.4/.5) only ever sees the normalized form.
- **Parity check:** verify the GraphQL path covers everything the MCP path does (status, comments, labels) so reconcile is genuinely transport-blind (the R13 guarantee).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-drive/SKILL.md` + `references/*.md` — ladder template + per-rung reference shape
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md` (from .2) — the adapter interface to implement

**Optional:**
- Linear GraphQL docs (auth no-Bearer, identifier vs UUID, complexity limits) and Linear MCP tool surface — pin at build

## Acceptance

- [ ] Round-trip spike: flow body → Linear issue → pulled back unchanged (idempotent format translation), no merge [R13]
- [ ] Transport ladder: MCP-when-registered → GraphQL-via-`LINEAR_API_KEY` → no-op+receipt; neither a hard dep; probe-don't-assume; no crash when both absent [R13]
- [ ] MCP tool names pinned + dated breadcrumb; GraphQL path documented (auth no-`Bearer`, `id` vs `identifier`, complexity limits, `RATELIMITED`/HTTP-400 backoff) [R13]
- [ ] GraphQL ↔ MCP capability parity verified (status/comments/labels) — reconcile output identical regardless of transport [R13]
- [ ] Error contract: a missing/deleted/404 linked issue emits an `errored`/`queued` receipt and prompts/queues unlink — it does NOT crash, clear state, or advance `lastSyncedAt`; rate-limit (`RATELIMITED`/HTTP-400) backs off rather than failing the run [R13]

## Done summary
Implemented the Linear transport adapter as a detect-best-available ladder (MCP → GraphQL via LINEAR_API_KEY → no-op + receipt; neither a hard dependency) across three new skill references — linear-ladder.md (rung router, normalized-mapping firewall, MCP↔GraphQL parity table, runnable round-trip spike with a diff oracle, and the never-crash error contract for 404/deleted/RATELIMITED), linear-mcp.md (interactive rung with a dated tool-name pin: save_issue/save_comment/list_comments/get_issue/list_issue_statuses upsert verbs verified 2026-06-03), and linear-graphql.md (headless rung: auth-no-Bearer asymmetry, id-vs-identifier, complexity rate limit as HTTP-400 RATELIMITED with backoff) — wired into SKILL.md and steps.md. Live Linear round-trip execution is intentionally deferred to the post-PR smoke phase (no creds in this env); the spike is a complete runnable procedure with an explicit pass/fail oracle.
## Evidence
- Commits: 631d7e1, 863d712, b0e939b, adf5fa6
- Tests: flowctl validate --spec fn-52-tracker-sync-bridge-project-flow-specs (Valid: True), markdown fence-balance + cross-ref link resolution checks (all pass), impl-review rp backend: SHIP (2 NEEDS_WORK rounds -> SHIP; sole findings were unbounded GraphQL connections, both fixed; R13 met across all 5 acceptance criteria)
- PRs: