# fn-30-memory-schema-upgrade.7 Docs, website, codex mirror, version bump

## Description

Rollup task: CHANGELOG, READMEs, CLAUDE.md, website page, codex regeneration, version bump.

**Size:** M (docs only)

**Files:**
- `CHANGELOG.md`
- `plugins/flow-next/README.md`
- `CLAUDE.md`
- `/Users/gordon/work/mickel.tech/app/apps/flow-next/page.tsx`
- `plugins/flow-next/.claude-plugin/plugin.json` (via bump.sh)
- `plugins/flow-next/.codex-plugin/plugin.json` (via bump.sh)
- `.claude-plugin/marketplace.json` (via bump.sh)
- `plugins/flow-next/codex/**` (via sync-codex.sh)

## Change details

### CHANGELOG.md

New entry:

```markdown
## [flow-next 0.34.0] - YYYY-MM-DD

### Added
- **Categorized memory schema.** `.flow/memory/` is now a tree under `bug/` (build-errors, test-failures, runtime-errors, performance, security, integration, data, ui) and `knowledge/` (architecture-patterns, conventions, tooling-decisions, workflow, best-practices). Each entry has YAML frontmatter with title, date, track, category, module, tags, and track-specific fields (problem_type/root_cause/resolution_type for bug; applies_when for knowledge).
- **Overlap detection on `memory add`.** Scans existing entries in the target category; high overlap updates existing in place, moderate creates new with `related_to: [existing-id]` reference. Prevents silent duplication drift.
- **`flowctl memory migrate`.** Converts legacy `.flow/memory/pitfalls.md` / `conventions.md` / `decisions.md` into categorized entries via fast-model classification. `--dry-run` prints plan; `--yes` skips confirmation; `--no-llm` uses mechanical defaults. Classifier auto-selects `codex` (default `gpt-5.4-mini`) or `copilot` (default `claude-haiku-4.5`) — override via `FLOW_MEMORY_CLASSIFIER_BACKEND` (`codex|copilot|none`), `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT`. Idempotent (re-run reports "No legacy files to migrate."). JSON mode refuses to write without `--yes` as a safety guard; per-entry JSON shape is `{source, source_entry, target, target_path, method, model}` and top-level adds `moved_legacy`, `count`, `dry_run`, `legacy_moved_to`.
- **`flowctl memory discoverability-patch`.** Optional command that adds a one-line reference to `.flow/memory/` in the project's AGENTS.md / CLAUDE.md so agents without flow-next loaded discover the store.
- **Ralph auto-capture rewrite.** Worker agent writes structured bug-track entries via `memory add --track bug --category <c>` on NEEDS_WORK → SHIP. Overlap detection handles duplicates.
- **Category-aware memory-scout.** Scout returns track/category-tagged results, prioritizing module-matched entries.

### Changed
- `memory list` / `read` / `search` gain `--track` and `--category` filter flags; still read legacy flat files until migration runs.
- `memory list` also gains `--status active|stale|all` (default: active) — stale entries hidden unless asked.
- `memory search` also gains `--module <m>`, `--tags "a,b"`, `--limit <N>` filters plus weighted token-overlap scoring (title 5×, tags 3×, body 1.5×, misc 1×).
- `memory read` accepts three id forms — full (`bug/runtime-errors/slug-YYYY-MM-DD`), slug+date (unique lookup), and slug-only (latest date wins) — plus legacy forms (`legacy/pitfalls.md`, `legacy/pitfalls#N`).
- Entry IDs now `<track>/<category>/<slug>-<date>` matching filepath.
- Legacy hits in `search` surface as synthetic entries with `track: "legacy"` and `entry_id` like `legacy/pitfalls#3` (1-based).
- JSON output shapes: `list` returns `{entries, legacy, count, status}`; `search` returns `{query, matches, count}`; `read` returns `{entry_id, path, frontmatter, body}` (categorized) or `{entry_id, path, legacy: true, body, index?}` (legacy).

<!-- Updated by plan-sync: fn-30.3 landed list/read/search with richer filter flags and concrete JSON shapes; CHANGELOG should enumerate them. -->
<!-- Updated by plan-sync: fn-30.4 ships FLOW_MEMORY_CLASSIFIER_BACKEND/MODEL/EFFORT env knobs (codex/copilot auto-detect, gpt-5.4-mini / claude-haiku-4.5 defaults), idempotency, and a JSON shape that differs from the original spec (adds moved_legacy/count/dry_run/target_path/model; refuses JSON writes without --yes). CLAUDE.md + plugin README should mention the env vars alongside the command form. -->
<!-- Updated by plan-sync: fn-30.6 shipped `discoverability-patch` with two explicit strategies (`listing` injects `.flow/memory/` into an existing `.flow/` fenced code block; `append` adds a `## Memory / Learnings` section), richer JSON shape `{target, action, reason, notes, strategy, diff, message}` where `action ∈ {exists, applied, dry-run, skipped}`, auto-target detection (handles `@AGENTS.md`/`@CLAUDE.md` shims, symlinks, prefers AGENTS.md when both substantive), `--apply` and `--dry-run` mutually exclusive (exit 2), and JSON callers must pass `--apply` explicitly (refuses destructive auto-write). README / CHANGELOG should mention the two strategies and `--target {auto,agents,claude}` default. -->


### Deprecated
- `memory add --type pitfall|convention|decision` maps to new `--track/--category` flags with deprecation warning. Will be removed in 0.36.0.

### Notes
- Backward compatible: legacy `.flow/memory/*.md` flat files continue to work until `memory migrate` runs.
- Opt-in remains the default — `flowctl init` does not create memory.
```

### plugins/flow-next/README.md

Rewrite the memory section. Include:
- Directory structure tree
- Frontmatter schema (bug + knowledge tracks)
- Command reference (add/list/read/search/migrate/discoverability-patch)
- Overlap detection explanation
- Ralph auto-capture mention
- Migration section for upgrading users

### CLAUDE.md (root)

Replace the current memory bullets with:

```markdown
**Memory system (categorized — v0.34+):**
- Tree under `.flow/memory/`: `bug/<category>/` and `knowledge/<category>/`
- YAML frontmatter: title, date, track, category, module, tags, + track-specific fields
- Enable: `flowctl memory init`
- Add: `flowctl memory add --track <bug|knowledge> --category <c> --title "..." [--module <m>] [--tags "a,b"] [--body-file <f>]`
- Query: `flowctl memory list [--track T] [--category C]`, `flowctl memory search <q>`
- Migrate legacy: `flowctl memory migrate --dry-run` then `--yes` (classifier auto-selects codex/copilot; override with `FLOW_MEMORY_CLASSIFIER_BACKEND=codex|copilot|none` + `FLOW_MEMORY_CLASSIFIER_MODEL` / `FLOW_MEMORY_CLASSIFIER_EFFORT`)
- Surface in AGENTS.md: `flowctl memory discoverability-patch`
- Overlap detection on add — high overlap updates existing; moderate creates with `related_to`
- Auto-capture: Ralph worker writes bug-track entries on NEEDS_WORK → SHIP
- `--type` (old API) deprecated; auto-maps to new flags until 0.36.0
```

### Website: `~/work/mickel.tech/app/apps/flow-next/page.tsx`

Update:
- Version string
- Metadata description — add "categorized learnings" / "overlap detection" keywords if memory section exists
- Feature grid / FAQ sections where memory is mentioned

### sync-codex + bump

After all task 1-6 edits land (or while drafting the CHANGELOG):

```bash
scripts/sync-codex.sh
scripts/bump.sh minor flow-next   # 0.33.0 → 0.34.0
```

### Tag + release

```bash
git tag flow-next-v0.34.0
git push origin flow-next-v0.34.0
```

## Acceptance

- **AC1:** CHANGELOG has `[flow-next 0.34.0]` entry with Added / Changed / Deprecated / Notes sections.
- **AC2:** plugin README memory section describes new schema, commands, migration.
- **AC3:** CLAUDE.md root section mentions categorized tree, all new commands, deprecation.
- **AC4:** Website page updated: version + any memory-related copy.
- **AC5:** sync-codex.sh run cleanly — no manual edits to `plugins/flow-next/codex/`.
- **AC6:** bump.sh updates all three manifests and the README badge.
- **AC7:** Tag pushed (or staged) to trigger release.

## Dependencies

- All fn-30 sibling tasks (1-6) must be merged first.

## Out of scope

- Marketing copy beyond website / README.
- Separate Discord announcement (default release automation).

## Done summary
fn-30 rollup shipped: flow-next 0.33.0. CHANGELOG + plugin README + root CLAUDE.md + website page.tsx updated for categorized memory schema, overlap detection, migrate, discoverability-patch, Ralph auto-capture rewrite, and category-aware memory-scout. Marketplace, plugin, and codex-plugin manifests bumped 0.32.1 -> 0.33.0 via scripts/bump.sh minor flow-next; codex mirror regenerated clean; badges synced. Smoke: 99/99. Website page (mickel.tech) updated locally and left staged for Gordon to commit in that repo. Release tag (flow-next-v0.33.0) not pushed per worker protocol -- user triggers.
## Evidence
- Commits: c3833f2a92e617a01b7936682d4131a5e88bbebf
- Tests: plugins/flow-next/scripts/smoke_test.sh (99/99 pass)
- PRs: