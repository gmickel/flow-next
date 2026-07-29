# Emitted acceptance criteria (one business pass over `transcript.md`)

Produced by running the write-back guidance in
`skills/flow-next-interview/references/write-back.md` § "Source tags on acceptance criteria"
once over the frozen transcript. Recorded so R5 (tags discriminate) is checkable without
re-running an interview: answered questions land on `[user]` / `[paraphrase]`, unasked
gap-fills land on `[inferred]`, the strategy-derived line carries its track.

## Acceptance Criteria

- **R1:** Zero "can you send me my saved searches" support tickets in the month after release. [user]
- **R2:** First release exports CSV only; JSON and the scheduled email digest are out of scope. [paraphrase]
- **R3:** Analysts on the paid tier can export; admins are not a target user for this feature. [user]
- **R4:** An export that exceeds the row cap fails with a message naming the cap, not a truncated file. [inferred]
- **R5:** Each completed export writes an audit-log entry with the actor and the row count. [inferred]
- **R6:** Every export path reachable in the product completes without a support ticket. [strategy:Self-serve]

Tally: `Source: [user] 2 · [paraphrase] 1 · [strategy] 1 · [inferred] 2`

No-self-blessing check fires: R4 and R5 are `[inferred]` and no interview question covered
them, so the write-back ask must not recommend `approve` - it states the count (2) and points
the PO at those two lines. The skipped Q4 is not a criterion; it belongs in `## Open Questions`.
