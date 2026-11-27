#!/bin/sh
# Copy the self-contained Flow-Next One (preview) skill folder for hosts without a
# marketplace install: opencode, muse, antigravity, or pi. Leaves shared
# directories untouched.
set -eu

usage() {
    echo "Usage: $0 <opencode|muse|antigravity|pi> [dest]" >&2
    exit 1
}

[ $# -ge 1 ] && [ $# -le 2 ] || usage
HOST="$1"
DEST="${2:-}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PLUGIN_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

case "$HOST" in
    opencode)    [ -n "$DEST" ] || DEST="${XDG_CONFIG_HOME:-$HOME/.config}/opencode" ;;
    muse)        [ -n "$DEST" ] || DEST="${XDG_CONFIG_HOME:-$HOME/.config}/muse" ;;
    antigravity) [ -n "$DEST" ] || DEST="$HOME/.gemini/config/plugins/flow" ;;
    pi)          [ -n "$DEST" ] || DEST="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" ;;
    -h|--help)   usage ;;
    *)           echo "Unknown host: $HOST" >&2; usage ;;
esac

mkdir -p "$DEST/skills"
rm -rf "$DEST/skills/flow"
cp -Rp "$PLUGIN_DIR/skills/flow" "$DEST/skills/flow"
find "$DEST/skills/flow" \( -name '__pycache__' -o -name '*.pyc' -o -name '.DS_Store' \) -prune -exec rm -rf {} +

if [ "$HOST" = "antigravity" ]; then
    cp -p "$PLUGIN_DIR/plugin.json" "$DEST/plugin.json"
fi

echo "Copied flow skill for $HOST to $DEST/skills/flow"
