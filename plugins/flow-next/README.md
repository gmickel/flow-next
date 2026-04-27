<div align="center">

# Flow-Next

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-blueviolet)](https://claude.ai/code)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI_Codex-Plugin-10a37f)](https://developers.openai.com/codex/cli/)

[![Version](https://img.shields.io/badge/Version-0.38.2-green)](../../CHANGELOG.md)

[![Status](https://img.shields.io/badge/Status-Active_Development-brightgreen)](../../CHANGELOG.md)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/f3DYq8AAm5)

**Plan first, work second. Zero external dependencies.**

</div>

---

> **Active development.** [Changelog](../../CHANGELOG.md) | [Report issues](https://github.com/gmickel/flow-next/issues)

🌐 **Prefer a visual overview?** See the [Flow-Next app page](https://mickel.tech/apps/flow-next) for diagrams and examples.

> **What's new in 0.38.0:** `/flow-next:capture` synthesizes free-form discussion into a flow-next epic spec with source-tagged criteria + mandatory read-back. `/flow-next:interview` enhanced with lead-with-recommendation + confidence tiers + codebase-first investigation + dependency-ordered question branches. Cross-platform tool handling moved into the Codex sync script; canonical skills stay Claude-native, sync rewrites for Codex mirror. [Full changelog](../../CHANGELOG.md).
>
> Recent highlights: agent-native [memory audit](#memory-system) (0.37.0), [memory migrate skill](#memory-system) (0.37.0), [PR feedback resolver](#pr-feedback-resolution) (0.34.0), [prospect skill](#prospecting) for ranked candidate ideation (0.36.0), [opt-in review flags](#cross-model-reviews) `--validate` / `--deep` / `--interactive` (0.35.0).

---

## Table of Contents

- [What Is This?](#what-is-this)
- [The Workflow](#the-workflow-ladder) — Idea → spec → tasks → ship → maintain
- [Why It Works](#why-it-works)
- [Quick Start](#quick-start) — Install, setup, use
- [When to Use What](#when-to-use-what) — Prospect / Capture / Interview / Plan
- [Prospecting](#prospecting) — `/flow-next:prospect`
- [Capture](#capture) — `/flow-next:capture`
- [Memory System](#memory-system) — `/flow-next:audit` + `/flow-next:memory-migrate`
- [Agent Readiness Assessment](#agent-readiness-assessment) — `/flow-next:prime`
- [PR Feedback Resolution](#pr-feedback-resolution) — `/flow-next:resolve-pr`
- [Cross-Model Reviews](#cross-model-reviews) — RepoPrompt / Codex / Copilot
- [Troubleshooting](#troubleshooting)
- [Ralph (Autonomous Mode)](#ralph-autonomous-mode) — Run overnight
- [Features](#features) — Re-anchoring, multi-user, reviews, dependencies
- [Commands](#commands) — All slash commands + flags
  - [Command Reference](#command-reference) — Detailed input docs for each command
- [The Workflow](#the-workflow) — Planning and work phases
- [.flow/ Directory](#flow-directory) — File structure
- [flowctl CLI](#flowctl-cli) — Direct CLI usage

---

## What Is This?

Flow-Next is a plugin for **agent-native AI orchestration**. Sixteen slash commands cover the full lifecycle: idea generation (`prospect`) → spec creation (`capture`) → refinement (`interview`) → planning (`plan`) → execution (`work`) → review (`impl-review` + `epic-review`) → PR feedback resolution (`resolve-pr`) → maintenance (`audit` + `memory-migrate`) → autonomous mode (`ralph-init`). Bundled task tracking, dependency graphs, re-anchoring, and cross-model reviews.

Everything lives in your repo. No external services. No global config. Uninstall: delete `.flow/` (and `scripts/ralph/` if enabled).

First-class on **Claude Code**, **OpenAI Codex** (CLI + Desktop), and **Factory Droid**. Canonical skills are Claude-native; `sync-codex.sh` rewrites for Codex mirror — both platforms see their own native tool names.

<table>
<tr>
<td><img src="../../assets/flow-next-plan.png" alt="Planning Phase" width="400"/></td>
<td><img src="../../assets/flow-next-work.png" alt="Implementation Phase" width="400"/></td>
</tr>
<tr>
<td align="center"><em>Planning: dependency-ordered tasks</em></td>
<td align="center"><em>Execution: fixes, evidence, review</em></td>
</tr>
</table>

---

## Epic-first task model

Flow-Next does not support standalone tasks.

Every unit of work belongs to an epic fn-N (even if it's a single task).

Tasks are always fn-N.M and inherit context from the epic spec.

Flow-Next always creates an epic container (even for one-offs) so every task has a durable home for context, re-anchoring, and automation. You never have to think about it.

Rationale: keeps the system simple, improves re-anchoring, makes automation (Ralph) reliable.

"One-off request" -> epic with one task.

---

## Why It Works

### You Control the Granularity

Work task-by-task with full review cycles for maximum control. Or throw the whole epic at it and let Flow-Next handle everything. Same guarantees either way.

```bash
# One task at a time (review after each)
/flow-next:work fn-1.1

# Entire epic (review after all tasks complete)
/flow-next:work fn-1
```

Both get: re-anchoring before each task, evidence recording, cross-model review (if a review backend is configured — RepoPrompt, Codex CLI, or GitHub Copilot CLI).

**Review timing**: The review runs once at the end of the work package—after a single task if you specified `fn-N.M`, or after all tasks if you specified `fn-N`. For tighter review loops on large epics, work task-by-task.

### No Context Length Worries

- **Tasks sized at planning:** Every task is scoped to fit one work iteration
- **Re-anchor every task:** Fresh context from `.flow/` specs before each task
- **Survives compaction:** Re-anchors after conversation summarization too
- **Fresh context in Ralph:** Each iteration starts with a clean context window

Never worry about context window limits again.

### Reviewer as Safety Net

If drift happens despite re-anchoring, a different model catches it before it compounds:

1. Claude implements task
2. A different model reviews via the configured backend — RepoPrompt (full-file context), Codex CLI, or GitHub Copilot CLI
3. Reviews block until `SHIP` verdict
4. Fix → re-review cycles continue until approved

Two models catch what one misses.

---

### Zero Friction

- **Works in 30 seconds.** Install the plugin, run a command. No setup.
- **Non-invasive.** No CLAUDE.md edits. No daemons. (Ralph uses plugin hooks for enforcement.)
- **Clean uninstall.** Delete `.flow/` (and `scripts/ralph/` if enabled).
- **Multi-user safe.** Teams work parallel branches without coordination servers.

---

## Quick Start

### 1. Install

#### Claude Code / Factory Droid

```bash
# Add marketplace
/plugin marketplace add https://github.com/gmickel/flow-next

# Install flow-next
/plugin install flow-next
```

#### OpenAI Codex

Clone the repo and run the install script:

```bash
git clone https://github.com/gmickel/flow-next.git
cd flow-next
./scripts/install-codex.sh flow-next
```

Then run `/flow-next:setup` in your project.

**Why a script and not Codex's `/plugins` install?** Codex's plugin protocol (as of April 2026) only registers `skills` declared in `plugin.json` — there's no `agents` or `hooks` field in the manifest schema yet. Installing flow-next via `/plugins` gives you the slash commands, but the bundled `.toml` agents (worker, scouts, plan-sync, pr-comment-resolver — 21 total) and Ralph hooks aren't wired into `~/.codex/config.toml`. That breaks subagent isolation (per-role model tiers, `disallowed_tools` enforcement) and the autonomous Ralph mode. `install-codex.sh` writes the agent and feature entries directly into your config, copies skills + agents + hooks + flowctl into `~/.codex/`, and gives you the full multi-agent experience. We'll switch back to `/plugins` once Codex's manifest supports `agents` + `hooks`.

#### OpenAI Codex (Update)

Re-run the install script after pulling:

```bash
cd flow-next && git pull
./scripts/install-codex.sh flow-next
```

The script is idempotent: it cleans its own previous entries before re-writing, so running it on every update is safe and required to pick up new skills, agents, or hook changes.

### 2. Setup (Recommended)

```bash
/flow-next:setup
```

This is technically optional but **highly recommended**. It:
- **Configures review backend** (RepoPrompt, Codex, Copilot, or none) — required for cross-model reviews
- Copies `flowctl` to `.flow/bin/` for direct CLI access
- Adds flow-next instructions to CLAUDE.md/AGENTS.md (helps other AI tools understand your project)
- Creates `.flow/usage.md` with full CLI reference

**Idempotent** - safe to re-run. Detects plugin updates and refreshes scripts automatically.

After setup:
```bash
export PATH=".flow/bin:$PATH"
flowctl --help
flowctl epics                # List all epics
flowctl tasks --epic fn-1    # List tasks for epic
flowctl ready --epic fn-1    # What's ready to work on
```

### 3. Use

```bash
# Spec: "create a spec for X" — writes epic with structured requirements
# Then plan or interview to refine

# Plan: research, create epic with tasks
/flow-next:plan Add a contact form with validation

# Work: execute tasks in dependency order
/flow-next:work fn-1

# Or work directly from a spec file (creates epic automatically)
/flow-next:work docs/my-feature-spec.md
```

That's it. Flow-Next handles research, task ordering, reviews, and audit trails.

### When to Use What

Flow-next is flexible. There's no single "correct" order — the right sequence depends on how well-defined your spec already is.

**The key question: How fleshed out is your idea?**

#### Spec-driven (recommended for new features)

```
Create spec → Interview or Plan → Work
```

1. **Create spec** — ask Claude to "create a spec for X". This creates an epic with a structured spec (goal, architecture, API contracts, edge cases, acceptance criteria, boundaries, decision context) — no tasks yet
2. **Refine or plan**:
   - `/flow-next:interview fn-1` — deep Q&A to pressure-test the spec, surface gaps
   - `/flow-next:plan fn-1` — research best practices + break into tasks
3. **Work** — `/flow-next:work fn-1` executes with re-anchoring and reviews

Best for: features where you want to nail down the WHAT/WHY before committing to HOW. The spec captures everything an implementer needs.

#### Vague idea or rough concept

```
Interview → Plan → Work
```

1. **Interview first** — `/flow-next:interview "your rough idea"` asks 40+ deep questions to surface requirements, edge cases, and decisions you haven't thought about
2. **Plan** — `/flow-next:plan fn-1` takes the refined spec and researches best practices, current docs, repo patterns, then splits into properly-sized tasks
3. **Work** — `/flow-next:work fn-1` executes with re-anchoring and reviews

#### Well-written spec or PRD

```
Plan → Interview → Work
```

1. **Plan first** — `/flow-next:plan specs/my-feature.md` researches best practices and current patterns, then breaks your spec into epic + tasks
2. **Interview after** — `/flow-next:interview fn-1` runs deep questions against the plan to catch edge cases, missing requirements, or assumptions
3. **Work** — `/flow-next:work fn-1` executes

#### Minimal planning

```
Plan → Work
```

Skip interview entirely for well-understood changes. Plan still researches best practices and splits into tasks.

#### Quick single-task (spec already complete)

```
Work directly
```

```bash
/flow-next:work specs/small-fix.md
```

For small, self-contained changes where you already have a complete spec. Creates an epic with **one task** and executes immediately. You get flow tracking, re-anchoring, and optional review — without full planning overhead.

Best for: bug fixes, small features, well-scoped changes that don't need task splitting.

**Note:** This does NOT split into multiple tasks. For detailed specs that need breakdown, use Plan first.

**Summary:**

| Starting point | Recommended sequence |
|----------------|---------------------|
| No target yet, want ranked candidates | Prospect → (promote) → Plan → Work ([details](#prospecting)) |
| Prospect survivor needs richer spec | Prospect → Capture → Interview/Plan → Work |
| Conversation already in flight | Capture → Interview/Plan → Work |
| Free-form discussion, lock it down | Capture → Plan → Work |
| New feature, want solid spec first | Spec → Interview/Plan → Work |
| Vague idea, rough notes | Interview → Plan → Work |
| Detailed spec/PRD | Plan → Interview → Work |
| Well-understood, needs task splitting | Plan → Work |
| Small single-task, spec complete | Work directly (creates 1 epic + 1 task) |

**Prospect vs Capture vs Spec vs Interview vs Plan:**
- **Prospect** (`/flow-next:prospect [hint]`) generates many candidate ideas, critiques each one, and writes a ranked artifact under `.flow/prospects/`. Use when you don't have a target yet. Promote a survivor to an epic via `flowctl prospect promote` (direct path to plan), or hand the survivor to `/flow-next:capture` for a richer conversation-driven spec.
- **Capture** (`/flow-next:capture`) synthesizes conversation context into an epic spec — the automated alternative to manual `flowctl epic create + epic set-plan`. Use after prospect-promotion or after a free-form design discussion. Source-tags every acceptance criterion (`[user]` / `[paraphrase]` / `[inferred]`); mandatory read-back loop; never silently invents requirements. Output goes to `.flow/specs/<epic-id>.md`.
- **Spec** (just ask "create a spec") creates an epic with structured requirements (goal, architecture, API contracts, edge cases, acceptance criteria, boundaries). Same destination as capture, but the manual heredoc path — useful for scripted callers.
- **Interview** refines an epic via deep Q&A (40+ questions). Writes back to the epic spec only — no tasks.
- **Plan** researches best practices, analyzes existing patterns, and creates sized tasks with dependencies.

You can always run interview again after planning to catch anything missed. Interview writes back to the epic spec only — it won't modify existing tasks.

---

## Prospecting

`/flow-next:prospect [focus hint]` fills the "what should I build?" gap above `interview` and `plan`. Generates many candidate ideas grounded in the repo, critiques every one with explicit rejection reasons, and surfaces only the survivors bucketed by leverage. Output is a ranked artifact under `.flow/prospects/<slug>-<date>.md` that promotes directly into an epic via `flowctl prospect promote`.

### When to use it

- You don't have a target yet — "what should I build next?"
- You want to compare candidates side-by-side before committing
- You want a durable record of ideas (and rejection reasons) that survives sessions

If you already have a target, skip prospect and go straight to `/flow-next:interview` or `/flow-next:plan`.

### Quick start

```bash
# Open-ended ideation
/flow-next:prospect

# Concept hint
/flow-next:prospect DX improvements

# Path hint (ideate inside a subtree)
/flow-next:prospect plugins/flow-next/skills/

# Constraint hint
/flow-next:prospect quick wins under 200 LOC

# Volume hint
/flow-next:prospect top 3
/flow-next:prospect 50 ideas
/flow-next:prospect raise the bar      # 60-70% rejection target
```

### How it works

Six phases, single chat (no subagent dispatch):

1. **Resume check** — artifacts <30 days old offered for extension; corrupt artifacts surface but never extend.
2. **Ground** — recent files (git log, 30 days), open epics, memory entries matching the hint, recent CHANGELOG. Records `scanned: none (reason)` for missing inputs.
3. **Generate (persona-seeded, divergent)** — 15-25 candidates by default, using ≥2 personas (`senior-maintainer` / `first-time-user` / `adversarial-reviewer`) to counter mode collapse.
4. **Critique (separate prompt, second pass)** — every candidate gets `keep`/`drop` with a taxonomy reason (`duplicates-open-epic | out-of-scope | insufficient-signal | too-large | backward-incompat | other`). Floor: ≥40% rejection (or 60-70% under `raise the bar`); on floor violation the skill asks whether to regenerate, loosen, or ship anyway.
5. **Rank survivors (bucketed)** — `High leverage (1-3)` / `Worth considering (4-7)` / `If you have the time (8+)`. Prose-only forced-format leverage sentence per survivor; no numeric scores.
6. **Write + handoff** — atomic write of the artifact, then a frozen-format prompt `1`|`2`|`...`|`skip`|`interview` to promote a survivor or refine via interview.

### Promote → epic

```bash
# Read the artifact
flowctl prospect read <artifact-id>

# Promote idea #2 to a new epic
flowctl prospect promote <artifact-id> --idea 2 --json
# -> Promoted idea #2 ("<title>") to <epic-id>. Next: /flow-next:interview <epic-id>

# Refine the new epic
/flow-next:interview <epic-id>
```

The new epic ships with a pre-filled spec skeleton: original idea summary, leverage reasoning, suggested size, and a `## Source` section linking back to `.flow/prospects/<artifact-id>.md#idea-N`. Promote is idempotent — if you try to promote the same idea twice, it refuses with exit 2 and a message referencing the prior epic-id; pass `--force` to override.

### flowctl prospect cheat sheet

```bash
# List artifacts (default: <30 days old)
flowctl prospect list                              # active artifacts
flowctl prospect list --all --json                 # everything (archived, stale, corrupt)

# Read an artifact (full body, or one section)
flowctl prospect read <id>
flowctl prospect read <id> --section focus
flowctl prospect read <id> --section grounding
flowctl prospect read <id> --section survivors
flowctl prospect read <id> --section rejected

# Promote a survivor to a new epic
flowctl prospect promote <id> --idea N
flowctl prospect promote <id> --idea N --epic-title "Custom title"
flowctl prospect promote <id> --idea N --force --json

# Archive (move to .flow/prospects/_archive/)
flowctl prospect archive <id>
```

ID forms: full id (`<slug>-<date>`), slug-only (latest date wins), or filepath. Same-day reruns are suffixed with `-2`, `-3` to avoid collisions.

**Exit codes:**
- `read` / `promote` on a corrupt artifact → exit **3** (stderr marker `[ARTIFACT CORRUPT: <reason>]`).
- `promote` on a duplicate idea without `--force` → exit **2** with the prior epic-id.
- Ralph-block (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` set when running `/flow-next:prospect`) → exit **2**.

### Artifact schema

```yaml
---
title: "DX improvements for flow-next"
date: "2026-04-24"
focus_hint: "DX improvements"
volume: 22
survivor_count: 6
rejected_count: 16
rejection_rate: 0.73
artifact_id: dx-improvements-2026-04-24
promoted_to: {2: [fn-37-dx-faster-resume]}    # numeric idea positions → epic ids
status: active                                  # active | corrupt | stale | archived
---
```

Optional flags `floor_violation`, `generation_under_volume` are omitted when unset. `promoted_to` is omitted when no idea has been promoted.

### Decision context

- **Why prose-only ranking?** Numeric scores are near-random past position 5 across reruns. Bucketing (3/4/∞) stabilizes the top-3 while preserving prose reasoning within each bucket.
- **Why two passes?** Single-pass prompts soft-reject — everything is kept, just ordered. A separate critique pass forces explicit rejection with a taxonomy.
- **Why persona seeding?** Post-RLHF mode collapse — same 5-8 "obvious" ideas every run. Persona-seeded divergent generation (≥2 personas) increases idea diversity.
- **Why Ralph-out?** Autonomous loops have no business deciding what a repo should tackle next; that's a human-in-the-loop judgement call.

---

## Capture

`/flow-next:capture` synthesizes the current conversation context into an epic spec. The automated alternative to the manual `flowctl epic create + epic set-plan` heredoc documented in `CLAUDE.md` — same destination (`.flow/specs/<epic-id>.md`), same template, but the host agent does the synthesis with full conversation context.

### When to use it

- A free-form design discussion has produced enough material for an epic spec — lock it down before the context decays.
- A `/flow-next:prospect` survivor needs a richer conversation-driven spec than the direct `flowctl prospect promote` skeleton provides.
- You want an audit trail of which acceptance criteria came from the user vs which the agent inferred — capture's source-tagging makes this visible.

If you already have a written spec or a clear feature description, skip capture and go straight to `/flow-next:plan` or `/flow-next:interview`.

### Quick start

```bash
# Interactive (default) — agent shows full draft via AskUserQuestion before writing
/flow-next:capture

# Autofix — print the draft to stdout; --yes required to commit
/flow-next:capture mode:autofix --yes

# Overwrite an existing epic spec (refused without this flag)
/flow-next:capture --rewrite fn-42-add-rate-limiting

# Override compaction-detection refusal (use only when you trust recent turns)
/flow-next:capture --from-compacted-ok
```

### How it works

Six phases, single chat (no subagent dispatch by default):

1. **Pre-flight** — duplicate detection (scan `.flow/epics/` + `flowctl memory search` on extracted keywords); compaction detection (refuse without `--from-compacted-ok` when conversation has truncation markers); idempotency guard (refuse without `--rewrite <id>` when target epic already exists).
2. **Conversation evidence** — extract a verbatim `## Conversation Evidence` block (raw user turns) into the spec FIRST, then draft other sections referencing it. Mitigates hallucinated requirements.
3. **Source-tagged synthesis** — draft spec sections; tag every acceptance criterion + decision-context line with `[user]` (verbatim from conversation), `[paraphrase]` (user intent restated), or `[inferred]` (agent fill-in, most-scrutinized at read-back). At 8+ acceptance criteria, surface a "consider splitting?" suggestion at read-back — never auto-split.
4. **Must-ask cases** — hard-error if any of these are unresolved without asking: (a) epic title genuinely ambiguous, (b) acceptance criterion can't be made testable without user judgment, (c) scope conflicts with existing epic.
5. **Read-back loop (mandatory, even in autofix)** — show full draft + `[inferred]` count via `AskUserQuestion`. User confirms / edits / aborts. Autofix prints to stdout; `--yes` required to commit.
6. **Write via flowctl** — `flowctl epic create --title "<extracted>" --json` → returns epic-id → `flowctl epic set-plan <epic-id> --file - --json <<EOF` (heredoc with rendered template). Optional `flowctl epic set-branch`.

### Forbidden behaviors

- **No tech-stack mentions unless the user stated them** (defer to `/flow-next:plan` per spec-kit convention).
- **No invented acceptance criteria** (must mark `[inferred]` and confirm at read-back).
- **No silent overwrite** (idempotency guard; `--rewrite` required to overwrite an existing spec).
- **No code snippets or specific file paths** (those belong in `/flow-next:plan`).

### Spec template

Capture writes the **CLAUDE.md richer template**: `## Goal & Context` / `## Architecture & Data Models` / `## API Contracts` / `## Edge Cases & Constraints` / `## Acceptance Criteria` / `## Boundaries` / `## Decision Context`. Acceptance criteria use R-IDs (`- **R1:** ...`) per repo convention. Spec footer prints "Suggested next step: `/flow-next:plan <epic-id>` (break into tasks) or `/flow-next:interview <epic-id>` (refine via Q&A)."

**Exit codes:**
- Ralph-block (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`) → exit **2**.
- Compaction detected without `--from-compacted-ok` → exit **2** with stderr hint.
- Existing epic without `--rewrite <id>` → triggers Phase 0 duplicate-detection branch (extend / supersede / proceed-anyway).

---

## Agent Readiness Assessment

> Inspired by [Factory.ai's Agent Readiness framework](https://factory.ai/news/agent-readiness)

`/flow-next:prime` assesses your codebase for agent-readiness and proposes improvements. Works for greenfield and brownfield projects.

### The Problem

Agents waste cycles when codebases lack:
- **Pre-commit hooks** → waits 10min for CI instead of 5sec local feedback
- **Documented env vars** → guesses, fails, guesses again
- **CLAUDE.md** → doesn't know project conventions
- **Test commands** → can't verify changes work

These are **environment problems**, not agent problems. Prime helps fix them.

### Quick Start

```bash
/flow-next:prime                 # Full assessment + interactive fixes
/flow-next:prime --report-only   # Just show the report
/flow-next:prime --fix-all       # Apply all fixes without asking
```

### The Eight Pillars

Prime evaluates your codebase across eight pillars (48 criteria total):

#### Agent Readiness (Pillars 1-5) — Scored, Fixes Offered

| Pillar | What It Checks |
|--------|----------------|
| **1. Style & Validation** | Linters, formatters, type checking, pre-commit hooks |
| **2. Build System** | Build tool, commands, lock files, monorepo tooling |
| **3. Testing** | Test framework, commands, verification, coverage, E2E |
| **4. Documentation** | README, CLAUDE.md, setup docs, architecture |
| **5. Dev Environment** | .env.example, Docker, devcontainer, runtime version |

#### Production Readiness (Pillars 6-8) — Reported Only

| Pillar | What It Checks |
|--------|----------------|
| **6. Observability** | Structured logging, tracing, metrics, error tracking, health endpoints |
| **7. Security** | Branch protection, secret scanning, CODEOWNERS, Dependabot |
| **8. Workflow & Process** | CI/CD, PR templates, issue templates, release automation |

**Two-tier approach**: Pillars 1-5 determine your agent maturity level and are eligible for fixes. Pillars 6-8 are reported for visibility but no fixes are offered — these are team/production decisions.

### Maturity Levels

| Level | Name | Description | Overall Score |
|-------|------|-------------|---------------|
| 1 | Minimal | Basic project structure only | <30% |
| 2 | Functional | Can build and run, limited docs | 30-49% |
| 3 | **Standardized** | Agent-ready for routine work | 50-69% |
| 4 | Optimized | Fast feedback loops, comprehensive docs | 70-84% |
| 5 | Autonomous | Full autonomous operation capable | 85%+ |

**Level 3 is the target** for most teams. It means agents can handle routine work: bug fixes, tests, docs, dependency updates.

### How It Works

1. **Parallel Assessment** — 9 sonnet scouts run in parallel (~15-20 seconds):

   Agent Readiness scouts:
   - `tooling-scout` — linters, formatters, pre-commit, type checking
   - `claude-md-scout` — CLAUDE.md/AGENTS.md analysis
   - `env-scout` — environment setup
   - `testing-scout` — test infrastructure
   - `build-scout` — build system
   - `docs-gap-scout` — README, ADRs, architecture docs

   Production Readiness scouts:
   - `observability-scout` — logging, tracing, metrics, health endpoints
   - `security-scout` — GitHub API checks, CODEOWNERS, Dependabot
   - `workflow-scout` — CI/CD, templates, automation

2. **Verification** — Verifies test commands actually work (e.g., `pytest --collect-only`)

3. **Synthesize Report** — Calculates Agent Readiness score, Production Readiness score, and maturity level

4. **Interactive Remediation** — Uses `AskUserQuestion` for agent readiness fixes only:
   ```
   Which tooling improvements should I add?
   ☐ Add pre-commit hooks (Recommended)
   ☐ Add linter config
   ☐ Add runtime version file
   ```

5. **Apply Fixes** — Creates/modifies files based on your selections

6. **Re-assess** — Optionally re-run to show improvement

### Example Report

```markdown
# Agent Readiness Report

**Repository**: my-project
**Assessed**: 2026-01-23

## Scores Summary

| Category | Score | Level |
|----------|-------|-------|
| **Agent Readiness** (Pillars 1-5) | 73% | Level 4 - Optimized |
| Production Readiness (Pillars 6-8) | 17% | — |
| **Overall** | 52% | — |

## Agent Readiness (Pillars 1-5)

| Pillar | Score | Status |
|--------|-------|--------|
| Style & Validation | 67% (4/6) | ⚠️ |
| Build System | 100% (6/6) | ✅ |
| Testing | 67% (4/6) | ⚠️ |
| Documentation | 83% (5/6) | ✅ |
| Dev Environment | 83% (5/6) | ✅ |

## Production Readiness (Pillars 6-8) — Report Only

| Pillar | Score | Status |
|--------|-------|--------|
| Observability | 33% (2/6) | ❌ |
| Security | 17% (1/6) | ❌ |
| Workflow & Process | 0% (0/6) | ❌ |

## Top Recommendations (Agent Readiness)

1. **Tooling**: Add pre-commit hooks — 5 sec feedback vs 10 min CI wait
2. **Tooling**: Add Python type checking — catch errors locally
3. **Docs**: Update README — replace generic template
```

### Remediation Templates

Prime offers fixes for agent readiness gaps (**not** team governance):

| Fix | What Gets Created |
|-----|-------------------|
| CLAUDE.md | Project overview, commands, structure, conventions |
| .env.example | Template with detected env vars |
| Pre-commit (JS) | Husky + lint-staged config |
| Pre-commit (Python) | `.pre-commit-config.yaml` |
| Linter config | ESLint, Biome, or Ruff config (if none exists) |
| Formatter config | Prettier or Biome config (if none exists) |
| .nvmrc/.python-version | Runtime version pinning |
| .gitignore entries | .env, build outputs, node_modules |

Templates adapt to your project's detected conventions and existing tools. Won't suggest ESLint if you have Biome, etc.

### User Consent Required

**By default, prime asks before every change** using interactive checkboxes. You choose what gets created.

- **Asks first** — uses `AskUserQuestion` tool for interactive selection per category
- **Never overwrites** existing files without explicit consent
- **Never commits** changes (leaves for you to review)
- **Never deletes** files
- **Merges** with existing configs when possible
- **Respects** your existing tools (won't add ESLint if you have Biome)

Use `--fix-all` to skip questions and apply everything. Use `--report-only` to just see the assessment.

### Flags

| Flag | Description |
|------|-------------|
| `--report-only` | Skip remediation, just show report |
| `--fix-all` | Apply all recommendations without asking |
| `<path>` | Assess a different directory |

---

### Interactive vs Autonomous (The Handoff)

After planning completes, you choose how to execute:

| Mode | Command | When to Use |
|------|---------|-------------|
| **Interactive** | `/flow-next:work fn-1` | Complex tasks, learning a codebase, taste matters, want to intervene |
| **Autonomous (Ralph)** | `scripts/ralph/ralph.sh` | Clear specs, bulk implementation, overnight runs |

**The heuristic:** If you can write checkboxes, you can Ralph it. If you can't, you're not ready to loop—you're ready to think.

For full autonomous mode, prepare 5-10 plans before starting Ralph. See [Ralph Mode](#ralph-autonomous-mode) for setup.

> 📖 Deep dive: [Ralph Mode: Why AI Agents Should Forget](https://medium.com/byte-sized-brainwaves/ralph-mode-why-ai-agents-should-forget-9f98bec6fc91)

---

## PR Feedback Resolution

`/flow-next:resolve-pr` closes out GitHub PR review feedback in one shot: fetch unresolved threads → triage new vs already-answered → dispatch resolver agents → run project validation → commit + push → reply + resolve via GraphQL.

### Invocation

```bash
/flow-next:resolve-pr                         # all unresolved threads on current branch's PR
/flow-next:resolve-pr 123                     # all unresolved on PR #123
/flow-next:resolve-pr <comment-url>           # targeted — single thread only
/flow-next:resolve-pr --dry-run               # fetch + plan, no edits/commits/replies
/flow-next:resolve-pr --no-cluster            # skip cluster analysis, all items individual
```

### What it does

1. **Detect PR** from arg or current branch
2. **Fetch** unresolved review threads + top-level PR comments + review submission bodies via GraphQL
3. **Triage** new vs already-replied vs non-actionable review-bot wrapper text (silent drop)
4. **Cluster analysis** when prior rounds exist and spatial overlap is detected — dispatch one resolver per cluster for broader investigation
5. **Dispatch** resolver agents in parallel (Claude Code) or serial (Codex/Copilot/Droid), with file-overlap avoidance
6. **Validate** combined state with project's test suite once; failures on resolver-touched files escalate to `needs-human`
7. **Commit + push** only resolver-reported files (never `git add -A`)
8. **Reply + resolve** each thread via GraphQL; `needs-human` threads stay open with a natural acknowledgment reply
9. **Verify** — re-fetch, confirm resolved; bounded at 2 fix-verify cycles before escalating recurring patterns to user

### Safety

- **Untrusted input:** comment text is treated as context only; resolvers never execute shell commands from comment bodies.
- **Ralph-out:** this command is user-triggered only. Ralph's autonomous loop does not invoke it — humans review, comments land, user runs `/flow-next:resolve-pr` once per review round.
- **Bounded loop:** 2 fix-verify cycles max; 3rd attempt surfaces the recurring pattern to the user rather than looping infinitely.
- **Zero runtime deps beyond `gh` + `jq`** — all GraphQL logic in bundled bash scripts.

See [CHANGELOG](../../CHANGELOG.md) for the full 0.34.0 entry.

---

## Troubleshooting

### Reset a stuck task

```bash
# Check task status
flowctl show fn-1.2 --json

# Reset to todo (from done/blocked)
flowctl task reset fn-1.2

# Reset + dependents in same epic
flowctl task reset fn-1.2 --cascade
```

### Clean up `.flow/` safely

Run manually in terminal (not via AI agent):

```bash
# Remove all flow state (keeps git history)
rm -rf .flow/

# Re-initialize
flowctl init
```

### Debug Ralph runs

```bash
# Check run progress
cat scripts/ralph/runs/*/progress.txt

# View iteration logs
ls scripts/ralph/runs/*/iter-*.log

# Check for blocked tasks
ls scripts/ralph/runs/*/block-*.md
```

### Receipt validation failing

```bash
# Check receipt exists
ls scripts/ralph/runs/*/receipts/

# Verify receipt format
cat scripts/ralph/runs/*/receipts/impl-fn-1.1.json
# Must have: {"type":"impl_review","id":"fn-1.1",...}
```

### Custom rp-cli instructions conflicting

> **Caution**: If you have custom instructions for `rp-cli` in your `CLAUDE.md` or `AGENTS.md`, they may conflict with Flow-Next's RepoPrompt integration.

Flow-Next's plan-review and impl-review skills include specific instructions for `rp-cli` usage (window selection, builder workflow, chat commands). Custom rp-cli instructions can override these and cause unexpected behavior.

**Symptoms:**
- Reviews not using the correct RepoPrompt window
- Builder not selecting expected files
- Chat commands failing or behaving differently

**Fix:** Remove or comment out custom rp-cli instructions from your `CLAUDE.md`/`AGENTS.md` when using Flow-Next reviews. The plugin provides complete rp-cli guidance.

---

## Uninstall

Run manually in terminal (DCG blocks these from AI agents):

```bash
rm -rf .flow/               # Core flow state
rm -rf scripts/ralph/       # Ralph (if enabled)
```

Or use `/flow-next:uninstall` which cleans up docs and prints commands to run.

---

## Ralph (Autonomous Mode)

> **⚠️ Safety first**: Ralph defaults to `YOLO=1` (skips permission prompts).
> - Start with `ralph_once.sh` to observe one iteration
> - Consider [Docker sandbox](https://docs.docker.com/ai/sandboxes/claude-code/) for isolation
> - Consider [DCG (Destructive Command Guard)](https://github.com/Dicklesworthstone/destructive_command_guard) to block destructive commands — see [DCG setup](docs/ralph.md#additional-safety-dcg-optional)
>
> **Community sandbox setups** (alternative approaches):
> - [devcontainer-for-claude-yolo-and-flow-next](https://github.com/Ranudar/devcontainer-for-claude-yolo-and-flow-next) — VS Code devcontainer with Playwright, firewall whitelisting, and RepoPrompt MCP bridge
> - [agent-sandbox](https://github.com/novotnyllc/agent-sandbox) — Docker Sandbox (Desktop 4.50+) with seccomp/user namespace isolation, .NET + Node.js

Ralph is the repo-local autonomous loop that plans and works through tasks end-to-end.

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

Ralph writes run artifacts under `scripts/ralph/runs/`, including review receipts used for gating.

📖 **[Ralph deep dive](docs/ralph.md)**

🖥️ **[Ralph TUI](../../flow-next-tui/)** — Terminal UI for monitoring runs in real-time (`bun add -g @gmickel/flow-next-tui`)

### How Ralph Differs from Other Autonomous Agents

Autonomous coding agents are taking the industry by storm—loop until done, commit, repeat. Most solutions gate progress by tests and linting alone. Ralph goes further.

**Multi-model review gates**: Ralph uses [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) (macOS) or OpenAI Codex CLI (cross-platform) to send plan and implementation reviews to a *different* model. A second set of eyes catches blind spots that self-review misses. RepoPrompt's builder provides full file context; Codex uses context hints from changed files.

**Review loops until Ship**: Reviews don't just flag issues—they block progress until resolved. Ralph runs fix → re-review cycles until the reviewer returns `<verdict>SHIP</verdict>`. No "LGTM with nits" that get ignored.

**Receipt-based gating**: Reviews must produce a receipt JSON file proving they ran. No receipt = no progress. This prevents drift where Claude skips the review step and marks things done anyway.

**Guard hooks**: Plugin hooks enforce workflow rules deterministically—blocking `--json` flags, preventing new chats on re-reviews, requiring receipts before stop. Only active when `FLOW_RALPH=1`; zero impact for non-Ralph users. See [Guard Hooks](docs/ralph.md#guard-hooks).

**Atomic window selection**: The `setup-review` command handles RepoPrompt window matching atomically. Claude can't skip steps or invent window IDs—the entire sequence runs as one unit or fails.

The result: code that's been reviewed by two models, tested, linted, and iteratively refined. Not perfect, but meaningfully more robust than single-model autonomous loops.

### Controlling Ralph

External agents (Clawdbot, GitHub Actions, etc.) can pause/resume/stop Ralph runs without killing processes.

**CLI commands:**
```bash
# Check status
flowctl status                    # Epic/task counts + active runs
flowctl status --json             # JSON for automation

# Control active run
flowctl ralph pause               # Pause run (auto-detects if single)
flowctl ralph resume              # Resume paused run
flowctl ralph stop                # Request graceful stop
flowctl ralph status              # Show run state

# Specify run when multiple active
flowctl ralph pause --run <id>
```

**Sentinel files (manual control):**
```bash
# Pause: touch PAUSE file in run directory
touch scripts/ralph/runs/<run-id>/PAUSE
# Resume: remove PAUSE file
rm scripts/ralph/runs/<run-id>/PAUSE
# Stop: touch STOP file (kept for audit)
touch scripts/ralph/runs/<run-id>/STOP
```

Ralph checks sentinels at iteration boundaries (after Claude returns, before next iteration).

**Task retry/rollback:**
```bash
# Reset completed/blocked task to todo
flowctl task reset fn-1-add-oauth.3

# Reset + cascade to dependent tasks (same epic)
flowctl task reset fn-1-add-oauth.2 --cascade
```

---

## Human-in-the-Loop Workflow (Detailed)

Default flow when you drive manually:

```mermaid
flowchart TD
  A0{Have a target?} -- no --> A1[/flow-next:prospect hint/<br/>generate ranked candidates]
  A1 --> A2[.flow/prospects/<br/>ranked artifact]
  A2 --> A3[flowctl prospect promote --idea N<br/>creates epic from survivor]
  A3 --> AC{Need richer<br/>conversation-driven spec?}
  AC -- yes --> AK
  AC -- no --> A
  A0 -- yes --> AS{Already discussing<br/>in conversation?}
  AS -- yes --> AK[/flow-next:capture/<br/>synthesize conversation → spec<br/>source-tagged + read-back]
  AS -- no --> A
  AK --> AKS[.flow/specs/&lt;epic-id&gt;.md]
  AKS --> A
  A[Idea or short spec<br/>prompt or doc] --> B{Need deeper spec?}
  B -- yes --> C[Optional: /flow-next:interview fn-N or spec.md<br/>40+ deep questions to refine spec]
  C --> D[Refined spec]
  B -- no --> D
  D --> E[/flow-next:plan idea or fn-N/]
  E --> F[Parallel subagents: repo patterns + online docs + best practices]
  F --> G[flow-gap-analyst: edge cases + missing reqs]
  G --> H[Writes .flow/ epic + tasks + deps]
  H --> I{Plan review?}
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
  Q --> R{Impl review?}
  R -- yes --> S[/flow-next:impl-review/]
  S --> T{Next ready task?}
  R -- no --> T
  T -- yes --> N
  T -- no --> V{Epic review?}
  V -- yes --> W[/flow-next:epic-review fn-N/]
  W --> X{Epic passes review?}
  X -- no --> Y[Fix gaps inline]
  Y --> W
  X -- yes --> U[Close epic]
  V -- no --> U
  classDef optional stroke-dasharray: 6 4,stroke:#999;
  class C,J,S,W,A1,A2,A3,AC,AS,AK,AKS optional;
```

Notes:
- `/flow-next:prospect` accepts an optional focus hint (concept / path / constraint / volume) and writes a ranked artifact under `.flow/prospects/` — see [Prospecting](#prospecting). Two downstream paths from a survivor: **direct** (`flowctl prospect promote --idea N` → ready epic, jump to plan) or **through capture** (hand the survivor to `/flow-next:capture` for a richer conversation-driven spec).
- `/flow-next:capture` synthesizes the current conversation (free-form discussion or post-prospect refinement) into an epic spec at `.flow/specs/<epic-id>.md` via existing `flowctl epic create + epic set-plan`. Mandatory read-back; source-tagged criteria. Ralph-blocked.
- `/flow-next:interview` accepts Flow IDs or spec file paths and writes refinements back
- `/flow-next:plan` accepts new ideas or an existing Flow ID to update the plan

Tip: with RP 1.5.68+, use `flowctl rp setup-review --create` to auto-open RepoPrompt windows. Alternatively, open RP on your repo beforehand for faster context loading.
Plan review in rp mode requires `flowctl rp chat-send`; if rp-cli/windows unavailable, the review gate retries.

---

## Features

Built for reliability. These are the guardrails.

**Re-anchoring prevents drift**

Before EVERY task, Flow-Next re-reads the epic spec, task spec, and git state from `.flow/`. This forces Claude back to the source of truth - no hallucinated scope creep, no forgotten requirements. In Ralph mode, this happens automatically each iteration.

Unlike agents that carry accumulated context (where early mistakes compound), re-anchoring gives each task a fresh, accurate starting point.

### Re-anchoring

Before EVERY task, Flow-Next re-reads:
- Epic spec and task spec from `.flow/`
- Current git status and recent commits
- Validation state

Per Anthropic's long-running agent guidance: agents must re-anchor from sources of truth to prevent drift. The reads are cheap; drift is expensive.

### Multi-user Safe

Teams can work in parallel branches without coordination servers:

- **Merge-safe IDs**: Scans existing files to allocate the next ID. No shared counters.
- **Soft claims**: Tasks track an `assignee` field. Prevents accidental duplicate work.
- **Actor resolution**: Auto-detects from git email, `FLOW_ACTOR` env, or `$USER`.
- **Local validation**: `flowctl validate --all` catches issues before commit.

```bash
# Actor A starts task
flowctl start fn-1.1   # Sets assignee automatically

# Actor B tries same task
flowctl start fn-1.1   # Fails: "claimed by actor-a@example.com"
flowctl start fn-1.1 --force  # Override if needed
```

### Parallel Worktrees

Multiple agents can work simultaneously in different git worktrees, sharing task state:

```bash
# Main repo
git worktree add ../feature-a fn-1-branch
git worktree add ../feature-b fn-2-branch

# Both worktrees share task state via .git/flow-state/
cd ../feature-a && flowctl start fn-1.1   # Agent A claims task
cd ../feature-b && flowctl start fn-2.1   # Agent B claims different task
```

**How it works:**
- Runtime state (status, assignee, evidence) lives in `.git/flow-state/` — shared across worktrees
- Definition files (title, description, deps) stay in `.flow/` — tracked in git
- Per-task `fcntl` locking prevents race conditions

**State directory resolution:**
1. `FLOW_STATE_DIR` env (explicit override)
2. `git --git-common-dir` + `/flow-state` (worktree-aware)
3. `.flow/state` fallback (non-git or old git)

**Commands:**
```bash
flowctl state-path                # Show resolved state directory
flowctl migrate-state             # Migrate existing repo (optional)
flowctl migrate-state --clean     # Migrate + remove runtime from tracked files
```

**Backward compatible** — existing repos work without migration. The merged read path automatically falls back to definition files when no state file exists.

### Zero Dependencies

Everything is bundled:
- `flowctl.py` ships with the plugin
- No external tracker CLI to install
- No external services
- Just Python 3

### Bundled Skills

Utility skills available during planning and implementation:

| Skill | Use Case |
|-------|----------|
| `browser` | Web automation via agent-browser CLI (verify UI, scrape docs, test flows) |
| `flow-next-rp-explorer` | Token-efficient codebase exploration via RepoPrompt |
| `flow-next-worktree-kit` | Git worktree management for parallel work |
| `flow-next-export-context` | Export context for external LLM review |

### Non-invasive

- No daemons
- No CLAUDE.md edits
- Delete `.flow/` to uninstall; if you enabled Ralph, also delete `scripts/ralph/`
- Ralph uses plugin hooks for workflow enforcement (only active when `FLOW_RALPH=1`)

### CI-ready

```bash
flowctl validate --all
```

Exits 1 on errors. Drop into pre-commit hooks or GitHub Actions. See `docs/ci-workflow-example.yml`.

### One File Per Task

Each epic and task gets its own JSON + markdown file pair. Merge conflicts are rare and easy to resolve.

### Investigation Targets

Plan writes explicit investigation targets into each task spec — files the worker must read before writing code. Workers read every required file, note patterns and constraints, then search for similar existing functionality (`reuse > extend > new`). Reduces hallucination, ensures pattern conformance, prevents duplicate implementations.

### Requirement Traceability

Epic specs include a requirement coverage table mapping each requirement to its implementing task(s). Plan-sync maintains the table as implementation drifts. Epic-review uses it for bidirectional coverage checking — spec→code (missed requirements) and code→spec (scope creep detection).

### Typed Escalation

When a worker blocks on a task, it emits a structured message with a category (`SPEC_UNCLEAR`, `DEPENDENCY_BLOCKED`, `DESIGN_CONFLICT`, `SCOPE_EXCEEDED`, `TOOLING_FAILURE`, `EXTERNAL_BLOCKED`). Faster triage than free-form "I'm stuck" messages.

### Confidence Qualifiers

Scout agents (repo-scout, context-scout) tag every finding as `[VERIFIED]` (confirmed via tool output) or `[INFERRED]` (deduced from patterns). Downstream consumers can weight findings appropriately and know which claims need validation.

### Test Budget Awareness

Quality-auditor flags disproportionate test generation — when test lines exceed 2:1 ratio vs implementation lines. Advisory only; doesn't block. Catches the common failure mode where agents generate massive test suites to avoid implementing hard logic.

### DESIGN.md Awareness

When a project has a [DESIGN.md](https://stitch.withgoogle.com/docs/design-md/overview/) file (Google Stitch format), flow-next detects it and injects design context at each pipeline stage:

- **Planning**: repo-scout reads DESIGN.md, plan writes `## Design context` in frontend task specs with relevant color/component/typography tokens
- **Implementation**: worker reads referenced DESIGN.md sections before coding, uses design tokens over hard-coded values
- **Readiness**: `/flow-next:prime` checks for DESIGN.md in Pillar 4 (Documentation) as informational criterion
- **Quality audit**: quality-auditor flags hard-coded colors/spacing in frontend files when design tokens exist (advisory)

Backend tasks are not affected — design injection only applies to tasks touching frontend files.

No DESIGN.md? No change in behavior. The feature is entirely opt-in.

### Cross-Model Reviews

Two models catch what one misses. Reviews use a second model (via RepoPrompt, Codex, or GitHub Copilot CLI) to verify plans and implementations before they ship.

**Three review types:**
- **Plan reviews** — Verify architecture before coding starts
- **Impl reviews** — Verify each task implementation
- **Completion reviews** — Verify epic delivers all spec requirements before closing

**Review criteria (Carmack-level, identical for all backends):**

| Review Type | Criteria |
|-------------|----------|
| **Plan** | Completeness, Feasibility, Clarity, Architecture, Risks (incl. security), Scope, Testability |
| **Impl** | Correctness, Simplicity, DRY, Architecture, Edge Cases, Tests, Security |
| **Completion** | Spec compliance: all requirements delivered, docs updated, no gaps |

Reviews block progress until `<verdict>SHIP</verdict>`. Fix → re-review cycles continue until approved.

#### RepoPrompt (Recommended)

[RepoPrompt](https://repoprompt.com/?atp=KJbuL4) provides the best review experience on macOS.

**Why recommended:**
- Best-in-class context builder for reviews (full file context, smart selection)
- Enables **context-scout** for deeper codebase discovery (alternative: repo-scout works without RP)
- Visual diff review UI + persistent chat threads

**Setup:**

1. Install RepoPrompt (v2.1.6+ recommended):
   ```bash
   brew install --cask repoprompt
   ```
   Already installed? Update via RepoPrompt → Check for Updates, or `brew upgrade --cask repoprompt`.

2. **Enable MCP Server** (required for rp-cli):
   - Settings → MCP Server → Enable
   - Click "Install CLI to PATH" (creates `/usr/local/bin/rp-cli`)
   - Verify: `rp-cli --version` (should show 2.1.6+)

3. **Configure models** — RepoPrompt uses two models that must be set in the UI (not controllable via CLI):

   | Setting | Recommended | Purpose |
   |---------|-------------|---------|
   | **Context Builder model** | GPT-5.3 Codex Medium (via Codex CLI or OpenAI API) | Builds file selection for reviews. Needs large context window. |
   | **Chat model** | GPT-5.2 High (via Codex CLI or OpenAI API) | Runs the actual review. Needs strong reasoning. |

   Set these in Settings → Models. Any OpenAI API-compatible model works (Codex CLI, OpenAI API key, or other providers). These models are what make cross-model review valuable — a different model catches blind spots that self-review misses.

   > **Note:** When `--create` auto-opens a new workspace, it inherits your default model settings. Configure models before first use.

**Usage:**
```bash
/flow-next:plan-review fn-1 --review=rp
/flow-next:impl-review --review=rp
```

#### Codex (Cross-Platform Alternative)

OpenAI Codex CLI works on any platform (macOS, Linux, Windows). Flow-Next is also a [native Codex plugin](#openai-codex) — install via `install-codex.sh` (clone the repo, run the script).

**Why use Codex:**
- Cross-platform (no macOS requirement)
- Terminal-based (no GUI needed)
- Session continuity via thread IDs
- Same Carmack-level review criteria as RepoPrompt
- Uses GPT 5.4 High by default when used as a review backend from Claude Code (no config needed)

**Trade-off:** Uses heuristic context hints from changed files rather than RepoPrompt's intelligent file selection.

> **Note:** When running Flow-Next inside Codex as a native plugin, commands use `$` prefix (e.g., `$flow-next-impl-review`). The `/flow-next:` prefix below applies to Claude Code.

**Setup:**
```bash
# Install and authenticate Codex CLI
npm install -g @openai/codex
codex auth
```

**Usage:**
```bash
/flow-next:plan-review fn-1 --review=codex
/flow-next:impl-review --review=codex

# Or via flowctl directly
flowctl codex plan-review fn-1 --base main
flowctl codex impl-review fn-1.3 --base main
```

**Verify installation:**
```bash
flowctl codex check
```

#### GitHub Copilot CLI (Cross-Platform Alternative)

[GitHub Copilot CLI](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) is a third review backend. Works on any platform, routes through GitHub's Copilot models (Claude 4.5 + GPT-5.2 families).

**Why use Copilot:**
- Cross-platform (macOS, Linux, Windows)
- Access to Claude Sonnet/Opus/Haiku 4.5 and GPT-5.2 families through a single CLI
- Session continuity via client-generated UUIDs (flowctl stores the UUID, passes `--resume=<uuid>` for re-reviews)
- Same Carmack-level review criteria as RepoPrompt and Codex
- `flowctl copilot check` does a live auth probe (not just a binary presence check)

**Trade-off:** Like Codex, uses heuristic context hints from changed files rather than RepoPrompt's intelligent file selection. Premium-request billing applies per review.

**Setup:**
```bash
# Install Copilot CLI (npm-based)
npm install -g @github/copilot

# Authenticate — either interactive login (uses your GitHub account)
copilot login

# Or set a fine-grained PAT with "Copilot Requests" read/write permission
export GITHUB_TOKEN=<your-pat>
```

**Usage:**
```bash
/flow-next:plan-review fn-1 --review=copilot
/flow-next:impl-review --review=copilot

# Or via flowctl directly
flowctl copilot plan-review fn-1 --base main
flowctl copilot impl-review fn-1.3 --base main
flowctl copilot completion-review fn-1
```

**Verify installation:**
```bash
flowctl copilot check
```

This runs a trivial live probe (`-p "ok"` with `claude-haiku-4.5`) so auth failures surface here, not during the first real review. `/flow-next:setup` also auto-detects `copilot` on `PATH` and offers it as a review backend option.

**Runtime configuration (env vars):**

Model + effort are env-only — no CLI flags. Resolved via `env > arg > default` cascade in flowctl's `_resolve_copilot_model_effort()` and stamped into every receipt (`model` + `effort` keys) so reviews are reproducible.

| Var | Default | Notes |
|---|---|---|
| `FLOW_COPILOT_MODEL` | `gpt-5.2` | Override the review model. Catalog: `claude-sonnet-4.5`, `claude-haiku-4.5`, `claude-opus-4.5`, `claude-sonnet-4`, `gpt-5.2`, `gpt-5.2-codex`, `gpt-5-mini`, `gpt-4.1`. |
| `FLOW_COPILOT_EFFORT` | `high` | Reasoning effort: `low` \| `medium` \| `high` \| `xhigh`. **Claude-family models reject `--effort`** — flowctl omits the flag automatically for them. |
| `FLOW_COPILOT_EMBED_MAX_BYTES` | `512000` | File embedding budget. `0` = unlimited. Mirrors the Codex budget var. |

```bash
# Per-session override
export FLOW_COPILOT_MODEL=claude-haiku-4.5
export FLOW_COPILOT_EFFORT=medium
/flow-next:impl-review --review=copilot
```

Ralph's `scripts/ralph/config.env` declares all three vars. `ralph.sh` only exports them when set (conditional export) — empty values would clobber flowctl defaults, so leaving a var unset in `config.env` cleanly falls back to the defaults above.

#### Configuration

Set default review backend (bare or spec form — `backend[:model[:effort]]`):
```bash
# Per-project (saved in .flow/config.json)
flowctl config set review.backend rp                        # bare backend
flowctl config set review.backend codex:gpt-5.5:xhigh       # full spec
flowctl config set review.backend copilot:claude-opus-4.5   # backend + model, default effort

# Per-session (environment variable) — same grammar as config key
export FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5:xhigh

# Per-task / per-epic pinning (stored in .flow/tasks/<id>.json / .flow/epics/<id>.json)
flowctl task set-backend fn-5.2 --review "codex:gpt-5.2"
flowctl epic set-backend fn-5   --review "copilot:claude-sonnet-4.5:high"
```

**Priority cascade** (first match wins):

1. `--spec backend:model:effort` CLI flag on review commands
2. Per-task `review` field (`.flow/tasks/<id>.json`)
3. Per-epic `default_review` field (`.flow/epics/<id>.json`)
4. `FLOW_REVIEW_BACKEND` env var (full spec accepted)
5. `.flow/config.json` `review.backend`
6. Backend-specific env vars fill missing fields only: `FLOW_CODEX_MODEL`, `FLOW_CODEX_EFFORT`, `FLOW_COPILOT_MODEL`, `FLOW_COPILOT_EFFORT`
7. Registry defaults (see table below)

Invalid specs are rejected at `set-backend` time with a helpful error listing valid values. Legacy bare-backend values (`codex`, `copilot`, `rp`) still work. Unparseable strings stored on disk fall back to bare backend with a stderr warning — never crash.

**Spec grammar — `backend[:model[:effort]]`:**

| Backend | Supported models | Supported efforts | Default model | Default effort |
|---------|------------------|-------------------|---------------|----------------|
| `rp` | _(bare only — model set via window/session)_ | _(n/a)_ | _n/a_ | _n/a_ |
| `codex` | `gpt-5.5`, `gpt-5.4`, `gpt-5.2`, `gpt-5`, `gpt-5-mini`, `gpt-5-codex` | `none`, `minimal`, `low`, `medium`, `high`, `xhigh` | `gpt-5.5` | `high` |
| `copilot` | `claude-sonnet-4.5`, `claude-haiku-4.5`, `claude-opus-4.7`, `claude-opus-4.6`, `claude-opus-4.5`, `claude-sonnet-4`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`, `gpt-5.2`, `gpt-5.2-codex`, `gpt-5-mini`, `gpt-4.1` | `low`, `medium`, `high`, `xhigh` | `gpt-5.5` | `high` |
| `none` | _(explicit opt-out)_ | _(n/a)_ | _n/a_ | _n/a_ |

Notes:
- `rp:model` and `rp:model:effort` are rejected — RepoPrompt picks model via its window/session config, not per-call.
- Codex `minimal` effort passes flowctl validation but is rejected server-side when `web_search` is enabled. Safe for flowctl reviews (no `web_search` used).
- Copilot `claude-*` models reject `--effort` at runtime — flowctl drops the flag automatically.
- Field-level resolution: env fills **missing** spec fields only. Task spec `codex:gpt-5.2` plus `FLOW_CODEX_EFFORT=low` resolves to `codex:gpt-5.2:low`. Same task with `FLOW_CODEX_MODEL=gpt-5.4` still resolves to `codex:gpt-5.2:low` — explicit spec values win over env.
- To override a stored task spec for one session, set `FLOW_REVIEW_BACKEND=codex:gpt-5.4:high` (full spec) or pass `--spec codex:gpt-5.4:high` on the review command.

**Inspect resolved backend:**
```bash
flowctl review-backend                    # prints bare backend (skill grep)
flowctl review-backend --json             # {"backend": "...", "spec": "...", "model": "...", "effort": "...", "source": "env"}
flowctl task show-backend fn-5.2 --json   # per-task raw + resolved + field-level sources
```

**Receipt schema:** reviews stamp `{"mode", "model", "effort", "spec"}` into receipts. `spec` is the canonical round-trippable form (`str(resolved_spec)`); `model` + `effort` stay for back-compat with older readers.

**No auto-detect.** Run `/flow-next:setup` to configure your preferred review backend, or pass `--review=X` (or `--spec backend:model:effort`) explicitly.

#### Which to Choose?

| Scenario | Recommendation |
|----------|----------------|
| macOS with GUI available | RepoPrompt (best context builder) |
| Linux/Windows, terminal-only | Codex or Copilot |
| CI/headless environments | Codex or Copilot (no GUI needed) |
| Want Claude 4.5 + GPT-5.2 under one CLI | Copilot |
| Want session continuity + thread IDs | Codex or Copilot |
| Ralph overnight runs | Any works; RP auto-opens with --create (1.5.68+); Copilot/Codex need no window |

Without a backend configured, reviews fail with a clear error. Run `/flow-next:setup` or pass `--review=X`.

### Opt-in Review Flags (v0.35.0+)

Three opt-in flags on `/flow-next:impl-review` layer extra capability **on top** of the default Carmack-level single-chat review. All three are off by default; the default review shape is unchanged. Receipt extensions are additive — existing Ralph scripts ignore unknowns.

Phase ordering when flags combine: **primary → deep → validate → interactive → verdict**.

**`--validate` — drop false-positive findings.** On a `NEEDS_WORK` verdict, dispatches a validator pass in the same backend chat session (session resume via receipt). Each finding is independently re-checked against the current code; confirmed false-positives are dropped with logged reasons. If all drop, the verdict upgrades `NEEDS_WORK → SHIP` (never downgrades from `SHIP` or `MAJOR_RETHINK`). Conservative bias — "only drop if clearly wrong; when uncertain, keep" (missing ids in validator output default to kept).

```bash
/flow-next:impl-review --validate
FLOW_VALIDATE_REVIEW=1 /flow-next:impl-review  # env opt-in (Ralph-compatible)
```

Receipt fields: `validator: {dispatched, dropped, kept, reasons}`, `validator_timestamp`, `verdict_before_validate` (on upgrade).

**`--deep` — additional specialized passes on top of primary.** Runs the primary Carmack-level review first, then layers deep passes in the same backend session:

- **Adversarial** — always when `--deep`.
- **Security** — auto-enabled when the diff touches auth / authz / secrets / permission boundaries; force via `--deep=security`.
- **Performance** — auto-enabled when the diff touches perf-sensitive paths; force via `--deep=performance`.

Findings tagged `pass: <name>`; merged with primary via fingerprint dedup (primary wins on collision). Cross-pass agreement (primary + deep-pass flag the same finding) promotes the primary's confidence one anchor step (`0→25→50→75→100`, ceiling 100). Cross-deep collisions dedup without promotion. Deep may upgrade verdict `SHIP → NEEDS_WORK` when it surfaces new blocking `introduced` findings (records `verdict_before_deep`); deep never downgrades.

```bash
/flow-next:impl-review --deep                            # adversarial + auto-enabled passes
/flow-next:impl-review --deep=adversarial,security       # explicit pass selection
FLOW_REVIEW_DEEP=1 /flow-next:impl-review                # env opt-in (Ralph-compatible)
echo '<changed-files>' | flowctl review-deep-auto        # inspect auto-enabled passes
```

Receipt fields: `deep_passes`, `deep_findings_count` (per-pass dict), `cross_pass_promotions: [{id, from, to, pass}]`, `deep_timestamp`, `verdict_before_deep` (on upgrade).

**`--interactive` — per-finding walkthrough.** Presents a blocking question for each finding with four actions (Apply / Defer / Skip / Acknowledge) plus "LFG the rest" escape hatch. LFG auto-classifier: `P0/P1` at confidence ≥ 75 → Apply; otherwise → Defer. Deferred findings append to `.flow/review-deferred/<branch-slug>.md` (append-only; each review session gets a new `## <timestamp> — review session <receipt-id>` section). Walkthrough never flips the verdict.

**Ralph-incompatible by design** — the flag hard-errors when `REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1` is set, with a clear "not compatible with Ralph mode" message. No env var form; per-invocation only.

```bash
/flow-next:impl-review --interactive
```

Receipt fields: `walkthrough: {applied, deferred, skipped, acknowledged, lfg_rest}`, `walkthrough_timestamp`.

**Flag combination matrix:**

| Combo | Behavior |
|-------|----------|
| `--validate` alone | Primary → validate on `NEEDS_WORK` → drop confirmed false-positives |
| `--deep` alone | Primary + deep passes → merged findings → standard verdict |
| `--interactive` alone | Primary → walk through findings on `NEEDS_WORK` |
| `--validate --deep` | Primary + deep → validate the merged `NEEDS_WORK` |
| `--validate --interactive` | Primary + validate → walk through validated findings only |
| `--deep --interactive` | Primary + deep → walk through merged findings |
| `--validate --deep --interactive` | Full stack — maximum signal + human control |
| No flags (default) | Unchanged — Carmack-level single-chat primary review |

**Ralph compatibility summary:**

| Flag | Default in Ralph | Env opt-in |
|------|------------------|------------|
| `--validate` | off | `FLOW_VALIDATE_REVIEW=1` |
| `--deep` | off | `FLOW_REVIEW_DEEP=1` |
| `--interactive` | **blocked** (hard error) | none |

See [CHANGELOG — flow-next 0.35.0](../../CHANGELOG.md#flow-next-0350---2026-04-24) for the full entry.

### Review Rigor (v0.32.1+)

Five prompt-level + minimal-flowctl improvements that raise review signal and cut review cost. All three backends (rp, codex, copilot) benefit equally. Zero breaking changes — receipt additions are additive.

**1. Requirement-ID traceability (R-IDs).** Epic specs emit numbered acceptance criteria:

```markdown
## Acceptance criteria
- **R1:** OAuth login works for Google provider
- **R2:** Session persists across page reloads
- **R3:** Logout clears session tokens
```

Task specs optionally reference them via frontmatter:

```yaml
---
satisfies: [R1, R3]
---
```

Rules:
- Plain markdown prose, not YAML — keeps specs human-editable.
- **Renumber-forbidden** after the first review cycle. Deletions leave gaps (`R1, R3, R5` stays that way); new criteria take the next unused number.
- Plan skill writes R-IDs on creation; plan-sync preserves them through drift updates.
- Impl-review and epic-review emit a per-R-ID coverage table (met / partial / not-addressed / deferred).
- Any unaddressed R-ID flips verdict to `NEEDS_WORK`; receipt carries an `unaddressed: ["R2", "R5"]` array so the fix loop has targeted work.

**2. Confidence anchors (0 / 25 / 50 / 75 / 100).** Reviewers score every finding on exactly five discrete values:

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from code alone, zero interpretation. |
| 75 | Full execution path traced — input → branch → wrong output. |
| 50 | Depends on conditions visible but not fully confirmable. |
| 25 | Requires runtime conditions with no direct evidence. |
| 0 | Speculative. |

**Suppression gate:** after dedup, findings below 75 are dropped. Exception: P0 findings at 50+ survive. Reviews report `suppressed_count` by anchor; receipt optionally carries it as `{"50": 3, "25": 7, "0": 2}`.

**3. Introduced vs pre-existing.** Each finding is classified:
- `introduced: true` — caused by this branch's diff.
- `pre_existing: true` — broken on the base branch.

Verdict gate considers only `introduced` findings. Pre-existing issues surface in a separate non-blocking "Pre-existing issues" section. Receipt carries `introduced_count` + `pre_existing_count` so Ralph stops fighting bugs it didn't introduce.

**4. Protected artifacts.** Review prompts carry a hardcoded never-flag list — findings recommending deletion or gitignore of these paths are discarded during synthesis:

- `.flow/*` (specs, tasks, memory, state)
- `.flow/bin/*` (bundled flowctl)
- `.flow/memory/*` (learnings store)
- `docs/plans/*`, `docs/solutions/*` (when the project uses them)
- `scripts/ralph/*` (Ralph harness)

Prevents cross-model reviewers unfamiliar with flow-next conventions from proposing destructive cleanups.

**5. Trivial-diff skip.** `flowctl triage-skip --base <ref>` runs a deterministic whitelist (lockfile-only / docs-only / release-chore / generated-file-only) and returns `VERDICT=SHIP` without invoking the configured backend. Receipt is written with `mode: triage_skip`, `source: deterministic`, and a one-line reason.

```bash
flowctl triage-skip --base main
# VERDICT=SHIP
# reason=lockfile-only (bun.lock)
# source=deterministic
```

Optional LLM layer (gpt-5-mini / claude-haiku-4.5) for ambiguous diffs is gated behind `FLOW_TRIAGE_LLM=1`. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`. Saves rp / codex / copilot calls on trivial commits.

**Receipt schema (additive only).** All review receipts may carry these optional fields; existing consumers that read by key ignore unknowns:

```json
{
  "mode": "codex",
  "verdict": "NEEDS_WORK",
  "unaddressed": ["R2", "R5"],
  "suppressed_count": {"50": 3, "25": 7, "0": 2},
  "introduced_count": 2,
  "pre_existing_count": 4
}
```

See [CHANGELOG — flow-next 0.32.1](../../CHANGELOG.md#flow-next-0321---2026-04-24) for the full list.

### Dependency Graphs

Tasks declare their blockers. `flowctl ready` shows what can start. Nothing executes until dependencies resolve.

**Epic-level dependencies**: During planning, `epic-scout` runs in parallel with other research scouts to find relationships with existing open epics. If the new plan depends on APIs/patterns from another epic, dependencies are auto-set via `flowctl epic add-dep`. Findings reported at end of planning—no prompts needed.

### Auto-Block Stuck Tasks

After MAX_ATTEMPTS_PER_TASK failures (default 5), Ralph:
1. Writes `block-<task>.md` with failure context
2. Marks task blocked via `flowctl block`
3. Moves to next task

Prevents infinite retry loops. Review `block-*.md` files in the morning to understand what went wrong.

### Plan-Sync (Opt-in)

Synchronizes downstream task specs when implementation drifts from the original plan.

**Automatic (opt-in):**
```bash
flowctl config set planSync.enabled true
```

When enabled, after each task completes, a plan-sync agent:
1. Compares what was planned vs what was actually built
2. Identifies downstream tasks that reference stale assumptions (names, APIs, data structures)
3. Updates affected task specs with accurate info

Skip conditions: disabled (default), task failed, no downstream tasks.

**Cross-epic sync (opt-in, default false):**
```bash
flowctl config set planSync.crossEpic true
```

When enabled, plan-sync also checks other open epics for stale references. Useful when multiple epics share APIs/patterns, but increases sync time. Disabled by default to avoid long Ralph loops.

**Manual trigger:**
```bash
/flow-next:sync fn-1.2              # Sync from specific task
/flow-next:sync fn-1                # Scan whole epic for drift
/flow-next:sync fn-1.2 --dry-run    # Preview changes without writing
```

Manual sync ignores `planSync.enabled` config—if you run it, you want it. Works with any source task status (not just done).

### Memory System (Opt-in, categorized — v0.33.0+)

Persistent learnings that survive context compaction. One entry per file, YAML frontmatter, two tracks.

**Directory tree:**

```
.flow/memory/
├── bug/
│   ├── build-errors/
│   ├── test-failures/
│   ├── runtime-errors/
│   ├── performance/
│   ├── security/
│   ├── integration/
│   ├── data/
│   └── ui/
└── knowledge/
    ├── architecture-patterns/
    ├── conventions/
    ├── tooling-decisions/
    ├── workflow/
    └── best-practices/
```

**Frontmatter schema (bug track):**

```yaml
---
title: SQLite locked under concurrent writes
date: 2026-04-24
track: bug
category: runtime-errors
module: storage/sqlite
tags: [sqlite, concurrency, locking]
problem_type: race
root_cause: missing WAL mode
resolution_type: config-fix
---
```

**Frontmatter schema (knowledge track):**

```yaml
---
title: Prefer flowctl rp wrappers over direct rp-cli
date: 2026-04-24
track: knowledge
category: conventions
module: scripts/ralph
tags: [rp, ralph, review]
applies_when: writing Ralph loop scripts or review shims
---
```

**Enable + init:**

```bash
flowctl config set memory.enabled true
flowctl memory init   # creates directory tree
```

**Add (new categorized API):**

```bash
flowctl memory add \
  --track bug \
  --category runtime-errors \
  --title "SQLite locked under concurrent writes" \
  --module storage/sqlite \
  --tags "sqlite,concurrency" \
  --body-file /tmp/writeup.md

flowctl memory add \
  --track knowledge \
  --category conventions \
  --title "Prefer flowctl rp wrappers" \
  --module scripts/ralph \
  --tags "rp,ralph"
```

`--type pitfall|convention|decision` (the old API) still works but emits a deprecation warning. Removed in 0.36.0.

**Overlap detection** runs on every `add`. The command scans existing entries in the target category; high overlap updates the existing entry in place, moderate overlap creates a new entry with `related_to: [existing-id]` in its frontmatter. Prevents silent duplication drift.

**Query:**

```bash
flowctl memory list                                # default: active only
flowctl memory list --track bug                    # filter by track
flowctl memory list --category runtime-errors      # filter by category
flowctl memory list --status all                   # include stale entries

flowctl memory search "sqlite locked"              # default: --status active
flowctl memory search "sqlite locked" --status stale  # only stale entries
flowctl memory search "sqlite locked" --status all    # active + stale
flowctl memory search "rp wrappers" \
  --module scripts/ralph \
  --tags "rp,ralph" \
  --limit 5

flowctl memory read bug/runtime-errors/sqlite-locked-2026-04-24   # full id
flowctl memory read sqlite-locked-2026-04-24                       # slug+date
flowctl memory read sqlite-locked                                  # slug only (latest date)
flowctl memory read legacy/pitfalls.md                             # legacy flat file
flowctl memory read legacy/pitfalls#3                              # legacy entry (1-based)
```

Search scoring is weighted: title 5×, tags 3×, body 1.5×, misc 1×. Legacy hits surface as synthetic entries with `track: "legacy"`. Default `--status active` excludes stale entries (audit-flagged advice stops polluting `memory-scout` output); pass `--status stale` or `--status all` to include them.

**Audit lifecycle (v0.37.0+):**

`/flow-next:audit [mode:autofix] [scope hint]` walks `.flow/memory/`, reviews each entry against the current codebase, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete**. Interactive mode (default) asks via the platform's blocking-question tool; autofix mode applies unambiguous actions and marks ambiguous entries as stale. The skill is agent-native — host agent reads the workflow markdown and executes it directly using its own Read/Grep/Glob tools (no Python audit engine, no codex/copilot subprocess dispatch). Legacy flat files are skipped with a warning.

Two flowctl helpers back the audit lifecycle (also callable directly):

```bash
# Mark an entry stale (used by /flow-next:audit, also callable directly)
flowctl memory mark-stale <id> --reason "module renamed in PR #123"
flowctl memory mark-stale <id> --reason "..." --audited-by "/flow-next:audit"
flowctl memory mark-stale <id> --reason "..." --json

# Clear stale flag
flowctl memory mark-fresh <id>
```

`mark-stale` sets `status: stale`, stamps `last_audited` (UTC), records `audit_notes` from `--reason`. Body is never modified. Idempotent — re-marking replaces `audit_notes` and re-stamps the date. `mark-fresh` drops the stale fields and stamps `last_audited`.

**Migrate legacy → categorized (v0.37.0+):**

`/flow-next:memory-migrate [mode:autofix] [scope hint]` is the recommended path. Agent-native skill — host agent reads each legacy entry, classifies it into the right `(track, category)` pair using its own intelligence + repo context, writes a categorized entry via `flowctl memory add`. Interactive mode (default) asks via the platform's blocking-question tool on ambiguous entries; autofix mode accepts mechanical defaults and logs ambiguous as `needs-review`. Optional scope hint narrows to a single legacy file (e.g. `/flow-next:memory-migrate pitfalls.md`). Phase 4 cleanup writes a self-ignoring `.flow/memory/_migrated/.gitignore` and renames originals on user consent (autofix declines by default; never auto-deletes).

```bash
flowctl memory list-legacy            # text mode: filename + entry count + mechanical default per entry
flowctl memory list-legacy --json     # {files: [{filename, entry_count, entries: [...]}]}
```

`memory list-legacy` is the parsing helper the skill consumes; also useful for ad-hoc inspection. Each entry carries `mechanical_track` / `mechanical_category` derived from the source filename so the agent has a sane default to override only when content warrants.

**Automation / CI fallback:**

```bash
flowctl memory migrate --dry-run      # print plan (mechanical-only)
flowctl memory migrate --yes          # apply (mechanical-only)
```

`flowctl memory migrate` is **deterministic-only** since v0.37.0 — uses the mechanical filename → `(track, category)` heuristic. The `--no-llm` flag is accepted-but-noop (kept for back-compat with scripted callers). For accurate per-entry classification, run the `/flow-next:memory-migrate` skill instead.

`migrate` is idempotent — re-running after legacy files are archived prints `No legacy files to migrate.` JSON mode refuses writes without `--yes` as a safety guard.

> **Removed in v0.37.0:** `FLOW_MEMORY_CLASSIFIER_BACKEND`, `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT` env vars are no longer consumed (subprocess classifier dispatch removed). Setting them now triggers a one-time stderr warning. Suppress via `FLOW_NO_DEPRECATION=1`.

**Surface the store in AGENTS.md / CLAUDE.md:**

```bash
flowctl memory discoverability-patch              # auto-detect target, dry-run
flowctl memory discoverability-patch --apply      # write
flowctl memory discoverability-patch --target agents --strategy listing --apply
```

Two strategies: `listing` (injects `.flow/memory/` into an existing `.flow/` fenced code block) and `append` (adds a `## Memory / Learnings` section). Auto-detect prefers AGENTS.md when both are substantive; handles `@AGENTS.md` / `@CLAUDE.md` shims and symlinks. JSON callers must pass `--apply` explicitly — the command refuses destructive auto-writes.

**When enabled:**

- **Planning**: category-aware `memory-scout` runs in parallel with other scouts, returns track/category-tagged hits and prioritizes module matches.
- **Work**: worker reads relevant entries during re-anchor.
- **Ralph**: worker writes structured bug-track entries via `memory add --track bug --category <c>` on NEEDS_WORK → SHIP. Overlap detection handles duplicates.

Config lives in `.flow/config.json`, separate from Ralph's `scripts/ralph/config.env`.

**Upgrading from 0.32.x:**

1. `git pull && (reinstall plugin)`.
2. **Recommended:** run `/flow-next:memory-migrate` for agent-native per-entry classification (host agent reads each legacy entry and picks the right `(track, category)` with full repo context). Or `/flow-next:memory-migrate mode:autofix` to accept mechanical defaults without prompts.
3. **Automation alternative:** `flowctl memory migrate --dry-run` then `flowctl memory migrate --yes` for deterministic mechanical-only classification (legacy files move to `.flow/memory/_legacy/`; migration is idempotent).
4. Optional: `flowctl memory discoverability-patch --apply` to surface the tree in AGENTS.md.

Until migration runs, legacy flat files continue to work; `list` / `read` / `search` read both.

---

## Commands

Sixteen commands, complete workflow:

| Command | What It Does |
|---------|--------------|
| `/flow-next:prospect [hint]` | Generate ranked candidate ideas grounded in the repo, upstream of `capture`/`interview`/`plan` ([details](#prospecting)) |
| `/flow-next:capture [flags]` | Synthesize conversation context into an epic spec; source-tagged + mandatory read-back ([details](#capture)) |
| `/flow-next:plan <idea>` | Research the codebase, create epic with dependency-ordered tasks |
| `/flow-next:work <id\|file>` | Execute epic, task, or spec file, re-anchoring before each |
| `/flow-next:interview <id>` | Deep interview to flesh out a spec before planning |
| `/flow-next:plan-review <id>` | Carmack-level plan review (RepoPrompt, Codex, or Copilot) |
| `/flow-next:impl-review` | Carmack-level impl review of current branch |
| `/flow-next:epic-review <id>` | Epic-completion review: verify implementation matches spec |
| `/flow-next:resolve-pr [arg]` | Resolve GitHub PR review threads (fetch → triage → fix → reply → resolve) ([details](#pr-feedback-resolution)) |
| `/flow-next:audit [mode:autofix] [hint]` | Review `.flow/memory/` against current code, decide Keep/Update/Consolidate/Replace/Delete per entry ([details](#memory-system)) |
| `/flow-next:memory-migrate [mode:autofix] [hint]` | Convert pre-fn-30 legacy memory files into the categorized schema; agent classifies each entry ([details](#memory-system)) |
| `/flow-next:prime` | Assess codebase agent-readiness, propose fixes ([details](#agent-readiness-assessment)) |
| `/flow-next:sync <id>` | Manual plan-sync: update downstream tasks after implementation drift |
| `/flow-next:ralph-init` | Scaffold repo-local Ralph harness (`scripts/ralph/`) |
| `/flow-next:setup` | Optional: install flowctl locally + add docs (for power users) |
| `/flow-next:uninstall` | Remove flow-next from project (keeps tasks if desired) |

Work accepts an epic (`fn-N`), task (`fn-N.M`), or markdown spec file (`.md`). Spec files auto-create an epic with one task.

### Autonomous Mode (Flags)

All commands accept flags to skip questions:

```bash
# Plan with flags
/flow-next:plan Add caching --research=grep --no-review
/flow-next:plan Add auth --research=rp --review=rp

# Work with flags
/flow-next:work fn-1 --branch=current --no-review
/flow-next:work fn-1 --branch=new --review=export

# Reviews with flags
/flow-next:plan-review fn-1 --review=rp
/flow-next:impl-review --review=export
```

Natural language also works:

```bash
/flow-next:plan Add webhooks, use context-scout, skip review
/flow-next:work fn-1 current branch, no review
```

| Command | Available Flags |
|---------|-----------------|
| `/flow-next:prospect` | `[focus hint]` (positional) — concept / path / constraint / volume |
| `/flow-next:capture` | `mode:autofix` (positional), `--rewrite <epic-id>`, `--from-compacted-ok`, `--yes` |
| `/flow-next:plan` | `--research=rp\|grep`, `--review=rp\|codex\|copilot\|export\|none`, `--no-review` |
| `/flow-next:work` | `--branch=current\|new\|worktree`, `--review=rp\|codex\|copilot\|export\|none`, `--no-review` |
| `/flow-next:plan-review` | `--review=rp\|codex\|copilot\|export` |
| `/flow-next:impl-review` | `--review=rp\|codex\|copilot\|export` |
| `/flow-next:resolve-pr` | `--dry-run`, `--no-cluster` |
| `/flow-next:prime` | `--report-only`, `--fix-all` |
| `/flow-next:sync` | `--dry-run` |

### Command Reference

Detailed input documentation for each command.

#### `/flow-next:prospect`

```
/flow-next:prospect [focus hint]
```

| Input | Description |
|-------|-------------|
| `[focus hint]` | Optional freeform single string. Concept (`DX improvements`), path (`plugins/flow-next/skills/`), constraint (`quick wins under 200 LOC`), or volume hint (`top 3` / `50 ideas` / `raise the bar`). Empty = open-ended (15-25 candidates → 5-8 survivors). |

Output: `.flow/prospects/<slug>-<date>.md` (atomic write, same-day collisions suffixed `-2`/`-3`). Promote a survivor with `flowctl prospect promote <id> --idea N`. Hard-errors with exit 2 under Ralph (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`). See [Prospecting](#prospecting) for full phase details.

#### `/flow-next:capture`

```
/flow-next:capture [mode:autofix] [--rewrite <epic-id>] [--from-compacted-ok] [--yes]
```

| Input | Description |
|-------|-------------|
| `mode:autofix` | Optional positional. Skip per-question prompts; print full draft to stdout. Requires `--yes` to actually commit. |
| `--rewrite <epic-id>` | Overwrite an existing epic spec. Without this flag, a duplicate-epic detection refuses or asks: extend / supersede / proceed-anyway. |
| `--from-compacted-ok` | Override the compaction-detection refusal when the conversation has truncation markers. Use only when you trust the recent turns. |
| `--yes` | Required in autofix mode to actually commit (mirrors `flowctl memory migrate --yes`). |

Output: `.flow/specs/<epic-id>.md` via `flowctl epic create + epic set-plan` (no new flowctl subcommands). Acceptance criteria source-tagged (`[user]` / `[paraphrase]` / `[inferred]`); mandatory read-back surfaces `[inferred]` count via `AskUserQuestion`. Hard-errors with exit 2 under Ralph (`REVIEW_RECEIPT_PATH` or `FLOW_RALPH=1`) — capture requires conversation context + user confirmation, both unavailable in autonomous loops.

#### `/flow-next:plan`

```
/flow-next:plan <idea or fn-N> [--research=rp|grep] [--review=rp|codex|copilot|export|none]
```

| Input | Description |
|-------|-------------|
| `<idea>` | Free-form feature description ("Add user authentication with OAuth") |
| `fn-N` | Existing epic ID to update the plan |
| `--research=rp` | Use RepoPrompt context-scout for deeper codebase discovery |
| `--research=grep` | Use grep-based repo-scout (default, faster) |
| `--review=rp\|codex\|copilot\|export\|none` | Review backend after planning |
| `--no-review` | Shorthand for `--review=none` |

#### `/flow-next:work`

```
/flow-next:work <id|file> [--branch=current|new|worktree] [--review=rp|codex|copilot|export|none]
```

| Input | Description |
|-------|-------------|
| `fn-N` | Execute entire epic (all tasks in dependency order) |
| `fn-N.M` | Execute single task |
| `path/to/spec.md` | Create epic from spec file, execute immediately |
| `--branch=current` | Work on current branch |
| `--branch=new` | Create new branch `fn-N-slug` (default) |
| `--branch=worktree` | Create git worktree for isolated work |
| `--review=rp\|codex\|copilot\|export\|none` | Review backend after work |
| `--no-review` | Shorthand for `--review=none` |

#### `/flow-next:interview`

```
/flow-next:interview <id|file>
```

| Input | Description |
|-------|-------------|
| `fn-N` | Interview about epic to refine requirements |
| `fn-N.M` | Interview about specific task |
| `path/to/spec.md` | Interview about spec file |
| `"rough idea"` | Interview about a new idea (creates epic) |

Deep questioning (40+ questions) to surface requirements, edge cases, and decisions.

**Three behavioral patterns from upstream `grill-me` (0.38.0+):**

- **Lead-with-recommendation** — every `AskUserQuestion` body includes options summary, recommended option, one-sentence rationale, and a confidence tier:
  - `[high]` — strong codebase signal or convention match; the recommendation is load-bearing.
  - `[judgment-call]` — slight lean but reasonable people disagree; user's call carries weight.
  - `[your-call]` — agent has no signal; "I genuinely don't know — your priority / domain knowledge / preference."
  The third tier prevents the always-recommend habit that trains users to defer.
- **Codebase-before-asking** — pre-question taxonomy classifies each candidate question:
  - **Codebase-answerable** ("what exists / how wired / what conventions") → investigated via Read/Grep/Glob, logged to a new `## Resolved via Codebase` audit-trail section in the refined spec.
  - **User-judgment-required** ("what should / what tradeoff / what priority") → asked via `AskUserQuestion`.
  Eliminates wasteful "should we use PostgreSQL?" questions when grep can answer "is there already a DB layer?". If the agent finds itself answering a "should" question via grep, that's the bug.
- **Dependency-ordered branches** — depth cap of 4; discover-as-you-go (not pre-compute); abandoned branches are surfaced ("Skipping persistence questions — you said no DB"). One-question-per-turn invariant reaffirmed.

These three patterns are additive enhancements to **how** questions are asked, not what gets asked. Existing 40+ question coverage is unchanged.

#### `/flow-next:plan-review`

```
/flow-next:plan-review <fn-N> [--review=rp|codex|copilot|export] [focus areas]
```

| Input | Description |
|-------|-------------|
| `fn-N` | Epic ID to review |
| `--review=rp` | Use RepoPrompt (macOS, visual builder) |
| `--review=codex` | Use OpenAI Codex CLI (cross-platform) |
| `--review=copilot` | Use GitHub Copilot CLI (cross-platform) |
| `--review=export` | Export context for manual review |
| `[focus areas]` | Optional: "focus on security" or "check API design" |

Carmack-level criteria: Completeness, Feasibility, Clarity, Architecture, Risks, Scope, Testability.

#### `/flow-next:impl-review`

```
/flow-next:impl-review [--review=rp|codex|copilot|export] [focus areas]
```

| Input | Description |
|-------|-------------|
| `--review=rp` | Use RepoPrompt (macOS, visual builder) |
| `--review=codex` | Use OpenAI Codex CLI (cross-platform) |
| `--review=copilot` | Use GitHub Copilot CLI (cross-platform) |
| `--review=export` | Export context for manual review |
| `[focus areas]` | Optional: "focus on performance" or "check error handling" |

Reviews current branch changes. Carmack-level criteria: Correctness, Simplicity, DRY, Architecture, Edge Cases, Tests, Security.

#### `/flow-next:epic-review`

```
/flow-next:epic-review <fn-N> [--review=rp|codex|copilot|none]
```

| Input | Description |
|-------|-------------|
| `fn-N` | Epic ID to review |
| `--review=rp` | Use RepoPrompt (macOS, visual builder) |
| `--review=codex` | Use OpenAI Codex CLI (cross-platform) |
| `--review=copilot` | Use GitHub Copilot CLI (cross-platform) |
| `--review=none` | Skip review |

Reviews epic implementation against spec. Runs after all tasks complete. Catches requirement gaps, missing functionality, incomplete doc updates.

#### `/flow-next:resolve-pr`

```
/flow-next:resolve-pr [PR# | comment URL] [--dry-run] [--no-cluster]
```

| Input | Description |
|-------|-------------|
| (no args) | Resolve all unresolved threads on current branch's PR |
| `<PR#>` | Resolve all unresolved threads on the given PR |
| `<comment URL>` | Targeted — resolve only the single thread containing the comment |
| `--dry-run` | Fetch + plan; no edits, commits, or replies |
| `--no-cluster` | Skip cross-invocation cluster analysis; all items individual |

User-triggered only (Ralph does not invoke). Fetches threads + PR comments + review bodies via GraphQL, dispatches `pr-comment-resolver` agents (parallel on Claude Code, serial elsewhere), validates combined state, commits + pushes fixes, replies and resolves via GraphQL. See [PR Feedback Resolution](#pr-feedback-resolution).

#### `/flow-next:prime`

```
/flow-next:prime [--report-only] [--fix-all] [path]
```

| Input | Description |
|-------|-------------|
| (no args) | Assess current directory, interactive fixes |
| `--report-only` | Show assessment report, skip remediation |
| `--fix-all` | Apply all recommendations without asking |
| `[path]` | Assess a different directory |

See [Agent Readiness Assessment](#agent-readiness-assessment) for details.

#### `/flow-next:sync`

```
/flow-next:sync <id> [--dry-run]
```

| Input | Description |
|-------|-------------|
| `fn-N` | Sync entire epic's downstream tasks |
| `fn-N.M` | Sync from specific task |
| `--dry-run` | Preview changes without writing |

Updates downstream task specs when implementation drifts from plan.

#### `/flow-next:ralph-init`

```
/flow-next:ralph-init
```

No arguments. Scaffolds `scripts/ralph/` for autonomous operation.

#### `/flow-next:setup`

```
/flow-next:setup
```

No arguments. Optional setup that:
- Configures review backend (rp, codex, or none)
- Copies flowctl to `.flow/bin/`
- Adds flow-next instructions to CLAUDE.md/AGENTS.md

#### `/flow-next:uninstall`

```
/flow-next:uninstall
```

No arguments. Interactive removal with option to keep tasks.

---

## The Workflow

### Defaults (manual and Ralph)

Flow-Next uses the same defaults in manual and Ralph runs. Ralph bypasses prompts only.

- plan: `--research=grep`
- work: `--branch=new`
- review: from `.flow/config.json` (set via `/flow-next:setup`), or `none` if not configured

Override via flags or `scripts/ralph/config.env`.

### Planning Phase

1. **Research (parallel subagents)**: `repo-scout` (or `context-scout` if rp-cli) + `practice-scout` + `docs-scout` + `github-scout` + `epic-scout` + `docs-gap-scout`
2. **Gap analysis**: `flow-gap-analyst` finds edge cases + missing requirements
3. **Epic creation**: Writes spec to `.flow/specs/fn-N.md`, sets epic dependencies from `epic-scout` findings
4. **Task breakdown**: Creates tasks + explicit dependencies in `.flow/tasks/`, adds doc update acceptance criteria from `docs-gap-scout`
5. **Validate**: `flowctl validate --epic fn-N`
6. **Review** (optional): `/flow-next:plan-review fn-N` with re-anchor + fix loop until "Ship"

### Work Phase

1. **Re-anchor**: Re-read epic + task specs + git state (EVERY task)
2. **Execute**: Implement using existing patterns
3. **Test**: Verify acceptance criteria
4. **Record**: `flowctl done` adds summary + evidence to the task spec
5. **Review** (optional): `/flow-next:impl-review` via RepoPrompt, Codex, or Copilot
6. **Loop**: Next ready task → repeat until no ready tasks. Close epic manually (`flowctl epic close fn-N`) or let Ralph close at loop end.

---

## Ralph Mode (Autonomous, Opt-In)

Ralph is repo-local and opt-in. Files are created only by `/flow-next:ralph-init`. Remove manually with `rm -rf scripts/ralph/`.
`/flow-next:ralph-init` also writes `scripts/ralph/.gitignore` so run logs stay out of git.

What it automates (one unit per iteration, fresh context each time):
- Selector chooses plan vs work unit (`flowctl next`)
- Plan gate = plan review loop until Ship (if enabled)
- Work gate = one task until pass (tests + validate + optional impl review)
 - Single run branch: all epics work on one `ralph-<run-id>` branch (cherry-pick/revert friendly)

Enable:
```bash
/flow-next:ralph-init
./scripts/ralph/ralph_once.sh   # one iteration (observe)
./scripts/ralph/ralph.sh        # full loop (AFK)
```

**Watch mode** - see what Claude is doing:
```bash
./scripts/ralph/ralph.sh --watch           # Stream tool calls in real-time
./scripts/ralph/ralph.sh --watch verbose   # Also stream model responses
```

Run scripts from terminal (not inside Claude Code). `ralph_once.sh` runs one iteration so you can observe before going fully autonomous.

### Ralph defaults vs recommended (plan review gate)

`REQUIRE_PLAN_REVIEW` controls whether Ralph must pass the **plan review gate** before doing any implementation work.

**Default (safe, won't stall):**

* `REQUIRE_PLAN_REVIEW=0`
  Ralph can proceed to work tasks even if `rp-cli` is missing or unavailable overnight.

**Recommended (best results, requires rp-cli):**

* `REQUIRE_PLAN_REVIEW=1`
* `PLAN_REVIEW=rp`

This forces Ralph to run `/flow-next:plan-review` until the epic plan is approved before starting tasks.

**Tip:** If you don't have a review backend installed (`rp-cli`, `codex`, or `copilot`), keep `REQUIRE_PLAN_REVIEW=0` or Ralph may repeatedly select the plan gate and make no progress.

Ralph verifies reviews via receipt JSON files in `scripts/ralph/runs/<run>/receipts/` (plan + impl). Receipts are backend-agnostic — RepoPrompt, Codex, and Copilot all write the same shape.

### Ralph loop (one iteration)

```mermaid
flowchart TD
  A[ralph.sh iteration] --> B[flowctl next]
  B -->|status=plan| C[/flow-next:plan-review fn-N/]
  C -->|verdict=SHIP| D[flowctl epic set-plan-review-status=ship]
  C -->|verdict!=SHIP| A

  B -->|status=work| E[/flow-next:work fn-N.M/]
  E --> F[tests + validate]
  F -->|fail| A

  F -->|WORK_REVIEW!=none| R[/flow-next:impl-review/]
  R -->|verdict=SHIP| G[flowctl done + git commit]
  R -->|verdict!=SHIP| A

  F -->|WORK_REVIEW=none| G

  G --> A

  B -->|status=completion_review| CR[/flow-next:epic-review fn-N/]
  CR -->|verdict=SHIP| CRD[flowctl epic set-completion-review-status=ship]
  CR -->|verdict!=SHIP| A
  CRD --> A

  B -->|status=none| H[close done epics]
  H --> I[<promise>COMPLETE</promise>]
```

**YOLO safety**: YOLO mode uses `--dangerously-skip-permissions`. Use a sandbox/container and no secrets in env for unattended runs.

---

## .flow/ Directory

```
.flow/
├── meta.json              # Schema version
├── config.json            # Project settings (memory enabled, etc.)
├── epics/
│   └── fn-1-add-oauth.json      # Epic metadata (id, title, status, deps)
├── specs/
│   └── fn-1-add-oauth.md        # Epic spec (plan, scope, acceptance)
├── tasks/
│   ├── fn-1-add-oauth.1.json    # Task metadata (id, status, priority, deps, assignee)
│   ├── fn-1-add-oauth.1.md      # Task spec (description, acceptance, done summary)
│   └── ...
└── memory/                # Persistent learnings (opt-in, categorized — v0.33.0+)
    ├── bug/               # Track: failures / defects
    │   ├── build-errors/
    │   ├── test-failures/
    │   ├── runtime-errors/
    │   ├── performance/
    │   ├── security/
    │   ├── integration/
    │   ├── data/
    │   └── ui/
    ├── knowledge/         # Track: patterns / decisions / conventions
    │   ├── architecture-patterns/
    │   ├── conventions/
    │   ├── tooling-decisions/
    │   ├── workflow/
    │   └── best-practices/
    └── legacy/            # (optional) archived flat files after migrate
```

Flowctl accepts schema v1 and v2; new fields are optional and defaulted.

New fields:
- Epic JSON: `plan_review_status`, `plan_reviewed_at`, `completion_review_status`, `completion_reviewed_at`, `depends_on_epics`, `branch_name`
- Task JSON: `priority`

### ID Format

- **Epic**: `fn-N-slug` where `slug` is derived from the epic title (e.g., `fn-1-add-oauth`, `fn-2-fix-login-bug`)
- **Task**: `fn-N-slug.M` (e.g., `fn-1-add-oauth.1`, `fn-2-fix-login-bug.2`)

The slug is automatically generated from the epic title (lowercase, hyphens for spaces, max 40 chars). This makes IDs human-readable and self-documenting.

**Backwards compatibility**: Legacy formats `fn-N` (no suffix) and `fn-N-xxx` (random 3-char suffix) are still fully supported. Existing epics don't need migration.

There are no task IDs outside an epic. If you want a single task, create an epic with one task.

### Separation of Concerns

- **JSON files**: Metadata only (IDs, status, dependencies, assignee)
- **Markdown files**: Narrative content (specs, descriptions, summaries)

---

## flowctl CLI

Bundled Python script for managing `.flow/`. Flow-Next's commands handle epic/task creation automatically—use `flowctl` for direct inspection, fixes, or advanced workflows:

```bash
# Setup
flowctl init                              # Create .flow/ structure
flowctl detect                            # Check if .flow/ exists

# Epics
flowctl epic create --title "..."         # Create epic
flowctl epic create --title "..." --branch "fn-1-epic"
flowctl epic set-plan fn-1 --file spec.md # Set epic spec from file
flowctl epic set-plan-review-status fn-1 --status ship
flowctl epic close fn-1                   # Close epic (requires all tasks done)

# Tasks
flowctl task create --epic fn-1 --title "..." --deps fn-1.2,fn-1.3 --priority 10
flowctl task set-description fn-1.1 --file desc.md
flowctl task set-acceptance fn-1.1 --file accept.md

# Dependencies
flowctl dep add fn-1.3 fn-1.2             # fn-1.3 depends on fn-1.2

# Workflow
flowctl ready --epic fn-1                 # Show ready/in_progress/blocked
flowctl next                              # Select next plan/work unit
flowctl start fn-1.1                      # Claim and start task
flowctl done fn-1.1 --summary-file s.md --evidence-json e.json
flowctl block fn-1.2 --reason-file r.md

# Queries
flowctl show fn-1 --json                  # Epic with all tasks
flowctl cat fn-1                          # Print epic spec

# Validation
flowctl validate --epic fn-1              # Validate single epic
flowctl validate --all                    # Validate everything (for CI)

# Review helpers
flowctl rp chat-send --window W --tab T --message-file m.md
flowctl prep-chat --message-file m.md --selected-paths a.ts b.ts -o payload.json

# Prospect (ideation artifacts under .flow/prospects/)
flowctl prospect list                          # active artifacts (<30d)
flowctl prospect list --all --json             # everything
flowctl prospect read <id>                     # full body
flowctl prospect read <id> --section survivors # focus|grounding|survivors|rejected
flowctl prospect promote <id> --idea N         # idea N → new epic
flowctl prospect promote <id> --idea N --force # override idempotency guard
flowctl prospect archive <id>                  # → .flow/prospects/_archive/
```

📖 **[Full CLI reference](docs/flowctl.md)**  
🤖 **[Ralph deep dive](docs/ralph.md)**

---

## Task Completion

When a task completes, `flowctl done` appends structured data to the task spec:

### Done Summary

```markdown
## Done summary

- Added ContactForm component with Zod validation
- Integrated with server action for submission
- All tests passing

Follow-ups:
- Consider rate limiting (out of scope)
```

### Evidence

```markdown
## Evidence

- Commits: a3f21b9
- Tests: bun test
- PRs:
```

This creates a complete audit trail: what was planned, what was done, how it was verified.

---

## Flow vs Flow-Next

| | Flow | Flow-Next |
|:--|:--|:--|
| **Task tracking** | External tracker or standalone plan files | `.flow/` directory (bundled flowctl) |
| **Install** | Plugin + optional external tracker | Plugin only |
| **Artifacts** | Standalone plan files | `.flow/specs/` and `.flow/tasks/` |
| **Config edits** | External config edits (if using tracker) | None |
| **Multi-user** | Via external tracker | Built-in (scan-based IDs, soft claims) |
| **Uninstall** | Remove plugin + external tracker config | Delete `.flow/` (and `scripts/ralph/` if enabled) |

**Choose Flow-Next if you want:**
- Zero external dependencies
- No config file edits
- Clean uninstall (delete `.flow/`, and `scripts/ralph/` if enabled)
- Built-in multi-user safety

**Choose Flow if you:**
- Already use an external tracker for issue tracking
- Want plan files as standalone artifacts
- Need full issue management features

---

## Requirements

- Python 3.8+
- git
- Optional: [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) for macOS GUI reviews + enables **context-scout** (deeper codebase discovery than repo-scout). Reviews work without it via Codex backend.
- Optional: [OpenAI Codex CLI](https://developers.openai.com/codex/cli/) (`npm install -g @openai/codex`) for cross-platform reviews. Also available as a [native Codex plugin](#openai-codex).

Without a review backend, reviews are skipped.

---

## Development

```bash
claude --plugin-dir ./plugins/flow-next
```

---

## Other Platforms

### Factory Droid (Native Support)

Flow-Next works natively in [Factory Droid](https://factory.ai) — no modifications needed.

**Install:**
```bash
# In Droid CLI
/plugin marketplace add https://github.com/gmickel/flow-next
/plugin install flow-next
```

**Cross-platform patterns used:**
- Skills use `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` bash fallback
- Hooks use `Bash|Execute` regex matcher (Claude Code = Bash, Droid = Execute)
- Agents use `disallowedTools` blacklist (not `tools` whitelist — tool names differ between platforms)

**Caveats:**
- Subagents may behave differently (Droid's Task tool implementation)
- Hook timing may vary slightly

> **Rollback:** If you experience issues, downgrade to v0.20.9 (last pre-Droid version): `claude plugins install flow-next@0.20.9`

### OpenAI Codex

Flow-Next is a **native Codex plugin** with near-parity to Claude Code. Pre-built agents, skills, and hooks ship in the `codex/` directory — no runtime conversion needed.

#### Install

```bash
git clone https://github.com/gmickel/flow-next.git
cd flow-next
./scripts/install-codex.sh flow-next
```

The script copies pre-built files from `codex/` to `~/.codex/` (skills, 21 `.toml` agents, hooks, flowctl, prompts, ralph templates) and merges agent + feature entries into `config.toml`. Idempotent — re-run after `git pull` to update. The native `/plugins` install path isn't used because Codex's plugin manifest only declares `skills`, not custom agents or hooks; until that changes, the script is the only way to get the full multi-agent experience.

#### Skill invocation

In Codex, skills appear with display names in the `$` dropdown (e.g. **Flow Setup**, **Flow Plan**). You can invoke them three ways:

1. **Dropdown**: Type `$` → select from the list (e.g. select "Flow Setup")
2. **Direct name**: Type `$flow-next-setup` in your prompt
3. **Implicit**: Just describe the task — Codex matches the skill description automatically (for skills with `allow_implicit_invocation: true`)

| Claude Code | Codex (dropdown) | Codex (direct) |
|-------------|-------------------|----------------|
| `/flow-next:prospect` | Flow Prospect | `$flow-next-prospect` |
| `/flow-next:capture` | Flow Capture | `$flow-next-capture` |
| `/flow-next:plan` | Flow Plan | `$flow-next-plan` |
| `/flow-next:work` | Flow Work | `$flow-next-work` |
| `/flow-next:impl-review` | Flow Implementation Review | `$flow-next-impl-review` |
| `/flow-next:plan-review` | Flow Plan Review | `$flow-next-plan-review` |
| `/flow-next:epic-review` | Flow Epic Review | `$flow-next-epic-review` |
| `/flow-next:interview` | Flow Interview | `$flow-next-interview` |
| `/flow-next:prime` | Flow Prime | `$flow-next-prime` |
| `/flow-next:setup` | Flow Setup | `$flow-next-setup` |

#### What works

- Planning, work execution, interviews, reviews — full workflow
- Multi-agent roles: 20 agents as `.toml` files with subagent optimizations (`sandbox_mode`, `nickname_candidates`)
- Cross-model reviews (Codex as review backend)
- flowctl CLI (`~/.codex/scripts/flowctl`)
- Setup skill (`$flow-next-setup`) — detects Codex platform, copies agents/hooks/flowctl to project
- `openai.yaml` UI metadata for Codex app display (brand color, descriptions)

#### Model mapping (3-tier)

| Tier | Codex Model | Agents | Reasoning |
|------|-------------|--------|-----------|
| Intelligent | `gpt-5.4` | quality-auditor, flow-gap-analyst, context-scout | high |
| Smart scouts | `gpt-5.4` | epic-scout, agents-md-scout, docs-gap-scout | high |
| Fast scouts | `gpt-5.4-mini` | build, env, testing, tooling, observability, security, workflow, memory scouts | default |
| Inherited | parent model | worker, plan-sync | parent |

Smart scouts need deeper reasoning for context building. Fast scouts check file presence and patterns — `gpt-5.4-mini` handles them efficiently.

Override model defaults (global install only):
```bash
CODEX_MODEL_INTELLIGENT=gpt-5.4 \
CODEX_MODEL_FAST=gpt-5.4-mini \
CODEX_REASONING_EFFORT=high \
CODEX_MAX_THREADS=12 \
./scripts/install-codex.sh flow-next
```

#### Hooks (experimental)

Codex now supports hooks. The pre-built `codex/hooks.json` includes Ralph guard hooks for `Bash|Execute` tool calls and `Stop` events.

**Limitation:** Codex hooks only intercept `Bash` (not `Edit`/`Write`). Ralph's file-modification guard won't catch direct file edits. The `SubagentStop` event is also not supported.

#### Per-project setup

Run `$flow-next-setup` (or select **Flow Setup** from the `$` dropdown) in your project. It detects the Codex platform and:
- Initializes `.flow/` directory
- Copies flowctl to `.flow/bin/`
- Copies 20 agent `.toml` configs to `.codex/agents/` (project-scoped)
- Copies `hooks.json` to `.codex/hooks.json` (project-scoped)
- Adds Flow-Next instructions to AGENTS.md
- Configures review backend and recommended defaults

**Manual setup** (alternative):
```bash
# Initialize .flow/ directory
~/.codex/scripts/flowctl init

# Optional: copy flowctl locally
mkdir -p .flow/bin
cp ~/.codex/scripts/flowctl .flow/bin/
cp ~/.codex/scripts/flowctl.py .flow/bin/
chmod +x .flow/bin/flowctl

# Configure review backend
~/.codex/scripts/flowctl config set review.backend codex
```

#### Caveats

- Ralph autonomous mode is limited — hooks intercept Bash only (not Edit/Write), no `SubagentStop` support
- `claude-md-scout` is auto-renamed to `agents-md-scout` (CLAUDE.md → AGENTS.md patching)
- Global install prompts (`/prompts:*`) are global-only (`~/.codex/prompts/`); native plugin avoids this limitation

### Community Ports and Inspired Projects

| Project | Platform | Notes |
|---------|----------|-------|
| [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | OpenCode | Flow-Next port |
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid | Flow port (note: flow-next now has native Droid support) |

---

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [@gmickel](https://twitter.com/gmickel)

</div>
