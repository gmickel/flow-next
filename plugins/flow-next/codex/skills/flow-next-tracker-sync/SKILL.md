---
name: flow-next-tracker-sync
description: Project a flow-next spec to a tracker issue (Linear first, GitHub next) and reconcile body/status/comments two-way — projection, not coordination. The spec stays the source of truth; the tracker is a co-editable mirror. Use to configure the bridge (discovery ceremony), link a spec to an issue (flow-first push or tracker-first "grab issue X and spec it"), push/pull/reconcile, or unlink. Triggers on /flow-next:tracker-sync, "sync to linear", "push this spec to the tracker", "grab issue X and spec it", "link this spec to the issue", "reconcile with the tracker". NOT /flow-next:sync (that is plan-sync, a different skill).
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Task
---

# flow-next-tracker-sync — project a spec to a tracker, reconcile two-way

The `.flow/specs/<id>.md` spec is the source of truth and the quality layer; the tracker (Linear first, GitHub next) is a **co-editable mirror** for teams that must live in it. This skill is **projection, not coordination** — the tracker mirrors the spec (body, status, comments all sync two-way) but never drives flow state or spawns agents (see the decision record at `.flow/memory/.../tracker-sync-is-projection-not-*`).

This skill is the **spine**: the discovery ceremony, the spec↔issue grain, the identity/naming alias, and a **transport-blind** push/pull/reconcile orchestration skeleton. It does NOT contain transport code or merge logic — those plug in via the interface defined here:

- **Transports** (`fetchIssue` / `writeIssue` / `listComments` / `postComment` / `readStatus` / `setStatus`) are implemented by the Linear adapter (fn-52.3) and GitHub adapter (fn-52.7). This skill calls them through the normalized interface; it never sees a wire shape. The **Linear adapter is a detect-best-available transport ladder** (MCP → GraphQL → no-op, mirroring fn-51's driver ladder) — see [`references/linear-ladder.md`](references/linear-ladder.md); the **GitHub adapter** is the headless-robust `gh` transport (single rung + no-op, reduced-fidelity status) — see [`references/github.md`](references/github.md).
- **Reconcile** operates only on the **normalized payload structs** (`issue` / `comment` / `status`) the adapters exchange. The agentic 3-way **body merge** + format translation + scoped conflict is in [`references/body-merge.md`](references/body-merge.md) (fn-52.4); the per-field **status who-wins** is [`references/status-sync.md`](references/status-sync.md) and **comments/evidence append + dedup** is [`references/comments-sync.md`](references/comments-sync.md) (fn-52.5). The interface is defined in `references/adapter-interface.md`.

**Read [steps.md](steps.md) for the full phase-by-phase execution.** Read [`references/adapter-interface.md`](references/adapter-interface.md) for the transport interface + normalized payload contract, [`references/body-merge.md`](references/body-merge.md) for the agentic 3-way body merge / format translation / scoped conflict, [`references/status-sync.md`](references/status-sync.md) for the per-field status who-wins + deadlock fallback, [`references/comments-sync.md`](references/comments-sync.md) for comments/evidence two-way append + dedup, [`references/identity.md`](references/identity.md) for the hybrid id model (tracker-first canonical vs flow-first alias), [`references/linear-ladder.md`](references/linear-ladder.md) (→ [`linear-mcp.md`](references/linear-mcp.md), [`linear-graphql.md`](references/linear-graphql.md)) for the Linear transport ladder, and [`references/github.md`](references/github.md) for the GitHub adapter (`gh` transport, reduced-fidelity status).

> Sync engine shape (discovery ceremony, per-item `lastSyncedAt`, surface-diffs-never-overwrite) adapted from Ray Fernando's `running-bug-review-board` `issue-trackers.md` (Apache-2.0) — see CHANGELOG.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `steps.md`) use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

Non-blocking, same pattern as `/flow-next:plan` — one-line nag when the local setup lags the plugin:

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
 echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
fi
```

Continue regardless (never blocks; silent when setup was never run or versions match).

**Inline skill (no `context: fork`)** — `plain-text numbered prompt` must stay reachable across phases. Subagents can't call plain-text numbered prompts (Claude Code issues #12890, #34592). The discovery ceremony (Phase 1) and genuine-conflict surfacing (handled in fn-52.4/.5) both require user choice in interactive mode.

## flowctl owns plumbing; the skill owns judgment

The canonical flow-next split. flowctl (fn-52.1, fn-52.10) provides atomic, deterministic helpers; this skill, running on the host agent, does the API calls / reconciliation / asking:

| flowctl owns (deterministic) | the skill owns (host-agent judgment) |
|---|---|
| `sync active` — is the bridge active (value-checked)? | discovery ceremony: probe signals, surface, ASK, confirm |
| `sync list-unsynced` / `list-stale` — enumerate | decide which specs to push/pull this run |
| `sync set-tracker-id` / `set-last-synced` / `set-merge-base` — atomic state write | call the transport (`fetchIssue` / `writeIssue` / …) |
| `sync clear` — unlink, wipe state atomically | semantic 3-way body merge (fn-52.4), status who-wins + comment dedup (fn-52.5) |
| `sync receipt` / `sync defer` — proof-of-work + queue | translate flow-structured ↔ tracker free-form |
| `sync check-collisions` — flag shared tracker ids | decide create-vs-link on ambiguity; ASK the user |
| `spec create --tracker-first` / `config set` — id + config write | choose the hybrid id origin (tracker-first vs flow-first) |
| `sync list-dep-relations` — enumerate `depends_on_epics` edges + resolved tracker links + local dep status (fn-64) | `projectDepRelations`: drive `setIssueRelation` / `listIssueRelations`, warn on unlinked deps, keep completed blockers visible, defer the missing-remotely collision (steps.md § projectDepRelations) |
| `sync set-dep-relation` / `clear-dep-relation` — atomic provenance-ledger write (fn-64) | decide *which* edges are ours-to-touch (ledger / fenced-block provenance — never clobber a manual relation) |

Never reimplement a flowctl helper inline; never push a merge/judgment decision into flowctl.

## Discovery ceremony (R2) — detect / surface / ask / never-assume

The bridge is **off until explicitly enabled**. The ceremony probes four signals, surfaces present AND absent, ASKS, and writes config **only on confirmation** — with provenance. No-signal ⇒ nothing written; `enabled` stays `false`. Never assume. But **once the user confirms, enabling is opt-OUT, not opt-in**: the ceremony activates the whole pipeline (every `perEvent` event) by default — hooking up the bridge means you want it to sync. The user excludes events at ceremony time or turns any off later (`flowctl config set tracker.perEvent.<event> off`). The `get_default_config()` schema default stays `off`, so a bare `enabled=true` set WITHOUT the ceremony activates **no lifecycle-event sync** (every `perEvent` event stays dormant) — only the ceremony's explicit writes activate them. (Two exceptions are unconditional whenever the bridge is active — no per-event gate, by design: (1) make-pr's PR↔issue link **and its In Review status push** (fn-66, R2 — an open PR is the In Review rung, riding the same Diffs-powering link path); (2) **`land.merged`** (fn-66, R10 — a real merge is the SOLE event that projects terminal `Done`, gated on the GitHub `MERGED` probe; leaving it opt-in would strand boards at In Review post-merge).)

Probe these four signals (detection lives in the skill, not flowctl — same shape as fn-51's driver-ladder detection):

| Signal | Probe | Means |
|---|---|---|
| Linear MCP registered | the host's MCP/tool list contains a Linear server (e.g. `*Linear*` tools like `save_issue`) | interactive Linear transport available (OAuth handled) |
| `LINEAR_API_KEY` | `[ -n "$LINEAR_API_KEY" ]` | headless Linear GraphQL transport available |
| GitHub auth | `gh auth status` exits 0 | headless GitHub transport available |
| Jira host | a `*.atlassian.net` host configured/visible | Jira present (out of scope here — surface but don't offer) |

Resolution model is **env > config > ASK**, mirroring `cmd_review_backend` (`flowctl.py:4859`): if the transport/tracker is already decided by env or config, don't re-ask. Steps in [steps.md](steps.md) Phase 1.

**On confirmation only**, write via `flowctl config set` (dot-paths are safe — config keys are nested):

```bash
$FLOWCTL config set tracker.enabled true
$FLOWCTL config set tracker.type linear # or github
$FLOWCTL config set tracker.provenance "discovery ceremony 2026-06-03; confirmed by <who>; signals: MCP+API_KEY"
# DEFAULT-ON (opt-out): activate the whole pipeline — skip only what the user excluded.
$FLOWCTL config set tracker.perEvent.capture reconcile
$FLOWCTL config set tracker.perEvent.interview reconcile
$FLOWCTL config set tracker.perEvent.plan reconcile
$FLOWCTL config set tracker.perEvent.work.firstClaim push
$FLOWCTL config set tracker.perEvent.work.done comment
$FLOWCTL config set tracker.perEvent.makePr comment
$FLOWCTL config set tracker.perEvent.resolvePr comment
$FLOWCTL config set tracker.perEvent.completionReview comment # fn-66: comment-shaped (verdict + R-ID coverage) — NEVER terminal Done; land.merged is the sole Done driver (active-by-default, no perEvent seed needed)
```

Confirm the result with `flowctl sync active --json` (must report `active: true` once enabled/type are set). Negative path: user declines ⇒ write nothing; `sync active` stays `active: false`.

## Flexible entry (R2) — no fixed starting point

Two entry flows, both attach sync state **on link** (never impose where the user must start):

1. **Author-in-flow-then-push (flow-first):** a `fn-NN` spec already exists (capture/interview/plan authored it). Push creates the tracker issue, then `sync set-tracker-id` attaches the issue UUID + `--identifier WOR-17` + `--url`. Keep the `fn-NN` id; store the tracker key as a resolvable alias.
2. **Link-existing-issue (tracker-first): "grab issue X and spec it."** Fetch the issue via an already-installed transport, create the spec **keyed by the tracker key** (`flowctl spec create --tracker-first --tracker-identifier WOR-17`), seed the merge base from the current issue body, first pass is pull-only. See [steps.md](steps.md) Phase 2 (link) and [`references/identity.md`](references/identity.md).

## Grain (R3) — one spec ↔ one issue

- **One flow spec maps to one tracker issue.** The tracker UUID is the durable dedupe key (`sync set-tracker-id`); `sync check-collisions` flags any UUID shared by two specs.
- **Tasks stay flow-local by default** — NEVER auto-created as tracker sub-issues.
- **Optional checklist-in-body render** — tasks MAY be rendered as a checklist inside the issue body (not sub-issues). **Scoping decision: deferred to fn-52.4 (body reconciliation).** The scaffold defines the grain (one-to-one, tasks-local); whether the checklist render lands in the first body-sync pass is decided when the merge engine is built, because the checklist is a body-format concern. The skeleton exposes a `renderTaskChecklist` hook on the body-sync path (off by default) so .4 can opt it in without reshaping the spine.

## Identity / naming (R16) — hybrid via fn-52.10's id layer

The link/create ceremony assigns the canonical id through fn-52.10's generator. **Never rename an existing spec.** Full rules in [`references/identity.md`](references/identity.md); the headline:

- **Tracker-first link → canonical spec id `wor-17-slug`, canonical tasks `wor-17-slug.M`.** The bare forms `wor-17` / `wor-17.M` are aliases, resolved by fn-52.10's widened resolver (`flowctl show wor-17`, `work wor-17`, … all resolve). Branch follows the canonical id. Use `flowctl spec create --tracker-first --tracker-identifier WOR-17`.
- **Flow-first → keep `fn-NN-slug`.** Store the tracker key in the single `tracker.identifier` field (R4, display form `WOR-17`) as a resolvable alias via `sync set-tracker-id --identifier WOR-17`, and write the back-reference into the issue (`flow:<id>` label / `[<id>]` title-prefix).
- **Resolution is fn-52.10's job, not the scaffold's.** The skill just calls flowctl and relies on the widened resolver. Surface `identifier` in sync listings (see Phase 6 in [steps.md](steps.md)).

## Orchestration skeleton — transport-blind

Three sync operations across three layers, all transport-blind. The skeleton routes; the named hooks plug in later:

```
push flow → tracker (writeIssue/setStatus/postComment from the normalized spec view)
pull tracker → flow (fetchIssue/readStatus/listComments → normalized → fold into spec)
reconcile two-way (3-way body merge + status who-wins + comment append)
```

- **Transport interface** (fn-52.3 Linear, fn-52.7 GitHub implement): `fetchIssue`, `writeIssue`, `listComments`, `postComment`, `readStatus`, `setStatus`, plus the fn-64 dependency-projection pair `listIssueRelations` / `setIssueRelation`. Each maps its wire shape to/from the normalized structs. Defined in [`references/adapter-interface.md`](references/adapter-interface.md).
- **Dependency projection** (fn-64): `projectDepRelations` rides the push + reconcile paths (modelled on `projectReadiness`) and projects a spec's local `depends_on_epics` edges as **blocked-by** tracker relations — transport-blind (R8), additive-only (never deletes a relation flow can't prove it created — R6), completed-blocker-aware (a `done` dep stays a visible historical blocker but never re-gates `ready=true` — R5), and conservative on collision (a ledgered relation a tracker user removed is **deferred + `queued`, never silently recreated** — R6/R10). On the GitHub fallback the `<!-- flow:deps -->` body block is flow-owned and excluded from body-merge divergence (the `trackerBodyForMerge` transform — body-merge.md Step 0.5, R10). Full hook body in [steps.md](steps.md) § projectDepRelations.
- **Reconcile** operates only on the normalized `issue` / `comment` / `status` structs — never a transport detail. The 3-way **body merge** + format translation + scoped conflict is [`references/body-merge.md`](references/body-merge.md) (fn-52.4); **status who-wins** is [`references/status-sync.md`](references/status-sync.md) and **comments/evidence append + dedup** is [`references/comments-sync.md`](references/comments-sync.md) (fn-52.5).
- **Link / unlink ceremony stubs:** first-link base-seeding is handled in fn-52.4 (seed base from current issue body so the first sync isn't a whole-body conflict). **Unlink** wipes state via `sync clear` and posts a one-line detached comment to the issue (`postComment`). Skeleton in [steps.md](steps.md) Phase 5.

Every run emits a receipt (`sync receipt --status …`) and genuine conflicts queue (`sync defer …`) — never block (R11/R12). The transport choice (mcp / graphql / gh / none) is recorded on the receipt; when no transport is reachable, the run is a `noop` + receipt note (never a crash). **Lifecycle runs are event-tagged** (fn-57): the calling skill passes `event: <perEvent-key>` in the invocation, and every receipt that run carries `--event` — the tag `flowctl sync check` audits at end-of-skill. Manual runs carry no event tag (see [steps.md](steps.md) Phase 0).

## Boundaries

- **This is the spine, not the transports or the merge.** Do not implement Linear/GitHub API calls here (fn-52.3/.7) or the 3-way merge / status who-wins (fn-52.4/.5). Define the hooks; leave them as named stubs that delegate.
- **`/flow-next:tracker-sync` is DISTINCT from `/flow-next:sync`** (= plan-sync, `flow-next-sync` skill). Never conflate them. The two are documented side-by-side (doc note lands in fn-52.8).
- **Projection, not coordination** — the tracker never drives flow state or spawns agents. A Symphony-style trigger layer is explicitly out of scope (separable future addition).
- **Dependency projection is strictly additive and flow-authoritative.** `projectDepRelations` NEVER deletes a tracker relation it can't prove it created (ledger / fenced marker — R6), NEVER silently recreates a relation a tracker user removed (collision ⇒ `sync defer` + `queued` — R6/R10), NEVER feeds a projected/completed relation back into `ready=true` gating (R5), and NEVER traverses the dep graph — only direct `depends_on_epics` edges project, no transitive expansion (R8). Tracker→flow dependency *authoring* (declaring deps from the tracker side) is out of scope. The hook is transport-blind — **no Linear-vs-GitHub branching in the skill** (R8); fidelity differences live in the adapters.
