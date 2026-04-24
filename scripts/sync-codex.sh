#!/bin/bash
# Generate pre-built Codex files from canonical skills/ and agents/ sources.
# Output: plugins/flow-next/codex/{skills/,agents/,hooks.json}
#
# Idempotent — running twice produces identical output.
# Run after modifying skills/, agents/, or hooks/ and commit the result.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$REPO_ROOT/plugins/flow-next"
CODEX_DIR="$PLUGIN_DIR/codex"
SRC_SKILLS="$PLUGIN_DIR/skills"
SRC_AGENTS="$PLUGIN_DIR/agents"
SRC_HOOKS="$PLUGIN_DIR/hooks/hooks.json"

# Model defaults (same as install-codex.sh)
CODEX_MODEL_INTELLIGENT="${CODEX_MODEL_INTELLIGENT:-gpt-5.4}"
CODEX_MODEL_FAST="${CODEX_MODEL_FAST:-gpt-5.4-mini}"
CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-high}"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────────────

# Scouts that need full intelligence (reasoning/judgment, not just scanning)
INTELLIGENT_SCOUTS="epic-scout agents-md-scout docs-gap-scout"
# Agents that use opus in Claude Code
OPUS_AGENTS="quality-auditor flow-gap-analyst context-scout docs-scout github-scout practice-scout repo-scout plan-sync"

rename_agent() {
  case "$1" in
    claude-md-scout) echo "agents-md-scout" ;;
    *) echo "$1" ;;
  esac
}

map_model() {
  local claude_model="$1" agent_name="${2:-}"
  case "$claude_model" in
    opus|claude-opus-*)
      echo "$CODEX_MODEL_INTELLIGENT" ;;
    sonnet|claude-sonnet-*)
      if echo "$INTELLIGENT_SCOUTS" | grep -qw "$agent_name" 2>/dev/null; then
        echo "$CODEX_MODEL_INTELLIGENT"
      else
        echo "$CODEX_MODEL_FAST"
      fi ;;
    haiku|claude-haiku-*)
      echo "$CODEX_MODEL_FAST" ;;
    inherit|"")
      echo "" ;;
    *)
      echo "$CODEX_MODEL_INTELLIGENT" ;;
  esac
}

model_supports_reasoning() {
  case "$1" in
    *mini*|*spark*) return 1 ;;
    *) return 0 ;;
  esac
}

# Determine sandbox mode for an agent
sandbox_for() {
  local name="$1"
  case "$name" in
    worker|plan-sync) echo "workspace-write" ;;
    *)                echo "read-only" ;;
  esac
}

# Nickname candidates for scouts (better parallel UX)
nicknames_for() {
  local name="$1"
  case "$name" in
    build-scout)          echo '["Foreman", "Constructor", "Assembler"]' ;;
    agents-md-scout)      echo '["Archivist", "Scribe", "Librarian"]' ;;
    context-scout)        echo '["Navigator", "Cartographer", "Pathfinder"]' ;;
    docs-gap-scout)       echo '["Inspector", "Reviewer", "Auditor"]' ;;
    docs-scout)           echo '["Scholar", "Researcher", "Curator"]' ;;
    env-scout)            echo '["Provisioner", "Configurer", "Warden"]' ;;
    epic-scout)           echo '["Strategist", "Planner", "Coordinator"]' ;;
    github-scout)         echo '["Tracker", "Monitor", "Watcher"]' ;;
    memory-scout)         echo '["Chronicler", "Historian", "Recorder"]' ;;
    observability-scout)  echo '["Sentinel", "Observer", "Beacon"]' ;;
    practice-scout)       echo '["Mentor", "Guide", "Counselor"]' ;;
    repo-scout)           echo '["Explorer", "Surveyor", "Ranger"]' ;;
    security-scout)       echo '["Guardian", "Protector", "Shield"]' ;;
    testing-scout)        echo '["Verifier", "Validator", "Tester"]' ;;
    tooling-scout)        echo '["Mechanic", "Technician", "Tinker"]' ;;
    workflow-scout)       echo '["Automator", "Orchestrator", "Dispatcher"]' ;;
    flow-gap-analyst)     echo '["Analyst", "Evaluator", "Diagnostician"]' ;;
    quality-auditor)      echo '["Auditor", "Critic", "Appraiser"]' ;;
    *) echo "" ;;
  esac
}

is_scout_or_analyst() {
  local name="$1"
  case "$name" in
    *-scout|flow-gap-analyst|quality-auditor) return 0 ;;
    *) return 1 ;;
  esac
}

# ─── Clean & recreate ────────────────────────────────────────────────────────

echo -e "${BLUE}Cleaning codex/ directory...${NC}"
rm -rf "$CODEX_DIR"
mkdir -p "$CODEX_DIR/skills" "$CODEX_DIR/agents"

# ─── 1. Copy & patch skills ──────────────────────────────────────────────────

echo -e "${BLUE}Generating skills...${NC}"
skill_count=0

for skill_dir in "$SRC_SKILLS"/*/; do
  [ -d "$skill_dir" ] || continue
  skill=$(basename "$skill_dir")
  cp -R "${skill_dir%/}" "$CODEX_DIR/skills/"
  skill_count=$((skill_count + 1))
done

# --- RENAME: 'browser' → 'agent-browser' in Codex mirror only ────────────────
# OpenAI ships a bundled @browser skill in Codex desktop (in-app browser for
# localhost / file:// previews). Renaming ours to @agent-browser prevents the
# collision. Claude Code and Droid keep 'browser' unchanged (no collision
# there).
if [ -d "$CODEX_DIR/skills/browser" ]; then
  mv "$CODEX_DIR/skills/browser" "$CODEX_DIR/skills/agent-browser"
  browser_skill="$CODEX_DIR/skills/agent-browser/SKILL.md"

  # Patch frontmatter name
  sed -i.bak -e 's/^name: browser$/name: agent-browser/' "$browser_skill"
  rm -f "${browser_skill}.bak"

  # Insert Codex-specific preface after the frontmatter block.
  # Explains when to use @browser (OpenAI iab) vs @agent-browser (ours).
  awk '
    /^---$/ { fm++; print; next }
    fm == 2 && !inserted {
      print ""
      print "> **Codex note — Browser Use vs this skill:** Codex **desktop** (v0.124+) bundles a **Browser Use** plugin (invoke `$browser-use <task>`) controlling its in-app browser. Scope is narrow: `localhost`, `127.0.0.1`, `::1`, `file://`, current in-app tab. No cookies, no auth, no extensions, no production sites, no Electron apps, no mobile sims. For those narrow cases, delegate: use `$browser-use` directly, or just describe the task in prose (Codex routes natural-language plugin calls). Use **this skill** (`$agent-browser` or prose triggers listed above) for everything outside that scope — production sites, authenticated flows, cookies/saved sessions, Electron apps (VS Code / Slack / Figma / etc), iOS Simulator, proxies, headed browsers, video recording, visual diff. In **Codex CLI** (no desktop app, no in-app browser), always use this skill — Browser Use is not available there."
      print ""
      inserted = 1
    }
    { print }
  ' "$browser_skill" > "${browser_skill}.tmp" && mv "${browser_skill}.tmp" "$browser_skill"
fi

# --- PATH patches (all .md files) ---
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  # Add $HOME/.codex fallback to FLOWCTL assignment
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl|g' \
    "$f"

  # After every FLOWCTL= line, insert local fallback (if not already present)
  # Use awk for multi-line insert (sed portability issues on macOS)
  awk '
    /^FLOWCTL=.*scripts\/flowctl/ && !seen[$0]++ {
      print
      print "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\""
      next
    }
    { print }
  ' "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"

  # Template/script path patches
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-ralph-init/templates|~/.codex/templates/flow-next-ralph-init|g' \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-worktree-kit/scripts|~/.codex/scripts|g' \
    "$f"

  # plugin.json path: primary → .codex-plugin, fallback → .claude-plugin
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/\.claude-plugin/plugin\.json|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json|g' \
    -e 's|\.factory-plugin/plugin\.json|.claude-plugin/plugin.json|g' \
    "$f"

  rm -f "${f}.bak"
done

# --- STRUCTURAL: Task tool → agent invocation ---

# flow-next-work: phases.md
phases="$CODEX_DIR/skills/flow-next-work/phases.md"
if [ -f "$phases" ]; then
  # Replace section 3c with agent invocation
  start_line=$(grep -n "^### 3c\. Spawn Worker" "$phases" | cut -d: -f1)
  end_line=$(grep -n "^### 3d\." "$phases" | cut -d: -f1)
  if [ -n "$start_line" ] && [ -n "$end_line" ]; then
    end_line=$((end_line - 1))
    head -n $((start_line - 1)) "$phases" > "${phases}.tmp"
    cat >> "${phases}.tmp" << 'SECTION3C'
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

SECTION3C
    tail -n +$end_line "$phases" >> "${phases}.tmp"
    mv "${phases}.tmp" "$phases"
  fi

  # Text replacements
  sed -i.bak \
    -e 's/Use the Task tool to spawn a `worker` subagent/Use the worker agent role/g' \
    -e 's/spawn a worker subagent with fresh context/use the worker agent with fresh context/g' \
    -e 's/spawn a worker subagent/use the worker agent/g' \
    -e 's/After worker returns/After the worker agent returns/g' \
    -e 's/the worker failed/the worker agent failed/g' \
    -e 's/Use the Task tool to spawn the `plan-sync` subagent/Use the plan_sync agent/g' \
    -e 's/spawn the `plan-sync` subagent/use the plan_sync agent/g' \
    -e 's/quality auditor subagent/quality_auditor agent/g' \
    -e 's/Task flow-next:quality-auditor/Use the quality_auditor agent/g' \
    -e 's/spawn worker/run worker agent/g' \
    -e 's/\*\*For each task\*\*, spawn a worker subagent with fresh context/**For each task**, use the worker agent with fresh context/g' \
    "$phases"
  rm -f "${phases}.bak"
fi

# flow-next-work: SKILL.md
work_skill="$CODEX_DIR/skills/flow-next-work/SKILL.md"
if [ -f "$work_skill" ]; then
  sed -i.bak \
    -e 's/worker subagent with fresh context/worker agent with fresh context/g' \
    -e 's/worker subagent/worker agent/g' \
    -e 's/Worker subagent/Worker agent/g' \
    -e 's/Each task is implemented by a `worker` subagent/Each task is implemented by the `worker` agent role/g' \
    -e 's/worker handles/worker agent handles/g' \
    -e 's/The worker invokes/The worker agent invokes/g' \
    "$work_skill"
  rm -f "${work_skill}.bak"
fi

# flow-next-plan: steps.md
plan_steps="$CODEX_DIR/skills/flow-next-plan/steps.md"
if [ -f "$plan_steps" ]; then
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
    "$plan_steps"
  rm -f "${plan_steps}.bak"
fi

# flow-next-plan: SKILL.md
plan_skill="$CODEX_DIR/skills/flow-next-plan/SKILL.md"
if [ -f "$plan_skill" ]; then
  sed -i.bak \
    -e 's/launch ALL scouts listed in steps.md in ONE parallel Task call/launch ALL scout agents listed in steps.md in parallel/g' \
    -e 's/Do NOT skip scouts or run them sequentially/Do NOT skip scouts or run them sequentially. Codex will spawn them as parallel multi-agent threads/g' \
    "$plan_skill"
  rm -f "${plan_skill}.bak"
fi

# flow-next-prime: workflow.md
prime_wf="$CODEX_DIR/skills/flow-next-prime/workflow.md"
if [ -f "$prime_wf" ]; then
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
    "$prime_wf"
  rm -f "${prime_wf}.bak"
fi

# --- BEHAVIORAL: RP warnings for review skills ---
RP_WARNING='
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

6. **Exit code 0 = success** - When the command finishes, check the exit code. If it is 0, it worked.

**If a command has been running for less than 15 minutes, WAIT. Do not retry. Do not output <promise>RETRY</promise>.**

---
'

for skill in flow-next-impl-review flow-next-plan-review flow-next-epic-review; do
  wf="$CODEX_DIR/skills/$skill/workflow.md"
  if [ -f "$wf" ]; then
    { head -1 "$wf"; echo "$RP_WARNING"; tail -n +2 "$wf"; } > "${wf}.tmp"
    mv "${wf}.tmp" "$wf"
  fi
  sk="$CODEX_DIR/skills/$skill/SKILL.md"
  if [ -f "$sk" ]; then
    sed -i.bak \
      -e 's|setup-review|setup-review (5-15 min, DO NOT RETRY)|g' \
      -e 's|chat-send|chat-send (2-10 min, DO NOT RETRY)|g' \
      "$sk"
    rm -f "${sk}.bak"
  fi
done

# --- NAMING: claude-md-scout → agents-md-scout ---
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  sed -i.bak \
    -e 's/claude-md-scout/agents-md-scout/g' \
    -e 's/claude_md_scout/agents_md_scout/g' \
    "$f"
  rm -f "${f}.bak"
done

# Remove .DS_Store and other cruft
find "$CODEX_DIR" -name ".DS_Store" -delete 2>/dev/null || true

# --- UI metadata: agents/openai.yaml for key skills ---
generate_openai_yaml() {
  local skill="$1" display="$2" desc="$3" color="$4" implicit="$5"
  local prompt="${6:-}"
  local dir="$CODEX_DIR/skills/$skill/agents"
  mkdir -p "$dir"
  {
    echo "interface:"
    echo "  display_name: \"$display\""
    echo "  short_description: \"$desc\""
    echo "  brand_color: \"$color\""
    [ -n "$prompt" ] && echo "  default_prompt: \"$prompt\""
    echo "policy:"
    echo "  allow_implicit_invocation: $implicit"
  } > "$dir/openai.yaml"
}

# Workflow skills (blue, explicit)
generate_openai_yaml "flow-next-plan"      "Flow Plan"      "Create structured build plans from feature requests" "#3B82F6" false "Plan out this feature: "
generate_openai_yaml "flow-next-work"      "Flow Work"      "Execute planned tasks with worker subagents"          "#3B82F6" false "Work on: "
generate_openai_yaml "flow-next-interview" "Flow Interview" "Deep Q&A to refine specs and requirements"            "#3B82F6" false
generate_openai_yaml "flow-next-setup"     "Flow Setup"     "Initialize flow-next in current project"              "#3B82F6" false

# Review skills (red, explicit)
generate_openai_yaml "flow-next-impl-review" "Flow Implementation Review" "Carmack-level code review via RepoPrompt"  "#EF4444" false
generate_openai_yaml "flow-next-plan-review" "Flow Plan Review"           "Carmack-level plan review via RepoPrompt"  "#EF4444" false
generate_openai_yaml "flow-next-epic-review" "Flow Epic Review"           "Verify epic implementation matches spec"   "#EF4444" false

# Utility skills (blue/amber, implicit allowed)
generate_openai_yaml "flow-next"       "Flow Tasks" "Manage .flow/ tasks and epics"                           "#3B82F6" true
generate_openai_yaml "flow-next-prime" "Flow Prime" "Comprehensive codebase assessment for agent readiness"    "#F59E0B" false

openai_yaml_count=$(find "$CODEX_DIR/skills" -name "openai.yaml" | wc -l | tr -d ' ')
echo -e "  ${GREEN}✓${NC} $openai_yaml_count openai.yaml metadata files generated"

echo -e "  ${GREEN}✓${NC} $skill_count skills generated"

# ─── 2. Convert agents (.md → .toml) ─────────────────────────────────────────

echo -e "${BLUE}Generating agents...${NC}"
agent_count=0

for md_file in "$SRC_AGENTS"/*.md; do
  [ -f "$md_file" ] || continue
  basename_raw="$(basename "${md_file%.md}")"
  codex_name=$(rename_agent "$basename_raw")

  # Parse YAML frontmatter
  name="" description="" model=""
  in_frontmatter=0 frontmatter_done=0
  body=""

  while IFS= read -r line; do
    if [ "$frontmatter_done" = "1" ]; then
      body+="$line"$'\n'
      continue
    fi
    if [ "$line" = "---" ]; then
      if [ "$in_frontmatter" = "0" ]; then in_frontmatter=1; continue; fi
      frontmatter_done=1; continue
    fi
    if [ "$in_frontmatter" = "1" ]; then
      case "$line" in
        name:*)        name="${line#name: }"; name="${name#name:}"; name="$(echo "$name" | xargs)" ;;
        description:*) description="${line#description: }"; description="${description#description:}"; description="$(echo "$description" | xargs)" ;;
        model:*)       model="${line#model: }"; model="${model#model:}"; model="$(echo "$model" | xargs)" ;;
      esac
    fi
  done < "$md_file"

  # Map model
  codex_model=$(map_model "$model" "$codex_name")
  sandbox=$(sandbox_for "$codex_name")

  # Clean body: strip leading/trailing blank lines
  body="$(echo "$body" | awk 'NF{p=1} p')"
  body="$(echo "$body" | awk '{a[NR]=$0} END{for(i=NR;i>=1;i--) if(a[i]!=""){for(j=1;j<=i;j++) print a[j]; break}}')"

  # Patch body for agents-md-scout
  if [ "$basename_raw" = "claude-md-scout" ]; then
    body="$(echo "$body" | sed \
      -e 's/CLAUDE\.md/AGENTS.md/g' \
      -e 's/claude\.md/agents.md/g' \
      -e 's/Claude Code/Codex/g')"
    description="Used by /flow-next:prime to analyze AGENTS.md quality and completeness. Do not invoke directly."
  fi

  # Escape backslashes for TOML triple-quoted strings
  body="$(echo "$body" | sed 's/\\/\\\\/g')"

  # Write .toml
  toml="$CODEX_DIR/agents/$codex_name.toml"
  {
    echo "# Auto-generated by sync-codex.sh from ${basename_raw}.md — do not edit manually"
    echo "name = \"$codex_name\""
    echo "description = \"$description\""
    if [ -n "$codex_model" ]; then
      echo "model = \"$codex_model\""
      if model_supports_reasoning "$codex_model"; then
        echo "model_reasoning_effort = \"$CODEX_REASONING_EFFORT\""
      fi
    else
      echo "# model: inherited from parent"
    fi
    echo "sandbox_mode = \"$sandbox\""

    # Nicknames for scouts/analysts
    nicks=$(nicknames_for "$codex_name")
    if [ -n "$nicks" ]; then
      echo "nickname_candidates = $nicks"
    fi

    echo ""
    echo "developer_instructions = \"\"\""
    echo "$body"
    echo "\"\"\""
  } > "$toml"

  agent_count=$((agent_count + 1))
done

echo -e "  ${GREEN}✓${NC} $agent_count agents generated"

# ─── 3. Generate hooks.json ──────────────────────────────────────────────────

echo -e "${BLUE}Generating hooks.json...${NC}"

# Build Codex hooks from canonical source:
# - Keep: PreToolUse (Bash only), PostToolUse (Bash only), Stop
# - Drop: SubagentStop, Edit/Write matchers
# - Add: python3 explicit, statusMessage fields
cat > "$CODEX_DIR/hooks.json" << 'HOOKS_EOF'
{
  "description": "Ralph workflow guards for Codex - only active when FLOW_RALPH=1 and ralph-init has been run",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Execute",
        "hooks": [
          {
            "type": "command",
            "command": "[ ! -f scripts/ralph/hooks/ralph-guard.py ] || python3 scripts/ralph/hooks/ralph-guard.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|Execute",
        "hooks": [
          {
            "type": "command",
            "command": "[ ! -f scripts/ralph/hooks/ralph-guard.py ] || python3 scripts/ralph/hooks/ralph-guard.py",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "[ ! -f scripts/ralph/hooks/ralph-guard.py ] || python3 scripts/ralph/hooks/ralph-guard.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
HOOKS_EOF

echo -e "  ${GREEN}✓${NC} hooks.json generated"

# ─── Validation ───────────────────────────────────────────────────────────────

echo -e "${BLUE}Validating...${NC}"
errors=0

# Count skills
actual_skills=$(find "$CODEX_DIR/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
if [ "$actual_skills" != "$skill_count" ]; then
  echo -e "  ${RED}✗${NC} Expected $skill_count skills, found $actual_skills"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} $actual_skills skills"
fi

# Count agents
actual_agents=$(find "$CODEX_DIR/agents" -name "*.toml" | wc -l | tr -d ' ')
if [ "$actual_agents" != "$agent_count" ]; then
  echo -e "  ${RED}✗${NC} Expected $agent_count agents, found $actual_agents"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} $actual_agents agents"
fi

# Validate TOML files parse (basic: check for required keys)
toml_errors=0
for toml in "$CODEX_DIR/agents"/*.toml; do
  if ! grep -q 'developer_instructions' "$toml" 2>/dev/null; then
    echo -e "  ${RED}✗${NC} $(basename "$toml") missing developer_instructions"
    toml_errors=$((toml_errors + 1))
  fi
done
if [ "$toml_errors" -eq 0 ]; then
  echo -e "  ${GREEN}✓${NC} All .toml files have required keys"
else
  errors=$((errors + toml_errors))
fi

# Validate hooks.json
if python3 -c "import json; json.load(open('$CODEX_DIR/hooks.json'))" 2>/dev/null; then
  echo -e "  ${GREEN}✓${NC} hooks.json valid JSON"
else
  echo -e "  ${RED}✗${NC} hooks.json invalid JSON"
  errors=$((errors + 1))
fi

# Check no bare CLAUDE_PLUGIN_ROOT without fallback in skills
bare_refs=$( { grep -r 'CLAUDE_PLUGIN_ROOT}/' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v 'CLAUDE_PLUGIN_ROOT:-' || true; } | { grep -v '\.codex' || true; } | wc -l | tr -d ' ')
if [ "$bare_refs" != "0" ]; then
  echo -e "  ${YELLOW}!${NC} $bare_refs bare CLAUDE_PLUGIN_ROOT refs (may need patching)"
else
  echo -e "  ${GREEN}✓${NC} No bare CLAUDE_PLUGIN_ROOT refs"
fi

# Check no "Task flow-next:" in codex skills
task_refs=$( { grep -r 'Task flow-next:' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$task_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $task_refs 'Task flow-next:' refs remain in codex/skills/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No 'Task flow-next:' refs"
fi

# Validate openai.yaml files
yaml_count=$(find "$CODEX_DIR/skills" -name "openai.yaml" | wc -l | tr -d ' ')
if [ "$yaml_count" -ge 9 ]; then
  echo -e "  ${GREEN}✓${NC} $yaml_count openai.yaml files"
else
  echo -e "  ${RED}✗${NC} Expected >= 9 openai.yaml files, found $yaml_count"
  errors=$((errors + 1))
fi

# Validate openai.yaml content (each must have interface + policy keys)
yaml_errors=0
for yf in $(find "$CODEX_DIR/skills" -name "openai.yaml"); do
  if ! grep -q 'interface:' "$yf" || ! grep -q 'policy:' "$yf"; then
    echo -e "  ${RED}✗${NC} $(dirname "$(dirname "$yf")" | xargs basename)/agents/openai.yaml missing required keys"
    yaml_errors=$((yaml_errors + 1))
  fi
done
if [ "$yaml_errors" -eq 0 ]; then
  echo -e "  ${GREEN}✓${NC} All openai.yaml files have required keys"
else
  errors=$((errors + yaml_errors))
fi

# Check claude-md-scout renamed (exclude provenance comments in .toml headers)
claude_md_refs=$( { grep -r 'claude-md-scout' "$CODEX_DIR/" 2>/dev/null || true; } | { grep -v '# Auto-generated' || true; } | wc -l | tr -d ' ')
if [ "$claude_md_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $claude_md_refs 'claude-md-scout' refs remain"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} claude-md-scout fully renamed to agents-md-scout"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────

echo
if [ "$errors" -gt 0 ]; then
  echo -e "${RED}Sync completed with $errors error(s)${NC}"
  exit 1
fi

echo -e "${GREEN}Sync complete:${NC} $skill_count skills, $agent_count agents, hooks.json"
echo -e "  ${BLUE}Output:${NC} plugins/flow-next/codex/"
