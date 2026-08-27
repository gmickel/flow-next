# Reviewer verification budget - focused suites only, the full gate belongs to quiesce

## Goal & Context

Observed live (2026-08-27, fn-205 rolling run): a host-backend impl-review re-reviewer, told the pinned suites were green and that it "may run read-only test commands", chose `python3 -m unittest discover` over the whole 192-file suite (serial, `timeout 580`) - on the critical path of a rolling run, where conductor-owned review blocks the next admission. The verdict was delayed ~10 minutes for verification the run already owns elsewhere: workers run focused suites in their workspaces, the conductor runs the focused integrated verify before each `done`, and the full gate runs exactly once at quiesce (rolling-scheduler 3f: "the full gate runs only here, never per task").

The budget discipline exists on the work/rolling side but is written nowhere the REVIEWER can see it. Neither `impl-review-prompt.md` nor the backend workflows tell the reviewer which verification is already covered by the run's architecture, so a thorough fresh-context reviewer rationally escalates to the full suite. On worker-owned review backends this hides inside worker wall time; with conductor-owned review (rolling, host-deferred) it becomes visible tail latency on every round. Same lesson as the wall-clock research finding on review scoping/churn dominating wall variance - new surface: reviewer TEST scope, not finding churn.

## Acceptance Criteria

- R1: The impl-review rubric states the verification budget in one rail: a review round verifies via the task's Quick commands / the focused suites its evidence names (plus targeted commands the findings themselves need); the FULL suite belongs to the run's final gate (work Phase 4/5, rolling quiesce), never to a review round. A reviewer that ran the whole suite has broken this. Errors: the rail must not forbid running the specific test a finding disputes - targeted verification stays licensed.
- R2: Both places that compose reviewer dispatch prompts for backends where the coordinator writes the prompt (impl-review `workflow-host.md`; spec-completion-review's host path if it shares the shape) carry the budget line, stated once by pointer to the rubric, not restated. Codex/copilot/cursor backends inherit it via the rubric the dispatch already sends.
- R3: `test_prompt_text_pinned` hashes updated in the same commit with the rationale (deliberate prompt change: reviewer verification budget rail); no other prompt text changes ride along.

## Boundaries

- No enforcement machinery: no test-command detection, no wrapper, no flowctl surface - this is a prose rail, same class as the read-only conduct lines. (Bitter-lesson rule: state the bar in one general sentence before building a mechanism.)
- Do not touch worker/rolling verification contracts - they are already correct; the gap is reviewer-side only.
- Codex mirror via the standard single sync-codex regen; no new transforms expected.
- Out of scope: review finding-churn scoping (wall-clock research finding #6 proper) - separate, larger lever with its own eval.

## Decision Context

- Trigger receipt: fn-205 rolling run, task .2 re-review round 2, reviewer process observed running `timeout 580 python3 -m unittest discover -p 'test_*.py'` at 13:02 while .5 admission was blocked on the verdict. Round-1 reviews that scoped to pinned suites returned in 3-5 min; this round ~10 min.
- Why prompt rail and not conductor-side scoping: the reviewer is an executor with a shell (fn-74/fn-169 doctrine); the budget is information it lacks, not judgment it should be denied. One sentence in the rubric closes it for every backend at once.


## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Budget rail in both reviewer prompts (targeted verification stays licensed) | fn-206-reviewer-verification-budget-focused.1 | — |
| R2 | Host dispatch pointers + byte-identical flowctl mirror constants | fn-206-reviewer-verification-budget-focused.1 | — |
| R3 | Same-commit hash-pin update with rationale | fn-206-reviewer-verification-budget-focused.1 | — |

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_backend_spec test_skill_prose_diet -q
```
