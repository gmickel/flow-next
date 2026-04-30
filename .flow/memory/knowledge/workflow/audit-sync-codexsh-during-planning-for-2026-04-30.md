---
title: Audit sync-codex.sh during planning for Codex mirror impact
date: "2026-04-30"
track: knowledge
category: workflow
module: planning
tags: [sync-codex, codex, planning, mirror, validation, subagents, tool-rewrites, openai-yaml]
applies_when: Audit sync-codex.sh during planning for Codex mirror impact
---

When planning a flow-next epic that touches skills, agents, slash commands, tool references, or skill prose, audit `scripts/sync-codex.sh` BEFORE writing tasks. The Codex mirror at `plugins/flow-next/codex/` is a derived artifact and the sync script is the single choke point — a missing sync rule silently degrades Codex parity (a real failure mode in 0.34.0-0.36.0, fixed in 0.37.1).

## What to verify during planning

**New user-facing skill** (any new `/flow-next:<name>` slash command):
- Add the skill name to the `REQUIRED_OPENAI_YAML_SKILLS` array in `scripts/sync-codex.sh` (~line 537). Validation hard-fails if missing.
- Add a `generate_openai_yaml` call (~lines 514-531). Pick the right brand color section: workflow blue `#3B82F6`, review red `#EF4444`, utility amber `#F59E0B`.
- Provide a default prompt only when it materially helps the user (capture/work/plan/prospect have one; interview/audit/setup don't).

**New tool reference** (a Claude-native tool we haven't used canonically before):
- Add a rewrite rule in the tool-name transformation block at lines 360-491 (currently handles `AskUserQuestion → request_user_input`). New tools need new sed transforms.
- Document the canonical → mirror mapping in CLAUDE.md "Cross-platform patterns" so future skill authors don't reinvent.

**New `.md` agent in `plugins/flow-next/agents/`**:
- Verify the `.md → .toml` conversion logic picks it up (sync-codex.sh walks the agents directory).
- After running sync, confirm the corresponding `.toml` file appears in `plugins/flow-next/codex/agents/`.

**New prose rule** (e.g. "no jargon X must appear in user-facing files"):
- Validation lives in **two places**, not one — mirror the existing `AskUserQuestion` / `ToolSearch` split:
  - **Canonical scan**: `ci_test.sh` greps `plugins/flow-next/skills + agents + commands + scripts/flowctl.py`
  - **Mirror scan**: `scripts/sync-codex.sh` validation block at lines 760-770 greps `plugins/flow-next/codex/skills/` and `codex/agents/`
- Mirror scan stays with the sync script because the mirror is its responsibility.

**After any prose change in skills/agents**:
- Re-run `./scripts/sync-codex.sh`. Verify zero validation errors before committing.
- The script regenerates the entire `codex/` tree; commit it alongside the canonical change.

## Why this matters

Skipping this audit during planning produces silent Codex degradation that doesn't surface for releases. Concrete past failures:
- 0.34.0-0.37.0: 4 user-facing skills (resolve-pr, prospect, audit, memory-migrate) shipped without `openai.yaml` UI metadata because nobody added the `generate_openai_yaml` call. Fixed in 0.37.1.
- Same era: skills shipped with inline cross-platform tables (`AskUserQuestion / request_user_input / ask_user`) polluting agent context because the sync rewrite responsibility wasn't centralized in the script. Also fixed in 0.37.1.

## Pattern this applies to

Any flow-next planning step that produces tasks touching:
- `plugins/flow-next/skills/**/*.md`
- `plugins/flow-next/agents/**/*.md`
- `plugins/flow-next/commands/**/*.md`
- `plugins/flow-next/scripts/flowctl.py` (when help text or argparse prose changes)
- `scripts/sync-codex.sh` itself (extending validation, rewrites, generation)

If the planned change touches any of these, the planning step MUST include a sync-codex.sh audit task or fold the audit into an existing task's acceptance.
