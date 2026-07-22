#!/bin/bash
# Install Flow-Next into Codex CLI (~/.codex) using pre-built files.
#
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/flow-next.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-codex.sh \
#     && trash /tmp/flow-next-install
#
# Usage: ./scripts/install-codex.sh [flow-next]
#
# (The plugin name is optional and defaults to flow-next — kept for backward
# compatibility with older one-liners. The legacy `flow` plugin was removed
# in flow-next 1.0.2.)
#
# What gets installed (from pre-built codex/ directory):
#   - Skills:    codex/skills/             → ~/.codex/skills/
#   - Agents:    codex/agents/*.toml       → ~/.codex/agents/
#   - Hooks:     none by default (fn-114). Ralph guard is opt-in via
#                /flow-next:ralph-init → project .codex/hooks.json
#   - Prompts:   commands/*.md             → ~/.codex/prompts/
#   - CLI tools: flowctl, flowctl.py       → ~/.codex/scripts/
#   - Scripts:   worktree.sh              → ~/.codex/scripts/  (from codex/skills/)
#   - Templates: ralph-init templates      → ~/.codex/templates/
#   - References: codex/references/*.md    → ~/.codex/references/
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

# Plugin is fixed to flow-next; the optional positional arg is accepted for
# backward compatibility with old one-liners that passed `flow-next` explicitly.
PLUGIN="${1:-flow-next}"
if [ "$PLUGIN" != "flow-next" ]; then
    echo -e "${RED}Error: only 'flow-next' is supported${NC}"
    echo "The legacy 'flow' plugin was removed in flow-next 1.0.2."
    echo "Usage: $0 [flow-next]"
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
         "$CODEX_DIR/prompts" "$CODEX_DIR/templates" "$CODEX_DIR/references"

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
# Legacy alias cleanup (upgrade path)
# ====================
# The flow-next-epic-review deprecation alias was removed from the source tree
# (fn-124). The loops above only replace skills still present in source and
# only copy current prompts, so stale copies from older installs would keep
# surfacing as a live (if still-functional) redirect forever. We RETIRE those
# two artifacts on upgrade — but NON-DESTRUCTIVELY.
#
# Two safety layers, because deleting a user's file is unacceptable while a
# lingering stale redirect is merely cosmetic:
#   1. Identity gate — act ONLY on an artifact whose leading-frontmatter `name:`
#      is EXACTLY the generator's own id (`flow-next:epic-review` for the prompt,
#      `flow-next-epic-review` for the skill). A hand-authored file rarely
#      carries our namespaced id; body-text heuristics (which a user migration
#      wrapper can mimic) are deliberately NOT used.
#   2. Non-destructive move — even on a match we never `rm`. We MOVE the artifact
#      into `~/.codex/.flow-next-retired/` (outside the scanned skills/ + prompts/
#      trees), so it stops surfacing as a command/skill but every byte is
#      preserved and trivially restorable. So even the pathological case (a user
#      file that really does carry our exact id) loses nothing — it is relocated,
#      recoverable, and logged.
RETIRED_DIR="$CODEX_DIR/.flow-next-retired"
frontmatter_name() {  # $1 = file → prints the leading-frontmatter `name:` value, ONLY if the block is well-formed (closing fence seen)
    awk '
      NR==1 && $0!="---" { exit }                         # no frontmatter block
      NR>1  && $0=="---" { print name; exit }             # closing fence → emit buffered name (empty if none)
      NR>1  && name=="" && /^name:[ \t]/ { name=$0; sub(/^name:[ \t]*/, "", name); gsub(/\r$/, "", name) }
    ' "$1" 2>/dev/null
}
retire_artifact() {  # $1 = path to move, $2 = subdir under RETIRED_DIR, $3 = human label
    local src="$1" destdir="$RETIRED_DIR/$2" label="$3"
    mkdir -p "$destdir"
    local dest="$destdir/$(basename "$src")"
    # No-clobber: NEVER overwrite a previously retired backup (a user could
    # recreate the live alias with different content between upgrades — the
    # earlier backup must survive too). Also avoids `mv`'s move-INTO-an-existing
    # -dir semantics for the skill directory. Pick the first free numbered name.
    if [ -e "$dest" ]; then
        local n=1
        while [ -e "$dest.$n" ]; do n=$((n + 1)); done
        dest="$dest.$n"
    fi
    mv "$src" "$dest"   # dest is guaranteed free → plain mv, no -f clobber
    echo -e "${GREEN}✓${NC} retired stale legacy $label → $dest (recoverable)"
}
LEGACY_SKILL="$CODEX_DIR/skills/flow-next-epic-review"
if [ -d "$LEGACY_SKILL" ]; then
    if [ "$(frontmatter_name "$LEGACY_SKILL/SKILL.md")" = "flow-next-epic-review" ]; then
        retire_artifact "$LEGACY_SKILL" "skills" "skill flow-next-epic-review"
    else
        echo -e "${YELLOW}!${NC} kept $LEGACY_SKILL (frontmatter name is not ours — left untouched)"
    fi
fi
LEGACY_PROMPT="$CODEX_DIR/prompts/epic-review.md"
if [ -f "$LEGACY_PROMPT" ]; then
    if [ "$(frontmatter_name "$LEGACY_PROMPT")" = "flow-next:epic-review" ]; then
        retire_artifact "$LEGACY_PROMPT" "prompts" "prompt epic-review.md"
    else
        echo -e "${YELLOW}!${NC} kept $LEGACY_PROMPT (frontmatter name is not ours — left untouched)"
    fi
fi

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
# Hooks (zero-default; fn-114)
# ====================
# Mirror ships no hooks.json (fn-114). Upgrade cleanup: a ~/.codex/hooks.json
# from an OLDER flow-next install would keep the outdated guard firing globally
# with [features] hooks=true set - remove it, but ONLY when it is verifiably
# ours (flow-next/ralph-guard fingerprint); user-customized files are kept.
if [ -f "$HOME/.codex/hooks.json" ] && grep -qE "ralph-guard|flow-next" "$HOME/.codex/hooks.json" 2>/dev/null; then
    # Strip ONLY the fingerprinted flow-next entries; user-defined hooks in the
    # same file survive. Delete the file only when nothing else remains.
    python3 - "$HOME/.codex/hooks.json" <<'PYEOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text())
except Exception:
    print("!  could not parse ~/.codex/hooks.json; leaving it untouched", file=sys.stderr)
    sys.exit(0)
def is_ours(entry):
    return "ralph-guard" in json.dumps(entry) or "flow-next" in json.dumps(entry)
changed = False
def _strip_events(container):
    global changed
    for event, entries in list(container.items()):
        if isinstance(entries, list):
            kept = [e for e in entries if not is_ours(e)]
            if len(kept) != len(entries):
                changed = True
                if kept:
                    container[event] = kept
                else:
                    del container[event]
if isinstance(data, dict):
    # Both shapes: flat {"PreToolUse": [...]} and the real pre-fn-114
    # nested {"hooks": {"PreToolUse": [...]}} (PR #226 review).
    _strip_events(data)
    if isinstance(data.get("hooks"), dict):
        _strip_events(data["hooks"])
        if not data["hooks"]:
            del data["hooks"]
            changed = True
    def _has_entries(d):
        for v in d.values():
            if isinstance(v, list) and v:
                return True
            if isinstance(v, dict) and _has_entries(v):
                return True
        return False
    remaining = _has_entries(data)
    if changed and not remaining:
        path.unlink()
        print("removed stale flow-next ~/.codex/hooks.json (no other hooks remained)")
    elif changed:
        path.write_text(json.dumps(data, indent=2) + "\n")
        print("stripped stale flow-next entries from ~/.codex/hooks.json (your other hooks kept)")
PYEOF
    echo -e "${YELLOW}!${NC} pre-opt-in flow-next hook entries cleaned (re-run /flow-next:ralph-init in projects that use Ralph)"
fi
if [ -f "$CODEX_SRC/hooks.json" ]; then
    echo -e "${YELLOW}!${NC} codex/hooks.json present in source but not installed (Ralph is opt-in via ralph-init)"
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
# Top-level templates (canonical spec template + future siblings)
# ====================
# Skills resolve `${CLAUDE_PLUGIN_ROOT}/templates/spec.md` at runtime
# (interview NEW IDEA path, CLAUDE.md cross-link). Without this copy,
# Codex installs miss the canonical template and the symmetric-interview
# new-spec path breaks. Mirrored by sync-codex.sh into $CODEX_SRC/templates/.
if [ -d "$CODEX_SRC/templates" ]; then
    for tpl in "$CODEX_SRC/templates/"*.md; do
        [ -f "$tpl" ] || continue
        cp "$tpl" "$CODEX_DIR/templates/"
    done
    TPL_COUNT=$(find "$CODEX_SRC/templates" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
    [ "$TPL_COUNT" -gt 0 ] && echo -e "${GREEN}✓${NC} $TPL_COUNT top-level template(s) (spec.md + siblings)"
    # Template subdirectories (memory/*.tpl + future siblings). flowctl
    # resolves ~/.codex/templates/memory/<name> via _memory_template_path;
    # without this copy it silently falls back to embedded defaults.
    for tpldir in "$CODEX_SRC/templates/"*/; do
        [ -d "$tpldir" ] || continue
        sub=$(basename "$tpldir")
        rm -rf "$CODEX_DIR/templates/$sub"
        cp -r "$tpldir" "$CODEX_DIR/templates/$sub"
        echo -e "${GREEN}✓${NC} templates/$sub"
    done
fi

# ====================
# References (shared disclosure files — fn-62.2)
# ====================
# Skills resolve `${CLAUDE_PLUGIN_ROOT}/references/<name>.md` at runtime
# (e.g. references/html-artifacts.md, loaded only when the matching config
# gate is on). Mirrored by sync-codex.sh into $CODEX_SRC/references/ —
# byte-identical to canonical (reference files are tool-name-agnostic).
if [ -d "$CODEX_SRC/references" ]; then
    for ref in "$CODEX_SRC/references/"*.md; do
        [ -f "$ref" ] || continue
        cp "$ref" "$CODEX_DIR/references/"
    done
    REF_COUNT=$(find "$CODEX_SRC/references" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
    [ "$REF_COUNT" -gt 0 ] && echo -e "${GREEN}✓${NC} $REF_COUNT shared reference file(s)"
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
for cmd in "$PLUGIN_DIR/commands/"*.md; do
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

# Migration: clean up legacy standalone [features] block (pre-fix versions
# of this script wrote a duplicate [features] table, which TOML rejects)
if grep -q "# --- flow-next features" "$CONFIG" 2>/dev/null; then
    sed -i.bak '/# --- flow-next features/,/# --- end flow-next features ---/d' "$CONFIG"
    rm -f "${CONFIG}.bak"
fi

# Ensure exactly one `hooks = true` under [features], migrating away from the
# deprecated `codex_hooks` spelling and de-duplicating. Idempotent + dedup-safe:
# handles a config that already carries BOTH codex_hooks and hooks (which older
# versions of this script produced) without leaving an invalid duplicate key.
python3 "$SCRIPT_DIR/normalize_codex_hooks.py" "$CONFIG"

# Generate agent entries
CODEX_MAX_THREADS="${CODEX_MAX_THREADS:-12}"
{
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
echo -e "  ${GREEN}✓${NC} [features] hooks = true (feature flag only; no default Ralph hooks file)"

# ====================
# Summary
# ====================
echo
echo -e "${GREEN}Done!${NC} $PLUGIN installed to ~/.codex"
echo "  $SKILL_COUNT skills, $AGENT_COUNT agents, $PROMPT_COUNT prompts"
[ "$HAS_FLOWCTL" = true ] && echo "  flowctl: ~/.codex/scripts/flowctl"
echo "  hooks: none by default (ralph-init writes project .codex/hooks.json when opted in)"
echo "  config: ~/.codex/config.toml (merged, max_threads=$CODEX_MAX_THREADS)"
echo
echo -e "${YELLOW}Requires Codex CLI 0.102.0+${NC}"
echo "  /$PLUGIN:plan  — create a plan"
echo "  /$PLUGIN:work  — execute tasks"
