#!/usr/bin/env bash
# Human-in-the-loop Ralph: runs exactly one iteration
# Use this to observe behavior before going fully autonomous

set -euo pipefail

# Resolve script directory (follows symlinks for user-level mode)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -L "$0" ]]; then
  SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
fi

export MAX_ITERATIONS=1
exec "$SCRIPT_DIR/ralph.sh" "$@"
