# Release process

Steps to ship a new version of either plugin in this marketplace.

## When to bump

- **Bump version** when skill / phase / agent / command files change (affects plugin behavior):
  - `plugins/<plugin>/skills/**/*.md`
  - `plugins/<plugin>/agents/**/*.md`
  - `plugins/<plugin>/commands/**/*.md`
- **Don't bump** for pure README / docs / agent_docs changes (users don't need an update).
- Use semver. Major (1.0+) requires breaking-change documentation in CHANGELOG.

## Files kept in sync

`scripts/bump.sh` handles all three; verify with `jq` after running:

- `.claude-plugin/marketplace.json` — plugin version inside the `plugins[]` array
- `plugins/<plugin>/.claude-plugin/plugin.json` — version
- `plugins/<plugin>/.codex-plugin/plugin.json` — version (flow-next only)

## Marketplace rules

- Keep `marketplace.json` and each plugin's `plugin.json` in sync (name, version, description, author, homepage).
- Only include fields supported by Claude Code specs.
- `source` in marketplace must point at plugin root.

## flow-next release

```bash
./scripts/bump.sh <patch|minor|major> flow-next   # 1. bump versions
./scripts/sync-codex.sh                            # 2. regenerate Codex mirror
jq . plugins/flow-next/.codex-plugin/plugin.json   # 3. verify version
# 4. update CHANGELOG.md with [flow-next X.Y.Z] entry

git add -A && git commit -m "chore(flow-next): bump version to X.Y.Z"
git push

git tag flow-next-vX.Y.Z && git push origin flow-next-vX.Y.Z   # triggers release + Discord
```

## flow release

```bash
./scripts/bump.sh <patch|minor|major> flow   # 1. bump versions + README badges
# 2. update CHANGELOG.md with new version entry
jq . .claude-plugin/marketplace.json
jq . plugins/flow/.claude-plugin/plugin.json
# 3. commit, push, verify
```

**Manual badge locations** (if not using `bump.sh`):
- `README.md` (Flow-vX.X.X badge)
- `plugins/flow/README.md` (Version-X.X.X badge)
