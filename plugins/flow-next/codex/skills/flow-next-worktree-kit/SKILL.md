---
name: flow-next-worktree-kit
description: Manage git worktrees (create/list/switch/cleanup) and copy .env files. Use for parallel feature work, isolated review, clean workspace, or when user mentions worktrees.
---

# Worktree kit

Use the manager script for all worktree actions.

```bash
bash "${CODEX_HOME:-$HOME/.codex}/scripts/worktree.sh" <command> [args]
```

Commands:
- `create <name> [base]`
- `list`
- `switch <name>` (prints the worktree path; it cannot change your shell's directory - use `cd "$(... switch <name>)"`)
- `cleanup [<name>...] [--yes]` (no args = interactive; names skip the prompt; `--yes` skips the confirmation, required off a terminal)
- `copy-env <name>`

Safety notes:
- `create` does not change the current branch
- `create` sets no upstream on the new branch (`--no-track`) - under the upstream-based push modes (`simple`, `upstream`, `current`) a bare `git push` cannot aim at the base branch; first push needs `git push -u origin <name>` (legacy `push.default=matching` pushes all name-matched branches regardless of upstream)
- `cleanup` does not force-remove worktrees and does not delete branches
- `cleanup` deletes the worktree directory (including ignored files); removal fails if the worktree is not clean
- `.env*` is copied with no overwrite (symlinks skipped)
- refuses to operate if `.worktrees/` or any worktree path component is a symlink
- `copy-env` only targets registered worktrees
- `origin` fetch is optional; local base refs are allowed
- fetch from `origin` only when base looks like a branch
- Worktrees live under `.worktrees/`
- `create` initializes `.worktrees/.gitignore` (`*` plus `!.gitignore`) when
 absent, so `git add -A` cannot stage nested worktrees as gitlinks; existing
 custom ignore files are preserved
