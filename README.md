<div align="center">

# gmickel claude marketplace

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin_Marketplace-blueviolet)](https://claude.ai/code)

[![Flow-next](https://img.shields.io/badge/Flow--next-v0.6.2-green)](plugins/flow-next/)

[![Flow-next](https://img.shields.io/badge/Flow--next-v0.6.2-green)](plugins/flow-next/)

[![Flow](https://img.shields.io/badge/Flow-v0.8.4-blue)](plugins/flow/)
[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤-ea4aaa)](https://github.com/sponsors/gmickel)

**Plugins that make AI agents actually work.**

</div>

> 🔄 **Update issues?** Run: `claude plugin update flow-next@gmickel-claude-marketplace`
>
> 🤖 **[Ralph mode](plugins/flow-next/docs/ralph.md)**: Ship features while you sleep. Fresh context per iteration, multi-model review gates, auto-blocks stuck tasks.
>
> 💪 **Stable features**: Plan-first workflow, re-anchoring, receipt-based gating, structured task management
>
> 📡 **Cross-platform reviews**: [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) (macOS) or [Codex CLI](plugins/flow-next/README.md#codex-review-backend) (any OS)

---

## The Problem

Process failures, not model failures:

- Starting to code before understanding the codebase
- Reinventing patterns already there
- Forgetting the plan mid-implementation
- Skipping edge cases obvious in hindsight

This marketplace ships plugins that fix these problems.

---

## Plugins

| Plugin | What It Does |
|--------|--------------|
| [**flow-next**](#flow-next) | Plan-first workflow with `.flow/` task tracking. Zero deps. Multi-user safe. **Recommended.** |
| ~~flow~~ | Legacy. Use flow-next instead. |

> **New here?** Install **flow-next**. It does everything flow does plus Ralph mode, better tooling, and active development. Flow is kept for existing users only.

---

## Flow-Next

🌐 **Prefer a visual overview?** See the [Flow-Next app page](https://mickel.tech/apps/flow-next) for diagrams and examples.

**Plan first, work second. Zero external dependencies.**

```bash
# 1. Install
/plugin marketplace add https://github.com/gmickel/gmickel-claude-marketplace
/plugin install flow-next

# 2. Setup (recommended - adds CLI access + project docs)
/flow-next:setup

# 3. Use
/flow-next:plan Add a contact form with validation
/flow-next:work fn-1
```

**What setup unlocks:**
- CLI access: `flowctl epics`, `flowctl ready`, `flowctl show` (no Claude needed)
- Project docs: Adds instructions for other AI tools (Codex, Cursor, etc.)
- Local guide: `.flow/usage.md` reference

Idempotent - safe to re-run. Skip if you only need `/flow-next:plan` and `/flow-next:work`.

### Choose Your Path

| I want to... | Command | Automation Level |
|--------------|---------|------------------|
| Plan + work one task at a time | `/flow-next:work fn-1.1` | Manual |
| Plan an epic, work with reviews | `/flow-next:plan` -> `/flow-next:work fn-1` | Manual + optional review |
| Run overnight unattended | `/flow-next:ralph-init` -> `scripts/ralph/ralph.sh` | Full autonomous |

**Agents that finish what they start.**

```mermaid
flowchart TD
  A[Idea or short spec<br/>prompt or doc] --> B{Need deeper spec?}
  B -- yes --> C[Optional: /flow-next:interview fn-N or spec.md<br/>40+ deep questions to refine spec]
  C --> D[Refined spec]
  B -- no --> D
  D --> E[/flow-next:plan idea or fn-N/]
  E --> F[Parallel subagents: repo patterns + online docs + best practices]
  F --> G[flow-gap-analyst: edge cases + missing reqs]
  G --> H[Writes .flow/ epic + tasks + deps]
  H --> I{Plan review? rp-cli only}
  I -- yes --> J[/flow-next:plan-review fn-N/]
  J --> K{Plan passes review?}
  K -- no --> L[Re-anchor + fix plan]
  L --> J
  K -- yes --> M[/flow-next:work fn-N/]
  I -- no --> M
  M --> N[Re-anchor before EVERY task]
  N --> O[Implement]
  O --> P[Test + verify acceptance]
  P --> Q[flowctl done: write done summary + evidence]
  Q --> R{Impl review? rp-cli only}
  R -- yes --> S[/flow-next:impl-review/]
  S --> T{Next ready task?}
  R -- no --> T
  T -- yes --> N
  T -- no --> U[flowctl epic close fn-N]
  classDef optional stroke-dasharray: 6 4,stroke:#999;
  class C,J,S optional;
```

📖 **Full guide (CLI, workflow, .flow layout):** [plugins/flow-next/README.md](plugins/flow-next/README.md)

<table>
<tr>
<td><img src="assets/flow-next-plan.png" alt="Planning Phase" width="400"/></td>
<td><img src="assets/flow-next-work.png" alt="Implementation Phase" width="400"/></td>
</tr>
<tr>
<td align="center"><em>Planning: dependency-ordered tasks</em></td>
<td align="center"><em>Execution: fixes, evidence, review</em></td>
</tr>
</table>

### How to Start

**1. Write a short spec**

Start with a rough idea - 1-5 sentences describing what you want to build. Save it as a markdown file or just keep it in your head.

**2. Flesh it out (optional but recommended)**

```bash
/flow-next:interview "Add user authentication with OAuth"
# or point to a spec file:
/flow-next:interview specs/auth.md
```

The interview asks 40+ deep questions to surface edge cases, requirements, and decisions before you start coding.

**3. Plan it**

```bash
/flow-next:plan "Add user authentication with OAuth"
# or if you have a refined spec:
/flow-next:plan fn-1  # refine existing epic
```

Creates an epic with dependency-ordered tasks in `.flow/`.

**4. Work it**

Choose your mode:

```bash
# Interactive - one task at a time, full control
/flow-next:work fn-1.1

# Interactive - whole epic, still in Claude
/flow-next:work fn-1

# Autonomous - run overnight, walk away
/flow-next:ralph-init  # one-time setup
scripts/ralph/ralph.sh  # run from terminal
```

That's it. Spec -> Interview -> Plan -> Work.

### Why It Works

**You control the granularity:**
- `/flow-next:work fn-1.1` — one task at a time with full review cycles
- `/flow-next:work fn-1` — throw the whole epic at it, walk away

Either way you get the same guarantees: re-anchoring, evidence, cross-model review.

**No context length worries:**
- Planning ensures every task fits one work iteration
- Re-anchoring after each task (and after compaction) prevents drift
- Fresh context window every iteration in Ralph mode

**Reviewer as safety net:**
- If drift happens despite re-anchoring, a different model catches it
- Reviews block until `SHIP` verdict - no "LGTM with nits" that get ignored

**What reviewers check:**

| Plan Reviews | Implementation Reviews |
|--------------|------------------------|
| Completeness & feasibility | Correctness & simplicity |
| Architecture & scope | DRY & edge cases |
| Dependencies & risks | Test coverage & security |
| Task breakdown quality | Evidence of completion |

**Re-anchoring prevents drift:**

Before EVERY task, Flow-Next re-reads the epic spec, task spec, and git state from `.flow/`. This forces Claude back to the source of truth - no hallucinated scope creep, no forgotten requirements. In Ralph mode, this happens automatically each iteration.

Unlike agents that carry accumulated context (where early mistakes compound), re-anchoring gives each task a fresh, accurate starting point.

Bundles everything in a single Python script. No npm. No daemons. No config edits. Try it in 30 seconds. Uninstall by deleting `.flow/` (and `scripts/ralph/` if enabled).

## Ralph (Autonomous Mode)

> **⚠️ Safety first**: Ralph defaults to `YOLO=1` (skips permission prompts).
> - Start with `ralph_once.sh` to observe one iteration
> - Consider [Docker sandbox](https://docs.docker.com/ai/sandboxes/claude-code/) for isolation

**Setup (one-time, inside Claude):**
```bash
/flow-next:ralph-init
```

Or from terminal without entering Claude:
```bash
claude -p "/flow-next:ralph-init"
```

**Run (outside Claude):**
```bash
scripts/ralph/ralph.sh
```

**How Ralph differs from other autonomous agents:**

Most agents gate by tests alone. Ralph adds production-grade quality gates:

- **Multi-model reviews**: Uses [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) to send code to a *different* model. Two models catch what one misses.
- **Review loops until SHIP**: Reviews block progress until `<verdict>SHIP</verdict>`. Fix → re-review cycles continue until approved.
- **Receipt-based gating**: Every review must produce a receipt JSON proving it ran. No receipt = no progress. At-least-once delivery with idempotent retry—treats agent as untrusted actor; receipts are proof-of-work.

<details>
<summary><strong>📸 Ralph in action</strong> (click to expand)</summary>
<br>
<img src="assets/ralph.png" alt="Ralph Autonomous Loop" width="600"/>
</details>

📖 **[Ralph deep dive](plugins/flow-next/docs/ralph.md)**

🖥️ **[Ralph TUI](flow-next-tui/)** — Terminal UI for monitoring runs in real-time (`bun add -g @gmickel/flow-next-tui`)

### Why Flow-Next Ralph vs Anthropic's ralph-wiggum?

Anthropic's official ralph-wiggum plugin uses a Stop hook to keep Claude in the same session. Flow-Next inverts this architecture for production-grade reliability.

| Aspect | ralph-wiggum | Flow-Next Ralph |
|--------|--------------|-----------------|
| **Session model** | Single session, accumulating context | Fresh context per iteration |
| **Loop mechanism** | Stop hook re-feeds prompt in SAME session | External bash loop, new `claude -p` each iteration |
| **Context management** | Transcript grows, context fills up | Clean slate every time |
| **Failed attempts** | Pollute future iterations | Gone with the session |
| **Re-anchoring** | None | Re-reads epic/task spec EVERY iteration |
| **Quality gates** | None (test-based only) | Multi-model reviews block until SHIP |
| **Stuck detection** | `--max-iterations` safety limit | Auto-blocks task after N failures |
| **State storage** | In-memory transcript | File I/O (`.flow/`, receipts, evidence) |
| **Auditability** | Session transcript | Per-iteration logs + receipts + evidence |

**The Core Problem with ralph-wiggum**

1. **Context pollution** - Every failed attempt stays in context, potentially misleading future iterations
2. **No re-anchoring** - As context fills, Claude loses sight of the original task spec
3. **Single model** - No external validation; Claude grades its own homework
4. **Binary outcome** - Either completion promise triggers, or you hit max iterations

**Flow-Next's Solution**

Fresh context every iteration + multi-model review gates + receipt-based proof-of-work.

Two models catch what one misses. Process failures, not model failures.

### Features

| | |
|:--|:--|
| **Re-anchoring** | Before EVERY task, re-reads epic/task specs + git state. No drift. |
| **Multi-user safe** | Scan-based IDs. Soft claims via assignee. Actor auto-detect. |
| **Zero deps** | Bundled `flowctl.py`. No external CLI. Just Python 3. |
| **Non-invasive** | No daemons or CLAUDE.md edits. Delete `.flow/` (and `scripts/ralph/` if enabled) to uninstall. |
| **CI-ready** | `flowctl validate --all` exits 1 on errors. Drop into pre-commit or GitHub Actions. |
| **One file per task** | Merge-friendly. Conflict surface is minimal. |
| **Automated reviews** | Require [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) (rp-cli). Without it, reviews are skipped. |
| **Dependency graphs** | Tasks declare blockers. Nothing starts until dependencies resolve. |
| **Auto-block stuck tasks** | After MAX_ATTEMPTS_PER_TASK failures (default 5), task is blocked with failure context. Prevents infinite retry loops. |

### Commands

| Command | What It Does |
|---------|--------------|
| `/flow-next:plan` | Research, create epic + tasks in `.flow/` |
| `/flow-next:work` | Execute epic end-to-end, task by task |
| `/flow-next:interview` | Deep interview to flesh out a spec |
| `/flow-next:plan-review` | Carmack-level plan review via rp-cli |
| `/flow-next:impl-review` | Carmack-level impl review (current branch) |
| `/flow-next:ralph-init` | Scaffold autonomous loop in `scripts/ralph/` |
| `/flow-next:setup` | Install flowctl locally + add project docs |
| `/flow-next:uninstall` | Remove flow-next from project |

### Autonomous Flags

All commands accept flags to bypass interactive questions:

```bash
# Interactive (asks questions)
/flow-next:plan Add caching
/flow-next:work fn-1

# Autonomous (flags)
/flow-next:plan Add caching --research=grep --no-review
/flow-next:work fn-1 --branch=current --no-review

# Autonomous (natural language)
/flow-next:plan Add caching, use context-scout, skip review
/flow-next:work fn-1 current branch, no review
```

📖 **[Full documentation](plugins/flow-next/README.md)**

---

## Install

```bash
# Add marketplace
/plugin marketplace add https://github.com/gmickel/gmickel-claude-marketplace

# Install plugin
/plugin install flow-next    # Recommended: zero deps, simpler
# or: /plugin install flow   # If you use Beads or want plan files

# Setup (recommended for flow-next)
/flow-next:setup             # Adds CLI access + project docs
```

---

## Flow (Legacy)

> **⚠️ Legacy plugin.** New users should install [flow-next](#flow-next) instead.

**Plan first, work second.** The original, with optional Beads integration. Kept for existing users.

```bash
/plugin install flow

/flow:plan Add OAuth login for users
/flow:work plans/add-oauth-login.md
```

### How It Works

| Failure Mode | How Flow Fixes It |
|--------------|-------------------|
| Weak research | Parallel agents gather context *before* coding starts |
| Ignoring existing code | Explicit pattern reuse from your repo |
| Drifting from plan | Plan re-read between every task |
| Shallow self-review | Cross-model review via RepoPrompt |

### Commands

| Command | What It Does |
|---------|--------------|
| `/flow:plan` | Research + produce `plans/<slug>.md` |
| `/flow:work` | Execute plan end-to-end with task tracking |
| `/flow:interview` | Deep interview to flesh out spec/bead |
| `/flow:plan-review` | Carmack-level plan review via rp-cli |
| `/flow:impl-review` | Carmack-level impl review (current branch) |

### Integrations

- **[RepoPrompt](https://repoprompt.com/?atp=KJbuL4)** for token-efficient codebase exploration + cross-model reviews
- **[Beads](https://github.com/steveyegge/beads)** for dependency-aware issue tracking (auto-detected)

📖 **[Full documentation](plugins/flow/README.md)** · **[Changelog](CHANGELOG.md)**

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
