#!/bin/bash
# Install Flow-Next into Cursor (~/.cursor/plugins/local) as a local plugin.
#
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/flow-next.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-cursor.sh \
#     && trash /tmp/flow-next-install
#
# Usage: ./scripts/install-cursor.sh [flow-next]
#
# Why a COPY (not a symlink): Cursor's plugin loader rejects a symlink whose
# realpath escapes ~/.cursor/ (the skill loader is laxer, but the plugin loader
# is not), so the plugin folder must physically live under ~/.cursor/plugins/local/.
# This script copies a snapshot — re-run it after `git pull` to update.
#
# What gets installed:
#   - Manifest:  .cursor-plugin/plugin.json   (commands path-override → commands/flow-next)
#   - Skills:    skills/<name>/SKILL.md        (Cursor default location)
#   - Commands:  commands/flow-next/*.md       (via the manifest override)
#   - Agents:    agents/*.md                   (Cursor default location)
#   - Hooks:     hooks/hooks.json              (loaded, but see the Ralph caveat below)
#   - flowctl:   scripts/flowctl[.py]          (resolved at runtime via .flow/bin after setup)
#
# Excludes the Codex mirror (codex/) and tests/ — not needed by Cursor.
#
# Caveats (cosmetic / known):
#   - Cursor registers the skills/commands/agents but does NOT show flow-next as a
#     grouped "plugin" card in the marketplace UI — the components still work.
#   - Ralph autonomous mode is NOT supported on Cursor: flow-next's hooks use Claude
#     Code's schema (PreToolUse/Stop + Bash|Execute matchers); Cursor's hook events
#     are afterFileEdit / beforeShellExecution, so the Ralph guard never fires.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PLUGIN="${1:-flow-next}"
if [ "$PLUGIN" != "flow-next" ]; then
    echo "Error: only 'flow-next' is supported (got '$PLUGIN')." >&2
    exit 1
fi

PLUGIN_DIR="$REPO_ROOT/plugins/$PLUGIN"
if [ ! -f "$PLUGIN_DIR/.cursor-plugin/plugin.json" ]; then
    echo "Error: $PLUGIN_DIR/.cursor-plugin/plugin.json not found." >&2
    echo "Run this from a flow-next checkout (the Cursor manifest must be present)." >&2
    exit 1
fi

DEST="$HOME/.cursor/plugins/local/$PLUGIN"

echo "Installing $PLUGIN into Cursor ($DEST)..."
mkdir -p "$HOME/.cursor/plugins/local"

# Real-dir copy (symlink is rejected by Cursor's plugin loader). --delete keeps
# the snapshot in lockstep with the source on re-run. Exclude the Codex mirror,
# tests, and Python/OS cruft.
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
        --exclude 'codex/' \
        --exclude 'tests/' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        --exclude '.DS_Store' \
        "$PLUGIN_DIR/" "$DEST/"
else
    # Fallback without rsync: clean + cp.
    rm -rf "$DEST"
    mkdir -p "$DEST"
    (cd "$PLUGIN_DIR" && tar --exclude='codex' --exclude='tests' \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
        -cf - .) | (cd "$DEST" && tar -xf -)
fi

echo ""
echo "Installed. Cursor registers the components on next launch:"
echo "  skills:   $(ls -d "$DEST"/skills/*/ 2>/dev/null | wc -l | tr -d ' ')"
echo "  commands: $(ls "$DEST"/commands/flow-next/*.md 2>/dev/null | wc -l | tr -d ' ')"
echo "  agents:   $(ls "$DEST"/agents/*.md 2>/dev/null | wc -l | tr -d ' ')"
echo ""
echo "Next steps:"
echo "  1. Fully restart Cursor (Cmd-Q, reopen) — a new local plugin needs a full restart."
echo "  2. In your project, run /flow-next:setup (writes .flow/bin/flowctl + AGENTS.md;"
echo "     skills resolve flowctl via .flow/bin since Cursor exposes no plugin-root env var)."
echo "  3. Drive the workflow by TYPING the commands — /flow-next:plan, /flow-next:work, ..."
echo "     (they run when typed even though the slash autocomplete under-lists them)."
echo ""
echo "Re-run this script after 'git pull' to update the snapshot."
echo "Uninstall: rm -rf \"$DEST\""
