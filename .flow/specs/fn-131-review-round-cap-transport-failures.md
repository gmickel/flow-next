# Review-round cap: transport failures must not consume rounds

## Goal & Context
<!-- scope: business -->

The fn-90 deterministic review-round cap counts every dispatch increment, including dispatches that fail at the transport layer before any reviewer verdict exists: a backend that emits no `<verdict>` tag, an RP/RepoPrompt timeout, a CLI crash or sandbox denial, an empty/truncated output stream. Burned rounds exhaust the cap without any adversarial signal having been exchanged, forcing manual `review-rounds reset` interventions that weaken the cap's authority and require operator judgment calls the cap was designed to remove.

Observed in the field twice on 2026-07-23/24 (flow-swarm dogfood): an RP transport timeout burned a plan-review round on one spec (the cross-model judge explicitly ruled "reset the counter, the round was burned by transport"); a codex dispatch that completed without emitting the verdict tag burned a round on another spec, and the immediate retry was refused at the cap - two of four rounds consumed with zero reviewer findings delivered.

Principle: **the cap bounds adversarial review rounds, not process spawns.** A round is consumed if and only if a reviewer verdict (SHIP / NEEDS_WORK / MAJOR_RETHINK) was actually obtained. Transport failures are a different failure class with their own bounded budget and their own observable trail.

## Scope
<!-- scope: technical -->

- flowctl review-cap machinery (`enforce_and_increment_review_cap`, the per-backend wrappers `codex|copilot|cursor plan-review|impl-review|completion-review`, and the rp-surface `review-rounds increment` path) - all backends, all three review kinds.
- Outcome classification at the wrapper level: verdict-bearing vs transport-failure (no verdict tag in output, nonzero transport exit, timeout, unparseable/empty output).
- Round accounting: keep the tamper-resistant pre-dispatch increment, add a refund on classified transport failure. Refunds are only ever issued for dispatches with NO verdict; every refund is durably logged (spec/task-scoped attempt log with timestamp, backend, failure class, output digest) so refund behavior is auditable and not gameable.
- Transport-failure budget: consecutive transport failures per review id get their own small bound (default 2); exceeding it exits with a DISTINCT error code/message (transport-unhealthy, retryable-after-human/env fix) - never the cap's `ESCALATE` (exit 4), which remains reserved for genuine non-convergence.
- Receipts: a failed dispatch must not silently delete/omit the receipt; write an attempt record (mode, failure class, no verdict) so callers and Phase-5-style audits can see what happened.
- Skill prose (plan-review / impl-review / spec-completion-review, all backends incl. the rp explicit-increment path + Codex mirror via sync-codex): reflect the new semantics - retry-on-transport-failure is sanctioned and does not touch the cap; never manually reset for transport burns again.
- `review-rounds` CLI surface: expose the attempt log (`review-rounds attempts <id>` or similar) and show burned-vs-real counts in the ESCALATE message.

## Boundaries / non-goals

- No change to cap size/defaults, the SHIP-reset rule, or the explicit re-plan reset ceremony.
- No retry automation beyond the bounded transport budget (no exponential backoff machinery).
- Verdict-bearing rounds always count, including MAJOR_RETHINK - a delivered verdict is never refundable.
- No change to the walkthrough/validator/deep-pass phases.

## Acceptance Criteria

- **R1:** A dispatch whose output contains no verdict tag (or fails at the transport level) does not consume a review round: the pre-dispatch increment is refunded, and a durable attempt record (backend, kind, failure class, timestamp) is written; verdict-bearing dispatches consume exactly one round each, never refundable.
- **R2:** Consecutive transport failures per review id are bounded (default 2) with a distinct non-ESCALATE error surface; the cap's ESCALATE remains exclusively for verdict-bearing non-convergence.
- **R3:** All backends (codex, copilot, cursor internal increments; rp explicit increment) and all three review kinds share the same classification + refund semantics, with tests per backend covering: no-verdict output, nonzero exit, timeout/empty output, and a normal verdict round.
- **R4:** Failed dispatches leave an attempt receipt/record instead of deleting or omitting the receipt; the ESCALATE message and a CLI surface report real-vs-burned attempt counts.
- **R5:** Skill prose (canonical + Codex mirror) documents the semantics; sync-codex passes; no skill instructs a manual reset for transport-burned rounds.
- **R6:** Refund auditability: the attempt log makes every refund traceable (no silent counter mutation); a test proves a crafted "reviewer output missing the tag" case refunds while a real NEEDS_WORK does not.
