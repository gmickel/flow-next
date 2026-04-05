---
name: flow-next-worktree-kit
description: Manage git worktrees (create/list/switch/cleanup) and copy .env files. Use for parallel feature work, isolated review, clean workspace, or when user mentions worktrees.
---

# Worktree kit

Use the manager script for all worktree actions.

```bash
bash ~/.codex/scripts/worktree.sh <command> [args]
```

Commands:
- `create <name> [base]`
- `list`
- `switch <name>` (prints path)
- `cleanup`
- `copy-env <name>`

Safety notes:
- `create` does not change the current branch
- `cleanup` does not force-remove worktrees and does not delete branches
- `cleanup` deletes the worktree directory (including ignored files); removal fails if the worktree is not clean
- `.env*` is copied with no overwrite (symlinks skipped)
- refuses to operate if `.worktrees/` or any worktree path component is a symlink
- `copy-env` only targets registered worktrees
- `origin` fetch is optional; local base refs are allowed
- fetch from `origin` only when base looks like a branch
- Worktrees live under `.worktrees/`
