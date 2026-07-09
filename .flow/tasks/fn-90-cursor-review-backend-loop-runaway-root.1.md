# fn-90-cursor-review-backend-loop-runaway-root.1 Implement fixes + validate assumptions against the fn-90 baseline dataset

## Description
TBD

## Acceptance
Covers R3, R4, R5 (minimal), R7 (measurement half). Assumption-test task: implement the minimal working version of each fix, then rerun the SAME dataset and prove the theories hold. If a theory fails, STOP and report — do not proceed to productionization on a broken assumption.

- [ ] Verdict extraction (R3): codex/copilot paths parse only the final agent message; parser takes last match. Poisoned-stream fixture (tool-output literal + quoted-grammar literal) parses to the true verdict — add as a unit/smoke test.
- [ ] Convergence ratchet (R4): receipt stores prior findings; `build_rereview_preamble` injects them with the shrink-only contract (verify prior fixed; only NEW >=Major blocks; all-fixed + no new >=Major => MUST SHIP).
- [ ] Deterministic cap (R5 minimal): cumulative round counter on spec state, enforced refusal + escalate marker at ${MAX_REVIEW_ITERATIONS:-3}; reset on SHIP/re-plan only.
- [ ] Cursor persona override (R7 half): prepend the supersession preamble on the cursor path.
- [ ] VALIDATION on the same dataset (fixture pinned in .flow/artifacts/fn-90-baseline/summary.json — same spec fn-89, same --files list): (a) rerun 2x fresh cursor + 1x codex plan-review, verdicts now honest end-to-end; (b) drive one full fix->re-review ratchet cycle on the Cursor backend to SHIP in <=3 rounds; (c) spot-check no >=Major baseline finding was suppressed by the ratchet; (d) archive post-fix outputs next to the baseline (.flow/artifacts/fn-90-baseline/after/) with a short delta summary.
- [ ] Write a findings note in the task summary: which assumptions held, which needed adjustment.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
