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
# Windows: use the PowerShell sibling instead — scripts/install-cursor.ps1
#   (robocopy-based; same excludes + real-dir copy). Or run THIS script under
#   Git Bash / WSL, where ~/.cursor resolves the same.
#
# Why a COPY (not a symlink): Cursor's plugin loader rejects a symlink whose
# realpath escapes ~/.cursor/ (the skill loader is laxer, but the plugin loader
# is not), so the plugin folder must physically live under ~/.cursor/plugins/local/.
# This script copies a snapshot — re-run it after `git pull` to update.
#
# What gets installed:
#   - Manifest:  .cursor-plugin/plugin.json   (explicit skills/agents/commands/rules paths)
#   - Skills:    skills/<name>/SKILL.md        (via the manifest override)
#   - Commands:  commands/flow-next/*.md       (via the manifest override)
#   - Agents:    agents/*.md                   (via the manifest override)
#   - Rules:     rules/*.mdc                   (flow-next.mdc guidance rail)
#   - Hooks:     none shipped at plugin level (Ralph is opt-in via ralph-init project settings)
#   - flowctl:   scripts/flowctl[.py]          (resolved at runtime via .flow/bin after setup)
#
# Excludes the Codex mirror (codex/) and tests/ — not needed by Cursor.
#
# Team path: team-marketplace repo import is the RECOMMENDED install for orgs
# (admin imports the GitHub repo via the Cursor GitHub App; Default Off/On/Required;
# auto-refresh on push). This script is the individual / fallback path.
#
# Caveats (cosmetic / known):
#   - Local installs register skills/commands/agents; a grouped "plugin" card in
#     the marketplace UI is a team-marketplace concern — the components still work.
#   - Ralph autonomous mode is intentionally not built for Cursor (Cursor has a
#     full agent-hook set; flow-next does not register Ralph guards there).

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
# the snapshot in lockstep with the source on re-run; --delete-excluded ALSO
# removes excluded paths (e.g. a stale codex/ from an earlier full copy) from the
# dest — plain --delete only removes files absent from source, NOT excluded ones.
# Setup's Cursor-vs-Codex detection is a POSITIVE path check (PLUGIN_ROOT under
# ~/.cursor/) — not codex/ absence — so a leftover codex/ no longer misclassifies
# the install; still exclude the mirror (and tests) as unused weight.
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --delete-excluded \
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
echo "  rules:    $(ls "$DEST"/rules/*.mdc 2>/dev/null | wc -l | tr -d ' ')"
echo ""
echo "Next steps:"
echo "  1. Fully restart Cursor (Cmd-Q, reopen) — a new local plugin needs a full restart."
echo "  2. In your project, run /flow-next:setup (writes .flow/bin/flowctl + AGENTS.md;"
echo "     skills resolve flowctl via .flow/bin since Cursor exposes no plugin-root env var)."
echo "  3. Drive the workflow: type or pick from slash autocomplete — hyphenated form"
echo "     shown (/flow-next-plan); colon form also works when typed (/flow-next:plan)."
echo ""
echo "Note: for teams, team-marketplace repo import is the recommended path"
echo "      (admin imports the GitHub repo via the Cursor GitHub App); this script"
echo "      is the individual / fallback install."
echo ""
echo "Re-run this script after 'git pull' to update the snapshot."
echo "Uninstall: rm -rf \"$DEST\""
