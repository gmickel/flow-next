End-to-end validation of both platforms after all changes.

## Claude Code validation

1. Install the plugin locally:
   ```bash
   # From repo root
   /plugin marketplace add ./
   /plugin install flow-next@gmickel-claude-marketplace
   ```

2. Verify in a test project:
   - `/flow-next:setup` works
   - `/flow-next:plan "add a hello endpoint"` works (scouts spawn via Task tool)
   - Skills reference `${CLAUDE_PLUGIN_ROOT}/scripts/flowctl` correctly
   - Hooks fire on Bash/Edit/Write (if Ralph mode)
   - No references to Codex-specific patterns leaked into Claude Code skills

3. Verify no regressions:
   - All 16 skills load
   - All 20 agents available via Task tool
   - Commands work: plan, work, interview, impl-review, plan-review, epic-review, prime, setup, sync

## Codex validation (install-codex.sh)

1. Run simplified install:
   ```bash
   ./scripts/install-codex.sh flow-next
   ```

2. Verify installed files:
   - `~/.codex/skills/` has 16 skill dirs
   - `~/.codex/agents/` has 20 .toml files
   - `~/.codex/scripts/flowctl` exists and is executable
   - `~/.codex/hooks.json` exists
   - `~/.codex/config.toml` has agent entries + `codex_hooks = true`

3. Verify no stale artifacts:
   - No `~/.codex/bin/flowctl` (moved to scripts/)
   - No runtime-converted .toml files mixed with pre-built ones

## Codex validation (native plugin)

1. Verify plugin discoverability:
   - `.codex-plugin/plugin.json` is valid JSON with correct version
   - `.agents/plugins/marketplace.json` is valid JSON
   - If codex-plugin-scanner available: `pipx run codex-plugin-scanner lint plugins/flow-next`

2. Verify skills in codex/:
   - All 16 skill dirs present in codex/skills/
   - No bare `${CLAUDE_PLUGIN_ROOT}` without fallback
   - No `Task flow-next:` invocation patterns (should use agent roles)
   - RP review skills have DO NOT RETRY warnings
   - agents-md-scout referenced (not claude-md-scout)

3. Verify agents in codex/:
   - All 20 .toml files parse correctly
   - Model mapping correct (gpt-5.4, gpt-5.4-mini, inherited)
   - Scouts have sandbox_mode = "read-only"
   - Worker has sandbox_mode = "workspace-write"
   - Scouts have nickname_candidates

4. Verify hooks in codex/:
   - Valid JSON
   - Only Bash matcher for PreToolUse/PostToolUse
   - No SubagentStop event
   - Has SessionStart hook

## Cross-platform consistency

- Both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` have same version
- Plugin name is "flow-next" in both
- Skills cover same functionality (16 each, different invocation patterns)
- Agents cover same 20 roles

## bump.sh validation

1. Run: `./scripts/bump.sh patch flow-next` (dry run or on branch)
2. Verify both manifests updated
3. Verify sync-codex.sh ran
4. Verify codex/ directory regenerated with new version

## Acceptance criteria
- [ ] Claude Code plugin installs and works (no regressions)
- [ ] install-codex.sh produces correct output
- [ ] Native Codex plugin structure validates
- [ ] codex-plugin-scanner passes (if available)
- [ ] Cross-platform version consistency
- [ ] bump.sh updates both platforms
- [ ] Smoke test: plan + work cycle runs on Claude Code
