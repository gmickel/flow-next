---
name: flow-next-ralph-init
description: Scaffold Ralph autonomous harness. Supports project-local (scripts/ralph/) or user-level (~/.config/flow-next/ralph/) modes. Use when user runs /flow-next:ralph-init.
---

# Ralph init

Scaffold Ralph autonomous harness. Opt-in only. Safe to re-run for updates.

## Installation Modes

### Project-local (default)
- Everything in `scripts/ralph/` in the current repo
- Scripts, config, and runs all in one place
- Good for: single project, team sharing via git

### User-level (`--user` flag)
- Scripts in `~/.config/flow-next/ralph/` (shared across projects)
- User config in `~/.config/flow-next/ralph/config.env` (defaults)
- Project config in `scripts/ralph/config.env` (overrides)
- Runs stay in project `scripts/ralph/runs/`
- Good for: multiple projects, personal workflow, easy updates

## Rules

### Project-local mode
- Create `scripts/ralph/` in the current repo
- If exists, ask user if they want to update or skip
- Copy all templates from `templates/` into `scripts/ralph/`
- Copy `flowctl` and `flowctl.py` from `${CLAUDE_PLUGIN_ROOT}/scripts/`
- Set executable bits

### User-level mode (`--user`)
- Create `~/.config/flow-next/ralph/` if not exists
- If exists, backup modified files then update from plugin
- Copy scripts to user dir: `ralph.sh`, `ralph_once.sh`, `flowctl`, `flowctl.py`, `watch-filter.py`, `prompt_*.md`, `config.env`
- Write VERSION file to track plugin version
- In project, create `scripts/ralph/` with:
  - `config.env` (project-specific overrides)
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
5. Check `scripts/ralph/` - if exists, ask "Update existing? (y/n)"
6. Copy templates to `scripts/ralph/`
7. Copy flowctl files
8. Replace `{{PLAN_REVIEW}}` and `{{WORK_REVIEW}}` in config.env (only on first install)
9. Set executable bits

### If user-level mode (--user):
5. Check `~/.config/flow-next/ralph/VERSION` for existing version
6. If exists: backup modified files to `~/.config/flow-next/ralph/backups/<timestamp>/`
7. Copy scripts to user dir
8. Update VERSION file with plugin version
9. In project `scripts/ralph/`:
   - Create config.env if not exists (project overrides only)
   - Create/update symlinks to user scripts
   - Create `runs/` directory
10. Set executable bits on user scripts

## Print next steps

### Project-local:
- Edit `scripts/ralph/config.env` to customize settings
- `./scripts/ralph/ralph_once.sh` (one iteration, observe)
- `./scripts/ralph/ralph.sh` (full loop, AFK)
- Update: re-run `/flow-next:ralph-init`
- Uninstall: `rm -rf scripts/ralph/`

### User-level:
- Edit `~/.config/flow-next/ralph/config.env` for user defaults
- Edit `scripts/ralph/config.env` for project-specific overrides
- `./scripts/ralph/ralph.sh` (runs from user-level scripts)
- Update: re-run `/flow-next:ralph-init --user` after plugin updates
- Backups: `~/.config/flow-next/ralph/backups/` (if files were modified)
- Uninstall project: `rm -rf scripts/ralph/`
- Uninstall user-level: `rm -rf ~/.config/flow-next/ralph/`
