# /flow-next:flow workflow - the hop loop

Mode, `FLOW_UNTIL`, `EXPLAIN` and `REVIEW_OVERRIDE` come from SKILL.md, and so does `$FLOWCTL`.

If `.flow/` does not exist, print `No .flow/ directory - run \`$FLOWCTL init\` first.` and stop.

## Step 1: Read the starting point

Read what was given and decide what it is: a spec or task id (`$FLOWCTL show <id> --json`,
`$FLOWCTL cat <id>`), a tracker issue (through the access this session already has), a branch
(`git log` and the spec whose `branch_name` matches), a path, a pasted bug report, a sentence of
intent. With no argument, read [references/no-argument.md](references/no-argument.md).

## Step 2: Route

Read [references/route-matrix.md](references/route-matrix.md). Routing and the QA gate never
ask the judge, so a run with a TypeSafe key and one without take the same route.

Then route once per hop (in auto mode, use the route `pilot snapshot` returned instead). A spec
gets the route call, which decides its lifecycle in code and never asks the judge:

```bash
"$FLOWCTL" judge --preset route --spec <spec-id> --json | jq -c '{available, reason, pr_probe_failed, decision}'
```

For a spec, code applies lifecycle order: an observed PR goes to landing, a closed spec without a
PR to you, all tasks done to QA and make-pr, a `stale` plan review to plan-review, tasks to the
recorded work route, a ready zero-task spec to direct or plan. When `decision.met` is true, use `decision.value`, unless the person asked to be interviewed on the spec: that routes to refine (`references/plan-vs-no-plan.md`). Intake without a spec
is yours: decide from the matrix. Print one line per hop: `Route: <route> (code)` or
`Route: <route> (host)`.

`EXPLAIN=1`: resolve the route (reading the references below as needed) but record nothing, then
read [references/explain.md](references/explain.md) and stop there.

A ready spec with no tasks and no recorded route: read
[references/plan-vs-no-plan.md](references/plan-vs-no-plan.md), resolve the rule, and record it
before any stage runs (`$FLOWCTL spec set-no-plan <id> --json` for direct,
`$FLOWCTL spec clear-no-plan <id> --json` for a positive plan signal). All tasks done and no PR:
read [references/gate-selection.md](references/gate-selection.md) for QA, then make-pr. An
existing PR: read [references/tail.md](references/tail.md). Uncaptured intent whose criteria trip
the tripwire: read [references/spec-count.md](references/spec-count.md). Two routes that would
materially differ with an answer you cannot observe: read
[references/prototype-before-ask.md](references/prototype-before-ask.md) before asking, and ask at
most one question per hop.

## Step 3: Run the routed stage

Invoke the stage skill by name with its normal arguments, passing `--review=<backend>` through when
`REVIEW_OVERRIDE` is set. Never copy a stage's steps inline.

- **Capture** gets the exact token `from:flow`; it applies plan-vs-no-plan itself and offers the
  saved spec for review. A request to capture or review only never authorizes work.
- **Defect reproduction**, when the report does not say where the problem is and `.flow/features/`
  exists: read [references/defect-intake.md](references/defect-intake.md) first.
- **Work** runs `flow-next:flow-next-work <spec-id>`; a recorded `no_plan` pre-answers its fork.
  Pick the branch rather than letting work ask: `--branch=current` on a branch other than the
  default, else `--branch=new`, unless the user named one. State the choice in one line.
- **QA** follows gate-selection.md; a skip is recorded, never silent.
- **Make-pr** runs under `--auto`, or attended when the person asks for the PR (working-rules.md);
  it ends a run from intent unless `--until=merge` or current explicit consent authorizes landing
  (tail.md). A PR this run just opened gets no landing question.

A stage that stops with `NEEDS_HUMAN`, a verdict that needs a person, or an open product question
stops flow with the same report; never answer on the user's behalf.

## Step 4: Re-evaluate

Re-read state (`$FLOWCTL show <spec-id> --json`, the PR, the receipts) and return to Step 2.
Advance on observed state, never on a stage's narration.

## Step 5: Stop and report

A pick among options a stage produced (prospect's candidates, chart's capture-or-split, refine's
choices) is asked inline, one per hop, and the run continues. Otherwise stop at the first of: the PR
exists (without landing authority), a decision a stage handed to the person, or a blocking question
that is not a pick. A PR this run just opened, without landing authority, ends the run; read
tail.md at a PR boundary only otherwise. Print the report shape from SKILL.md: one
`stage:` line per stage reached (a skipped stage with its reason), inline picks on the `Route taken`
line, then `Next:` in the host's command form.
