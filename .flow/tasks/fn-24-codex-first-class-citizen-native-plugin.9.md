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

## Done summary
# End-to-end validation of both platforms

All validation checks passed.

## Codex plugin structure
- `.codex-plugin/plugin.json`: valid JSON, name=flow-next, version=0.26.1
- `.agents/plugins/marketplace.json`: valid JSON
- `codex/skills/`: 16 dirs (matches canonical)
- `codex/agents/`: 20 .toml files (matches canonical)
- `codex/hooks.json`: valid JSON

## Codex skills patches
- No bare `${CLAUDE_PLUGIN_ROOT}` without fallback
- No `Task flow-next:` patterns (all converted to agent roles)
- `claude-md-scout` renamed to `agents-md-scout` everywhere (only provenance comment remains)
- RP review skills have DO NOT RETRY warnings

## Codex agents
- All 20 .toml files parse (tomli)
- Scouts: sandbox_mode=read-only, have nickname_candidates
- Worker: sandbox_mode=workspace-write
- plan-sync: sandbox_mode=workspace-write
- Model mapping: gpt-5.4 for intelligent (opus/smart scouts), gpt-5.4-mini for fast scouts

## No Claude Code regressions
- `skills/`: only expected additions/modifications from task .7 (setup skill)
- `agents/`: unchanged
- `.claude-plugin/marketplace.json`: unchanged
- `hooks/hooks.json`: unchanged

## Cross-platform consistency
- Both plugin.json files: name=flow-next, version=0.26.1
- 16 skills each, 20 agents each

## Script validation
- `bash -n scripts/install-codex.sh`: syntax OK
- `bash -n scripts/bump.sh`: syntax OK
- `sync-codex.sh`: idempotent (no diff after re-run)

## Hooks structure
- Events: PreToolUse, PostToolUse, Stop
- No SubagentStop (correctly dropped)
- Matchers: Bash|Execute (cross-platform)
## Evidence
- Commits:
- Tests:
- PRs:
## Acceptance criteria
- [ ] Claude Code plugin installs and works (no regressions)
- [ ] install-codex.sh produces correct output
- [ ] Native Codex plugin structure validates
- [ ] codex-plugin-scanner passes (if available)
- [ ] Cross-platform version consistency
- [ ] bump.sh updates both platforms
- [ ] Smoke test: plan + work cycle runs on Claude Code
