Simplify `scripts/install-codex.sh` to use pre-built `codex/` files instead of runtime conversion.

## Current state (785 lines)
The script currently:
1. Copies skills and patches all paths at runtime
2. Converts agents .md → .toml at runtime (YAML frontmatter parsing in bash)
3. Patches flow-next-work, flow-next-plan, flow-next-prime for Codex invocation patterns
4. Adds RP review warnings
5. Generates config.toml entries
6. Copies flowctl, scripts, templates

## Target state (~200 lines)
With pre-built `codex/` directory (from sync-codex.sh), the script becomes:
1. Copy `codex/skills/` → `~/.codex/skills/` (pre-patched, no runtime conversion)
2. Copy `codex/agents/` → `~/.codex/agents/` (pre-built .toml, no conversion)
3. Copy `codex/hooks.json` → `~/.codex/hooks.json`
4. Copy flowctl → `~/.codex/scripts/flowctl` (NOTE: changed from bin/ to scripts/ for path consistency)
5. Copy flowctl.py → `~/.codex/scripts/flowctl.py`
6. Copy worktree.sh → `~/.codex/scripts/`
7. Copy templates → `~/.codex/templates/`
8. Copy plugin.json → `~/.codex/plugin.json` (from .codex-plugin/plugin.json now)
9. Merge config.toml (agent entries + max_threads + multi_agent + hooks feature flag)

## Config.toml changes

### Keep from current script:
- `multi_agent = true` at root
- `[agents]` section with `max_threads`
- `[agents.X]` sub-tables for each agent (description + config_file)
- Clean old flow-next entries before adding new ones

### Add new:
- `[features]` section with `codex_hooks = true` (enables hook system)

### Update agent entries:
- Read name + description from pre-built .toml files (no more MD parsing)
- Point `config_file` at `agents/<name>.toml`

## flowctl path change

**IMPORTANT:** Move flowctl from `~/.codex/bin/` to `~/.codex/scripts/` so the path pattern `${ROOT}/scripts/flowctl` is consistent:
- Claude Code: `${CLAUDE_PLUGIN_ROOT}/scripts/flowctl` ✓
- Droid: `${DROID_PLUGIN_ROOT}/scripts/flowctl` ✓  
- Codex: `$HOME/.codex/scripts/flowctl` ✓

Keep backward compat: if `~/.codex/bin/flowctl` exists, remove it (or symlink to new location).

## What to remove from the script
- `patch_for_codex()` function — pre-patched in codex/skills/
- `convert_agent_to_toml()` function — pre-built in codex/agents/
- `patch_work_for_codex_agents()` — pre-patched
- `patch_plan_for_codex_agents()` — pre-patched
- `patch_prime_for_codex_agents()` — pre-patched
- `patch_rp_review_skills_for_codex()` — pre-patched
- `rename_agent_for_codex()` — pre-renamed
- `patch_agent_body_for_codex()` — pre-patched
- `map_model_to_codex()` — pre-mapped
- `model_supports_reasoning()` — pre-configured
- Model mapping env vars (CODEX_MODEL_INTELLIGENT, etc.) — baked into pre-built files

## What to keep
- Argument parsing (flow|flow-next)
- Directory creation
- Config.toml merging logic (generate_config_entries — simplified to read from .toml)
- Summary output
- Color output helpers

## Self-bootstrapping one-liner

Add a comment at the top of the script with the zero-clone install command:
```bash
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/gmickel-claude-marketplace.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-codex.sh flow-next \
#     && trash /tmp/flow-next-install
```

## Acceptance criteria
- [ ] Script is under 200 lines
- [ ] No runtime MD→TOML conversion
- [ ] No runtime skill patching
- [ ] flowctl installed to ~/.codex/scripts/ (not bin/)
- [ ] config.toml has [features] codex_hooks = true
- [ ] config.toml agent entries read from pre-built .toml files
- [ ] Old ~/.codex/bin/flowctl cleaned up (symlink or remove)
- [ ] Output summary shows installed components
- [ ] One-liner install comment at top of script
- [ ] Still works for both `flow` and `flow-next` arguments (flow falls back to old behavior or errors gracefully)
