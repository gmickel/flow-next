# work tracker touchpoints (gated reference)

> **Loaded only when a phases.md tracker gate prints its `GATE ACTIVE — STOP`
> sentinel** (bridge active, or the gate's probe/parse errored — fail open). A
> default (bridge-inactive) run never reads this file. Phase 5's end-of-run
> `sync check` + retro-fire + the mandatory four-state `Tracker sync:` summary
> slot are NOT here — they stay inline in phases.md Phase 5 and run on EVERY run.

Contents:

- [Bridge overview](#bridge-overview) — active predicate, perEvent table, shared gating predicate, best-effort rules
- [First claim](#first-claim) — phases.md 3b.1: first task claimed → issue In-Progress (`work.firstClaim`)
- [Task done](#task-done) — phases.md 3d.1: task done → status comment + evidence (`work.done`)
- [Completion review](#completion-review) — phases.md 3g: SHIP → verdict comment, never terminal Done (`work.completionReview`)

## Bridge overview

**The no-tracker path is the documented default and is behaviorally unchanged.** Every tracker touchpoint below runs ONLY when the bridge is **active** AND the specific event is opted in; otherwise it is a silent no-op (no new steps, no new prerequisites). The bridge is active iff `flowctl sync active --json` reports `active: true` (the single value-checked predicate from fn-52.1: raw `tracker.enabled == true` OR raw `tracker.type ∈ {linear,github,gitlab,jira}` — NOT merely that a `tracker` block exists, and NOT a stray `type:null`). Each event then reads its own nested `perEvent` leaf (all default `off`):

| Lifecycle event | perEvent key | Effect when opted in |
|---|---|---|
| first task claimed (phases.md 3b.1) | `tracker.perEvent.work.firstClaim` | move the linked issue In-Progress |
| task done (phases.md 3d.1) | `tracker.perEvent.work.done` | post a status comment + evidence (tests / commits / PR) |
| spec-completion-review SHIP (phases.md 3g) | `tracker.perEvent.completionReview` | post verdict / R-ID coverage as a comment; NEVER terminal Done (fn-66 — Done is reserved for a MERGED PR, driven by land.merged) — at most leaves the issue at In Review |

(capture / interview / plan / make-pr / resolve-pr carry their own touchpoints in those skills, gated identically on `tracker.perEvent.{capture,interview,plan,makePr,resolvePr}`.)

**Observable + forcing (fn-57):** every touchpoint invocation above carries its `event: <perEvent-key>` tag, which the tracker-sync skill stamps onto that run's receipts (`sync receipt --event`). Phase 5 then runs an end-of-run `flowctl sync check` over the events that actually triggered, retro-fires any `MISSING` touchpoint exactly once, and surfaces the outcome in a mandatory four-state `Tracker sync:` slot in the final summary (phases.md Phase 5) — a configured-but-didn't-fire touchpoint is a visible gap, never a silent one. Bridge inactive stays zero-overhead: the check exits silently and the slot reads `n/a (bridge inactive)`.

**Shared gating predicate** — every touchpoint uses this exact shape (active AND leaf ≠ off/null):

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.<key> --json | jq -r '.value')"
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
  # invoke the flow-next-tracker-sync skill (operation per the leaf / event)
  :
fi
```

The actual tracker work (transport, body merge, status who-wins, comment dedup, receipts) lives entirely in the **`flow-next-tracker-sync` skill** — the lifecycle skills only gate + delegate. Every touchpoint is **best-effort**: a tracker failure (no transport reachable, 404 issue, etc.) never blocks the lifecycle; the tracker-sync skill emits its own `sync receipt` and, under Ralph, queues genuine conflicts (`sync defer`) instead of asking. A spec with **no linked tracker id** is **flow-first-pushed (issue created + linked) on the first touchpoint that fires**, then reconciled by later ones (tracker-sync §Phase 3 "create-if-unlinked") — an active bridge keeps in-flow-authored specs in sync rather than leaving them untracked. A touchpoint only no-ops when no transport is reachable.

## First claim

phases.md **3b.1 — first claim → In-Progress.** Optional. Runs only when the tracker bridge is active AND `work.firstClaim` is opted in. Trigger only on the spec's **first** claimed task this run (the issue moves to In-Progress once, not per task).

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.work.firstClaim --json | jq -r '.value')"   # read the leaf ONCE (shared gating predicate — Bridge overview above)
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
  # Invoke the flow-next-tracker-sync skill: move the linked issue In-Progress.
  #   skill: flow-next-tracker-sync   (operation: push <spec-id>, status-only, event: work.firstClaim)
  # Unlinked spec → the skill flow-first-pushes (creates + links the issue) first,
  # then moves it In-Progress (tracker-sync §Phase 3 create-if-unlinked). No-op only
  # if no transport is reachable; in Ralph mode it queues/records a receipt — never blocks.
  :
fi
```

Best-effort: a tracker failure must never block the worker. The skill emits its own receipt, event-tagged `--event work.firstClaim` — the tag Phase 5's end-of-run `sync check` audits.

## Task done

phases.md **3d.1 — task done → status comment + evidence.** Optional. Runs only when the tracker bridge is active AND `work.done` is opted in, and only when the task reached `done` (phases.md 3d). Posts a structured status comment + evidence (tests / PR links from the task's evidence) to the linked issue; appends-only (R8), deduped by marker — never a conflict.

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.work.done --json | jq -r '.value')"   # read the leaf ONCE (shared gating predicate — Bridge overview above)
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
  # Invoke the flow-next-tracker-sync skill: append a lifecycle comment to the
  # linked issue carrying the task's done-summary + evidence (tests / commits / PR).
  #   skill: flow-next-tracker-sync   (operation: comment <spec-id>, event: work.done)
  # Unlinked spec → flow-first push (create + link) first, then comment
  # (tracker-sync §Phase 3 create-if-unlinked). No-op only if no transport; Ralph queues.
  :
fi
```

Best-effort — append-only comment sync never blocks the work loop; the skill emits its own receipt, event-tagged `--event work.done` (audited by Phase 5's end-of-run `sync check`).

## Completion review

phases.md **3g — SHIP → verdict comment, NEVER terminal Done (fn-66).** Runs only when the tracker bridge is active AND `completionReview` is opted in, immediately after the caller sets `completion_review_status=ship`. Hooked **at the caller** (not inside the review skill) because that is where `completion_review_status=ship` lands. **Local completion review is NOT merge evidence** — `Done` is reserved for a `MERGED` PR (fn-66 status-sync `flowToNormalized`), so this touchpoint is **comment-shaped only**: it posts the verdict + R-ID coverage and at most leaves the issue at `In Review` (if an open PR exists). It NEVER pushes `Done`/`verified`:

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.completionReview --json | jq -r '.value')"   # read the leaf ONCE (shared gating predicate — Bridge overview above)
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
  # Invoke the flow-next-tracker-sync skill: post the completion-review verdict +
  # R-ID coverage as a comment (comment-shaped — NEVER a terminal status push).
  # The skill's reconcileStatus gate (status-sync.md flowToNormalized) refuses
  # terminal `Done`/`verified` without a MERGED probe, so even if a stale config
  # set this leaf to `reconcile` the gate keeps it non-terminal: at most it leaves
  # the issue at `In Review` (open-PR evidence). land.merged is the SOLE Done driver.
  #   skill: flow-next-tracker-sync   (operation: comment <spec-id>, event: work.completionReview)
  #   (the comment carries the verdict + R-ID coverage as evidence — never a status push)
  # Unlinked spec → flow-first push (create + link) first, then the verdict comment
  # (tracker-sync §Phase 3 create-if-unlinked). No-op only if no transport; Ralph queues.
  # The skill's receipts carry --event work.completionReview — audited by Phase 5's sync check.
  :
fi
```
