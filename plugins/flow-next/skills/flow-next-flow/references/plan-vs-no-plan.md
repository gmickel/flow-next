# Plan versus no-plan rule

## The rule

**Direct execution through `flow-next:flow-next-work <spec-id> --no-plan` is the default for a ready spec.**

Plan is chosen only on a positive signal:

1. The user asked for a plan.
2. Separate human owners will implement.
3. Delivery is staged across several PRs.

Risk, size, and file count never trigger plan on their own. Design risk routes to `flow-next:flow-next-plan-review` (which reviews a spec with zero tasks). Unresolved product or authority choices route to `flow-next:flow-next-refine`. Unknown model identity creates no detector and no question.

**When to refine.** A person who asks to be interviewed on a spec gets refine, with the role or audience they stated as its lens (`--biz` for product or business, otherwise `--scope=<their words>`); refine's own test still decides what it asks. Otherwise refine only when you can name at least one open decision that would change what gets built and that only the human can make. Do not refine when the acceptance criteria state the intended behaviour and what remains is how; when the touched area has established patterns; when the only gaps are technical detail, performance, or edge cases that implementation, review, and QA will surface; when the only uncertainty is criteria capture inferred itself; or for a defect, a structural cleanup, or a measured-improvement request. A technical question needs a named technical fork that is costly to reverse and that the code does not answer (a data model or migration, a public contract, a security boundary).

## What the direct route keeps

Implementation review per `review.backend` or the invocation flag, acceptance coverage from the single implicit owner task's `satisfies` list, the single-task completion-review skip, and QA per `pipeline.qa`. The worker keeps its broad parallel license. Nothing here changes scheduling.

## Printing the recommendation

Both the manual path (capture's closer, plan's menu, work's ask) and the flow path print the rule's result the same way:

```
Recommended next: /flow-next:work <spec-id> --no-plan - ready cohesive spec; no positive plan signal
Recommended next: /flow-next:plan <spec-id> - <which positive signal: asked | separate owners | staged PRs>
Recommended next: /flow-next:refine <spec-id> - <the named open decision>
```

Under flow, the route is recorded before mint (`flowctl spec set-no-plan` for direct, `spec clear-no-plan` for plan). Under manual capture the field is set only by the explicit `--no-plan` flag; the recommendation is printed either way.
