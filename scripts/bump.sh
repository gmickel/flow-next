#!/usr/bin/env bash
set -euo pipefail

# Bump versions in marketplace and/or plugin manifests
# Usage: ./scripts/bump.sh <patch|minor|major> [marketplace|flow|all]

BUMP_TYPE="${1:-}"
TARGET="${2:-all}"

MARKETPLACE=".claude-plugin/marketplace.json"
PLUGIN_FLOW="plugins/flow/.claude-plugin/plugin.json"
PLUGIN_FLOW_NEXT="plugins/flow-next/.claude-plugin/plugin.json"

bump_semver() {
  local version="$1"
  local type="$2"
  local major minor patch
  IFS='.' read -r major minor patch <<< "$version"

  case "$type" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "$major.$((minor + 1)).0" ;;
    patch) echo "$major.$minor.$((patch + 1))" ;;
    *) echo "$version" ;;
  esac
}

if [[ -z "$BUMP_TYPE" ]] || [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
  echo "Usage: $0 <patch|minor|major> [marketplace|flow|flow-next|all]"
  echo "  marketplace - bump marketplace version only"
  echo "  flow        - bump flow plugin version"
  echo "  flow-next   - bump flow-next plugin version"
  echo "  all         - bump all versions (default)"
  exit 1
fi

if [[ "$TARGET" == "marketplace" || "$TARGET" == "all" ]]; then
  OLD=$(jq -r '.metadata.version' "$MARKETPLACE")
  NEW=$(bump_semver "$OLD" "$BUMP_TYPE")
  jq --arg v "$NEW" '.metadata.version = $v' "$MARKETPLACE" > tmp.json && mv tmp.json "$MARKETPLACE"
  echo "marketplace: $OLD -> $NEW"
fi

if [[ "$TARGET" == "flow" || "$TARGET" == "all" ]]; then
  OLD=$(jq -r '.version' "$PLUGIN_FLOW")
  NEW=$(bump_semver "$OLD" "$BUMP_TYPE")

  # Update plugin.json
  jq --arg v "$NEW" '.version = $v' "$PLUGIN_FLOW" > tmp.json && mv tmp.json "$PLUGIN_FLOW"

  # Update marketplace.json flow plugin version
  jq --arg v "$NEW" '(.plugins[] | select(.name == "flow")).version = $v' "$MARKETPLACE" > tmp.json && mv tmp.json "$MARKETPLACE"

  # Update version badges in READMEs
  sed -i '' "s/Flow-v[0-9]*\.[0-9]*\.[0-9]*/Flow-v$NEW/" README.md
  sed -i '' "s/Version-[0-9]*\.[0-9]*\.[0-9]*/Version-$NEW/" plugins/flow/README.md

  echo "flow: $OLD -> $NEW"
fi

if [[ "$TARGET" == "flow-next" || "$TARGET" == "all" ]]; then
  OLD=$(jq -r '.version' "$PLUGIN_FLOW_NEXT")
  NEW=$(bump_semver "$OLD" "$BUMP_TYPE")

  # Update plugin.json
  jq --arg v "$NEW" '.version = $v' "$PLUGIN_FLOW_NEXT" > tmp.json && mv tmp.json "$PLUGIN_FLOW_NEXT"

  # Update marketplace.json flow-next plugin version
  jq --arg v "$NEW" '(.plugins[] | select(.name == "flow-next")).version = $v' "$MARKETPLACE" > tmp.json && mv tmp.json "$MARKETPLACE"

  # Update marketplace metadata version to match (required for auto-updates)
  jq --arg v "$NEW" '.metadata.version = $v' "$MARKETPLACE" > tmp.json && mv tmp.json "$MARKETPLACE"

  # Update version badges in READMEs
  sed -i '' "s/Flow--next-v[0-9]*\.[0-9]*\.[0-9]*/Flow--next-v$NEW/" README.md
  sed -i '' "s/Version-[0-9]*\.[0-9]*\.[0-9]*/Version-$NEW/" plugins/flow-next/README.md

  echo "flow-next: $OLD -> $NEW"
  echo "marketplace: -> $NEW (synced)"
fi

echo "done"
