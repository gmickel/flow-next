---
satisfies: [R8, R14, R15]
---

## Description

Cross-platform parity verification, Codex mirror registration, full release plumbing across plugin metadata + CHANGELOG + root README + flow-next.dev docs site. Final integration task — depends on all prior tasks landing first.

**Size:** M
**Files:**
- `plugins/flow-next/docs/platforms.md` — Node 22+ "Optional skill requirements" paragraph (R8)
- `plugins/flow-next/docs/troubleshooting.md` — "clawpatch not found / version mismatch" section (R8)
- `plugins/flow-next/docs/README.md` — doc index entry for the map skill (R8)
- `plugins/flow-next/docs/flowctl.md` — verify R3's repo-map group documentation landed; cross-link from index
- `.github/workflows/test-flow-next.yml` — add two new "Python unit tests" steps for `test_repo_map.py` (fn-50.2) and `test_scout_fallback_contract.py` (fn-50.3) so they run on the full ubuntu/macos/windows matrix; add a `map_smoke_test.sh` entry wiring `plugins/flow-next/scripts/map_smoke_test.sh` (produced by fn-50.1) (R8 + R14) <!-- Updated by plan-sync: fn-50.1 produced map_smoke_test.sh — wiring is now unconditional -->
- `scripts/sync-codex.sh` — add `flow-next-map` to `REQUIRED_OPENAI_YAML_SKILLS` array (R14)
- `plugins/flow-next/codex/` — regenerated Codex mirror including flow-next-map (R14)
- `plugins/flow-next/.claude-plugin/plugin.json` — bump description **skill count `23 → 24`**; scored-criterion count stays "48" (DE7 informational); NO `version` field bump here (release-cut concern) (R15)
- `plugins/flow-next/.codex-plugin/plugin.json` — mirror the skill-count bump (R15)
- `.claude-plugin/marketplace.json` + `.agents/plugins/marketplace.json` — re-check the description (likely no edit needed; explicit re-check required by R15) (R15)
- `README.md` (root) — skill table row (Optional / enrichment section if needed) (R15)
- `CHANGELOG.md` (root) — entry **under `## [Unreleased]`** describing fn-50 (release skill dates + versions on cut) (R15)
- `GLOSSARY.md` (root) — entries for "feature map" + "features_anchored" (R15)
- `STRATEGY.md` (root) — clarifying sentence in zero-deps track (R15)
- `~/work/flow-next.dev/src/content/docs/skills/map.mdx` (new) (R15)
- `~/work/flow-next.dev/src/lib/site.ts` — nav entry in Skills → Maintenance group (NO `FLOW_NEXT_VERSION` bump here — release-cut concern) (R15)
- `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` — highlight prose staged under the unreleased section (release-cut dates + versions it) (R15)

**Explicitly NOT touched in fn-50.6** (handled at release-cut by `agent_docs/releasing.md` flow): `~/work/flow-next.dev/package.json` version field; `~/work/flow-next.dev/src/lib/site.ts` `FLOW_NEXT_VERSION`; dated `[flow-next X.Y.Z]` block in `CHANGELOG.md`; `plugin.json` `version` field.

## Approach

### R8 — Cross-platform parity verification

Cross-platform smoke matrix (manual + documented):
- macOS: shell out works via `command -v`; pnpm-global path resolves
- Linux: same as macOS
- WSL/Git Bash on Windows: `command -v` resolves npm bin shims (`.cmd`/`.ps1`); skill bash works
- Pure Windows (cmd.exe / PowerShell host): out of scope; flow-next runs in bash environments within Claude/Codex/Droid

Update `plugins/flow-next/docs/platforms.md` (model the new paragraph on the existing "Windows + Copilot" section at lines 148-157 which documents a conditional requirement). Add an **"Optional skill requirements"** subsection naming `/flow-next:map` + Node 22+ requirement.

**CI matrix coverage (per user directive at work-start time):** the GitHub Actions workflow at `.github/workflows/test-flow-next.yml` already runs the ubuntu / macos / windows matrix on bash + Python 3.11. New tests added by fn-50.2 (`test_repo_map.py`) and fn-50.3 (`test_scout_fallback_contract.py`) MUST be wired into this workflow as additional `python -m unittest discover -p "<file>"` steps so they exercise all three OSes. Drop the new test entries right after the existing "fn-43 invariants" block (lines 62-83). Pattern (verbatim shape):

```yaml
- name: Python unit tests — repo-map readers (fn-50.2)
  run: |
    python -m unittest discover \
      -s plugins/flow-next/tests \
      -p "test_repo_map.py" \
      -v

- name: Python unit tests — scout fallback contract (fn-50.3)
  run: |
    python -m unittest discover \
      -s plugins/flow-next/tests \
      -p "test_scout_fallback_contract.py" \
      -v
```

fn-50.1 produced `plugins/flow-next/scripts/map_smoke_test.sh` (65 cases — install-detect, version-range, Ralph-block, .gitignore skeleton, config-state echo, argument parsing). Add a `map_smoke_test.sh` entry alongside the other smokes, matching the `cd "$RUNNER_TEMP" && bash "$GITHUB_WORKSPACE/..."` pattern at lines 108-172. <!-- Updated by plan-sync: fn-50.1 shipped map_smoke_test.sh — conditional removed -->

**Why this matters:** Python's behavior is consistent across OSes for our usage (json + os.path + subprocess), but the Windows path-separator and PNPM_HOME quirks called out in fn-50.1's edge cases need the windows-latest runner to actually fire the test code to catch regressions. Without explicit workflow entries, new test files sit dormant and break silently when a future change drifts.

**`SUPPORTED_CLAWPATCH` version-range single source.** fn-50.1 defines the range constant in skill prose (`plugins/flow-next/skills/flow-next-map/SKILL.md`). Docs (`platforms.md`, `troubleshooting.md`, the docs-site `map.mdx`) MUST reference the skill prose generically (e.g. *"The skill carries the tested `clawpatch` version range; see `flow-next-map/SKILL.md` for the current pin"*) rather than restating the literal range. This prevents drift when the range bumps for a new clawpatch minor.

Update `plugins/flow-next/docs/troubleshooting.md` with a **"clawpatch not found / version mismatch / Node 20"** section covering the three failure modes (similar pattern to the rp-cli section at line 62).

### R14 — Codex mirror registration

Add `flow-next-map` to `REQUIRED_OPENAI_YAML_SKILLS` in `scripts/sync-codex.sh`. Pick the appropriate `generate_openai_yaml` color tag (utility `#F59E0B` amber recommended for the optional/enrichment skill — confirm against existing tags).

Run `bash scripts/sync-codex.sh` and verify clean output. Inspect `plugins/flow-next/codex/flow-next-map/` for: correct rewritten tool names (`AskUserQuestion` → numbered-prompt prose, `Task subagent_type=Explore` → `spawn_agent`), no stale fallback chains, FLOWCTL prelude is the consolidated form.

Smoke: `flowctl --help` and the new `repo-map` subcommands surface in both Claude and Codex mirror paths.

### R15 — Release plumbing

**plugin.json** (`plugins/flow-next/.claude-plugin/plugin.json` + `plugins/flow-next/.codex-plugin/plugin.json`): bump description string — skill count `23 → 24`. Criterion count depends on fn-50.5's decision (informational vs scored DE7); update accordingly.

**root `README.md`** skill table at lines 206-221: add a `/flow-next:map` row. If a clear "core" vs "optional" split would help, introduce an "Optional / enrichment" subsection; otherwise append to the existing table.

**`CHANGELOG.md`** — append under the existing `## [Unreleased]` section (NOT a dated `[flow-next X.Y.Z]` block; release-cut adds the version + date):

```
## [Unreleased]

### Added
- `/flow-next:map` skill wrapping openclaw/clawpatch's `clawpatch map` ...
- `flowctl repo-map list/show/since-ref` reader subcommands
- `repo-scout` and `context-scout` `features_anchored` optional output field
- `/flow-next:prime` DE7 sub-criterion (Pillar 5 Dev Environment — informational)
```

If `## [Unreleased]` does not currently exist at the top of CHANGELOG.md, create it. Style: match recent dated entries (1.2.1 / 1.2.0) once the release cut promotes the section.

**`GLOSSARY.md`** new entries (two lines each, terse):
- **feature map** — the `.clawpatch/features/*.json` index produced by `clawpatch map`; consumed by scouts via `flowctl repo-map`
- **features_anchored** — optional scout output field listing feature slices from the feature map that overlap the current scope

**STRATEGY.md** clarifying sentence in the "zero external dependencies" track noting `/flow-next:map` is opt-in convenience; `flowctl` core stays zero-dep.

**`~/work/flow-next.dev`** updates **in this task** (artefacts only — version bumps happen at release-cut):
- New `src/content/docs/skills/map.mdx` modeled on `prospect.mdx` or `audit.mdx`. Cover: what it does, install prerequisite, default `--source heuristic`, passthrough flags, `.clawpatch/.gitignore` skeleton, when to re-run, scout consumption.
- Nav entry in `src/lib/site.ts` Skills → Maintenance group (alphabetical position).
- Changelog highlight staged under the **unreleased / next-version** section of `src/content/docs/releases/changelog.mdx` (mirror the existing 1.2.1 prose style but leave the version + date placeholders). The release skill dates and versions on cut.
- Run `cd ~/work/flow-next.dev && pnpm build` as the docs-site gate.

**Explicitly OUT of scope for fn-50.6** (handled at release-cut time, NOT here, so that fn-50.6 can complete and merge without claiming an unreleased version on the live site):
- `~/work/flow-next.dev/package.json` `version` bump
- `~/work/flow-next.dev/src/lib/site.ts` `FLOW_NEXT_VERSION` bump
- Dated `[flow-next X.Y.Z]` block in `CHANGELOG.md` (this task stages the entry under `## [Unreleased]`)
- Plugin-side `plugin.json` `version` field bump (skill count IS bumped here; semantic version is bumped at release)

### Verification

Final gate before completion:
- `python3 -m pytest plugins/flow-next/tests/` green
- `bash plugins/flow-next/tests/scout-fallback.sh` green
- `bash scripts/sync-codex.sh` clean
- Manual: `/flow-next:map` in this repo → install instructions branch fires cleanly
- Manual: `/flow-next:prime` reports DE7 ❌ informational
- Manual: `flowctl repo-map list --json` returns count=0 without `.clawpatch/`
- `cd ~/work/flow-next.dev && pnpm build` green
- `cd ~/work/flow-next.dev` site shows the new map page + changelog highlight

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/docs/platforms.md:148-157` — existing conditional-requirement paragraph pattern
- `plugins/flow-next/docs/troubleshooting.md` (rp-cli section ~line 62) — pattern for optional-tool failure modes
- `scripts/sync-codex.sh` — `REQUIRED_OPENAI_YAML_SKILLS` array + `generate_openai_yaml` call sites
- `agent_docs/adding-skills.md:11-20` — full release-plumbing checklist for a new skill
- `plugins/flow-next/.claude-plugin/plugin.json` — description string format
- `CHANGELOG.md` top — recent entry style (1.2.1, 1.2.0)
- `~/work/flow-next.dev/src/content/docs/skills/prospect.mdx` or `audit.mdx` — skill page template

**Optional**:
- `~/work/flow-next.dev/src/lib/site.ts` nav structure — Skills → Maintenance group
- `STRATEGY.md` "zero external dependencies" track text

## Key context

- The flow-next.dev site update commits in the separate `~/work/flow-next.dev` repo, not this monorepo (per CLAUDE.md).
- `pnpm build` is the docs-site gate. Must pass before this task closes.
- Version bump for the main plugin happens at release time (not in this task — task owns the prep; release skill cuts the actual version).
- If fn-50.5 marked DE7 informational (recommended path), plugin.json description criterion-count claim stays at "48"; skill count goes 23 → 24. Adjust accordingly.

## Acceptance

- [ ] R8: `plugins/flow-next/docs/platforms.md` gains "Optional skill requirements" paragraph naming `/flow-next:map` Node 22+ requirement
- [ ] R8: `plugins/flow-next/docs/troubleshooting.md` gains clawpatch-failure-modes section (missing binary, version mismatch, Node 20)
- [ ] R8: `plugins/flow-next/docs/README.md` doc-index lists the map skill
- [ ] R14: `flow-next-map` added to `scripts/sync-codex.sh` REQUIRED_OPENAI_YAML_SKILLS; `bash scripts/sync-codex.sh` runs cleanly
- [ ] R8/R14: `.github/workflows/test-flow-next.yml` gains explicit `python -m unittest discover -p "test_repo_map.py"` step AND `python -m unittest discover -p "test_scout_fallback_contract.py"` step so both run on ubuntu/macos/windows matrix
- [ ] R8/R14: `plugins/flow-next/scripts/map_smoke_test.sh` (shipped by fn-50.1) has a matching workflow step using the existing `cd "$RUNNER_TEMP" && bash "$GITHUB_WORKSPACE/..."` pattern <!-- Updated by plan-sync: fn-50.1 shipped the smoke; entry is now mandatory -->
- [ ] R14: `plugins/flow-next/codex/flow-next-map/` exists with correct tool-name rewrites + consolidated FLOWCTL prelude
- [ ] R14: `plugins/flow-next/commands/flow-next/map.md` slash-command shim verified (already created in fn-50.1; verify here)
- [ ] R15: `plugin.json` description string updated — **skill count 23 → 24**; scored-criterion count stays "48" (DE7 informational per fn-50.5); both `.claude-plugin/` and `.codex-plugin/` mirrors
- [ ] R15: `.claude-plugin/marketplace.json` + `.agents/plugins/marketplace.json` descriptions re-checked (recorded as "no change needed" or updated as appropriate)
- [ ] R15: Root `README.md` skill table row added for `/flow-next:map`
- [ ] R15: `CHANGELOG.md` new entry staged under `## [Unreleased]` (NOT under a dated `[flow-next X.Y.Z]` block — release skill dates + versions on cut)
- [ ] R15: `GLOSSARY.md` entries for "feature map" + "features_anchored"
- [ ] R15: `STRATEGY.md` zero-deps track gains opt-in-skill clarification sentence
- [ ] R15: `~/work/flow-next.dev/src/content/docs/skills/map.mdx` exists
- [ ] R15: `~/work/flow-next.dev/src/lib/site.ts` nav entry added (alphabetical, Skills → Maintenance group). **No `FLOW_NEXT_VERSION` bump in this task.**
- [ ] R15: `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` highlight prose staged under unreleased section (no version + date — release cut fills those)
- [ ] R15: `~/work/flow-next.dev/package.json` version is **NOT** bumped in this task (release-cut concern)
- [ ] R10-supporting: `platforms.md`, `troubleshooting.md`, and `map.mdx` reference `SUPPORTED_CLAWPATCH` generically via "see `flow-next-map/SKILL.md` for the tested version pin" — they do NOT restate the literal range
- [ ] Docs-site gate: `cd ~/work/flow-next.dev && pnpm build` green
- [ ] Full repo gate: `python3 -m pytest plugins/flow-next/tests/` green + `bash plugins/flow-next/tests/scout-fallback.sh` green
- [ ] Manual smoke: `/flow-next:prime` shows DE7 informational; `flowctl repo-map list --json` returns count=0 cleanly

## Done summary
Final-integration task for fn-50: cross-platform parity docs, sync-codex.sh registration, full release plumbing across plugin metadata + CHANGELOG + GLOSSARY + STRATEGY + root README + flow-next.dev docs site. Codex review caught five real bugs in prior tasks during the wider-base re-review (sync-codex agent FLOWCTL gap, .clawpatch/.gitignore directory-level miss, set -e swallowing MAP_EXIT, prime DE7 missing FLOWCTL prelude, flowctl config text-mode false-none) — all fixed in the same task with regression-locking smoke assertions. SHIP after 4 fix cycles; 0 introduced findings remaining.
## Evidence
- Commits: 94b34e7, 114ac47, 197f300, 1f43e1e, 747c565, e9ca4e3, 7674ced
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (681 passed, 2 skipped), python3 -m unittest discover -s plugins/flow-next/tests -p test_repo_map.py (21 passed), python3 -m unittest discover -s plugins/flow-next/tests -p test_scout_fallback_contract.py (14 passed), bash plugins/flow-next/tests/scout-fallback.sh (14 passed), cd /tmp && bash plugins/flow-next/scripts/map_smoke_test.sh (75/75 passed), bash scripts/sync-codex.sh (clean, 25 skills, 21 agents, 14 validators green, byte-idempotent), cd ~/work/flow-next.dev && pnpm build (green, 51 pages, /skills/map/ rendered), Manual: flowctl repo-map list --json from /tmp returns count:0 cleanly
- PRs: