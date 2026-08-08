# Wave join, integrate, and verify (gated reference)

> **Loaded only when this run dispatched a parallel wave** (phases.md 3a
> `Dispatch count` > 1) **or a reviewer-overlap one-task wave** (fn-176). A run whose
> waves are all single, non-overlapped workers never reads this file — phases.md 3d's
> inline single-worker verify + failure rules cover it.

Contents:

- [Join and integrate](#join-and-integrate) — wait for every worker, report outcomes, bring commits onto the target
- [Join collision handling](#join-collision-handling) — fn-176: never auto-resolve; serial re-run of the losing task
- [Reviewer overlap](#reviewer-overlap) — fn-176: the schedule point, its preconditions, and the plan-sync barrier
- [Per-task review, integrated verify, completion](#per-task-review-integrated-verify-completion) — the six ordered steps
- [Partial failures](#partial-failures) — diagnose inside the assigned workspace before classifying

## Join and integrate

For a parallel wave, wait for every dispatched worker before selecting more
work or running plan-sync. Report each worker outcome and the completed join:

```text
Worker outcomes:
- fn-X.1: success — <commit/workspace>
- fn-X.2: failed — <typed reason or ground-truth state>
Join: complete (2/2 returned)
```

Use the host's chosen integration mechanism to bring each successful worker's
commits onto the target branch.

## Join collision handling

**Join collision handling (fn-176 — never auto-resolve).** A merge conflict at
the join means the wave dispatch rule's declared `**Touches:**` sets were
wrong. Never resolve conflict hunks by hand and never drop the losing commits:
abort the conflicted integration, keep the clean side joined, then SERIALLY
re-run the losing task from the joined state (fresh worker, current tree).
Record the collision in the receipt surface — a stage-outcome line per fn-178:
`stage: wave-join - failed(collision: <task-ids> on <paths>)` — so plan review
sees which `**Touches:**` declarations were wrong.

## Reviewer overlap

**Reviewer overlap (fn-176).** review(N) may run concurrently with
implement(N+1) ONLY when ALL hold: N+1 is dep-independent of N (transitive,
same walk as the dispatch rule); AND `planSync.enabled` is NOT true — Phase
3e's actual target set is EVERY remaining `todo` task, so with plan-sync on,
a claimed N+1 would dodge the sync it is entitled to; with plan-sync enabled
the overlap path is OFF and dispatch of N+1 waits for plan-sync(N) exactly as
today (fail-closed: the status quo is the failure mode). **The schedule point
is the sequential single-worker path**: when worker N has returned and its
impl-review is about to be dispatched, the conductor MAY claim and dispatch
N+1's worker (isolated workspace, wave rules apply) before or while running
review(N) — instead of leaving the reviewer as the only live agent. This
schedule point exists for review modes the CONDUCTOR runs after the worker
returns (`host` / host-deferred); with worker-owned review backends (rp,
codex, copilot, cursor) the review finishes inside the worker, so there is
nothing to overlap post-return — concurrency there comes from the wave
dispatch rule itself. The
overlapped worker is a ONE-TASK WAVE: it returns the parallel-wave handover
(workspace, commits, summary/evidence paths; no `flowctl done`), and the
conductor joins, reviews, and completes it through the standard 3d machinery
before 3f recomputes the ready frontier — never left dangling. On the
parallel-wave path the existing join-then-review order stands unchanged.
**Plan-sync remains the barrier before any dependent work anchors**: done(N)
still precedes plan-sync(N), which still precedes any anchor that could read
N's downstream updates — overlap is scheduling only and never reorders
receipts.

## Per-task review, integrated verify, completion

Reuse the existing per-task review contract in
two passes:

1. confirm the task's code, tests, commit, and handover files;
2. normalize each task's evidence to the integrated commit IDs and retain its
 exact task-specific normalized integrated base **and head**;
3. when its resolved `REVIEW_MODE` is not `none`, run
 `$flow-next-impl-review <task-id> --base <task-normalized-integrated-base> --review=<backend>`
 from a safe review context whose `HEAD` is that task's normalized integrated
 head. The host chooses that context and isolation mechanism; it must not use
 the wave target's later `HEAD` when peer commits extend it. Apply the existing
 bounded fix loop, integrate any review-fix commits onto the target branch,
 and append them to that task's evidence.

After every successful task has the required SHIP verdict (or review is `none`)
and all review-fix commits are integrated:

4. run the existing Phase 5 Verify contract once on the final integrated target
 **immediately before tasks are marked done**. This verification is mandatory
 even when every worker was green in isolation: classify the combined diff,
 honor only valid integrated-HEAD receipts, otherwise run the required suite,
 and fix + re-commit any failure. Append verification-fix commits (distinct
 from review-fix commits) plus the integrated-target verification's exact
 commands/results to every affected task's evidence;
5. for each successful task, run `flowctl done` with the updated task-unique
 summary/evidence;
6. verify `flowctl show <task-id> --json` reports `done`, then run the existing
 3d.1 tracker touchpoint.

## Partial failures

Partial failures use the ground-truth recovery rules in phases.md 3d, but first
diagnose each failed or missing-result worker **inside its assigned workspace**.
The conductor already knows that workspace plus the task-unique
`HANDOVER_SUMMARY` and `HANDOVER_EVIDENCE` paths from dispatch; enter and
physically verify the workspace, inspect those handovers, and run
`flowctl show`, `git log`, and `git status` there before classifying the
failure. Never infer "nothing landed" from the wave target or conductor
checkout when the worker used an isolated workspace. Successful tasks may be
integrated and completed, but the wave is not resolved until each failed task
has been continued, retried within the existing cap, or surfaced as blocked.
No batch state is introduced.
