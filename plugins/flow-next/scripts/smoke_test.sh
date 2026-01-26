#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

TEST_DIR="/tmp/flowctl-smoke-$$"
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

echo -e "${YELLOW}=== flowctl smoke tests ===${NC}"

mkdir -p "$TEST_DIR/repo/scripts"
cd "$TEST_DIR/repo"
git init -q

cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl" scripts/flowctl
chmod +x scripts/flowctl

scripts/flowctl init --json >/dev/null
printf '{"commits":[],"tests":[],"prs":[]}' > "$TEST_DIR/evidence.json"
printf "ok\n" > "$TEST_DIR/summary.md"

echo -e "${YELLOW}--- idempotent init ---${NC}"

# Test 1: Re-run init (no changes)
init_result="$(scripts/flowctl init --json)"
init_actions="$(echo "$init_result" | "$PYTHON_BIN" -c 'import json,sys; print(len(json.load(sys.stdin).get("actions", [])))')"
if [[ "$init_actions" == "0" ]]; then
  echo -e "${GREEN}✓${NC} init idempotent (no changes on re-run)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init idempotent: expected 0 actions, got $init_actions"
  FAIL=$((FAIL + 1))
fi

# Test 2: Config upgrade (old config without planSync)
echo '{"memory":{"enabled":true}}' > .flow/config.json
init_upgrade="$(scripts/flowctl init --json)"
upgrade_msg="$(echo "$init_upgrade" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("message", ""))')"
if [[ "$upgrade_msg" == *"upgraded config.json"* ]]; then
  echo -e "${GREEN}✓${NC} init upgrades config (adds missing keys)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init upgrade: expected 'upgraded config.json' in message, got: $upgrade_msg"
  FAIL=$((FAIL + 1))
fi

# Test 3: Verify existing values preserved after upgrade
memory_val="$(scripts/flowctl config get memory.enabled --json | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("value"))')"
if [[ "$memory_val" == "True" ]]; then
  echo -e "${GREEN}✓${NC} init preserves existing config values"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init preserve: expected memory.enabled=True, got $memory_val"
  FAIL=$((FAIL + 1))
fi

# Test 4: Verify new defaults added (memory + planSync now default to True)
plansync_val="$(scripts/flowctl config get planSync.enabled --json | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("value"))')"
if [[ "$plansync_val" == "True" ]]; then
  echo -e "${GREEN}✓${NC} init adds new default keys"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init defaults: expected planSync.enabled=True, got $plansync_val"
  FAIL=$((FAIL + 1))
fi

# Reset config for remaining tests
scripts/flowctl config set memory.enabled false --json >/dev/null

echo -e "${YELLOW}--- next: plan/work/none + priority ---${NC}"
# Capture epic ID from create output (fn-N-xxx format)
EPIC1_JSON="$(scripts/flowctl epic create --title "Epic One" --json)"
EPIC1="$(echo "$EPIC1_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --epic "$EPIC1" --title "Low pri" --priority 5 --json >/dev/null
scripts/flowctl task create --epic "$EPIC1" --title "High pri" --priority 1 --json >/dev/null

plan_json="$(scripts/flowctl next --require-plan-review --json)"
"$PYTHON_BIN" - "$plan_json" "$EPIC1" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
expected_epic = sys.argv[2]
assert data["status"] == "plan"
assert data["epic"] == expected_epic, f"Expected {expected_epic}, got {data['epic']}"
PY
echo -e "${GREEN}✓${NC} next plan"
PASS=$((PASS + 1))

scripts/flowctl epic set-plan-review-status "$EPIC1" --status ship --json >/dev/null
work_json="$(scripts/flowctl next --json)"
"$PYTHON_BIN" - "$work_json" "$EPIC1" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
expected_epic = sys.argv[2]
assert data["status"] == "work"
assert data["task"] == f"{expected_epic}.2", f"Expected {expected_epic}.2, got {data['task']}"
PY
echo -e "${GREEN}✓${NC} next work priority"
PASS=$((PASS + 1))

scripts/flowctl start "${EPIC1}.2" --json >/dev/null
scripts/flowctl done "${EPIC1}.2" --summary-file "$TEST_DIR/summary.md" --evidence-json "$TEST_DIR/evidence.json" --json >/dev/null
scripts/flowctl start "${EPIC1}.1" --json >/dev/null
scripts/flowctl done "${EPIC1}.1" --summary-file "$TEST_DIR/summary.md" --evidence-json "$TEST_DIR/evidence.json" --json >/dev/null
none_json="$(scripts/flowctl next --json)"
"$PYTHON_BIN" - <<'PY' "$none_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["status"] == "none"
PY
echo -e "${GREEN}✓${NC} next none"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- artifact files in tasks dir (GH-21) ---${NC}"
# Create artifact files that match glob but aren't valid task files
# This simulates Claude writing evidence/summary files to .flow/tasks/
cat > ".flow/tasks/${EPIC1}.1-evidence.json" << 'EOF'
{"commits":["abc123"],"tests":["npm test"],"prs":[]}
EOF
cat > ".flow/tasks/${EPIC1}.1-summary.json" << 'EOF'
{"summary":"Task completed successfully"}
EOF
# Test that next still works with artifact files present
set +e
next_result="$(scripts/flowctl next --json 2>&1)"
next_rc=$?
set -e
if [[ "$next_rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} next ignores artifact files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} next crashes on artifact files: $next_result"
  FAIL=$((FAIL + 1))
fi
# Test that list still works
set +e
list_result="$(scripts/flowctl list --json 2>&1)"
list_rc=$?
set -e
if [[ "$list_rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} list ignores artifact files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} list crashes on artifact files: $list_result"
  FAIL=$((FAIL + 1))
fi
# Test that ready still works
set +e
ready_result="$(scripts/flowctl ready --epic "$EPIC1" --json 2>&1)"
ready_rc=$?
set -e
if [[ "$ready_rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} ready ignores artifact files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} ready crashes on artifact files: $ready_result"
  FAIL=$((FAIL + 1))
fi
# Test that show (with tasks) still works
set +e
show_result="$(scripts/flowctl show "$EPIC1" --json 2>&1)"
show_rc=$?
set -e
if [[ "$show_rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} show ignores artifact files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} show crashes on artifact files: $show_result"
  FAIL=$((FAIL + 1))
fi
# Test that validate still works
set +e
validate_result="$(scripts/flowctl validate --epic "$EPIC1" --json 2>&1)"
validate_rc=$?
set -e
if [[ "$validate_rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} validate ignores artifact files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} validate crashes on artifact files: $validate_result"
  FAIL=$((FAIL + 1))
fi
# Cleanup artifact files
rm -f ".flow/tasks/${EPIC1}.1-evidence.json" ".flow/tasks/${EPIC1}.1-summary.json"

echo -e "${YELLOW}--- plan_review_status default ---${NC}"
"$PYTHON_BIN" - "$EPIC1" <<'PY'
import json, sys
from pathlib import Path
epic_id = sys.argv[1]
path = Path(f".flow/epics/{epic_id}.json")
data = json.loads(path.read_text())
data.pop("plan_review_status", None)
data.pop("plan_reviewed_at", None)
data.pop("branch_name", None)
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
show_json="$(scripts/flowctl show "$EPIC1" --json)"
"$PYTHON_BIN" - <<'PY' "$show_json"
import json, sys
data = json.loads(sys.argv[1])
assert data.get("plan_review_status") == "unknown"
assert data.get("plan_reviewed_at") is None
assert data.get("branch_name") is None
PY
echo -e "${GREEN}✓${NC} plan_review_status defaulted"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- branch_name set ---${NC}"
scripts/flowctl epic set-branch "$EPIC1" --branch "${EPIC1}-epic" --json >/dev/null
show_json="$(scripts/flowctl show "$EPIC1" --json)"
"$PYTHON_BIN" - "$show_json" "$EPIC1" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
expected_branch = f"{sys.argv[2]}-epic"
assert data.get("branch_name") == expected_branch, f"Expected {expected_branch}, got {data.get('branch_name')}"
PY
echo -e "${GREEN}✓${NC} branch_name set"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- block + validate + epic close ---${NC}"
EPIC2_JSON="$(scripts/flowctl epic create --title "Epic Two" --json)"
EPIC2="$(echo "$EPIC2_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --epic "$EPIC2" --title "Block me" --json >/dev/null
scripts/flowctl task create --epic "$EPIC2" --title "Other" --json >/dev/null
printf "Blocked by test\n" > "$TEST_DIR/reason.md"
scripts/flowctl block "${EPIC2}.1" --reason-file "$TEST_DIR/reason.md" --json >/dev/null
scripts/flowctl validate --epic "$EPIC2" --json >/dev/null
echo -e "${GREEN}✓${NC} validate allows blocked"
PASS=$((PASS + 1))

set +e
scripts/flowctl epic close "$EPIC2" --json >/dev/null
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then
  echo -e "${GREEN}✓${NC} epic close fails when blocked"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} epic close fails when blocked"
  FAIL=$((FAIL + 1))
fi

scripts/flowctl start "${EPIC2}.1" --force --json >/dev/null
scripts/flowctl done "${EPIC2}.1" --summary-file "$TEST_DIR/summary.md" --evidence-json "$TEST_DIR/evidence.json" --json >/dev/null
scripts/flowctl start "${EPIC2}.2" --json >/dev/null
scripts/flowctl done "${EPIC2}.2" --summary-file "$TEST_DIR/summary.md" --evidence-json "$TEST_DIR/evidence.json" --json >/dev/null
scripts/flowctl epic close "$EPIC2" --json >/dev/null
echo -e "${GREEN}✓${NC} epic close succeeds when done"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- config set/get ---${NC}"
scripts/flowctl config set memory.enabled true --json >/dev/null
config_json="$(scripts/flowctl config get memory.enabled --json)"
"$PYTHON_BIN" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] == True, f"Expected True, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} config set/get"
PASS=$((PASS + 1))

scripts/flowctl config set memory.enabled false --json >/dev/null
config_json="$(scripts/flowctl config get memory.enabled --json)"
"$PYTHON_BIN" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] == False, f"Expected False, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} config toggle"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- planSync config ---${NC}"
scripts/flowctl config set planSync.enabled true --json >/dev/null
config_json="$(scripts/flowctl config get planSync.enabled --json)"
"$PYTHON_BIN" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] is True, f"Expected True, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} planSync config set/get"
PASS=$((PASS + 1))

scripts/flowctl config set planSync.enabled false --json >/dev/null
config_json="$(scripts/flowctl config get planSync.enabled --json)"
"$PYTHON_BIN" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] is False, f"Expected False, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} planSync config toggle"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- memory commands ---${NC}"
scripts/flowctl config set memory.enabled true --json >/dev/null
scripts/flowctl memory init --json >/dev/null
if [[ -f ".flow/memory/pitfalls.md" ]]; then
  echo -e "${GREEN}✓${NC} memory init creates files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory init creates files"
  FAIL=$((FAIL + 1))
fi

scripts/flowctl memory add --type pitfall "Test pitfall entry" --json >/dev/null
if grep -q "Test pitfall entry" .flow/memory/pitfalls.md; then
  echo -e "${GREEN}✓${NC} memory add pitfall"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory add pitfall"
  FAIL=$((FAIL + 1))
fi

scripts/flowctl memory add --type convention "Test convention" --json >/dev/null
scripts/flowctl memory add --type decision "Test decision" --json >/dev/null
list_json="$(scripts/flowctl memory list --json)"
"$PYTHON_BIN" - <<'PY' "$list_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] == True
counts = data["counts"]
assert counts["pitfalls.md"] >= 1
assert counts["conventions.md"] >= 1
assert counts["decisions.md"] >= 1
assert data["total"] >= 3
PY
echo -e "${GREEN}✓${NC} memory list"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- schema v1 validate ---${NC}"
"$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
path = Path(".flow/meta.json")
data = json.loads(path.read_text())
data["schema_version"] = 1
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
scripts/flowctl validate --all --json >/dev/null
echo -e "${GREEN}✓${NC} schema v1 validate"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- codex commands ---${NC}"
# Test codex check (may or may not have codex installed)
codex_check_json="$(scripts/flowctl codex check --json 2>/dev/null || echo '{"success":true}')"
"$PYTHON_BIN" - <<'PY' "$codex_check_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] == True, f"codex check failed: {data}"
# available can be true or false depending on codex install
PY
echo -e "${GREEN}✓${NC} codex check"
PASS=$((PASS + 1))

# Test codex impl-review help (no codex required for argparse check)
set +e
scripts/flowctl codex impl-review --help >/dev/null 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} codex impl-review --help"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} codex impl-review --help"
  FAIL=$((FAIL + 1))
fi

# Test codex plan-review help
set +e
scripts/flowctl codex plan-review --help >/dev/null 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} codex plan-review --help"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} codex plan-review --help"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- context hints ---${NC}"
# Create files in same commit, then modify one to test context hints
mkdir -p "$TEST_DIR/repo/src"
# First commit: both auth.py and handler.py together
cat > "$TEST_DIR/repo/src/auth.py" << 'EOF'
def validate_token(token: str) -> bool:
    """Validate JWT token."""
    return len(token) > 10

class User:
    def __init__(self, name: str):
        self.name = name
EOF
cat > "$TEST_DIR/repo/src/handler.py" << 'EOF'
from auth import validate_token, User

def handle_request(token: str):
    if validate_token(token):
        return User("test")
    return None
EOF
git -C "$TEST_DIR/repo" add src/
git -C "$TEST_DIR/repo" commit -m "Add auth and handler" >/dev/null

# Second commit: only modify auth.py (handler.py stays unchanged)
cat > "$TEST_DIR/repo/src/auth.py" << 'EOF'
def validate_token(token: str) -> bool:
    """Validate JWT token with expiry check."""
    if len(token) < 10:
        return False
    return True

class User:
    def __init__(self, name: str, email: str = ""):
        self.name = name
        self.email = email
EOF
git -C "$TEST_DIR/repo" add src/auth.py
git -C "$TEST_DIR/repo" commit -m "Update auth with expiry" >/dev/null

# Test context hints: should find handler.py referencing validate_token/User
cd "$TEST_DIR/repo"
hints_output="$(PYTHONPATH="$SCRIPT_DIR" "$PYTHON_BIN" -c "
from flowctl import gather_context_hints
hints = gather_context_hints('HEAD~1')
print(hints)
" 2>&1)"

# Verify hints mention handler.py referencing validate_token or User
if echo "$hints_output" | grep -q "handler.py"; then
  echo -e "${GREEN}✓${NC} context hints finds references"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} context hints finds references (got: $hints_output)"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- build_review_prompt ---${NC}"
# Go back to plugin root for Python tests
cd "$TEST_DIR/repo"
# Test that build_review_prompt generates proper structure
"$PYTHON_BIN" - "$SCRIPT_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from flowctl import build_review_prompt

# Test impl prompt has all 7 criteria
impl_prompt = build_review_prompt("impl", "Test spec", "Test hints", "Test diff")
assert "<review_instructions>" in impl_prompt
assert "Correctness" in impl_prompt
assert "Simplicity" in impl_prompt
assert "DRY" in impl_prompt
assert "Architecture" in impl_prompt
assert "Edge Cases" in impl_prompt
assert "Tests" in impl_prompt
assert "Security" in impl_prompt
assert "<verdict>SHIP</verdict>" in impl_prompt
assert "File:Line" in impl_prompt  # Structured output format

# Test plan prompt has all 7 criteria
plan_prompt = build_review_prompt("plan", "Test spec", "Test hints")
assert "Completeness" in plan_prompt
assert "Feasibility" in plan_prompt
assert "Clarity" in plan_prompt
assert "Architecture" in plan_prompt
assert "Risks" in plan_prompt
assert "Scope" in plan_prompt
assert "Testability" in plan_prompt
assert "<verdict>SHIP</verdict>" in plan_prompt

# Test context hints and diff are included
assert "<context_hints>" in impl_prompt
assert "Test hints" in impl_prompt
assert "<diff_summary>" in impl_prompt
assert "Test diff" in impl_prompt
assert "<spec>" in impl_prompt
assert "Test spec" in impl_prompt
PY
echo -e "${GREEN}✓${NC} build_review_prompt has full criteria"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- parse_receipt_path ---${NC}"
# Test receipt path parsing for Ralph gating (both legacy and new fn-N-xxx formats)
"$PYTHON_BIN" - "$SCRIPT_DIR/hooks" <<'PY'
import sys
hooks_dir = sys.argv[1]
sys.path.insert(0, hooks_dir)
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location("ralph_guard", f"{hooks_dir}/ralph-guard.py")
guard = module_from_spec(spec)
spec.loader.exec_module(guard)

# Test plan receipt parsing (legacy format)
rtype, rid = guard.parse_receipt_path("/tmp/receipts/plan-fn-1.json")
assert rtype == "plan_review", f"Expected plan_review, got {rtype}"
assert rid == "fn-1", f"Expected fn-1, got {rid}"

# Test impl receipt parsing (legacy format)
rtype, rid = guard.parse_receipt_path("/tmp/receipts/impl-fn-1.3.json")
assert rtype == "impl_review", f"Expected impl_review, got {rtype}"
assert rid == "fn-1.3", f"Expected fn-1.3, got {rid}"

# Test plan receipt parsing (new fn-N-xxx format)
rtype, rid = guard.parse_receipt_path("/tmp/receipts/plan-fn-5-x7k.json")
assert rtype == "plan_review", f"Expected plan_review, got {rtype}"
assert rid == "fn-5-x7k", f"Expected fn-5-x7k, got {rid}"

# Test impl receipt parsing (new fn-N-xxx format)
rtype, rid = guard.parse_receipt_path("/tmp/receipts/impl-fn-5-x7k.3.json")
assert rtype == "impl_review", f"Expected impl_review, got {rtype}"
assert rid == "fn-5-x7k.3", f"Expected fn-5-x7k.3, got {rid}"

# Test fallback
rtype, rid = guard.parse_receipt_path("/tmp/unknown.json")
assert rtype == "impl_review"
assert rid == "UNKNOWN"
PY
echo -e "${GREEN}✓${NC} parse_receipt_path works"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- codex e2e (requires codex CLI) ---${NC}"
# Check if codex is available (handles its own auth)
codex_available="$(scripts/flowctl codex check --json 2>/dev/null | "$PYTHON_BIN" -c "import sys,json; print(json.load(sys.stdin).get('available', False))" 2>/dev/null || echo "False")"
if [[ "$codex_available" == "True" ]]; then
  # Create a simple epic + task for testing
  EPIC3_JSON="$(scripts/flowctl epic create --title "Codex test epic" --json)"
  EPIC3="$(echo "$EPIC3_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --epic "$EPIC3" --title "Test task" --json >/dev/null

  # Write a simple spec
  cat > ".flow/specs/${EPIC3}.md" << 'EOF'
# Codex Test Epic

Simple test epic for smoke testing codex reviews.

## Scope
- Test that codex can review a plan
- Test that codex can review an implementation
EOF

  cat > ".flow/tasks/${EPIC3}.1.md" << 'EOF'
# Test Task

Add a simple hello world function.

## Acceptance
- Function returns "hello world"
EOF

  # Test plan-review e2e
  # Create a simple code file inside the repo for the plan to reference
  mkdir -p src
  echo 'def hello(): return "hello world"' > src/hello.py
  set +e
  plan_result="$(scripts/flowctl codex plan-review "$EPIC3" --files "src/hello.py" --base main --receipt "$TEST_DIR/plan-receipt.json" --json 2>&1)"
  plan_rc=$?
  set -e

  if [[ "$plan_rc" -eq 0 ]]; then
    # Verify receipt was written with correct schema
    if [[ -f "$TEST_DIR/plan-receipt.json" ]]; then
      "$PYTHON_BIN" - "$TEST_DIR/plan-receipt.json" "$EPIC3" <<'PY'
import sys, json
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
expected_id = sys.argv[2]
assert data.get("type") == "plan_review", f"Expected type=plan_review, got {data.get('type')}"
assert data.get("id") == expected_id, f"Expected id={expected_id}, got {data.get('id')}"
assert data.get("mode") == "codex", f"Expected mode=codex, got {data.get('mode')}"
assert "verdict" in data, "Missing verdict in receipt"
assert "session_id" in data, "Missing session_id in receipt"
PY
      echo -e "${GREEN}✓${NC} codex plan-review e2e"
      PASS=$((PASS + 1))
    else
      echo -e "${RED}✗${NC} codex plan-review e2e (no receipt)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo -e "${RED}✗${NC} codex plan-review e2e (exit $plan_rc)"
    FAIL=$((FAIL + 1))
  fi

  # Test impl-review e2e (create a simple change first)
  cat > "$TEST_DIR/repo/src/hello.py" << 'EOF'
def hello():
    return "hello world"
EOF
  git -C "$TEST_DIR/repo" add src/hello.py
  git -C "$TEST_DIR/repo" commit -m "Add hello function" >/dev/null

  set +e
  impl_result="$(scripts/flowctl codex impl-review "${EPIC3}.1" --base HEAD~1 --receipt "$TEST_DIR/impl-receipt.json" --json 2>&1)"
  impl_rc=$?
  set -e

  if [[ "$impl_rc" -eq 0 ]]; then
    # Verify receipt was written with correct schema
    if [[ -f "$TEST_DIR/impl-receipt.json" ]]; then
      "$PYTHON_BIN" - "$TEST_DIR/impl-receipt.json" "$EPIC3" <<'PY'
import sys, json
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
expected_id = f"{sys.argv[2]}.1"
assert data.get("type") == "impl_review", f"Expected type=impl_review, got {data.get('type')}"
assert data.get("id") == expected_id, f"Expected id={expected_id}, got {data.get('id')}"
assert data.get("mode") == "codex", f"Expected mode=codex, got {data.get('mode')}"
assert "verdict" in data, "Missing verdict in receipt"
assert "session_id" in data, "Missing session_id in receipt"
PY
      echo -e "${GREEN}✓${NC} codex impl-review e2e"
      PASS=$((PASS + 1))
    else
      echo -e "${RED}✗${NC} codex impl-review e2e (no receipt)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo -e "${RED}✗${NC} codex impl-review e2e (exit $impl_rc)"
    FAIL=$((FAIL + 1))
  fi
else
  echo -e "${YELLOW}⊘${NC} codex e2e skipped (codex not available)"
fi

echo -e "${YELLOW}--- depends_on_epics gate ---${NC}"
cd "$TEST_DIR/repo"  # Back to test repo
# Create epics and capture their IDs
DEP_BASE_JSON="$(scripts/flowctl epic create --title "Dep base" --json)"
DEP_BASE_ID="$(echo "$DEP_BASE_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --epic "$DEP_BASE_ID" --title "Base task" --json >/dev/null
DEP_CHILD_JSON="$(scripts/flowctl epic create --title "Dep child" --json)"
DEP_CHILD_ID="$(echo "$DEP_CHILD_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
"$PYTHON_BIN" - "$DEP_CHILD_ID" "$DEP_BASE_ID" <<'PY'
import json, sys
from pathlib import Path
child_id, base_id = sys.argv[1], sys.argv[2]
path = Path(f".flow/epics/{child_id}.json")
data = json.loads(path.read_text())
data["depends_on_epics"] = [base_id]
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
printf '{"epics":["%s"]}\n' "$DEP_CHILD_ID" > "$TEST_DIR/epics.json"
blocked_json="$(scripts/flowctl next --epics-file "$TEST_DIR/epics.json" --json)"
"$PYTHON_BIN" - "$DEP_CHILD_ID" "$blocked_json" <<'PY'
import json, sys
child_id = sys.argv[1]
data = json.loads(sys.argv[2])
assert data["status"] == "none"
assert data["reason"] == "blocked_by_epic_deps"
assert child_id in data.get("blocked_epics", {})
PY
echo -e "${GREEN}✓${NC} depends_on_epics blocks"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- stdin support ---${NC}"
cd "$TEST_DIR/repo"
STDIN_EPIC_JSON="$(scripts/flowctl epic create --title "Stdin test" --json)"
STDIN_EPIC="$(echo "$STDIN_EPIC_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
# Test epic set-plan with stdin
scripts/flowctl epic set-plan "$STDIN_EPIC" --file - --json <<'EOF'
# Stdin Test Plan

## Overview
Testing stdin support for set-plan.

## Acceptance
- Works via stdin
EOF
# Verify content was written
spec_content="$(scripts/flowctl cat "$STDIN_EPIC")"
echo "$spec_content" | grep -q "Testing stdin support" || { echo "stdin set-plan failed"; FAIL=$((FAIL + 1)); }
echo -e "${GREEN}✓${NC} stdin epic set-plan"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- task set-spec combined ---${NC}"
scripts/flowctl task create --epic "$STDIN_EPIC" --title "Set-spec test" --json >/dev/null
SETSPEC_TASK="${STDIN_EPIC}.1"
# Write temp files for combined set-spec
echo 'This is the description.' > "$TEST_DIR/desc.md"
echo '- [ ] Check 1
- [ ] Check 2' > "$TEST_DIR/acc.md"
scripts/flowctl task set-spec "$SETSPEC_TASK" --description "$TEST_DIR/desc.md" --acceptance "$TEST_DIR/acc.md" --json >/dev/null
# Verify both sections were written
task_spec="$(scripts/flowctl cat "$SETSPEC_TASK")"
echo "$task_spec" | grep -q "This is the description" || { echo "set-spec description failed"; FAIL=$((FAIL + 1)); }
echo "$task_spec" | grep -q "Check 1" || { echo "set-spec acceptance failed"; FAIL=$((FAIL + 1)); }
echo -e "${GREEN}✓${NC} task set-spec combined"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- task set-spec --file (full replacement) ---${NC}"
scripts/flowctl task create --epic "$STDIN_EPIC" --title "Full replacement test" --json >/dev/null
FULLREPLACE_TASK="${STDIN_EPIC}.2"
# Write complete spec file
cat > "$TEST_DIR/full_spec.md" << 'FULLSPEC'
# Task: Full replacement test

## Description

This is a completely new spec that replaces everything.

## Acceptance

- [ ] Verify full replacement works
- [ ] Original content is gone
FULLSPEC
scripts/flowctl task set-spec "$FULLREPLACE_TASK" --file "$TEST_DIR/full_spec.md" --json >/dev/null
# Verify full replacement
full_spec="$(scripts/flowctl cat "$FULLREPLACE_TASK")"
echo "$full_spec" | grep -q "completely new spec that replaces everything" || { echo "set-spec --file content failed"; FAIL=$((FAIL + 1)); }
echo "$full_spec" | grep -q "Verify full replacement works" || { echo "set-spec --file acceptance failed"; FAIL=$((FAIL + 1)); }
echo -e "${GREEN}✓${NC} task set-spec --file"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- task set-spec --file stdin ---${NC}"
scripts/flowctl task create --epic "$STDIN_EPIC" --title "Stdin replacement test" --json >/dev/null
STDIN_REPLACE_TASK="${STDIN_EPIC}.3"
# Full replacement via stdin
scripts/flowctl task set-spec "$STDIN_REPLACE_TASK" --file - --json <<'EOF'
# Task: Stdin replacement test

## Description

This spec was written via stdin.

## Acceptance

- [ ] Stdin replacement works
EOF
# Verify stdin replacement
stdin_spec="$(scripts/flowctl cat "$STDIN_REPLACE_TASK")"
echo "$stdin_spec" | grep -q "spec was written via stdin" || { echo "set-spec --file stdin failed"; FAIL=$((FAIL + 1)); }
echo -e "${GREEN}✓${NC} task set-spec --file stdin"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- checkpoint save/restore ---${NC}"
# Save checkpoint
scripts/flowctl checkpoint save --epic "$STDIN_EPIC" --json >/dev/null
# Verify checkpoint file exists
[[ -f ".flow/.checkpoint-${STDIN_EPIC}.json" ]] || { echo "checkpoint file not created"; FAIL=$((FAIL + 1)); }
# Modify epic spec
scripts/flowctl epic set-plan "$STDIN_EPIC" --file - --json <<'EOF'
# Modified content
EOF
# Restore from checkpoint
scripts/flowctl checkpoint restore --epic "$STDIN_EPIC" --json >/dev/null
# Verify original content restored
restored_spec="$(scripts/flowctl cat "$STDIN_EPIC")"
echo "$restored_spec" | grep -q "Testing stdin support" || { echo "checkpoint restore failed"; FAIL=$((FAIL + 1)); }
# Delete checkpoint
scripts/flowctl checkpoint delete --epic "$STDIN_EPIC" --json >/dev/null
[[ ! -f ".flow/.checkpoint-${STDIN_EPIC}.json" ]] || { echo "checkpoint delete failed"; FAIL=$((FAIL + 1)); }
echo -e "${GREEN}✓${NC} checkpoint save/restore/delete"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- sync command files ---${NC}"
# Test 1: Command stub exists
if [[ -f "$PLUGIN_ROOT/commands/flow-next/sync.md" ]]; then
  echo -e "${GREEN}✓${NC} sync command stub exists"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync command stub missing"
  FAIL=$((FAIL + 1))
fi

# Test 2: Skill file exists
if [[ -f "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md" ]]; then
  echo -e "${GREEN}✓${NC} sync skill exists"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill missing"
  FAIL=$((FAIL + 1))
fi

# Test 3: Command invokes skill
if grep -q "flow-next-sync" "$PLUGIN_ROOT/commands/flow-next/sync.md"; then
  echo -e "${GREEN}✓${NC} sync command invokes skill"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync command doesn't reference skill"
  FAIL=$((FAIL + 1))
fi

# Test 4: Skill has correct frontmatter
if grep -q "name: flow-next-sync" "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md"; then
  echo -e "${GREEN}✓${NC} sync skill has correct name"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill missing name frontmatter"
  FAIL=$((FAIL + 1))
fi

# Test 5: Skill mentions plan-sync agent
if grep -q "plan-sync" "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md"; then
  echo -e "${GREEN}✓${NC} sync skill references plan-sync agent"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill doesn't reference plan-sync agent"
  FAIL=$((FAIL + 1))
fi

# Test 6: Skill supports dry-run
if grep -qi "dry.run\|dry-run\|DRY_RUN" "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md"; then
  echo -e "${GREEN}✓${NC} sync skill supports dry-run"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill missing dry-run support"
  FAIL=$((FAIL + 1))
fi

echo ""
echo -e "${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
echo -e "\n${GREEN}All tests passed!${NC}"
