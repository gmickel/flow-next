# Architecture

How flow-next stores state, how the spec-first task model works, and the separation of concerns between metadata and narrative content.

## Spec-first task model

Flow-next does not support standalone tasks. Every unit of work belongs to a spec `fn-N-slug` (even if it's a single task). Tasks are always `fn-N-slug.M` and inherit context from the parent spec.

Flow-next always creates a spec container (even for one-offs) so every task has a durable home for context, re-anchoring, and automation. You never have to think about it.

Rationale: keeps the system simple, improves re-anchoring, makes automation (Ralph) reliable.

"One-off request" → spec with one task.

## `.flow/` directory layout

```
.flow/
├── meta.json              # Schema version (1.0+ uses `next_spec`; reads `next_epic` for back-compat)
├── config.json            # Project settings (memory enabled, etc.)
├── .flow_version          # 1.0.0 sentinel — written after `flowctl migrate-rename`
├── .gitignore             # Auto-managed by flowctl (1.0+) — excludes migration transients
├── specs/
│   ├── fn-1-add-oauth.md        # Spec content (plan, scope, acceptance)
│   └── fn-1-add-oauth.json      # Spec metadata (id, title, status, deps) — colocated with markdown in 1.0+
├── tasks/
│   ├── fn-1-add-oauth.1.json    # Task metadata (id, status, priority, deps, assignee, `spec` field)
│   ├── fn-1-add-oauth.1.md      # Task spec (description, acceptance, done summary)
│   └── ...
└── memory/                # Persistent learnings (opt-in, categorized — v0.33.0+)
    ├── bug/               # Track: failures / defects
    │   ├── build-errors/
    │   ├── test-failures/
    │   ├── runtime-errors/
    │   ├── performance/
    │   ├── security/
    │   ├── integration/
    │   ├── data/
    │   └── ui/
    ├── knowledge/         # Track: patterns / decisions / conventions
    │   ├── architecture-patterns/
    │   ├── conventions/
    │   ├── tooling-decisions/
    │   ├── workflow/
    │   └── best-practices/
    └── legacy/            # (optional) archived flat files after migrate
```

Pre-1.0 repos have `.flow/epics/<id>.json` instead of `.flow/specs/<id>.json`; the alias layer keeps reads working until you run `flowctl migrate-rename --yes` (or `/flow-next:setup`'s upgrade branch).

The auto-managed `.flow/.gitignore` (written by `flowctl init` and `flowctl migrate-rename` since 1.0.0) excludes per-run state (`.checkpoint-*.json`, `receipts/`, `tmp/`) and migration transients (`.backup-pre-1.0/`, `.banner-acknowledged`, `.migrating`, `.migration-manifest`) so users don't accidentally commit a multi-megabyte backup directory or a per-developer banner-ack timestamp on `git add -A`. User patterns added below the auto-managed footer are preserved on subsequent runs. `.flow/.flow_version` is intentionally tracked (schema sentinel; semantics like `Cargo.lock`).

Flowctl accepts schema v1 and v2; new fields are optional and defaulted.

New fields:
- Spec JSON: `plan_review_status`, `plan_reviewed_at`, `completion_review_status`, `completion_reviewed_at`, `depends_on_specs` (1.0+ canonical; `depends_on_epics` accepted on read), `branch_name`
- Spec JSON `ready` (1.12.0+, lazy): the human-owned readiness gate. **Written only after a toggle changes state** (`flowctl spec ready` / `spec unready`) — `spec create` never writes it, and an absent key reads `false` — so non-adopters' sidecars stay byte-identical. Every JSON read surface (`show`, `specs`, `list`) emits an explicit `"ready": <bool>` regardless. Orthogonal to `status`; `capture --rewrite` resets it to `false` (a full re-authoring re-opens the blessing — interview refinement never resets it). For tracker-connected repos, `tracker.readyState` projects the tracker state onto this flag on every pull-side sync (one-way; tracker authoritative) — see [`tracker-sync.md`](tracker-sync.md).
- Spec JSON `tracker` block (tracker-sync, defaulted/optional): `tracker.id` (tracker UUID — durable dedupe key), `identifier` (display key `WOR-17`), `url`, `lastSyncedAt` (advances only on a real reconcile), `baseHashFlow` / `baseHashTracker` (echo-fence content hashes), `mergeBaseFlow` / `mergeBaseTracker` (paired body snapshots — the 3-way merge base, written atomically as a unit). Full schema: [`tracker-sync.md`](tracker-sync.md).
- Task JSON: `priority`. The 1.0+ canonical field name for the parent reference is `spec`; `epic` is accepted on read for back-compat through 1.x and emitted on write only by pre-1.0 callers.

## ID format

- **Spec**: `fn-N-slug` where `slug` is derived from the spec title (e.g., `fn-1-add-oauth`, `fn-2-fix-login-bug`)
- **Task**: `fn-N-slug.M` (e.g., `fn-1-add-oauth.1`, `fn-2-fix-login-bug.2`)

The slug is automatically generated from the spec title (lowercase, hyphens for spaces, max 40 chars). This makes IDs human-readable and self-documenting.

**Backwards compatibility**: Legacy formats `fn-N` (no suffix) and `fn-N-xxx` (random 3-char suffix) are still fully supported. Existing specs don't need migration.

**Hybrid id model (tracker-sync, R16)**: a tracker-linked spec may be keyed two ways, which coexist with `fn-NN`. A **tracker-first** spec is canonically `wor-17-slug` (tasks `wor-17-slug.M`, branch `wor-17-slug`); bare `wor-17` / `wor-17.M` resolve as aliases. A **flow-first** spec keeps `fn-NN-slug` and stores the tracker key in `tracker.identifier` (display form `WOR-17`) as a resolvable display alias. flowctl widened the **id resolver / canonicalizer** (`is_spec_id` / `expand_bare_spec_id`) so every command inherits **case-insensitive** resolution — `show wor-17`, `work wor-17`, `plan wor-17` all resolve — and the **origin-branched id generator** (`spec create --tracker-first`) keys by the tracker identifier instead of allocating a fresh `fn-NN`. The native `fn-` scheme is reserved; `fn-N` allocation counts `fn-*` only (a `wor-9999` never bumps the next `fn`). **One tracker team per repo**; **ids never rename** on link. Full model: [`tracker-sync.md`](tracker-sync.md).

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

- Task tracking lives in `.flow/` (bundled flowctl, no external tracker).
- Install: plugin only — no external services, no config-file edits.
- Artifacts: `.flow/specs/` (markdown + JSON sidecar) and `.flow/tasks/` (markdown + JSON sidecar).
- Multi-user safe: scan-based IDs + soft claims.
- Uninstall: delete `.flow/` (and `scripts/ralph/` if enabled). `GLOSSARY.md` / `STRATEGY.md` at the repo root persist by design.

## See also

- [`spec-template.md`](spec-template.md) — canonical scaffold + acceptance-criteria discipline.
- [`memory-schema.md`](memory-schema.md) — categorized `.flow/memory/` schema.
- [`flowctl.md`](flowctl.md) — full CLI reference.
- [`../README.md`](../README.md) — plugin overview.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) — Spec, Task, Handover object, Receipt.
