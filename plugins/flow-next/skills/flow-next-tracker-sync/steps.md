# flow-next-tracker-sync — phase-by-phase execution

Read [SKILL.md](SKILL.md) first for the architecture, the flowctl-vs-skill split, and the boundaries. This file is the execution detail. `$FLOWCTL` is defined in SKILL.md's Preamble.

This file is the transport-blind orchestration **spine**: discovery ceremony, link/unlink ceremony, grain, identity, and the push/pull/reconcile skeleton with named hooks. The hook bodies live in dedicated reference files: transports (`fetchIssue`/`writeIssue`/… — Linear [`references/linear-ladder.md`](references/linear-ladder.md), GitHub [`references/github.md`](references/github.md)) and reconcile (3-way body merge [`references/body-merge.md`](references/body-merge.md); status who-wins [`references/status-sync.md`](references/status-sync.md); comments/evidence append [`references/comments-sync.md`](references/comments-sync.md)), all plugging through the contract in [`references/adapter-interface.md`](references/adapter-interface.md). Inline, a hook points at its reference with **[→ ref: <file>]** — read that file for the body; this file owns only the routing.

## Phase 0 — Mode + Ralph awareness

Parse `$ARGUMENTS` for an optional operation token (`push` / `pull` / `reconcile` / `link` / `unlink` / `discover`) and an optional spec id. With none, default to the interactive menu (discover if the bridge is inactive, else offer push/pull/reconcile over `list-unsynced` / `list-stale`).

**Ralph / autonomous mode** (R11): when `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` is set, the skill still runs — but the discovery ceremony NEVER prompts (it needs a human; if the bridge isn't already configured, no-op + receipt note), and any genuine conflict **queues** (`sync defer`) instead of asking. Confident merges and conflict-free status/comment ops proceed unattended. "Ask the human" resolves to "queue for the human" in autonomous mode — same policy, surface-dependent delivery (mirrors fn-51's surface-aware ladder).

```bash
RALPH=0
[[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" ]] && RALPH=1
```

## Phase 1 — Discovery ceremony (R2)

Only when the bridge is not yet active (`flowctl sync active --json` → `active: false`) AND not in Ralph mode. If already active, skip to Phase 2.

1. **Probe the four signals** (see SKILL.md table). Detection lives here, not flowctl:
   ```bash
   # Linear MCP: inspect the host's MCP/tool list for a Linear server (verified upsert
   #   verbs save_issue / save_comment / list_comments / get_issue / list_issue_statuses —
   #   see references/linear-mcp.md). Host-agent introspection — no flowctl call.
   LINEAR_API=0; [ -n "${LINEAR_API_KEY:-}" ] && LINEAR_API=1
   GH_OK=0; gh auth status >/dev/null 2>&1 && GH_OK=1
   # Jira: a *.atlassian.net host visible in config/env (surface only — out of scope here).
   ```
   The Linear transport rung the bridge will use follows from these signals (MCP
   beats GraphQL when both present): MCP registered → rung 1; else `LINEAR_API_KEY`
   set → rung 2 (GraphQL); else no-op. See [`references/linear-ladder.md`](references/linear-ladder.md).
2. **Surface present AND absent.** Tell the user what was found and what wasn't — e.g. "Linear MCP: present. LINEAR_API_KEY: absent. gh: authenticated. Jira: none." Absent signals matter (they explain why a transport is unavailable).
3. **ASK via `AskUserQuestion`** (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Lead with the recommended tracker (the strongest present signal) + a one-sentence rationale. Ask: enable the bridge? which tracker (`linear` / `github`)? **Enabling activates the WHOLE pipeline by default (opt-out model)** — tell the user that on confirmation every lifecycle event (capture / interview / plan / work.firstClaim / work.done / makePr / resolvePr / completionReview) starts mirroring to the tracker, because hooking up the bridge means you want it to sync. Offer an **optional opt-out**: any events to exclude now (default: all on); they can also turn any off later via `flowctl config set tracker.perEvent.<event> off`. Resolution is **env > config > ASK** — don't re-ask anything env/config already decided.
4. **On confirmation, write config** (dot-paths are safe). Activate every lifecycle event to its natural op — **skip only the ones the user explicitly excluded in step 3**:
   ```bash
   $FLOWCTL config set tracker.enabled true
   $FLOWCTL config set tracker.type "$CHOSEN_TYPE"        # linear | github
   $FLOWCTL config set tracker.provenance "discovery ceremony $(date -u +%Y-%m-%d); confirmed by <who>; signals: <list>"
   # DEFAULT-ON (opt-out): activate the whole pipeline so it mirrors end-to-end.
   $FLOWCTL config set tracker.perEvent.capture reconcile           # two-way body sync on capture
   $FLOWCTL config set tracker.perEvent.interview reconcile         # two-way body sync on interview
   $FLOWCTL config set tracker.perEvent.plan reconcile              # project the planned spec
   $FLOWCTL config set tracker.perEvent.work.firstClaim push        # move the issue In-Progress
   $FLOWCTL config set tracker.perEvent.work.done comment           # status comment + evidence
   $FLOWCTL config set tracker.perEvent.makePr comment              # PR link is unconditional; extra status comment
   $FLOWCTL config set tracker.perEvent.resolvePr comment           # resolution comment
   $FLOWCTL config set tracker.perEvent.completionReview reconcile  # flip Done/verified + verdict / R-ID coverage
   $FLOWCTL config set tracker.perTracker.teamId "<team>"           # if the user named one
   $FLOWCTL sync active --json   # confirm active: true
   ```
   **Never assume — but default-on is not assuming.** No signal / user declines the bridge ⇒ write nothing; `enabled` stays `false`; `sync active` stays `active: false`. Confirming the bridge IS the consent to sync the pipeline. The **config schema default stays `off`** (in `get_default_config()`), so a bare `tracker.enabled=true` set by hand or a script — WITHOUT this ceremony — activates **no lifecycle-event sync** (every `perEvent` event stays dormant). The **one exception** is make-pr's PR↔issue link, which is unconditional whenever the bridge is active (no per-event gate, by design — it powers Linear Diffs); only the ceremony's explicit per-event writes activate the events themselves. Users opt out per event afterward via `flowctl config set tracker.perEvent.<event> off`.

## Phase 2 — Link / create ceremony (R2/R3/R16)

Attach sync state **on link**. Pick the flow by where the user is starting:

### 2a — Flow-first (author-in-flow-then-push)

A `fn-NN` spec already exists. Keep the `fn-NN` id (never rename). Push body via the body-sync hook **[→ ref: body-merge.md]**, which creates the issue via `writeIssue` **[→ ref: linear-ladder.md / github.md]**, then attach state.

> **The pushed body is the COMPLETE spec — every section, in full.** The render (`renderFlowToTracker`, body-merge.md Step 3) is a *format translation*, NOT a summary: never condense, truncate, abbreviate, or drop a section. Projection means the issue mirrors the whole spec (the Step 3.5 structural gate enforces "no section silently dropped"). If you find yourself summarizing to save tokens, stop — read body-merge.md Step 3 and render the full body.

```bash
$FLOWCTL sync set-tracker-id "$SPEC_ID" "$ISSUE_UUID" --identifier "WOR-17" --url "$ISSUE_URL"
```

Write the back-reference into the issue: a `flow:<id>` label and/or a `[<id>]` title prefix (transport call — `writeIssue`/`setStatus` **[→ ref: linear-ladder.md / github.md]**) so the issue points back at the spec. The tracker key `WOR-17` becomes a resolvable alias for the `fn-NN` spec (`work wor-17` resolves — fn-52.10).

### 2b — Tracker-first (link an existing issue — "grab issue X and spec it")

Fetch the issue via the transport (`fetchIssue` **[→ ref: linear-ladder.md / github.md]**) → normalized `issue` struct. Create the spec **keyed by the tracker key** so the repo artifact mirrors the board:

```bash
$FLOWCTL spec create --tracker-first --tracker-identifier "WOR-17" --title "<issue title>" --json
# → canonical id wor-17-slug; tasks wor-17-slug.M; bare wor-17 / wor-17.M are aliases (fn-52.10).
$FLOWCTL sync set-tracker-id "wor-17-slug" "$ISSUE_UUID" --identifier "WOR-17" --url "$ISSUE_URL"
```

Seed the merge base from the **current issue body** so the first sync is pull-only (never surfaces the whole issue as a conflict) — first-link base-seeding is in **[→ ref: body-merge.md]**; call `sync set-merge-base` with the flow-form + tracker-form snapshots it produces:

```bash
# fn-52.4 produces both body forms; the setter requires BOTH halves together (paired-snapshot invariant):
$FLOWCTL sync set-merge-base "wor-17-slug" --flow-file flow.txt --tracker-file tracker.txt
$FLOWCTL sync set-last-synced "wor-17-slug"
```

> **Paired-snapshot invariant** (memory: `paired-snapshot-setter-must-write-both`): `sync set-merge-base` requires BOTH `--flow*` AND `--tracker*` together — never pass one half alone (it errors and leaves state unchanged). The merge base is one snapshot of both bodies at one sync point.

### 2c — Collision guard

Before linking, ensure the tracker UUID isn't already attached to another spec:

```bash
$FLOWCTL sync check-collisions --json   # flags any UUID shared by >1 spec
```

If `set-tracker-id` reports a collision, ask the user (interactive) or queue (`sync defer`, Ralph) — never `--force` silently.

## Phase 3 — Orchestration skeleton (transport-blind)

Route the operation; each layer calls hooks that operate on the normalized structs ([`references/adapter-interface.md`](references/adapter-interface.md)). The skeleton is real; the hook bodies plug in later. The **Linear transport hooks** (`fetchIssue`/`writeIssue`/`listComments`/`postComment`/`readStatus`/`setStatus`) are implemented by the detect-best-available ladder in [`references/linear-ladder.md`](references/linear-ladder.md) (MCP → GraphQL → no-op); GitHub's are the `gh` transport in [`references/github.md`](references/github.md) (single rung + no-op, reduced-fidelity status — fn-52.7). The **body hooks** (`renderFlowToTracker` / `foldTrackerIntoFlow` / `threeWayMergeBody`) are the agentic 3-way merge + format translation in [`references/body-merge.md`](references/body-merge.md) (fn-52.4); the **status who-wins** hook (`reconcileStatus`) is [`references/status-sync.md`](references/status-sync.md) and the **comments/evidence append + dedup** hooks (`postLifecycleComment` / `pullCommentsToSyncLog`) are [`references/comments-sync.md`](references/comments-sync.md) (fn-52.5).

```
push(spec):
  body    = renderFlowToTracker(spec)            → body-merge.md Step 3 (flow→tracker) — COMPLETE spec, ALL sections; never summarize/truncate
  writeIssue(issue{... body ...})                [→ ref: transport]
  setStatus(map flow status → tracker status)    → status-sync.md (who-wins)
  postComment(lifecycle event marker)            → comments-sync.md (append + dedup)
  sync set-merge-base (BOTH halves) + set-last-synced   # snapshot the pushed pair (body-merge.md Step 5)
  receipt: pushed

pull(spec):
  issue   = fetchIssue(trackerId)                [→ ref: transport]  → normalized issue
  comments= listComments(trackerId)              [→ ref: transport]  → normalized comment[]
  status  = readStatus(trackerId)                [→ ref: transport]  → normalized status
  foldTrackerIntoFlow(spec, issue, status)       → body-merge.md Step 3 (tracker→flow) + status-sync.md (who-wins) + comments-sync.md (pull genuine comments to sync log)
            # echo-fence first: pulled body hash == baseHashTracker ⇒ noop (body-merge.md Step 1 / Fixture D)
  receipt: pulled | noop
```

For the **reconcile** path, the orchestration delegates the full 3-way merge to
[`references/body-merge.md`](references/body-merge.md) (fn-52.4) — it is no longer a
stub. The skeleton's job is to fetch the three inputs, hand them to the merge, and
route the result to the receipt / defer / write-back; the merge logic (pre-reduction,
agentic both-sides-diverged judgment, format translation, structural gate, scoped
conflict) lives in that reference:

```
reconcile(spec):
  base    = sync get-state → merge-base snapshot (BOTH forms: mergeBaseFlow + mergeBaseTracker)
  issue   = fetchIssue(trackerId)                [→ ref: transport]
  merged  = threeWayMergeBody(base, flowBody, issue.body)   → body-merge.md
            # Step 1 pre-reduce: echo / byte-identical / only-one-side-changed ⇒ auto (no conflict)
            # Step 2 agentic merge (both diverged) + Step 3 format translation + Step 3.5 structural gate
  if genuine conflict (body-merge.md Step 4):
     interactive → show merged body, confirm the ONE scoped section before write-back (AskUserQuestion)
     Ralph       → sync defer (queue the scoped conflict, never block)   [R9/R11]
     receipt: diverged
  else:
     writeIssue(merged) + setStatus(who-wins)    [transport → fn-52.3/.7] + status-sync.md (who-wins)
     sync set-merge-base (BOTH halves) + sync set-last-synced   # body-merge.md Step 5 — ONLY on success
     receipt: merged | updated
  # no-base bootstrap (first link): body-merge.md "First-sync / no-base bootstrap" —
  #   flow-first ⇒ fast-forward projection; tracker-first ⇒ seed base, pull-only. Never a conflict.
```

**Echo-loop suppression** (constraint): after a push, record the resulting tracker-side content hash; on the next pull a hash match = flow's own echo ⇒ `noop`, never a phantom conflict. `lastSyncedAt` advances only on a real reconciliation, never on a no-op pull. The hash bookkeeping rides on the merge-base snapshot (fn-52.4).

**Failure handling** (constraints): a 404 / archived / deleted linked issue does NOT crash, does NOT clear state or advance `lastSyncedAt` — emit an `errored` receipt and prompt/queue an unlink decision. Batch sync is item-level: one spec's failure gets its own `errored` receipt + no state write, and the run continues.

Every operation ends with a receipt:

```bash
$FLOWCTL sync receipt "$SPEC_ID" --status pushed --tracker-id "$ISSUE_UUID" --transport "$TRANSPORT" --note "..."
# status ∈ {pushed,pulled,merged,updated,diverged,queued,errored,noop}; --transport ∈ {mcp,graphql,gh,none}
# --merges-file records body-merge records for audit/rollback (fn-52.4 supplies it)
```

## Phase 4 — Genuine conflict (scoped) — body-merge.md Step 4

Only a genuine semantic contradiction the agent can't confidently resolve is surfaced — **scoped to the section**, never the whole body, never a silent overwrite. Interactive: show the merged body for confirmation before write-back. Ralph/autonomous: queue.

```bash
$FLOWCTL sync defer "$SPEC_ID" --summary "Goal section rewritten on both sides to mean different things" \
  --suggested "Human picks: keep flow's framing, the tracker's, or a merge" --reason "genuine-contradiction"
```

The decision flow and the structural gate (no section silently dropped; both sides' non-conflicting additions present) live in [`references/body-merge.md`](references/body-merge.md) (fn-52.4, Steps 3.5 + 4). The skeleton wires the `sync defer` queue + the interactive `AskUserQuestion` confirmation entry point; the merge reference owns the judgment of *what* is a genuine, section-scoped contradiction (vs an additive change both sides keep).

## Phase 5 — Unlink / teardown

Unlinking clears tracker id + `lastSyncedAt` + merge-base atomically and posts a one-line "detached" comment to the issue. A re-link re-seeds the base (does not resurrect stale state).

```bash
# 1. post the detached comment FIRST (best-effort; a failed comment must not block the unlink)
postComment(trackerId, "Detached from flow spec <id> on $(date -u +%Y-%m-%d).")   [transport → fn-52.3/.7]
# 2. wipe state atomically
$FLOWCTL sync clear "$SPEC_ID"
$FLOWCTL sync receipt "$SPEC_ID" --status updated --note "unlinked from tracker"
```

`sync clear` is atomic (fn-52.1) — it wipes the tracker id, `lastSyncedAt`, and the merge-base snapshot together. The id/branch/files of the spec are NEVER touched (no rename on unlink).

## Phase 6 — Listings (surface `identifier`)

When listing sync state, surface the tracker `identifier` (display form, e.g. `WOR-17`) alongside the flow id so users see both handles:

```bash
$FLOWCTL sync list-unsynced --json   # specs needing a first push
$FLOWCTL sync list-stale --json      # linked specs with old/missing lastSyncedAt (default tracker.staleAfterHours)
$FLOWCTL sync get-state "$SPEC_ID" --json   # one spec's full state (tracker id + identifier + url + base)
```

For each linked spec, render a line like `wor-17-slug  ↔  WOR-17  (linked, synced 3h ago)` or `fn-42-foo  ↔  WOR-99  (alias, stale)`. The flow id is the canonical handle; `identifier` is the board-facing display form.

## Boundaries (repeat — load-bearing for this scaffold)

- Hook bodies marked **[→ ref: <file>]** are NOT inlined here — this file routes; read the referenced file for the body. Transports live in `linear-ladder.md` / `github.md`; reconcile in `body-merge.md` / `status-sync.md` / `comments-sync.md`.
- `set-merge-base` always writes BOTH halves (paired-snapshot invariant).
- Receipts on every run; conflicts queue (`sync defer`), never block (R11).
- Codex mirror is regenerated in fn-52.9 — keep this file Claude-native (`AskUserQuestion`, `Task`).
