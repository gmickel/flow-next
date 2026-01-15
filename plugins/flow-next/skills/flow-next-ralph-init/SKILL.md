---
name: flow-next-ralph-init
description: Scaffold repo-local Ralph autonomous harness under scripts/ralph/. Use when user runs /flow-next:ralph-init.
---

# Ralph init

Scaffold repo-local Ralph harness. Opt-in only.

## Rules

- Only create `scripts/ralph/` in the current repo.
- If `scripts/ralph/` already exists, stop and ask the user to remove it first.
- Copy templates from `templates/` into `scripts/ralph/`.
- Copy `flowctl` and `flowctl.py` from `${CLAUDE_PLUGIN_ROOT}/scripts/` into `scripts/ralph/`.
- Set executable bit on `scripts/ralph/ralph.sh`, `scripts/ralph/ralph_once.sh`, and `scripts/ralph/flowctl`.

## Workflow

1. Resolve repo root: `git rev-parse --show-toplevel`
2. Check `scripts/ralph/` does not exist.
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
5. Copy all files using bash (MUST use cp, NOT Write tool):
   ```bash
   mkdir -p scripts/ralph/runs
   cp -R "${CLAUDE_PLUGIN_ROOT}/skills/flow-next-ralph-init/templates/." scripts/ralph/
   cp "${CLAUDE_PLUGIN_ROOT}/scripts/flowctl" "${CLAUDE_PLUGIN_ROOT}/scripts/flowctl.py" scripts/ralph/
   chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl
   ```
   Note: `cp -R templates/.` copies all files including dotfiles (.gitignore).
6. Edit `scripts/ralph/config.env` to set the chosen review backend:
   - Replace `PLAN_REVIEW=codex` with `PLAN_REVIEW=<chosen>`
   - Replace `WORK_REVIEW=codex` with `WORK_REVIEW=<chosen>`
7. Print next steps (run from terminal, NOT inside Claude Code):
   - Edit `scripts/ralph/config.env` to customize settings
   - `./scripts/ralph/ralph_once.sh` (one iteration, observe)
   - `./scripts/ralph/ralph.sh` (full loop, AFK)
   - Uninstall: `rm -rf scripts/ralph/`
