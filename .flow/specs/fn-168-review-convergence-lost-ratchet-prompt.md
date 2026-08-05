# Review convergence lost: ratchet prompt never states the prior-finding line grammar

## Problem

Three consecutive flow-swarm specs (fn-156, fn-157.2/fn-158.2 impl, fn-158 completion) hit `ESCALATE: review loop stalled (flat-trajectory)` on healthily converging loops — each round's findings were fully fixed and the open set was shrinking (6→1, 7→2), yet the counter refused the final round and the host had to hand-verify and record a basis in evidence.

Root cause, verified against live digests in flow-swarm's `.flow/specs/fn-158-…json` `review_attempts`:

- The digest carries prior findings forward as `status: open, firstSeenThisRound: false` unless the reviewer emits explicit per-ordinal resolution lines. `_review_finding_prior_items` parses those via `_FINDINGS_PRIOR_RECORD_RE` / `_FINDINGS_PRIOR_RE`, which require line-start records shaped `Prior finding #N: fixed|not-fixed|withdrawn` (aliases in `_FINDINGS_STATUS_ALIASES`). The carry-forward comment is explicit: "an omitted prior finding remains current until the reviewer explicitly fixes or withdraws it."
- The re-review ratchet prompt (`flowctl.py` ~11840, "Shrink-only contract") instructs: "For EACH prior finding above, state whether it is now **fixed** or **not-fixed**" — but never states the machine line grammar. Codex complies semantically (prose "All prior findings fixed", requirements tables, `unaddressed: []` in the JSON tail) and emits ZERO parseable records.
- Result: every carried finding stays `open` in the next round's digest; any round raising ≥1 new finding then has `current_open ≥ previous_open` with unimproved worst severity → `_review_stall_classification` returns `flat-trajectory` → ESCALATE at 2/8 rounds, exactly when the loop is one round from SHIP.

Observed digest (fn-158 completion r2): six carried P1s `open/firstSeen:false` + one new P1 = 7 open vs r1's 6 open. The reviewer's own text resolved all six.

## Approach

Fix both sides of the seam; either alone closes the live failure, both make it robust:

1. **Prompt states the grammar (primary).** The shrink-only contract's rule 1 gains the exact machine format with an example block: one line per prior finding, line-start, `Prior finding #N: fixed` / `Prior finding #N: not-fixed` / `Prior finding #N: withdrawn`, using the prior set's ordinals; prose/tables remain welcome but the lines are mandatory. Same wording wherever the ratchet block is emitted (codex/cursor/copilot share the builder; host workflow files already pass structured items).
2. **Parser accepts the aggregate all-clear (fallback).** When a re-review round yields zero parseable prior records AND the response carries an unambiguous aggregate resolution — the structured JSON tail's `"unaddressed": []` (already emitted by the canonical contract) — `_review_finding_prior_items` marks ALL carried priors `fixed` for that round. Any parseable per-ordinal record disables the aggregate path (explicit beats implicit). Absent both signals, today's conservative carry-forward stands.
3. **Classifier honesty guard (belt-and-braces).** A digest whose only `open` items are carried-and-unverified (`firstSeenThisRound: false` with no resolution record this round) must not satisfy `flat-trajectory` on its own — the classifier requires at least one re-affirmed (`not_fixed`) or fresh open finding in the current round before declaring a stall. `same-not-fixed-lineage` and `fresh-introduced-critical` semantics unchanged.

## Non-goals

- No change to the review cap, reservation/refund machinery, or the other stall classes' semantics.
- No new receipt schema fields (aggregate resolution reuses the existing `unaddressed` tail; digest shape unchanged).
- No relaxation for genuinely flat loops: a reviewer that re-affirms the same finding (`Prior finding #N: not-fixed`) twice still stalls exactly as today.

## Acceptance

- **R1:** The ratchet/shrink-only prompt block includes the exact line grammar with an example, and a fixture-driven test proves a codex-style compliant response (per-ordinal lines) yields carried items with correct `fixed`/`not_fixed` statuses in the receipt findings container.
- **R2:** Aggregate fallback: a re-review response with zero parseable prior records and `"unaddressed": []` in the canonical JSON tail marks all carried priors `fixed`; the same response WITH one explicit `Prior finding #2: not-fixed` line disables the aggregate path (only ordinal 2 stays open... others follow explicit/default rules as specified); a response with neither signal carries forward exactly as today. Table-tested.
- **R3:** Classifier guard: a digest pair where the current round's open set consists solely of carried-unverified priors plus new findings, with the new-finding count strictly below the prior round's open count, does NOT classify `flat-trajectory`. The fn-158 completion shape (6 open → 6 carried-unverified + 1 new) is the named regression fixture and must pass through to a normal round-3 reservation. Genuine stalls (re-affirmed `not_fixed` overlap; equal-or-growing fresh open sets) still classify.
- **R4:** End-to-end: a scripted two-round codex-style transcript (round 1 NEEDS_WORK with findings, round 2 NEEDS_WORK resolving all priors in prose + `unaddressed: []` + one new finding) reaches round 3 without ESCALATE under the default caps.
- **R5:** Docs: the review-backend workflow docs describe the prior-finding line grammar and the aggregate fallback; CHANGELOG entry; no behavior change for round-1 reviews or legacy receipts (regression-tested).
