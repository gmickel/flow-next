# flowctl CLI Reference

CLI for `.flow/` task tracking. Agents must use flowctl for all writes.

> **Note:** This is the full human reference. Agents should read `.flow/usage.md` (created by `/flow-next:setup`).

## Available Commands

```
init, detect, status, config, review-backend, memory, prospect, glossary, strategy,
spec, task, dep, show, specs, tasks, list, cat, anchor, ready, next, start, done, block,
state-path, migrate-state, migrate-rename, migrate-rollback, validate, triage-skip,
checkpoint, prep-chat, repo-map, sync,
ralph, rp, codex, copilot, cursor,
review-deep-auto, review-walkthrough-defer, review-walkthrough-record
```

> **Renamed in 1.0.0:** `epic` → `spec`, `epics` → `specs`, `--epic` flag → `--spec`. Legacy forms continue to work as thin aliases with one-line stderr deprecation warnings (suppress via `FLOW_NO_DEPRECATION=1`); soft-removal target is 2.0.0, telemetry-driven (R28 forbids hard-coded sunset dates). See [Deprecated aliases](#deprecated-aliases) below.

## Multi-User Safety

Works out of the box for parallel branches. No setup required.

- **ID allocation**: Scans existing files to determine next ID (merge-safe)
- **Soft claims**: Tasks have `assignee` field to prevent duplicate work
- **Actor resolution**: `FLOW_ACTOR` env → git email → git name → `$USER` → "unknown"
- **Local validation**: `flowctl validate --all` catches issues before commit

**Optional**: Add CI gate with `docs/ci-workflow-example.yml` to block bad PRs.

## File Structure

```
.flow/
├── meta.json                  # {schema_version, next_spec}
├── .flow_version              # 1.0.0 sentinel — written after `flowctl migrate-rename`
├── specs/fn-N-slug.json       # Spec state (e.g., fn-1-add-oauth.json) — colocated with .md in 1.0+
├── specs/fn-N-slug.md         # Spec markdown
├── tasks/fn-N-slug.M.json     # Task state (e.g., fn-1-add-oauth.1.json)
├── tasks/fn-N-slug.M.md       # Task spec (markdown)
├── memory/                    # Agent memory (reserved)
├── bin/                       # (optional) Local flowctl install via /flow-next:setup
│   ├── flowctl                # bash launcher (Git Bash / WSL / macOS / Linux)
│   ├── flowctl.cmd            # batch launcher (cmd.exe / PowerShell) — probes py -3/python3/python
│   └── flowctl.py             # Python entrypoint (all CLI logic)
└── usage.md                   # (optional) CLI reference via /flow-next:setup
```

Both launchers resolve a working Python by **probing functionality** (`<cand> -c "import sys"`, order `$PYTHON_BIN` → `py -3` → `python3` → `python`) so the Windows Microsoft Store `python3` alias stub is skipped (fn-77). `flowctl init` re-stamps **both** `bin/flowctl` and `bin/flowctl.cmd` from in-module launcher constants, so an existing install self-heals a pre-fix launcher without a full `/flow-next:setup` re-run — see [`platforms.md` → Windows: Python discovery](platforms.md#windows-python-discovery).

Pre-1.0 layout had spec JSON sidecars at `.flow/epics/fn-N-slug.json` (the markdown was already at `.flow/specs/fn-N-slug.md`). The alias layer keeps reads working until you run `flowctl migrate-rename --yes` (or `/flow-next:setup`'s upgrade branch).

Flowctl accepts schema v1 and v2 (and v3 post-migration); new fields are optional and defaulted.

New fields:
- Spec JSON: `plan_review_status`, `plan_reviewed_at`, `completion_review_status`, `completion_reviewed_at`, `depends_on_epics` (JSON field name preserved for back-compat; reads accept both keys), `branch_name`, `default_impl`, `default_review`, `default_sync`, `ready` (1.12.0+, lazy — written only after a toggle; absent reads `false`)
- Task JSON: `priority`, `impl`, `review`, `sync`

## ID Format

- **Spec**: `fn-N-slug` where `slug` is derived from the title (e.g., `fn-1-add-oauth`, `fn-2-fix-login-bug`)
- **Task**: `fn-N-slug.M` (e.g., `fn-1-add-oauth.1`, `fn-2-fix-login-bug.2`)

**Backwards compatibility**: Legacy formats `fn-N` (no suffix) and `fn-N-xxx` (random 3-char suffix) are still supported.

## Commands

### init

Initialize `.flow/` directory.

```bash
flowctl init [--json]
```

Idempotent. Creates the canonical 1.0 layout on a fresh repo (`.flow/specs/`, `.flow/tasks/`, `.flow/memory/`, `meta.json` with `schema_version: 3` + `next_spec: 1`, `config.json`). Skips anything that already exists; upgrades existing `config.json` by merging in any new default keys. Re-running on a 1.0 repo reports "already up to date".

**Auto-managed `.flow/.gitignore`** (since 1.0.0). Both `flowctl init` and `flowctl migrate-rename` write `.flow/.gitignore` with the auto-managed pattern set so users don't accidentally commit migration transients or per-run state on `git add -A`:

```gitignore
# Auto-managed by flowctl — do not edit above this marker.
.checkpoint-*.json
receipts/
tmp/
.backup-pre-1.0/
.banner-acknowledged
.migrating
.migration-manifest
# End of auto-managed block. User patterns below this line are preserved.
```

Idempotent: the auto-block is only written if absent. User patterns added below the footer survive subsequent `flowctl init` / `flowctl migrate-rename` runs. Existing user `.flow/.gitignore` files are migrated in-place by prepending the auto-block. **`.flow/.flow_version` is intentionally NOT in the block** — it's the post-migration schema sentinel and should be tracked per repo so multiple devs share the same migrated state (semantics like `Cargo.lock`).

### detect

Check if `.flow/` exists and is valid.

```bash
flowctl detect [--json]
```

Output:
```json
{"success": true, "exists": true, "valid": true, "path": "/repo/.flow"}
```

### spec create

Create new spec.

```bash
flowctl spec create --title "Spec title" [--branch "fn-1-spec-title"] [--json]

# Tracker-first: key the spec by its tracker identifier (wor-17-slug) instead of fn-NN
flowctl spec create --title "Spec title" --tracker-first --tracker-identifier WOR-17 [--json]
```

Output:
```json
{"success": true, "id": "fn-1-spec-title", "title": "Spec title", "spec_path": ".flow/specs/fn-1-spec-title.md"}
```

`--tracker-first` (requires `--tracker-identifier WOR-17`) keys the spec by the tracker key — canonical id `wor-17-slug`, tasks `wor-17-slug.M`, branch `wor-17-slug`; bare `wor-17` / `wor-17.M` resolve as aliases. Used by the `/flow-next:tracker-sync` "grab issue X and spec it" flow. See [`tracker-sync.md`](tracker-sync.md) for the hybrid id model. No fresh `fn-NN` is allocated; ids never rename.

### spec set-plan

Overwrite spec markdown from file.

```bash
flowctl spec set-plan fn-1 --file plan.md [--json]
```

See [`plugins/flow-next/templates/spec.md`](../templates/spec.md) for the canonical section structure (Goal & Context, Architecture & Data Models, API Contracts, Edge Cases & Constraints, Acceptance Criteria, Boundaries, Decision Context) and scope-owner annotations.

### spec set-plan-review-status

Set plan review status and timestamp.

```bash
flowctl spec set-plan-review-status fn-1 --status ship|needs_work|unknown [--json]
```

### spec set-completion-review-status

Set completion review status and timestamp.

```bash
flowctl spec set-completion-review-status fn-1 --status ship|needs_work|unknown [--json]
```

### spec reset-review-rounds

Reset the deterministic review-round counter for a spec (fn-90) — the **re-plan** reset path. Zeroes the spec-scoped `plan_review_rounds` (which plan AND completion reviews share); pass `--impl` to also zero every per-task `impl_review_rounds[<task-id>]`. Use this after an explicit re-plan to re-open the review cap; a `SHIP` verdict resets automatically, so this is only for the deliberate re-plan case. See [codex impl-review § Deterministic review cap](#codex-impl-review) for the full cap/reset semantics.

```bash
flowctl spec reset-review-rounds fn-1 [--impl] [--json]
```

### review-rounds increment / reset

Prose-facing surface of the deterministic review-round cap (fn-90) for the **rp backend**, whose reviews are dispatched from skill prose via `flowctl rp chat-send` rather than through a `flowctl <backend> *-review` handler. `increment` enforces + increments the same cumulative counter the codex/copilot/cursor handlers wire internally — call it before EVERY rp review dispatch (including the first); at `${MAX_REVIEW_ITERATIONS:-4}` it refuses with an `ESCALATE:` marker + exit `4` (not retryable). `reset` zeroes the counter on a `SHIP` verdict (convergence); for a re-plan use `spec reset-review-rounds` instead. Completion reviews pass `--kind plan` (shared spec-scoped counter); impl reviews require `--task` (per-task counter).

```bash
flowctl review-rounds increment fn-1 --kind plan|impl [--task fn-1.2] [--json]
flowctl review-rounds reset fn-1 --kind plan|impl [--task fn-1.2] [--json]
```

### spec set-branch

Set spec branch_name.

```bash
flowctl spec set-branch fn-1 --branch "fn-1-spec" [--json]
```

### spec set-title

Rename a spec by setting a new title (slug + filenames update; the JSON sidecar's `id` field follows).

```bash
flowctl spec set-title fn-1 --title "New title" [--json]
```

### spec close

Close spec (requires all tasks done).

```bash
flowctl spec close fn-1 [--json]
```

### spec ready / spec unready

Mark / clear the spec's human-owned readiness gate (1.12.0+). Readiness is orthogonal to `status` — a ready spec stays `open` through planning and work, and `done` specs may be toggled.

```bash
flowctl spec ready fn-1 [--json]
flowctl spec unready fn-1 [--json]
```

Output:
```json
{"id": "fn-1", "ready": true, "changed": true, "message": "Spec fn-1 marked ready"}
```

Both verbs are **idempotent no-ops** when the flag already matches (no write, no `updated_at` bump, `"changed": false`) — which is what lets unconditional callers like `capture --rewrite`'s readiness reset run without turning every spec into a readiness adopter. The on-disk flag is **lazy**: the sidecar carries `ready` only after a toggle actually changes state (absent reads `false`; `spec create` never writes it). Task ids (`fn-1.2`) are rejected — readiness is spec-level only. When `tracker.readyState` is configured, the tracker is authoritative: a local `spec ready` is overwritten by the next pull-side sync (see [`tracker-sync.md`](tracker-sync.md)).

### spec add-dep / spec rm-dep

Manage spec-level dependencies (one spec depends on another).

```bash
flowctl spec add-dep fn-2 fn-1 [--json]   # fn-2 now depends on fn-1
flowctl spec rm-dep  fn-2 fn-1 [--json]   # remove the dependency
```

### spec set-backend

Set default backend specs for impl/review/sync workers. Used by orchestration products (e.g., flow-swarm).

```bash
flowctl spec set-backend fn-1 --impl codex:gpt-5.4 [--json]
flowctl spec set-backend fn-1 --impl codex:gpt-5.4-high --review claude:opus [--json]
flowctl spec set-backend fn-1 --impl "" [--json]  # Clear impl (inherit from config)
```

Options:
- `--impl SPEC`: Default impl backend (e.g., `codex:gpt-5.4-high`, `claude:opus`)
- `--review SPEC`: Default review backend (e.g., `claude:opus`, `agent:opus-4.5-thinking`)
- `--sync SPEC`: Default sync backend (e.g., `claude:haiku`, `gemini:gemini-2.5-flash`)

Format: `backend:model` where backend is a CLI name and model is backend-specific.

### spec export-cognitive-aid

Aggregate spec markdown, tasks, memory, glossary diff, strategy alignment, diff stats, and review receipts into one structured payload (consumed by `/flow-next:make-pr`).

```bash
flowctl spec export-cognitive-aid fn-1 --base origin/main [--section spec|tasks|memory|glossary|strategy|diff|reviews] [--json]
```

### task create

Create task under spec.

```bash
flowctl task create --spec fn-1 --title "Task title" [--deps fn-1.2,fn-1.3] [--acceptance-file accept.md] [--priority 10] [--json]
```

Section content is normalized on write (here and in `task set-description` / `set-acceptance` / `set-spec`): a leading title-like H2 (e.g. `## Acceptance Criteria (…)`) is stripped, and any remaining `## ` headings in the content are demoted to `### ` (fenced code blocks untouched) so they never become section boundaries.

Output:
```json
{"success": true, "id": "fn-1.4", "spec": "fn-1", "title": "Task title", "depends_on": ["fn-1.2", "fn-1.3"]}
```

### task set-description

Set task description section.

```bash
flowctl task set-description fn-1.2 --file desc.md [--json]
```

### task set-acceptance

Set task acceptance section.

```bash
flowctl task set-acceptance fn-1.2 --file accept.md [--json]
```

### task set-spec

Set description and acceptance in one call (fewer writes).

```bash
flowctl task set-spec fn-1.2 --description desc.md --acceptance accept.md [--json]
```

Both `--description` and `--acceptance` are optional; supply one or both.

### task reset

Reset task to `todo` status, clearing assignee and completion data.

```bash
flowctl task reset fn-1.2 [--cascade] [--json]
```

Use `--cascade` to also reset dependent tasks within the same spec.

### task set-backend

Set backend specs for impl/review/sync workers. Used by orchestration products (e.g., flow-swarm).

```bash
flowctl task set-backend fn-1.1 --impl codex:gpt-5.4-high [--json]
flowctl task set-backend fn-1.1 --impl codex:gpt-5.4-high --review claude:opus [--json]
flowctl task set-backend fn-1.1 --impl "" [--json]  # Clear impl (inherit from spec/config)
```

Options:
- `--impl SPEC`: Impl backend (e.g., `codex:gpt-5.4-high`, `claude:opus`)
- `--review SPEC`: Review backend (e.g., `claude:opus`, `agent:opus-4.5-thinking`)
- `--sync SPEC`: Sync backend (e.g., `claude:haiku`, `gemini:gemini-2.5-flash`)

Format: `backend:model` where backend is a CLI name and model is backend-specific.

### task show-backend

Show effective backend specs for a task. Reports task-level and spec-level specs only (config-level resolution happens in flow-swarm).

```bash
flowctl task show-backend fn-1.1 [--json]
```

Output (text):
```
impl: codex:gpt-5.4-high (task)
review: claude:opus (spec)
sync: null
```

Output (json):
```json
{
  "success": true,
  "id": "fn-1.1",
  "spec": "fn-1",
  "impl": {"spec": "codex:gpt-5.4-high", "source": "task"},
  "review": {"spec": "claude:opus", "source": "spec"},
  "sync": {"spec": null, "source": null}
}
```

### dep add

Add single dependency to task.

```bash
flowctl dep add fn-1.3 fn-1.2 [--json]
```

Dependencies must be within same spec.

### task set-deps

Set multiple dependencies for a task (convenience command).

```bash
flowctl task set-deps fn-1.3 --deps fn-1.1,fn-1.2 [--json]
```

Equivalent to multiple `dep add` calls. Dependencies must be within same spec.

### show

Show spec or task details.

```bash
flowctl show fn-1 [--json]     # Spec with tasks
flowctl show fn-1.2 [--json]   # Task only
```

Spec output includes `tasks` array with id/title/status/priority/depends_on, plus an explicit `"ready": <bool>` (1.12.0+ — absent on-disk key reads `false`, so consumers always see a stable boolean).

### specs

List all specs.

```bash
flowctl specs [--json]
```

Output:
```json
{"success": true, "specs": [{"id": "fn-1", "title": "...", "status": "open", "ready": false, "tasks": 5, "done": 2}], "count": 1}
```

Human-readable output shows progress: `[open] fn-1: Title (2/5 tasks done)`. Ready specs carry a badge — `[open] [ready] fn-1: …` — shown **only** when the flag is set (no draft-noise for non-adopters).

### tasks

List tasks, optionally filtered.

```bash
flowctl tasks [--json]                    # All tasks
flowctl tasks --spec fn-1 [--json]        # Tasks for specific spec
flowctl tasks --status todo [--json]      # Filter by status
flowctl tasks --spec fn-1 --status done   # Combine filters
```

Status options: `todo`, `in_progress`, `blocked`, `done`

Output:
```json
{"success": true, "tasks": [{"id": "fn-1.1", "spec": "fn-1", "title": "...", "status": "todo", "priority": null, "depends_on": []}], "count": 1}
```

### list

List all specs with their tasks grouped together.

```bash
flowctl list [--json]
```

Human-readable output:
```
Flow Status: 2 specs, 5 tasks (2 done)

[open] fn-1: Add auth system (1/3 done)
    [done] fn-1.1: Create user model
    [in_progress] fn-1.2: Add login endpoint
    [todo] fn-1.3: Add logout endpoint

[open] fn-2: Add caching (1/2 done)
    [done] fn-2.1: Setup Redis
    [todo] fn-2.2: Cache API responses
```

JSON output:
```json
{"success": true, "specs": [...], "tasks": [...], "spec_count": 2, "task_count": 5}
```

Each `specs[]` entry carries the explicit `"ready"` boolean; the human-readable spec lines show the same `[ready]` badge as `flowctl specs` (only on ready specs).

### cat

Print spec markdown (no JSON mode).

```bash
flowctl cat fn-1      # Spec markdown
flowctl cat fn-1.2    # Task spec
```

### anchor

Single-call worker anchor bundle — the `/flow-next:work` worker's entire Phase-1 re-anchor in one deterministic, pure read.

```bash
flowctl anchor fn-1.2          # Worker-facing markdown render (default)
flowctl anchor fn-1.2 --md     # Explicit markdown render
flowctl anchor fn-1.2 --json   # Machine form (sections + dependencies)
```

Sections come in fixed order, each the **verbatim captured stdout of the same production function the standalone command dispatches to** (no re-parsing, no filtering, no truncation): `show <task> --json`, `cat <task>`, `show <spec> --json`, `cat <spec>`, `git status`, `git log -5 --oneline`, `git rev-parse --abbrev-ref HEAD`, `config get memory.enabled --json`, `glossary list --json`, and `memory list --json` (captured only when `memory.enabled` resolves true — mirroring the worker's own conditional read; otherwise the section carries a skip `note`). A final dependencies section lists each `depends_on` task's id, title, status, and `## Done summary` (fence-aware section read), in the task file's recorded order. The byte-for-byte superset test (`tests/test_anchor_bundle.py`) locks every section against the real CLI wire-form output.

`--json` shape:

```json
{
  "task": "fn-1.2",
  "spec": "fn-1",
  "sections": [
    {"name": "task_show", "command": "flowctl show fn-1.2 --json", "output": "…", "error": null}
  ],
  "dependencies": [
    {"id": "fn-1.1", "title": "…", "status": "done", "done_summary": "…"}
  ]
}
```

- **Fail-open, never a crash:** a broken section is reported inline — markdown renders `(section unavailable: <reason> — run `` `<command>` `` directly)`, JSON carries the `error` field — so the caller falls back to running that one read directly. Same for an unloadable dependency (`error: "task not loadable"`).
- **Floor, not a ceiling:** the bundle replaces the worker's discrete Phase-1 reads but caps nothing — memory keyword-search (`flowctl memory search`) and every further read stay available.
- Pure read (no state mutation, no `updated_at` bumps); markdown banner lines (`===== [k/N] …`) cannot collide with embedded content — spec/task bodies never start lines with `===== [`.
- `--json` and `--md` are mutually exclusive; invalid/unresolvable task id or missing `.flow/` → standard error exit (JSON envelope under `--json`). Short task ids resolve via the usual resolution rules.

### ready

List tasks ready to start, in progress, and blocked.

```bash
flowctl ready --spec fn-1 [--json]
```

Output:
```json
{
  "success": true,
  "spec": "fn-1",
  "actor": "user@example.com",
  "ready": [{"id": "fn-1.3", "title": "...", "depends_on": []}],
  "in_progress": [{"id": "fn-1.1", "title": "...", "assignee": "user@example.com"}],
  "blocked": [{"id": "fn-1.4", "title": "...", "blocked_by": ["fn-1.2"]}]
}
```

Spec-level deps gate the whole spec (same rule as `next`): when the spec's `depends_on_epics` include a spec that is missing or not `done`, `ready` returns empty `ready`/`in_progress`/`blocked` lists plus `blocked_by_specs` (legacy alias `epic_blocked_by` co-emitted through 1.x):

```json
{
  "success": true,
  "spec": "fn-2",
  "actor": "user@example.com",
  "ready": [],
  "in_progress": [],
  "blocked": [],
  "blocked_by_specs": ["fn-1"],
  "epic_blocked_by": ["fn-1"]
}
```

**`ready --all`** (fn-68, backlog mode) — a **spec-level** backlog-wide eligibility scan (ignores `--spec`), the deterministic substrate `/flow-next:pilot` backlog mode (`pilot.autonomy=backlog`) consumes:

```bash
flowctl ready --all [--json]
```

Output:
```json
{
  "success": true,
  "specs": [
    {"id": "fn-12-add-auth", "ready": true,  "readySignal": "local", "blockedBy": [],            "hasSpec": true},
    {"id": "fn-13-rate-limit", "ready": false, "readySignal": "none",  "blockedBy": ["fn-12-add-auth"], "hasSpec": true}
  ]
}
```

Returns **deterministic eligibility facts only** for every open flow spec — `ready` (the **local** fn-58 `ready` boolean, exactly what flowctl sees on disk), `readySignal ∈ {local, none}` (whether that local flag is set — flowctl stores no readiness *provenance*, so it cannot attribute a tracker-projected ready; the skill annotates tracker-origin readiness when it unions tracker items), `blockedBy` (unsatisfied dep spec ids), and `hasSpec` (whether a spec file exists). It **never** computes a judgment `triageClass` / completeness score — *workable / thin / ambiguous / needs-spec* is the host agent's agentic read in the `triage` stage, never a flowctl field (the agentic/deterministic line). flowctl has **no tracker transport** and must not grow one: the **tracker-side** open items (incl. tickets with no flow spec) are unioned in by the skill from tracker-sync's adapter, not by `ready --all`. After a backlog tick's tracker pull projects `tracker.readyState` onto the local flag, a tracker-promoted spec simply reads `ready: true, readySignal: local` like any other.

### pilot-log

The per-tick **decision log** `/flow-next:pilot` backlog mode (fn-68) writes — the factory-metrics substrate (and the later self-improvement-synthesis substrate). Receipt-shaped rows under `.flow/pilot-runs/` (a sync-runs-style dir, auto-gitignored) — deliberately **NOT** any `receipts/` path the ralph-guard validates, so a pilot-log row never trips a Ralph receipt gate.

```bash
# Append one row (called by the skill at each backlog terminal)
flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> \
                         [--stage <stage|->] [--cost-tokens <n>] [--json]

# List all rows
flowctl pilot-log summary [--json]
```

- `--id` — an **opaque** id: the spec id when spec-backed, else a bare tracker key (safe-filename-normalized).
- `--action` — the **frozen** enum `triaged | advanced | asked | blocked | needs-human`, aligned to the backlog verdict grammar.
- `--stage` — the pipeline stage label (`-` or omitted = none).
- `--cost-tokens` — **host-reported** token cost (optional; omitted/null when the host can't report it — flowctl only stores the row, it never *measures* cost).

`summary` output:
```json
{"success": true, "rows": [{"tick": 1, "id": "fn-12-add-auth", "action": "advanced", "stage": "work", "costTokens": 84213}], "count": 1}
```

`tick` is a per-id monotonic counter assigned by `append` (flock-guarded). The rows power the efficiency readout — % of items moved with no question / one async answer / parked, and cost per change.

### next

Select next plan/work unit.

```bash
flowctl next [--specs-file specs.json] [--require-plan-review] [--require-completion-review] [--json]
```

Output:
```json
{"status":"plan|work|completion_review|none","spec":"fn-12","task":"fn-12.3","reason":"needs_plan_review|needs_completion_review|resume_in_progress|ready_task|none|blocked_by_spec_deps","blocked_specs":{"fn-12":["fn-3"]}}
```

The `--require-completion-review` flag gates spec closure on completion review. When all tasks are done but `completion_review_status != ship`, returns `status: completion_review`.

### start

Start task (set status=in_progress). Sets assignee to current actor.

```bash
flowctl start fn-1.2 [--force] [--note "..."] [--json]
```

Validates:
- Status is `todo` (or `in_progress` if resuming own task)
- Status is not `blocked` unless `--force`
- All dependencies are `done`
- Not claimed by another actor

Use `--force` to skip checks and take over from another actor.
Use `--note` to add a claim note (auto-set on takeover).

### done

Complete task with summary and evidence. Requires `in_progress` status.

```bash
flowctl done fn-1.2 --summary-file summary.md --evidence-json evidence.json [--force] [--json]
```

Use `--force` to skip status check.

Evidence JSON format:
```json
{"commits": [], "tests": ["test_foo"], "prs": ["#42"]}
```

### block

Block a task and record a reason in the task spec.

```bash
flowctl block fn-1.2 --reason-file reason.md [--json]
```

### validate

Validate spec structure (specs, deps, cycles).

```bash
flowctl validate --spec fn-1 [--json]
flowctl validate --all [--json]
```

Single spec output:
```json
{"success": false, "spec": "fn-1", "valid": false, "errors": ["..."], "warnings": [], "task_count": 5}
```

All specs output:
```json
{
  "success": false,
  "valid": false,
  "specs": [{"spec": "fn-1", "valid": true, ...}],
  "total_specs": 2,
  "total_tasks": 10,
  "total_errors": 1
}
```

Checks:
- Spec/task markdown exists
- Task specs have required headings
- Task statuses are valid (`todo`, `in_progress`, `blocked`, `done`)
- Dependencies exist and are within same spec
- No dependency cycles
- Done status consistency

Exits with code 1 if validation fails (for CI use).

### config

Manage project configuration stored in `.flow/config.json`.

```bash
# Get a config value
flowctl config get memory.enabled [--json]
flowctl config get review.backend [--json]

# Set a config value
flowctl config set memory.enabled true [--json]
flowctl config set review.backend codex [--json]  # rp, codex, copilot, cursor, or none

# Toggle boolean config
flowctl config toggle memory.enabled [--json]
```

**Available settings:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `memory.enabled` | bool | `false` | Enable memory system |
| `planSync.enabled` | bool | `false` | Enable plan-sync after task completion |
| `planSync.crossSpec` | bool | `false` | Cross-spec plan-sync — scan other open specs for stale references after each task (opt-in; increases sync time)* |
| `scouts.github` | bool | `false` | Enable github-scout during planning (requires gh CLI) |
| `review.backend` | string | `null` | Default review backend (`rp`, `codex`, `copilot`, `cursor`, `none`), or spec form (`codex:gpt-5.4:high`, `cursor:gpt-5.5-high` — cursor folds effort into the model, no `:effort` rung). If unset, review commands require `--review` or `FLOW_REVIEW_BACKEND`. |
| `tracker.enabled` | bool | `false` | Enable the tracker-sync bridge (see [`sync`](#sync)). The bridge is active iff raw `tracker.enabled == true` OR raw `tracker.type ∈ {linear, github, gitlab, jira}`. |
| `tracker.type` | string | `null` | Tracker backend: `linear`, `github`, `gitlab`, or `jira`. |
| `tracker.provenance` | string | `null` | Free-form provenance written by the discovery ceremony on confirmation (who/when/signals). |
| `tracker.perEvent.<event>` | string | `off` | Per-lifecycle-event sync op. Events: `capture`, `interview`, `plan`, `work.firstClaim`, `work.done`, `makePr`, `resolvePr`, `completionReview`. Leaf values: `off | pull | push | reconcile | comment`. **Schema default `off`** — so a bare `enabled=true` set without the ceremony fires no lifecycle-event sync (accidental-enable guard; two paths are unconditional whenever the bridge is active — make-pr's PR↔issue link + `In Review` push, and `land.merged`'s `Done`-on-merge — see [`tracker-sync.md`](tracker-sync.md)). But the `/flow-next:tracker-sync` discovery ceremony **activates all events by default (opt-out)** when you hook up the bridge; you turn any off with `config set tracker.perEvent.<event> off`. `completionReview` is seeded `comment` (verdict + R-ID coverage; **never terminal `Done`** — fn-66). |
| `tracker.perEvent.qa` | string | `off` | **`/flow-next:qa` verdict post (fn-53, R9).** Posts the live-app QA ship verdict (`type: qa_verdict`) as a tracker comment when set non-`off` AND the bridge is active. Leaf values: **`off | comment` only** — `comment` is the only sensible verb for a verdict; `push`/`pull`/`reconcile` operate on the issue body/status and don't apply, so the QA skill treats any non-`off` value as `comment`. **Default `off`, and — unlike the other events — NOT switched on by the discovery ceremony's opt-out default-on set**: a QA verdict post is QA-specific opt-in, enabled explicitly with `config set tracker.perEvent.qa comment`. The post is best-effort and never blocks the verdict. |
| `tracker.perEvent.land.merged` | string | `off` | **`/flow-next:land` post-merge touchpoint (fn-60, 1.14.0+; fn-66 made it the sole `Done` driver).** After land merges a PR and closes its spec, dispatches tracker-sync (`operation: push <spec-id>`, event tag `land.merged`) — status flips to the **merge-confirmed** terminal state (`done`/`verified`, gated on the GitHub `MERGED` probe) and the merge/release verdict comment is posted. **fn-66: active-by-default whenever the bridge is active** — a real merge is the ONLY event that legitimately projects terminal `Done`, so this touchpoint rides the bridge-active predicate alone (NOT gated behind this leaf, which then only tunes the optional verdict comment). The schema default stays `off` (accidental-enable guard); the land skill fires it on bridge-active regardless. Best-effort — a tracker failure never blocks land's tail or changes the PR's verdict. |
| `tracker.perTracker.teamId` / `projectId` / `labelMap` / `priorityMap` | mixed | `null` / `{}` | Per-tracker linkage hints (Linear team/project ids; label/priority maps). |
| `tracker.perTracker.repo` / `project` / `host` | string | `null` | Tracker-specific repo/project linkage. **GitHub** writes `repo` (`owner/name`). **GitLab** writes `project` (the group/sub-group/project path, e.g. `group/subgroup/project`; URL-encoded once for the API, never double-encoded) and, for self-managed hosts, `host`. Written by the `/flow-next:tracker-sync` discovery ceremony on confirmation. |
| `tracker.perTracker.baseUrl` / `projectKey` / `authScheme` / `apiVersion` / `statusMap` / `sslVerify` | mixed | `null` | **Jira linkage (fn-70).** `baseUrl` = the site base (`https://acme.atlassian.net` Cloud / `https://jira.acme.com` DC/Server; `JIRA_BASE_URL` env overrides). `projectKey` = the project key (the `listOpenIssues` JQL scope; validated `^[A-Z][A-Z0-9]+$`). `authScheme` = `cloud-basic` (Cloud HTTP-basic `email:API_TOKEN`) \| `bearer-pat` (DC/Server `Authorization: Bearer <PAT>`) — runtime reads only this, never re-probes the env. `apiVersion` = `3` (Cloud `/rest/api/3`, ADF) \| `2` (DC/Server `/rest/api/2`). `statusMap` = normalized status → Jira transition target (`{"id":…}` preferred over `{"name":…}`; applied via the **transitions API**, not a direct status set — `tracker.readyState` is used RAW, NOT through this map). `sslVerify` = `false` opts out of TLS verification for a self-hosted cert (`JIRA_SSL_VERIFY=false` env override; default `true`). Written by the discovery ceremony on confirmation (references/jira.md). |
| `tracker.staleAfterHours` | int | `24` | Staleness threshold (hours) consumed by `sync list-stale`. |
| `tracker.conflictTiebreak` | string | `always-ask` | Status who-wins tiebreak: `flow-wins | tracker-wins | always-ask`. In Ralph mode `always-ask` resolves to *queue*, not prompt. |
| `tracker.readyState` | string | `null` | **Readiness projection (fn-58, 1.12.0+).** The tracker workflow state that means "ready for work" — a Linear workflow-state **name** or a **Jira status name** (both matched case-insensitive/trimmed against `status.raw`; names, not `state.type` — a custom "Ready" state is typically `type=unstarted`, indistinguishable from Todo by type alone; the Jira name is used RAW in the promoted-lane JQL, validated to exist at ceremony time), or a GitHub / GitLab **label** (pre-created at ceremony time; label present ⇒ ready, absent ⇒ not ready — a normal state, never an error). Set by the `/flow-next:tracker-sync` discovery ceremony (optional, skippable). When set, every pull-side sync projects the state onto the local spec `ready` flag — **one-way, tracker → local; the tracker is authoritative** (a local `spec ready` is overwritten on the next sync, and capture/interview's mark-ready prompt is gated off). A single scalar at the tracker top level (sibling of `conflictTiebreak`), not under `perTracker`. `null` = projection off (readiness gate dormant); clear with `flowctl config set tracker.readyState null` (the literal `null` token is stored as JSON null, not the string). |
| `work.delegate` | `codex \| false` | `false` | Opt-in `/flow-next:work` implementation-delegation to a local `codex exec`. **Set the value to the string `codex` to activate** (`flowctl config set work.delegate codex`) — **any other value, including bool `true`, is OFF**; the activation predicate is `value == "codex"`. **OFF by default** — with it off the work flow is byte-identical to today. Resolution: arg token `delegate:codex` / `delegate:local` > this config > hard default OFF. The generic fuzzy "use codex" is NOT a delegation trigger (it stays mapped to the review backend). See [`codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md). |
| `work.delegateModel` | string | `gpt-5.5` | Model passed to `codex exec` for delegated implementation. |
| `work.delegateEffort` | string | `medium` | Reasoning-effort floor (`none | low | medium | high | xhigh`). The per-batch risk escalation floors against this; gpt-5.5 supports `none`, not `minimal`. |
| `work.delegateSandbox` | string | `yolo` | Codex sandbox mode (`yolo | full-auto`). Persisted by the one-time consent gate. `yolo` has a wider blast radius — the gate surfaces this before first use. |
| `work.delegateConsent` | bool | `false` | One-time-consent flag, written by the host consent gate after the user opts in. Headless/Ralph requires this pre-set to `true` (no live prompt path). |
| `work.delegateDecision` | string | `auto` | Per-task delegation decision (`auto | ask`). `auto` delegates every eligible task; `ask` prompts per-task in interactive mode (treated as `auto` in headless only when `delegateConsent=true`). |
| `land.release` | bool | `true` | **`/flow-next:land` (fn-60, 1.14.0+).** Run the post-merge release-follow step (the project's own release docs; also no-ops when no release docs are discovered). `false` = stop at merge. |
| `land.patienceMinutes` | int | `30` | Land's reviewer patience window, anchored to the LAST push (a land-authored CI-fix push restarts it). |
| `land.reviewSignal` | string | `silence` | Land's merge review-signal: `silence` (automated review present + zero unresolved threads + window elapsed), `approve` (formal `reviewDecision == APPROVED`), or a GitHub login (that reviewer's latest review must be clean). |
| `land.automatedReviewers` | string | `""` | CSV allowlist of reviewer logins land counts as automated, supplementing the `[bot]`-suffix rule. |
| `land.reviewTrigger` | string | `""` | One-shot comment land posts to summon a reviewer bot on a draft PR with zero automated reviews (e.g. `"@codex review"` — bots don't auto-review drafts). Empty = never post. |
| `land.cleanReviewCommentPattern` | string | `(Didn'?t find any( major)? issues\|No( major)? issues found).*Reviewed commit` | **`/flow-next:land` clean-review comment signal (fn-65, 2.1.1+).** Under the default `silence` review signal, a review bot that posts a no-findings **issue comment** instead of a formal APPROVE (e.g. Codex's "Didn't find any major issues. Reviewed commit: `<sha>`") also satisfies the gate. Land scans `issues/<n>/comments` for an automated-reviewer (`[bot]`-suffix or `land.automatedReviewers`) comment matching this ERE that names the **current head SHA**, and only ever *adds* this evidence (CI, unresolved-thread, and window gates are unchanged; a stale-SHA or non-automated comment is ignored). The default is the structured built-in ERE shown here — it requires BOTH the clean phrase AND the `Reviewed commit` marker, so a bare "no issues" mention never satisfies the gate. `null`/missing (an unseeded older repo) falls back to this built-in default; **set to an empty string `""` to disable the comment scan** (pure reviews-API behavior — the only real off-switch). |
| `land.ciFixBudget` | int | `3` | CI-fix attempts per PR before land durably labels it `flow-next:needs-human` and skips it on later ticks. |
| `artifacts.html.enabled` | bool | `false` | **Optional HTML artifact mode (fn-62, 2.0.0+).** Enable with `flowctl config set artifacts.html.enabled true`: participating skills (capture, plan, make-pr) load the shared render-lens reference and emit self-contained HTML artifacts at the fixed paths `.flow/artifacts/<spec-id>/spec.html` / `pr.html` (regenerable lenses, never timestamped — markdown stays the sole source of truth and artifacts are never parsed back as state). **OFF by default** — with it off, no reference file loads, no artifacts are written, no Lavish session opens; behavior is byte-identical to markdown-only. flowctl only stores the knob; generation is skill-side. |
| `pipeline.qa` | `off \| on` | `off` | **Optional QA pipeline stage (fn-72, 2.2.0+).** Enable with `flowctl config set pipeline.qa on` — this is a **string-enum** knob (`off \| on`), **NOT a bool**; the activating value is the literal string `on` and **any other value, including bool `true`, is OFF** (the `/flow-next:pilot` gate read is the canonical 3-clause guard `value != "off" && value != "null"`). With it `on`, pilot inserts a `qa` stage at the **all-tasks-done** juncture (before make-pr): one live `/flow-next:qa` pass over the complete build, surfacing its `qa_outcome` into the draft PR. **OFF by default** — with it off, pilot's stage set and behavior are byte-for-byte unchanged. Augments (never replaces) CI/staging/manual QA; `BLOCKED` (no local app) / `NA` (no UI) advance, `NEEDS_WORK` still advances to the draft PR + surfaces findings (it never hard-blocks the loop). flowctl only stores the knob; the QA stage is host-agent skill wiring (no new subcommand/engine). |
| `pilot.autonomy` | `ready \| backlog` | `ready` | **Pilot backlog mode (fn-68).** A **scalar string-enum** (`ready \| backlog`), **NOT a bool**. `ready` (default) = current behavior: pilot selects only already-ready specs. Set to the literal `backlog` (`flowctl config set pilot.autonomy backlog`, or per-run `--backlog` / `--auto`) to enable **backlog mode** — pilot widens selection to the whole open backlog (flow specs via `ready --all` + tracker issues unioned by the skill), triages the top dep-ordered item, and either advances it or surfaces an async question (`ASKED`). **Only the literal `backlog` activates** — any other value (bool `true`, a typo, `null`) leaves pilot byte-for-byte in `ready` mode, and `references/backlog-mode.md` is never read. Backlog mode **never authors a spec, never sets `ready`, never merges**; readiness stays the human's explicit signal. flowctl only stores the knob; the SELECT/TRIAGE/ASK workflow is host-agent skill wiring. |
| `pilot.gateClasses` | string[] | `[]` | **Backlog-mode force-gate (fn-68).** An optional list of class names (e.g. `["risky", "prod-config"]`) that, in backlog mode, force **surfacing before action** — a matching item is parked with a question (`ASKED`) instead of advanced full-auto, even when otherwise workable. A **sibling** key, deliberately NOT `pilot.autonomy.gate` (a scalar and an object cannot share the `pilot.autonomy` dot-path). Empty `[]` (default) = full-auto for every workable item. |

\* The pre-1.1.3 legacy alias `planSync.crossEpic` was **removed in 2.0.0** (it was readable through 1.x with a stderr deprecation warning). `flowctl` no longer reads or writes it — a leftover `crossEpic` key in `.flow/config.json` is inert. If you relied on it, set the canonical key once: `flowctl config set planSync.crossSpec true`.

Priority: `--review=...` argument > `FLOW_REVIEW_BACKEND` env > `.flow/config.json` > error.

No auto-detect. Run `/flow-next:setup` (or `flowctl config set review.backend ...`) to configure.

### review-backend

Resolve the active review backend spec (used by skills + Ralph). With an optional **task/spec id**, a per-task `review:` / per-spec `default_review` override wins **above env/config** (the id is canonicalized first, so short/tracker handles like `fn-74.1` / `fn-74` resolve to the slugged id). Precedence: per-task / per-epic override > `FLOW_REVIEW_BACKEND` > `.flow/config.json` `review.backend` > backend-specific env > registry default. Without an id it reads env/config only. The review skills pass the review-target id so a task's own backend override actually routes.

```bash
flowctl review-backend [<task-or-spec-id>] [--json]
```

Text output prints the bare backend name (e.g. `codex`) for skill grep back-compat. JSON output (`source` ∈ `task` / `epic` / `env` / `config` / `hint`):

```json
{"backend": "codex", "spec": "codex:gpt-5.4:high", "model": "gpt-5.4", "effort": "high", "source": "env"}
```

Spec grammar: `backend[:model[:effort]]`. Examples: `rp`, `codex`, `codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5:high`, `cursor:gpt-5.5-high` (cursor folds effort into the model name — no `:effort` rung). RP is bare only (model set via window config); `none` is an explicit opt-out.

#### Model resolution (strongest-available, never-fail — fn-76)

When a review runs **without an explicit model** (unconfigured `codex` / `copilot` / `cursor`), flow-next resolves the *strongest model the account can actually run* instead of a fixed hardcoded default. The mechanism is **optimistic-first**, so the happy path costs nothing:

- **Ranking.** Each backend's model set is a curated **quality ranking** (strongest first); the ranking's top entry IS the encoded default (`codex` → `gpt-5.6-sol`, `copilot` → `gpt-5.5`, `cursor` → `gpt-5.6-sol-high`). The ranking is a *preference*, never a parse-time gate — an **unknown explicit model warns and is accepted** (the CLI stays the availability authority); the reasoning-effort axis stays strict.
- **Happy path (zero overhead).** The top model dispatches directly — no probe, no list call, no extra subprocess. On a current CLI where the default just works, the argv is byte-identical to a hardcoded default.
- **Fallback ladder (failure only).** If — and only if — that dispatch fails with the backend's **distinctive model-unavailable signature** (codex: *"requires a newer version of Codex"* / model-not-found; copilot: *`… from --model flag is not available`*; cursor: *`Cannot use this model: …`*), flow-next resolves a fallback: **cursor** consults `cursor-agent --list-models` and dispatches the best `list ∩ ranking` entry; **codex/copilot** step down the ranking (max 2 steps). The terminal **floor** never fails — codex omits `--model`, copilot/cursor use `--model auto` (and the reasoning-effort flag is dropped). Any *other* failure (auth / network / sandbox / timeout) propagates unchanged — the ladder never masks a real error. A ladder retry is the **same review round** (it does not consume an extra review-cap iteration).
- **Cache.** The resolved fallback is memoized per **`(backend, CLI version)`** in `.flow/.cache/model-resolution.json` (atomic write, gitignored). A CLI upgrade changes the key → natural re-resolution; a corrupt/missing cache is a cold start, never an error; explicit models bypass the cache entirely. So the one failed round-trip after a ranking-top bump is paid at most once per CLI version.
- **Hygiene.** A downgrade or floor emits **one** stderr warning naming what was tried and what ran; the receipt records the model **actually used** (else `"auto"` / `"default"`), never a fabricated name.

Explicit pins anywhere in the precedence chain (`--spec` > per-task/per-spec `review` > env > config) are byte-identical to before — no probing, no cache, no retry-downgrade; an explicit unavailable model errors clearly.

### memory

Manage persistent learnings under `.flow/memory/`.

**Schema (v0.33.0+):** Categorized YAML — one entry per file under `bug/<category>/*.md` or `knowledge/<category>/*.md`. Frontmatter: `title`, `date`, `track`, `category`, `module`, `tags`, plus track-specific fields (`problem_type` / `root_cause` / `resolution_type` for `bug`; `applies_when` for `knowledge`). Optional `status: active|stale`, `last_audited`, `audit_notes`.

**Knowledge categories:** `architecture-patterns`, `conventions`, `tooling-decisions`, `workflow`, `best-practices`, `decisions` (the last shipped in 0.39.0 for load-bearing architectural choices). Decision entries may add three optional fields: `decision_status` (enum: `proposed | accepted | superseded`), `superseded_by` (id reference), `alternatives_considered` (free-form prose). Body convention: 1–3 sentence floor describing trade-offs, irreversibility, and surprise factor.

**Bug categories:** `build-errors`, `test-failures`, `runtime-errors`, `performance`, `security`, `integration`, `data`, `ui`.

Enable: `flowctl config set memory.enabled true`. Then `flowctl memory init`.

```bash
# Initialize tree + templates
flowctl memory init [--json]

# Add entry — bug track
flowctl memory add --track bug --category runtime-errors \
  --title "subprocess UnicodeEncodeError on Windows cp1252" \
  --module flowctl.py --tags "windows,subprocess,unicode" \
  --problem-type runtime-error --root-cause "..." \
  --resolution-type fix --body-file body.md [--json]

# Add entry — knowledge track
flowctl memory add --track knowledge --category conventions \
  --title "Use flowctl rp wrappers (not direct rp-cli)" \
  --module ralph --tags "rp,review" \
  --applies-when "any review-backend dispatch" \
  --body-file body.md [--json]

# Query
flowctl memory list [--track bug] [--category runtime-errors] [--status active|stale|all] [--json]
flowctl memory search "windows subprocess" [--track bug] [--module flowctl.py] [--tags "unicode"] [--limit 10] [--status active|stale|all] [--json]
flowctl memory read <id> [--json]
```

`memory read` accepts: full id (`bug/runtime-errors/slug-YYYY-MM-DD`), `slug+date`, `slug` (latest date wins), or legacy forms (`legacy/pitfalls.md`, `legacy/pitfalls#N`).

`--status` defaults to `active`. Stale entries are excluded from default `search` results so audit-flagged advice stops polluting `memory-scout` output.

#### memory mark-stale

Flag an entry as stale (sets `status: stale`, stamps `last_audited`, records `audit_notes`).

```bash
flowctl memory mark-stale <id> --reason "no longer accurate after fn-37 refactor" \
  [--audited-by "audit-2026-04"] [--json]
```

Idempotent — re-marking replaces `audit_notes` and re-stamps `last_audited`. Body untouched. Used by `/flow-next:audit`; also callable directly.

#### memory mark-fresh

Clear the stale flag (drops `status` and `audit_notes`, stamps `last_audited`).

```bash
flowctl memory mark-fresh <id> [--audited-by "audit-2026-04"] [--json]
```

Idempotent on already-active entries.

#### memory migrate (deprecated path)

Migrate legacy flat files (`.flow/memory/{pitfalls,conventions,decisions}.md`) into the categorized schema using a deterministic filename → `(track, category)` mechanical heuristic.

```bash
flowctl memory migrate --dry-run [--json]
flowctl memory migrate --yes [--json]
```

`--no-llm` is accepted-but-noop since 0.37.0 (classification is mechanical-only). For accurate per-entry classification with full repo context, use the agent-native `/flow-next:memory-migrate` skill — host agent classifies in-context.

Stderr emits a one-time deprecation hint pointing at the skill (TTY only; suppress via `FLOW_NO_DEPRECATION=1`).

#### memory list-legacy

Parse legacy flat-files into structured entries with mechanical default `(track, category)` per entry.

```bash
flowctl memory list-legacy [--json]
```

Returns `{files: []}` (rc=0) when no legacy files exist. Used by `/flow-next:memory-migrate` skill; also useful for ad-hoc inspection.

#### memory discoverability-patch

Patch the project's `AGENTS.md` / `CLAUDE.md` with a one-line reference to `.flow/memory/` so agents without flow-next skills can still discover the learnings store.

```bash
flowctl memory discoverability-patch [--target auto|agents|claude] [--apply] [--dry-run] [--json]
```

Defaults to `--target auto` (picks the substantive file when one is a symlink). JSON callers must pass `--apply` explicitly to write — JSON mode refuses dry-run-by-default.

### prospect

Manage prospect artifacts produced by `/flow-next:prospect` under `.flow/prospects/`.

```bash
# List active artifacts (<30 days, status=active)
flowctl prospect list [--all] [--json]

# Read a full artifact or a single section
flowctl prospect read <artifact-id> [--section focus|grounding|survivors|rejected] [--json]

# Promote a survivor to a new spec with pre-filled spec skeleton
flowctl prospect promote <artifact-id> --idea N [--spec-title "..."] [--force] [--json]

# Archive a prospect (move to .flow/prospects/_archive/)
flowctl prospect archive <artifact-id> [--json]
```

`<artifact-id>` accepts full form (`dx-improvements-2026-04-24`) or slug-only (latest date wins).

`promote` allocates a spec via the same scan-based logic as `spec create`, inlining the spec write so the prospect-context spec lands on disk from the first byte. Idempotency guard: refuses if `promoted_to` already includes the target idea — pass `--force` to override.

Exit codes: corrupt artifact on `read`/`promote` → 3 (stderr `[ARTIFACT CORRUPT: <reason>]`); duplicate idea on `promote` without `--force` → 2; Ralph-block (`REVIEW_RECEIPT_PATH` / `FLOW_RALPH=1`) on `/flow-next:prospect` → 2.

### sync

Tracker-sync plumbing for the `/flow-next:tracker-sync` bridge — atomic, deterministic helpers the skill calls. flowctl owns "set this field / enumerate / atomic-write"; the skill owns the API calls, reconciliation, and asking. Full subsystem reference: [`tracker-sync.md`](tracker-sync.md).

> **`flowctl sync` (this) is NOT `/flow-next:sync`.** `/flow-next:sync` is plan-sync (downstream task specs after drift). `flowctl sync` / `/flow-next:tracker-sync` is the external tracker bridge.

```bash
# Is the bridge active? (value-checked: enabled OR type ∈ {linear, github, gitlab, jira})
flowctl sync active [--json]

# Per-spec sync state
flowctl sync get-state <spec-id> [--json]
flowctl sync set-tracker-id <spec-id> <tracker-uuid> [--identifier WOR-17] [--url URL] [--force] [--json]
flowctl sync set-last-synced <spec-id> [--at ISO] [--json]      # defaults to now
flowctl sync set-merge-base  <spec-id> --flow|--flow-file F --tracker|--tracker-file F [--json]
flowctl sync clear <spec-id> [--json]                            # unlink, wipe state atomically

# Enumerate / guard
flowctl sync list-unsynced [--json]                             # linked-id missing → need first push
flowctl sync list-stale [--older-than-hours N] [--json]         # default N = tracker.staleAfterHours
flowctl sync check-collisions [--json]                          # tracker UUIDs shared by >1 spec

# Dependency-relation projection (fn-64) — transport-blind ledger plumbing
flowctl sync list-dep-relations <spec-id> [--json]              # edges + resolved tracker links + projected status
flowctl sync set-dep-relation <spec-id> --dep-spec <id> \
    --from-tracker-id <blocked-issue> --to-tracker-id <blocking-issue> \
    [--type blocks] [--source flow] [--json]                    # record a projected relation (idempotent)
flowctl sync clear-dep-relation <spec-id> (--key <token> | --dep-spec <id>) [--json]

# Proof-of-work + Ralph-safe queueing
flowctl sync receipt <spec-id> --status STATUS [--event KEY] [--tracker-id ID] [--transport mcp|graphql|gh|glab|rest|none] [--merges-file F] [--note N] [--json]
flowctl sync defer   <spec-id> --summary "..." [--suggested "..."] [--reason "..."] [--branch B] [--json]

# Read-only lifecycle audit (fn-57) — did every triggered touchpoint fire?
flowctl sync check <spec-id> --events <csv> --since <iso> [--json]
```

- **`set-tracker-id`** stores the durable UUID dedupe key + display `--identifier` (`WOR-17`) + url. `--force` overrides the dup-tracker-id collision guard.
- **`set-merge-base`** is a **paired-snapshot** writer: `--flow`/`--flow-file` AND `--tracker`/`--tracker-file` must come **together** (a partial one-sided write is rejected so the 3-way base never pins one half to a stale sync point).
- **`list-dep-relations`** is the transport-blind enumerator behind the skill's `projectDepRelations` hook (fn-64): it reads the spec's `depends_on_epics`, resolves each dep spec's tracker link + **local** status from sync state, and reports whether the edge is already in the `depRelations` provenance ledger — `[{dep_spec, dep_tracker_id, dep_identifier, dep_status, projected}]`. `dep_status` is the *local* dep-spec status (`done`/`open`/…), never a remote fetch — flow is authoritative, and the completed-blocker rule keys off the local dep spec being `done`. Self-edges are skipped. A dep spec with no tracker link surfaces as `dep_tracker_id: null` (the skill turns that into the missing-link warning).
- **`set-dep-relation`** records a projected blocked-by edge in the per-spec `depRelations` ledger (the `.flow/specs/<id>.json` sidecar, atomic write). `--from-tracker-id` is the **blocked** (current) issue; `--to-tracker-id` is the **blocking** (dependency) issue. The ledger entry's `key` is an opaque hash of the directed pair (never a raw issue key inline — trackers auto-linkify keys even inside HTML comments). Idempotent append (mirrors `spec add-dep`): re-recording the same directed edge is a no-op that does **not** bump `updatedAt`, so reruns are true no-ops. Self-edges are rejected.
- **`clear-dep-relation`** removes a ledger entry by `--key` (opaque token) or `--dep-spec` (canonicalized); removing a non-existent entry is a no-op success. This is the provenance-safe removal path — it only ever touches edges flow recorded, so a human-added relation outside the ledger is never affected.
- **`receipt --status`** enum: `pushed | pulled | merged | updated | diverged | queued | errored | noop`. When no transport is reachable the run is a `noop` + receipt note, never a crash. **`--event <perEvent-key>`** tags the receipt with the lifecycle touchpoint it served (`work.firstClaim`, `work.done`, `capture`, `makePr`, …) — free-form, NOT enum-validated (the perEvent key set is an open extension point). Pre-flag receipts carry `event: null` and never satisfy an event-specific `sync check`.
- **`check`** is the **read-only** end-of-skill audit (no tracker-mutation code lives in flowctl): for each event in `--events` (comma-separated perEvent keys that *triggered this run*), it reports `OK:<event>` / `MISSING:<event>` (`--json`: `{events, missing, count}`). MISSING iff the event triggered AND its `tracker.perEvent` leaf is enabled AND the bridge is active AND no receipt with a matching `event` tag and `timestamp ≥ --since` exists. Any receipt status clears (the check asserts the touchpoint *ran*); `--since` is the run-scoping lower bound (older receipts never clear); linkage is NOT a precondition (a never-linked spec that should have create-if-unlinked'd is exactly the miss this catches). **Bridge inactive → silent constant-time exit 0 before any IO** — the zero-overhead path for non-tracker repos. Exit 0 always; output drives agent action, not the exit code.
- **`defer`** queues a genuine conflict to the review deferred-findings sink (`.flow/review-deferred/<branch>.md`) — **never blocks**. In Ralph mode an `always-ask` tiebreak resolves to *queue*, not prompt.
- The hybrid id model (tracker-first `wor-17-slug` canonical / flow-first `fn-NN` + resolvable `WOR-17` alias) is keyed at create/link time: `flowctl spec create --tracker-first --tracker-identifier WOR-17` (see [`spec create`](#spec-create)). Ids never rename; resolution is case-insensitive. Details in [`tracker-sync.md`](tracker-sync.md) + [`architecture.md`](architecture.md).

### repo-map

Read clawpatch's `.clawpatch/features/*.json` codebase feature index (`/flow-next:map` skill output; clawpatch is an opt-in convenience — flowctl never imports or requires it).

**Bypasses the `ensure_flow_exists()` guard.** These readers gate on `.clawpatch/` presence instead of `.flow/`. Absent `.clawpatch/` returns `{count: 0, features: [], clawpatch_present: false}` with exit 0 — so `/flow-next:prime`'s DE7 sub-criterion check works without special-casing.

```bash
# List all parsed features (text table or JSON)
flowctl repo-map list [--count] [--json]

# Show one feature by featureId
flowctl repo-map show --feature <id> [--json]

# List features touched since a git ref (overlaps ownedFiles[] / entrypoints[]
# against `git diff --name-only <ref>..HEAD`)
flowctl repo-map since-ref <ref> [--json]
```

**Schema-version guard (R9):** `.clawpatch/features/*.json` carries `schemaVersion: 1` (Zod-validated on write by clawpatch). Mismatch or malformed JSON emits a one-line stderr diagnostic naming the offending path + expected-vs-found and skips the file — `list` never aborts. The skip count surfaces as `parse_skipped` in `list --json` when non-zero.

**`since-ref` failure handling (zero-exit envelope):** `since-ref` returns `{success: false, count: 0, features: [], error: "<kind>"}` with exit 0 — never a non-zero exit — so skill bash can branch on the JSON `success` field rather than the exit code. Error kinds:

- `not-a-git-repo` — cwd has no reachable `.git/`; `list` + `show` still work, only `since-ref` is unavailable.
- `unknown-ref` — `git rev-parse --verify <ref>^{commit}` failed.

**`list --json` shape:**

```json
{
  "success": true,
  "count": 2,
  "features": [
    {
      "featureId": "auth",
      "title": "Authentication module",
      "kind": "service",
      "confidence": "high",
      "tags": ["security", "auth"],
      "updatedAt": "2026-05-26T10:00:00Z",
      "ownedFiles": ["src/auth.ts", "src/auth.test.ts"],
      "entrypoints": ["src/auth.ts"],
      "path": ".clawpatch/features/auth.json"
    }
  ],
  "clawpatch_present": true,
  "parse_skipped": 1
}
```

**`show --json` shape:** raw `featureRecord` JSON (passthrough from `.clawpatch/features/<file>.json`) plus top-level `path` (source file location, repo-relative). Exit 3 on `--feature <id>` not resolved or `.clawpatch/` absent (distinct from generic exit 1).

**`since-ref --json` shape:** identical to `list --json` with two extra keys — `ref` (echoed input) and `changed_files` (sorted list of paths returned by `git diff --name-only <ref>..HEAD`).

`--count` (list only) prints just the scalar feature count in plain mode — used by `/flow-next:prime`'s DE7 detection (`flowctl repo-map list --count > 0`). Under `--json`, `--count` is ignored (the JSON `count` field IS the contract).

### glossary

Manage `GLOSSARY.md` — the project's canonical terminology file. Lives at the **repo root** (and optionally subdirectories), NOT inside `.flow/`. Survives `rm -rf .flow/` (R18 — terminology is the project's, not flow-next's).

**Format:** H2-per-term markdown aligned with `open-gitops/documents` and `glossarify-md` so generic markdown tooling reads it cleanly.

**Resolution:** Nearest-ancestor walk from cwd up to repo root, first match wins (same shape as `tsconfig.json` / EditorConfig). Cap 32 levels with cycle detection (constant: `GLOSSARY_WALK_MAX_DEPTH`). Fenced code blocks inside definitions are masked during parse so example terms in code don't get parsed as headings.

```bash
# Add or update a term — single-line definition
flowctl glossary add <term> --definition "Short definition." [--json]

# Add or update a term — multi-line definition from a file
flowctl glossary add <term> --definition-file body.md [--json]

# Add or update a term — multi-line definition from stdin
flowctl glossary add <term> --definition-file - [--json]

# Optional alias / cross-reference flags (comma-separated)
flowctl glossary add <term> --definition "..." \
  --avoid "alt1,alt2"          # rendered as `_Avoid_:` italic line
  --relates-to "x,y"           # rendered as `_Relates to_:` italic line

# List defined terms across every GLOSSARY.md on the ancestor chain (nearest first)
flowctl glossary list [--json]

# Read a term — walks ancestors, first match wins
flowctl glossary read <term> [--json]

# Remove a term — last-term remove leaves an `# Glossary` H1 husk on disk (R18)
flowctl glossary remove <term> [--json]
```

**JSON shapes:**

`glossary list --json`:
```json
{
  "success": true,
  "groups": [
    {"path": "GLOSSARY.md", "entries": [{"term": "Spec", "definition": "...", "avoid": [], "relates_to": []}], "count": 1}
  ],
  "file_count": 1,
  "total_terms": 1
}
```

`glossary read --json`:
```json
{"success": true, "path": "GLOSSARY.md", "term": "Spec", "definition": "...", "avoid": [], "relates_to": []}
```

**Husk semantics:** Last-term `remove` leaves a `# Glossary` H1 husk — the file is never deleted (R18). Doc-aware autodetect should branch on `total_terms > 0` (or `file_count > 0` and any group's `count > 0`), not on `[[ -f GLOSSARY.md ]]` — the latter would falsely activate doc-aware mode on an empty husk.

**Helpers (Python imports):** Downstream skills should call the subcommands rather than reimplementing parsing, but the building blocks are exposed for ad-hoc reuse: `find_nearest_glossary` / `find_all_glossaries` / `parse_glossary_file` / `render_glossary_file` / `validate_glossary_entry` / `_glossary_term_matches` / `_glossary_strip_fenced_code`. Constants: `GLOSSARY_FILE` (`"GLOSSARY.md"`), `GLOSSARY_WALK_MAX_DEPTH` (`32`).

### triage-skip

Trivial-diff fast path that bypasses the configured review backend on whitelisted diffs (lockfile-only, docs-only, release-chore, generated-file-only). Returns `VERDICT=SHIP` deterministically.

```bash
flowctl triage-skip --base main [--task fn-1.2] [--receipt /tmp/triage.json] [--json]

# With LLM judge for ambiguous diffs (gated behind FLOW_TRIAGE_LLM=1 in Ralph)
flowctl triage-skip --base main --backend codex --model gpt-5-mini --effort low [--json]

# Whitelist-only mode (ambiguous → REVIEW)
flowctl triage-skip --base main --no-llm [--json]
```

Exit codes: `0` SKIP, `1` REVIEW, `2+` error. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.

Receipt schema (only on SKIP):
```json
{"type": "triage_skip", "id": "fn-1.2", "mode": "triage_skip", "verdict": "SHIP", "timestamp": "..."}
```

### prep-chat

Generate properly escaped JSON for RepoPrompt chat. Avoids shell escaping issues with complex prompts.
Optional legacy positional arg is ignored; do not pass spec/task IDs.

```bash
# Write message to file (avoids escaping issues)
cat > /tmp/prompt.md << 'EOF'
Your multi-line prompt with "quotes", $variables, and `backticks`.
EOF

# Generate JSON
flowctl prep-chat \
  --message-file /tmp/prompt.md \
  --mode chat \
  [--new-chat] \
  [--chat-name "Review Name"] \
  [--selected-paths file1.ts file2.ts] \
  [-o /tmp/payload.json]

# Prefer flowctl rp chat-send (uses this internally)
flowctl rp chat-send --window W --tab T --message-file /tmp/prompt.md
```

Options:
- `--message-file FILE` (required): File containing the message text
- `--mode {chat,ask}`: Chat mode (default: chat)
- `--new-chat`: Start a new chat session
- `--chat-name NAME`: Name for the new chat
- `--selected-paths FILE...`: Files to include in context (for follow-ups)
- `-o, --output FILE`: Write JSON to file (default: stdout)

Output (stdout or file):
```json
{"message": "...", "mode": "chat", "new_chat": true, "chat_name": "...", "selected_paths": ["..."]}
```

### rp

RepoPrompt wrappers (preferred for reviews). Requires RepoPrompt 1.5.68+.

**Primary entry point** (handles window selection + builder atomically):

```bash
# Atomic setup - picks window by repo root and creates builder tab
eval "$(flowctl rp setup-review --repo-root "$REPO_ROOT" --summary "Review a plan to ...")"
# Returns: W=<window> T=<tab>

# With --create: auto-creates RP window if none matches (RP 1.5.68+)
eval "$(flowctl rp setup-review --repo-root "$REPO_ROOT" --summary "..." --create)"
```

**Post-setup commands** (use $W and $T from setup-review):

```bash
flowctl rp prompt-get --window "$W" --tab "$T"
flowctl rp prompt-set --window "$W" --tab "$T" --message-file /tmp/review-prompt.md
flowctl rp select-add --window "$W" --tab "$T" path/to/file
flowctl rp chat-send --window "$W" --tab "$T" --message-file /tmp/review-prompt.md
flowctl rp prompt-export --window "$W" --tab "$T" --out /tmp/export.md
```

**Low-level commands** (prefer setup-review instead):

```bash
flowctl rp windows [--json]
flowctl rp pick-window --repo-root "$REPO_ROOT"
flowctl rp ensure-workspace --window "$W" --repo-root "$REPO_ROOT"
flowctl rp builder --window "$W" --summary "Review a plan to ..."
```

### codex

OpenAI Codex CLI wrappers — cross-platform alternative to RepoPrompt.

**Requirements:**
```bash
npm install -g @openai/codex
codex auth
```

**Model:** Uses the ranking top, GPT 5.6 Sol at High effort, by default (no user config needed) — resolved strongest-available via the [model-resolution ladder](#model-resolution-strongest-available-never-fail--fn-76) (on an older codex CLI that rejects it, the ladder transparently downgrades to `gpt-5.5` and caches that). Override with `FLOW_CODEX_MODEL` env var.

**Commands:**

```bash
# Verify codex is available
flowctl codex check [--json]

# Implementation review (reviews code changes for a task)
flowctl codex impl-review <task-id> --base <branch> [--sandbox <mode>] [--receipt <path>] [--json]
# Example: flowctl codex impl-review fn-1.3 --base main --sandbox auto --receipt /tmp/impl-fn-1.3.json

# Plan review (reviews spec before implementation)
flowctl codex plan-review <spec-id> --files <file1,file2,...> [--sandbox <mode>] [--receipt <path>] [--json]
# Example: flowctl codex plan-review fn-1 --files "src/auth.ts,src/config.ts" --sandbox auto --receipt /tmp/plan-fn-1.json
# Note: Spec/task markdown is included automatically; --files should be CODE files for repository context.

# Completion review (reviews spec implementation against acceptance criteria)
flowctl codex completion-review <spec-id> [--sandbox <mode>] [--receipt <path>] [--json]
# Example: flowctl codex completion-review fn-1 --sandbox auto --receipt /tmp/completion-fn-1.json
# Runs after all tasks done; verifies implementation matches spec requirements
```

**How it works:**

1. **Gather context hints** — Analyzes changed files, extracts symbols (functions, classes), finds references in unchanged files
2. **Build review prompt** — Uses same Carmack-level criteria as RepoPrompt (7 criteria each for plan/impl)
3. **Run codex** — Executes `codex exec` with the prompt (or `codex exec resume` for session continuity)
4. **Parse verdict** — Extracts `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>` from output
5. **Write receipt** — If `--receipt` provided, writes JSON for Ralph gating

**Context hints example:**
```
Changed files: src/auth.py, src/handlers.py
Symbols: authenticate(), UserSession, validate_token()
References: src/middleware.py:45 (calls authenticate), tests/test_auth.py:12
```

**Review criteria (identical to RepoPrompt):**

| Review | Criteria |
|--------|----------|
| Plan | Completeness, Feasibility, Clarity, Architecture, Risks, Scope, Testability |
| Impl | Correctness, Simplicity, DRY, Architecture, Edge Cases, Tests, Security |

**Receipt schema (Ralph-compatible):**

Impl review receipt:
```json
{
  "type": "impl_review",
  "id": "fn-1.3",
  "mode": "codex",
  "verdict": "SHIP",
  "session_id": "thread_abc123",
  "timestamp": "2026-01-11T10:30:00Z"
}
```

Completion review receipt:
```json
{
  "type": "completion_review",
  "id": "fn-1",
  "mode": "codex",
  "verdict": "SHIP",
  "session_id": "thread_xyz456",
  "timestamp": "2026-01-11T10:30:00Z"
}
```

**Session continuity:** Receipt includes `session_id` (thread_id from codex). Subsequent reviews read the existing receipt and resume the conversation, maintaining full context across fix → re-review cycles.

**Deterministic review cap + convergence (fn-90 — all backends: codex/copilot/cursor internally; rp via `flowctl review-rounds`):**

The fix→re-review loop is bounded by a **flowctl-owned cumulative round counter on spec state**, not just the host LLM's in-agent iteration counter (which resets on every fresh `/flow-next:*-review` invocation — the loop-runaway root cause). It applies to every backend and every review kind:

- **Counter surfaces:** plan reviews increment a spec-scoped `plan_review_rounds`; impl reviews increment a per-task `impl_review_rounds[<task-id>]`. **Completion reviews reuse the spec-scoped `plan_review_rounds` counter** (they are spec-scoped, no task in context) — a plan review and a completion review on the same spec spend the *same* cap, so neither can independently re-open the runaway. Both surface in `flowctl show --json`.
- **Enforcement:** each backend dispatch calls the cap check BEFORE running the reviewer (codex/copilot/cursor inside their `flowctl <backend> *-review` handlers; rp — dispatched from skill prose via `rp chat-send` — through an explicit `flowctl review-rounds increment` call in the workflow, see [review-rounds increment / reset](#review-rounds-increment--reset)). At `${MAX_REVIEW_ITERATIONS:-4}` (default 4, env-overridable) it **refuses to dispatch**, prints an `ESCALATE:` marker, and exits with a **dedicated exit code `4`** — distinct from transport/backend-failure codes (`2` = exec failure, `3` = sandbox), so a host or Ralph loop cannot misread the cap refusal as a retryable error. Under Ralph/autonomous the refusal must surface as **NEEDS_HUMAN**, never a retry (a retry loop on the cap re-creates the runaway one level up). The refusal is idempotent — repeated calls at the cap keep refusing without further increment.
- **Round-counting semantics (deliberate anti-runaway bias):** a "round" is **every dispatch ATTEMPT, including a failed/malformed exec** — NOT only SHIP/NEEDS_WORK-resolved rounds. A reviewer run that produces no parseable verdict still consumes the cap. Worst case is *early* human escalation, which is the safe direction; the alternative (only counting resolved rounds) would let malformed-verdict retries loop unbounded.
- **Reset semantics:** the counter resets to 0 **only** on a `SHIP` verdict (from the receipt-write path) or an explicit re-plan (`flowctl spec reset-review-rounds <spec-id>` — see [spec reset-review-rounds](#spec-reset-review-rounds)). It does **NOT** reset on a spec/code edit (fix rounds legitimately edit the artifact; resetting there reopens the runaway through the back door) nor on a fresh invocation.

**Receipt convergence-ratchet fields (fn-90, back-compatible):**

- The receipt stores the prior round's review text in a `review` field. On a re-review, flowctl injects it into a **shrink-only convergence-ratchet preamble** (verify each prior finding fixed; only a NEW ≥ Major finding may block; all prior fixed + no new ≥ Major ⇒ verdict MUST be SHIP) instead of ordering a fresh blind review each round. A receipt written by older flowctl **without** the `review` field parses fine and is treated as a **fresh round-1 review** (no ratchet) — full back-compat. The **rp backend needs no injected ratchet**: its re-reviews deliberately stay in the SAME RepoPrompt chat (no `--new-chat`), so the reviewer retains genuine conversational memory of its own prior findings — the fresh-blind churn the ratchet compensates for does not occur there; on rp only the cap applies.
- **Receipt default paths are spec/task-scoped.** The skill/workflow defaults are now `/tmp/plan-review-receipt-<spec>.json`, `/tmp/completion-review-receipt-<spec>.json`, and `/tmp/impl-review-receipt-<task>.json` (standalone branch review with no task falls back to the unscoped name) — concurrent reviews of different specs/tasks no longer collide on one shared `/tmp` receipt. An explicit **`REVIEW_RECEIPT_PATH`** (or `--receipt`) still wins, unchanged.
- **Codex/copilot verdict extraction is honest.** The verdict parse isolates the **final agent message** from the stream (dropping `command_execution` / `aggregated_output` tool output) and takes the **last** `<verdict>` match — a verdict literal echoed in tool output or a quoted-grammar literal in the final message can no longer beat the reviewer's real verdict. The offline regression that locks this in: `optimization/review-prompt/reveval_parse_guard.py` (runs in the gate via `test_reveval_parse_guard.py`).

**Sandbox mode (`--sandbox`):** Controls Codex CLI's file system access. Available modes:
- `read-only` (default on Unix) — Can only read files
- `workspace-write` — Can write files in workspace
- `danger-full-access` — Full file system access (required for Windows)
- `auto` — Resolves to `danger-full-access` on Windows, `read-only` on Unix

**Windows users:** Codex CLI's `read-only` sandbox blocks ALL shell commands on Windows (including reads). Use `--sandbox auto` or `--sandbox danger-full-access` for Windows compatibility.

**Note:** After plugin update, re-run `/flow-next:setup` or `/flow-next:ralph-init` to get sandbox fixes.

#### codex validate

Validator pass over prior review findings (`fn-32.1 --validate`). Drops confirmed false-positives in the same chat session.

```bash
flowctl codex validate --findings-file findings.jsonl --receipt /tmp/impl-fn-1.3.json [--spec codex:gpt-5.4:high] [--json]
```

`--findings-file` is JSON-Lines (one finding per line, with at least `id`). Empty/missing → no-op. Receipt drives session resume via `session_id`.

#### codex deep-pass

Specialized deep-review pass (`fn-32.2 --deep`). Runs after primary review in the same chat session.

```bash
flowctl codex deep-pass --pass adversarial --receipt /tmp/impl-fn-1.3.json [--primary-findings primary.jsonl] [--spec codex:gpt-5.4:high] [--json]
flowctl codex deep-pass --pass security    --receipt /tmp/impl-fn-1.3.json --primary-findings primary.jsonl
flowctl codex deep-pass --pass performance --receipt /tmp/impl-fn-1.3.json --primary-findings primary.jsonl
```

Pass options: `adversarial`, `security`, `performance`. Primary findings JSONL provides cross-pass agreement / dedup context. Receipt is required (provides `session_id` for resume).

### copilot

GitHub Copilot CLI wrappers — alternative review backend, parallel to codex. Same review criteria (Carmack-level, 7 each for plan/impl), same receipt schema, same session-resume model.

```bash
# Verify copilot availability + auth
flowctl copilot check [--json]

# Implementation review
flowctl copilot impl-review <task-id> --base <branch> [--receipt <path>] [--spec copilot:claude-opus-4.5:high] [--json]

# Plan review
flowctl copilot plan-review <spec-id> --files <file1,file2,...> [--receipt <path>] [--spec ...] [--json]

# Completion review
flowctl copilot completion-review <spec-id> [--receipt <path>] [--spec ...] [--json]

# Validator pass (fn-32.1 --validate)
flowctl copilot validate --findings-file findings.jsonl --receipt /tmp/impl-fn-1.3.json [--spec ...] [--json]

# Deep-pass review (fn-32.2 --deep)
flowctl copilot deep-pass --pass adversarial|security|performance \
  --receipt /tmp/impl-fn-1.3.json [--primary-findings primary.jsonl] [--spec ...] [--json]
```

Spec form: `copilot[:model[:effort]]`. Default model resolved via env (`FLOW_COPILOT_MODEL`) / config / registry. Receipt fields mirror codex: `mode: "copilot"`, `session_id` for resume.

### cursor

Cursor `cursor-agent` CLI wrappers — alternative review backend, parallel to codex/copilot. Same review criteria (Carmack-level, 7 each for plan/impl), same receipt schema, same session-resume model. Unlocks Cursor-billed review (your existing Cursor subscription, no separate API key) and Cursor reviewer models the others can't reach in one place: `gpt-5.6-sol-high` (1M ctx, the default since 2.10.3 — verified live via `--list-models`), the `gpt-5.6-terra`/`gpt-5.6-luna` variants, `gpt-5.5-high`, the `gpt-5.3-codex` family, `composer-2.5`, `claude-opus-4-8-thinking-high`.

```bash
# Verify cursor availability + auth
flowctl cursor check [--json] [--skip-probe]

# Implementation review
flowctl cursor impl-review <task-id> --base <branch> [--receipt <path>] [--spec cursor:gpt-5.5-high] [--json]

# Plan review
flowctl cursor plan-review <spec-id> --files <file1,file2,...> [--receipt <path>] [--spec ...] [--json]

# Completion review
flowctl cursor completion-review <spec-id> [--receipt <path>] [--spec ...] [--json]

# Validator pass (fn-32.1 --validate)
flowctl cursor validate --findings-file findings.jsonl --receipt /tmp/impl-fn-1.3.json [--spec ...] [--json]

# Deep-pass review (fn-32.2 --deep)
flowctl cursor deep-pass --pass adversarial|security|performance \
  --receipt /tmp/impl-fn-1.3.json [--primary-findings primary.jsonl] [--spec ...] [--json]
```

Spec form: `cursor[:model]` — **effort is folded into the model name** (Cursor convention), so `cursor:<model>:<effort>` is rejected. Default model resolved via env (`FLOW_CURSOR_MODEL`, no `FLOW_CURSOR_EFFORT`) / config / registry. Receipt fields mirror codex/copilot but **omit `effort`**: `mode: "cursor"`, `spec: "cursor:<model>"`, `session_id` for resume. Sessions are **resume-only** — the first call omits `--resume` and persists Cursor's generated `session_id`; a continuation passes `--resume <stored-id>` only when the receipt's `mode == "cursor"` (cross-backend → fresh). Runs `cursor-agent -p --output-format json --trust --mode ask` with `cwd=repo_root` (read-only Q&A; never mutates the tree). Keep the model list synced with `cursor-agent --list-models`. **Auth:** stored `cursor-agent` login OR `CURSOR_API_KEY`. **Triage note:** the opt-in LLM triage judge (`FLOW_TRIAGE_LLM=1`, default off) stays `codex|copilot` — a cursor user who enables it also needs codex/copilot present; with the judge off (the default) cursor reviews use the deterministic whitelist, zero extra dependency.

### ralph

Ralph autonomous-loop run control. Reads/writes the run-state file at `scripts/ralph/runs/<run>/state.json`.

```bash
flowctl ralph status   [--json]   # Show active runs + their state
flowctl ralph pause              # Pause a Ralph run (worker checks between iterations)
flowctl ralph resume             # Resume a paused run
flowctl ralph stop               # Request a Ralph run to stop gracefully
```

Used by humans to pause/stop a long-running Ralph loop without `kill -9`. Worker scripts poll the state file at iteration boundaries and act accordingly.

### review-deep-auto

Print the deep-pass set that auto-enables for a changed-file list (`fn-32.2`). Used by `--deep` (without explicit list) to derive `security` / `performance` based on file globs (Dockerfiles → security; large refactors / hot paths → performance).

```bash
flowctl review-deep-auto --files "src/auth.ts,src/handlers.ts" [--json]
flowctl review-deep-auto < changed-files.txt   # one path per line
```

Output (text): comma-separated pass names (e.g. `adversarial,security`). JSON: `{"passes": ["adversarial", "security"]}`.

### review-walkthrough-defer

Append deferred findings to `.flow/review-deferred/<branch>.md` (`fn-32.3 --interactive`). Append-only; creates the directory if absent.

```bash
flowctl review-walkthrough-defer --findings-file deferred.jsonl \
  [--receipt /tmp/impl-fn-1.3.json] [--branch fn-1-add-auth] [--json]
```

`--findings-file`: JSON-Lines (one finding per line: `id`, `severity`, `confidence`, `classification`, `file`, `line`, `title`, `suggested_fix`; optional `deferred_reason` overrides default label). `--receipt` adds session header. `--branch` overrides slug derivation (default: `git branch --show-current`, falls back to `HEAD` on detached).

### review-walkthrough-record

Stamp the receipt with walkthrough bucket counts (`fn-32.3 --interactive`). Additive — never changes verdict.

```bash
flowctl review-walkthrough-record --receipt /tmp/impl-fn-1.3.json \
  --applied 3 --deferred 5 --skipped 2 --acknowledged 1 --lfg-rest false [--json]
```

Receipt gets a `walkthrough` block:
```json
{"walkthrough": {"applied": 3, "deferred": 5, "skipped": 2, "acknowledged": 1, "lfg_rest": false},
 "walkthrough_timestamp": "2026-04-28T..."}
```

### checkpoint

Save and restore spec state (used during review-fix cycles).

```bash
# Save spec state to .flow/.checkpoint-fn-1.json
flowctl checkpoint save --spec fn-1 [--json]

# Restore spec state from checkpoint
flowctl checkpoint restore --spec fn-1 [--json]

# Delete checkpoint
flowctl checkpoint delete --spec fn-1 [--json]
```

Checkpoints preserve full spec + task state. Useful when compaction occurs during plan-review cycles.

### status

Show `.flow/` state summary.

```bash
flowctl status [--json]
```

Output:
```json
{"success": true, "spec_count": 2, "task_count": 5, "done_count": 2, "active_runs": []}
```

Human-readable output shows spec/task counts and any active Ralph runs.

### state-path

Show the resolved state directory path (useful for debugging parallel worktree setups).

```bash
flowctl state-path [--json]
```

Output:
```json
{"success": true, "state_dir": "/repo/.git/flow-state", "source": "git-common-dir"}
```

Source values:
- `env` — `FLOW_STATE_DIR` environment variable
- `git-common-dir` — `git --git-common-dir` (shared across worktrees)
- `fallback` — `.flow/state` (non-git or old git)

### migrate-state

Migrate existing repos to the shared runtime state model.

```bash
flowctl migrate-state [--clean] [--json]
```

Options:
- `--clean` — Remove runtime fields from tracked JSON files after migration (recommended for cleaner git diffs)

What it does:
1. Scans all task JSON files for runtime fields (`status`, `assignee`, `claimed_at`, etc.)
2. Writes those fields to the state directory (`.git/flow-state/tasks/`)
3. With `--clean`: removes runtime fields from the original JSON files

**When to use:**
- After upgrading to 0.17.0+ if you want parallel worktree support
- To clean up git diffs (runtime changes no longer tracked)

**Not required** for normal operation — the merged read path handles backward compatibility automatically.

### migrate-rename

Migrate the on-disk `.flow/` layout from pre-1.0 (`.flow/epics/`) to canonical 1.0 (`.flow/specs/`). Writes a complete pre-migration snapshot to `.flow/.backup-pre-1.0/` and a structured manifest at `.flow/.migration-manifest`; stamps `.flow/.flow_version = 1.0.0` LAST so a crash mid-migration is recoverable on the next run.

```bash
flowctl migrate-rename [--dry-run] [--yes] [--json]
```

Default mode is `--dry-run`: prints the plan without writing anything (except the `.flow/.banner-acknowledged` marker — see below). Pass `--yes` to apply. Passing both `--dry-run` and `--yes` is a hard error (exit code 2) so a CI-set `--yes` cannot silently become a no-op when a CLI default flips.

`--json` output requires `--yes` for write operations (refuses dry-run-by-default to avoid ambiguity).

**What it does (when applied):**

1. Acquire `.flow/.migrating/` lockfile (cross-platform `os.mkdir` atomicity; PID written inside for stale-detection).
2. Snapshot `.flow/` → `.flow/.backup-pre-1.0/`; write `.complete` marker only after the copy finishes.
3. Initialize `.flow/.migration-manifest` with the planned entries.
4. Move JSON sidecars from `.flow/epics/` to `.flow/specs/`; rewrite `meta.json` (`schema_version` → 3, `next_epic` → `next_spec`); rewrite task JSON `epic` field → `spec`; remove the now-empty `.flow/epics/`.
5. Atomically write `.flow/.flow_version = "1.0.0"` (LAST — sentinel-based idempotency anchor).
6. Release the lockfile.

The backup directory is retained after a successful migration. Use `flowctl migrate-rollback --yes` to undo.

**Crash-recovery decision tree** (executed on every invocation, before any new writes):

| State on disk | Interpretation | Action |
|---------------|----------------|--------|
| Sentinel valid (`.flow_version = 1.0.0`) | Already migrated | Idempotent skip; works on read-only `.flow/` (the idempotency check runs BEFORE the read-only refusal so archived-branch builds and frozen worktrees pass through cleanly). |
| Sentinel absent + backup `.complete` marker present | Mid-migration crash; backup intact | Copy backup contents back over `.flow/`, then restart at step 4 (fresh attempt). |
| Sentinel absent + backup dir present + no `.complete` marker | Backup mid-copy crashed | Wipe the partial backup; restart at step 4. |
| Sentinel absent + no backup + no `.flow/epics/` | Neither pre-1.0 nor migrated (e.g. fresh init) | No-op exit 0; refuses to mutate state speculatively. |
| Sentinel absent + `.flow/epics/` present | Pre-1.0 layout confirmed | Migrate. |

**Cross-platform lockfile + PID-liveness reclaim:** `os.mkdir` is atomic on POSIX and Windows. The PID written inside is checked against the running process table on both platforms (POSIX `kill(pid, 0)`, Windows `OpenProcess`/`GetExitCodeProcess`). If the holder is dead, the lock is reclaimed. A `MIGRATE_LOCK_PID_GRACE_SECS` window covers the race between `mkdir` and the PID write so a crash between the two steps doesn't leave the next invocation waiting the full `MIGRATE_LOCK_WAIT_SECS` before reclaim.

**SHA256 task-drift detection:** the manifest records SHA256 of every task JSON the migration touched. `migrate-rollback` re-hashes those files on disk and refuses to roll back if any drifted (unless `--force-overwrite-post-migration-changes` is passed) — protects against the "Ralph wrote new tasks under the migrated layout, then someone tried to undo the migration" footgun.

**Banner acknowledgement:** `--dry-run` writes `.flow/.banner-acknowledged` with an ISO timestamp. The migration auto-detect banner uses this marker to suppress the 6-line stderr nudge for 7 days. Bare `flowctl <verb>` invocations DO NOT write this marker — passive banner display is not acknowledgement. See [Migration banner](#migration-banner).

**Read-only filesystem ordering:** the idempotency check runs FIRST so already-migrated repos on read-only `.flow/` are no-ops, NOT failures. Only an explicit `--yes` against an unmigrated read-only `.flow/` errors out (pre-1.0 layout that genuinely needs writing).

**JSON output (success path):**

```json
{"migrated": true, "dry_run": false, "plan": ["backup .flow/ -> .backup-pre-1.0/...", "..."],
 "entries": [{"from": ".flow/epics/fn-1.json", "to": ".flow/specs/fn-1.json", "sha256": "..."}],
 "manifest_path": ".flow/.migration-manifest", "sentinel_path": ".flow/.flow_version",
 "backup_path": ".flow/.backup-pre-1.0"}
```

### migrate-rollback

Restore the pre-1.0 layout from `.flow/.backup-pre-1.0/`. Refuses by default if the manifest is missing or any post-migration spec/task file exists outside the manifest (drift detection).

```bash
flowctl migrate-rollback [--yes] [--force-overwrite-post-migration-changes] [--json]
```

`--yes` is required for any rollback. Without it, prints the safety-check summary and exits 1.

**Manifest-safety contract:**

- Refuses if `.flow/.backup-pre-1.0/.complete` is missing (no complete backup exists).
- Refuses if `.flow/.migration-manifest` is missing or unreadable (cannot detect post-migration writes safely).
- Refuses if any post-migration spec/task file exists that the manifest doesn't cover (`unexpected paths`). Pass `--force-overwrite-post-migration-changes` to discard them.
- Refuses on read-only `.flow/` (same shape as `migrate-rename`).
- Acquires the same `.flow/.migrating/` lockfile so rollback can't race a parallel `migrate-rename`.

**Rollback-deletes-manifest invariant:** rollback removes the sentinel + manifest from `.flow/`, leaving the backup directory intact. This is what makes the migrate → rollback cycle repeatable (run `migrate-rename --yes` again immediately after rollback and it does the right thing). The backup is NOT deleted by rollback — `migrate-rename` re-snapshots on the next run.

**JSON output (success path):**

```json
{"rolled_back": true, "actions": ["restored specs/fn-1.json from backup", "removed .flow_version", "removed .migration-manifest"],
 "post_migration_writes_overridden": false, "unexpected_paths": [], "backup_path": ".flow/.backup-pre-1.0"}
```

## Migration banner

flowctl emits a one-time stderr banner when it detects a pre-1.0 `.flow/` layout. The banner is informational only — it never affects subcommand exit codes or behavior. It runs once per process (process-level dedup flag); it never auto-applies the migration.

**The 6-line copy (verbatim):**

```
flow-next 1.0 renamed `flowctl epic` -> `flowctl spec`.
Your `.flow/epics/` directory is from 0.x; alias mode keeps everything working.
Migrate to unlock future flow-swarm compatibility:
  Interactive:  /flow-next:setup
  Deterministic: flowctl migrate-rename --yes
Suppress this banner: FLOW_NO_AUTO_MIGRATE=1 (alias keeps working)
```

**Suppression matrix** (any one true → silent return):

| Suppressor | Reason |
|------------|--------|
| `FLOW_RALPH=1` | Autonomous loop; no human reads stderr. |
| `REVIEW_RECEIPT_PATH` set | Review subprocess; agent doesn't see stderr. |
| `FLOW_NO_AUTO_MIGRATE=1` | User opt-out env knob. |
| Process-level dedup flag | Already emitted in this invocation. |
| Sentinel valid (≤ 1.x) | Already migrated. |
| `.banner-acknowledged` < 7 days old | User actively engaged with migration UX. |

**`.flow/.banner-acknowledged` lifecycle:**

- Written by `flowctl migrate-rename --dry-run` (the user inspected the plan — that's acknowledgement).
- Written by `/flow-next:setup` when the user defers the upgrade interactively (T9/.10).
- **Never** written by bare `flowctl <verb>` invocations (banner emission is passive display, not acknowledgement).
- File payload is an ISO-8601 UTC timestamp. Missing / empty / unparseable / future-dated timestamps all fall through to banner emission (defensive read).

**7-day re-nudge cadence:** after acknowledgement, the banner is suppressed for `BANNER_RENUDGE_DAYS = 7` days. After expiry the banner re-emits ONCE on the next invocation; the timestamp is NOT auto-refreshed — the user must run `migrate-rename --dry-run` again (or migrate) to extend the suppression window.

**Future-version downgrade-safety warning:** if the sentinel parses as semver `>=2.x` (e.g. someone migrated with a newer flowctl, then a teammate runs an older flowctl on the same repo), the banner subsystem emits a one-line warning to stderr — *"Warning: .flow/ was migrated by a newer flow-next (X.Y.Z); some features may be unavailable."* — and lets the subcommand proceed normally with its own exit code. The pre-1.0 banner is NOT shown in this case (mutually exclusive paths).

**Process-level dedup:** the banner emits at most once per `flowctl` invocation. Multi-process invocations (e.g. a Ralph loop spawning many `flowctl` calls) DO each emit the banner once if their suppressors don't match — there is no cross-process dedup. The expected pattern is for Ralph to set `FLOW_RALPH=1` and absorb the suppression that way.

## Deprecated aliases

flow-next 1.0.0 renamed the spec surface from `epic` to `spec`. Every legacy form continues to work in 1.x as a thin alias; each alias emits a one-line stderr deprecation warning. Suppress all such warnings via `FLOW_NO_DEPRECATION=1`. **Soft-removal target is 2.0.0 — telemetry-driven, NOT calendar-driven.** R28 explicitly forbids hard-coded sunset dates; if real-world `flowctl epic` invocations stay common, the alias layer stays past 2.0.0.

**Verb / parent subcommand aliases:**

| Legacy form | Canonical 1.0 form |
|-------------|---------------------|
| `flowctl epic create` | `flowctl spec create` |
| `flowctl epic set-plan` | `flowctl spec set-plan` |
| `flowctl epic set-plan-review-status` | `flowctl spec set-plan-review-status` |
| `flowctl epic set-completion-review-status` | `flowctl spec set-completion-review-status` |
| `flowctl epic set-branch` | `flowctl spec set-branch` |
| `flowctl epic set-title` | `flowctl spec set-title` |
| `flowctl epic close` | `flowctl spec close` |
| `flowctl epic ready` | `flowctl spec ready` |
| `flowctl epic unready` | `flowctl spec unready` |
| `flowctl epic add-dep` | `flowctl spec add-dep` |
| `flowctl epic rm-dep` | `flowctl spec rm-dep` |
| `flowctl epic set-backend` | `flowctl spec set-backend` |
| `flowctl epic export-cognitive-aid` | `flowctl spec export-cognitive-aid` |
| `flowctl epics` | `flowctl specs` |

**Flag aliases:**

| Legacy flag | Canonical 1.0 flag | Used on |
|-------------|---------------------|---------|
| `--epic` | `--spec` | `task create`, `tasks`, `ready`, `validate`, `checkpoint save/restore/delete` |
| `--epic-title` | `--spec-title` | `prospect promote` (silent alias — no deprecation warning, since the prospect-promote skill is internal enough that a warning would just spam Ralph; the verb-level `flowctl epic *` deprecation already surfaces the rename path) |
| `--epics-file` | `--specs-file` | `next` |

**Filesystem aliases:**

| Legacy path | Canonical 1.0 path |
|-------------|---------------------|
| `.flow/epics/<id>.json` | `.flow/specs/<id>.json` |

The markdown was already at `.flow/specs/<id>.md` pre-1.0; only the JSON sidecar moved. The alias layer keeps reads working until you run `flowctl migrate-rename --yes`.

**Slash-command alias:**

| Legacy command | Canonical 1.0 command |
|----------------|------------------------|
| `/flow-next:epic-review` | `/flow-next:spec-completion-review` |

The old slash command stays as a thin redirect.

**Suppression env var:**

```bash
export FLOW_NO_DEPRECATION=1   # silence per-process
```

The same env var also silences the legacy `FLOW_MEMORY_CLASSIFIER_*` warning surface (removed in 0.37.0).

## Ralph Receipts

RepoPrompt review receipts are written by the review skills (not flowctl commands). Codex review receipts are written by `flowctl codex impl-review` and `flowctl codex completion-review` when `--receipt` is provided. Ralph sets `REVIEW_RECEIPT_PATH` to coordinate both.

See: [Ralph deep dive](ralph.md)

## JSON Output

All commands support `--json` (except `cat`). Wrapper format:

```json
{"success": true, ...}
{"success": false, "error": "message"}
```

Exit codes: 0=success, 1=general error, 2=tool/parse error, 3=sandbox configuration error.

## Error Handling

- Missing `.flow/`: "Run 'flowctl init' first"
- Invalid ID format: "Expected format: fn-N (spec) or fn-N.M (task)"
- File conflicts: Refuses to overwrite existing specs/tasks
- Dependency violations: Same-spec only, must exist, no cycles
- Status violations: Can't start non-todo, can't close with incomplete tasks
