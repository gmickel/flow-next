# Review failures name their cause, a rewritten spec loses its plan SHIP, land reports a queued merge

## Goal & Context

Three issues reported by @sn-furali on 2026-10-05, each fixed in its smallest truthful form. [paraphrase]

1. GitHub #515: when the codex account behind a review hits its usage limit, every draw fails in seconds and is recorded as `nonzero_exit`; the skill retries it and the terminal text says to repair a healthy backend. The cause is only visible in the CLI's own output (codex `--json` ends with `{"type":"error","message":"Your workspace is out of credits..."}` and a `turn.failed` event). Other CLIs print their own quota text (Copilot printed "You've reached your additional usage limit for your plan" on stdout with exit 0). [paraphrase]
2. GitHub #514: `spec set-plan` already resets a policy-excused completion review when it rewrites a spec, but leaves a plan-review `ship` in place, so a spec refined after its SHIP routes straight to work with tasks that predate the new criteria. [paraphrase]
3. GitHub #516 (partial): under a merge queue, land's own merge call enqueues the PR and the re-read finds it still open; what land reports then is unspecified. [paraphrase]

<!-- Source: 40% user / 55% [paraphrase] / 5% [inferred] -->

## Acceptance Criteria

- **R1:** A review run that returns no verdict records the CLI's own last error text (codex: the message of the last `error` or `turn.failed` event in its JSON stream; any other backend: the last non-empty output line), bounded in length, on the attempt row and the draw's result, and prints it in the failure line and the TRANSPORT_UNHEALTHY terminal text. It works the same on every CLI reviewer through the shared runner. No new failure class and no list of provider phrases. Errors: no output at all records no message, as today. [paraphrase]
- **R2:** The review skills (implementation, plan, completion) tell the agent that when that message reports a usage, credit or spend limit, it does not retry and stops with the message; every other transport failure keeps today's retry-once rule. Errors: no error surface. [paraphrase]
- **R3:** `spec set-plan` sets a `ship` plan review to a new status `stale` when it changes the spec body (same lock shape and JSON report as the existing excused-completion reset); any other status, and a write that leaves the body unchanged, is untouched. `spec set-plan-review-status` accepts `stale`. Errors: a concurrent verdict write is never clobbered. [paraphrase]
- **R4:** Work and `/flow-next:flow --auto` treat a `stale` plan review like `needs_work` for a spec with any number of tasks: plan-review runs before work. Specs reading `unknown` (never reviewed) route exactly as today. Errors: no error surface. [paraphrase]
- **R5:** After refine changes a planned spec's body, its next step names `/flow-next:plan-review <id>`; otherwise it stays `/flow-next:work <id>`. Errors: no error surface. [paraphrase]
- **R6:** When land's merge call leaves the PR open because it was added to a merge queue, land reports `QUEUED` (not a failure), runs no post-merge tracker step, and tells the person to run `/flow-next:land <pr>` again after it merges (the existing already-merged replay runs the tracker step). Errors: an open PR that is not queued keeps today's handling. [paraphrase]
- **R7:** Parity on every harness (Codex mirror regenerated), docs and the CHANGELOG Unreleased entry updated crediting @sn-furali for #514, #515 and #516; full suite and gates pass. Errors: no error surface. [paraphrase]

## Boundaries

- No `usage_limit` failure class, no provider phrase table, no reset-time parsing (#515's proposals 1 and 4). [paraphrase]
- No digest of what each SHIP reviewed (#514's proposal 2). [paraphrase]
- No new flowctl verb for merges outside land (#516's main ask); that is decided separately. [paraphrase]
- No change to how `unknown` plan reviews route. [paraphrase]

## Decision Context

- **Maintainer, 2026-10-05:** "go ahead with the other ones where we have clear fixes and are low risk"; worried about machinery for #515. Agent first: surface the CLI's own words and let the agent judge, rather than classifying provider text in code. [paraphrase]
