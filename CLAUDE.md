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

flow-next is a **skill-driven plugin running inside an agentic coding environment** (host platforms: Claude Code, Codex, Factory Droid, Cursor - see the roster below). The host agent IS the intelligence. Default to skill-based architecture; reach for deterministic Python in flowctl only when there's a real reason.

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

**Sanctioned carve-out (subprocess LLM judgment):** do not "fix" these licensed cases when the symptom list matches. Review-backend dispatch, the triage-skip judge, and fn-55 delegation classify may spawn a subprocess LLM for judgment. Rationale: cross-model verdicts about pipeline-written code must not be self-issued by the host.

## Cross-platform patterns

**HOST PLATFORM ROSTER (memorize - do not forget any of these when building features):**

| Host | Mechanism | Consumes |
|---|---|---|
| Claude Code | canonical plugin (`.claude-plugin/`) | canonical files as-is |
| Codex | pre-built mirror at `plugins/flow-next/codex/`, regenerated by `scripts/sync-codex.sh` | REWRITTEN copies (tool names, ask fallback, dispatch phrases) |
| Factory Droid | auto-translates the Claude plugin format on install | canonical files as-is (`DROID_PLUGIN_ROOT` alias) |
| Cursor | `.cursor-plugin/plugin.json` + `scripts/install-cursor.sh` / `.ps1` (blanket rsync copy to `~/.cursor/plugins/local/`, excludes codex/ + tests/) | canonical files AS-IS - no rewrite pass exists |
| Grok Build | reads the Claude plugin format directly (compat, verified) | canonical files as-is |
| OpenCode | community port | out-of-repo |

**Architectural rule:** canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites them in the Codex mirror. Skill prose stays concrete; cross-platform maintenance lives in one place — the sync script. Cursor/Droid/Grok get NO rewrite pass, so anything Claude-specific in canonical prose must either work there or carry an explicit portable-host clause.

**Checklist when adding/editing skills, agents, or hooks (walk ALL of it):**

1. Run `./scripts/sync-codex.sh` TWICE (idempotency) and commit the mirror diff with the canonical change. Its validation guards must stay green; new Claude-only phrases (tool dispatches, model-name examples) may need a new transform + hard-fail guard (pattern: the fn-100 Explore-dispatch and scout-tier rules).
2. Claude BUILTIN references (`Explore`, `general-purpose`, `AskUserQuestion`, model names) are invisible to the Cursor/Droid consumers - every such reference needs a portable-host fallback clause in the canonical prose (generic read-only dispatch with Edit/Write disallowed; plain-text numbered-prompt fallback for asks) or graceful degradation stated inline.
3. Plugin-root env vars: Cursor exposes NONE - every bash preamble must keep the `.flow/bin/flowctl` fallback after the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` probe.
4. No plugin-level hooks (`plugins/flow-next/hooks/` is gone): Ralph registration is agent-driven via `/flow-next:ralph-init` (merge fingerprinted entries into project settings per host). Guard matchers stay Claude-schema (`PreToolUse`/`Stop`, `Bash|Execute` shell + file-tool set); works on Claude Code + Droid, NOT Cursor (different hook events) - never assume the guard fires there.
5. Installers need no enumeration updates (Cursor installers blanket-copy; the codex mirror is a full regen) - but `plugins/flow-next/docs/platforms.md` DOES need a note when host behavior differs.
6. `agents/*.md` model fields are family aliases resolved by the host; on non-Claude hosts they map to host defaults - never version-pin, and never assume a specific tier is honored off Claude Code.

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
- **Version bumps are batched, not per-spec.** When implementing a spec, land the code + docs + an `## Unreleased` CHANGELOG entry (repo + docs-site), but do NOT run `scripts/bump.sh` or touch the version manifests / `FLOW_NEXT_VERSION`. The release + version-number decision is made separately, later, across several accumulated specs — to avoid version churn. Spec/task acceptance that says "bump to X.Y.Z" means *stage under `## Unreleased`*; the actual bump happens at the batched release.

## PR workflow

- **PRs derived from a flow-next spec** → use `/flow-next:make-pr <spec-id>`. It generates a cognitive-aid PR body (R-ID coverage table, critical-changes summary, decision context, "where to look") from the spec export. Never hand-write a body when a spec exists — the skill carries discipline the manual version drifts away from.
- **Chore PRs without a spec** (version bumps, small mechanical fixes, CHANGELOG-only changes, third-party-reported regressions) — write the body manually but match the make-pr structure: short summary + What changed + Verification + Version note (or "no version bump per CLAUDE.md docs-only rule" if applicable). Don't open bare-body PRs.
- **Review feedback on any PR** → `/flow-next:resolve-pr` (auto-detects PR from current branch). Resolves threads via dispatched resolver agents, validates combined state, replies + resolves via GraphQL. Bounded at 2 fix-verify cycles before escalation.
- **No direct `gh pr merge` from skills.** Merge is a human decision; do it explicitly when the PR is ready. Sole confined exception: the opt-in `/flow-next:land` ship loop merges explicitly (`--squash --match-head-commit`, never `--auto`) after its full gate tree passes — that license is bounded to land and extends to no other skill.

## Docs site

- A public docs site exists at **`https://flow-next.dev`** (source repo `~/work/flow-next.dev`). User-facing changes — behavior, commands, setup, public vocabulary, README, release notes — should be reflected there in the same workstream. **The detailed update/release workflow for the docs site, and the maintainer's other downstream/narrative properties, live in the maintainer's *private* config — not this committed file** (they reference maintainer-local repos/paths that other contributors don't have).

## Where to look

| For | Look at |
|---|---|
| Plugin overview + install + 5-command quick start | [`README.md`](README.md) (root) — canonical entry point |
| Full doc index (subsystem + workflow references) | [`plugins/flow-next/docs/README.md`](plugins/flow-next/docs/README.md) |
| Spec-driven team workflow + handover objects | [`plugins/flow-next/docs/teams.md`](plugins/flow-next/docs/teams.md) |
| Build-loop conductor (`/flow-next:pilot` — single-tick spec-to-PR pipeline driven by host `/loop` / `/goal`; verdict grammar, strikes, autonomous-mode signal) | [`plugins/flow-next/skills/flow-next-pilot/SKILL.md`](plugins/flow-next/skills/flow-next-pilot/SKILL.md) |
| Ralph autonomous mode internals | [`plugins/flow-next/docs/ralph.md`](plugins/flow-next/docs/ralph.md) |
| Orchestration & model routing (steering tiers, review-backend precedence, `delegate:codex`, CLAUDE.md model tables, pilot+land chaining) | [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md) |
| Full `flowctl` CLI reference | [`plugins/flow-next/docs/flowctl.md`](plugins/flow-next/docs/flowctl.md) |
| `.flow/` directory layout + spec-first task model | [`plugins/flow-next/docs/architecture.md`](plugins/flow-next/docs/architecture.md) |
| Memory schema (bug/knowledge tracks, audit lifecycle) | [`plugins/flow-next/docs/memory-schema.md`](plugins/flow-next/docs/memory-schema.md) |
| Tracker-sync bridge (projection model, hybrid id, transport ladder; `/flow-next:tracker-sync` ≠ `/flow-next:sync`) | [`plugins/flow-next/docs/tracker-sync.md`](plugins/flow-next/docs/tracker-sync.md) |
| Live-app QA (`/flow-next:qa` — spec-derived scenarios, drives the running app via `flow-next-drive`, P0/P1/P2 findings, `qa_verdict` receipt; forbidden from marking PASS by reading source; opt-in) | [`plugins/flow-next/skills/flow-next-qa/SKILL.md`](plugins/flow-next/skills/flow-next-qa/SKILL.md) |
| Opinionated agent-readiness assessment (`/flow-next:prime` - project classification, operability ladder + hard gates, per-stack matrix, substance-over-existence, verdict + ranked next-actions; deterministic `flowctl prime classify` emitter; `--classify-only` portfolio triage) | [`plugins/flow-next/skills/flow-next-prime/SKILL.md`](plugins/flow-next/skills/flow-next-prime/SKILL.md) |
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

This project uses Flow-Next. Use `.flow/bin/flowctl` for ALL task tracking. Do NOT create markdown TODOs or use TodoWrite. Re-anchor (re-read spec + task status) before every task.

```bash
.flow/bin/flowctl list                # specs + tasks
.flow/bin/flowctl show fn-N.M         # view task
.flow/bin/flowctl start fn-N.M        # claim -> implement -> commit
.flow/bin/flowctl done fn-N.M --summary-file s.md --evidence-json e.json
# e.json: {"commits": ["<sha>"], "tests": ["<command>"], "prs": []}
```

**Creating a spec:** write it directly - do NOT use `/flow-next:plan` (task breakdown only). Scaffold cascade (first match wins): `SPEC.md` -> `spec.md` -> `.flow/templates/spec.md` -> bundled template.

```bash
.flow/bin/flowctl spec create --title "Short title" --json
.flow/bin/flowctl spec set-plan <spec-id> --file plan.md
```

Then `/flow-next:plan <spec-id>`.

**Spec Quick commands (this repo):** list FOCUSED suites for the feature's files (e.g. `cd plugins/flow-next/tests && python3 -m unittest test_config_snapshot test_task_create_files -q`). That is what workers baseline and verify per task. The FULL suite runs ONCE at the final gate (work Phase 4 / completion review): `python3 scripts/run_tests_parallel.py` (serial fallback `--serial`). Do not put the full discover/parallel command on every task's Quick commands.

**More:** `.flow/bin/flowctl --help` or `.flow/usage.md`
<!-- END FLOW-NEXT -->

<!-- flow-next:model-routing:start -->
## Picking models for flow-next workflows and subagents

_Scaffolded by `/flow-next:setup` — edit freely; re-run setup to regenerate. These scores are starting opinions (as of Jul 2026): re-rank them to what you actually pay for and prefer. This section is yours now._

Rankings, higher = better. **cost** = how lightly it rides your subscription quota (higher = run it freely; lower = it burns the plan's budget fast, so spend it sparingly), NOT list $/token, and each provider is a separate budget; **speed** = output speed at *default* reasoning effort (raising effort trades speed for intelligence); **intelligence** = how hard a problem you can hand it unsupervised; **taste** = UI/UX, code quality, API design, copy.

| model         | cost | speed | intelligence | taste |
|---------------|------|-------|--------------|-------|
| fable-5       | 2    | 2     | 10           | 9     |
| opus-4.8      | 4    | 3     | 7            | 8     |
| gpt-5.6-sol   | 8    | 5     | 9            | 6     |
| gpt-5.6-terra | 9    | 7     | 7            | 5     |
| grok-4.5      | 9    | 9     | 7            | 5     |
| composer-2.5  | 9    | 10    | 6            | 6     |
| sonnet-5      | 5    | 6     | 7            | 7     |
| haiku-4.5     | 8    | 9     | 4            | 4     |

How to apply — defaults, not limits. Unless prompted otherwise, route work across these models as you judge best — no permission needed; an explicit user instruction always overrides this table. Standing permission to escalate: if a cheaper model misses the bar, rerun on a smarter one without asking. Judge the output, not the price tag.
- For anything that ships, intelligence > taste > cost; cost is a tie-breaker only.
- Orchestration, planning, review verdicts, anything ambiguous → the session model (whichever row you are running as the conductor). Never delegate judgment.
- Anything user-facing (UI, copy, API design) needs taste ≥ 7 → keep on the session model even if it looks mechanical.
- Reviews prefer a different family than the writer — uncorrelated blind spots.
- Graceful degrade: a routed CLI that is missing, unauthenticated, or errors → report it unavailable and fall back to the session model. Never block.

Recommended default pipeline (swap any row to taste): the SESSION model authors specs — capture, interview, plan; that is where plan quality is made — then gpt-5.6-terra @ medium implements via the implementation routes below (packaged delegation on Claude Code; the same-family self-bridge on a Codex host until MAv2 role pins are reliable), then reviews go to the strongest reviewer from a DIFFERENT family than the writer (single-subscription fallback: the strongest same-family model that did not write the diff). On Claude Code this resolves to fable-5 → terra → sol; on a Codex host to sol → terra → a Claude-family reviewer when installed, else sol.

flow-next wiring — roles with a MENU, not fixed pairings: pick per task. Claude tiers run natively (spawn subagents with the model parameter); other families ride the headless bridges — recipes in `.flow/usage.md` § Orchestration & model steering. Probe-marked lines are live only if their CLI is installed:
- Implementation, native: a worker/subagent on opus-4.8 (quality) or sonnet-5 (speed) via the model parameter.
Implementation via gpt-5.6-terra @ medium (the packaged delegate default): `/flow-next:work <id> delegate:codex` (consent-gated, host keeps git/review) or a direct `codex exec` bridge. Eval-matched gpt-5.6-sol correctness at ~2/3 wall-clock on strong specs; escalate work.delegateModel to gpt-5.6-sol for gnarly tasks.
Implementation via composer-2.5: the `cursor-agent` bridge (`--force` to apply); host reviews + commits.
Implementation via grok-4.5: a fast, cheap first-draft worker via the `grok -p` one-shot bridge; host reviews + commits on a taste-heavier tier. Route it to bulk/implementation, NOT UI or final taste-critical work (higher hallucination, weaker on UI). (Or reach grok-4.5 through the cursor review line below.)
Review, cross-family (recommended default when the writer is Claude-family; on a GPT-writer host pick a non-GPT reviewer instead): `review.backend codex`; per-task `review:` pins exceptions; escalate reviewer↔worker disagreements to the session model.
Review, cross-family via cursor (multi-family reach): `review.backend cursor:claude-opus-4-8-thinking-high` (Claude-family; `cursor:claude-fable-5-thinking-high` for the frontier gate — NO ZDR) or `cursor:gpt-5.6-sol-high` (GPT-family) — pick the family that did NOT write the diff. Ids are volatile → `cursor-agent --list-models`. Composer/grok tiers are quick extra voices, never the gate.
- Review, same-family heavy: a fresh-context reviewer subagent on opus-4.8 (or the session model) with the review criteria — no registry rung needed; describe the arrangement.
Bulk, low-judgment reads (codebase sweeps): scouts may shell out to `cursor-agent`; only the digest returns.
- Bulk reads, native: haiku-4.5 / sonnet-5 subagents for scans and digests.
- Autonomous loops: never call a bridge CLI raw - wrap it in a thin fast-tier subagent that runs the bridge in the FOREGROUND and self-heals environment failures only (bridges fail silently outside trusted git dirs), never judgment; recipes in `.flow/usage.md` § Orchestration & model steering.
Reach gpt-5.6-terra inside a subagent (thin-wrapper) for cheap bulk reads/digests only — not implementation: a cheap wrapper writes a self-contained prompt, runs `codex exec` over Bash, returns the digest.
<!-- flow-next:model-routing:end -->
