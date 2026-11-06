# Plan only when the person asks for it

## Goal & Context

Teams using `/flow-next:flow` report that it still picks the planned route (plan, task breakdown, workers) more often than it should, instead of the direct route (`work --no-plan`). The planned route is measured slower and more expensive at equal quality, and the research scouts stay reachable without planning (`refine --scope=research`). The maintainer's decision: plan only when the person asks for a plan or a task breakdown. [paraphrase]

Today four things push work toward plan:
- the rule's two judgment signals (separate owners, delivery staged across several PRs);
- flowctl's route regexes, which match descriptive spec text ("the 4-task plan", "touch separate owners");
- the plan skill's trigger text ("Use when planning features or designing implementation");
- work's zero-task question, which lists "Plan first" first.

Several skills also still name `/flow-next:plan` as the way to build. Meanwhile an explicit ask made in the invocation (`/flow-next:flow fn-12 break it into tasks first`) does not reach plan for a ready spec, because the code route reads only the spec body. [inferred]

<!-- Source: 20% user / 40% [paraphrase] / 40% [inferred] -->

## Architecture & Data Models

- The routing rule lives in one shared reference, plan-vs-no-plan. Capture's route judgment, flow's routing, work's zero-task question, refine's closer and goal children all read it, so narrowing the rule changes every one of them. [inferred]
- For a ready spec with no tasks and no recorded route, flowctl's route judge returns the direct route without reading the body; whether the person asked for a plan is the host's reading. [inferred]
- Flow's routing step also treats an ask for a plan or task breakdown in the person's own request as the plan route, the way it already treats an interview request as refine. [inferred]
- The plan skill's trigger text is guarded the way work's is, so Claude Code picks flow for build requests and plan only for an explicit plan or task-breakdown request. [paraphrase]

## Edge Cases & Constraints

- Specs that already have tasks keep their planned route; nothing re-routes existing work. [inferred]
- `--no-plan`, `spec set-no-plan` / `clear-no-plan` and a recorded `no_plan` keep their meaning. [inferred]
- A person naming owners or several PRs without asking for a breakdown gets the direct route; the single task can still deliver several PRs. [paraphrase]
- `/flow-next:plan` itself is unchanged when invoked. [inferred]

## Acceptance Criteria

- **R1:** plan-vs-no-plan names one positive signal: the person asked for a plan or a task breakdown. Separate owners and staged PRs are no longer signals, and size, risk and file count still never are. Errors: no error surface beyond the rule text. [paraphrase]
- **R2:** flowctl's code route for a ready zero-task spec with no recorded route returns the direct route and never reads a plan ask from the spec body; asks, owners, PR counts and plans described in passing all route direct there. Errors: no error surface beyond the decision value. [inferred]
- **R3:** A person's request for a plan or task breakdown, in the flow invocation or in the spec, routes a ready zero-task spec to plan; flow's host reads it, attended and under `--auto`. Errors: a request that only mentions size, owners or PRs routes direct. [inferred]
- **R4:** The plan skill's trigger text limits it to an explicit plan or task-breakdown request, or a flow route to plan; other requests to build a spec or idea go to flow. [paraphrase]
- **R5:** Work's zero-task question lists the direct route first as the recommended option, and describes both options without favouring either. Errors: no error surface beyond the question text. [inferred]
- **R6:** Shipped skills no longer name `/flow-next:plan` as the default way to build or plan a feature (the task-manager skill, prime, prospect, strategy, map); they point to `/flow-next:flow`. Errors: no error surface beyond the text. [inferred]
- **R7:** A pre-registered routing study measures the change, baseline 9.7.0 vs candidate on one model. The candidate picks plan on no-ask states at most once, reaches plan on explicit asks, and Claude Code picks the plan skill on no-ask build prompts at most once. Tests cover R2 and R3, and the Codex mirror, CHANGELOG and affected docs are updated. [inferred]

## Boundaries

- No change to how plan builds tasks, its scouts, plan-review, or worker scheduling. [inferred]
- No removal of `/flow-next:plan` or the planned route. [paraphrase]
- No new flag, config key or verb. [inferred]

## Decision Context

The planned route measured slower and dearer at equal quality, and field reports show the existing rule "Risk, size, and file count never trigger plan" does not hold: agents argue size, owners or staged PRs into a plan. Making the person's explicit ask the only signal removes the judgment that goes wrong and deletes the plan regexes rather than adding machinery. Matching the ask with word lists was tried in review and kept misfiring in both directions ("provide a task plan" missed, "a plan ID" matched), so the ask is the host's reading. Team ownership was considered as a surviving signal and dropped by the maintainer: owners can split one task's work afterwards. [paraphrase]
