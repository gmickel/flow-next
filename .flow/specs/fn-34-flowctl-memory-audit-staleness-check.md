# flowctl memory audit — staleness check against current code

## Overview

Memory entries decay. A `.flow/memory/bug/runtime-errors/` entry logged six months ago might reference a file that's been renamed, a function that's been deleted, or a codepath that's been replaced. Without a check-against-reality sweep, the memory store silently accumulates zombie entries and `memory-scout` surfaces outdated advice to future work skills.

`flowctl memory audit` runs a deterministic reference-resolution sweep over every memory entry, scores staleness, and writes a report. Optional `--rewrite` pipes hard-stale entries through a fast-model classifier that either proposes an updated version based on current code or flags the entry with `status: stale` in its frontmatter. Deletion is never automatic — the output is a report + frontmatter flag that the queryable surface (`memory list`, `memory search`) can filter.

Fits cleanly on top of fn-30's categorized memory schema: uses the existing YAML frontmatter, the `status` field already supported by `memory list --status active|stale|all`, and the same `bug/` + `knowledge/` tree.

## Constraints (CRITICAL)

- Zero-dep: bash + Python stdlib + flowctl only. Reference checks use `git ls-files` + grep. LLM rewrite uses the existing codex/copilot classifier dispatch from fn-30's `memory migrate`.
- Never silently deletes. Audit output is a report + `status: stale` frontmatter; human decides what to remove.
- Ralph-out by default. `memory audit` is manual or scheduled (`/schedule`); running `--rewrite` under Ralph would overwrite entries mid-loop.
- Idempotent. Re-running on a clean store does no work; subsequent runs only re-examine entries modified since last audit (tracked via `last_audited` sentinel).
- Additive frontmatter. `status: stale` and `last_audited` join existing keys without breaking `memory list / read / search` or any existing consumer.
- Cross-backend. `--backend codex|copilot|none` for the optional LLM rewrite pass; `--no-llm` keeps audit deterministic (file-exists + symbol-presence only).

## Approach

### Command: `flowctl memory audit`

```bash
flowctl memory audit                           # deterministic sweep, writes report, no rewrites
flowctl memory audit --track bug               # audit only bug entries
flowctl memory audit --category runtime-errors # audit only one category
flowctl memory audit --rewrite                 # propose updated bodies for hard-stale via fast-model
flowctl memory audit --no-llm                  # force deterministic even under --rewrite
flowctl memory audit --json                    # JSON output for tooling
flowctl memory audit --backend codex           # LLM backend override (default: auto via FLOW_MEMORY_CLASSIFIER_BACKEND)
flowctl memory audit --force                   # re-audit entries untouched since last_audited
```

### Reference extraction per entry

For each entry file, the audit extracts:

1. **Frontmatter refs:** `module` field parsed as a path; `tags` fields scanned for path-like values.
2. **Body refs:** regex-extract patterns that look like code references:
   - Path-like tokens: `plugins/foo/bar.py`, `src/auth/service.ts`, `./scripts/release.sh`
   - Symbol citations: `fn `function_name()`, `class `ClassName` `, `method `obj.method()`
   - Import statements copied verbatim
   - Config keys: `.flow/config.json` dotted paths like `review.backend`

### Deterministic resolution

For each extracted reference:

- **Path:** check `git ls-files` (fast cache of tracked paths) for exact match. If no match, try case-insensitive + fuzzy (Levenshtein ≤ 3) for common rename patterns.
- **Symbol:** `grep -rn "$symbol" <tracked-files>` with a hard timeout (500ms per symbol).
- **Config key:** parse `.flow/config.json` (if exists) and check the dotted path resolves.

A reference is **resolved** if at least one deterministic check succeeds, **missing** if none do.

### Staleness scoring

```
fresh        — 100% refs resolved
soft-stale   — 1-2 refs missing, or ≤33% of total refs missing
hard-stale   — >33% refs missing, OR module path no longer exists, OR 0 refs extractable (body is too abstract)
```

Scores are attached to each entry in the audit report; no frontmatter change for `fresh` entries.

### Audit report artifact

Report writes to `.flow/memory/_audit/<date>.md`:

```markdown
---
date: 2026-04-24
audited: 47
fresh: 31
soft_stale: 10
hard_stale: 6
rewritten: 0
backend: none
---

# Memory audit 2026-04-24

## Hard-stale (requires attention — 6)

### bug/runtime-errors/race-condition-in-worker-2026-03-01
- **Missing refs:** `scripts/worker-legacy.py` (not tracked), `WorkerPool.acquire()` (not found in codebase)
- **Suggestion:** The entry references a legacy module path. Consider: (a) update to point at current location (`scripts/flowctl.py` → `_triage_run_codex_judge`?), or (b) archive if the pattern no longer applies.
- **Action needed:** review + rewrite or archive

### ...

## Soft-stale (verify — 10)

- `knowledge/conventions/use-pnpm-not-npm-2026-04-24` — 1 missing ref (`package.json` still tracked, but `"packageManager"` field not found). Minor drift.
- ...

## Fresh (no action — 31)

Queryable via `flowctl memory list --status active` (default).
```

### `status: stale` frontmatter

For entries scored `hard-stale` (and `soft-stale` when `--rewrite` is active and the LLM confirms decay), the audit updates the entry's frontmatter:

```yaml
---
title: Race condition in worker
date: 2026-03-01
track: bug
category: runtime-errors
module: scripts/worker-legacy.py  # original, preserved
status: stale
last_audited: 2026-04-24
audit_notes: "missing refs: scripts/worker-legacy.py, WorkerPool.acquire()"
---
```

The body is **never rewritten by default** — human reads the audit report and decides. `--rewrite` flips this behaviour (see next).

### Optional `--rewrite` pass

When `--rewrite` is passed and a fast-model backend is available:

1. Hard-stale entries are sent to the classifier with a prompt: *"This memory entry references code that no longer exists. Here is the current repo snapshot of the referenced area (grep results + nearest surviving files). Either: (a) propose an updated version of the entry body that accurately describes the current state, with minimal rewriting of the reasoning, or (b) confirm the entry is obsolete and should be marked stale."*
2. Option (a) → body is rewritten, `last_updated` stamped, `status` unset (re-audited as fresh).
3. Option (b) → body left untouched, `status: stale` added.
4. Never deletes, never silently modifies without a `last_updated` stamp.

### Idempotency

`last_audited` frontmatter field stamps when each entry was last examined. Re-running `memory audit` without `--force` skips entries where `last_audited >= file_mtime`. With `--force`, re-examines all. Rerunning on a clean store exits fast.

## Acceptance criteria

- **R1:** `flowctl memory audit` walks `.flow/memory/<track>/<category>/*.md`, extracts refs from frontmatter + body, resolves against `git ls-files` + grep.
- **R2:** Scoring: `fresh` / `soft-stale` / `hard-stale` tiers per the rules above. Report emits counts per tier.
- **R3:** Report writes to `.flow/memory/_audit/<date>.md` with YAML frontmatter (`date, audited, fresh, soft_stale, hard_stale, rewritten, backend`) and structured body sections.
- **R4:** Hard-stale entries get `status: stale` + `last_audited` + `audit_notes` frontmatter added (body preserved). Never deletes.
- **R5:** `--rewrite` uses fast-model classifier (codex/copilot, same dispatch as `memory migrate`); proposes updated body OR confirms stale; never overwrites without `last_updated` stamp.
- **R6:** `--no-llm` forces deterministic (skips rewrite even when available).
- **R7:** `--track <t>` / `--category <c>` scope the audit; `--force` re-audits entries untouched since last `last_audited`.
- **R8:** Idempotent — re-running on clean store does nothing; `last_audited >= file_mtime` check skips untouched entries.
- **R9:** `--json` returns `{audited, fresh, soft_stale, hard_stale, rewritten, report_path, backend, model}`.
- **R10:** `memory list --status stale` surfaces entries flagged by audit (already supported by fn-30 infrastructure; this epic verifies integration).
- **R11:** Ralph-out: hard-errors with exit 2 on `FLOW_RALPH=1` UNLESS the caller explicitly passes `--allow-ralph` (reserved for scheduled runs via `/schedule`, never for autonomous loops).
- **R12:** Smoke test: synthetic repo with 3 fresh + 2 soft-stale + 2 hard-stale entries; audit produces correct counts + frontmatter flags + report. Re-run is no-op.
- **R13:** Docs updated: CHANGELOG entry, plugins/flow-next/README.md memory section (add audit subcommand reference), CLAUDE.md memory block (add `memory audit` bullet).

## Testing strategy

- **Unit:**
  - Reference extractor (path-like + symbol + config-key patterns)
  - Deterministic resolver (git ls-files + grep, with timeouts)
  - Staleness scorer (fresh / soft / hard boundaries)
  - Frontmatter diff (status + last_audited + audit_notes additions preserve existing keys)
  - Idempotency check (skip when `last_audited >= mtime`)
- **Smoke (synthetic repo):**
  - Seed memory with 3 fresh + 2 soft-stale + 2 hard-stale entries
  - Run `memory audit --no-llm`; assert counts, report structure, frontmatter updates on stale entries, no change on fresh
  - Run again; assert zero work done (idempotent)
  - Run `memory audit --force`; assert re-examination of all entries
  - Run `memory audit --track bug --category runtime-errors`; assert scope
- **Ralph regression:** invoke under `FLOW_RALPH=1` without `--allow-ralph`; assert exit 2 and zero writes.

## Boundaries

- Not deleting entries. `status: stale` is a flag, not a removal.
- Not auto-committing changes. Audit updates frontmatter in place; user decides when to stage + commit.
- Not cross-project. Audits only the current repo's `.flow/memory/`.
- Not replacing `memory migrate`. Migrate converts legacy flat files to the categorized schema (fn-30). Audit examines existing categorized entries for staleness. Different phases of lifecycle.
- Not scoring knowledge-track entries by codepath alone. Knowledge entries (conventions, tooling decisions) may legitimately reference abstract patterns with no code refs — they score `fresh` by default unless `applies_when` or `module` frontmatter explicitly breaks.

## Decision context

**Why "audit" not "refresh"?** "Audit" is a standard engineering verb (security audit, audit log) — implies check-against-reality, not modification. Distinguishes cleanly from `--rewrite` which actually changes content. Matches the intent: by default, audit only reports; rewrite is an opt-in layer.

**Why deterministic-first?** Reference resolution via `git ls-files + grep` is milliseconds per entry. An entire memory store (typical: ~50 entries) audits in seconds without a single LLM call. LLM is only paid for entries that already look broken, and only under `--rewrite`. Keeps the default cheap.

**Why `status: stale` instead of deletion?** Memory entries encode reasoning that may still be valuable even when the specific code they cite is gone. A stale entry is worth reading for the *why*; deletion erases that history. The queryable surface (`memory list --status active` vs `--status all`) gives users the filter they need without destroying content.

**Why Ralph-out by default?** `--rewrite` modifies entries; an autonomous loop rewriting memory mid-run could change the advice a concurrent `memory-scout` call surfaces to a different task. Safer as manual or scheduled.

## Risks

| Risk | Mitigation |
|---|---|
| False-positive stale (grep misses a symbol that does exist, e.g. inside a docstring) | Resolver tries multiple check modes; soft-stale tier catches boundary cases; hard-stale requires >33% missing |
| LLM rewrite loses valuable reasoning from original entry | Prompt explicitly says "minimal rewriting"; `last_updated` stamp preserves git history; `--no-llm` available as deterministic-only |
| Report artifact sprawl (weekly audits accumulate) | `.flow/memory/_audit/` keeps dated history but `_audit` prefix excludes it from default `memory list` / `search` surfaces |
| Idempotency skip misses legitimately changed files | `last_audited >= file_mtime` check uses filesystem mtime; `--force` override always available |

## Follow-ups (not in this epic)

- Scheduled weekly audit via `/schedule` background agent
- Cross-track staleness correlation (e.g. bug entry referring to code that knowledge-track entry also references — flag both)
- Integration with `/flow-next:prospect` (surface stale memory as ideation input: "these entries are decayed, worth revisiting?")

## Tasks

Planned task breakdown (epic-review will finalize):

1. Reference extractor + deterministic resolver (`_memory_extract_refs`, `_memory_resolve_ref`)
2. Staleness scorer + report writer (emits `.flow/memory/_audit/<date>.md`)
3. `flowctl memory audit` CLI + argparse wiring + frontmatter updater
4. Optional `--rewrite` pass using fn-30's classifier dispatch
5. Smoke test + Ralph-block verification + idempotency check
6. Docs, codex mirror, version bump (patch: 0.35.1 → 0.35.2)
