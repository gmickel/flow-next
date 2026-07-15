# Other Platforms

Flow-next is a first-class citizen on Claude Code (canonical), OpenAI Codex (pre-built mirror), and Factory Droid (native cross-platform patterns). A community port exists for OpenCode. xAI **Grok Build** reads the Claude Code plugin with zero config — skills load, the `/flow-next:*` commands **run when typed** (hooks fire), and **multi-agent flows work** (a full `/flow-next:plan` fanned out all seven scouts, verified). Grok's UI just under-lists flow-next's commands/agents (cosmetic — they work when invoked); Ralph autonomous mode is the one piece still to validate (see [Grok Build](#grok-build-claude-code-compatibility) below). **Cursor** runs flow-next too, via its own `.cursor-plugin/` local install (`./scripts/install-cursor.sh` on macOS/Linux, `install-cursor.ps1` on Windows) — skills, commands, and multi-agent flows verified; Ralph unsupported there (hook-schema mismatch). See [Cursor](#cursor-local-plugin) below.

## Install matrix

| Platform | Install command | Plugin file | Notes |
|----------|-----------------|-------------|-------|
| Claude Code | `/plugin marketplace add gmickel/flow-next-marketplace && /plugin install flow-next` | `.claude-plugin/plugin.json` | Canonical environment |
| Factory Droid | `droid plugin marketplace add https://github.com/gmickel/flow-next && droid plugin install flow-next` (in Droid CLI) | `.claude-plugin/plugin.json` (Droid auto-translates Claude Code plugin format) | Native cross-platform patterns |
| OpenAI Codex | `git clone https://github.com/gmickel/flow-next.git && cd flow-next && ./scripts/install-codex.sh` | `.codex-plugin/plugin.json` | Pre-built mirror under `plugins/flow-next/codex/` |
| Grok Build (xAI) | Auto-discovered if installed in Claude Code (run `grok inspect`); or add `gmickel/flow-next` as a `[[marketplace.sources]]` entry. **Not** `grok plugin install <repo>`. | `.claude-plugin/plugin.json` (read via Claude Code compat) | **Works incl. multi-agent** (full `/flow-next:plan` scout fan-out verified). UI under-lists commands/agents (cosmetic); Ralph TBD — see below |
| Cursor | `./scripts/install-cursor.sh` (macOS/Linux) or `install-cursor.ps1` (Windows) → copies to `~/.cursor/plugins/local/` | `.cursor-plugin/plugin.json` (Cursor's own namespace — does NOT read `.claude-plugin/`) | **Works incl. multi-agent** (verified). No plugin card + autocomplete under-list (cosmetic); **Ralph unsupported** (hook-schema mismatch) — see below |
| OpenCode | See [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | n/a | Community port |

> The canonical install path on Claude Code is the marketplace. Direct `--plugin-dir` (`claude --plugin-dir ./plugins/flow-next`) is the development path.

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
| Worker (default) | *inherit (session model)* | *session default* | worker |
| Inherited | parent model | parent | pr-comment-resolver |

`quality-auditor` is review-shaped (a second pair of eyes on uncommitted changes) and stays at `high` — undershooting risks missed regressions. Other intelligent agents do scout/editorial work and run efficiently at `medium`. The worker defaults to `inherit` on BOTH platforms - your session model rules, and flow-next never hardcodes a model opinion into generated config. An OPT-IN pin is available at sync time (`CODEX_MODEL_WORKER` / `CODEX_REASONING_EFFORT_WORKER`); the eval-motivated recommendation is `gpt-5.6-terra` @ `medium`. Note (Jul 2026): on Sol/Multi-Agent-V2 builds role-profile model application is currently unreliable (openai/codex#33268, #33314) - prefer the `codex exec -m` self-bridge to steer models from a Codex host until those are fixed (fn-97, 2026-07 controlled pipeline eval at n=3: terra-medium matched `gpt-5.6-sol` correctness at ~2/3 wall-clock on frontier-authored specs). The actual review backend (`flowctl impl-review` / `plan-review` / `completion-review`) is configured separately in `flowctl.py` and defaults to `gpt-5.5:high` on its own.

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

## Grok Build (Claude Code compatibility)

[xAI Grok Build](https://x.ai/cli) (the `grok` CLI) advertises zero-config Claude Code compatibility — per [xAI docs](https://docs.x.ai/build/features/skills-plugins-marketplaces) it *"automatically reads Claude Code marketplaces, plugins, skills, MCPs, agents, hooks, and instruction files."* If flow-next is already installed in Claude Code, Grok picks it up with no extra setup.

### Install (pick one)

- **Already in Claude Code?** Nothing to do — run `grok inspect` and you'll see flow-next's skills + hook loaded.
- **Add as a marketplace source:** flow-next's repo root is a Claude Code **marketplace** (`.claude-plugin/marketplace.json`), so register `gmickel/flow-next` via `[[marketplace.sources]]` in `~/.grok/config.toml` (or the TUI **Marketplace** tab, opened with `/plugins`), then enable the `flow-next` plugin.
- **Local / dev:** `grok --plugin-dir /path/to/flow-next/plugins/flow-next`.

> **Do NOT run `grok plugin install https://github.com/gmickel/flow-next`.** That is the **single-plugin** git installer; the repo root is a **marketplace** (the plugin is nested at `plugins/flow-next/`), so it errors `no plugins found in the source (no plugin.json or convention components)` — there is no single plugin at the repo root. This is the same reason you don't `claude plugin install` a marketplace repo. Use the marketplace / auto-read path above.

### What works (verified, Grok 0.2.27 alpha)

- All 24 flow-next **skills** load (`grok inspect`: `plugin: flow-next`); discovery used the **Claude Code plugin install** directly (`Marketplaces (0)`, no Grok-side config).
- **The `/flow-next:<name>` commands run when typed.** Typing `/flow-next:plan` fires `user_prompt_submit`, loads the `flow-next-plan` skill, and runs its workflow — **hooks fire** (`user_prompt_submit` + skill hooks). The Ralph-guard **hook** loads (`file → plugin: flow-next`).
- **Multi-agent flows work — verified end-to-end.** A real `/flow-next:plan` run under Grok 0.2.27 **fanned out all seven scout subagents** (`repo-scout`, `practice-scout`, `docs-scout`, `spec-scout`, `docs-gap-scout`, `memory-scout`, `flow-gap-analyst`) in parallel; they spawned, completed, and the skill drove `flowctl` to create the spec + tasks and validate — a full plan, start to finish. So Grok **dispatches flow-next's custom `subagent_type`s** even though `grok inspect` doesn't list them in its agent UI. (UI listing ≠ functionality — see below.)
- **MCP servers** resolve (e.g. RepoPrompt, linear-server); `flowctl` resolves via the bundled `.flow/bin/flowctl` copy.

### Caveats (cosmetic, not functional)

- **Grok's UI under-lists flow-next's commands and agents — but both work when invoked.** `grok inspect` shows only Grok's 3 builtin agents (not flow-next's 21), and the slash *autocomplete* lists only the ~7 skills with **no** `user-invocable` key (`flow-next`, `flow-next-deps`, `flow-next-drive`, `flow-next-export-context`, `flow-next-rp-explorer`, `flow-next-worktree-kit`). The 20 `user-invocable: false` skills + the 22 `commands/flow-next/*.md` wrappers don't show in the menu, and the custom agents don't show in `inspect` — yet **the commands run when typed in full** (e.g. `/flow-next:plan`) and **the subagents dispatch** (verified above). flow-next marks skills `user-invocable: false` because the Claude Code entry point is the command wrapper; Grok's menu keys on that flag and its `inspect` summary just doesn't surface plugin agents. **Discoverability gap, not a functional one — type the command.**
- **Ralph autonomous mode — not yet validated.** The verified run was interactive multi-agent work; Ralph's hook-gated `Stop`/`SubagentStop` loop hasn't been exercised under Grok. Hooks load and fire; the autonomous gating specifically is untested.

> **Status (Grok 0.2.27 alpha):** skills load; `/flow-next:*` commands **run when typed** (hooks fire); MCP + `flowctl` resolve; and **multi-agent subagent dispatch works** — a full `/flow-next:plan` fanned out all seven scouts end-to-end. Caveat: Grok's autocomplete + `grok inspect` under-list flow-next's commands/agents (cosmetic — they work when invoked). Ralph autonomous mode is the one piece still to validate.

## Cursor (local plugin)

[Cursor](https://cursor.com) has its own plugin system in the `.cursor-plugin/` namespace and does **not** auto-read Claude Code's `.claude-plugin/` (unlike Grok). flow-next ships a `.cursor-plugin/plugin.json` + a local installer.

### Install

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

Both copy the plugin into `~/.cursor/plugins/local/flow-next` (`%USERPROFILE%\.cursor\plugins\local\flow-next` on Windows) as a **real directory** (NOT a symlink — Cursor's plugin loader rejects a symlink whose realpath escapes `~/.cursor/`), with the `.cursor-plugin/plugin.json` manifest (a `commands` path-override points Cursor at the nested `commands/flow-next/`). They exclude the Codex mirror + tests. It's a **snapshot — re-run after `git pull`** to update. Then **fully restart Cursor** (Cmd-Q / Quit, reopen — a new local plugin needs a full restart) and run `/flow-next:setup` in your project.

### What works (verified)

flow-next's **skills, commands, and subagents all register and run** on Cursor. A full `/flow-next:plan` run fanned out the scout subagents in parallel (Opus 4.8) and drove `flowctl` to create the spec + tasks end-to-end — the same multi-agent engine as Claude Code. `flowctl` resolves via `.flow/bin/flowctl` after `/flow-next:setup`: Cursor exposes **no plugin-root env var**, so the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` path is empty, but the project-local `.flow/bin/flowctl` + the `AGENTS.md` / `.flow/usage.md` instructions are what the agent uses (verified end-to-end).

### Caveats

- **No "plugin" card.** Cursor registers the individual skills/commands/agents (they appear in the `/` menu + skill/command/subagent lists), but flow-next does **not** show as a grouped plugin in the marketplace UI — cosmetic; the components work.
- **Slash autocomplete under-lists** (same as Grok): `user-invocable: false` skills + the command wrappers don't populate the menu, but **run when typed in full**.
- **Ralph autonomous mode is NOT supported.** Cursor's hook schema is `afterFileEdit` / `beforeShellExecution`; flow-next's hooks use Claude Code's `PreToolUse` / `Stop` + `Bash|Execute` matchers, which Cursor doesn't recognize — so the Ralph guard never fires. The interactive plan / work / review workflow is unaffected. (A future Cursor-format hook mirror could add it.)

> **Status:** skills + commands + agents register and run; **multi-agent verified**; flowctl resolves post-`/flow-next:setup`. Cosmetic: no plugin card + autocomplete under-lists. Ralph unsupported (hook-schema mismatch).

## Windows: Python discovery

flow-next's bundled `flowctl` is a thin launcher over `flowctl.py`. On Windows it resolves the Python interpreter by **probing functionality, not presence** (fn-77): each candidate must actually run `<cand> -c "import sys"` and exit 0. Probe order is `$PYTHON_BIN` → `py -3` → `python3` → `python`.

- **Dual launcher.** The extensionless bash `flowctl` runs under Git Bash / WSL (and macOS / Linux); a **`flowctl.cmd`** batch shim runs the same probe under **cmd.exe / PowerShell** — i.e. Claude Desktop, native Codex, and native Cursor, where the bash launcher's shebang is never honored. Both live under `.flow/bin/` and are (re-)written by `flowctl init` / `/flow-next:setup`.
- **`py -3` preferred.** The [py launcher](https://docs.python.org/3/using/windows.html) (`C:\Windows\py.exe`, installed by python.org / [PEP 397](https://peps.python.org/pep-0397/)) is never a Store alias stub, so it's the most reliable Windows candidate.
- **Alias-stub pitfall.** On Windows `python3` is, by default, the Microsoft Store **App Execution Alias** stub — on `PATH` but non-functional (prints *"Python was not found"*, exits **9009**). The probe skips it; a bare presence check does not. If a *pre-fix* install still hits it, see [`troubleshooting.md` → Windows `python3` / Store alias stub](troubleshooting.md#windows-python3-not-found--microsoft-store-alias-stub-fixed-in-fn-77) for the two recovery paths (re-stamp launchers via `py -3 .flow/bin/flowctl.py init`, or disable the alias).
- **Ralph mode requires Git Bash on Windows.** The Ralph harness (`ralph.sh`) and its hook wrapper are bash, and the `ralph-guard.py` hook is invoked via a bash wrapper that sources the shared resolver — there is **no** native `ralph-guard.cmd`, because the harness that would call it is itself bash. So run Ralph under Git Bash / WSL on Windows. The interactive `flowctl` / plan / work / review workflow needs no such constraint (the `.cmd` shim covers cmd/PowerShell).

## RepoPrompt review backend (macOS-only)

The `rp` review backend drives the [RepoPrompt](https://repoprompt.com) macOS GUI via `rp-cli` — it does not exist on Linux or Windows. `/flow-next:plan` and `/flow-next:plan-review` therefore only *propose* the RepoPrompt path when it can actually run (host is macOS, or `rp-cli` is on PATH). On other hosts, `/flow-next:plan`'s setup questions default research to `repo-scout` (no RepoPrompt question) and offer Codex / export / none for review; `/flow-next:plan-review`'s guidance steers only to the cross-platform backends (`codex`, `copilot`, `cursor`, `none`). `/flow-next:impl-review` and `/flow-next:spec-completion-review` apply the same gate: on ineligible hosts their backend summaries, "Backend at a glance" lists, and ASK-error/override hints omit rp and steer only to `codex` / `copilot` / `cursor` (+ `none`). An explicit `--review=rp` / `review.backend=rp` is still accepted anywhere and fails at runtime with a clear `rp-cli not found in PATH` error if the CLI is absent.

## Windows + Copilot review backend

Works natively from flow-next 1.1.9. flow-next picks the prompt-delivery path per host:

- **POSIX (macOS / Linux / WSL):** `copilot -p "<prompt>" --resume=<uuid> ...` — argv path, create-or-resume in one call.
- **Windows:** `copilot --session-id=<uuid> ...` (first call) or `--resume=<uuid>` (continuation), with the prompt piped via stdin. Bypasses the `CreateProcessW` 32,767-char cap that broke the argv path for spec-sized prompts in 1.1.8 and earlier.

No configuration knob — `run_copilot_exec` switches transparently on `sys.platform == "win32"`. Session continuity is tracked via a touch marker under `.flow/tmp/copilot-sessions/<uuid>` (needed because stdin-mode `--resume` is resume-only, unlike `-p` mode's create-or-resume).

Upstream tracking: [github/copilot-cli#3398](https://github.com/github/copilot-cli/issues/3398) requests a first-class `--prompt-file` flag, which will let both paths converge.

## Optional skill requirements

Most flow-next skills run on the base flowctl install (Python 3.8+, `jq`, `gh`). A couple of opt-in skills carry an extra prerequisite:

> **Windows Python 3.8+ caveat:** the `py` launcher or a python.org install satisfies this; the Microsoft Store `python3` **alias stub does not** (it's on `PATH` but non-functional). flowctl's launcher probes past it automatically — see [Windows: Python discovery](#windows-python-discovery).

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
- [`troubleshooting.md`](troubleshooting.md) — review-backend conflicts (`rp-cli` custom instructions), receipt validation.
- [`ralph.md`](ralph.md) — Ralph hook limits on each platform.
- [`../scripts/install-codex.sh`](../../../scripts/install-codex.sh) — canonical install script for Codex.
