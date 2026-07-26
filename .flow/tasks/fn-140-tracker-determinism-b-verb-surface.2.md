---
satisfies: [R3, R4, R5]
---
# fn-140-tracker-determinism-b-verb-surface.2 create / create-first / persist-external + MCP boundary

## Description
Implement the three creation-and-linking verbs with the receipt semantics from the command-semantics table.

`create` (spec exists) writes a receipt. `create-first` (no spec yet) uses fn-134's recovery-record path and writes NO receipt, preserving the no-duplicate-on-retry guarantee.

`persist-external` records an MCP-performed write. **Linear MCP returns the display identifier only, never the durable UUID** (`linear-mcp.md:100`), so it accepts identifier-only input and resolves the UUID via GraphQL before persisting. GraphQL unreachable -> explicitly-marked identifier-only state, completed by a later reconcile. Never fabricate a durable id; never silently omit one.

MCP is restricted to create/discovery. Every other operation requires GraphQL - state that in the contract.

## Acceptance
- [ ] `create` vs `create-first` receipt semantics match the table
- [ ] `create-first` preserves fn-134 no-duplicate-on-retry
- [ ] `persist-external` resolves UUID via GraphQL after identifier-only MCP result
- [ ] GraphQL unreachable -> `tracker.linkState: "identifier_only"` with populated identifier/url and null id; NOT misread as unlinked
- [ ] Commands needing a durable id return `class: unresolved` against that state
- [ ] `tracker reconcile` is the named entry point and atomically completes it (tested)
- [ ] Persist failure surfaces identifier + url and writes a warning receipt
- [ ] MCP restriction to create/discovery stated in the skill contract

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
