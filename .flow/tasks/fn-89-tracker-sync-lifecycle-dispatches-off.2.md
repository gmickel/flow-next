---
satisfies: [R1, R2, R3, R4, R6, R7, R10, R11, R12]
---

# Work-skill touchpoints + Phase 5 pre-audit join + per-spec ledger

## Description

Size: M
Files:
- `plugins/flow-next/skills/flow-next-work/phases.md` (3b.1, 3d.1, 3g, Phase 5 join)
- `plugins/flow-next/skills/flow-next-work/references/tracker-touchpoints.md` (First claim / Task done / Completion review dispatch blocks)
- Regenerate `plugins/flow-next/codex/`

Rewire the three work-skill lifecycle touchpoints to dispatch the `tracker-runner` (from .1) instead of running tracker-sync inline, add the per-conversation ledger + state-shaped serialization in the work conductor, and make the Phase 5 end-of-run `sync check` a pre-audit join.

## Approach

1. **firstClaim (state-shaped, awaited — R2).** In `tracker-touchpoints.md` "First claim" (:43-60, dispatch at :52) change the inline `skill: flow-next-tracker-sync (operation: push <spec-id>, status-only, event: work.firstClaim)` to a host `Task flow-next:tracker-runner` carrying `operation: push <spec-id>`, `event: work.firstClaim`, `DISPATCH: forked` — AWAITED at the touchpoint (record its handle in the ledger, then join before continuing). The phases.md 3b.1 gate (:205-223) is unchanged (still prints the STOP sentinel → read the reference); only the reference's dispatch body changes.
2. **task done (fire-and-forget — R1, R10).** In `tracker-touchpoints.md` "Task done" (:62-79, dispatch at :72) change to a fire-and-forget `Task flow-next:tracker-runner` (`operation: comment <spec-id>`, `event: work.done`, `DISPATCH: forked`): record the handle in the ledger and continue immediately (no await). phases.md 3d.1 gate (:298-316) unchanged.
3. **completionReview (fire-and-forget — R1, R10).** In `tracker-touchpoints.md` "Completion review" (:81-102, dispatch at :95) and phases.md 3g (:407-448, dispatch note at :443-445) change to fire-and-forget `Task flow-next:tracker-runner` (`operation: comment <spec-id>`, `event: work.completionReview`, `DISPATCH: forked`) — comment-shaped only, NEVER terminal Done (keep the fn-66 non-terminal doctrine verbatim). Record handle, continue.
4. **Ledger + serialization (R3).** Add prose in the work conductor (phases.md Phase 3 header, near the delegation counter init at ~:318 / the Phase 3 loop) describing the per-conversation ledger (spec id → outstanding runner handle). Rule: comment-shaped dispatches (done/completionReview) may overlap freely; a STATE-shaped dispatch (firstClaim) first AWAITS any outstanding dispatch on the spec. Since firstClaim fires once and before any done-comment, the natural ordering already holds — state it explicitly so the invariant is documented.
5. **Phase 5 pre-audit join (R4).** In phases.md Phase 5 (:506-546), BEFORE the `sync check` (:528), add a step: await ALL outstanding tracker-runner dispatches for `$SPEC_ID` (join the ledger handles). Then the existing check reads settled receipts. Keep the retro-fire-once cycle (:537-546) and the four-state `Tracker sync:` summary slot (:548-556) unchanged. On compaction/resume with unknown handles, fall through to `sync check` semantics (receipts on disk are truth) — note this. **R4 is a PROSE contract** here, validated by the .1 Step 0 live interleave + the already-demonstrated audit race (Feasibility) — do NOT add a receipt-timeline unit test for the join timing; `test_sync_check.py` only guards the underlying `sync check`/`--since` semantics (the audit primitive the join calls).
6. **Ask-after-join + summary (R6, R7).** Wire the outcome lines into the mandatory summary: fire-and-forget outcomes surface in the `Tracker sync:` slot / summary; a `queued` outcome (genuine conflict) is reported, and — interactive only — the host MAY surface it via `AskUserQuestion` after the Phase 5 join. Under Ralph, route to stderr as today (no new stdout).
7. **Timeout (R12).** Document the 10-min awaited bound at the firstClaim await and the Phase 5 join: on timeout/death of an AWAITED op treat as transport-unreachable (event-tagged errored receipt via host, continue). **Fire-and-forget deaths (done/completionReview) get NO host-side receipt** — `sync check` clears on ANY event-tagged receipt, so the unwritten receipt is exactly what makes the Phase 5 pre-join audit report MISSING and retro-fire once; a host-written receipt there would kill the backstop.
7b. **Linked-spec precondition for fire-and-forget (R1/R3).** Before classifying done/completionReview as fire-and-forget, the host checks the spec is LINKED (ledger knowledge or a cheap `sync get-state` probe for `tracker.id`). On an UNLINKED spec the comment op triggers tracker-sync's create-if-unlinked (writes tracker id + merge-base pair + lastSyncedAt) — classify it STATE-shaped for that first touch: awaited + serialized per the R3 ledger rule. Overlapping comment dispatches on an unlinked spec would race to create duplicate issues / torn link state.
7c. **completionReview event-key normalization (R9 — confirmed live bug).** The dispatch + audit currently use `event: work.completionReview` (phases.md:543, :524) but the config leaf is TOP-LEVEL `tracker.perEvent.completionReview`, so `_per_event_enabled("work.completionReview")` resolves to None → False and `sync check` can NEVER report it missing (the retro-fire backstop this task's fire-and-forget class depends on is dead today). Normalize the EVENT TAG to `completionReview` (drop the `work.` prefix) at phases.md:543 + :524 and in the tracker-sync steps.md Phase 0 example event list — do NOT move the config leaf (shipped user configs + the discovery ceremony already write the top-level key).
8. **inline hatch (R5 consumer).** Each rewritten gate must honor `tracker.dispatch` — when `inline`, run the op inline exactly as today (byte-identical), skipping the fork. Reference the .1 capability gate + leaf; do not re-derive.
9. Regenerate the Codex mirror; confirm the new `Task flow-next:tracker-runner` tokens are rewritten and the guard + mirror-parity test pass. The tokens introduced here are covered by the GLOBAL sync-codex sweep landed in .1 (a single `find … -exec sed` over all mirror skill markdown) — add NO new per-file rewrite rule; just regenerate + verify.

## Investigation targets

Required:
- `plugins/flow-next/skills/flow-next-work/references/tracker-touchpoints.md` (whole file — the three dispatch blocks)
- `plugins/flow-next/skills/flow-next-work/phases.md:205-223` (3b.1), `:298-316` (3d.1), `:407-448` (3g), `:506-556` (Phase 5 join + retro-fire + summary)
- `plugins/flow-next/agents/tracker-runner.md` (the .1 contract — inputs to pass)

Optional:
- `plugins/flow-next/skills/flow-next-work/phases.md:318-345` (Phase-3 counter init pattern — where ledger prose fits)
- `plugins/flow-next/tests/test_sync_check.py` (`test_cli_receipt_event_round_trip` — guards the `sync check`/`--since` semantics ONLY; R4's host-side join is a prose contract, NOT a receipt-timeline test — see Approach Step 5)

## Key context

- The phases.md gate blocks (the `RAW=... ACTIVE=... STOP sentinel` shape) are UNCHANGED — the STOP-and-read-the-reference indirection stays; only the reference's dispatch body and the Phase 5 join change. Do not touch the gate probe shape (fn-81 gate-skeleton, fail-open).
- fn-85 Tier B will later trim these SAME gate blocks — leave them trimmable; do not restructure beyond the dispatch body + join.
- firstClaim is the ONLY state-shaped op in the work skill; done + completionReview are comment-shaped. Only firstClaim awaits; the two comments fire-and-forget (their backstop is the Phase 5 join — R10).
- Keep the fn-66 completionReview doctrine verbatim (comment-shaped, never terminal Done; land.merged is the sole Done driver).
- Regenerating the mirror is required; do NOT bump version.

## Acceptance

- [ ] tracker-touchpoints.md First-claim dispatch is an AWAITED `Task flow-next:tracker-runner` (push, event: work.firstClaim, DISPATCH: forked); Task-done + Completion-review are fire-and-forget runner dispatches (comment, event: work.done / work.completionReview).
- [ ] phases.md Phase 3 carries the ledger + state-shaped serialization prose; firstClaim-before-done ordering stated.
- [ ] phases.md Phase 5 awaits outstanding same-spec dispatches BEFORE `sync check`; retro-fire-once + four-state `Tracker sync:` slot unchanged; compaction fallthrough noted.
- [ ] Fire-and-forget + queued outcomes surface in the summary; interactive host-side ask-after-join documented; Ralph routes to stderr.
- [ ] 10-min await bound + errored-on-timeout documented at the await sites.
- [ ] `tracker.dispatch inline` restores byte-identical inline behavior at all three touchpoints.
- [ ] Codex mirror regenerated; `Task flow-next:` guard + `test_tracker_sync_mirror_parity.py` green; `uvx pytest plugins/flow-next/tests -q` green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
