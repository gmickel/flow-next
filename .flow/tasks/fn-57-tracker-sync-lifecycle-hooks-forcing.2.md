---
satisfies: [R1, R7, R9]
---

## Description

Tag every receipt emission in the tracker-sync skill with `--event`, define how callers pass the event into the skill invocation, and apply the linear-mcp.md UUID/identifier correction (same skill directory).

**Size:** S/M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/steps.md`, `references/body-merge.md`, `references/github.md`, `references/linear-ladder.md`, `references/status-sync.md`, `references/linear-mcp.md`

## Approach

- ~22 `sync receipt` call sites across steps.md (:167, :192) and the four transport/merge references — each gains `--event "$EVENT"`. The skill receives the event from its caller: extend the invocation convention (currently `operation: push <spec-id>` in the touchpoint comments) to carry `event: <perEvent-key>`; lifecycle-agnostic invocations (manual `/flow-next:tracker-sync push`) omit `--event` — that is legal (null event = not a lifecycle touchpoint).
- `linear-mcp.md` correction (R9): the claude.ai Linear MCP returns **identifiers (`WOR-17`), never UUIDs** — on create AND fetch. Fix the `writeIssue`/fetch table rows (:27-28, :73-81 imply UUID returns), the asymmetry note (:49-54), and add a Gotcha: "MCP create/fetch returns an identifier, not a UUID — first-link requires the GraphQL rung (`LINEAR_API_KEY`) to obtain the UUID for `sync set-tracker-id`." Grounded by live verification 2026-06-09 (get_issue/list_issues/save_issue all returned `id: "FLOW-7"`). `linear-ladder.md:83` (UUID as dedupe key) is already correct — leave it.
- Linear auto-linkifies issue-key substrings (memory `trackers-auto-linkify-issue-key`) — keep the correction prose free of bare `WOR-N`-style keys where they'd mangle (use backticks, as existing docs do).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md:160-200` — Phase 3 receipt emission + first-link sequence
- `plugins/flow-next/skills/flow-next-tracker-sync/references/linear-mcp.md:27-54, 73-81, 139-143` — the rows/notes carrying the UUID claim
- `plugins/flow-next/skills/flow-next-tracker-sync/references/linear-ladder.md:80-90, 180-185` — what is already correct (don't touch)

**Optional:**
- `references/body-merge.md`, `references/github.md`, `references/status-sync.md` — remaining receipt call sites (grep `sync receipt`)

## Acceptance

- [ ] Every `sync receipt` example/instruction in the tracker-sync skill carries `--event` when invoked from a lifecycle touchpoint, and the invocation convention documents how the caller passes the event
- [ ] Manual (non-lifecycle) invocations legitimately omit `--event` — documented as such
- [ ] `linear-mcp.md` no longer claims MCP returns UUIDs; the first-link-requires-GraphQL gotcha is present; `linear-ladder.md`'s correct UUID-dedupe-key prose is unchanged
- [ ] No receipt call site missed: `grep -rn "sync receipt" plugins/flow-next/skills/flow-next-tracker-sync/` shows `--event` (or a documented manual-mode exemption) on every hit

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: tracker-sync receipt callers all stamp --event today (perEvent vocabulary is the live facade contract; linear ladder docs current). No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: