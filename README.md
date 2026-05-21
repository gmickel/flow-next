<div align="center">

# Flow-Next

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Flow-next](https://img.shields.io/badge/Flow--next-v1.1.5-green)](CHANGELOG.md)
[![Docs](https://img.shields.io/badge/Docs-📖-informational)](plugins/flow-next/docs/README.md)

[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤-ea4aaa)](https://github.com/sponsors/gmickel)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/f3DYq8AAm5)

**Plan-first AI workflow. Zero external dependencies.**

</div>

> 📖 **[Full doc index →](plugins/flow-next/docs/README.md)** · 🌐 **[flow-next.dev](https://flow-next.dev)** · 👥 **[Teams guide](plugins/flow-next/docs/teams.md)** · 💬 **[Discord](https://discord.gg/f3DYq8AAm5)**

---

## What is this?

Flow-Next is an AI agent orchestration plugin. **Twenty-three agent-native skills** for the full lifecycle: idea → spec → tasks → review → ship → maintain. Bundled task tracking, dependency graphs, re-anchoring before every task, multi-model reviews, decay-aware project memory, GitHub PR creation and resolution, agent-readiness audits. Everything lives in your repo — no external services, no global config. Uninstall: delete `.flow/`.

- **Spec-first.** Every unit of work belongs to a spec `fn-N`. Tasks `fn-N.M` inherit context.
- **Fresh-context workers.** Each task runs in its own subagent. No token bleed between tasks.
- **Cross-model reviews.** A different model (RepoPrompt / Codex / Copilot) gates every implementation.
- **R-IDs frozen at handover.** Acceptance criteria numbered once, never renumbered.

First-class on **Claude Code**, **OpenAI Codex** (CLI + Desktop), and **Factory Droid**. Also runs on **OpenCode** via the [community port](https://github.com/gmickel/flow-next-opencode).

> 🆕 **v1.0+ — `flowctl epic` → `flowctl spec`.** The 1.0 release renames the canonical primitive across the entire flow-next surface. **All 0.x scripts and CLAUDE.md examples keep working** — the legacy CLI is preserved as a deprecation alias layer through all of 1.x. See the [CHANGELOG](CHANGELOG.md) for the migration path (interactive via `/flow-next:setup` or deterministic via `flowctl migrate-rename --yes`, both transactional with rollback).

---

## Quick start

### Install

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

**Why a script for Codex?** Codex's plugin protocol only registers `skills` from `plugin.json` — not custom `.toml` agents or hooks. `install-codex.sh` merges all 21 agents + hooks into `~/.codex/config.toml`. Idempotent — safe to re-run. Full platform matrix + community ports in [`docs/platforms.md`](plugins/flow-next/docs/platforms.md).

### The 5-command happy path

```bash
/flow-next:capture                   # 1. Synthesize conversation → .flow/specs/<id>.md
/flow-next:plan <spec-id>            # 2. Break the spec into dependency-ordered tasks
/flow-next:work <spec-id>            # 3. Execute tasks in fresh-context worker subagents
/flow-next:make-pr <spec-id>         # 4. Render a cognitive-aid PR body (9 input streams)
/flow-next:resolve-pr <PR#>          # 5. Fetch review threads → triage → resolve
```

That's the inner loop. Branch in (`/flow-next:prospect` for ranked candidates, `/flow-next:interview` for structured discovery), branch out (`/flow-next:ralph-init` for autonomous overnight runs, `/flow-next:audit` for memory garbage collection).

---

## How the flow works

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

The loop is spec-driven. Each step below maps to one skill; click through to flow-next.dev for the full page.

### 1. Capture or prospect a spec

Either synthesize an existing conversation into a structured spec (source-tagged, mandatory read-back), or — when starting from scratch — generate ranked candidate ideas grounded in the repo. Both land in `.flow/specs/<id>.md`.

```bash
/flow-next:capture                    # from a conversation
/flow-next:prospect <focus-hint>      # from a focus hint (concept, path, constraint, volume)
```

→ [flow-next.dev/skills/capture](https://flow-next.dev/skills/capture) · [flow-next.dev/skills/prospect](https://flow-next.dev/skills/prospect)

### 2. Interview to refine

Deep Q&A pass over a spec or task: lead-with-recommendation, confidence tiers, codebase-first investigation. Use to flesh out an ambiguous spec before breaking it down. `--scope=business|technical|both` symmetrically narrows the pass.

```bash
/flow-next:interview <spec-id>
```

→ [flow-next.dev/skills/interview](https://flow-next.dev/skills/interview)

### 3. Plan into dependency-ordered tasks

Research the codebase, then write the spec + tasks together. Tasks `fn-N.M` declare blockers, inherit context from the parent spec, and stay dependency-ordered. This skill does not write code — only the plan.

```bash
/flow-next:plan <spec-id>             # or <free-form text>
```

→ [flow-next.dev/skills/plan](https://flow-next.dev/skills/plan)

### 4. Work through the tasks

Execute tasks systematically: each runs in a fresh-context worker subagent, re-anchors against the spec before starting, then implements + commits + records evidence. Cross-model review gates (`impl-review`, `plan-review`) wrap the loop.

```bash
/flow-next:work <spec-id>             # or <task-id>
```

→ [flow-next.dev/skills/work](https://flow-next.dev/skills/work)

### 5. Open the PR with a cognitive-aid body

Render a PR body from nine flow-next input streams (spec R-IDs, per-task evidence, memory hits, glossary changes, strategy alignment, deferred review findings, the diff itself). Optional mermaid diagrams on module-boundary changes. Pushes via `gh`.

```bash
/flow-next:make-pr <spec-id>          # auto-detects from current branch
```

→ [flow-next.dev/skills/make-pr](https://flow-next.dev/skills/make-pr)

### 6. Resolve PR review feedback

Fetch unresolved threads + top-level comments + review-submission bodies, cluster them, dispatch per-thread resolver agents (parallel on Claude Code, serial elsewhere), validate, commit, then reply + resolve via GraphQL.

```bash
/flow-next:resolve-pr <PR#>
```

→ [flow-next.dev/skills/resolve-pr](https://flow-next.dev/skills/resolve-pr)

---

**Going autonomous?** `/flow-next:ralph-init` scaffolds a repo-local Ralph harness under `scripts/ralph/`. Ralph loops the same steps overnight with fresh context per iteration, multi-model review gates, and auto-block on stuck tasks. → [flow-next.dev/ralph](https://flow-next.dev/ralph)

---

## Why it works

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

| Command | What it does |
|---------|--------------|
| `/flow-next:strategy` | Write `STRATEGY.md` — target problem, approach, users, metrics, active tracks |
| `/flow-next:prospect` | Generate ranked candidate ideas grounded in the repo, upstream of `capture`/`interview`/`plan` |
| `/flow-next:capture` | Synthesize conversation context into a spec (source-tagged, mandatory read-back) |
| `/flow-next:interview` | Deep spec refinement with lead-with-recommendation + confidence tiers + codebase-first investigation; `--scope=business\|technical\|both` |
| `/flow-next:plan` | Research codebase, create spec + dependency-ordered tasks |
| `/flow-next:work` | Execute tasks with re-anchoring + worker subagents + review gates |
| `/flow-next:impl-review` | Cross-model implementation review (RepoPrompt, Codex, or Copilot) |
| `/flow-next:plan-review` | Cross-model plan review |
| `/flow-next:spec-completion-review` | Spec-completion review gate — verify combined implementation matches the spec (renamed from `/flow-next:epic-review` in 1.0.0; soft-removal target 2.0.0) |
| `/flow-next:make-pr` | Render a cognitive-aid PR body (9 input streams) and open via `gh` |
| `/flow-next:resolve-pr` | Resolve GitHub PR review threads (fetch → triage → fix → reply → resolve via GraphQL) |
| `/flow-next:audit` | Agent-native review of `.flow/memory/` entries against current code (Keep / Update / Consolidate / Replace / Delete) |
| `/flow-next:memory-migrate` | Lift legacy flat memory files into the categorized schema |
| `/flow-next:prime` | 8-pillar agent-readiness assessment with parallel scouts; remediation via consent prompts |
| `/flow-next:ralph-init` | Scaffold autonomous loop (`scripts/ralph/`) |
| `/flow-next:sync` | Manually trigger plan-sync to update downstream task specs after drift |

Full command reference (every flag, every default) in [`docs/flowctl.md`](plugins/flow-next/docs/flowctl.md).

---

## Ralph (autonomous mode)

Run overnight. Fresh context per iteration + multi-model review gates + auto-block stuck tasks.

```bash
/flow-next:ralph-init           # One-time setup
scripts/ralph/ralph.sh          # Run from terminal
```

📖 **[Ralph deep dive](plugins/flow-next/docs/ralph.md)** · **[Ralph TUI](flow-next-tui/)** (`bun add -g @gmickel/flow-next-tui`)

---

## Where to look

The repo holds the offline-resilient reference. [flow-next.dev](https://flow-next.dev) holds the narrative, browseable guide. Pick by audience.

| Looking for… | Repo file | Website |
|---|---|---|
| 5-minute pitch + install | `README.md` (this page) | [flow-next.dev](https://flow-next.dev) |
| Adopting in a team, handover objects, Spec-as-PR, adoption ladder | [`docs/teams.md`](plugins/flow-next/docs/teams.md) | [Teams guide](https://flow-next.dev) |
| Full `flowctl` CLI reference — every command, every flag | [`docs/flowctl.md`](plugins/flow-next/docs/flowctl.md) | — |
| Ralph autonomous mode internals — hooks, receipts, DCG | [`docs/ralph.md`](plugins/flow-next/docs/ralph.md) | — |
| `.flow/` directory layout, spec-first task model, ID format | [`docs/architecture.md`](plugins/flow-next/docs/architecture.md) | — |
| Spec template — R-ID rules, confidence anchors, receipt schema | [`docs/spec-template.md`](plugins/flow-next/docs/spec-template.md) · canonical scaffold at [`templates/spec.md`](plugins/flow-next/templates/spec.md) | — |
| Memory schema — bug / knowledge tracks, frontmatter, audit lifecycle | [`docs/memory-schema.md`](plugins/flow-next/docs/memory-schema.md) | — |
| Project glossary — `GLOSSARY.md` shape, R17 forbidden-vocabulary guard | [`docs/glossary.md`](plugins/flow-next/docs/glossary.md) · [`GLOSSARY.md`](GLOSSARY.md) | — |
| Project strategy — `STRATEGY.md` shape, downstream skill grounding | [`docs/strategy.md`](plugins/flow-next/docs/strategy.md) · [`STRATEGY.md`](STRATEGY.md) | — |
| Cross-platform install matrix + Codex / Droid / OpenCode notes | [`docs/platforms.md`](plugins/flow-next/docs/platforms.md) | — |
| `scripts/sync-codex.sh` pipeline, plain-text transform, validation guards | [`docs/sync-codex.md`](plugins/flow-next/docs/sync-codex.md) | — |
| Troubleshooting — stuck tasks, Ralph debug, receipt validation, uninstall | [`docs/troubleshooting.md`](plugins/flow-next/docs/troubleshooting.md) | — |
| Adding a new `/flow-next:<name>` skill | [`agent_docs/adding-skills.md`](agent_docs/adding-skills.md) | — |
| Cutting a release | [`agent_docs/releasing.md`](agent_docs/releasing.md) | — |
| Local plugin dev + smoke tests + Ralph e2e | [`agent_docs/local-dev.md`](agent_docs/local-dev.md) | — |
| Repo strategic intent + active tracks | [`STRATEGY.md`](STRATEGY.md) | — |
| Canonical vocabulary | [`GLOSSARY.md`](GLOSSARY.md) | — |
| Visual overview, diagrams, methodology | — | [`mickel.tech/apps/flow-next`](https://mickel.tech/apps/flow-next) · [`flow-next.dev`](https://flow-next.dev) |

Doc index with one-line descriptions: [`plugins/flow-next/docs/README.md`](plugins/flow-next/docs/README.md).

---

## Requirements

- **Python 3.8+** — bundled `flowctl` CLI is pure-stdlib.
- **`jq`** and **`gh`** — required for the review subsystem and PR plumbing.
- **`bun`** *(optional)* — only needed for the [Ralph TUI](flow-next-tui/).

## Platforms

| Platform | Status |
|---|---|
| Claude Code | First-class (canonical surface) |
| OpenAI Codex (CLI + Desktop) | First-class (mirror at `plugins/flow-next/codex/`, regenerated by `scripts/sync-codex.sh`) |
| Factory Droid | First-class (regex-OR matchers handle `Execute` ↔ `Bash`) |
| OpenCode | Community port: [`flow-next-opencode`](https://github.com/gmickel/flow-next-opencode) |

Detailed install + cross-platform patterns in [`docs/platforms.md`](plugins/flow-next/docs/platforms.md).

## Ecosystem

| Project | Platform |
|---|---|
| [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | OpenCode |
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid |
| [Ralph TUI](flow-next-tui/) | Cross-platform TUI for Ralph runs |

## Also check out

> **[GNO](https://gno.sh)** — local hybrid search for your notes, docs, and code. Long-term memory over your files via MCP.
>
> ```bash
> bun install -g @gmickel/gno && gno mcp install --target claude-code
> ```

---

## License

MIT — see [`LICENSE`](LICENSE).

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [@gmickel](https://twitter.com/gmickel) · [gordon@mickel.tech](mailto:gordon@mickel.tech)

[![Sponsor](https://img.shields.io/badge/Sponsor_this_project-❤-ea4aaa?style=for-the-badge)](https://github.com/sponsors/gmickel)

</div>
