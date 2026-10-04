# Work: several tasks, or a worker

Read from phases.md Phase 3 when this run implements more than one task, or when a single task
goes to a worker. Phases 1-2 are done; Phases 4-5 in [phases.md](../phases.md) follow this file.

## Phase 3: Task Scheduling (several tasks)

**Route decision (once, at Phase 3 entry).** Two schedulers exist; the rolling
frontier is the default and the wave loop below is its structural fallback.
Decide from spec state plus the plan-sync setting - never from a config knob,
a host name, or a Touches comparison (Touches are judged per admission inside
whichever scheduler runs):

```bash
$FLOWCTL config get planSync.enabled --json
$FLOWCTL tasks --spec <spec-id> --json   # SPEC_MODE: open tasks + depends_on
```

Take the **wave route** (3a-3g below) when ANY of these hold:

1. SINGLE_TASK_MODE - the run was given a task id, so the wave route runs
   exactly the requested task alone; the spec's other open tasks are never
   admitted (rolling admits from the whole ready frontier, which is the wrong
   scope for a task-id run);
2. `planSync.enabled` is not explicitly `false` (plan-sync's per-wave barrier
   is the existing fail-closed rule; `false` is the shipped default since
   4.5.1, so this fires only on repos that opted in);
3. SPEC_MODE with fewer than two open tasks - a no-plan implicit task, or one
   task left (a single lane has nothing to admit);
4. SPEC_MODE where no two open tasks are dependency-independent under the
   transitive `depends_on` closure (a fully sequential chain admits one lane
   at a time, and the single-worker path runs one lane with less machinery
   than a worktree plus a conductor integration per task).

Otherwise take the **rolling route**: read
[references/rolling-scheduler.md](rolling-scheduler.md) and execute
it as this run's Phase 3 (it re-enters 3b.1, 3c, 3d.1, 3e's stage-line
contract, and 3g by pointer). Do not execute 3a-3g directly on that route.

Echo the decision exactly once in the run report, before the first claim:

```text
Scheduling: rolling
Scheduling: degraded to wave (host lacks non-blocking dispatch)
Scheduling: wave (<task-id run | planSync.enabled=true | single task | sequential dependency chain>)
```

The wave route prints its line here, at Phase 3 entry. The rolling route
prints its line from inside the scheduler at run setup, after its
dispatch-behaviour probe (rolling-scheduler.md 3.0) and before the first
admission or claim - so a host measured to block prints the `degraded` form
instead of `rolling`, never both. A run that
printed no `Scheduling:` line, printed two, or took the rolling route with
plan-sync on, has broken this.

**Wave route.** In SPEC_MODE, inspect the whole ready frontier and prefer a
concurrent safe subset. In SINGLE_TASK_MODE, the selected wave is always the
requested task alone. Every task gets a fresh-context worker.

### 3a. Inspect Ready Frontier and Select a Wave

```bash
$FLOWCTL ready --spec <spec-id> --json
```

For a direct owner admitted for resume in Phase 1, re-read its task status and
claim. While it remains `in_progress` under this actor, select that owner alone
instead of the ready list; re-anchor and continue through the usual claim and
worker gates, where 3b's claim carries `--reclaim` for this owner only. Stop on a
changed owner. Once the task is `done`, discard the resume
selection. Retain the original mode: `SINGLE_TASK_MODE` executes no other task and
proceeds to Phase 4; `SPEC_MODE` uses the normal frontier, including the 3f loop
and 3g completion-review policy when the frontier is empty.
For every non-resume selection, an empty ready frontier proceeds to 3g as usual.

In SPEC_MODE, consider every returned task and apply the **wave dispatch rule
(fail-closed)**. **Concurrent dispatch requires all five conditions
together; any one unmet sends the wave serial.** A wave dispatched with a missing
or overlapping `**Touches:**` declaration has broken this.

1. same spec;
2. wave size ≤ 3;
3. no dependency path between any pair, in either direction, **transitively**
   (walk the `depends_on` closure from `$FLOWCTL show <task-id> --json` /
   `$FLOWCTL tasks --spec <spec-id> --json` — `flowctl dep` only writes edges,
   it has no read verb; a direct-only check is wrong);
4. every dispatched task carries a `**Touches:**` declaration, and the declared
   sets are pairwise **disjoint** (`touches(A) ∩ touches(B) = ∅`, glob-aware);
5. no task touches the always-serial set: `.flow/`, lockfiles, migration
   dirs, codegen/generated outputs,
   or spec/task files.

The error paths are the rule: a task with no `**Touches:**` declaration →
serial; any intersection → serial; any doubt about a glob, a hidden coupling
(shared fixtures, services), or host capacity → serial. The failure mode is
today's behavior — sequential dispatch — never a risky wave. This replaces
judgment with declared intent: the same trust model as `deps` (its
decision record untouched; no semantic prediction anywhere). Safety is
structural, not the check — workers run in isolated worktrees, so a wrong
dispatch surfaces at the join as a merge conflict (3d), costing one serial
retry, never correctness. Never run concurrent writers in one checkout. An
explicit request to parallelize strengthens the preference but never
overrides the rule.

Report the decision before claiming:

```text
Ready frontier: [fn-X.1, fn-X.2]
Selected wave: [fn-X.1, fn-X.2]
Selection rule: <why THIS subset of the frontier — the dispatch-rule condition or preference that picked it>
Isolation: <native worktrees | linked worktrees | other safe mechanism>
Dispatch count: 2
Sequential fallback: <reason> # only when multiple tasks were ready but one selected
```

The `Selection rule:` line is printed before claiming — an unstated selection
is unreviewable, and a wrong wave discovered at the join can no longer say why
it was picked.

Done when: the five report lines are printed (plus `Sequential fallback:` when one applies) and the selected wave satisfies all five conditions above.

### 3b. Claim the Selected Wave

Claim every selected task before dispatch:

```bash
$FLOWCTL start <task-id> --json
```

For the direct owner admitted for resume in Phase 1 (and only for it), the
claim is `$FLOWCTL start <owner-id> --reclaim --json`: a plain start refuses an
`in_progress` task held by this same actor, and the Phase 1 evidence check is
what licenses the flag. Every other claim runs without `--reclaim`; a same-actor
contention refusal there means another run of this actor is live on the task -
fail closed exactly as for a foreign claim, never add the flag to get past it.

If any claim fails, do not dispatch that task. Retain every successfully
claimed task in the selected wave and recompute only the failed/unclaimed
membership from ground truth; never abandon a task that this conductor already
moved to `in_progress`. A successful atomic claim prevents duplicate ownership;
it does not make shared-checkout Git or filesystem mutations safe.

Done when: every task in the selected wave reads `in_progress` under this actor, and any task whose claim failed has been dropped from the wave rather than dispatched.

Before the run's first tracker gate, snapshot once to a run-unique file under `.flow/tmp/` with `$FLOWCTL sync active --json > <run-sync-active.json>`. Retain the path for every touchpoint below; its `ops` map already resolves per-event operations. If the probe fails, leave no usable snapshot and retain the existing fail-open read/dispatch behavior. Do not re-probe configuration at each task return.

#### 3b.1 Tracker sync (opt-in) — first claim → In-Progress

**Optional. Runs only when the tracker bridge is active AND `work.firstClaim` is opted in. With no tracker configured this is a no-op — the work flow is unchanged.**

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$(cat <run-sync-active.json> 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — read and execute references/tracker-touchpoints.md#first-claim, then continue with Phase 3c."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/tracker-touchpoints.md](tracker-touchpoints.md), execute its `First claim` section (`work.firstClaim` leaf check + best-effort dispatch), then continue with Phase 3c. When the gate is silent (bridge inactive), continue — nothing fires here.

### 3c. Run Worker Agent(s)

Implementation is the **implementer** tier: absent any preference, the worker runs on the session model. **Routing precedence, highest first: an explicit argument in the invocation, then the project routing block in the instruction file, then the agent definition's own default, then the session model.** How this harness reaches a non-session model — and what the degradation is when it cannot — lives in its reach page (`plugins/flow-next/docs/reach/`), never here.

Before spawning, apply [judge-tier.md](judge-tier.md) once for this task. Use its selected model in the host spawn-model parameter as well as the `IMPLEMENTER:` line; an explicit invocation always wins.

**When the implementer tier resolves to a model this harness reaches only over a CLI bridge, the worker bridges and the conductor never does.** The dispatch below is unchanged: the worker resolves the tier itself (worker Phase 1b), hands the task to the bridged child with the usage guide's brief, and reviews the child's commit range before its own review dispatch. The bridged child owns the task and its own delegation; a conductor that composed a brief, ran a bridge call, or fanned out on the implementer's behalf has broken this.

Use the **worker** agent role to implement each selected task. For a multi-task
wave, create one isolated mutable workspace and task-unique summary/evidence
paths per worker, then dispatch the selected workers concurrently. For a
one-task wave, use the existing single-worker path. On every route, choose and pass absolute, task-unique `HANDOVER_SUMMARY` and `HANDOVER_EVIDENCE` paths before dispatch; create their parent directory.

**Commit the spec and task files BEFORE creating the workspaces.** A wave
workspace is branched from a commit, so anything still uncommitted in the
conductor's checkout does not exist inside it — and a freshly planned spec is
uncommitted by default. A worker dispatched into such a workspace cannot
re-anchor at all: `$FLOWCTL show <task-id>` finds no task there, and the failure
looks like a broken worker rather than a missing commit. Commit `.flow/` first
(`git add -- .flow/`), then create the workspaces from that commit. Single-worker runs are unaffected — they share
the conductor's checkout.

The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status, task-relevant glossary terms when populated)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

The last two responsibilities apply only to the existing single-worker path. A
parallel-wave worker defers review and all shared lifecycle work to the
conductor after integration.

**`REVIEW_MODE` is per-task, not a fixed run-wide value.** Resolve it for THIS task: if the user
passed an explicit `--review=<backend>` to `/flow-next:work`, use that (a deliberate run-wide override
wins for every task); OTHERWISE resolve task-aware — `REVIEW_MODE=$($FLOWCTL review-backend "$TASK_ID")`
— so a task's own `review:` override (e.g. `review: cursor:...` under a `codex` project default) selects
its backend rather than the project default. `none` still skips review.

**Invoke the worker:**

"Use the worker agent to implement this task:

TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: $FLOWCTL
REVIEW_MODE: none|codex|copilot|cursor|claude|host|host-deferred
PARALLEL_WAVE: true|false
WORKSPACE: <isolated mutable workspace>
HANDOVER_SUMMARY: <task-unique summary path>
HANDOVER_EVIDENCE: <task-unique evidence path>
BASELINE_HANDOFF: green (verified at <sha8> by <task-id>)
IMPLEMENTER: <model> at <effort>
TIER_LINE: <dispatch Tier: line>
FORBIDDEN: implementation edits outside this task's declared Touches (worker lifecycle writes are exempt: .flow/tmp/, the handover paths above, the receipt flowctl done writes); no force-push; no rebase of the target
TIMEBOX: <cap> - on expiry write the handover with partial findings and return, never run on

Follow your phases exactly."

`FORBIDDEN` echoes the task's declared write surface into the dispatch — an
out-of-scope edit is the collision class the Touches-disjointness rule exists
to prevent, and force-pushes/rebases of the target rewrite history peers have
already built on. The ban covers implementation edits only: the lifecycle
artifacts worker.md itself requires (the persisted base file, the handover
summary/evidence, the `flowctl done` receipt) stay writable. `TIMEBOX` is the return-partial contract: expiry means the
worker writes its handover with whatever it has and returns — a partial
handover is diagnosable; a lane that runs on past its cap is not. The
conductor sets `<cap>` at dispatch — its own judgment from the task's declared
scope and Quick commands; no config key stores it. The contract is
cooperative, not host-enforced: on a host where the dispatch blocks, the
conductor cannot act mid-flight, so the cap is applied at its next control
point — the worker's return, the host's own tool timeout or error, or a lost
result — where 3d's side-effects rule classifies whatever the lane left
behind.

`IMPLEMENTER` carries an explicit invocation model first; otherwise it may carry the confident mechanical tier's reachable fast-scout model from `references/judge-tier.md`. Omit it when neither applies. Pass the native model through the spawn-model parameter too. The conductor never bridges or composes the worker's brief.

`BASELINE_HANDOFF` is optional. The conductor MAY pass it only when ALL hold: the prior task in this run reached done with its Phase 5 Verify green over the SAME Quick commands, HEAD has not moved since except by commits changing only `.flow/` paths, and the new task's declared Touches do not intersect files changed since that verification. Conductor judgment on stated facts; when in doubt, omit the line. On the wave route the first task receives no handoff. The rolling route instead runs a green spec-base baseline before its first admission and may hand that baseline to the first batch under the same `.flow/`-only rule. Check every intervening commit with `git log --format= --name-only <verified-sha>..HEAD`; any non-`.flow/` path invalidates the handoff, including changes later reverted.

Set `PARALLEL_WAVE: true` only for a concurrently dispatched multi-task wave.
Those workers implement, test, commit, and return their workspace, commits, and
the exact handover paths. They do **not** call `flowctl done`, project tracker
state, invoke plan-sync, run impl-review, or integrate their own commit. This
host-deferred shape is independent of `REVIEW_MODE`; the conductor preserves
the resolved backend and applies it after integration. The prompt fields are an
internal handoff, not a public CLI or stored schema.

**Host review routes OUTSIDE the worker — and gates BEFORE done.** On the wave route's single-worker path only, when the resolved review mode is \`host\`, pass \`REVIEW_MODE: host-deferred\`: the worker skips review dispatch AND defers \`flowctl done\` (returns with the task still in_progress + summary/evidence files written). The conductor then runs \`$flow-next-impl-review <task-id> --review=host\` as the mandatory gate and only on SHIP runs \`flowctl done\` with the worker-prepared summary/evidence plus the review receipt; terminal NEEDS_WORK escalates after impl-review's internal bounded fix loop; never re-invoke it. Read references/host-deferred-review.md for the task-base and memory auto-capture gates.

**Worker returns** (both paths): task id, terminal status, commit range, `actual_model` when evidenced, and the
summary/evidence paths (plus the review receipt path when the single-worker path
ran review). Content lives in those files — read them, never a restatement.

### 3d. Join, Integrate, and Verify

**Before accepting any worker return**, use the existing `$FLOWCTL show <task-id> --json` read below (or the handover path's status read) and check the host's background-task list or process table only for commands attributable to that task's lane by its workspace (on the single-worker path the sole lane is the conductor's checkout, so a command started there during the dispatch is that worker's); unattributable commands are not that worker's, and `in_progress` alone triggers nothing: a confirmed parallel-wave or host-deferred handover with no attributable live command proceeds through its existing gates (3d.0 first where applicable). For any `in_progress` return with an attributable live command, a confirmed handover included, wait within the dispatch `TIMEBOX`, then dispatch a re-anchoring continuation worker into the same workspace after the command exits, without counting the early return as a failed attempt; past `TIMEBOX`, the existing stand-down and 2-strike rules below govern, and with no live command the existing not-done diagnosis applies.

**Parallel wave or reviewer-overlap dispatch** (3a `Dispatch count` > 1, or an
overlapped one-task wave): read
[references/wave-join.md](wave-join.md) and execute it — it owns the
join report, integration, collision handling (never auto-resolve), the
reviewer-overlap schedule point and its plan-sync barrier, the per-task review
passes, the mandatory integrated-target verification before `done`, completion,
and workspace-first partial-failure diagnosis. Do not select more work or run
plan-sync until every dispatched worker has returned and the wave is resolved.

On the single-worker path, verify completion as before:

```bash
$FLOWCTL show <task-id> --json
```

#### 3d.0 host-deferred gate (runs FIRST on the single-worker path when this task's REVIEW_MODE was `host-deferred`)

A host-deferred worker returns with the task still `in_progress` BY DESIGN — that is the contract, not a failure. Before any failure classification, read [references/host-deferred-review.md](host-deferred-review.md) and execute its `3d.0 gate` section (re-read the persisted base, confirm the handover, run the mandatory `$flow-next-impl-review --review=host`, update evidence, then `done` only on SHIP). Only after this gate does the standard rule below apply to host-deferred tasks.

**Progress is side effects only** — commits in the lane's workspace, a moved
task status, handover files on disk. A lane past its `TIMEBOX` with none of
these is stuck, whatever its narration said: diagnose in its workspace, stand
it down, and count the stand-down against the existing 2-strike cap below —
never a third budget. (Known risk, accepted: a slow-but-healthy lane can be
stood down; the strike cap bounds that cost to one bounded retry, never
correctness.)

If status is not `done` (and the 3d.0 gate did not apply or already ran, subject to the early-return exemption above), the worker agent failed. Diagnose from ground truth (below) then retry — **but the retry is bounded**: keep a per-task failure strike counter. **After 2 consecutive non-`done` returns for the *same task*** (a worker that keeps aborting early or a persistently red Quick command), retrying stops and the failure escalates. A third respawn of the same task has broken this. Under `SPEC_MODE` / `mode:autonomous`, emit the worker's typed `BLOCKED: <reason>` as a `NEEDS_HUMAN` line and move on to the next ready task (autonomy's "never hang" promise has no loop-guard otherwise — a bad Quick command or broken baseline would rerun worker agents forever); interactively, surface the failure and stop.

**Lost / errored worker result (`[Tool result missing due to internal error]`).** On long runs the host (Agent-tool) can drop the worker's completion report — you get an error placeholder instead of the report, even though the worker's *work* may be complete. Don't block waiting for a result that will never arrive. Treat a missing/errored result the same as "status not `done`" and **diagnose from ground truth** before retrying:

```bash
$FLOWCTL show <task-id> --json          # status + evidence the worker recorded
git log --oneline -5                     # did the worker leave commits?
git status --short                       # uncommitted-but-complete changes?
```

Classify and act:
- **Already `done`** (status `done`, clean worktree at HEAD) — the report was lost but the task finished. Proceed to plan-sync (3e) as normal.
- **Code present but not finalized** (commits and/or uncommitted changes exist, but status is still `in_progress` and build/review/`flowctl done` never ran) — spawn a **re-anchoring continuation worker** that re-reads the spec + current task status + `git status`/`git diff` and resumes from the late phase (verify build → review → `flowctl done`), rather than restarting the task from scratch. For that continuation worker, the inherited trail is **authoritative for what was decided and written** — never redo it — but its **pass/fail claims are unproven**: re-verify on the real artifact (run the gate, read the receipt) before `done`. Trusting an inherited "tests green" narration is how a dead lane's unverified claim becomes a completed task.
- **Nothing landed** (no commits, clean worktree, still `in_progress`) — the worker aborted early; retry the task normally.

Done when: every dispatched task in the wave reads `done`, or has been escalated with a typed reason after its second consecutive failure — and no task is left silently `in_progress`.

#### 3d.1 Tracker sync (opt-in) — task done → status comment + evidence

**Optional. Runs only when the tracker bridge is active AND `work.done` is opted in, and only when the task reached `done` (from 3d). With no tracker configured this is a no-op.**

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$(cat <run-sync-active.json> 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — read and execute references/tracker-touchpoints.md#task-done, then continue with Phase 3e."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/tracker-touchpoints.md](tracker-touchpoints.md), execute its `Task done` section (`work.done` leaf check + best-effort dispatch), then continue with Phase 3e. When the gate is silent (bridge inactive), continue — nothing fires here.

### 3e. Plan Sync After the Resolved Wave (if enabled) — both modes

**Runs in SINGLE_TASK_MODE and SPEC_MODE.** Only the loop-back in 3f differs by mode.

Do not run plan-sync while any peer worker is active or the wave is unresolved.
After the join, integration, review, and completion steps finish, collect every
task that reached `done` in the resolved wave and run this section **once for
that set** — one `plan-sync` dispatch carrying the full completed-task list.
If a task is not `done`, omit it from the set and investigate/retry. An empty
set (nothing reached `done`) or no remaining `todo` downstream tasks means no
dispatch.

Check if plan-sync should run:

```bash
$FLOWCTL config get planSync.enabled --json
```

Skip unless planSync.enabled is explicitly `true` (null/false/missing = skip) and advance to 3f: `flowctl done` already recorded that skip's stage line on each completed task.

Downstream target extraction, the `planSync.crossSpec` read, and the `plan-sync`
subagent dispatch live in [references/plan-sync-dispatch.md](plan-sync-dispatch.md)
— read it and execute it now, then record the per-task stage-outcome lines below.
Its skip and failure branches (`skipped(empty: ...)`, `failed(EXTRACT_FAILED: ...)`)
feed those same lines. The conductor derives one line per completed task from
the batched report's per-task sections.

**Stage-outcome line (mandatory).** Whatever happened above, record ONE
outcome line for the plan-sync stage in **each** completed task's done evidence
(the task .md `## Done summary` the run already writes, via a small append or
the next `flowctl done` summary when the wave is still resolving). A single
batched dispatch still yields one line per completed task:

```
stage: plan-sync - ran [<start>..<end>] | skipped(empty: no downstream todo tasks) | failed(EXTRACT_FAILED: <detail>) | failed(error: <detail>)
```

**A skipped stage is an event with a reason, never an absence.** `DOWNSTREAM=EXTRACT_FAILED`
yields a `failed(EXTRACT_FAILED...)` line (a broken extraction becomes visible on
first occurrence) and "no downstream tasks" yields `skipped(empty...)`, which is
distinguishable from a broken extraction; a run that recorded a broken extraction as
"nothing to do", or omitted the line entirely, has broken this. Include start..end
timestamps when this orchestrator knows them.

Done when: each `done` task in the resolved wave carries exactly one `stage: plan-sync - …` line in its evidence.

### 3f. Loop or Finish

**Steps 3d and 3e run after the whole selected wave returns, in both modes.** A run
that skipped either because it was in `SINGLE_TASK_MODE` has broken this. Only the
loop-back behavior differs:

**SINGLE_TASK_MODE**: After 3d→3e, go to Phase 4 (Quality). No loop.

**SPEC_MODE**: After 3d→3e, recompute the next ready frontier at 3a. Never
select it before the current wave is joined and resolved.

### 3f.1 Pause path (wave boundary only, explicit signal only)

A run may pause ONLY at a wave boundary (the current wave joined and resolved,
before the next 3a selection), and ONLY on an explicit pause request or an
imminent-compaction signal from the host. An autonomous "keep going"
instruction never triggers it — a self-granted pause is an availability
failure dressed as prudence. To pause: commit this run's WIP (with a
broken-tree note in the commit message if the tree is not coherent). Commit
scope is the paths this run produced — `.flow/` state, files its workers
touched per their handovers — never the whole tree (the resume map is written
AFTER this commit, to `/tmp`, outside the repository — it is the explicit
handoff, never a staged path): on a
current-branch run the tree may carry uncommitted work that predates the run
(the run-start `git status` shows it), and the spec base alone cannot tell it
from the run's own (the same rule as the worker's BLOCKED revert scope) —
leave it uncommitted and name it in the resume map instead of sweeping it into
the pause commit. Then write the workspace/handover map — task ids, statuses,
workspace paths, handover paths, next frontier, any pre-existing uncommitted
paths left in place — to `/tmp/<spec-id>-resume.md`. In-context state does not
survive summarization; the resume file is the only map the next session gets.

### 3g. Completion Review Gate (SPEC_MODE only)

When 3a finds no ready tasks, this gate is default-on — its unique value is
cross-task integration + R-ID coverage.

**Policy skip — ahead of dispatch.** Judge these facts yourself (no classifier,
no config key). Skip the review when ALL of the following hold:

- (a) the spec has exactly one task
- (b) that task's per-task impl-review reached SHIP (its receipt/evidence records it; `REVIEW_MODE` was not `none`)
- (c) every spec R-ID is covered by that task's declared `satisfies`

On skip, persist the excused decision FIRST — atomically, only from `unknown`:

```bash
$FLOWCTL spec set-completion-review-status <spec-id> --status not_required --if-current unknown --json
```

Branch on the reported outcome, recording the run-scoped stage-outcome line for
the Phase 5 final summary ONLY on the two skip branches (a stage line for a
skip that did not happen is a false receipt):

```
stage: completion-review - skipped(policy: single-task, per-task SHIP covers spec surface)
```

- `.written == true` — the skip landed: record the stage line, go to Phase 4.
- `.written == false` and the reported `completion_review_status` is
  `not_required` — a prior run already excused this spec (idempotent
  re-entry): record the stage line, go to Phase 4.
- `.written == false` with a verdict status (`ship` / `needs_work` /
  `needs_human`) — a real review landed meanwhile: a normal no-skip outcome,
  not an error. Do NOT record the skip line; fall through to the status check
  below. A `refused` surface report (the spec no longer has exactly one task)
  falls through the same way: no skip line, the status check decides.

Never write `ship` here; the skip is a policy outcome, not a SHIP —
`not_required` claims the requirement is satisfied without a review having run.

Otherwise check whether review is still required.

**Check spec's completion review status directly:**

```bash
$FLOWCTL show <spec-id> --json | jq -r '.completion_review_status'
```

- If `ship` → review already passed, go to Phase 4
- If `not_required` → review excused by policy, go to Phase 4
- If `unknown` or `needs_work` → needs review

**If review needed** (policy skip did not fire):

1. Invoke `$flow-next-spec-completion-review <spec-id>` skill
   - Pass `--review=<backend>` matching the work review backend
   - Skill handles codex/copilot/cursor/claude/host backend dispatch
   - Skill owns its fix and re-review loop (working-rules.md, Review) and writes the terminal
     `completion_review_status` through its backend-aware shared owner

2. After skill returns with SHIP:
   - **Tracker sync (opt-in) — SHIP posts a verdict comment, never a terminal `Done`:** runs only when the tracker bridge is active and `completionReview` is opted in. With no tracker configured this is a no-op:

     ```bash
     ACTIVE=0
     # NO pipelines in the probe — a failed producer masked by a healthy consumer
     # fails CLOSED. Capture raw first, rc-checked; parse separately.
     RAW="$(cat <run-sync-active.json> 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
     if [ "$ACTIVE" = "0" ]; then
       VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
       [ "$VAL" = "true" ] && ACTIVE=1
     fi
     if [ "$ACTIVE" = "1" ]; then
       echo "GATE ACTIVE — read and execute references/tracker-touchpoints.md#completion-review, then continue with Phase 4."
     fi   # default branch: bare no-op — NO link, NO read path
     ```

     When the sentinel prints, read [references/tracker-touchpoints.md](tracker-touchpoints.md), execute its `Completion review` section (`completionReview` leaf check + comment-shaped verdict/R-ID-coverage dispatch), then continue with Phase 4. **`land.merged` is the only driver that writes terminal `Done`/`verified`** — a dispatch from here that flipped the issue terminal has broken this. When the gate is silent (bridge inactive), continue — nothing fires here.
   - Go to Phase 4 (Quality)

**Note:** The spec-completion-review skill owns every terminal
verdict write to `completion_review_status` (`ship`/`needs_work`/`needs_human`).
Work's single sanctioned write is the 3g policy-skip CAS
(`--status not_required --if-current unknown`); work never writes a verdict status. After
the skill returns SHIP, Work only posts the opt-in verdict / R-ID-coverage
comment to the linked tracker issue here. **That comment never flips the
issue to `Done`/`verified`** (that is gated on a `MERGED` PR and driven
solely by `land.merged`).

**Fix loop**: the skill owns it ([working-rules.md](../../../references/working-rules.md),
Review); do not re-invoke it. A `NEEDS_WORK` or an `ESCALATE:` stop comes back with its
surviving findings: report them and stop. If skill outputs `RETRY: no verdict (backend or transport failure)`, there was a backend error - retry the skill invocation.

Done when: the policy skip recorded its stage line and `completion_review_status` reads `not_required` (written by this run's CAS or already excused by a prior run), or a verdict-status CAS miss fell through to the status check without a skip line, or `completion_review_status` reads `ship` (or the gate did not apply), and the opt-in tracker comment either fired or was a documented no-op.

---

**Why spawn a worker?**

Context optimization. Each task gets fresh context:
- No bleed from previous task implementations
- Re-anchor info stays with implementation (not lost to compaction)
- Review cycles stay isolated
- Main conversation stays lean (just summaries)

A run with a single task has no next task to bleed into, so phases.md Phase 3 implements it inline unless it was sent here for a worker.

**Autonomous mode** (`mode:autonomous` token or `FLOW_AUTONOMOUS=1`): forward `FLOW_AUTONOMOUS=1` to the worker when set. It suppresses questions only.

**Interactive mode**: Permission prompts pass through to user. Worker runs in foreground (blocking).

