#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Python interpreter resolution via the shared functionality probe (skips the
# Windows Store python3 alias stub; fills the FLOW_PY array). See lib/pick-python.sh.
# shellcheck source=lib/pick-python.sh
. "$SCRIPT_DIR/lib/pick-python.sh"
pick_python || { echo "ERROR: python not found (need python3 or python in PATH)" >&2; exit 1; }

# Safety: never run tests from the main plugin repo
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-/tmp/flow-next-ralph-e2e-rp-$$}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
FLOWCTL=""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() { echo "ralph_e2e_rp: $*" >&2; exit 1; }

run_with_timeout() {
  local timeout_s="$1"
  shift
  "${FLOW_PY[@]}" - "$timeout_s" "$@" <<'PY'
import subprocess, sys
try:
    timeout = float(sys.argv[1])
except Exception:
    timeout = 0
cmd = sys.argv[2:]
try:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout if timeout > 0 else None)
except subprocess.TimeoutExpired:
    print(f"timeout after {timeout}s: {' '.join(cmd)}", file=sys.stderr)
    sys.exit(124)
if proc.stdout:
    sys.stdout.write(proc.stdout)
if proc.stderr:
    sys.stderr.write(proc.stderr)
sys.exit(proc.returncode)
PY
}

retry_cmd() {
  local label="$1"
  local timeout_s="$2"
  local retries="$3"
  shift 3
  local attempt=1
  while true; do
    if out="$(run_with_timeout "$timeout_s" "$@")"; then
      echo "$out"
      return 0
    fi
    local rc="$?"
    if [[ "$attempt" -ge "$retries" ]]; then
      echo "ralph_e2e_rp: $label failed after $attempt attempts" >&2
      return "$rc"
    fi
    attempt="$((attempt + 1))"
    sleep 2
  done
}

swap_tmp_root() {
  "${FLOW_PY[@]}" - "$1" <<'PY'
import sys
path = sys.argv[1]
if path.startswith("/private/tmp/"):
    print("/tmp/" + path[len("/private/tmp/"):])
elif path.startswith("/tmp/"):
    print("/private/tmp/" + path[len("/tmp/"):])
else:
    print(path)
PY
}

latest_jsonl() {
  # Search in project subdirectories (flat names like -private-tmp-...), exclude agent logs
  # Use ~ which expands reliably even when $HOME is unset
  # Return only files that exist and are readable
  local candidate
  candidate=$(find ~/.claude/projects -maxdepth 2 -name "*.jsonl" ! -name "agent-*.jsonl" -type f -print 2>/dev/null | \
    xargs ls -t 2>/dev/null | head -n 1)
  if [[ -n "$candidate" && -r "$candidate" ]]; then
    echo "$candidate"
    return
  fi
  candidate=$(find ~/.claude/transcripts -maxdepth 1 -name "*.jsonl" -type f -print 2>/dev/null | \
    xargs ls -t 2>/dev/null | head -n 1)
  if [[ -n "$candidate" && -r "$candidate" ]]; then
    echo "$candidate"
  fi
}

new_session_id() {
  "${FLOW_PY[@]}" - <<'PY'
import uuid
print(uuid.uuid4())
PY
}


find_jsonl() {
  if [[ -n "${FLOW_RALPH_CLAUDE_SESSION_ID:-}" ]]; then
    if command -v fd >/dev/null 2>&1; then
      fd -a "${FLOW_RALPH_CLAUDE_SESSION_ID}.jsonl" "$HOME/.claude/projects" | head -n 1 || true
    else
      find "$HOME/.claude/projects" -name "${FLOW_RALPH_CLAUDE_SESSION_ID}.jsonl" -print 2>/dev/null | head -n 1 || true
    fi
  fi
}
cleanup() {
  if [[ "${KEEP_TEST_DIR:-0}" != "1" && "${CREATE:-0}" != "1" ]]; then
    rm -rf "$TEST_DIR"
  fi
}
trap cleanup EXIT

command -v "$CLAUDE_BIN" >/dev/null 2>&1 || fail "claude not found (set CLAUDE_BIN if needed)"
command -v rp-cli >/dev/null 2>&1 || fail "rp-cli not found (required for rp review)"

echo -e "${YELLOW}=== ralph e2e (rp reviews) ===${NC}"
echo "Test dir: $TEST_DIR"

mkdir -p "$TEST_DIR/repo"
cd "$TEST_DIR/repo"
git init -q
git config user.email "ralph-e2e@example.com"
git config user.name "Ralph E2E"
git checkout -b main >/dev/null 2>&1 || true

mkdir -p src
cat > src/index.ts <<'EOF'
export const placeholder = 0;
EOF

cat > package.json <<'EOF'
{
  "name": "tmp-flow-next-ralph",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "test": "node -e \"console.log('ok')\""
  }
}
EOF

cat > README.md <<'EOF'
# tmp-flow-next-ralph

TBD
EOF

git add .
git commit -m "chore: init" >/dev/null

mkdir -p scripts/ralph
cp -R "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/." scripts/ralph/
cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl_bootstrap.py" scripts/ralph/flowctl_bootstrap.py
cp "$PLUGIN_ROOT/scripts/flowctl" scripts/ralph/flowctl
chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl
FLOWCTL="scripts/ralph/flowctl"

"${FLOW_PY[@]}" - <<'PY'
from pathlib import Path
import re
cfg = Path("scripts/ralph/config.env")
text = cfg.read_text()
text = text.replace("{{PLAN_REVIEW}}", "rp").replace("{{WORK_REVIEW}}", "rp")
text = re.sub(r"^REQUIRE_PLAN_REVIEW=.*$", "REQUIRE_PLAN_REVIEW=1", text, flags=re.M)
text = re.sub(r"^BRANCH_MODE=.*$", "BRANCH_MODE=new", text, flags=re.M)
text = re.sub(r"^MAX_ITERATIONS=.*$", "MAX_ITERATIONS=8", text, flags=re.M)
# MAX_TURNS not limited - let Claude finish naturally via promise tags
text = re.sub(r"^MAX_ATTEMPTS_PER_TASK=.*$", "MAX_ATTEMPTS_PER_TASK=2", text, flags=re.M)
text = re.sub(r"^YOLO=.*$", "YOLO=1", text, flags=re.M)
text = re.sub(r"^EPICS=.*$", "EPICS=fn-1,fn-2", text, flags=re.M)
cfg.write_text(text)
PY

scripts/ralph/flowctl init --json >/dev/null

# Mirror /flow-next:setup - add .flow/bin/ + usage.md + CLAUDE.md
mkdir -p .flow/bin
cp "$PLUGIN_ROOT/scripts/flowctl" .flow/bin/flowctl
cp "$PLUGIN_ROOT/scripts/flowctl.py" .flow/bin/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl_bootstrap.py" .flow/bin/flowctl_bootstrap.py
chmod +x .flow/bin/flowctl
cp "$PLUGIN_ROOT/templates/usage.md" .flow/usage.md
cat "$PLUGIN_ROOT/skills/flow-next-setup/templates/claude-md-snippet.md" > CLAUDE.md
echo -e "${GREEN}✓${NC} Setup mirrored (.flow/bin/, usage.md, CLAUDE.md)"

scripts/ralph/flowctl spec create --title "Tiny lib" --json >/dev/null
scripts/ralph/flowctl spec create --title "Tiny follow-up" --json >/dev/null

cat > "$TEST_DIR/epic.md" <<'EOF'
# fn-1 Tiny lib

## Overview
Add a production-quality add() helper with proper validation and documentation.

## Function Contract
- Signature: `add(a: number, b: number): number`
- Named export only from `src/index.ts`
- MUST validate inputs at runtime (throw TypeError if not numbers)
- Standard JS addition semantics for valid numbers (NaN/Infinity follow JS)

## Current State
- `src/index.ts` does not yet export `add()`
- README is a placeholder

## Scope
- `src/index.ts`: add `add()` with runtime validation and full JSDoc
- `README.md`: add usage snippet with error handling example

## Approach
Edit src/index.ts and README.md only. Repo is source-only (no build step).

## Quick commands
- `npm test` (smoke only)

## Acceptance
- [ ] `add(a: number, b: number): number` exported as named export
- [ ] Runtime validation: throw `TypeError` if either argument is not a number
- [ ] JSDoc MUST include:
  - @param tags for both parameters
  - @returns tag
  - @throws tag documenting TypeError
  - @example tag with working code
- [ ] README includes:
  - usage snippet showing successful call
  - error handling example with try/catch
  - note that this is TypeScript source and requires TS tooling to run
- [ ] `npm test` passes (smoke only)

## Risks
- README import path is TypeScript source; call out runtime requirements
- Easy to forget @throws in JSDoc (common pitfall)

## References
- None
EOF

scripts/ralph/flowctl spec set-plan fn-1 --file "$TEST_DIR/epic.md" --json >/dev/null
scripts/ralph/flowctl spec set-plan fn-2 --file "$TEST_DIR/epic.md" --json >/dev/null
scripts/ralph/flowctl spec set-plan-review-status fn-2 --status ship --json >/dev/null

cat > "$TEST_DIR/accept.md" <<'EOF'
- [ ] Export `add(a: number, b: number): number` from `src/index.ts`
- [ ] Add brief JSDoc for `add()` (params + return)
- [ ] README snippet uses `import { add } from "./src/index.ts"` and shows `console.log(add(1,2)) // 3`
- [ ] README notes TS tooling required to run snippet
- [ ] `npm test` passes (smoke only)
EOF

scripts/ralph/flowctl task create --spec fn-1 --title "Add add() helper" --acceptance-file "$TEST_DIR/accept.md" --json >/dev/null
scripts/ralph/flowctl task create --spec fn-2 --title "Add tiny note" --acceptance-file "$TEST_DIR/accept.md" --json >/dev/null

mkdir -p "$TEST_DIR/bin"
PLUGINS_DIR="$(dirname "$PLUGIN_ROOT")"
cat > "$TEST_DIR/bin/claude" <<EOF
#!/usr/bin/env bash
exec "$CLAUDE_BIN" --plugin-dir "$PLUGINS_DIR" "\$@"
EOF
chmod +x "$TEST_DIR/bin/claude"

# Workaround for plugin hooks bug (#14410): --plugin-dir hooks don't execute.
# Copy hooks to project scope so they run properly.
HOOKS_SRC="$PLUGIN_ROOT/scripts/hooks"
if [[ -d "$HOOKS_SRC" ]]; then
  mkdir -p ".claude/hooks"
  cp -r "$HOOKS_SRC"/* ".claude/hooks/"
  chmod +x ".claude/hooks/"*.py 2>/dev/null || true
  cat > ".claude/settings.local.json" <<'HOOKSJSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]
      }
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]}
    ],
    "SubagentStop": [
      {"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]}
    ]
  }
}
HOOKSJSON
  echo -e "${GREEN}✓${NC} Hooks installed to .claude/hooks/ (workaround for #14410)"
fi

# CREATE mode: set up repo and exit (user opens RP, then re-runs without CREATE)
if [[ "${CREATE:-0}" == "1" ]]; then
  echo -e "${GREEN}✓${NC} Test repo created: $TEST_DIR/repo"
  echo ""
  echo "Next steps:"
  echo "  1. Open RepoPrompt on: $TEST_DIR/repo"
  echo "  2. Re-run without CREATE:"
  echo "     TEST_DIR=$TEST_DIR KEEP_TEST_DIR=1 $0"
  exit 0
fi

echo -e "${YELLOW}--- running ralph (rp) ---${NC}"
REPO_ROOT="$(pwd)"

# Optional preflight using atomic setup-review
if [[ "${RP_PREFLIGHT:-0}" == "1" ]]; then
  preflight_msg="$TEST_DIR/preflight.md"
  cat > "$preflight_msg" <<'EOF'
Smoke preflight: confirm chat pipeline.
EOF
  eval "$(retry_cmd "rp setup-review" 180 2 "$FLOWCTL" rp setup-review --repo-root "$REPO_ROOT" --summary "Smoke preflight")"
  [[ -n "$W" && -n "$T" ]] || fail "setup-review failed: W=$W T=$T"
  retry_cmd "rp chat-send" 180 2 "$FLOWCTL" rp chat-send --window "$W" --tab "$T" --message-file "$preflight_msg" --new-chat --chat-name "Smoke Preflight" >/dev/null
fi
CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh

"${FLOW_PY[@]}" - <<'PY'
import json
from pathlib import Path
for tid in ["fn-1.1", "fn-2.1"]:
    data = json.loads(Path(f".flow/tasks/{tid}.json").read_text())
    assert data["status"] == "done"
runs = [p for p in Path("scripts/ralph/runs").iterdir() if p.is_dir() and p.name != ".gitkeep"]
runs.sort()
run_dir = runs[0].name
assert Path(f"scripts/ralph/runs/{run_dir}/progress.txt").exists()
data = json.loads(Path(f"scripts/ralph/runs/{run_dir}/branches.json").read_text())
# Check run branch format (single branch for all epics)
assert "run_branch" in data, "branches.json should have run_branch"
assert data["run_branch"].startswith("ralph-"), f"run_branch should start with 'ralph-': {data['run_branch']}"
assert "base_branch" in data, "branches.json should have base_branch"
receipts = Path(f"scripts/ralph/runs/{run_dir}/receipts")
plan = json.loads(Path(receipts / "plan-fn-1.json").read_text())
assert plan["type"] == "plan_review"
assert plan["id"] == "fn-1"
impl1 = json.loads(Path(receipts / "impl-fn-1.1.json").read_text())
assert impl1["type"] == "impl_review"
assert impl1["id"] == "fn-1.1"
impl2 = json.loads(Path(receipts / "impl-fn-2.1.json").read_text())
assert impl2["type"] == "impl_review"
assert impl2["id"] == "fn-2.1"
PY

if [[ "${FLOW_RALPH_VERBOSE:-}" == "1" ]]; then
  run_dir="$(ls -t scripts/ralph/runs | grep -v '^\\.gitkeep$' | head -n 1)"
  log_file="scripts/ralph/runs/$run_dir/ralph.log"
  [[ -f "$log_file" ]] || fail "missing verbose log $log_file"
  if command -v rg >/dev/null 2>&1; then
    rg -q "flowctl rp setup-review" "$log_file" || fail "missing setup-review in ralph.log"
    rg -q "flowctl rp chat-send" "$log_file" || fail "missing chat-send in ralph.log"
    rg -q "REVIEW_RECEIPT_WRITTEN" "$log_file" || fail "missing receipt marker in ralph.log"
  else
    grep -q "flowctl rp setup-review" "$log_file" || fail "missing setup-review in ralph.log"
    grep -q "flowctl rp chat-send" "$log_file" || fail "missing chat-send in ralph.log"
    grep -q "REVIEW_RECEIPT_WRITTEN" "$log_file" || fail "missing receipt marker in ralph.log"
  fi
fi

jsonl="$(find_jsonl)"
[[ -n "$jsonl" ]] || jsonl="$(latest_jsonl)"
[[ -n "$jsonl" ]] || fail "no claude jsonl logs found"
[[ -r "$jsonl" ]] || fail "jsonl file not readable: $jsonl"
if command -v rg >/dev/null 2>&1; then
  rg -q --no-messages "REVIEW_RECEIPT_WRITTEN" "$jsonl" || fail "missing receipt marker in jsonl"
  rg -q --no-messages "<verdict>" "$jsonl" || fail "missing verdict tag in jsonl"
else
  grep -q "REVIEW_RECEIPT_WRITTEN" "$jsonl" || fail "missing receipt marker in jsonl"
  grep -q "<verdict>" "$jsonl" || fail "missing verdict tag in jsonl"
fi

echo -e "${GREEN}✓${NC} task done"
echo -e "${GREEN}✓${NC} ralph e2e rp complete"
echo "Claude logs: $HOME/.claude/projects"
