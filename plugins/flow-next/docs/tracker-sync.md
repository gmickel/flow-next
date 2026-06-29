# Tracker sync bridge

Project a flow-next spec to a tracker issue (Linear, GitHub, GitLab, or Jira) and reconcile body / status / comments two-way. Drives the `/flow-next:tracker-sync` skill plus the `flowctl sync …` plumbing.

> **`/flow-next:tracker-sync` is NOT `/flow-next:sync`.** `/flow-next:sync` is **plan-sync** — it updates downstream *task* specs after implementation drift inside flow-next (`flow-next-sync` skill). `/flow-next:tracker-sync` is the **external tracker bridge** documented here. The two share a verb and nothing else.

## Projection, not coordination

The `.flow/specs/<id>.md` spec is the **single source of truth** and the quality layer. The tracker is a **co-editable mirror** for teams that must live in it. The bridge is **projection**, not **coordination**:

- The tracker **mirrors** the spec. Body, status, and comments all sync **two-way** — a vague PM-authored issue can be pulled in, fleshed out in flow-next, and synced back.
- The tracker **never drives flow state or spawns agents**. There is no board-status-flips-fire-an-agent control plane (that is OpenAI Symphony's model). Spec stays where work is authored, enriched, and executed.

"Not coordination" means the tracker is not a control plane — it does **not** mean one-way. The decision record is `knowledge/decisions/tracker-sync-is-projection-not-2026-06-01` (survives `rm -rf .flow/` only if mirrored into `STRATEGY.md` / a decision entry that is committed). A Symphony-style board-triggered per-spec executor is a **separable future addition** — explicitly out of scope here.

The contrast with Symphony: there, Linear is the canonical finite-state machine that spawns agents off a thin per-issue `WORKFLOW.md`. flow-next's pitch is "Symphony, but with real specs + re-anchoring + receipts" — the spec carries the weight, the tracker is a downstream window.

## Setup — the discovery ceremony

**Configuring the bridge is its own one-time step, separate from `/flow-next:setup`.** `/flow-next:setup` installs flowctl + project docs and **never touches tracker config** — that keeps the zero-dep base install clean for the (many) users who run no project-management software. The bridge is set up by running **`/flow-next:tracker-sync`**, whose **discovery ceremony** writes the config. (`/flow-next:setup` proposes running it as an optional next step when it finishes, so it's discoverable without being imposed.)

The bridge is **off until explicitly enabled** (`tracker.enabled` defaults `false`, `tracker.type` defaults `null`). The discovery ceremony **detects → surfaces → asks → never assumes**, and writes config **only on confirmation**, with provenance. No signal ⇒ nothing written.

Six probed signals:

| Signal | Probe | Means |
|---|---|---|
| Linear MCP registered | host MCP/tool list contains a Linear server (e.g. `*Linear*` tools) | interactive Linear transport available (OAuth handled) |
| `LINEAR_API_KEY` | `[ -n "$LINEAR_API_KEY" ]` | headless Linear GraphQL transport available |
| GitHub auth | `gh auth status` exits 0 | headless GitHub transport available |
| GitLab auth / token | `glab auth status` exits 0, or `GITLAB_TOKEN` / `CI_JOB_TOKEN` set | GitLab transport available (`glab` CLI primary → raw-REST token fallback; self-managed hosts honored) |
| Jira REST + token | `JIRA_BASE_URL` set, plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` OR self-hosted DC/Server `JIRA_PAT` | Jira REST transport available — **offered** (Cloud `/rest/api/3` + API-token, DC/Server `/rest/api/2` + PAT; single rung + no-op, NO MCP). A bare `*.atlassian.net` host with no credential is surfaced but can't be offered |

Resolution is **env > config > ASK** (mirrors `flowctl review-backend`): if env/config already decides the transport, the ceremony doesn't re-ask. On confirmation the skill writes via `flowctl config set tracker.…` and verifies with `flowctl sync active --json` (must report `active: true`). The bridge is active iff raw `tracker.enabled == true` **OR** raw `tracker.type ∈ {linear, github, gitlab, jira}`.

For a **GitLab** tracker the ceremony additionally writes `tracker.perTracker.project` (the group/sub-group/project path, e.g. `group/subgroup/project` — the GitLab analog of GitHub's `repo`) and, for self-managed hosts, `tracker.perTracker.host`. flow-next stores the literal path and derives the URL-encoded form (`group%2Fsubgroup%2Fproject`) once for the API, never double-encoding. **Zero special setup** — GitLab works from an existing `glab auth login` session OR a `GITLAB_TOKEN`/`CI_JOB_TOKEN` already present (gh-style), with no flow-next-specific provisioning; the spec-first floor applies when neither is present.

For a **Jira** tracker the ceremony writes `tracker.perTracker.baseUrl` (the site, e.g. `https://acme.atlassian.net`) + `tracker.perTracker.projectKey` (the `PROJ` key), and **persists the deployment shape the probe detected** — `tracker.perTracker.authScheme` (`cloud-basic` = Cloud HTTP-basic `email:API_TOKEN`; `bearer-pat` = DC/Server `Authorization: Bearer <PAT>`) and `tracker.perTracker.apiVersion` (`3` Cloud `/rest/api/3` ADF; `2` DC/Server `/rest/api/2`) — so runtime never re-infers (decided once, like `review-backend`). An opt-in `tracker.perTracker.sslVerify=false` (env `JIRA_SSL_VERIFY=false`) covers self-hosted internal-CA / self-signed certs; never silent. **Credentials are read from env each run, never stored in flow state.** **Zero special setup** — a standard Jira credential the company already issues (Cloud API token or DC/Server PAT) — no OAuth app, MCP server, webhook, or Connect/Forge app; the spec-first floor applies when no credential is present. NO MCP rung: the official Atlassian MCP can't transition status / update fields / set links (the writes a two-way sync needs) and the community MCP is a redundant PAT-wrapper (the fn-70 transport decision).

After the config writes, the ceremony asks **one optional, skippable readiness question** (1.12.0+): *which tracker workflow state means "ready for work"?* — a Linear workflow-state name (discovered from the team's states, with a "Ready"-looking name recommended), a GitHub label (suggested `ready`, pre-created idempotently), on GitLab a label (suggested `ready`, pre-created idempotently; GitLab has no rich workflow, so readiness is a label like GitHub), or — on **Jira** — a workflow **status name** (like Linear; validated against the project's statuses when a credential is present, else skip → no-op backlog lane). The answer is stored as `tracker.readyState`; skipping writes nothing and leaves the readiness gate dormant. See [Readiness projection](#readiness-projection--trackerreadystate--local-ready-flag) below.

## Two entry flows — no fixed starting point

Both attach sync state **on link**:

1. **Author-in-flow-then-push (flow-first).** A `fn-NN` spec already exists. Push creates the tracker issue, then `flowctl sync set-tracker-id` attaches the issue UUID + `--identifier WOR-17` + `--url`. The `fn-NN` id is kept; the tracker key becomes a resolvable alias.
2. **Link-existing-issue (tracker-first): "grab issue X and spec it."** Fetch the issue, create the spec **keyed by the tracker key** (`flowctl spec create --tracker-first --tracker-identifier WOR-17`), seed the merge base from the current issue body, first pass is pull-only. **Tracker-first needs an alpha-prefixed `KEY-N` key — Linear `WOR-17` AND Jira `PROJ-123`** (both `KEY-N`: alpha key + number). It mints the canonical spec id from it (`wor-17-slug` / `proj-123-slug`), and bare `wor-17` / `proj-123` resolve as aliases. **GitHub `#N` and GitLab `<project>#<iid>` are NOT `KEY-N`** (no alpha key / slashes + `#`), so `cmd_spec_create`'s strict validator rejects them — **grab those flow-first**: create an `fn-NN` spec, then `flowctl sync set-tracker-id fn-NN <issue-id> --identifier <key> --url <url>` (the link-time validator accepts the issue ref), as in flow #1. So **Jira joins the tracker-first camp like Linear** — BOTH entry flows work — distinct from GitHub/GitLab flow-first-only.

## Hybrid id model (R16)

The two id schemes **coexist**; resolution is provided by flowctl's widened resolver (case-insensitive). **Ids NEVER change — there is no rename-on-push.**

| | Tracker-first (canonical) | Flow-first (alias) |
|---|---|---|
| canonical spec id | `wor-17-slug` | `fn-NN-slug` (unchanged) |
| canonical task ids | `wor-17-slug.M` | `fn-NN-slug.M` |
| branch | `wor-17-slug` | `fn-NN-slug` |
| bare aliases | `wor-17` / `wor-17.M` resolve to the canonical slug id | `WOR-17` (stored in `tracker.identifier`) resolves to `fn-NN-slug` |
| create / link | `flowctl spec create --tracker-first --tracker-identifier WOR-17` | `flowctl sync set-tracker-id fn-NN-slug <uuid> --identifier WOR-17 --url <url>` |

- **Resolution is case-insensitive.** `flowctl show wor-17`, `work wor-17`, `plan wor-17`, tasks `wor-17.M` all resolve. `tracker.identifier` stores the **display form** (`WOR-17`); the canonical id derives from the lowercase key (`wor-17-slug`).
- **The native `fn-` prefix is reserved** for the sequential scheme; tracker-key resolution is tried only after the `fn-` path misses. Enumeration sees tracker-key specs, but native `fn-N` allocation counts `fn-*` only — a `wor-9999` never bumps the next `fn`.
- **One tracker team / workspace per repo.** The bridge assumes a single team key so a bare `wor-17` resolves unambiguously. Cross-workspace same-key collision (two teams both keyed `WOR`) is out of scope.
- **No rename-on-push.** Existing spec/task ids, branches, and dep edges are never mutated on link; the tracker key is added as a resolvable handle, not a replacement. `flowctl spec set-title` on a tracker-linked spec updates the title only — it does **not** re-slug the id, branch, or files.

The widened resolver / canonicalizer + the origin-branched id generator live in `flowctl.py` — see [`architecture.md`](architecture.md).

## Grain — one spec ↔ one issue

- **One flow spec maps to one tracker issue.** The tracker UUID is the durable dedupe key (`flowctl sync set-tracker-id`); `flowctl sync check-collisions` flags any UUID shared by two specs.
- **Tasks stay flow-local by default** — never auto-created as tracker sub-issues. An optional checklist-in-body render (tasks as a body checklist, not sub-issues) is a body-format concern off by default.

## Sync-state schema

State lives in the existing `.flow/specs/<id>.json` sidecar (not frontmatter — merge-base body snapshots would bloat the markdown). Per-spec `tracker` block:

| Field | Meaning |
|---|---|
| `id` | tracker UUID — the durable dedupe key |
| `identifier` | display key, e.g. `WOR-17` |
| `url` | issue URL |
| `lastSyncedAt` | ISO timestamp of last real reconciliation (advances on a real reconcile, never on a no-op pull / echo) |
| `baseHashFlow` / `baseHashTracker` | content hashes of each merge-base side (echo fence) |
| `mergeBaseFlow` / `mergeBaseTracker` | the body snapshots themselves — the common ancestor for the agentic 3-way merge |

The **merge base is a paired snapshot at one sync point**: `flowctl sync set-merge-base` requires **both** `--flow`/`--flow-file` AND `--tracker`/`--tracker-file` together (a partial write that pins one half to a stale sync point is rejected). The base is stored in a form comparable to each side so a 3-way merge can compare flow-structured spec against tracker free-form issue.

## Transport ladder

The skill is **transport-blind** — it calls a normalized interface (`fetchIssue` / `writeIssue` / `listComments` / `postComment` / `readStatus` / `setStatus`) and never sees a wire shape. Each adapter detects the **best available transport** and degrades gracefully:

| Adapter | Ladder | Status fidelity |
|---|---|---|
| **Linear** | MCP → GraphQL (`LINEAR_API_KEY`) → no-op | full workflow states |
| **GitHub** | `gh` (single rung) → no-op | reduced fidelity (open/closed) |
| **GitLab** | `glab` CLI → raw-REST `/api/v4` (`GITLAB_TOKEN` / `CI_JOB_TOKEN`) → no-op | reduced fidelity (open/closed) |
| **Jira** | REST `/rest/api/{3,2}` token (Cloud `email:API_TOKEN` / DC-Server `Bearer PAT`) → no-op; **NO MCP** | full workflow states via the transitions API + `statusMap` |

When **no transport is reachable**, the run is a **`noop` + receipt note** — never a crash. The transport actually used (`mcp` / `graphql` / `gh` / `glab` / `rest` / `none`) is recorded on every receipt. (`glab` is GitLab's CLI rung; `rest` is GitLab's raw-REST `/api/v4` token fallback **and** Jira's `/rest/api/{3,2}` token rung — Jira is REST-only, single-rung, no MCP.)

## Lifecycle sync points (on by default — opt-out)

Sync is wired into seven lifecycle skills. **When you hook the bridge up via the `/flow-next:tracker-sync` discovery ceremony, the whole pipeline activates by default** — the point of connecting a tracker is to keep it in sync, so you don't opt in event-by-event. You **opt out** instead: exclude events at ceremony time, or turn any off later with `flowctl config set tracker.perEvent.<event> off`. Leaf values: `off | pull | push | reconcile | comment`.

| Event | Config key | Default op | Fires when |
|---|---|---|---|
| capture | `tracker.perEvent.capture` | `reconcile` | a spec is captured |
| interview | `tracker.perEvent.interview` | `reconcile` | a spec is refined |
| plan | `tracker.perEvent.plan` | `reconcile` | a spec is decomposed into tasks |
| work (first claim) | `tracker.perEvent.work.firstClaim` | `push` | the first task of a spec is claimed |
| work (done) | `tracker.perEvent.work.done` | `comment` | a task completes |
| make-pr | `tracker.perEvent.makePr` | `comment` | a PR is opened (→ issue **In Review** + PR link, unconditional when bridge active — fn-66) |
| resolve-pr | `tracker.perEvent.resolvePr` | `comment` | PR threads are resolved |
| completion review | `tracker.perEvent.completionReview` | `comment` | a spec-completion review runs (verdict + R-ID coverage; **never terminal Done** — fn-66) |
| land (merged) | `tracker.perEvent.land.merged` | `push` | a PR **merges** (→ issue **Done**, the SOLE Done driver, gated on the GitHub `MERGED` probe; **active-by-default** when bridge active — fn-66) |

The lifecycle skills value-check `flowctl sync active` and the specific `perEvent` leaf, short-circuiting cleanly when the bridge is off or an event was opted out — so a no-tracker repo (or an excluded event) costs a single value-check, no transport.

**Observable + forcing (fn-57).** Every lifecycle dispatch is **event-tagged**: the tracker-sync skill writes its receipt with `--event <perEvent-key>` (`work.firstClaim`, `work.done`, `capture`, `makePr`, …), so `.flow/sync-runs/` records which touchpoint each run served. At end-of-skill, **work, capture, and make-pr** run the read-only audit `flowctl sync check <spec-id> --events <triggered-csv> --since <run-anchor>` — independently of the touchpoints themselves, so a wholesale-skipped dispatch block is still caught. An event is `MISSING` iff it triggered this run AND its `perEvent` leaf is enabled AND the bridge is active AND no receipt with a matching `event` tag and `timestamp ≥ --since` exists (any receipt status clears — the check asserts the touchpoint *ran*; the receipt's own status carries success/failure detail). A `MISSING` event is **retro-fired exactly once** — the skill re-dispatches the missed touchpoint via tracker-sync, then re-checks against a fresh `--since` — and the skill's final summary carries a mandatory four-state `Tracker sync:` slot: `OK` | `MISSING:<event> → retro-fired → OK` | `MISSING:<event> (retro-fire failed: <reason>)` | `n/a (bridge inactive)`. An explicit `n/a` proves the check ran; an absent slot is visible as a skipped check. With no tracker configured `sync check` exits silently in constant time — non-tracker repos see no change anywhere.

**Auto-link on first touch (create-if-unlinked).** When a lifecycle event fires for a spec that isn't yet linked — e.g. you went straight to `/flow-next:plan` instead of `/flow-next:capture` — the tracker-sync skill **flow-first-pushes (creates the issue + links it) *before* running the event's operation**, then later events reconcile the now-linked spec (skill `steps.md` §Phase 3 "create-if-unlinked"). That is the point of the opt-out model: an active bridge keeps **every** in-flow-authored spec in sync, not just the ones you remembered to link by hand. The spec ↔ one-issue grain is unchanged — tasks never become sub-issues. Only `unlink` no-ops on an unlinked spec; every other op creates-then-syncs (and still no-ops cleanly if no transport is reachable).

**Activation is ceremony-gated, not flag-gated.** The config *schema* default for every `perEvent` leaf stays `off`, so a bare `tracker.enabled=true` set by hand or a script — without running the discovery ceremony — fires **no lifecycle-event sync** (every `perEvent` event stays dormant). Only the ceremony's explicit per-event writes (or your own `config set`) turn events on. This keeps the accidental-enable guard while making the *intended* path (run the ceremony) sync everything. **The two things that are *not* gated this way are make-pr's PR↔issue link (+ In Review) and `land.merged`'s Done-on-merge** — both unconditional whenever the bridge is active (the exceptions documented just below), so a bare `enabled=true` plus a linked spec will still add a `Ref` line + move the issue to In Review on the next make-pr, and move it to Done on a confirmed merge. The make-pr linkage is cheap, conflict-free, and the whole point (Linear Diffs); the land.merged Done is merge-evidence-gated so it only fires for genuinely shipped work. Neither mutates the spec beyond the linked issue's status.

**Two unconditional paths when the bridge is active (fn-66).** Some status transitions are too important to leave opt-in:

1. **make-pr — PR link + In Review.** make-pr always links the new PR to its tracker issue *and* moves the issue to **In Review** when `sync active` and the issue is linked — it does **not** require opting `makePr` in. An open PR *is* the In Review lifecycle rung (`flowToNormalized(spec, open) → in-review`, non-terminal), and the link powers Linear Diffs — both ride the same unconditional path. The `perEvent.makePr` leaf still governs any *extra* make-pr sync (e.g. an optional breadcrumb comment). make-pr additionally **verifies the ref landed** post-create (§4.6b): it fetches the LIVE PR body via `gh pr view --json body` and, when the `Ref <identifier>` line is absent (e.g. an agent hand-rolled `gh pr create` and bypassed the deterministic append), repairs it append-only via `gh pr edit` — mechanical, idempotent, fully non-fatal.
2. **land — Done on merge.** `land.merged` is **active-by-default** when the bridge is active and is the **SOLE** driver of the terminal `Done` state. A real merge is the only event that legitimately projects "shipped", so leaving it opt-in would strand boards at In Review forever after a merge. The terminal write self-checks the GitHub `MERGED` probe (the merge-evidence invariant) — no path writes `Done` without it. The `perEvent.land.merged` leaf, if set, only tunes the optional verdict comment, never the (MERGED-gated) status.

These are the only two unconditional touchpoints; everything else stays `perEvent`-gated.

### MISSING after retro-fire — recovery

A `Tracker sync: MISSING:<event> (retro-fire failed: <reason>)` summary line means the touchpoint didn't fire AND the one bounded retro-fire couldn't recover it — typically no reachable transport (MCP server down, no `LINEAR_API_KEY`, `gh` unauthenticated). The primary work is unaffected: tracker sync is best-effort and never blocks, so the task is done / the PR is open. To recover by hand:

1. **Read the failure reason** from the run's receipts: `ls -t .flow/sync-runs/sync-<spec-id>-*.json | head -3` — the `status` (`noop` / `errored`) and `note` fields on the event-tagged receipt say why it failed.
2. **Once transport returns**, re-fire the missed touchpoint manually via the skill: `/flow-next:tracker-sync push <spec-id>` for the status event (`work.firstClaim`), or the matching `comment <spec-id>` op for comment events (`work.done`, `makePr`, and `work.completionReview` — the last posts only a verdict + R-ID coverage comment, never a terminal status per fn-66).
3. **Verify**: `flowctl sync check <spec-id> --events <event> --since <retro-fire-time>` now prints `OK:<event>`.

## Linear Diffs — review the PR inside the issue

[Linear Diffs](https://linear.app/docs/diffs) (GA May 2026) renders a GitHub PR's diff, file changes, checks, and inline review threads directly on the Linear issue, and lets you approve / request changes / merge from Linear. flow-next makes your PRs **Diffs-ready automatically** when `tracker.type == linear`:

- **What flow-next does:** make-pr puts a **non-closing** `Ref WOR-N` line in the PR body (make-pr §4.6a) so Linear's GitHub integration auto-links the PR to the issue — which is exactly what makes the diff render. On the GraphQL transport it also creates the rich PR attachment (`attachmentLinkURL`) for status sync. *Non-closing* (`Ref`, not `Fixes`) is deliberate: the PR links + renders as a diff but does **not** auto-complete the Linear issue on merge — flow-next's `land.merged` touchpoint owns the `Done` transition (fn-66), gated on a GitHub-confirmed `MERGED` probe. (Pre-fn-66 this said "spec-completion-review owns the Done transition" — that was the bug FLOW-15 caught: completion review is *local* completion, not merge evidence, so it could close the issue before the PR merged. Completion review now posts only a verdict comment + at most `In Review`; `Done` is reserved for a merged PR.)
- **What you must enable (one-time, Linear-side — flow-next can't set these):** the Linear **GitHub integration with code access** to the repo, your **personal GitHub connection**, and **"Enable code reviews"** in Linear settings. Without them the PR still links and status still syncs; only the rendered diff view needs them.
- **GitHub / GitLab / Jira tracker:** no Linear Diffs — the PR is cross-linked natively (`Refs #N` on GitHub; `Ref <project>#<iid>` on GitLab; a **remote link** — `POST /issue/{key}/remotelink`, with a PR-URL comment fallback — on Jira, since Jira has neither PR auto-linkify nor `gh`) and review happens on the host.

## Reconciliation — who-wins

- **Body** — agentic host-agent semantic **3-way merge** against the `lastSyncedAt` merge-base snapshot, translating between flow's structured spec and the tracker's free-form issue. Only **genuine contradictions** surface; confident merges proceed.
- **Status** — per-field **who-wins** ladder. The collision/deadlock case is evaluated **before** single-field terminal-wins rules (a `tracker=done × flow=…` deadlock must fall to `conflictTiebreak`, not be silently overwritten by terminal-wins). Tiebreak is `tracker.conflictTiebreak` (`flow-wins | tracker-wins | always-ask`, default `always-ask`).
- **Comments / evidence** — two-way **append** with dedup; neither side overwrites the other.

## Readiness projection — `tracker.readyState` → local `ready` flag

When `tracker.readyState` is configured (the optional ceremony question above), every operation that reads the issue (`pull` / `reconcile`) projects the configured tracker state onto the local spec [`ready` flag](flowctl.md#spec-ready--spec-unready) — giving readiness a **single local read path** whether it's human-set or tracker-driven (1.12.0+, fn-58).

- **One-way pull, tracker authoritative.** Readiness is projected tracker → local only — the local `ready` flag is never pushed to the tracker (no `setStatus`, no label add/remove). A local `flowctl spec ready` on a tracker-connected repo is overwritten by the next sync; tracker users set readiness on the board (which is why capture/interview's mark-ready prompt is gated off when `readyState` is configured).
- **Match semantics.** Linear: case-insensitive trimmed match on the workflow-state **name** (names, not `state.type` — a custom "Ready" state is typically `type=unstarted`, so type alone can't distinguish Todo from Ready). GitHub: the `readyState` **label** — present on the issue ⇒ `ready=true`, absent ⇒ `ready=false` (absence is a normal state; un-labeling IS how a GitHub user un-readies a spec). GitLab: identical label semantics to GitHub — the `readyState` **label** present ⇒ `ready=true`, absent ⇒ `ready=false` (GitLab has no rich workflow, so readiness is a label). Jira: like Linear, a case-insensitive trimmed match on the workflow-**status name** (`status.raw` = `fields.status.name`, never `statusCategory`) — the raw Jira status name, validated to exist in the project at ceremony time.
- **Change-only receipts.** The projection applies via the idempotent `spec ready`/`unready` toggles and emits an event-tagged receipt **only when the local flag actually changes** — silent on a no-op echo (mirrors the `lastSyncedAt` advance-only-on-real-reconciliation rule).
- **Stale-config degradation.** A configured state name / label that no longer resolves on the tracker (renamed/deleted) ⇒ **warn + `noop` receipt + flag untouched + the sync continues** — one bad knob never aborts the run, and a stale `readyState` must not silently un-ready every linked spec.
- **Orthogonal to status.** The projection never feeds the who-wins ladder above, never advances `lastSyncedAt` by itself, and never blocks — body/status/comments reconcile exactly as before. `readyState: null` (the default) skips it entirely: no calls, no receipts, no flag writes.
- **Opting back out.** `flowctl config set tracker.readyState null` clears the knob (the literal `null` token is stored as JSON null) — the projection goes dormant and local `spec ready`/`unready` is authoritative again.
- **Pilot interplay (1.13.0+).** [`/flow-next:pilot`](../skills/flow-next-pilot/SKILL.md) selects ready specs and, after two healthy no-advance ticks, runs a local `spec unready` (don't-thrash). On a `readyState`-configured repo that local write is **advisory until the board reflects it** — the next pull projects the issue's state back, re-readying the spec, and pilot treats a ready-again spec as human re-blessed (strikes cleared). So when pilot strikes a spec out, **move the issue out of the ready state on the board** before the next sync; re-blessing after a fix is the reverse move. The board stays the single control plane for readiness either way.

## Dependency projection — `depends_on_epics` → tracker issue relations

Flow specs declare cross-spec dependencies locally via `depends_on_epics` (the edges shown by `flowctl show` / `flowctl dep`). Left alone, that graph stays **local-only** — the board shows independent issues even though Flow knows one blocks another. Dependency projection (2.1.0+, fn-64) closes that gap: on push/reconcile of a linked spec, each `depends_on_epics` edge between two **linked** specs becomes a **blocked-by** relation between their issues — on Linear, GitHub, GitLab, and Jira, each at its native fidelity (see Per-adapter fidelity below; Jira specifically uses native "is blocked by" issue links — directional and universally available, no licence gate), idempotently, never clobbering a relation a human added by hand. It is the relations counterpart to body/status/comments sync — projection, not coordination; flow stays authoritative and the tracker is never a control plane for deps.

The projection runs through the transport-blind `projectDepRelations` hook (modelled on the one-way `projectReadiness` pull): the skill resolves the edges via `flowctl sync list-dep-relations`, then calls the normalized adapter relation transport (`setIssueRelation` / `listIssueRelations`, see [`references/adapter-interface.md`](../skills/flow-next-tracker-sync/references/adapter-interface.md)). The skill code does **not** branch on tracker type — only the adapter fidelity differs.

- **Direction — blocked-by.** Flow's `depends_on_epics` means "this spec is blocked by those," a direct match to the blocked-by/blocks relation pair. The current (dependent) issue is recorded as **blocked by** each dependency issue — no inversion ambiguity. On Linear that is a `blocks` edge with the operands swapped; on GitHub a `blocked_by` dependency; on GitLab an `is_blocked_by` issue link; on Jira a `POST /issueLink` with `type.name="Blocks"`, `inwardIssue=A` (the blocked current issue, shows "is blocked by") and `outwardIssue=B` (the blocker dependency, shows "blocks").
- **Per-adapter fidelity.** **Linear:** native issue relations — MCP `save_issue` `blockedBy`/`blocks` if the pinned schema exposes them, else the GraphQL `issueRelationCreate` rung, else a `noop` receipt on the bottom rung. **GitHub:** native issue **dependencies** (GA Aug 2025) via the REST `…/issues/{n}/dependencies/blocked_by` endpoints where the repo/account has them (feature-detected with a `GET` probe), else a provenance-fenced **"Blocked by" body block** (`<!-- flow:deps -->`…`<!-- /flow:deps -->` list of `#N` references) — the same reduced-fidelity posture the adapter already takes for status. **GitLab:** native directional issue **links** (`POST /issues/{iid}/links`, `link_type=is_blocked_by`) on a **Premium/Ultimate-licensed namespace**; on a Free or personal namespace the API returns `403 Blocked issues not available for current license`, so the adapter writes a **directionless `relates_to`** link for GitLab-UI visibility instead. **On both tiers the adapter ALWAYS also writes the provenance-fenced `<!-- flow:deps -->` body block** — it is the durable direction + provenance source on the native path (alongside the board-visible link) and the *sole* direction record on the degrade, so a `writeIssue` update must preserve it on every tier. `listIssueRelations` reads directed `blocks` edges **only** from native directional links or the fenced block — never from a directionless `relates_to`. **Jira:** native **"is blocked by" issue links** (`POST /rest/api/{3,2}/issueLink`, `type.name="Blocks"`) — directional and **universally available** (no licence tier, no degrade ladder), so there is one fidelity and **no `<!-- flow:deps -->` body block** (the native link is the sole projection; `linkPresent` is always `true`, never orphans). The flow-side `depRelations` ledger is its sole provenance authority; a ledgered edge whose native link a human deleted is a defer-on-removal collision (queued, never silently re-created), not a missing projection to recreate.
- **Idempotent — read-before-write.** No platform reliably no-ops a duplicate, so every projection reads the existing relations first (Linear: across **both** `relations` AND `inverseRelations`, each canonicalized to one direction; GitHub native: the `blocked_by` listing; GitHub fenced: the existing `#N` lines; GitLab: the existing `/links` listing or the `#N` lines in the fenced block; Jira: the `fields.issuelinks[]` listing filtered to `type.name == "Blocks"`, since Jira creates a *second* link on a duplicate `POST /issueLink`). A rerun creates zero new relations and appends nothing to the fenced block.
- **Provenance — flow-side ledger.** Neither tracker stores relation authorship, so tracker-sync records the edges it created in a per-spec `depRelations` ledger (the `.flow/specs/<id>.json` sidecar, atomic write — mirroring the merge-base hash-provenance shape). Each entry is `{key, dep_spec, from_tracker_id, to_tracker_id, type: "blocks", source: "flow", updatedAt}`, where `key` is an opaque hash of the directed pair (never a raw issue key inline — trackers auto-linkify keys even inside HTML comments). A relation **not** in the ledger (native) / **outside** the fenced block (GitHub's fenced fallback, and GitLab's `<!-- flow:deps -->` block on every tier) is **never removed** — a human's manual relation is safe, by construction. Removal of *our* now-stale edges is the provenance-safe `clear-dep-relation` path; removing ours-but-stale is best-effort, never a delete of someone else's.
- **GitHub fenced block ↔ body-merge.** The `<!-- flow:deps -->` block is **flow-owned**: the body-merge layer strips it before every hash / merge-base / divergence comparison (the canonical `trackerBodyForMerge` transform, [`references/body-merge.md`](../skills/flow-next-tracker-sync/references/body-merge.md)), so flow's own dependency block never round-trips back into the spec or registers as phantom tracker divergence.
- **Completed-blocker rule.** A dependency whose **local** dep spec is `done` (→ its issue Done/Closed) is a historical/completed blocker: the relation stays **visible** on the tracker (the board keeps the real historical ordering) but does **not** feed back into Flow `ready=true` gating — readiness already treats done deps as satisfied, and this hook must not regress that. `dep_status` in `list-dep-relations` is the *local* dep-spec status, never a remote fetch — flow is authoritative and the rule keys off the local dep being `done`.
- **Warnings, never silent drops.** A dependency spec with **no tracker link** is surfaced as a warning naming the dep spec id (and parent), in the skill report and on the `sync receipt`; the rest of the sync proceeds (item-level failure isolation). Self-edges are skipped with a warning. A dependency **cycle** in the flow graph is tolerated — each declared edge is projected as an independent direct relation, with **no** graph traversal or transitive expansion.
- **Collision — human-removed relations are not recreated.** An edge present in the `depRelations` ledger AND still in `depends_on_epics`, but **missing remotely** (a tracker user removed the projected relation), is evaluated **before** per-side rules: it emits `sync defer` + a `queued` receipt rather than silently recreating the relation. Re-creating a human-removed relation is the explicit anti-behavior — same conservative posture as the body/status who-wins ladder.

## Ralph-safe / autonomous-safe — never blocks

Every run emits a receipt (`flowctl sync receipt --status …`); genuine conflicts **queue** (`flowctl sync defer …`) rather than block. In autonomous / Ralph mode an `always-ask` tiebreak resolves to **queue**, not prompt — same policy, surface-dependent delivery. Deferred conflicts land in the **review deferred-findings sink** (`.flow/review-deferred/<branch>.md`) where the human already looks for deferred work — so tracker-sync never needs `flowctl block`, never stalls the loop. See [`ralph.md`](ralph.md).

The Phase-0 gate recognizes the **full autonomy marker family** (2.2.0+, fn-68 R14): `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, **`FLOW_AUTONOMOUS=1`, or the `mode:autonomous` token** — matching `work` / `make-pr` / `resolve-pr` / `capture`. tracker-sync was the **one** lifecycle-participating skill whose gate omitted `FLOW_AUTONOMOUS`; under the marker NO code path reaches a prompt (discovery ceremony, collision guard, genuine conflict, and `question` authoring all resolve "ask the human" to `sync defer`). This is what makes tracker-sync safe to call **per-tick from [`/flow-next:pilot`](../skills/flow-next-pilot/SKILL.md) backlog mode** — a live prompt mid-tick would stall the whole autonomous loop.

## Backlog-mode enumeration + the async question-valve (2.2.0+, fn-68)

[`/flow-next:pilot`](../skills/flow-next-pilot/SKILL.md) backlog mode reaches in front of the ready gate — it enumerates the whole promoted lane (including tracker tickets with no flow spec) and surfaces "stuck" as a **question, not a stall**. Two skill-level, transport-blind named ops carry that (NOT flowctl transport — flowctl has no tracker transport):

- **`list-open`** — enumerate the promoted-lane open issues via the 9th adapter method `listOpenIssues(filter) → issue[]`, filtered to the **exact** `tracker.readyState` state/label (no ordering, no "beyond"). Returns normalized `issue[]` so pilot can union in tracker-only tickets `flowctl specs` can't see. **No-ops with a note when `tracker.readyState` is unset** (no promoted lane to filter on — backlog mode then runs flow-ready specs only). Implemented for **Linear, GitHub, GitLab + Jira** (Jira via JQL `project = <KEY> AND status = "<readyState>"`, fn-70).
- **`question <spec-id | tracker-id>`** — post a question-valve comment behind a **stable anchor** `<!-- flow-next:question id=<hash> status=open -->`, where `id` hashes **stable fields only** (`subjectId` + blocked-stage + reason code + question slug; free prose is *outside* the hash, so rephrasing never duplicates; `subjectId` is the spec id when spec-backed, else the opaque tracker UUID — never a bare tracker key, which trackers auto-linkify). A human's reply carries `<!-- flow-next:answer id=<hash> -->`, matched by `id` (threaded on Linear via the comment's reply/parent metadata; flat on GitHub / GitLab / Jira via the body marker) and imported **under the matching `## Open Questions` entry**, flipping the anchor to `answered`. A **tracker-only** `question` (no spec) is **exempt from the spec-id sync receipt** — its parked/answered state lives in the tracker (scan the comments for the open/answer markers), with no spec import until `capture`/`interview` later creates a spec.

See [`references/adapter-interface.md`](../skills/flow-next-tracker-sync/references/adapter-interface.md) (the `listOpenIssues` contract + the `comment` reply/parent metadata), [`steps.md`](../skills/flow-next-tracker-sync/steps.md) Phase 7 (the named-op bodies + the answer round-trip), and [`references/comments-sync.md`](../skills/flow-next-tracker-sync/references/comments-sync.md) (the question-valve marker dedup).

## flowctl surface

The skill owns judgment (API calls, reconciliation, asking); `flowctl sync` owns deterministic plumbing. Full flag reference in [`flowctl.md`](flowctl.md#sync) — `sync active` / `get-state` / `set-tracker-id` / `set-last-synced` / `set-merge-base` / `clear` / `list-unsynced` / `list-stale` / `check-collisions` / `list-dep-relations` / `set-dep-relation` / `clear-dep-relation` (the dependency-projection ledger) / `receipt` (event-tagged via `--event <perEvent-key>`) / `check` (read-only lifecycle audit, `OK`/`MISSING` per event) / `defer`, plus the `tracker.*` config keys.

> Sync-engine shape (discovery ceremony, per-item `lastSyncedAt`, surface-diffs-never-overwrite) adapted from Ray Fernando's `running-bug-review-board` `issue-trackers.md` (Apache-2.0) — see CHANGELOG.

## See also

- [`flowctl.md`](flowctl.md#sync) — `flowctl sync` subcommands + `tracker.*` config keys.
- [`teams.md`](teams.md) — projection-not-coordination positioning, Symphony contrast, adoption ladder.
- [`architecture.md`](architecture.md) — spec-JSON `tracker` fields, widened id resolver.
- [`ralph.md`](ralph.md) — conflicts queue to deferred-decisions, never block.
