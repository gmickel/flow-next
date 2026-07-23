---
name: flow-next-setup
description: Install or refresh flowctl and project instructions for flow-next in this repo. Use when asked to set up flow-next.
user-invocable: false
---

# Flow-Next Setup (Optional)

Install flowctl locally and add instructions to project docs. **Fully optional** - flow-next works without this via the plugin.

## Benefits

- `flowctl` accessible from command line (add `.flow/bin` to PATH)
- Other AI agents (Codex, Cursor, etc.) can read instructions from CLAUDE.md/AGENTS.md
- Works without Claude Code plugin installed

## Workflow

Read [workflow.md](workflow.md) and follow each step in order.

`workflow.md` is the common router. Resolve each documented gate before reading
its direct `references/*.md` target. When a branch says **MUST read exactly
one**, read that complete reference before acting; never preload sibling host,
model-routing, model-pin, or Ralph references. Unknown/malformed routing state
uses the safe/common fallback named at that gate.

## Notes

- **Fully optional** - standard plugin usage works without local setup
- Copies scripts (not symlinks) for portability across environments
- Safe to re-run - will detect existing setup and offer to update
