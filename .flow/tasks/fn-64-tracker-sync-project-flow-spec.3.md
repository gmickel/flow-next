# fn-64-tracker-sync-project-flow-spec.3 Linear adapter relation transport (MCP save_issue + GraphQL issueRelationCreate, read-before-write dedup)

## Description
### Goal
Implement the relation transport on the Linear adapter ladder (MCP + GraphQL rungs), with read-before-write dedup. **Satisfies R1, R3.**

### Investigation targets
- `references/adapter-interface.md` — the `setIssueRelation`/`listIssueRelations` contract from fn-64.2.
- `references/linear-mcp.md:27` `save_issue` (exposes `blockedBy`/`blocks`, append-only) + `:28` `get_issue` `includeRelations:true` (read path). MCP rung: `setIssueRelation` via `save_issue` blockedBy; `listIssueRelations` via `get_issue` includeRelations.
- `references/linear-graphql.md:93-118` mutations — add `issueRelationCreate(input:{issueId, relatedIssueId, type: blocks})`. "A blocked by B" = `blocks` edge with `issueId:B, relatedIssueId:A`. Enum is lowercase `blocks`/`related`/`duplicate` — do NOT invent `blocked_by`.
- List/dedup: query BOTH `relations { nodes {...} }` AND `inverseRelations { nodes {...} }` — each REQUIRES an explicit `first:` arg (memory: linear-graphql-every-nodes-connection) or Linear rejects the query. Canonicalize each edge to one direction before comparing to avoid silent inverse-duplicates.
- `references/linear-ladder.md` — place the new method in the MCP→GraphQL→no-op ladder; bottom rung no-ops + `noop` receipt.
## Acceptance
- [ ] MCP rung: `setIssueRelation` via `save_issue` blockedBy/blocks — but FIRST re-verify the pinned MCP schema actually exposes these params (it drifts); if absent, fall back to the GraphQL rung when `LINEAR_API_KEY` is set, else write a `noop` receipt.
- [ ] GraphQL rung: `issueRelationCreate(input:{issueId, relatedIssueId, type: blocks})` with correct operand direction ("A blocked by B" = issueId:B, relatedIssueId:A).
- [ ] Dedup (read-before-write): list via BOTH `relations` AND `inverseRelations` (each with explicit `first:`), canonicalize each edge to one direction before comparing; re-run creates no duplicate (R3).
- [ ] Bottom rung no-ops with a `noop` receipt (not "deferred").
- [ ] linear-mcp.md / linear-graphql.md / linear-ladder.md updated with exact mutation/field names, verified against the live schema.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
