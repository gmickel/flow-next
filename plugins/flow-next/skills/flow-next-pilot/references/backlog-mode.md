# Backlog mode — the agentic floor scheduler (fn-68)

> **Loaded only when backlog mode is active.** `SKILL.md` / `workflow.md` read this
> file ONLY after `pilot.autonomy` resolves to `backlog` (config `pilot.autonomy`
> > per-run `--backlog` / `--auto`; default `ready` ⇒ this file is never read and
> pilot's behavior is byte-identical to today — R1). The wiring that resolves the
> mode, threads the verdict grammar, and enforces the never-merge / never-author
> invariants lives in `SKILL.md` + `workflow.md` (fn-68.4); **this file is the
> workflow those hooks execute** — the wide dep-ordered selection, the agentic
> triage read, and the spec-first floor.

This is the **agentic heart** of backlog mode. Everything below is **prose the host
agent executes** with its own judgment — it is **NOT a deterministic engine**. The
triage classification (workable / ready-but-thin / needs-spec / blocked /
needs-human) is the **host agent's READ of the spec**, never a flowctl-computed
field, never a completeness scorer, never a regex spec-grader, never a weighted
score, never a second LLM spawned to judge. flowctl supplies **facts**
(`ready --all` eligibility, the decision-log row); the agent supplies the
**judgment**. If you find yourself reaching for a scoring algorithm or a
`triageClass` field, stop — that is the deterministic mistake this whole feature
exists to avoid.

**One smarter tick, not a runner.** Backlog mode is a *wider* single pilot tick: it
enumerates the full open set, dep-orders it, triages the top item, and resolves to
exactly one state-changing terminal. It is **NOT** a daemon, a polling loop, a
trigger handler, a webhook, a cron, or a parallel-worktree fan-out — that standing
control-plane role is mergefoundry / flow-swarm's (fn-94/99), not flow-next's. The
host `/loop` (Claude Code) or `/goal` (Claude Code / Codex) owns repetition; one
invocation advances one item by one stage. The autonomous span runs only from a
**workable spec → draft PR (`make-pr`)** — never authoring upstream, never merging
downstream (land owns the merge — R6).

---

## How this extends pilot's ready-only tick

Ready-only pilot (`workflow.md` Phase 1 SELECT) two-pass-filters on `status==open`
+ the fn-58 `ready` flag + `depends_on_epics` satisfaction, and emits `NO_WORK`
when none qualify. Backlog mode reuses that wholesale and adds exactly three things,
nothing more:

1. **A second ready source** — a tracker issue at the exact `tracker.readyState`
   counts as promoted, alongside the flow `ready` flag pilot already reads.
2. **Acting on SELECT's skip pile** — the not-ready-but-signalled, the
   dep-unsatisfied, and the spec-less items pilot today silently drops to `NO_WORK`
   are triaged / sequenced / surfaced instead of dropped.
3. **Enumerating tracker issues with no flow spec** — promoted tickets invisible to
   `flowctl specs`, unioned in via the `list-open` op.

A **workable** item routes straight into pilot's **existing** CLASSIFY → DISPATCH →
VERIFY path (`workflow.md` Phase 2–5) unchanged — backlog mode does not re-implement
the pipeline, it only widens what reaches the front of it. There is no new gate and
no spec-authoring engine.

---

## Phase 1 — SELECT (pull-before-scan, wide)

The order is load-bearing. Readiness from the tracker must be **fresh this tick**
(R16), so the pull runs **before** the scan — a human moving a ticket out of
Backlog is reflected on the next tick with no manual sync.

### 1a — Pull/reconcile first (R16)

Run an **unattended** tracker-sync pull/reconcile for linked specs, then continue.
This applies status-sync's existing `tracker.readyState` → local `ready` projection,
so a tracker-promoted spec reads `ready: true` from `flowctl ready --all` in 1b like
any other:

```text
/flow-next:tracker-sync reconcile mode:autonomous     # FLOW_AUTONOMOUS=1
```

- **No-op when the bridge is inactive** (no `tracker.type`, no transport reachable)
  — the reconcile returns a `noop` receipt and selection proceeds on the flow facts
  alone (R17 spec-first floor). Never a block, never a ceremony mid-loop.
- **Autonomous-safe (R14).** The reconcile runs under the autonomy gate
  (tracker-sync Phase 0 recognizes `FLOW_AUTONOMOUS` / `mode:autonomous` after
  fn-68.2): no path reaches `AskUserQuestion`; a genuine conflict / id collision /
  readyState-label failure resolves to `sync defer` (queued for the human), never a
  prompt that would stall the loop.

### 1b — Scan the flow side (facts)

```bash
READY_ALL_JSON="$($FLOWCTL ready --all --json)"
```

`ready --all` returns the flow-side open specs with **deterministic eligibility
facts only** — `{id, ready, readySignal, blockedBy, hasSpec}` (R8):

- `ready` — the local fn-58 `ready` boolean (after 1a's projection, a
  tracker-promoted spec reads `true`).
- `readySignal ∈ {local, none}` — whether the local flag is set. flowctl stores no
  readiness provenance, so it cannot attribute a *tracker-projected* ready; that is
  fine — after the 1a pull the flag is simply `local`.
- `blockedBy` — the unsatisfied `depends_on_epics` (the flow dep edges, 1d).
- `hasSpec` — whether a spec file exists.

flowctl returns **no** `triageClass` — *thin / ambiguous / needs-spec / needs-human*
is the agent's read in Phase 2, never a flowctl field.

### 1c — Union the tracker side (`list-open`)

Union in the **tracker-only** promoted issues that have no flow spec — tickets a
human promoted on the board but never `capture`/`interview`'d into a spec, invisible
to `flowctl specs`. flowctl has **no** tracker transport (architecture rule — it must
not grow one), so the skill supplies this half via tracker-sync's transport-blind
named op:

```text
/flow-next:tracker-sync list-open mode:autonomous
```

- It enumerates open issues at the **exact** `tracker.readyState` (the promoted lane
  — the same explicit signal as the flow `ready` flag), via the `listOpenIssues`
  adapter method. Returns normalized `issue[]` (`{id, identifier, title, status,
  labels, url}`) — **transport-blind**: backlog mode reads the struct and never
  branches on tracker type (Linear / GitHub / GitLab).
- **`tracker.readyState` unset ⇒ `list-open` no-ops** (returns `[]` + a note): no
  promoted lane exists to filter on, so backlog mode runs the **flow-ready specs
  only**. The flow `ready` flag needs no tracker (R17). Same floor when no transport
  is reachable.
- A tracker-only ticket is one with **no linked flow spec** — decided
  authoritatively by the **local sync state** (the tracker-ids the skill recorded
  as linked), NOT by the absence of a `flow:<id>` label (the label is a
  corroborating hint only; a bounded/truncated label set is never read as
  "unlinked"). A linked issue already shows up on the flow side via 1b, so **de-dup
  by tracker id** (the sync-state link) when unioning — the `flow:<id>` label is a
  fallback hint, never the sole test — to avoid scanning the same item twice.

The merged candidate set = the flow specs (1b) ∪ the tracker-only issues (1c).

### 1d — Skip parked subjects (R7/R15)

**Skip any candidate carrying a `status=open` parked question** — it was already
surfaced and is waiting on a human; re-picking it every tick is exactly the nagging
R3 forbids. Check the parked home that applies to the item:

- **Spec-backed** — scan the spec's `## Open Questions` for a
  `<!-- flow-next:question id=… status=open -->` anchor.
- **Tracker-only** (no spec) — scan the tracker comments (from the `list-open` /
  `listComments` read) for a `flow-next:question id=… status=open` anchor with **no**
  matching `<!-- flow-next:answer id=… -->`. The parked state lives in the tracker;
  there is no spec to anchor in.

An item whose anchor has flipped to `status=answered` (a human edited the spec
anchor, or the answer round-trip matched a tracker reply by `id` — tracker-sync
steps.md Phase 7) is **no longer parked**: it re-enters the candidate set and is
re-triaged this tick (R7 — an answered question lets the next tick proceed).

### 1e — Dep-order the survivors (reuse the topo-sort — NO new graph engine)

Order the candidates so a blocker is always offered before the thing it blocks. The
edges come from **two** sources and feed **one** existing sorter:

- **Flow deps** — `blockedBy` from `ready --all` (1b). An edge `A blockedBy B`.
- **Tracker deps** — these are **NOT** in the `issue` struct (`list-open` returns
  issue-only). For each **tracker** candidate, read its relations via the
  **`list-relations`** named op and normalize the `relation[]` edges (`from` =
  blocked, `to` = blocker):

  ```text
  /flow-next:tracker-sync list-relations <tracker-id> mode:autonomous   # per tracker issue
  ```

  (This routes through the `listIssueRelations` adapter method from fn-64 over the
  same transport-blind ladder — backlog mode never calls a tracker API directly. It
  is a **READ** — on pilot's dispatch allowlist, never a merge/write. No-ops when the
  bridge is inactive or the issue has no relations.)

Feed **both** edge sets — the flow `blockedBy` edges and the normalized tracker
`relation[]` edges — into the **flow-next-deps jq topo-sort** (the phase-assignment
`reduce` in [`../../flow-next-deps/SKILL.md`](../../flow-next-deps/SKILL.md) Step 3).
**Reuse it — build no new graph engine.** Phase 1 of that algorithm is the
ready-now set; pick from it.

- **A cycle / deadlock is never spun on.** If the topo-sort cannot place a candidate
  because its dep chain is circular (or a dep is itself parked / unsatisfiable),
  that candidate routes to `ASKED` (surface the unresolvable dependency as an async
  question — Phase 3) or `BLOCKED` (Phase 2's dep-unsatisfied branch), never picked
  again-and-again. Selection must terminate every tick.

### 1f — Pick the top actionable item

The **first** candidate in dep-order that (a) carries an explicit readiness signal
and (b) is not parked becomes the item to triage in Phase 2. **A signalled item is
selectable even when a dependency is unsatisfied** — it is picked and routed to
`BLOCKED` in Phase 2's `dep-unsatisfied` branch, which **surfaces the dep wait** as a
state-changing terminal (R10 — a live triage never ends on a no-op). Dep-blocked is
**not** a reason to skip selection; only a `status=open` **parked** question
(already surfaced, waiting on a human — 1d) removes a candidate from the pool.

### 1g — Apply pilot's ready-mode claim / collision / re-bless checks

Backlog SELECT **reuses the SAME checks as ready-mode SELECT** (`workflow.md` Phase 1
Pass 2) on the picked candidate — it does not skip them. Phase 2 CLASSIFY (and its
stale-claim `NEEDS_HUMAN` row) **assumes other-actor `in_progress` claims were
already skipped at SELECT**, so they must run here, before triage:

- **Collision avoidance** — for a spec-backed candidate, any task `in_progress` and
  assigned to **another** actor makes the candidate non-selectable: drop it and take
  the next dep-ordered candidate (record `claimed by other actor` in the skip table).
  Resolve the actor exactly as `flowctl.get_actor()` does. (A tracker-only item has
  no flow tasks — this is a no-op for it.)
- **Strikes / re-bless** — a `count >= 2` ledger entry on a candidate that is **ready
  again** has been human re-blessed: clear the entry and treat the spec as fresh
  (skip the write under `--dry-run`, report would-clear instead).
- **No gh here** — PR state belongs only to the all-done CLASSIFY branch.

Reuse pilot's existing ready-mode checks — do not reinvent them. (The dependency
half is already covered by 1e's topo-sort + the `dep-unsatisfied` triage class.)

So the **only** items excluded from selection are the silently-skipped unsignalled
items (never in the pool), the parked-and-unanswered ones (1d), and any candidate an
**other actor is mid-flight on** (1g collision). Fall through to pilot's existing
terminal split **only when the pool is genuinely empty of a selectable, reportable
candidate**:

- **`NO_WORK`** — no signalled, unparked candidate exists at all (and no dep wait to
  report). A signalled-but-dep-blocked candidate is *selectable*, so its presence
  yields `BLOCKED`, never `NO_WORK`.
- **`DEFERRED_TO_LAND`** — every all-done candidate has an open PR (verbatim from
  `workflow.md` Phase 6).

Backlog mode adds neither verdict and changes neither — it only ensures a
ready-but-blocked item reaches `BLOCKED` (Phase 2) rather than collapsing into
`NO_WORK`.

---

## Phase 2 — TRIAGE (the host agent's read — R3, R8)

Triage is **judgment, not arithmetic**. Read the selected item — its spec body (or,
tracker-only, the issue title + body), its readiness signal, its deps — and classify
it. The classification is **your read**; there is no flowctl field, no score, no
regex grader, no second model. Classify by the **explicit readiness signal FIRST**,
then by your reading of whether the spec is actually workable.

**Unready items are skipped silently.** An item with **no** explicit readiness signal
(neither the fn-58 flow `ready` flag set, nor the tracker status at the exact
`tracker.readyState`) is **never worked, never asked, never nagged**. The human
promotes it by setting ready / dragging the ticket out of Backlog — promoting *is*
the consent act. Backlog mode does not gatekeep raw ideas and does not nag every
un-promoted item; it simply moves on. (Selection in 1f already filters to signalled
items, so a silent skip here is the rare case of an item that lost its signal between
scan and triage.)

For a **signalled** item, route it to exactly one class. **First match wins — and `dep-unsatisfied` is evaluated BEFORE `workable`:** a signalled item carrying an unsatisfied (acyclic) blocker is a dep-wait, never a workable advance, so it surfaces the wait (`BLOCKED`) rather than slipping into CLASSIFY/DISPATCH (1f selects it precisely so the wait gets surfaced — R10):

| Class | The agent's read | Route |
|---|---|---|
| **needs-spec** | a **tracker-only** promoted item — no flow spec exists at all | **`ask` via the tracker comment ALONE** (Phase 3) — surface "run capture/interview"; **never a spec stub** |
| **dep-unsatisfied** | signal present, but a blocker (flow or tracker) is not yet done | **`BLOCKED <id> by <dep>`** — a state-changing terminal that **surfaces the dep wait** (never `NO_WORK` — the item was selectable in 1f); the topo-sort offers the blocker first on a later tick. A circular/unsatisfiable dep routes to `ASKED` instead (1e) |
| **workable** | signal present, **deps satisfied**, AND the spec is complete enough to act on (clear AC / R-IDs, an actionable next stage) | **advance** — hand to pilot's existing CLASSIFY (`workflow.md` Phase 2); it advances exactly one stage (`plan → plan-review → work → [qa] → make-pr`) |
| **ready-but-thin / ambiguous** | signal present, deps satisfied, but the spec is missing, a stub, or too thin/ambiguous to act on safely | **`ask`** (Phase 3) — kick back the gap; **never build, never auto-author** |
| **needs-human** | signal present, deps satisfied, spec exists, but a genuine decision needs a person (conflicting AC, a real design fork) | **`ask`** (Phase 3) |

**The completeness read may only WITHHOLD, never FORCE.** A promoted-but-thin item is
kicked back with a question (`ask`) — it is **never** built into a slop PR. But the
read **never overrides an explicit ready signal to *force* work** on an item the
human did not promote, and **never sets the ready flag itself**, and **never
promotes** on its own reading of the prose. The signal gates eligibility; the
completeness read is a one-way safety net that can only hold work back, never start
it.

**`needs-spec` is always a *promoted* item missing a workable spec** — never an
un-promoted backlog idea (that is silently skipped, above). A tracker-only promoted
item **always** triages to `needs-spec`: there is no flow spec, so there is nothing
to advance — the only correct action is to surface the gap (Phase 3, tracker comment
alone).

A **live** triage always resolves to a **state-changing** terminal — `ADVANCED`
(workable → advanced a stage), `ASKED` (thin / needs-spec / needs-human → parked),
`BLOCKED` (dep-unsatisfied), or `NEEDS_HUMAN` (a crash-class condition). It never
ends on a no-op `TRIAGED` line in a live tick, so an item can never re-select
forever. (`TRIAGED <id> <class>` is diagnostic / dry-run only — emitted under a
triage-only inspection, never as a live terminal. The verdict grammar itself is
owned by fn-68.4.)

The `dep-unsatisfied` → `BLOCKED` terminal is a **dep-wait surface, NOT a strike**:
it records no strike, never unreadies the spec, and emits its own `blocked`
decision-log row — its concrete verdict-line + `pilot-log` template live in
`workflow.md` Phase 6 ("Backlog-mode dep-wait `BLOCKED` terminal"), distinct from
the strike-based `BLOCKED`.

---

## Phase 3 — ASK (the async question valve — surface, never block)

When triage cannot safely proceed (ready-but-thin, needs-spec, needs-human), park
the item behind an **async** question and resolve the tick to `ASKED`. **Never ask
interactively** — `AskUserQuestion` is forbidden on the tick path; the human answers
later, on their own time, via the spec or the tracker.

Backlog mode **does not author specs.** Spec authoring (`capture`,
conversation→spec; `interview`, interactive Q&A) is human-gated and upstream. A
ticket without a workable spec is **surfaced as a gap** — "run `/flow-next:capture`
or `/flow-next:interview`" — **never auto-written**. An agent inventing scope from a
one-line ticket is exactly the slop the valve exists to prevent.

The question is posted via tracker-sync's transport-blind `question` op, which owns
the stable-anchor authoring, the comments-sync dedup, and the answer round-trip
(tracker-sync steps.md Phase 7 — backlog mode invokes it, never re-implements it):

```text
/flow-next:tracker-sync question <spec-id | tracker-id> mode:autonomous
```

Where the question parks depends on whether a spec exists:

- **Spec-backed** (`question <spec-id>`) — the durable parked state lives in the
  spec's `## Open Questions` behind the `<!-- flow-next:question id=… status=open -->`
  anchor (the floor), AND it is mirrored as a tracker comment when the bridge is
  active. The op writes both.
- **Tracker-only** (`question <tracker-id>`, a promoted ticket with no flow spec) —
  there is no spec to anchor in, so the question lives in the **tracker comment
  ALONE**. The surfaced gap is always *"this promoted ticket has no flow spec — run
  `/flow-next:capture` or `/flow-next:interview`"*. **Backlog mode never writes a
  spec stub** (that is the forbidden authoring). Its parked/answered state lives in
  the tracker (the `status=open` anchor + a matching `<!-- flow-next:answer id=… -->`,
  detected by scanning the issue comments) — **no spec import/flip happens until
  capture/interview later creates a spec.**

**Idempotent (R7/R15).** Re-triaging the same blocked subject computes the **same**
anchor `id` (the hash covers stable fields only — `subjectId` + blocked-stage +
`reasonCode` + `questionSlug`; the free prose is outside it), so comments-sync's
marker dedup finds the existing comment and **skips the re-post**. A re-triage never
duplicates a question. An **answered** question (Phase 1d) lets the next tick
re-triage and proceed.

**Spec-first floor (R17).** When **no transport is reachable**, the question is
written to the spec's `## Open Questions` **only** (when a spec exists), plus a
one-line "enable tracker-sync to mirror" note — **never a block**. A tracker-only
item with no transport has nowhere to park; that degrades to a `NEEDS_HUMAN` surface
(the gap cannot be recorded), never a silent drop. The loop always works with zero
trackers configured — the mirror auto-lights per detected transport.

The terminal for a parked item is `ASKED <id> (<n>)` — a **durable** park that set
the `status=open` anchor so Phase 1d skips it next tick (the verdict grammar +
durable-park semantics are owned by fn-68.4).

---

## Full-auto default (R5) + the optional force-gate

**Full-auto by default.** A **workable**, **dep-clear**, **unambiguous** item is
selected-and-advanced with **no pre-gate** — the agent never sets the ready flag
itself and never asks before acting on a clean item. This is the point of backlog
mode: the human's promotion (ready flag / board move) is the consent; everything
downstream of a workable spec runs unattended to the draft PR.

**Optional force-gate.** The sibling config key **`pilot.gateClasses: [<class>…]`**
(an array — NOT `pilot.autonomy.gate`; a scalar and an object cannot share the
`pilot.autonomy` dot-path) force-surfaces named classes before action. When the
selected item matches a configured gate class (e.g. `risky`, `prod-config`), route
it to `ask` (Phase 3) instead of advancing — even when it is otherwise workable. An
empty / unset `gateClasses` (the default) gates nothing; full-auto is unconditional.

```bash
# Tolerate BOTH a JSON array (`["risky"]`) AND a scalar set via the CLI —
# `flowctl config set pilot.gateClasses risky` persists the bare string "risky",
# which the array-only `.value[]?` would silently drop.
GATE_CLASSES="$($FLOWCTL config get pilot.gateClasses --json | jq -r '(.value // empty) | if type=="array" then .[] elif type=="string" then (if startswith("[") then (fromjson | .[]?) else . end) else empty end' 2>/dev/null)"
```

(Matching an item to a gate class is the agent's read of the item, like triage —
no scorer. The classes are stable slugs the operator chose; you decide whether the
selected item belongs to one.)

---

## Transport-blind, multi-tracker (R13)

Backlog mode's tracker surface is **only** the three transport-blind named ops —
`list-open` (enumerate the promoted lane), `list-relations` (READ one issue's dep
edges via `listIssueRelations`), and `question` (park a gap). All three are on
pilot's dispatch allowlist; `list-open` / `list-relations` are read-only, `question`
posts a comment. It calls **no** tracker-specific API and **never** branches on
tracker type; the active adapter (from `tracker.type`) supplies the wire query behind
the normalized interface.

- **Ships on Linear, GitHub + GitLab** — the three adapters that implement
  `listOpenIssues` / `listIssueRelations` / the comment ops (fn-68.2 / fn-64 / fn-69).
  On **GitLab** the adapter derives the project-local `iid` its issue API paths require
  from the issue's normalized **`identifier`** (`<project>#<iid>`) — never the global
  id (gitlab.md § identity / fetchIssue). That identifier is available in **both**
  backlog cases, so no spec is required: a **spec-backed** issue carries it as the
  stored `tracker.identifier`, and a **tracker-only** issue (one `list-open` enumerated
  with no flow spec) carries it in the `listOpenIssues` normalized `issue.identifier`.
  The normalized op signature is identical for every tracker; the iid derivation is an
  adapter-internal concern, so pilot still branches on **no** tracker type.
- **Jira (fn-70)** inherits the same contract once its adapter
  ships — backlog mode layers coverage on with **zero** pilot changes (no
  tracker-specific code lives here to update).
- **Zero-setup (R17).** Each tracker resolves via tracker-sync's discovery-ceremony
  probe ladder, preferring auth the company already has (`gh`/`glab` CLI session,
  registered Linear/Atlassian MCP, or a CI/REST env token) — no flow-next-specific
  provisioning, OAuth app, webhook, or special config. The spec-first floor
  guarantees the loop works with **zero** trackers configured.

---

## What backlog mode must NOT do (load-bearing boundaries)

- **No daemon / polling loop / trigger / webhook / cron / parallel-worktree.** One
  smarter tick — the host `/loop` · `/goal` owns repetition. The standing
  control-plane role (scheduler, cloud environments, triggers, multi-agent at
  scale) is mergefoundry / flow-swarm's (fn-94/99), not flow-next's. If this file
  ever starts describing a standing process, that is drift — remove it.
- **Never authors a spec.** `capture`/`interview` are human-gated; a needs-spec gap
  is surfaced, never auto-written (may augment an obvious blank in an *existing*
  spec only — never create one). The span is *workable spec → draft PR*, not
  *ticket → draft PR*.
- **Never merges / never invokes land.** The terminus is `make-pr` (draft). Merge
  stays human-gated; land owns it (R6).
- **Never sets the ready flag / never promotes.** Readiness is the human's explicit
  signal; the agent's completeness read can only *withhold*, never *force* or
  *promote*.
- **No deterministic triage.** No completeness scorer, no regex spec-grader, no
  weighted scoring, no flowctl `triageClass` field, no second LLM spawned to judge.
  Triage is the host agent's read; flowctl supplies facts and a log row only.
- **No new graph engine.** Dep-ordering reuses the flow-next-deps jq topo-sort; a
  cycle is surfaced (`ASKED`/`BLOCKED`), never spun on.
- **Codex mirror is regenerated in fn-68.5** (a SEPARATE task) — keep this file
  Claude-native (`AskUserQuestion`, `Task`); do NOT regenerate the mirror here.
