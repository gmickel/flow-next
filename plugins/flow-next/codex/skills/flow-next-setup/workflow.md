# Flow-Next Setup Workflow

Follow these steps in order. This workflow is **idempotent** - safe to re-run.

## Step 0: Resolve plugin path and detect platform

The plugin root is the parent of this skill's directory. From this SKILL.md location, go up to find `scripts/` and `.claude-plugin/`.

Example: if this file is at `~/.claude/plugins/cache/.../flow-next/0.3.12/skills/flow-next-setup/workflow.md`, then plugin root is `~/.claude/plugins/cache/.../flow-next/0.3.12/`.

Store this as `PLUGIN_ROOT` for use in later steps.

### Platform detection

Detect which platform is running:

```bash
if [ -n "${DROID_PLUGIN_ROOT:-}" ]; then
  PLATFORM="droid"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  PLATFORM="claude-code"
else
  PLATFORM="codex"
fi
```

Store `PLATFORM` for use in later steps. This determines:
- Which manifest to read for version (`plugin.json`)
- Which docs file to prefer (CLAUDE.md vs AGENTS.md)
- Whether to copy Codex agents and hooks to project

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

Also read plugin version from the platform-specific manifest:
- Codex: `${PLUGIN_ROOT}/.codex-plugin/plugin.json`
- Claude Code: `${PLUGIN_ROOT}/.claude-plugin/plugin.json`
- Factory Droid: `${PLUGIN_ROOT}/.claude-plugin/plugin.json`

Check whichever matches `PLATFORM`. Fall back to `.claude-plugin/plugin.json` if the platform-specific file doesn't exist.

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

## Step 4b: Codex-specific project setup (PLATFORM=codex only)

**Skip this step entirely if PLATFORM is not `codex`.**

On Codex, agents and hooks live in project-scoped `.codex/` directories (not in the plugin cache). Copy them:

### Copy agent .toml files

```bash
# Source: pre-built agents from plugin (or global install)
AGENTS_SRC="${PLUGIN_ROOT}/codex/agents"
[ -d "$AGENTS_SRC" ] || AGENTS_SRC="$HOME/.codex/agents"

if [ -d "$AGENTS_SRC" ]; then
  mkdir -p .codex/agents
  cp "$AGENTS_SRC"/*.toml .codex/agents/
  echo "Copied $(ls .codex/agents/*.toml 2>/dev/null | wc -l | tr -d ' ') agent configs to .codex/agents/"
else
  echo "Warning: No agent .toml files found at ${PLUGIN_ROOT}/codex/agents/ or ~/.codex/agents/"
fi
```

### Copy hooks.json

```bash
HOOKS_SRC="${PLUGIN_ROOT}/codex/hooks.json"
[ -f "$HOOKS_SRC" ] || HOOKS_SRC="$HOME/.codex/hooks.json"

if [ -f "$HOOKS_SRC" ]; then
  mkdir -p .codex
  cp "$HOOKS_SRC" .codex/hooks.json
  echo "Copied hooks.json to .codex/hooks.json"
else
  echo "Warning: No hooks.json found at ${PLUGIN_ROOT}/codex/hooks.json or ~/.codex/hooks.json"
fi
```

### Enable Codex hooks feature (if config.toml exists)

```bash
if [ -f .codex/config.toml ]; then
  if ! grep -q 'codex_hooks' .codex/config.toml 2>/dev/null; then
    echo -e '\n[features]\ncodex_hooks = true' >> .codex/config.toml
    echo "Enabled codex_hooks in .codex/config.toml"
  fi
fi
```

## Step 5: Update meta.json

Read current `.flow/meta.json`, add/update these fields (preserve all others):

```json
{
  "setup_version": "<PLUGIN_VERSION>",
  "setup_date": "<ISO_DATE>"
}
```

## Step 6: Configuration Questions

### 6a: Detect current config and tools

Before asking questions, detect available tools and read current config:

```bash
# Detect available review backends
HAVE_RP=$(which rp-cli >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_CODEX=$(which codex >/dev/null 2>&1 && echo 1 || echo 0)

# Read current config values if they exist
CURRENT_BACKEND=$("${PLUGIN_ROOT}/scripts/flowctl" config get review.backend --json 2>/dev/null | jq -r '.value // empty')
CURRENT_MEMORY=$("${PLUGIN_ROOT}/scripts/flowctl" config get memory.enabled --json 2>/dev/null | jq -r '.value // empty')
CURRENT_PLANSYNC=$("${PLUGIN_ROOT}/scripts/flowctl" config get planSync.enabled --json 2>/dev/null | jq -r '.value // empty')
CURRENT_CROSSEPIC=$("${PLUGIN_ROOT}/scripts/flowctl" config get planSync.crossEpic --json 2>/dev/null | jq -r '.value // empty')
CURRENT_GITHUB_SCOUT=$("${PLUGIN_ROOT}/scripts/flowctl" config get scouts.github --json 2>/dev/null | jq -r '.value // empty')
```

Store detection results for use in questions. When showing options, indicate current value if set (e.g., "(current)" after the matching option label).

### 6b: Check docs status

Choose the correct template based on platform:
- **Codex** (`PLATFORM=codex`): read [templates/agents-md-snippet.md](templates/agents-md-snippet.md) — uses `$flow-next-plan` syntax
- **Claude Code / Droid**: read [templates/claude-md-snippet.md](templates/claude-md-snippet.md) — uses `/flow-next:plan` syntax

For each of CLAUDE.md and AGENTS.md:
1. Check if file exists
2. If exists, check if `<!-- BEGIN FLOW-NEXT -->` marker exists
3. If marker exists, extract content between markers and compare with template

Determine status for each file:
- **missing**: file doesn't exist or no flow-next section
- **current**: section exists and matches template
- **outdated**: section exists but differs from template

### 6c: Show current config notice

If ANY config values are already set, print a notice before asking questions:

```
Current configuration:
- Memory: <enabled|disabled> (change with: flowctl config set memory.enabled <true|false>)
- Plan-Sync: <enabled|disabled> (change with: flowctl config set planSync.enabled <true|false>)
- Plan-Sync cross-epic: <enabled|disabled> (change with: flowctl config set planSync.crossEpic <true|false>)
- Review backend: <codex|rp|none> (change with: flowctl config set review.backend <codex|rp|none>)
- GitHub scout: <enabled|disabled> (change with: flowctl config set scouts.github <true|false>)
```

Only include lines for config values that are set. If no config is set, skip this notice.

### 6d: Build questions list

Build the questions array dynamically. **Only include questions for config values that are NOT already set.**

Available questions (include only if corresponding config is unset):

**Memory question** (include if CURRENT_MEMORY is empty):
```json
{
  "header": "Memory",
  "question": "Enable memory system? (Auto-captures learnings from NEEDS_WORK reviews)",
  "options": [
    {"label": "Yes (Recommended)", "description": "Auto-capture pitfalls and conventions from review feedback"},
    {"label": "No", "description": "Disable with: flowctl config set memory.enabled false"}
  ],
  "multiSelect": false
}
```

**Plan-Sync question** (include if CURRENT_PLANSYNC is empty):
```json
{
  "header": "Plan-Sync",
  "question": "Enable plan-sync? (Updates downstream task specs after implementation drift)",
  "options": [
    {"label": "Yes (Recommended)", "description": "Sync task specs when implementation differs from original plan"},
    {"label": "No", "description": "Disable with: flowctl config set planSync.enabled false"}
  ],
  "multiSelect": false
}
```

**Plan-Sync cross-epic question** (include if CURRENT_PLANSYNC is "true" AND CURRENT_CROSSEPIC is empty):
```json
{
  "header": "Cross-Epic",
  "question": "Enable cross-epic plan-sync? (Also checks other open epics for stale references)",
  "options": [
    {"label": "No (Recommended)", "description": "Only sync within current epic. Faster, avoids long Ralph loops."},
    {"label": "Yes", "description": "Also update tasks in other epics that reference changed APIs/patterns."}
  ],
  "multiSelect": false
}
```

**GitHub Scout question** (include if CURRENT_GITHUB_SCOUT is empty):
```json
{
  "header": "GitHub Scout",
  "question": "Enable GitHub scout? (Searches public/private repos for patterns during planning, requires gh CLI)",
  "options": [
    {"label": "No (Recommended)", "description": "Skip cross-repo search. Faster plans, no gh CLI needed."},
    {"label": "Yes", "description": "Search GitHub repos for patterns/examples during /flow-next:plan"}
  ],
  "multiSelect": false
}
```

**Review question** (include if CURRENT_BACKEND is empty):
```json
{
  "header": "Review",
  "question": "Which review backend for Carmack-level reviews?",
  "options": [
    {"label": "Codex CLI", "description": "Cross-platform, uses GPT 5.2 High for reviews. Simple setup, works everywhere. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, ~65% fewer tokens than traditional approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
    {"label": "None", "description": "Skip reviews, can configure later with --review flag"}
  ],
  "multiSelect": false
}
```

**Docs question** (always include — adjust default based on platform):

For **Codex** (`PLATFORM=codex`):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions?",
  "options": [
    {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (Codex reads this)"},
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Claude Code / Droid**:
```json
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
}
```

**Star question** (always include):
```json
{
  "header": "Star",
  "question": "Flow-Next is free and open source. Star the repo on GitHub?",
  "options": [
    {"label": "Yes, star it", "description": "Uses gh CLI if available, otherwise shows link"},
    {"label": "No thanks", "description": "Skip starring"}
  ],
  "multiSelect": false
}
```

Use `AskUserQuestion` with the built questions array.

**Note:** If docs are already current, adjust the Docs question description to mention "(already up to date)" or skip that question entirely.

**Note:** If neither rp-cli nor codex is detected, add note to the Review question: "Neither rp-cli nor codex detected. Install one for review support."

## Step 7: Process Answers

Only process answers for questions that were asked (config values that were unset). Skip processing for config that was already set.

**Memory** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled false --json`

**Plan-Sync** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled false --json`

**Plan-Sync cross-epic** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.crossEpic true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.crossEpic false --json`

**GitHub Scout** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set scouts.github true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set scouts.github false --json`

**Review** (if question was asked):
Map user's answer to config value and persist:

```bash
# Determine backend from answer
case "$review_answer" in
  "Codex"*) REVIEW_BACKEND="codex" ;;
  "RepoPrompt"*) REVIEW_BACKEND="rp" ;;
  *) REVIEW_BACKEND="none" ;;
esac

"${PLUGIN_ROOT}/scripts/flowctl" config set review.backend "$REVIEW_BACKEND" --json
```

**Docs:**
For each chosen file (CLAUDE.md and/or AGENTS.md):
1. Read the file (create if doesn't exist)
2. If marker exists: replace everything between `<!-- BEGIN FLOW-NEXT -->` and `<!-- END FLOW-NEXT -->` (inclusive)
3. If no marker: append the snippet

Use the correct template based on **target file** and **platform**:
- AGENTS.md on **Codex**: use [templates/agents-md-snippet.md](templates/agents-md-snippet.md) (uses `$flow-next-plan` syntax)
- AGENTS.md on **Claude Code / Droid**: use [templates/claude-md-snippet.md](templates/claude-md-snippet.md) (uses `/flow-next:plan` syntax)
- CLAUDE.md (any platform): use [templates/claude-md-snippet.md](templates/claude-md-snippet.md)

**Star:**
- If "Yes, star it":
  1. Check if `gh` CLI is available: `which gh`
  2. If available, run: `gh api -X PUT /user/starred/gmickel/gmickel-claude-marketplace`
  3. If `gh` not available or command fails, show: `Star manually: https://github.com/gmickel/gmickel-claude-marketplace`

## Step 8: Print Summary

```
Flow-Next setup complete!

Platform: <claude-code|codex|droid>

Installed:
- .flow/bin/flowctl (v<VERSION>)
- .flow/bin/flowctl.py
- .flow/usage.md
```

**If PLATFORM=codex, also show:**
```
Codex project setup:
- .codex/agents/*.toml (<N> agent configs)
- .codex/hooks.json (Ralph workflow guards)
```

**Then always show:**
```
To use from command line:
  export PATH=".flow/bin:$PATH"
  flowctl --help

Configuration (use flowctl config set to change):
- Memory: <enabled|disabled>
- Plan-Sync: <enabled|disabled>
- Plan-Sync cross-epic: <enabled|disabled>
- GitHub scout: <enabled|disabled>
- Review backend: <codex|rp|none>

Documentation updated:
- <files updated or "none">

Notes:
- Re-run /flow-next:setup after plugin updates to refresh scripts
- Interested in autonomous mode? Run /flow-next:ralph-init
- Uninstall (run manually): rm -rf .flow/bin .flow/usage.md and remove <!-- BEGIN/END FLOW-NEXT --> block from docs
- This setup is optional - plugin works without it
```
