---
satisfies: [R11]
---

## Description

Rollup task: CHANGELOG, READMEs, CLAUDE.md, website, codex mirror, version bump.

**Size:** S (docs rollup, mechanical)
**Files:**
- `CHANGELOG.md`
- `plugins/flow-next/README.md`
- `CLAUDE.md` (root)
- `README.md` (root)
- `.flow/usage.md`
- `~/work/mickel.tech/app/apps/flow-next/page.tsx`
- `plugins/flow-next/.claude-plugin/plugin.json` (via bump.sh)
- `plugins/flow-next/.codex-plugin/plugin.json` (via bump.sh)
- `.claude-plugin/marketplace.json` (via bump.sh)
- `plugins/flow-next/codex/**` (via sync-codex.sh)

## Approach

Mechanical rollup following the pattern used by fn-29.7, fn-30.7, fn-31.7, fn-32.6:

1. **Version bump:** `scripts/bump.sh minor flow-next` (0.35.1 → 0.36.0). New skill = minor bump.

2. **CHANGELOG entry** under new `[flow-next 0.36.0]`:
   - `### Added` block covering `/flow-next:prospect` command, all 4 `flowctl prospect` subcommands (`list`, `read`, `archive`, `promote`), `.flow/prospects/` artifact directory, Ralph-out behavior, bucketed ranking, persona seeding, rejection floor.
   - Mention the shipped flowctl.py helpers from task 3: `write_prospect_artifact`, `render_prospect_body`, `validate_prospect_frontmatter`, `_prospect_slug`, `_prospect_next_id`, `PROSPECT_REQUIRED_FIELDS`/`PROSPECT_OPTIONAL_FIELDS`/`PROSPECT_FIELD_ORDER`. <!-- Updated by plan-sync: task 3 shipped these public-ish helpers; include in changelog. -->
   - Mention the shipped flowctl.py helpers from task 4: `_prospect_parse_frontmatter`, `_prospect_detect_corruption`, `_prospect_artifact_status`, `_prospect_resolve_id`, `_prospect_iter_artifacts`, `_prospect_extract_section`, `_prospect_extract_survivors`, `_prospect_extract_rejected`, `get_prospects_dir`, plus the `PROSPECT_CORRUPT_*` module constants that own the R16 reason-string contract. <!-- Updated by plan-sync: task 4 shipped the CLI + parsing/status helper surface; document in the technical-details paragraph. -->
   - Mention the shipped flowctl.py helpers from task 5: `_render_epic_skeleton_from_prospect`, `_prospect_rewrite_in_place` (shared in-place atomic rewrite helper, used by both `cmd_prospect_archive` and `cmd_prospect_promote`), and the inline-flow dict branch added to `_format_prospect_yaml_value` for the new `promoted_to` field. Note that task 5 did NOT add a standalone `_extract_survivor` helper — survivor lookup is inlined via `next((s for s in _prospect_extract_survivors(body) if s["position"] == N), None)`. Also note: promote inlines epic allocation + spec write (mirrors `cmd_epic_create`'s scan-based allocation) rather than calling `cmd_epic_create` + `cmd_epic_set_plan` — one-shot write keeps the prospect-context spec on disk from the first byte. <!-- Updated by plan-sync: task 5 shipped _prospect_rewrite_in_place (shared helper refactored out of archive) and inlined epic creation; document both in technical-details. -->
   - Document exit codes: `flowctl prospect read` on corrupt artifact exits `3` (distinct from Ralph-block `2`); `flowctl prospect promote` on corrupt artifact also exits `3` (stderr marker `[ARTIFACT CORRUPT: <reason>]`); `promote` on duplicate idea without `--force` exits `2` with a message referencing the prior epic-id; `list --all` surfaces corrupt entries with `corrupt (<reason>)` in the status column. <!-- Updated by plan-sync: task 5 added promote's exit-3 corrupt branch and exit-2 idempotency branch. -->
   - Artifact frontmatter shape: `date` round-trips as quoted string; optional flags `floor_violation`, `generation_under_volume`, `promoted_to` (post-task-5, renders as inline-flow dict `{N: [epic-A, epic-B]}` with bare-numeric keys for integer idea positions) are omitted when unset.
   - `### Changed` block if any existing behavior shifted (expected: none — prospect is purely additive).
   - Mention testing: dedicated `plugins/flow-next/scripts/prospect_smoke_test.sh` (11 cases, 94 assertions, ~58s, zero LLM calls) — pattern matches `impl-review_smoke_test.sh` (fn-32.5); existing `smoke_test.sh` unchanged (regression-checked only). <!-- Updated by plan-sync: fn-33-…6 shipped a standalone smoke script rather than extending smoke_test.sh; changelog should say so. -->
   - Match verbose style of `[flow-next 0.34.0]` (resolve-pr) entry.

3. **`plugins/flow-next/README.md` updates:**
   - Command table: add `/flow-next:prospect [focus hint]` row.
   - flowctl cheat sheet: add `flowctl prospect list / read / archive / promote` block with examples. Include `--section focus|grounding|survivors|rejected` on `read`, `--all` on `list`, `--idea N`/`--epic-title`/`--force`/`--json` on `promote`, and the exit-3 contract for corrupt artifacts (applies to both `read` and `promote`). Show the promote success output format: `Promoted idea #N ("<title>") to <epic-id>. Next: /flow-next:interview <epic-id>`. <!-- Updated by plan-sync: task 4 + task 5 shipped these exact flag shapes + text output. -->
   - Lifecycle diagram (mermaid): insert `prospect → interview → plan → work` as an upstream branch before the current `interview → plan → work` path.
   - New "## Prospecting (v0.36.0+)" section before "## Planning" covering: when to use, artifact schema, promote flow, decision context (why prose-only ranking, why bucketed, why Ralph-out).

4. **`CLAUDE.md` (root) updates:**
   - Command list block (around line 19-25): add `/flow-next:prospect [focus hint]` entry with one-liner + note about `.flow/prospects/` artifact directory.
   - Add new "Prospecting (v0.36.0+)" bullet block following the fn-30 memory block style.

5. **`README.md` (root) updates:**
   - Version badge: already bumped by `bump.sh`.
   - Commands table: add prospect row.

6. **`.flow/usage.md` updates:**
   - Add `flowctl prospect list / read / archive / promote` to the Common Commands section.

7. **Website (`~/work/mickel.tech/app/apps/flow-next/page.tsx`) updates:**
   - Version string → 0.36.0.
   - Metadata description + keywords: add "ideation" / "prospect" / "ranked candidates" terms.
   - `commands` array: add `/flow-next:prospect` entry.
   - `coreFeatures` or `optInFeatures`: new card for Prospecting (similar shape to the fn-30 memory card + fn-31 resolve-pr card).
   - FAQ: new entry "When do I use prospect vs interview vs plan?" distinguishing the three upstream-of-work commands.
   - Lifecycle diagram update if present.

8. **Codex mirror:** `scripts/sync-codex.sh` (regenerates `plugins/flow-next/codex/` — expected: +1 skill subdirectory for flow-next-prospect, no new agents, hooks.json unchanged).

9. **Final validations:**
   - `jq .` on all three manifests (valid JSON).
   - Full test suite: `plugins/flow-next/scripts/smoke_test.sh` + `plugins/flow-next/scripts/prospect_smoke_test.sh` + `python3 -m unittest discover -s plugins/flow-next/tests`.
   - `scripts/sync-codex.sh` run twice — second run must be no-op (zero drift).

## Investigation targets

**Required:**
- `CHANGELOG.md` `[flow-next 0.34.0]` entry — closest precedent (new command + Ralph-out + zero-dep)
- `plugins/flow-next/README.md` — current structure for command table + flowctl cheat sheet + lifecycle diagram
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` — commit `37f9022` (fn-31 update) + `5820f29` (fn-32 update) as templates

## Key context

- Website repo is separate from the plugin repo — commit + push to `~/work/mickel.tech` in a distinct commit.
- `scripts/sync-codex.sh` must run AFTER skill files are authored — any drift flags an incomplete earlier task.
- Don't cross-reference compound-engineering or any external plugin in the final docs; prose should frame prospect in terms of flow-next's own lifecycle.

## Acceptance

- [ ] Version bumped 0.35.1 → 0.36.0 via `scripts/bump.sh minor flow-next`; all 3 manifests + 2 README badges updated.
- [ ] CHANGELOG `[flow-next 0.36.0]` entry exists, covers all new surface.
- [ ] `plugins/flow-next/README.md` has new Prospecting section, updated command table, updated flowctl cheat sheet, updated lifecycle diagram.
- [ ] `CLAUDE.md` (root) command list + new Prospecting block.
- [ ] `README.md` (root) + `.flow/usage.md` updated.
- [ ] Website `page.tsx` updated: version, commands, coreFeatures/optInFeatures card, FAQ; committed + pushed.
- [ ] `scripts/sync-codex.sh` regenerates Codex mirror; second run is no-op (zero drift).
- [ ] Both smoke suites (`smoke_test.sh`, `prospect_smoke_test.sh`) + unit tests pass. <!-- Updated by plan-sync: fn-33-…6 shipped prospect_smoke_test.sh as a dedicated standalone script (764 lines, 94 assertions, ~58s) instead of extending smoke_test.sh; there are two smoke suites, not three. -->
- [ ] No references to compound-engineering or other plugins in shipped docs.

## Done summary
Bumped flow-next 0.35.1 → 0.36.0 (minor) for the new `/flow-next:prospect` skill and `flowctl prospect` subcommands. Updated CHANGELOG, READMEs, CLAUDE.md, .flow/usage.md, plugin manifests (17→18 skills, 12→13 commands), and the website page. Regenerated Codex mirror (sync is idempotent — second run is no-op). All smoke suites + unit tests + website lint/typecheck pass.
## Evidence
- Commits: a70834009a50136563f4cd5d25e05ff35045d020, 588b6ff89e805e5d1b97c178710e15eb0de966fb
- Tests: plugins/flow-next/scripts/smoke_test.sh (125 PASS), plugins/flow-next/scripts/prospect_smoke_test.sh (94 PASS), python3 -m unittest discover -s plugins/flow-next/tests (308 OK), scripts/sync-codex.sh (idempotent: 2nd run zero diff), pnpm lint app/apps/flow-next/page.tsx (mickel.tech, biome OK)
- PRs: