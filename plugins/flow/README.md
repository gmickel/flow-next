<div align="center">

# Flow

[![Website](https://img.shields.io/badge/Website-mickel.tech%2Fapps%2Fflow-blue?style=for-the-badge)](https://mickel.tech/apps/flow)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-blueviolet)](https://claude.ai/code)
[![Version](https://img.shields.io/badge/Version-0.8.4-green)](../../CHANGELOG.md)
[![Status](https://img.shields.io/badge/Status-Legacy-orange)](../flow-next/)
[![Commands](https://img.shields.io/badge/Commands-5-green)](commands/)
[![Agents](https://img.shields.io/badge/Agents-6-yellow)](agents/)
[![Skills](https://img.shields.io/badge/Skills-7-blue)](skills/)

**Plan first, work second.**

</div>

> **⚠️ Legacy plugin.** New users should install [flow-next](../flow-next/) instead.
>
> Flow is stable but no longer developed. Flow-next has Ralph mode, better tooling, and works with Beads/plan files too. Flow is kept for existing users only.

---

## The Problem

Most agent failures aren't about model capability—they're about process:

- ✗ Starting to code before understanding the codebase
- ✗ Reinventing patterns that already exist in the repo
- ✗ Forgetting the original plan mid-implementation
- ✗ Missing edge cases that were obvious in hindsight

## How Flow Fixes It

| Failure Mode | Solution |
|--------------|----------|
| Weak research | 3 agents gather context in parallel *before* any code is written |
| Ignoring existing code | Explicit pattern reuse—agents find what already exists |
| Drifting from plan | Plan re-read before every task in the execute loop |
| Missing edge cases | Gap analyst identifies missing flows before implementation |
| Shallow self-review | Cross-model review via [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) catches what same-model review misses |

Flow doesn't make Claude smarter. It makes the workflow disciplined enough that capability translates to results.

---

## Install

```bash
/plugin marketplace add https://github.com/gmickel/flow-next
/plugin install flow
```

> **RepoPrompt v1.5.62+ Required** — Flow v0.8.1+ requires RepoPrompt 1.5.62 or later for review features (`-t` flag, progress notifications).
> If using an older RepoPrompt, downgrade Flow: `/plugin install flow@0.8.0`

---

## Quick Start

```bash
/flow:plan Add OAuth login for users
/flow:work plans/add-oauth-login.md
```

That's it. Two commands, one disciplined workflow.

### Optional: Interview First

For complex features, start with an interview to flesh out requirements:

```bash
/flow:interview docs/oauth-spec.md   # or a bead ID
/flow:plan Add OAuth login for users
/flow:work plans/add-oauth-login.md
```

Interview asks 40+ deep questions about technical details, edge cases, testing strategy, etc.

### What Happens

**`/flow:plan`**:
1. Runs 3 research agents in parallel (patterns, best practices, docs)
2. Runs gap analyst to find edge cases and missing flows
3. Writes `plans/<slug>.md` with references and acceptance checks
4. Optionally runs Carmack-level review via different model

**`/flow:work`**:
1. Reads plan fully, clarifies blockers
2. Sets up branch or worktree
3. Executes task loop—re-reads plan before each task
4. Runs tests + lint
5. Ships with clear Definition of Done
6. Optionally runs Carmack-level implementation review

---

## Commands

| Command | Description |
|---------|-------------|
| `/flow:plan` | Research + produce `plans/<slug>.md` |
| `/flow:work` | Execute a plan end-to-end |
| `/flow:interview` | Deep interview about a spec/bead, write refined details back |
| `/flow:plan-review` | Carmack-level plan review via rp-cli |
| `/flow:impl-review` | Carmack-level impl review (current branch) |

---

## Cross-Model Review

When [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) rp-cli is detected, both `/flow:plan` and `/flow:work` ask upfront:

```
Review — Run Carmack-level review after?
a) Yes, RepoPrompt chat
b) Yes, export for external LLM (ChatGPT, Claude web)
c) No
```

**Option a)**: Review runs via RepoPrompt's chat with a **different model**. We recommend GPT-5.2 High.

**Option b)**: Exports full context (files, codemaps, review prompt) to `~/Desktop/` and opens the file. Paste into ChatGPT Pro, Claude web, or any LLM.

**Why cross-model?** Same-model self-review has blind spots. A different model catches things Claude missed—architectural issues, edge cases, security gaps.

**Review criteria:**
- Simplicity & minimalism (YAGNI)
- DRY & code reuse
- Idiomatic patterns
- Architecture & data flow
- Edge cases & error handling
- Testability
- Performance
- Security
- Maintainability

**Output:** Issues with severity (Critical/Major/Minor/Nitpick), location, problem, suggestion, rationale. Overall: Ship ✓ / Needs Work ⚠ / Major Rethink ✗

---

## Usage Patterns

### Standalone

```bash
/flow:plan Add OAuth login for users
/flow:work plans/add-oauth-login.md
/flow:plan-review plans/add-oauth-login.md
/flow:impl-review
```

### With Beads

```bash
/flow:work bd-a3f8e9              # Work on Beads epic
/flow:plan-review bd-a3f8e9       # Review Beads epic
```

### Chaining

```bash
/flow:plan Add rate limiting to API, then implement it with /flow:work
```

### Natural Language

```
Help me plan out adding OAuth login for users
```
```
Implement the plan in plans/add-oauth-login.md
```
```
Review my current branch changes
```

Claude auto-triggers the matching skill based on intent.

---

## RepoPrompt Integration

When rp-cli is detected, `/flow:plan` asks which research approach to use:

| Aspect | repo-scout (fast) | context-scout (deep) |
|--------|-------------------|----------------------|
| Tools | Grep, Glob, Read | RepoPrompt rp-cli |
| Speed | ~45 seconds | Slower (builder takes time) |
| Tokens | ~65k | ~45k (30% less) |
| Best for | Bug fixes, simple changes | Complex features, architecture |

**Recommendation:** Use `context-scout` when architecture understanding matters. Use `repo-scout` for quick fixes.

### Direct Invocation

```bash
# Agent (isolated subprocess)
> Use context-scout to understand how authentication works

# Skill (current conversation)
> use rp to explore how auth works
```

---

## Workflow Detail

### `/flow:plan` — (Interview →) Research → Plan → Review

```
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
  OPTIONAL: /flow:interview
│ ┌─────────────────────────────────────────────────────────────────┐  │
  │ Deep interview (40+ questions) about spec/bead                  │
│ │ → Technical details, edge cases, testing, architecture          │  │
  │ → Writes refined spec back to source                            │
│ └─────────────────────────────────────────────────────────────────┘  │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ > /flow:plan gno-40i                                                  │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ SETUP (if rp-cli detected)                                            │
├───────────────────────────────────────────────────────────────────────┤
│  Q1: Use RepoPrompt for deeper context?   ○ Yes (context-scout)       │
│      (slower, better for complex features) ○ No (repo-scout) [faster] │
│                                                                       │
│  Q2: Run Carmack-level review?            ○ RepoPrompt ○ Export ○ No  │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Parallel Research                                            │
├───────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌───────────────┐  ┌─────────────┐          │
│  │ context-scout (rp)  │  │ practice-scout│  │ docs-scout  │          │
│  │ OR repo-scout       │  └───────┬───────┘  └──────┬──────┘          │
│  └──────────┬──────────┘          │                 │                 │
│             └─────────────────────┼─────────────────┘                 │
│                                   ▼                                   │
│              ┌────────────────────────────┐                           │
│              │ Patterns, practices, docs  │                           │
│              └────────────────────────────┘                           │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Gap Analysis                                                 │
├───────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ flow-gap-analyst                                                │  │
│  │ → Edge cases, missing flows, requirements                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Write Plan                                                   │
├───────────────────────────────────────────────────────────────────────┤
│  Beads ID input → update issue, create child tasks                    │
│  Text input     → plans/<slug>.md or new Beads epic                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ gno-40i: Linear Scan Optimization                               │  │
│  │ ├── .1: hybrid.ts optimization                                  │  │
│  │ ├── .2: vsearch.ts optimization                                 │  │
│  │ ├── .3: rerank.ts optimization                                  │  │
│  │ ├── .4: search.ts optimization                                  │  │
│  │ └── .5: Run tests ──depends on──▶ [.1-.4]                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 4: Plan Review (if opted in)                                    │
├───────────────────────────────────────────────────────────────────────┤
│  rp-cli builder → context    rp-cli chat → Carmack review             │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Simplicity · DRY · Idiomatic · Architecture · Edge cases        │  │
│  │ Testability · Performance · Security · Maintainability          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Output: Ship ✓ │ Needs Work ⚠ │ Major Rethink ✗                      │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
             ┌────────────┐                ┌────────────┐
             │  Ship ✓    │                │  Iterate   │
             │ Ready for  │                │  Fix and   │
             │ /flow:work │                │  re-review │
             └────────────┘                └─────┬──────┘
                                                 └──────▶ Back to Review
```

### `/flow:work` — Setup → Execute → Ship

```
┌───────────────────────────────────────────────────────────────────────┐
│ > /flow:work gno-40i                    (review: auto if rp-cli)      │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Confirm                                                      │
├───────────────────────────────────────────────────────────────────────┤
│  bd show gno-40i → read plan/issue                                    │
│  Read referenced files (hybrid.ts, vsearch.ts, rerank.ts, search.ts)  │
│  Ask blocking questions → get user go-ahead                           │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Setup (MUST ASK)                                             │
├───────────────────────────────────────────────────────────────────────┤
│  "Work on current branch, new branch, or isolated worktree?"          │
│                                                                       │
│     ○ Current branch     ○ New branch     ○ Worktree                  │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 3-4: Execute Loop                                               │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  bd ready --parent gno-40i → pick next task                           │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  For each child task:                                           │  │
│  │                                                                 │  │
│  │  ┌─────────┐    ┌───────────┐    ┌──────┐    ┌───────────────┐  │  │
│  │  │bd update│ -> │ Implement │ -> │ Test │ -> │ git commit    │  │  │
│  │  │in_progress   │  + test   │    │ pass │    │ bd close task │  │  │
│  │  └─────────┘    └───────────┘    └──────┘    └───────────────┘  │  │
│  │                                                                 │  │
│  │  .1 ✓ → .2 ✓ → .3 ✓ → .4 ✓ → .5 (unblocked) ✓                   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 5: Quality                                                      │
├───────────────────────────────────────────────────────────────────────┤
│  bun test → 521 pass    bun run lint → no issues                      │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 6: Ship                                                         │
├───────────────────────────────────────────────────────────────────────┤
│  bd close gno-40i → close epic                                        │
│  bd sync → commit beads changes                                       │
│  git push → push to remote                                            │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ PHASE 7: Impl Review (if opted in)                                    │
├───────────────────────────────────────────────────────────────────────┤
│  rp-cli builder → context around changed files                        │
│  rp-cli chat → Carmack review of implementation                       │
│                                                                       │
│  Output: Ship ✓ │ Needs Work ⚠ (fix and re-review)                    │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Purpose | Used By |
|-------|---------|---------|
| `repo-scout` | Find existing patterns, conventions, related code | `/flow:plan` |
| `practice-scout` | Gather best practices and pitfalls | `/flow:plan` |
| `docs-scout` | Fetch relevant framework/library docs | `/flow:plan` |
| `flow-gap-analyst` | Identify missing flows, edge cases, requirements | `/flow:plan` |
| `quality-auditor` | Review changes for correctness, security, tests | `/flow:work` |
| `context-scout` | Token-efficient codebase exploration via RepoPrompt | On-demand |

---

## Skills

| Skill | Purpose |
|-------|---------|
| `flow-plan` | Planning workflow logic |
| `flow-work` | Execution workflow logic |
| `interview` | Deep interview to flesh out specs/beads |
| `flow-plan-review` | Plan review via rp-cli + chat |
| `flow-impl-review` | Impl review via rp-cli + chat |
| `worktree-kit` | Manage git worktrees for parallel work |
| `rp-explorer` | Token-efficient codebase exploration via rp-cli |

Skills use **progressive disclosure**: only name + description (~100 tokens) loaded at startup. Full logic loads on-demand when triggered.

**Two ways to trigger**:
1. **Explicit**: `/flow:plan add OAuth` or `/flow:work plans/oauth.md`
2. **Natural language**: "help me plan out adding OAuth" — Claude auto-triggers the matching skill

---

## Beads Integration

Flow has optional [Beads](https://github.com/steveyegge/beads) (`bd`) integration for dependency-aware issue tracking.

**When Beads is detected** (`.beads/` exists or CLAUDE.md mentions it):

| Command | Beads Mode |
|---------|-----------|
| `/flow:plan` | Create epic/tasks instead of markdown |
| `/flow:work <beads-id>` | Track via `bd ready`/`bd close` instead of TodoWrite |
| `/flow:plan-review <beads-id>` | Review Beads epic directly |

**Fallback**: If `bd` unavailable, uses markdown plans + TodoWrite (no config needed).

---

## Plan Depths

- **SHORT**: Bugs, small changes — just problem, acceptance checks, key context
- **STANDARD**: Most features — overview, approach, risks, acceptance, test notes, refs
- **DEEP**: Large/critical — detailed phases, alternatives, rollout/rollback, metrics

---

## Definition of Done

- All plan steps completed or explicitly deferred
- All tasks done (Beads children closed or TodoWrite complete)
- Tests pass
- Lint/format pass
- Docs updated if needed

---

## Who It's For

Developers who want Claude Code to ship reliably, not just generate code. If you've ever had an agent "finish" a task only to realize it forgot half the requirements—this is for you.

---

## Development

```bash
claude --plugin-dir ./plugins/flow
```

### Conventions

- Plan files live in `plans/`
- Prefer reuse of centralized code
- Tests and linting are part of the plan

---

## Other Platforms

### OpenAI Codex (Experimental)

Flow partially works in OpenAI Codex with some limitations:

**Caveats:**
- No subagent support (research scouts run inline or are skipped)

**Install:**
```bash
./scripts/install-codex.sh flow
```

### Community Ports and Inspired Projects

| Project | Platform |
|---------|----------|
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid |

---

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [gordon@mickel.tech](mailto:gordon@mickel.tech)

</div>
