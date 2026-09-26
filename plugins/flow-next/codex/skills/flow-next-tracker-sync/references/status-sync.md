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
> guess a meaning). The facade applies the policy and owns the status write,
> `lastSyncedAt`, and the receipt; the agent queues a human decision with
> `sync defer`. This file owns the policy + the deadlock judgment.

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
| **flow** | spec: `open` · `done`; task: `todo` · `in_progress` · `blocked` · `done`; plus the spec's `completion_review_status` (`unknown` · `ship` · `not_required` · `needs_work` · `needs_human`; satisfying set `{ship, not_required}`) | `flowctl.py` `SPEC_STATUS` / `TASK_STATUS` / `COMPLETION_REVIEW_STATUSES` |
| **normalized** (the stable middle) | `backlog` · `planned` · `in-progress` · `in-review` · `done` · `verified` · `deferred` · `wontfix` | [adapter-interface.md](adapter-interface.md) |

The **tracker side** maps its team-specific workflow-state names into the normalized
vocabulary in the adapter ([linear-ladder.md](linear-ladder.md) status table). The
**flow side** maps onto the normalized vocabulary here:

### flow → normalized (what the spec's status *means* on the tracker)

The spec's tracker-facing status is derived from the spec + its tasks (one spec ↔
one issue, R3 — there are no per-task sub-issues) **and a merge-evidence probe**.
The signature is **`flowToNormalized(spec, prEvidence)`** — it takes PR-merge
evidence as a second input, NOT spec state alone. **Local completion is necessary,
not sufficient, for a terminal status (R1).** A spec that is locally `done` with a
shipped completion review is still only `in-review` on the tracker until a
`MERGED`-state PR for its branch is observed; `done`/`verified` are reserved for
merge-confirmed work.

**`prEvidence`** is the result of the merge-evidence probe the facade runs for the
spec branch. Its buckets:

- `merged` — ≥1 MERGED PR whose changed files include a path outside
  `.flow/specs/` and `.flow/tasks/` (a spec-text-only merge is the spec landing,
  not shipped work, #391).
- `open` — ≥1 OPEN, 0 MERGED.
- `closed-unmerged` — ≥1 CLOSED, 0 MERGED/OPEN.
- `none` — no PR for the branch (probe succeeded, empty result).
- `ambiguous` — a state the four buckets above don't cleanly cover, e.g. a branch
  with BOTH an open AND a closed-unmerged PR, or a draft-only result where no clear
  merge/open/closed signal dominates.
- `probe-error` — the probe itself failed (no auth, network) or `branch_name` is
  unknown (cannot probe).

**Probe failure / unknown branch is NOT merge evidence.** `probe-error` is never
`none` and never `merged`. Both `probe-error` and `ambiguous` are non-terminal and
route to NEEDS_HUMAN (below); terminal is reachable ONLY from an unambiguous
`merged`.

`flowToNormalized` maps to the normalized rung the spec *would* project. **It never
forces a rung downgrade by itself** — the evaluation order (below) decides whether to
*write* it. In particular, `prEvidence == none` projects `in-review` but the
**no-PR preserve rule** keeps an already-valid non-terminal tracker state; the
`in-review` projection only drives a `setStatus` when there is a real open-PR
(`open`) signal behind it.

**Row-order discipline (load-bearing).** `prEvidence` is evaluated **FIRST** — a PR
signal (`merged` / `open`) decides the rung *before* any local task/completion-status
row gets a vote. The local-status rows (the `no PR evidence` block) apply **only**
when there is no PR signal (`none` / `closed-unmerged` / `ambiguous` / `probe-error`).
This ordering is what makes an all-tasks-done OPEN spec with an open PR project
`in-review` (not `in-progress`), and a merged ungated/`unknown`-completion spec reach
terminal Done (not stay `in-review`). The merge-evidence INVARIANT is intact: terminal
(`done`/`verified`) is reachable ONLY from `prEvidence == merged`.

| # | flow condition | `prEvidence` | normalized | Rationale |
|---|---|---|---|---|
| 1 | spec `done`, no completion-review configured | `merged` | **`done`** | terminal, no review gate, **merge-confirmed** — a merge is a merge |
| 2 | spec `done`, `completion_review_status` in the satisfying set (`ship` · `not_required`) | `merged` | **`verified`** (`ship`) / **`done`** (`not_required`) | requirement satisfied **and** PR merged — terminal. The verified-vs-done label selector stays `ship`-only: only a review that ran can claim `verified`; policy-excused `not_required` is terminal `done` |
| 3 | spec `done`, `completion_review_status` outside the satisfying set (`unknown` · `needs_work` · `needs_human` · absent/unrecognized) | `merged` | `in-review` | PR merged but a configured completion review is neither shipped nor excused — stay in review until satisfied |
| 4 | spec at any local status (incl. all-tasks-done OPEN, or spec `done`) | `open` | `in-review` | open PR awaiting merge — the In Review rung, drives `setStatus(in-review)` (R2). The open-PR signal wins over the local task rows |
| 5 | spec `done` | `none` | **`in-review`** projection (NOT terminal); the facade **preserves** an existing non-terminal state | no PR exists — no merge evidence, no open-PR signal → never terminal, never a forced advance (R1) |
| 6 | spec `done` | `closed-unmerged` / `ambiguous` / `probe-error` | **`in-review`** (NOT terminal) **+ surface NEEDS_HUMAN** | locally shipped but the probe is not a clean MERGED — never terminal; the conflict goes to a human (R6) |
| 7 | spec `open`, **any** task `in_progress` or some `done` | `none` / `closed-unmerged` / `ambiguous` / `probe-error` | `in-progress` | work underway, no open/merged PR signal |
| 8 | spec `open`, **no** task `in_progress`/`done` yet (all `todo`) | `none` / `closed-unmerged` / `ambiguous` / `probe-error` | `planned` (or `backlog` if no tasks exist) | authored, not started |

> **Why row 3 catches `unknown`.** flowctl normalizes a missing completion-review
> field to `unknown` (the `completion_review_status` fallback in `flowctl.py`), and for repos without a
> completion-review backend `flow --auto` skips the gate entirely. Row 3 is the `merged` +
> not-satisfied rung **only when a completion review is
> actually configured** — when no completion-review backend is configured at all,
> row 1 fires first (a spec with no review gate has nothing to wait on, so a merge is
> terminal `done`). Distinguish the two by `flowctl config`: "no completion-review
> configured" ⇒ row 1; "configured but the spec's status is outside the satisfying
> set `{ship, not_required}`" ⇒ row 3.

> **Why rows 4–6 sit above rows 7–8.** A PR signal — open or merged — is stronger
> evidence of where the work *is* than the local task ledger. In the normal make-pr
> path, make-pr closes the completed spec on the PR branch before opening the PR.
> The open-PR row (4) keeps that closed spec **In Review** until merge evidence
> permits a terminal state. It also takes precedence over the broad "some task
> done → in-progress" row (7) for PRs whose specs remain incomplete.

**Terminal (`done`/`verified`) is impossible without a `MERGED` probe result.** The
old map mapped `spec done + completion ship → verified` and `spec done,
no review → done` with NO merge check, so a locally-completed spec auto-closed its
tracker issue before the PR merged. The merge-evidence gate fixes that at the root,
upstream of the who-wins ladder (which is unchanged). A `closed-unmerged` /
missing-branch / ambiguous probe NEVER yields terminal — it stays `in-review` (a
non-terminal rung) and surfaces NEEDS_HUMAN for the closed-unmerged case (R6).

`deferred` / `wontfix` have no native flow status — they only ever arrive **from**
the tracker side and are **surfaced, never auto-applied** (see the who-wins table).
`blocked` tasks do not change the spec-level normalized status (the issue stays
`in-progress`); a blocked note can ride along as a comment (see
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

### Applying the table (evaluation order)

**Evaluation order matters.** The **deadlock check fires FIRST** — before the
terminal-wins and in-progress-wins rules — because the canonical deadlock
(`tracker ∈ {done, verified}` while `flow == in-progress`, or the mirror) satisfies
*both* of those single-field rules at once. If terminal-wins ran first it would
silently auto-close the spec and `conflictTiebreak` would never fire — the exact bug
this ordering prevents. The terminal-vs-active **pair itself is the deadlock
signal**; it does not depend on any stored prior status (flowctl's sync state stores
the merge-base *body* + hashes, not a prior status field — so the check reads only
the two current normalized statuses, which are always available).

The facade evaluates in this order: a `deferred`/`wontfix` (cancelled-family)
status → surface; the deadlock check; a locally-done spec whose `prEvidence` is
`closed-unmerged` / `ambiguous` / `probe-error` → NEEDS_HUMAN `conflict`, no
status write; agreement → `noop`; the per-field rules (tracker terminal wins,
flow in-progress wins, the no-PR preserve rule, the open-PR `in-review` push, the
merged terminal push); anything else → `conflict` (`unmapped`), never a silent
default.

The deadlock branch deliberately **subsumes** the `tracker-done × flow-in-progress`
case that the terminal-wins rule would otherwise grab — that is the whole point of
putting it first. The `conflictTiebreak` default (`always-ask`) then queues/asks
rather than silently closing a spec whose agent loop is still live; teams that
*want* the tracker's closure to win automatically set `tracker.conflictTiebreak:
tracker-wins`.

## Status deadlock → R1 `conflictTiebreak` fallback (R7)

A **status deadlock** is the one case the per-field table can't resolve cleanly:
the two sides assert *incompatible terminal-vs-active* states at the same sync point
— the canonical case is **tracker `done` simultaneously with flow `in-progress`** (a
PM closed the issue while the agent loop is still running, or vice versa: flow `done`
while the tracker reopened to `in-progress`). The terminal rule says "tracker wins
terminal" but the in-progress rule says "flow wins in-progress" — they collide. This
is not a field the bridge silently overwrites.

**Because both single-field rules match a deadlock at once, the facade
evaluates the deadlock check FIRST** (see the evaluation order above) — if terminal-wins ran
before it, the deadlock would be silently auto-closed and `conflictTiebreak` would
never fire. The terminal-vs-active **pair itself is the signal**; the check needs no
stored prior status (flowctl persists the merge-base *body* + hashes, not a status
field), so it reads only the two current normalized statuses. The clean
tracker-wins-terminal path applies only when flow is NOT `in-progress`
(flow at `planned`/`backlog`/`done` — no live work to contradict the closure).

Resolution falls back to the **R1 `conflictTiebreak` default**
(`tracker.conflictTiebreak` ∈ `flow-wins | tracker-wins | always-ask`, default
`always-ask` — `flowctl config get tracker.conflictTiebreak`):

| `conflictTiebreak` | Interactive | Ralph / autonomous |
|---|---|---|
| `tracker-wins` | if the tracker is terminal, fold `done` into the spec through the existing local-status path (no provider write; `pulled` receipt). The mirror — merged Flow terminal while the tracker is active — is not durably representable by raw `spec.status`, so return the candidate-bearing `status-deadlock-unrepresentable` conflict with no mutation | same deterministic result |
| `flow-wins` | push Flow's normalized state through the existing provider-neutral `setStatus` path; terminal projection still requires clean merged-PR evidence | same — confident, proceeds |
| `always-ask` (default) | **ask via `plain-text numbered prompt`** — show both states, let the human pick | **`sync defer`** — queue the deadlock, never block (R11) |

"Ask the human" resolves to "**queue** for the human" in autonomous mode (the
deferred-decisions sink) — same policy, surface-dependent delivery, mirroring
flow-next-drive's surface-aware ladder and the body-merge `always-ask × Ralph` rule.

```bash
# Ralph deadlock under always-ask — queue, write no status, advance no state:
$FLOWCTL sync defer "$SPEC_ID" \
  --summary "Status deadlock: tracker=done, flow=in-progress" \
  --suggested "Human picks: close the spec to match the tracker, or reopen the issue to match flow" \
  --reason "status-deadlock"
```

The facade applies supported `flow-wins` / `tracker-wins` resolutions itself. Only
the unrepresentable `tracker-wins` mirror and `always-ask` reach the agent, as a
`conflict` with no provider or local write.

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
| `started` | `in-progress` (or `in-review` for a `started`-type state named "In Review" — the open-PR rung, resolved via `statusMap`) | spec `open`, work underway / in review | **flow wins** (flow drives the loop) |
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
Only the Jira and Linear providers read `statusMap`; GitHub and GitLab carry
status as `status:*` labels with a fixed vocabulary, so `statusMap` has no
effect there and a status conflict on those trackers is never a mapping gap.

For a state the bridge genuinely **cannot map** (a name-override the config doesn't
have, or — defensively — a `state.type` value Linear adds in a future schema version
that isn't in the fixed six), the rule is **warn + surface, never guess and never
crash**:

```
normalizeTrackerStatus(state):
  if state.type ∈ {the six fixed types}:
     base = defaultMap[state.type]               # table above
     # apply a config name-override if one exists for this state name:
     return statusMap.get(state.name, base)
  else:
     # an unknown type (future Linear schema) — do NOT guess a flow effect:
     warn("unmapped tracker state '<name>' (type '<type>') — surfacing, not auto-applying")
     surface to the user (interactive ask / Ralph sync defer)
     return UNMAPPED                              # treated like deferred/wontfix: never auto-change flow
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

## Readiness projection — `tracker.readyState` → local `ready` flag

**One-way, pull-side only.** When `tracker.readyState` is configured (the ceremony
question, steps.md Phase 1 step 5), every operation that reads the issue (`pull` /
`reconcile`) projects the configured tracker state onto the local spec `ready`
flag — after the status normalization above, independent of the who-wins rules
(readiness is **orthogonal to status**; it never feeds the status policy and never
drives a `setStatus`). `readyState: null` (the default) ⇒ this whole section is
skipped — no calls, no receipts, no flag writes (R7 invisibility).

**Derive the desired flag** from the normalized `issue`:

- **Linear** — `desired = (trim+casefold(status.raw) == trim+casefold(readyState))`.
  The match is on the workflow-state **name** (`status.raw` carries it), not the
  `state.type`: names are non-unique and renamable, and a custom "Ready" state is
  typically `type=unstarted` — type alone cannot distinguish Todo from Ready (same
  rationale as the `statusMap` name-override above).
- **GitHub** — `desired = (readyState label ∈ issue.labels[].name)`, compared
  case-insensitive/trimmed (GitHub label names are case-insensitively unique).
  **Label absent ⇒ `desired = false` — a normal state, never an error or a warn**;
  un-labeling the issue is exactly how a GitHub user un-readies a spec.
- **GitLab** — same as GitHub: GitLab has no workflow states, so readiness is a
  **label**. `desired = (readyState label ∈ issue.labels[])` (the normalized
  `issue.labels`), compared case-insensitive/trimmed. **Label absent ⇒ `desired =
  false`** — a normal state; removing the label is how a GitLab user un-readies a spec.
- **Jira** — like Linear, Jira has **workflow states, not labels**, so readiness is a
  **status-name match**: `desired = (trim+casefold(status.raw) ==
  trim+casefold(readyState))`. The match is on the workflow-state **name**
  (`status.raw` carries `fields.status.name`), **never** `statusCategory` — names are
  what a human moves an issue *to* on the board, and a "Ready" state could be any
  category. `readyState` here is the **raw Jira status name** (the same value
  `listOpenIssues` interpolates into its JQL — [jira.md](jira.md) § `listOpenIssues`),
  NOT a `statusMap`-resolved value. One-way, tracker-authoritative.

The facade applies the derived flag. `desired = false` is ambiguous between "the
issue genuinely isn't in the ready state" and "the config is stale (state
renamed/deleted, label removed)", so the facade first confirms the configured
name still exists on the tracker. Stale config leaves the flag untouched, reports
`degraded.kind: stale_readyState`, and the rest of the sync continues — a stale
`readyState` must not silently un-ready every linked spec. The receipt records a
readiness change only when the flag actually changed.

### Invariants (load-bearing)

- **Never write readiness back to the tracker.** No `setStatus`, no label
  add/remove is ever driven by the local `ready` flag. A local `flowctl spec
  ready` on a tracker-connected repo is overwritten by the next sync — the
  tracker is authoritative (which is why the capture/interview mark-ready prompt
  is gated off when `readyState` is configured).
- **Readiness receipts are local-only** — never posted as tracker comments
  (readiness is not a lifecycle comment; tracker-side comment text also gets
  auto-linkified/rewritten, so it could never round-trip cleanly anyway).
- The projection never advances `lastSyncedAt` by itself, never blocks, and never
  aborts the run — body/status/comments reconcile exactly as before.

## Worked fixtures (runnable without a live tracker)

Each fixture is a flow state + a tracker `status` struct + the expected reconcile
outcome — the oracles for R7, exercisable by the host agent reading them (no live
Linear; the live `setStatus` is the smoke phase).

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
deadlock check fires **first** in the evaluation order (before terminal-wins), it is
NOT auto-closed by the tracker-wins-terminal rule — it resolves via
`tracker.conflictTiebreak`:
- `always-ask` (default) → **interactive ask** / **Ralph `sync defer`** (queue —
  see the `sync defer` block above). PASS iff exactly one
  scoped status deadlock is surfaced and **no** status is written.
- `tracker-wins` → the facade folds `done` into the spec. PASS iff the spec
  closes.
- `flow-wins` → the facade pushes `in-progress`. PASS iff the board reopens.

### Fixture S-F — unmapped custom state, warn + surface (R7)

**Tracker:** a custom workflow state named `"Pending Legal"` with a `state.type`
the config `statusMap` has no override for and that isn't in the default name map.

**Expected:** `warn` + **surface** (`sync defer --reason unmapped-state`); the status
field is treated like `deferred` (never auto-applied), and **every other field still
reconciles** — the run does **not** crash or abort.

**Oracle:** a warning is logged, one `unmapped-state` entry is surfaced, the body /
comments reconcile proceeds, and no `setStatus` is driven from the unmapped status.
PASS iff no crash and the rest of the sync completes.

### Fixture S-J — closed-unmerged PR → non-terminal + NEEDS_HUMAN (R6)

**Flow:** spec `done`, `completion_review_status == ship`.
**`prEvidence`:** `closed-unmerged` (a PR for the branch is `CLOSED` with 0 `MERGED`
and 0 `OPEN` — closed without merging).
**Tracker:** `status.normalized = "in-progress"`.

**Expected:** `flowToNormalized(spec, closed-unmerged)` → **`in-review`** (NON-terminal
— a closed-without-merge PR is NOT merge evidence, so terminal is forbidden). The
ambiguity (locally shipped, but the PR was closed unmerged) **surfaces NEEDS_HUMAN**
(interactive ask / Ralph `sync defer --reason closed-unmerged`). The issue stays
**non-terminal** (In Progress preserved); no terminal write.

**Oracle:** **no** `setStatus(done|verified)` / no close; exactly one NEEDS_HUMAN
surfaced/queued entry naming the closed-unmerged branch; the issue stays
non-terminal. PASS iff a closed-unmerged spec never auto-closes the tracker issue and
the conflict reaches a human.

> **`ambiguous` and `probe-error` share S-J's path.** A `prEvidence` of `ambiguous`
> (e.g. both an open AND a closed-unmerged PR on the branch) or `probe-error`
> (`gh` failed / no auth / unknown `branch_name`) is handled by the **same**
> reconcile branch as `closed-unmerged`: `flowToNormalized` → `in-review`
> (non-terminal), and the facade returns a NEEDS_HUMAN `conflict` the agent surfaces (`sync defer --reason ambiguous`
> / `--reason probe-error`) with **no** status write. Terminal is reachable ONLY
> from an unambiguous `merged` — a failed or ambiguous probe never closes the
> issue.

## Boundaries

- **This is the status/metadata layer, not the body merge or the transport.** The
  3-way body merge is [body-merge.md](body-merge.md); the transport
  (`setStatus`/`readStatus` wire detail) is [linear-ladder.md](linear-ladder.md)
  / the GitHub adapter. This file consumes the normalized
  `status` struct and applies the per-field policy.
- **Per-field who-wins — never one global rule.** Terminal → tracker; in-progress →
  flow; priority + `deferred`/`wontfix` + unmapped → surface, never auto-change.
- **Status is never silently overwritten on a deadlock** — it falls back to the R1
  `conflictTiebreak`; `always-ask` queues in Ralph, prompts interactively.
- **State advances only on a successful reconcile.** A `setStatus` error, an
  unmapped state surfaced, or a queued deadlock does NOT advance `lastSyncedAt`.
- **Native open records a manual reopen.** On GitHub and GitLab, a lone stale
  terminal `status:*` label cannot override the provider's open state. An
  ambiguous multi-label namespace still fails closed.
- **Readiness projection is one-way pull** (`tracker.readyState` → local `ready`
  flag): change-only receipts, stale config warns + leaves the flag
  untouched, and readiness is never written back to the tracker.
