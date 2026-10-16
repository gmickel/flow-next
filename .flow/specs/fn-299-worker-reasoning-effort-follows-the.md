# Worker reasoning effort follows the dispatch tier

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 55% [paraphrase], 45% [inferred] -->

Before each worker spawn, work makes one tier call that classifies the task as mechanical, moderate, intelligent or long-running. Only the model follows that answer: a confidently mechanical task can go to the routing block's fast model. Reasoning effort never follows it. Every worker runs at the host's default effort whether it renames a constant or redesigns a scheduler, unless a person spells out an effort in an explicit invocation. [paraphrase]

Thinking time between tool calls is a large share of a worker's wall clock. Lowering effort on routine tasks cuts exactly that, and raising it on the hardest tasks spends it where a wrong first attempt costs most. Keeping the same model family at a different effort changes speed and depth without changing the worker's behaviour or style. [paraphrase]

Target user: anyone running work or `flow --auto` on a spec with a mix of routine and hard tasks, who pays for every worker's thinking time. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **Effort follows the existing tier answer.** The same tier call that already runs before each spawn sets the worker's effort: mechanical runs one level below the host's default effort, moderate and long-running run at the default, intelligent runs one level above. No new judge question, preset or call. [paraphrase]
- **Precedence unchanged.** An explicit invocation (`<model> at <effort>`), a role that pins its model or effort, and an effort written in the project's routing block all win over the tier, exactly as an explicit model wins today. [paraphrase]
- **No judge key, no change.** When the tier call cannot run (no key, judge disabled, judge unavailable), effort stays at the host default, matching how the model tier falls back to the session model. [paraphrase]
- **Only where a spawn can carry it.** The effort reaches hosts whose spawn takes an effort parameter and bridges that take a reasoning effort. Where neither exists, the worker runs as today and the dispatch line says effort was not applied. A spawn that rejects the requested effort is retried once at the host default, never at a third level, and the line says so. [paraphrase]
- **Visible.** The dispatch's tier line names the effort applied (or not applied, with the reason), and the task's done summary keeps it, as it already keeps the tier line. [paraphrase]
- **Workers only.** Scouts keep their own model and effort selection. [inferred]

## Examples
<!-- scope: both -->

Tier lines a reviewer would see in a done summary (shape follows the existing line; wording is the implementer's):

```text
Tier: mechanical (jev 0.91) -> fast model at low effort (host default medium)
Tier: session (jev intelligent 0.84) at high effort (host default medium)
Tier: session (jev moderate 0.77) at default effort
Tier: implementer - opus at xhigh (explicit invocation)
Tier: session (jev-unavailable(no key)) at default effort
Tier: mechanical (jev 0.88) -> fast model; effort not applied (host spawn takes no effort)
```

[inferred]

A spec with five tasks: two config bumps and a doc mirror (mechanical, low effort), a bounded parser fix (moderate, default), and a scheduler redesign across modules (intelligent, high). Without a judge key all five run at the default, as today. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- The host's default is already its lowest level: mechanical stays at that level. Its highest is already the default: intelligent stays there. [inferred]
- A running worker is never re-tiered; the effort is fixed at dispatch, like the model. [paraphrase]
- Bridged children receive the effort through the bridge's own reasoning-effort setting; a bridge without one runs unchanged and says so. [inferred]
- A low-effort worker whose task turns out harder than the tier said follows its normal escalation; work never silently re-dispatches at a higher effort. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** With a judge available, each worker's effort follows its tier: one level below the host default for mechanical, the default for moderate and long-running, one level above for intelligent, bounded by the host's lowest and highest levels. Errors: no tier answer → host default. [paraphrase]
- **R2:** An explicit invocation effort, a role pin or a routing-block effort wins over the tier effort. An explicit invocation that names a model but no effort keeps that model and still takes the tier effort: the tier call runs and its answer sets the effort, even though the explicit branch of `judge_tier_dispatch` ignores the answer for model selection today. No error surface beyond today's precedence rules. [paraphrase]
- **R3:** Without a judge key, or when the judge is disabled or unavailable, every worker runs at the host default effort. No error surface. [paraphrase]
- **R4:** The effort reaches the worker through the host's spawn effort parameter or the bridge's reasoning-effort setting; where neither exists, or the spawn rejects the level, the worker runs at the default and the tier line says why. Errors: rejected level → one retry at the default, never a third level. [paraphrase]
- **R5:** The tier line names the effort applied or not applied, and the done summary keeps it. No error surface. [paraphrase]
- **R6:** A replay on the maintainer's worker fixture bank, with mechanical fixtures added and the model pin current, shows no lower pass rate on the shipped tests and shorter wall time on mechanical fixtures at the lowered effort; a same-time control run of the large-feature case in the end-to-end comparison harness shows no extra review rounds and no longer total time. No error surface beyond the studies' verdicts. [inferred]

## Boundaries
<!-- scope: business -->

- No change to model selection, the tier question, its categories or its fallback. [paraphrase]
- No fast mode or speed setting; effort only. [inferred]
- No change to scouts or reviewers. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The tier call already answers how hard a task is; using that answer for effort as well costs no extra call and keeps the model family, so diversity and behaviour stay as configured. [paraphrase] The maintainer decided on 2026-10-15 that without a judge key effort stays at the host default rather than following a code rule from task signals, matching the model tier's fallback. [paraphrase] The main risk is a lowered effort producing weaker diffs that cost extra review rounds and end slower overall; R6 measures exactly that before release. [inferred]

Delivery order: 4 of 6 in this set; independent. Route: direct. [paraphrase]

The model-only case in R2 (added 2026-10-16) matters because callers that pin the implementer's model still want per-task effort. MergeFoundry adds "use <model> for the implementation" to every flow run it starts, and never an effort. If an explicit model also pinned the effort, this spec would never change effort for those runs. [inferred]

## Strategy Alignment

Serves the **Cross-platform parity** track (effort reaches each host through its own parameter, or is reported as not applied) and the **Autonomous mode** track (shorter unattended runs at unchanged quality). Follows the **Agent first** design principle: no new field or question; the tier line is written at dispatch.

## Strategy Conflicts

None found.
