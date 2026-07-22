---
name: flow-next-rp-explorer
description: Token-efficient codebase exploration using RepoPrompt CLI. Use when user says "use rp to..." or "use repoprompt to..." followed by explore, find, understand, search, or similar actions.
---

# RP-Explorer

Token-efficient codebase exploration using RepoPrompt Community Edition's CLI.

## Trigger Phrases

Activates when user combines "use rp" or "use repoprompt" with an action:
- "use rp to explore how auth works"
- "use repoprompt to find similar patterns"
- "use rp to understand the data flow"
- "use repoprompt to search for API endpoints"

## CLI Reference

Read [cli-reference.md](cli-reference.md) for complete command documentation.

## Quick Start

### Step 1: Get Overview
```bash
rpce-cli -e 'tree'
rpce-cli -e 'structure .'
```

### Step 2: Find Relevant Files
```bash
rpce-cli -e 'search "auth" --context-lines 2'
rpce-cli -e 'builder "understand authentication"'
```

### Step 3: Deep Dive
```bash
rpce-cli -e 'select set src/auth/'
rpce-cli -e 'structure --scope selected'
rpce-cli -e 'read src/auth/login.ts'
```

### Step 4: Export Context
```bash
rpce-cli -e 'context --all > codebase-map.md'
```

## Token Efficiency

- Use `structure` instead of reading full files (10x fewer tokens)
- Use `builder` for AI-powered file discovery
- Select only relevant files before exporting context

## Tab Isolation

`builder` creates an isolated compose tab automatically. Use `-t` to target it:
```bash
# Builder returns: Tab: <UUID> • <Name>
rpce-cli -w W -t "<Name>" -e 'select add extra.ts && context'

# Or chain commands:
rpce-cli -w W -e 'builder "find auth" && select add extra.ts && context'
```

## Requirements

RepoPrompt CE 1.1.0+ with `rpce-cli` installed. Direct Classic `rp-cli` instructions are intentionally not used; Classic is discontinued and survives only behind Flow-Next's wrapper compatibility ladder.
