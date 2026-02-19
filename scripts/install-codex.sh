#!/bin/bash
# Install Flow or Flow-Next skills and prompts into Codex CLI (~/.codex)
#
# Usage: ./scripts/install-codex.sh <flow|flow-next>
#
# What gets installed:
#   - Skills:    plugins/<plugin>/skills/*     → ~/.codex/skills/
#   - Agents:    plugins/<plugin>/agents/*     → ~/.codex/agents/ (as .toml role configs)
#   - Prompts:   plugins/<plugin>/commands/*   → ~/.codex/prompts/
#   - CLI tools: flowctl, flowctl.py           → ~/.codex/bin/
#   - Scripts:   worktree.sh, etc.             → ~/.codex/scripts/
#   - Templates: ralph-init templates          → ~/.codex/templates/
#   - Config:    config.toml agent entries     → ~/.codex/config.toml (merged)
#
# Path patching:
#   All ${CLAUDE_PLUGIN_ROOT} references are replaced with ~/.codex
#   so skills work without Claude Code's plugin system.
#
# Agent conversion (Codex 0.102.0+ multi-agent roles):
#   Claude Code agent .md files (YAML frontmatter + body) are converted to
#   Codex .toml role configs (model, developer_instructions, sandbox_mode).
#   Agent entries are merged into ~/.codex/config.toml with descriptions.
#
#   Model mapping (3-tier, Claude → Codex):
#     opus              → gpt-5.3-codex + reasoning:high
#       (quality-auditor, flow-gap-analyst, context-scout)
#     sonnet (smart)    → gpt-5.3-codex + reasoning:high
#       (epic-scout, agents-md-scout, docs-gap-scout — need deeper analysis)
#     sonnet (fast)     → gpt-5.3-codex-spark (no reasoning)
#       (build, env, testing, tooling, observability, security, workflow, memory scouts)
#     inherit           → (omitted, inherits from parent: worker, plan-sync)
#
#   claude-md-scout is auto-renamed to agents-md-scout (AGENTS.md, not CLAUDE.md)
#
#   Override defaults via env vars:
#     CODEX_MODEL_INTELLIGENT=gpt-5.3-codex
#     CODEX_MODEL_FAST=gpt-5.3-codex-spark
#     CODEX_REASONING_EFFORT=high
#     CODEX_AGENT_SANDBOX=workspace-write
#     CODEX_MAX_THREADS=12
#
# Skill patching:
#   flow-next-work: Task tool → Codex multi-agent role invocations
#   flow-next-plan: flow-next:<scout> refs → Codex role names (underscore)
#   flow-next-prime: Task flow-next:<scout> → Use the <role> agent (9 scouts)
#   RP review skills: adds CRITICAL wait/no-retry warnings for slow commands
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

# Codex model defaults (override via env vars)
CODEX_MODEL_INTELLIGENT="${CODEX_MODEL_INTELLIGENT:-gpt-5.3-codex}"
CODEX_MODEL_FAST="${CODEX_MODEL_FAST:-gpt-5.3-codex-spark}"
CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-high}"
CODEX_AGENT_SANDBOX="${CODEX_AGENT_SANDBOX:-workspace-write}"
CODEX_MAX_THREADS="${CODEX_MAX_THREADS:-12}"

# Parse argument
PLUGIN="${1:-}"
if [ -z "$PLUGIN" ]; then
    echo -e "${RED}Error: Plugin name required${NC}"
    echo "Usage: $0 <flow|flow-next>"
    exit 1
fi

if [ "$PLUGIN" != "flow" ] && [ "$PLUGIN" != "flow-next" ]; then
    echo -e "${RED}Error: Invalid plugin '$PLUGIN'${NC}"
    echo "Usage: $0 <flow|flow-next>"
    exit 1
fi

PLUGIN_DIR="$REPO_ROOT/plugins/$PLUGIN"

echo "Installing $PLUGIN to Codex CLI (multi-agent mode)..."
echo

# Check codex dir exists
if [ ! -d "$CODEX_DIR" ]; then
    echo -e "${RED}Error: ~/.codex not found. Is Codex CLI installed?${NC}"
    exit 1
fi

# Check plugin exists
if [ ! -d "$PLUGIN_DIR" ]; then
    echo -e "${RED}Error: Plugin '$PLUGIN' not found${NC}"
    exit 1
fi

# Create dirs
mkdir -p "$CODEX_DIR/skills"
mkdir -p "$CODEX_DIR/prompts"
mkdir -p "$CODEX_DIR/bin"
mkdir -p "$CODEX_DIR/scripts"
mkdir -p "$CODEX_DIR/templates"
mkdir -p "$CODEX_DIR/agents"

# Function to patch CLAUDE_PLUGIN_ROOT references for Codex
patch_for_codex() {
    local file="$1"
    if [ -f "$file" ]; then
        sed -i.bak \
            -e 's|\${CLAUDE_PLUGIN_ROOT}/scripts/flowctl|~/.codex/bin/flowctl|g' \
            -e 's|\${PLUGIN_ROOT}/scripts/flowctl|~/.codex/bin/flowctl|g' \
            -e 's|"\${CLAUDE_PLUGIN_ROOT}/scripts/flowctl"|"$HOME/.codex/bin/flowctl"|g' \
            -e 's|"\${PLUGIN_ROOT}/scripts/flowctl"|"$HOME/.codex/bin/flowctl"|g' \
            -e 's|\${CLAUDE_PLUGIN_ROOT}/scripts/|~/.codex/bin/|g' \
            -e 's|\${CLAUDE_PLUGIN_ROOT}/skills/flow-next-ralph-init/templates|~/.codex/templates/flow-next-ralph-init|g' \
            -e 's|\${CLAUDE_PLUGIN_ROOT}/skills/flow-next-worktree-kit/scripts|~/.codex/scripts|g' \
            -e 's|\${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json|~/.codex/plugin.json|g' \
            "$file"
        rm -f "${file}.bak"
    fi
}

# Scouts that need full intelligence despite being sonnet-tier in Claude Code.
# These do reasoning/judgment, not just config scanning.
# Note: claude-md-scout is renamed to agents-md-scout (Codex uses AGENTS.md not CLAUDE.md)
INTELLIGENT_SCOUTS="epic-scout agents-md-scout docs-gap-scout"

# Agent renames for Codex (Claude Code name → Codex name)
# Codex uses AGENTS.md, not CLAUDE.md
rename_agent_for_codex() {
    local name="$1"
    case "$name" in
        claude-md-scout) echo "agents-md-scout" ;;
        *) echo "$name" ;;
    esac
}

# Patch agent body content for Codex differences
patch_agent_body_for_codex() {
    local body="$1"
    local name="$2"
    case "$name" in
        claude-md-scout|agents-md-scout)
            # Codex uses AGENTS.md, not CLAUDE.md
            echo "$body" | sed \
                -e 's/CLAUDE\.md/AGENTS.md/g' \
                -e 's/claude\.md/agents.md/g' \
                -e 's/Claude Code/Codex/g'
            ;;
        *)
            echo "$body"
            ;;
    esac
}

# Map Claude Code model to Codex model
# Takes claude_model and agent_name to handle sonnet scouts that need intelligence
map_model_to_codex() {
    local claude_model="$1"
    local agent_name="${2:-}"
    case "$claude_model" in
        opus|claude-opus-*)
            echo "$CODEX_MODEL_INTELLIGENT"
            ;;
        sonnet|claude-sonnet-*)
            # Some sonnet scouts need full intelligence (reasoning/judgment tasks)
            if [ -n "$agent_name" ] && echo "$INTELLIGENT_SCOUTS" | grep -qw "$agent_name"; then
                echo "$CODEX_MODEL_INTELLIGENT"
            else
                echo "$CODEX_MODEL_FAST"
            fi
            ;;
        haiku|claude-haiku-*)
            echo "$CODEX_MODEL_FAST"
            ;;
        inherit|"")
            echo ""  # Empty = inherit from parent
            ;;
        *)
            echo "$CODEX_MODEL_INTELLIGENT"
            ;;
    esac
}

# Check if model supports reasoning settings (Spark does not)
model_supports_reasoning() {
    local model="$1"
    case "$model" in
        *spark*) return 1 ;;
        *) return 0 ;;
    esac
}

# Convert Claude Code agent .md to Codex .toml role config
# Extracts: name, description, model from YAML frontmatter
# Body content → developer_instructions
convert_agent_to_toml() {
    local md_file="$1"
    local toml_file="$2"

    if [ ! -f "$md_file" ]; then
        return
    fi

    # Parse YAML frontmatter
    local name="" description="" model=""
    local in_frontmatter=0
    local body=""
    local frontmatter_done=0

    while IFS= read -r line; do
        if [ "$frontmatter_done" = "1" ]; then
            body+="$line"$'\n'
            continue
        fi

        if [ "$line" = "---" ]; then
            if [ "$in_frontmatter" = "0" ]; then
                in_frontmatter=1
                continue
            else
                frontmatter_done=1
                continue
            fi
        fi

        if [ "$in_frontmatter" = "1" ]; then
            case "$line" in
                name:*)
                    name="${line#name: }"
                    name="${name#name:}"
                    name="$(echo "$name" | xargs)"  # trim whitespace
                    ;;
                description:*)
                    description="${line#description: }"
                    description="${description#description:}"
                    description="$(echo "$description" | xargs)"
                    ;;
                model:*)
                    model="${line#model: }"
                    model="${model#model:}"
                    model="$(echo "$model" | xargs)"
                    ;;
            esac
        fi
    done < "$md_file"

    # Apply Codex renames
    local codex_name
    codex_name=$(rename_agent_for_codex "$name")

    # Map model (use codex_name for intelligent scout matching)
    local codex_model
    codex_model=$(map_model_to_codex "$model" "$codex_name")

    # Strip leading/trailing blank lines from body (macOS-compatible)
    body="$(echo "$body" | awk 'NF{p=1} p')"
    body="$(echo "$body" | awk '{a[NR]=$0} END{for(i=NR;i>=1;i--) if(a[i]!=""){for(j=1;j<=i;j++) print a[j]; break}}')"

    # Patch body content for Codex differences
    body="$(patch_agent_body_for_codex "$body" "$name")"

    # Escape backslashes for TOML basic strings (triple-quoted """ still interprets \)
    body="$(echo "$body" | sed 's/\\/\\\\/g')"

    # Write .toml role config
    {
        echo "# Auto-generated from $name.md (codex: $codex_name) — do not edit manually"
        echo "# Re-run install-codex.sh to regenerate"
        echo ""
        if [ -n "$codex_model" ]; then
            echo "model = \"$codex_model\""
            if model_supports_reasoning "$codex_model"; then
                echo "model_reasoning_effort = \"$CODEX_REASONING_EFFORT\""
                echo "model_reasoning_summary = \"detailed\""
            else
                echo "# Spark: reasoning settings not supported"
            fi
        else
            echo "# model: inherited from parent"
        fi
        echo "sandbox_mode = \"$CODEX_AGENT_SANDBOX\""
        echo ""
        echo "developer_instructions = \"\"\""
        echo "$body"
        echo "\"\"\""
    } > "$toml_file"
}

# Generate config.toml agent entries
# Reads existing config.toml, removes old flow-next agent entries, adds new ones
# Handles: root-level multi_agent, [agents] dedup, sub-table merging
generate_config_entries() {
    local config_file="$CODEX_DIR/config.toml"
    local agents_dir="$1"  # Source .md files dir
    local tmp_entries="/tmp/codex-agent-entries.toml"

    # --- Step 1: Ensure multi_agent = true at TOML root ---
    # Must appear before any [table] header to stay at root scope.
    if [ -f "$config_file" ]; then
        if ! grep -q "^multi_agent" "$config_file" 2>/dev/null; then
            # Insert at line 1 (before any table headers)
            local tmp_cfg="/tmp/codex-config-prepend.toml"
            {
                echo "# Enable custom multi-agent roles (Codex 0.102.0+)"
                echo "multi_agent = true"
                echo ""
                cat "$config_file"
            } > "$tmp_cfg"
            mv "$tmp_cfg" "$config_file"
        fi
    fi

    # --- Step 2: Clean old flow-next entries ---
    if [ -f "$config_file" ]; then
        if grep -q "flow-next multi-agent roles" "$config_file" 2>/dev/null; then
            sed -i.bak '/# --- flow-next multi-agent roles/,/# --- end flow-next roles ---/d' "$config_file"
            rm -f "${config_file}.bak"
        fi
    fi

    # --- Step 3: Generate agent sub-table entries ---
    {
        echo ""
        echo "# --- flow-next multi-agent roles (auto-generated) ---"
        echo "# Re-run install-codex.sh to regenerate"
        echo ""

        # Only declare [agents] if it doesn't already exist in user config
        if ! grep -q "^\[agents\]" "$config_file" 2>/dev/null; then
            echo "[agents]"
        fi
        # Always set max_threads under [agents] (idempotent — appears right after [agents])
        echo "max_threads = $CODEX_MAX_THREADS"
        echo ""

        for md_file in "$agents_dir"/*.md; do
            if [ ! -f "$md_file" ]; then continue; fi
            local basename
            basename="$(basename "${md_file%.md}")"
            # Apply Codex renames
            local codex_basename
            codex_basename=$(rename_agent_for_codex "$basename")
            # Convert hyphens to underscores for TOML key
            local role_key="${codex_basename//-/_}"

            # Parse description from frontmatter
            local desc=""
            local in_fm=0
            while IFS= read -r line; do
                if [ "$line" = "---" ]; then
                    if [ "$in_fm" = "0" ]; then in_fm=1; continue; fi
                    break
                fi
                if [ "$in_fm" = "1" ]; then
                    case "$line" in
                        description:*)
                            desc="${line#description: }"
                            desc="${desc#description:}"
                            desc="$(echo "$desc" | xargs)"
                            # Patch description for renames
                            if [ "$basename" = "claude-md-scout" ]; then
                                desc="Used by /flow-next:prime to analyze AGENTS.md quality and completeness. Do not invoke directly."
                            fi
                            ;;
                    esac
                fi
            done < "$md_file"

            # [agents.X] sub-tables are always safe to append — they extend [agents]
            echo "[agents.$role_key]"
            echo "description = \"$desc\""
            echo "config_file = \"agents/$codex_basename.toml\""
            echo ""
        done

        echo "# --- end flow-next roles ---"
    } > "$tmp_entries"

    # --- Step 4: Merge into config.toml ---
    if [ -f "$config_file" ]; then
        # Remove old max_threads we may have written (will be re-added from tmp_entries)
        if grep -q "^max_threads" "$config_file" 2>/dev/null; then
            sed -i.bak '/^max_threads/d' "$config_file"
            rm -f "${config_file}.bak"
        fi
        cat "$tmp_entries" >> "$config_file"
    else
        # No config.toml yet — prepend multi_agent before our entries
        {
            echo "# Enable custom multi-agent roles (Codex 0.102.0+)"
            echo "multi_agent = true"
            echo ""
            cat "$tmp_entries"
        } > "$config_file"
    fi

    rm -f "$tmp_entries"
}

# Patch flow-next-work for Codex multi-agent (replace Task tool with role invocation)
patch_work_for_codex_agents() {
    local phases_file="$1/phases.md"
    local skill_md="$1/SKILL.md"

    if [ ! -f "$phases_file" ]; then return; fi

    # Replace section 3c "Spawn Worker" with Codex role invocation
    local start_line end_line
    start_line=$(grep -n "^### 3c\. Spawn Worker" "$phases_file" | cut -d: -f1)
    end_line=$(grep -n "^### 3d\." "$phases_file" | cut -d: -f1)

    if [ -n "$start_line" ] && [ -n "$end_line" ]; then
        end_line=$((end_line - 1))
        head -n $((start_line - 1)) "$phases_file" > "${phases_file}.tmp"
        cat >> "${phases_file}.tmp" << 'SECTION3CEOF'
### 3c. Run Worker Agent

Use the **worker** agent role to implement the task. The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

**Invoke the worker:**

"Use the worker agent to implement this task:

TASK_ID: fn-X.Y
EPIC_ID: fn-X
FLOWCTL: $FLOWCTL
REVIEW_MODE: none|rp|codex
RALPH_MODE: true|false

Follow your phases exactly."

**Worker returns**: Summary of implementation, files changed, test results, review verdict.

SECTION3CEOF
        tail -n +$end_line "$phases_file" >> "${phases_file}.tmp"
        mv "${phases_file}.tmp" "$phases_file"
    fi

    # Light text replacements
    sed -i.bak \
        -e 's/Use the Task tool to spawn a `worker` subagent/Use the worker agent role/g' \
        -e 's/spawn a worker subagent with fresh context/use the worker agent with fresh context/g' \
        -e 's/After worker returns/After the worker agent returns/g' \
        -e 's/the worker failed/the worker agent failed/g' \
        -e 's/spawn the `plan-sync` subagent/use the plan_sync agent/g' \
        -e 's/quality auditor subagent/quality_auditor agent/g' \
        "$phases_file"
    rm -f "${phases_file}.bak"

    # Patch SKILL.md
    if [ -f "$skill_md" ]; then
        sed -i.bak \
            -e 's/worker subagent with fresh context/worker agent with fresh context/g' \
            -e 's/worker subagent/worker agent/g' \
            -e 's/Worker subagent/Worker agent/g' \
            -e 's/Each task is implemented by a `worker` subagent/Each task is implemented by the `worker` agent role/g' \
            -e 's/worker handles/worker agent handles/g' \
            -e 's/The worker invokes/The worker agent invokes/g' \
            "$skill_md"
        rm -f "${skill_md}.bak"
    fi
}

# Patch flow-next-prime for Codex multi-agent (replace Task tool scout refs with role names)
patch_prime_for_codex_agents() {
    local skills_dir="$1"
    local workflow_file="$skills_dir/flow-next-prime/workflow.md"

    if [ -f "$workflow_file" ]; then
        # Replace "Task flow-next:scout-name" with "Use the scout_name agent"
        sed -i.bak \
            -e 's|Task flow-next:tooling-scout|Use the tooling_scout agent|g' \
            -e 's|Task flow-next:claude-md-scout|Use the agents_md_scout agent|g' \
            -e 's|Task flow-next:env-scout|Use the env_scout agent|g' \
            -e 's|Task flow-next:testing-scout|Use the testing_scout agent|g' \
            -e 's|Task flow-next:build-scout|Use the build_scout agent|g' \
            -e 's|Task flow-next:docs-gap-scout|Use the docs_gap_scout agent|g' \
            -e 's|Task flow-next:observability-scout|Use the observability_scout agent|g' \
            -e 's|Task flow-next:security-scout|Use the security_scout agent|g' \
            -e 's|Task flow-next:workflow-scout|Use the workflow_scout agent|g' \
            -e 's/Run all 9 scouts in parallel using the Task tool:/Run all 9 scouts in parallel (Codex spawns them as multi-agent threads):/g' \
            -e 's/Launch all 9 scouts in parallel for speed/Launch all 9 scout agents in parallel for speed/g' \
            "$workflow_file"
        rm -f "${workflow_file}.bak"
    fi
}

# Patch flow-next-plan for Codex multi-agent (replace Task tool scout refs with role names)
patch_plan_for_codex_agents() {
    local skills_dir="$1"
    local steps_file="$skills_dir/flow-next-plan/steps.md"
    local skill_md="$skills_dir/flow-next-plan/SKILL.md"

    if [ -f "$steps_file" ]; then
        # Replace flow-next:scout-name with Codex role names (underscore format)
        sed -i.bak \
            -e 's|`flow-next:context-scout`|the `context_scout` agent|g' \
            -e 's|`flow-next:repo-scout`|the `repo_scout` agent|g' \
            -e 's|`flow-next:practice-scout`|the `practice_scout` agent|g' \
            -e 's|`flow-next:docs-scout`|the `docs_scout` agent|g' \
            -e 's|`flow-next:github-scout`|the `github_scout` agent|g' \
            -e 's|`flow-next:memory-scout`|the `memory_scout` agent|g' \
            -e 's|`flow-next:epic-scout`|the `epic_scout` agent|g' \
            -e 's|`flow-next:docs-gap-scout`|the `docs_gap_scout` agent|g' \
            -e 's|`flow-next:flow-gap-analyst`|the `flow_gap_analyst` agent|g' \
            -e 's|Task flow-next:flow-gap-analyst|Use the flow_gap_analyst agent|g' \
            "$steps_file"
        rm -f "${steps_file}.bak"
    fi

    if [ -f "$skill_md" ]; then
        sed -i.bak \
            -e 's/launch ALL scouts listed in steps.md in ONE parallel Task call/launch ALL scout agents listed in steps.md in parallel/g' \
            -e 's/Do NOT skip scouts or run them sequentially/Do NOT skip scouts or run them sequentially. Codex will spawn them as parallel multi-agent threads/g' \
            "$skill_md"
        rm -f "${skill_md}.bak"
    fi
}

# Patch RP review skills for Codex (add CRITICAL wait instructions)
patch_rp_review_skills_for_codex() {
    local codex_skills_dir="$1"

    cat > /tmp/codex-rp-warning.md << 'WARNINGEOF'

---

## CRITICAL: RepoPrompt Commands Are SLOW - DO NOT RETRY

**READ THIS BEFORE RUNNING ANY COMMANDS:**

1. **`setup-review` takes 5-15 MINUTES** - It runs the RepoPrompt context builder which indexes files. This is NORMAL. Do NOT assume it is stuck.

2. **`chat-send` takes 2-10 MINUTES** - It waits for the LLM to generate a full review. This is NORMAL. Do NOT assume it is stuck.

3. **Run commands directly and WAIT** - Do NOT use background jobs. Just run the command and wait:
   ```bash
   # Run setup-review - takes 5-15 minutes, just wait
   $FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "..."
   # You will see file paths printed as it indexes - this is progress, not errors
   ```

4. **Output is progress, not errors** - The context builder prints file paths as it indexes. Seeing many lines of output is NORMAL. Do not interpret this as an error loop.

5. **NEVER retry these commands** - If you run them again, you will create duplicate reviews and waste time. Run ONCE and WAIT.

6. **Exit code 0 = success** - When the command finishes, check the exit code. If it's 0, it worked.

**If a command has been running for less than 15 minutes, WAIT. Do not retry. Do not output <promise>RETRY</promise>.**

---

WARNINGEOF

    for skill in flow-next-impl-review flow-next-plan-review flow-next-epic-review; do
        local wf="$codex_skills_dir/$skill/workflow.md"
        if [ -f "$wf" ]; then
            head -1 "$wf" > "${wf}.tmp"
            cat /tmp/codex-rp-warning.md >> "${wf}.tmp"
            tail -n +2 "$wf" >> "${wf}.tmp"
            mv "${wf}.tmp" "$wf"
        fi
    done

    for skill in flow-next-impl-review flow-next-plan-review flow-next-epic-review; do
        local skill_md="$codex_skills_dir/$skill/SKILL.md"
        if [ -f "$skill_md" ]; then
            sed -i.bak \
                -e 's|setup-review|setup-review (5-15 min, DO NOT RETRY)|g' \
                -e 's|chat-send|chat-send (2-10 min, DO NOT RETRY)|g' \
                "$skill_md"
            rm -f "${skill_md}.bak"
        fi
    done

    rm -f /tmp/codex-rp-warning.md
}

# ====================
# Install CLI tools (flow-next only)
# ====================
HAS_FLOWCTL=false
if [ -f "$PLUGIN_DIR/scripts/flowctl" ]; then
    echo -e "${BLUE}Installing CLI tools...${NC}"
    cp "$PLUGIN_DIR/scripts/flowctl" "$CODEX_DIR/bin/"
    chmod +x "$CODEX_DIR/bin/flowctl"
    echo -e "  ${GREEN}✓${NC} flowctl"
    HAS_FLOWCTL=true
fi

if [ -f "$PLUGIN_DIR/scripts/flowctl.py" ]; then
    cp "$PLUGIN_DIR/scripts/flowctl.py" "$CODEX_DIR/bin/"
    echo -e "  ${GREEN}✓${NC} flowctl.py"
fi

# ====================
# Install scripts
# ====================
echo -e "${BLUE}Installing scripts...${NC}"

if [ -f "$PLUGIN_DIR/skills/flow-next-worktree-kit/scripts/worktree.sh" ]; then
    cp "$PLUGIN_DIR/skills/flow-next-worktree-kit/scripts/worktree.sh" "$CODEX_DIR/scripts/"
    chmod +x "$CODEX_DIR/scripts/worktree.sh"
    echo -e "  ${GREEN}✓${NC} worktree.sh"
fi

# ====================
# Install templates
# ====================
echo -e "${BLUE}Installing templates...${NC}"

if [ -d "$PLUGIN_DIR/skills/flow-next-ralph-init/templates" ]; then
    rm -rf "$CODEX_DIR/templates/flow-next-ralph-init"
    cp -r "$PLUGIN_DIR/skills/flow-next-ralph-init/templates" "$CODEX_DIR/templates/flow-next-ralph-init"
    chmod +x "$CODEX_DIR/templates/flow-next-ralph-init/"*.sh 2>/dev/null || true
    chmod +x "$CODEX_DIR/templates/flow-next-ralph-init/"*.py 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} flow-next-ralph-init templates"
fi

if [ -d "$PLUGIN_DIR/skills/flow-next-setup/templates" ]; then
    rm -rf "$CODEX_DIR/templates/flow-next-setup"
    cp -r "$PLUGIN_DIR/skills/flow-next-setup/templates" "$CODEX_DIR/templates/flow-next-setup"
    echo -e "  ${GREEN}✓${NC} flow-next-setup templates"
fi

# ====================
# Copy plugin.json for version info
# ====================
if [ -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ]; then
    cp "$PLUGIN_DIR/.claude-plugin/plugin.json" "$CODEX_DIR/plugin.json"
    echo -e "  ${GREEN}✓${NC} plugin.json (version info)"
fi

# ====================
# Install skills (with patching)
# ====================
echo -e "${BLUE}Installing skills...${NC}"

for skill_dir in "$PLUGIN_DIR/skills/"*/; do
    if [ -d "$skill_dir" ]; then
        skill=$(basename "$skill_dir")
        rm -rf "$CODEX_DIR/skills/$skill"
        cp -r "${skill_dir%/}" "$CODEX_DIR/skills/"

        # Patch all markdown files in the skill (including nested)
        find "$CODEX_DIR/skills/$skill" -name "*.md" -type f | while read -r md_file; do
            patch_for_codex "$md_file"
        done

        echo -e "  ${GREEN}✓${NC} $skill"
    fi
done

# Patch flow-next-work for Codex multi-agent roles
if [ -d "$CODEX_DIR/skills/flow-next-work" ]; then
    patch_work_for_codex_agents "$CODEX_DIR/skills/flow-next-work"
    echo -e "  ${GREEN}✓${NC} flow-next-work (patched for multi-agent roles)"
fi

# Patch flow-next-plan for Codex multi-agent roles
patch_plan_for_codex_agents "$CODEX_DIR/skills"
echo -e "  ${GREEN}✓${NC} flow-next-plan (patched for multi-agent roles)"

# Patch flow-next-prime for Codex multi-agent roles
patch_prime_for_codex_agents "$CODEX_DIR/skills"
echo -e "  ${GREEN}✓${NC} flow-next-prime (patched for multi-agent roles)"

# Patch all RP review skills for Codex
patch_rp_review_skills_for_codex "$CODEX_DIR/skills"
echo -e "  ${GREEN}✓${NC} RP review skills (patched - DO NOT RETRY warnings)"

# ====================
# Install agents (convert .md → .toml role configs)
# ====================
if [ -d "$PLUGIN_DIR/agents" ] && [ "$(ls -A "$PLUGIN_DIR/agents" 2>/dev/null)" ]; then
    echo -e "${BLUE}Installing agents (multi-agent roles)...${NC}"

    # Clean old flow-next .toml role configs to remove stale/renamed agents
    # Only removes files we generated (identified by our header comment)
    grep -rl "Auto-generated from.*\.md.*do not edit manually" "$CODEX_DIR/agents/"*.toml 2>/dev/null | xargs rm -f 2>/dev/null || true

    AGENT_COUNT=0

    for agent_file in "$PLUGIN_DIR/agents/"*.md; do
        if [ -f "$agent_file" ]; then
            name="$(basename "${agent_file%.md}")"
            codex_name=$(rename_agent_for_codex "$name")
            convert_agent_to_toml "$agent_file" "$CODEX_DIR/agents/$codex_name.toml"
            if [ "$name" != "$codex_name" ]; then
                echo -e "  ${GREEN}✓${NC} $codex_name.toml (renamed from $name)"
            else
                echo -e "  ${GREEN}✓${NC} $codex_name.toml"
            fi
            AGENT_COUNT=$((AGENT_COUNT + 1))
        fi
    done

    # Generate config.toml entries
    generate_config_entries "$PLUGIN_DIR/agents"
    echo -e "  ${GREEN}✓${NC} config.toml ($AGENT_COUNT agent entries, max_threads=$CODEX_MAX_THREADS)"
fi

# ====================
# Install prompts (commands)
# ====================
echo -e "${BLUE}Installing prompts...${NC}"

for cmd in "$PLUGIN_DIR/commands/$PLUGIN/"*.md; do
    if [ -f "$cmd" ]; then
        name=$(basename "$cmd")
        cp "$cmd" "$CODEX_DIR/prompts/$name"
        patch_for_codex "$CODEX_DIR/prompts/$name"
        echo -e "  ${GREEN}✓${NC} $name"
    fi
done

# ====================
# Summary
# ====================
echo
echo -e "${GREEN}Done!${NC} $PLUGIN installed to ~/.codex (multi-agent mode)"
echo
echo -e "${BLUE}Directory structure:${NC}"
echo "  ~/.codex/"
if [ "$HAS_FLOWCTL" = true ]; then
echo "  ├── bin/flowctl          # CLI tool"
echo "  ├── bin/flowctl.py"
fi
echo "  ├── skills/              # Skill definitions"
echo "  ├── prompts/             # Command prompts"
if [ -d "$CODEX_DIR/agents" ] && [ "$(ls -A "$CODEX_DIR/agents" 2>/dev/null)" ]; then
echo "  ├── agents/              # .toml role configs (multi-agent)"
fi
if [ -d "$CODEX_DIR/scripts" ] && [ "$(ls -A "$CODEX_DIR/scripts" 2>/dev/null)" ]; then
echo "  ├── scripts/             # Helper scripts"
fi
if [ -d "$CODEX_DIR/templates" ] && [ "$(ls -A "$CODEX_DIR/templates" 2>/dev/null)" ]; then
echo "  └── templates/           # Ralph/setup templates"
fi
echo
echo -e "${BLUE}Model mapping:${NC}"
echo "  Intelligent agents (opus):   $CODEX_MODEL_INTELLIGENT (reasoning: $CODEX_REASONING_EFFORT)"
echo "  Smart scouts (reasoning):    $CODEX_MODEL_INTELLIGENT (epic-scout, agents-md-scout, docs-gap-scout)"
echo "  Fast scouts (scanning):      $CODEX_MODEL_FAST (8 remaining scouts)"
echo "  Worker agent:                inherited from parent"
echo "  Max parallel threads:        $CODEX_MAX_THREADS"
echo
echo -e "${YELLOW}Notes:${NC}"
echo "  • Requires Codex CLI 0.102.0+ for multi-agent role support"
echo "  • Agents are defined as .toml role configs in ~/.codex/agents/"
echo "  • Agent entries merged into ~/.codex/config.toml"
echo "  • Scouts run as parallel multi-agent threads during planning"
echo "  • Worker agent handles task implementation with fresh context"
echo "  • Reviews are MANDATORY - run /flow-next:impl-review after each task"
echo "  • Run /flow-next:epic-review when all tasks in an epic are done"
if [ "$HAS_FLOWCTL" = true ]; then
echo "  • Run 'flowctl --help' via ~/.codex/bin/flowctl"
fi
echo
echo -e "${BLUE}Quick start:${NC}"
if [ "$HAS_FLOWCTL" = true ]; then
echo "  1. Add ~/.codex/bin to PATH (optional)"
echo "  2. Use /$PLUGIN:plan to create a plan"
echo "  3. Use /$PLUGIN:work to execute tasks"
else
echo "  1. Use /$PLUGIN:plan to create a plan"
echo "  2. Use /$PLUGIN:work to execute tasks"
fi
echo
echo -e "${BLUE}Override models:${NC}"
echo "  CODEX_MODEL_INTELLIGENT=gpt-5.3-codex \\"
echo "  CODEX_MODEL_FAST=gpt-5.3-codex-spark \\"
echo "  CODEX_MAX_THREADS=12 \\"
echo "  ./scripts/install-codex.sh $PLUGIN"
