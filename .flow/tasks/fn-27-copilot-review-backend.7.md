## Description

Documentation updates, `scripts/sync-codex.sh` regeneration of the codex mirror, and `scripts/bump.sh patch` for the version bump. Gates on all code + skill tasks completing.

**Size:** M
**Files:**
- `plugins/flow-next/README.md`
- `CLAUDE.md` (project guide at repo root)
- `plugins/flow-next/codex/**` (regenerated, not hand-edited)
- `.claude-plugin/marketplace.json` (bumped)
- `plugins/flow-next/.claude-plugin/plugin.json` (bumped)
- `plugins/flow-next/.codex-plugin/plugin.json` (bumped)
- `CHANGELOG.md`

## Approach

**README.md** (`plugins/flow-next/README.md`):
- `### Cross-Model Reviews` section (starts line 853): add "GitHub Copilot CLI" to intro enumeration
- Line 862: `**Review criteria (Carmack-level, identical for both backends):**` → change "both" to "all"
- Insert new `#### GitHub Copilot CLI (Cross-Platform Alternative)` subsection after the Codex subsection (after line 972). Same structure: Why use, Setup, Usage, Verify. Reference `copilot login` and fine-grained PAT with Copilot Requests permission.
- `#### Which to Choose?` (line 963): add a row for Copilot in the scenario table
- Command flag reference tables (lines 1099-1199): add `copilot` to every `--review=rp|codex|export|none` enumeration
- `#### Configuration` block (line 948, line 953, line 956): update prose + comment to mention `copilot` as a valid value

**CLAUDE.md** (repo root):
- Lines 23-24: flow-next commands block — extend `/flow-next:plan-review`/`impl-review` comments to mention all three backends (rp, codex, copilot). Not mandatory but contributor-friendly.

**Generated codex mirror:**
```bash
scripts/sync-codex.sh
```
This regenerates `plugins/flow-next/codex/**` from source skills. Do NOT hand-edit codex files. Confirm task 4 and task 5's skill changes get reflected across:
- `codex/skills/flow-next-{impl,plan,epic}-review/`
- `codex/skills/flow-next-ralph-init/`
- `codex/skills/flow-next-setup/`
- `codex/skills/flow-next-{work,plan}/` (if they have copilot references)

**Version bump:**
```bash
scripts/bump.sh patch flow-next
```
Updates all three manifest files. Per CLAUDE.md, skill + command + agent changes require a bump.

**CHANGELOG.md**: add `[flow-next X.Y.Z]` entry summarizing the new `copilot` review backend.

**Low-priority / skip unless content actually changes:**
- `plans/ralph-getting-started.md` — rp-focused; update only if copilot e2e script is added (not in scope)
- `plans/ralph-e2e-notes.md` — rp-focused; same

## Investigation targets

**Required:**
- `plugins/flow-next/README.md:853-1199` — cross-model reviews section, scenario table, flag enumerations
- `CLAUDE.md:23-24` — flow-next command block
- `scripts/sync-codex.sh` — understand what it regenerates before running
- `scripts/bump.sh` — confirm patch mode behavior
- `CHANGELOG.md` — format of existing entries

**Optional:**
- `plans/ralph-getting-started.md`, `plans/ralph-e2e-notes.md` — only skim; low-priority

## Acceptance

- [ ] `plugins/flow-next/README.md` Cross-Model Reviews section documents copilot on equal footing with codex: setup, usage, verify
- [ ] README flag tables list `rp|codex|copilot|export|none` everywhere
- [ ] `CLAUDE.md` mentions copilot as a valid review backend
- [ ] `scripts/sync-codex.sh` has been run; `plugins/flow-next/codex/**` reflects all skill changes from tasks 4, 5, 6
- [ ] `scripts/bump.sh patch flow-next` has bumped all three manifest versions consistently
- [ ] `CHANGELOG.md` has a new entry noting `copilot` review backend
- [ ] `jq . .claude-plugin/marketplace.json` and the two plugin.json files parse cleanly
- [ ] No hand edits under `plugins/flow-next/codex/**` (all via sync-codex.sh)

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
