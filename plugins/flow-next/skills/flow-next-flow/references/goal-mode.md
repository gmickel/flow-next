# Goal mode (gated reference)

> Read from auto.md only when the run parsed `--goal`. It replaces auto.md's phases for this run;
> auto.md's argument parse, verdict contract and Forbidden list still hold, except that a goal run
> may invoke more than one stage before its verdict.

A goal is an ordinary spec: its acceptance criteria are the bar, its Boundaries hold what no child
may change, and its Goal & Context states the outcome or links whatever describes it. The person
who runs `--goal` names it, and that invocation is the consent for the whole goal, so the goal spec
stays unready (a goal marked ready is unreadied with `$FLOWCTL spec unready <goal-id> --json`, and
the log says so). The run reaches the bar through child specs it mints and builds, and stops when
the bar is met or a person is needed.

## The contract

- Never change the goal's criteria, Boundaries or budget, never edit a section of the goal spec
  other than its `## Goal log`, and never edit a spec this goal did not mint.
- A criterion counts as met only on an observed result (a command's output, a test, a benchmark, a
  merged child's receipts) recorded with the integration-branch commit it ran on. A criterion only
  a person can judge counts only on the answer they wrote in the goal spec, quoted with its date.
  Measure before claiming the bar is met.
- Never ask interactively. A question goes into the log once: what is asked, the options with their
  measured cost, a recommendation, and the criterion it blocks. It parks only that criterion. The
  person answers by editing the goal spec; the next run quotes the answer with its date and treats
  it as settled.
- Landing consent comes only from the current invocation (`--until=merge`); the log never records
  or restores it. Without it the run ends `DEFERRED_TO_LAND` at the first pull request that needs
  landing.
- Start on a clean tree: run auto.md's snapshot fence with `PILOT_SPEC` empty and apply its guards,
  setting `GOAL_REASON_PREFIX="goal <the goal id, or the source until it resolves>; "` and, once the
  goal is known, `GOAL_SPEC=<goal-id>` on the command line of every auto.md fence the run runs.
- Build with the stage skills under `mode:autonomous` (capture, plan, plan-review, work, qa,
  make-pr, land, impl-review), passing the invocation's `--review=<backend>` to those that take it;
  never copy their steps. A stage's `NEEDS_HUMAN` or `ESCALATE:` ends the run with its reason. Merge
  a pull request only through land, never reopen or replace a closed one, never write planning
  state onto a branch with an open one, and never force-push or rebase a shared branch.
- The `## Goal log` at the end of the goal spec is the run's only memory between sessions: dated
  one-line entries in plain prose, written after acting. Write it with
  `$FLOWCTL spec set-plan <goal-id> --file <path> --json`, every other section byte for byte.

## Resolve the goal

`PILOT_GOAL` empty stops `NEEDS_HUMAN`, reason `--goal needs a spec id or a source`. After
`git fetch`, the goal is the spec `PILOT_GOAL` names, in the checkout or on an `origin/goal/<b>`
branch whose `.flow/specs/<id>.md` has `branch_name` `<b>`; for a source (a path, a URL, a tracker
issue, pasted text) it is the open spec whose log's first entry names that source. With none,
capture it with `flow-next:flow-next-capture from:goal <source>` and log
`goal captured from <source>`; a refusal stops `NEEDS_HUMAN` with capture's reason. A closed goal
stops `NEEDS_HUMAN`. Read the whole goal spec every run: criteria, Boundaries, Decision Context,
answers the person wrote, and the log.

## The integration branch

Children land on `goal/<the goal spec's branch_name>`. The default branch sees the goal only
through one final pull request, which runs the repository's CI.

- Create it once: in a scratch worktree at `origin/<default>`, commit the goal spec's two files
  with a log entry naming the branch and the default-branch commit, and push it as
  `refs/heads/goal/<branch_name>`. A branch of that name whose copy of the goal spec does not record
  it as this goal's stops `NEEDS_HUMAN`. A goal whose log already records children landing on the
  default branch finishes that way, ending `GOAL_MET` once every criterion is met.
- The log and the children's specs live on this branch: commit log entries there, and when
  `origin/goal/<branch_name>` holds newer copies than the checkout, read them from it (`git show`).
- Keep it current by merging the default branch's remote head into it (`git merge`, never a
  rebase). A conflict the run cannot resolve inside the Boundaries is aborted and logged as a
  question.
- Measure on its pushed head, in a scratch worktree that leaves the run's checkout untouched.
- CI often runs only on pull requests into the default branch. When the rigor waits on CI for a
  child's pull request and it shows no checks a minute after opening, while pull requests into the
  default branch have them, it is not green: stop `NEEDS_HUMAN` so the person adds `goal/**` to the
  trigger.
- Land squash-merges: compare heads by identity, never by ancestry.

## How strict

The goal spec sets, in plain words, how strict a child's path to the integration branch is: a pull
request per child or commits straight onto the integration branch, review per child, the final
review, QA, waits on CI and review bots. Where it says nothing, the repository's configuration
applies: each child goes through work with `--base=goal/<branch_name>`, make-pr with
`--base goal/<branch_name>` and land, named to land as this goal's child into its integration
branch so it waits for no review bots ([tail.md](tail.md)); review follows `review.backend` and the
working rules' risk rule, QA follows `pipeline.qa`, and the whole diff gets a final review. A goal
that asks for less gets less: a prototype's children may be committed straight onto the integration
branch once their tests pass, each closed with `$FLOWCTL spec close <child-id> --json`. Words that
conflict with the Boundaries or a repository rule (branch protection, required checks) follow the
stricter one, and the conflict is logged. The first run logs the rigor it applied and the words it
came from; later runs follow the log unless the goal spec changed.

## Your call

How to split the goal into children, how large each one is, in what order, whether to work several
at once (your own subagents, each in its own worktree), and when to measure. Settle a route's
premise with a scratch probe first when that is cheap ([prototype-before-ask.md](prototype-before-ask.md));
a premise no probe settles, or a product choice, is a question.

Mint a child with `flow-next:flow-next-capture from:goal <goal-id>` after stating in the session
the gap it serves (the criterion, its last result, the route, the premise), then
`$FLOWCTL spec add-dep <goal-id> <child-id> --json` and `$FLOWCTL spec ready <child-id> --json`,
and log the mint. A child is never itself a goal. When capture names an open, ready spec that
covers the gap, adopt it (logged; this run never retires it). A child this goal minted that never
merged, whose premise a probe falsified or that another child covers, may be retired with
`$FLOWCTL spec close <child-id> --retire superseded --by <id> --json` (or `--retire moot`), logged.
A discovery off a child's path is that child's follow-up; mint for it only when it serves a
criterion.

## Stop and finish

- Stop `NEEDS_HUMAN`, with the log as the evidence, when a budget or stop date the goal states is
  reached, when the last two merged children each moved no criterion, or when every unmet criterion
  waits on a question.
- A final pull request the log records comes first on a later run: open, land it under current
  consent or defer again; merged, end `GOAL_MET`, the merged pull request being the record; closed
  unmerged, `NEEDS_HUMAN`.
- Every criterion met: resolve the final review's backend first (the invocation's
  `--review=<backend>`, else `$FLOWCTL review-backend <goal-id>`). `none` or `ASK`, or a goal that
  asked for no final review, skips it with the outcome `skipped(config: review=none)`,
  `skipped(config: no review backend)` or `skipped(goal: <its words>)`. Otherwise run
  `flow-next:flow-next-impl-review --base <the integration branch's merge-base with the default
  branch> mode:autonomous` over the whole diff under the unattended review loop, pushing its fixes
  to the integration branch. Commit the log entry (criteria met, commit, review outcome), open one
  pull request from the integration branch to the default branch with `gh pr create` (`--draft`
  when the review left an `OPEN_ITEM:`), titled with the goal, with the log and the review outcome
  as its body, commit its URL to the log, and hand it to land as [tail.md](tail.md) says, bound by
  that URL (head `goal/<branch_name>`, base the default branch, the goal as its scoped spec).
  Without landing authority the run ends `DEFERRED_TO_LAND`. The review and opening report stage
  `make-pr`, landing it `land`. The goal stays open for the person to accept and close.

## Verdicts, `--tick` and `--explain`

```text
PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN|GOAL_MET> spec=<id> stage=<stage> reason="goal <goal-id>; <one line>"
```

`spec=` names the child the run worked on last, or the goal when no child was built. A goal capture
or a mint is stage `capture`; a measurement alone is stage `-`. A driver re-invokes on `ADVANCED`,
treats `DEFERRED_TO_LAND` as it does today (land the pull request, or wait for its merge), and
stops on `GOAL_MET`, `NEEDS_HUMAN` and `BLOCKED`.

- `--tick`: one goal action, then the verdict: a goal capture, a measurement and its log entry, a
  mint, one stage of one child, the final review with its pull request, or its landing.
- `--explain`: print the next goal action and stop. Nothing is captured, measured or logged. The
  verdict is `NO_WORK`, as for any explain run.

One goal run per goal at a time: two concurrent runs can mint for the same gap.
