#!/bin/bash
# Install Flow-Next into Codex CLI (~/.codex) using pre-built files.
#
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/gmickel-claude-marketplace.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-codex.sh flow-next \
#     && trash /tmp/flow-next-install
#
# Usage: ./scripts/install-codex.sh <flow|flow-next>
#
# What gets installed (from pre-built codex/ directory):
#   - Skills:    codex/skills/             → ~/.codex/skills/
#   - Agents:    codex/agents/*.toml       → ~/.codex/agents/
#   - Hooks:     codex/hooks.json          → ~/.codex/hooks.json
#   - Prompts:   commands/flow-next/*.md   → ~/.codex/prompts/
#   - CLI tools: flowctl, flowctl.py       → ~/.codex/scripts/
#   - Scripts:   worktree.sh              → ~/.codex/scripts/  (from codex/skills/)
#   - Templates: ralph-init templates      → ~/.codex/templates/
#   - Manifest:  .codex-plugin/plugin.json → ~/.codex/plugin.json
#   - Config:    agent entries             → ~/.codex/config.toml (merged)
#
# All path patching and agent conversion is done at build time by sync-codex.sh.
# This script just copies pre-built files and merges config.toml.
#
# Requires Codex CLI 0.102.0+ for multi-agent role support.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CODEX_DIR="$HOME/.codex"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse argument
PLUGIN="${1:-}"
if [ -z "$PLUGIN" ]; then
    echo -e "${RED}Error: Plugin name required${NC}"
    echo "Usage: $0 <flow|flow-next>"
    exit 1
fi

if [ "$PLUGIN" = "flow" ]; then
    echo -e "${RED}Error: 'flow' plugin does not have pre-built Codex files.${NC}"
    echo "Use 'flow-next' instead."
    exit 1
fi

if [ "$PLUGIN" != "flow-next" ]; then
    echo -e "${RED}Error: Invalid plugin '$PLUGIN'${NC}"
    echo "Usage: $0 <flow|flow-next>"
    exit 1
fi

PLUGIN_DIR="$REPO_ROOT/plugins/$PLUGIN"
CODEX_SRC="$PLUGIN_DIR/codex"

# Validate source directories exist
if [ ! -d "$CODEX_SRC" ]; then
    echo -e "${RED}Error: Pre-built codex/ directory not found at $CODEX_SRC${NC}"
    echo "Run scripts/sync-codex.sh first to generate it."
    exit 1
fi

if [ ! -d "$CODEX_DIR" ]; then
    echo -e "${RED}Error: ~/.codex not found. Is Codex CLI installed?${NC}"
    exit 1
fi

echo "Installing $PLUGIN to Codex CLI (multi-agent mode)..."
echo

# Create target directories
mkdir -p "$CODEX_DIR/skills" "$CODEX_DIR/agents" "$CODEX_DIR/scripts" \
         "$CODEX_DIR/prompts" "$CODEX_DIR/templates"

# ====================
# Skills (pre-patched)
# ====================
SKILL_COUNT=0
for skill_dir in "$CODEX_SRC/skills/"*/; do
    [ -d "$skill_dir" ] || continue
    rm -rf "$CODEX_DIR/skills/$(basename "$skill_dir")"
    cp -r "${skill_dir%/}" "$CODEX_DIR/skills/"
    SKILL_COUNT=$((SKILL_COUNT + 1))
done
echo -e "${GREEN}✓${NC} $SKILL_COUNT skills"

# ====================
# Agents (pre-built .toml)
# ====================
# Clean old auto-generated agents
grep -rl "Auto-generated.*sync-codex\|Auto-generated from.*\.md.*do not edit" "$CODEX_DIR/agents/"*.toml 2>/dev/null | xargs rm -f 2>/dev/null || true

AGENT_COUNT=0
for toml_file in "$CODEX_SRC/agents/"*.toml; do
    [ -f "$toml_file" ] || continue
    cp "$toml_file" "$CODEX_DIR/agents/"
    AGENT_COUNT=$((AGENT_COUNT + 1))
done
echo -e "${GREEN}✓${NC} $AGENT_COUNT agents"

# ====================
# Hooks
# ====================
if [ -f "$CODEX_SRC/hooks.json" ]; then
    cp "$CODEX_SRC/hooks.json" "$CODEX_DIR/hooks.json"
    echo -e "${GREEN}✓${NC} hooks.json"
fi

# ====================
# CLI tools → ~/.codex/scripts/
# ====================
HAS_FLOWCTL=false
if [ -f "$PLUGIN_DIR/scripts/flowctl" ]; then
    cp "$PLUGIN_DIR/scripts/flowctl" "$CODEX_DIR/scripts/"
    chmod +x "$CODEX_DIR/scripts/flowctl"
    HAS_FLOWCTL=true
fi
if [ -f "$PLUGIN_DIR/scripts/flowctl.py" ]; then
    cp "$PLUGIN_DIR/scripts/flowctl.py" "$CODEX_DIR/scripts/"
fi
[ "$HAS_FLOWCTL" = true ] && echo -e "${GREEN}✓${NC} flowctl → ~/.codex/scripts/"

# Clean up old bin/ location
if [ -f "$CODEX_DIR/bin/flowctl" ]; then
    rm -f "$CODEX_DIR/bin/flowctl" "$CODEX_DIR/bin/flowctl.py"
    echo -e "${YELLOW}→${NC} removed old ~/.codex/bin/flowctl (moved to scripts/)"
fi

# ====================
# Templates (ralph-init)
# ====================
if [ -d "$CODEX_SRC/skills/flow-next-ralph-init/templates" ]; then
    rm -rf "$CODEX_DIR/templates/flow-next-ralph-init"
    cp -r "$CODEX_SRC/skills/flow-next-ralph-init/templates" "$CODEX_DIR/templates/flow-next-ralph-init"
    chmod +x "$CODEX_DIR/templates/flow-next-ralph-init/"*.sh 2>/dev/null || true
    chmod +x "$CODEX_DIR/templates/flow-next-ralph-init/"*.py 2>/dev/null || true
    echo -e "${GREEN}✓${NC} ralph-init templates"
fi

# ====================
# Plugin manifest
# ====================
if [ -f "$PLUGIN_DIR/.codex-plugin/plugin.json" ]; then
    cp "$PLUGIN_DIR/.codex-plugin/plugin.json" "$CODEX_DIR/plugin.json"
    echo -e "${GREEN}✓${NC} plugin.json"
fi

# ====================
# Prompts (commands → prompts, no patching needed)
# ====================
PROMPT_COUNT=0
for cmd in "$PLUGIN_DIR/commands/$PLUGIN/"*.md; do
    [ -f "$cmd" ] || continue
    cp "$cmd" "$CODEX_DIR/prompts/"
    PROMPT_COUNT=$((PROMPT_COUNT + 1))
done
echo -e "${GREEN}✓${NC} $PROMPT_COUNT prompts"

# ====================
# Config.toml (merge agent entries + features)
# ====================
echo -e "${BLUE}Merging config.toml...${NC}"
CONFIG="$CODEX_DIR/config.toml"

# Ensure multi_agent = true at TOML root
if [ -f "$CONFIG" ]; then
    if ! grep -q "^multi_agent" "$CONFIG" 2>/dev/null; then
        tmp="/tmp/codex-config-prepend.toml"
        { echo "# Enable custom multi-agent roles (Codex 0.102.0+)"
          echo "multi_agent = true"
          echo ""
          cat "$CONFIG"
        } > "$tmp"
        mv "$tmp" "$CONFIG"
    fi
else
    { echo "# Enable custom multi-agent roles (Codex 0.102.0+)"
      echo "multi_agent = true"
      echo ""
    } > "$CONFIG"
fi

# Clean old flow-next entries
if grep -q "flow-next multi-agent roles" "$CONFIG" 2>/dev/null; then
    sed -i.bak '/# --- flow-next multi-agent roles/,/# --- end flow-next roles ---/d' "$CONFIG"
    rm -f "${CONFIG}.bak"
fi

# Clean old max_threads we may have written
if grep -q "^max_threads" "$CONFIG" 2>/dev/null; then
    sed -i.bak '/^max_threads/d' "$CONFIG"
    rm -f "${CONFIG}.bak"
fi

# Clean old [features] section we may have written
if grep -q "# --- flow-next features" "$CONFIG" 2>/dev/null; then
    sed -i.bak '/# --- flow-next features/,/# --- end flow-next features ---/d' "$CONFIG"
    rm -f "${CONFIG}.bak"
fi

# Generate agent + feature entries
CODEX_MAX_THREADS="${CODEX_MAX_THREADS:-12}"
{
    echo ""
    echo "# --- flow-next features (auto-generated) ---"
    echo "[features]"
    echo "codex_hooks = true"
    echo "# --- end flow-next features ---"
    echo ""
    echo "# --- flow-next multi-agent roles (auto-generated) ---"
    echo "# Re-run install-codex.sh to regenerate"
    echo ""

    # Only declare [agents] if it doesn't already exist
    if ! grep -q "^\[agents\]" "$CONFIG" 2>/dev/null; then
        echo "[agents]"
    fi
    echo "max_threads = $CODEX_MAX_THREADS"
    echo ""

    for toml_file in "$CODEX_SRC/agents/"*.toml; do
        [ -f "$toml_file" ] || continue
        name=$(basename "$toml_file" .toml)
        role_key="${name//-/_}"
        desc=$(grep '^description = ' "$toml_file" | head -1 | sed 's/^description = "//;s/"$//')
        echo "[agents.$role_key]"
        echo "description = \"$desc\""
        echo "config_file = \"agents/$name.toml\""
        echo ""
    done

    echo "# --- end flow-next roles ---"
} >> "$CONFIG"

echo -e "  ${GREEN}✓${NC} config.toml ($AGENT_COUNT agent entries, max_threads=$CODEX_MAX_THREADS)"
echo -e "  ${GREEN}✓${NC} [features] codex_hooks = true"

# ====================
# Summary
# ====================
echo
echo -e "${GREEN}Done!${NC} $PLUGIN installed to ~/.codex"
echo "  $SKILL_COUNT skills, $AGENT_COUNT agents, $PROMPT_COUNT prompts"
[ "$HAS_FLOWCTL" = true ] && echo "  flowctl: ~/.codex/scripts/flowctl"
echo "  hooks: ~/.codex/hooks.json"
echo "  config: ~/.codex/config.toml (merged, max_threads=$CODEX_MAX_THREADS)"
echo
echo -e "${YELLOW}Requires Codex CLI 0.102.0+${NC}"
echo "  /$PLUGIN:plan  — create a plan"
echo "  /$PLUGIN:work  — execute tasks"
