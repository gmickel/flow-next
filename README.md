<div align="center">

# Flow-Next

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Flow-next](https://img.shields.io/badge/Flow--next-v1.0.0-green)](plugins/flow-next/)
[![Docs](https://img.shields.io/badge/Docs-📖-informational)](plugins/flow-next/README.md)

[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤-ea4aaa)](https://github.com/sponsors/gmickel)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/f3DYq8AAm5)

**Plan-first AI workflow. Zero external dependencies.**

</div>

> 📖 **[Read the full docs →](plugins/flow-next/README.md)** — the main documentation. All 18 commands with reference, lifecycle workflow with mermaid diagrams, install + setup on every platform, Ralph autonomous mode, Codex / Droid / OpenCode notes, complete `flowctl` CLI reference, project glossary + strategy + decision records, memory system. **Start there if you want depth — this root page is the marketing TL;DR.**

> 👥 **[Adopting in a team? Read the teams + spec-driven-development guide →](plugins/flow-next/docs/teams.md)** — maps each SDLC stage to a Flow-Next command, names the six handover objects in the agentic lifecycle, and walks through Spec-as-PR, parallel work from one spec, R-ID frozen-at-handover, the symmetric interview pattern, and the Week 1 / Month 1 / Quarter 1 adoption ladder. Cross-links to the [AI-x-SDLC-Starter-Kit methodology guide](https://github.com/gmickel/AI-x-SDLC-Starter-Kit/blob/main/guides/methodology.md) for the underlying theory.

> 💬 **[Join the Discord](https://discord.gg/f3DYq8AAm5)** — discussions, updates, feature requests, bug reports

---

## What Is This?

Flow-Next is an AI agent orchestration plugin. **Eighteen agent-native skills** for the full lifecycle: idea → spec → tasks → review → ship → maintain. Bundled task tracking, dependency graphs, re-anchoring, multi-model reviews, decay-aware project memory, GitHub PR creation + resolution, agent-readiness audits. Everything lives in your repo — no external services, no global config. Uninstall: delete `.flow/`.

First-class on **Claude Code**, **OpenAI Codex** (CLI + Desktop), and **Factory Droid**. Also runs on **OpenCode** via the [community port](https://github.com/gmickel/flow-next-opencode).

> 🆕 **v0.42.0 — PR-as-cognitive-aid.** New `/flow-next:make-pr` skill closes the gap between "all tasks done" and "human reviews the PR" — renders a reviewable PR body from nine flow-next input streams (spec with R-IDs, per-task `done_summary` + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred review findings, the diff itself). Body sections include TL;DR, R-ID coverage table (R# → satisfying task → evidence commit), Critical changes (high-churn / cross-module / public-interface / security-sensitive / behavior-visible), Decisions, Memory, Glossary/strategy deltas, Open items, Where to look (reviewer-focus list). Mermaid codefences when the diff crosses ≥2 modules (max 3 diagrams × 12 nodes; markdown codefence — GitHub / GitLab / Gitea render natively). Default `--draft` if open items > 0 or under Ralph; `--ready` overrides. Uses `gh pr create --body-file` not heredoc (LLM-markdown safety — heredocs choke on backticks / `$` / dollar-paren). Backed by `flowctl spec export-cognitive-aid` plumbing (deterministic 9-stream JSON aggregation, reusable from any future skill / script). NOT Ralph-blocked — PR creation is the autonomous-loop terminus, Ralph defaults to `--draft` for human review. NO cross-model review of the body — each harness identifies critical changes from the structured input; `/flow-next:impl-review` already covers the *code itself*. [Full changelog](CHANGELOG.md).

> 🌐 **[Visual overview at mickel.tech/apps/flow-next](https://mickel.tech/apps/flow-next)** — diagrams, examples, the full feature tour.

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
cd flow-next
./scripts/install-codex.sh flow-next
# then: /flow-next:setup
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

**Why a script for Codex?** Codex's plugin protocol currently only registers `skills` from `plugin.json` — not custom `.toml` agents or hooks. The `/plugins` install gives you slash commands, but no subagent isolation (worker model tier, `disallowed_tools`) and no Ralph hooks. `install-codex.sh` merges all 21 agents + hooks directly into `~/.codex/config.toml` so you get the full multi-agent + Ralph experience. We'll switch to `/plugins` once Codex's manifest supports `agents` and `hooks` fields.

**Update Codex:** `cd flow-next && git pull && ./scripts/install-codex.sh flow-next`. The script is idempotent — safe to re-run on every update.

📖 **[Full docs](plugins/flow-next/README.md)** · **[Codex install guide](plugins/flow-next/README.md#openai-codex)** · **[OpenCode port](https://github.com/gmickel/flow-next-opencode)**

---

## The Workflow

```mermaid
flowchart LR
    Idea([💡 Idea]) --> P[/flow-next:prospect/]
    Idea --> C[/flow-next:capture/]
    P --> C
    P -.->|direct via promote| L[/flow-next:plan/]
    C --> L
    C --> I[/flow-next:interview/]
    I --> L
    L --> W[/flow-next:work/]
    W --> R[/flow-next:impl-review/]
    R -->|SHIP| Done([🚀 Ship])
    R -->|NEEDS_WORK| W

    Done -.maintenance.-> A[/flow-next:audit/]
    A -.-> M[(.flow/memory/)]
```

Idea → spec → tasks → ship. Branch in, branch out — pick the entry point that matches your context.

---

## Why It Works

| Problem | Solution |
|---------|----------|
| Context drift | **Re-anchoring** before every task — re-reads specs + git state |
| Context window limits | **Fresh context per task** — worker subagent starts clean |
| Single-model blind spots | **Cross-model reviews** — RepoPrompt, Codex, or Copilot as second opinion |
| Forgotten requirements | **Dependency graphs** — tasks declare blockers, run in order |
| "It worked on my machine" | **Evidence recording** — commits, tests, PRs tracked per task |
| Infinite retry loops | **Auto-block stuck tasks** — fails after N attempts, moves on |
| Duplicate implementations | **Pre-implementation search** — worker checks for similar code before writing new |
| Hallucinated specs from "I think we discussed…" | **Source-tagged capture** — every acceptance criterion marked `[user]` / `[paraphrase]` / `[inferred]`, mandatory read-back loop |
| Stale project memory polluting future work | **`/flow-next:audit` + categorized memory schema** — agent reviews each entry, flags stale (never deletes) |
| GitHub PR review threads piling up | **`/flow-next:resolve-pr`** — fetch → triage → dispatch resolver agents → reply → resolve via GraphQL |

---

## Commands

| Command | What It Does |
|---------|--------------|
| `/flow-next:prospect` | Generate ranked candidate ideas grounded in the repo, upstream of `capture`/`interview`/`plan` |
| `/flow-next:capture` | Synthesize conversation context into a spec (source-tagged, mandatory read-back) |
| `/flow-next:interview` | Deep spec refinement with lead-with-recommendation + confidence tiers + codebase-first investigation |
| `/flow-next:plan` | Research codebase, create spec + dependency-ordered tasks |
| `/flow-next:work` | Execute tasks with re-anchoring + worker subagents + review gates |
| `/flow-next:impl-review` | Cross-model implementation review (RepoPrompt, Codex, or Copilot) |
| `/flow-next:plan-review` | Cross-model plan review |
| `/flow-next:spec-completion-review` | Spec-completion review gate — verify combined implementation matches the spec (renamed from `/flow-next:epic-review` in 1.0.0; alias removed in 2.0.0) |
| `/flow-next:resolve-pr` | Resolve GitHub PR review threads (fetch → triage → fix → reply → resolve via GraphQL) |
| `/flow-next:audit` | Agent-native review of `.flow/memory/` entries against current code (Keep / Update / Consolidate / Replace / Delete) |
| `/flow-next:memory-migrate` | Lift legacy flat memory files into the categorized schema; agent classifies each entry |
| `/flow-next:prime` | 8-pillar agent-readiness assessment with parallel scouts; remediation via consent prompts |
| `/flow-next:ralph-init` | Scaffold autonomous loop (`scripts/ralph/`) |

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
