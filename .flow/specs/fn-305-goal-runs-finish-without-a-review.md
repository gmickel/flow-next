# Goal runs finish without a review backend or child-PR waits

## Goal & Context

Three goal-mode bugs in 9.3.2, fixed together in one simple spec ahead of the goal-mode redesign,
which is a separate spec. [paraphrase] All three surfaced while reading every surface a `--goal`
run touches during the 2026-10-28 parallel-children study. [inferred]

1. A repository with no review backend configured gets every child built and merged onto the
   integration branch, and then the goal stops at its mandatory final whole-diff review, because
   the review stops when nothing is configured, while each child's own work skips review with a
   note. [inferred]
2. A `--review=<backend>` given on the goal invocation is forwarded to plan, plan-review and work;
   whether it reaches the goal's final review is unconfirmed. [inferred]
3. Under `--until=merge`, land holds every child PR into the integration branch for
   `land.patienceMinutes` (default 10) so review bots can post, although those children reach the
   default branch only through the final PR, which is where bots and humans review. [inferred]

The person asked what happens today when a user "doesn't have review.backend set". The answer
was this stall.

## Acceptance Criteria

- **R1:** With no review backend configured (unset, or `none`), a goal run's final review records
  a skip with its reason in the goal log and in the final pull request's body, and the run goes on
  to open and land the final pull request. The run never ends because no backend is configured.
  Errors: a configured backend that fails to run still stops the run with its reason, as today;
  the run never substitutes another reviewer. [inferred]
- **R2:** A `--review=<backend>` on the goal invocation reaches every review the goal run
  dispatches, the final review included; `--review=none` skips the final review exactly as R1
  does. When the flag already reaches the final review today, the fix only makes that explicit and
  says so in the done summary. No error surface beyond the existing handling of an unknown or
  removed backend name. [inferred]
- **R3:** Under `--until=merge`, a child pull request into the goal's integration branch merges
  once land's other gates pass, without waiting out the review-bot patience window. The final pull
  request into the default branch keeps `land.patienceMinutes` as today, and a human's in-session
  merge authorization still waives it there. Errors: branch protection or a repository rule that
  requires reviews on the integration branch still holds (land already honors stricter rules), so
  such a child stops `AWAITING_REVIEW` as today. [inferred]
- **R4:** The user-facing goal-mode documentation describes the final review's skip without a
  backend and the patience rule for child versus final pull requests; behavior and docs agree.
  No error surface. [inferred]

## Boundaries

- The goal-mode redesign (integration branch always, rigor set per goal in the goal spec, fewer
  procedural rules, children driven in parallel) is the next spec, not this one. [paraphrase]
- No new configuration key, flag or template section. [inferred]
- Per-child review behavior, and land's patience for pull requests outside goal runs, stay as
  they are. [inferred]

## Decision Context

The person set the order: the three bugs first, as one simple spec, then the redesign as its own
spec. [paraphrase] A missing backend is already a recorded skip everywhere else in the pipeline,
so the final review following the same rule removes an inconsistency rather than lowering a
gate. [inferred] Child pull requests into the integration branch never reach the default branch
on their own; the final pull request does, so that is where the bot window belongs. [inferred]
