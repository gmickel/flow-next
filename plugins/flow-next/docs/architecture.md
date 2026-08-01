# Architecture

How flow-next stores state, how the spec-first task model works, and the separation of concerns between metadata and narrative content.

The design tenet behind all of it: **everything lives in the repo**. Specs, tasks, memory, receipts are plain markdown + JSON under `.flow/` - in git, code-reviewable, diff-able, fork-survivable. No external services, no global config, no database. Uninstall is `rm -rf .flow/`.

## Spec-first task model

Flow-next does not support standalone tasks. Every unit of work belongs to a spec `fn-N-slug` (even if it's a single task). Tasks are always `fn-N-slug.M` and inherit context from the parent spec.

Flow-next always creates a spec container (even for one-offs) so every task has a durable home for context, re-anchoring, and automation. You never have to think about it.

Rationale: keeps the system simple, improves re-anchoring, makes automation (Ralph) reliable.

"One-off request" → spec with one task.

## `.flow/` directory layout

```
.flow/
├── meta.json              # Schema version (1.0+ uses `next_spec`)
├── config.json            # Project settings (memory, review, tracker, …)
├── .flow_version          # Schema sentinel (tracked; semantics like Cargo.lock)
├── .gitignore             # Auto-managed by flowctl - excludes per-run state
├── usage.md               # Agent CLI reference (written by /flow-next:setup)
├── bin/                   # Local flowctl install (via /flow-next:setup)
│   ├── flowctl            # bash launcher
│   ├── flowctl.cmd        # Windows launcher
│   └── flowctl.py         # Python entrypoint
├── templates/
│   └── spec.md            # Setup-managed copy of the canonical scaffold
├── specs/
│   ├── fn-1-add-oauth.md        # Spec content (plan, scope, acceptance)
│   └── fn-1-add-oauth.json      # Spec metadata (id, title, status, deps)
├── tasks/
│   ├── fn-1-add-oauth.1.json    # Task metadata (id, status, priority, deps, assignee, `spec` field)
│   ├── fn-1-add-oauth.1.md      # Task spec (description, acceptance, done summary)
│   └── ...
├── charts/                # Optional pre-capture decision maps (fn-135)
│   ├── fn-140.md                # Chart map body (Outcome, Notes, Decisions ledger, Open Questions, Boundaries)
│   ├── fn-140.json              # Chart metadata (id, title, outcome, status, decisions[], briefings[], tracker, produced_specs[])
│   ├── fn-140/                  # Decision records (one pair per D-ID)
│   │   ├── 1.md                 # ## Question body for D1
│   │   ├── 1.json               # Decision sidecar (type, attendance, status, graph, claim, answer, assets)
│   │   └── ...
│   ├── fn-140-briefing.md       # Briefing index (immutable versioned handoff for capture)
│   ├── fn-140-briefing-1.md     # Per-cluster briefing when a multi-spec split is confirmed
│   └── .transactions/           # (auto-gitignored) write-ahead journal for multi-file chart mutations
├── memory/                # Persistent learnings (opt-in, categorized)
│   ├── bug/               # Track: failures / defects
│   │   ├── build-errors/
│   │   ├── test-failures/
│   │   ├── runtime-errors/
│   │   ├── performance/
│   │   ├── security/
│   │   ├── integration/
│   │   ├── data/
│   │   └── ui/
│   ├── knowledge/         # Track: patterns / decisions / conventions
│   │   ├── architecture-patterns/
│   │   ├── conventions/
│   │   ├── tooling-decisions/
│   │   ├── workflow/
│   │   └── best-practices/
│   └── legacy/            # (optional) archived flat files after migrate
├── artifacts/             # HTML lenses + immutable PR cognitive-aid generations
│   └── <spec-id>/pr-cognitive-aid/<artifactId>.json
├── review-receipts/       # Review receipt copies kept under .flow/
│   └── <receipt>.json.history/
│       └── <digest>.json  # Immutable structured-finding generations
├── receipts/              # (auto-gitignored) Ralph/runtime receipt scratch
├── sync-runs/             # (auto-gitignored) tracker-sync run receipts
├── pilot-runs/            # (auto-gitignored) pilot backlog decision-log rows
├── locks/                 # (auto-gitignored) setup-block serialization locks
├── tmp/                   # (auto-gitignored) scratch (green receipts, codex-*)
└── .cache/                # (auto-gitignored) CLI model-resolution cache
```

`flowctl init` creates `specs/`, `tasks/`, `memory/`, `meta.json`, `config.json`, and the auto-managed `.gitignore`. `/flow-next:setup` additionally stamps `bin/`, `templates/`, and `usage.md`. Runtime dirs (`sync-runs/`, `pilot-runs/`, `locks/`, `tmp/`, `receipts/`, `.cache/`) appear on first use and stay gitignored. `charts/` and `charts/.transactions/` appear on first `/flow-next:chart` / `flowctl chart create` (the WAL is gitignored; chart maps and decision records are tracked like specs).

### Charts layout (fn-135)

Charts share the native `fn-N` allocation domain with specs: one cross-kind counter under a shared lock scans specs and charts across the working tree, linked worktrees, and visible refs, then reserves the next id with no-clobber creation. `flowctl spec create` and `flowctl chart create` therefore cannot race into the same id. Chart kind is distinct so `flowctl list` can render charts separately.

| Path | Role |
|---|---|
| `.flow/charts/<id>.md` | Map body at gist level: `## Outcome`, `## Notes`, append-only `## Decisions` ledger, `## Open Questions`, `## Boundaries`. Never restates full answers. |
| `.flow/charts/<id>.json` | Sidecar: `id`, `title`, `outcome`, `status` (`open\|done\|abandoned`), `decisions[]`, `briefings[]` (append-only; per-briefing `status` lives here and is the single source of truth for capture-readiness), optional `tracker` projection keys, `produced_specs[]`, audited force/break-claim events. |
| `.flow/charts/<id>/<n>.md` + `.json` | Decision record pair (local number `n` = D-ID). Body is `## Question` only; sidecar holds type, attendance, status, `blocked_by[]` / `depends_on[]`, claim, answer, assets. |
| `.flow/charts/<id>-briefing-B<k>.md` (+ `-B<k>-<cluster>.md`) | Immutable per-version briefing package for capture (`B1`, `B2`, ...), one file per B-ID plus one per cluster when the proposal splits. The unversioned `<id>-briefing.md` / `<id>-briefing-<cluster>.md` paths are always-latest convenience copies, rewritten on every emission. A `reopen` stales prior packages; the re-brief that follows advances the counter to `B(n+1)` rather than reinstating a staled B-ID, so the reversal stays in the ledger. |
| `.flow/charts/.transactions/` | Crash-recovery WAL: pre-state fingerprints, intended mutation set, publication phase. Every chart command recovers an incomplete journal under the resource lock before reading state. |

Multi-file chart mutations (map + sidecars + ledger + dependent cascade) are one recoverable transaction: no-clobber creates, staged replacements, atomic rename, rollback to pre-call state on failure. Full CLI contract: [`flowctl.md`](flowctl.md#chart).

Review receipts may contain the optional versioned `findings` projection. Before
advancing a latest receipt pointer, Flow-Next preserves its valid prior
generation in `<receipt-path>.history/<sha256(sourceReceiptId)>.json`. The
history is an immutable evidence chain, not a second current-state store.
Consumers select one head-current chain tip and fail closed on ambiguity; see
[`review-findings.md`](review-findings.md).

PR cognitive-aid generations use a separate immutable chain under
`.flow/artifacts/<spec-id>/pr-cognitive-aid/`. The newest valid chain tip is
current only when both its base and head SHAs match the live PR identity.
Consumers enumerate that documented home and use labeled fallback states on
stale, unsupported, or invalid input; see
[`pr-cognitive-aid.md`](pr-cognitive-aid.md).

Pre-1.0 repos that still have `.flow/epics/<id>.json` must port by hand: see `.flow/usage.md` "Pre-1.0 layout porting" (and `docs/troubleshooting.md`). The automated `migrate-rename` path was removed in fn-111.

The auto-managed `.flow/.gitignore` (written by `flowctl init`) excludes per-run state (`.checkpoint-*.json`, `receipts/`, `tmp/`, `sync-runs/`, `pilot-runs/`, `locks/`, `.cache/`) and historical migration transients (`.backup-pre-1.0/`, `.banner-acknowledged`, `.migrating`, `.migration-manifest`) so users don't accidentally commit runtime artifacts on `git add -A`. User patterns added below the auto-managed footer are preserved on subsequent runs. `.flow/.flow_version` is intentionally tracked (schema sentinel; semantics like `Cargo.lock`).

Flowctl accepts schema v1 and v2; new fields are optional and defaulted.

New fields:
- Spec JSON: `plan_review_status`, `plan_reviewed_at`, `completion_review_status`, `completion_reviewed_at`, `depends_on_epics` (canonical JSON field name for cross-spec deps), `branch_name`
- Spec JSON `ready` (1.12.0+, lazy): the human-owned readiness gate. **Written only after a toggle changes state** (`flowctl spec ready` / `spec unready`) - `spec create` never writes it, and an absent key reads `false` - so non-adopters' sidecars stay byte-identical. Every JSON read surface (`show`, `specs`, `list`) emits an explicit `"ready": <bool>` regardless. Orthogonal to `status`; `capture --rewrite` resets it to `false` (a full re-authoring re-opens the blessing - interview refinement never resets it). For tracker-connected repos, `tracker.readyState` projects the tracker state onto this flag on every pull-side sync (one-way; tracker authoritative) - see [`tracker-sync.md`](tracker-sync.md).
- Spec JSON `tracker` block (tracker-sync, defaulted/optional): `tracker.id` (tracker UUID - durable dedupe key), `identifier` (display key `WOR-17`), `url`, `lastSyncedAt` (advances only on a real reconcile), `baseHashFlow` / `baseHashTracker` (echo-fence content hashes), `mergeBaseFlow` / `mergeBaseTracker` (paired body snapshots - the 3-way merge base, written atomically as a unit). Full schema: [`tracker-sync.md`](tracker-sync.md).
- Task JSON: `priority`. The parent reference field is `spec`.

### Review bookkeeping: authority and write-ordering

The spec sidecar carries two views of review state. `review_attempts[]` is the
authoritative ledger - one row per finalized reservation, with backend,
outcome, verdict, output hash, and (best-effort) the `head_sha` the review
observed (the pre-dispatch snapshot on the in-process backend paths;
finalize-time HEAD is the fallback where no snapshot exists, e.g. rp). `plan_review_status` / `completion_review_status` (plus their
`*_reviewed_at` stamps) are a denormalized read model derived from that
ledger; when the two ever diverge, the ledger wins.

Write-ordering differs by path, on purpose:

- **In-process plan review** (`flowctl codex|copilot|cursor plan-review`)
  finalizes the attempt row, writes `plan_review_status`, and performs the
  SHIP round-counter reset as ONE atomic sidecar write inside
  `record_review_attempt` - there is no interrupt window where the ledger
  carries a verdict the status field has not seen.
- **In-process completion review** deliberately stays two writes: the receipt
  (and its recovery payload) must persist BEFORE the terminal
  `completion_review_status` lands. That ordering is a recovery contract - if
  the process dies between the writes, status stays non-terminal and the
  skill restores from the recovery payload instead of dispatching another
  round. The SHIP cap reset is folded into the attempt write; the status
  write stays separate, with the ledger authoritative on divergence.
- **Host/rp paths** (`flowctl review-rounds record`,
  `set-plan-review-status`, `set-completion-review-status`) are separate CLI
  invocations by design - the host agent sequences them - and the same
  authority rule applies: the ledger row is the record of what happened; the
  status field is the projection.

## ID format

- **Spec**: `fn-N-slug` where `slug` is derived from the spec title (e.g., `fn-1-add-oauth`, `fn-2-fix-login-bug`)
- **Task**: `fn-N-slug.M` (e.g., `fn-1-add-oauth.1`, `fn-2-fix-login-bug.2`)
- **Chart**: same native `fn-N` (or `fn-N-slug`) domain as specs; kind is chart, never a task. Decision: `<chart-id>.D<n>` (e.g., `fn-140.D2`); local form `D<n>` is chart-scoped.

The slug is automatically generated from the spec title (lowercase, hyphens for spaces, max 40 chars). This makes IDs human-readable and self-documenting.

**Backwards compatibility**: Legacy formats `fn-N` (no suffix) and `fn-N-xxx` (random 3-char suffix) are still fully supported. Existing specs don't need migration.

**Native `fn-N` allocation (fn-134 + fn-135)** takes the max across the working tree, every registered git worktree's `.flow/specs/` **and** `.flow/charts/`, and every ref (monotonic; fail-open on git problems). Specs and charts share one allocator under one lock - a chart and a spec never share an id. That shrinks parallel-agent collisions; separate unfetched clones can still collide.

**Hybrid id model (tracker-sync, R16 / fn-134)**: a tracker-linked spec may be keyed two ways, which coexist with `fn-NN`. A **tracker-first** spec is canonically `wor-17-slug` (Linear/Jira native `KEY-N`) or synthetic `gh-123-slug` / `gl-456-slug` (GitHub `#123` / GitLab project-scoped `iid`); bare `wor-17` / `gh-123` / `gl-456` resolve as aliases. A **flow-first** spec keeps `fn-NN-slug` and stores the tracker key in `tracker.identifier` as a resolvable display alias. `tracker.specIds=tracker` makes skills route to tracker-first by default when the bridge is active. flowctl widened the **id resolver / canonicalizer** so every command inherits **case-insensitive** resolution, and the **origin-branched id generator** (`spec create --tracker-first`) keys by the tracker identifier instead of allocating a fresh `fn-NN`. **`fn` is the only globally reserved prefix**; synthetic `gh`/`gl` are reserved only while `tracker.type` matches. Native `fn-N` allocation counts `fn-*` only. **One tracker team per repo**; **ids never rename** on link. Full model: [`tracker-sync.md`](tracker-sync.md).

There are no task IDs outside a spec. If you want a single task, create a spec with one task.

## Separation of concerns

- **JSON files**: Metadata only (IDs, status, dependencies, assignee)
- **Markdown files**: Narrative content (specs, descriptions, summaries)

Skills and the host agent read the markdown for content; flowctl reads the JSON for plumbing. This split makes the two surfaces independently evolvable: schema changes in JSON without touching markdown, prose edits in markdown without touching schema.

## Task completion

When a task completes, `flowctl done` appends two structured sections to the task spec markdown.

### Done Summary

```markdown
## Done summary

- Added ContactForm component with Zod validation
- Integrated with server action for submission
- All tests passing

Follow-ups:
- Consider rate limiting (out of scope)
```

### Evidence

```markdown
## Evidence

- Commits: a3f21b9
- Tests: bun test
- PRs:
```

This creates a complete audit trail: what was planned, what was done, how it was verified.

## flow-next vs flow

The legacy `flow` plugin was removed in flow-next 1.0.2 (commit `ffc7189`). The repo now ships flow-next only. The historical comparison table lives in CHANGELOG; the live shape is:

- Task tracking lives in `.flow/` (no external tracker). flowctl reaches it either as a repo-local copy (`.flow/bin/`, copy mode) or straight off the plugin's PATH-injected `bin/` (plugin mode, Claude Code — see [platforms.md → Setup modes](platforms.md#setup-modes-plugin-vs-copy-fn-121)).
- Install: plugin only - no external services, no config-file edits.
- Artifacts: `.flow/specs/` (markdown + JSON sidecar), `.flow/tasks/` (markdown + JSON sidecar), and optionally `.flow/charts/` (decision maps + decision records + briefings).
- Multi-user safe: scan-based IDs + soft claims (task assignee; chart decision claims).
- Uninstall: delete `.flow/` (and `scripts/ralph/` if enabled). `GLOSSARY.md` / `STRATEGY.md` at the repo root persist by design.

## See also

- [`spec-template.md`](spec-template.md) - canonical scaffold + acceptance-criteria discipline.
- [`memory-schema.md`](memory-schema.md) - categorized `.flow/memory/` schema.
- [`review-findings.md`](review-findings.md) - portable structured-review
  receipt contract and currentness rules.
- [`flowctl.md`](flowctl.md) - full CLI reference (including [`chart`](flowctl.md#chart)).
- [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md) - optional pre-capture decision-map skill.
- [`../README.md`](../README.md) - plugin overview.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) - Spec, Chart, D-ID, Task, Handover object, Receipt.
