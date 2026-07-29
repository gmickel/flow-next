# work tracker touchpoints (gated reference)

> **Loaded only when a phases.md tracker gate prints its active
> read/execute/continue sentinel** (bridge active, or the gate's probe/parse
> errored — fail open). A default (bridge-inactive) run never reads this file. Phase 5's end-of-run
> `sync check` + retro-fire + the mandatory four-state `Tracker sync:` summary
> slot are NOT here — they stay inline in phases.md Phase 5 and run on EVERY run.

Contents:

- [Bridge overview](#bridge-overview) — active predicate, perEvent table, shared gating predicate, best-effort rules
- [First claim](#first-claim) — phases.md 3b.1: first task claimed → issue In-Progress (`work.firstClaim`)
- [Task done](#task-done) — phases.md 3d.1: task done → status comment + evidence (`work.done`)
- [Completion review](#completion-review) — phases.md 3g: SHIP → verdict comment, never terminal Done (`completionReview`)

## Bridge overview

**The no-tracker path is the documented default and is behaviorally unchanged.** Every tracker touchpoint below runs ONLY when the bridge is **active** AND the specific event is opted in; otherwise it is a silent no-op (no new steps, no new prerequisites). The bridge is active iff `flowctl sync active --json` reports `active: true` (the single value-checked predicate from fn-52.1: raw `tracker.enabled == true` OR raw `tracker.type ∈ {linear,github,gitlab,jira}` — NOT merely that a `tracker` block exists, and NOT a stray `type:null`). Each event then reads its own nested `perEvent` leaf (all default `off`):

| Lifecycle event | perEvent key | Resolved facade op | Effect when opted in |
|---|---|---|---|
| first task claimed (phases.md 3b.1) | `tracker.perEvent.work.firstClaim` | fixed `push --status-only` for `pull`, `push`, `reconcile`, or `comment` | move the linked issue In-Progress without body/relation overwrite |
| task done (phases.md 3d.1) | `tracker.perEvent.work.done` | fixed `comment` for `pull`, `push`, `reconcile`, or `comment` | post a status comment + evidence (tests / commits / PR) |
| spec-completion-review SHIP (phases.md 3g) | `tracker.perEvent.completionReview` | fixed `comment` for `pull`, `push`, `reconcile`, or `comment` | post verdict / R-ID coverage as a comment; NEVER terminal Done (fn-66: Done is reserved for a MERGED PR, driven by land.merged); at most leaves the issue at In Review |

(capture / interview / plan / make-pr / resolve-pr carry their own touchpoints in those skills, gated identically on `tracker.perEvent.{capture,interview,plan,makePr,resolvePr}`.)

**Observable + forcing (fn-57):** every touchpoint invocation above carries its `event: <perEvent-key>` tag, which the tracker-sync skill stamps onto that run's receipts (`sync receipt --event`). Phase 5 then runs an end-of-run `flowctl sync check` over the events that actually triggered, retro-fires any `MISSING` touchpoint exactly once, and surfaces the outcome in a mandatory four-state `Tracker sync:` slot in the final summary (phases.md Phase 5) — a configured-but-didn't-fire touchpoint is a visible gap, never a silent one. Bridge inactive stays zero-overhead: the check exits silently and the slot reads `n/a (bridge inactive)`.

**Shared gating predicate** — every touchpoint uses this exact shape (active AND leaf ≠ off/null):

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.<key> --json | jq -r '.value')"
case "$LEAF" in
 pull|push|reconcile|comment) ENABLED=1 ;;
 off|null) ENABLED=0 ;;
 *) ENABLED=0 ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
 && [ "$ENABLED" = "1" ]; then
 # invoke the event's fixed lifecycle facade operation below
 :
fi
```

The actual tracker work (transport, body merge, status who-wins, comment dedup, receipts) lives entirely in the **`flow-next-tracker-sync` inline wrapper and fn-140 lifecycle facade**. Lifecycle skills keep the silent caller gate and synthesize their own comment content. The wrapper prepares mode `0600` inputs, makes exactly one `flowctl tracker sync` call, then routes structured recovery. Every touchpoint is **best-effort**: a tracker failure (no transport reachable, 404 issue, etc.) never blocks the lifecycle. A spec with **no linked tracker id** is created and linked by the facade on the first touchpoint that fires. A touchpoint only no-ops when no transport is reachable.

## First claim

phases.md **3b.1 — first claim → In-Progress.** Optional. Runs only when the tracker bridge is active AND `work.firstClaim` is opted in. Trigger only on the spec's **first** claimed task this run (the issue moves to In-Progress once, not per task).

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.work.firstClaim --json | jq -r '.value')" # read the leaf ONCE (shared gating predicate — Bridge overview above)
case "$LEAF" in
 pull|push|reconcile|comment) OP="push" ;;
 off|null) OP="off" ;;
 *) OP="off" ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
 && [ "$OP" != "off" ]; then
 # Invoke the inline wrapper. Work supplies the create-time approved snapshots,
 # then the wrapper makes exactly one facade call:
 # "$FLOWCTL" tracker sync "$SPEC_ID" --op push --status-only --event work.firstClaim <legal file flags>
 # For an already-linked issue this updates status only: it never pushes the
 # local body or relations over tracker-side edits. An unlinked spec still
 # creates, links, seeds the paired base, and then updates status.
 # Unlinked specs create and link inside the facade. No reachable transport is
 # best-effort; in Ralph mode structured conflicts queue instead of asking.
 :
fi
```

Best-effort: a tracker failure must never block the worker. The skill emits its own receipt, event-tagged `--event work.firstClaim` — the tag Phase 5's end-of-run `sync check` audits.

## Task done

phases.md **3d.1 — task done → status comment + evidence.** Optional. Runs only when the tracker bridge is active AND `work.done` is opted in, and only when the task reached `done` (phases.md 3d). Posts a structured status comment + evidence (tests / PR links from the task's evidence) to the linked issue; appends-only (R8), deduped by marker — never a conflict.

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.work.done --json | jq -r '.value')" # read the leaf ONCE (shared gating predicate — Bridge overview above)
case "$LEAF" in
 pull|push|reconcile|comment) OP="comment" ;;
 off|null) OP="off" ;;
 *) OP="off" ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
 && [ "$OP" != "off" ]; then
 # Work synthesizes the comment content by name: the task done summary plus
 # tests, commits, and PR evidence. Its FIRST line is the stable per-task
 # identity `evidence=<task-id>@<final-evidence-commit-sha>` (or, when the
 # task has no commit, `<task-id>@<sha256-of-task-evidence-json>`). Write the
 # remaining comment to a mode 0600 temporary body file.
 # The inline wrapper then makes exactly one facade call and deletes the file:
 # "$FLOWCTL" tracker sync "$SPEC_ID" --op comment --event work.done --body-file "$BODY_FILE"
 # Unlinked specs create and link inside the facade. No reachable transport is
 # best-effort; Ralph queues structured conflicts.
 :
fi
```

Best-effort — append-only comment sync never blocks the work loop; the skill emits its own receipt, event-tagged `--event work.done` (audited by Phase 5's end-of-run `sync check`).

## Completion review

phases.md **3g — SHIP → verdict comment, NEVER terminal Done (fn-66).** Runs only when the tracker bridge is active AND `completionReview` is opted in, immediately after the completion-review skill returns with its terminal status already written. The status owner stays inside the review skill; this caller-owned touchpoint exists only to project the verdict evidence. **Local completion review is NOT merge evidence** — `Done` is reserved for a `MERGED` PR (fn-66 status-sync `flowToNormalized`), so this touchpoint is **comment-shaped only**: it posts the verdict + R-ID coverage and at most leaves the issue at `In Review` (if an open PR exists). It NEVER pushes `Done`/`verified`:

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.completionReview --json | jq -r '.value')" # read the leaf ONCE (shared gating predicate — Bridge overview above)
case "$LEAF" in
 pull|push|reconcile|comment) OP="comment" ;;
 off|null) OP="off" ;;
 *) OP="off" ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
 && [ "$OP" != "off" ]; then
 # Work synthesizes the comment content by name: completion-review verdict and
 # R-ID coverage. Its FIRST line is `evidence=<reviewed-head-sha>`, so a retry
 # of the same review deduplicates while a review after new commits does not.
 # Write it to a mode 0600 temporary body file. The inline wrapper makes
 # exactly one facade call and deletes the file:
 # "$FLOWCTL" tracker sync "$SPEC_ID" --op comment --event completionReview --body-file "$BODY_FILE"
 # This is comment-only and NEVER a terminal status push. land.merged is the
 # sole Done driver. Unlinked specs create and link inside the facade.
 # The facade receipt carries --event completionReview and is audited by
 # Phase 5's sync check. The tag matches
 # the TOP-LEVEL config leaf (tracker.perEvent.completionReview) — never `work.`-prefixed.
 :
fi
```
