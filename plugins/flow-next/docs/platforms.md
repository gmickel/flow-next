# Other Platforms

Flow-next is a first-class citizen on Claude Code (canonical), OpenAI Codex (pre-built mirror), and Factory Droid (native cross-platform patterns). A community port exists for OpenCode.

## Install matrix

| Platform | Install command | Plugin file | Notes |
|----------|-----------------|-------------|-------|
| Claude Code | `/plugin marketplace add gmickel/flow-next-marketplace && /plugin install flow-next` | `.claude-plugin/plugin.json` | Canonical environment |
| Factory Droid | `droid plugin marketplace add https://github.com/gmickel/flow-next && droid plugin install flow-next` (in Droid CLI) | `.claude-plugin/plugin.json` (Droid auto-translates Claude Code plugin format) | Native cross-platform patterns |
| OpenAI Codex | `git clone https://github.com/gmickel/flow-next.git && cd flow-next && ./scripts/install-codex.sh` | `.codex-plugin/plugin.json` | Pre-built mirror under `plugins/flow-next/codex/` |
| OpenCode | See [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | n/a | Community port |

> The canonical install path on Claude Code is the marketplace. Direct `--plugin-dir` (`claude --plugin-dir ./plugins/flow-next`) is the development path.

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
- **Hook tool name** — Droid's shell-command tool is named **`Execute`** (not `Bash`); per Factory docs, `Bash` is not a recognized matcher in Droid. flow-next's `hooks.json` uses `"matcher": "Bash|Execute"` (regex OR) so a single hook entry fires on both Claude (`Bash`) and Droid (`Execute`).
- **Agent permissions** — flow-next uses `disallowedTools` blacklists instead of `tools` whitelists, because tool names diverge (Claude `Bash` vs Droid `Execute`, etc.) but both platforms understand the common deny-list set (`Edit`, `Write`, `Task`).

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

The script copies pre-built files from `codex/` to `~/.codex/` (skills, 21 `.toml` agents, hooks, flowctl, prompts, ralph templates) and merges agent + feature entries into `config.toml`. Idempotent — re-run after `git pull` to update. The native `/plugins` install path isn't used because Codex's plugin manifest only declares `skills`, not custom agents or hooks; until that changes, the script is the only way to get the full multi-agent experience.

### Skill invocation

In Codex, skills appear with display names in the `$` dropdown (e.g. **Flow Setup**, **Flow Plan**). Three invocation forms:

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
| `/flow-next:spec-completion-review` | Flow Spec Completion Review | `$flow-next-spec-completion-review` |
| `/flow-next:make-pr` | Flow Make PR | `$flow-next-make-pr` |
| `/flow-next:interview` | Flow Interview | `$flow-next-interview` |
| `/flow-next:prime` | Flow Prime | `$flow-next-prime` |
| `/flow-next:setup` | Flow Setup | `$flow-next-setup` |

### What works

- Planning, work execution, interviews, reviews — full workflow.
- Multi-agent roles: 20 agents as `.toml` files with subagent optimizations (`sandbox_mode`, `nickname_candidates`).
- Cross-model reviews (Codex as review backend).
- flowctl CLI (`~/.codex/scripts/flowctl`).
- Setup skill (`$flow-next-setup`) — detects Codex platform, copies agents/hooks/flowctl to project.
- `openai.yaml` UI metadata for Codex app display (brand color, descriptions).

### Model mapping (per-agent reasoning tier)

| Tier | Codex Model | Reasoning | Agents |
|------|-------------|-----------|--------|
| Review-shaped | `gpt-5.5` | `high` | quality-auditor |
| Scout / editorial | `gpt-5.5` | `medium` | flow-gap-analyst, context-scout, docs-scout, github-scout, practice-scout, repo-scout, plan-sync, spec-scout, agents-md-scout, docs-gap-scout |
| Fast scouts | `gpt-5.4-mini` | n/a | build, env, testing, tooling, observability, security, workflow, memory scouts |
| Inherited | parent model | parent | worker, pr-comment-resolver |

`quality-auditor` is review-shaped (a second pair of eyes on uncommitted changes) and stays at `high` — undershooting risks missed regressions. Other intelligent agents do scout/editorial work and run efficiently at `medium`. The actual review backend (`flowctl impl-review` / `plan-review` / `completion-review`) is configured separately in `flowctl.py` and defaults to `gpt-5.5:high` on its own.

Override model defaults (global install only):

```bash
CODEX_MODEL_INTELLIGENT=gpt-5.5 \
CODEX_MODEL_FAST=gpt-5.4-mini \
CODEX_REASONING_EFFORT=medium \
CODEX_REASONING_EFFORT_AUDITOR=high \
CODEX_MAX_THREADS=12 \
./scripts/install-codex.sh flow-next
```

### Hooks (experimental)

Codex now supports hooks. The pre-built `codex/hooks.json` includes Ralph guard hooks for `Bash|Execute` tool calls and `Stop` events.

**Limitation:** Codex hooks only intercept `Bash` (not `Edit`/`Write`). Ralph's file-modification guard won't catch direct file edits. The `SubagentStop` event is also not supported.

### Per-project setup

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

### Caveats

- Ralph autonomous mode is limited — hooks intercept Bash only (not Edit/Write), no `SubagentStop` support.
- `claude-md-scout` is auto-renamed to `agents-md-scout` (CLAUDE.md → AGENTS.md patching).
- Global install prompts (`/prompts:*`) are global-only (`~/.codex/prompts/`); native plugin avoids this limitation.

## Windows + Copilot review backend

Works natively from flow-next 1.1.9. flow-next picks the prompt-delivery path per host:

- **POSIX (macOS / Linux / WSL):** `copilot -p "<prompt>" --resume=<uuid> ...` — argv path, create-or-resume in one call.
- **Windows:** `copilot --session-id=<uuid> ...` (first call) or `--resume=<uuid>` (continuation), with the prompt piped via stdin. Bypasses the `CreateProcessW` 32,767-char cap that broke the argv path for spec-sized prompts in 1.1.8 and earlier.

No configuration knob — `run_copilot_exec` switches transparently on `sys.platform == "win32"`. Session continuity is tracked via a touch marker under `.flow/tmp/copilot-sessions/<uuid>` (needed because stdin-mode `--resume` is resume-only, unlike `-p` mode's create-or-resume).

Upstream tracking: [github/copilot-cli#3398](https://github.com/github/copilot-cli/issues/3398) requests a first-class `--prompt-file` flag, which will let both paths converge.

## Optional skill requirements

Most flow-next skills run on the base flowctl install (Python 3.8+, `jq`, `gh`). One opt-in skill carries an extra prerequisite:

| Skill | Requires | Notes |
|---|---|---|
| `/flow-next:map` | Node 22+ and `clawpatch` global (`pnpm add -g clawpatch`) | Wraps openclaw/clawpatch's `clawpatch map` to produce `.clawpatch/features/*.json`. Skill works on macOS / Linux / WSL / Git Bash on Windows wherever the host shell can resolve `clawpatch`. Missing binary → skill prints `pnpm add -g clawpatch` install instructions verbatim and exits cleanly (no auto-install). pnpm-installed-but-not-on-PATH → skill prints the PNPM_HOME `bin/` hint (run `pnpm setup`, re-source shell rc). The skill carries the tested `clawpatch` version range (`SUPPORTED_CLAWPATCH`); see `plugins/flow-next/skills/flow-next-map/SKILL.md` for the current pin. Outside-range → skill warns one line to stderr and degrades — never blocks. **Opt-in convenience** — `flowctl` core never imports or requires clawpatch; scouts gracefully fall back to the grep/glob path when `.clawpatch/` is absent. |

Removing the skill is trivial: `rm -rf .clawpatch/` removes both the index and the self-contained `.gitignore` skeleton in one step (the skill does not touch the repo `.gitignore`).

## Community ports and inspired projects

| Project | Platform | Notes |
|---------|----------|-------|
| [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | OpenCode | Flow-Next port |
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid | Flow port (note: flow-next now has native Droid support) |

## See also

- [`sync-codex.md`](sync-codex.md) — how the Codex mirror is generated from canonical sources; validation guards.
- [`troubleshooting.md`](troubleshooting.md) — review-backend conflicts (`rp-cli` custom instructions), receipt validation.
- [`ralph.md`](ralph.md) — Ralph hook limits on each platform.
- [`../scripts/install-codex.sh`](../../../scripts/install-codex.sh) — canonical install script for Codex.
