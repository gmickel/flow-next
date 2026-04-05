<div align="center">

# Flow-Next

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Flow-next](https://img.shields.io/badge/Flow--next-v0.28.0-green)](plugins/flow-next/)
[![Docs](https://img.shields.io/badge/Docs-📖-informational)](plugins/flow-next/README.md)

[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤-ea4aaa)](https://github.com/sponsors/gmickel)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/nHEmyJB5tg)

**Plan-first AI workflow. Zero external dependencies.**

</div>

> 💬 **[Join the Discord](https://discord.gg/nHEmyJB5tg)** — discussions, updates, feature requests, bug reports

---

## What Is This?

Flow-Next is an AI agent orchestration plugin. Bundled task tracking, dependency graphs, re-anchoring, and cross-model reviews. Everything lives in your repo — no external services, no global config. Uninstall: delete `.flow/`.

Works on **Claude Code**, **OpenAI Codex** (CLI + Desktop), **Factory Droid**, and **OpenCode**.

---

## Install

<table>
<tr>
<td><strong>Claude Code</strong></td>
<td><strong>OpenAI Codex</strong></td>
<td><strong>Factory Droid</strong></td>
</tr>
<tr>
<td>

```bash
/plugin marketplace add \
  https://github.com/gmickel/flow-next
/plugin install flow-next
/flow-next:setup
```

</td>
<td>

```bash
git clone https://github.com/gmickel/flow-next.git
cd flow-next && codex
# /plugins → install Flow-Next
# then: $flow-next-setup
```

</td>
<td>

```bash
droid plugin marketplace add \
  https://github.com/gmickel/flow-next
# /plugins → install flow-next
```

</td>
</tr>
</table>

📖 **[Full docs](plugins/flow-next/README.md)** · **[Codex install guide](plugins/flow-next/README.md#openai-codex)** · **[OpenCode port](https://github.com/gmickel/flow-next-opencode)**

---

## Why It Works

| Problem | Solution |
|---------|----------|
| Context drift | **Re-anchoring** before every task — re-reads specs + git state |
| Context window limits | **Fresh context per task** — worker subagent starts clean |
| Single-model blind spots | **Cross-model reviews** — RepoPrompt or Codex as second opinion |
| Forgotten requirements | **Dependency graphs** — tasks declare blockers, run in order |
| "It worked on my machine" | **Evidence recording** — commits, tests, PRs tracked per task |
| Infinite retry loops | **Auto-block stuck tasks** — fails after N attempts, moves on |
| Duplicate implementations | **Pre-implementation search** — worker checks for similar code before writing new |

---

## Commands

| Command | What It Does |
|---------|--------------|
| `/flow-next:plan` | Research codebase, create epic + tasks |
| `/flow-next:work` | Execute tasks with re-anchoring |
| `/flow-next:interview` | Deep spec refinement (40+ questions) |
| `/flow-next:impl-review` | Cross-model implementation review |
| `/flow-next:plan-review` | Cross-model plan review |
| `/flow-next:epic-review` | Epic-completion review gate |
| `/flow-next:prime` | Assess codebase agent-readiness |
| `/flow-next:ralph-init` | Scaffold autonomous loop |

---

## Ralph (Autonomous Mode)

Run overnight. Fresh context per iteration + multi-model review gates + auto-block stuck tasks.

```bash
/flow-next:ralph-init           # One-time setup
scripts/ralph/ralph.sh          # Run from terminal
```

📖 **[Ralph deep dive](plugins/flow-next/docs/ralph.md)** · **[Ralph TUI](flow-next-tui/)** (`bun add -g @gmickel/flow-next-tui`)

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

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [@gmickel](https://twitter.com/gmickel) · [gordon@mickel.tech](mailto:gordon@mickel.tech)

[![Sponsor](https://img.shields.io/badge/Sponsor_this_project-❤-ea4aaa?style=for-the-badge)](https://github.com/sponsors/gmickel)

</div>
