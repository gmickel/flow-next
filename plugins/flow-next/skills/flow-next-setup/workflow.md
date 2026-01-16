# Flow-Next Setup Workflow

Follow these steps in order. This workflow is **idempotent** - safe to re-run.

## Step 0: Resolve plugin path

The plugin root is the parent of this skill's directory. From this SKILL.md location, go up to find `scripts/` and `.claude-plugin/`.

Example: if this file is at `~/.claude/plugins/cache/.../flow-next/0.3.12/skills/flow-next-setup/workflow.md`, then plugin root is `~/.claude/plugins/cache/.../flow-next/0.3.12/`.

Store this as `PLUGIN_ROOT` for use in later steps.

## Step 1: Initialize .flow/

Use flowctl init (idempotent - safe to re-run, handles upgrades):

```bash
"${PLUGIN_ROOT}/scripts/flowctl" init --json
```

This creates/upgrades:
- `.flow/` directory structure (epics/, specs/, tasks/, memory/)
- `meta.json` with schema version
- `config.json` with defaults (merges new keys on upgrade)

## Step 2: Check existing setup

Read `.flow/meta.json` and check for `setup_version` field.

Also read `${PLUGIN_ROOT}/.claude-plugin/plugin.json` to get current plugin version.

**If `setup_version` exists (already set up):**
- If **same version**: tell user "Already set up with v<VERSION>. Re-run to update docs only? (y/n)"
  - If yes: skip to Step 6 (docs)
  - If no: done
- If **older version**: tell user "Updating from v<OLD> to v<NEW>" and continue

**If no `setup_version`:** continue (first-time setup)

## Step 3: Create .flow/bin/

```bash
mkdir -p .flow/bin
```

## Step 4: Copy files

**IMPORTANT: Do NOT read flowctl.py - it's too large. Just copy it.**

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
  "setup_date": "<ISO_DATE>"
}
```

## Step 6: Configuration Questions

First, check docs status for the question:

Read the template from [templates/claude-md-snippet.md](templates/claude-md-snippet.md).

For each of CLAUDE.md and AGENTS.md:
1. Check if file exists
2. If exists, check if `<!-- BEGIN FLOW-NEXT -->` marker exists
3. If marker exists, extract content between markers and compare with template

Determine status for each file:
- **missing**: file doesn't exist or no flow-next section
- **current**: section exists and matches template
- **outdated**: section exists but differs from template

Now use `AskUserQuestion` with all questions at once:

```json
{
  "questions": [
    {
      "header": "Memory",
      "question": "Enable memory system? (Auto-captures learnings from NEEDS_WORK reviews)",
      "options": [
        {"label": "No (Recommended)", "description": "Off by default. Enable later with: flowctl config set memory.enabled true"},
        {"label": "Yes", "description": "Auto-capture pitfalls and conventions from review feedback"}
      ],
      "multiSelect": false
    },
    {
      "header": "Plan-Sync",
      "question": "Enable plan-sync? (Updates downstream task specs after implementation drift)",
      "options": [
        {"label": "No (Recommended)", "description": "Off by default. Enable later with: flowctl config set planSync.enabled true"},
        {"label": "Yes", "description": "Sync task specs when implementation differs from original plan"}
      ],
      "multiSelect": false
    },
    {
      "header": "Docs",
      "question": "Update project documentation with Flow-Next instructions?",
      "options": [
        {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
        {"label": "AGENTS.md only", "description": "Add flow-next section to AGENTS.md"},
        {"label": "Both", "description": "Add flow-next section to both files"},
        {"label": "Skip", "description": "Don't update documentation"}
      ],
      "multiSelect": false
    },
    {
      "header": "Star",
      "question": "Flow-Next is free and open source. Star the repo on GitHub?",
      "options": [
        {"label": "Yes, star it", "description": "Uses gh CLI if available, otherwise shows link"},
        {"label": "No thanks", "description": "Skip starring"}
      ],
      "multiSelect": false
    }
  ]
}
```

**Note:** If docs are already current, adjust the Docs question description to mention "(already up to date)" or skip that question entirely.

## Step 7: Process Answers

Based on user answers:

**Memory:**
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled true --json`

**Plan-Sync:**
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled true --json`

**Docs:**
For each chosen file (CLAUDE.md and/or AGENTS.md):
1. Read the file (create if doesn't exist)
2. If marker exists: replace everything between `<!-- BEGIN FLOW-NEXT -->` and `<!-- END FLOW-NEXT -->` (inclusive)
3. If no marker: append the snippet from [templates/claude-md-snippet.md](templates/claude-md-snippet.md)

**Star:**
- If "Yes, star it":
  1. Check if `gh` CLI is available: `which gh`
  2. If available, run: `gh api -X PUT /user/starred/gmickel/gmickel-claude-marketplace`
  3. If `gh` not available or command fails, show: `Star manually: https://github.com/gmickel/gmickel-claude-marketplace`

## Step 8: Print Summary

```
Flow-Next setup complete!

Installed:
- .flow/bin/flowctl (v<VERSION>)
- .flow/bin/flowctl.py
- .flow/usage.md

To use from command line:
  export PATH=".flow/bin:$PATH"
  flowctl --help

Configuration:
- Memory: <enabled|disabled>
- Plan-Sync: <enabled|disabled>

Documentation updated:
- <files updated or "none">

Notes:
- Re-run /flow-next:setup after plugin updates to refresh scripts
- Interested in autonomous mode? Run /flow-next:ralph-init
- Uninstall: rm -rf .flow/bin .flow/usage.md and remove <!-- BEGIN/END FLOW-NEXT --> block from docs
- This setup is optional - plugin works without it
```
