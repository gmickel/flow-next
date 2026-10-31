# QA stage - freshness rule

> **The rule, not a step to run.** `flow --auto` gets `QA_FRESH` from the pilot snapshot
> (`selected.qa_fresh`), which implements the receipt identity, outcome and branch-head checks
> below. Read this file to understand what counts as a fresh QA verdict.

## QA-stage freshness (what the snapshot checks)

When the gate selects QA, the all-done juncture classifies `qa` **only when no *fresh* `qa_verdict` receipt exists** for the spec. Every hop re-classifies from disk. The freshness check prevents repeated QA from blocking make-pr. The receipt lives at the committed path `.flow/review-receipts/qa-<spec-id>.json` (the QA skill's default). A receipt is **fresh** iff all three hold:

1. `receipt.id == <spec-id>` (the receipt's existing spec-id field is `id`, not `spec`).
2. `receipt.head_sha` matches the spec **branch** head **with the `chore(flow): qa verdict` bookkeeping commits peeled off**. The receipt records the CODE head. The QA skill commits the receipt above it, so a raw `rev-parse "$BRANCH_NAME"` would never match and QA would re-run forever. Compute against the branch, never `HEAD`, because a resumed or manual run may sit on another branch.
3. `receipt.qa_outcome` is a valid terminal value (`SHIP`, `NEEDS_WORK`, `NA`, or `BLOCKED`).
