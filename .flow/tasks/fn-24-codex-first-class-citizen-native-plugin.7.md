Update the setup skill (`/flow-next:setup`) to detect Codex and configure project-scoped agents and hooks.

## Background

When a Codex user installs the native plugin and runs setup, the skill should:
1. Copy flowctl to `.flow/bin/` (existing behavior, works on all platforms)
2. **NEW:** Detect Codex environment and copy agents + hooks to project-scoped locations:
   - Agent .toml files → `.codex/agents/` (project-scoped custom agents)
   - hooks.json → `.codex/hooks.json` (project-scoped hooks)
3. Update AGENTS.md (Codex equivalent of CLAUDE.md) with flow-next instructions

## Codex detection

Check for Codex environment:
```bash
# Codex sets these, Claude Code doesn't
if command -v codex &>/dev/null || [ -d "$HOME/.codex" ]; then
  PLATFORM="codex"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  PLATFORM="claude-code"
elif [ -n "${DROID_PLUGIN_ROOT:-}" ]; then
  PLATFORM="droid"
fi
```

## Changes to setup skill

### In the SKILL.md instructions:

Add a platform detection step early in the workflow:

```
## Platform detection

Detect which platform is running:
- If `${CLAUDE_PLUGIN_ROOT}` is set → Claude Code
- If `${DROID_PLUGIN_ROOT}` is set → Factory Droid
- Otherwise → Codex (or standalone)

For Codex:
1. Copy pre-built agent configs to project: `.codex/agents/`
   Source: `${PLUGIN_ROOT}/codex/agents/*.toml` (from native plugin cache)
   Or: `$HOME/.codex/agents/*.toml` (from install-codex.sh)
   Target: `.codex/agents/` in the project
2. Copy hooks: `${PLUGIN_ROOT}/codex/hooks.json` → `.codex/hooks.json`
3. Add `[features] codex_hooks = true` to `.codex/config.toml` if not present
4. Use AGENTS.md instead of CLAUDE.md for project instructions
```

### In the setup templates:

The setup templates (used by the skill to generate CLAUDE.md/AGENTS.md content) should:
- Detect platform and use the right filename (CLAUDE.md vs AGENTS.md)
- For Codex, mention `$flow-next-plan` instead of `/flow-next:plan`
- For Codex, mention agent roles instead of Task tool

## Scope

This task modifies the **canonical** setup skill (not just the codex/ copy), since the platform detection should work everywhere. The sync-codex.sh script will then propagate the changes to codex/skills/.

## Acceptance criteria
- [ ] Setup skill detects Codex platform
- [ ] On Codex, copies agent .toml files to `.codex/agents/`
- [ ] On Codex, copies hooks.json to `.codex/hooks.json`
- [ ] On Codex, updates AGENTS.md (not CLAUDE.md)
- [ ] On Claude Code / Droid, behavior unchanged
- [ ] After setup on Codex, project-scoped agents are discoverable by Codex

## Done summary
Updated setup skill with Codex platform detection and project-scoped agent/hooks copying.
## Evidence
- Commits:
- Tests: smoke_test.sh (52/52 pass), sync-codex.sh validation (all checks pass)
- PRs: