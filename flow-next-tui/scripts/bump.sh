#!/usr/bin/env bash
# Bump flow-next-tui version
# Usage: ./scripts/bump.sh <patch|minor|major>

set -euo pipefail

cd "$(dirname "$0")/.."

BUMP_TYPE="${1:-}"

if [[ -z "$BUMP_TYPE" ]] || [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
  echo "Usage: $0 <patch|minor|major>"
  exit 1
fi

# Get current version
CURRENT=$(jq -r .version package.json)
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# Bump
case "$BUMP_TYPE" in
  patch) PATCH=$((PATCH + 1)) ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

# Update package.json
jq --arg v "$NEW_VERSION" '.version = $v' package.json > package.json.tmp
mv package.json.tmp package.json

echo "Bumped: $CURRENT -> $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  git add package.json"
echo "  git commit -m \"chore(tui): bump to $NEW_VERSION\""
echo "  git push origin main"
