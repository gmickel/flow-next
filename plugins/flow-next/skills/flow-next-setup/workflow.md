# Flow-Next Setup Workflow

Follow these steps in order. This workflow is **idempotent** - safe to re-run.

## Step 0: Parse arguments and resolve paths

Check if `--user` flag was passed. Set `USER_MODE=true` if so.

The plugin root is the parent of this skill's directory. From this SKILL.md location, go up to find `scripts/` and `.claude-plugin/`.

Example: if this file is at `~/.claude/plugins/cache/.../flow-next/0.3.12/skills/flow-next-setup/workflow.md`, then plugin root is `~/.claude/plugins/cache/.../flow-next/0.3.12/`.

Store this as `PLUGIN_ROOT` for use in later steps.

Set paths based on mode:
- **Project-local mode**: `BIN_DIR=".flow/bin"`
- **User-level mode**: `USER_BIN_DIR="$HOME/.config/flow-next/bin"`, `BIN_DIR=".flow/bin"` (for symlinks)

## Step 1: Check .flow/ exists

Check if `.flow/` directory exists (use Bash `ls .flow/` or check for `.flow/meta.json`).

- If `.flow/` exists: continue
- If `.flow/` doesn't exist: create it with `mkdir -p .flow` and create minimal meta.json:
  ```json
  {"schema_version": 2, "next_epic": 1}
  ```

Also ensure `.flow/config.json` exists (empty to inherit user config):
```bash
if [ ! -f .flow/config.json ]; then
  echo '{}' > .flow/config.json
fi
```

## Step 2: Check existing setup

Read `${PLUGIN_ROOT}/.claude-plugin/plugin.json` to get current plugin version.

**For user-level mode:**
- Check `~/.config/flow-next/VERSION` for existing version
- If exists and same version: "Already up to date (v<VERSION>). Update anyway? (y/n)"
- If exists and different: "Updating from v<OLD> to v<NEW>"

**For project-local mode:**
- Read `.flow/meta.json` and check for `setup_version` field
- If `setup_version` exists (already set up):
  - If **same version**: tell user "Already set up with v<VERSION>. Re-run to update docs only? (y/n)"
    - If yes: skip to Step 6 (docs)
    - If no: done
  - If **older version**: tell user "Updating from v<OLD> to v<NEW>" and continue
- If no `setup_version`: continue (first-time setup)

## Step 3: Create directories

**User-level mode:**
```bash
mkdir -p ~/.config/flow-next/bin
mkdir -p .flow/bin
```

**Project-local mode:**
```bash
mkdir -p .flow/bin
```

## Step 4: Copy/link files

**IMPORTANT: Do NOT read flowctl.py - it's too large. Just copy it.**

### User-level mode

First, backup any modified files:
```bash
if [[ -d ~/.config/flow-next/bin ]]; then
  BACKUP_DIR="$HOME/.config/flow-next/backups/$(date +%Y%m%dT%H%M%S)"
  # Check if files differ from plugin
  for f in flowctl flowctl.py; do
    if [[ -f ~/.config/flow-next/bin/$f ]]; then
      PLUGIN_HASH=$(md5sum "${PLUGIN_ROOT}/scripts/$f" | cut -d' ' -f1)
      USER_HASH=$(md5sum ~/.config/flow-next/bin/$f | cut -d' ' -f1)
      if [[ "$PLUGIN_HASH" != "$USER_HASH" ]]; then
        mkdir -p "$BACKUP_DIR"
        cp ~/.config/flow-next/bin/$f "$BACKUP_DIR/"
        diff -u "${PLUGIN_ROOT}/scripts/$f" ~/.config/flow-next/bin/$f > "$BACKUP_DIR/$f.diff" 2>/dev/null || true
        echo "Backed up: $f (modified)"
      fi
    fi
  done
fi
```

Copy to user-level:
```bash
cp "${PLUGIN_ROOT}/scripts/flowctl" ~/.config/flow-next/bin/flowctl
cp "${PLUGIN_ROOT}/scripts/flowctl.py" ~/.config/flow-next/bin/flowctl.py
chmod +x ~/.config/flow-next/bin/flowctl
```

Create symlinks in project:
```bash
ln -sf ~/.config/flow-next/bin/flowctl .flow/bin/flowctl
ln -sf ~/.config/flow-next/bin/flowctl.py .flow/bin/flowctl.py
```

Update user-level VERSION:
```bash
echo "<PLUGIN_VERSION>" > ~/.config/flow-next/VERSION
```

### Project-local mode

Copy using Bash `cp` with absolute paths:
```bash
cp "${PLUGIN_ROOT}/scripts/flowctl" .flow/bin/flowctl
cp "${PLUGIN_ROOT}/scripts/flowctl.py" .flow/bin/flowctl.py
chmod +x .flow/bin/flowctl
```

Then read [templates/usage.md](templates/usage.md) and write it to `.flow/usage.md`.

## Step 5: Update meta.json

Read current `.flow/meta.json`, add/update these fields (preserve all others):

```json
{
  "setup_version": "<PLUGIN_VERSION>",
  "setup_date": "<ISO_DATE>",
  "setup_mode": "<user|project>"
}
```

## Step 6: Check and update documentation

Read the template from [templates/claude-md-snippet.md](templates/claude-md-snippet.md).

For each of CLAUDE.md and AGENTS.md:
1. Check if file exists
2. If exists, check if `<!-- BEGIN FLOW-NEXT -->` marker exists
3. If marker exists, extract content between markers and compare with template

Determine status for each file:
- **missing**: file doesn't exist or no flow-next section
- **current**: section exists and matches template
- **outdated**: section exists but differs from template

Based on status:

**If both are current:**
```
Documentation already up to date (CLAUDE.md, AGENTS.md).
```
Skip to Step 7.

**If one or both need updates:**
Show status and ask:
```
Documentation status:
- CLAUDE.md: <missing|current|outdated>
- AGENTS.md: <missing|current|outdated>

Update docs? (Only showing files that need changes)
1. CLAUDE.md only
2. AGENTS.md only
3. Both
4. Skip

(Reply: 1, 2, 3, or 4)
```
Only show options for files that are missing or outdated.

Wait for response, then for each chosen file:
1. Read the file (create if doesn't exist)
2. If marker exists: replace everything between `<!-- BEGIN FLOW-NEXT -->` and `<!-- END FLOW-NEXT -->` (inclusive)
3. If no marker: append the snippet

## Step 7: Print summary

**User-level mode:**
```
Flow-Next setup complete! (user-level)

Installed to ~/.config/flow-next/bin/:
- flowctl (v<VERSION>)
- flowctl.py

Project symlinks in .flow/bin/

To use from command line:
  export PATH="$HOME/.config/flow-next/bin:$PATH"
  flowctl --help

Documentation updated:
- <files updated or "none">

Config hierarchy (project overrides user):
  1. ~/.config/flow-next/config.json (user defaults)
  2. .flow/config.json (project overrides)

Set user-level defaults:
  flowctl config set memory.enabled true --user

Notes:
- Re-run /flow-next:setup --user after plugin updates
- Scripts shared across all projects
- Backups: ~/.config/flow-next/backups/ (if files were modified)
```

**Project-local mode:**
```
Flow-Next setup complete!

Installed:
- .flow/bin/flowctl (v<VERSION>)
- .flow/bin/flowctl.py
- .flow/usage.md

To use from command line:
  export PATH=".flow/bin:$PATH"
  flowctl --help

Documentation updated:
- <files updated or "none">

Memory system: disabled by default
Enable for this project: flowctl config set memory.enabled true
Enable for all projects: flowctl config set memory.enabled true --user

Notes:
- Re-run /flow-next:setup after plugin updates to refresh scripts
- Uninstall: rm -rf .flow/bin .flow/usage.md and remove <!-- BEGIN/END FLOW-NEXT --> block from docs
- This setup is optional - plugin works without it
```

## Step 8: Ask about starring

Use `AskUserQuestion` to ask if the user would like to ⭐ star the repository on GitHub to support the project.

**Question:** "Flow-Next is free and open source. Would you like to ⭐ star the repo on GitHub to support the project?"

**Options:**
1. "Yes, star the repo"
2. "No thanks"

**If yes:**
1. Check if `gh` CLI is available: `which gh`
2. If available, run: `gh api -X PUT /user/starred/gmickel/gmickel-claude-marketplace`
3. If `gh` not available or command fails, provide the link:
   ```
   Star manually: https://github.com/gmickel/gmickel-claude-marketplace
   ```

**If no:** Thank them and complete setup without starring.
