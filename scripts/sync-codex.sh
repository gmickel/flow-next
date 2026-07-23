#!/bin/bash
# Generate pre-built Codex files from canonical skills/ and agents/ sources.
# Output: plugins/flow-next/codex/{skills/,agents/}
# (No hooks.json: Ralph hooks are opt-in via ralph-init project settings, not the mirror.)
#
# Idempotent — running twice produces identical output.
# Run after modifying skills/ or agents/ and commit the result.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$REPO_ROOT/plugins/flow-next"
CODEX_DIR="$PLUGIN_DIR/codex"
SRC_SKILLS="$PLUGIN_DIR/skills"
SRC_AGENTS="$PLUGIN_DIR/agents"

# Model defaults (same as install-codex.sh).
# Precedence (fn-115.3, mirror-regen only): env > models.roles scout pin > baseline.
# Role map is read from the dogfood/repo .flow/config.json when present; absent
# or unparseable keeps the hardcoded baseline. No runtime coupling - env still
# wins for one-shot overrides.
_SCOUT_INTELLIGENT_BASELINE="gpt-5.5"
_SCOUT_FAST_BASELINE="gpt-5.4-mini"

# Read models.roles.<role>.codex model id (strip optional :effort). Silent on miss.
_role_map_scout_model() {
  local role="$1"
  local cfg="$REPO_ROOT/.flow/config.json"
  [ -f "$cfg" ] || return 0
  python3 -c '
import json, sys
role = sys.argv[1]
path = sys.argv[2]
try:
    data = json.load(open(path, encoding="utf-8"))
except Exception:
    sys.exit(0)
pin = ((data.get("models") or {}).get("roles") or {}).get(role) or {}
raw = pin.get("codex")
if raw is None:
    sys.exit(0)
text = str(raw).strip()
if not text:
    sys.exit(0)
# model or model:effort — scout map only needs the model id
print(text.split(":", 1)[0].strip())
' "$role" "$cfg" 2>/dev/null || true
}

_resolve_scout_pin() {
  # $1 = role (scoutFast|scoutIntelligent), $2 = env value (may be empty), $3 = baseline
  local role="$1"
  local env_val="$2"
  local baseline="$3"
  if [ -n "$env_val" ]; then
    printf '%s\n' "$env_val"
    return
  fi
  local pin
  pin="$(_role_map_scout_model "$role")"
  if [ -n "$pin" ]; then
    printf '%s\n' "$pin"
    return
  fi
  printf '%s\n' "$baseline"
}

CODEX_MODEL_INTELLIGENT="$(_resolve_scout_pin scoutIntelligent "${CODEX_MODEL_INTELLIGENT:-}" "$_SCOUT_INTELLIGENT_BASELINE")"
CODEX_MODEL_FAST="$(_resolve_scout_pin scoutFast "${CODEX_MODEL_FAST:-}" "$_SCOUT_FAST_BASELINE")"
# Default reasoning effort for scout/analyst/editorial subagents.
# Review-shaped agents (quality-auditor) override to a higher tier — see reasoning_effort_for().
CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-medium}"
CODEX_REASONING_EFFORT_AUDITOR="${CODEX_REASONING_EFFORT_AUDITOR:-high}"
# fn-97: OPT-IN worker pin for the Codex mirror. Default is EMPTY = the worker
# keeps `inherit` (the Codex user's session model rules, same as the Claude-side
# worker) - flow-next never hardcodes a model opinion into generated config;
# routing opinions belong to the prompted layer (the AGENTS.md model table).
# To pin (eval-motivated recommendation: terra-medium matched gpt-5.6-sol
# hidden-suite correctness at ~2/3 wall-clock on frontier-authored specs,
# 2026-07-14 eval, n=3), set at sync time:
#   CODEX_MODEL_WORKER=gpt-5.6-terra CODEX_REASONING_EFFORT_WORKER=medium ./scripts/sync-codex.sh
CODEX_MODEL_WORKER="${CODEX_MODEL_WORKER:-}"
CODEX_REASONING_EFFORT_WORKER="${CODEX_REASONING_EFFORT_WORKER:-}"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────────────

# Scouts that need full intelligence (reasoning/judgment, not just scanning).
# repo/context/docs/github/practice were opus-on-Claude, downgraded to sonnet after a
# verified A/B (fn-84 fleet review — sonnet held quality). Codex has only INTELLIGENT/FAST,
# and FAST (gpt-5.4-mini) was NOT tested, so keep them INTELLIGENT (gpt-5.5) here = no Codex
# regression; the Claude-side opus→sonnet cut is the verified saving.
INTELLIGENT_SCOUTS="spec-scout agents-md-scout docs-gap-scout repo-scout context-scout docs-scout github-scout practice-scout plan-sync flow-gap-analyst"
# Agents that stay on opus in Claude Code (bug/gap detection = horsepower; failures invisible)
OPUS_AGENTS="quality-auditor"

rename_agent() {
  case "$1" in
    claude-md-scout) echo "agents-md-scout" ;;
    *) echo "$1" ;;
  esac
}

map_model() {
  local claude_model="$1" agent_name="${2:-}"
  # fn-97: worker pin is OPT-IN - only overrides `inherit` when the user set
  # CODEX_MODEL_WORKER at sync time (see above). Everything else keeps the
  # FAST/INTELLIGENT tier mapping below.
  if [ "$agent_name" = "worker" ] && [ -n "$CODEX_MODEL_WORKER" ]; then
    echo "$CODEX_MODEL_WORKER"
    return
  fi
  # fn-89: tracker-runner runs the SESSION model on Codex (Tier B spawn
  # inheritance; subagent model steering is unreliable on MAv2) - no pin.
  if [ "$agent_name" = "tracker-runner" ]; then
    echo ""
    return
  fi
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

# Per-agent reasoning effort. Review-shaped agents (quality-auditor) need
# higher reasoning than scout/editorial agents — they're a second pair of
# eyes on uncommitted changes, so undershooting risks missed regressions.
reasoning_effort_for() {
  case "$1" in
    quality-auditor) echo "$CODEX_REASONING_EFFORT_AUDITOR" ;;
    worker)          echo "${CODEX_REASONING_EFFORT_WORKER:-$CODEX_REASONING_EFFORT}" ;;
    *)               echo "$CODEX_REASONING_EFFORT" ;;
  esac
}

# Determine sandbox mode for an agent
sandbox_for() {
  local name="$1"
  case "$name" in
    worker|plan-sync) echo "workspace-write" ;;
    tracker-runner)   echo "workspace-write" ;;
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
    spec-scout)           echo '["Strategist", "Planner", "Coordinator"]' ;;
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

# Mirror canonical templates dir (R20: codex picks up templates/spec.md). Skills
# cross-link `../../templates/spec.md` from `skills/<name>/<file>.md` — after
# this copy the same relative path resolves to the mirrored copy at
# `codex/templates/spec.md` (2 levels up from `codex/skills/<name>/`).
if [ -d "$PLUGIN_DIR/templates" ]; then
  cp -R "$PLUGIN_DIR/templates" "$CODEX_DIR/"
fi

# Mirror canonical references dir (fn-62.2: shared disclosure files such as
# references/html-artifacts.md, loaded by skills only when the matching config
# gate is on). Same shape as the templates copy above: skills cite the file by
# repo-relative path; in the mirror, `../../references/<name>.md` from
# `codex/skills/<name>/<file>.md` resolves to `codex/references/<name>.md`.
# Reference files are tool-name-agnostic by contract, so NO rewrite pass below
# touches them — the mirror copy must stay byte-identical to canonical.
if [ -d "$PLUGIN_DIR/references" ]; then
  cp -R "$PLUGIN_DIR/references" "$CODEX_DIR/"
fi

# --- flow-next-drive: Codex Browser-Use preface ──────────────────────────────
# The canonical skill is `flow-next-drive` (no `@browser` collision — the old
# `browser` → `agent-browser` rename is gone; the copy loop above already
# mirrors the canonical dir name). We still want a Codex-only note: Codex
# desktop bundles a narrow-scope Browser Use plugin, and users should know when
# to delegate to it vs. drive with this skill. Inject that preface after the
# frontmatter; canonical (Claude/Droid) stays unchanged.
drive_skill="$CODEX_DIR/skills/flow-next-drive/SKILL.md"
if [ -f "$drive_skill" ]; then
  # Insert Codex-specific preface after the frontmatter block.
  awk '
    /^---$/ { fm++; print; next }
    fm == 2 && !inserted {
      print ""
      print "> **Codex note — Browser Use vs this skill:** Codex **desktop** (v0.124+) bundles a **Browser Use** plugin (invoke `$browser-use <task>`) controlling its in-app browser. Scope is narrow: `localhost`, `127.0.0.1`, `::1`, `file://`, current in-app tab. No cookies, no auth, no extensions, no production sites, no Electron apps, no mobile sims. For those narrow cases, delegate: use `$browser-use` directly, or just describe the task in prose (Codex routes natural-language plugin calls). Use **this skill** (the prose triggers listed above — `check the page`, `verify UI`, `test this app`, etc.) for everything outside that scope — production sites, authenticated flows, cookies/saved sessions, Electron / native apps, iOS Simulator, proxies, headed browsers, video recording, visual diff. In **Codex CLI** (no desktop app, no in-app browser), always use this skill — Browser Use is not available there."
      print ""
      inserted = 1
    }
    { print }
  ' "$drive_skill" > "${drive_skill}.tmp" && mv "${drive_skill}.tmp" "$drive_skill"
fi

# --- PATH patches (all .md files) ---
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  # Rewrite FLOWCTL assignment to the direct $HOME/.codex form.
  # Inside Codex, neither DROID_PLUGIN_ROOT nor CLAUDE_PLUGIN_ROOT is ever set —
  # only $HOME/.codex resolves (install-codex.sh's canonical target). The old
  # `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}` chain was dead
  # code in the mirror. See fn-48.1 (R4a).
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl|$HOME/.codex/scripts/flowctl|g' \
    "$f"

  # fn-48.6: canonical files now use a once-per-skill `PLUGIN_ROOT` prelude
  # (e.g. flow-next-ralph-init/SKILL.md) to collapse 10+ inline expansions.
  # Rewrite the PLUGIN_ROOT assignment to the direct Codex form so subsequent
  # `$PLUGIN_ROOT/...` references resolve. Then path-remap specific subtrees
  # that have different on-disk layouts in the Codex install (templates land
  # at `~/.codex/templates/<skill>` rather than `~/.codex/skills/<skill>/templates`).
  sed -i.bak \
    -e 's|PLUGIN_ROOT="\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}"|PLUGIN_ROOT="$HOME/.codex"|g' \
    "$f"

  # After every FLOWCTL= line, insert local fallback — IDEMPOTENT.
  # Canonical skill preambles may ALREADY carry the
  # `[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"` fallback on the line
  # directly after the FLOWCTL= assignment (added for the Cursor / env-var-less
  # path, where neither DROID_PLUGIN_ROOT nor CLAUDE_PLUGIN_ROOT resolves). Only
  # inject when the next line is NOT already that fallback — otherwise the mirror
  # gets a duplicate. Mirrors the agents-block guard below. (awk for multi-line
  # insert: sed portability issues on macOS.)
  awk '
    function flush_pending(   stripped) {
      if (pending) {
        stripped = nextline
        sub(/^[[:space:]]+/, "", stripped)
        if (stripped != "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\"") {
          print fallback
        }
        pending = 0
      }
    }
    /^FLOWCTL=.*scripts\/flowctl/ && !seen[$0]++ {
      print
      fallback = "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\""
      pending = 1
      next
    }
    {
      nextline = $0
      flush_pending()
      print
    }
    END { if (pending) print fallback }
  ' "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"

  # Template/script path patches — both legacy inline form and the new
  # fn-48.6 `$PLUGIN_ROOT/...` consolidated form.
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-ralph-init/templates|~/.codex/templates/flow-next-ralph-init|g' \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-worktree-kit/scripts|~/.codex/scripts|g' \
    -e 's|\$PLUGIN_ROOT/skills/flow-next-ralph-init/templates|~/.codex/templates/flow-next-ralph-init|g' \
    -e 's|\$PLUGIN_ROOT/skills/flow-next-worktree-kit/scripts|~/.codex/scripts|g' \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/|$HOME/.codex/skills/|g' \
    -e 's|\$PLUGIN_ROOT/skills/|$HOME/.codex/skills/|g' \
    "$f"
  # The two generic /skills/ rules above are a catch-all for skill-local asset
  # paths (e.g. resolve-pr's SCRIPTS dir) — install-codex.sh copies each skill
  # dir wholesale to ~/.codex/skills/, so that root always resolves. Specific
  # destinations (ralph-init templates, worktree-kit scripts) are rewritten
  # first and therefore win. $HOME (not ~) so the path expands inside quotes.

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
  # fn-123 R5: the 3d.0 host-deferred gate is an ACTIONABLE invocation — rewrite
  # the canonical slash-command to the Codex skill name (passive /flow-next:
  # mentions elsewhere stay; this one the agent must execute).
  sed -i.bak 's|`/flow-next:impl-review <task-id> --base \$BASE_COMMIT --review=host`|`$flow-next-impl-review <task-id> --base $BASE_COMMIT --review=host`|g' "$phases"
  rm -f "${phases}.bak"

  # Replace section 3c with agent invocation
  start_line=$(grep -n "^### 3c\. Spawn Worker" "$phases" | cut -d: -f1)
  end_line=$(grep -n "^### 3d\." "$phases" | cut -d: -f1)
  if [ -n "$start_line" ] && [ -n "$end_line" ]; then
    end_line=$((end_line - 1))
    head -n $((start_line - 1)) "$phases" > "${phases}.tmp"
    cat >> "${phases}.tmp" << 'SECTION3C'
### 3c. Run Worker Agent(s)

Use the **worker** agent role to implement each selected task. For a multi-task
wave, create one isolated mutable workspace and task-unique summary/evidence
paths per worker, then dispatch the selected workers concurrently. For a
one-task wave, use the existing single-worker path.

The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status, task-relevant glossary terms when populated)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

The last two responsibilities apply only to the existing single-worker path. A
parallel-wave worker defers review and all shared lifecycle work to the
conductor after integration.

**`REVIEW_MODE` is per-task, not a fixed run-wide value.** Resolve it for THIS task: if the user
passed an explicit `--review=<backend>` to `/flow-next:work`, use that (a deliberate run-wide override
wins for every task); OTHERWISE resolve task-aware — `REVIEW_MODE=$($FLOWCTL review-backend "$TASK_ID")`
— so a task's own `review:` override (e.g. `review: cursor:...` under a `codex` project default) selects
its backend rather than the project default. `none` still skips review.

**Invoke the worker:**

"Use the worker agent to implement this task:

TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: $FLOWCTL
REVIEW_MODE: none|rp|codex|copilot|cursor|host-deferred
RALPH_MODE: true|false
PARALLEL_WAVE: true|false
WORKSPACE: <isolated mutable workspace>
HANDOVER_SUMMARY: <task-unique summary path>
HANDOVER_EVIDENCE: <task-unique evidence path>

Follow your phases exactly."

Set `PARALLEL_WAVE: true` only for a concurrently dispatched multi-task wave.
Those workers implement, test, commit, and return their workspace, commits, and
the exact handover paths. They do **not** call `flowctl done`, project tracker
state, invoke plan-sync, run impl-review, or integrate their own commit. This
host-deferred shape is independent of `REVIEW_MODE`; the conductor preserves
the resolved backend and applies it after integration. The prompt fields are an
internal handoff, not a public CLI or stored schema.

**Host review routes OUTSIDE the worker (fn-123 R5) — and gates BEFORE done.** When the resolved review mode is \`host\`, pass \`REVIEW_MODE: host-deferred\`: the worker skips review dispatch AND defers \`flowctl done\` (returns with the task still in_progress + summary/evidence files written). The conductor then runs \`$flow-next-impl-review <task-id> --review=host\` as the mandatory gate and only on SHIP runs \`flowctl done\` with the worker-prepared summary/evidence plus the review receipt; NEEDS_WORK drives the bounded fix loop before done.

**Worker returns**: Summary of implementation, files changed, test results,
review verdict on the single-worker path; or task ID, workspace, commits, and
task-unique handover paths on the parallel path.

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

# canonical templates/usage.md (mirrored to codex/templates/) — Codex command-name syntax
# This template is copied into projects as `.flow/usage.md` by setup Step 4
# (which byte-compares `.flow/usage.md` against it on re-runs). On Codex the
# skill reads THIS mirror copy, and Codex project docs use `$flow-next-<cmd>`
# names, not `/flow-next:<cmd>` (same per-platform split the agents-md-snippet
# vs claude-md-snippet templates and workflow.md's model-routing substitution
# encode). Rewrite command tokens in the mirror template only — skill prose
# elsewhere keeps `/flow-next:` (agents resolve those contextually; this file
# is a user-facing project doc where a literal `/flow-next:work` invocation
# would hit an unavailable command). Validation below guards regression.
setup_usage="$CODEX_DIR/templates/usage.md"
if [ -f "$setup_usage" ]; then
  sed -i.bak -E 's|/flow-next:([a-z-]+)|$flow-next-\1|g' "$setup_usage"
  rm -f "${setup_usage}.bak"
fi

# fn-121: plugin mode is Claude-Code-only (bin PATH injection). The Codex mirror
# must never OFFER it: strip the plugin-mode sections from the setup workflow,
# leaving copy mode as the only documented setup path. The per-skill pre-check
# plugin BRANCH stays in the mirror - a repo set up in plugin mode by a Claude
# Code user is still workable from Codex (its FLOWCTL preamble self-resolves),
# and the branch is inert unless .flow/meta.json says setup_mode=plugin. For the
# same reason the slim snippet TEMPLATE ships in the mirror (PR #227 review):
# the mirrored pre-check's "Refresh now" path reads it, and excluding it would
# strand a plugin-mode repo's snippet refresh when visited from Codex. Data, not
# doctrine: the file alone offers nothing. Validation below guards regression.
#
# fn-126 R4: the Codex mirror is consumed ONLY by Codex. Replace the multi-host
# Step-0 detection cascade with unconditional PLATFORM="codex" (canonical hosts
# never read this mirror; a GROK_AGENT / CURSOR_AGENT inheritance must not
# reclassify a Codex session). Hard-fail guard below enforces no host-detection
# branches in the mirror Step-0 bash fence.
setup_wf="$CODEX_DIR/skills/flow-next-setup/workflow.md"
if [ -f "$setup_wf" ]; then
  awk '
    # fn-126 R4: first ```bash under Step 0 Platform detection → unconditional codex
    /^## Step 0: Resolve plugin path and detect platform/ {in_step0=1}
    in_step0 && /^## / && !/^## Step 0:/ {in_step0=0; det_done=0}
    in_step0 && !det_done && /^```bash$/ {
      print "```bash"
      print "# Codex mirror: this workflow is consumed only by Codex."
      print "# Host detection is irrelevant — always PLATFORM=codex"
      print "# (canonical Claude-format hosts never read this mirror)."
      print "PLATFORM=\"codex\""
      skip_det=1
      det_done=1
      next
    }
    skip_det && /^```$/ {
      print
      skip_det=0
      next
    }
    skip_det {next}

    /^## Step 2b: Setup mode/ {
      print "## Existing-mode guard (before Step 3)";
      print "";
      print "Read the stamped mode before writing anything:";
      print "";
      print "```bash";
      print "CURRENT_MODE=$(jq -r '"'"'.setup_mode // empty'"'"' .flow/meta.json 2>/dev/null)";
      print "```";
      print "";
      print "When `CURRENT_MODE` is `plugin`, this repo is a Claude-Code-managed install with NO local `.flow/bin`/`.flow/templates`/`.flow/usage.md` snapshots by design. Never convert it silently: ask (plain-text numbered prompt) `Keep as-is (Recommended)` - skip Step 3, Step 4 copies, and the Step 7c stamp (set `MODE=plugin-kept`; config steps still run, and the Docs step may target AGENTS.md only - the CLAUDE.md marker block is the Claude-Code-managed rail, never touched from this host) - or `Convert to copy` - proceed normally (writes the snapshots; Step 7c stamps copy). Any other `CURRENT_MODE` value: set `MODE=copy` and continue.";
      print "";
      skip=1
    }
    /^## Step 3: Create \.flow\/bin\// {skip=0}
    /^For \*\*Claude Code in plugin mode\*\*/ {skip2=1}
    skip2 && /fall back to copy mode`/ && /^On / {skip2=0; next}
    /^### Step 7c: Stamp setup mode/ {
      print "### Step 7c: Stamp setup mode (fn-121)";
      print "";
      print "Runs after every Step 7 write, before Step 8. When the existing-mode guard chose `MODE=plugin-kept`, do NOT run the stamp - the existing `setup_mode` stays untouched (report `Setup mode: plugin (kept - managed from Claude Code)` in Step 8). Otherwise:";
      print "";
      print "```bash";
      print "\"${PLUGIN_ROOT}/scripts/flowctl\" setup-mode set copy --json";
      print "```";
      print "";
      print "Include `Setup mode: copy` in the Step 8 summary.";
      print "";
      skip3=1; next
    }
    skip3 && /^## Step 8: Print Summary/ {skip3=0}
    /^### Step 8a: Plugin-mode summary variant/ {skip4=1}
    skip || skip2 || skip3 || skip4 {next}
    /^\*\*Copy mode only .* skip to Step 4a\.\*\*$/ {next}
    {print}
  ' "$setup_wf" > "${setup_wf}.fn121tmp" && mv "${setup_wf}.fn121tmp" "$setup_wf"
  sed -i.bak \
    -e 's/continue from Step 2b — the mode gate runs on EVERY pass (PR #227 review: a same-version re-run in a plugin-mode repo must not fall straight into Step 3.s copies); copy-mode repos then flow into Step 3.s re-copy/continue from the existing-mode guard (before Step 3) — it runs on EVERY pass, then copy-mode repos flow into Step 3'"'"'s re-copy/' \
    -e '/^- \*\*Claude Code in plugin mode\*\*/d' \
    -e '/^- CLAUDE.md on \*\*Claude Code in plugin mode\*\*/d' \
    -e 's/^Choose the correct template based on platform AND mode:/Choose the correct template based on platform:/' \
    -e 's|^- \*\*Claude Code (copy mode) / Droid / Cursor\*\*|- **Claude Code / Droid / Cursor**|' \
    -e 's|^- AGENTS.md on \*\*Claude Code (copy mode) / Droid / Cursor\*\*|- AGENTS.md on **Claude Code / Droid / Cursor**|' \
    -e 's|^- CLAUDE.md (any platform, copy mode):|- CLAUDE.md (any platform):|' \
    "$setup_wf"
  rm -f "${setup_wf}.bak"
fi

# flow-next-plan: steps.md
# NOTE: no `../../templates/spec.md` → `../../../templates/spec.md` rewrite —
# the codex mirror now ships its own `codex/templates/spec.md` (sibling to
# `codex/skills/`), so `../../templates/spec.md` from `codex/skills/<name>/<file>.md`
# resolves correctly to the mirrored template. Canonical and mirror use the
# same relative path string.
plan_steps="$CODEX_DIR/skills/flow-next-plan/steps.md"
if [ -f "$plan_steps" ]; then
  sed -i.bak \
    -e 's|`flow-next:context-scout`|the `context_scout` agent|g' \
    -e 's|`flow-next:repo-scout`|the `repo_scout` agent|g' \
    -e 's|`flow-next:practice-scout`|the `practice_scout` agent|g' \
    -e 's|`flow-next:docs-scout`|the `docs_scout` agent|g' \
    -e 's|`flow-next:github-scout`|the `github_scout` agent|g' \
    -e 's|`flow-next:memory-scout`|the `memory_scout` agent|g' \
    -e 's|`flow-next:spec-scout`|the `spec_scout` agent|g' \
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

for skill in flow-next-impl-review flow-next-plan-review flow-next-spec-completion-review; do
  # Prefer the backend-split workflow-rp.md (fn-48.3+) — the RP warning only
  # applies to the RP path. If the skill hasn't been split yet, fall back to
  # the monolithic workflow.md so unaffected skills keep the warning at the
  # top of their file.
  if [ -f "$CODEX_DIR/skills/$skill/workflow-rp.md" ]; then
    wf="$CODEX_DIR/skills/$skill/workflow-rp.md"
  else
    wf="$CODEX_DIR/skills/$skill/workflow.md"
  fi
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

# --- TOOL NAMES: read-only Explore dispatch → spawn_agent (fn-100 R12) ---
# Canonical prose writes the interview fact-scout dispatch Claude-native as
# "(`Task` with `subagent_type: Explore`)". Codex spawns subagents via
# `spawn_agent` with `agent_type: explorer` (same naming as the audit
# workflow's platform table). Exact-phrase match only: the "`Task` tool with
# `subagent_type: Explore`" variants (audit platform table, capture prose)
# deliberately document the Claude Code naming inside cross-platform tables
# and must NOT be rewritten. A validation guard below hard-fails if the
# exact dispatch phrase survives in the mirror.
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  sed -i.bak \
    -e 's/`Task` with `subagent_type: Explore`/`spawn_agent` with `agent_type: explorer`/g' \
    -e 's/(sonnet on Claude Code)/(the host'"'"'s mid-tier)/g' \
    "$f"
  rm -f "${f}.bak"
done

# --- TOOL NAMES: tracker-runner dispatch → tracker_runner role (fn-89) ---
# Touchpoint gates dispatch the background runner Claude-native as
# `Task flow-next:tracker-runner` and in prose as "a background
# `tracker-runner`". Codex has no Task tool and install-codex.sh registers
# the hyphenated agent file under the underscore role key
# (agents.tracker_runner), so BOTH forms must resolve to the role name in
# the mirror (skills AND references - tracker-dispatch.md lives in
# references/). A validation guard below hard-fails if either Claude-native
# form survives.
find "$CODEX_DIR/skills" "$CODEX_DIR/references" -name "*.md" -type f 2>/dev/null | while read -r f; do
  sed -i.bak \
    -e 's|Task flow-next:tracker-runner|Use the tracker_runner agent|g' \
    -e 's|as a background `tracker-runner` per|as a background `tracker_runner` agent (Use the tracker_runner agent) per|g' \
    -e 's|a background `tracker-runner` subagent|a background `tracker_runner` agent|g' \
    -e 's|`tracker-runner`|`tracker_runner`|g' \
    "$f"
  rm -f "${f}.bak"
done

# --- TOOL NAMES: AskUserQuestion → plain-text numbered prompt (fn-45) ---
# Canonical skills use Claude-native `AskUserQuestion`. Codex's structured
# `request_user_input` errors outside Plan mode (openai/codex #10384, #11536,
# #12694 — closed without resolution as of Feb 2026), so the Codex mirror
# instead instructs the agent to render a plain-text numbered prompt with a
# final `N+1. Other — type your own answer` option, then stop and wait for
# the user's next message. The mirror never mentions `request_user_input` —
# validation guards below (R6) hard-fail if it leaks in.
#
# Order:
#   1. Strip maintainer breadcrumbs (any form — parens, bare sentence)
#   2. Strip ToolSearch references (Claude-only schema-load mechanism)
#   3. Rewrite AskUserQuestion → plain-text numbered-prompt instruction
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  # 1. Strip maintainer breadcrumbs in their original (canonical) form,
  #    BEFORE the AskUserQuestion → plain-text-numbered-prompt rewrite happens.
  #    Use python for multi-form matching (sed gets unwieldy here).
  python3 - "$f" <<'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as fp:
    text = fp.read()

# Strip parenthetical breadcrumbs (allow whitespace incl. newlines inside
# the parens — canonical authors sometimes wrap them across lines).
text = re.sub(
    r' *\(sync-codex\.sh\s+rewrites[^)]*Codex mirror\.?\)',
    '',
    text,
)
# Strip non-parenthetical sentence breadcrumbs (any leading space, the
# sentence, optional period).
text = re.sub(
    r' *sync-codex\.sh rewrites[^.\n]*Codex mirror\.?',
    '',
    text,
)

# Strip maintainer-note BULLETS about the Codex mirror generation itself
# ("- **Codex mirror** ... regenerated in fn-NN — keep this file Claude-native
# ...", "- Codex mirror is regenerated in fn-NN — keep this file Claude-native
# ..."). These are author-facing reminders that the canonical file is the
# source and the mirror is derived; they're meaningless (and self-contradictory)
# inside the already-rewritten mirror, where they'd tell the Codex agent to
# "keep this file Claude-native". Run BEFORE the AskUserQuestion rewrite so the
# `Claude-native` anchor is still present.
#
# Two concrete shapes (handle each explicitly — a single lazy regex backtracks
# unpredictably across the wrapped form):
#   The bullet may lead with a bare "Codex mirror" OR a bold-opening
#   "**Codex mirror ...**" where the bold span carries extra words before it
#   closes (e.g. "**Codex mirror is regenerated in fn-68.5**"). `(?:\*\*)?`
#   matches an OPTIONAL opening bold marker (zero or two asterisks) so both the
#   tracker-sync (bare-led) and backlog-mode (bold-led) breadcrumbs are stripped.
#   (a) two-line bullet — "- **Codex mirror** ...\n  Claude-native ...\n"
#       (line 1 opens the bullet, line 2 is a 2-space-indented continuation
#       carrying the `Claude-native` anchor).
text = re.sub(
    r'(?m)^- (?:\*\*)?Codex mirror[^\n]*\n  [^\n]*Claude-native[^\n]*\n',
    '',
    text,
)
#   (b) single-line bullet — "- **Codex mirror** ... Claude-native ...\n"
#       (both the `Codex mirror` lead and the `Claude-native` anchor on one line).
text = re.sub(
    r'(?m)^- (?:\*\*)?Codex mirror[^\n]*Claude-native[^\n]*\n',
    '',
    text,
)

with open(path, 'w') as fp:
    fp.write(text)
PYEOF

  # 2. Strip ToolSearch references — Codex doesn't use ToolSearch.
  #    Run case-insensitively. Cover parenthetical, bare-sentence,
  #    multi-line bullet, and standalone-backtick variants.
  python3 - "$f" <<'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as fp:
    text = fp.read()

# Strip parenthetical ToolSearch fallback notes (case-insensitive on the verb).
text = re.sub(
    r' *\([Cc]all `ToolSearch`[^)]*\)',
    '',
    text,
)
text = re.sub(
    r' *\([Cc]all `ToolSearch select:[^`]+`[^)]*\)',
    '',
    text,
)
text = re.sub(
    r' *\(deferred — load via `ToolSearch select:[^`]+`[^)]*\)',
    '',
    text,
)
# Strip "If <X>'s schema isn't loaded ..., call `ToolSearch` ..." sentences
# FIRST — the generic "call `ToolSearch` ..." stripper below would eat the
# suffix and leave a dangling fragment (e.g. fn-45 review observed
# `flow-next-memory-migrate/workflow.md` keeping "If <X>'s schema isn't
# loaded on Claude Code," with no completing clause).
text = re.sub(
    r"If `[^`]+`'s schema isn'?t loaded on Claude Code, call `ToolSearch`[^.\n]*\.",
    '',
    text,
)
# Belt-and-suspenders: any dangling "If <X>'s schema isn't loaded on Claude
# Code," fragment (no completing clause) left over from an earlier rewrite
# also gets stripped — keep the mirror prose self-consistent.
text = re.sub(
    r"If `[^`]+`'s schema isn'?t loaded on Claude Code,? *\n?",
    '',
    text,
)
# Strip "Call/call `ToolSearch` with ..." sentences (case-insensitive).
text = re.sub(
    r'(?:^|(?<=[.\s]))[Cc]all `ToolSearch`[^.\n]*\.',
    '',
    text,
    flags=re.MULTILINE,
)
# Strip standalone ToolSearch backtick refs in line items.
text = re.sub(
    r'`ToolSearch select:[^`]+`',
    '',
    text,
)
# Strip multi-line bullet items that mention ToolSearch with a Claude-only
# anti-pattern flavor — these don't apply on Codex.
# Pattern: dash-bullet where any line contains ToolSearch (multi-line aware).
# Match the bullet from "- **...**" through to the end of the bullet (next
# blank line OR next dash-bullet at same indent).
def strip_toolsearch_bullets(text):
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect start of a top-level bullet that contains ToolSearch in
        # the bullet body (line + continuation lines until next blank or
        # next bullet).
        if re.match(r'^- \*\*', line):
            # Collect bullet content
            bullet = [line]
            j = i + 1
            while j < len(lines) and (lines[j].startswith('  ') or lines[j] == ''):
                if lines[j] == '' and j + 1 < len(lines) and not lines[j + 1].startswith('  '):
                    break
                bullet.append(lines[j])
                j += 1
            bullet_text = '\n'.join(bullet)
            if 'ToolSearch' in bullet_text:
                # Skip — strip this bullet from output
                i = j
                continue
        out.append(line)
        i += 1
    return '\n'.join(out)

text = strip_toolsearch_bullets(text)

# Collapse double spaces that result from strips.
text = re.sub(r'  +', ' ', text)
# Collapse blank-line runs to max 2.
text = re.sub(r'\n{3,}', '\n\n', text)
# Trim trailing whitespace per line.
text = '\n'.join(line.rstrip() for line in text.split('\n'))

with open(path, 'w') as fp:
    fp.write(text)
PYEOF

  # 3. Rewrite AskUserQuestion invocations into a plain-text numbered-prompt
  #    instruction for the Codex mirror (fn-45). Distinct re.sub calls handle
  #    the canonical surface forms, longest-most-specific first so bare-token
  #    rules don't eat structured ones. Hard mandates softened to "MUST ask
  #    via the plain-text numbered prompt"; auto-fix-loop "Never use" mandates
  #    preserve semantics (token rewrite only). Frontmatter `allowed-tools:`
  #    lines keep the legacy `request_user_input` token — Codex reads
  #    agents/openai.yaml for the actual contract; the frontmatter is residue
  #    that just needs to clear the askq_refs guard.
  python3 - "$f" <<'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as fp:
    text = fp.read()

# Track whether this file referenced AskUserQuestion in prose (frontmatter
# only doesn't count — that's harmless residue). We use this flag after
# substitutions to inject the R2 instruction block exactly once.
prose_text = re.sub(r'(?ms)\A---\n.*?\n---\n', '', text)
had_ask_in_prose = bool(re.search(r'\bAskUserQuestion\b', prose_text))

# --- Longest-most-specific patterns first ----------------------------------

# A. Hard mandate "CRITICAL REQUIREMENT: You MUST use the `AskUserQuestion`
#    tool for every question." → softened mandate (R3). Used by
#    flow-next-interview/SKILL.md:217.
text = re.sub(
    r'\*\*CRITICAL REQUIREMENT\*\*: You MUST use the `AskUserQuestion` tool for every question\.',
    '**CRITICAL REQUIREMENT**: For every question, you MUST ask via the plain-text numbered prompt described below.',
    text,
)

# B. Hard mandate "**CRITICAL**: You MUST use the `AskUserQuestion` tool for
#    consent." → softened mandate (R3). Used by
#    flow-next-prime/workflow.md:194.
text = re.sub(
    r'\*\*CRITICAL\*\*: You MUST use the `AskUserQuestion` tool for consent\.',
    '**CRITICAL**: For consent, you MUST ask via the plain-text numbered prompt described below.',
    text,
)

# C. "MUST use `AskUserQuestion` tool" bullet / mandate (R3).
#    Used by flow-next-prime/workflow.md:306, SKILL.md:109 fragment.
text = re.sub(
    r'MUST use `AskUserQuestion` tool',
    'MUST ask via the plain-text numbered prompt described below',
    text,
)

# D. "ONLY ask questions via AskUserQuestion tool calls" (R3).
#    Used by flow-next-interview/SKILL.md:221.
text = re.sub(
    r'ONLY ask questions via AskUserQuestion tool calls',
    'ONLY ask via the plain-text numbered prompt',
    text,
)

# E. Anti-mandate "do NOT use AskUserQuestion tool" — used in
#    flow-next-plan/SKILL.md:117 + flow-next-ralph-init/SKILL.md:37 to tell
#    the agent "ask in plain text ad-hoc, not via the structured tool". On
#    Codex there IS no structured tool, so the negation is a tautology.
#    Strip the parenthetical entirely (along with optional surrounding
#    whitespace + parens) to keep the prose clean. Also drop the now-empty
#    leading space.
text = re.sub(
    r' *\(do NOT use AskUserQuestion tool\)',
    '',
    text,
)
# Bare-form fallback (no parens) — leave a soft replacement in case the
# anti-mandate appears outside a parenthetical somewhere.
text = re.sub(
    r'do NOT use AskUserQuestion tool',
    'ask using plain text instead of any structured prompt tool',
    text,
)

# F. Auto-fix-loop mandate "Never use AskUserQuestion in this loop" (R3
#    boundary — token rewrite only, intent preserved). Used by
#    impl-review/plan-review/spec-completion-review workflow.md + SKILL.md.
text = re.sub(
    r'Never use AskUserQuestion in this loop',
    'Never use the plain-text numbered prompt in this loop',
    text,
)

# G. "Call AskUserQuestion tool with question and options." prose
#    (flow-next-interview/SKILL.md:231).
text = re.sub(
    r'Call AskUserQuestion tool with question and options\.',
    'Render the question and options as a plain-text numbered prompt (see below).',
    text,
)

# H. Frontmatter `allowed-tools: AskUserQuestion, ...` — STRIP the token
#    entirely from the mirror. fn-45 originally rewrote it to
#    `request_user_input` on the assumption that Codex reads
#    `agents/openai.yaml` for the tool contract and treats SKILL.md
#    frontmatter as harmless residue. In practice the agent reads
#    SKILL.md frontmatter, trusts the listed tools, and calls
#    `request_user_input` — which errors out in Default mode
#    (openai/codex #10384, #11536, #12694). Stripping the token leaves
#    only tools the mirror actually uses. Clean up any leading comma or
#    trailing comma left behind so the list stays well-formed.
def _strip_aukq(match):
    head = match.group(1)
    rest = match.group(2)
    # Drop the token AND a trailing ", " if present; else drop a leading
    # ", " if it was the last item.
    if rest.startswith(', '):
        return head + rest[2:]
    if head.endswith(', '):
        return head[:-2] + rest
    return head + rest
text = re.sub(
    r'^(allowed-tools:[^\n]*?)\bAskUserQuestion\b(.*)$',
    _strip_aukq,
    text,
    flags=re.MULTILINE,
)

# I. Generic backticked invocation: `AskUserQuestion`
#    → `plain-text numbered prompt` (kept backticked for in-prose readability).
text = re.sub(
    r'`AskUserQuestion`',
    '`plain-text numbered prompt`',
    text,
)

# J. Generic "AskUserQuestion tool" (no backticks) → "plain-text numbered
#    prompt". Catches inline mentions in headings + non-backticked prose.
text = re.sub(
    r'AskUserQuestion tool',
    'plain-text numbered prompt',
    text,
)

# K. Bare AskUserQuestion (table cells, headings, residual prose). Catch-all
#    last so structured patterns above run first.
text = re.sub(
    r'\bAskUserQuestion\b',
    'plain-text numbered prompt',
    text,
)

# L. Strip Claude-only schema-loader prose left over after AskUserQuestion
#    substitution. Examples (post-substitution):
#      "Use `plain-text numbered prompt`. It's a deferred tool — call first
#       to load its schema if it isn't already in scope."
#    On Codex there is no schema to load — strip the deferred-tool sentence.
text = re.sub(
    r" It'?s a deferred tool — call first to load its schema if it isn'?t already in scope\.",
    '',
    text,
)

# L2. Strip the vestigial "Do NOT / Never just print questions as text"
#     anti-print prose. In canonical (Claude) it correctly means "use the
#     structured AskUserQuestion tool, not bare prose". After the A-K
#     rewrites turn the tool reference into the plain-text numbered prompt,
#     the same sentence becomes a self-contradiction ("ask via plain text
#     ... but do not print as text"). Drop it in the mirror. Covers:
#       1. " — Never just print questions as text" (em-dash bullet form,
#          no trailing period — appears mid-bullet, run FIRST so the
#          generic rule below doesn't leave a dangling em-dash)
#       2. " Do NOT just print questions as text." (trailing-sentence form)
#       3. " Never just print questions as text." (trailing-sentence form,
#          appears after bullet body in SKILL.md)
text = re.sub(
    r' — (?:Do NOT|Never) just print questions as text\.?',
    '',
    text,
)
text = re.sub(
    r' (?:Do NOT|Never) just print questions as text\.?',
    '',
    text,
)

# M. Strip / soften UI-shape prose that assumes a structured prompt tool.
#    "The tool provides an interactive UI." → drop the sentence (its
#    immediate sibling sentences still describe per-question structure
#    advice that translates fine to plain text).
text = re.sub(
    r'The tool provides an interactive UI\. ?',
    '',
    text,
)

# N. Structured-tool API prose — directives that reference fields and
#    concepts that only exist in Claude's AskUserQuestion JSON contract.
#    On Codex these become misleading. Translate to plain-text equivalents
#    that still convey the intent.
text = re.sub(
    r'Use `multiSelect: true` so users can pick multiple items',
    'Allow multi-select when options are not exclusive — number the options as `1.` … `N.` and ask the user to reply with the numbers (or labels) of all that apply',
    text,
)
text = re.sub(
    r'Build the questions array dynamically',
    'Build the prompt content (question text + numbered option list) dynamically',
    text,
)
text = re.sub(
    r'Use `plain-text numbered prompt` with the built questions array\.',
    'Print the prompt content built above and stop for the user\'s reply.',
    text,
)
text = re.sub(
    r'platform blocking question tool',
    'plain-text numbered prompt',
    text,
)
# Handle multi-line bold-wrapped variant like:
#     **blocking
#     question tool**
# (canonical authors sometimes wrap mid-phrase). Collapse to a single
# inline replacement.
text = re.sub(
    r'\*\*blocking\s+question tool\*\*',
    '**plain-text numbered prompt**',
    text,
)
text = re.sub(
    r'blocking question tool',
    'plain-text numbered prompt',
    text,
)
# Hyphenated form: "blocking-question tool" / "blocking-question tools".
text = re.sub(
    r'blocking-question tools?',
    'plain-text numbered prompt',
    text,
)
# Interview-skill anti-patterns that assumed structured-tool prompts.
# After fn-45, "output questions as text" IS the contract on Codex —
# the "DO NOT" bullets directly contradict the plain-text instruction.
# Strip both bullets and the "Anti-pattern (WRONG)" framing that followed
# (the literal plain-text example WAS the bad pattern under structured
# tools, but it IS the correct pattern on plain-text Codex).
text = re.sub(
    r'^- DO NOT output questions as text\n',
    '',
    text,
    flags=re.MULTILINE,
)
text = re.sub(
    r'^- DO NOT list questions in your response\n',
    '',
    text,
    flags=re.MULTILINE,
)
# "per tool call" → "per prompt turn" — the multi-question batching
# rule still applies, but framed for plain-text turns rather than
# structured tool invocations.
text = re.sub(
    r'\bper tool call\b',
    'per prompt turn',
    text,
)
# "tool call" residual mentions in bullet items / inline prose.
text = re.sub(
    r'\bin a single tool call\b',
    'in a single prompt turn',
    text,
)
text = re.sub(
    r'\btool call(s?)\b',
    r'prompt turn\1',
    text,
)
# The interview "Anti-pattern (WRONG)" example showed a plain-text
# numbered question as the wrong pattern under structured tools — on
# Codex that example IS the correct pattern. Drop the inverted framing
# block entirely (header + fenced example + "Correct pattern:" line).
text = re.sub(
    r'\*\*Anti-pattern \(WRONG\)\*\*:\n```\nQuestion 1:[^`]+```\n\n\*\*Correct pattern\*\*:[^\n]*\n',
    '',
    text,
)
# "Per-finding blocking question" prose (used in R8 recap line) —
# rewrite to drop the Claude-blocking-tool framing.
text = re.sub(
    r'Per-finding blocking question',
    'Per-finding plain-text numbered prompt',
    text,
)
# "the blocking tool" / "platform blocking tool" / "blocking-question tool"
# residual refs.
text = re.sub(
    r'\bthe (?:platform )?blocking tool\b',
    'the plain-text numbered prompt',
    text,
)
# "via blocking question" / "a blocking question" / "blocking prompt"
# residual refs (Claude-specific framing on Codex).
text = re.sub(
    r'\bvia (?:a |the )?blocking question\b',
    'via plain-text numbered prompt',
    text,
)
text = re.sub(
    r'\b(a |the )blocking question\b',
    r'\1plain-text numbered prompt',
    text,
)
text = re.sub(
    r'\bblocking prompt\b',
    'plain-text numbered prompt',
    text,
)
# Bare "blocking question" (no article — e.g. "surfaces blocking question
# with frozen options") and bold-wrapped variants.
text = re.sub(
    r'\*\*blocking question\*\*',
    '**plain-text numbered prompt**',
    text,
)
text = re.sub(
    r'\bblocking question\b',
    'plain-text numbered prompt',
    text,
)
# "no blocking tool is available/reachable" — describes a fallback gate.
# On Codex the "blocking tool" framing doesn't apply.
text = re.sub(
    r'\bno blocking tool is (available|reachable)\b',
    r'plain text is the prompt mechanism',
    text,
)
# "the platform's question tool" — phrasing inherited from canonical;
# Codex doesn't have a structured question tool.
text = re.sub(
    r"\bthe platform'?s question tool\b",
    'the plain-text numbered prompt',
    text,
)

# O. Strip the stale "Fall back if the tool is unreachable" fallback prose.
#    In canonical (Claude) the phrasing means: "if the structured
#    AskUserQuestion tool is unavailable, drop to plain-text numbered list".
#    After A-N collapse the tool references into the plain-text numbered
#    prompt itself, the surviving fallback sentences read as if the
#    plain-text numbered prompt is a tool with a separate "fall back to
#    plain text" path — which is nonsensical (the plain-text numbered
#    prompt IS that path) and reintroduces the Codex Default-mode failure
#    fn-45 was meant to fix by sending the agent looking for a nonexistent
#    prompt tool. Strip every variant, preserving any non-fallback tail
#    clauses (e.g. "Never silently skip the question.") that follow the
#    strip site. Must run AFTER M/N — the multi-line pattern references
#    "the plain-text numbered prompt", which only exists post-rewrite of
#    canonical "the blocking tool".
#
#    Patterns matched longest-most-specific-first so bare strippers don't
#    eat the suffix of the longer-tail replacement.
#
# b. " Fall back ... — never silently skip the question." → preserve the
#    never-skip tail (sole site: flow-next-strategy/SKILL.md).
text = re.sub(
    r' Fall back to numbered options in chat only when the tool is unreachable in the harness or the call errors — never silently skip the question\.',
    ' Never silently skip the question.',
    text,
)
# a. " Fall back to numbered options in plain text only if the tool is
#    unreachable or errors." → strip (capture / memory-migrate / audit).
text = re.sub(
    r' Fall back to numbered options in plain text only if the tool is unreachable or errors\.',
    '',
    text,
)
# c. " Fall back to a numbered options prompt only if the tool is
#    unreachable." → strip (make-pr).
text = re.sub(
    r' Fall back to a numbered options prompt only if the tool is unreachable\.',
    '',
    text,
)
# d. " Fall back to numbered options in plain text only when the tool is
#    unreachable." → strip (interview).
text = re.sub(
    r' Fall back to numbered options in plain text only when the tool is unreachable\.',
    '',
    text,
)
# e. "; fall back to printing the numbered list and reading a typed reply
#    if the tool is unreachable." → "." (prospect:157).
text = re.sub(
    r'; fall back to printing the numbered list and reading a typed reply if the tool is unreachable\.',
    '.',
    text,
)
# f. "; fall back to numbered-options when the tool is unreachable." → "."
#    (prospect:605).
text = re.sub(
    r'; fall back to numbered-options when the tool is unreachable\.',
    '.',
    text,
)
# g. " If the tool is unreachable, print the frozen-string format below
#    and read the user's reply from chat." → strip (prospect:851).
text = re.sub(
    r" If the tool is unreachable, print the frozen-string format below and read the user'?s reply from chat\.",
    '',
    text,
)
# h. " If the tool is unreachable, fall back to printing a numbered list
#    and reading a typed reply." → strip (audit/workflow:476).
text = re.sub(
    r' If the tool is unreachable, fall back to printing a numbered list and reading a typed reply\.',
    '',
    text,
)
# i. Multi-line paragraph (impl-review/walkthrough.md:43-45):
#       If the tool is unreachable, fall through to a chat-prompt fallback (print
#       the question, wait for the user's next message). The fallback is less
#       reliable — prefer the plain-text numbered prompt wherever available.
#    Strip the whole paragraph.
text = re.sub(
    r"If the tool is unreachable, fall through to a chat-prompt fallback \(print\nthe question, wait for the user'?s next message\)\. The fallback is less\nreliable — prefer the plain-text numbered prompt wherever available\.\n",
    '',
    text,
)

# --- R2 instruction block injection ----------------------------------------
# Inject the full plain-text numbered-prompt contract once per file. The
# instruction tells the Codex agent how to render options, how to signal
# the freeform "Other" affordance, and that it must STOP after printing.
INSTRUCTION = (
    '**Ask the user via plain text.** Render the options below as a '
    'numbered list `1.` … `N.`, followed by a final option '
    '`N+1. Other — type your own answer`. Print the question, then the '
    'numbered list, then **stop and wait for the user\'s next message '
    'before continuing**. Parse the reply as: a bare number `1`–`N+1` → '
    'that option; the literal text of an option label → that option; free '
    'text after `Other` → custom answer.'
)

def is_negative_context(line):
    """True when 'plain-text numbered prompt' appears in a context that
    is NOT a live ask — auto-fix-loop sites, skip/no-prompt prose,
    reference/checklist bullets about what something IS NOT or what is
    skipped. Injecting R2 here either contradicts the surrounding prose
    or pollutes deterministic/Ralph branches."""
    # Auto-fix-loop hard mandates.
    if 'Never use' in line and 'plain-text numbered prompt' in line:
        return True
    if 'do NOT use' in line and 'plain-text numbered prompt' in line:
        return True
    # Hard-error / no-user prose ("questions hard-error ...", "no user to
    # ask ..."). These lines DESCRIBE a Ralph/autonomous branch that refuses
    # to ask — injecting the R2 ask block here would contradict the branch
    # semantics (observed: make-pr autonomous bullet, fn-59.3 review).
    if ('hard-error' in line or 'no user to ask' in line) \
            and 'plain-text numbered prompt' in line:
        return True
    # Capability-negation prose ("cannot call X", "can't ask via X", "cannot
    # use X"). These describe a subagent/context that is UNABLE to ask — a
    # descriptive site (e.g. the delegation reference's "the worker is a
    # subagent and cannot call `plain-text numbered prompt`"), NOT a live ask.
    # Injecting the R2 block here flips the meaning into an instruction to ask.
    if re.search(r"\b(?:cannot|can[’']?t|could not|couldn[’']?t)\s+(?:call|use|ask\b[^.]*?via)\b", line) \
            and 'plain-text numbered prompt' in line:
        return True
    # Skip/no-prompt prose ("skips the ... preview", "no plain-text ...
    # call", etc.). These describe deterministic branches, not active asks.
    if re.search(r'\bskips? the `?plain-text numbered prompt`?', line):
        return True
    if re.search(r'\bno `?plain-text numbered prompt`? call', line):
        return True
    if re.search(r'without (?:a |an |any )?(?:`?plain-text numbered prompt`?|prompt) call', line):
        return True
    # Reference-style "It is not / X is not ..." bullets. These describe
    # what the prompt isn't — not a live ask site.
    if re.search(r'(?:It|This|That) is not\b', line) and 'plain-text numbered prompt' in line:
        return True
    # Forbidden / never-reached / never-interactive prose. An autonomous-only
    # skill (pilot) — and tracker-sync's Phase-0 autonomy invariant — describe
    # the prompt path ONLY to forbid it: "never an interactive `plain-text
    # numbered prompt`", "`plain-text numbered prompt` is forbidden on the tick
    # path", "`plain-text numbered prompt` is never reached / never reachable",
    # "no path reaches `plain-text numbered prompt`", "NO code path may reach
    # `plain-text numbered prompt`", "Never asks interactively". Injecting the R2
    # ask block here contradicts the surface-don't-block / autonomous contract
    # (fn-68 R14: the backlog/Ralph path never reaches an interactive prompt).
    # The verb regex mis-reads the leading "Asking ..." / "Never asks ..." OR the
    # trailing "ask the human" as an active-ask anchor, so this guard must catch
    # the negation explicitly.
    #
    # CASE-INSENSITIVE on purpose: the tracker-sync invariant capitalizes it as
    # "NO code path may reach" (review caught this — a case-sensitive
    # "no ... reaches" missed both the uppercase AND the "may reach" form). The
    # `reach` clause covers reach / reaches / reached / reachable, with or
    # without an intervening modal ("may"/"can"/"could"/"will") and the optional
    # "code" qualifier.
    if 'plain-text numbered prompt' in line and re.search(
        r'\b(?:is|are) forbidden\b'
        r'|\bnever an interactive\b'
        r'|\bnever asks?\s+interactively\b'
        r'|\b(?:no|never)\b[^.]*?\b(?:code\s+)?path[^.]*?\breach(?:es|ed|able)?\b'
        r'|\bis\s+never\s+reach(?:ed|able)\b'
        r'|\bnever\s+reach(?:es|ed|able)\b',
        line,
        re.IGNORECASE,
    ):
        return True
    return False

def is_table_line(line):
    """True for markdown table rows or delimiter rows. Injecting a
    paragraph between table rows breaks the table — skip these as
    injection anchors."""
    stripped = line.lstrip()
    return stripped.startswith('|') or stripped.startswith('|-')

# Verbs that indicate an active ask / prompt site. The R2 instruction
# block belongs adjacent to one of these — not in deterministic prose,
# reference lists, or "what X is not" bullets.
ACTIVE_ASK_VERBS = re.compile(
    r'\b('
    r'[Aa]sk|MUST ask|[Mm]ust use|[Mm]ust ask|MUST use|'
    r'[Uu]se `?plain-text numbered prompt`?|'
    r'[Dd]efault to `?plain-text numbered prompt`?|'
    r'[Ff]ormat the question|'
    r'[Rr]ender|[Ss]urface|[Ff]ire|[Pp]resent|[Ss]how|'
    r'[Cc]all `?plain-text numbered prompt`?|'
    r'[Ii]nvoke `?plain-text numbered prompt`?|'
    r'via `?plain-text numbered prompt`?'
    r')\b'
)

def is_active_ask_anchor(line):
    """True when the line is a plausible active-ask site for the R2
    instruction. Anchors should describe ASKING via the prompt, not
    skipping it or describing what it isn't."""
    if 'plain-text numbered prompt' not in line:
        return False
    return bool(ACTIVE_ASK_VERBS.search(line))

# Inject once per file. Two strategies, in priority order:
#  1. If a hard-mandate pattern (A/B/C) fired, it left a "described below"
#     sentinel. Splice the instruction immediately after that paragraph.
#  2. Otherwise, if the original file referenced AskUserQuestion in prose
#     in an affirmative context, splice the instruction immediately before
#     the FIRST positive (non-negative, non-table) noun-phrase reference so
#     the substituted noun phrase has a definition the agent can resolve.
#     If every remaining reference is a negative mandate or sits inside a
#     markdown table, skip injection entirely — the surrounding prose is
#     either contradicting it or structurally fragile.
if 'described below' in text:
    lines = text.split('\n')
    out = []
    injected = False
    for line in lines:
        out.append(line)
        if not injected and 'described below' in line:
            out.append('')
            out.append(INSTRUCTION)
            injected = True
    text = '\n'.join(out)
elif had_ask_in_prose and 'plain-text numbered prompt' in text:
    lines = text.split('\n')
    # Track fenced-code-block state so we never inject inside a ``` ... ```
    # region (would split a working code example). Anchor must be:
    #   - active-ask shape (verb match in line)
    #   - not a negative context (skip / Never use / It is not / ...)
    #   - not a markdown table row or delimiter
    #   - not inside a fenced code block
    in_fence = False
    anchor_idx = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not is_active_ask_anchor(line):
            continue
        if is_negative_context(line):
            continue
        if is_table_line(line):
            continue
        anchor_idx = i
        break
    if anchor_idx >= 0:
        out = []
        for i, line in enumerate(lines):
            if i == anchor_idx:
                out.append(INSTRUCTION)
                out.append('')
            out.append(line)
        text = '\n'.join(out)

# Collapse double spaces / blank-line runs left over from substitutions.
text = re.sub(r'  +', ' ', text)
text = re.sub(r'\n{3,}', '\n\n', text)
text = '\n'.join(line.rstrip() for line in text.split('\n'))

with open(path, 'w') as fp:
    fp.write(text)
PYEOF
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

# Workflow skills (blue, implicit - surfaced in the model catalog so prose
# like "plan this feature" / "pilot this to completion" resolves the skill)
generate_openai_yaml "flow-next-plan"      "Flow Plan"      "Create structured build plans from feature requests" "#3B82F6" true "Plan out this feature: "
generate_openai_yaml "flow-next-work"      "Flow Work"      "Execute planned tasks with worker subagents"          "#3B82F6" true "Work on: "
generate_openai_yaml "flow-next-interview" "Flow Interview" "Deep Q&A to refine specs and requirements"            "#3B82F6" true
generate_openai_yaml "flow-next-setup"     "Flow Setup"     "Initialize flow-next in current project"              "#3B82F6" true
generate_openai_yaml "flow-next-prospect"  "Flow Prospect"  "Generate ranked candidate ideas grounded in the repo" "#3B82F6" true "What should we build next? "
generate_openai_yaml "flow-next-capture"   "Flow Capture"   "Synthesize conversation context into a flow-next spec" "#3B82F6" true "Capture this as a spec: "
generate_openai_yaml "flow-next-strategy"  "Flow Strategy"  "Generate or update repo-root STRATEGY.md (problem, approach, personas, metrics, tracks)" "#3B82F6" true
generate_openai_yaml "flow-next-audit"     "Flow Audit"     "Review .flow/memory/ entries against current code"   "#3B82F6" true
generate_openai_yaml "flow-next-memory-migrate" "Flow Memory Migrate" "Migrate legacy flat memory files to categorized YAML schema" "#3B82F6" true
generate_openai_yaml "flow-next-make-pr" "Flow Make PR" "Render a cognitive-aid PR body from flow-next state and open via gh" "#3B82F6" true
generate_openai_yaml "flow-next-tracker-sync" "Flow Tracker Sync" "Project a spec to a tracker (Linear/GitHub/GitLab/Jira) and reconcile two-way — NOT plan-sync" "#3B82F6" true
generate_openai_yaml "flow-next-qa" "Flow QA" "Live-app real-user QA pass derived from the spec — drives the running app, files P0/P1/P2 findings, emits a YES/NO verdict" "#3B82F6" true
generate_openai_yaml "flow-next-pilot" "Flow Pilot" "Single-tick autonomous build-loop conductor — one ready spec, one stage per tick, terminal PILOT_VERDICT line" "#3B82F6" true
generate_openai_yaml "flow-next-land" "Flow Land" "Cadence-tick autonomous PR babysitter — CI-fix, resolve, converge, merge, close, release; terminal LAND_VERDICT line" "#3B82F6" true

# Review skills (red, implicit)
generate_openai_yaml "flow-next-impl-review" "Flow Implementation Review" "Carmack-level code review via RepoPrompt"  "#EF4444" true
generate_openai_yaml "flow-next-plan-review" "Flow Plan Review"           "Carmack-level plan review via RepoPrompt"  "#EF4444" true
generate_openai_yaml "flow-next-spec-completion-review" "Flow Spec Completion Review" "Verify spec implementation matches the spec" "#EF4444" true
generate_openai_yaml "flow-next-resolve-pr"  "Flow Resolve PR"            "Resolve PR review feedback via GraphQL"    "#EF4444" true "Resolve PR "

# Utility skills (blue/amber, implicit allowed)
generate_openai_yaml "flow-next"       "Flow Tasks" "Manage .flow/ tasks and specs"                           "#3B82F6" true
generate_openai_yaml "flow-next-prime" "Flow Prime" "Comprehensive codebase assessment for agent readiness"    "#F59E0B" true
generate_openai_yaml "flow-next-map"   "Flow Map"   "Wrap clawpatch map for a semantic feature index (opt-in)" "#F59E0B" true
generate_openai_yaml "flow-next-ralph-init" "Flow Ralph Init" "Scaffold the repo-local Ralph autonomous harness" "#3B82F6" true

# Internal skills (gray, explicit-only). These are spawned by other skills,
# never by user prose. Codex defaults allow_implicit_invocation to TRUE when
# no openai.yaml exists, silently injecting name+description into EVERY
# session's skill catalog (a shared budget of min(8000 chars, 2% of context;
# codex-rs/core-skills/src/render.rs) - overflow truncates ALL skills'
# descriptions, including unrelated user skills). Hidden skills stay fully
# invocable by the skills that dispatch them (paths in prose) and via $name.
generate_openai_yaml "flow-next-drive"          "Flow Drive [internal]"          "Browser/app driver used by Flow QA"                 "#9CA3AF" false
generate_openai_yaml "flow-next-sync"           "Flow Plan-Sync [internal]"      "Downstream task-spec sync used by Flow Work"        "#9CA3AF" false
generate_openai_yaml "flow-next-export-context" "Flow Export Context [internal]" "Context bundle export used by reviews"              "#9CA3AF" false
generate_openai_yaml "flow-next-rp-explorer"    "Flow RP Explorer [internal]"    "RepoPrompt exploration helper used by reviews"      "#9CA3AF" false
generate_openai_yaml "flow-next-worktree-kit"   "Flow Worktree Kit [internal]"   "Worktree helper used by Flow Work"                  "#9CA3AF" false
generate_openai_yaml "flow-next-deps"           "Flow Deps [internal]"           "Dependency-graph helper used by planning skills"    "#9CA3AF" false

# --- Deprecation redirect skills (1.0 alias surface) ---
# The last redirect alias, flow-next-epic-review, was retired on all platforms
# in fn-124 (self-declared dead since 2.0), which left the redirect generator
# with no callers — removed here. Reintroduce a generator only if a new
# deprecation alias is ever needed on the Codex mirror.

# --- Catalog description diet (surfaced skills only) ---
# Codex injects each implicit skill's SKILL.md frontmatter `description` into
# the model context verbatim (render.rs uses `description`, NOT openai.yaml's
# short_description, capped 1024 chars each) under the shared skills budget.
# Canonical descriptions are Claude-Code-length (250-700 chars, "Triggers on
# /flow-next:..." tails); at 22 surfaced skills that alone would blow the
# budget and truncate every skill on the user's machine. Rewrite the MIRROR
# frontmatter description to a tight catalog line (target <=160 chars, no
# colons so the unquoted YAML stays valid). Hidden (internal) skills keep
# their canonical descriptions - they are never injected.
# MAINTENANCE: a new user-facing skill needs an entry here; the validation
# guard below hard-fails when a surfaced skill's description exceeds 200 chars.
python3 - "$CODEX_DIR" <<'PYEOF'
import sys, pathlib
codex_dir = pathlib.Path(sys.argv[1])
DIET = {
    "flow-next-plan": "Plan a feature into a flow-next spec with tasks in .flow/. Use when asked to plan, spec out, or break down work (fn-N ids).",
    "flow-next-work": "Execute a flow-next spec or task end-to-end with worker subagents, gates, and commits. Use when asked to work on, implement, or execute fn-N.",
    "flow-next-pilot": "Single-tick autonomous build-loop conductor. Advances one ready spec one stage per tick, emits PILOT_VERDICT. Use when asked to pilot a spec or backlog.",
    "flow-next-land": "Autonomous PR babysitter tick. Fixes CI, resolves feedback, merges when converged, closes the spec, releases. Emits LAND_VERDICT. Use when asked to land PRs.",
    "flow-next-make-pr": "Open a PR with a cognitive-aid body rendered from flow-next spec state via gh. Use whenever asked to make or open a PR in a flow-next repo.",
    "flow-next-resolve-pr": "Resolve PR review feedback. Fetches unresolved threads, triages, fixes, replies and resolves via GraphQL. Use when asked to address review comments.",
    "flow-next-interview": "In-depth Q&A to refine a spec, task, or spec file before building. Use when asked to flesh out, refine, or interrogate requirements.",
    "flow-next-capture": "Synthesize the current conversation into a flow-next spec with read-back gating. Use when asked to capture this as a spec.",
    "flow-next-setup": "Install or refresh flowctl and project instructions for flow-next in this repo. Use when asked to set up flow-next.",
    "flow-next-prospect": "Generate ranked candidate ideas grounded in the repo. Use when asked what to build next.",
    "flow-next-strategy": "Create or update repo-root STRATEGY.md (problem, approach, users, metrics, tracks). Use for strategy or roadmap doc requests.",
    "flow-next-audit": "Audit .flow/memory/ entries against current code and keep, update, consolidate, or delete each. Use when asked to audit or refresh memory.",
    "flow-next-memory-migrate": "Migrate legacy flat .flow/memory files to the categorized YAML schema. One-time ceremony. Use when asked to migrate flow memory.",
    "flow-next-tracker-sync": "Project a flow-next spec to a tracker issue (Linear, GitHub, GitLab, Jira) and reconcile two-way. Use when asked to sync to a tracker. NOT plan-sync.",
    "flow-next-qa": "Live-app QA pass derived from the spec. Drives the running app, files P0/P1/P2 findings with evidence, emits a YES or NO qa_verdict receipt.",
    "flow-next-prime": "Assess codebase agent and production readiness. Classifies the project, verifies commands run, leads with a verdict and ranked next actions.",
    "flow-next-map": "Build a semantic feature index of the repo via clawpatch map (opt-in). Use when asked to map the repo.",
    "flow-next-impl-review": "Carmack-level implementation review of changes via the configured backend. Use when asked to review code or a diff in a flow-next repo.",
    "flow-next-plan-review": "Carmack-level review of a flow-next spec or plan via the configured backend. Use when asked to review a plan or spec.",
    "flow-next-spec-completion-review": "Verify that a spec's completed tasks fully implement the spec requirements. Use at spec completion before close.",
    "flow-next-ralph-init": "Scaffold the repo-local Ralph autonomous harness and project hooks. Use when asked to set up Ralph.",
    "flow-next": "Manage .flow/ tasks and specs. Use for show or list tasks, task status, what is ready, show fn-N. NOT for planning or executing (use the plan and work skills).",
}
failed = 0
for skill, desc in DIET.items():
    p = codex_dir / "skills" / skill / "SKILL.md"
    if not p.is_file():
        print(f"DIET-FAIL: {skill}/SKILL.md missing")
        failed += 1
        continue
    lines = p.read_text(encoding="utf-8").split("\n")
    done = False
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            lines[i] = f"description: {desc}"
            done = True
            break
        if i > 0 and line == "---":
            break
    if not done:
        print(f"DIET-FAIL: no description line in {skill}/SKILL.md frontmatter")
        failed += 1
        continue
    p.write_text("\n".join(lines), encoding="utf-8")
if failed:
    sys.exit(1)
print(f"  diet applied to {len(DIET)} surfaced skill descriptions")
PYEOF

# REQUIRED list — every user-facing slash-command skill MUST have an
# openai.yaml entry above. When you add a new skill, add it here AND add
# a generate_openai_yaml call. Validation will fail otherwise.
# See CLAUDE.md > "Adding a new user-facing skill" for the full checklist.
REQUIRED_OPENAI_YAML_SKILLS=(
  "flow-next-plan"
  "flow-next-work"
  "flow-next-interview"
  "flow-next-setup"
  "flow-next-prospect"
  "flow-next-capture"
  "flow-next-strategy"
  "flow-next-audit"
  "flow-next-memory-migrate"
  "flow-next-make-pr"
  "flow-next-tracker-sync"
  "flow-next-qa"
  "flow-next-pilot"
  "flow-next-land"
  "flow-next-impl-review"
  "flow-next-plan-review"
  "flow-next-spec-completion-review"
  "flow-next-resolve-pr"
  "flow-next"
  "flow-next-prime"
  "flow-next-map"
  "flow-next-ralph-init"
  "flow-next-drive"
  "flow-next-sync"
  "flow-next-export-context"
  "flow-next-rp-explorer"
  "flow-next-worktree-kit"
  "flow-next-deps"
)

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
  # Known keys: name/description/model map into TOML. Cursor-native `readonly:`
  # (fn-123 R4) and Claude-only keys (disallowedTools, color, user-invocable)
  # are recognized so they never leak into developer_instructions and never
  # trip a future strict-key guard. Codex enforces read-only via sandbox_mode
  # (sandbox_for), not a `readonly` TOML field — so we swallow, not emit.
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
        name:*)             name="${line#name: }"; name="${name#name:}"; name="$(echo "$name" | xargs)" ;;
        description:*)      description="${line#description: }"; description="${description#description:}"; description="$(echo "$description" | xargs)" ;;
        model:*)            model="${line#model: }"; model="${model#model:}"; model="$(echo "$model" | xargs)" ;;
        readonly:*)         ;; # Cursor-native; Codex uses sandbox_mode (tolerated, not emitted)
        disallowedTools:*)  ;; # Claude/Droid-only capability blacklist
        color:*)            ;; # Claude UI chrome
        user-invocable:*)   ;; # Claude plugin catalog flag
        ""|\#*)             ;; # blank / comment lines in frontmatter
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

  # FLOWCTL prelude rewrite (fn-50.6): canonical agents use the
  # `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` form
  # (Droid + Claude fallback). In Codex neither env var is set, so the
  # expansion resolves to `/scripts/flowctl` — broken. Mirror the skill-side
  # rewrite (line ~183) here so generated `.toml` agent bodies use the direct
  # Codex form plus the local `.flow/bin/flowctl` fallback. fn-50.3 added the
  # repo-scout / context-scout `repo-map` probes that surfaced this gap.
  body="$(echo "$body" | sed -E 's|\$\{DROID_PLUGIN_ROOT:-\$\{CLAUDE_PLUGIN_ROOT\}\}/scripts/flowctl|$HOME/.codex/scripts/flowctl|g')"
  # fn-89: same class of rewrite for skill-file paths in agent bodies
  # (tracker-runner reads the tracker-sync skill body) - neither plugin-root
  # var resolves inside Codex; the installed mirror lives at ~/.codex/skills/.
  body="$(echo "$body" | sed -E 's|\$\{DROID_PLUGIN_ROOT:-\$\{CLAUDE_PLUGIN_ROOT\}\}/skills/|$HOME/.codex/skills/|g')"
  # Insert the local fallback line after every FLOWCTL= assignment that points
  # at the Codex path. Matches `FLOWCTL="$HOME/.codex/scripts/flowctl"` with
  # any leading whitespace; the inserted fallback line preserves that
  # indentation so embedded bash blocks stay aligned. Uses POSIX awk
  # (no gawk-only 3-arg match) so macOS / Linux behave identically.
  #
  # IDEMPOTENT: canonical agent bodies may ALREADY carry the
  # `[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"` fallback on the line
  # directly after the FLOWCTL= assignment (fn-50.3 hardening added it to
  # repo-scout / context-scout for the Claude/Droid path). Only inject when
  # the next line is NOT already that fallback — otherwise we emit a duplicate.
  body="$(echo "$body" | awk '
    function flush_pending(   stripped) {
      if (pending) {
        stripped = nextline
        sub(/^[[:space:]]+/, "", stripped)
        if (stripped != "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\"") {
          print fallback
        }
        pending = 0
      }
    }
    /^[[:space:]]*FLOWCTL="\$HOME\/\.codex\/scripts\/flowctl"[[:space:]]*$/ {
      print
      indent = ""
      i = 1
      while (i <= length($0) && substr($0, i, 1) ~ /[[:space:]]/) {
        indent = indent substr($0, i, 1)
        i++
      }
      fallback = indent "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\""
      pending = 1
      next
    }
    {
      nextline = $0
      flush_pending()
      print
    }
    END { if (pending) print fallback }
  ')"

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
        echo "model_reasoning_effort = \"$(reasoning_effort_for "$codex_name")\""
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

# ─── 3. Hooks (none by default; fn-114) ───────────────────────────────────────
# Codex mirror ships ZERO hooks. Plugin hooks/ is gone; Ralph guard registration
# is agent-driven via /flow-next:ralph-init into project .codex/hooks.json.
# Remove any stale mirror hooks.json left from older sync runs.
echo -e "${BLUE}Hooks: zero-default (no codex/hooks.json)...${NC}"
if [ -f "$CODEX_DIR/hooks.json" ]; then
  rm -f "$CODEX_DIR/hooks.json"
  echo -e "  ${GREEN}✓${NC} removed stale codex/hooks.json"
else
  echo -e "  ${GREEN}✓${NC} no codex/hooks.json (correct)"
fi

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

# Assert no default hooks.json in the Codex mirror (fn-114 zero-default)
if [ -f "$CODEX_DIR/hooks.json" ]; then
  echo -e "  ${RED}✗${NC} codex/hooks.json must not ship (Ralph is opt-in via ralph-init)"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} no codex/hooks.json (zero-default)"
fi

# Check no bare CLAUDE_PLUGIN_ROOT without fallback in skills
bare_refs=$( { grep -r 'CLAUDE_PLUGIN_ROOT}/' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v 'CLAUDE_PLUGIN_ROOT:-' || true; } | { grep -v '\.codex' || true; } | wc -l | tr -d ' ')
if [ "$bare_refs" != "0" ]; then
  echo -e "  ${YELLOW}!${NC} $bare_refs bare CLAUDE_PLUGIN_ROOT refs (may need patching)"
else
  echo -e "  ${GREEN}✓${NC} No bare CLAUDE_PLUGIN_ROOT refs"
fi

# Check no plugin-root /skills/ path refs survive (must be rewritten to
# $HOME/.codex/skills/ or a specific destination — an unrewritten ref expands
# to a broken /skills/... path inside Codex where neither var is set)
skills_refs=$( { grep -rE '(DROID_PLUGIN_ROOT|CLAUDE_PLUGIN_ROOT|\$PLUGIN_ROOT)[^[:space:]]*/skills/' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$skills_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $skills_refs unrewritten plugin-root /skills/ path refs in codex/skills/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No unrewritten plugin-root /skills/ path refs"
fi

# Check no "Task flow-next:" in codex skills
task_refs=$( { grep -r 'Task flow-next:' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$task_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $task_refs 'Task flow-next:' refs remain in codex/skills/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No 'Task flow-next:' refs"
fi

# Check no "/flow-next:" slash-command tokens in the setup usage.md template —
# it is copied into projects as `.flow/usage.md`, and Codex resolves
# `$flow-next-<cmd>`, not `/flow-next:<cmd>`. The targeted rewrite above must
# have converted every token.
usage_slash_refs=$( { grep -c '/flow-next:' "$CODEX_DIR/templates/usage.md" 2>/dev/null || true; } | tr -d ' ')
[ -n "$usage_slash_refs" ] || usage_slash_refs=0
if [ "$usage_slash_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $usage_slash_refs '/flow-next:' refs remain in codex templates/usage.md — should be \$flow-next-<cmd>"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No '/flow-next:' refs in codex templates/usage.md"
fi

# fn-121: the Codex mirror must not describe plugin mode (Claude-Code-only) —
# negative half: no plugin-mode prose in the setup workflow, no slim template.
pm_refs=$( { grep -cE 'Step 2b|claude-md-snippet-plugin|setup-mode set plugin|plugin mode' "$CODEX_DIR/skills/flow-next-setup/workflow.md" 2>/dev/null || true; } | tr -d ' ')
[ -n "$pm_refs" ] || pm_refs=0
if [ "$pm_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} plugin-mode prose leaked into the codex mirror setup workflow (refs=$pm_refs)"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No plugin-mode prose in codex setup workflow"
fi

# fn-121 (PR #227 review): the slim template MUST ship in the mirror - the
# retained per-skill pre-check's "Refresh now" path reads it cross-host.
if [ -f "$CODEX_DIR/skills/flow-next-setup/templates/claude-md-snippet-plugin.md" ]; then
  echo -e "  ${GREEN}✓${NC} Slim plugin snippet template present in mirror (pre-check refresh path)"
else
  echo -e "  ${RED}✗${NC} Slim plugin snippet template missing from mirror - the mirrored pre-check's Refresh now path would 404"
  errors=$((errors + 1))
fi

# fn-121 positive half: copy-mode behavior retained in the mirror.
if grep -q '^## Step 3: Create .flow/bin/' "$CODEX_DIR/skills/flow-next-setup/workflow.md" 2>/dev/null \
   && grep -q 'setup-mode set copy' "$CODEX_DIR/skills/flow-next-setup/workflow.md" 2>/dev/null; then
  echo -e "  ${GREEN}✓${NC} Copy-mode setup path retained in codex mirror (Step 3 + copy stamp)"
else
  echo -e "  ${RED}✗${NC} Copy-mode setup path missing from codex mirror (Step 3 heading or copy stamp gone)"
  errors=$((errors + 1))
fi

# fn-126 R4: mirror Step-0 detection bash must be unconditional PLATFORM=codex
# (no multi-host cascade — Codex always reads this mirror as PLATFORM=codex).
# Scope: the first ```bash fence under the Step 0 heading only (prose may still
# mention host signals for documentation; the executable detection block must not).
setup_mirror_wf="$CODEX_DIR/skills/flow-next-setup/workflow.md"
if [ -f "$setup_mirror_wf" ]; then
  det_block=$(awk '
    /^## Step 0: Resolve plugin path and detect platform/ {in_s0=1; next}
    in_s0 && /^## / {exit}
    in_s0 && /^```bash$/ {grab=1; next}
    grab && /^```$/ {exit}
    grab {print}
  ' "$setup_mirror_wf")
  det_bad=0
  # Fail-CLOSED (codex impl-review): the executable content must be EXACTLY the
  # single `PLATFORM="codex"` assignment. Strip comment/blank lines, then require
  # the remainder to equal that one line — so ANY future branch (new signal,
  # if/case, extra assignment) fails, not just the four named signals.
  det_exec=$(printf '%s\n' "$det_block" | sed 's/#.*$//' | grep -vE '^[[:space:]]*$' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [ "$det_exec" != 'PLATFORM="codex"' ]; then
    echo -e "  ${RED}✗${NC} codex mirror setup Step-0 executable content is not exactly 'PLATFORM=\"codex\"' (fn-126 R4 — must be unconditional; got: $(printf '%s' "$det_exec" | tr '\n' '|'))"
    det_bad=1
  fi
  if [ "$det_bad" = "0" ]; then
    echo -e "  ${GREEN}✓${NC} Codex mirror setup Step-0 is unconditional PLATFORM=codex (no host-detection branches)"
  else
    errors=$((errors + 1))
  fi
else
  echo -e "  ${RED}✗${NC} codex mirror setup workflow missing — cannot validate Step-0 (fn-126 R4)"
  errors=$((errors + 1))
fi

# Check no "AskUserQuestion" or "ToolSearch select:AskUserQuestion" in codex
# skill prose — should all have been rewritten to the plain-text numbered
# prompt by Stage 3 (fn-45). Bare AskUserQuestion in the Codex skill prose
# is a sync bug.
# Exclude templates/ subdirs (those are user-script templates, not skill prose
# that the agent reads — e.g., ralph-init/templates/watch-filter.py uses the
# tool name as a dict key for hook event emoji mapping, which is intentional).
askq_refs=$( { grep -rE 'AskUserQuestion|ToolSearch select:AskUserQuestion' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$askq_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $askq_refs Claude-native tool refs (AskUserQuestion / ToolSearch) remain in codex skill prose — extend sync transforms"
  { grep -rnE 'AskUserQuestion|ToolSearch select:AskUserQuestion' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-native tool refs in Codex skill prose"
fi

# fn-100 R12: the Claude-native fact-scout dispatch phrase must not survive in
# the mirror — the Explore-dispatch transform above rewrites it to
# `spawn_agent` with `agent_type: explorer`. Exact-phrase match: the
# "`Task` tool with" variants in cross-platform tables are deliberate
# documentation of the Claude Code naming and are excluded by construction.
scout_refs=$( { grep -r '`Task` with `subagent_type: Explore`' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$scout_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $scout_refs Claude-native Explore-dispatch refs remain in codex skill prose — Explore-dispatch transform (fn-100 R12) should have rewritten these"
  { grep -rn '`Task` with `subagent_type: Explore`' "$CODEX_DIR/skills/" 2>/dev/null || true; } | head -5
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-native Explore-dispatch refs in Codex skill prose"
fi

# fn-89: the Claude-native tracker-runner dispatch must not survive in the
# mirror - the transform above rewrites it to the tracker_runner agent role.
runner_refs=$( { grep -r --include='*.md' -e 'Task flow-next:tracker-runner' -e '`tracker-runner`' "$CODEX_DIR/skills/" "$CODEX_DIR/references/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$runner_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $runner_refs Claude-native tracker-runner dispatch refs remain in codex skill/reference prose - the tracker-runner transform (fn-89) should have rewritten these to the tracker_runner role"
  { grep -rn --include='*.md' -e 'Task flow-next:tracker-runner' -e '`tracker-runner`' "$CODEX_DIR/skills/" "$CODEX_DIR/references/" 2>/dev/null || true; } | head -5
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-native tracker-runner dispatch refs in Codex skill/reference prose"
fi

# fn-89 (fn-50.6 symmetry rule): agent toml bodies must not carry unrewritten
# plugin-root /skills/ paths - the agents-pipeline rewrite maps them to
# $HOME/.codex/skills/. The skills-side guard above has no agents coverage.
agent_skill_refs=$( { grep -rE '(DROID_PLUGIN_ROOT|CLAUDE_PLUGIN_ROOT|\$PLUGIN_ROOT)[^[:space:]]*/skills/' "$CODEX_DIR/agents/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$agent_skill_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $agent_skill_refs unrewritten plugin-root /skills/ path refs in codex/agents/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No unrewritten plugin-root /skills/ path refs in codex/agents/"
fi

# fn-100 R12 follow-up: the Claude-specific scout-tier example "(sonnet on
# Claude Code)" must read platform-neutral in the mirror — the transform above
# rewrites it to "(the host's mid-tier)".
tier_refs=$( { grep -r '(sonnet on Claude Code)' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$tier_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $tier_refs Claude-specific scout-tier example(s) remain in codex skill prose — the tier-example transform should have rewritten these"
  { grep -rn '(sonnet on Claude Code)' "$CODEX_DIR/skills/" 2>/dev/null || true; } | head -5
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-specific scout-tier examples in Codex skill prose"
fi

# R6 mirror scan — `request_user_input` must NOT leak into the Codex mirror
# (fn-45). The Codex Default-mode + CLI surface errors on `request_user_input`
# calls (openai/codex #10384, #11536, #12694). Stage 3 instructs the agent to
# render a plain-text numbered prompt instead; any surviving reference is a
# sync bug that would re-introduce the failure. Exclude /templates/ subdirs.
# Patterns: backticked invocation, "tool" form, function-call form, the two
# hard-mandate phrasings that survived the old `request_user_input` rewrite
# era, AND `allowed-tools:` frontmatter listings (v1.1.7 — fn-45 originally
# exempted these as "harmless residue", but agents trust the frontmatter
# tool list and call the unavailable tool).
RUI_PATTERN='`request_user_input`|request_user_input tool|request_user_input\(|MUST use `request_user_input`|ONLY ask via `request_user_input`|^allowed-tools:.*\brequest_user_input\b'
rui_refs=$( { grep -rnE "$RUI_PATTERN" "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$rui_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $rui_refs request_user_input refs leaked into codex skill prose — Stage 3 (fn-45) should have rewritten these"
  { grep -rnE "$RUI_PATTERN" "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No request_user_input refs in Codex skill prose"
fi

# R17 mirror scan — DDD vocabulary guard for the Codex mirror (fn-38 task 7).
# Canonical clean + mechanical rewrite should keep mirror clean, but a derived
# artifact deserves its own validation. Pattern strings are the authoritative
# forbidden list — see CLAUDE.md / fn-38 spec for rationale.
ddd_refs=$( { grep -rE 'ubiquitous language|bounded context|domain expert|aggregate root' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$ddd_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $ddd_refs R17 forbidden-vocabulary refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R17 forbidden vocabulary in Codex mirror"
fi

# R4 mirror scan — no early-design meta-file references leaked into mirror.
meta_refs=$( { grep -rE 'GLOSSARY-MAP\.md|CONTEXT-MAP\.md' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$meta_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $meta_refs R4 meta-file refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R4 meta-file refs in Codex mirror"
fi

# R19 mirror scan — strategy-doc fluff guard for the Codex mirror (fn-39 task 5).
# Tier 1 jargon only — Rumelt's "fluff" hallmarks. Scope is the Codex mirror
# of the strategy skill; references/interview.md is excluded (must describe
# anti-patterns to push back on them — same exemption as the canonical guard).
fluff_refs=$( { grep -rEi '\bsynergy\b|\bpivot\b|\bdisrupt\b|thought[ -]leadership|best-in-class|world-class|\b10x\b' "$CODEX_DIR/skills/flow-next-strategy/" 2>/dev/null || true; } | { grep -v '/references/interview\.md' || true; } | wc -l | tr -d ' ')
if [ "$fluff_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $fluff_refs R19 strategy-doc fluff refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R19 strategy-doc fluff in Codex mirror"
fi

# R30 mirror scan — alias-vocabulary guard for the Codex mirror (fn-43 task 14).
# Catch fresh prose that uses the legacy `flowctl epic*` CLI surface instead
# of canonical 1.0 `flowctl spec*`. Lines describing deprecation / alias /
# legacy semantics are excluded — these legitimately reference the legacy
# form. references/ files are also excluded (anti-pattern documentation).
alias_refs=$( { grep -rE 'flowctl epic\b|flowctl epics\b|--epic\b|--epics-file\b|--section epic\b|\bEPICS_FILE\b' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -vE '/references/' || true; } | { grep -vE 'deprecat|legacy|alias|_emit_rename_|removed in 2\.0|flow-next 1\.0 renamed|R31|R30|fn-43|\bT[0-9]+\b' || true; } | { grep -vE '^[^:]+:[0-9]+:[[:space:]]+"--(epic|epics-file|epic-title)",?[[:space:]]*$' || true; } | wc -l | tr -d ' ')
if [ "$alias_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $alias_refs R30 legacy CLI vocabulary refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R30 legacy CLI vocabulary in Codex mirror"
fi

# R21 canonical scan — spec-template duplication guard (fn-44 task 1).
# The canonical spec template at `plugins/flow-next/templates/spec.md` is
# the single source of truth for the 7-section spec structure. Any other
# skill markdown file that inline-duplicates the canonical sequence is a
# drift hazard — the template owns the section list; skills cross-link.
#
# Detection: ANY `*.md` under `plugins/flow-next/skills/*/` (not just
# SKILL.md — also workflow.md, phases.md, steps.md, examples.md, ...)
# containing `^## Goal & Context` followed within 30 lines by both
# `^## Architecture & Data Models` AND `^## API Contracts` triggers an
# error. The template at `plugins/flow-next/templates/spec.md` is the
# only allowed location for the full canonical sequence.
#
# False-positive avoidance: skills that legitimately quote the section
# names in isolation (e.g., a question bank or a reference file) won't
# trip the guard because the three headers must co-occur within a 30-line
# window AND each must be at column 1 (`^## `). Single-mention references
# pass through fine.
CANONICAL_SKILLS_DIR="plugins/flow-next/skills"
spec_template_dup_hits=""
if [ -d "$CANONICAL_SKILLS_DIR" ]; then
  # One awk pass per file: scan for `^## Goal & Context`; on a hit, look
  # ahead 30 lines for both `^## Architecture & Data Models` AND
  # `^## API Contracts`. If both co-occur in the window, print the file
  # and the line number of the Goal & Context marker. Single-mention
  # references won't trip — all three headers must co-occur at column 1.
  spec_template_dup_hits=$(find "$CANONICAL_SKILLS_DIR" -name "*.md" -type f 2>/dev/null \
    | xargs -I {} awk '
        FNR == NR { lines[FNR] = $0; total = FNR }
        END {
          for (i = 1; i <= total; i++) {
            if (lines[i] ~ /^## Goal & Context/) {
              arch = 0; api = 0
              for (j = i + 1; j <= i + 30 && j <= total; j++) {
                if (lines[j] ~ /^## Architecture & Data Models/) arch = 1
                if (lines[j] ~ /^## API Contracts/) api = 1
              }
              if (arch && api) {
                printf "%s:%d\n", FILENAME, i
              }
            }
          }
        }
      ' {} 2>/dev/null)
fi
if [ -n "$spec_template_dup_hits" ]; then
  spec_template_dup_count=$(printf '%s\n' "$spec_template_dup_hits" | wc -l | tr -d ' ')
  echo -e "  ${RED}✗${NC} $spec_template_dup_count R21 spec-template duplication(s) in canonical skill markdown:"
  printf '%s\n' "$spec_template_dup_hits" | sed 's/^/    /'
  echo -e "    Canonical template lives at plugins/flow-next/templates/spec.md."
  echo -e "    Replace the duplicated section list with a cross-link."
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R21 spec-template duplication in canonical skill markdown"
fi

# Validate openai.yaml files — every skill in REQUIRED_OPENAI_YAML_SKILLS
# MUST have one. Missing entries fail CI. Extras are fine (utility skills
# may opt in later).
yaml_missing=0
for required_skill in "${REQUIRED_OPENAI_YAML_SKILLS[@]}"; do
  yf="$CODEX_DIR/skills/$required_skill/agents/openai.yaml"
  if [ ! -f "$yf" ]; then
    echo -e "  ${RED}✗${NC} REQUIRED $required_skill/agents/openai.yaml missing — add a generate_openai_yaml call (see CLAUDE.md > Adding a new user-facing skill)"
    yaml_missing=$((yaml_missing + 1))
  fi
done
if [ "$yaml_missing" -eq 0 ]; then
  yaml_count=$(find "$CODEX_DIR/skills" -name "openai.yaml" | wc -l | tr -d ' ')
  echo -e "  ${GREEN}✓${NC} All ${#REQUIRED_OPENAI_YAML_SKILLS[@]} required skills have openai.yaml ($yaml_count total)"
else
  errors=$((errors + yaml_missing))
fi

# Validate openai.yaml content (each must have interface + policy keys)
yaml_errors=0
for yf in $(find "$CODEX_DIR/skills" -name "openai.yaml"); do
  if ! grep -q 'interface:' "$yf" || ! grep -q 'policy:' "$yf"; then
    echo -e "  ${RED}✗${NC} $(dirname "$(dirname "$yf")" | xargs basename)/agents/openai.yaml missing required keys"
    yaml_errors=$((yaml_errors + 1))
  fi
done

# Catalog-policy guard: EVERY mirror skill must declare an explicit
# allow_implicit_invocation - Codex defaults ABSENT to true, so a skill
# without one silently lands in every session's shared skill catalog
# (that inversion shipped for months: internals injected, user verbs hidden).
for sd in "$CODEX_DIR/skills"/*/; do
  sname=$(basename "$sd")
  if ! grep -q 'allow_implicit_invocation:' "$sd/agents/openai.yaml" 2>/dev/null; then
    echo -e "  ${RED}✗${NC} $sname has no explicit allow_implicit_invocation (Codex defaults ABSENT to true) - add a generate_openai_yaml call"
    yaml_errors=$((yaml_errors + 1))
  fi
done

# Catalog-budget guard: surfaced (implicit true) skills' mirror descriptions
# are injected verbatim into the shared skills context budget (min(8000 chars,
# 2% of window)); the diet pass above must keep each <=200 chars.
for sd in "$CODEX_DIR/skills"/*/; do
  sname=$(basename "$sd")
  grep -q 'allow_implicit_invocation: true' "$sd/agents/openai.yaml" 2>/dev/null || continue
  dlen=$(awk '/^description:/{sub(/^description: */,""); print length($0); exit}' "$sd/SKILL.md" 2>/dev/null)
  if [ -z "$dlen" ] || [ "$dlen" -gt 200 ]; then
    echo -e "  ${RED}✗${NC} $sname is surfaced in the model catalog but its description is ${dlen:-missing} chars (max 200) - add/trim its DIET entry"
    yaml_errors=$((yaml_errors + 1))
  fi
done

if [ "$yaml_errors" -eq 0 ]; then
  echo -e "  ${GREEN}✓${NC} All openai.yaml files have required keys, explicit catalog policy, and dieted surfaced descriptions"
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

echo -e "${GREEN}Sync complete:${NC} $skill_count skills, $agent_count agents (no default hooks)"
echo -e "  ${BLUE}Output:${NC} plugins/flow-next/codex/"
