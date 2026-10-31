# Backlog mode - the agentic floor scheduler

> **Loaded only when backlog mode is active.** `auto.md` (the `flow --auto`
> workflow) reads this file ONLY after `pilot.autonomy` resolves to `backlog`
> (config `pilot.autonomy`, or the per-run `--backlog` flag; default `ready`
> means this file is never read and the ready-mode run is byte-identical). The
> wiring that resolves the mode, threads the verdict grammar, and enforces the
> landing-authority / never-author invariants lives in `auto.md`; **this file is the
> workflow those hooks execute**: the wide dep-ordered selection, the agentic
> triage read, and the spec-first floor.

The host classifies backlog items using `ready --all` eligibility facts and spec content; flowctl stores eligibility facts and decision-log rows.

Backlog mode selects one dependency-ordered item, triages it, and drives it through the hop loop. The next invocation selects the next item.

---

## Backlog-only verdict grammar

Backlog mode extends the common `auto.md` grammar with `ASKED`:

```text
PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"
```

Stage values add `triage` / `ask` to the common set.

- **`ASKED <id> (<n>)`** - a **durable park**. The `ask` stage wrote a
  `status=open` question anchor (spec `## Open Questions` for a spec-backed item,
  or the tracker comment alone for a tracker-only item), so the next run's SELECT
  skips this subject. `<n>` is the count of open questions surfaced. Stage = `ask`.
- **`ADVANCED <id> <stage>`** and **`BLOCKED <id> by <dep>`** - reused unchanged
  (`BLOCKED` here is the ready-but-dep-unsatisfied state-changing dep-wait surface).
- **`NO_WORK` and `DEFERRED_TO_LAND` stay VERBATIM** - drivers grep
  `DEFERRED_TO_LAND` to route an all-done-with-open-PR spec to
  `$flow-next-land`, and `/goal` / `/loop` stop clauses key on `NO_WORK`.
  Coalescing either into generic idle breaks the land hand-off or loop stop.
- **No `PROMOTED` verb** - the agent never sets the ready flag; promotion is the
  human's board act.

**`TRIAGED <id> <class>` is DIAGNOSTIC / dry-run ONLY:**

- **Live backlog grammar** (no `--explain`): `ADVANCED | ASKED | NO_WORK |
  DEFERRED_TO_LAND | BLOCKED | NEEDS_HUMAN`. **`TRIAGED` is NOT a live terminal.**
  A live triage always resolves to a state-changing terminal; it MUST NOT end on a
  bare `TRIAGED` no-op line.
- **Explain-only grammar** (`--explain`, or its one-release alias `--dry-run`): adds
  `TRIAGED <id> <class>` as the diagnostic terminal. The run classifies and stops,
  dispatching nothing and parking nothing. A `/loop` / `/goal` driver never runs
  `--explain`.

---

## Backlog additions to the Forbidden list

These extend `auto.md`'s Forbidden list for a backlog run.

- In backlog mode, ambiguity that needs a person is surfaced **async** via the `ask` stage (`ASKED`), never an interactive `plain-text numbered prompt`.
- **Backlog mode additionally invokes tracker-sync for `reconcile` and `question`; read-only `list-open`, `comment-list`, and `relation-list` run directly through `$FLOWCTL tracker wire`**, never as pipeline stages.
- The question-anchor authoring plus answer round-trip live in tracker-sync; backlog mode invokes them, never re-implements them.
- Never authoring a spec and no merge authority: see [What backlog mode must NOT do](#what-backlog-mode-must-not-do-load-bearing-boundaries).

---

## How this extends the ready-only run

The ready-mode run (`auto.md` Phase 1 SELECT) filters on `status==open`
+ the `ready` flag + `depends_on_epics` satisfaction, and emits `NO_WORK`
when none qualify. Backlog mode reuses that wholesale and adds exactly three things,
nothing more:

1. **A second ready source** - a tracker issue at the exact `tracker.readyState`
   counts as promoted, alongside the flow `ready` flag ready mode already reads.
2. **Acting on SELECT's skip pile** - the not-ready-but-signalled, the
   dep-unsatisfied, and the spec-less items ready mode silently drops to `NO_WORK`
   are triaged / sequenced / surfaced instead of dropped.
3. **Enumerating tracker issues with no flow spec** - promoted tickets invisible to
   `flowctl specs`, unioned in via the `list-open` op.

For a workable item, continue at `auto.md` Phase 2.

---

## Phase 1 - SELECT (pull-before-scan, wide)

The order is load-bearing. Readiness from the tracker must be **fresh this run**
so the pull runs **before** the scan - a human moving a ticket out of
Backlog is reflected on the next run with no manual sync.

### 1a - Pull/reconcile first

Run an **unattended** tracker-sync pull/reconcile for linked specs, then continue.
This applies status-sync's existing `tracker.readyState` → local `ready` projection,
so a tracker-promoted spec reads `ready: true` from `flowctl ready --all` in 1b like
any other:

```text
$flow-next-tracker-sync reconcile mode:autonomous     # FLOW_AUTONOMOUS=1
```

- **No-op when the bridge is inactive** (no `tracker.type`, no transport reachable)
  - the reconcile returns a `noop` receipt and selection proceeds on the flow facts
  alone (the spec-first floor). Never a block, never a ceremony mid-loop.
- **Autonomous-safe.** The reconcile runs under the autonomy gate
  (tracker-sync Phase 0 recognizes `FLOW_AUTONOMOUS` / `mode:autonomous`): no path reaches `plain-text numbered prompt`; a genuine conflict / id collision /
  readyState-label failure resolves to `sync defer` (queued for the human), never a
  prompt that would stall the loop.

### 1b - Scan the flow side (facts)

```bash
READY_ALL_JSON="$($FLOWCTL ready --all --json)"
```

`ready --all` returns the flow-side open specs with **deterministic eligibility
facts only** - `{id, ready, noPlan, readySignal, blockedBy, hasSpec}`:

- `ready` - the local `ready` boolean (after 1a's projection, a
  tracker-promoted spec reads `true`).
- `noPlan` - the spec-level `no_plan` boolean (absent-on-disk reads
  `false`); `true` records the direct route. Never tracker-projected.
- `readySignal ∈ {local, none}` - whether the local flag is set. flowctl stores no
  readiness provenance, so it cannot attribute a *tracker-projected* ready; that is
  fine - after the 1a pull the flag is simply `local`.
- `blockedBy` - the unsatisfied `depends_on_epics` (the flow dep edges, 1d). A
  **chain parent** (an open dependency with every task done and its branch on
  origin) is already excluded here: flowctl's admission gate treats it as
  satisfied, so a chained spec sorts as ready-now in 1e.
- `hasSpec` - whether a spec file exists.

flowctl returns **no** `triageClass` - *thin / ambiguous / needs-spec / needs-human*
is the agent's read in Phase 2, never a flowctl field.

### 1c - Union the tracker side (`list-open`)

Union in the **tracker-only** promoted issues that have no flow spec - tickets a
human promoted on the board but never `capture`/`refine`'d into a spec, invisible
to `flowctl specs`. Read this half directly through
flowctl's deterministic tracker transport:

```text
$FLOWCTL tracker wire list-open --json
```

- It enumerates open issues at the **exact** `tracker.readyState` (the promoted lane
  - the same explicit signal as the flow `ready` flag), via the `listOpenIssues`
  adapter method. Returns normalized `issue[]` (`{id, identifier, title, status,
  labels, url}`) - **provider-neutral**: backlog mode reads the struct and never
  branches on tracker type (Linear / GitHub / GitLab / Jira).
- **`tracker.readyState` unset ⇒ `list-open` no-ops** (returns `[]` + a note): no
  promoted lane exists to filter on, so backlog mode runs the **flow-ready specs
  only**. The flow `ready` flag needs no tracker. Same floor when no transport
  is reachable.
- A tracker-only ticket is one with **no linked flow spec** - decided
  authoritatively by the **local sync state** (the tracker-ids the skill recorded
  as linked), NOT by the absence of a `flow:<id>` label (the label is a
  corroborating hint only; a bounded/truncated label set is never read as
  "unlinked"). A linked issue already shows up on the flow side via 1b, so **de-dup
  by tracker id** (the sync-state link) when unioning - the `flow:<id>` label is a
  fallback hint, never the sole test - to avoid scanning the same item twice.

The merged candidate set = the flow specs (1b) ∪ the tracker-only issues (1c).

### 1d - Skip parked subjects

**Skip any candidate carrying a `status=open` parked question** - it was already
surfaced and is waiting on a human; re-picking it every run is exactly the nagging this mode exists to avoid. Check the parked home that applies to the item:

- **Spec-backed** - scan the spec's `## Open Questions` for a
  `<!-- flow-next:question id=… status=open -->` anchor.
- **Tracker-only** (no spec) - `list-open` returns issues, not comments. Before
  deciding parked state, run `$FLOWCTL tracker wire comment-list --locator "$LOCATOR" --json` exactly once for
  that candidate (`LOCATOR` as built in 1e below). It maps to the normalized `comment-list` wire read. Compare
  matching `flow-next:question` / `flow-next:answer` markers by stable `id` and
  immutable `created_at`: the subject is parked when its latest matching marker
  is a question, and answered when its latest matching marker is an answer.
  This supports repeated rounds (`question → answer → question`) without an old
  answer falsely clearing the new question. The parked state lives in the
  tracker; there is no spec to anchor in.

  A failed or truncated comment listing, or mixed matching markers without
  unambiguous timestamps, fails closed. Do not select that candidate from an
  incomplete history; route the structured error and end `NEEDS_HUMAN` when it
  prevents a safe selection.

An item whose anchor has flipped to `status=answered` (a human edited the spec
anchor, or the answer round-trip matched a tracker reply by `id` - tracker-sync
steps.md Phase 7) is **no longer parked**: it re-enters the candidate set and is
re-triaged this run (an answered question lets the next run proceed).

### 1e - Dep-order the survivors (reuse the topo-sort - NO new graph engine)

Order the candidates so a blocker is always offered before the thing it blocks. The
edges come from **two** sources and feed **one** existing sorter:

- **Flow deps** - `blockedBy` from `ready --all` (1b). An edge `A blockedBy B`.
- **Tracker deps** - these are **NOT** in the `issue` struct (`list-open` returns
  issue-only). For each **tracker** candidate, read its relations via the
  **`list-relations`** named op and normalize the `relation[]` edges (`from` =
  blocked, `to` = blocker):

  ```text
  $FLOWCTL tracker wire relation-list --locator "$LOCATOR" --json   # per tracker issue
  ```

  **`LOCATOR` is JSON, never a bare id:** `{"durable":issue.id,"display":issue.identifier}`
  from the candidate's `list-open` row (a spec-backed candidate uses its stored
  `tracker.id` / `tracker.identifier`); the wire verb rejects a bare identifier. On
  GitLab the adapter indexes `/projects/:id/issues/:iid` from the `<project>#<iid>`
  the display half carries (gitlab.md § identity). On GitHub this read validates the
  issue and returns no dependency edges: parent/sub-issue hierarchy is not
  blocked-by and never feeds the sorter.

  (Backlog mode never calls a tracker API
  directly. It is a **READ** - on the run's dispatch allowlist, never a
  merge/write. It no-ops when the bridge is inactive or the issue has no
  relations. A structured `subtype: truncated` error is a failed read, never a
  partial graph to sort.)

Feed **both** edge sets - the flow `blockedBy` edges and the normalized tracker
`relation[]` edges - into the **flow-next-deps jq topo-sort** (the phase-assignment
`reduce` in [`../../flow-next-deps/SKILL.md`](../../flow-next-deps/SKILL.md) Step 3).
**Reuse it - build no new graph engine.** Phase 1 of that algorithm is the
ready-now set; pick from it.

- **A cycle / deadlock is never spun on.** If the topo-sort cannot place a candidate
  because its dep chain is circular (or a dep is itself parked / unsatisfiable),
  that candidate routes to `ASKED` (surface the unresolvable dependency as an async
  question - Phase 3) or `BLOCKED` (Phase 2's dep-unsatisfied branch), never picked
  again-and-again. Selection must terminate every run.

### 1f - Pick the top actionable item

The **first** candidate in dep-order that (a) carries an explicit readiness signal
and (b) is not parked becomes the item to triage in Phase 2. **A signalled item is
selectable even when a dependency is unsatisfied** - it is picked and routed to
`BLOCKED` in Phase 2's `dep-unsatisfied` branch, which **surfaces the dep wait** as a
state-changing terminal (a live triage never ends on a no-op). Dep-blocked is
**not** a reason to skip selection; only a `status=open` **parked** question
(already surfaced, waiting on a human - 1d) removes a candidate from the pool.

For a **spec-backed** pick with dependencies, the flow-side dependency answer is
`CHAIN_JSON="$($FLOWCTL spec chain "$SUBJECT_ID" --json)"` - the same predicate
ready-mode SELECT applies (auto.md Phase 1's `chain.eligible`; the command is the single
owner of chain eligibility, never re-derived from `show <dep>`). `.eligible == true`
means the flow deps are satisfied (every dependency done, or exactly one open
**chain parent** with all tasks done and its branch on origin - keep `.parent` as
`CHAIN_PARENT` for the verdict prefix); `.eligible == false` is the
`dep-unsatisfied` class with the command's `.reason` as the `<dep>` clause. Tracker
relations keep their existing `list-relations` read.

### 1g - Apply the ready-mode claim / collision / re-bless checks

Backlog SELECT **reuses the SAME checks as ready-mode SELECT** (`auto.md` Phase 1)
on the picked candidate - it does not skip them. Phase 2 CLASSIFY (and its
stale-claim `NEEDS_HUMAN` row) **assumes other-actor `in_progress` claims were
already skipped at SELECT**, so they must run here, before triage:

- **Collision avoidance** - for a spec-backed candidate, any task `in_progress` and
  assigned to **another** actor makes the candidate non-selectable: drop it and take
  the next dep-ordered candidate (record `claimed by other actor` in the skip table).
  Resolve the actor exactly as `flowctl.get_actor()` does. (A tracker-only item has
  no flow tasks - this is a no-op for it.) An own-actor `in_progress` claim is not
  skipped here; it reaches CLASSIFY's resume-consent / stale-claim rows, and
  `flowctl start` refuses it without `--reclaim`, which only the evidence-checked
  resume row licenses - a second run of this actor never resumes by default.
- **Strikes / re-bless** - a `count >= 2` ledger entry on a candidate that is **ready
  again** has been human re-blessed: clear the entry and treat the spec as fresh.
  **BUT NOT under an active `tracker.readyState` projection** - 1a re-projects `ready=true`
  from the board every run, so a projected "ready again" is MECHANICAL, not a human
  re-bless; clearing on it re-dispatches the same failing spec forever (the strike limit,
  defeated). With `tracker.readyState` set, do NOT clear a `count >= 2` strike on
  projection-set ready - keep the candidate struck (skipped) until the human runs
  `flowctl pilot strikes clear <spec-id>`, which is THE recognized human clear under an
  armed `tracker.readyState` (no board move can serve as one: a deliberate re-ready and a
  projection echo are byte-identical in every durable artifact)
  (skip the write under `--dry-run`, report would-clear instead).
- **No gh here** - PR state belongs only to the all-done CLASSIFY branch.

Reuse the existing ready-mode checks - do not reinvent them. (The dependency
half is already covered by 1e's topo-sort + the `dep-unsatisfied` triage class.)

So the **only** items excluded from selection are the silently-skipped unsignalled
items (never in the pool), the parked-and-unanswered ones (1d), and any candidate an
**other actor is mid-flight on** (1g collision). Fall through to the existing
terminal split **only when the pool is genuinely empty of a selectable, reportable
candidate**:

- **`NO_WORK`** - no signalled, unparked candidate exists at all (and no dep wait to
  report). A signalled-but-dep-blocked candidate is *selectable*, so its presence
  yields `BLOCKED`, never `NO_WORK`.

  ```text
  PILOT_VERDICT=NO_WORK spec=- stage=- reason="no signalled, unparked backlog item"
  ```

- **`DEFERRED_TO_LAND`** - every all-done candidate has an open PR (verbatim from
  `auto.md` Phase 6) and no current landing authority. A currently authorized selected item stays selected for the landing handoff.

Backlog mode adds neither verdict and changes neither - it only ensures a
ready-but-blocked item reaches `BLOCKED` (Phase 2) rather than collapsing into
`NO_WORK`.

---

## Phase 1.5 - SELECT (wide, backlog mode only)

**Active only when `PILOT_AUTONOMY=backlog`.** Execute the SELECT workflow in Phase 1 above (1a to 1g); its mechanics are authoritative and single-sourced there. What stays here is the enforcing bash: the explain gate, the guarded dispatches, and the invariants.

**`--explain` is dispatch-free.** An explain backlog run is inspection-only: **it dispatches nothing and mutates nothing**, no readiness projection, no receipts. An explain run that fired a tracker-sync op has broken this. So when `PILOT_DRY_RUN=1`, **skip the tracker-sync `reconcile` (1a) and `list-open` (1c) dispatches entirely** and select from the **flow-side `ready --all` facts alone**; then Phase 1.6 classifies and the run stops with the diagnostic `TRIAGED` line (no `ask`, no pilot-log row). The gate below wraps every Phase 1.5 dispatch:

```bash
DRY="${PILOT_DRY_RUN:-0}"   # 1 => inspection-only: no tracker-sync dispatch, flow-side facts only
```

1. **1a - pull-before-scan** (1a above). **Skipped under `--explain`** (dispatch-free; the explain readiness read is whatever `ready --all` already reflects locally). Otherwise dispatch this fixed, allowlisted read:

   ```bash
   if [ "$DRY" = "0" ]; then
     echo "DISPATCH: $flow-next-tracker-sync reconcile mode:autonomous"
     # -> dispatch: $flow-next-tracker-sync reconcile mode:autonomous   (FLOW_AUTONOMOUS=1; no-op when the bridge is inactive)
   fi
   ```

2. **1b - scan the flow side (facts)** (1b above): `READY_ALL_JSON="$($FLOWCTL ready --all --json)"`.

3. **1c - union the tracker side (`list-open`)** (1c above). **Skipped under `--explain`**; the candidate set is then the flow specs (1b) only. Otherwise dispatch this fixed, allowlisted read:

   ```bash
   if [ "$DRY" = "0" ]; then
     $FLOWCTL tracker wire list-open --json   # no-ops when tracker.readyState unset -> flow-ready specs only)
   fi
   ```

4. **1d - skip parked subjects** (1d above). For every tracker-only candidate, execute the missing comment read before deciding whether its latest question round is parked:

   ```bash
   if [ "$DRY" = "0" ]; then
     echo "DISPATCH: tracker wire comment-list per tracker-only issue"
     # -> dispatch per tracker-only issue: $FLOWCTL tracker wire comment-list --locator "$LOCATOR" --json
     #   LOCATOR = {"durable":issue.id,"display":issue.identifier} from the list-open row.
     # Any error or truncated listing fails closed: do not select from an
     # incomplete question/answer history.
   fi
   ```

5. **1e - dep-order the survivors** (1e above). The tracker relation edges come from the per-issue `list-relations` READ (invariant #1: on the allowlist, never a merge):

   ```bash
   if [ "$DRY" = "0" ]; then
     echo "DISPATCH: tracker wire relation-list per tracker issue"
     # For each TRACKER candidate, read its relations to add the tracker dep edges.
     # -> dispatch per tracker issue: $FLOWCTL tracker wire relation-list --locator "$LOCATOR" --json
     #   LOCATOR = {"durable":issue.id,"display":issue.identifier} from the list-open row
     #   (GitLab indexes /issues/:iid from the <project>#<iid> the display handle carries).
     #   (the listIssueRelations read; no-op/empty when the bridge is inactive or the issue has no relations)
   fi
   ```

   (Under `--explain` there are no tracker candidates, 1c was skipped, so 1e uses the flow `blockedBy` edges only and issues no tracker read; the dispatch above is skipped.) **Invariant #4: a cycle/deadlock is surfaced, never spun on.** When the topo-sort cannot place the chosen candidate because its dep chain is circular or a dep is itself parked/unsatisfiable, set `DEP_DEADLOCK=1` and route it to a state-changing terminal, never fall through to re-pick it next run:

   ```bash
   if [ "${DEP_DEADLOCK:-0}" = "1" ]; then
     # The unresolvable dependency is surfaced as an async question (Phase 3.5 ask -> ASKED).
     # (A plain unsatisfied-but-acyclic dep is NOT a deadlock; it routes to BLOCKED in Phase 1.6.)
     SUBJECT_ID="$DEADLOCK_SUBJECT_ID"; HAS_SPEC="$DEADLOCK_HAS_SPEC"; SPEC_PATH="$DEADLOCK_SPEC_PATH"
     ASK_REASON="unresolvable/circular dependency — $DEADLOCK_DETAIL"
     # -> fall into Phase 3.5 ASK (terminal ASKED). Selection terminates this run.
   fi
   ```

6. **1f - pick the top actionable item** (1f above); it becomes `SUBJECT_ID`, the one item to triage in Phase 1.6.

7. **1g - apply the ready-mode claim / collision / re-bless checks to the picked candidate** (1g above) before triage; Phase 1.6 CLASSIFY assumes other-actor `in_progress` claims were already skipped here. Under `--explain`, write no ledger; report a re-bless entry as would-clear instead.

**Invariant #3 (single item per run) is enforced here.** Selection sets exactly ONE `SUBJECT_ID`; there is no `for item in candidates` advance/park loop downstream. **Assign `SELECTED_SUBJECTS` to the chosen subject** (the single id 1f/1g settled on, or empty when the pool yielded none), resolve `SPEC_PATH` (the spec file path when spec-backed, else **empty** for a tracker-only item, whose `SUBJECT_ID` is the candidate's `list-open` `issue.identifier`, the display handle the downstream `list-relations` / `question` dispatches resolve against, never the opaque global id) and `HAS_SPEC`, then hard-assert the count:

```bash
# SELECTED_SUBJECTS = the chosen subject id; selection yields exactly one (or
# empty when no candidate survived 1f/1g). Assign it from SUBJECT_ID here so the
# single-item guard below counts the REAL selection (an unset var would always
# count 0 and wrongly fall through to NO_WORK even after a subject was picked).
SELECTED_SUBJECTS="${SUBJECT_ID:-}"
SELECTED_COUNT="$(printf '%s\n' "$SELECTED_SUBJECTS" | grep -c . )"
if [ "$SELECTED_COUNT" -gt 1 ]; then
  echo "Evidence: backlog selection yielded $SELECTED_COUNT subjects — single-tick contract violated"
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="backlog single-tick — selection must pick exactly one item"'
  exit 1
fi
```

A `SELECTED_COUNT` of 0 (empty `SUBJECT_ID`, no candidate survived 1f/1g) falls through to the terminal split at the end of 1g (`NO_WORK`); exactly 1 proceeds to Phase 1.6.

Done when: `SELECTED_COUNT` is 0 or 1, `SPEC_PATH` / `HAS_SPEC` are resolved for the picked subject, and no dispatch happened under `--explain`.

---

## Phase 2 - TRIAGE (the host agent's read)

Check the item's explicit readiness signal first, then classify its spec or issue content and dependencies.

**Unready items are skipped silently.** An item with **no** explicit readiness signal
(neither the flow `ready` flag set, nor the tracker status at the exact
`tracker.readyState`) is **never worked, never asked, never nagged**. The human
promotes it by setting ready / dragging the ticket out of Backlog - promoting *is*
the consent act. Backlog mode does not gatekeep raw ideas and does not nag every
un-promoted item; it simply moves on. (Selection in 1f already filters to signalled
items, so a silent skip here is the rare case of an item that lost its signal between
scan and triage.)

For a **signalled** item, route it to exactly one class. **First match wins - and `dep-unsatisfied` is evaluated BEFORE `workable`:** a signalled item carrying an unsatisfied (acyclic) blocker is a dep-wait, never a workable advance, so it surfaces the wait (`BLOCKED`) rather than slipping into CLASSIFY/DISPATCH (1f selects it precisely so the wait gets surfaced):

| Class | The agent's read | Route |
|---|---|---|
| **needs-spec** | a **tracker-only** promoted item - no flow spec exists at all | **`ask` via the tracker comment ALONE** (Phase 3) - surface "run capture/refine"; **never a spec stub** |
| **dep-unsatisfied** | signal present, but a blocker (flow or tracker) is not yet done - for a spec-backed item, `spec chain` reported `eligible: false` (1f) | **`BLOCKED <id> by <dep>`** - a state-changing terminal that **surfaces the dep wait** (never `NO_WORK` - the item was selectable in 1f); `<dep>` is the command's `reason` string for a flow dep; the topo-sort offers the blocker first on a later run. A circular/unsatisfiable dep routes to `ASKED` instead (1e) |
| **workable** | signal present, **deps satisfied**, AND the spec is complete enough to act on (clear AC / R-IDs, an actionable next stage) | **advance**: hand to `auto.md` Phase 2, which drives it from there |
| **ready-but-thin / ambiguous** | signal present, deps satisfied, but the spec is missing, a stub, or too thin/ambiguous to act on safely | **`ask`** (Phase 3) - kick back the gap; **never build, never auto-author** |
| **needs-human** | signal present, deps satisfied, spec exists, but a genuine decision needs a person (conflicting AC, a real design fork) | **`ask`** (Phase 3) |

**Check `.flow/memory/declined/` by concept before triaging an item as workable.** One `ls` of the directory (one file per concept, `<concept-slug>.md`); read any file whose concept the item touches. On a hit, the item is **not** workable however ready it looks - append the item as a dated line under that file's `## Prior requests`, cite the file, and route to `ask` (Phase 3) so a human decides whether the decision still holds. **Only the user reopens a declined concept**; the run never reopens one on its own read. No directory means nothing was declined: continue silently.

**The completeness read may only WITHHOLD, never FORCE.** A promoted-but-thin item is
kicked back with a question (`ask`) - it is **never** built into a slop PR. But the
read **never overrides an explicit ready signal to *force* work** on an item the
human did not promote, and **never sets the ready flag itself**, and **never
promotes** on its own reading of the prose. The signal gates eligibility; the
completeness read is a one-way safety net that can only hold work back, never start
it. A read that started work the human had not promoted has broken this.

**`needs-spec` is always a *promoted* item missing a workable spec** - never an
un-promoted backlog idea (that is silently skipped, above). A tracker-only promoted
item **always** triages to `needs-spec`: there is no flow spec, so there is nothing
to advance - the only correct action is to surface the gap (Phase 3, tracker comment
alone).

A **live** triage always resolves to a **state-changing** terminal - `ADVANCED`
(workable → advanced a stage), `ASKED` (thin / needs-spec / needs-human → parked),
`BLOCKED` (dep-unsatisfied), or `NEEDS_HUMAN` (a crash-class condition). It never
ends on a no-op `TRIAGED` line in a live run, so an item can never re-select
forever. (`TRIAGED <id> <class>` is diagnostic / dry-run only - emitted under a
triage-only inspection, never as a live terminal.)

The `dep-unsatisfied` → `BLOCKED` terminal is a **dep-wait surface, NOT a strike**:
it records no strike, never unreadies the spec, and emits its own `blocked`
decision-log row - its concrete verdict-line + `pilot-log` template live in
[Backlog-mode dep-wait `BLOCKED` terminal](#backlog-mode-dep-wait-blocked-terminal) below, distinct from
the strike-based `BLOCKED`.

---

## Phase 1.6 - TRIAGE the selected item (backlog mode only)

**Active only when `PILOT_AUTONOMY=backlog`.** TRIAGE runs **in front of** CLASSIFY: a thin / specless / blocked item never reaches the pipeline. Execute Phase 2 above; its class table and routes are authoritative and single-sourced there (first match wins; **`dep-unsatisfied` is checked BEFORE `workable`**). The classification is the **host agent's READ** of the item, never a flowctl field, never a score, never a regex grader, never a second LLM. flowctl supplied facts (Phase 1.5b); the agent supplies judgment here.

**Optional force-gate.** Apply [the optional force-gate](#full-auto-default--the-optional-force-gate) below; a matching item routes to `ask` even when otherwise workable.

**A live triage always resolves to a state-changing terminal**: `ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`. It never ends on a bare `TRIAGED` no-op line; `TRIAGED <id> <class>` is diagnostic / explain only. Append the matching decision-log row at the resolving terminal (Backlog-mode decision log below).

**Explain is the only case that emits `TRIAGED`, and it short-circuits every route.** Under `--explain` (`PILOT_DRY_RUN=1`), backlog triage classifies the subject and stops; an explain run that reached Phase 2 CLASSIFY, Phase 3.5 ASK, the `BLOCKED` terminal, or the Phase 6 pilot-log row has broken this. This branch runs immediately after the class is resolved, before any routing:

```bash
if [ "${PILOT_DRY_RUN:-0}" = "1" ]; then
  # $TRIAGE_CLASS = the class resolved above (workable | ready-but-thin | needs-spec | dep-unsatisfied | needs-human).
  echo "PILOT_VERDICT=TRIAGED spec=$SUBJECT_ID stage=triage reason=\"dry-run: classified $TRIAGE_CLASS, nothing dispatched or parked\""
  exit 0
fi
```

When NOT explaining, route by class: **workable** sets `SELECTED_SPEC="$SUBJECT_ID"` and continues into Phase 2 CLASSIFY (the existing pipeline; the hop loop then drives this one item); every other class skips Phases 2 to 5 and resolves in Phase 3.5 (ask) or directly at the dep-wait `BLOCKED` terminal below. A live run never emits `TRIAGED` (it always lands on a state-changing terminal).

---

## Phase 3 - ASK (the async question valve - surface, never block)

When triage cannot safely proceed (ready-but-thin, needs-spec, needs-human), park
the item behind an **async** question and resolve the run to `ASKED`. **Never ask
interactively** - `plain-text numbered prompt` is forbidden on the run path; the human answers
later, on their own time, via the spec or the tracker.

Backlog mode **does not author specs.** Spec authoring (`capture`,
conversation→spec; `refine`, interactive Q&A) is human-gated and upstream. A
ticket without a workable spec is **surfaced as a gap** - "run `$flow-next-capture`
or `$flow-next-refine`" - **never auto-written**. An agent inventing scope from a
one-line ticket is exactly the slop the valve exists to prevent.

The question is posted through tracker-sync's inline `question` wrapper. The skill
owns the semantic question and recovery choice; flowctl owns deterministic comment
transport, marker dedup, and the normalized answer readback (tracker-sync steps.md
Phase 7 - backlog mode invokes it, never re-implements it):

```text
$flow-next-tracker-sync question <spec-id | tracker-id> mode:autonomous
```

For a **tracker-only** subject the `<tracker-id>` is the candidate's `list-open`
`issue.identifier` (the display handle, not the opaque global id) - posting the comment
hits `POST /projects/:id/issues/:iid/notes` on GitLab, which needs the `<project>#<iid>`
the identifier carries (gitlab.md § identity); a spec-backed subject passes its `<spec-id>`.
The wrapper resolves the matching durable/display locator, writes the free-prose
body to a mode `0600` temporary file, then executes `flowctl tracker wire
question` with `--subject-id`, `--blocked-stage`, `--reason-code`,
`--question-slug`, and `--body-file` exactly as specified in tracker-sync
`steps.md` Phase 7. The stable subject id is the spec id for a spec-backed item
or normalized `issue.id` for a tracker-only item; the display handle is locator
input only, never hash identity.

The question line ends with who decides, `*(owner: <role>)*`: the role the
blocking reason points at (missing scope or intent → product; a technical block
→ engineering). The same line goes into the spec's `## Open Questions` entry. The
tag is prose, so it changes neither the question id nor dedup.

Where the question parks depends on whether a spec exists:

- **Spec-backed** (`question <spec-id>`) - the durable parked state lives in the
  spec's `## Open Questions` behind the `<!-- flow-next:question id=… status=open -->`
  anchor (the floor), AND it is mirrored as a tracker comment when the bridge is
  active. The op writes both.
- **Tracker-only** (`question <tracker-id>`, a promoted ticket with no flow spec) -
  there is no spec to anchor in, so the question lives in the **tracker comment
  ALONE**. The surfaced gap is always *"this promoted ticket has no flow spec - run
  `$flow-next-capture` or `$flow-next-refine`"*. **Backlog mode never writes a
  spec stub** (that is the forbidden authoring). Its parked/answered state lives in
  the tracker (the `status=open` anchor + a matching `<!-- flow-next:answer id=… -->`,
  detected by scanning the issue comments) - **no spec import/flip happens until
  capture/refine later creates a spec.**

**Idempotent.** Re-triaging the same blocked subject computes the **same**
anchor `id` (the hash covers stable fields only - `subjectId` + blocked-stage +
`reasonCode` + `questionSlug`; the free prose is outside it), so comments-sync's
marker dedup finds the existing comment and **skips the re-post**. A re-triage never
duplicates a question. An **answered** question (Phase 1d) lets the next run
re-triage and proceed.

**Spec-first floor.** When **no transport is reachable**, the question is
written to the spec's `## Open Questions` **only** (when a spec exists), plus a
one-line "enable tracker-sync to mirror" note - **never a block**. A tracker-only
item with no transport has nowhere to park; that degrades to a `NEEDS_HUMAN` surface
(the gap cannot be recorded), never a silent drop. The loop always works with zero
trackers configured - the mirror auto-lights per detected transport.

The terminal for a parked item is `ASKED <id> (<n>)` - a **durable** park that set
the `status=open` anchor so Phase 1d skips it next run.

```text
PILOT_VERDICT=ASKED spec=<id> stage=ask reason="parked behind <n> open question(s): <one line>"
```

(`spec=<id>` is the spec id for a spec-backed subject, else the tracker id for a tracker-only subject.)

---

## Backlog-mode dep-wait `BLOCKED` terminal

**Active only when `PILOT_AUTONOMY=backlog` AND Phase 1.6 routed the subject to `dep-unsatisfied`.** It writes a `blocked` decision-log row, records no strike, preserves readiness, and names the first unsatisfied dependency (`<dep>`, a flow `blockedBy` edge or a tracker relation). For a spec-backed subject the `<dep>` clause is the `reason` string `spec chain` returned (1f above), so an unpushed parent reads `parent branch <b> not on origin; push it or land the parent first` rather than a bare `not yet done`; on a chained subject the row's `--reason` is the verdict line's reason text.

```bash
# No ledger write; a dep wait is healthy, not a strike. STAGE is the stage the
# item would advance to once unblocked (or '-'); $SUBJECT_ID is spec-backed or a
# tracker key. The `blocked` action distinguishes the dep wait from the strike path.
$FLOWCTL pilot-log append --id "$SUBJECT_ID" --action blocked --stage "${STAGE:--}" ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"} ${CHAIN_PARENT:+--reason "$REASON"}
```

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="dep wait — blocked by <dep> (not yet done); topo-sort offers the blocker first next tick"
```

(A circular/unsatisfiable dep does NOT reach here; Phase 1e routes it to `ASKED` instead. This terminal is for the plain acyclic dep wait only.)

---

## Backlog-mode decision log - one row per dispatched stage, at the resolving terminal

**Active only when `PILOT_AUTONOMY=backlog`.** Every backlog run that selected a subject appends exactly **one** decision-log row per dispatched stage (one per hop), each with its own `--stage`, keyed to the verdict grammar action, at its resolving terminal. The row co-occurs with the state-changing terminal; a live `TRIAGED` is never a bare no-op, so the logged action is always a terminal action. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, NOT a `receipts/` path), auto-gitignored:

```bash
# ACTION in {advanced, asked, blocked, needs-human}  (mapped from the terminal verdict)
#   ADVANCED  -> advanced   · ASKED -> asked   · BLOCKED -> blocked   · NEEDS_HUMAN -> needs-human
# STAGE is the pipeline stage advanced/blocked-at, or 'ask' for ASKED, or '-' when none.
# COST_TOKENS is host-reported (this run's token cost); omit the flag when unavailable.
$FLOWCTL pilot-log append --id "$SUBJECT_ID" --action "$ACTION" --stage "${STAGE:--}" ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"} ${CHAIN_PARENT:+--reason "$REASON"}
# --reason is passed ONLY on a chained dispatch (CHAIN_PARENT set): REASON is the verdict
# line's reason text after the `# fence:verdict-reason` prefix, so that row begins
# `chained on <parent-id>; ` exactly like the verdict. A non-chained dispatch omits the
# flag and its row keeps the frozen shape byte-identically.

# A run that dispatched several stages appends one row per stage, in dispatch order.
# Every intermediate row is `advanced` (the loop continued only from ADVANCED) and
# carries NO cost; the last row carries the run's terminal action and the
# whole-run cost ONCE. Each append mints its own row id, so a multi-hop run
# reads as several rows in the log, never as a doubled cost.
# $FLOWCTL pilot-log append --id "$SUBJECT_ID" --action advanced --stage qa
# $FLOWCTL pilot-log append --id "$SUBJECT_ID" --action "$ACTION" --stage make-pr ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}
```

- **`--id`** takes the spec id (spec-backed) OR the bare tracker key (tracker-only); flowctl safe-filename-normalizes it.
- **`--action`** is the frozen enum `triaged|advanced|asked|blocked|needs-human`. A **live** run logs only terminal actions (`advanced`/`asked`/`blocked`/`needs-human`); `triaged` is for a diagnostic/explain inspection only, matching the `TRIAGED` diagnostic-only verdict.
- **`--cost-tokens`** is host-reported by the skill (flowctl only stores the row; it never measures cost). Omit the flag when the host cannot report it.

Under backlog, a dispatched waiting land tick records `--action blocked --stage land` once (the existing log enum has no wait action), with its actual wait reason in the output; this is not a strike.

A default `NO_WORK` / `DEFERRED_TO_LAND` run that dispatched no subject writes **no** row. A scoped land tick that reports waiting did dispatch the selected item and records its one row as described above. An `--explain` run writes no row (classification/inspection only). Exactly one row per dispatched stage on an acting backlog run.

**The dep-wait `BLOCKED` terminal above already emits its own `--action blocked` row inline**; that is its single decision-log row, so this generic block adds none for that path. It covers the other resolving terminals (`advanced` / `asked` / `needs-human`) and the strike-based `BLOCKED`. Whichever terminal resolves a dispatched stage writes exactly **one** row for it; a second row for the same stage, or a dispatched stage with no row, has broken this.

---

## Full-auto default + the optional force-gate

**Full-auto by default.** A **workable**, **dep-clear**, **unambiguous** item is
selected-and-advanced with **no pre-gate** - the agent never sets the ready flag
itself and never asks before acting on a clean item. This is the point of backlog
mode: the human's promotion (ready flag / board move) is the consent; everything
downstream of a workable spec runs unattended to the pull request.

**Optional force-gate.** The sibling config key **`pilot.gateClasses: [<class>…]`**
(an array - NOT `pilot.autonomy.gate`; a scalar and an object cannot share the
`pilot.autonomy` dot-path) force-surfaces named classes before action. When the
selected item matches a configured gate class (e.g. `risky`, `prod-config`), route
it to `ask` (Phase 3) instead of advancing - even when it is otherwise workable. An
empty / unset `gateClasses` (the default) gates nothing; full-auto is unconditional.
A scalar `flowctl config set pilot.gateClasses risky` is read as the single class `risky`; multiple classes use a JSON array.

```bash
[ -n "${PILOT_SNAPSHOT:-}" ] || PILOT_SNAPSHOT="$(cat "$(git rev-parse --show-toplevel)/.flow/tmp/pilot-snapshot.json" 2>/dev/null)"
printf '%s' "$PILOT_SNAPSHOT" | jq -e 'type == "object"' >/dev/null 2>&1 || { echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="pilot snapshot missing or unreadable; rerun the snapshot step"'; exit 1; }
GATE_CLASSES="$(printf '%s' "$PILOT_SNAPSHOT" | jq -r '(.config.pilot.gateClasses // empty) | if type=="array" then .[] elif type=="string" then (if startswith("[") then (fromjson | .[]?) else . end) else empty end')"
```

(Matching an item to a gate class is the agent's read of the item, like triage -
no scorer. The classes are stable slugs the operator chose; you decide whether the
selected item belongs to one.)

---

## Deterministic, multi-tracker

Backlog reads use `$FLOWCTL tracker wire list-open --json`, `comment-list --locator "$LOCATOR" --json`, and `relation-list --locator "$LOCATOR" --json` (`LOCATOR` = `{"durable":…,"display":…}` JSON) directly. Their existing envelopes and failure behavior are unchanged; flow never adds a tracker-specific API or branches on tracker type. Keep tracker-sync for `reconcile` and `question`, where semantic folding and question authoring remain host work.

- **Ships on Linear, GitHub, GitLab + Jira** - the four adapters that implement
  `listOpenIssues` / `listIssueRelations` / the comment ops.
  On **GitLab** the adapter derives the project-local `iid` its issue API paths require
  from the issue's normalized **`identifier`** (`<project>#<iid>`) - never the global
  id (gitlab.md § identity / fetchIssue). On **Jira** the `{issueIdOrKey}` path accepts
  either, and the adapter **prefers the durable numeric `id`** (the immutable issue id,
  e.g. `"10042"`) over the renamable `PROJ-123` key (jira.md § identity) - the opposite
  of GitLab, whose global id can't index a path at all. The handle the adapter needs is
  available in **both** backlog cases, so no spec is required: a **spec-backed** issue
  carries the durable `id` as the stored `tracker.id` (and `tracker.identifier` for
  display), and a **tracker-only** issue (one `list-open` enumerated with no flow spec)
  carries both `issue.id` and `issue.identifier` in the normalized struct.
  The normalized op signature is identical for every tracker; the id/iid/key derivation is an
  adapter-internal concern, so the run still branches on **no** tracker type.
- **Zero-setup.** Tracker-sync's one-time discovery ceremony resolves and
  persists the destination, available capabilities, and existing auth
  (`gh`/`glab` CLI session, a registered Linear MCP, or a CI/REST env token - Jira
  is REST-token only, **no MCP**). Runtime operations
  consume that resolved state through `flowctl tracker`. No flow-next-specific
  provisioning, OAuth app, webhook, or special config is required. The spec-first floor
  guarantees the loop works with **zero** trackers configured.

---

## What backlog mode must NOT do (load-bearing boundaries)

- **No daemon / polling loop / trigger / webhook / cron / parallel-worktree.** One
  item per run - the next invocation (a human, a host `/loop` · `/goal`) owns repetition. The standing
  control-plane role (scheduler, cloud environments, triggers, multi-agent at
  scale) belongs to an orchestrator above flow-next, not to flow-next. If this file
  ever starts describing a standing process, that is drift - remove it.
- **Never authors a spec.** `capture`/`refine` are human-gated; a needs-spec gap
  is surfaced, never auto-written (may augment an obvious blank in an *existing*
  spec only - never create one). The span is *workable spec → pull request*, not
  *ticket → pull request*.
- **Backlog mode grants no merge authority.** The default terminus is `make-pr`. A current scoped merge destination may invoke land through `tail.md`; land owns convergence and merge gates.
- **Never sets the ready flag / never promotes.** Readiness is the human's explicit
  signal; the agent's completeness read can only *withhold*, never *force* or
  *promote*.
- **No deterministic triage.** No completeness scorer, no regex spec-grader, no
  weighted scoring, no flowctl `triageClass` field, no second LLM spawned to judge.
  Triage is the host agent's read; flowctl supplies facts and a log row only.
- **No new graph engine.** Dep-ordering reuses the flow-next-deps jq topo-sort; a
  cycle is surfaced (`ASKED`/`BLOCKED`), never spun on.
