---
satisfies: [R1, R2]
---
# fn-203-rolling-frontier-scheduling-with-shared.3 Run the paired draws, blind-score, record the R2 outcome

## Description
Execute the pre-registered study, score it, and record the outcome before any Phase B work starts. This task is the spec's early proof point.

**Size:** M
**Files:** .flow/specs/fn-203-rolling-frontier-scheduling-with-shared.md (Decision Context appendix only); study artifacts live in the eval workspace
**Touches:** [.flow/specs/fn-203-rolling-frontier-scheduling-with-shared.md]

### Approach
- Run paired same-machine draws per the registration: baseline arm on shipped skill state, arms 1 and 2 on their branches; isolated checkout + own state dir per draw.
- Launch every draw's conductor and workers on the registered model configuration (opus-5 at medium effort) and verify it from the host record per draw - read the actual run config/transcript, never a model self-report; a draw that ran on the wrong model or effort is invalidated, not scored.
- Supervise draws live against the registered budgets and abort rules: kill immediately on harness failure, wrong model/effort, runaway review churn, or budget exhaustion; log every kill with its rule and the tokens/wall spent; killed draws are invalidated, not scored. Apply the registered futility rule (and only it) for outcome-based early stopping - no ad-hoc peeking; an early stop records which rule fired and the state at stop.
- Count the five incident classes per draw; classify each as contained or uncontained per R1's definitions.
- Blind-score via the redaction contract; run full deterministic suites per arm.
- Include the named secondary probe: one draw of the leading rolling arm at a cap above 3 (reported, not gating).
- Apply the pre-registered decision rule verbatim; record per-arm pass/fail/inconclusive and the winner (if any) in the study changelog AND append the outcome to this spec's Decision Context.
- On no-arm-passes or inconclusive: close tasks 4-7 unimplemented with the result recorded; the spec closes as a completed negative result.
## Acceptance
- [ ] All registered draws executed with isolation and same-second concurrent arm launches as registered (or invalidated draws documented per R1's error path, with the kill rule and spend logged)
- [ ] Model/effort verified per draw from the host record, never a self-report; wrong-model draws invalidated
- [ ] Decision rule and futility rule applied verbatim; outcome recorded in study changelog and spec Decision Context
- [ ] Gate fail/inconclusive path honored: downstream tasks closed unimplemented if no arm passes
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
