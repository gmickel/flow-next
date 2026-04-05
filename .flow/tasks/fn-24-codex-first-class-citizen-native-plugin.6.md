Update `scripts/bump.sh` to handle dual manifests and trigger codex sync.

## Current behavior
bump.sh updates:
- `.claude-plugin/marketplace.json` → plugin version in plugins array
- `plugins/<plugin>/.claude-plugin/plugin.json` → version field

## New behavior
bump.sh must also update:
- `plugins/<plugin>/.codex-plugin/plugin.json` → version field (if exists)
- `.agents/plugins/marketplace.json` → no version field to update (marketplace itself is versionless), but verify plugin entry exists

After bumping versions, automatically run `scripts/sync-codex.sh` to regenerate `codex/` with updated version references.

## Changes needed

1. After updating `.claude-plugin/plugin.json`, check if `.codex-plugin/plugin.json` exists in the same plugin directory
2. If it does, update its `version` field to the same new version
3. After all version bumps, run `scripts/sync-codex.sh` if the plugin has a `codex/` directory
4. Print confirmation of Codex manifest update

## Acceptance criteria
- [ ] Bumping flow-next updates both .claude-plugin/plugin.json AND .codex-plugin/plugin.json
- [ ] Both manifests have identical version after bump
- [ ] sync-codex.sh runs automatically after bump
- [ ] Bumping flow (which has no .codex-plugin/) doesn't error
- [ ] Script output shows both manifest updates
