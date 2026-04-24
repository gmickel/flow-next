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
   - `### Added` block covering `/flow-next:prospect` command, all 4 `flowctl prospect` subcommands, `.flow/prospects/` artifact directory, Ralph-out behavior, bucketed ranking, persona seeding, rejection floor.
   - `### Changed` block if any existing behavior shifted (expected: none — prospect is purely additive).
   - Match verbose style of `[flow-next 0.34.0]` (resolve-pr) entry.

3. **`plugins/flow-next/README.md` updates:**
   - Command table: add `/flow-next:prospect [focus hint]` row.
   - flowctl cheat sheet: add `flowctl prospect list / read / archive / promote` block with examples.
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
- [ ] All three smoke suites + unit tests pass.
- [ ] No references to compound-engineering or other plugins in shipped docs.

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
