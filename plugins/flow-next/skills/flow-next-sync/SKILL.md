---
name: flow-next-sync
description: Sync user-level Ralph scripts from plugin. Backs up local changes before updating. Use when user runs /flow-next:sync.
---

# Flow-Next Sync

Update user-level Ralph scripts from plugin templates. Creates diff backups of local changes.

## Overview

When using user-level Ralph installation (`~/.config/flow-next/ralph/`), this command:
1. Compares current scripts with plugin templates
2. Backs up any local modifications
3. Updates scripts to latest plugin version
4. Reports what changed

## Rules

- Only operates on user-level installation (`~/.config/flow-next/ralph/`)
- If user-level dir doesn't exist, suggest running `/flow-next:ralph-init --user`
- Always create backup before overwriting modified files
- Backup location: `~/.config/flow-next/ralph/backups/<timestamp>/`
- Update VERSION file after sync

## Workflow

1. Check `~/.config/flow-next/ralph/` exists
   - If not: print "No user-level Ralph found. Run `/flow-next:ralph-init --user` first."

2. Read current VERSION from `~/.config/flow-next/ralph/VERSION`
   - If missing, assume version "0.0.0"

3. Read plugin VERSION from `${CLAUDE_PLUGIN_ROOT}/VERSION`

4. Compare versions:
   - If same: print "Already up to date (version X.Y.Z)"
   - If different: proceed with sync

5. For each script file, check if modified:
   ```bash
   # Files to sync:
   ralph.sh
   ralph_once.sh
   watch-filter.py
   prompt_plan.md
   prompt_work.md
   flowctl
   flowctl.py
   ```

6. Create backup directory if any files modified:
   ```bash
   BACKUP_DIR="$HOME/.config/flow-next/ralph/backups/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$BACKUP_DIR"
   ```

7. For each modified file:
   - Create diff: `diff -u <plugin_file> <user_file> > $BACKUP_DIR/<filename>.diff`
   - Copy user file to backup: `cp <user_file> $BACKUP_DIR/<filename>`
   - Print: "Backed up: <filename> (modified)"

8. Copy all template files from plugin:
   - From: `${CLAUDE_PLUGIN_ROOT}/skills/flow-next-ralph-init/templates/`
   - To: `~/.config/flow-next/ralph/`
   - Skip: `config.env`, `runs/`, `.gitignore`

9. Copy flowctl files from plugin:
   - From: `${CLAUDE_PLUGIN_ROOT}/scripts/flowctl`, `flowctl.py`
   - To: `~/.config/flow-next/ralph/`

10. Update VERSION file:
    ```bash
    cp "${CLAUDE_PLUGIN_ROOT}/VERSION" "$HOME/.config/flow-next/ralph/VERSION"
    ```

11. Set executable bits:
    ```bash
    chmod +x ~/.config/flow-next/ralph/ralph.sh
    chmod +x ~/.config/flow-next/ralph/ralph_once.sh
    chmod +x ~/.config/flow-next/ralph/flowctl
    chmod +x ~/.config/flow-next/ralph/watch-filter.py
    ```

12. Print summary:
    ```
    Synced to version X.Y.Z
    Updated: <list of files>
    Backups: ~/.config/flow-next/ralph/backups/<timestamp>/
    ```

## Detecting Modifications

Compare file checksums (md5sum or sha256sum):
```bash
PLUGIN_HASH=$(md5sum "$PLUGIN_FILE" | cut -d' ' -f1)
USER_HASH=$(md5sum "$USER_FILE" | cut -d' ' -f1)
if [[ "$PLUGIN_HASH" != "$USER_HASH" ]]; then
  # File was modified
fi
```

## Force Mode

If user says "force" or passes `--force`:
- Skip version check
- Always sync all files
- Still create backups of modified files
