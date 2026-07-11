# Flow-Next Usage Guide

Task tracking for AI agents. All state lives in `.flow/`.

## CLI

```bash
.flow/bin/flowctl --help              # All commands
.flow/bin/flowctl <cmd> --help        # Command help
```

## File Structure

```
.flow/
├── bin/flowctl                  # CLI (this install)
├── templates/spec.md            # Canonical 7-section spec scaffold (copied by /flow-next:setup)
├── specs/fn-N-slug.md           # Spec content (canonical)
├── specs/fn-N-slug.json         # Spec metadata (1.0+ — colocated with the markdown)
├── tasks/fn-N-slug.M.md         # Task specifications
├── tasks/fn-N-slug.M.json       # Task metadata
├── memory/{bug,knowledge}/<category>/  # Context memory (categorized; bug: build-errors, runtime-errors, test-failures, …; knowledge: architecture-patterns, conventions, …)
├── prospects/<slug>-<date>.md   # Ideation artifacts (v0.36.0+)
├── artifacts/<spec-id>/         # Regenerable HTML render lenses — spec.html + pr.html (opt-in via artifacts.html.enabled; fixed paths, never timestamped; commit-or-gitignore per project)
├── review-receipts/<branch>.json  # Review verdicts + findings (per branch)
├── review-deferred/<branch>.md  # Walkthrough deferrals (fn-32.3)
├── .flow_version                # 1.0.0 sentinel — written after layout migration
├── .gitignore                   # Auto-managed by flowctl (1.0+) — excludes per-developer state + migration transients
└── meta.json                    # Project metadata (schema_version, setup_version, setup_date)
```

`.flow/epics/` is the pre-1.0 sidecar location. Repos created on 1.0+ never have it; pre-1.0 repos keep working via the alias layer until you run `flowctl migrate-rename --yes` (or `/flow-next:setup`'s upgrade branch).

`.flow/.gitignore` is auto-written by `flowctl init` and `flowctl migrate-rename` so `git add -A` doesn't accidentally commit per-developer state (`.checkpoint-*.json`, `receipts/`, `tmp/`) or migration transients (`.backup-pre-1.0/`, `.banner-acknowledged`, `.migrating`, `.migration-manifest`). Idempotent; user patterns added below the auto-managed footer are preserved on update.

The project's strategic intent and canonical vocabulary live **outside** `.flow/` so they survive `rm -rf .flow/`:

- `STRATEGY.md` (repo root) — target problem, approach, personas, metrics, active tracks (v0.40.0+).
- `GLOSSARY.md` (repo root or any ancestor) — canonical terms with `_Avoid_` aliases (v0.39.0+).

## IDs

- Specs: `fn-N-slug` where slug is derived from title (e.g., fn-1-add-oauth, fn-2-fix-login-bug)
- Tasks: `fn-N-slug.M` (e.g., fn-1-add-oauth.1, fn-2-fix-login-bug.2)

**Backwards compatibility**: Legacy formats `fn-N`, `fn-N-xxx`, `fn-N.M`, and `fn-N-xxx.M` still work.

## Common Commands

```bash
# List
.flow/bin/flowctl list                          # All specs + tasks grouped
.flow/bin/flowctl specs                         # All specs with progress
.flow/bin/flowctl tasks                         # All tasks
.flow/bin/flowctl tasks --spec fn-1-add-oauth   # Tasks for spec
.flow/bin/flowctl tasks --status todo           # Filter by status

# View
.flow/bin/flowctl show fn-1-add-oauth           # Spec with all tasks
.flow/bin/flowctl show fn-1-add-oauth.2         # Single task
.flow/bin/flowctl cat fn-1-add-oauth            # Spec markdown
.flow/bin/flowctl cat fn-1-add-oauth.2          # Task spec (markdown)

# State
.flow/bin/flowctl status                        # .flow state + active Ralph runs
.flow/bin/flowctl ready --spec fn-1-add-oauth   # Tasks ready to work on
.flow/bin/flowctl validate --all                # Check structure
.flow/bin/flowctl state-path                    # Show state directory (for worktrees)

# Spec lifecycle
.flow/bin/flowctl spec create --title "..."                    # Create new spec
.flow/bin/flowctl spec set-plan fn-1-add-oauth --file plan.md  # Replace spec markdown
.flow/bin/flowctl spec set-title fn-1-add-oauth --title "..."  # Rename (updates slug)
.flow/bin/flowctl spec set-branch fn-1-add-oauth --branch ...  # Set branch name
.flow/bin/flowctl spec close fn-1-add-oauth                    # Close spec
.flow/bin/flowctl spec ready fn-1-add-oauth                    # Mark ready for execution (human gate; idempotent)
.flow/bin/flowctl spec unready fn-1-add-oauth                  # Clear ready flag (idempotent)
.flow/bin/flowctl spec skeleton                                # Print fresh-spec scaffold

# Task lifecycle
.flow/bin/flowctl task create --spec fn-1-add-oauth --title "..."
.flow/bin/flowctl task create --spec fn-1-add-oauth --title "..." --deps fn-1-add-oauth.1,fn-1-add-oauth.2
.flow/bin/flowctl task set-description <id> --description-file desc.md
.flow/bin/flowctl task set-acceptance <id> --acceptance-file accept.md
.flow/bin/flowctl task set-spec <id> --file spec.md            # Full task spec from file
.flow/bin/flowctl task reset <id>                              # Reset to todo (cascading: --cascade)

# Dependencies
.flow/bin/flowctl task set-deps fn-1-add-oauth.3 --deps fn-1-add-oauth.1,fn-1-add-oauth.2
.flow/bin/flowctl dep add fn-1-add-oauth.3 fn-1-add-oauth.1
.flow/bin/flowctl spec add-dep fn-1-add-oauth --dep fn-2
.flow/bin/flowctl spec rm-dep fn-1-add-oauth --dep fn-2

# Work
.flow/bin/flowctl start fn-1-add-oauth.2        # Claim task
.flow/bin/flowctl done fn-1-add-oauth.2 --summary-file s.md --evidence-json e.json
.flow/bin/flowctl block fn-1-add-oauth.2 --reason-file reason.md   # Block task with reason

# Spec cognitive-aid export (used by /flow-next:make-pr, v0.42.0+)
.flow/bin/flowctl spec export-cognitive-aid fn-1-add-oauth                  # text mode summary
.flow/bin/flowctl spec export-cognitive-aid fn-1-add-oauth --json           # full structured payload
.flow/bin/flowctl spec export-cognitive-aid fn-1-add-oauth --base main      # diff against base ref
.flow/bin/flowctl spec export-cognitive-aid fn-1-add-oauth --section coverage --json  # one section only

# Prospect (ideation artifacts under .flow/prospects/, v0.36.0+)
.flow/bin/flowctl prospect list                          # active artifacts (<30d)
.flow/bin/flowctl prospect list --all --json             # everything
.flow/bin/flowctl prospect read <id>                     # full body
.flow/bin/flowctl prospect read <id> --section survivors # focus|grounding|survivors|rejected
.flow/bin/flowctl prospect promote <id> --idea N         # idea N → new spec
.flow/bin/flowctl prospect promote <id> --idea N --force # override idempotency guard
.flow/bin/flowctl prospect archive <id>                  # → .flow/prospects/_archive/

# Tracker sync (project a spec to a Linear/GitHub/GitLab/Jira issue — /flow-next:tracker-sync bridge)
# NOTE: /flow-next:tracker-sync (external tracker bridge) is NOT /flow-next:sync (plan-sync of downstream task specs).
.flow/bin/flowctl sync active                            # is the bridge active? (enabled OR type ∈ {linear,github,gitlab,jira})
.flow/bin/flowctl sync get-state <spec-id>               # per-spec tracker state (id/identifier/url/lastSyncedAt/merge-base)
.flow/bin/flowctl sync set-tracker-id <spec-id> <uuid> --identifier WOR-17 --url <url>   # link (flow-first alias)
.flow/bin/flowctl sync set-last-synced <spec-id>         # advance lastSyncedAt (default: now)
.flow/bin/flowctl sync set-merge-base <spec-id> --flow-file f.md --tracker-file t.md     # paired snapshot (both required)
.flow/bin/flowctl sync clear <spec-id>                   # unlink, wipe state atomically
.flow/bin/flowctl sync list-unsynced                     # specs with no tracker id (need first push)
.flow/bin/flowctl sync list-stale --older-than-hours 24  # linked specs with old/missing lastSyncedAt
.flow/bin/flowctl sync check-collisions                  # tracker UUIDs shared by >1 spec
.flow/bin/flowctl sync receipt <spec-id> --status pushed --transport mcp --event work.firstClaim   # proof-of-work, event-tagged (status enum: pushed|pulled|merged|updated|diverged|queued|errored|noop)
.flow/bin/flowctl sync check <spec-id> --events work.firstClaim,work.done --since <iso>   # read-only audit: OK/MISSING per triggered touchpoint (bridge inactive → silent exit)
.flow/bin/flowctl sync defer <spec-id> --summary "..."   # queue a genuine conflict (never blocks; → review-deferred sink)
# Tracker-first spec (keyed by the tracker identifier instead of fn-NN):
.flow/bin/flowctl spec create --title "..." --tracker-first --tracker-identifier WOR-17  # canonical wor-17-slug

# Memory (categorized learnings under .flow/memory/, v0.33.0+)
.flow/bin/flowctl memory list                            # default: --status active
.flow/bin/flowctl memory list --status stale             # stale entries only
.flow/bin/flowctl memory search <query>                  # default: --status active
.flow/bin/flowctl memory search <query> --status all     # active + stale
.flow/bin/flowctl memory read <id>                       # full entry
.flow/bin/flowctl memory mark-stale <id> --reason "..."  # flag stale (v0.37.0+)
.flow/bin/flowctl memory mark-fresh <id>                 # clear stale flag (v0.37.0+)
.flow/bin/flowctl memory list-legacy                     # list legacy entries with mechanical defaults (v0.37.0+)
.flow/bin/flowctl memory list-legacy --json              # used by /flow-next:memory-migrate skill
.flow/bin/flowctl memory migrate [--yes] [--json]        # deterministic-only legacy migration (use /flow-next:memory-migrate for agent-native classification)

# Glossary (project-canonical terms at repo root, v0.39.0+ — survives `rm -rf .flow/`)
.flow/bin/flowctl glossary add <term> --definition "..."           # upsert single-line term
.flow/bin/flowctl glossary add <term> --definition-file body.md    # multi-line definition from file
.flow/bin/flowctl glossary add <term> --definition-file -          # multi-line from stdin
.flow/bin/flowctl glossary add <term> --avoid "alt1,alt2" --relates-to "x,y"
.flow/bin/flowctl glossary list                                    # text mode: grouped by file (nearest first)
.flow/bin/flowctl glossary list --json                             # {groups, file_count, total_terms}
.flow/bin/flowctl glossary read <term>                             # nearest-ancestor walk; first match wins
.flow/bin/flowctl glossary read <term> --json                      # {path, term, definition, avoid, relates_to}
.flow/bin/flowctl glossary remove <term>                           # last-term remove leaves `# Glossary` husk (R18)

# Strategy (project-canonical strategic intent at repo root, v0.40.0+ — survives `rm -rf .flow/`)
.flow/bin/flowctl strategy status                                  # text mode: husk / sections_filled / total_sections / last_updated
.flow/bin/flowctl strategy status --json                           # {exists, husk, sections_filled, total_sections, last_updated, file_path}
.flow/bin/flowctl strategy read                                    # full STRATEGY.md (single-root walk from cwd up to repo root)
.flow/bin/flowctl strategy read --section approach                 # one section only (target_problem / approach / personas / metrics / tracks / milestones / not_working_on)
.flow/bin/flowctl strategy read --json                             # {path, name, last_updated, target_problem, approach, personas, metrics, tracks, milestones, not_working_on}
.flow/bin/flowctl strategy list --json                             # {groups, file_count, total_sections} — parallel to glossary list

# /flow-next:strategy skill writes STRATEGY.md directly (no flowctl strategy add — too prose-heavy for atomic CLI).

# Config (per-project knobs in .flow/config.json — see /flow-next:setup for guided setup)
.flow/bin/flowctl config get review.backend                        # rp|codex|copilot|cursor|none, or spec form like codex:gpt-5.4:high / cursor:gpt-5.5-high
.flow/bin/flowctl config get review.backend --raw --json           # bypass merged defaults (null = absent from file)
.flow/bin/flowctl config set review.backend codex                  # bare backend
.flow/bin/flowctl config set review.backend codex:gpt-5.4:high     # full spec (backend:model:effort)
.flow/bin/flowctl config set memory.enabled true                   # auto-capture from NEEDS_WORK reviews
.flow/bin/flowctl config set planSync.enabled true                 # sync downstream task specs after impl drift
.flow/bin/flowctl config set planSync.crossSpec false              # also check other open specs (canonical key; legacy alias planSync.crossEpic removed in 2.0)
.flow/bin/flowctl config set scouts.github false                   # GitHub scout (requires gh CLI)
.flow/bin/flowctl config set artifacts.html.enabled true           # optional HTML artifact mode: skills render specs/PRs as self-contained HTML under .flow/artifacts/<spec-id>/ (OFF by default; markdown stays the source of truth)
.flow/bin/flowctl config set work.delegate codex                   # /flow-next:work opt-in: offload impl to local `codex exec` (value MUST be `codex` to activate; OFF by default, consent-gated; arg `delegate:codex` overrides per-run)
.flow/bin/flowctl config set tracker.perEvent.qa comment           # /flow-next:qa opt-in: post the live-app QA ship verdict as a tracker comment (off|comment; default off; needs the tracker bridge active)

# Per-spec / per-task backend overrides (override the global review.backend per workstream)
.flow/bin/flowctl spec set-backend fn-1-add-oauth --review codex:gpt-5.4:high
.flow/bin/flowctl task set-backend fn-1-add-oauth.3 --impl copilot:claude-opus-4.5
.flow/bin/flowctl task show-backend fn-1-add-oauth.3                # effective specs (task + spec levels merged)
.flow/bin/flowctl review-backend                                    # show backend that would run now (ASK if unset)

# Checkpoint (save/restore spec state — useful before destructive edits)
.flow/bin/flowctl checkpoint save fn-1-add-oauth                    # snapshot spec + tasks
.flow/bin/flowctl checkpoint restore fn-1-add-oauth                 # restore from snapshot
.flow/bin/flowctl checkpoint delete fn-1-add-oauth                  # delete snapshot

# Ralph (autonomous mode run control — for /flow-next:ralph-init users)
.flow/bin/flowctl ralph status                                      # current run state
.flow/bin/flowctl ralph pause                                       # pause running loop
.flow/bin/flowctl ralph resume                                      # resume paused loop
.flow/bin/flowctl ralph stop                                        # request stop after current iteration
```

## Orchestration & model steering

flow-next skills are prompts the host agent executes — so you (the host) can route work across model families with zero code. **Defaults are pre-tuned; none of this is required** — reach for it only when your model mix, subscriptions, or taste differ. Full guide: [`docs/orchestration.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/orchestration.md) · https://flow-next.dev/orchestration/

**Headless CLI bridges** — drive another harness from a Bash call with a *self-contained* prompt (full context in, digest back). The delegate writes code and never touches git; no recursive delegation.

```bash
# codex exec DEFAULTS to a read-only sandbox. Redirect stdin from /dev/null —
# spawned by another agent it hangs indefinitely on inherited non-TTY stdin.
codex exec -s read-only "<self-contained investigation prompt>" </dev/null               # read-only investigation
codex exec --sandbox workspace-write -o out.md "<self-contained impl prompt>" </dev/null  # implement + capture result via -o/--output-last-message (never stdout scraping; --full-auto is deprecated)

# cursor-agent: -p print mode; --force actually APPLIES edits (else proposed-only).
CURSOR_API_KEY=... cursor-agent -p --force --model <id> "<prompt>"                        # model IDs are volatile → cursor-agent --list-models

# claude -p: the same bridge in REVERSE — drive Claude headlessly from a Codex/Cursor host.
claude -p "<self-contained prompt>" --output-format text --allowedTools "Read,Bash" </dev/null  # prompt BEFORE --allowedTools (variadic — it swallows trailing args); edits need --permission-mode acceptEdits

# grok -p: xAI's headless one-shot (grok CLI, v0.2.x alpha). Prints the response to stdout and exits.
grok -p "<self-contained prompt>" -m grok-4.5-high </dev/null                              # read-only-ish; add --always-approve (or --permission-mode acceptEdits) to let it act. -m/--model + --reasoning-effort; --json-schema for structured output. Grok 4.5 = fast + cheap first-draft; route to bulk/implementation, not UI or final taste-critical work.
```

Harness-relative: every direction works — from Claude Code the bridges are `codex exec` / `cursor-agent`; from Codex or Cursor they are `claude -p` / the other CLI. Any harness that can run Bash can conduct the others.

**flow-next shortcuts** — the same bridges, packaged as config:

```bash
# Delegate implementation to codex (host keeps gating/git/review; codex only writes code)
.flow/bin/flowctl config set work.delegate codex     # value MUST be `codex` to activate (OFF by default, consent-gated)
# …or per-run, no config:  /flow-next:work fn-1-add-oauth delegate:codex

# Cross-family review — the model that writes is never the model that reviews
.flow/bin/flowctl config set review.backend codex                                 # or cursor:composer-2.5
.flow/bin/flowctl task set-backend fn-1-add-oauth.3 --review cursor:composer-2.5   # per-task review: override
```

**Prompted orchestration** — describe the policy; the host judges per item, no parameter required:

```text
Work the ready specs — decide per spec by complexity: auth/migration tasks you
implement yourself; plain CRUD is delegated (delegate:codex). Reviews from codex either way.

Run /flow-next:work fn-12 with delegate:codex. If a task's review comes back
NEEDS_WORK twice, stop delegating it and implement it yourself on the session model.
```

None of these pairings are fixed — any stage of any flow-next pipeline (research, implementation, review, QA) can route to whatever harness you can reach from Bash: describe the arrangement in the invocation or your instruction files and the host builds it.

Make any of this durable by writing it into `CLAUDE.md`/`AGENTS.md` — the host reads your instruction files every session and flow-next skills inherit them automatically.

## Workflow

1. `.flow/bin/flowctl specs` - list all specs
2. `.flow/bin/flowctl ready --spec fn-N-slug` - find available tasks
3. `.flow/bin/flowctl start fn-N-slug.M` - claim task
4. Implement the task
5. `.flow/bin/flowctl done fn-N-slug.M --summary-file ... --evidence-json ...` - complete

## Evidence JSON Format

```json
{"commits": ["abc123"], "tests": ["npm test"], "prs": []}
```

## Parallel Worktrees

Runtime state (status, assignee, etc.) is stored in `.git/flow-state/`, shared across worktrees:

```bash
.flow/bin/flowctl state-path              # Show state directory
.flow/bin/flowctl migrate-state           # Migrate existing repo
.flow/bin/flowctl migrate-state --clean   # Migrate + remove runtime from tracked files
```

Migration is optional — existing repos work without changes.

## Deprecation: legacy `flowctl epic *` aliases

flow-next 1.0.0 renamed the spec surface from `epic` to `spec`. The legacy `flowctl epic *` subcommands continue to work in 1.x as thin aliases that dispatch to the new `flowctl spec *` handlers; each invocation emits a one-line stderr deprecation warning. Suppress via `FLOW_NO_DEPRECATION=1`. Aliases are removed in 2.0.

A pre-1.0 `.flow/` directory keeps working via the alias layer (no auto-migration). To migrate to the canonical 1.0+ layout, run either:

- `/flow-next:setup` (interactive, prompts before writing) — recommended in human-driven sessions.
- `flowctl migrate-rename --yes` (deterministic) — recommended for scripts and CI.

`FLOW_NO_AUTO_MIGRATE=1` suppresses the migration banner entirely; alias mode keeps working.

## More Info

- Human docs: https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/flowctl.md
- CLI reference: `.flow/bin/flowctl --help`
