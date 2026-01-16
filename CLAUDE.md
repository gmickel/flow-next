# Claude Code Project Guide

## Purpose
This repo is a Claude Code plugin marketplace. It ships two plugins: **flow** and **flow-next**.

## Structure
- Marketplace manifest: `.claude-plugin/marketplace.json`
- Plugins live in `plugins/`
- Each plugin has: `.claude-plugin/plugin.json`, `commands/`, `skills/`, optionally `agents/`

## Plugins

### flow-next (recommended)
Zero-dependency workflow with bundled `flowctl.py`. All state in `.flow/` directory.

Commands:
- `/flow-next:plan` → creates epic + tasks in `.flow/`
- `/flow-next:work` → executes tasks with re-anchoring
- `/flow-next:interview` → deep spec refinement
- `/flow-next:plan-review` → Carmack-level plan review via rp-cli
- `/flow-next:impl-review` → Carmack-level impl review (current branch)

Ralph (autonomous loop):
- Script template lives in `plugins/flow-next/skills/flow-next-ralph-init/templates/`.
- Ralph uses `flowctl rp` wrappers (not direct rp-cli) for reviews.
- Receipts gate progress when `REVIEW_RECEIPT_PATH` is set.
- Runbooks: `plans/ralph-e2e-notes.md`, `plans/ralph-getting-started.md`.

Memory system (opt-in):
- Config in `.flow/config.json` (NOT Ralph's `config.env`)
- Enable: `flowctl config set memory.enabled true`
- Init: `flowctl memory init`
- Add: `flowctl memory add --type <pitfall|convention|decision> "content"`
- Query: `flowctl memory list`, `flowctl memory search "pattern"`
- Auto-capture: NEEDS_WORK reviews → pitfalls.md (in Ralph mode)

### flow
Original plugin with optional Beads integration. Plan files in `plans/`.

Commands:
- `/flow:plan` → writes `plans/<slug>.md`
- `/flow:work` → executes a plan
- `/flow:interview` → deep interview about spec/bead
- `/flow:plan-review` → Carmack-level plan review via rp-cli
- `/flow:impl-review` → Carmack-level impl review (current branch)

## Marketplace rules
- Keep `marketplace.json` and each plugin's `plugin.json` in sync (name, version, description, author, homepage).
- Only include fields supported by Claude Code specs.
- `source` in marketplace must point at plugin root.

## Versioning
- Use semver.
- **Bump version** when skill/phase/agent/command files change (affects plugin behavior):
  - `plugins/<plugin>/skills/**/*.md`
  - `plugins/<plugin>/agents/**/*.md`
  - `plugins/<plugin>/commands/**/*.md`
- **Don't bump** for pure README/doc changes (users don't need update)
- When bumping, update:
  - `.claude-plugin/marketplace.json` → plugin version in plugins array
  - `plugins/<plugin>/.claude-plugin/plugin.json` → version

## Editing rules
- Keep prompts concise and direct.
- Avoid feature flags or backwards-compatibility scaffolding (plugins are pre-release).
- Do not add extra commands/agents/skills unless explicitly requested.

## Agent workflow (Ralph + RP)

Runbooks:
- `plans/ralph-e2e-notes.md`
- `plans/ralph-getting-started.md`

Tests:
```bash
plugins/flow-next/scripts/smoke_test.sh
plugins/flow-next/scripts/ralph_smoke_test.sh
```

RP smoke (RP 1.5.68+ auto-opens window with --create, or open manually on `${TEST_DIR}/repo`):
```bash
RP_SMOKE=1 TEST_DIR=/tmp/flow-next-ralph-smoke-rpN KEEP_TEST_DIR=1 \
  plugins/flow-next/scripts/ralph_smoke_rp.sh
```

Full RP e2e (RP 1.5.68+ auto-opens window with --create, or open manually on `${TEST_DIR}/repo`):
```bash
TEST_DIR=/tmp/flow-next-ralph-e2e-rpN KEEP_TEST_DIR=1 \
  plugins/flow-next/scripts/ralph_e2e_rp_test.sh
```

Short RP e2e (2 tasks, faster iteration):
```bash
CREATE=1 TEST_DIR=/tmp/flow-next-ralph-e2e-short-rpN \
  plugins/flow-next/scripts/ralph_e2e_short_rp_test.sh
# With RP 1.5.68+: windows auto-open. Older: open RP on test repo, re-run without CREATE
```

RP gotchas (must follow):
- Use `flowctl rp` wrappers only (no direct `rp-cli`).
- Resolve numeric window id via `flowctl rp pick-window --repo-root "$REPO_ROOT"` before builder.
- Do not call `flowctl rp builder` without `--window` and `--summary`.
- Write receipt JSON after chat returns when `REVIEW_RECEIPT_PATH` is set.

Debug envs (optional, Ralph only):
```bash
FLOW_RALPH_CLAUDE_MODEL=claude-opus-4-5-20251101
FLOW_RALPH_CLAUDE_DEBUG=hooks
FLOW_RALPH_CLAUDE_VERBOSE=1
FLOW_RALPH_CLAUDE_PERMISSION_MODE=bypassPermissions
FLOW_RALPH_CLAUDE_NO_SESSION_PERSISTENCE=1
```

### Developing with local changes

**Preferred: local marketplace install** (hooks work correctly):
```bash
# From this repo root
/plugin marketplace add ./
/plugin install flow-next@gmickel-claude-marketplace

# Test in any project - plugin hooks work via ${CLAUDE_PLUGIN_ROOT}
```

Uninstall global version first if installed: `claude plugins uninstall flow-next`

**Alternative: --plugin-dir** (test scripts only):

Bug #14410: Plugin hooks don't fire when using `--plugin-dir`. Subagents get `${CLAUDE_PLUGIN_ROOT}` literal instead of expanded path.

Test scripts (`ralph_smoke_test.sh`, `ralph_e2e_rp_test.sh`) handle this by copying hooks to `.claude/hooks/` in the test repo. This workaround is only needed for automated tests using `--plugin-dir`.

See `plans/ralph-e2e-notes.md` for full --plugin-dir hook setup if needed.

Logs:
- Ralph run logs: `scripts/ralph/runs/<run>/`
- Verbose log: `scripts/ralph/runs/<run>/ralph.log`
- Receipts: `scripts/ralph/runs/<run>/receipts/`
- Claude jsonl: `~/.claude/projects/**/<session_id>.jsonl`

## Release checklist (flow-next)

1. Update versions manually (no bump script yet):
   - `plugins/flow-next/.claude-plugin/plugin.json` → version
   - `.claude-plugin/marketplace.json` → flow-next version in plugins array
   - `plugins/flow-next/README.md` → Version badge
   - `README.md` → Flow-next badge
2. Update `CHANGELOG.md` with `[flow-next X.Y.Z]` entry
3. Validate JSON:
   ```bash
   jq . .claude-plugin/marketplace.json
   jq . plugins/flow-next/.claude-plugin/plugin.json
   ```
4. Commit, push, verify

## Release checklist (flow)

1. Run `./scripts/bump.sh <patch|minor|major> flow` (updates versions + README badges)
2. Update `CHANGELOG.md` with new version entry
3. Validate JSON:
   ```bash
   jq . .claude-plugin/marketplace.json
   jq . plugins/flow/.claude-plugin/plugin.json
   ```
4. Commit, push, verify

**Manual badge locations (if not using bump script):**
- `README.md` (Flow-vX.X.X badge)
- `plugins/flow/README.md` (Version-X.X.X badge)

## Contributing / Development

Before running tests or developing plugins locally:

```bash
# Uninstall marketplace plugins to avoid conflicts with local dev versions
claude plugins uninstall flow-next
claude plugins uninstall flow
```

Global installs take precedence over `--plugin-dir`, causing tests to use stale cached versions instead of your local changes.

## Repo metadata
- Author: Gordon Mickel (gordon@mickel.tech)
- Homepage: https://mickel.tech
- Marketplace repo: https://github.com/gmickel/gmickel-claude-marketplace

## Codex CLI Installation

Install flow or flow-next to OpenAI Codex:

```bash
# Install flow-next (recommended)
./scripts/install-codex.sh flow-next

# Or install flow
./scripts/install-codex.sh flow
```

**What gets installed:**
- `~/.codex/bin/flowctl` + `flowctl.py` - CLI tool
- `~/.codex/skills/` - Skill definitions (patched for Codex paths)
- `~/.codex/prompts/` - Command prompts
- `~/.codex/scripts/` - Helper scripts (worktree.sh)
- `~/.codex/templates/` - Ralph/setup templates

**Path patching:** All `${CLAUDE_PLUGIN_ROOT}` references are automatically replaced with `~/.codex` paths during install.

**Limitations:**
- Subagents won't run (Codex lacks Task tool)
- Hooks not supported
- Core `/flow-next:plan` and `/flow-next:work` commands work

**Usage in Codex:**
```bash
# Add to PATH (optional)
export PATH="$HOME/.codex/bin:$PATH"

# Use flowctl directly
~/.codex/bin/flowctl --help
```

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

**Rules:**
- Use `.flow/bin/flowctl` for ALL task tracking
- Do NOT create markdown TODOs or use TodoWrite
- Re-anchor (re-read spec + status) before every task

**More info:** `.flow/bin/flowctl --help` or read `.flow/usage.md`
<!-- END FLOW-NEXT -->
