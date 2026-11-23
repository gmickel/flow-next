#!/bin/sh
# Copy the Flow-Next (preview) plugin for hosts without a marketplace install:
# opencode, muse, or antigravity. Copies files unchanged; leaves tests behind.
set -eu

usage() {
    echo "Usage: $0 <opencode|muse|antigravity> [dest]" >&2
    exit 1
}

[ $# -ge 1 ] && [ $# -le 2 ] || usage
HOST="$1"
DEST="${2:-}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PLUGIN_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

case "$HOST" in
    opencode)
        [ -n "$DEST" ] || DEST="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
        COPY_MANIFEST=0
        ;;
    muse)
        [ -n "$DEST" ] || DEST="${XDG_CONFIG_HOME:-$HOME/.config}/muse"
        COPY_MANIFEST=0
        ;;
    antigravity)
        [ -n "$DEST" ] || DEST="$HOME/.gemini/config/plugins/flow"
        COPY_MANIFEST=1
        ;;
    -h|--help)
        usage
        ;;
    *)
        echo "Unknown host: $HOST" >&2
        usage
        ;;
esac

mkdir -p "$DEST/skills"
rm -rf "$DEST/skills/flow" "$DEST/scripts" "$DEST/templates"
cp -Rp "$PLUGIN_DIR/skills/flow" "$DEST/skills/flow"
cp -Rp "$PLUGIN_DIR/scripts" "$DEST/scripts"
cp -Rp "$PLUGIN_DIR/templates" "$DEST/templates"
if [ "$COPY_MANIFEST" -eq 1 ]; then
    cp -p "$PLUGIN_DIR/plugin.json" "$DEST/plugin.json"
fi

find "$DEST" \( -name '__pycache__' -o -name '*.pyc' -o -name '.DS_Store' \) -prune -exec rm -rf {} +

echo "Copied flow plugin for $HOST to $DEST"
