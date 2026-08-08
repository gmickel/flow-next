# Overview

Issue #312 (sn-furali, follow-on to #279/#283): a `review_attempts[]` row records what was reviewed but not how the verdict was produced. The reporter measured resumed `--receipt` sessions returning `VERDICT=SHIP` in ~1.1-1.6 KB outputs with ZERO tool calls, asserting "measured" facts that happened to be true - answered from the previous round's context while claiming fresh measurement. The unchanged-artifact guard (3.16.x) blocks the cheap identical repeat but not a slightly-changed artifact, a forced dispatch, or the fail-open hash path. Verdict-text inspection cannot detect it; only work-volume can.

**Evidence standing: two reporter-measured occurrences across two review kinds (plan and completion), with fresh-receipt re-dispatch controls (151 KB / 22 tool calls and 248 KB / 20 tool calls producing real NEEDS_WORK findings). No new evals.**

## Goal & Context

Three fields on the attempt row make a verdict identifiable and credible: a work-volume measure (catches both measured occurrences), a provenance marker on `head_sha` (observed snapshot vs finalize-time fallback), and `base_sha` beside `head_sha` (locate and re-render the judged diff). All three are known to the dispatcher at row-write time; zero added work.

## Architecture & Data Models

1. **Work volume:** `record_review_attempt` gains an output byte count and, where the backend reports it, a tool-call count. Written from values the dispatcher already holds; consumers can set a floor, humans can audit a row.
2. **head_sha provenance:** `head_sha_observed: true|false` - true when a pre-dispatch snapshot supplied it, false on the finalize-time `git rev-parse HEAD` fallback (the `review-rounds record` CLI path used by rp/host backends always takes the fallback today). Alternative accepted by the issue: omit the field when unobserved; pick one and document it.
3. **base_sha:** forwarded from `_capture_review_snapshot(base_branch)`, which already returns `(base, head)` and already hands both to the receipt while forwarding only head to the ledger. A keyword argument and a dict key on a path #283 already rewrote.

## Edge Cases & Constraints

- `session_id` is explicitly NOT the fix: the codex resume path returns the same thread id for the fabricating round and the real one. Copying it onto the row is welcome but cannot answer the question.
- No new verdict-validity rules, no re-review policy, no reviewer behavior change, no new command: the consumer asks the question; flowctl only makes it askable.
- Rows written by older versions lack the fields; readers must treat absence as unknown, never as zero.
- DEPENDS ON fn-178 (stage receipts) landing first: same receipts/ledger neighborhood; sequencing avoids churn and lets this spec reuse any shared conventions fn-178 establishes.
- Ledger schema changes ride the existing `hash_epoch` / architecture-notes discipline; dual copies + mirrors as always.

## Acceptance Criteria

- **R1:** Every new attempt row carries an output byte count; tool-call count present where the backend exposes it, absent otherwise (never fabricated). Errors: a backend reporting neither still writes the row; missing metrics are absent, not zero.
- **R2:** `head_sha` provenance is distinguishable on the row (marker or omission, one documented choice); the rp/host CLI record path is the fixture proving the fallback case.
- **R3:** `base_sha` recorded beside `head_sha` on paths where `_capture_review_snapshot` runs; absent (not guessed) elsewhere.
- **R4:** `review-rounds attempts --json` surfaces all new fields; old rows read back with fields absent and no crash.
- **R5:** Architecture notes state what each field answers and that absence means unknown. Docs + CHANGELOG Unreleased crediting @sn-furali. Errors: parity red blocks merge.

## Boundaries

- No change to verdict validity, re-review policy, or the unchanged-artifact guard.
- No retention of review outputs; the byte count is recorded, the output is not.
- No new commands.
- Version bump deferred to the batched release.

## Decision Context

Field order follows the issue's own preference (work volume first) because it is the only field that would have caught both measured occurrences: the fabricated SHIP stated three true facts, so plausibility checks fail by construction, and the resume path reuses the session id, so identity checks fail too. The only reliable question is "is the evidence it states measured?", and a 0-tool-call 1.1 KB run answers it. The fn-178 dependency is sequencing hygiene, not a semantic coupling: fn-178 covers pipeline-stage outcome lines, this covers the review-attempt ledger; they share receipts conventions, not code paths.
