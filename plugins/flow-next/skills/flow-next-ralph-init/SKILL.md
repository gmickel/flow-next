---
name: flow-next-ralph-init
description: Scaffold Ralph autonomous harness. Supports project-local (scripts/ralph/) or user-level (~/.config/flow-next/ralph/) modes. Use when user runs /flow-next:ralph-init.
---

# Ralph init

Scaffold Ralph autonomous harness. Opt-in only.

## Installation Modes

### Project-local (default)
- Everything in `scripts/ralph/` in the current repo
- Scripts, config, and runs all in one place
- Good for: single project, team sharing via git

### User-level (`--user` flag)
- Scripts in `~/.config/flow-next/ralph/` (shared across projects)
- Project gets `scripts/ralph/config.env` and symlinks
- Runs stay in project `scripts/ralph/runs/`
- Good for: multiple projects, personal workflow, auto-updates via `/flow-next:sync`

## Rules

### Project-local mode
- Create `scripts/ralph/` in the current repo
- If exists, stop and ask user to remove it first
- Copy all templates from `templates/` into `scripts/ralph/`
- Copy `flowctl` and `flowctl.py` from `${CLAUDE_PLUGIN_ROOT}/scripts/`
- Set executable bits

### User-level mode (`--user`)
- Create `~/.config/flow-next/ralph/` if not exists
- If exists, ask user if they want to update (runs /flow-next:sync) or skip
- Copy scripts to user dir: `ralph.sh`, `ralph_once.sh`, `flowctl`, `flowctl.py`, `watch-filter.py`, `prompt_*.md`
- Write VERSION file to track plugin version
- In project, create `scripts/ralph/` with:
  - `config.env` (project-specific config)
  - Symlinks: `ralph.sh -> ~/.config/flow-next/ralph/ralph.sh` etc.
  - `runs/` directory for run logs

## Workflow

1. Parse arguments: check for `--user` flag
2. Resolve repo root: `git rev-parse --show-toplevel`
3. Detect available review backends:
   ```bash
   HAVE_RP=$(which rp-cli >/dev/null 2>&1 && echo 1 || echo 0)
   HAVE_CODEX=$(which codex >/dev/null 2>&1 && echo 1 || echo 0)
   ```
4. Determine review backend:
   - If BOTH available, ask user (do NOT use AskUserQuestion tool):
     ```
     Both RepoPrompt and Codex available. Which review backend?
     a) RepoPrompt (macOS, visual builder)
     b) Codex CLI (cross-platform, GPT 5.2 High)

     (Reply: "a", "rp", "b", "codex", or just tell me)
     ```
     Wait for response. Default if empty/ambiguous: `rp`
   - If only rp-cli available: use `rp`
   - If only codex available: use `codex`
   - If neither available: use `none`

### If project-local mode (no --user):
5. Check `scripts/ralph/` does not exist
6. Copy templates to `scripts/ralph/`
7. Copy flowctl files
8. Replace `{{PLAN_REVIEW}}` and `{{WORK_REVIEW}}` in config.env
9. Set executable bits

### If user-level mode (--user):
5. Check/create `~/.config/flow-next/ralph/`
6. Copy scripts to user dir (skip config.env)
7. Write `~/.config/flow-next/ralph/VERSION` with plugin version
8. In project `scripts/ralph/`:
   - Copy config.env template, replace placeholders
   - Create symlinks to user scripts
   - Create `runs/` directory
9. Set executable bits on user scripts

## Print next steps

### Project-local:
- Edit `scripts/ralph/config.env` to customize settings
- `./scripts/ralph/ralph_once.sh` (one iteration, observe)
- `./scripts/ralph/ralph.sh` (full loop, AFK)
- Uninstall: `rm -rf scripts/ralph/`

### User-level:
- Edit `scripts/ralph/config.env` for project-specific settings
- `./scripts/ralph/ralph.sh` (runs from user-level scripts)
- Update scripts: `/flow-next:sync` (backs up changes, updates from plugin)
- Uninstall project: `rm -rf scripts/ralph/`
- Uninstall user-level: `rm -rf ~/.config/flow-next/ralph/`
