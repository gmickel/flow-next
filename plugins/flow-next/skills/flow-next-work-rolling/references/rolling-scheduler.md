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
mkdir -p "$NOTES_DIR" || NOTES_DIR=""
```

If creation fails, set `NOTES_DIR` empty, report
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
report `Sequential fallback: planSync.enabled=true` once. **`true` is the
SHIPPED DEFAULT** - `flowctl init` writes `planSync.enabled: true` and
`config get` answers the default when the key is absent - so a repo that never
touched this knob takes the serial branch. Rolling admission therefore has an
explicit beta prerequisite: `planSync.enabled=false`. When the gate fires
interactively, offer the exact opt-out once - `flowctl config set
planSync.enabled false`, then re-invoke - and proceed serially on decline.
Autonomous runs report the unmet prerequisite in the fallback line and NEVER
mutate config themselves.

## 3a Admission at Every Worker-Return Event

The conductor keeps an **in-flight set** of concurrently running tasks (cap 3)
and admits new ready tasks **at every worker-return event** - the moment any
in-flight task returns - instead of at wave boundaries. In SINGLE_TASK_MODE
the in-flight set is always the requested task alone. Recompute admission at
loop start and at every worker-return event; never precompute admissions for
the run - worker return order is nondeterministic.

```bash
$FLOWCTL ready --spec <spec-id> --json
```

If the ready frontier is empty AND the in-flight set is empty, the run has
quiesced: go to 3f.

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

**Tracker touchpoint:** run canonical phases.md 3b.1 exactly as written there
(read `$WORK_SKILL/phases.md`, section 3b.1) for each claimed task.

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
- **Notes pointer line:** when `NOTES_DIR` is non-empty, append one line to
  the canonical prompt template (after the config lines, before "Follow your
  phases"):

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

**Blocking-dispatch hosts degrade honestly (fail-closed).** On a host whose
ordinary subagent dispatch BLOCKS until completion and offers no background
dispatch with completion notifications (portable-host clause - Cursor, Grok,
and any other host consuming this prose as-is), dispatching multiple workers
silently recreates the wave barrier: the conductor cannot observe the first
return until all return, and the run is wave scheduling wearing a rolling
label. Do not pretend otherwise. The conductor MUST fall back to canonical
wave scheduling for the run (canonical phases.md Phase 3 semantics) AND record
the degradation wherever the run reports its shape - the run report and any
receipt line describing scheduling carries
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
- **SHIP** → run the focused integrated verify; `flowctl done` with the
  updated task-unique summary/evidence; verify `done`; run the 3d.1 tracker
  touchpoint; **run 3e for this completed task** (in the serial plan-sync mode
  that is the full canonical dispatch, and no new task is claimed or anchored
  until it finishes - done(N) precedes plan-sync(N), which precedes any anchor
  that could read N's downstream updates; in rolling mode it records the skip
  line); THEN free the slot and recompute admission at 3a. done(N) fires only
  on SHIP(N).
- **NEEDS_WORK** → drive the bounded fix loop as that task's continuing
  in-flight activity: fix, commit, integrate the fix commits, append them to
  the task's evidence, re-dispatch the re-review concurrently (same slot,
  still `(review)`). The loop never blocks handling of other events or
  admission of other tasks.
- **MAJOR_RETHINK, reviewer dispatch failure, or fix-loop cap exhausted** →
  typed escalation (below) frees the slot; recompute admission at 3a.

Reviewer identity, rubric, diff scope, and the fix-loop cap are canonical
impl-review's, untouched.

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
interactively, surface the failure and stop. The run never wedges on one task.

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
run reaches **quiesce** when the ready frontier AND the in-flight set are both
empty. At quiesce:

1. Run the full-suite verification once on the final integrated target
   (wave-join.md's integrated-target verification contract - the full gate
   runs only here, never per task); fix and commit any failure.
2. Run canonical phases.md 3g (completion review gate) exactly as written
   there - only its timing shifts to quiesce, never its semantics.

Then continue with canonical Phase 4 (quality) and Phase 5 (ship). **The notes
directory outlives quiesce**: delete it (`rm -r "$NOTES_DIR"` when non-empty)
only as the run's LAST cleanup step, after canonical Phase 5 completes cleanly
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
