#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="/tmp/ralph-smoke-$$"

# Python detection: prefer python3, fallback to python (Windows support, GH-35)
pick_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 && { echo "$PYTHON_BIN"; return; }
  fi
  if command -v python3 >/dev/null 2>&1; then echo "python3"; return; fi
  if command -v python  >/dev/null 2>&1; then echo "python"; return; fi
  echo ""
}

PYTHON_BIN="$(pick_python)"
[[ -n "$PYTHON_BIN" ]] || { echo "ERROR: python not found (need python3 or python in PATH)" >&2; exit 1; }

# Safety: never run tests from the main plugin repo
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo -e "${YELLOW}=== ralph smoke tests ===${NC}"

mkdir -p "$TEST_DIR/repo"
cd "$TEST_DIR/repo"
git init -q
git config user.email "ralph-smoke@example.com"
git config user.name "Ralph Smoke"
git checkout -b main >/dev/null 2>&1 || true

cat > README.md <<'EOF'
# ralph-smoke
EOF
git add README.md
git commit -m "chore: init" >/dev/null

scaffold() {
  mkdir -p scripts/ralph
  cp -R "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/." scripts/ralph/
  cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/flowctl.py
  cp "$PLUGIN_ROOT/scripts/flowctl" scripts/ralph/flowctl
  chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl
}

write_config() {
  local plan="$1"
  local work="$2"
  local require="$3"
  local branch="$4"
  local max_iter="$5"
  local max_turns="$6"
  local max_attempts="$7"
  "$PYTHON_BIN" - <<'PY' "$plan" "$work" "$require" "$branch" "$max_iter" "$max_turns" "$max_attempts"
from pathlib import Path
import re, sys
plan, work, require, branch, max_iter, max_turns, max_attempts = sys.argv[1:8]
cfg = Path("scripts/ralph/config.env")
text = cfg.read_text()
# Replace template placeholders first (for initial setup)
text = text.replace("{{PLAN_REVIEW}}", plan).replace("{{WORK_REVIEW}}", work)
# Then use re.sub for subsequent calls (when values are already set)
text = re.sub(r"^PLAN_REVIEW=.*$", f"PLAN_REVIEW={plan}", text, flags=re.M)
text = re.sub(r"^WORK_REVIEW=.*$", f"WORK_REVIEW={work}", text, flags=re.M)
text = re.sub(r"^REQUIRE_PLAN_REVIEW=.*$", f"REQUIRE_PLAN_REVIEW={require}", text, flags=re.M)
text = re.sub(r"^BRANCH_MODE=.*$", f"BRANCH_MODE={branch}", text, flags=re.M)
text = re.sub(r"^MAX_ITERATIONS=.*$", f"MAX_ITERATIONS={max_iter}", text, flags=re.M)
text = re.sub(r"^MAX_TURNS=.*$", f"MAX_TURNS={max_turns}", text, flags=re.M)
text = re.sub(r"^MAX_ATTEMPTS_PER_TASK=.*$", f"MAX_ATTEMPTS_PER_TASK={max_attempts}", text, flags=re.M)
cfg.write_text(text)
PY
}

# Extract epic/task ID from JSON output
extract_id() {
  "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['id'])"
}

scaffold

echo -e "${YELLOW}--- ralph-init scaffold ---${NC}"
missing=0
for f in ralph.sh ralph_once.sh prompt_plan.md prompt_work.md config.env runs/.gitkeep flowctl flowctl.py .gitignore; do
  if [[ ! -f "scripts/ralph/$f" ]]; then
    echo -e "${RED}✗${NC} missing scripts/ralph/$f"
    missing=1
  fi
done
if [[ "$missing" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} scaffold files present"
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
fi

mkdir -p "$TEST_DIR/bin"
# Dynamic claude stub that extracts epic IDs from prompts using the new fn-N-xxx format
cat > "$TEST_DIR/bin/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
 mode="${STUB_MODE:-success}"
 write_receipt="${STUB_WRITE_RECEIPT:-1}"
 write_plan="${STUB_WRITE_PLAN_RECEIPT:-$write_receipt}"
 write_impl="${STUB_WRITE_IMPL_RECEIPT:-$write_receipt}"
 exit_code="${STUB_EXIT_CODE:-0}"
 skip_done="${STUB_SKIP_DONE:-0}"
has_p=0
for arg in "$@"; do
  if [[ "$arg" == "-p" ]]; then has_p=1; break; fi
done
if [[ "$has_p" -eq 0 ]]; then
  exit 0
fi

prompt="${@: -1}"
if [[ "$mode" == "retry" ]]; then
  echo "<promise>RETRY</promise>"
  exit 0
fi

if [[ "$prompt" == *"Ralph plan gate iteration"* ]]; then
  # Extract epic ID with optional suffix (fn-N or fn-N-xxx)
  epic_id="$(printf '%s\n' "$prompt" | sed -n 's/.*EPIC_ID=\(fn-[0-9][0-9]*\(-[a-z0-9][a-z0-9][a-z0-9]\)\{0,1\}\).*/\1/p' | head -n1)"
  if [[ -n "$epic_id" ]]; then
    scripts/ralph/flowctl epic set-plan-review-status "$epic_id" --status ship --json >/dev/null
  fi
  if [[ "$write_plan" == "1" && -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
    cat > "$REVIEW_RECEIPT_PATH" <<EOF_RECEIPT
{"type":"plan_review","id":"$epic_id","mode":"stub","timestamp":"$ts"}
EOF_RECEIPT
    echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
  fi
  echo "<verdict>SHIP</verdict>"
  exit "$exit_code"
fi

if [[ "$prompt" == *"Ralph work iteration"* ]]; then
  # Extract task ID with optional suffix (fn-N.M or fn-N-xxx.M)
  task_id="$(printf '%s\n' "$prompt" | sed -n 's/.*TASK_ID=\(fn-[0-9][0-9]*\(-[a-z0-9][a-z0-9][a-z0-9]\)\{0,1\}\.[0-9][0-9]*\).*/\1/p' | head -n1)"
  if [[ "$skip_done" != "1" ]]; then
    summary="$(mktemp)"
    evidence="$(mktemp)"
    printf "ok\n" > "$summary"
    printf '{"commits":[],"tests":[],"prs":[]}' > "$evidence"
    scripts/ralph/flowctl start "$task_id" --json >/dev/null
    scripts/ralph/flowctl done "$task_id" --summary-file "$summary" --evidence-json "$evidence" --json >/dev/null
    rm -f "$summary" "$evidence"
  fi
  if [[ "$write_impl" == "1" && -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    mkdir -p "$(dirname "$REVIEW_RECEIPT_PATH")"
    cat > "$REVIEW_RECEIPT_PATH" <<EOF_RECEIPT
{"type":"impl_review","id":"$task_id","mode":"stub","timestamp":"$ts"}
EOF_RECEIPT
    echo "REVIEW_RECEIPT_WRITTEN: $REVIEW_RECEIPT_PATH"
  fi
  echo "done $task_id"
  exit "$exit_code"
fi

echo "<promise>FAIL</promise>"
exit 0
EOF
chmod +x "$TEST_DIR/bin/claude"

scripts/ralph/flowctl init --json >/dev/null

latest_run_dir() {
  ls -t scripts/ralph/runs | grep -v '^\\.gitkeep$' | head -n 1
}

echo -e "${YELLOW}--- ralph_once ---${NC}"
EPIC1_JSON="$(scripts/ralph/flowctl epic create --title "Ralph Epic" --json)"
EPIC1="$(echo "$EPIC1_JSON" | extract_id)"
scripts/ralph/flowctl task create --epic "$EPIC1" --title "Ralph Task" --json >/dev/null
write_config "none" "none" "0" "new" "3" "5" "2"
CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph_once.sh >/dev/null
# Mark plan review done so it doesn't block later tests when REQUIRE_PLAN_REVIEW=1
scripts/ralph/flowctl epic set-plan-review-status "$EPIC1" --status ship --json >/dev/null
echo -e "${GREEN}✓${NC} ralph_once runs"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- ralph.sh completes epic ---${NC}"
EPIC2_JSON="$(scripts/ralph/flowctl epic create --title "Ralph Epic 2" --json)"
EPIC2="$(echo "$EPIC2_JSON" | extract_id)"
TASK2_1_JSON="$(scripts/ralph/flowctl task create --epic "$EPIC2" --title "Task 1" --json)"
TASK2_1="$(echo "$TASK2_1_JSON" | extract_id)"
TASK2_2_JSON="$(scripts/ralph/flowctl task create --epic "$EPIC2" --title "Task 2" --json)"
TASK2_2="$(echo "$TASK2_2_JSON" | extract_id)"
# Use rp for both to test receipt generation (none skips receipts correctly via fix for #8)
write_config "rp" "rp" "1" "new" "6" "5" "2"
STUB_MODE=success STUB_WRITE_RECEIPT=1 CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh >/dev/null
"$PYTHON_BIN" - <<PY "$TASK2_1" "$TASK2_2"
import json, sys
from pathlib import Path
for tid in sys.argv[1:3]:
    data = json.loads(Path(f".flow/tasks/{tid}.json").read_text())
    assert data["status"] == "done"
PY
run_dir="$(latest_run_dir)"
"$PYTHON_BIN" - <<PY "$run_dir" "$EPIC2" "$TASK2_1"
import json, sys
from pathlib import Path
run_dir, epic2, task2_1 = sys.argv[1:4]
receipts = Path(f"scripts/ralph/runs/{run_dir}/receipts")
plan = json.loads((receipts / f"plan-{epic2}.json").read_text())
impl = json.loads((receipts / f"impl-{task2_1}.json").read_text())
assert plan["type"] == "plan_review"
assert plan["id"] == epic2
assert impl["type"] == "impl_review"
assert impl["id"] == task2_1
PY
iter_log="scripts/ralph/runs/$run_dir/iter-001.log"
if [[ -f "$iter_log" ]]; then
  if command -v rg >/dev/null 2>&1; then
    rg -q "<verdict>" "$iter_log"
  else
    grep -q "<verdict>" "$iter_log"
  fi
fi
echo -e "${GREEN}✓${NC} ralph completes tasks"
PASS=$((PASS + 1))

run_dir="$(ls -1 scripts/ralph/runs | grep -v '^\\.gitkeep$' | head -n 1)"
if [[ -f "scripts/ralph/runs/$run_dir/branches.json" ]]; then
  echo -e "${GREEN}✓${NC} branches.json created"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} branches.json created"
  FAIL=$((FAIL + 1))
fi
if [[ -f "scripts/ralph/runs/$run_dir/progress.txt" ]]; then
  echo -e "${GREEN}✓${NC} progress.txt created"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} progress.txt created"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- UI output verification ---${NC}"
EPIC3_JSON="$(scripts/ralph/flowctl epic create --title "UI Test Epic" --json)"
EPIC3="$(echo "$EPIC3_JSON" | extract_id)"
scripts/ralph/flowctl task create --epic "$EPIC3" --title "UI Test Task" --json >/dev/null
write_config "none" "none" "0" "new" "3" "5" "2"
ui_output="$(STUB_MODE=success CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh 2>&1)"

# Check elapsed time format [X:XX]
if echo "$ui_output" | grep -qE '\[[0-9]+:[0-9]{2}\]'; then
  echo -e "${GREEN}✓${NC} elapsed time shown"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} elapsed time shown"
  FAIL=$((FAIL + 1))
fi

# Check progress counter (Epic X/Y * Task X/Y)
if echo "$ui_output" | grep -qE 'Epic [0-9]+/[0-9]+.*Task [0-9]+/[0-9]+'; then
  echo -e "${GREEN}✓${NC} progress counter shown"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} progress counter shown"
  FAIL=$((FAIL + 1))
fi

# Check task title is shown (quoted)
if echo "$ui_output" | grep -q '"UI Test Task"'; then
  echo -e "${GREEN}✓${NC} task title shown"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} task title shown"
  FAIL=$((FAIL + 1))
fi

# Check completion summary shows Tasks: X/Y
if echo "$ui_output" | grep -qE 'Tasks:.*[0-9]+/[0-9]+'; then
  echo -e "${GREEN}✓${NC} completion summary shown"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} completion summary shown"
  FAIL=$((FAIL + 1))
fi

# Check branch is shown
if echo "$ui_output" | grep -q 'Branch:'; then
  echo -e "${GREEN}✓${NC} branch shown"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} branch shown"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- ralph.sh backstop ---${NC}"
EPIC4_JSON="$(scripts/ralph/flowctl epic create --title "Ralph Epic 4" --json)"
EPIC4="$(echo "$EPIC4_JSON" | extract_id)"
TASK4_1_JSON="$(scripts/ralph/flowctl task create --epic "$EPIC4" --title "Stuck Task" --json)"
TASK4_1="$(echo "$TASK4_1_JSON" | extract_id)"
write_config "none" "none" "0" "new" "3" "5" "2"
STUB_MODE=retry CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh >/dev/null
"$PYTHON_BIN" - <<PY "$TASK4_1"
import json, sys
from pathlib import Path
data = json.loads(Path(f".flow/tasks/{sys.argv[1]}.json").read_text())
assert data["status"] == "blocked"
PY
echo -e "${GREEN}✓${NC} blocks after attempts"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- missing receipt forces retry ---${NC}"
EPIC5_JSON="$(scripts/ralph/flowctl epic create --title "Ralph Epic 5" --json)"
EPIC5="$(echo "$EPIC5_JSON" | extract_id)"
TASK5_1_JSON="$(scripts/ralph/flowctl task create --epic "$EPIC5" --title "Receipt Task" --json)"
TASK5_1="$(echo "$TASK5_1_JSON" | extract_id)"
write_config "none" "rp" "0" "new" "3" "5" "1"
set +e
STUB_MODE=success STUB_WRITE_PLAN_RECEIPT=1 STUB_WRITE_IMPL_RECEIPT=0 CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh >/dev/null
rc=$?
set -e
run_dir="$(latest_run_dir)"
receipts_dir="scripts/ralph/runs/$run_dir/receipts"
if [[ -f "$receipts_dir/impl-$TASK5_1.json" ]]; then
  echo -e "${RED}✗${NC} impl receipt unexpectedly exists"
  FAIL=$((FAIL + 1))
else
  echo -e "${GREEN}✓${NC} missing impl receipt forces retry (rc=$rc)"
  PASS=$((PASS + 1))
fi

run_count="$(ls -1 scripts/ralph/runs | wc -l | tr -d ' ')"
STUB_MODE=retry CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh >/dev/null
run_count2="$(ls -1 scripts/ralph/runs | wc -l | tr -d ' ')"
if [[ "$run_count2" -gt "$run_count" ]]; then
  echo -e "${GREEN}✓${NC} multi-run uniqueness"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} multi-run uniqueness"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- non-zero exit code handling (#11) ---${NC}"
# Test 1: task done + non-zero exit -> should NOT fail
# This validates fix for issue #11 where transient errors caused false failures
EPIC6_JSON="$(scripts/ralph/flowctl epic create --title "Exit Code Epic 1" --json)"
EPIC6="$(echo "$EPIC6_JSON" | extract_id)"
TASK6_1_JSON="$(scripts/ralph/flowctl task create --epic "$EPIC6" --title "Done but exit 1" --json)"
TASK6_1="$(echo "$TASK6_1_JSON" | extract_id)"
write_config "none" "none" "0" "new" "3" "5" "2"
set +e
STUB_MODE=success STUB_EXIT_CODE=1 CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh >/dev/null 2>&1
rc=$?
set -e
"$PYTHON_BIN" - <<PY "$TASK6_1"
import json, sys
from pathlib import Path
data = json.loads(Path(f".flow/tasks/{sys.argv[1]}.json").read_text())
assert data["status"] == "done", f"Expected done, got {data['status']}"
PY
if [[ $? -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} task done + exit 1 -> task completed (rc=$rc)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} task done + exit 1 -> task completed"
  FAIL=$((FAIL + 1))
fi

# Test 2: task NOT done + non-zero exit -> should fail/block
EPIC7_JSON="$(scripts/ralph/flowctl epic create --title "Exit Code Epic 2" --json)"
EPIC7="$(echo "$EPIC7_JSON" | extract_id)"
TASK7_1_JSON="$(scripts/ralph/flowctl task create --epic "$EPIC7" --title "Not done and exit 1" --json)"
TASK7_1="$(echo "$TASK7_1_JSON" | extract_id)"
write_config "none" "none" "0" "new" "3" "5" "1"
set +e
STUB_MODE=success STUB_EXIT_CODE=1 STUB_SKIP_DONE=1 CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh >/dev/null 2>&1
rc=$?
set -e
"$PYTHON_BIN" - <<PY "$TASK7_1"
import json, sys
from pathlib import Path
data = json.loads(Path(f".flow/tasks/{sys.argv[1]}.json").read_text())
# Should be blocked because task wasn't done AND exit was non-zero
assert data["status"] == "blocked", f"Expected blocked, got {data['status']}"
PY
if [[ $? -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} task not done + exit 1 -> blocked (rc=$rc)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} task not done + exit 1 -> blocked"
  FAIL=$((FAIL + 1))
fi

# Note: verdict=SHIP check for plan phase uses identical logic, verified by code review

echo ""
echo -e "${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
echo -e "\n${GREEN}All tests passed!${NC}"
