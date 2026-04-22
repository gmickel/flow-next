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
- **Env-var documentation (task-5 finding):** in the new Copilot subsection, document the three runtime knobs landed in `config.env` / `ralph.sh`:
  - `FLOW_COPILOT_MODEL` (default `claude-opus-4.5`; catalog: claude-sonnet-4.5, claude-haiku-4.5, claude-opus-4.5, claude-sonnet-4, gpt-5.2, gpt-5.2-codex, gpt-5-mini, gpt-4.1)
  - `FLOW_COPILOT_EFFORT` (default `high`; `low|medium|high|xhigh`)
  - `FLOW_COPILOT_EMBED_MAX_BYTES` (default 512000; `0` = unlimited)
  - Note env-only resolution via `_resolve_copilot_model_effort()` (env > arg > default cascade), values stamped into every receipt (`model` + `effort` keys) for reproducibility. No CLI flags.
  - Note ralph.sh only exports these when set (conditional export at `ralph.sh:409-411`) — empty values would clobber flowctl defaults.
- `#### Which to Choose?` (line 963): add a row for Copilot in the scenario table
- Command flag reference tables (lines 1099-1199): add `copilot` to every `--review=rp|codex|export|none` enumeration
- `#### Configuration` block (line 948, line 953, line 956): update prose + comment to mention `copilot` as a valid value
<!-- Updated by plan-sync: task 5 landed FLOW_COPILOT_{MODEL,EFFORT,EMBED_MAX_BYTES} with env-cascade resolver and conditional export in ralph.sh -->

**CLAUDE.md** (repo root):
- Lines 23-24: flow-next commands block — extend `/flow-next:plan-review`/`impl-review` comments to mention all three backends (rp, codex, copilot). Not mandatory but contributor-friendly.

**flow-next-setup/workflow.md note (task-6 finding):** setup skill already lands `HAVE_COPILOT=$(which copilot ...)` detection at line 153 and a "Copilot CLI" option in the Review question (line 261) mapping to `review.backend=copilot` (line 347). README Setup/Verify for Copilot should reference the setup skill offering Copilot auto-detection — no additional skill edits needed in task 7.
<!-- Updated by plan-sync: task 6 landed HAVE_COPILOT detection + Copilot option in flow-next-setup/workflow.md; task 7 only documents it -->

**smoke_test.sh coverage note (task-6 finding):** smoke suite grew 52→59 tests (4 copilot command help checks + 3 live copilot e2e: plan-review, plan-review re-resume asserting stable session_id, impl-review). Live e2e gates on `available` (not `authed`) because `--skip-probe` returns `authed: null`; real auth failure surfaces as natural e2e failure. E2e uses `gpt-5-mini` + `FLOW_COPILOT_EFFORT=low`. CHANGELOG entry should mention new smoke coverage.
<!-- Updated by plan-sync: task 6 added 7 smoke tests (4 help + 3 live e2e); CHANGELOG should reference -->

**Generated codex mirror:**
```bash
scripts/sync-codex.sh
```
This regenerates `plugins/flow-next/codex/**` from source skills. Do NOT hand-edit codex files. Confirm task 4, 5, 6 skill changes get reflected across:
- `codex/skills/flow-next-{impl,plan,epic}-review/`
- `codex/skills/flow-next-ralph-init/` (ralph-guard.py bumped to 0.14.0 with copilot block + `copilot_review_succeeded` state key; config.env + ralph.sh templates carry `FLOW_COPILOT_*` vars; prompt_{plan,work,completion}.md carry `--review=copilot` branch per task 5)
- `codex/skills/flow-next-setup/`
- `codex/skills/flow-next-{work,plan}/` (if they have copilot references)
<!-- Updated by plan-sync: task 5 landed ralph-guard 0.14.0 + FLOW_COPILOT_* templates; sync-codex must mirror them -->

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
