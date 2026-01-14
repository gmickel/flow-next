#!/usr/bin/env bash
# Comprehensive CI tests for flowctl.py and ralph.sh helpers
# Runs on Linux, macOS, and Windows (Git Bash)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Python detection
pick_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 && { echo "$PYTHON_BIN"; return; }
  fi
  if command -v python3 >/dev/null 2>&1; then echo "python3"; return; fi
  if command -v python  >/dev/null 2>&1; then echo "python"; return; fi
  echo ""
}

PYTHON_BIN="$(pick_python)"
[[ -n "$PYTHON_BIN" ]] || { echo "ERROR: python not found" >&2; exit 1; }

# Use provided TEST_DIR or create temp
if [[ -z "${TEST_DIR:-}" ]]; then
  TEST_DIR="$(mktemp -d)"
  CLEANUP_TEST_DIR=1
else
  CLEANUP_TEST_DIR=0
fi

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
  [[ "$CLEANUP_TEST_DIR" == "1" ]] && rm -rf "$TEST_DIR"
}
trap cleanup EXIT

pass() { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }

# Helper to run flowctl
flowctl() {
  "$PYTHON_BIN" "$TEST_DIR/scripts/flowctl.py" "$@"
}

echo -e "${YELLOW}=== flow-next CI tests ===${NC}"
echo "Python: $PYTHON_BIN"
echo "Test dir: $TEST_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p "$TEST_DIR/scripts"
cd "$TEST_DIR"
git init -q
git config user.email "ci@test.local"
git config user.name "CI Test"

cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/

# ─────────────────────────────────────────────────────────────────────────────
# 1. Basic Commands
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Basic Commands ---${NC}"

flowctl init --json >/dev/null && pass "init" || fail "init"

EPIC_JSON="$(flowctl epic create --title "Test Epic" --json)"
EPIC_ID="$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$EPIC_JSON")"
[[ -n "$EPIC_ID" ]] && pass "epic create ($EPIC_ID)" || fail "epic create"

TASK1_JSON="$(flowctl task create --epic "$EPIC_ID" --title "Task One" --priority 2 --json)"
TASK1_ID="$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$TASK1_JSON")"
[[ -n "$TASK1_ID" ]] && pass "task create ($TASK1_ID)" || fail "task create"

TASK2_JSON="$(flowctl task create --epic "$EPIC_ID" --title "Task Two" --priority 1 --json)"
TASK2_ID="$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$TASK2_JSON")"

flowctl list --json >/dev/null && pass "list" || fail "list"
flowctl show "$EPIC_ID" --json >/dev/null && pass "show epic" || fail "show epic"
flowctl show "$TASK1_ID" --json >/dev/null && pass "show task" || fail "show task"

# ─────────────────────────────────────────────────────────────────────────────
# 2. State Machine Transitions
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- State Machine ---${NC}"

# next should return plan (no plan review yet)
NEXT_JSON="$(flowctl next --require-plan-review --json)"
STATUS="$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['status'])" <<< "$NEXT_JSON")"
[[ "$STATUS" == "plan" ]] && pass "next returns plan" || fail "next returns plan (got $STATUS)"

# set plan review status
flowctl epic set-plan-review-status "$EPIC_ID" --status ship --json >/dev/null && pass "set-plan-review-status" || fail "set-plan-review-status"

# next should now return work with higher priority task (Task Two, priority 1)
NEXT_JSON="$(flowctl next --json)"
NEXT_TASK="$("$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin).get('task',''))" <<< "$NEXT_JSON")"
[[ "$NEXT_TASK" == "$TASK2_ID" ]] && pass "next picks high priority task" || fail "next picks high priority (expected $TASK2_ID, got $NEXT_TASK)"

# start task
flowctl start "$TASK2_ID" --json >/dev/null && pass "start task" || fail "start task"

# verify task is in_progress
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "in_progress" ]] && pass "task status is in_progress" || fail "task status (got $TASK_STATUS)"

# block task (requires --reason-file)
echo "Waiting for external API" > "$TEST_DIR/block_reason.md"
flowctl block "$TASK2_ID" --reason-file "$TEST_DIR/block_reason.md" --json >/dev/null && pass "block task" || fail "block task"
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "blocked" ]] && pass "task status is blocked" || fail "task blocked status (got $TASK_STATUS)"

# Note: there's no unblock command - use --force to restart blocked tasks
flowctl start "$TASK2_ID" --force --json >/dev/null && pass "restart blocked task (--force)" || fail "restart blocked task"
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "in_progress" ]] && pass "task status restored to in_progress" || fail "task unblocked status (got $TASK_STATUS)"

# done task (create temp files for evidence)
echo "Task completed" > "$TEST_DIR/summary.md"
echo '{"commits":["abc123"],"tests":["npm test"],"prs":[]}' > "$TEST_DIR/evidence.json"
flowctl done "$TASK2_ID" --summary-file "$TEST_DIR/summary.md" --evidence-json "$TEST_DIR/evidence.json" --json >/dev/null && pass "done task" || fail "done task"
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "done" ]] && pass "task status is done" || fail "task done status (got $TASK_STATUS)"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Error Handling
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Error Handling ---${NC}"

# Invalid epic ID
set +e
ERR_OUT="$(flowctl show "fn-9999-xxx" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "invalid epic ID returns error" || fail "invalid epic ID should fail"

# Invalid task ID
set +e
ERR_OUT="$(flowctl start "fn-9999-xxx.99" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "invalid task ID returns error" || fail "invalid task ID should fail"

# Double start (task already done)
set +e
ERR_OUT="$(flowctl start "$TASK2_ID" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "start done task returns error" || fail "start done task should fail"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Config System
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Config System ---${NC}"

flowctl config set memory.enabled true --json >/dev/null && pass "config set" || fail "config set"

CONFIG_VAL="$(flowctl config get memory.enabled --json | "$PYTHON_BIN" -c "import json,sys; print(json.load(sys.stdin)['value'])")"
[[ "$CONFIG_VAL" == "True" ]] && pass "config get" || fail "config get (got $CONFIG_VAL)"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Memory System
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Memory System ---${NC}"

flowctl memory init --json >/dev/null && pass "memory init" || fail "memory init"

flowctl memory add --type pitfall "Never use sync IO in async handlers" --json >/dev/null && pass "memory add pitfall" || fail "memory add pitfall"
flowctl memory add --type convention "Use snake_case for functions" --json >/dev/null && pass "memory add convention" || fail "memory add convention"

MEM_LIST="$(flowctl memory list --json)"
# memory list returns {counts: {pitfalls.md: N, conventions.md: M, ...}, total: X}
MEM_TOTAL="$("$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); print(d.get('total', 0))" <<< "$MEM_LIST")"
[[ "$MEM_TOTAL" -ge 2 ]] && pass "memory list ($MEM_TOTAL total)" || fail "memory list (got $MEM_TOTAL)"

# ─────────────────────────────────────────────────────────────────────────────
# 6. Symbol Extraction
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Symbol Extraction ---${NC}"

# Create sample files
mkdir -p "$TEST_DIR/src"

cat > "$TEST_DIR/src/sample.py" << 'EOF'
def calculate_total(items):
    return sum(items)

class OrderProcessor:
    def process(self):
        pass

__all__ = ["calculate_total", "OrderProcessor"]
EOF

cat > "$TEST_DIR/src/sample.ts" << 'EOF'
export function fetchData(url: string): Promise<any> {
    return fetch(url);
}

export class ApiClient {
    constructor() {}
}

export const API_VERSION = "1.0";
EOF

cat > "$TEST_DIR/src/sample.go" << 'EOF'
package main

func ProcessRequest(r *Request) error {
    return nil
}

type Handler struct {
    Name string
}
EOF

cat > "$TEST_DIR/src/sample.rs" << 'EOF'
pub fn handle_event(event: Event) -> Result<(), Error> {
    Ok(())
}

pub struct EventProcessor {
    id: u64,
}

impl EventProcessor {
    pub fn new() -> Self {
        Self { id: 0 }
    }
}
EOF

cat > "$TEST_DIR/src/sample.cs" << 'EOF'
public class UserService {
    public async Task<User> GetUserAsync(int id) {
        return await _repository.FindAsync(id);
    }
}

public interface IRepository<T> {
    Task<T> FindAsync(int id);
}

public record UserDto(string Name, string Email);
EOF

cat > "$TEST_DIR/src/sample.java" << 'EOF'
public class PaymentProcessor {
    public void processPayment(Payment payment) {
        // process
    }
}

public interface PaymentGateway {
    boolean authorize(String token);
}
EOF

# Test symbol extraction via Python directly
"$PYTHON_BIN" - "$TEST_DIR" << 'PYTEST'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
from flowctl import extract_symbols_from_file
from pathlib import Path

test_dir = Path(sys.argv[1])
errors = []

# Python
py_symbols = extract_symbols_from_file(test_dir / "src/sample.py")
if "calculate_total" not in py_symbols:
    errors.append(f"Python: missing calculate_total, got {py_symbols}")
if "OrderProcessor" not in py_symbols:
    errors.append(f"Python: missing OrderProcessor, got {py_symbols}")

# TypeScript
ts_symbols = extract_symbols_from_file(test_dir / "src/sample.ts")
if "fetchData" not in ts_symbols:
    errors.append(f"TS: missing fetchData, got {ts_symbols}")
if "ApiClient" not in ts_symbols:
    errors.append(f"TS: missing ApiClient, got {ts_symbols}")

# Go
go_symbols = extract_symbols_from_file(test_dir / "src/sample.go")
if "ProcessRequest" not in go_symbols:
    errors.append(f"Go: missing ProcessRequest, got {go_symbols}")
if "Handler" not in go_symbols:
    errors.append(f"Go: missing Handler, got {go_symbols}")

# Rust
rs_symbols = extract_symbols_from_file(test_dir / "src/sample.rs")
if "handle_event" not in rs_symbols:
    errors.append(f"Rust: missing handle_event, got {rs_symbols}")
if "EventProcessor" not in rs_symbols:
    errors.append(f"Rust: missing EventProcessor, got {rs_symbols}")

# C#
cs_symbols = extract_symbols_from_file(test_dir / "src/sample.cs")
if "UserService" not in cs_symbols:
    errors.append(f"C#: missing UserService, got {cs_symbols}")
if "IRepository" not in cs_symbols:
    errors.append(f"C#: missing IRepository, got {cs_symbols}")
if "UserDto" not in cs_symbols:
    errors.append(f"C#: missing UserDto (record), got {cs_symbols}")

# Java
java_symbols = extract_symbols_from_file(test_dir / "src/sample.java")
if "PaymentProcessor" not in java_symbols:
    errors.append(f"Java: missing PaymentProcessor, got {java_symbols}")
if "PaymentGateway" not in java_symbols:
    errors.append(f"Java: missing PaymentGateway, got {java_symbols}")

if errors:
    print("Symbol extraction errors:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("All symbol extractions passed")
PYTEST
[[ $? -eq 0 ]] && pass "symbol extraction (6 languages)" || fail "symbol extraction"

# ─────────────────────────────────────────────────────────────────────────────
# 7. ralph.sh Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- ralph.sh Helpers ---${NC}"

# Test tag extraction
"$PYTHON_BIN" - << 'PYTEST'
import re
import sys

def extract_tag(text, tag):
    matches = re.findall(rf"<{tag}>(.*?)</{tag}>", text, flags=re.S)
    return matches[-1] if matches else ""

# Test cases
test1 = "<verdict>SHIP</verdict>"
assert extract_tag(test1, "verdict") == "SHIP", f"Expected SHIP, got {extract_tag(test1, 'verdict')}"

test2 = "<promise>continue</promise> some text <promise>stop</promise>"
assert extract_tag(test2, "promise") == "stop", f"Expected stop (last), got {extract_tag(test2, 'promise')}"

test3 = "no tags here"
assert extract_tag(test3, "verdict") == "", f"Expected empty, got {extract_tag(test3, 'verdict')}"

test4 = "<verdict>NEEDS_WORK</verdict>\n<reason>Missing tests</reason>"
assert extract_tag(test4, "verdict") == "NEEDS_WORK"
assert extract_tag(test4, "reason") == "Missing tests"

print("Tag extraction tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "tag extraction" || fail "tag extraction"

# Test JSON helpers (simulate ralph.sh json_get)
"$PYTHON_BIN" - << 'PYTEST'
import json

def json_get(key, data):
    val = data.get(key)
    if val is None:
        return ""
    elif isinstance(val, bool):
        return "1" if val else "0"
    else:
        return str(val)

test_data = {"status": "work", "task": "fn-1-abc.2", "blocked": False, "count": 5}

assert json_get("status", test_data) == "work"
assert json_get("task", test_data) == "fn-1-abc.2"
assert json_get("blocked", test_data) == "0"
assert json_get("count", test_data) == "5"
assert json_get("missing", test_data) == ""

print("JSON helper tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "JSON helpers" || fail "JSON helpers"

# Test attempts tracking
"$PYTHON_BIN" - "$TEST_DIR" << 'PYTEST'
import json
import sys
from pathlib import Path

test_dir = Path(sys.argv[1])
attempts_file = test_dir / "attempts.json"

def bump_attempts(path, task):
    data = {}
    if path.exists():
        data = json.loads(path.read_text())
    count = int(data.get(task, 0)) + 1
    data[task] = count
    path.write_text(json.dumps(data, indent=2))
    return count

# Test bump
assert bump_attempts(attempts_file, "fn-1.1") == 1
assert bump_attempts(attempts_file, "fn-1.1") == 2
assert bump_attempts(attempts_file, "fn-1.2") == 1
assert bump_attempts(attempts_file, "fn-1.1") == 3

# Verify file content
data = json.loads(attempts_file.read_text())
assert data["fn-1.1"] == 3
assert data["fn-1.2"] == 1

print("Attempts tracking tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "attempts tracking" || fail "attempts tracking"

# ─────────────────────────────────────────────────────────────────────────────
# 8. Artifact File Handling (GH-21)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Artifact File Handling ---${NC}"

# Create artifact files that look like tasks but aren't
cat > ".flow/tasks/${EPIC_ID}.1-evidence.json" << 'EOF'
{"commits":["abc123"],"tests":["npm test"],"prs":[]}
EOF
cat > ".flow/tasks/${EPIC_ID}.1-summary.md" << 'EOF'
Task completed successfully
EOF

# next should still work (not crash on artifact files)
set +e
NEXT_OUT="$(flowctl next --json 2>&1)"
NEXT_RC=$?
set -e
[[ $NEXT_RC -eq 0 ]] && pass "next ignores artifact files" || fail "next with artifact files (rc=$NEXT_RC)"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
