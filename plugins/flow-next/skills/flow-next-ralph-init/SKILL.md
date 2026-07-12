---
name: flow-next-ralph-init
description: Scaffold repo-local Ralph autonomous harness under scripts/ralph/. Use when user runs /flow-next:ralph-init.
user-invocable: false
---

# Ralph init

Scaffold or update repo-local Ralph harness. Opt-in only.

## Preamble

## Pre-check: Local setup version

Compare `.flow/meta.json` `setup_version` to the plugin version; on mismatch, escalate once per plugin version. Fail-open throughout: a missing `jq`, `.flow/meta.json`, or plugin manifest silently continues.

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
        || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
        || "$VERSION_ACK" == "$PLUGIN_VER" ]]; then
    echo "Local setup v${SETUP_VER} differs from plugin v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts." >&2
  else
    echo "FLOW_SETUP_ASK ${SETUP_VER} ${PLUGIN_VER}"
  fi
fi
```

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with AskUserQuestion (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
  ```bash
  PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  PV=$(jq -r '.version' "$PJ" 2>/dev/null)
  [[ -n "$PV" && "$PV" != "null" ]] && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

The plugin root resolves once via the cross-platform env-var fallback (Droid uses `DROID_PLUGIN_ROOT`; Claude Code documents `CLAUDE_PLUGIN_ROOT` as its compat alias). Subsequent blocks use `$PLUGIN_ROOT`:

```bash
PLUGIN_ROOT="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}"
```

## Rules

- Only create/update `scripts/ralph/` in the current repo.
- If `scripts/ralph/` already exists, offer to update (preserves config.env).
- Copy templates from `templates/` into `scripts/ralph/`.
- Copy `flowctl`, `flowctl.cmd`, `flowctl.py` (from `$PLUGIN_ROOT/scripts/`) and `pick-python.sh` (from `$PLUGIN_ROOT/scripts/lib/`) into `scripts/ralph/` — flat, so the resolver lands at `scripts/ralph/pick-python.sh` (NOT `scripts/ralph/lib/`) where `ralph.sh` and the hook wrapper source it.
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
   HAVE_CURSOR=$(which cursor-agent >/dev/null 2>&1 && echo 1 || echo 0)
   ```

4. Determine review backend (skip if UPDATE_MODE=1):
   - If MULTIPLE available, ask user (do NOT use AskUserQuestion tool). Only
     show the options whose CLIs were detected:
     ```
     Multiple review backends available. Which one?
     a) RepoPrompt (macOS, visual builder)
     b) Codex CLI (cross-platform, GPT 5.5 High)
     c) GitHub Copilot CLI (cross-platform, Claude/GPT via Copilot)
     d) Cursor CLI (cross-platform, runs cursor-agent; gpt-5.5-high via Cursor subscription)

     (Reply: "a", "rp", "b", "codex", "c", "copilot", "d", "cursor", or just tell me)
     ```
     Wait for response. Default if empty/ambiguous: prefer `rp` > `codex` > `copilot` > `cursor`.
   - If only rp-cli available: use `rp`
   - If only codex available: use `codex`
   - If only copilot available: use `copilot`
   - If only cursor-agent available: use `cursor`
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
   cp "$PLUGIN_ROOT/scripts/flowctl" "$PLUGIN_ROOT/scripts/flowctl.cmd" "$PLUGIN_ROOT/scripts/flowctl.py" "$PLUGIN_ROOT/scripts/lib/pick-python.sh" scripts/ralph/
   mkdir -p scripts/ralph/hooks
   cp "$PLUGIN_ROOT/scripts/hooks/ralph-guard.py" "$PLUGIN_ROOT/scripts/hooks/ralph-guard" scripts/ralph/hooks/
   chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl scripts/ralph/hooks/ralph-guard.py scripts/ralph/hooks/ralph-guard

   # Restore config.env
   cp /tmp/ralph-config-backup.env scripts/ralph/config.env
   ```

   **If UPDATE_MODE=0 (fresh install):**
   ```bash
   mkdir -p scripts/ralph/runs scripts/ralph/hooks
   cp -R "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/." scripts/ralph/
   cp "$PLUGIN_ROOT/scripts/flowctl" "$PLUGIN_ROOT/scripts/flowctl.cmd" "$PLUGIN_ROOT/scripts/flowctl.py" "$PLUGIN_ROOT/scripts/lib/pick-python.sh" scripts/ralph/
   cp "$PLUGIN_ROOT/scripts/hooks/ralph-guard.py" "$PLUGIN_ROOT/scripts/hooks/ralph-guard" scripts/ralph/hooks/
   chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl scripts/ralph/hooks/ralph-guard.py scripts/ralph/hooks/ralph-guard
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
