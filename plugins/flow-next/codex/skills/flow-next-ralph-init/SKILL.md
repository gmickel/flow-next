---
name: flow-next-ralph-init
description: Scaffold repo-local Ralph autonomous harness under scripts/ralph/. Use when user runs /flow-next:ralph-init.
user-invocable: false
---

# Ralph init

Scaffold or update repo-local Ralph harness. Opt-in only.

## Rules

- Only create/update `scripts/ralph/` in the current repo.
- If `scripts/ralph/` already exists, offer to update (preserves config.env).
- Copy templates from `templates/` into `scripts/ralph/`.
- Copy `flowctl` and `flowctl.py` from `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/` into `scripts/ralph/`.
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
   ```

4. Determine review backend (skip if UPDATE_MODE=1):
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

5. Copy files using bash (MUST use cp, NOT Write tool):

   **If UPDATE_MODE=1 (updating):**
   ```bash
   # Backup config.env
   cp scripts/ralph/config.env /tmp/ralph-config-backup.env

   # Update templates (preserves runs/)
   cp "~/.codex/templates/flow-next-ralph-init/ralph.sh" scripts/ralph/
   cp "~/.codex/templates/flow-next-ralph-init/ralph_once.sh" scripts/ralph/
   cp "~/.codex/templates/flow-next-ralph-init/prompt_plan.md" scripts/ralph/
   cp "~/.codex/templates/flow-next-ralph-init/prompt_work.md" scripts/ralph/
   cp "~/.codex/templates/flow-next-ralph-init/prompt_completion.md" scripts/ralph/
   cp "~/.codex/templates/flow-next-ralph-init/watch-filter.py" scripts/ralph/
   cp "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl" "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl.py" scripts/ralph/
   mkdir -p scripts/ralph/hooks
   cp "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/hooks/ralph-guard.py" scripts/ralph/hooks/
   chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl scripts/ralph/hooks/ralph-guard.py

   # Restore config.env
   cp /tmp/ralph-config-backup.env scripts/ralph/config.env
   ```

   **If UPDATE_MODE=0 (fresh install):**
   ```bash
   mkdir -p scripts/ralph/runs scripts/ralph/hooks
   cp -R "~/.codex/templates/flow-next-ralph-init/." scripts/ralph/
   cp "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl" "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl.py" scripts/ralph/
   cp "${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/hooks/ralph-guard.py" scripts/ralph/hooks/
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
