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
- `.flow/` directory structure (specs/, tasks/, memory/; legacy `epics/` is preserved when present, see Step 1b for migration)
- `meta.json` with schema version
- `config.json` with defaults (merges new keys on upgrade)

## Step 1b: Pre-1.0 layout detection (interactive migration arm)

Detect the pre-1.0 `.flow/` layout (epic-named directories from the 0.x era). When detected, prompt the user to migrate now, defer, or suppress the auto-detect banner permanently. This is the **interactive arm** of the consented-migrate design — the deterministic arm is `flowctl migrate-rename --yes`.

Detection rule:
- `.flow/epics/` exists AND `.flow/.flow_version` (the post-migration sentinel) is absent → pre-1.0 layout, prompt the user.
- `.flow/.flow_version` present → already migrated, skip this step entirely.
- `.flow/epics/` absent → fresh-install repo, skip this step entirely.

```bash
PRE_1_0_LAYOUT=0
if [[ -d .flow/epics && ! -f .flow/.flow_version ]]; then
  PRE_1_0_LAYOUT=1
fi
```

When `PRE_1_0_LAYOUT=1`, prompt via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.):

- **header**: `Migrate .flow/?`
- **body**: `Detected pre-1.0 .flow/ layout (.flow/epics/ present, no .flow/.flow_version sentinel). flow-next 1.0 renames .flow/epics/ to .flow/specs/ on disk; alias mode keeps the old layout working but new tooling (flow-swarm, future specs) targets the canonical layout. Recommended: Migrate now — backup is automatic and rollback is one command. Confidence: [high].`
- **options**:
  - `Migrate now` — apply migration via `flowctl migrate-rename --yes`. Safe (backup written to `.flow/.backup-pre-1.0/`, rollback via `flowctl migrate-rollback`).
  - `Defer` — keep alias mode, suppress the auto-detect banner for 7 days. Re-prompted on the next `flowctl` invocation after the window expires.
  - `Suppress permanently` — keep alias mode, never auto-prompt. Print instructions for the `FLOW_NO_AUTO_MIGRATE=1` env var so the user can suppress the banner across the whole machine.
  - `abort` — exit cleanly. No migration, no banner-ack write, no Step 2-onward setup changes. Step 1's `flowctl init` may already have run (idempotent — safe to leave). Re-run `/flow-next:setup` later to complete setup.

### Routing the answer

**Migrate now** (recommended):
```bash
"${PLUGIN_ROOT}/scripts/flowctl" migrate-rename --yes --json
```
Surface the JSON output to the user (renamed entries + sentinel write). On error, print stderr verbatim and continue to Step 2 — the user can re-run setup or use `flowctl migrate-rollback` if needed. Migration failure is non-fatal for the rest of setup.

**Defer** (suppress banner 7 days):
```bash
# migrate-rename --dry-run writes .flow/.banner-acknowledged with an ISO-8601 UTC
# timestamp ending in `Z` as a side effect (T4's banner ack contract). It also
# prints the migration plan to stdout, which is value-add for the defer experience.
"${PLUGIN_ROOT}/scripts/flowctl" migrate-rename --dry-run --json
```
The dry-run output shows the user exactly what would change if they reconsidered, and the side-effect ack-file write is the canonical way to start the 7-day re-nudge window. Do NOT hand-roll the timestamp via `Edit` / `Write` — the format must match `now_iso()` exactly (`2026-05-08T14:23:11.123456Z`).

**Suppress permanently**:
Print the user-facing instructions verbatim:
```
To suppress the migration banner permanently, set FLOW_NO_AUTO_MIGRATE=1 in your shell profile:

  export FLOW_NO_AUTO_MIGRATE=1   # ~/.bashrc / ~/.zshrc / ~/.profile

Alias mode keeps your existing .flow/epics/ layout working indefinitely.
You can still migrate later via: flowctl migrate-rename --yes
```

**abort**:
Exit 0 immediately — no migration, no banner-ack file write, no Step 2-onward setup changes. Step 1's `flowctl init --json` ran before Step 1b, so `.flow/` (meta.json, config.json, directory scaffold) may already have been created or upgraded by `init` — that work is **not** rolled back; `init` is idempotent on re-run. Only the migration + remaining setup phases (Step 2 onward — version pin, file copy, docs update) are skipped. Print:
```
Setup cancelled at migration prompt. .flow/ may have been initialized/upgraded
by Step 1 (idempotent — safe to leave). No migration applied; Step 2 onward
skipped. Re-run /flow-next:setup later to complete setup.
```

**Continue to Step 2 regardless of answer (except `abort`, which exits 0).** Migration choice is otherwise independent of the rest of setup.

## Step 2: Check existing setup

Read `.flow/meta.json` and check for `setup_version` field.

Also read plugin version from the platform-specific manifest:
- Codex: `${PLUGIN_ROOT}/.codex-plugin/plugin.json`
- Claude Code: `${PLUGIN_ROOT}/.claude-plugin/plugin.json`
- Factory Droid: `${PLUGIN_ROOT}/.factory-plugin/plugin.json`

Check whichever matches `PLATFORM`. Fall back to `.claude-plugin/plugin.json` if the platform-specific file doesn't exist.

**If `setup_version` exists (already set up):**
- If **same version**: tell user "Already set up with v<VERSION>. Re-run to refresh files + docs? (y/n)"
  - If yes: continue from Step 3 — re-copy bin + templates + docs (idempotent; same-version refresh should NOT skip the file copy, otherwise a project running an unchanged version number but a moved template lands docs that point at a missing path)
  - If no: done
- If **older version**: tell user "Updating from v<OLD> to v<NEW>" and continue

**If no `setup_version`:** continue (first-time setup)

## Step 3: Create .flow/bin/ and .flow/templates/

```bash
mkdir -p .flow/bin .flow/templates
```

## Step 4: Copy files

**IMPORTANT: Do NOT read flowctl.py - it's too large. Just copy it.**

Copy using Bash `cp` with absolute paths:

```bash
cp "${PLUGIN_ROOT}/scripts/flowctl" .flow/bin/flowctl
cp "${PLUGIN_ROOT}/scripts/flowctl.py" .flow/bin/flowctl.py
cp "${PLUGIN_ROOT}/templates/spec.md" .flow/templates/spec.md
chmod +x .flow/bin/flowctl
```

`.flow/templates/spec.md` is the canonical 7-section spec scaffold that the AGENTS.md / CLAUDE.md snippet points downstream agents at. Copying it project-local means the path the snippet references resolves without depending on the plugin install location.

Then handle `.flow/usage.md` — preserve any repo-customized variant:

1. Read [templates/usage.md](templates/usage.md) (this is the canonical content).
2. If `.flow/usage.md` does not exist → write the canonical content.
3. If `.flow/usage.md` exists → compare byte-for-byte with the canonical content:
   - **Identical**: no-op (skip the write entirely — re-running setup must not bump mtime on unchanged files).
   - **Customized** (any deviation): do NOT overwrite. Ask the user via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror):
     - **header**: `Overwrite customized .flow/usage.md?`
     - **body**: `.flow/usage.md exists and differs from the canonical template shipped with this plugin version. Overwriting replaces your edits. Keeping skips this file (you can manually merge later via diff against \`${PLUGIN_ROOT}/skills/flow-next-setup/templates/usage.md\`).`
     - **options**:
       - `Keep mine (Recommended)` — leave `.flow/usage.md` unchanged. Print the path to the canonical template so the user can diff manually.
       - `Overwrite with canonical` — replace `.flow/usage.md` with the template content. Repo customization is lost.
       - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, Step 3 mkdir, Step 4 bin/template copies above) may already have run; they are idempotent and safe to leave. No `.flow/usage.md` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

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
HAVE_COPILOT=$(which copilot >/dev/null 2>&1 && echo 1 || echo 0)

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
- Plan-Sync cross-spec: <enabled|disabled> (change with: flowctl config set planSync.crossEpic <true|false>)
- Review backend: <current value, bare or spec form> (change with: flowctl config set review.backend <codex|rp|copilot|none OR spec form like codex:gpt-5.4:xhigh>)
- GitHub scout: <enabled|disabled> (change with: flowctl config set scouts.github <true|false>)
```

Only include lines for config values that are set. If no config is set, skip this notice.

### 6d: Build questions list

Build the questions array dynamically. **Only include questions for config values that are NOT already set** — existing config is preserved, never overwritten. To change an already-set value, the user runs `flowctl config set <key> <value>` directly (the commands are surfaced in 6c's current-config notice).

Skipped questions = config values already persisted from a prior run. Asking again would either no-op (same answer) or silently flip a deliberate user choice — both are wrong. The grouped single-prompt design (a single `AskUserQuestion` call below, with one questions array containing only the unset entries) means a re-run with all config set produces zero config questions and asks only the always-include Docs + Star questions.

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

**Plan-Sync cross-spec question** (include if CURRENT_PLANSYNC is "true" AND CURRENT_CROSSEPIC is empty; the underlying config key is `planSync.crossEpic` for back-compat):
```json
{
  "header": "Cross-Spec",
  "question": "Enable cross-spec plan-sync? (Also checks other open specs for stale references)",
  "options": [
    {"label": "No (Recommended)", "description": "Only sync within current spec. Faster, avoids long Ralph loops."},
    {"label": "Yes", "description": "Also update tasks in other specs that reference changed APIs/patterns."}
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
    {"label": "Copilot CLI", "description": "Cross-platform, routes to Claude (Sonnet/Opus/Haiku 4.5) or GPT-5.2 via GitHub Copilot. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, ~65% fewer tokens than traditional approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
    {"label": "None", "description": "Skip reviews, can configure later with --review flag"}
  ],
  "multiSelect": false
}
```

Stored value is a bare backend name by default. Power users can also write a full spec like `codex:gpt-5.4:high` or `copilot:claude-opus-4.5:xhigh` via `flowctl config set review.backend <spec>` after setup — the review commands accept both forms.

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

Use `AskUserQuestion` with the built questions array (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.

**Note:** If docs are already current, adjust the Docs question description to mention "(already up to date)" or skip that question entirely.

**Note:** If none of rp-cli, codex, or copilot is detected, add note to the Review question: "No review backend detected. Install rp-cli, codex, or copilot for review support."

## Step 7: Process Answers

Only process answers for questions that were asked (config values that were unset). Skip processing for config that was already set.

**Memory** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled false --json`

**Plan-Sync** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled false --json`

**Plan-Sync cross-spec** (if question was asked; config key is `planSync.crossEpic` for back-compat):
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
  "Copilot"*|"copilot"*) REVIEW_BACKEND="copilot" ;;
  "RepoPrompt"*) REVIEW_BACKEND="rp" ;;
  *) REVIEW_BACKEND="none" ;;
esac

"${PLUGIN_ROOT}/scripts/flowctl" config set review.backend "$REVIEW_BACKEND" --json
```

**Docs:**

Use the correct template based on **target file** and **platform**:
- AGENTS.md on **Codex**: use [templates/agents-md-snippet.md](templates/agents-md-snippet.md) (uses `$flow-next-plan` syntax)
- AGENTS.md on **Claude Code / Droid**: use [templates/claude-md-snippet.md](templates/claude-md-snippet.md) (uses `/flow-next:plan` syntax)
- CLAUDE.md (any platform): use [templates/claude-md-snippet.md](templates/claude-md-snippet.md)

For each chosen file (CLAUDE.md and/or AGENTS.md) — preserve repo-custom content; only touch the marker block:

1. Read the file (create if doesn't exist).
2. **No marker block present** (`<!-- BEGIN FLOW-NEXT -->` absent): append the snippet at the end of the file. All pre-existing content outside the snippet is untouched.
3. **Marker block present** — compare current marker-block content (everything between `<!-- BEGIN FLOW-NEXT -->` and `<!-- END FLOW-NEXT -->`, inclusive) against the canonical template byte-for-byte:
   - **Identical**: no-op. Skip the write — re-running setup must not bump mtime on unchanged files.
   - **Customized** (any deviation, including whitespace): do NOT silently replace. Ask the user via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror):
     - **header**: `Overwrite customized <FILE>?` (substitute CLAUDE.md or AGENTS.md)
     - **body**: `<FILE> contains a flow-next marker block that has been customized (differs from the canonical template shipped with this plugin version). Overwriting replaces your customizations within the marker block; pre-existing content outside the markers is untouched either way.`
     - **options**:
       - `Keep mine (Recommended)` — leave the marker block unchanged. Print the path to the canonical template so the user can diff manually (`${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md`).
       - `Overwrite with canonical` — replace the marker block with the canonical snippet. Customizations inside the markers are lost; content outside the markers is preserved.
       - `abort` — exit cleanly. Earlier steps (init, file copies, config writes, prior docs-file decisions for any already-processed file) may already have run; they are idempotent and safe to leave. Remaining docs files and Star step are skipped. Re-run `/flow-next:setup` later to complete setup.

The marker-block boundaries are load-bearing: pre-existing prose outside `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` is **never** modified by this step. Only the bytes between (and including) those markers are candidates for replacement.

**Star:**
- If "Yes, star it":
  1. Check if `gh` CLI is available: `which gh`
  2. If available, run: `gh api -X PUT /user/starred/gmickel/flow-next`
  3. If `gh` not available or command fails, show: `Star manually: https://github.com/gmickel/flow-next`

## Step 8: Print Summary

```
Flow-Next setup complete!

Platform: <claude-code|codex|droid>

Installed:
- .flow/bin/flowctl (v<VERSION>)
- .flow/bin/flowctl.py
- .flow/templates/spec.md
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
- Plan-Sync cross-spec: <enabled|disabled>
- GitHub scout: <enabled|disabled>
- Review backend: <codex|rp|none>

Documentation updated:
- <files updated or "none">

Notes:
- Re-run /flow-next:setup after plugin updates to refresh scripts
- Interested in autonomous mode? Run /flow-next:ralph-init
- Uninstall (run manually): rm -rf .flow/bin .flow/templates .flow/usage.md and remove <!-- BEGIN/END FLOW-NEXT --> block from docs
- This setup is optional - plugin works without it
```
