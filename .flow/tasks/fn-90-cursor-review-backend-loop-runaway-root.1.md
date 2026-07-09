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
Implemented and validated the fn-90 root-cause fixes for the Cursor review-backend loop runaway: R3 honest verdict extraction (codex/copilot parse the isolated final agent message, last-match — poison `<verdict>` literals in tool output can no longer win), R4 convergence ratchet (re-review injects prior findings with a shrink-only contract), R5 deterministic cumulative round cap (flowctl-owned counter on spec state, refuses at MAX_REVIEW_ITERATIONS with an ESCALATE marker + exit 4, resets on SHIP/re-plan, plus `spec reset-review-rounds`), and R7 cursor persona-override preamble on all cursor review paths.

Validated live on the pinned fn-89 baseline fixture (cursor gpt-5.5-high + codex gpt-5.5): all verdicts now honest end-to-end (poison confirmed live in both codex streams, correctly isolated); the Cursor fix->re-review ratchet cycle converged to SHIP in 2 rounds (<=3) with the prior finding verified fixed and no genuine >=Major suppressed. All four assumptions HELD. Post-fix outputs + delta archived under .flow/artifacts/fn-90-baseline/after/. +39 new tests; full suite 1512 passing (green baseline); dual flowctl copies kept in sync.
## Evidence
- Commits: 65933c8f9064d55a834d368f68f617f5bc5c853a
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1512 passing, baseline: green), live cursor+codex plan-review validation on fn-89 fixture (archived .flow/artifacts/fn-90-baseline/after/)
- PRs: