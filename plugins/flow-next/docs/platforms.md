# Other Platforms

Flow-next is a first-class citizen on Claude Code (canonical), OpenAI Codex (pre-built mirror), and Factory Droid (native cross-platform patterns). A community port exists for OpenCode. xAI **Grok Build** reads the canonical Claude plugin format AS-IS (skills, agents, commands, MCP, instruction files). Skills load, `/flow-next:*` slash commands run when typed, and **multi-agent flows work** (a full `/flow-next:plan` fanned out all seven scouts, verified). Setup detects Grok via **`GROK_AGENT=1`** (not Codex fallback / `$flow-next-` syntax). Copy mode + `.flow/bin/flowctl`; Ralph intentionally not built for Grok. See [Grok Build](#grok-build-claude-code-compatibility) below. **Cursor** is first-class too: **recommended install is team-marketplace repo import** (admin imports the GitHub repo via the Cursor GitHub App; Default Off / On / Required modes; auto-refresh on push); local `install-cursor.sh` / `.ps1` remain the individual/fallback path. Skills, commands, multi-agent flows, native asks, and slash autocomplete verified; Ralph intentionally not built for Cursor. See [Cursor](#cursor) below.

### Ralph hooks: per-host registration (no plugin-default)

The plugin **does not** ship `hooks/hooks.json`. Fresh install = zero guard process. Registration is **agent-driven** by `/flow-next:ralph-init` (and setup's Ralph yes path), which merges entries into project settings. Host differences:

| Host | Where hooks land | Notes |
|------|------------------|-------|
| Claude Code | `.claude/settings.json` `hooks` key | Project-hooks trust prompt = consent gate |
| Factory Droid | `.factory/hooks.json` (primary) | Fallback: `hooks` in `.factory/settings.json` if already used |
| Codex | `.codex/hooks.json` (project) | Shell + Stop only; no plugin auto-hooks |
| Cursor | *(none)* | Cursor has a full agent-hook set; flow-next intentionally does not build/register Ralph on Cursor |
| Grok Build | *(none)* | flow-next intentionally does not build/register Ralph on Grok (same posture as Cursor; not a schema gap) |

## Install matrix

| Platform | Install command | Plugin file | Notes |
|----------|-----------------|-------------|-------|
| Claude Code | `/plugin marketplace add https://github.com/gmickel/flow-next && /plugin install flow-next` | `.claude-plugin/plugin.json` | Canonical environment |
| Factory Droid | `droid plugin marketplace add https://github.com/gmickel/flow-next && droid plugin install flow-next` (in Droid CLI) | `.claude-plugin/plugin.json` (Droid auto-translates Claude Code plugin format) | Native cross-platform patterns |
| OpenAI Codex | `git clone https://github.com/gmickel/flow-next.git && cd flow-next && ./scripts/install-codex.sh` | `.codex-plugin/plugin.json` | Pre-built mirror under `plugins/flow-next/codex/` |
| Grok Build (xAI) | Auto-discovered if installed in Claude Code (run `grok inspect`); or add `gmickel/flow-next` as a `[[marketplace.sources]]` entry. **Not** `grok plugin install <repo>`. | `.claude-plugin/plugin.json` (canonical Claude files AS-IS; no Codex mirror) | **Detected via `GROK_AGENT=1`.** Namespaced slash commands (`/flow-next:*`), copy mode, multi-agent verified. Ralph intentionally not built. See [Grok Build](#grok-build-claude-code-compatibility) |
| Cursor | **Recommended:** team-marketplace repo import (admin imports `gmickel/flow-next` via Cursor GitHub App). **Fallback:** `./scripts/install-cursor.sh` / `install-cursor.ps1` → `~/.cursor/plugins/local/` | `.cursor-plugin/plugin.json` (Cursor's own namespace — does NOT read `.claude-plugin/`) | **First-class** (multi-agent, native asks, autocomplete verified). Ralph intentionally not built for Cursor — see [Cursor](#cursor) |
| OpenCode | See [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | n/a | Community port |

> The canonical install path on Claude Code is the marketplace. Direct `--plugin-dir` (`claude --plugin-dir ./plugins/flow-next`) is the development path.

## Setup modes: plugin vs copy (fn-121)

`/flow-next:setup` on **Claude Code** asks one mode question per repo; every other host is always copy mode.

| | **Plugin mode** (Claude Code only) | **Copy mode** (all hosts) |
|---|---|---|
| What lands in the repo | A slim versioned CLAUDE.md snippet — nothing else | `.flow/bin/flowctl*`, `.flow/templates/spec.md`, `.flow/usage.md` snapshots + full snippet |
| How agents reach flowctl | Bare `flowctl` — Claude Code injects the plugin's `bin/` onto the Bash PATH | `.flow/bin/flowctl` (works with no plugin installed at all) |
| The agent guide | Pulled live via `flowctl usage` (always current) | `.flow/usage.md` on disk |
| Plugin updates | Land silently — **no setup re-run, ever** | Re-run `/flow-next:setup` per repo to refresh the snapshots |
| Who should pick it | Claude-Code-only repos | Repos with Codex/Cursor/Droid teammates, CI, or plain-terminal flowctl use |

Why other hosts can't have plugin mode: Cursor exposes no plugin-root env vars and no bin PATH injection; Codex resolves flowctl from `$HOME/.codex/scripts/`; Droid's bin injection is unverified. A plugin-mode repo remains **workable from Codex and Droid** (Codex skills self-resolve flowctl from `$HOME/.codex/scripts/`; Droid reads the plugin-root envs) — but **NOT from Cursor**, whose skill preambles need `.flow/bin`; a Cursor visitor is offered a consented convert-to-copy. If teammates on other hosts are the norm, choose copy mode. Switching modes later is a consented `/flow-next:setup` re-run; the mode stamp (`setup_mode` in `.flow/meta.json`) is written only by `flowctl setup-mode set`, which refuses a plugin stamp unless the CLAUDE.md rail is present and no copy snapshots remain. Contributor-facing internals: [`agent_docs/setup-modes.md`](../../../agent_docs/setup-modes.md).

**Team / org-wide deployment (Claude Code).** To install flow-next across a whole team without each developer running the commands, deploy it through Claude Code settings rather than per-user: a `managed-settings.json` for org-wide rollout (admin/IT, via MDM/GPO — `extraKnownMarketplaces` registers the marketplace, `enabledPlugins` force-enables `flow-next@flow-next`, not user-overridable), or a committed `.claude/settings.json` for a prompt-on-trust install scoped to one repo. A one-time trust prompt still appears by design, and each repo still needs `/flow-next:setup` to wire the local `.flow/` state. Full JSON + OS paths: [flow-next.dev/install → Team / org-wide deployment](https://flow-next.dev/install/#team--org-wide-deployment-claude-code-managed-settings).

## Factory Droid (native support)

Flow-next works natively in [Factory Droid](https://factory.ai) — no modifications needed. flow-next is a **Claude-first plugin**; Droid's documented plugin interop layer translates the format on install.

**Install:**
```bash
# In Droid CLI
droid plugin marketplace add https://github.com/gmickel/flow-next
droid plugin install flow-next
```

**How interop works** (verified against [Factory docs](https://docs.factory.ai/cli/configuration/plugins) on 2026-05-25):

- **Plugin manifest** — Factory documents: "Droid is compatible with plugins built for Claude Code. If you find a Claude Code plugin you'd like to use, you can install it directly - the plugin format is interoperable." flow-next ships only `.claude-plugin/plugin.json`; Droid reads it directly. The repo deliberately does **not** include a `.factory-plugin/plugin.json` — it would be redundant.
- **Plugin-root env var** — Droid sets `DROID_PLUGIN_ROOT` (canonical) and exposes `CLAUDE_PLUGIN_ROOT` as an alias (per [Factory hooks-reference](https://docs.factory.ai/reference/hooks-reference): *"`${CLAUDE_PLUGIN_ROOT}` — Alias for `${DROID_PLUGIN_ROOT}` (Claude Code compatibility)"*). flow-next skill bash blocks use the fallback chain `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` — conservative ordering, correct on both platforms.
- **Hook tool name** — Droid's shell-command tool is named **`Execute`** (not `Bash`); per Factory docs, `Bash` is not a recognized matcher in Droid. When Ralph is opt-in-installed, matchers use `"Bash|Execute"` (regex OR) so a single entry fires on both Claude (`Bash`) and Droid (`Execute`).
- **Agent permissions** — flow-next uses `disallowedTools` blacklists instead of `tools` whitelists, because tool names diverge (Claude `Bash` vs Droid `Execute`, etc.) but both platforms understand the common deny-list set (`Edit`, `Write`, `Task`).
- **Ralph hooks are not plugin-default** — the plugin ships no `hooks/hooks.json`. `/flow-next:ralph-init` (agent prose) merges guard entries into the project file **`.factory/hooks.json`** (Factory's project hooks path; fallback: `hooks` key in `.factory/settings.json` if that is already the project's hooks surface).

**Caveats:**
- Subagents may behave differently (Droid's Task tool implementation).
- Hook timing may vary slightly.
- Plugins relying on Droid-specific lifecycle hooks (`SessionStart`, `SessionEnd`) and Droid-only env vars are not portable back to Claude Code — flow-next deliberately stays within the shared subset.

> **Rollback:** If you experience issues, downgrade to v0.20.9 (last pre-Droid version): `claude plugins install flow-next@0.20.9`.

> **Status (last verified 2026-05-25, fn-48.2):** Droid remains divergent on env-var canonical name (`DROID_PLUGIN_ROOT`) and tool name (`Execute`), but Factory's interop layer handles `.claude-plugin/plugin.json` and `CLAUDE_PLUGIN_ROOT` automatically. flow-next preserves the `Bash|Execute` matcher and `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback; the historic `.factory-plugin/plugin.json` fallback was redundant and is being cleaned up in fn-48.6.

## OpenAI Codex

Flow-next is a **native Codex plugin** with near-parity to Claude Code. Pre-built agents, skills, and hooks ship in the `codex/` directory — no runtime conversion needed.

### Install

```bash
git clone https://github.com/gmickel/flow-next.git
cd flow-next
./scripts/install-codex.sh flow-next
```

The script copies pre-built files from `codex/` to `~/.codex/` (skills, 22 `.toml` agents, hooks, flowctl, prompts, ralph templates) and merges agent + feature entries into `config.toml`. Idempotent — re-run after `git pull` to update. The native `/plugins` install path isn't used because Codex's plugin manifest only declares `skills`, not custom agents or hooks; until that changes, the script is the only way to get the full multi-agent experience.

### Skill invocation

In Codex, skills appear with display names in the `$` dropdown (e.g. **Flow Setup**, **Flow Plan**). Three invocation forms:

1. **Dropdown**: Type `$` → select from the list (e.g. select "Flow Setup")
2. **Direct name**: Type `$flow-next-setup` in your prompt
3. **Implicit**: Just describe the task — Codex matches the skill description automatically (for skills with `allow_implicit_invocation: true`)

All user-facing skills ship `allow_implicit_invocation: true`, so prose like "plan this feature", "pilot fn-12 to completion", or "open a PR" resolves the matching skill from the model's skill catalog — Codex's naming rule then *requires* it to use that skill. Internal skills that only other skills dispatch (`drive`, `sync`, `export-context`, `rp-explorer`, `worktree-kit`, `deps`) ship `false`: they stay out of the shared skill-catalog context budget (min of 8,000 chars and 2% of the context window, shared with every other skill on your machine) but remain fully invocable by name. The mirror's catalog descriptions are dieted to ≤200 chars each for the same reason — the full skill body loads on invocation either way.

| Claude Code | Codex (dropdown) | Codex (direct) |
|-------------|-------------------|----------------|
| `/flow-next:prospect` | Flow Prospect | `$flow-next-prospect` |
| `/flow-next:capture` | Flow Capture | `$flow-next-capture` |
| `/flow-next:plan` | Flow Plan | `$flow-next-plan` |
| `/flow-next:work` | Flow Work | `$flow-next-work` |
| `/flow-next:impl-review` | Flow Implementation Review | `$flow-next-impl-review` |
| `/flow-next:plan-review` | Flow Plan Review | `$flow-next-plan-review` |
| `/flow-next:spec-completion-review` | Flow Spec Completion Review | `$flow-next-spec-completion-review` |
| `/flow-next:make-pr` | Flow Make PR | `$flow-next-make-pr` |
| `/flow-next:interview` | Flow Interview | `$flow-next-interview` |
| `/flow-next:prime` | Flow Prime | `$flow-next-prime` |
| `/flow-next:setup` | Flow Setup | `$flow-next-setup` |

### What works

- Planning, work execution, interviews, reviews — full workflow.
- Multi-agent roles: 22 agents as `.toml` files with subagent optimizations (`sandbox_mode`, `nickname_candidates`).
- Cross-model reviews (Codex as review backend).
- flowctl CLI (`~/.codex/scripts/flowctl`).
- Setup skill (`$flow-next-setup`) — detects Codex platform, copies agents/flowctl to project; Ralph hooks only if the Ralph ceremony answers yes.
- `openai.yaml` UI metadata for Codex app display (brand color, descriptions).
- Tracker-sync background dispatch at **Tier B (isolated-but-awaited)**: comment-shaped tracker touchpoints on linked specs run in a `tracker_runner` agent (context isolation preserved) but are **awaited** — the fire-and-forget overlap is Claude-Code-only (Tier A). Same for Cursor. See `docs/tracker-sync.md` § Background dispatch + `references/tracker-dispatch.md` (host capability ladder).

### Model mapping (per-agent reasoning tier)

| Tier | Codex Model | Reasoning | Agents |
|------|-------------|-----------|--------|
| Review-shaped | `gpt-5.5` | `high` | quality-auditor |
| Scout / editorial | `gpt-5.5` | `medium` | flow-gap-analyst, context-scout, docs-scout, github-scout, practice-scout, repo-scout, plan-sync, spec-scout, agents-md-scout, docs-gap-scout |
| Fast scouts | `gpt-5.4-mini` | n/a | build, env, testing, tooling, observability, security, workflow, memory scouts |
| Worker (default) | *inherit (session model)* | *session default* | worker |
| Inherited | parent model | parent | pr-comment-resolver |

`quality-auditor` is review-shaped (a second pair of eyes on uncommitted changes) and stays at `high` — undershooting risks missed regressions. Other intelligent agents do scout/editorial work and run efficiently at `medium`. The worker defaults to `inherit` on BOTH platforms - your session model rules, and flow-next never hardcodes a model opinion into generated config. An OPT-IN pin is available at sync time (`CODEX_MODEL_WORKER` / `CODEX_REASONING_EFFORT_WORKER`); the eval-motivated recommendation is `gpt-5.6-terra` @ `medium`. Note (Jul 2026): on Sol/Multi-Agent-V2 builds role-profile model application is currently unreliable (openai/codex#33268, #33314) - prefer the `codex exec -m` self-bridge to steer models from a Codex host until those are fixed (fn-97, 2026-07 controlled pipeline eval at n=3: terra-medium matched `gpt-5.6-sol` correctness at ~2/3 wall-clock on frontier-authored specs). The actual review backend (`flowctl <backend> impl-review` / `plan-review` / `completion-review`) is configured separately in `flowctl.py` and defaults on its own to the backend's ranking-top model at `high` effort (current ids in [`flowctl.md`](flowctl.md)).

Override model defaults: the `CODEX_MODEL_*` / `CODEX_REASONING_EFFORT_*` env vars are read by **`sync-codex.sh`** (which generates the agent `.toml` files) — `install-codex.sh` only copies the pre-built mirror, so regenerate first, then install:

```bash
CODEX_MODEL_INTELLIGENT=gpt-5.5 \
CODEX_MODEL_FAST=gpt-5.4-mini \
CODEX_MODEL_WORKER=gpt-5.6-terra \
CODEX_REASONING_EFFORT=medium \
CODEX_REASONING_EFFORT_AUDITOR=high \
CODEX_REASONING_EFFORT_WORKER=medium \
./scripts/sync-codex.sh
CODEX_MAX_THREADS=12 ./scripts/install-codex.sh flow-next   # CODEX_MAX_THREADS is the installer's own knob
```

### Hooks (experimental, Ralph opt-in only)

Codex supports hooks, but flow-next installs **none** by default: the Codex mirror ships no `hooks.json`, and `install-codex.sh` does not copy one (fn-114 zero-default). Project hooks land only when Ralph is enabled via `$flow-next-ralph-init` (or setup's Ralph yes path), which writes/merges project `.codex/hooks.json` with the Codex subset (`PreToolUse`/`PostToolUse` shell + `Stop`; no `SubagentStop`, no `Edit`/`Write` matchers).

`install-codex.sh` still sets `[features] hooks = true` in `~/.codex/config.toml` (feature flag only, not a Ralph install). That flag enables Codex's hooks runtime so a later ralph-init project hooks file can load; it does **not** install any guard entries by itself.

**Limitation:** Codex hooks only intercept `Bash` (not `Edit`/`Write`). Ralph's file-modification guard won't catch direct file edits. The `SubagentStop` event is also not supported.

### Per-project setup

Run `$flow-next-setup` (or select **Flow Setup** from the `$` dropdown) in your project. It detects the Codex platform and:
- Initializes `.flow/` directory
- Copies flowctl to `.flow/bin/`
- Copies 22 agent `.toml` configs to `.codex/agents/` (project-scoped)
- Asks whether to enable Ralph (default **No**). Yes → ralph-init (scaffold + `.codex/hooks.json`). No → strips any fingerprinted Ralph guard entries if present
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

### Caveats

- Ralph autonomous mode is limited — hooks intercept Bash only (not Edit/Write), no `SubagentStop` support.
- `claude-md-scout` is auto-renamed to `agents-md-scout` (CLAUDE.md → AGENTS.md patching).
- Global install prompts (`/prompts:*`) are global-only (`~/.codex/prompts/`); native plugin avoids this limitation.

## Grok Build (Claude Code compatibility)

[xAI Grok Build](https://x.ai/cli) (the `grok` CLI) reads the **canonical Claude plugin format AS-IS** - skills, agents, commands, MCP, and instruction files. Per [xAI docs](https://docs.x.ai/build/features/skills-plugins-marketplaces) it *"automatically reads Claude Code marketplaces, plugins, skills, MCPs, agents, hooks, and instruction files."* If flow-next is already installed in Claude Code, Grok picks it up with no extra setup.

**Grok is not a Codex host.** It does **not** consume the Codex mirror, does **not** use `$flow-next-*` command syntax, and must not fall through setup's `else → codex` path. Drive with `/flow-next:*` slash commands; after `/flow-next:setup` resolve flowctl via `.flow/bin/flowctl` (copy mode only).

### Setup detection (fn-126)

`/flow-next:setup` classifies the host via a positive rung, ordered after Droid / Claude / Cursor and **before** the `else → codex` fallback:

| Signal | Role |
|--------|------|
| **`GROK_AGENT=1`** | **Only valid detection signal.** Set BY grok in its agent shell. Probe-verified 2026-07-22 (present in a real grok session; absent from a plain-shell control on the same machine/profile). |
| `~/.grok/` directory | **Not a signal.** Install dir exists on the machine regardless of whether a grok session is running. |
| `~/.grok/bin` on `PATH` | **Not a signal.** Profile-level; present outside grok sessions too. |

**Instruction files (probe-verified):** Grok loads **both** `CLAUDE.md` and `AGENTS.md` into context (seeded-codename probe, 2026-07-22). Setup therefore writes the lifecycle docs snippet to **CLAUDE.md** by default (`/flow-next:` slash syntax, not Codex `$flow-next-`) and the model-routing scaffold to **AGENTS.md** (where host-review workflows resolve pins). A pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form (marker-scoped).

**Known nesting edge (Droid → Grok) - NEEDS-HUMAN:** if a grok child inherits `DROID_PLUGIN_ROOT` from a Droid parent shell, the cascade classifies as `droid` (higher precedence). Nested Droid→Grok is **unsupported** pending a this-process-is-grok discriminator, unless a live smoke confirms `DROID_PLUGIN_ROOT` does not propagate. Claude/Cursor launched from a grok shell still classify correctly via their own higher-precedence signals. The probe disproved `CLAUDE_PLUGIN_ROOT` propagation into a grok child.

### Install (pick one)

- **Already in Claude Code?** Nothing to do - run `grok inspect` and you'll see flow-next's skills loaded.
- **Add as a marketplace source:** flow-next's repo root is a Claude Code **marketplace** (`.claude-plugin/marketplace.json`), so register `gmickel/flow-next` via `[[marketplace.sources]]` in `~/.grok/config.toml` (or the TUI **Marketplace** tab, opened with `/plugins`), then enable the `flow-next` plugin.
- **Local / dev:** `grok --plugin-dir /path/to/flow-next/plugins/flow-next`.

Then run **`/flow-next:setup`** in the project (slash syntax - **not** `$flow-next-setup`). Grok is always **copy mode** (no plugin-root bin PATH injection): setup stamps `.flow/bin/flowctl`, writes the slash-syntax docs snippet, offers the Grok review + model-routing menus, and does **not** copy `.codex/agents` or offer Ralph.

> **Do NOT run `grok plugin install https://github.com/gmickel/flow-next`.** That is the **single-plugin** git installer; the repo root is a **marketplace** (the plugin is nested at `plugins/flow-next/`), so it errors `no plugins found in the source (no plugin.json or convention components)` - there is no single plugin at the repo root. This is the same reason you don't `claude plugin install` a marketplace repo. Use the marketplace / auto-read path above.

### What works (verified, Grok 0.2.27 alpha + fn-126 setup)

- All 28 flow-next **skills** load (`grok inspect`: `plugin: flow-next`); discovery used the **Claude Code plugin install** directly (`Marketplaces (0)`, no Grok-side config).
- **Slash commands.** Drive with `/flow-next:<name>` - **not** Codex `$flow-next-` syntax. Type `/flow-next:` to discover the namespaced command surface. The separately indexed `/flow-next-…` skill names are an implementation surface, not the documented invocation contract.
- **Multi-agent flows work - verified end-to-end.** A real `/flow-next:plan` run under Grok 0.2.27 **fanned out all seven scout subagents** (`repo-scout`, `practice-scout`, `docs-scout`, `spec-scout`, `docs-gap-scout`, `memory-scout`, `flow-gap-analyst`) in parallel; they spawned, completed, and the skill drove `flowctl` to create the spec + tasks and validate. Grok **dispatches flow-next's custom `subagent_type`s** even when `grok inspect` does not list them in its agent UI.
- **MCP servers** resolve (e.g. RepoPrompt, linear-server); after setup, `flowctl` resolves via **`.flow/bin/flowctl`** (copy mode).
- **Review menu includes `host`.** Setup offers `host` alongside `rp` / `codex` / `copilot` / `cursor` / `none`. **Single-family fail-closed:** Grok's only native model family is `grok-4.5`, so native `host` review fails closed (interactive → ask; autonomous → `NEEDS_HUMAN`) unless the writer is non-Grok. Cross-family review on Grok comes through bridge backends (`codex` / `cursor` / `copilot`), not a native multi-family subagent. Host-native model-routing scaffold lands in AGENTS.md and documents the same honesty.

### Caveats / intentional limits

- **Command discovery - live-verified with Grok 0.2.111 on 2026-07-23.** Type **`/flow-next:`** to open the plugin command autocomplete (`/flow-next:plan`, `/flow-next:work`, and the other user-facing verbs). Typing `/flow-next-` searches the separate hyphen-named skill surface instead, which is why plan/work appeared to be missing while internal skills such as `/flow-next-deps` appeared. This is a prefix-family distinction, not command under-listing. The pre-3.3.1 tripled-name bug remains fixed by fn-124.
- **Skill argument hints work.** Grok 0.2.111 showed a command-free skill's name and description in autocomplete, then rendered its `argument-hint` after Tab selection. Command and skill discovery remain separate prefix families: `/flow-next:` for the shipped namespaced commands; `/flow-next-` for the current hyphen-named skills.
- **Detection signal (live-verified 2026-07-22).** `GROK_AGENT=1` confirmed present in a STANDALONE grok session (`env \| grep GROK_AGENT` → `GROK_AGENT=1`, no other vars) - not an artifact of a launched-from-another-agent probe.
- **Ralph is intentionally not built for Grok.** Same posture as Cursor - not a hook-schema gap and not "TBD validation." Setup never offers Ralph on `PLATFORM=grok`, never registers guard hooks, and never runs ralph-init from the ceremony. Interactive plan / work / review is the supported surface.

> **Status:** verified-compat host. Detection: `GROK_AGENT=1` only. Canonical Claude files AS-IS; both CLAUDE.md and AGENTS.md loaded; `/flow-next:` slash syntax and command autocomplete; copy mode + `.flow/bin/flowctl`; review includes `host` with single-family fail-closed; no Ralph (intentional). Multi-agent scout fan-out verified. `GROK_AGENT=1` + no-nesting slash menu live-verified; command-prefix behavior re-verified on Grok 0.2.111 (2026-07-23). Nested Droid→Grok unsupported pending propagation smoke.

## Cursor

[Cursor](https://cursor.com) has its own plugin system in the `.cursor-plugin/` namespace and does **not** auto-read Claude Code's `.claude-plugin/` (unlike Grok). flow-next ships a root `.cursor-plugin/marketplace.json`, a per-plugin `.cursor-plugin/plugin.json` (explicit skills/agents/commands/rules paths so marketplace installs never discover `codex/` or `tests/`), and a Cursor-native `rules/flow-next.mdc` guidance rail.

### Recommended: team-marketplace repo import

For teams (and anyone on Cursor Teams / Enterprise), **import the GitHub repo as a team marketplace** — this is the **recommended** Cursor install. An admin connects the Cursor GitHub App, imports [`gmickel/flow-next`](https://github.com/gmickel/flow-next), and chooses an install mode:

| Mode | Meaning |
|------|---------|
| **Default Off** | Plugin available; each engineer opts in |
| **Default On** | Installed for the team; engineers can disable |
| **Required** | Forced on for every team member |

Cursor **auto-refreshes** the marketplace on push (GitHub App webhooks, ~10-minute batching). Engineers then run `/flow-next:setup` once per repo (writes `.flow/bin/flowctl`, `AGENTS.md` model-routing scaffold, etc.). No per-developer `git clone` + re-run-after-pull cycle.

Public Cursor Marketplace submission is **not** the path here (publisher-terms decision); team-marketplace repo import delivers the same one-click / auto-update / org-enforceable value without those terms.

#### Admin runbook

1. **Import the repo.** In Cursor team settings → Marketplaces / Plugins, import `https://github.com/gmickel/flow-next` via the Cursor GitHub App (requires admin on the Cursor team + GitHub App install on the org/repo).
2. **Choose install mode.** Prefer **Default On** for voluntary adoption, **Required** when every engineer must run flow-next on day one.
3. **Verify auto-refresh.** After a push that changes plugin files, wait for Cursor's refresh window (~10 min batching) and confirm team clients pick up the new surface (skills/commands/rules count or a known skill description change).
4. **Per-repo setup.** Each engineer (or the first clone of each project) runs `/flow-next:setup` — copy mode only on Cursor (no plugin-root env vars / bin PATH injection). Setup leads the review-backend menu with `host` (recommended), scaffolds AGENTS.md model-routing with live Cursor slugs, and stamps `.flow/bin/flowctl`.

### Fallback: local install scripts (individuals)

For solo use, air-gapped machines, or before team-marketplace is configured, the local installers copy a snapshot into `~/.cursor/plugins/local/flow-next`:

**macOS / Linux:**

```bash
git clone https://github.com/gmickel/flow-next.git
cd flow-next
./scripts/install-cursor.sh
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/gmickel/flow-next.git
cd flow-next
powershell -ExecutionPolicy Bypass -File .\scripts\install-cursor.ps1
```

The Windows installer (`install-cursor.ps1`) is a robocopy-based sibling of the bash script — same destination, same excludes, same real-directory contract. (Running the bash script under Git Bash / WSL works too, since `~/.cursor` resolves the same.)

Both copy the plugin into `~/.cursor/plugins/local/flow-next` (`%USERPROFILE%\.cursor\plugins\local\flow-next` on Windows) as a **real directory** (NOT a symlink — Cursor's plugin loader rejects a symlink whose realpath escapes `~/.cursor/`), with the `.cursor-plugin/plugin.json` manifest (its `commands` field points Cursor at the flat `./commands` directory) shipping `rules/*.mdc`. They exclude the Codex mirror + tests. It's a **snapshot — re-run after `git pull`** to update. Then **fully restart Cursor** (Cmd-Q / Quit, reopen — a new local plugin needs a full restart) and run `/flow-next:setup` in your project.

### What works (verified)

- **Skills, commands, and subagents** register and run. Slash autocomplete **lists** flow-next commands (hyphenated form, e.g. `/flow-next-plan`); the colon form (`/flow-next:plan`) also works when typed. Natural-language skill triggering works.
- **AskUserQuestion** renders natively, including multi-question batches (auto "Other...", Skip honored).
- **Multi-agent:** a full `/flow-next:plan` fans out scout subagents in parallel and drives `flowctl` end-to-end. Explicit subagent model pins (Cursor slugs, e.g. `claude-opus-4-8-thinking-high`) are honored; the host self-corrects near-miss ids.
- **`readonly: true`** on read-only agents (scouts, reviewers) enforces write restriction on Cursor (`disallowedTools` is not consumed there).
- **`review.backend host`:** fresh-context subagent review pinned via AGENTS.md routing / caller-side slug pins to a family that did not write the diff (preferred from inside Cursor; existing `codex` / `copilot` / `cursor` CLI / `rp` backends remain selectable).
- **`rules/flow-next.mdc`:** Cursor-native guidance rail (flowctl lifecycle + `flowctl usage` pull directives).
- **AGENTS.md model-routing scaffold** from setup: date-stamped Cursor slugs + dispatch-pin rules (cheap slug for scouts, cross-family for review, inherit otherwise); re-run setup to refresh.
- **`flowctl`** resolves via `.flow/bin/flowctl` after setup (Cursor exposes no plugin-root env var).

The interview skill's optional async fact-scout dispatch names Claude Code's `Explore` builtin; Cursor has no such builtin, so the skill's portable-host clause applies — generic read-only dispatch, falling back to inline investigation if none is available.

### Caveats / intentional limits

- **Agents frontmatter aliases → inherit.** On Cursor, `agents/*.md` family aliases (`opus`, `sonnet`, …) are ignored; subagents inherit the session model. Caller-side in-prompt slug pins are the escape hatch — no alias-to-slug rewrite pass (marketplace import consumes canonical files as-is).
- **Ralph autonomous mode is intentionally not built for Cursor.** Cursor has a full agent-hook set (and Claude Code hook compatibility exists upstream), but flow-next does **not** register Ralph guards on Cursor — interactive plan / work / review is the supported surface. Scaffolding `scripts/ralph/` does not enable the autonomous loop here.
- **Tracker-sync background dispatch runs at Tier B (isolated-but-awaited).** Comment-shaped tracker touchpoints dispatch to a `tracker-runner` subagent for context isolation, but the host **awaits** it — fire-and-forget overlap is Claude-Code-only (Tier A). See `docs/tracker-sync.md` § Background dispatch.

> **Status:** first-class on Cursor. Recommended path = team-marketplace repo import; local scripts = individual/fallback. Multi-agent, native asks, slash autocomplete, `review.backend host`, rules rail, and setup model-routing verified. Ralph intentionally not built for Cursor.

## Windows: Python discovery

flow-next's bundled `flowctl` is a thin launcher over `flowctl.py`. On Windows it resolves the Python interpreter by **probing functionality and the Python 3.11 minimum, not presence**: each candidate must run a version probe successfully. Probe order is `$PYTHON_BIN` → `py -3` → `python3` → `python`. Broken Store aliases are skipped; if only working interpreters below 3.11 exist, the launcher reports that distinct condition before loading flowctl.

- **Dual launcher.** The extensionless bash `flowctl` runs under Git Bash / WSL (and macOS / Linux); a **`flowctl.cmd`** batch shim runs the same probe under **cmd.exe / PowerShell** — i.e. Claude Desktop, native Codex, and native Cursor, where the bash launcher's shebang is never honored. Both live under `.flow/bin/` and are (re-)written by `flowctl init` / `/flow-next:setup`.
- **`py -3` preferred.** The [py launcher](https://docs.python.org/3/using/windows.html) (`C:\Windows\py.exe`, installed by python.org / [PEP 397](https://peps.python.org/pep-0397/)) is never a Store alias stub, so it's the most reliable Windows candidate.
- **Alias-stub pitfall.** On Windows `python3` is, by default, the Microsoft Store **App Execution Alias** stub — on `PATH` but non-functional (prints *"Python was not found"*, exits **9009**). The probe skips it; a bare presence check does not. If a *pre-fix* install still hits it, see [`troubleshooting.md` → Windows `python3` / Store alias stub](troubleshooting.md#windows-python3-not-found--microsoft-store-alias-stub-fixed-in-fn-77) for the two recovery paths (re-stamp launchers via `py -3 .flow/bin/flowctl.py init`, or disable the alias).
- **Ralph mode requires Git Bash on Windows.** The Ralph harness (`ralph.sh`) and its hook wrapper are bash, and the `ralph-guard.py` hook is invoked via a bash wrapper that sources the shared resolver — there is **no** native `ralph-guard.cmd`, because the harness that would call it is itself bash. So run Ralph under Git Bash / WSL on Windows. The interactive `flowctl` / plan / work / review workflow needs no such constraint (the `.cmd` shim covers cmd/PowerShell).

## RepoPrompt review backend (macOS-only)

The `rp` review backend drives [RepoPrompt Community Edition](https://repoprompt.com) on macOS. Flow-Next prefers `rpce-cli` on PATH, then the current and legacy CE user links, with discontinued Classic `rp-cli` retained only as the final compatibility fallback. Once CE is selected, a connection or command failure is authoritative and never retries against Classic. `/flow-next:plan` and the review skills only *propose* RepoPrompt when that CE-first capability ladder finds a runnable CLI; other hosts steer to the cross-platform backends (`codex`, `copilot`, `cursor`, `host`, `none`). Explicit `--review=rp` / `review.backend=rp` remains accepted anywhere and fails at runtime with a clear supported-RepoPrompt-CLI diagnostic when no candidate exists.

## Windows + Copilot review backend

Works natively from flow-next 1.1.9. flow-next picks the prompt-delivery path per host:

- **POSIX (macOS / Linux / WSL):** `copilot -p "<prompt>" --resume=<uuid> ...` — argv path, create-or-resume in one call.
- **Windows:** `copilot --session-id=<uuid> ...` (first call) or `--resume=<uuid>` (continuation), with the prompt piped via stdin. Bypasses the `CreateProcessW` 32,767-char cap that broke the argv path for spec-sized prompts in 1.1.8 and earlier.

No configuration knob — `run_copilot_exec` switches transparently on `sys.platform == "win32"`. Session continuity is tracked via a touch marker under `.flow/tmp/copilot-sessions/<uuid>` (needed because stdin-mode `--resume` is resume-only, unlike `-p` mode's create-or-resume).

Upstream tracking: [github/copilot-cli#3398](https://github.com/github/copilot-cli/issues/3398) requests a first-class `--prompt-file` flag, which will let both paths converge.

## Optional skill requirements

Most flow-next skills run on the base flowctl install (Python 3.11+, `jq`, `gh`). A couple of opt-in skills carry an extra prerequisite:

> **Windows Python 3.11+ caveat:** the `py` launcher or a supported python.org install satisfies this; the Microsoft Store `python3` **alias stub does not** (it's on `PATH` but non-functional). flowctl's launcher probes past it automatically and separately identifies working but too-old interpreters — see [Windows: Python discovery](#windows-python-discovery).

| Skill | Requires | Notes |
|---|---|---|
| `/flow-next:map` | Node 22+ and `clawpatch` global (`pnpm add -g clawpatch`) | Wraps openclaw/clawpatch's `clawpatch map` to produce `.clawpatch/features/*.json`. Skill works on macOS / Linux / WSL / Git Bash on Windows wherever the host shell can resolve `clawpatch`. Missing binary → skill prints `pnpm add -g clawpatch` install instructions verbatim and exits cleanly (no auto-install). pnpm-installed-but-not-on-PATH → skill prints the PNPM_HOME `bin/` hint (run `pnpm setup`, re-source shell rc). The skill carries the tested `clawpatch` version range (`SUPPORTED_CLAWPATCH`); see `plugins/flow-next/skills/flow-next-map/SKILL.md` for the current pin. Outside-range → skill warns one line to stderr and degrades — never blocks. **Opt-in convenience** — `flowctl` core never imports or requires clawpatch; scouts gracefully fall back to the grep/glob path when `.clawpatch/` is absent. |
| `/flow-next:qa` | A **live deploy** + a **driver** resolved by [`flow-next-drive`](../skills/flow-next-drive/SKILL.md) | The live-app QA pass consumes `flow-next-drive`'s surface-aware driver ladder (agent-browser → chrome-devtools-mcp → Playwright → cursor-ide-browser → manual, with the **Cua Driver** (MIT, provider-agnostic, background) → Computer Use for native surfaces and a **Cua Sandbox** rung for headless/CI native runs); QA never re-implements driving. Whatever rung `flow-next-drive` resolves for the surface — including degraded-to-manual — is what QA inherits. With **no live deploy or no driver**, QA surfaces a **BLOCKED** verdict (could not verify) rather than failing; a spec with no driveable UI yields a clean **N/A** verdict. **Opt-in** — adds nothing to the base flow when unused. |

Removing the skill is trivial: `rm -rf .clawpatch/` removes both the index and the self-contained `.gitignore` skeleton in one step (the skill does not touch the repo `.gitignore`).

## Community ports and inspired projects

| Project | Platform | Notes |
|---------|----------|-------|
| [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | OpenCode | Flow-Next port |
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid | Flow port (note: flow-next now has native Droid support) |

## See also

- [`sync-codex.md`](sync-codex.md) — how the Codex mirror is generated from canonical sources; validation guards.
- [`troubleshooting.md`](troubleshooting.md) — review-backend conflicts (custom RepoPrompt CLI instructions), receipt validation.
- [`ralph.md`](ralph.md) — Ralph hook limits on each platform.
- [`../scripts/install-codex.sh`](../../../scripts/install-codex.sh) — canonical install script for Codex.
