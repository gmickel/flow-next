# Tracker sync bridge

Project a flow-next spec to a tracker issue (Linear first, GitHub next) and reconcile body / status / comments two-way. Drives the `/flow-next:tracker-sync` skill plus the `flowctl sync …` plumbing.

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

Four probed signals:

| Signal | Probe | Means |
|---|---|---|
| Linear MCP registered | host MCP/tool list contains a Linear server (e.g. `*Linear*` tools) | interactive Linear transport available (OAuth handled) |
| `LINEAR_API_KEY` | `[ -n "$LINEAR_API_KEY" ]` | headless Linear GraphQL transport available |
| GitHub auth | `gh auth status` exits 0 | headless GitHub transport available |
| Jira host | a `*.atlassian.net` host configured/visible | Jira present — surfaced but out of scope (not offered) |

Resolution is **env > config > ASK** (mirrors `flowctl review-backend`): if env/config already decides the transport, the ceremony doesn't re-ask. On confirmation the skill writes via `flowctl config set tracker.…` and verifies with `flowctl sync active --json` (must report `active: true`). The bridge is active iff raw `tracker.enabled == true` **OR** raw `tracker.type ∈ {linear, github}`.

## Two entry flows — no fixed starting point

Both attach sync state **on link**:

1. **Author-in-flow-then-push (flow-first).** A `fn-NN` spec already exists. Push creates the tracker issue, then `flowctl sync set-tracker-id` attaches the issue UUID + `--identifier WOR-17` + `--url`. The `fn-NN` id is kept; the tracker key becomes a resolvable alias.
2. **Link-existing-issue (tracker-first): "grab issue X and spec it."** Fetch the issue, create the spec **keyed by the tracker key** (`flowctl spec create --tracker-first --tracker-identifier WOR-17`), seed the merge base from the current issue body, first pass is pull-only.

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

When **no transport is reachable**, the run is a **`noop` + receipt note** — never a crash. The transport actually used (`mcp` / `graphql` / `gh` / `none`) is recorded on every receipt.

## Lifecycle sync points (on by default — opt-out)

Sync is wired into seven lifecycle skills. **When you hook the bridge up via the `/flow-next:tracker-sync` discovery ceremony, the whole pipeline activates by default** — the point of connecting a tracker is to keep it in sync, so you don't opt in event-by-event. You **opt out** instead: exclude events at ceremony time, or turn any off later with `flowctl config set tracker.perEvent.<event> off`. Leaf values: `off | pull | push | reconcile | comment`.

| Event | Config key | Default op | Fires when |
|---|---|---|---|
| capture | `tracker.perEvent.capture` | `reconcile` | a spec is captured |
| interview | `tracker.perEvent.interview` | `reconcile` | a spec is refined |
| plan | `tracker.perEvent.plan` | `reconcile` | a spec is decomposed into tasks |
| work (first claim) | `tracker.perEvent.work.firstClaim` | `push` | the first task of a spec is claimed |
| work (done) | `tracker.perEvent.work.done` | `comment` | a task completes |
| make-pr | `tracker.perEvent.makePr` | `comment` | a PR is opened |
| resolve-pr | `tracker.perEvent.resolvePr` | `comment` | PR threads are resolved |
| completion review | `tracker.perEvent.completionReview` | `reconcile` | a spec-completion review runs |

The lifecycle skills value-check `flowctl sync active` and the specific `perEvent` leaf, short-circuiting cleanly when the bridge is off or an event was opted out — so a no-tracker repo (or an excluded event) costs a single value-check, no transport.

**Observable + forcing (fn-57).** Every lifecycle dispatch is **event-tagged**: the tracker-sync skill writes its receipt with `--event <perEvent-key>` (`work.firstClaim`, `work.done`, `capture`, `makePr`, …), so `.flow/sync-runs/` records which touchpoint each run served. At end-of-skill, **work, capture, and make-pr** run the read-only audit `flowctl sync check <spec-id> --events <triggered-csv> --since <run-anchor>` — independently of the touchpoints themselves, so a wholesale-skipped dispatch block is still caught. An event is `MISSING` iff it triggered this run AND its `perEvent` leaf is enabled AND the bridge is active AND no receipt with a matching `event` tag and `timestamp ≥ --since` exists (any receipt status clears — the check asserts the touchpoint *ran*; the receipt's own status carries success/failure detail). A `MISSING` event is **retro-fired exactly once** — the skill re-dispatches the missed touchpoint via tracker-sync, then re-checks against a fresh `--since` — and the skill's final summary carries a mandatory four-state `Tracker sync:` slot: `OK` | `MISSING:<event> → retro-fired → OK` | `MISSING:<event> (retro-fire failed: <reason>)` | `n/a (bridge inactive)`. An explicit `n/a` proves the check ran; an absent slot is visible as a skipped check. With no tracker configured `sync check` exits silently in constant time — non-tracker repos see no change anywhere.

**Auto-link on first touch (create-if-unlinked).** When a lifecycle event fires for a spec that isn't yet linked — e.g. you went straight to `/flow-next:plan` instead of `/flow-next:capture` — the tracker-sync skill **flow-first-pushes (creates the issue + links it) *before* running the event's operation**, then later events reconcile the now-linked spec (skill `steps.md` §Phase 3 "create-if-unlinked"). That is the point of the opt-out model: an active bridge keeps **every** in-flow-authored spec in sync, not just the ones you remembered to link by hand. The spec ↔ one-issue grain is unchanged — tasks never become sub-issues. Only `unlink` no-ops on an unlinked spec; every other op creates-then-syncs (and still no-ops cleanly if no transport is reachable).

**Activation is ceremony-gated, not flag-gated.** The config *schema* default for every `perEvent` leaf stays `off`, so a bare `tracker.enabled=true` set by hand or a script — without running the discovery ceremony — fires **no lifecycle-event sync** (every `perEvent` event stays dormant). Only the ceremony's explicit per-event writes (or your own `config set`) turn events on. This keeps the accidental-enable guard while making the *intended* path (run the ceremony) sync everything. **The one thing that is *not* gated this way is make-pr's PR↔issue link** — it's unconditional whenever the bridge is active (the exception documented just below), so a bare `enabled=true` plus a linked spec will still add a `Ref` line on the next make-pr. That linkage is cheap, conflict-free, and the whole point (Linear Diffs); it does not mutate the spec or fire the lifecycle touchpoints.

**One exception — PR linkage is unconditional when the bridge is active.** make-pr always links the new PR to its tracker issue when `sync active` and the issue is linked — it does **not** require opting `makePr` in. Linking a PR to its issue is zero-/near-zero-cost hygiene and is the whole value (it powers Linear Diffs, below), so there's no reason to gate it. The `perEvent.makePr` leaf still governs any *extra* make-pr sync (e.g. a status comment). make-pr additionally **verifies the ref landed** post-create (§4.6b): it fetches the LIVE PR body via `gh pr view --json body` and, when the `Ref <identifier>` line is absent (e.g. an agent hand-rolled `gh pr create` and bypassed the deterministic append), repairs it append-only via `gh pr edit` — mechanical, idempotent, fully non-fatal.

### MISSING after retro-fire — recovery

A `Tracker sync: MISSING:<event> (retro-fire failed: <reason>)` summary line means the touchpoint didn't fire AND the one bounded retro-fire couldn't recover it — typically no reachable transport (MCP server down, no `LINEAR_API_KEY`, `gh` unauthenticated). The primary work is unaffected: tracker sync is best-effort and never blocks, so the task is done / the PR is open. To recover by hand:

1. **Read the failure reason** from the run's receipts: `ls -t .flow/sync-runs/sync-<spec-id>-*.json | head -3` — the `status` (`noop` / `errored`) and `note` fields on the event-tagged receipt say why it failed.
2. **Once transport returns**, re-fire the missed touchpoint manually via the skill: `/flow-next:tracker-sync push <spec-id>` for status events (`work.firstClaim`, `work.completionReview`), or the matching op for comment events (`comment <spec-id>` for `work.done` / `makePr`).
3. **Verify**: `flowctl sync check <spec-id> --events <event> --since <retro-fire-time>` now prints `OK:<event>`.

## Linear Diffs — review the PR inside the issue

[Linear Diffs](https://linear.app/docs/diffs) (GA May 2026) renders a GitHub PR's diff, file changes, checks, and inline review threads directly on the Linear issue, and lets you approve / request changes / merge from Linear. flow-next makes your PRs **Diffs-ready automatically** when `tracker.type == linear`:

- **What flow-next does:** make-pr puts a **non-closing** `Ref WOR-N` line in the PR body (make-pr §4.6a) so Linear's GitHub integration auto-links the PR to the issue — which is exactly what makes the diff render. On the GraphQL transport it also creates the rich PR attachment (`attachmentLinkURL`) for status sync. *Non-closing* (`Ref`, not `Fixes`) is deliberate: the PR links + renders as a diff but does **not** auto-complete the Linear issue on merge — flow-next's spec-completion-review owns the Done transition.
- **What you must enable (one-time, Linear-side — flow-next can't set these):** the Linear **GitHub integration with code access** to the repo, your **personal GitHub connection**, and **"Enable code reviews"** in Linear settings. Without them the PR still links and status still syncs; only the rendered diff view needs them.
- **GitHub tracker:** no Linear Diffs — the PR is cross-linked natively (`Refs #N`) in the same repo; review happens on GitHub.

## Reconciliation — who-wins

- **Body** — agentic host-agent semantic **3-way merge** against the `lastSyncedAt` merge-base snapshot, translating between flow's structured spec and the tracker's free-form issue. Only **genuine contradictions** surface; confident merges proceed.
- **Status** — per-field **who-wins** ladder. The collision/deadlock case is evaluated **before** single-field terminal-wins rules (a `tracker=done × flow=…` deadlock must fall to `conflictTiebreak`, not be silently overwritten by terminal-wins). Tiebreak is `tracker.conflictTiebreak` (`flow-wins | tracker-wins | always-ask`, default `always-ask`).
- **Comments / evidence** — two-way **append** with dedup; neither side overwrites the other.

## Ralph-safe — never blocks

Every run emits a receipt (`flowctl sync receipt --status …`); genuine conflicts **queue** (`flowctl sync defer …`) rather than block. In autonomous / Ralph mode an `always-ask` tiebreak resolves to **queue**, not prompt — same policy, surface-dependent delivery. Deferred conflicts land in the **review deferred-findings sink** (`.flow/review-deferred/<branch>.md`) where the human already looks for deferred work — so tracker-sync never needs `flowctl block`, never stalls the loop. See [`ralph.md`](ralph.md).

## flowctl surface

The skill owns judgment (API calls, reconciliation, asking); `flowctl sync` owns deterministic plumbing. Full flag reference in [`flowctl.md`](flowctl.md#sync) — `sync active` / `get-state` / `set-tracker-id` / `set-last-synced` / `set-merge-base` / `clear` / `list-unsynced` / `list-stale` / `check-collisions` / `receipt` (event-tagged via `--event <perEvent-key>`) / `check` (read-only lifecycle audit, `OK`/`MISSING` per event) / `defer`, plus the `tracker.*` config keys.

> Sync-engine shape (discovery ceremony, per-item `lastSyncedAt`, surface-diffs-never-overwrite) adapted from Ray Fernando's `running-bug-review-board` `issue-trackers.md` (Apache-2.0) — see CHANGELOG.

## See also

- [`flowctl.md`](flowctl.md#sync) — `flowctl sync` subcommands + `tracker.*` config keys.
- [`teams.md`](teams.md) — projection-not-coordination positioning, Symphony contrast, adoption ladder.
- [`architecture.md`](architecture.md) — spec-JSON `tracker` fields, widened id resolver.
- [`ralph.md`](ralph.md) — conflicts queue to deferred-decisions, never block.
