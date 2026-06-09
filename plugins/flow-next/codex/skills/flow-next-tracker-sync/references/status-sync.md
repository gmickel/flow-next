# Status / metadata reconciliation — per-field who-wins (R7)

The status-sync reconcile body behind the [../steps.md](../steps.md) `push` /
`pull` / `reconcile` hooks (`setStatus` / `readStatus`). It reconciles **status,
priority, and metadata two-way** with **explicit, per-field who-wins rules** — NOT
one global "tracker always wins" or "flow always wins". It operates ONLY on the
normalized `status` / `issue` structs ([adapter-interface.md](adapter-interface.md));
the transport ([linear-ladder.md](linear-ladder.md)) is the firewall, this file is
the reconciliation.

> **This is policy, not a deterministic merge engine.** The who-wins table below is
> a fixed, mechanical per-field policy — that part *is* deterministic (a status
> field has a small, enumerable vocabulary, unlike free-form body prose). The
> agentic judgment lives in the **deadlock fallback** (a `tracker-done × flow-in-
> progress` collision routes through the R1 tiebreak, which in `always-ask` mode is
> a human/queue decision) and in the **unmapped-state** path (warn + surface, never
> guess a meaning). flowctl owns the state write (`sync set-last-synced`,
> `sync receipt`, `sync defer`); this file owns the policy + the deadlock judgment.

> **Live-verification status (this environment).** Calling Linear's `setStatus`
> against a real workspace (resolving a normalized status → the team's concrete
> `stateId`) needs live credentials — unavailable in the build environment. The
> **strictly-live `setStatus` round-trip is deferred to the post-PR smoke-testing
> phase** the maintainer drives (same posture as the
> [linear-ladder.md](linear-ladder.md) round-trip spike and
> [body-merge.md](body-merge.md)). Everything else here — the who-wins table, the
> deadlock fallback, the `state.type` ↔ flow-status mapping, the unmapped-state
> warn-and-surface — is a complete, runnable procedure with worked fixtures and
> explicit oracles below, exercisable without a live tracker.

## The two normalized vocabularies this file reconciles between

| Side | Vocabulary | Source |
|---|---|---|
| **flow** | spec: `open` · `done`; task: `todo` · `in_progress` · `blocked` · `done`; plus the spec's `completion_review_status` (`unknown` · `ship` · `needs_work`) | `flowctl.py` `SPEC_STATUS` / `TASK_STATUS` |
| **normalized** (the stable middle) | `backlog` · `planned` · `in-progress` · `in-review` · `done` · `verified` · `deferred` · `wontfix` | [adapter-interface.md](adapter-interface.md) |

The **tracker side** maps its team-specific workflow-state names into the normalized
vocabulary in the adapter ([linear-ladder.md](linear-ladder.md) status table). The
**flow side** maps onto the normalized vocabulary here:

### flow → normalized (what the spec's status *means* on the tracker)

The spec's tracker-facing status is derived from the spec + its tasks (one spec ↔
one issue, R3 — there are no per-task sub-issues):

| flow condition | normalized | Rationale |
|---|---|---|
| spec `open`, **no** task `in_progress`/`done` yet (all `todo`) | `planned` (or `backlog` if no tasks exist) | authored, not started |
| spec `open`, **any** task `in_progress` or some `done` | `in-progress` | work underway |
| spec `done`, `completion_review_status != ship` | `in-review` | implementation complete, awaiting completion review |
| spec `done`, `completion_review_status == ship` | `verified` | completion review shipped |
| spec `done`, no completion-review configured | `done` | terminal, no review gate |

`deferred` / `wontfix` have no native flow status — they only ever arrive **from**
the tracker side and are **surfaced, never auto-applied** (see the who-wins table).
`blocked` tasks do not change the spec-level normalized status (the issue stays
`in-progress`); a blocked note can ride along as a comment (fn-52.5
[comments-sync.md](comments-sync.md)), not a status change.

## The who-wins table — per field, NOT one global rule (R7)

This is the heart of R7. Each row is independent. The reconcile applies them
field-by-field; there is no single winner.

| Field | When flow & tracker disagree | Who wins | Why |
|---|---|---|---|
| status = **terminal** (`done` / `verified` / a closed state) | tracker says terminal | **tracker wins** | the tracker is where humans close work; a PM marking the issue Done is authoritative for closure |
| status = **`in-progress`** (and earlier: `planned` / `backlog`) | flow has moved it to in-progress | **flow wins** | flow drives the agent loop; flow's "work started / planned" is the live truth while work is active |
| **`priority`** | sides differ | **neither — surface to the user** | priority is a human triage signal; the bridge never silently overwrites it |
| status = **`deferred`** / **`wontfix`** (canceled-family) | tracker (or flow) sets it | **neither — surface to the user** | a deliberate human decision to stop; auto-changing it either way loses intent |
| **labels** / other metadata | sides differ | **append-union, surface removals** | additive labels merge; a *removed* label is surfaced (could be intentional) — never silently dropped both ways |

**"Surface to the user"** means: interactive → show the divergence and ask via
`plain-text numbered prompt`; Ralph/autonomous → `sync defer` (queue, never block). It does
**not** mean "pick a side" — the field is left as-is on both sides until a human
decides. This is the R7 "priority + `deferred`/`wontfix` surface to the user, never
auto-changed" guarantee, made mechanical.

### Applying the table (the reconcile loop)

**Evaluation order matters.** The **deadlock check fires FIRST** — before the
terminal-wins and in-progress-wins rules — because the canonical deadlock
(`tracker ∈ {done, verified}` while `flow == in-progress`, or the mirror) satisfies
*both* of those single-field rules at once. If terminal-wins ran first it would
silently auto-close the spec and `conflictTiebreak` would never fire — the exact bug
this ordering prevents. The terminal-vs-active **pair itself is the deadlock
signal**; it does not depend on any stored prior status (flowctl's sync state stores
the merge-base *body* + hashes, not a prior status field — so the check reads only
the two current normalized statuses, which are always available).

```
reconcileStatus(spec, issue):
 flowNorm = flowToNormalized(spec) # table above
 trackerNorm = issue.status.normalized # adapter already mapped it

 if flowNorm == trackerNorm:
 noop (status already agrees) — no setStatus, no spec change

 # ── DEADLOCK CHECK FIRST — terminal on one side, active (in-progress) on the
 # other. This pair matches BOTH the terminal-wins and in-progress-wins rules,
 # so it MUST be caught before either, or it auto-resolves silently. Routes to
 # the R1 conflictTiebreak; never lets a single-field rule win it outright. ──
 elif (trackerNorm ∈ {done, verified} and flowNorm == in-progress)
 OR (flowNorm ∈ {done, verified} and trackerNorm == in-progress):
 # genuine status deadlock (tracker=done × flow=in-progress, simultaneously) →
 # R1 conflictTiebreak fallback (next section). NOT a silent auto-close.

 elif trackerNorm ∈ {done, verified} (terminal, flow NOT in-progress):
 # tracker wins terminal — flow is at backlog/planned/done, so the tracker's
 # closure folds in cleanly (no live in-progress work to contradict it)
 mark the spec done (+ completion_review_status if the tracker says verified)
 # do NOT call setStatus (tracker already terminal)

 elif flowNorm == in-progress and trackerNorm ∈ {backlog, planned}:
 # flow wins in-progress — push flow's progress to the tracker
 setStatus(trackerId, in-progress) [transport — linear-ladder.md]

 elif trackerNorm ∈ {deferred, wontfix} OR priority differs:
 # surface, never auto-change (interactive ask / Ralph queue) — see below

 elif flowNorm ∈ {done, verified} and trackerNorm ∈ {backlog, planned}:
 # flow reached terminal, tracker still pre-active (not in-progress → not a
 # deadlock) — push flow's closure out
 setStatus(trackerId, flowNorm) [transport]

 else:
 # any residual incompatibility the rules above didn't resolve →
 # R1 conflictTiebreak fallback (next section)
```

The deadlock branch deliberately **subsumes** the `tracker-done × flow-in-progress`
case that the terminal-wins rule would otherwise grab — that is the whole point of
putting it first. The `conflictTiebreak` default (`always-ask`) then queues/asks
rather than silently closing a spec whose agent loop is still live; teams that
*want* the tracker's closure to win automatically set `tracker.conflictTiebreak:
tracker-wins`.

A `setStatus` resolves the normalized status → the team's concrete `stateId` via
the config status map ([linear-ladder.md](linear-ladder.md) — MCP
`list_issue_statuses` / GraphQL `workflowStates`). A `stateId` not belonging to the
team ⇒ the adapter returns `errored`; the reconcile emits an `errored` receipt and
does **not** advance state (no `lastSyncedAt`) — same no-corrupt contract as the
body merge.

## Status deadlock → R1 `conflictTiebreak` fallback (R7)

A **status deadlock** is the one case the per-field table can't resolve cleanly:
the two sides assert *incompatible terminal-vs-active* states at the same sync point
— the canonical case is **tracker `done` simultaneously with flow `in-progress`** (a
PM closed the issue while the agent loop is still running, or vice versa: flow `done`
while the tracker reopened to `in-progress`). The terminal rule says "tracker wins
terminal" but the in-progress rule says "flow wins in-progress" — they collide. This
is not a field the bridge silently overwrites.

**Because both single-field rules match a deadlock at once, the reconcile loop
evaluates the deadlock check FIRST** (see the loop above) — if terminal-wins ran
before it, the deadlock would be silently auto-closed and `conflictTiebreak` would
never fire. The terminal-vs-active **pair itself is the signal**; the check needs no
stored prior status (flowctl persists the merge-base *body* + hashes, not a status
field), so it reads only the two current normalized statuses. The clean
tracker-wins-terminal path (Fixture S-A) applies only when flow is NOT `in-progress`
(flow at `planned`/`backlog`/`done` — no live work to contradict the closure).

Resolution falls back to the **R1 `conflictTiebreak` default**
(`tracker.conflictTiebreak` ∈ `flow-wins | tracker-wins | always-ask`, default
`always-ask` — `flowctl config get tracker.conflictTiebreak`):

| `conflictTiebreak` | Interactive | Ralph / autonomous |
|---|---|---|
| `tracker-wins` | apply the tracker's state to flow (fold `done` into the spec) | same — confident, proceeds |
| `flow-wins` | push flow's state to the tracker (`setStatus`) | same — confident, proceeds |
| `always-ask` (default) | **ask via `plain-text numbered prompt`** — show both states, let the human pick | **`sync defer`** — queue the deadlock, never block (R11) |

"Ask the human" resolves to "**queue** for the human" in autonomous mode (the
deferred-decisions sink) — same policy, surface-dependent delivery, mirroring
fn-51's surface-aware ladder and the body-merge `always-ask × Ralph` rule.

```bash
# Ralph deadlock under always-ask — queue, write no status, advance no state:
$FLOWCTL sync defer "$SPEC_ID" \
 --summary "Status deadlock: tracker=done, flow=in-progress" \
 --suggested "Human picks: close the spec to match the tracker, or reopen the issue to match flow" \
 --reason "status-deadlock"
# ($EVENT = lifecycle event tag from steps.md Phase 0; empty on manual runs.)
$FLOWCTL sync receipt "$SPEC_ID" --status diverged --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
 --note "status deadlock queued (tracker=done × flow=in-progress); no status written, base unchanged"
```

`flow-wins` / `tracker-wins` auto-resolve (still a confident reconcile → proceed +
`sync set-last-synced` + a `merged`/`updated` receipt). Only `always-ask` surfaces.

## Linear `workflowState.type` ↔ flow status mapping (R7) — with unmapped fallback

The adapter maps Linear's **fixed `state.type` taxonomy** (`triage | backlog |
unstarted | started | completed | canceled`) into the normalized vocabulary; this
file is the authoritative who-wins-facing version of that map (the per-rung wire
detail lives in [linear-ladder.md](linear-ladder.md)):

| Linear `state.type` | normalized | flow effect on pull | who-wins |
|---|---|---|---|
| `triage` | `backlog` | spec stays `open`/unstarted | — |
| `backlog` | `backlog` | spec stays `open`/unstarted | — |
| `unstarted` | `planned` | spec stays `open` (planned) | — |
| `started` | `in-progress` | spec `open`, work underway | **flow wins** (flow drives the loop) |
| `completed` | `done` (or `verified` via a "Verified" name-override) | spec → `done` | **tracker wins terminal** |
| `canceled` | `wontfix` (or `deferred` via a name-override) | **surface — do NOT auto-change** | surface to user |

> `triage` is Linear's pre-backlog state; it maps to `backlog` for who-wins purposes
> (both are "not yet planned"). The default-config status table in
> [linear-ladder.md](linear-ladder.md) lists the five core types; `triage` folds into
> `backlog` here so the who-wins logic sees a single "not-started" bucket.

### Unmapped / custom state — never crash, warn + surface

A team can define a **custom workflow state** whose `state.type` is one of the six
fixed types (so it always normalizes) but whose **name** carries meaning the default
map misses — e.g. a `completed`-type state literally named "Verified" (→ should be
normalized `verified`, not `done`), or a `canceled`-type "Won't Fix" vs "Duplicate".
The `tracker.perTracker.statusMap` config name-override handles the *known* ones.

For a state the bridge genuinely **cannot map** (a name-override the config doesn't
have, or — defensively — a `state.type` value Linear adds in a future schema version
that isn't in the fixed six), the rule is **warn + surface, never guess and never
crash**:

```
normalizeTrackerStatus(state):
 if state.type ∈ {the six fixed types}:
 base = defaultMap[state.type] # table above
 # apply a config name-override if one exists for this state name:
 return statusMap.get(state.name, base)
 else:
 # an unknown type (future Linear schema) — do NOT guess a flow effect:
 warn("unmapped tracker state '<name>' (type '<type>') — surfacing, not auto-applying")
 surface to the user (interactive ask / Ralph sync defer)
 return UNMAPPED # treated like deferred/wontfix: never auto-change flow
```

An `UNMAPPED` status is treated exactly like `deferred`/`wontfix`: **surfaced, never
auto-applied to flow, never used to drive `setStatus`**. The reconcile continues for
every *other* field (body, comments, priority) — one unmapped status never aborts
the run.

```bash
# Unmapped state — surface it, reconcile the rest, never crash:
$FLOWCTL sync defer "$SPEC_ID" \
 --summary "Unmapped tracker state 'Pending Legal' (type 'started') — name not in statusMap" \
 --suggested "Add a tracker.perTracker.statusMap override, or confirm it means in-progress" \
 --reason "unmapped-state"
```

## Worked fixtures (runnable without a live tracker)

Each fixture is a flow state + a tracker `status` struct + the expected reconcile
outcome — the oracles for R7, exercisable by the host agent reading them (no live
Linear; the live `setStatus` is the smoke phase).

### Fixture S-A — tracker wins terminal (R7 headline)

**Flow:** spec `open`, all tasks still `todo` → flow-normalized `planned` (no live
in-progress work — so this is NOT a deadlock).
**Tracker:** `status.normalized = "done"` (PM marked the issue Done).

**Expected:** the deadlock check fails (flow is `planned`, not `in-progress`) →
tracker wins terminal → mark the spec `done`; do **not** call `setStatus` (the
tracker is already terminal). No `setStatus` to push back.

**Oracle:** the spec moves to `done` and **no** `setStatus` call is made. PASS iff
the tracker's closure folds into flow and flow does not "fight back" by re-opening
the issue. (Contrast S-E: had flow been `in-progress`, this would be a deadlock, not
a clean tracker-wins.)

### Fixture S-B — flow wins in-progress (R7 headline)

**Flow:** spec `open`, a task just claimed → flow-normalized `in-progress`.
**Tracker:** `status.normalized = "planned"` (still in the backlog on the board).

**Expected:** flow wins in-progress → `setStatus(trackerId, in-progress)` so the
board reflects that work has started. The spec is unchanged.

**Oracle:** exactly one `setStatus(in-progress)` call; the spec stays `open`. PASS
iff flow's live progress propagates to the tracker.

### Fixture S-C — priority surfaced, never auto-changed (R7)

**Flow:** the spec has no notion of priority (flow priority is `null`).
**Tracker:** `issue.priority = "Urgent"`, and on a later sync a human lowered it to
`"Medium"`.

**Expected:** the priority change is **surfaced** (interactive ask / Ralph
`sync defer`) — the bridge writes **no** priority on either side.

**Oracle:** zero priority writes; one surfaced/queued entry naming the priority
change. PASS iff priority is never auto-changed.

### Fixture S-D — `wontfix`/`deferred` surfaced, never auto-applied (R7)

**Flow:** spec `open`, task `in_progress` → `in-progress`.
**Tracker:** `status.normalized = "wontfix"` (a `canceled`-type state — the PM
cancelled the issue).

**Expected:** `wontfix` is **surfaced, never auto-applied** — the spec is NOT
silently closed/cancelled (cancelling live in-progress work is a human decision).
Surface (ask / queue); reconcile the rest of the fields normally.

**Oracle:** the spec is **not** auto-closed; one surfaced/queued entry. PASS iff the
cancel intent reaches a human instead of silently killing the spec.

### Fixture S-E — status deadlock → `conflictTiebreak` (R7)

**Flow:** spec `open` with a task `in_progress` → `in-progress` (live agent loop
running).
**Tracker:** `status.normalized = "done"` (the PM closed the issue). Terminal on the
tracker side, active on the flow side — the canonical deadlock pair.

This is the canonical deadlock (terminal-vs-in-progress collision). Because the
deadlock check fires **first** in the reconcile loop (before terminal-wins), it is
NOT auto-closed by the tracker-wins-terminal rule — it resolves via
`tracker.conflictTiebreak`:
- `always-ask` (default) → **interactive ask** / **Ralph `sync defer`** (queue,
 `diverged` receipt — see the `sync defer` block above). PASS iff exactly one
 scoped status deadlock is surfaced and **no** status is written.
- `tracker-wins` → fold `done` into the spec (confident → `set-last-synced` +
 `merged` receipt). PASS iff the spec closes and state advances.
- `flow-wins` → `setStatus(in-progress)` (confident → advance). PASS iff the board
 reopens and state advances.

### Fixture S-F — unmapped custom state, warn + surface (R7)

**Tracker:** a custom workflow state named `"Pending Legal"` with a `state.type`
the config `statusMap` has no override for and that isn't in the default name map.

**Expected:** `warn` + **surface** (`sync defer --reason unmapped-state`); the status
field is treated like `deferred` (never auto-applied), and **every other field still
reconciles** — the run does **not** crash or abort.

**Oracle:** a warning is logged, one `unmapped-state` entry is surfaced, the body /
comments reconcile proceeds, and no `setStatus` is driven from the unmapped status.
PASS iff no crash and the rest of the sync completes.

## Boundaries

- **This is the status/metadata layer, not the body merge or the transport.** The
 3-way body merge is [body-merge.md](body-merge.md) (fn-52.4); the transport
 (`setStatus`/`readStatus` wire detail) is [linear-ladder.md](linear-ladder.md)
 (fn-52.3) / the GitHub adapter (fn-52.7). This file consumes the normalized
 `status` struct and applies the per-field policy.
- **Per-field who-wins — never one global rule.** Terminal → tracker; in-progress →
 flow; priority + `deferred`/`wontfix` + unmapped → surface, never auto-change.
- **Status is never silently overwritten on a deadlock** — it falls back to the R1
 `conflictTiebreak`; `always-ask` queues in Ralph, prompts interactively.
- **State advances only on a successful reconcile.** A `setStatus` error, an
 unmapped state surfaced, or a queued deadlock does NOT advance `lastSyncedAt`.
