# Goal mode (gated reference)

> Read from auto.md only when the run parsed `--goal`. A run without it never reads this file.
> auto.md's guards, stages, strikes, branch rules and verdict contract hold here unchanged;
> this file adds only what goal mode changes.

A goal is an ordinary spec whose acceptance criteria are the bar, whose Boundaries hold what no
child may change, and whose Goal & Context states the outcome or links whatever describes it. The
person who runs `--goal` names it, and that is the consent for the whole goal: the goal spec
itself stays unready, so no plain `--auto` run builds it as one spec. Each run measures against
the bar, builds the next child spec through auto.md's hop loop, and repeats until the bar is met
or a person is needed. The goal spec's `## Goal log` is the run's memory across sessions; nothing
is resumed from a transcript.

## What a goal run may do beyond auto.md

- Capture the goal from the source it was handed, and mint children, through
  `$flow-next-capture from:goal <goal-id or source>`.
- Add each child as a dependency of the goal, and mark ready a child it just minted.
- Retire a child it minted that never merged, with the reason in the log.
- Write the goal spec's `## Goal log` section.

Nothing else. It never edits another section of the goal spec, never edits a spec it did not
mint, and never changes the goal's criteria, Boundaries or budget once the goal spec exists,
including a goal spec it captured. Refine, chart and prospect stay outside every unattended run.

## Step 1: guard, then resolve the goal

1. Run auto.md's snapshot fence with `PILOT_SPEC` empty and apply its guards; a dirty tree stops
   `NEEDS_HUMAN` before any write.
2. `PILOT_GOAL` empty: stop `NEEDS_HUMAN`, reason `--goal needs a spec id or a source`.
3. `$FLOWCTL show "$PILOT_GOAL" --json` resolves: that spec is the goal. A closed goal stops
   `NEEDS_HUMAN`.
4. Otherwise `PILOT_GOAL` is a source (a path, a URL, a tracker issue, pasted text). An open spec
   whose goal log's first entry names this same source is the goal; this keeps a re-sent
   invocation on the goal it already started. With none, capture it:
   `$flow-next-capture from:goal <source>`. A refusal (no checkable outcome, a duplicate)
   stops `NEEDS_HUMAN` with capture's reason and nothing written. On success write the first log
   entry: the date and `goal captured from <source>`.
5. A goal marked ready is unreadied (`$FLOWCTL spec unready <goal-id> --json`) and the log says so.
6. Read the whole goal spec (`$FLOWCTL cat <goal-id>`) every run: criteria, Boundaries, Decision
   Context, answers the person wrote, and the log.

## Step 2: drive an open child

The children are the goal's dependencies the log records as minted for it. An open one (not
closed, or closed with its PR not yet merged) is this run's item: set `PILOT_SPEC` to it, rerun
auto.md's snapshot fence for it, and continue at auto.md's Phase 2. It must pass `eligible` like
any named scope, and every stage, gate, strike and guard is auto.md's. One child is open at a
time; after a crash that left two, drive the older first.

A child's PR without landing authority, a deferral to land, a strike, or `NEEDS_HUMAN` ends the
goal run with that outcome, logged. A confirmed merge returns to Step 3.

## Step 3: measure

Measure on the default branch's current remote head, in a scratch worktree that never touches the
run's checkout: fetch, `git worktree add --detach .flow/tmp/goal-measure origin/<default>`, run
each criterion's check there, then remove the worktree. A criterion counts as met only on an
observed result: a command's output, a test, a benchmark, or a merged child's receipts, recorded
with the commit it ran on. A criterion only a person can judge counts only on the answer they
wrote in the spec, quoted with its date; without one it is an open question (Step 6), never a
pass. Log one dated measurement entry: each criterion, its result, the commit.

## Step 4: decide

- Every criterion met: log it and end `GOAL_MET`. The goal stays open for the person to accept
  and close.
- Stop `NEEDS_HUMAN`, with the log as the evidence, when a budget or stop date the goal spec
  states is reached, when the last two merged children each moved no criterion, or when every
  unmet criterion waits on an open question.
- Otherwise mint the next child (Step 5).

## Step 5: mint the next child

Pick the unmet criterion whose gap does most for the bar next, among those not waiting on a
question. State the gap in the session: the criterion, its last result, the route, and the
premise the route rests on. When the premise is cheap to check, settle it first with a probe
under [prototype-before-ask.md](prototype-before-ask.md) (scratch only, nothing staged), and state
the result. A premise no probe settles, or a route that is a product choice, is an open question
instead.

Then invoke `$flow-next-capture from:goal <goal-id>`. Size the child for one pull request;
a child is never itself a goal and never mints. When capture refuses (it would ask, it would
cross a Boundary or reopen a settled decision, the gap is too large), record an open question;
when it names an open spec that already covers the gap, take that spec as the child if it is
ready, otherwise record a question. On success:

```bash
"$FLOWCTL" spec add-dep <goal-id> <child-id> --json
"$FLOWCTL" spec ready <child-id> --json
```

Log the mint (child, criterion, why it was next), then drive it (Step 2). The child is routed
exactly as a spec a person wrote: plan or no-plan, plan review, QA and every other gate follow
their own rules.

A child this goal minted that never merged, whose premise a probe falsified or that another
child covers, may be retired:
`$FLOWCTL spec close <child-id> --retire superseded --by <id> --json` (or `--retire moot`),
with the reason logged.

## Step 6: open questions

Log each question once: what is asked, the options with their measured cost, a recommendation,
and the criterion it blocks. Never ask interactively. The person answers by editing the goal
spec; the next run quotes the answer with its date in the log and treats it as settled. A
question parks only its criterion: keep working on the others.

## The goal log

A `## Goal log` section at the end of the goal spec, created by the first entry: dated one-line
entries in plain prose, written after acting, never before. Write it with
`$FLOWCTL spec set-plan <goal-id> --file <path> --json`, every other section unchanged byte for
byte. The edits are `.flow` bookkeeping: they ride onto the next child's branch with its spec
files, and the dirty guard ignores them. The log never records or restores landing consent;
`--until=merge` holds only for the invocation it was passed to.

Each child runs under the working rules like any other change: a discovery off its path is that
child's follow-up, and this run may later mint for it only when it serves a criterion.

## Verdicts, `--tick` and `--explain`

```text
PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN|GOAL_MET> spec=<id> stage=<stage> reason="goal <goal-id>; <one line>"
```

`spec=` names the child the run worked on, or the goal when no child was dispatched. A goal
capture or a mint is stage `capture`; a measurement alone is stage `-`. A driver re-invokes on
`ADVANCED`, treats `DEFERRED_TO_LAND` as it does today (land the child's PR, or wait for its
merge), and stops on `GOAL_MET`, `NEEDS_HUMAN` and `BLOCKED`.

- `--tick`: one goal action, then the verdict: a goal capture, a measurement and its log entry, a
  mint, or one child hop.
- `--explain`: print the next goal action (capture the goal, measure, mint for a named gap, or
  drive a named child with its route) and stop. Nothing is captured, measured or logged.

One goal run per goal at a time: two concurrent runs can mint for the same gap.
