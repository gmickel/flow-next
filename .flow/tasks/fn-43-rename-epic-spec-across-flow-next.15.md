---
satisfies: [R19, R22, R23, R28]
---

## Description

Final assembly: bump versions, update plugin manifests, write the CHANGELOG `[flow-next 1.0.0]` block (with explicit Migration guide subsection), self-edit `scripts/sync-codex.sh` for the agent rename + epic-review skill rename + R19 mirror-scan validation, then run `./scripts/sync-codex.sh` to regenerate the entire Codex mirror from the post-rename canonical state. Optionally implement `flowctl migrate-docs --dry-run` helper for users who want to clean their CLAUDE.md/AGENTS.md.

**Size:** M
**Files:**
- `.claude-plugin/marketplace.json` (version bump via `scripts/bump.sh`)
- `plugins/flow-next/.claude-plugin/plugin.json` (version + longDescription)
- `plugins/flow-next/.codex-plugin/plugin.json` (version + longDescription)
- `CHANGELOG.md` (NEW `[flow-next 1.0.0]` block)
- `scripts/sync-codex.sh` (lines 31, 98, 226, 281, 348, 532, 541, 545, 565 + new R19 validation block) <!-- Updated by plan-sync: T5 already updated lines 31/98/281 (epic-scout -> spec-scout) and line 226 (worker heredoc EPIC_ID -> SPEC_ID); T15 owns the remaining sites + R19 validation block -->
- `plugins/flow-next/codex/` (full regeneration -- many files)
- `plugins/flow-next/scripts/flowctl.py` (optional `flowctl migrate-docs` helper)

## Approach

- `scripts/bump.sh major flow-next` bumps `.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, and `plugins/flow-next/.codex-plugin/plugin.json` to 1.0.0.
- `longDescription` field in both `.claude-plugin/plugin.json:24` and `.codex-plugin/plugin.json` -- replace "epics and tasks" prose with "specs and tasks".
- `CHANGELOG.md` new top entry under `[flow-next 1.0.0] - 2026-MM-DD`:
  - **What changed.** One-paragraph executive summary.
  - **What still works.** Aliases keep all 0.x scripts and CLAUDE.md examples functional through 1.x.
  - **Two migration paths.** `/flow-next:setup` interactive vs `flowctl migrate-rename --yes` deterministic.
  - **Optional cleanup.** `sed` snippet for users who want to refresh their CLAUDE.md/AGENTS.md; optional `flowctl migrate-docs --dry-run`.
  - **Alias removal timeline.** Soft deadline at 2.0.0; telemetry-driven.
  - **Rollback.** `flowctl migrate-rollback` restores `.flow/.backup-pre-1.0/`.
  - **Known issue.** Anthropic plugin auto-update bug (anthropics/claude-code#52218) -- users may need a manual `/plugin update` to pick up bundled hook changes.
- `scripts/sync-codex.sh` self-edits at lines 31, 98, 281, 348, 532, 541, 545, 565 (per repo-scout) — T5 already shipped lines 31/98/281 (epic-scout -> spec-scout) and line 226 (worker template heredoc EPIC_ID -> SPEC_ID); T15 owns the remaining sites; add new R19 validation block scanning canonical for `flowctl epic` references except deprecation context. <!-- Updated by plan-sync: T5 partially edited sync-codex.sh; T15 picks up the rest -->
- Run `./scripts/sync-codex.sh` once -- regenerates `plugins/flow-next/codex/` from post-rename canonical state.
- OPTIONAL `flowctl migrate-docs --dry-run` helper: rewrites `flowctl epic` -> `flowctl spec` in user's CLAUDE.md / AGENTS.md after showing diff. Default `--dry-run`; `--yes` to commit. Defer if scope tight.

## Investigation targets

**Required:**
- `scripts/bump.sh` -- existing major-bump path.
- `scripts/sync-codex.sh` (full file).
- `CHANGELOG.md` -- existing entry structure for `[flow-next 0.42.0]`.
- `plugins/flow-next/.claude-plugin/plugin.json:24` -- longDescription field.

**Optional:**
- `plugins/flow-next/codex/` -- regenerated wholesale.

## Acceptance

- [ ] Plugin version is `1.0.0` in all three manifests; verified via `jq`.
- [ ] longDescription updated to use spec vocabulary in both plugin.json files.
- [ ] CHANGELOG has `[flow-next 1.0.0]` block with all 7 subsections from approach above.
- [ ] sync-codex.sh updated for agent rename + epic-review skill rename + R19 validation block.
- [ ] `./scripts/sync-codex.sh` runs cleanly; Codex mirror regenerated; no `flowctl epic` references in mirror except in deprecation-context comments.
- [ ] ci_test.sh + sync-codex.sh validation block both pass on the post-rename state.
- [ ] CHANGELOG block names alias deprecation timeline (R28) and the auto-update bug.

## Done summary
T15 final assembly: bumped flow-next to 1.0.0 across 3 manifests; updated `.codex-plugin/plugin.json` longDescription and sync-codex.sh openai.yaml short_descriptions to use "spec" vocabulary; wrote CHANGELOG `[flow-next 1.0.0]` block (7 subsections: What changed / What still works / Two migration paths / Optional cleanup / Alias removal timeline / Rollback / Known issue); regenerated Codex mirror via sync-codex.sh (23 skills, 21 agents, all R30/R19/R17/R4 guards green). Reconciled stale skill / command counts (22→23 / 17→19 / Eighteen→Nineteen) across both READMEs. Replaced "alias removed in 2.0.0" with R28-aligned soft-removal phrasing across docs/. Added `/flow-next:epic-review` deprecation-alias row to plugin README commands table. ci_test 58/58, smoke_test 130/130, alias_smoke 20/20, migration_smoke 45/45 all pass.
## Evidence
- Commits: 5643bde, 0046b67, 8fa1013, 862313b, 70b24df, ae7fb13
- Tests: bash scripts/sync-codex.sh (clean, 23 skills + 21 agents + hooks.json, all R30/R19/R17/R4 mirror guards green), bash plugins/flow-next/scripts/ci_test.sh (58/58 pass), cd /tmp && bash plugins/flow-next/scripts/smoke_test.sh (130/130 pass), cd /tmp && bash plugins/flow-next/scripts/alias_smoke.sh (20/20 pass), cd /tmp && bash plugins/flow-next/scripts/migration_smoke.sh (45/45 pass), jq verification: marketplace + claude-plugin + codex-plugin all 1.0.0 with 19 commands / 23 skills / 21 subagents, Codex impl-review (codex:gpt-5.5:high, FLOW_VALIDATE_REVIEW=1): SHIP after fresh-receipt cycle
- PRs: