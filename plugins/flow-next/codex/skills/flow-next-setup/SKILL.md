---
name: flow-next-setup
description: Install or refresh flowctl and project instructions for flow-next in this repo. Use when asked to set up flow-next.
user-invocable: false
---

# Flow-Next Setup (Optional)

Wire this repo to the plugin: the versioned docs snippet plus flow-next configuration. **Fully optional** - flow-next works without this via the plugin.

## Benefits

- Other AI agents (Codex, Cursor, etc.) can read instructions from CLAUDE.md/AGENTS.md

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Workflow

Read [workflow.md](workflow.md) and follow each step in order.

## Notes

- **Fully optional** - standard plugin usage works without local setup
- Copies nothing into the repo - skills and flowctl update with the plugin, on any host
- Safe to re-run - needed when the changelog says the docs snippet changed, or configuration/seeds change
