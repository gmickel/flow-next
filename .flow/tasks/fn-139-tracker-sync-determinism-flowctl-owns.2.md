---
satisfies: [R1, R18, R31]
---
# fn-139-tracker-sync-determinism-flowctl-owns.2 Wire verbs: read/update/comment CRUD/label/assign + persist-external

## Description
Implement the wire verb group against all four adapters using the .1 executor: `read`, `update`, `comment-add/list/update/delete` (parent tracker id required - GitLab and Jira both need it), `label`, `assign`, `list-open`.

Implement `persist-external <spec-id>` (R18). **Linear MCP returns the display identifier only, never the durable UUID** (`linear-mcp.md:100`), so this verb accepts identifier-only input and resolves the UUID via the GraphQL rung before persisting. If GraphQL is unreachable it persists an explicitly-marked identifier-only linked state rather than fabricating or silently omitting `tracker.id`.

Implement the result envelope and the full `class` enum with 1:1 exit-code mapping.

## Acceptance
- [ ] All wire verbs work on GitHub, GitLab, Linear, Jira via fake transport
- [ ] `comment-update`/`comment-delete` take and require the parent tracker id
- [ ] `persist-external` resolves UUID via GraphQL after an identifier-only MCP result
- [ ] GraphQL unavailable -> identifier-only state, explicitly marked, never a fabricated id
- [ ] Persist failure surfaces identifier + url and writes a warning receipt
- [ ] `class` enum exhaustive; exit code maps 1:1; wire verbs write NO receipt
- [ ] Content-bearing args go via stdin/file, never argv

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
