# fn-39-project-strategy-strategymd-anchor.5 Codex sync + fluff guard + version bump + docs + mickel.tech

## Description
Ship the new skill: regenerate Codex mirror, add Tier-1 forbidden-vocabulary guard (separate from R17 DDD pattern), bump version to 0.40.0, update all in-repo docs (CHANGELOG, README, CLAUDE.md, .flow/usage.md), and update Gordon's external mickel.tech site.

**Size:** M (large M — touches many doc files but each edit is mechanical)
**Files:**
- `scripts/sync-codex.sh` (add `flow-next-strategy` to `REQUIRED_OPENAI_YAML_SKILLS` array; add `generate_openai_yaml` call in workflow blue group)
- `plugins/flow-next/scripts/ci_test.sh` (new section — strategy-doc fluff guard, separate from R17 DDD section 5c)
- `plugins/flow-next/.claude-plugin/plugin.json` + `.codex-plugin/plugin.json` + `.claude-plugin/marketplace.json` (version bump via `./scripts/bump.sh minor flow-next` — script handles all 3 manifests)
- `CHANGELOG.md` (new `[flow-next 0.40.0]` block)
- `plugins/flow-next/README.md` (TOC, lede count, new "Project Strategy" section, commands table, doc-aware autodetect rule)
- `CLAUDE.md` (commands list, new "Project strategy (v0.40.0+)" subsection, doc-aware autodetect rule)
- `.flow/usage.md` (new `# Strategy` block)
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` (commands array, lede count, feature card)

Depends on Tasks 1-4 (everything must be authored before sync regenerates the mirror; description counts must reflect final feature set).

## Approach

**1. Forbidden-vocabulary guard (R19)** — add NEW guard block in `plugins/flow-next/scripts/ci_test.sh`, separate from R17 DDD section 5c (lines 351-388). Comment must specify "strategy-doc fluff guard, NOT R17". Block scopes: `plugins/flow-next/skills/flow-next-strategy/` + `plugins/flow-next/scripts/flowctl.py` (cmd_strategy_*) + `plugins/flow-next/commands/flow-next/strategy.md`. References file `plugins/flow-next/skills/flow-next-strategy/references/interview.md` is excluded (must describe anti-patterns to push back on them — same exemption as glossary references). Tier 1 list: synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x.

**2. Mirror in sync-codex.sh** — add R19 grep block to the validation block at lines 774-794 (currently has R17 DDD-vocab + R4 meta-file mirror scans). Identical pattern, scoped to Codex mirror at `plugins/flow-next/codex/skills/flow-next-strategy/`.

**3. sync-codex.sh skill registration**:
- Add `flow-next-strategy` to `REQUIRED_OPENAI_YAML_SKILLS` array (lines 537-552).
- Add `generate_openai_yaml "flow-next-strategy" "Flow Strategy" "Generate or update repo-root STRATEGY.md (problem, approach, personas, metrics, tracks)" "#3B82F6" false` in workflow blue group (after the existing `flow-next-capture` call at line 519 area).

**4. Version bump**: run `./scripts/bump.sh minor flow-next`. Updates all 3 manifests automatically. Bumps 0.39.0 → 0.40.0. Update plugin.json descriptions to reflect new counts: 19 skills, 14 commands (or whatever final count is). Three manifests have description text: `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json` (line 4 description + line 24 longDescription), `.claude-plugin/marketplace.json` flow-next entry.

**5. Run sync**: `./scripts/sync-codex.sh`. Verify zero errors; verify `plugins/flow-next/codex/skills/flow-next-strategy/` exists with rewritten tool names (`request_user_input` not `AskUserQuestion`); verify `plugins/flow-next/codex/agents/openai.yaml` has the strategy entry. Commit regenerated `plugins/flow-next/codex/` directory.

**6. CHANGELOG.md** — add `## [flow-next 0.40.0] - <today>` block above the existing 0.39.0 entry. Sections: Files Added (skill, references, slash command, smoke test, fluff guard, ci_test section), Files Changed (downstream skills + plan-sync + interview autodetect + capture + sync-codex), Constraints (R-IDs from spec — STRATEGY.md repo-root, single-root walk, husk semantics, foreign-file refusal, Ralph block), Smoke coverage (T1-T12).

**7. plugins/flow-next/README.md updates**:
- Line 24 lede ("What's new in 0.39.0") → add 0.40.0 lede paragraph above describing strategy
- Line 40 TOC → add `- [Project Strategy](#project-strategy)` parallel to glossary entry
- Line 57 lede ("Sixteen slash commands") → bump to seventeen + insert strategy in lifecycle position
- After line 1757 (end of `## Project Glossary`) → new `## Project Strategy` section. Mirror glossary section's sub-structure: Format / Resolution / Subcommands (only status/read/list — note no add/edit) / Husk semantics / How the rest of flow-next uses it / Forbidden vocabulary / Why no migration in v1.
- Line 1761 ("Sixteen commands") → bump to seventeen; add `/flow-next:strategy` row to commands table.
- Line 1809-1820 flag-matrix table → add `--strategy` / `--no-strategy` row.
- Line 1917 doc-aware autodetect rule → extend OR condition to include `STRATEGY.md sections_filled >= 1`.

**8. CLAUDE.md updates**:
- Lines 19-29 commands list → add `/flow-next:strategy [optional: section to revisit]` bullet with one-sentence description and version tag `(v0.40.0+)`.
- After line 112 (end of "Project glossary (v0.39.0+)") → new "Project strategy (v0.40.0+)" subsection. Cover: STRATEGY.md repo-root convention (R18 invariant — survives `.flow/` wipe), single-root walk (NOT nearest-ancestor, contrast glossary), 3 frontmatter keys (`name`, `last_updated`, `generator: flow-next-strategy`), section structure (5 required + 2 optional, drop CE Marketing), `flowctl strategy status/read/list` subcommands, husk semantics (`sections_filled >= 1` rule, NOT file-existence), how downstream skills consume it (read-only, advisory, never auto-supersede), foreign-file refusal in v1.
- Line 109 doc-aware autodetect one-liner → extend with strategy condition.
- Line 280 area "Adding a new user-facing skill" checklist → no change (this task validates the checklist).

**9. .flow/usage.md** lines 88-97 area → add `# Strategy` sub-block after the `# Glossary` block. Lists the three subcommands with example invocations.

**10. mickel.tech update** at `~/work/mickel.tech/app/apps/flow-next/page.tsx`:
- Increment lede command count
- Add `strategy` entry to commands array (find the existing pattern — likely a TS array of `{name, description, version}` objects)
- Add feature card for "Project Strategy" parallel to the existing glossary feature card; mirror title / description / version-badge structure
- FAQ entry if applicable (e.g., "How does flow-next ground prospect/plan in product strategy?")

This task is coupled — version bump must happen AFTER doc edits (so plugin.json descriptions reflect final feature counts), and sync MUST run AFTER version bump (so the Codex mirror picks up the new version). Order: forbidden-vocab guards → docs → version bump → sync → commit.

## Investigation targets

**Required:**
- `scripts/sync-codex.sh:497-552` — `generate_openai_yaml` definition + call sites + `REQUIRED_OPENAI_YAML_SKILLS` array
- `scripts/sync-codex.sh:774-794` — R17 + R4 mirror validation blocks (model for R19 fluff guard mirror)
- `plugins/flow-next/scripts/ci_test.sh:351-388` — section 5c R17 DDD guard (model — but DON'T extend; create new section)
- `plugins/flow-next/README.md:24,40,57,1715-1757,1759-1820,1917` — exact line refs for all README edits per docs-gap-scout
- `CLAUDE.md:19-29,100-112,109,280` — exact line refs for all CLAUDE.md edits
- `CHANGELOG.md:5` — current `[flow-next 0.39.0]` block; new 0.40.0 goes above
- `.flow/usage.md:88-97` — `# Glossary` block (model for `# Strategy` block)
- `scripts/bump.sh` — version bump tool; figure out which manifests it updates
- `plugins/flow-next/.claude-plugin/plugin.json:3` — version field; description field needs count update
- `plugins/flow-next/.codex-plugin/plugin.json:3-4,24` — version + description + longDescription
- `.claude-plugin/marketplace.json:9,15` — marketplace + plugin version

**Optional:**
- `~/work/mickel.tech/app/apps/flow-next/page.tsx` — commands array + feature cards (read access may be limited if this is in a separate repo; check before editing)

## Key context

- R19 forbidden-vocab guard is SEPARATE from R17 DDD guard. Each block has one purpose. Comment in ci_test.sh must specify "strategy-doc fluff guard, NOT R17" so future maintainers don't mix them.
- `references/interview.md` is exempt from the guard (must describe anti-patterns to push back on them — same exemption pattern as glossary references file vs the canonical SKILL.md).
- Two-tier guard: ci_test.sh validates canonical, sync-codex.sh validates the Codex mirror. Both must catch a violation.
- mickel.tech update is "in scope per user request" — Gordon's repo, but he asked it to ship in this epic. External contributors would normally skip this per CLAUDE.md "Contributing / Development" section.
- Order matters: docs → version bump → sync. Sync regenerates the Codex mirror after the canonical files are stable.
- Verify post-sync: `plugins/flow-next/codex/skills/flow-next-strategy/SKILL.md` exists, contains `request_user_input` not `AskUserQuestion`, has zero R19/R17 forbidden-vocab matches.
## Acceptance
- [ ] `plugins/flow-next/scripts/ci_test.sh` has a NEW guard block (separate from R17 section 5c) titled "strategy-doc fluff guard, NOT R17". Block grep pattern includes Tier 1 jargon: `synergy|pivot|disrupt|thought leadership|best-in-class|world-class|10x` (with appropriate word boundaries). Scopes: `plugins/flow-next/skills/flow-next-strategy/SKILL.md` + `plugins/flow-next/scripts/flowctl.py` (`cmd_strategy_*` regions) + `plugins/flow-next/commands/flow-next/strategy.md`. Excludes `plugins/flow-next/skills/flow-next-strategy/references/interview.md` (must describe anti-patterns).
- [ ] `scripts/sync-codex.sh` validation block (lines 774-794) extended with R19 mirror scan against `plugins/flow-next/codex/skills/flow-next-strategy/` (rewritten Codex mirror). Same pattern as the canonical guard.
- [ ] `scripts/sync-codex.sh:537-552` — `REQUIRED_OPENAI_YAML_SKILLS` array contains `"flow-next-strategy"` entry. CI fails when missing.
- [ ] `scripts/sync-codex.sh` workflow-blue group has `generate_openai_yaml "flow-next-strategy" "Flow Strategy" "<description>" "#3B82F6" false` call (placement after existing `flow-next-capture` call).
- [ ] Version bumped 0.39.0 → 0.40.0 across all 3 manifests via `./scripts/bump.sh minor flow-next`. Verified by:
      - `jq -r '.version' plugins/flow-next/.claude-plugin/plugin.json` returns 0.40.0
      - `jq -r '.version' plugins/flow-next/.codex-plugin/plugin.json` returns 0.40.0
      - `jq -r '.plugins[] | select(.name=="flow-next") | .version' .claude-plugin/marketplace.json` returns 0.40.0
- [ ] Three plugin.json description fields updated to reflect final counts (skills + commands + agents). Description in `plugins/flow-next/.claude-plugin/plugin.json` + `.codex-plugin/plugin.json` description + longDescription + `.claude-plugin/marketplace.json` flow-next entry.
- [ ] `./scripts/sync-codex.sh` run completes with zero errors. Verified by:
      - `plugins/flow-next/codex/skills/flow-next-strategy/SKILL.md` exists with `request_user_input` substituted for `AskUserQuestion`
      - `plugins/flow-next/codex/agents/openai.yaml` includes a `flow-next-strategy` entry
      - `grep -RE 'AskUserQuestion' plugins/flow-next/codex/skills/flow-next-strategy/` returns no hits (sync rewrites cleanly)
- [ ] `CHANGELOG.md` has new `## [flow-next 0.40.0] - <today's ISO date>` block above the existing 0.39.0 entry. Sections: Files Added, Files Changed, Constraints (R-IDs), Smoke coverage (T1-T12).
- [ ] `plugins/flow-next/README.md` updated:
      - Line 24 area: 0.40.0 lede paragraph above existing 0.39.0 lede
      - Line 40 TOC: `- [Project Strategy](#project-strategy)` entry
      - Line 57 lede: command count bumped to seventeen + strategy mentioned in lifecycle chain
      - New `## Project Strategy` section after `## Project Glossary` (line 1757). Sub-sections: Format, Resolution, Subcommands (status/read/list only — note absence of add/edit), Husk semantics, How the rest of flow-next uses it, Forbidden vocabulary (Tier 1 list), Why no migration in v1
      - Line 1761 commands table: count bumped to seventeen + new `/flow-next:strategy` row
      - Line 1809-1820 flag-matrix table: new `--strategy` / `--no-strategy` row
      - Line 1917 doc-aware autodetect rule: OR condition extended to include `STRATEGY.md sections_filled >= 1`
- [ ] `CLAUDE.md` updated:
      - Lines 19-29 commands list: `/flow-next:strategy [optional: section to revisit]` bullet added in lifecycle order with `(v0.40.0+)` version tag
      - After line 112: new "Project strategy (v0.40.0+)" subsection covering R18 invariant, single-root walk, 3 frontmatter keys, section structure (5+2, no Marketing), 3 subcommands, husk semantics, downstream consumers (read-only advisory), v1 foreign-file refusal
      - Line 109: doc-aware autodetect one-liner extended with strategy condition
- [ ] `.flow/usage.md` lines 88-97 area: new `# Strategy` block after `# Glossary` block. Lists `flowctl strategy status [--json]`, `flowctl strategy read [--section <name>] [--json]`, `flowctl strategy list [--json]` with one-line example invocations.
- [ ] `~/work/mickel.tech/app/apps/flow-next/page.tsx` updated:
      - Lede command count bumped
      - Strategy entry added to commands array (matching existing pattern shape)
      - Feature card for "Project Strategy" added parallel to glossary feature card
      - FAQ entry added if pattern exists for parallel features
- [ ] CI passes after all changes: `plugins/flow-next/scripts/ci_test.sh` exits 0 with no R17/R19 violations and no R4 meta-file violations. `./scripts/sync-codex.sh` validation block exits 0.
- [ ] `git diff --stat` shows expected file set; no accidental edits to `.flow/`, smoke fixtures, or unrelated files.
## Done summary
Shipped fn-39 task 5: Codex sync + R19 strategy-doc fluff guard + version bump 0.39.0→0.40.0 + docs across CHANGELOG / plugins/flow-next/README.md / CLAUDE.md / .flow/usage.md / root README.md / mickel.tech. Two-tier R19 guard (canonical ci_test.sh section 5d + sync-codex.sh validation block) blocks Tier 1 fluff (synergy / pivot / disrupt / thought-leadership / best-in-class / world-class / 10x) in flow-next-strategy SKILL.md + cmd_strategy_* in flowctl.py + strategy.md command, with references/interview.md exempt for anti-pattern descriptions. flow-next-strategy added to REQUIRED_OPENAI_YAML_SKILLS + workflow blue group; Codex mirror regenerated with request_user_input substituted for AskUserQuestion. All 3 manifests at 0.40.0 with description counts refreshed to 21 subagents / 17 commands / 22 skills. ci_test.sh 57/57, smoke_test.sh 130/130, glossary_smoke_test.sh 80/80, sync-codex.sh zero errors.
## Evidence
- Commits: 951e27faf8331e92d83d9cfa22b1a087309c0d6b
- Tests: plugins/flow-next/scripts/ci_test.sh (57/57 pass — includes new R19 strategy-doc fluff guard), plugins/flow-next/scripts/ci_test.sh fluff-fixture-injection: confirmed guard fires non-zero on seeded synergy keyword in flow-next-strategy/SKILL.md (then reverted), ./scripts/sync-codex.sh (22 skills, 21 agents, 15 openai.yaml; R19 mirror green; flow-next-strategy/agents/openai.yaml generated), ./scripts/bump.sh minor flow-next: 0.39.0 -> 0.40.0 across all 3 manifests (claude-plugin / codex-plugin / marketplace) verified via jq, smoke_test.sh from /tmp (130/130 pass), glossary_smoke_test.sh from /tmp (80/80 pass), Codex strategy mirror verified: grep -c request_user_input = 8, grep -c AskUserQuestion = 0, Plugin description counts updated to 21 subagents / 17 commands / 22 skills across 3 plugin.json files
- PRs: