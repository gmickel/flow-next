# Goal mode: integration branch always, rigor set by the goal

## Goal & Context

"we're 'hard coding' too much stuff into it" — goal mode fixes the shape of the work: every
child is driven like a standalone unattended spec through the whole hop loop, one child at a
time, PR-sized, with repo-wide gates, and the goal itself has no way to say how strict to be.

"i think we defintely always want an integration branch, i just think it should be up to the
user/prd or type of goal whether we force constraints etc, maybe the person wants to use --goal to
iterate on a prototype and doesn't want massive ci checks all the time"

"remember the bitter lesson": state the outcome and the contract, and let the model plan the
work, instead of a procedure that plans it for the model. [paraphrase]

The 2026-10-28 study (agent-evals `studies/goal-parallel-children-2026-10/`) showed the cost of
procedure twice: harness-scheduled parallel children lost to serial on the PRD case, and a single
sentence licensing parallel subagents inside the serial procedure was never used. [inferred]

## Acceptance Criteria

- **R1:** Children always land on the goal's integration branch, and the default branch is reached
  only through the one final pull request, which always runs the repository's CI. The option to
  land children directly on the default branch is removed. Errors: a goal whose log already
  recorded direct landing finishes under its log; a branch named for the goal that does not
  record it as this goal's still stops for a person, as today. [inferred]
- **R2:** How strict the path to the integration branch is (a pull request per child or commits
  straight onto the integration branch, per-child review, the final review, QA, waits on CI and
  review bots) is set in plain words in the goal spec, the way a goal spec already states where
  children land; with nothing said, the repository's configuration applies as it does today. The
  run records in the goal log which rigor it applied and the words it came from. No new
  configuration key, flag or template section. Errors: words that conflict with the goal's
  Boundaries or a repository rule (branch protection, required checks) follow the stricter one
  and log the conflict. [inferred]
- **R3:** Goal-mode instructions keep the contract and the few facts the model cannot infer, and
  drop the procedure. Contract: the run never changes the goal's criteria, Boundaries or budget; a
  criterion counts as met only on an observed result tied to a commit; questions go into the goal
  spec and are never asked interactively; landing consent comes only from the current
  invocation; no force-push or rebase of shared branches; the goal log is the memory between
  sessions; one verdict line. The model decides how to split the goal, how large each child is,
  in what order, whether children run in parallel, and when to measure. No error surface beyond
  the contract's stops. [inferred]
- **R4:** Whether each child is still driven through the full unattended hop loop or by the goal
  run directly is decided by R5's evidence; either way the unattended guards hold (clean tree,
  current consent, no merge steps outside land, stop on a stage's request for a person). No error
  surface beyond those guards. [inferred]
- **R5:** "prove that goals still work as well as they do now for people that do have more gated
  use cases". On pre-registered fixtures (at least the study's PRD and port cases) under gated
  configuration (a review backend set, a pull request per child), the redesigned goal mode
  reaches its goal at least as often as 9.3.x, with hidden-check quality no lower and wall time
  and cost within pre-registered margins. A goal that asks for light rigor in its spec applies
  fewer gates, and still never reaches the default branch except through the final pull request.
  Errors: a regression on any guard blocks shipping and is recorded with the evidence. [inferred]
- **R6:** "the 2nd thing is if parallisation would work". The same evaluation reports whether
  runs worked children concurrently and how wall time compared with serial on both cases; the
  instructions license parallel children only when a pre-registered gain is met. A zero-gain
  result is recorded, and the redesign ships without the licence. [inferred]

## Boundaries

- The three goal-mode bugs (final review without a backend, `--review` reach, child-PR patience)
  are fixed first, in their own spec. [paraphrase]
- No orchestration outside the session: no harness coordinator, scheduler or driver per child.
  [inferred]
- The gates of the stage skills themselves (work, review, QA, make-pr, land) are unchanged except
  where goal mode's per-goal rigor needs a way to ask for less. [inferred]

## Decision Context

The integration branch is what makes light rigor safe: children only ever reach the integration
branch, and the default branch is reached through one final pull request with the repository's
CI, so a prototype goal can drop per-child gates without putting the default branch at risk.
[inferred] Rigor lives in the goal spec's own words rather than configuration, following the
repository's agent-first rule; the existing landing line in a goal spec is the precedent.
[inferred] The study's arms B (harness coordinator plus scheduling rules) and C (one licence
sentence inside the serial procedure) are the rejected designs. [inferred] The person's guess for
R5 is "yes as it's fully decidable in the goal spec"; the evaluation is what confirms it.

## Strategy Alignment

- Autonomous mode: goal mode is the long-horizon unattended path; this narrows what the
  instructions decide on the model's behalf. [strategy:Autonomous mode]
