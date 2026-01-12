---
name: flow-next-setup
description: Optional local install of flowctl CLI and CLAUDE.md/AGENTS.md instructions. Supports --user for user-level install. Use when user runs /flow-next:setup.
---

# Flow-Next Setup (Optional)

Install flowctl locally and add instructions to project docs. **Fully optional** - flow-next works without this via the plugin.

## Installation Modes

### Project-local (default)
- Installs to `.flow/bin/` in current project
- Good for: team sharing via git, portable projects

### User-level (`--user` flag)
- Installs to `~/.config/flow-next/` (shared across projects)
- Project gets symlinks to user-level scripts
- Good for: multiple projects, personal workflow, easy updates

## Benefits

- `flowctl` accessible from command line
- Other AI agents (Codex, Cursor, etc.) can read instructions from CLAUDE.md/AGENTS.md
- Works without Claude Code plugin installed

## Workflow

1. Parse arguments: check for `--user` flag
2. Read [workflow.md](workflow.md) and follow each step in order
3. Adapt paths based on mode:
   - Project-local: `.flow/bin/`
   - User-level: `~/.config/flow-next/bin/` with symlinks in `.flow/bin/`

## Notes

- **Fully optional** - standard plugin usage works without local setup
- Safe to re-run - will detect existing setup and offer to update
- User-level mode creates backups before updating modified files
