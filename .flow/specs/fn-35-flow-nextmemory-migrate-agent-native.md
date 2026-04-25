# /flow-next:memory-migrate — agent-native legacy migration

## Overview

`flowctl memory migrate` (shipped in fn-30, v0.33.0) converts pre-fn-30 flat memory files (`.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md`) into the categorized YAML schema. It dispatches `codex` or `copilot` via subprocess to classify each entry into the right `(track, category)` pair.

**This is the same architectural mistake as fn-34's original design.** `flowctl memory migrate` is invoked from inside an agentic environment (Claude Code / Codex / Droid). The host agent could classify each entry directly using its own intelligence — there's no need to spawn a second LLM via subprocess.

This epic refactors migrate to a skill-based design, mirroring the fix landed in fn-34.

**Architecture target:**
- New skill `/flow-next:memory-migrate` — host agent reads each legacy entry, classifies it, writes categorized form
- `flowctl memory migrate --no-llm` keeps the deterministic mechanical path (filename → `(track, category)` heuristic) for genuinely headless invocations (CI, scripts, cron without an agent in the loop)
- Drop `_memory_classify_run_codex` / `_memory_classify_run_copilot` / `_memory_classify_select_backend` / `_memory_classify_build_prompt` / `_memory_classify_parse_response` / `_memory_classify_entry` — the entire subprocess-dispatch chain in flowctl.py:6221-6535
- `flowctl memory migrate` (no flags) becomes mechanical-mode by default, with a deprecation hint pointing to `/flow-next:memory-migrate`

This epic is a **minor bump (0.37.0 → 0.38.0)** because it removes a subprocess-dispatch code path (back-compat-breaking for any external scripts that pinned on `_memory_classify_*` symbols, though none exist outside this repo).

## Architecture (agent-native)

```
User: /flow-next:memory-migrate          (or auto-suggested by /flow-next:audit when legacy files detected)
         │
         ▼
    Skill workflow runs in host agent
         │
         ├─ Phase 0: Detect legacy files
         │     same as flowctl memory migrate's current step 1
         │
         ├─ Phase 1: Parse entries
         │     reuse existing _memory_parse_legacy_entries via flowctl helper:
         │     `flowctl memory list-legacy --json` returns parsed segments
         │
         ├─ Phase 2: Classify (host agent — no subprocess)
         │     For each entry: agent reads title + body + filename context,
         │     decides (track, category). Uses its own intelligence.
         │     For ambiguous: ask via blocking-question tool (interactive)
         │     or pick most confident option (autofix).
         │
         ├─ Phase 3: Write categorized entries
         │     `flowctl memory add --track ... --category ... --title ... --body-file ...`
         │     for each, respecting slug uniqueness and date stamping.
         │
         ├─ Phase 4: Verify + Report
         │     Re-read all newly created entries to confirm round-trip.
         │     Print: N legacy files processed, M entries migrated, K skipped.
         │
         └─ Phase 5: Optional cleanup
             Ask (interactive) or default-decline (autofix): rename original
             flat files to `.flow/memory/_migrated/<filename>.bak` for
             traceability. NEVER auto-delete.
```

**flowctl plumbing simplification:**
- New: `flowctl memory list-legacy --json` — emits parsed segments (uses existing `_memory_parse_legacy_entries`) without classification. Skill consumes this.
- Existing: `flowctl memory add` (write helper) — used as-is by the skill.
- Existing: `flowctl memory migrate --no-llm` — kept as the mechanical-only fallback. Filename → `(track, category)` regex map per `_memory_classify_mechanical`.
- Removed: `_memory_classify_*` subprocess chain (six functions, ~200 LoC) plus their import dependencies.
- Removed: `cmd_memory_migrate` LLM-dispatch branch (lines 6574-6613ish). `cmd_memory_migrate` becomes mechanical-only.

## Acceptance criteria (sketch — to be expanded by /flow-next:plan)

- **R1:** New skill `plugins/flow-next/skills/flow-next-memory-migrate/` with SKILL.md + workflow.md + phases (parse, classify, write, verify, cleanup).
- **R2:** Slash command `/flow-next:memory-migrate` registered.
- **R3:** New `flowctl memory list-legacy --json` subcommand (parses legacy files, emits structured entries; no classification).
- **R4:** Skill calls `list-legacy` to enumerate, then classifies via host agent's intelligence, then writes via `flowctl memory add`.
- **R5:** Interactive mode asks via blocking-question tool on ambiguous classifications.
- **R6:** Autofix mode picks most-confident classification per entry, marks low-confidence as needing review (logs to report, not to memory store).
- **R7:** `flowctl memory migrate` (no flags) becomes mechanical-mode default with a stderr hint suggesting `/flow-next:memory-migrate` for accurate classification.
- **R8:** `flowctl memory migrate --no-llm` continues to work unchanged (mechanical mode is the implementation, just default now).
- **R9:** Subprocess-dispatch chain removed: `_memory_classify_run_codex`, `_run_copilot`, `_select_backend`, `_build_prompt`, `_parse_response`, `_classify_entry`. Plus `_classify_mechanical` is preserved (used by the kept `--no-llm` path).
- **R10:** `/flow-next:audit` (fn-34) Phase 0 legacy-skip warning updated to recommend `/flow-next:memory-migrate` instead of `flowctl memory migrate`.
- **R11:** Smoke test: skill manually-invokable; `flowctl memory list-legacy` smoke covers parsing; `flowctl memory migrate --no-llm` smoke unchanged from fn-30.
- **R12:** Docs updated: CHANGELOG, README, CLAUDE.md, website. Note that subprocess dispatch was removed (architectural simplification).
- **R13:** Version bump 0.37.0 → 0.38.0 (subprocess removal + new skill = minor).

## Why now (and why not bundle into fn-34)

fn-34 specs the audit skill — itself a substantial scope (3 tasks). Bundling migrate refactor would balloon fn-34. Separate epic keeps each focused. fn-35 inherits the architectural decision from fn-34 (agent-native skill, thin flowctl plumbing) and applies the same fix to a parallel feature.

fn-35 should ship after fn-34 lands, since:
- fn-34's `/flow-next:audit` skill structure becomes the template for fn-35's `/flow-next:memory-migrate`
- fn-34 establishes precedent for `mark-stale`/`mark-fresh` thin helpers; fn-35's `list-legacy` follows the same shape

## Tasks

To be broken out via `/flow-next:plan fn-35-flow-nextmemory-migrate-agent-native` once fn-34 ships. Anticipated breakdown: ~3 tasks (skill files, flowctl plumbing simplification + `list-legacy`, smoke + docs + version bump).

## Boundaries

- Not changing the categorized memory schema (no frontmatter changes).
- Not changing `cmd_memory_add` or `_memory_iter_entries` (already correct).
- Not changing the mechanical filename → `(track, category)` map (preserved as `--no-llm` path).
- Not silently deleting legacy flat files. Optional rename to `_migrated/` with user confirmation.

## Decision context

**Why a skill instead of keeping subprocess dispatch?** The subprocess pattern made sense for use cases where flowctl is invoked headlessly (no host agent in the loop). But `flowctl memory migrate` is always invoked from inside Claude Code / Codex / Droid — the user upgrades flow-next, the host agent runs the migration. Spawning a second agent is wasteful (cost + latency + ~200 LoC of subprocess plumbing + classifier prompt + response parser + backend selection). The host agent already has the intelligence to classify entries.

**Why keep `--no-llm` mechanical mode?** Two real use cases: (a) automation that runs flowctl from scripts without an agent in the loop (rare but exists), (b) users on locked-down systems with no codex/copilot available. The mechanical path is ~50 LoC and well-tested; keeping it costs nothing.

**Why deprecate the LLM-dispatch path entirely (not maintain both)?** Maintaining two intelligence paths doubles the test surface and creates "which one fired?" debugging questions. The skill path is strictly better when a host agent is present (which is always, when invoked from a slash command). The mechanical fallback is the "no agent available" path. Two clean modes; no overlap.

## Follow-ups (not in this epic)

- Audit other places in flowctl.py that use codex/copilot subprocess dispatch and evaluate whether they should also become skill-based. Candidates: review-backend invocations (probably stay as subprocess — those are the review intelligence, separate from the host agent), `triage-skip` LLM judge under `FLOW_TRIAGE_LLM=1` (Ralph-mode optimization, runs in autonomous loop — keep subprocess), any other hidden classifier dispatch.

## Status

Drafted. Ready for `/flow-next:plan fn-35-flow-nextmemory-migrate-agent-native` once fn-34 ships.
