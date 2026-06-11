---
name: flow-next-ralph-init
description: Scaffold repo-local Ralph autonomous harness under scripts/ralph/. Use when user runs /flow-next:ralph-init.
user-invocable: false
---

# Ralph init

Scaffold or update repo-local Ralph harness. Opt-in only.

## Preamble

## Pre-check: Local setup version

Non-blocking, same pattern as `/flow-next:plan` — one-line nag when the local setup lags the plugin:

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
fi
```

Continue regardless (never blocks; silent when setup was never run or versions match).

The plugin root resolves once via the cross-platform env-var fallback (Droid uses `DROID_PLUGIN_ROOT`; Claude Code documents `CLAUDE_PLUGIN_ROOT` as its compat alias). Subsequent blocks use `$PLUGIN_ROOT`:

```bash
PLUGIN_ROOT="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}"
```

## Rules

- Only create/update `scripts/ralph/` in the current repo.
- If `scripts/ralph/` already exists, offer to update (preserves config.env).
- Copy templates from `templates/` into `scripts/ralph/`.
- Copy `flowctl` and `flowctl.py` from `$PLUGIN_ROOT/scripts/` into `scripts/ralph/`.
- Set executable bit on `scripts/ralph/ralph.sh`, `scripts/ralph/ralph_once.sh`, and `scripts/ralph/flowctl`.

## Workflow

1. Resolve repo root: `git rev-parse --show-toplevel`

2. Check if `scripts/ralph/` exists:
   - If exists: ask "Update existing Ralph setup? (preserves config.env and runs/) [y/n]"
     - If no: stop
     - If yes: set UPDATE_MODE=1
   - If not exists: set UPDATE_MODE=0

3. Detect available review backends (skip if UPDATE_MODE=1):
   ```bash
   HAVE_RP=$(which rp-cli >/dev/null 2>&1 && echo 1 || echo 0)
   HAVE_CODEX=$(which codex >/dev/null 2>&1 && echo 1 || echo 0)
   HAVE_COPILOT=$(which copilot >/dev/null 2>&1 && echo 1 || echo 0)
   ```

4. Determine review backend (skip if UPDATE_MODE=1):
   - If MULTIPLE available, ask user (do NOT use AskUserQuestion tool). Only
     show the options whose CLIs were detected:
     ```
     Multiple review backends available. Which one?
     a) RepoPrompt (macOS, visual builder)
     b) Codex CLI (cross-platform, GPT 5.5 High)
     c) GitHub Copilot CLI (cross-platform, Claude/GPT via Copilot)

     (Reply: "a", "rp", "b", "codex", "c", "copilot", or just tell me)
     ```
     Wait for response. Default if empty/ambiguous: prefer `rp` > `codex` > `copilot`.
   - If only rp-cli available: use `rp`
   - If only codex available: use `codex`
   - If only copilot available: use `copilot`
   - If none available: use `none`

5. Copy files using bash (MUST use cp, NOT Write tool):

   **If UPDATE_MODE=1 (updating):**
   ```bash
   # Backup config.env
   cp scripts/ralph/config.env /tmp/ralph-config-backup.env

   # Update templates (preserves runs/)
   cp "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/ralph.sh" scripts/ralph/
   cp "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/ralph_once.sh" scripts/ralph/
   cp "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/prompt_plan.md" scripts/ralph/
   cp "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/prompt_work.md" scripts/ralph/
   cp "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/prompt_completion.md" scripts/ralph/
   cp "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/watch-filter.py" scripts/ralph/
   cp "$PLUGIN_ROOT/scripts/flowctl" "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/
   mkdir -p scripts/ralph/hooks
   cp "$PLUGIN_ROOT/scripts/hooks/ralph-guard.py" scripts/ralph/hooks/
   chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl scripts/ralph/hooks/ralph-guard.py

   # Restore config.env
   cp /tmp/ralph-config-backup.env scripts/ralph/config.env
   ```

   **If UPDATE_MODE=0 (fresh install):**
   ```bash
   mkdir -p scripts/ralph/runs scripts/ralph/hooks
   cp -R "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/." scripts/ralph/
   cp "$PLUGIN_ROOT/scripts/flowctl" "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/
   cp "$PLUGIN_ROOT/scripts/hooks/ralph-guard.py" scripts/ralph/hooks/
   chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl scripts/ralph/hooks/ralph-guard.py
   ```
   Note: `cp -R templates/.` copies all files including dotfiles (.gitignore).

6. Edit `scripts/ralph/config.env` to set the chosen review backend (skip if UPDATE_MODE=1):
   - Replace `PLAN_REVIEW={{PLAN_REVIEW}}` with `PLAN_REVIEW=<chosen>`
   - Replace `WORK_REVIEW={{WORK_REVIEW}}` with `WORK_REVIEW=<chosen>`
   - Replace `COMPLETION_REVIEW={{COMPLETION_REVIEW}}` with `COMPLETION_REVIEW=<chosen>`

7. Print next steps (run from terminal, NOT inside Claude Code):

   **If UPDATE_MODE=1:**
   ```
   Ralph updated! Your config.env was preserved.

   Changes in this version:
   - Removed local hooks requirement (plugin hooks work when installed normally)

   Run from terminal:
   - ./scripts/ralph/ralph_once.sh (one iteration, observe)
   - ./scripts/ralph/ralph.sh (full loop, AFK)
   ```

   **If UPDATE_MODE=0:**
   ```
   Ralph initialized!

   Next steps (run from terminal, NOT inside Claude Code):
   - Edit scripts/ralph/config.env to customize settings
   - ./scripts/ralph/ralph_once.sh (one iteration, observe)
   - ./scripts/ralph/ralph.sh (full loop, AFK)

   Maintenance:
   - Re-run /flow-next:ralph-init after plugin updates to refresh scripts
   - Uninstall (run manually): rm -rf scripts/ralph/
   ```
