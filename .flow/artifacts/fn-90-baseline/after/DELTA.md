# fn-90 post-fix validation — delta vs baseline

Same fixture as `../summary.json` (spec **fn-89-tracker-sync-lifecycle-dispatches-off**,
identical `--files` list). Re-run AFTER the fn-90 fixes (R3 verdict extraction, R4
convergence ratchet, R5 deterministic cap, R7 cursor persona override). Live
`cursor-agent` (gpt-5.5-high) + `codex` (gpt-5.5) runs.

## Verdict honesty (acceptance a) — verdicts now honest end-to-end

| run | backend | baseline flowctl → true | **after** flowctl verdict | true verdict | honest? |
|-----|---------|-------------------------|---------------------------|--------------|---------|
| x1  | codex   | **SHIP → NEEDS_WORK** (parse bug) | NEEDS_WORK | NEEDS_WORK | ✅ |
| x2  | codex   | NEEDS_WORK → NEEDS_WORK | NEEDS_WORK | NEEDS_WORK | ✅ |
| c1  | cursor  | NEEDS_WORK → NEEDS_WORK | NEEDS_WORK | NEEDS_WORK | ✅ |
| c2  | cursor  | NEEDS_WORK → NEEDS_WORK | NEEDS_WORK | NEEDS_WORK | ✅ |

**R3 verdict-extraction fix — live confirmation of the poison mechanism:**
- x1 raw codex stream: **2** `<verdict>` literals; only **1** in the agent
  message. Poison came from a `command_execution` `aggregated_output` echoing
  repo file content the reviewer grepped.
- x2 raw codex stream: **4** `<verdict>` literals; only **1** in the agent
  message — 3 poison literals from a single `rg` command's tool output. The fix
  (`extract_codex_final_message` + last-match) collapses the 4 ambiguous
  literals to the 1 authoritative verdict.
- In these two live runs the poison literals happened to also be `NEEDS_WORK`,
  so old-first-match and new-agent-last-match agree — but they prove the
  pollution channel is **live and frequent** (every review that greps the repo).
  The baseline `x1` is the recorded case where the identical mechanism produced
  a false **SHIP** (grep echoed `smoke_test.sh`'s `<verdict>SHIP</verdict>`
  assertion). The divergent SHIP-poison case is locked in a deterministic unit
  test (`test_codex_verdict_extraction.py::test_both_pollution_shapes_combined`).

## Convergence ratchet (acceptance b) — SHIP in ≤3 rounds

One full fix→re-review cycle on the **Cursor** backend:

- **Round 1** (`c1`, fresh): NEEDS_WORK. Major finding — `fn-89.2` completion-
  review dispatch instructs `event: work.completionReview`, contradicting the
  epic's top-level `completionReview` requirement (reintroduces the shipped
  2.9.1 audit bug).
- **Fix**: changed both `work.completionReview` references in
  `.flow/tasks/fn-89-tracker-sync-lifecycle-dispatches-off.2.md` (lines 21, 52)
  to `completionReview`.
- **Round 2** (`ratchet-round2`, resumed session + injected prior findings):
  **SHIP** — reviewer text: *"Prior finding: **fixed**. … No new ≥ Major
  blocker introduced by the fix."* Converged in **2 rounds** (≤3 ✅).

The re-review preamble carried the CONVERGENCE RATCHET block (prior findings +
shrink-only contract). The reviewer verified the prior finding fixed and did NOT
re-derive a fresh finding set — exactly the ratchet behavior (vs. the baseline
~50% fresh-finding churn between c1/c2).

## No ≥Major suppressed (acceptance c)

- Round 2 SHIP is honest: the sole injected prior finding was genuinely fixed
  (verifiable in `fn-89.2` — no `work.completionReview` remains in plan
  instructions), and the reviewer explicitly reported no new ≥Major introduced.
- The ratchet did **not** suppress `c2`'s independent second Major (the fn-89.1
  "Step 0 proof point" concern). That finding was never in `c1`'s prior set
  (the round-1 receipt driving the ratchet), was not introduced by the fix, and
  is a pre-existing plan concern about a *different* task — correctly outside
  the shrink-only re-review's blocking scope (convergence, not leniency). It
  remains a real finding for fn-89 to address separately; it was not silently
  dropped, just not in-scope for THIS re-review's prior-finding set.

## Deterministic cap (acceptance — R5) — end-to-end

- `plan_review_rounds` incremented on each dispatch and **reset to 0 on the
  round-2 SHIP** (observed live). Unit tests
  (`test_review_convergence_cap.py`) prove: survives fresh invocations, refuses
  at cap 3 with an ESCALATE marker + exit 4, idempotent at cap, per-task impl
  counters, `spec reset-review-rounds` re-plan reset.

## Assumptions: held / adjusted

- **R3 (verdict poison):** HELD. Poison is live and frequent (grep/rg echoing
  repo `<verdict>` literals into `command_execution` output). Fix isolates the
  agent message cleanly.
- **R4 (convergence ratchet):** HELD. Injecting prior findings + shrink-only
  contract converged the Cursor re-review to SHIP in 2 rounds with the prior
  finding verified fixed and no genuine ≥Major suppressed.
- **R5 (deterministic cap):** HELD. Flowctl-owned counter survives fresh
  invocations, refuses at the cap, resets on SHIP/re-plan.
- **R7 (cursor persona override):** HELD (prompt-level). The override rides at
  the head of the cursor prompt (verified reaching `run_cursor_exec` in tests);
  cursor verdicts stayed honest and scoped. A rigorous A/B isolating persona
  effect from model effect is the deeper R7 half — the measurement half here
  confirms the override is delivered and does not regress verdict honesty.

Files: `x1/x2/c1/c2` = fresh runs; `ratchet-round2` = the re-review SHIP.
`*.receipt.json` = full receipts; `*.clean.md` = agent-message-only review text.
