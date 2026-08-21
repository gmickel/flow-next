# Tracker sync bridge

> **Codex install note:** commands written as `/flow-next:<name>` in this page are invoked on this host as `$flow-next-<name>` (or picked from the skills dropdown); examples prefixed `claude -p` or `/loop` are Claude Code host examples and run there unchanged.


Project a flow-next spec to a tracker issue (Linear, GitHub, GitLab, or Jira) and reconcile body / status / comments two-way. Drives the `/flow-next:tracker-sync` skill plus the `flowctl sync …` plumbing.

> **Optional.** flow-next runs fully without this. It costs a bidirectional round-trip per lifecycle event you enable, plus a conflict policy to hold an opinion about and a second place state can be wrong; turn it on when other people need to read or edit status where they already work, or invoke it manually with `/flow-next:tracker-sync` and leave the bridge off in between. Spec-only is a first-class mode, not a degraded one. See [`running-lean.md`](running-lean.md).

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
| Jira REST + token | `JIRA_BASE_URL` set, plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` OR self-hosted DC/Server `JIRA_PAT` | Jira REST transport available and **offered**. API version 2 is the default for Cloud and DC/Server; a bare `*.atlassian.net` host with no credential is surfaced but cannot be offered |

Resolution is **env > config > ASK** (mirrors `flowctl review-backend`): if env/config already decides the transport, the ceremony doesn't re-ask. On confirmation the skill writes via `flowctl config set tracker.…` and verifies with `flowctl sync active --json` (must report `active: true`). The bridge is active iff raw `tracker.enabled == true` **OR** raw `tracker.type ∈ {linear, github, gitlab, jira}`.

For a **GitLab** tracker the ceremony additionally writes `tracker.perTracker.project` (the group/sub-group/project path, e.g. `group/subgroup/project` — the GitLab analog of GitHub's `repo`) and, for self-managed hosts, `tracker.perTracker.host`. A self-managed instance on plain http and/or a non-default port stores the **scheme-prefixed origin** (e.g. `http://gitlab.internal:8929`) — the HTTP transport derives its API base from it verbatim, while the `glab` CLI route normalizes it to the bare hostname for `--hostname` (glab carries protocol/port itself under that host key in its own config; measured live 2026-07-28). A plain hostname (`gitlab.example.com`) keeps meaning https on 443. flow-next stores the literal path and derives the URL-encoded form (`group%2Fsubgroup%2Fproject`) once for the API, never double-encoding. **Zero special setup** — GitLab works from an existing `glab auth login` session OR a `GITLAB_TOKEN`/`CI_JOB_TOKEN` already present (gh-style), with no flow-next-specific provisioning; the spec-first floor applies when neither is present.

For a **Jira** tracker the ceremony writes `tracker.perTracker.baseUrl` (the site, e.g. `https://acme.atlassian.net`) + `tracker.perTracker.projectKey` (the `PROJ` key), and **persists the deployment shape the probe detected**: `tracker.perTracker.authScheme` (`cloud-basic` = Cloud HTTP-basic `email:API_TOKEN`; `bearer-pat` = DC/Server `Authorization: Bearer <PAT>`) and `tracker.perTracker.apiVersion`. Resolution and migration converge on API version **2** because measured v2 issue bodies round-trip as plain strings byte-exact. Runtime never re-infers the shape. An opt-in `tracker.perTracker.sslVerify=false` (env `JIRA_SSL_VERIFY=false`) covers self-hosted internal-CA / self-signed certs; never silent. **Credentials are read from env each run, never stored in flow state.** **Zero special setup**: a standard Jira credential the company already issues (Cloud API token or DC/Server PAT), with no OAuth app, MCP server, webhook, or Connect/Forge app. The spec-first floor applies when no credential is present. The official Atlassian MCP cannot transition status, update fields, or set links, and the community MCP is a redundant PAT wrapper, so Jira operations run through flowctl's deterministic REST transport.

After the config writes, the ceremony asks **one optional, skippable readiness question** (1.12.0+): *which tracker workflow state means "ready for work"?* — a Linear workflow-state name (discovered from the team's states, with a "Ready"-looking name recommended), a GitHub label (suggested `ready`, pre-created idempotently), on GitLab a label (suggested `ready`, pre-created idempotently; GitLab has no rich workflow, so readiness is a label like GitHub), or — on **Jira** — a workflow **status name** (like Linear; validated against the project's statuses when a credential is present, else skip → no-op backlog lane). The answer is stored as `tracker.readyState`; skipping writes nothing and leaves the readiness gate dormant. See [Readiness projection](#readiness-projection--trackerreadystate--local-ready-flag) below.

## Three entry flows — no fixed starting point

All attach sync state **on link**:

1. **Author-in-flow-then-push (flow-first).** A `fn-NN` spec already exists. Push creates the tracker issue, then `flowctl sync set-tracker-id` attaches the issue UUID + `--identifier WOR-17` + `--url`. The `fn-NN` id is kept; the tracker key becomes a resolvable alias.
2. **Link-existing-issue (tracker-first): "grab issue X and spec it."** Fetch the issue, create the spec **keyed by the tracker key** (`flowctl spec create --tracker-first --tracker-identifier <key>`), seed the merge base from the current issue body, first pass is pull-only. **All four trackers support tracker-first:**
   - Linear `WOR-17` / Jira `PROJ-123` are native `KEY-N` and mint directly (`wor-17-slug` / `proj-123-slug`).
   - GitHub `#123` and GitLab `<project>#456` are **not** literal `KEY-N` (no alpha key / path + `#`), so flowctl mints **synthetic keys** while `tracker.type` matches: `#123` → `gh-123-slug`, `<project>#456` → `gl-456-slug` (project-scoped `iid`, never the opaque global id). Bare `gh-123` / `gl-456` resolve as aliases.
   - Flow-first remains available on every tracker (create `fn-NN`, then `set-tracker-id` with the issue ref as a display alias).
3. **Create-first (fresh idea — issue before any local spec).** When `tracker.specIds=tracker` and no issue exists yet, tracker-sync creates the issue from title + body (no local spec id), returns `{id, identifier, url}`, then the caller mints → attaches → seeds the merge base. Pre-spec recovery lives under `.flow/create-first/` (gitignored); a retry after partial failure **links**, never re-creates. See the skill's Phase 2d.

   **Racing promoters (fn-182, #310):** the post-mint `sync create-first-put --spec-id` should pass `--if-absent` - the record write is then a compare-and-set, and the loser of a concurrent promotion exits `10` with `class=conflict`, `subtype=spec_already_minted`, and `details.recordedSpecId` naming the winner. On that conflict, adopt the recorded spec and discard the locally minted one instead of re-putting; `--expect-spec-id <id>` is the CAS form for updating a claim you already own.

   **Abandoning a never-promoted candidate (fn-182, #309):** the ordering is remote-first. (1) Close or cancel the remote issue - that side is **the consumer's to do**, in the tracker UI or with the tracker's own tooling; flow-next never closes an issue it did not project a lifecycle for. (2) Then `flowctl sync create-first-clear --key <k>` removes the local recovery record. Clearing first would leave a live intake issue with no local trace, so the next same-key run could re-create a duplicate; closing first means a stale record at worst resolves to an already-closed issue, which the retry path links and reports rather than duplicating.

## Hybrid id model (R16)

The two id schemes **coexist**; resolution is provided by flowctl's widened resolver (case-insensitive). **Ids NEVER change — there is no rename-on-push.** Mixed stores (`fn-N-slug` next to `KEY-N-slug` / `gh-N-slug`) are permanent and expected.

| | Tracker-first (canonical) | Flow-first (alias) |
|---|---|---|
| canonical spec id | `wor-17-slug` / `gh-123-slug` / `gl-456-slug` | `fn-NN-slug` (unchanged) |
| canonical task ids | `wor-17-slug.M` / `gh-123-slug.M` | `fn-NN-slug.M` |
| branch | same as canonical id | `fn-NN-slug` |
| bare aliases | `wor-17` / `gh-123` / `gl-456` (and `.M` task forms) resolve to the full slug id | `WOR-17` (stored in `tracker.identifier`) resolves to `fn-NN-slug`. A GitHub/GitLab ref like `#123` is **display-only** - stored and shown, never a resolvable handle; only the synthetic `gh-123` / `gl-456` form resolves |
| create / link | `flowctl spec create --tracker-first --tracker-identifier <key-or-ref>` | `flowctl sync set-tracker-id fn-NN-slug <uuid> --identifier <key> --url <url>` |

### Synthetic keys (GitHub / GitLab)

GitHub and GitLab do not ship a native `KEY-N` display form. While `tracker.type` is `github` / `gitlab`, flowctl synthesizes a resolvable key from the issue number:

| `tracker.type` | Native identifier | Minted spec id |
|---|---|---|
| `linear` | `WOR-17` | `wor-17-slug` (native key, unchanged) |
| `jira` | `PROJ-123` | `proj-123-slug` (native key, unchanged) |
| `github` | `#123` | `gh-123-slug` (synthetic `gh`) |
| `gitlab` | `<project>#456` | `gl-456-slug` (synthetic `gl`; uses project-scoped **`iid`**, never the opaque global id) |

**Guards (not type-gating alone):** while `tracker.type` is `github`/`gitlab`, the matching prefix (`gh`/`gl`) is **contextually reserved** for synthesis — an explicit native `GH-123` identifier is rejected at mint/link. Before minting, a **preflight** of the existing store refuses a colliding canonical id or resolvable alias. A Linear/Jira repo natively keyed `GH` is unaffected (type is not `github`/`gitlab`). **Re-pointing `tracker.type`** (or re-pointing GitLab at a different project) is a documented hazard: previously minted ids keep their meaning; preflight stops a new mint from colliding with them.

### `tracker.specIds` — team default gate

| Value | Behavior |
|---|---|
| `flow` (default; also the fail-closed read for a malformed on-disk value) | Spec-creating skills mint `fn-N-slug` (today's behavior) |
| `tracker` | With an active bridge, skills mint tracker-keyed ids: named issue → `--tracker-first`; fresh idea → create-first then mint |

Write side: `flowctl config set tracker.specIds <value>` accepts only `flow` or `tracker` (invalid CLI writes are rejected). The leaf is **unset-detectable** (not materialized at init) so `/flow-next:setup` can ask once when a tracker is configured and the key is still absent; once set either way, setup never re-asks. Skills route on this from an existing root config snapshot — no new config read. Bridge inactive / no transport degrades silently to flow-first. Explicit user override always wins.

Network cost is conditional: when the matching `tracker.perEvent.*` touchpoint is already active, tracker-first reorders an existing remote write; when those leaves are off (their default), tracker-first introduces an earlier remote write that flow-first would not make.

### Duplicate ordinals

A duplicate native `fn-N` ordinal whose full ids are distinct (e.g. two `fn-122-…` specs) is **untidy, not broken**. `flowctl validate --all` reports it as a top-level **`root_warnings`** entry (counted in `total_warnings`), not a `root_error`. Bare `fn-N` resolution disambiguates rather than guessing — lists candidates and requires the full id (same idea as git short-hash disambiguation). Ids never change; do not renumber.

### Other hybrid rules

- **Resolution is case-insensitive.** `flowctl show wor-17`, `work gh-123`, `plan gl-456`, tasks `wor-17.M` all resolve. `tracker.identifier` stores the **display form** (`WOR-17` / `#123` / `group/project#456`); the canonical id derives from the lowercase key.
- **`fn` is the only globally reserved prefix.** Synthetic `gh`/`gl` are reserved only while `tracker.type` matches. Enumeration sees tracker-key specs, but native `fn-N` allocation counts `fn-*` only — a `wor-9999` never bumps the next `fn`.
- **Native `fn-N` allocation is a union scan** over the working tree, every registered git worktree's `.flow/specs/`, and every ref (monotonic max-ever-allocated). Fail-open on git problems. That shrinks the parallel-agent collision window; separate unfetched clones can still collide — that is what `tracker.specIds=tracker` is for.
- **One tracker team / workspace per repo.** The bridge assumes a single team key so a bare `wor-17` resolves unambiguously. Cross-workspace same-key collision is out of scope.
- **No local identity rename on push.** Existing spec/task ids, branches, and dep edges are never mutated on link; the tracker key is added as a resolvable handle, not a replacement. `flowctl spec set-title` on a tracker-linked spec updates the local title only — it does **not** re-slug the id, branch, or files. The next facade push/reconcile projects that title to the tracker's native issue-title field.

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
| `projectId` / `projectMilestoneId` | **optional, Linear only (fn-182, #315):** per-spec Linear Project (and Project Milestone) the issue belongs in. Hand-set in the spec's tracker block; sent on `issueCreate` and reconciled on every `sync-body` push (including converged-body pushes). **Absent = unmanaged, not none** — flow-next never clears tracker-side membership, never creates or manages Projects, and carries exactly the id it is given (a bad id surfaces Linear's own error). Non-Linear trackers refuse the field with a capability error |

The **merge base is a paired snapshot at one sync point**: `flowctl sync set-merge-base` requires **both** `--flow`/`--flow-file` AND `--tracker`/`--tracker-file` together (a partial write that pins one half to a stale sync point is rejected). The base is stored in a form comparable to each side so a 3-way merge can compare flow-structured spec against tracker free-form issue.

## Flowctl-owned transport and resolved capabilities

`flowctl tracker` owns provider selection, credentials, request construction,
pagination, retries, normalization, capability checks, and mutations. The skill
does not select or execute a runtime transport path. It supplies semantic input
files, then branches only on the structured result envelope.

| Provider | Flowctl-owned route | Status fidelity |
|---|---|---|
| **Linear** | GraphQL with `LINEAR_API_KEY`; host MCP is limited to discovery or create, then handed back through `tracker persist-external` | full workflow states |
| **GitHub** | authenticated `gh api` | reduced fidelity through open/closed plus the configured status label |
| **GitLab** | authenticated `glab api` or REST, selected deterministically from resolved configuration and available credentials | reduced fidelity through open/closed plus the configured status label |
| **Jira** | REST with the resolved deployment/authentication shape; API version 2 by default | full workflow states through resolved transition ids |

Discovery persists the normalized runtime facts under
`tracker.resolved`; consuming verbs read that block instead of rediscovering
provider metadata:

```json
{
  "tracker": {
    "resolved": {
      "destination": {
        "owner": "acme",
        "repo": "widget",
        "statusIds": {"todo": "1", "in_progress": "2", "done": "3"},
        "stateIds": {"todo": "a", "in_progress": "b", "done": "c"}
      },
      "capabilities": {
        "attachments": false,
        "blockedBy": false,
        "subIssues": true,
        "deleteIssue": false
      },
      "scopeResolvedAt": {
        "destination": "<ISO timestamp>",
        "destination.statusIds": "<ISO timestamp>",
        "destination.stateIds": "<ISO timestamp>",
        "capabilities": "<ISO timestamp>"
      },
      "resolvedAt": "<ISO timestamp or null>"
    }
  }
}
```

The destination fields are provider-specific: GitHub uses `owner` and `repo`;
GitLab uses `projectId`, `projectPath`, `host`, and `namespaceId`; Linear uses
`teamId`, `teamKey`, `stateIds`, and `labelIds`; Jira uses `baseUrl`,
`projectKey`, `projectId`, `issueTypeId`, `apiVersion`, `style`, and
`statusIds`. `resolvedAt` is set only when every required destination field,
required normalized status slot, and capability boolean is present. Each
`scopeResolvedAt` timestamp belongs only to its named scope, so a partial
refresh cannot make unrelated data look fresh.

Capability degradation is explicit. GitLab's plan-sensitive `blockedBy`
capability is re-probed after 24 hours. A confirmed change from available to
unavailable returns success with a `degraded` object such as
`{"capability":"blockedBy","from":true,"to":false,"fallback":"body-block"}`.
A failed probe keeps the prior capability and reports a separate `probe`
object; a transient authorization or transport failure never becomes a silent
downgrade. A requested unsupported operation returns `class: capability` with
typed details. No provider path is selected from prose or provider error text.

## Lifecycle sync points (on by default — opt-out)

Sync is wired into seven lifecycle skills. **When you hook the bridge up via the `/flow-next:tracker-sync` discovery ceremony, the whole pipeline activates by default** — the point of connecting a tracker is to keep it in sync, so you don't opt in event-by-event. You **opt out** instead: exclude events at ceremony time, or turn any off later with `flowctl config set tracker.perEvent.<event> off`. Leaf values: `off | pull | push | reconcile | comment`.

| Event | Config key | Default op | Fires when |
|---|---|---|---|
| capture | `tracker.perEvent.capture` | `reconcile` | a spec is captured |
| interview | `tracker.perEvent.interview` | `reconcile` | a spec is refined |
| plan | `tracker.perEvent.plan` | `reconcile` | a spec is decomposed into tasks |
| work (first claim) | `tracker.perEvent.work.firstClaim` | `push --status-only` | the first task of a spec is claimed |
| work (done) | `tracker.perEvent.work.done` | `comment` | a task completes |
| make-pr | `tracker.perEvent.makePr` | `reconcile --pr-url` | a PR is opened (→ issue **In Review** + PR link, unconditional when bridge active — fn-66) |
| resolve-pr | `tracker.perEvent.resolvePr` | `comment` | PR threads are resolved |
| completion review | `tracker.perEvent.completionReview` | `comment` | a spec-completion review runs (verdict + R-ID coverage; **never terminal Done** — fn-66) |
| land (merged) | `tracker.perEvent.land.merged` | `push` | a PR **merges** (→ issue **Done**, the SOLE Done driver, gated on the GitHub `MERGED` probe; **active-by-default** when bridge active — fn-66) |

The lifecycle skills value-check `flowctl sync active` and the specific `perEvent` leaf, short-circuiting cleanly when the bridge is off or an event was opted out — so a no-tracker repo (or an excluded event) costs a single value-check, no transport.

**Observable + forcing (fn-57).** Every lifecycle dispatch is **event-tagged**: the tracker-sync skill writes its receipt with `--event <perEvent-key>` (`work.firstClaim`, `work.done`, `capture`, `makePr`, …), so `.flow/sync-runs/` records which touchpoint each run served. At end-of-skill, **work, capture, and make-pr** run the read-only audit `flowctl sync check <spec-id> --events <triggered-csv> --since <run-anchor>` — independently of the touchpoints themselves, so a wholesale-skipped dispatch block is still caught. An event is `MISSING` iff it triggered this run AND its `perEvent` leaf is enabled AND the bridge is active AND no receipt with a matching `event` tag and `timestamp ≥ --since` exists (any receipt status clears — the check asserts the touchpoint *ran*; the receipt's own status carries success/failure detail). A `MISSING` event is **retro-fired exactly once** — the skill re-dispatches the missed touchpoint via tracker-sync, then re-checks against a fresh `--since` — and the skill's final summary carries a mandatory four-state `Tracker sync:` slot: `OK` | `MISSING:<event> → retro-fired → OK` | `MISSING:<event> (retro-fire failed: <reason>)` | `n/a (bridge inactive)`. An explicit `n/a` proves the check ran; an absent slot is visible as a skipped check. With no tracker configured `sync check` exits silently in constant time — non-tracker repos see no change anywhere.

**Auto-link on first touch (create-if-unlinked).** When a lifecycle event fires for an unlinked spec, the `flowctl tracker sync` facade creates and links the issue before applying the requested operation. Later events use the persisted durable identity. This keeps every in-Flow-authored spec projected without making callers reconstruct lifecycle ordering. The spec to one-issue grain is unchanged; tasks never become sub-issues. Only `unlink` no-ops on an unlinked spec. An inactive bridge is filtered by the caller gate, while a failed facade returns a structured class and one aggregate receipt.

**Activation is ceremony-gated, not flag-gated.** The config *schema* default for every `perEvent` leaf stays `off`, so a bare `tracker.enabled=true` set by hand or a script — without running the discovery ceremony — fires **no lifecycle-event sync** (every `perEvent` event stays dormant). Only the ceremony's explicit per-event writes (or your own `config set`) turn events on. This keeps the accidental-enable guard while making the *intended* path (run the ceremony) sync everything. **The two things that are *not* gated this way are make-pr's PR↔issue link (+ In Review) and `land.merged`'s Done-on-merge** — both unconditional whenever the bridge is active (the exceptions documented just below), so a bare `enabled=true` plus a linked spec will still add a `Ref` line + move the issue to In Review on the next make-pr, and move it to Done on a confirmed merge. The make-pr linkage is cheap, conflict-free, and the whole point (Linear Diffs); the land.merged Done is merge-evidence-gated so it only fires for genuinely shipped work. Neither mutates the spec beyond the linked issue's status.

**Two unconditional paths when the bridge is active (fn-66).** Some status transitions are too important to leave opt-in:

1. **make-pr — PR link + In Review.** make-pr always links the new PR to its tracker issue *and* moves the issue to **In Review** when `sync active` and the issue is linked — it does **not** require opting `makePr` in. An open PR *is* the In Review lifecycle rung (`flowToNormalized(spec, open) → in-review`, non-terminal), and the link powers Linear Diffs — both ride the same unconditional path. The `perEvent.makePr` leaf still governs any *extra* make-pr sync (e.g. an optional breadcrumb comment). make-pr additionally **verifies the ref landed** post-create (§4.6b): it fetches the LIVE PR body via `gh pr view --json body` and, when the `Ref <identifier>` line is absent (e.g. an agent hand-rolled `gh pr create` and bypassed the deterministic append), repairs it append-only via `gh pr edit` — mechanical, idempotent, fully non-fatal.
2. **land — Done on merge.** `land.merged` is **active-by-default** when the bridge is active and is the **SOLE** driver of the terminal `Done` state. A real merge is the only event that legitimately projects "shipped", so leaving it opt-in would strand boards at In Review forever after a merge. The terminal write self-checks the GitHub `MERGED` probe (the merge-evidence invariant) — no path writes `Done` without it. The `perEvent.land.merged` leaf, if set, only tunes the optional verdict comment, never the (MERGED-gated) status.

These are the only two unconditional touchpoints; everything else stays `perEvent`-gated.

### MISSING after retro-fire — recovery

A `Tracker sync: MISSING:<event> (retro-fire failed: <reason>)` summary line means the touchpoint did not fire and the one bounded retro-fire could not recover it. The primary work is unaffected: tracker sync is best-effort and never blocks, so the task is done or the PR is open. To recover by hand:

1. **Read the structured failure** from the event receipt. Its class and typed details distinguish `auth`, `unresolved`, `stale_id`, `rate_limited`, `transport`, `capability`, `conflict`, and `external_action_required`.
2. **Resolve the named condition**, then re-fire the missed touchpoint through `/flow-next:tracker-sync`. The skill supplies semantic inputs and recovery judgment; its one runtime action is the matching `flowctl tracker sync` facade call.
3. **Verify**: `flowctl sync check <spec-id> --events <event> --since <retro-fire-time>` now prints `OK:<event>`.

## Lifecycle facade

Lifecycle callers retain their bridge-active and `perEvent` gates, synthesize
any comment content they own, and invoke `flowctl tracker sync <spec-id> --op
<op> --event <key>` inline. The facade owns create-if-unlinked, transport,
marker dedup, ordering, and the single aggregate receipt. Content travels only
through mode `0600` temporary files.

Every synthesized comment file (`comment --body-file` or push
`--comment-file`) must start with `evidence=<token>`. The token is a stable,
whitespace-free identity for that occurrence: for example a task plus its
evidence commit, the reviewed/tested head SHA, a spec-content fingerprint, or
the merge commit. Flowctl strips the line before posting and uses it only in
the dedup marker. Missing or placeholder evidence is rejected before any
provider call; otherwise separate occurrences of one event would all collapse
onto the old shared `evidence=none` marker.

`push` may additionally receive `--comment-file` when the caller owns a
judgment-bearing verdict that must accompany the lifecycle projection. The
facade posts or deduplicates that comment under the same outer transaction and
records status, relations, and comment in one aggregate receipt. Land uses this
form after a confirmed merge so its terminal verdict and `Done` projection
cannot split into two independently retried facade calls.

Make PR's reconcile call additionally receives the just-created absolute URL
as `--pr-url`. That input is accepted only for `--op reconcile --event makePr`
and is projected inside the same facade claim and receipt: GitHub uses the
non-closing PR-body reference, GitLab posts/deduplicates a URL note, Jira
upserts a remote link with a URL-comment fallback, and Linear creates its rich
`attachmentLinkURL` attachment. Merge evidence determines lifecycle state; it
does not carry the URL.

Work's `firstClaim` caller uses `push --status-only`: an already-linked issue
receives status only, preserving tracker-side body and relation co-edits. An
unlinked spec still creates, links, seeds the paired merge base, and then
projects status.

The same path runs on Claude Code, Codex, Cursor, Droid, and Grok Build. A
structured conflict or external action request returns to the tracker-sync
skill for recovery routing. Under Ralph, any decision requiring a person queues
with `sync defer`; it never prompts.

## Linear Diffs — review the PR inside the issue

[Linear Diffs](https://linear.app/docs/diffs) (GA May 2026) renders a GitHub PR's diff, file changes, checks, and inline review threads directly on the Linear issue, and lets you approve / request changes / merge from Linear. flow-next makes your PRs **Diffs-ready automatically** when `tracker.type == linear`:

- **What flow-next does:** make-pr puts a **non-closing** `Ref WOR-N` line in the PR body (make-pr §4.6a) so Linear's GitHub integration auto-links the PR to the issue — which is exactly what makes the diff render. On the GraphQL transport it also creates the rich PR attachment (`attachmentLinkURL`) for status sync. *Non-closing* (`Ref`, not `Fixes`) is deliberate: the PR links + renders as a diff but does **not** auto-complete the Linear issue on merge — flow-next's `land.merged` touchpoint owns the `Done` transition (fn-66), gated on a GitHub-confirmed `MERGED` probe. (Pre-fn-66 this said "spec-completion-review owns the Done transition" — that was the bug FLOW-15 caught: completion review is *local* completion, not merge evidence, so it could close the issue before the PR merged. Completion review now posts only a verdict comment + at most `In Review`; `Done` is reserved for a merged PR.)
- **What you must enable (one-time, Linear-side — flow-next can't set these):** the Linear **GitHub integration with code access** to the repo, your **personal GitHub connection**, and **"Enable code reviews"** in Linear settings. Without them the PR still links and status still syncs; only the rendered diff view needs them.
- **GitHub / GitLab / Jira tracker:** no Linear Diffs — the PR is cross-linked natively (`Refs #N` on GitHub; `Ref <project>#<iid>` on GitLab; a **remote link** — `POST /issue/{key}/remotelink`, with a PR-URL comment fallback — on Jira, since Jira has neither PR auto-linkify nor `gh`) and review happens on the host.

## Reconciliation — who-wins

- **Body** — agentic host-agent semantic **3-way merge** against the `lastSyncedAt` merge-base snapshot, translating between flow's structured spec and the tracker's free-form issue. Only **genuine contradictions** surface; confident merges proceed.
- **Status** — per-field **who-wins** ladder. The collision/deadlock case is evaluated **before** single-field terminal-wins rules (a `tracker=done × flow=…` deadlock must fall to `conflictTiebreak`, not be silently overwritten by terminal-wins). Tiebreak is `tracker.conflictTiebreak` (`flow-wins | tracker-wins | always-ask`, default `always-ask`). `flow-wins` reuses the provider-neutral status write and still requires merged-PR evidence for terminal projection. `tracker-wins` reuses the local terminal fold when the tracker is terminal (no provider write, existing `pulled` receipt). The mirror — merged Flow terminal while the tracker is active — cannot converge through raw `spec.status`; it remains an explicit candidate-bearing conflict with no mutation or `lastSyncedAt` advance.
- **Comments / evidence** — two-way **append** with dedup; neither side overwrites the other.

## Readiness projection — `tracker.readyState` → local `ready` flag

When `tracker.readyState` is configured (the optional ceremony question above), every operation that reads the issue (`pull` / `reconcile`) projects the configured tracker state onto the local spec [`ready` flag](flowctl.md#spec-ready--spec-unready) — giving readiness a **single local read path** whether it's human-set or tracker-driven (1.12.0+, fn-58).

- **One-way pull, tracker authoritative.** Readiness is projected tracker → local only — the local `ready` flag is never pushed to the tracker (no `setStatus`, no label add/remove). A local `flowctl spec ready` on a tracker-connected repo is overwritten by the next sync; tracker users set readiness on the board (which is why capture/interview's mark-ready prompt is gated off when `readyState` is configured).
- **Match semantics.** Linear: case-insensitive trimmed match on the workflow-state **name** (names, not `state.type`; a custom "Ready" state is typically `type=unstarted`, so type alone can't distinguish Todo from Ready). GitHub: the `readyState` **label**; present on the issue ⇒ `ready=true`, absent ⇒ `ready=false` (absence is a normal state; un-labeling IS how a GitHub user un-readies a spec). GitLab: identical label semantics to GitHub; the `readyState` **label** present ⇒ `ready=true`, absent ⇒ `ready=false` (GitLab has no rich workflow, so readiness is a label). Its project-label existence check drains bounded search pages and treats a capped scan as unproven, never as stale configuration. Jira: like Linear, a case-insensitive trimmed match on the workflow-**status name** (`status.raw` = `fields.status.name`, never `statusCategory`), the raw Jira status name validated to exist in the project at ceremony time.
- **Change-only receipts.** The projection applies via the idempotent `spec ready`/`unready` toggles and emits an event-tagged receipt **only when the local flag actually changes** — silent on a no-op echo (mirrors the `lastSyncedAt` advance-only-on-real-reconciliation rule).
- **Stale-config degradation.** A configured state name / label that no longer resolves on the tracker (renamed/deleted) ⇒ **warn + `noop` receipt + flag untouched + the sync continues** — one bad knob never aborts the run, and a stale `readyState` must not silently un-ready every linked spec.
- **Orthogonal to status.** The projection never feeds the who-wins ladder above, never advances `lastSyncedAt` by itself, and never blocks — body/status/comments reconcile exactly as before. `readyState: null` (the default) skips it entirely: no calls, no receipts, no flag writes.
- **Opting back out.** `flowctl config set tracker.readyState null` clears the knob (the literal `null` token is stored as JSON null) — the projection goes dormant and local `spec ready`/`unready` is authoritative again.
- **Pilot interplay (1.13.0+, corrected in fn-184).** [`/flow-next:pilot`](../../skills/flow-next-pilot/SKILL.md) selects ready specs and, after two healthy no-advance ticks, runs a local `spec unready` (don't-thrash) and records a strike. On a `readyState`-configured repo that local write is **advisory until the board reflects it** — the next pull projects the issue's state back and re-readies the spec. **A projection-set ready never clears a strike** (fn-87 R7): the board echo re-grants readiness with no human involved, and clearing on it would re-dispatch the same failing spec every tick forever. So a struck spec on an armed-`readyState` repo reads ready on the board while pilot keeps skipping it as still-struck. **The recovery is the verb, not the board:** `flowctl pilot strikes clear <spec-id>` (see [`flowctl.md`](flowctl.md#pilot-strikes) and [`troubleshooting.md`](troubleshooting.md)). Moving the issue out of the ready state is still worth doing - it stops pointless re-selection noise and keeps the board honest about what is waiting on a human - but it is not what clears the strike. The board remains the single control plane for **readiness**; strikes are pilot state, not readiness state.

## Dependency projection — `depends_on_epics` → tracker issue relations

Flow specs declare cross-spec dependencies locally via `depends_on_epics` (the edges shown by `flowctl show` / `flowctl dep`). Left alone, that graph stays **local-only** — the board shows independent issues even though Flow knows one blocks another. Dependency projection (2.1.0+, fn-64) closes that gap: on push/reconcile of a linked spec, each `depends_on_epics` edge between two **linked** specs becomes a **blocked-by** relation between their issues — on Linear, GitHub, GitLab, and Jira, each at its native fidelity (see Per-adapter fidelity below; Jira specifically uses native "is blocked by" issue links — directional and universally available, no licence gate), idempotently, never clobbering a relation a human added by hand. It is the relations counterpart to body/status/comments sync — projection, not coordination; flow stays authoritative and the tracker is never a control plane for deps.

The projection is flowctl-owned. `flowctl sync list-dep-relations` enumerates
local dependency state, and `flowctl tracker relate` or the lifecycle facade
performs the normalized provider mutation. The tracker-sync skill supplies
semantic recovery only and never branches on provider type. This replaces the
agent-driven mutation rule from fn-57 R3; **fn-141 R8 is the superseding
decision and implementation pointer**.

- **Direction - blocked-by.** Flow's `depends_on_epics` means "this spec is blocked by those," a direct match to the blocked-by/blocks relation pair. The current (dependent) issue is recorded as **blocked by** each dependency issue, with no inversion ambiguity. Linear uses a `blocks` edge with the operands swapped. GitLab uses an `is_blocked_by` issue link. Jira uses the configured blocking link type with the blocker as `inwardIssue` and the blocked issue as `outwardIssue`. GitHub has no issue-level blocked-by relation: flowctl makes the blocked issue a `sub_issue` of the blocker and reports that hierarchy proxy as structured degradation, never as blocked-by.
- **Per-provider fidelity.** `flowctl tracker relate` reads the persisted capability set and applies one deterministic provider policy. Linear and Jira use native directional blocked-by relations. GitHub uses the `sub_issues` hierarchy proxy and returns `degraded.kind: "hierarchy"` with `degraded.form: "sub_issues"`. GitLab uses a native directional link when `capabilities.blockedBy` is true; when it is false, flowctl records a directionless `relates_to` link for board visibility and keeps direction/provenance in the fenced body block. A confirmed GitLab plan change returns the `degraded` capability transition described above. Missing or ambiguous required metadata returns `unresolved`, `capability`, or `conflict`; the skill chooses recovery from that class instead of selecting a provider route.
- **Idempotent - read-before-write.** No platform reliably no-ops a duplicate, so every projection reads existing relations first: Linear checks `relations` and `inverseRelations`; GitHub drains the blocker's `sub_issues`; GitLab reads issue links or the fenced block; Jira filters `fields.issuelinks[]` to the configured blocking type. A rerun creates zero new relations and appends nothing to a fenced block.
- **Provenance - flow-side ledger.** Neither tracker stores relation authorship, so tracker-sync records the edges it created in a per-spec `depRelations` ledger (the `.flow/specs/<id>.json` sidecar, atomic write - mirroring the merge-base hash-provenance shape) via `flowctl sync set-dep-relation`. Each entry is `{key, dep_spec, from_tracker_id, to_tracker_id, type: "blocks", source: "flow", updatedAt}`, where `key` is an opaque hash of the directed pair (never a raw issue key inline - trackers auto-linkify keys even inside HTML comments). Projection is additive-only: flowctl never removes a tracker relation. A relation or hierarchy proxy **not** in the ledger, or a GitLab dependency outside the fenced block, is never touched. A human's manual relation is safe by construction; a missing remote relation that remains declared locally is deferred as a conflict instead of being recreated.
- **GitLab fenced block and body merge.** The GitLab `<!-- flow:deps -->` block is **flow-owned**: the body-merge layer strips it before every hash, merge-base, or divergence comparison (the canonical `trackerBodyForMerge` transform, [`references/body-merge.md`](../../skills/flow-next-tracker-sync/references/body-merge.md)), so the dependency block never round-trips back into the spec or registers as phantom tracker divergence.
- **Completed-blocker rule.** A dependency whose **local** dep spec is `done` (→ its issue Done/Closed) is a historical/completed blocker: the relation stays **visible** on the tracker (the board keeps the real historical ordering) but does **not** feed back into Flow `ready=true` gating — readiness already treats done deps as satisfied, and this hook must not regress that. `dep_status` in `list-dep-relations` is the *local* dep-spec status, never a remote fetch — flow is authoritative and the rule keys off the local dep being `done`.
- **Warnings, never silent drops.** A dependency spec with **no tracker link** is surfaced as a warning naming the dep spec id (and parent), in the skill report and on the `sync receipt`; the rest of the sync proceeds (item-level failure isolation). Self-edges are skipped with a warning. A dependency **cycle** in the flow graph is tolerated — each declared edge is projected as an independent direct relation, with **no** graph traversal or transitive expansion.
- **Collision — human-removed relations are not recreated.** An edge present in the `depRelations` ledger AND still in `depends_on_epics`, but **missing remotely** (a tracker user removed the projected relation), is evaluated **before** per-side rules: it emits `sync defer` + a `queued` receipt rather than silently recreating the relation. Re-creating a human-removed relation is the explicit anti-behavior — same conservative posture as the body/status who-wins ladder.

## Ralph-safe / autonomous-safe — never blocks

Every run emits a receipt (`flowctl sync receipt --status …`); genuine conflicts **queue** (`flowctl sync defer …`) rather than block. In autonomous / Ralph mode an `always-ask` tiebreak resolves to **queue**, not prompt — same policy, surface-dependent delivery. Deferred conflicts land in the **review deferred-findings sink** (`.flow/review-deferred/<branch>.md`) where the human already looks for deferred work — so tracker-sync never needs `flowctl block`, never stalls the loop. See [`ralph.md`](ralph.md).

The Phase-0 gate recognizes the **full autonomy marker family** (2.2.0+, fn-68 R14): `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, **`FLOW_AUTONOMOUS=1`, or the `mode:autonomous` token** — matching `work` / `make-pr` / `resolve-pr` / `capture`. tracker-sync was the **one** lifecycle-participating skill whose gate omitted `FLOW_AUTONOMOUS`; under the marker NO code path reaches a prompt (discovery ceremony, collision guard, genuine conflict, and `question` authoring all resolve "ask the human" to `sync defer`). This is what makes tracker-sync safe to call **per-tick from [`/flow-next:pilot`](../../skills/flow-next-pilot/SKILL.md) backlog mode** — a live prompt mid-tick would stall the whole autonomous loop.

## Backlog-mode enumeration + the async question-valve (2.2.0+, fn-68)

[`/flow-next:pilot`](../../skills/flow-next-pilot/SKILL.md) backlog mode reaches in front of the ready gate and enumerates the whole promoted lane, including tracker tickets with no Flow spec. It surfaces "stuck" as a **question, not a stall**. `flowctl tracker` now owns the deterministic enumeration and comment transport; **fn-141 R8 supersedes fn-57 R3**. The skill retains the semantic question text and recovery choice:

- **`flowctl tracker wire list-open`** enumerates promoted-lane open issues, filtered to the **exact** `tracker.readyState` state/label (no ordering, no "beyond"). It returns normalized `issue[]` so pilot can union tracker-only tickets with `flowctl specs`. When `tracker.readyState` is unset there is no promoted tracker lane: on **Linear** `list-open` now refuses with an explicit `unresolved`/`ready_state` error naming `tracker.readyState` (fn-182, #311) - a caller treats that refusal as "no ready lane configured", never as an empty board - while GitHub/GitLab/Jira still return the transport-free empty; backlog mode falls back to Flow-ready specs either way. Leaving `readyState` unset remains a legitimate, deliberate configuration.
- **`list-comments <tracker-id>`** maps to `flowctl tracker wire comment-list --locator …` for every tracker-only candidate before parked-state selection. Normalized comments include immutable `created_at`; a failed or truncated read fails closed.
- **`flowctl tracker wire relation-list --locator …`** reads one issue's normalized directed dependency rows for pilot ordering. The locator comes from the same `list-open` row: durable `issue.id` plus display `issue.identifier`. GitHub validates the issue but returns no rows because parent/sub-issue hierarchy is not blocked-by and must not order backlog work.
- **`flowctl tracker wire list-states`** enumerates the destination's workflow states read-only (Linear + Jira; GitHub/GitLab have no workflow-state pool and return a typed `capability` error). Output is the exhaustive `{"states":[{"id","name","type"}], "complete": bool}` shape; `complete: false` means the provider listing was truncated (partial states, exit 0 - the caller decides to refuse). Jira scopes the listing to the resolved `issueTypeId` - the same scoping `statusIds` is pinned to - and returns `unresolved` when it is missing or unmatched. It never writes `.flow/config.json`: `resolve` repairs and writes, `list-states` detects. This is the read primitive for "does every configured state id still name a live state?" - the comparison itself stays in the consumer.
- **`question <spec-id | tracker-id>`** is the skill-owned semantic operation. The skill composes the question text, then calls `flowctl tracker wire question` with the issue locator, four stable identity inputs, and a secure body file. flowctl computes the stable `id`, takes a local provider+issue+question claim, and reads existing comments. A concurrent identical ask returns retryable `question_in_flight`; its retry sees the winner's marker. Latest matching question means parked and dedups; latest matching answer posts a new round with the same id. Missing, tied, or truncated chronology fails closed. The `id` hashes `subjectId` + blocked-stage + reason code + question slug; free prose is outside the hash, so rephrasing never duplicates an open round. A human reply carries `<!-- flow-next:answer id=<hash> -->`, matched by `id` and imported under the matching `## Open Questions` entry. A tracker-only question has no spec receipt; its parked/answered state stays in tracker comments until `capture` or `interview` creates a spec.

See [`references/adapter-interface.md`](../../skills/flow-next-tracker-sync/references/adapter-interface.md) (the `listOpenIssues` contract + the `comment` reply/parent metadata), [`steps.md`](../../skills/flow-next-tracker-sync/steps.md) Phase 7 (the named-op bodies + the answer round-trip), and [`references/comments-sync.md`](../../skills/flow-next-tracker-sync/references/comments-sync.md) (the question-valve marker dedup).

## flowctl surface

The skill owns discovery choices, semantic body/comment composition, conflict adjudication, and recovery routing. [`flowctl tracker`](flowctl.md#flowctl-tracker) owns deterministic provider transport and mutation. [`flowctl sync`](flowctl.md#flowctl-sync) owns local bridge state, receipts, audits, and deferred-finding plumbing.

> Sync-engine shape (discovery ceremony, per-item `lastSyncedAt`, surface-diffs-never-overwrite) adapted from Ray Fernando's `running-bug-review-board` `issue-trackers.md` (Apache-2.0) — see CHANGELOG.

## Chart lifecycle projection

Optional operational view of a local chart (fn-135). **Local chart state is always canonical.** Enable with:

```bash
flowctl config set tracker.charts on   # string-enum off|on; only literal "on" activates
```

Requires the bridge active (`tracker.enabled` / typed tracker). When off or inactive, all `flowctl chart` operations succeed **local-only** - no remote calls, no failure.

### What projects

| Surface | Content |
|---|---|
| **Parent (chart)** | Outcome, chart status (`open\|done\|abandoned`), compact counts (actionable / blocked / claimed / resolved / superseded / out-of-scope / parked), latest resolved D-ID + title + gist, current frontier summary |
| **Children (decisions)** | D-ID + title, type, attendance, local status, blocking relation (`blocked_by[]` only - `depends_on[]` stays local unless an adapter has a lossless distinct relation), safe resolution gist, approved evidence references |

Full answers, unsafe assets, and secrets stay local. Claim changes do not masquerade as provider workflow status.

### Local-first lifecycle + receipts

Every local lifecycle transition (create/wire, claim/release, resolve, supersede, out-of-scope, briefing/done, abandon, reopen) **commits locally first**, then passes through the post-fn-141 facade with a **chart revision** and **idempotency marker**. A partial, failed, unsupported, or reordered remote update leaves a durable projection receipt and converges on **retry/reconcile** - it never rolls back the local transition. Provider-specific gaps in hierarchy, type, attendance, status, evidence, or rollup return as **explicit capability degradation** across Linear / GitHub / GitLab / Jira - never as a hard block on local discovery.

Tracker rollups are **visibility only** - never a control plane, roadmap, task board substitute, or PR status substitute.

### Pasted parent / decision URL re-entry

Pasting a projected chart or decision URL is a **re-entry convenience**, not identity. `flowctl chart locate <selector>`:

1. Normalizes only supported provider URL forms; validates configured host/project.
2. Resolves **strictly through the local provenance ledger** - no network search, no redirect following, no title inference.
3. On success, always reads back the **canonical local chart/D-ID, title, and record link** before work continues.
4. Parent URL re-anchors the chart; open decision URL selects that D-ID; **resolved or superseded** decision URL renders **history** and replacement/frontier options - never silently chooses different work.
5. Unrecorded, ambiguous, credential-bearing, wrong-host, stale-parent, or conflicting selectors fail with **structured detail and no mutation**. Fallback: use the local chart-id / D-ID directly.

Unsupported or stale URLs produce a local recovery path; they never create, relink, or guess a chart.

Skill surfaces and automation: [`../skills/flow-next-chart/SKILL.md`](../../skills/flow-next-chart/SKILL.md), [`flowctl.md`](flowctl.md#chart).

## See also

- [`flowctl tracker`](flowctl.md#flowctl-tracker) for deterministic provider verbs and [`flowctl sync`](flowctl.md#flowctl-sync) for local bridge state.
- [`flowctl.md`](flowctl.md#chart) - full chart CLI + locate contract.
- [`teams.md`](teams.md) - projection-not-coordination positioning, Symphony contrast, adoption ladder, chart handover.
- [`architecture.md`](architecture.md) - spec-JSON `tracker` fields, widened id resolver, charts layout.
- [`ralph.md`](ralph.md) - conflicts queue to deferred-decisions, never block.
