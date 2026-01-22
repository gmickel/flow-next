---
name: flow-next-setup
description: Optional local install of flowctl CLI and CLAUDE.md/AGENTS.md instructions. Triggers on /flow-next:setup.
---

# Flow-Next Setup (Optional)

Install flowctl locally and add instructions to project docs. **Fully optional** - flow-next works without this via the plugin.

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"
"${PLUGIN_ROOT}/scripts/flowctl" <command>
```

## What This Skill Does

1. Initialize `.flow/` directory via `flowctl init`
2. Copy flowctl scripts to `.flow/bin/` for local CLI access
3. Ask user configuration questions (memory, plan-sync, review backend)
4. Optionally update CLAUDE.md/AGENTS.md with flow-next instructions

**You execute these steps directly.** Do NOT invoke other skills or delegate to subagents.

## Benefits

- `flowctl` accessible from command line (add `.flow/bin` to PATH)
- Other AI agents (Codex, Cursor, etc.) can read instructions from CLAUDE.md/AGENTS.md
- Works without Claude Code plugin installed

## Workflow

Read [workflow.md](workflow.md) and follow each step in order. Execute each step yourself using Bash, Read, Edit, Write, and AskUserQuestion tools.

## Notes

- **Fully optional** - standard plugin usage works without local setup
- Copies scripts (not symlinks) for portability across environments
- Safe to re-run - will detect existing setup and offer to update
