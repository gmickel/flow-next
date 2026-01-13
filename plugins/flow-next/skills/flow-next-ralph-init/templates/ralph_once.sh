#!/usr/bin/env bash
# Human-in-the-loop Ralph: runs exactly one iteration
# Use this to observe behavior before going fully autonomous

set -euo pipefail

# Portable realpath (same as ralph.sh)
_portable_realpath() {
  local path="$1"
  if readlink -f "$path" 2>/dev/null; then
    return
  elif command -v greadlink >/dev/null 2>&1; then
    greadlink -f "$path"
  elif command -v realpath >/dev/null 2>&1; then
    realpath "$path"
  else
    python3 -c "import os; print(os.path.realpath('$path'))"
  fi
}

# Resolve script directory (follows symlinks for user-level mode)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -L "$0" ]]; then
  SCRIPT_DIR="$(dirname "$(_portable_realpath "$0")")"
fi

export MAX_ITERATIONS=1
exec "$SCRIPT_DIR/ralph.sh" "$@"
