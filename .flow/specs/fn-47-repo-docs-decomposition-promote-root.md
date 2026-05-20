# Repo docs decomposition: promote root README + flat docs/ + workflow narrative

## Overview

The repo currently maintains two READMEs — root `README.md` (~186 lines, lean) and `plugins/flow-next/README.md` (~2,719 lines, kitchen-sink). Two-README pattern is a vestige of the marketplace-ships-multiple-plugins design; the legacy `flow` plugin was removed in 1.0.2 (commit `ffc7189`). The marketplace ships ONE plugin; the repo IS flow-next.

Structural simplification:
- **Promote root README to canonical** (~300-350 lines): pitch + install + 6-step workflow narrative with links to flow-next.dev + "Where to look" table + Requirements/Platforms/License.
- **Stub plugin README** (~10-30 lines): tagline + 3-6 relative deep links into root + `docs/`. **No symlinks** (broken on GitHub per github/markup#21, #882).
- **Extract dev-reference into flat `plugins/flow-next/docs/`** — 8 new focused files alongside existing 4 (`flowctl.md`, `ralph.md`, `teams.md`, `ci-workflow-example.yml`).
- **Update CLAUDE.md** to reflect single-plugin reality + retarget "Where to look" row 1.
- **Cross-link sweep** — root README (3 sites), CLAUDE.md (1 row), `agent_docs/adding-skills.md:19`, `docs/teams.md` (11 anchor links into legacy plugin README), `docs/ralph.md:992-993`.
- **Skills directory untouched** — agent-facing only; no per-skill READMEs.
- **CHANGELOG immutable** — line-number references to plugin README in historical entries stay as-is.

Audience split: repo = "enough to get started" (offline, fork-resilient, dev-reference); flow-next.dev = "deeper guide for teams and users" (browseable, narrative, conceptual).

## Quick commands

```bash
# Phase 1 verification
ls plugins/flow-next/docs/                   # should grow to 12 files (4 existing + 8 new + index)
wc -l plugins/flow-next/docs/*.md            # each file ~50-300 lines

# Phase 2 verification — stale cross-link check
grep -rn "plugins/flow-next/README\.md" --include="*.md" --include="*.json" \
  | grep -v "CHANGELOG\.md"                  # exclude immutable changelog refs
# expected: 0 hits after sweep (or only the new stub-internal references)

# Final repo-root README length check
wc -l README.md                              # expected: ~300-350

# Plugin README is a stub
wc -l plugins/flow-next/README.md            # expected: ~10-30

# Smoke + sync (purely docs changes; should be no-op for tests)
bash plugins/flow-next/scripts/smoke_test.sh   # 130/130
./scripts/sync-codex.sh                        # validates + regenerates Codex mirror (docs aren't mirrored but skill files are)
python3 -m unittest discover -s plugins/flow-next/tests  # 612/612 expected
```

## Boundaries / non-goals

- Not creating user-facing per-skill READMEs in `plugins/flow-next/skills/<name>/`. Skills stay agent-facing.
- Not mirroring flow-next.dev's TOC in the repo `docs/` folder. Different audiences, different shapes.
- Not deleting walkthrough content that hasn't yet landed on flow-next.dev. Phase 3 coordinates with the docs-site agent for any gaps before compression.
- Not migrating `agent_docs/` (`adding-skills.md`, `releasing.md`, `local-dev.md`). They stay where they are.
- Not changing the canonical `templates/spec.md` scaffold or any skill files.
- Not removing `plugins/flow-next/README.md` entirely — keep as thin stub. External tools (Claude Code marketplace UI, plugin discoverers) may navigate to the plugin directory and expect a README.
- Not rewriting CHANGELOG line-number references in historical entries (immutable).
- Plugin version bump policy: docs-only changes don't bump version (per CLAUDE.md "For pure docs / agent_docs / README changes, do NOT bump the plugin version"). All 3 phases are docs-only → no version bump expected.
- Not coordinating with flow-next.dev content edits directly (per the "ignore other agent's WIP" rule); Phase 3 produces a handover prompt for the docs-site agent.

## Strategy Alignment

Active tracks served by this plan:
- **World-class docs as differentiator** — the repo's discovery surface (GitHub README) currently underperforms because the 2,719-line plugin README is the canonical entry. Promoting the root README + extracting reference into `docs/` puts a lean, evaluator-ready surface at the front door.
- **v1.0 vocabulary stability** — single-plugin reality (after `flow` removal in 1.0.2) becomes visible in CLAUDE.md instead of stale "ships two plugins" framing.

## Decision context

- **Promote root, stub plugin** over **keep both equal**: avoids drift; clear canonical entry surface. Evaluators landing on github.com/gmickel/flow-next see the lean version, not the kitchen-sink one.
- **Flat `docs/` folder** over **hierarchical** (no subdirs): 12 reference files are easier to navigate offline + via GitHub web UI than a deep tree. Website carries the hierarchy.
- **Stub pattern over symlink**: github/markup#21, #882 confirm symlinked READMEs don't render correctly. 10-30 line stub with relative paths + tagline + 3-6 deep links is the cleanest pattern.
- **R17 cross-link discipline** (link, never re-embed): memory entry `fn-44.5-review-r17-enforcement-beyond-2026-05-15` confirms this is review-blocking. Every new `docs/` file links the canonical source; never copies blocks of plugin README content into multiple destinations.
- **Phase ordering — dev-reference first, README promotion second, walkthrough compression third**: Phase 1 is fully self-contained (zero coordination); Phase 2 is structural reorganization (no content loss); Phase 3 is the only phase that depends on flow-next.dev coverage. Easiest → hardest, smallest blast radius per PR.
- **Close fn-39 + fn-42 before Phase 2**: scout flagged both as "open with all tasks done" touching `CLAUDE.md` + plugin README. Closed during planning to clear the merge-conflict risk.
- **README length target ~300-350 lines**: empirical band from healthy OSS repos (uv: 329, ruff: 563, bun: 446 for workflow-narrative READMEs vs cli/cli: 105 for thin-pitch). flow-next's methodology-selling shape fits the uv band.

## Acceptance

- **R1:** Root `README.md` rewritten as THE flow-next README. Final shape: tagline + badges; "What is this?" (50-second pitch); "Quick start" (install + 5-command happy path); "How the flow works" (6-step workflow narrative — Capture/Prospect → Interview → Plan → Work → Make PR → Resolve PR, plus optional Ralph — each ~5-10 lines with a link to the corresponding flow-next.dev page); "Where to look" table (task → repo docs OR website); Requirements / Platforms / License. Target: ~300-350 lines. Workflow steps self-contained for offline / fork / GitHub-discovery readers.
- **R2:** `plugins/flow-next/README.md` reduced to a thin stub (~10-30 lines): plugin name + tagline + 3-6 relative deep links — to root `README.md`, root quick-start anchor, `plugins/flow-next/docs/` (index + flowctl.md + ralph.md + teams.md). No symlink (GitHub-broken). External-surface cross-link sweep: root README badge (line 7), root README prose links (lines 18, 83), CLAUDE.md "Where to look" row (line 86), `agent_docs/adding-skills.md:19`, `docs/teams.md` 11 anchor links (lines 78, 108, 159, 189, 201, 207, 341, 357, 452, 455, 456), `docs/ralph.md:992-993`. All retargeted to root README or new `docs/<file>.md` siblings. CHANGELOG historical line-refs untouched (immutable).
- **R3:** 8 new dev-reference files in `plugins/flow-next/docs/` (flat, no subdirs):
  - `architecture.md` (~115 lines) — sources: plugin README §`.flow/ Directory` (2377-2436), §Task Completion (2505-2535), §Flow vs Flow-Next (2536-2557), §Spec-first task model (81-96), §Separation of Concerns (2432-2436).
  - `spec-template.md` (~75 lines) — sources: plugin README §Acceptance criteria (1485-1559); cross-links canonical `templates/spec.md` and the 4-tier discovery cascade (fn-46).
  - `memory-schema.md` (~205 lines) — sources: plugin README §Memory System (1609-1813); directory tree, bug/knowledge tracks, frontmatter schemas, decisions/ subtree.
  - `glossary.md` (~45 lines) — sources: plugin README §Project Glossary (1813-1856).
  - `strategy.md` (~45 lines) — sources: plugin README §Project Strategy (1857-1900).
  - `platforms.md` (~135 lines) — sources: plugin README §Other Platforms (2579-2715) — Factory Droid, OpenAI Codex (CLI + Desktop), Community Ports.
  - `sync-codex.md` (~50-80 lines) — sources: `scripts/sync-codex.sh` top-of-file comments (lines 2-141) + plugin README cross-platform notes (66, 1853, 1895). NOT primarily plugin-README-sourced.
  - `troubleshooting.md` (~80 lines) — sources: plugin README §Troubleshooting (811-876) + §Uninstall (877-889).
- **R4:** No skill READMEs created. `plugins/flow-next/skills/<name>/` directories untouched. Verified by post-PR grep: `find plugins/flow-next/skills -name "README.md"` returns nothing new.
- **R5:** Repo docs structure does NOT mirror flow-next.dev. Flat `docs/` (~12 files) vs hierarchical website (24+ pages, 7 clusters). No nested subdirs added under `docs/`.
- **R6:** `CLAUDE.md` updated: line 3 framing flipped from "ships two plugins: flow and flow-next" to single-plugin reality ("ships flow-next"; the repo IS flow-next). "Where to look" row 1 (line 86) retargeted from `plugins/flow-next/README.md` to `README.md` (root) + relevant `plugins/flow-next/docs/<file>.md` for deeper detail. Legacy `flow` removal sentinel (line 97, commit `0a45aff`) kept as historical breadcrumb.
- **R7:** `plugins/flow-next/docs/README.md` index lists all docs files (existing 4 + new 8 = 12) with a one-line description each. Main `README.md` "Where to look" table cross-links into both repo `docs/` and flow-next.dev — each row says what you're looking for + the surface (repo file OR website page) that holds it.
- **R8:** Migration sequenced in 3 PRs (one per task), each self-contained: fn-47.1 (Phase 1, dev-reference extraction) lands first with zero website dependency; fn-47.2 (Phase 2, root promotion + stub + CLAUDE.md + cross-link sweep) lands next as structural reorganization; fn-47.3 (Phase 3, walkthrough compression + flow-next.dev gap handover + final "Where to look" polish) lands last after coordinating gaps with the docs-site agent. No version bump per phase (docs-only).

## Early proof point

Task `fn-47.1` validates the source-mapping discipline: 8 new docs files can be extracted from the plugin README's identified line ranges with R17 link-don't-duplicate discipline intact. If extraction produces content that's hard to scope-isolate (e.g. §Memory System has tangled cross-refs into §Glossary), re-evaluate the file boundaries before continuing with fn-47.2 (root promotion) and fn-47.3 (compression).

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Root README rewrite (~350 lines, workflow narrative) | fn-47.2, fn-47.3 (narrative compression in .3) | — |
| R2  | Plugin README stub + cross-link sweep | fn-47.2 | — |
| R3  | 8 new docs/ files | fn-47.1 | — |
| R4  | Skills untouched | (no work; verified post-PR by grep) | — |
| R5  | Flat docs/ (no subdirs) | fn-47.1 | — |
| R6  | CLAUDE.md single-plugin framing + Where-to-look | fn-47.2 | — |
| R7  | docs/README.md index + main README Where-to-look | fn-47.2 (index), fn-47.3 (main README table) | — |
| R8  | 3-phase migration as 3 PRs | fn-47.1 / fn-47.2 / fn-47.3 | — |

## References

- Source line ranges in plugin README (repo-scout verified): §`.flow/ Directory` 2377-2436, §Task Completion 2505-2535, §Flow vs Flow-Next 2536-2557, §Acceptance criteria 1485-1559, §Memory System 1609-1813, §Project Glossary 1813-1856, §Project Strategy 1857-1900, §Other Platforms 2579-2715, §Troubleshooting 811-876, §Uninstall 877-889, §Spec-first task model 81-96.
- Walkthrough sections for Phase 3 compression: §Prospecting 349-466 (~117), §Capture 467-525 (~58), §Agent Readiness 526-716 (~190), §PR Creation 717-773 (~56), §PR Feedback Resolution 774-810 (~36), §Ralph 890-982 (~92), §Human-in-the-Loop 983-1045 (~62), §The Workflow 2234-2296 (~62), §Features 1046-1412 (~366).
- Cross-link sweep targets (verbatim grep hits): root `README.md:7,18,83`; `CLAUDE.md:3,86`; `agent_docs/adding-skills.md:19`; `plugins/flow-next/docs/teams.md:78,108,159,189,201,207,341,357,452,455,456` (anchor links into legacy plugin README); `plugins/flow-next/docs/ralph.md:992-993`.
- CHANGELOG immutable: line-number references like `CHANGELOG.md:27` mention `plugins/flow-next/README.md:1589-1594` historically; DO NOT rewrite.
- Stub pattern source: GitHub symlink rendering bugs — github/markup#21, #882. NO symlinks.
- README length precedents: anthropics/claude-code 72, cli/cli 105, astral-sh/uv 329, astral-sh/ruff 563, oven-sh/bun 446. flow-next ~350 target fits the uv/bun workflow-narrative band.
- R17 cross-link discipline: memory entry `fn-44.5-review-r17-enforcement-beyond-2026-05-15` — link, never re-embed.
- Local-dev smoke audit: memory entry `codex-mirror-smoke-docs-miss-composed-2026-05-18` — `agent_docs/local-dev.md` is the first place to break when files move; audit it explicitly during Phase 1.
- flow-next.dev page inventory (for Phase 3 gap-handover): existing pages at `~/work/flow-next.dev/src/content/docs/{introduction, flowctl/*, ralph/*, releases/*, review/*, specs/*, strategy/*, tasks/*, teams/*}.mdx`. MISSING pages for Phase 3 deep-link targets: `prospect`, `capture`, `interview`, `audit`, `prime`, `make-pr`, `resolve-pr`, `memory`. Handover prompt must enumerate.
- Prior art (docs-side review lessons): `fn-44.7-review-cycle-scoped-diff-false`, `fn-44.1-review-cycle-json-contracts-html`, `fn-44.2-review-both-pass-policy`.
- Spec deps closed during planning: fn-39 (Project Strategy / STRATEGY.md anchor), fn-42 (make-pr cognitive-aid) — both touched CLAUDE.md + plugin README; closed pre-Phase-2 to avoid conflict.
- `plugins/flow-next/docs/` existing: `flowctl.md` (1278 lines, expand only if needed), `ralph.md` (994 lines), `teams.md` (456 lines, 11 anchor links into legacy plugin README need redirect), `ci-workflow-example.yml` (31 lines).
