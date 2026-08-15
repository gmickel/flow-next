---
name: flow-next-setup
description: Install or refresh flowctl and project instructions for flow-next in this repo. Use when asked to set up flow-next.
user-invocable: false
---

# Flow-Next Setup (Optional)

Wire this repo to the plugin: the versioned docs snippet plus flow-next configuration. **Fully optional** - flow-next works without this via the plugin.

## Benefits

- Other AI agents (Codex, Cursor, etc.) can read instructions from CLAUDE.md/AGENTS.md

## Workflow

Read [workflow.md](workflow.md) and follow each step in order.

`workflow.md` is the common router. Resolve each documented gate before reading
its direct `references/*.md` target. When a branch says **MUST read exactly
one**, read that complete reference before acting; never preload sibling host or
Ralph references. Unknown/malformed routing state
uses the safe/common fallback named at that gate.

## Notes

- **Fully optional** - standard plugin usage works without local setup
- Copies nothing into the repo - plugin updates need no per-repo re-run, on any host
- Safe to re-run - needed only when the snippet schema bumps or configuration/seeds change
