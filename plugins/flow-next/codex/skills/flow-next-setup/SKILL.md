---
name: flow-next-setup
description: Optional local install of flowctl CLI and CLAUDE.md/AGENTS.md instructions. Use when user runs /flow-next:setup.
user-invocable: false
---

# Flow-Next Setup (Optional)

Install flowctl locally and add instructions to project docs. **Fully optional** - flow-next works without this via the plugin.

## Benefits

- `flowctl` accessible from command line (add `.flow/bin` to PATH)
- Other AI agents (Codex, Cursor, etc.) can read instructions from CLAUDE.md/AGENTS.md
- Works without Claude Code plugin installed

## Workflow

Read [workflow.md](workflow.md) and follow each step in order.

## Notes

- **Fully optional** - standard plugin usage works without local setup
- Copies scripts (not symlinks) for portability across environments
- Safe to re-run - will detect existing setup and offer to update
