# Claude Code Project Guide

This repo is a Claude Code plugin marketplace. It ships two plugins: **flow** and **flow-next**. flow-next is the recommended workflow: spec-driven, zero-deps, with a bundled `flowctl` Python CLI, autonomous Ralph mode, and first-class support on Claude Code / OpenAI Codex / Factory Droid.

The repo's strategic intent and canonical vocabulary live at the repo root:

- [`STRATEGY.md`](STRATEGY.md) — target problem, approach, who it's for, key metrics, active tracks
- [`GLOSSARY.md`](GLOSSARY.md) — canonical terms (Spec, Task, R-ID, Handover object, Receipt, Ralph, ...)

Every other detail is in a focused file you should consult when relevant — see "Where to look" below.

## Stack and tooling

- Python 3.8+ (flowctl), Node ecosystem optional (TUI uses `bun`).
- `jq` and `gh` are required for review-subsystem and PR plumbing.
- Package manager: pick one and stay with it per project. `pnpm` for the TUI.
- Pre-commit / lint: `biome` is the source of truth for the TUI; flowctl uses pure-stdlib Python.

## Architecture: agentic vs deterministic (READ BEFORE PLANNING NEW FEATURES)

flow-next is a **skill-driven plugin running inside an agentic coding environment** (Claude Code, Codex, Factory Droid). The host agent IS the intelligence. Default to skill-based architecture; reach for deterministic Python in flowctl only when there's a real reason.

### When to use a SKILL (the default)

A workflow that walks files, makes per-item judgments, investigates code, composes multi-step actions where each depends on prior context, asks the user on ambiguous cases, and could reasonably be invoked via `/flow-next:<command>`.

→ **Build it as a skill.** The host agent reads the skill workflow file, executes via existing Read/Grep/Glob/Edit/Write tools, dispatches subagents via the platform primitive (`Agent`/`Task` in Claude, `spawn_agent` in Codex), asks via `AskUserQuestion`. Canonical files use Claude-native tool names; `sync-codex.sh` rewrites for the Codex mirror.

**Do not spawn `codex`/`copilot`/other LLMs via subprocess from inside flowctl when invoked from a skill.** The host agent is already an LLM running the skill — there is no need for a second one.

### When to use DETERMINISTIC flowctl Python

Mechanical operations needing to work without an agent in the loop: Ralph hooks (PreToolUse / Stop / SubagentStop matchers), receipts (review / walkthrough / ralph_blocked), schema validation, atomic file writes, git plumbing, the triage-skip whitelist, the review-subsystem backend dispatch (`flowctl rp`, `flowctl review-backend`).

→ **Build it in flowctl Python.** Pure plumbing, no intelligence required.

### The common pattern: SKILL + thin flowctl plumbing

Most features look like this. Skill drives the workflow; flowctl provides atomic helpers the skill calls. Examples: `/flow-next:prospect` skill + `flowctl prospect list/read/promote`. `/flow-next:audit` skill + `flowctl memory mark-stale`.

**Split rule:** flowctl owns "set this field" / "validate this schema" / "atomic-write this file" / "list these things." Skill owns "read this and judge" / "compose multi-step decision flow" / "ask user when unsure" / "dispatch subagents."

### How to spot a mistake

Symptoms suggesting deterministic when you should build skill-based:
- Writing regex to extract "code references" from prose → host agent can read prose
- Building a stoplist of common English words → host agent knows English
- Spawning `codex --exec` to make judgments → host agent makes judgments
- Parsing structured-verdict YAML from an LLM response → host agent's own structured output
- Building a deterministic "fallback" engine for when LLM unavailable → host agent is always available
- Weighted scoring math substituting for "is this still relevant?" → host agent answers directly

If three or more apply, stop and convert to a skill. The deterministic path is harder to maintain, more brittle, and produces worse output.

## Cross-platform patterns

flow-next is a first-class citizen on Claude Code, Codex, and Factory Droid. **Architectural rule:** canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites them in the Codex mirror. Skill prose stays concrete; cross-platform maintenance lives in one place — the sync script.

- **Variable references** — bash fallback: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`.
- **Hook matchers** — regex OR: `"matcher": "Bash|Execute"` (Claude `Bash`, Droid `Execute`).
- **Agent permissions** — `disallowedTools` blacklist (not `tools` whitelist). Tool names differ across platforms; blacklist works because both understand `Edit`, `Write`, `Task`.
- **Plugin paths** — check both: `.claude-plugin/plugin.json` falls back to `.factory-plugin/plugin.json`.
- **Blocking-question tool** — every interactive skill MUST use the platform's blocking primitive. Canonical writes `AskUserQuestion`; sync rewrites to `request_user_input` for Codex. Droid (currently) sees the canonical name. Always bare `AskUserQuestion` in canonical files; an optional parenthetical breadcrumb noting the rewrite is fine.
- **Subagent dispatch** — canonical writes `Task` with `subagent_type: Explore`; sync rewrites to `spawn_agent`. Read-only enforcement via `disallowedTools: Edit, Write, Task`.

## Editing rules

- Keep prompts concise and direct.
- Avoid feature flags or backwards-compatibility scaffolding (plugins are pre-1.0 except flow-next 1.0+).
- Do not add extra commands / agents / skills unless explicitly requested.
- For pure docs / agent_docs / README changes, do NOT bump the plugin version.

## Where to look

| For | Look at |
|---|---|
| Plugin command catalog, install paths, feature deep-dives | [`plugins/flow-next/README.md`](plugins/flow-next/README.md) |
| Spec-driven team workflow + handover objects | [`plugins/flow-next/docs/teams.md`](plugins/flow-next/docs/teams.md) |
| Ralph autonomous mode internals | [`plugins/flow-next/docs/ralph.md`](plugins/flow-next/docs/ralph.md) |
| Full `flowctl` CLI reference | [`plugins/flow-next/docs/flowctl.md`](plugins/flow-next/docs/flowctl.md) |
| Adding a new `/flow-next:<name>` skill | [`agent_docs/adding-skills.md`](agent_docs/adding-skills.md) |
| Cutting a release | [`agent_docs/releasing.md`](agent_docs/releasing.md) |
| Local plugin dev + smoke tests + Ralph e2e | [`agent_docs/local-dev.md`](agent_docs/local-dev.md) |
| Repo strategy + active tracks | [`STRATEGY.md`](STRATEGY.md) |
| Canonical vocabulary | [`GLOSSARY.md`](GLOSSARY.md) |
| flow plugin (legacy) | [`plugins/flow/README.md`](plugins/flow/README.md) |
| Repo structure | `.claude-plugin/marketplace.json` (Claude); `.agents/plugins/marketplace.json` (Codex); `plugins/<name>/.claude-plugin/plugin.json`, `plugins/<name>/.codex-plugin/plugin.json`; Codex pre-built mirror at `plugins/flow-next/codex/` (regenerated by `scripts/sync-codex.sh`) |

## Repo metadata

- Author: Gordon Mickel (gordon@mickel.tech)
- Homepage: https://mickel.tech
- Marketplace: https://github.com/gmickel/flow-next

<!-- BEGIN FLOW-NEXT -->
## Flow-Next

This project uses Flow-Next for task tracking. Use `.flow/bin/flowctl` instead of markdown TODOs or TodoWrite.

**Quick commands:**
```bash
.flow/bin/flowctl list                # List all epics + tasks
.flow/bin/flowctl epics               # List all epics
.flow/bin/flowctl tasks --epic fn-N   # List tasks for epic
.flow/bin/flowctl ready --epic fn-N   # What's ready
.flow/bin/flowctl show fn-N.M         # View task
.flow/bin/flowctl start fn-N.M        # Claim task
.flow/bin/flowctl done fn-N.M --summary-file s.md --evidence-json e.json
```

**Creating a spec** ("create a spec", "spec out X", "write a spec for X"):

A spec = an epic. Create one directly — do NOT use `/flow-next:plan` (that breaks specs into tasks).

**Two paths:**
- **Automated** (recommended for any spec emerging from conversation): `/flow-next:capture` — host agent synthesizes the spec from conversation context, source-tags every acceptance criterion (`[user]` / `[paraphrase]` / `[inferred]`), and shows the full draft via mandatory read-back before writing. Output goes to the same `.flow/specs/<epic-id>.md` location, via the same `flowctl epic create + epic set-plan` plumbing — but with conversation context preserved as `## Conversation Evidence` and an audit trail of which criteria came from the user. Added in 0.38.0.
- **Manual** (for direct flowctl scripting): the `flowctl epic create + epic set-plan` heredoc shown below.

```bash
.flow/bin/flowctl epic create --title "Short title" --json
.flow/bin/flowctl epic set-plan <epic-id> --file - --json <<'EOF'
# Title

## Goal & Context
Why this exists, what problem it solves.

## Architecture & Data Models
System design, data flow, key components.

## API Contracts
Endpoints, interfaces, input/output shapes.

## Edge Cases & Constraints
Failure modes, limits, performance requirements.

## Acceptance Criteria
- [ ] Testable criterion 1
- [ ] Testable criterion 2

## Boundaries
What's explicitly out of scope.

## Decision Context
Why this approach over alternatives.
EOF
```

After creating a spec, choose next step:
- `/flow-next:plan <epic-id>` — research + break into tasks
- `/flow-next:interview <epic-id>` — deep Q&A to refine the spec
- `/flow-next:capture --rewrite <epic-id>` — re-synthesize from updated conversation context

**Rules:**
- Use `.flow/bin/flowctl` for ALL task tracking
- Do NOT create markdown TODOs or use TodoWrite
- Re-anchor (re-read spec + status) before every task

**More info:** `.flow/bin/flowctl --help` or read `.flow/usage.md`
<!-- END FLOW-NEXT -->
