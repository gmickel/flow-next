# Review, QA, and completion-review selection (routing reference 4 of 6)

**Decision record**

- Source: the review-backend grammar (`docs/flowctl.md`), the `pipeline.qa` gate, work's completion-review policy, the QA freshness probe the unattended driver reads (`qa-stage.md`).
- Trigger: a route reaches a gate - after implementation (review), at all-tasks-done (QA, completion review), before a PR (make-pr's coverage).
- Purpose: one place naming which gate applies and from which config key or flag it is read, so flow and the stage skills agree.
- Evidence: gate policy scattered across skills is the enumeration-site drift class; every routed or skipped stage must leave a `ran` / `skipped(reason)` line.
- Disposition: keep. flowctl stores the values and never interprets them; whether a gate applies is judgment and stays here.

## Implementation review

Runs per `review.backend` or the invocation's `--review=<backend>` flag; `/flow-next:impl-review` resolves the backend itself. `none` skips with `skipped(config: review=none)`. A qualifying `flowctl triage-skip --base <ref>` receipt (docs-only, lockfile-only, release-chore, generated-only) records `mode: triage_skip` and satisfies the gate. Flow never lowers the gate and never fabricates a verdict.

## Design review

`/flow-next:plan-review <spec-id>` runs on an explicit request or when the route names design risk. It reviews a spec with zero tasks; task decomposition is never a prerequisite.

## Live QA

`pipeline.qa` is a string enum `off | on | auto`; any other value is `off`.

- `off`: QA runs only when the user invokes `/flow-next:qa`.
- `on`: QA runs at all-tasks-done, before make-pr, on every spec.
- `auto`: QA runs at all-tasks-done when the spec's acceptance describes UI behaviour on a drivable surface **and** a target can be started (a documented dev server, a deploy URL, or a running instance the QA skill can reach). Otherwise the stage records `skipped(config: pipeline.qa=auto: <no UI-observable criteria | no drivable surface | no startable target>)` and the route advances.

Whether a spec is drivable is judgment, read from the acceptance criteria and the repo (`.flow/features/`, the prime QA-readiness line, a documented start command). QA never hard-blocks the loop; `NEEDS_WORK` and `BLOCKED` advance to the draft PR with their findings. The evidence-aware subtraction inside QA is unchanged: runtime, UI, and integration criteria are always re-driven; deterministic re-runnable tests subtract. Under `flow --auto` the same three values apply at the all-done juncture: `on` runs QA, `auto` runs it on the drivability read above and otherwise records the skip and advances, `off` goes to make-pr.

## Completion review

Unchanged single-task policy: with one minted task whose acceptance is the whole spec, the per-task implementation review is the integration check and completion review records `skipped(policy: single-task, per-task SHIP covers spec surface)`. Multi-task plans run `/flow-next:spec-completion-review` as configured.

## Receipts

Every stage flow routes or skips records one line in the receipt surface that stage already writes - the task's done summary for task-scoped stages, the run's final report for run-scoped ones:

```
stage: <name> - ran [<start>..<end>] | skipped(<policy|config|empty|error>: <detail>) | failed(<reason>: <detail>)
```

`flowctl usage --stages <spec-id>` summarizes the task-scoped lines. A skipped stage is an event with a reason, never an absence.
