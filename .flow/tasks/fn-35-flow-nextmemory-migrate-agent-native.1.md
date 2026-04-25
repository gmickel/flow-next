---
satisfies: [R1, R2, R3, R4, R5, R10, R11]
---

## Description

Create the `/flow-next:memory-migrate` skill — markdown files describing the workflow the host agent (Claude / Codex / Droid) executes when the user invokes the slash command. Mirrors fn-34's `flow-next-audit/` skill shape exactly. No code, just instructions.

This is the skill-side of fn-35. Task 2 lands the flowctl plumbing the skill calls (`list-legacy`, deprecated migrate). Task 3 lands docs + the fn-34 audit warning update.

**Size:** S → M (mostly markdown; M because it covers idempotency + self-ignoring backup dir patterns)
**Files:**
- `plugins/flow-next/skills/flow-next-memory-migrate/SKILL.md` (new)
- `plugins/flow-next/skills/flow-next-memory-migrate/workflow.md` (new)
- `plugins/flow-next/skills/flow-next-memory-migrate/phases.md` (new)
- `plugins/flow-next/commands/flow-next/memory-migrate.md` (new — slash command pass-through)

## Approach

### `SKILL.md` shape

Mirror `plugins/flow-next/skills/flow-next-audit/SKILL.md` exactly. Frontmatter:
- `name: flow-next-memory-migrate`
- `description: <one paragraph>` — trigger phrases ("migrate memory", "convert legacy memory", "/flow-next:memory-migrate", "lift pitfalls into categorized schema"); arg syntax (`mode:autofix` token + optional scope)
- Same `user-invocable: false`, `allowed-tools` list as fn-34 (`AskUserQuestion`, `Read`, `Bash`, `Grep`, `Glob`, `Write`, `Edit`, `Task`)

Body sections:
1. **What this is** — agent classifies legacy entries; no codex/copilot subprocess; flowctl provides parsing + writing only
2. **Mode Detection** — `mode:autofix` strips from args; remainder is scope hint (e.g., `mode:autofix pitfalls.md` → autofix on just pitfalls.md)
3. **Inline skill (no `context: fork`)** — same rationale as fn-34; AskUserQuestion + blocking-question tools must stay reachable
4. **Pre-check** — setup-version banner (lifted from fn-34 SKILL.md:80-94)
5. **Reference workflow.md + phases.md**

### `workflow.md` shape

Document the 5 phases. Each phase ends with "Done when" criterion.

**Phase 0 — Detect & enumerate**
- Run `flowctl memory list-legacy --json` (Task 2 ships this)
- Output shape: `{filename: "pitfalls.md", entries: [{title, body, tags, date, mechanical_track, mechanical_category}]}`
- If no legacy files: report "No legacy files to migrate." and exit cleanly
- Show user a triage summary (interactive) or proceed (autofix): "Found N entries across M files. Migrating now..."

**Phase 1 — Classify (one entry per tool call)**
- Iterate per-entry. **Do not batch-classify in single prompt** — risks silent skips under context pressure (practice-scout flagged).
- For each entry:
  - Read its title + body + filename context
  - Default to mechanical (track, category) from `list-legacy` output
  - Override only if context warrants (e.g., entry titled "race condition in worker" was mechanically mapped to `bug/general` based on `pitfalls.md`; agent might override to `bug/runtime-errors`)
  - Log every override decision with rationale (for end-of-run report)
- Ambiguous → ask via `AskUserQuestion` / `request_user_input` / `ask_user` (interactive); pick mechanical default + log "needs-review" (autofix)
- Validate (track, category) against schema — pin valid set in skill prompt; `flowctl memory add` validates again via `validate_memory_frontmatter`

**Phase 2 — Write categorized entries**
- For each classified entry, invoke `flowctl memory add --track <t> --category <c> --title "<t>" --body-file <tmpfile>`
- Slug uniqueness handled by existing helper (`-2`/`-3` suffix on collision)
- Capture entry id from JSON output for the final report

**Phase 3 — Verify + Report**
- Re-read all newly created entries to confirm round-trip (via `flowctl memory read <id>`)
- Print summary:
  - `N legacy files processed`
  - `M entries migrated successfully`
  - `K skipped (already migrated)`
  - `P overrides (mechanical → agent-decided)`
  - `Q needs-review` (autofix only)
- For interactive mode, this is the moment to confirm before Phase 4

**Phase 4 — Optional cleanup**
- Ask user (interactive) or default-decline (autofix): rename original flat files to `.flow/memory/_migrated/<filename>.bak` for traceability
- On first cleanup write `.flow/memory/_migrated/.gitignore` containing `*` (self-ignoring directory pattern)
- NEVER auto-delete legacy files — rename only

### `phases.md` shape

Lookup table for the (track, category) decision tree. Lift heavily from the existing `_memory_classify_mechanical` map (the deterministic baseline) plus narrative guidance for when to override.

Sections:
- **Mechanical baseline** — table mapping legacy filename → default (track, category):
  - `pitfalls.md` → `bug/general`
  - `conventions.md` → `knowledge/conventions`
  - `decisions.md` → `knowledge/decisions`
- **When to override** — concrete examples:
  - Entry title contains "race condition" / "deadlock" / "leak" → `bug/runtime-errors`
  - Entry references build/CI failures → `bug/build-failures`
  - Entry recommends use of specific tooling (e.g., "use pnpm not npm") → `knowledge/tooling`
  - Entry documents architectural decision → `knowledge/decisions`
  - When in doubt → mechanical default
- **Idempotency rules** — how the skill checks `_migrated/` for already-migrated files

### `commands/flow-next/memory-migrate.md`

Minimal slash-command pass-through. Mirror `commands/flow-next/audit.md` shape exactly. Frontmatter (`name`, `description`, `argument-hint`), body invokes the skill with `$ARGUMENTS`.

### Idempotency strategy (R10)

Phase 0 checks for `.flow/memory/_migrated/<filename>.bak` before reading the legacy file. If backup exists for a given legacy filename, skip it and log "already migrated". This is the cleanest idempotency check — cheaper than diffing against existing categorized entries.

### Self-ignoring `_migrated/` directory (R11)

Phase 4 writes `.flow/memory/_migrated/.gitignore` with content `*` on first cleanup. This is the standard "self-ignoring directory" pattern (used by `node_modules`, `__pycache__` tooling). Avoids requiring users to update top-level `.gitignore`. Only needed once — subsequent migrations skip if the gitignore already exists.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` — frontmatter + mode detection + pre-check + interaction principles to mirror
- `plugins/flow-next/skills/flow-next-audit/workflow.md` — phase shape + "Done when" pattern
- `plugins/flow-next/skills/flow-next-audit/phases.md` — outcome lookup style
- `plugins/flow-next/commands/flow-next/audit.md` — slash command pass-through pattern
- `plugins/flow-next/scripts/flowctl.py:6390-6400` — `_memory_classify_mechanical` (the mechanical baseline our skill defaults to)
- `plugins/flow-next/scripts/flowctl.py:6359-6387` — `_memory_parse_legacy_entries` (output shape that `list-legacy --json` will wrap)

**Optional:**
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` — additional skill reference for shape
- `/tmp/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound-refresh/SKILL.md` — upstream reference (different feature but similar agent-native pattern)

## Key context

- Skill files are markdown — no Python, no shell, no testing. The "test" is invoking the skill in a real session.
- Mode detection MUST live in SKILL.md so the host agent finds it on first read.
- The slash command file is just the trigger — actual workflow lives in `skills/flow-next-memory-migrate/`.
- Don't invent new flowctl subcommands beyond what Task 2 will provide (`list-legacy`). Phase 2 uses existing `flowctl memory add`.
- Phase 1's "one entry per tool call" rule is critical — agents under context pressure batch-classify in-prompt and silently skip entries (practice-scout flagged this as a real failure mode).
- `AskUserQuestion` schema may not be loaded — call `ToolSearch` with `select:AskUserQuestion` if needed (per fn-34 pattern).

## Acceptance

- [ ] `plugins/flow-next/skills/flow-next-memory-migrate/SKILL.md` exists with valid frontmatter (`name`, `description`, `user-invocable: false`, `allowed-tools`), mode detection (`mode:autofix` parsing), interaction principles, FLOWCTL var fallback, pre-check banner.
- [ ] `plugins/flow-next/skills/flow-next-memory-migrate/workflow.md` documents Phases 0–4 with "Done when" per phase. Phase 1 explicitly enforces "one entry per tool call".
- [ ] `plugins/flow-next/skills/flow-next-memory-migrate/phases.md` documents mechanical baseline (legacy filename → default track/category) + override examples + idempotency rules.
- [ ] `plugins/flow-next/commands/flow-next/memory-migrate.md` exists, invokes the skill with `$ARGUMENTS`, mirrors audit command shape.
- [ ] Skill references `flowctl memory list-legacy --json` (Task 2's deliverable) — forward-looking reference.
- [ ] Skill references `flowctl memory add` for Phase 2 writes — uses existing helper unchanged.
- [ ] Phase 4 cleanup logic documents self-ignoring `.flow/memory/_migrated/.gitignore` pattern with content `*`.
- [ ] Idempotency check (Phase 0) documents skip-if-`_migrated/<filename>.bak`-exists logic.
- [ ] No code in the skill files. Markdown only. No Python, no bash beyond illustrative snippets in workflow descriptions.
- [ ] Cross-platform subagent dispatch documented (Claude `Agent`/`Task`, Codex `spawn_agent`, Droid equivalent) — though this skill is mostly main-thread (each entry is a tool call, no parallel investigation needed).


## Done summary

(populated when task completes)

## Evidence

(populated when task completes)
