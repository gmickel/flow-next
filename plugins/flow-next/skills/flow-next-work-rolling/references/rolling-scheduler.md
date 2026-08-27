# Rolling frontier scheduler (Phase 3 replacement)

> Loaded from this skill's SKILL.md as the run's Phase 3. `$FLOWCTL` and
> `$WORK_SKILL` are already resolved by the SKILL.md preamble. Canonical
> phases.md Phases 1, 2, 4, and 5 run unchanged around this file; every
> pointer below into `$WORK_SKILL` files means READ that file and execute the
> named section verbatim - never restate or fork it.

Contents:

- [3.0 Notes surface + plan-sync gate](#30-notes-surface--plan-sync-gate) - run setup, both fail-soft/fail-closed rules
- [3a Admission at every worker-return event](#3a-admission-at-every-worker-return-event) - the five conditions + report lines
- [3b Claim at admission](#3b-claim-at-admission) - claim-at-admission + tracker touchpoint pointer
- [3c Spawn workers](#3c-spawn-workers) - always `PARALLEL_WAVE: true`; notes pointer line
- [3d Per-return integrate, review, complete](#3d-per-return-integrate-review-complete) - event-driven lifecycle; conductor-owned review; failure strikes
- [3e Plan-sync stage lines](#3e-plan-sync-stage-lines) - serial-only execution; mandatory stage-outcome lines
- [3f Quiesce](#3f-quiesce) - loop rule, full suite at quiesce, completion gate pointer, end-of-run notes cleanup

**Why isolated worktrees (design rationale, fn-203 eval).** The pre-registered
three-arm eval also tested this scheduler over a single shared checkout with
commit discipline (stage only your declared paths, commit under a mutex). That
arm was faster still - and failed quality parity, with a measured mechanism:
when the Touches declaration is the commit boundary, every NEW file a worker
creates risks a violation, and tests are exactly the artifact that spawns new
files - the arm was structurally incentivized toward fewer test files (11 vs 20
at comparable product code), and constrained verify windows made test iteration
costly. The per-task worktree pool dissolves both pressures: workers create
files and run suites freely, and the conductor's per-return integration doubles
as a quality pass over each diff. Speed bought by under-testing is the failure
mode this architecture exists to avoid.

## 3.0 Notes surface + plan-sync gate

**Shared notes surface (create FIRST, advisory).** One per-run notes directory
outside the mutable tree, sibling to the runtime state dir, keyed by spec id
plus a run identifier so concurrent runs (other specs, or a beta and a
canonical session sharing one state root) never collide:

```bash
# Sibling of the runtime state dir: FLOW_STATE_DIR's parent when set,
# else the git common dir (where flowctl keeps flow-state/).
if [ -n "${FLOW_STATE_DIR:-}" ]; then
  NOTES_PARENT="$(dirname "$FLOW_STATE_DIR")"
else
  NOTES_PARENT="$(git rev-parse --path-format=absolute --git-common-dir)"
fi
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
NOTES_DIR="$NOTES_PARENT/flow-notes/<spec-id>-$RUN_ID"
# Remove any stale pointer FIRST - an interrupted earlier run can leave
# .flow/tmp/notes_dir behind, and 3c reads the FILE: if this run's mkdir
# then failed, workers would inherit the abandoned run's directory (and 3f
# cleanup would delete it). Clearing only the shell variable has broken this.
rm -f .flow/tmp/notes_dir
if mkdir -p "$NOTES_DIR" \
   && mkdir -p .flow/tmp \
   && printf '%s' "$NOTES_DIR" > .flow/tmp/notes_dir; then
  : # Pointer persisted - bash variables do not survive tool calls.
else
  NOTES_DIR=""
fi
```

The path embeds a timestamp and PID, so it cannot be re-derived later:
every later consumer (the 3c pointer lines, 3f cleanup) re-reads it via
`$(cat .flow/tmp/notes_dir)` instead of assuming the shell variable
survived. `.flow/tmp/notes_dir` is runtime state under `.flow/tmp` (already
outside the receipts discipline) and is removed together with the notes
directory at 3f cleanup.

If creation OR the pointer persist fails (the two are one failure mode: a
surface whose pointer never landed is unreachable by 3c's file read), set
`NOTES_DIR` empty, report
`Notes surface: unavailable (<reason>) - continuing without it`, and run
WITHOUT the surface - advisory, never blocking. When it exists, pass its path
in **every** worker and scout dispatch prompt as a pointer line (3c). Scouts
and workers write markdown notes there (exploration findings, integration
warnings for later tasks); consumers read by pointer. **Never embed the notes
directory's content into a dispatch prompt** - a dispatch that pasted a note's
body instead of the path has broken this. The conductor deletes the directory
only after canonical Phase 5 completes cleanly (see 3f); a dir abandoned by an
interrupted run is inert prose and may be removed by hand.

**plan-sync gate (fail-closed).** Before the first admission:

```bash
$FLOWCTL config get planSync.enabled --json
```

Unless the answer is explicitly `false`, concurrent admission is DISABLED for
the entire run: dispatch strictly serially (at most one in-flight task; 3e
runs after each completed task exactly as canonical phases.md 3e ships) and
report `Sequential fallback: planSync.enabled=true` once. **`false` is the
shipped default since 4.5.1** - `flowctl init` writes `planSync.enabled: false`
and `config get` answers the default when the key is absent - so a fresh repo
takes the rolling branch. A repo that opted into plan-sync (`true`, including
every pre-4.5.1 init) fail-closes to serial: the beta prerequisite is
`planSync.enabled=false`. When the gate fires interactively, offer the exact
opt-out once - `flowctl config set planSync.enabled false`, then re-invoke -
and proceed serially on decline. Autonomous runs report the unmet prerequisite
in the fallback line and NEVER mutate config themselves.

## 3a Admission at Every Worker-Return Event

The conductor keeps an **in-flight set** of concurrently running tasks (cap 3)
and admits new ready tasks **at every worker-return event** - the moment any
in-flight task returns - instead of at wave boundaries. In SINGLE_TASK_MODE
(single task, no loop - mirroring canonical phases.md), run start is the run's
ONE admission event and its sole candidate is the requested task: it is
admitted (the five conditions are judged against an empty comparison set and
hold vacuously, except condition 5's always-serial check, which still applies -
and a single task dispatching alone already IS serial dispatch), claimed per
3b (a failed claim is 3b's typed contention outcome, never a silent stall),
dispatched per 3c, and 3d/3f then run as written with the in-flight set being
that task alone. Recompute admission at
loop start and at every worker-return event; never precompute admissions for
the run - worker return order is nondeterministic.

```bash
$FLOWCTL ready --spec <spec-id> --json
```

If the ready frontier is empty AND the in-flight set is empty, check for
**foreign in-flight tasks** before calling it quiesce: read
`$FLOWCTL tasks --spec <spec-id> --json` and collect every task that is
`in_progress` but NOT in this conductor's in-flight set - those belong to
another run (canonical or beta) on the same spec, and `flowctl ready`
rightly excludes them from the frontier. Only when that foreign set is ALSO
empty has the run quiesced: go to 3f. When foreign in_progress tasks exist
with an empty local set, do NOT quiesce - completion review against another
run's incomplete work is the failure this check exists to prevent. Report
the contention (task ids + who holds them) and end the run with a typed
contention outcome:

```text
Rolling run ended: spec contended (fn-X.N in_progress by another run) - quiesce deferred to that run or a re-invocation
```

This is the same fail-closed posture as 3b's claim contention: runs never
steal from or bless over each other.

In SPEC_MODE, apply the **admission rule (fail-closed - canonical fn-176 wave
rule, re-scoped from wave peers to the in-flight set)**. Admission within one
event is **incremental**: consider candidates one at a time (ready-list
order), and judge each against the **comparison set** = every task currently
in flight PLUS every candidate already tentatively admitted at THIS event.
Checking candidates only against the pre-event in-flight set has broken this -
two candidates with intersecting Touches would both pass. A candidate is
admitted only when ALL five conditions hold against EVERY task in the
comparison set; any one unmet holds the candidate (a held candidate is not
added to the comparison set):

1. same spec;
2. in-flight size after admission ≤ 3;
3. no dependency path between the candidate and any comparison-set task, in
   either direction, **transitively** (walk the `depends_on` closure from
   `$FLOWCTL show <task-id> --json` / `$FLOWCTL tasks --spec <spec-id> --json`
   - `flowctl dep` only writes edges, it has no read verb; a direct-only check
   is wrong);
4. the candidate carries a `**Touches:**` declaration, and its declared set is
   **disjoint** vs every comparison-set task's declared set
   (`touches(candidate) ∩ touches(member) = ∅`, glob-aware) - so the tasks
   admitted at one event are pairwise Touches-disjoint by construction;
5. the candidate does not touch the always-serial set: `.flow/`, lockfiles,
   migration dirs, codegen/generated outputs, or spec/task files.

The error paths are the rule: a candidate with no `**Touches:**` declaration →
held; any intersection → held; any doubt about a glob, a hidden coupling
(shared fixtures, services), or host capacity → held. An empty admissible set
with a non-empty frontier degrades to serial dispatch - the next ready task
dispatches alone once the in-flight set drains - and the report states why
each held task is held. The failure mode is sequential dispatch, never a risky
admission. Safety is structural: workers run in isolated workspaces, so a
wrong admission surfaces at that task's integration as a merge conflict (3d),
costing one serial retry, never correctness. Never run concurrent writers in
one checkout. An explicit request to parallelize strengthens the preference
but never overrides the rule.

Report the decision at every admission event, before claiming (the canonical
report lines plus three rolling lines - exhaustive shape):

```text
Ready frontier: [fn-X.4, fn-X.5]
In-flight: [fn-X.1 (review), fn-X.3 (impl)]
Admitted: [fn-X.4]
Held: [fn-X.5: Touches intersects fn-X.3]
Isolation: <native worktrees | linked worktrees | other safe mechanism>
Dispatch count: 1
Sequential fallback: <reason> # only when the admissible set is empty with a non-empty frontier
```

Done when: the report lines are printed for this admission event and every
admitted task satisfies all five conditions against the in-flight set.

## 3b Claim at Admission

Claim every task admitted at this event before dispatch:

```bash
$FLOWCTL start <task-id> --json
```

If a claim fails, do not dispatch that task: drop it from this admission event
(it may become admissible again at a later event; recompute from ground
truth). A failed claim can also mean another run - beta or canonical - owns
the task: claims are spec-scoped in the shared runtime state store, and
contention fails closed. Never clear or steal another run's claim. Retain
every successfully claimed task; never abandon a task this conductor already
moved to `in_progress`.

**All-claims-lost re-entry (no event will save you).** If candidates were
admitted at this event but EVERY one of them lost its claim race (e.g. the
sole ready task at loop start was claimed by another run), no worker gets
dispatched - so no worker-return event will ever re-enter 3a, and waiting
would hang the loop. Instead, immediately recompute ground truth and re-run
admission (one immediate re-entry to 3a; the claims that beat us now show as
foreign in_progress and 3a's foreign-in-flight check sees them). If the
recomputed frontier is empty and the local in-flight set is empty, route to
3a's typed contention outcome (`Rolling run ended: spec contended ...`)
rather than waiting for an event that cannot arrive.

**Tracker touchpoint:** run canonical phases.md 3b.1 exactly as written there
(read `$WORK_SKILL/phases.md`, section 3b.1) **once per RUN, at the run's
first successful claim only** - the `work.firstClaim` event is a run-lifecycle
event, not a per-task one (tracker-touchpoints.md scopes it to the spec's
first claimed task). Track that it fired; later admission events never re-run
it. A run that dispatched 3b.1 per claimed task has broken this.

## 3c Spawn Workers

Read canonical phases.md 3c (`$WORK_SKILL/phases.md`) and execute it with
these fixed values - everything else (implementer-tier routing, the
commit-spec-files-first rule, the prompt template, per-task `REVIEW_MODE`
resolution, `BASELINE_HANDOFF` judgment) is canonical:

- **Every admitted worker - including a one-task admission - gets its own
  isolated mutable workspace, task-unique summary/evidence paths, and
  `PARALLEL_WAVE: true`.** There is no self-completing single-worker path in
  this beta: the worker implements, tests, and commits in its workspace, then
  returns the parallel handover. Review and completion are conductor-owned
  for every backend (3d) - the conductor RECORDS each task's resolved
  `REVIEW_MODE` at dispatch and applies it itself after integration.
- **Notes pointer line:** when `.flow/tmp/notes_dir` exists, re-read the
  path (`NOTES_DIR="$(cat .flow/tmp/notes_dir)"` - never assume the 3.0
  shell variable survived intervening tool calls) and append one line to
  the canonical prompt template (after the config lines, before "Follow your
  phases"). A MISSING pointer file means this run has no notes surface
  (3.0 failed and reported it): omit the line and dispatch without it -
  never treat the absence as an error:

  ```
  NOTES_DIR: <path>   # shared run-notes surface - read it by pointer for sibling findings; write markdown notes (findings, integration warnings) there; never restate its content in prompts or returns
  ```

  The same pointer line goes into every scout dispatch this run makes.

**Do not block the loop on the full in-flight set.** Rolling admission
requires a **non-blocking join mechanism**: on hosts whose subagent dispatch
runs in the background and delivers a completion notification (Claude Code's
background Task dispatch is the canonical example), dispatch every admitted
worker in the background and treat each completion notification as the event -
a worker return OR a review completion (3d) - handle it, then recompute
admission at 3a. While one task's review or fix loop runs, the other in-flight
workers keep running.

**Blocking-dispatch hosts degrade honestly (fail-closed - scheduling/join
only).** On a host whose ordinary subagent dispatch BLOCKS until completion
and offers no background dispatch with completion notifications, dispatching
multiple workers silently recreates the wave barrier. **Judge that condition
by the host's ACTUAL dispatch behavior - a live measurement (dispatch two
short sleep agents and observe whether control returns before completion,
with per-completion signals) or a prior in-session one - never by host name:
the original host list here was an assumption, and both named hosts fell to a
five-minute probe (measured non-blocking and rolling end-to-end 2026-08-27:
Cursor on macOS, and Grok Build 1.0.5 via `spawn_subagent` background mode;
Claude Code's background Task dispatch remains the canonical example).** On a
genuinely blocking host the failure shape is: the
conductor cannot observe the first return until all return, and the run is
wave scheduling wearing a rolling label. Do not pretend otherwise - but
degrade ONLY the scheduling and the join, never the rest of this beta's
lifecycle. The conductor keeps running THIS file's phases with wave-shaped
dispatch: admit a group per 3a, claim per 3b, dispatch the group, and await
it as a group - the host's blocking dispatch IS the join - then run 3d for
each returned task in the group (integration, conductor-owned review,
completion) before the next admission event. The notes surface (3.0 creation,
3c pointer lines, 3f cleanup) and every other section of this file apply
unchanged; only the rolling overlap is lost, exactly as the platforms note
states. Record the degradation wherever the run reports its shape - the run
report and any receipt line describing scheduling carries
`Scheduling: degraded to wave (host lacks non-blocking dispatch)` - so a field
receipt can never claim rolling for a run that actually exercised waves.

## 3d Per-Return Integrate, Review, Complete

**The task lifecycle is event-driven; a task holds its in-flight slot (and
counts against the cap) from admission until `done` or a typed escalation.**
Two event kinds drive 3d, and **admission (3a) is recomputed immediately after
handling EACH event** - never deferred to the end of a task's review tail:

**Worker-return event** (that task only):
1. Read `$WORK_SKILL/references/wave-join.md` and execute its handover +
   integration steps: confirm the handover; integrate that task's workspace
   commits onto the target branch; normalize its evidence SHAs to the
   integrated commit IDs (retaining the task's normalized integrated base and
   head).
2. When the task's resolved `REVIEW_MODE` is not `none`, LAUNCH its review
   conductor-side
   (`/flow-next:impl-review <task-id> --base <task-normalized-integrated-base> --review=<backend>`
   from a safe review context per wave-join.md) **as a concurrent activity via
   the thin-wrapper-subagent pattern from the project's orchestration
   guidance - do not wait for the verdict here.** The task transitions to the
   `(review)` in-flight state, still holding its slot. When `REVIEW_MODE` is
   `none`, skip to the SHIP branch of the review-completion event below.
3. Recompute admission at 3a NOW.

**Degraded serial-review path:** a host with no concurrent-dispatch primitive
for the review runs it inline (blocking) instead; admission then recomputes
after the verdict. That is a degradation to report
(`Sequential fallback: review ran inline (no concurrent dispatch)`), never the
default shape.

**Review-completion event** (that task only):
- **SHIP** → FIRST, when the review's internal fix loop produced commits,
  integrate them onto the target branch with the same wave-join.md
  integration mechanics the task's own workspace commits used (they live in
  the review context, not on the target) and append their integrated SHAs to
  the task's evidence commits - a SHIP whose fix commits are not on the
  target is not a completable state, and running `done` over it has broken
  this. THEN run the focused integrated verify; `flowctl done` with the
  updated task-unique summary/evidence; verify `done`; run the 3d.1 tracker
  touchpoint; **run 3e for this completed task** (in the serial plan-sync mode
  that is the full canonical dispatch, and no new task is claimed or anchored
  until it finishes - done(N) precedes plan-sync(N), which precedes any anchor
  that could read N's downstream updates; in rolling mode it records the skip
  line); THEN free the slot and recompute admission at 3a. done(N) fires only
  on SHIP(N).
- **NEEDS_WORK** → TERMINAL. impl-review returns NEEDS_WORK only after its
  own internal fix loop and churn cap are exhausted; the canonical worker
  contract is exactly one impl-review invocation per task, then typed
  escalation. The conductor escalates exactly as that contract does: the
  typed escalation (below) frees the slot, the task stays un-`done` and is
  reported NEEDS_HUMAN-style in the run report. Never dispatch a second
  review for the task and never mutate it further this run - starting a
  conductor-side fix/re-review cycle on NEEDS_WORK has broken this.
  Admission of other tasks continues unaffected; recompute at 3a.
- **MAJOR_RETHINK or reviewer dispatch failure** →
  typed escalation (below) frees the slot; recompute admission at 3a.

Reviewer identity, rubric, diff scope, and the internal fix-loop cap are
canonical impl-review's, untouched.

**Join collision:** a merge conflict at integration means the admission rule's
declared `**Touches:**` sets were wrong - a wrong admission surfacing
structurally. Never auto-resolve: follow wave-join.md's collision handling
(abort the conflicted integration, keep the target clean, record the
`stage: wave-join - failed(collision: ...)` line). The losing task then enters
an explicit **collision-hold** state: it KEEPS its claim and its in-flight
slot (so nothing else claims it) and is appended to an ordered
**collision-retry queue** (return order). While that queue is non-empty the
conductor admits NO new tasks and drains every **non-held** in-flight task to
completion or typed escalation - a second task that collides during the drain
joins the queue in the same held state rather than resetting anything. Once
no non-held task remains, retry the queued tasks one at a time in queue
order, each serially from the current joined target state; a queued hold is
parked, not executing, so it never blocks the active retry. Each retried
task's slot frees on completion or typed escalation, exactly like any other
task; admission resumes when the queue is empty. Waiting for the WHOLE set to
drain would deadlock on the held tasks' own slots - the drain condition is
"every non-held task", never "the whole set". One serial retry per collided
task, never a correctness loss.

**Worker failure handling (per task).** A worker that returns without a valid
handover (or whose result is lost) is diagnosed from ground truth INSIDE its
assigned workspace per wave-join.md's partial-failures rules, then classified
per canonical phases.md 3d (work complete / continuation worker into the SAME
workspace / retry). **The retry is bounded by the canonical per-task strike
counter (2 consecutive failures → typed escalation; a third respawn has broken
this).** A stall-guard terminal (blocked-with-green-code) or the second
consecutive failure FREES the in-flight slot: the task leaves the set with its
typed `BLOCKED:` escalation and the loop continues - under SPEC_MODE /
`mode:autonomous`, emit a `NEEDS_HUMAN` line and keep admitting other tasks;
interactively, surface the failure and stop - but **DRAIN before stopping**:
stop admitting new tasks, await every live worker return and review
completion, and run each returned task's 3d handling (integrate, review,
complete, or escalate as that task's own outcome dictates); only then stop,
with the failure report covering every task's terminal state. Stopping while
siblings are live abandons their `in_progress` claims and lets late returns
arrive after the conductor is gone - no task is ever left silently
`in_progress`. The run never wedges on one task.

**Tracker touchpoint:** when the task reached `done`, run canonical phases.md
3d.1 exactly as written there.

## 3e Plan-Sync Stage Lines

The 3.0 gate already decided this run's shape. When `planSync.enabled` is
explicitly `true`, the run is SERIAL and canonical phases.md 3e runs after
each completed task exactly as shipped (read `$WORK_SKILL/phases.md` 3e and
its plan-sync-dispatch reference; done(N) precedes plan-sync(N), which
precedes any anchor that could read N's downstream updates). When plan-sync is
off (rolling admission active), record the skip line on each completed task -
`stage: plan-sync - skipped(config: planSync.enabled != true)` - per the
canonical stage-outcome contract. A skipped stage is an event with a reason,
never an absence.

## 3f Quiesce

**SINGLE_TASK_MODE**: after 3d→3e for the requested task, go to canonical
Phase 4. No loop.

**SPEC_MODE**: every event - worker return or review completion - loops back
to 3a (recompute the frontier, admit, dispatch) after its 3d handling. The
run reaches **quiesce** when the ready frontier, the in-flight set, AND 3a's
foreign in-flight set (tasks `in_progress` under another run on this spec)
are ALL empty - a non-empty foreign set routes to 3a's typed contention
outcome instead, never here. At quiesce:

1. Run the full-suite verification once on the final integrated target
   (wave-join.md's integrated-target verification contract - the full gate
   runs only here, never per task); fix and commit any failure.
2. Run canonical phases.md 3g (completion review gate) exactly as written
   there - only its timing shifts to quiesce, never its semantics.

Then continue with canonical Phase 4 (quality) and Phase 5 (ship). **The notes
directory outlives quiesce**: delete it only as the run's LAST cleanup step -
re-read the path from the persisted file
(`NOTES_DIR="$(cat .flow/tmp/notes_dir)"`; the 3.0 shell variable has not
survived this many tool calls), then
`rm -r "$NOTES_DIR" && rm -f .flow/tmp/notes_dir` when non-empty - after
canonical Phase 5 completes cleanly
- a quality or ship failure is not a clean completion, and its diagnostic
notes must still exist. On an interrupted or escalated run leave the directory
in place (inert prose, removable by hand).

**The run is not over at the last `done` (field receipt #1, 2026-08-22).** The
final integration is the moment this failure happens: the frontier is empty,
every task reads `done`, and ending the turn feels complete - but quiesce has
not run. **Detect quiesce and continue IN THE SAME TURN**: after ANY 3d
handling, recompute the frontier immediately; when it and the in-flight set
are both empty, proceed straight into steps 1-2 above and canonical Phases
4-5 without ending the turn, ever waiting for another event (none is coming),
or handing control back. A session that ends after the final integration
without the Phase 5 final summary - unrun quiesce suite, undeleted notes
directory, no `Tracker sync:` slot - has broken this. This is doubly binding
in headless/background sessions, where no user exists to nudge the run
onward.
