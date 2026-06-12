# Claude Code Project Guide

This repo ships the **flow-next** Claude Code plugin — a spec-driven, zero-dependency workflow for AI-assisted SDLC, with a bundled `flowctl` Python CLI, autonomous Ralph mode, and first-class support on Claude Code / OpenAI Codex / Factory Droid. The repo IS flow-next.

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

**Narrow carve-out — `/flow-next:work` Codex delegation (fn-55 decision):** the opt-in `work.delegate` / `delegate:codex` mode is **host-orchestrated implementation-offload, not a judgment hand-off**. The host work skill spawns a local `codex exec` to *write code* for a task while the host retains all judgment (gating, classification, git ownership, review, commit). This is the one sanctioned second-LLM spawn — it is OFF by default, consent-gated, never spawned from inside flowctl, and `codex exec` is forbidden from git/decisions. It does **not** license spawning LLMs for judgment from flowctl. See [`skills/flow-next-work/references/codex-delegation.md`](plugins/flow-next/skills/flow-next-work/references/codex-delegation.md).

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

- **Variable references** — bash fallback: `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`. Droid sets `DROID_PLUGIN_ROOT` and also exposes `CLAUDE_PLUGIN_ROOT` as an alias (per Factory docs, "Alias for `${DROID_PLUGIN_ROOT}` (Claude Code compatibility)"). The fallback order is conservative but correct on both platforms. *(Last verified against Factory docs 2026-05-25 — fn-48.2.)*
- **Hook matchers** — regex OR: `"matcher": "Bash|Execute"` (Claude `Bash`, Droid `Execute` — Factory hooks-reference 2026-05-25 still lists `Execute` as canonical and `Bash` as not recognized).
- **Agent permissions** — `disallowedTools` blacklist (not `tools` whitelist). Tool names differ across platforms; blacklist works because both understand `Edit`, `Write`, `Task`.
- **Plugin paths** — flow-next is a Claude-first plugin; use `${PLUGIN_ROOT}/.claude-plugin/plugin.json` directly. Droid auto-translates Claude Code plugin format on install (Factory docs: "Droid is compatible with plugins built for Claude Code… the plugin format is interoperable"), so a `.factory-plugin/plugin.json` fallback is **not** needed for Claude-first plugins like flow-next. Native Droid-first plugins (e.g. Factory-AI/factory-plugins marketplace) ship `.factory-plugin/plugin.json`; we don't.
- **Blocking-question tool** — every interactive skill MUST use the platform's blocking primitive. Canonical writes `AskUserQuestion`; `sync-codex.sh` transforms canonical invocations into a plain-text numbered-prompt instruction (with `N+1. Other — type your own answer` as the final option) for the Codex mirror — the mirror never mentions `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694; closed without resolution as of Feb 2026). Droid (currently) sees the canonical name. Always bare `AskUserQuestion` in canonical files; an optional parenthetical breadcrumb noting the rewrite is fine.
- **Subagent dispatch** — canonical writes `Task` with `subagent_type: Explore`; sync rewrites to `spawn_agent`. Read-only enforcement via `disallowedTools: Edit, Write, Task`.

## Editing rules

- Keep prompts concise and direct.
- Avoid feature flags or backwards-compatibility scaffolding (plugins are pre-1.0 except flow-next 1.0+).
- Do not add extra commands / agents / skills unless explicitly requested.
- For pure docs / agent_docs / README changes, do NOT bump the plugin version.

## PR workflow

- **PRs derived from a flow-next spec** → use `/flow-next:make-pr <spec-id>`. It generates a cognitive-aid PR body (R-ID coverage table, critical-changes summary, decision context, "where to look") from the spec export. Never hand-write a body when a spec exists — the skill carries discipline the manual version drifts away from.
- **Chore PRs without a spec** (version bumps, small mechanical fixes, CHANGELOG-only changes, third-party-reported regressions) — write the body manually but match the make-pr structure: short summary + What changed + Verification + Version note (or "no version bump per CLAUDE.md docs-only rule" if applicable). Don't open bare-body PRs.
- **Review feedback on any PR** → `/flow-next:resolve-pr` (auto-detects PR from current branch). Resolves threads via dispatched resolver agents, validates combined state, replies + resolves via GraphQL. Bounded at 2 fix-verify cycles before escalation.
- **No direct `gh pr merge` from skills.** Merge is a human decision; do it explicitly when the PR is ready. Sole confined exception: the opt-in `/flow-next:land` ship loop merges explicitly (`--squash --match-head-commit`, never `--auto`) after its full gate tree passes — that license is bounded to land and extends to no other skill.

## flow-next.dev docs site

- Marketing/docs site lives at `~/work/flow-next.dev` (`https://flow-next.dev`).
- When changing Flow-Next behavior, commands, setup, public vocabulary, README/docs, `teams.md`, `ralph.md`, `flowctl.md`, release notes, or anything user-facing, update `~/work/flow-next.dev` in the same workstream.
- Keep the site comprehensive: landing page copy, Starlight docs pages, navigation, examples, install instructions, and cross-links should match current Flow-Next reality.
- **Navigation has TWO sources — update BOTH.** The visible left rail is rendered by `src/components/DocsRail.astro` from `src/lib/site.ts` `navGroups`; there is also the Starlight `sidebar` in `astro.config.mjs`. A new/removed/renamed page (especially a skill) must be added to **both** or it silently goes missing from the rail (e.g. `/flow-next:qa` was added to `astro.config.mjs` only and never appeared). A new skill needs three edits: a `skills/<name>.mdx` page, **both** navbars, and a changelog entry. See `~/work/flow-next.dev/CLAUDE.md` "Navigation — TWO sources" for the slug-set diff sanity check.
- Update the docs-site changelog/release page too, following the strict per-release format in [`agent_docs/releasing.md`](agent_docs/releasing.md) "Docs-site changelog entry" — version `### X.Y.Z — title` heading + bold one-line summary + `<details>` for verbose releases, newest at the top of `## Latest`, and bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json`. It's a scannable highlights page, NOT a copy of the repo `CHANGELOG.md`. If a changelog page does not exist yet, create one before handoff.
- Run the docs-site gate before handoff: `cd ~/work/flow-next.dev && pnpm build`.
- Commit docs-site changes separately in the `flow-next.dev` repo unless the user asks for a combined handoff.

## Where to look

| For | Look at |
|---|---|
| Plugin overview + install + 5-command quick start | [`README.md`](README.md) (root) — canonical entry point |
| Full doc index (subsystem + workflow references) | [`plugins/flow-next/docs/README.md`](plugins/flow-next/docs/README.md) |
| Spec-driven team workflow + handover objects | [`plugins/flow-next/docs/teams.md`](plugins/flow-next/docs/teams.md) |
| Build-loop conductor (`/flow-next:pilot` — single-tick spec-to-PR pipeline driven by host `/loop` / `/goal`; verdict grammar, strikes, autonomous-mode signal) | [`plugins/flow-next/skills/flow-next-pilot/SKILL.md`](plugins/flow-next/skills/flow-next-pilot/SKILL.md) |
| Ralph autonomous mode internals | [`plugins/flow-next/docs/ralph.md`](plugins/flow-next/docs/ralph.md) |
| Full `flowctl` CLI reference | [`plugins/flow-next/docs/flowctl.md`](plugins/flow-next/docs/flowctl.md) |
| `.flow/` directory layout + spec-first task model | [`plugins/flow-next/docs/architecture.md`](plugins/flow-next/docs/architecture.md) |
| Memory schema (bug/knowledge tracks, audit lifecycle) | [`plugins/flow-next/docs/memory-schema.md`](plugins/flow-next/docs/memory-schema.md) |
| Tracker-sync bridge (projection model, hybrid id, transport ladder; `/flow-next:tracker-sync` ≠ `/flow-next:sync`) | [`plugins/flow-next/docs/tracker-sync.md`](plugins/flow-next/docs/tracker-sync.md) |
| Live-app QA (`/flow-next:qa` — spec-derived scenarios, drives the running app via `flow-next-drive`, P0/P1/P2 findings, `qa_verdict` receipt; forbidden from marking PASS by reading source; opt-in) | [`plugins/flow-next/skills/flow-next-qa/SKILL.md`](plugins/flow-next/skills/flow-next-qa/SKILL.md) |
| HTML artifact mode (opt-in render lenses — `artifacts.html.enabled`, spec/PR artifacts under `.flow/artifacts/`, disclosure reference, Lavish companion, autonomous generate-only discipline) | [`plugins/flow-next/docs/html-artifacts.md`](plugins/flow-next/docs/html-artifacts.md) |
| Cross-platform install matrix (Claude / Codex / Droid / OpenCode) | [`plugins/flow-next/docs/platforms.md`](plugins/flow-next/docs/platforms.md) |
| Codebase feature map (optional) | [`plugins/flow-next/skills/flow-next-map/`](plugins/flow-next/skills/flow-next-map/) — `/flow-next:map` wraps `clawpatch map` |
| Troubleshooting + uninstall | [`plugins/flow-next/docs/troubleshooting.md`](plugins/flow-next/docs/troubleshooting.md) |
| Canonical spec-template scaffold (single source of truth — section list, scope-owner annotations, `## Decision Context` flat-vs-H3 conditional; `.flow/templates/spec.md` is a setup-managed copy) | [`plugins/flow-next/templates/spec.md`](plugins/flow-next/templates/spec.md) |
| Adding a new `/flow-next:<name>` skill | [`agent_docs/adding-skills.md`](agent_docs/adding-skills.md) |
| Cutting a release | [`agent_docs/releasing.md`](agent_docs/releasing.md) |
| Local plugin dev + smoke tests + Ralph e2e | [`agent_docs/local-dev.md`](agent_docs/local-dev.md) |
| Optimizing a skill/agent prompt (token/accuracy, eval-driven) | [`agent_docs/optimizing-skills.md`](agent_docs/optimizing-skills.md) |
| Repo strategy + active tracks | [`STRATEGY.md`](STRATEGY.md) |
| Canonical vocabulary | [`GLOSSARY.md`](GLOSSARY.md) |
| Repo structure | `.claude-plugin/marketplace.json` (Claude); `.agents/plugins/marketplace.json` (Codex); `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`; Codex pre-built mirror at `plugins/flow-next/codex/` (regenerated by `scripts/sync-codex.sh`) |

Optional: `/flow-next:map` wraps [openclaw/clawpatch](https://github.com/openclaw/clawpatch)'s `clawpatch map` command to build a semantic feature index under `.clawpatch/features/*.json`. When present, `repo-scout` and `context-scout` use it to anchor R-IDs and `Investigation targets` to concrete codebase regions. Provider-free by default; install via `pnpm add -g clawpatch` (Node 22+).

> The legacy `flow` plugin was removed in flow-next 1.0.2 (see CHANGELOG). To browse the old code: `git show 0a45aff:plugins/flow/README.md` or `git checkout 0a45aff -- plugins/flow/`. It was never tagged as a release.

## Repo metadata

- Author: Gordon Mickel (gordon@mickel.tech)
- Homepage: https://mickel.tech
- Marketplace: https://github.com/gmickel/flow-next

<!-- BEGIN FLOW-NEXT -->
## Flow-Next

This project uses Flow-Next for task tracking. Use `.flow/bin/flowctl` instead of markdown TODOs or TodoWrite.

**Quick commands:**
```bash
.flow/bin/flowctl list                # List all specs + tasks
.flow/bin/flowctl specs               # List all specs
.flow/bin/flowctl tasks --spec fn-N   # List tasks for spec
.flow/bin/flowctl ready --spec fn-N   # What's ready
.flow/bin/flowctl show fn-N.M         # View task
.flow/bin/flowctl start fn-N.M        # Claim task
.flow/bin/flowctl done fn-N.M --summary-file s.md --evidence-json e.json
```

**Creating a spec** ("create a spec", "spec out X", "write a spec for X"):

Create one directly — do NOT use `/flow-next:plan` (that breaks specs into tasks). The canonical 7-section spec scaffold lives at `.flow/templates/spec.md` (copied here by `/flow-next:setup`) — read it for the section list, scope ownership, and `## Decision Context` H3 conditional. To customize the scaffold for this project, copy `.flow/templates/spec.md` to `<repo-root>/SPEC.md` and edit there — the discovery cascade prefers it (first match wins): `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled plugin template.

```bash
.flow/bin/flowctl spec create --title "Short title" --json
.flow/bin/flowctl spec set-plan <spec-id> --file - --json <<'EOF'
# Title

# ... fill the 7 canonical sections (see SPEC.md / .flow/templates/spec.md)
EOF
```

After creating a spec, choose next step:
- `/flow-next:plan <spec-id>` — research + break into tasks
- `/flow-next:interview <spec-id>` — deep Q&A to refine the spec

**Rules:**
- Use `.flow/bin/flowctl` for ALL task tracking
- Do NOT create markdown TODOs or use TodoWrite
- Re-anchor (re-read spec + status) before every task

**Optional — codebase feature map:** `/flow-next:map` wraps [openclaw/clawpatch](https://github.com/openclaw/clawpatch)'s `clawpatch map` command to build a semantic feature index under `.clawpatch/features/*.json`. When present, `repo-scout` and `context-scout` use it to anchor R-IDs and `Investigation targets` to concrete codebase regions. Provider-free by default; install via `pnpm add -g clawpatch` (Node 22+).

**More info:** `.flow/bin/flowctl --help` or read `.flow/usage.md`
<!-- END FLOW-NEXT -->
