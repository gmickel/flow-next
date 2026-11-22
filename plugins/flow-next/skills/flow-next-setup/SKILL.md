---
name: flow-next-setup
description: Optional local install of flowctl CLI and CLAUDE.md/AGENTS.md instructions, plus a commented model-routing example proposed into the project instruction file. Use when user runs /flow-next:setup.
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
- Copies nothing into the repo - plugin updates need no per-repo re-run, on any host
- Safe to re-run - needed when the changelog says the docs snippet changed, or configuration/seeds change
