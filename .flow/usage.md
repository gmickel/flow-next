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
├── specs/fn-N-slug.md           # Spec content (canonical)
├── specs/fn-N-slug.json         # Spec metadata (1.0+ — colocated with the markdown)
├── tasks/fn-N-slug.M.json       # Task metadata (e.g., fn-1-add-oauth.1.json)
├── tasks/fn-N-slug.M.md         # Task specifications
├── memory/                      # Context memory (categorized bug/ + knowledge/)
├── prospects/<slug>-<date>.md   # Ideation artifacts (v0.36.0+)
├── .flow_version                # 1.0.0 sentinel — written after layout migration
├── .gitignore                   # Auto-managed by flowctl (1.0+) — excludes migration transients
└── meta.json                    # Project metadata
```

`.flow/epics/` is the pre-1.0 sidecar location. Repos created on 1.0+ never have it; pre-1.0 repos keep working via the alias layer until you run `flowctl migrate-rename --yes` (or `/flow-next:setup`'s upgrade branch).

`.flow/.gitignore` is auto-written by `flowctl init` and `flowctl migrate-rename` so `git add -A` doesn't accidentally commit per-developer state (`.checkpoint-*.json`, `receipts/`, `tmp/`) or migration transients (`.backup-pre-1.0/`, `.banner-acknowledged`, `.migrating`, `.migration-manifest`). Idempotent; user patterns added below the auto-managed footer are preserved on update.

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

# Status
.flow/bin/flowctl ready --spec fn-1-add-oauth   # What's ready to work on
.flow/bin/flowctl validate --all                # Check structure
.flow/bin/flowctl state-path                    # Show state directory (for worktrees)

# Create
.flow/bin/flowctl spec create --title "..."
.flow/bin/flowctl task create --spec fn-1-add-oauth --title "..."
.flow/bin/flowctl task create --spec fn-1-add-oauth --title "..." --deps fn-1-add-oauth.1,fn-1-add-oauth.2

# Dependencies
.flow/bin/flowctl task set-deps fn-1-add-oauth.3 --deps fn-1-add-oauth.1,fn-1-add-oauth.2
.flow/bin/flowctl dep add fn-1-add-oauth.3 fn-1-add-oauth.1

# Work
.flow/bin/flowctl start fn-1-add-oauth.2        # Claim task
.flow/bin/flowctl done fn-1-add-oauth.2 --summary-file s.md --evidence-json e.json

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
```

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
