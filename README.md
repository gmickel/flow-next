<div align="center">

# gmickel claude marketplace

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin_Marketplace-blueviolet)](https://claude.ai/code)

[![Flow-next](https://img.shields.io/badge/Flow--next-v0.18.0-green)](plugins/flow-next/)
[![Flow-next Docs](https://img.shields.io/badge/Docs-📖-informational)](plugins/flow-next/README.md)

[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤-ea4aaa)](https://github.com/sponsors/gmickel)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/ST5Y39hQ)

**Plugins that make AI agents actually work.**

</div>

> 💬 **[Join the Discord](https://discord.gg/ST5Y39hQ)** — discussions, updates, feature requests, bug reports
>
> 🔄 **Update issues?** Run: `claude plugin update flow-next@gmickel-claude-marketplace`
>
> 💡 **Force update (most reliable):** `/plugin` → Marketplaces → gmickel-claude-marketplace → Update marketplace
>
> 🤖 **[Ralph mode](plugins/flow-next/docs/ralph.md)**: Ship features while you sleep. Fresh context per iteration, multi-model review gates, auto-blocks stuck tasks.
>
> 💪 **Stable features**: Plan-first workflow, re-anchoring, receipt-based gating, structured task management
>
> 📡 **Cross-platform reviews**: [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) (macOS) or [Codex CLI](plugins/flow-next/README.md#cross-model-reviews) (any OS)
>
> 🧪 **OpenCode user?** Try [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) (experimental port)

---

## The Problem

Process failures, not model failures:

- Starting to code before understanding the codebase
- Reinventing patterns already there
- Forgetting the plan mid-implementation
- Skipping edge cases obvious in hindsight

This marketplace ships plugins that fix these problems.

---

## Flow-Next

**Plan first, work second. Zero external dependencies.**

```bash
# Install
/plugin marketplace add https://github.com/gmickel/gmickel-claude-marketplace
/plugin install flow-next

# Setup (configures review backend + CLI tools)
/flow-next:setup

# Use
/flow-next:plan Add a contact form with validation
/flow-next:work fn-1
```

### Why It Works

| Problem | Solution |
|---------|----------|
| Context drift | **Re-anchoring** before EVERY task — re-reads specs + git state from `.flow/` |
| 200K token limits | **Fresh context per task** — worker subagent starts clean each task |
| Single-model blind spots | **Cross-model reviews** — RepoPrompt or Codex as second opinion |
| Forgotten requirements | **Dependency graphs** — tasks declare blockers, nothing runs out of order |
| "It worked on my machine" | **Evidence recording** — commits, test output, PRs tracked per task |
| Infinite retry loops | **Auto-block stuck tasks** — fails after N attempts, moves on |
| Team conflicts | **Multi-user safe** — scan-based IDs, soft claims, no coordination server |

### Commands

| Command | What It Does |
|---------|--------------|
| `/flow-next:plan` | Research codebase, create epic + tasks |
| `/flow-next:work` | Execute tasks with re-anchoring |
| `/flow-next:interview` | Deep spec refinement (40+ questions) |
| `/flow-next:plan-review` | Cross-model plan review |
| `/flow-next:impl-review` | Cross-model implementation review |
| `/flow-next:ralph-init` | Scaffold autonomous loop |

📖 **[Full documentation](plugins/flow-next/README.md)** — CLI reference, workflow details, troubleshooting

🤔 **Confused when to use Interview vs Plan vs Work?** See [When to Use What](plugins/flow-next/README.md#when-to-use-what)

---

## Ralph (Autonomous Mode)

Run overnight, walk away. Fresh context per iteration + multi-model review gates.

```bash
/flow-next:ralph-init           # One-time setup
scripts/ralph/ralph.sh          # Run from terminal
```

**How Ralph differs:**

| Aspect | Typical Agents | Ralph |
|--------|---------------|-------|
| Context | Accumulates (drift) | Fresh each iteration |
| Review | Self-review only | Cross-model gates |
| Stuck tasks | Infinite retry | Auto-block after N failures |
| Validation | Tests only | Tests + receipts + reviews |

📖 **[Ralph deep dive](plugins/flow-next/docs/ralph.md)** — guard hooks, receipt gating, sentinel controls

🖥️ **[Ralph TUI](flow-next-tui/)** — Terminal UI for monitoring (`bun add -g @gmickel/flow-next-tui`)

---

## Install

```bash
# Add marketplace
/plugin marketplace add https://github.com/gmickel/gmickel-claude-marketplace

# Install flow-next
/plugin install flow-next

# Setup (configures review backend + CLI tools)
/flow-next:setup
```

---

## Other Plugins

| Plugin | Status |
|--------|--------|
| **flow-next** | Active development. Recommended. |
| **flow** | Legacy. [Documentation](plugins/flow/README.md) |

---

## Ecosystem

| Project | Platform |
|---------|----------|
| [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | OpenCode |
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid |

---

## Also Check Out

> **[GNO](https://gno.sh)** — Local hybrid search for your notes, docs, and code. Give Claude Code long-term memory over your files via MCP.
>
> ```bash
> bun install -g @gmickel/gno && gno mcp install --target claude-code
> ```

---

## Contributing

1. Create `plugins/<name>/` with `.claude-plugin/plugin.json`
2. Add commands/agents/skills under that plugin root
3. Update `.claude-plugin/marketplace.json`
4. Validate: `jq . .claude-plugin/marketplace.json`

---

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [@gmickel](https://twitter.com/gmickel) · [gordon@mickel.tech](mailto:gordon@mickel.tech)

[![Sponsor](https://img.shields.io/badge/Sponsor_this_project-❤-ea4aaa?style=for-the-badge)](https://github.com/sponsors/gmickel)

</div>
