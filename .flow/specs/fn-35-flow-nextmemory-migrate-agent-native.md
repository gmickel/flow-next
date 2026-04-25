# /flow-next:memory-migrate — agent-native legacy migration

## Overview

`flowctl memory migrate` (shipped in fn-30, v0.33.0) converts pre-fn-30 flat memory files (`.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md`) into the categorized YAML schema. It dispatches `codex` or `copilot` via subprocess to classify each entry into the right `(track, category)` pair.

**This is the same architectural mistake fn-34 fixed for the audit feature.** `flowctl memory migrate` is invoked from inside an agentic environment (Claude Code / Codex / Droid). The host agent could classify each entry directly using its own intelligence — there's no need to spawn a second LLM via subprocess.

This epic refactors migrate to a skill-based design, mirroring fn-34. **Bundled into the same release as fn-34 (v0.37.0)** — no separate version bump, single CHANGELOG entry covering both.

**Architecture target:**
- New skill `/flow-next:memory-migrate` — host agent reads each legacy entry, classifies it, writes categorized form
- New `flowctl memory list-legacy --json` — emits parsed segments with mechanical defaults; skill consumes
- `flowctl memory migrate` becomes deterministic-only (mechanical mode, default behavior); stderr deprecation hint points at `/flow-next:memory-migrate` for accurate classification
- Drop `_memory_classify_*` subprocess chain (six functions, ~225 LoC at flowctl.py:6403-6627)
- Drop `FLOW_MEMORY_CLASSIFIER_BACKEND` / `_MODEL` / `_EFFORT` env vars (only used by removed dispatch chain)
- Keep `_memory_classify_mechanical` (6390-6400) — the deterministic filename → `(track, category)` heuristic
- Keep `_memory_parse_legacy_entries` (6359-6387) — wrapped by `list-legacy --json`
- Keep `cmd_memory_migrate` `--no-llm` flag accepted-but-noop (avoids breaking scripted callers)

## Architecture (agent-native)

```
User: /flow-next:memory-migrate                  (interactive default)
       /flow-next:memory-migrate mode:autofix    (autofix mode)
         │
         ▼
    Skill workflow runs in host agent
         │
         ├─ Phase 0: Detect & enumerate legacy files
         │     `flowctl memory list-legacy --json` returns parsed segments
         │     with mechanical default (track, category) per entry — agent
         │     overrides only when context warrants
         │
         ├─ Phase 1: Classify (host agent — no subprocess)
         │     Iterate one entry per tool call (no batch-classify in-prompt
         │     — risks silent skips under context pressure).
         │     For each: read title + body + filename context, decide
         │     (track, category). Use mechanical default unless evidence
         │     warrants override (log overrides for receipt).
         │     For ambiguous: ask via blocking-question tool (interactive)
         │     or pick mechanical default (autofix), log as "needs-review".
         │
         ├─ Phase 2: Write categorized entries
         │     `flowctl memory add --track ... --category ... --title ...`
         │     for each. Slug uniqueness handled by existing helper.
         │
         ├─ Phase 3: Verify + Report
         │     Re-read all newly created entries.
         │     Print: N legacy files, M entries migrated, K skipped,
         │     P overrides (mechanical→agent-decided differences).
         │
         └─ Phase 4: Optional cleanup
             Ask (interactive) or default-decline (autofix): rename original
             flat files to `.flow/memory/_migrated/<filename>.bak` for
             traceability. Self-ignoring directory pattern: write a
             `.gitignore: *` file on first cleanup. NEVER auto-delete.
```

**flowctl plumbing simplification:**
- New: `flowctl memory list-legacy [--json]` — wraps `_memory_parse_legacy_entries` per file in `MEMORY_LEGACY_FILES`. Each entry includes `mechanical_track` / `mechanical_category` from `_memory_classify_mechanical(filename)` so the agent has a sane default to override.
- Existing (used as-is): `flowctl memory add` (categorized write), `_memory_classify_mechanical` (filename heuristic).
- Simplified: `cmd_memory_migrate` collapses ~250 LoC to mechanical-only path. Keeps `method`/`model` JSON receipt fields (always `"mechanical"` / `null`) for backcompat per CLAUDE.md memory-system additive-schema rule.
- Removed: `_memory_classify_run_codex` (6468-6508), `_memory_classify_run_copilot` (6511-6561), `_memory_classify_select_backend` (6564-6587), `_memory_classify_build_prompt` (6403-6437), `_memory_classify_parse_response` (6440-6465), `_memory_classify_entry` (6590-6627). ~225 LoC dropped.

**Deprecation hint** on `flowctl memory migrate` (no flags or with `--no-llm`):
```
[DEPRECATED] Subprocess-based classification removed. Now mechanical-only by default.
For agent-native classification, use: /flow-next:memory-migrate
```
Print to stderr once per process, only when `sys.stderr.isatty()` (don't pollute `--json` pipelines).

If `FLOW_MEMORY_CLASSIFIER_BACKEND` / `_MODEL` / `_EFFORT` are set in env, emit a separate one-time stderr warning so users with leftover env vars notice they're now dead.

## Acceptance criteria

- **R1:** New skill at `plugins/flow-next/skills/flow-next-memory-migrate/` with `SKILL.md`, `workflow.md`, `phases.md`. Mirrors fn-34's `flow-next-audit/` shape (frontmatter, mode detection, interaction principles, FLOWCTL var fallback, inline-skill rationale).
- **R2:** Slash command `/flow-next:memory-migrate` registered at `plugins/flow-next/commands/flow-next/memory-migrate.md` (minimal pass-through mirroring `commands/flow-next/audit.md`).
- **R3:** Skill workflow phases 0–4 documented with "Done when" criteria. Phase 1 enforces "one entry per tool call" (no batch classification in-prompt).
- **R4:** Skill iterates `flowctl memory list-legacy --json` output. For each entry, agent decides (track, category) using mechanical default + repo context. Writes via `flowctl memory add`.
- **R5:** Interactive mode asks via blocking-question tool on ambiguous classifications. Autofix mode picks mechanical default + logs as "needs-review" in report.
- **R6:** New `flowctl memory list-legacy [--json]` subcommand wraps `_memory_parse_legacy_entries` for each file in `MEMORY_LEGACY_FILES`. Output includes `mechanical_track` + `mechanical_category` per entry. Argparse entry slots alongside `p_memory_migrate` at line ~15904.
- **R7:** `_memory_classify_run_codex`, `_memory_classify_run_copilot`, `_memory_classify_select_backend`, `_memory_classify_build_prompt`, `_memory_classify_parse_response`, `_memory_classify_entry` removed from `flowctl.py:6403-6627`. `_memory_classify_mechanical` and `_memory_parse_legacy_entries` preserved.
- **R8:** `cmd_memory_migrate` collapsed to mechanical-only. JSON receipt shape preserves `method` (always `"mechanical"`) and `model` (always `null`) keys for backcompat. `--no-llm` flag accepted-but-noop (no removal — avoids breaking scripted callers).
- **R9:** Deprecation hint emitted once per process to stderr (only when TTY) when `flowctl memory migrate` runs without args. Separate one-time warning if `FLOW_MEMORY_CLASSIFIER_*` env vars are set (they're now dead).
- **R10:** Idempotency: re-running migrate on already-migrated files is safe. Skill checks `_migrated/<filename>.bak` presence before re-classifying — skips if backup exists. Existing slug-uniqueness handles within-run collisions.
- **R11:** Skill Phase 4 cleanup writes `.flow/memory/_migrated/.gitignore` containing `*` on first use (self-ignoring directory pattern). User-confirmed in interactive; default-declined in autofix.
- **R12:** fn-34's `/flow-next:audit` Phase 0 legacy-skip warning updated: workflow.md:67 + SKILL.md:119 strings change `Run \`flowctl memory migrate\` first` → `Run \`/flow-next:memory-migrate\` first (or \`flowctl memory migrate --yes\` for deterministic-only)`.
- **R13:** Smoke test: existing `smoke_test.sh:1927-1997` migrate block untouched (already uses `--no-llm` exclusively — still works post-collapse). New `flowctl memory list-legacy` smoke added covering: parse 2-entry pitfalls.md, mechanical defaults present, `--json` output shape. Hint-string assertion at smoke_test.sh:766 verified to still match the new deprecation hint.
- **R14:** Docs updated:
  - `CHANGELOG.md` — expand existing `[flow-next 0.37.0]` Added block (don't add new release block) with: `/flow-next:memory-migrate` skill, `flowctl memory list-legacy [--json]`, classifier dispatch removal, dropped env vars
  - `plugins/flow-next/README.md:1565-1581` — replace migrate description, add `list-legacy`, demote `flowctl memory migrate` to "automation/CI" subhead
  - `plugins/flow-next/README.md:1626` — add memory-migrate skill row to skills table
  - `CLAUDE.md:72` — replace migrate bullet
  - `CLAUDE.md:74` — update audit "(run memory migrate first)" reference
  - `CLAUDE.md:82` — update legacy-files persistence reference
  - `CLAUDE.md:143` — update fn-35 self-reference (currently "tracked as fn-35"; change to "shipped in 0.37.0")
  - `.flow/usage.md:76-83` — append memory-migrate skill + list-legacy subcommand
  - `~/work/mickel.tech/app/apps/flow-next/page.tsx:537` — replace "fast-model classifier" reference with deterministic + skill mention
- **R15:** `scripts/sync-codex.sh` regenerates `plugins/flow-next/codex/skills/flow-next-memory-migrate/`. (No version bump — bundled into 0.37.0 from fn-34's `bump.sh` run.)

## Why bundle into 0.37.0?

User intent: ship both fixes (fn-34 audit + fn-35 migrate) in one release as a clean architectural correction. Both are the same architectural fix applied to two parallel features. Single CHANGELOG entry, single tag, single PR — better signal-to-noise than two consecutive minor bumps. fn-34's `bump.sh` already landed 0.37.0; fn-35 piggybacks on the same version.

## Risks

| Risk | Mitigation |
|------|------------|
| Users with `FLOW_MEMORY_CLASSIFIER_*` env vars set get silent behavior change | One-time stderr warning at CLI entry surfacing the deprecation (R9) |
| Half-removed conditionals (`if backend == "codex"` legs) leave orphaned `elif backend == "none"` | Remove whole if/elif chain in `cmd_memory_migrate`; verify with grep on `backend` after edits |
| `--no-llm` flag becomes confusing (was the opt-out, now the default) | Keep accepted-but-noop; don't remove (avoids breaking scripted callers) |
| Skill batch-classifies in single prompt → silent skips on context pressure | Phase 1 enforces "one entry per tool call" iteration discipline |
| Agent hallucinates categories not in schema | Skill prompt pins valid set; `flowctl memory add` validates via existing `validate_memory_frontmatter` |
| Idempotency: re-running migrate creates duplicate categorized entries | Check `_migrated/<filename>.bak` presence first; skip if already migrated |
| `_migrated/` backups committed accidentally | Self-ignoring directory: write `.flow/memory/_migrated/.gitignore` with `*` on first cleanup |
| JSON receipt shape regression (`method`/`model` keys) | Preserve both keys; set to `"mechanical"` / `null` post-collapse (additive schema rule) |
| Smoke at `smoke_test.sh:766` references deprecation hint string | Verify assertion still passes; update hint wording if needed |

## Boundaries

- Not changing the categorized memory schema (no frontmatter changes).
- Not changing `cmd_memory_add` or `_memory_iter_entries` (already correct).
- Not changing the mechanical filename → `(track, category)` map (preserved as `--no-llm` path; surfaced via `list-legacy --json`).
- Not silently deleting legacy flat files. Optional rename to `_migrated/` with user confirmation in Phase 4.
- Not removing `--no-llm` argparse flag (kept accepted-but-noop for backcompat).
- Not bumping version (bundled into 0.37.0 from fn-34's bump).

## Decision context

**Why a skill instead of keeping subprocess dispatch?** The subprocess pattern made sense for headless invocation (no host agent). But `flowctl memory migrate` is always invoked from inside Claude Code / Codex / Droid — the user upgrades flow-next, the host agent runs the migration. Spawning a second agent is wasteful (cost + latency + ~225 LoC of subprocess plumbing + classifier prompt + response parser + backend selection). Host agent already has the intelligence + repo context.

**Why keep mechanical mode as the flowctl-side fallback?** Two real use cases: (a) automation that runs flowctl from scripts without an agent in the loop (rare but exists), (b) users on locked-down systems with no codex/copilot available who already use `--no-llm`. The mechanical path is ~50 LoC and well-tested; keeping it costs nothing.

**Why deprecate the LLM-dispatch path entirely (not maintain both)?** Two intelligence paths doubles test surface and creates "which one fired?" debugging questions. Skill path is strictly better when host agent is present (always, when invoked from a slash command). Mechanical fallback is the "no agent available" path. Two clean modes; no overlap.

**Why "one entry per tool call" in skill Phase 1?** Practice-scout flagged: agents under context pressure batch-classify in-prompt and silently skip entries. One-call-per-entry iteration discipline avoids this; also gives clean per-entry verdict logging.

**Why `_migrated/` self-ignoring directory pattern?** Standard pattern (used by `node_modules`, `__pycache__` tooling). Avoids accidental commits without requiring a top-level `.gitignore` change.

## Follow-ups (not in this epic)

- Audit other places in flowctl.py that use codex/copilot subprocess dispatch and evaluate. Candidates evaluated: review-backend invocations (stay as subprocess — review intelligence is a separate second-opinion LLM, distinct from the host agent), `triage-skip` LLM judge under `FLOW_TRIAGE_LLM=1` (Ralph-mode optimization in autonomous loop — keep subprocess; no host agent in autonomous Ralph). No remaining classifier-style dispatch identified for removal after fn-35.

## Tasks

Three tasks. Bundled into the same branch + PR as fn-34.

1. fn-35.1 — Skill files + slash command (`flow-next-memory-migrate/SKILL.md`, `workflow.md`, `phases.md` + `commands/flow-next/memory-migrate.md`)
2. fn-35.2 — flowctl plumbing: add `list-legacy [--json]` subcommand, drop `_memory_classify_*` subprocess chain (6 functions), collapse `cmd_memory_migrate` to mechanical-only with deprecation hint
3. fn-35.3 — Update fn-34 audit Phase 0 warnings + docs (CHANGELOG amend, README, CLAUDE.md, .flow/usage.md, website) + smoke for `list-legacy` + `sync-codex.sh` regen

## Requirement coverage

| Req | Description | Task(s) |
|-----|-------------|---------|
| R1, R2 | Skill files + slash command | fn-35.1 |
| R3, R4, R5 | Workflow phases + interactive/autofix modes | fn-35.1 |
| R6 | `list-legacy` subcommand | fn-35.2 |
| R7 | Subprocess chain removal | fn-35.2 |
| R8, R9 | Migrate collapse + deprecation hint | fn-35.2 |
| R10, R11 | Idempotency + self-ignoring backup dir (skill side) | fn-35.1 |
| R12 | fn-34 audit Phase 0 warning update | fn-35.3 |
| R13 | Smoke test for list-legacy | fn-35.3 |
| R14 | Docs updates (README, CLAUDE.md, CHANGELOG, website, usage) | fn-35.3 |
| R15 | Codex mirror sync | fn-35.3 |
