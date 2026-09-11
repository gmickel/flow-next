# Plan versus no-plan rule (routing reference 3 of 6)

**Decision record**

- Source: the maintainer's direction that direct execution is the default; capture's closer, plan's menu, work's zero-task ask, and pipeline-variations each carried a copy before this file.
- Trigger: a ready spec has no tasks and no recorded route - flow before mint, capture's closer, plan's next-steps menu, work's zero-task fork, `flow --explain`.
- Purpose: one statement of the default and the positive signals that override it.
- Evidence: internal benchmarking found the direct route can produce higher-scoring implementations with capable frontier models because the owner sees the whole task; scaffolding around a model's current weakness rots into cost.
- Disposition: keep, single copy. Decomposition is the exception with a stated reason.

## The rule

**Direct execution through `/flow-next:work <spec-id> --no-plan` is the default for a ready spec.**

Plan is chosen only on a positive signal:

1. The user asked for a plan.
2. Separate human owners will implement.
3. Delivery is staged across several PRs.
4. The implementer is routed out of the session model - an `implementer:` line in the project routing block that points at a bridge or a cheaper tier.

Risk, size, and file count never trigger plan on their own. Design risk routes to `/flow-next:plan-review` (which reviews a spec with zero tasks). Unresolved product or authority choices route to `/flow-next:interview`. Unknown model identity creates no detector and no question.

## What the direct route keeps

Implementation review per `review.backend` or the invocation flag, acceptance coverage from the single implicit owner task's `satisfies` list, the single-task completion-review skip, and QA per `pipeline.qa`. The worker keeps its broad parallel license. Nothing here changes scheduling.

## Printing the recommendation

Both the manual path (capture's closer, plan's menu, work's ask) and the flow path print the rule's result the same way:

```
Recommended next: /flow-next:work <spec-id> --no-plan - ready cohesive spec; no positive plan signal
Recommended next: /flow-next:plan <spec-id> - <which positive signal: asked | separate owners | staged PRs | routed implementer>
```

Under flow, the route is recorded before mint (`flowctl spec set-no-plan` for direct, `spec clear-no-plan` for plan). Under manual capture the field is set only by the explicit `--no-plan` flag; the recommendation is printed either way.
