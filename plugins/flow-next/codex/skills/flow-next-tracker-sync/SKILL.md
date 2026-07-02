---
name: flow-next-tracker-sync
description: Project a flow-next spec to a tracker issue (Linear, GitHub, GitLab, or Jira) and reconcile body/status/comments two-way — projection, not coordination. The spec stays the source of truth; the tracker is a co-editable mirror. Use to configure the bridge (discovery ceremony), link a spec to an issue (flow-first push or tracker-first "grab issue X and spec it"), push/pull/reconcile, or unlink. Triggers on /flow-next:tracker-sync, "sync to linear", "push this spec to the tracker", "grab issue X and spec it", "link this spec to the issue", "reconcile with the tracker". NOT /flow-next:sync (that is plan-sync, a different skill).
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Task
---

# flow-next-tracker-sync — project a spec to a tracker, reconcile two-way

The `.flow/specs/<id>.md` spec is the source of truth and the quality layer; the tracker (Linear, GitHub, GitLab, or Jira) is a **co-editable mirror** for teams that must live in it. This skill is **projection, not coordination** — the tracker mirrors the spec (body, status, comments all sync two-way) but never drives flow state or spawns agents (see the decision record at `.flow/memory/.../tracker-sync-is-projection-not-*`).

This skill is the **spine**: the discovery ceremony, the spec↔issue grain, the identity/naming alias, and a **transport-blind** push/pull/reconcile orchestration skeleton. It does NOT contain transport code or merge logic — those plug in via the interface defined here:

- **Transports** (`fetchIssue` / `writeIssue` / `listComments` / `postComment` / `readStatus` / `setStatus`) are implemented by the Linear, GitHub, GitLab, and Jira adapters. This skill calls them through the normalized interface; it never sees a wire shape. The **Linear adapter is a detect-best-available transport ladder** (MCP → GraphQL → no-op) — see [`references/linear-ladder.md`](references/linear-ladder.md); the **GitHub adapter** is the headless-robust `gh` transport (single rung + no-op, reduced-fidelity status) — see [`references/github.md`](references/github.md); the **GitLab adapter** is the headless-robust `glab` transport (`glab` CLI → raw-REST token fallback → no-op, reduced-fidelity status) — see [`references/gitlab.md`](references/gitlab.md); the **Jira adapter** is the REST transport (Cloud `/rest/api/3` + ADF → DC/Server `/rest/api/2` → no-op, workflow-aware status via the transitions API, NO MCP) — see [`references/jira.md`](references/jira.md).
- **Reconcile** operates only on the **normalized payload structs** (`issue` / `comment` / `status`) the adapters exchange. The agentic 3-way **body merge** + format translation + scoped conflict is in [`references/body-merge.md`](references/body-merge.md); the per-field **status who-wins** is [`references/status-sync.md`](references/status-sync.md) and **comments/evidence append + dedup** is [`references/comments-sync.md`](references/comments-sync.md). The interface is defined in `references/adapter-interface.md`.

**Read [steps.md](steps.md) for the full phase-by-phase execution.** Read [`references/adapter-interface.md`](references/adapter-interface.md) for the transport interface + normalized payload contract, [`references/body-merge.md`](references/body-merge.md) for the agentic 3-way body merge / format translation / scoped conflict, [`references/status-sync.md`](references/status-sync.md) for the per-field status who-wins + deadlock fallback, [`references/comments-sync.md`](references/comments-sync.md) for comments/evidence two-way append + dedup, [`references/identity.md`](references/identity.md) for the hybrid id model (tracker-first canonical vs flow-first alias), [`references/linear-ladder.md`](references/linear-ladder.md) (→ [`linear-mcp.md`](references/linear-mcp.md), [`linear-graphql.md`](references/linear-graphql.md)) for the Linear transport ladder, [`references/github.md`](references/github.md) for the GitHub adapter (`gh` transport, reduced-fidelity status), [`references/gitlab.md`](references/gitlab.md) for the GitLab adapter (`glab` CLI → raw-REST token fallback, reduced-fidelity status), and [`references/jira.md`](references/jira.md) for the Jira adapter (REST `/rest/api/{3,2}` token transport, ADF body translation, workflow-aware status via the transitions API).

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

**Inline skill (no `context: fork`)** — `plain-text numbered prompt` must stay reachable across phases. Subagents can't call plain-text numbered prompts (Claude Code issues #12890, #34592). The discovery ceremony (Phase 1) and genuine-conflict surfacing (body-merge / comments-sync) both require user choice in interactive mode.

## flowctl owns plumbing; the skill owns judgment

The canonical flow-next split. flowctl provides atomic, deterministic helpers; this skill, running on the host agent, does the API calls / reconciliation / asking:

| flowctl owns (deterministic) | the skill owns (host-agent judgment) |
|---|---|
| `sync active` — is the bridge active (value-checked)? | discovery ceremony: probe signals, surface, ASK, confirm |
| `sync list-unsynced` / `list-stale` — enumerate | decide which specs to push/pull this run |
| `sync set-tracker-id` / `set-last-synced` / `set-merge-base` — atomic state write | call the transport (`fetchIssue` / `writeIssue` / …) |
| `sync clear` — unlink, wipe state atomically | semantic 3-way body merge (body-merge.md), status who-wins + comment dedup (status-sync.md / comments-sync.md) |
| `sync receipt` / `sync defer` — proof-of-work + queue | translate flow-structured ↔ tracker free-form |
| `sync check-collisions` — flag shared tracker ids | decide create-vs-link on ambiguity; ASK the user |
| `spec create --tracker-first` / `config set` — id + config write | choose the hybrid id origin (tracker-first vs flow-first) |
| `sync list-dep-relations` — enumerate `depends_on_epics` edges + resolved tracker links + local dep status | `projectDepRelations`: drive `setIssueRelation` / `listIssueRelations`, warn on unlinked deps, keep completed blockers visible, defer the missing-remotely collision (steps.md § projectDepRelations) |
| `ready --all` — flow-side open specs + eligibility facts | **`list-open`**: union in the tracker-only items via `listOpenIssues`, no-op when `readyState` unset; **`list-relations`**: READ one issue's dep relations via `listIssueRelations` (dep-ordering edges, never a write); **`question`**: author the stable question-valve anchor + post via `postComment`, detect/import the matched answer (steps.md Phase 7) |
| `sync set-dep-relation` / `clear-dep-relation` — atomic provenance-ledger write | decide *which* edges are ours-to-touch (ledger / fenced-block provenance — never clobber a manual relation) |

Never reimplement a flowctl helper inline; never push a merge/judgment decision into flowctl.

## Discovery ceremony (R2) — detect / surface / ask / never-assume

The bridge is **off until explicitly enabled**. The ceremony probes six signals, surfaces present AND absent, ASKS, and writes config **only on confirmation** — with provenance. No-signal ⇒ nothing written; `enabled` stays `false`. Never assume. But **once the user confirms, enabling is opt-OUT, not opt-in**: the ceremony activates the whole pipeline (every `perEvent` event) by default — hooking up the bridge means you want it to sync. The user excludes events at ceremony time or turns any off later (`flowctl config set tracker.perEvent.<event> off`). The `get_default_config()` schema default stays `off`, so a bare `enabled=true` set WITHOUT the ceremony activates **no lifecycle-event sync** (every `perEvent` event stays dormant) — only the ceremony's explicit writes activate them. (Two exceptions are unconditional whenever the bridge is active — no per-event gate, by design: (1) make-pr's PR↔issue link **and its In Review status push** (R2 — an open PR is the In Review rung, riding the same Diffs-powering link path); (2) **`land.merged`** (R10 — a real merge is the SOLE event that projects terminal `Done`, gated on the GitHub `MERGED` probe; leaving it opt-in would strand boards at In Review post-merge).)

Probe these six signals (detection lives in the skill, not flowctl):

| Signal | Probe | Means |
|---|---|---|
| Linear MCP registered | the host's MCP/tool list contains a Linear server (e.g. `*Linear*` tools like `save_issue`) | interactive Linear transport available (OAuth handled) |
| `LINEAR_API_KEY` | `[ -n "$LINEAR_API_KEY" ]` | headless Linear GraphQL transport available |
| GitHub auth | `gh auth status` exits 0 | headless GitHub transport available |
| GitLab auth / token | `glab auth status` exits 0, or `GITLAB_TOKEN` / `CI_JOB_TOKEN` set | GitLab transport available (`glab` primary → REST token fallback; self-managed hosts honored — references/gitlab.md) |
| Jira REST + token | `JIRA_BASE_URL` set, plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` OR self-hosted DC/Server `JIRA_PAT` | Jira REST transport available — **offered** (Cloud `/rest/api/3` + API-token, DC/Server `/rest/api/2` + PAT; single rung + no-op, NO MCP — references/jira.md). A bare `*.atlassian.net` host with no credential is surfaced but can't be offered |

Resolution model is **env > config > ASK**, mirroring `cmd_review_backend`: if the transport/tracker is already decided by env or config, don't re-ask. Steps in [steps.md](steps.md) Phase 1.

**On confirmation only**, write via `flowctl config set` (dot-paths are safe — config keys are nested):

```bash
$FLOWCTL config set tracker.enabled true
$FLOWCTL config set tracker.type linear # or github / gitlab / jira
$FLOWCTL config set tracker.provenance "discovery ceremony 2026-06-03; confirmed by <who>; signals: MCP+API_KEY"
# DEFAULT-ON (opt-out): activate the whole pipeline — skip only what the user excluded.
$FLOWCTL config set tracker.perEvent.capture reconcile
$FLOWCTL config set tracker.perEvent.interview reconcile
$FLOWCTL config set tracker.perEvent.plan reconcile
$FLOWCTL config set tracker.perEvent.work.firstClaim push
$FLOWCTL config set tracker.perEvent.work.done comment
$FLOWCTL config set tracker.perEvent.makePr comment
$FLOWCTL config set tracker.perEvent.resolvePr comment
$FLOWCTL config set tracker.perEvent.completionReview comment # comment-shaped (verdict + R-ID coverage) — NEVER terminal Done; land.merged is the sole Done driver (active-by-default, no perEvent seed needed)
# Jira (tracker.type jira) — write the site + project key, and PERSIST the
# deployment shape the probe detected (auth scheme + api version) so runtime
# never re-infers. Credentials stay in env (read each run), never written here.
$FLOWCTL config set tracker.perTracker.baseUrl "https://acme.atlassian.net" # Jira: the site base (JIRA_BASE_URL env overrides; the persisted value is the default)
$FLOWCTL config set tracker.perTracker.projectKey "PROJ" # Jira: the project key (JQL / listOpenIssues scope)
$FLOWCTL config set tracker.perTracker.authScheme "cloud-basic" # Jira: cloud-basic (Cloud email:API_TOKEN) | bearer-pat (DC/Server PAT) — detected from the credential/host, persisted
$FLOWCTL config set tracker.perTracker.apiVersion "3" # Jira: 3 (Cloud, ADF) | 2 (DC/Server) — the REST endpoint family
$FLOWCTL config set tracker.perTracker.statusMap "$DERIVED_STATUSMAP_JSON" # Jira: normalized→{id|name}, AUTO-DERIVED from the project workflow — WITHOUT it setStatus defers EVERY status (steps.md / jira.md § Status); write {} + warn the user when no creds
$FLOWCTL sync active --json # confirm active: true
```

> **Auth scheme + api version are detected from the credential/deployment and PERSISTED at the ceremony** — a `*.atlassian.net` `baseUrl` ⇒ `cloud-basic` + apiVersion `3`. A **custom domain** (a Cloud tenant on an Atlassian custom domain, OR self-hosted — neither ends in `.atlassian.net`) can't be told apart by URL, so infer from the **credential**: only `JIRA_EMAIL`+`JIRA_API_TOKEN` ⇒ `cloud-basic` + `3`; only `JIRA_PAT` ⇒ `bearer-pat` + `2`. If BOTH `JIRA_API_TOKEN` and `JIRA_PAT` are present AND the deployment is genuinely ambiguous, **ASK** (never silently guess), then persist. Runtime reads only the persisted `authScheme` — precedence is decided once here, never re-raced per run (mirrors `cmd_review_backend`).

Confirm the result with `flowctl sync active --json` (must report `active: true` once enabled/type are set). Negative path: user declines ⇒ write nothing; `sync active` stays `active: false`.

## Flexible entry (R2) — no fixed starting point

Two entry flows, both attach sync state **on link** (never impose where the user must start):

1. **Author-in-flow-then-push (flow-first):** a `fn-NN` spec already exists (capture/interview/plan authored it). Push creates the tracker issue, then `sync set-tracker-id` attaches the issue UUID + `--identifier WOR-17` + `--url`. Keep the `fn-NN` id; store the tracker key as a resolvable alias.
2. **Link-existing-issue (tracker-first): "grab issue X and spec it."** Fetch the issue via an already-installed transport, create the spec **keyed by the tracker key** (`flowctl spec create --tracker-first --tracker-identifier WOR-17`), seed the merge base from the current issue body, first pass is pull-only. **Tracker-first needs an alpha-prefixed `KEY-N` key — Linear `WOR-17` AND Jira `PROJ-123` (both `KEY-N`, both tracker-first capable).** GitHub `#N` / GitLab `<project>#<iid>` are NOT `KEY-N`, so they go flow-first only (see steps.md Phase 2). See [steps.md](steps.md) Phase 2 (link) and [`references/identity.md`](references/identity.md).

## Grain (R3) — one spec ↔ one issue

- **One flow spec maps to one tracker issue.** The tracker UUID is the durable dedupe key (`sync set-tracker-id`); `sync check-collisions` flags any UUID shared by two specs.
- **Tasks stay flow-local by default** — NEVER auto-created as tracker sub-issues.
- **Optional checklist-in-body render** — tasks MAY be rendered as a checklist inside the issue body (not sub-issues). **Scoping decision: owned by the body-merge layer (body-merge.md).** The scaffold defines the grain (one-to-one, tasks-local); the checklist is a body-format concern. The skeleton exposes a `renderTaskChecklist` hook on the body-sync path (off by default) so the body-merge layer can opt it in without reshaping the spine.

## Identity / naming (R16) — hybrid via flowctl's id layer

The link/create ceremony assigns the canonical id through flowctl's id generator. **Never rename an existing spec.** Full rules in [`references/identity.md`](references/identity.md); the headline:

- **Tracker-first link → canonical spec id `wor-17-slug`, canonical tasks `wor-17-slug.M`.** The bare forms `wor-17` / `wor-17.M` are aliases, resolved by flowctl's widened resolver (`flowctl show wor-17`, `work wor-17`, … all resolve). Branch follows the canonical id. Use `flowctl spec create --tracker-first --tracker-identifier WOR-17`.
- **Flow-first → keep `fn-NN-slug`.** Store the tracker key in the single `tracker.identifier` field (R4, display form `WOR-17`) as a resolvable alias via `sync set-tracker-id --identifier WOR-17`, and write the back-reference into the issue (`flow:<id>` label / `[<id>]` title-prefix).
- **Resolution is flowctl's job, not the scaffold's.** The skill just calls flowctl and relies on the widened resolver. Surface `identifier` in sync listings (see Phase 6 in [steps.md](steps.md)).

## Orchestration skeleton — transport-blind

Three sync operations across three layers, all transport-blind. The skeleton routes; the named hooks plug in later:

```
push flow → tracker (writeIssue/setStatus/postComment from the normalized spec view)
pull tracker → flow (fetchIssue/readStatus/listComments → normalized → fold into spec)
reconcile two-way (3-way body merge + status who-wins + comment append)
```

- **Transport interface** (the Linear / GitHub / GitLab / Jira adapters implement): `fetchIssue`, `writeIssue`, `listComments`, `postComment`, `readStatus`, `setStatus`, the dependency-projection pair `listIssueRelations` / `setIssueRelation`, plus the backlog enumeration method `listOpenIssues(filter) → issue[]` (the promoted-lane scan backlog mode unions in — Linear, GitHub, GitLab + Jira). Each maps its wire shape to/from the normalized structs. Defined in [`references/adapter-interface.md`](references/adapter-interface.md).
- **Backlog-mode named ops**: `list-open` (enumerate the promoted lane via `listOpenIssues`), `list-relations <tracker-id>` (READ one issue's dependency relations via `listIssueRelations` for dep-ordering — read-only, never a write), and `question <spec-id | tracker-id>` (post the async question-valve comment behind a stable anchor) — skill-level + transport-blind, invoked per-tick by `/flow-next:pilot` backlog mode. Bodies in [steps.md](steps.md) Phase 7; all run under the autonomy gate (never `plain-text numbered prompt`).
- **Dependency projection**: `projectDepRelations` rides the push + reconcile paths (modelled on `projectReadiness`) and projects a spec's local `depends_on_epics` edges as **blocked-by** tracker relations — transport-blind (R8), additive-only (never deletes a relation flow can't prove it created — R6), completed-blocker-aware (a `done` dep stays a visible historical blocker but never re-gates `ready=true` — R5), and conservative on collision (a ledgered relation a tracker user removed is **deferred + `queued`, never silently recreated** — R6/R10). On GitHub's fenced fallback and on GitLab (every tier — the durable direction source alongside the native link, and the sole one on the degrade) the `<!-- flow:deps -->` body block is flow-owned and excluded from body-merge divergence (the `trackerBodyForMerge` transform — body-merge.md Step 0.5, R10). Full hook body in [steps.md](steps.md) § projectDepRelations.
- **Reconcile** operates only on the normalized `issue` / `comment` / `status` structs — never a transport detail. The 3-way **body merge** + format translation + scoped conflict is [`references/body-merge.md`](references/body-merge.md); **status who-wins** is [`references/status-sync.md`](references/status-sync.md) and **comments/evidence append + dedup** is [`references/comments-sync.md`](references/comments-sync.md).
- **Link / unlink ceremony stubs:** first-link base-seeding is handled by the body-merge layer (body-merge.md — seed base from current issue body so the first sync isn't a whole-body conflict). **Unlink** wipes state via `sync clear` and posts a one-line detached comment to the issue (`postComment`). Skeleton in [steps.md](steps.md) Phase 5.

Every run emits a receipt (`sync receipt --status …`) and genuine conflicts queue (`sync defer …`) — never block (R11/R12). The transport choice (mcp / graphql / gh / glab / rest / none) is recorded on the receipt; when no transport is reachable, the run is a `noop` + receipt note (never a crash). **Lifecycle runs are event-tagged**: the calling skill passes `event: <perEvent-key>` in the invocation, and every receipt that run carries `--event` — the tag `flowctl sync check` audits at end-of-skill. Manual runs carry no event tag (see [steps.md](steps.md) Phase 0).

## Boundaries

- **This is the spine, not the transports or the merge.** Do not implement Linear/GitHub/GitLab/Jira API calls here (the adapter references) or the 3-way merge / status who-wins (body-merge.md / status-sync.md / comments-sync.md). Define the hooks; leave them as named stubs that delegate.
- **`/flow-next:tracker-sync` is DISTINCT from `/flow-next:sync`** (= plan-sync, `flow-next-sync` skill). Never conflate them. The two are documented side-by-side in `docs/tracker-sync.md`.
- **Projection, not coordination** — the tracker never drives flow state or spawns agents. A Symphony-style trigger layer is explicitly out of scope (separable future addition).
- **Dependency projection is strictly additive and flow-authoritative.** `projectDepRelations` NEVER deletes a tracker relation it can't prove it created (ledger / fenced marker — R6), NEVER silently recreates a relation a tracker user removed (collision ⇒ `sync defer` + `queued` — R6/R10), NEVER feeds a projected/completed relation back into `ready=true` gating (R5), and NEVER traverses the dep graph — only direct `depends_on_epics` edges project, no transitive expansion (R8). Tracker→flow dependency *authoring* (declaring deps from the tracker side) is out of scope. The hook is transport-blind — **no per-tracker (Linear / GitHub / GitLab / Jira) branching in the skill** (R8); fidelity differences live in the adapters.
- **Backlog-mode ops are skill-level, never flowctl transport**: `list-open` / `question` enumerate / post via the agentic adapter ladder — flowctl has no tracker transport and must not grow one. A tracker-only `question` (no spec) is exempt from the spec-id sync receipt; its parked/answered state lives in the tracker comments.
