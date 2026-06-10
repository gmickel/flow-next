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
Event-tagged every sync receipt call site in the tracker-sync skill via the `${EVENT:+--event "$EVENT"}` idiom, defined the caller invocation convention (`event: <perEvent-key>` token, parsed in steps.md Phase 0; manual runs legitimately untagged — unlink/spikes carry documented exemptions), and corrected linear-mcp.md: the claude.ai Linear MCP returns identifiers, never UUIDs (create AND fetch, verified live 2026-06-09), so first-link requires the GraphQL rung to obtain the UUID for sync set-tracker-id. linear-ladder.md's correct UUID-dedupe-key prose untouched.
## Evidence
- Commits: 1a0ef2c3c280f650b0b8f42c9ec19517dd70f0d5
- Tests: cd plugins/flow-next && python3 -m unittest discover -s tests (1033 tests OK, 2 skipped), grep -rn 'sync receipt' plugins/flow-next/skills/flow-next-tracker-sync/ — every call site carries --event or a documented manual-mode exemption
- PRs: