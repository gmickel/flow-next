## Goal & Context

<!-- Goal & Context: 100% [user-observed incident, 2026-08-14 flow-98 run] -->

A host-backend review `record` whose output file lacks the `<verdict>` tag is correctly classified `transport_failure` / `missing_verdict` and its reserved round refunded — but when the call carried `--receipt-target`, the durable attempt row and its write-ahead journal are left with `finalized: {receipt: pending, digest: pending}` legs that nothing can ever complete:

- Re-`record` against the same reservation refuses: "Reservation was already finalized with different output".
- `review-rounds increment` hits the journal-without-verdict branch and errors `REPLAY_REQUIRED: an earlier delivered review verdict is still being finalized` — forever.
- The documented repair, `flowctl spec reset-review-rounds --impl`, clears counters/pending/reservations but only unlinks journals for reservations *still in the reservations map*; the orphaned journal file survives, and even after removing it the attempt row's pending legs still trip the `incomplete` check. The counter is wedged with no CLI path out.

Observed live on flow-98.1's host impl-review (2026-08-14). Manual repair required deleting the journal file AND hand-editing the spec sidecar's attempt row legs to terminal states — exactly the kind of surgery flowctl exists to prevent.

## Acceptance Criteria

- **R1:** A `record` that classifies as transport failure (any `failure_class`) never leaves `pending` finalization legs on its attempt row or journal — a refunded attempt's legs land in a terminal state (`not_applicable` or equivalent), and the journal is completed or removed in the same transaction. [user]
- **R2:** `review-rounds increment` never hard-errors `REPLAY_REQUIRED` on a verdict-less (transport-failure) journal — it either replays/refunds it cleanly or treats it as terminal debris and proceeds. [user]
- **R3:** `spec reset-review-rounds [--impl]` is a complete repair: it removes orphaned journal files (journals whose reservation is no longer tracked) and clears any remaining `pending` legs on attempt rows in the reset scope, so a post-reset increment always succeeds. [user]
- **R4:** Regression test reproducing the exact incident: host `record` with `--receipt-target` + verdict-less output → refund → subsequent `increment` for the same task succeeds without manual file surgery. [user]

## Boundaries

- Do NOT weaken the REPLAY_REQUIRED protection for journals that DO carry a delivered verdict — that path is load-bearing crash recovery; only verdict-less transport-failure journals are in scope. [user]
- No change to the verdict grammar or the refund semantics themselves — classification stays as-is; only the finalization-leg bookkeeping and repair verbs change. [inferred]

## Decision Context

Stub captured from the live incident during the flow-98 conducted run; the conductor's workaround (trash the journal, hand-edit `review_attempts[].finalized`) is recorded in the flow-98 session, not in any receipt. Sizing: likely S/M — the fix is in `cmd_review_rounds_record`'s transport-failure branch, the increment pre-gate's journal scan, and `cmd_spec_reset_review_rounds`.
