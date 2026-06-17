# fn-64-tracker-sync-project-flow-spec.2 Adapter interface contract: setIssueRelation / listIssueRelations + relation struct

## Description
### Goal
Define the normalized, transport-blind relation contract both adapters implement, so the skill never branches on Linear-vs-GitHub. **Satisfies R8.**

### Investigation targets
- `plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md:14-21` — the 6-method transport table (fetchIssue/writeIssue/listComments/postComment/readStatus/setStatus). Add two rows: `setIssueRelation(issue, blockedBy)` and `listIssueRelations(issue)`.
- Same file `:35-65` — the normalized `issue`/`comment` structs; model a new `relation` struct: `{from, to, type, source}` where `source` ∈ {flow, human, unknown} when the transport can tell, else the flow-side `depRelations` ledger is authoritative.
- Cross-link the contract to fn-64.1's `depRelations` state and fn-64.3/.4's adapter rungs.

### Notes
Pure doc/contract task; small. It unblocks fn-64.3 and fn-64.4 (both depend on it).
## Acceptance
- adapter-interface.md documents `setIssueRelation` / `listIssueRelations` with input/output shapes, the `relation` struct, the **read-before-write** idempotency rule (neither platform reliably no-ops a duplicate), and the never-delete-non-ours provenance contract.
- States the direction convention once (blocked-by = "current issue blocked by dep issue") so both adapters map consistently.
- No code — this is the contract doc both downstream adapter tasks implement against.
## Done summary
Documented the normalized dependency-relation contract in adapter-interface.md: added `setIssueRelation(issue, blockedBy)` / `listIssueRelations(issue)` to the transport table, a new `relation` struct `{from, to, type, source}`, the once-stated blocked-by direction convention, and the mandatory read-before-write idempotency + never-delete-non-ours provenance rules — cross-linked to fn-64.1's depRelations ledger and the fn-64.4 fenced-block/body-merge exclusion. Contract-only doc that unblocks fn-64.3 and fn-64.4.
## Evidence
- Commits: a5f4384cad8212326ea0ec6e2d380983b3ca6247
- Tests: docs-only — no tests; impl-review triage-skip SHIP (docs-only, mode=triage_skip)
- PRs: