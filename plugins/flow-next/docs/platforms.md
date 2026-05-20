# Other Platforms

Flow-next is a first-class citizen on Claude Code (canonical), OpenAI Codex (pre-built mirror), and Factory Droid (native cross-platform patterns). A community port exists for OpenCode.

## Install matrix

| Platform | Install command | Plugin file | Notes |
|----------|-----------------|-------------|-------|
| Claude Code | `/plugin marketplace add gmickel/flow-next-marketplace && /plugin install flow-next` | `.claude-plugin/plugin.json` | Canonical environment |
| Factory Droid | `/plugin marketplace add https://github.com/gmickel/flow-next && /plugin install flow-next` (in Droid CLI) | `.factory-plugin/plugin.json` (falls back from Claude file) | Native cross-platform patterns |
| OpenAI Codex | `git clone https://github.com/gmickel/flow-next.git && cd flow-next && ./scripts/install-codex.sh` | `.codex-plugin/plugin.json` | Pre-built mirror under `plugins/flow-next/codex/` |
| OpenCode | See [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | n/a | Community port |

> The canonical install path on Claude Code is the marketplace. Direct `--plugin-dir` (`claude --plugin-dir ./plugins/flow-next`) is the development path.

## Factory Droid (native support)

Flow-next works natively in [Factory Droid](https://factory.ai) — no modifications needed.

**Install:**
```bash
# In Droid CLI
/plugin marketplace add https://github.com/gmickel/flow-next
/plugin install flow-next
```

**Cross-platform patterns used:**
- Skills use `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` bash fallback.
- Hooks use `Bash|Execute` regex matcher (Claude Code = `Bash`, Droid = `Execute`).
- Agents use `disallowedTools` blacklist (not `tools` whitelist — tool names differ between platforms; blacklist works because both understand `Edit`, `Write`, `Task`).
- Plugin paths check both: `.claude-plugin/plugin.json` falls back to `.factory-plugin/plugin.json`.

**Caveats:**
- Subagents may behave differently (Droid's Task tool implementation).
- Hook timing may vary slightly.

> **Rollback:** If you experience issues, downgrade to v0.20.9 (last pre-Droid version): `claude plugins install flow-next@0.20.9`.

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
