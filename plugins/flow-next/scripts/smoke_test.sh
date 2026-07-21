#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Convert Git Bash style /d/a/... to Windows-friendly D:/a/... so paths
# interpolated into native-Windows Python (sys.path / argv / file_path
# comparisons) resolve. `cygpath -m` produces forward-slash Windows paths
# that Python accepts and that match Python's pathlib output.
# No-op on Linux/macOS where cygpath is absent.
to_winpath() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1"
  else
    printf '%s' "$1"
  fi
}
SCRIPT_DIR="$(to_winpath "$SCRIPT_DIR")"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_ROOT="$(to_winpath "$PLUGIN_ROOT")"

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

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/flowctl-smoke-$$}"
# Normalize Windows backslashes from $RUNNER_TEMP to forward slashes
# so paths interpolated into `python -c "..."` source code are not
# corrupted by Python escape parsing (e.g. `D:\a\_temp` → `D:<bell>...`).
# Windows accepts forward-slash paths natively; no-op on Linux/macOS.
TEST_DIR="${TEST_DIR//\\//}"
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

# fn-43.14: probe both canonical .flow/specs/<id>.json and legacy .flow/epics/<id>.json
# so assertions work on fresh post-1.0 repos AND on alias-mode 0.x repos that still
# write JSON sidecars to .flow/epics/. Mirrors the Python `find_spec_json_path` helper.
spec_json_path() {
  local id="$1"
  if [[ -f ".flow/specs/${id}.json" ]]; then
    printf '%s' ".flow/specs/${id}.json"
  elif [[ -f ".flow/epics/${id}.json" ]]; then
    printf '%s' ".flow/epics/${id}.json"
  else
    # Caller should fail loudly; return canonical path so the error message
    # surfaces the expected location.
    printf '%s' ".flow/specs/${id}.json"
  fi
}

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
init_actions="$(echo "$init_result" | "${FLOW_PY[@]}" -c 'import json,sys; print(len(json.load(sys.stdin).get("actions", [])))')"
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
upgrade_msg="$(echo "$init_upgrade" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin).get("message", ""))')"
if [[ "$upgrade_msg" == *"upgraded config.json"* ]]; then
  echo -e "${GREEN}✓${NC} init upgrades config (adds missing keys)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init upgrade: expected 'upgraded config.json' in message, got: $upgrade_msg"
  FAIL=$((FAIL + 1))
fi

# Test 3: Verify existing values preserved after upgrade
memory_val="$(scripts/flowctl config get memory.enabled --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin).get("value"))')"
if [[ "$memory_val" == "True" ]]; then
  echo -e "${GREEN}✓${NC} init preserves existing config values"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init preserve: expected memory.enabled=True, got $memory_val"
  FAIL=$((FAIL + 1))
fi

# Test 4: Verify new defaults added (memory + planSync now default to True)
plansync_val="$(scripts/flowctl config get planSync.enabled --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin).get("value"))')"
if [[ "$plansync_val" == "True" ]]; then
  echo -e "${GREEN}✓${NC} init adds new default keys"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init defaults: expected planSync.enabled=True, got $plansync_val"
  FAIL=$((FAIL + 1))
fi

# fn-77.3 (+ fn-77 impl-review): init self-heals .flow/bin launchers (re-stamps
# bash + .cmd) — but ONLY when the launcher target .flow/bin/flowctl.py is
# already present. A bare/fresh init must NOT leave orphan launchers.
echo -e "${YELLOW}--- init self-heals .flow/bin launchers (fn-77.3) ---${NC}"

# Fresh init above had no .flow/bin/flowctl.py target → no launchers stamped.
if [[ ! -f .flow/bin/flowctl && ! -f .flow/bin/flowctl.cmd ]]; then
  echo -e "${GREEN}✓${NC} fresh init leaves no orphan launchers (no flowctl.py target)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} fresh init wrongly stamped .flow/bin launchers without a target"
  FAIL=$((FAIL + 1))
fi

# Simulate an existing install: seed the launcher target, then a pre-fix broken
# `exec python3` launcher + missing .cmd. init self-heals both.
mkdir -p .flow/bin
cp scripts/flowctl.py .flow/bin/flowctl.py
printf '#!/bin/bash\nexec python3 "$(dirname "${BASH_SOURCE[0]}")/flowctl.py" "$@"\n' > .flow/bin/flowctl
rm -f .flow/bin/flowctl.cmd
scripts/flowctl init --json >/dev/null
if diff -q .flow/bin/flowctl "$PLUGIN_ROOT/scripts/flowctl" >/dev/null \
   && [[ -f .flow/bin/flowctl.cmd ]] \
   && diff -q .flow/bin/flowctl.cmd "$PLUGIN_ROOT/scripts/flowctl.cmd" >/dev/null; then
  echo -e "${GREEN}✓${NC} init self-heals old exec-python3 launcher + re-adds flowctl.cmd"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init did not self-heal a broken .flow/bin launcher"
  FAIL=$((FAIL + 1))
fi

# Idempotent: a second init makes no .flow/bin change (no tracked-file churn).
heal_bin_actions="$(scripts/flowctl init --json | "${FLOW_PY[@]}" -c 'import json,sys; print([a for a in json.load(sys.stdin).get("actions",[]) if "bin/" in a])')"
if [[ "$heal_bin_actions" == "[]" ]]; then
  echo -e "${GREEN}✓${NC} init .flow/bin stamping idempotent (no churn on re-run)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} init .flow/bin not idempotent, got: $heal_bin_actions"
  FAIL=$((FAIL + 1))
fi

# Reset config for remaining tests
scripts/flowctl config set memory.enabled false --json >/dev/null

echo -e "${YELLOW}--- next: plan/work/none + priority ---${NC}"
# Capture epic ID from create output (fn-N-xxx format)
EPIC1_JSON="$(scripts/flowctl spec create --title "Epic One" --json)"
EPIC1="$(echo "$EPIC1_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --spec "$EPIC1" --title "Low pri" --priority 5 --json >/dev/null
scripts/flowctl task create --spec "$EPIC1" --title "High pri" --priority 1 --json >/dev/null

plan_json="$(scripts/flowctl next --require-plan-review --json)"
"${FLOW_PY[@]}" - "$plan_json" "$EPIC1" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
expected_epic = sys.argv[2]
assert data["status"] == "plan"
assert data["spec"] == expected_epic, f"Expected {expected_epic}, got {data['spec']}"
PY
echo -e "${GREEN}✓${NC} next plan"
PASS=$((PASS + 1))

scripts/flowctl spec set-plan-review-status "$EPIC1" --status ship --json >/dev/null
work_json="$(scripts/flowctl next --json)"
"${FLOW_PY[@]}" - "$work_json" "$EPIC1" <<'PY'
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
"${FLOW_PY[@]}" - <<'PY' "$none_json"
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
ready_result="$(scripts/flowctl ready --spec "$EPIC1" --json 2>&1)"
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
validate_result="$(scripts/flowctl validate --spec "$EPIC1" --json 2>&1)"
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
EPIC1_JSON_PATH="$(spec_json_path "$EPIC1")"
"${FLOW_PY[@]}" - "$EPIC1_JSON_PATH" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text())
data.pop("plan_review_status", None)
data.pop("plan_reviewed_at", None)
data.pop("branch_name", None)
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
show_json="$(scripts/flowctl show "$EPIC1" --json)"
"${FLOW_PY[@]}" - <<'PY' "$show_json"
import json, sys
data = json.loads(sys.argv[1])
assert data.get("plan_review_status") == "unknown"
assert data.get("plan_reviewed_at") is None
assert data.get("branch_name") is None
PY
echo -e "${GREEN}✓${NC} plan_review_status defaulted"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- branch_name set ---${NC}"
scripts/flowctl spec set-branch "$EPIC1" --branch "${EPIC1}-epic" --json >/dev/null
show_json="$(scripts/flowctl show "$EPIC1" --json)"
"${FLOW_PY[@]}" - "$show_json" "$EPIC1" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
expected_branch = f"{sys.argv[2]}-epic"
assert data.get("branch_name") == expected_branch, f"Expected {expected_branch}, got {data.get('branch_name')}"
PY
echo -e "${GREEN}✓${NC} branch_name set"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- epic set-title ---${NC}"
# Create epic with tasks for rename test
RENAME_EPIC_JSON="$(scripts/flowctl spec create --title "Old Title" --json)"
RENAME_EPIC="$(echo "$RENAME_EPIC_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --spec "$RENAME_EPIC" --title "First task" --json >/dev/null
scripts/flowctl task create --spec "$RENAME_EPIC" --title "Second task" --json >/dev/null
# Add task dependency within epic
scripts/flowctl dep add "${RENAME_EPIC}.2" "${RENAME_EPIC}.1" --json >/dev/null

# Rename epic
rename_result="$(scripts/flowctl spec set-title "$RENAME_EPIC" --title "New Shiny Title" --json)"
NEW_EPIC="$(echo "$rename_result" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["new_id"])')"

# Test 1: Verify old files are gone (probe both legacy + canonical paths)
if [[ ! -f ".flow/epics/${RENAME_EPIC}.json" ]] && [[ ! -f ".flow/specs/${RENAME_EPIC}.json" ]] && [[ ! -f ".flow/specs/${RENAME_EPIC}.md" ]]; then
  echo -e "${GREEN}✓${NC} set-title removes old files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-title old files still exist"
  FAIL=$((FAIL + 1))
fi

# Test 2: Verify new files exist (JSON in canonical or legacy; markdown in specs/)
NEW_EPIC_JSON_PATH="$(spec_json_path "$NEW_EPIC")"
if [[ -f "$NEW_EPIC_JSON_PATH" ]] && [[ -f ".flow/specs/${NEW_EPIC}.md" ]]; then
  echo -e "${GREEN}✓${NC} set-title creates new files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-title new files missing"
  FAIL=$((FAIL + 1))
fi

# Test 3: Verify epic JSON content updated
"${FLOW_PY[@]}" - "$NEW_EPIC" "$NEW_EPIC_JSON_PATH" <<'PY'
import json, sys
from pathlib import Path
new_id = sys.argv[1]
epic_data = json.loads(Path(sys.argv[2]).read_text())
assert epic_data["id"] == new_id, f"Epic ID not updated: {epic_data['id']}"
assert epic_data["title"] == "New Shiny Title", f"Title not updated: {epic_data['title']}"
assert new_id in epic_data["spec_path"], f"spec_path not updated: {epic_data['spec_path']}"
PY
echo -e "${GREEN}✓${NC} set-title updates epic JSON"
PASS=$((PASS + 1))

# Test 4: Verify task files renamed
if [[ -f ".flow/tasks/${NEW_EPIC}.1.json" ]] && [[ -f ".flow/tasks/${NEW_EPIC}.2.json" ]]; then
  echo -e "${GREEN}✓${NC} set-title renames task files"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-title task files not renamed"
  FAIL=$((FAIL + 1))
fi

# Test 5: Verify task JSON content updated (including depends_on).
# fn-43.2: persisted task JSON uses canonical "spec" key; legacy "epic"
# only present in 0.x files that haven't been rewritten. Accept either.
"${FLOW_PY[@]}" - "$NEW_EPIC" <<'PY'
import json, sys
from pathlib import Path
new_id = sys.argv[1]
task1_data = json.loads(Path(f".flow/tasks/{new_id}.1.json").read_text())
task2_data = json.loads(Path(f".flow/tasks/{new_id}.2.json").read_text())
assert task1_data["id"] == f"{new_id}.1", f"Task 1 ID not updated: {task1_data['id']}"
task1_spec = task1_data.get("spec") or task1_data.get("epic")
assert task1_spec == new_id, f"Task 1 spec not updated: {task1_spec}"
assert task2_data["id"] == f"{new_id}.2", f"Task 2 ID not updated: {task2_data['id']}"
# Verify depends_on was updated
deps = task2_data.get("depends_on", [])
assert f"{new_id}.1" in deps, f"depends_on not updated: {deps}"
PY
echo -e "${GREEN}✓${NC} set-title updates task JSON and deps"
PASS=$((PASS + 1))

# Test 6: Verify show works with new ID
show_json="$(scripts/flowctl show "$NEW_EPIC" --json)"
"${FLOW_PY[@]}" - "$show_json" "$NEW_EPIC" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
expected_id = sys.argv[2]
assert data["id"] == expected_id, f"Show returns wrong ID: {data['id']}"
assert data["title"] == "New Shiny Title"
PY
echo -e "${GREEN}✓${NC} set-title show works with new ID"
PASS=$((PASS + 1))

# Test 7: depends_on_epics update in other epics
DEP_EPIC_JSON="$(scripts/flowctl spec create --title "Depends on renamed" --json)"
DEP_EPIC="$(echo "$DEP_EPIC_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl spec add-dep "$DEP_EPIC" "$NEW_EPIC" --json >/dev/null
# Rename the dependency
rename2_result="$(scripts/flowctl spec set-title "$NEW_EPIC" --title "Final Title" --json)"
FINAL_EPIC="$(echo "$rename2_result" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["new_id"])')"
# Verify DEP_EPIC's depends_on_epics was updated. Use `flowctl show --json`
# instead of reading .flow/epics/<id>.json directly so the assertion works
# regardless of whether write went to legacy .flow/epics/ or canonical
# .flow/specs/ (the on-disk JSON key is still `depends_on_epics` through 1.x).
DEP_EPIC_SHOW="$(scripts/flowctl show "$DEP_EPIC" --json)"
"${FLOW_PY[@]}" - "$FINAL_EPIC" "$DEP_EPIC_SHOW" <<'PY'
import json, sys
final_epic = sys.argv[1]
data = json.loads(sys.argv[2])
deps = data.get("depends_on_epics", [])
assert final_epic in deps, f"depends_on_epics not updated: {deps}, expected {final_epic}"
PY
echo -e "${GREEN}✓${NC} set-title updates depends_on_epics in other epics"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- block + validate + epic close ---${NC}"
EPIC2_JSON="$(scripts/flowctl spec create --title "Epic Two" --json)"
EPIC2="$(echo "$EPIC2_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --spec "$EPIC2" --title "Block me" --json >/dev/null
scripts/flowctl task create --spec "$EPIC2" --title "Other" --json >/dev/null
printf "Blocked by test\n" > "$TEST_DIR/reason.md"
scripts/flowctl block "${EPIC2}.1" --reason-file "$TEST_DIR/reason.md" --json >/dev/null
scripts/flowctl validate --spec "$EPIC2" --json >/dev/null
echo -e "${GREEN}✓${NC} validate allows blocked"
PASS=$((PASS + 1))

set +e
scripts/flowctl spec close "$EPIC2" --json >/dev/null
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
scripts/flowctl spec close "$EPIC2" --json >/dev/null
echo -e "${GREEN}✓${NC} epic close succeeds when done"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- spec ready/unready + badge (fn-58.1) ---${NC}"
# Lazy on-disk: never-toggled spec carries no `ready` key; JSON reads false.
ready_spec_path() {
  if [[ -f ".flow/specs/${1}.json" ]]; then printf '.flow/specs/%s.json' "$1"
  else printf '.flow/epics/%s.json' "$1"
  fi
}
EPIC2_PATH="$(ready_spec_path "$EPIC2")"
show_json="$(scripts/flowctl show "$EPIC2" --json)"
"${FLOW_PY[@]}" - "$show_json" "$EPIC2_PATH" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
assert data["ready"] is False, f"Expected explicit false, got {data.get('ready')!r}"
sidecar = json.load(open(sys.argv[2]))
assert "ready" not in sidecar, "lazy purity violated: ready key on never-toggled spec"
PY
echo -e "${GREEN}✓${NC} lazy ready default (explicit false, no key on disk)"
PASS=$((PASS + 1))

# unready on a never-ready spec is a byte-identical no-op (no adoption churn).
before_bytes="$("${FLOW_PY[@]}" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$EPIC2_PATH")"
noop_json="$(scripts/flowctl spec unready "$EPIC2" --json)"
after_bytes="$("${FLOW_PY[@]}" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$EPIC2_PATH")"
"${FLOW_PY[@]}" - "$noop_json" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
assert data["changed"] is False, f"Expected no-op, got {data}"
PY
[[ "$before_bytes" == "$after_bytes" ]]
echo -e "${GREEN}✓${NC} unready on never-ready spec is byte-identical no-op"
PASS=$((PASS + 1))

# Toggle on a DONE spec (readiness is status-orthogonal) + badge appears.
scripts/flowctl spec ready "$EPIC2" --json >/dev/null
specs_human="$(scripts/flowctl specs)"
if ! echo "$specs_human" | grep -q "\[ready\] $EPIC2"; then
  echo "badge missing: $specs_human"; exit 1
fi
if echo "$specs_human" | grep -q "\[ready\] $EPIC1"; then
  echo "badge leaked to non-ready spec"; exit 1
fi
echo -e "${GREEN}✓${NC} ready works on done spec; badge only on ready specs"
PASS=$((PASS + 1))

scripts/flowctl spec unready "$EPIC2" --json >/dev/null
if scripts/flowctl specs | grep -q "\[ready\]"; then
  echo "badge survived unready"; exit 1
fi
echo -e "${GREEN}✓${NC} badge gone after unready"
PASS=$((PASS + 1))

# `.M` task ids rejected with a targeted error.
set +e
ready_err="$(scripts/flowctl spec ready "${EPIC2}.1" --json 2>&1)"
rc=$?
set -e
if [[ "$rc" -ne 0 ]] && echo "$ready_err" | grep -q "spec-level"; then
  echo -e "${GREEN}✓${NC} spec ready rejects task id"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} spec ready rejects task id (rc=$rc; $ready_err)"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- config set/get ---${NC}"
scripts/flowctl config set memory.enabled true --json >/dev/null
config_json="$(scripts/flowctl config get memory.enabled --json)"
"${FLOW_PY[@]}" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] == True, f"Expected True, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} config set/get"
PASS=$((PASS + 1))

scripts/flowctl config set memory.enabled false --json >/dev/null
config_json="$(scripts/flowctl config get memory.enabled --json)"
"${FLOW_PY[@]}" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] == False, f"Expected False, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} config toggle"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- planSync config ---${NC}"
scripts/flowctl config set planSync.enabled true --json >/dev/null
config_json="$(scripts/flowctl config get planSync.enabled --json)"
"${FLOW_PY[@]}" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] is True, f"Expected True, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} planSync config set/get"
PASS=$((PASS + 1))

scripts/flowctl config set planSync.enabled false --json >/dev/null
config_json="$(scripts/flowctl config get planSync.enabled --json)"
"${FLOW_PY[@]}" - <<'PY' "$config_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["value"] is False, f"Expected False, got {data['value']}"
PY
echo -e "${GREEN}✓${NC} planSync config toggle"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- memory commands ---${NC}"
scripts/flowctl config set memory.enabled true --json >/dev/null
scripts/flowctl memory init --json >/dev/null
# fn-30 task 1: init creates categorized tree + README, not legacy flat files.
if [[ -f ".flow/memory/README.md" && -d ".flow/memory/bug/build-errors" && -d ".flow/memory/knowledge/conventions" ]]; then
  echo -e "${GREEN}✓${NC} memory init creates categorized tree"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory init creates categorized tree (missing README or tree dirs)"
  FAIL=$((FAIL + 1))
fi

# All 8 bug categories + 6 knowledge categories present, each with .gitkeep.
# Knowledge: architecture-patterns, conventions, tooling-decisions, workflow,
# best-practices, decisions (fn-38 T1 added the last).
bug_count=$(find .flow/memory/bug -mindepth 2 -name .gitkeep 2>/dev/null | wc -l | tr -d ' ')
kn_count=$(find .flow/memory/knowledge -mindepth 2 -name .gitkeep 2>/dev/null | wc -l | tr -d ' ')
if [[ "$bug_count" == "8" && "$kn_count" == "6" ]]; then
  echo -e "${GREEN}✓${NC} memory init creates 8 bug + 6 knowledge .gitkeep placeholders"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory init placeholders (bug=$bug_count expected 8, knowledge=$kn_count expected 6)"
  FAIL=$((FAIL + 1))
fi
# fn-38 T1 explicit lazy-dir-create assertion: decisions/.gitkeep must exist.
if [[ -f ".flow/memory/knowledge/decisions/.gitkeep" ]]; then
  echo -e "${GREEN}✓${NC} memory init lazy-creates knowledge/decisions/.gitkeep"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory init missing knowledge/decisions/.gitkeep"
  FAIL=$((FAIL + 1))
fi

# fn-30 task 2: --type legacy backcompat auto-maps to --track/--category with stderr warning.
add_json="$(scripts/flowctl memory add --type pitfall "Test pitfall entry" --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True
assert data["action"] == "created"
assert data["entry_id"].startswith("bug/build-errors/"), data
assert data["path"].endswith(".md"), data
assert data["overlap_level"] == "low"
# Warning surfaces in the JSON payload.
warnings = data.get("warnings", [])
assert any("deprecated" in w for w in warnings), warnings
PY
echo -e "${GREEN}✓${NC} memory add --type pitfall auto-maps to bug/build-errors with deprecation warning"
PASS=$((PASS + 1))

# FLOW_NO_DEPRECATION=1 suppresses stderr but keeps the JSON warning.
stderr_out="$(FLOW_NO_DEPRECATION=1 scripts/flowctl memory add --type convention "Silenced" --json 2>&1 >/dev/null)"
if [[ -z "$stderr_out" ]]; then
  echo -e "${GREEN}✓${NC} FLOW_NO_DEPRECATION=1 suppresses stderr warning"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} FLOW_NO_DEPRECATION=1 did not suppress stderr (got: $stderr_out)"
  FAIL=$((FAIL + 1))
fi

# New schema: --track bug --category runtime-errors creates categorized entry.
add_json="$(scripts/flowctl memory add \
  --track bug --category runtime-errors \
  --title "Null deref in auth middleware" \
  --module "src/auth.ts" \
  --tags "auth,nullcheck" \
  --problem-type runtime-error \
  --symptoms "TypeError on missing session" \
  --root-cause "Missing optional chaining" \
  --resolution-type fix \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True
assert data["action"] == "created"
assert data["entry_id"].startswith("bug/runtime-errors/null-deref"), data
assert data["overlap_level"] == "low"
assert data["warnings"] == []
PY
echo -e "${GREEN}✓${NC} memory add --track bug --category runtime-errors (new schema)"
PASS=$((PASS + 1))

# Overlap detection (fn-113.2): high overlap CREATES and surfaces matches; the
# caller decides. Explicit --update <id> then mutates the matched entry.
add_json="$(scripts/flowctl memory add \
  --track bug --category runtime-errors \
  --title "Null deref auth middleware" \
  --module "src/auth.ts" \
  --tags "auth,nullcheck" \
  --problem-type runtime-error \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True, data
assert data["action"] == "created", data
assert data["overlap_level"] == "high", data
assert data["matches"], data
PY
MATCH_ID="$(printf '%s' "$add_json" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["matches"][0]["id"])')"
upd_json="$(scripts/flowctl memory add \
  --track bug --category runtime-errors \
  --title "Null deref auth middleware" \
  --module "src/auth.ts" \
  --tags "auth,nullcheck" \
  --problem-type runtime-error \
  --update "$MATCH_ID" \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$upd_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True, data
assert data["action"] == "updated", data
PY
echo -e "${GREEN}✓${NC} memory add high overlap creates + explicit --update mutates"
PASS=$((PASS + 1))

# Overlap detection: --no-overlap-check always creates new.
add_json="$(scripts/flowctl memory add \
  --track bug --category runtime-errors \
  --title "Null deref auth middleware again" \
  --module "src/auth.ts" \
  --tags "auth,nullcheck" \
  --no-overlap-check \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True, data
assert data["action"] == "created", data
assert data["overlap_level"] == "low", data
PY
echo -e "${GREEN}✓${NC} memory add --no-overlap-check bypasses detection"
PASS=$((PASS + 1))

# Moderate overlap: different title but shared tag (2 dimensions -> moderate).
add_json="$(scripts/flowctl memory add \
  --track knowledge --category conventions \
  --title "Prefer pnpm over npm" \
  --tags "pnpm,tooling" \
  --applies-when "choosing package manager" \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["action"] == "created"
assert data["overlap_level"] == "low"
PY
add_json="$(scripts/flowctl memory add \
  --track knowledge --category conventions \
  --title "Lockfile discipline for pnpm workspaces" \
  --tags "pnpm,workspace" \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
# Shared tag pnpm + same category = score 2 (moderate).
assert data["action"] == "created"
assert data["overlap_level"] == "moderate", data
assert len(data["related_to"]) >= 1, data
PY
echo -e "${GREEN}✓${NC} memory add moderate overlap sets related_to reference"
PASS=$((PASS + 1))

# Invalid category returns exit code 2 with list of valid categories.
set +e
err_out="$(scripts/flowctl memory add --track bug --category nonsense --title "x" --json 2>&1)"
rc=$?
set -e
if [[ $rc -ne 0 ]] && echo "$err_out" | grep -q "build-errors"; then
  echo -e "${GREEN}✓${NC} memory add rejects invalid category with list of valid options"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory add invalid category (rc=$rc, err=$err_out)"
  FAIL=$((FAIL + 1))
fi

# Missing --title returns exit code 2.
set +e
scripts/flowctl memory add --track bug --category build-errors --json >/dev/null 2>&1
rc=$?
set -e
if [[ $rc -eq 2 ]]; then
  echo -e "${GREEN}✓${NC} memory add missing --title returns exit code 2"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory add missing --title exit code (got $rc, expected 2)"
  FAIL=$((FAIL + 1))
fi

# Body via stdin (--body-file -).
add_json="$(printf 'Body from stdin\n' | scripts/flowctl memory add \
  --track knowledge --category workflow \
  --title "Entry with stdin body" \
  --body-file - \
  --applies-when "always" \
  --json 2>/dev/null)"
"${FLOW_PY[@]}" - <<'PY' "$add_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["action"] == "created", data
PY
stdin_path=$(echo "$add_json" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["path"])')
if grep -q "Body from stdin" "$stdin_path"; then
  echo -e "${GREEN}✓${NC} memory add --body-file - reads body from stdin"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory add --body-file - (body not written)"
  FAIL=$((FAIL + 1))
fi

# fn-30.3: list / read / search with categorized tree.
list_json="$(scripts/flowctl memory list --json)"
"${FLOW_PY[@]}" - <<'PY' "$list_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True
entries = data.get("entries", [])
assert len(entries) >= 1, f"expected at least one entry, got {data}"
tracks = {e["track"] for e in entries}
assert "bug" in tracks, f"bug track missing from {tracks}"
# Filter application.
for e in entries:
    assert e["status"] == "active", f"expected active filter, saw {e}"
PY
echo -e "${GREEN}✓${NC} memory list returns categorized entries (default --status active)"
PASS=$((PASS + 1))

list_json="$(scripts/flowctl memory list --track knowledge --json)"
"${FLOW_PY[@]}" - <<'PY' "$list_json"
import json, sys
data = json.loads(sys.argv[1])
entries = data["entries"]
assert all(e["track"] == "knowledge" for e in entries), f"--track filter failed: {entries}"
PY
echo -e "${GREEN}✓${NC} memory list --track knowledge filters to knowledge only"
PASS=$((PASS + 1))

# Seed a stale entry and verify --status stale picks it up.
mkdir -p .flow/memory/knowledge/workflow
cat > .flow/memory/knowledge/workflow/stale-example-2026-01-01.md <<'EOF'
---
title: "Stale example"
date: "2026-01-01"
track: knowledge
category: workflow
status: stale
stale_reason: "obsoleted by migration"
stale_date: "2026-04-24"
applies_when: "never"
---

Body.
EOF
stale_json="$(scripts/flowctl memory list --status stale --json)"
"${FLOW_PY[@]}" - <<'PY' "$stale_json"
import json, sys
data = json.loads(sys.argv[1])
ids = [e["entry_id"] for e in data["entries"]]
assert "knowledge/workflow/stale-example-2026-01-01" in ids, f"stale not listed: {ids}"
assert all(e["status"] == "stale" for e in data["entries"])
PY
echo -e "${GREEN}✓${NC} memory list --status stale surfaces stale entries"
PASS=$((PASS + 1))

# Read by full id.
read_json="$(scripts/flowctl memory read knowledge/workflow/stale-example-2026-01-01 --json)"
"${FLOW_PY[@]}" - <<'PY' "$read_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["entry_id"] == "knowledge/workflow/stale-example-2026-01-01"
assert data["frontmatter"]["track"] == "knowledge"
PY
echo -e "${GREEN}✓${NC} memory read accepts full entry-id"
PASS=$((PASS + 1))

# Read by slug+date.
read_json="$(scripts/flowctl memory read stale-example-2026-01-01 --json)"
"${FLOW_PY[@]}" - <<'PY' "$read_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["entry_id"].endswith("stale-example-2026-01-01")
PY
echo -e "${GREEN}✓${NC} memory read accepts slug+date"
PASS=$((PASS + 1))

# Read by slug only (latest date).
read_json="$(scripts/flowctl memory read stale-example --json)"
"${FLOW_PY[@]}" - <<'PY' "$read_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["entry_id"].endswith("stale-example-2026-01-01")
PY
echo -e "${GREEN}✓${NC} memory read accepts bare slug (latest date wins)"
PASS=$((PASS + 1))

# Unknown id -> exit non-zero.
set +e
scripts/flowctl memory read does-not-exist --json >/dev/null 2>&1
rc=$?
set -e
if [[ $rc -ne 0 ]]; then
  echo -e "${GREEN}✓${NC} memory read unknown id returns non-zero exit"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} memory read unknown id (expected non-zero, got $rc)"
  FAIL=$((FAIL + 1))
fi

# Search with token overlap. Pass --status all because the seeded entry
# carries `status: stale` and fn-34.2 default-excludes stale from search.
search_json="$(scripts/flowctl memory search 'stale example' --status all --json)"
"${FLOW_PY[@]}" - <<'PY' "$search_json"
import json, sys
data = json.loads(sys.argv[1])
matches = data["matches"]
assert matches, f"expected matches, got {data}"
top = matches[0]
assert top["entry_id"].endswith("stale-example-2026-01-01"), top
assert top["score"] > 0
PY
echo -e "${GREEN}✓${NC} memory search ranks by token overlap"
PASS=$((PASS + 1))

# Search default (no --status) excludes stale entries — fn-34.2 contract.
search_json="$(scripts/flowctl memory search 'stale example' --json)"
"${FLOW_PY[@]}" - <<'PY' "$search_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["matches"] == [], f"default search leaked stale entry: {data}"
PY
echo -e "${GREEN}✓${NC} memory search default --status active excludes stale (fn-34.2)"
PASS=$((PASS + 1))

# Search --track filter.
search_json="$(scripts/flowctl memory search 'stale example' --track bug --status all --json)"
"${FLOW_PY[@]}" - <<'PY' "$search_json"
import json, sys
data = json.loads(sys.argv[1])
# No bug-track entry mentions "stale example" → expect no matches.
assert data["matches"] == [], f"--track filter leaked: {data}"
PY
echo -e "${GREEN}✓${NC} memory search --track narrows scope"
PASS=$((PASS + 1))

rm -rf .flow/memory/knowledge/workflow/stale-example-2026-01-01.md

# Legacy detection hint: seed a flat pitfalls.md and re-init.
cat > .flow/memory/pitfalls.md <<'EOF'
# Pitfalls

## 2026-01-01 manual [pitfall]
legacy entry about null deref in auth

---

## 2026-02-01 manual [pitfall]
another legacy pitfall
EOF
hint_json="$(scripts/flowctl memory init --json)"
"${FLOW_PY[@]}" - <<'PY' "$hint_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["success"] is True
assert "pitfalls.md" in data.get("legacy", []), f"legacy not detected: {data}"
assert "migrate" in data.get("hint", ""), f"migration hint missing: {data}"
PY
echo -e "${GREEN}✓${NC} memory init detects legacy files and emits hint"
PASS=$((PASS + 1))

# Legacy list includes the file.
list_json="$(scripts/flowctl memory list --json)"
"${FLOW_PY[@]}" - <<'PY' "$list_json"
import json, sys
data = json.loads(sys.argv[1])
legacy = data.get("legacy", [])
names = [l["filename"] for l in legacy]
assert "pitfalls.md" in names, f"legacy missing from list: {legacy}"
PY
echo -e "${GREEN}✓${NC} memory list reports legacy files as synthetic entries"
PASS=$((PASS + 1))

# Legacy read by path.
read_json="$(scripts/flowctl memory read legacy/pitfalls --json)"
"${FLOW_PY[@]}" - <<'PY' "$read_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["legacy"] is True
assert "null deref" in data["body"]
PY
echo -e "${GREEN}✓${NC} memory read legacy/pitfalls returns whole file"
PASS=$((PASS + 1))

# Legacy read by entry index.
read_json="$(scripts/flowctl memory read legacy/pitfalls#2 --json)"
"${FLOW_PY[@]}" - <<'PY' "$read_json"
import json, sys
data = json.loads(sys.argv[1])
assert data["legacy"] is True
assert data["index"] == 2
assert "another legacy" in data["body"]
PY
echo -e "${GREEN}✓${NC} memory read legacy/pitfalls#2 returns the 2nd entry"
PASS=$((PASS + 1))

# Search covers legacy file.
search_json="$(scripts/flowctl memory search 'null deref' --json)"
"${FLOW_PY[@]}" - <<'PY' "$search_json"
import json, sys
data = json.loads(sys.argv[1])
ids = [m["entry_id"] for m in data["matches"]]
assert any(mid.startswith("legacy/") for mid in ids), f"legacy not in search: {ids}"
PY
echo -e "${GREEN}✓${NC} memory search covers legacy files (substring)"
PASS=$((PASS + 1))

# fn-34/fn-35: search --status stale must NOT include legacy hits
# (legacy entries have no status field; treating them as implicit-active means
# excluding from --status stale queries — Codex P2 finding on PR #120).
stale_json="$(scripts/flowctl memory search 'null deref' --status stale --json)"
"${FLOW_PY[@]}" - <<'PY' "$stale_json"
import json, sys
data = json.loads(sys.argv[1])
legacy = [m for m in data["matches"] if m.get("legacy")]
assert not legacy, f"legacy leaked into --status stale: {legacy}"
PY
echo -e "${GREEN}✓${NC} memory search --status stale excludes legacy hits"
PASS=$((PASS + 1))

# --status all should include legacy back in.
all_json="$(scripts/flowctl memory search 'null deref' --status all --json)"
"${FLOW_PY[@]}" - <<'PY' "$all_json"
import json, sys
data = json.loads(sys.argv[1])
legacy = [m for m in data["matches"] if m.get("legacy")]
assert legacy, f"legacy missing from --status all: {data['matches']}"
PY
echo -e "${GREEN}✓${NC} memory search --status all includes legacy hits"
PASS=$((PASS + 1))

rm -f .flow/memory/pitfalls.md

echo -e "${YELLOW}--- schema v1 validate ---${NC}"
"${FLOW_PY[@]}" - <<'PY'
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

echo -e "${YELLOW}--- copilot commands ---${NC}"
# Test copilot impl-review help (no copilot required for argparse check)
set +e
scripts/flowctl copilot impl-review --help >/dev/null 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} copilot impl-review --help"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} copilot impl-review --help"
  FAIL=$((FAIL + 1))
fi

# Test copilot plan-review help
set +e
scripts/flowctl copilot plan-review --help >/dev/null 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} copilot plan-review --help"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} copilot plan-review --help"
  FAIL=$((FAIL + 1))
fi

# Test copilot completion-review help
set +e
scripts/flowctl copilot completion-review --help >/dev/null 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo -e "${GREEN}✓${NC} copilot completion-review --help"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} copilot completion-review --help"
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
hints_output="$(PYTHONPATH="$SCRIPT_DIR" "${FLOW_PY[@]}" -c "
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
"${FLOW_PY[@]}" - "$SCRIPT_DIR" <<'PY'
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

# fn-29.3: confidence rubric + suppression gate baked into impl prompt (fn-74: tightened headings)
assert "Confidence (pick ONE anchor" in impl_prompt
assert "Suppression gate" in impl_prompt
assert "0 / 25 / 50 / 75 / 100" in impl_prompt
assert "Suppressed findings" in impl_prompt

# fn-29.4: introduced vs pre_existing classification baked into impl prompt (fn-74: tightened heading)
assert "Introduced vs pre-existing" in impl_prompt
assert "introduced" in impl_prompt
assert "pre_existing" in impl_prompt
assert "Pre-existing issues (not blocking this verdict)" in impl_prompt
assert "Classification counts" in impl_prompt
assert "Verdict gate" in impl_prompt

# fn-29.4: plan review does NOT need classification (plans don't have diffs to classify against)
assert "Introduced vs pre-existing" not in plan_prompt
PY
echo -e "${GREEN}✓${NC} build_review_prompt has full criteria"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- parse_suppressed_count (fn-29.3) ---${NC}"
"${FLOW_PY[@]}" - "$SCRIPT_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from flowctl import parse_suppressed_count

# Canonical line
r = parse_suppressed_count("blah\nSuppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0.\n")
assert r == {"50": 3, "25": 7, "0": 2}, r

# Blockquote + partial anchors
r = parse_suppressed_count("> Suppressed findings: 1 at anchor 50, 5 at anchor 25")
assert r == {"50": 1, "25": 5}, r

# Bold markdown wrappers
r = parse_suppressed_count("**Suppressed findings:** 2 at anchor 25, 1 at anchor 0.")
assert r == {"25": 2, "0": 1}, r

# Empty / none payload → None
assert parse_suppressed_count("Suppressed findings: none.") is None
assert parse_suppressed_count("no suppression line here") is None

# Invalid anchors are rejected (e.g. 42 is not one of {0,25,50,75,100})
assert parse_suppressed_count("Suppressed findings: 3 at anchor 42") is None

# High anchors still recognized
r = parse_suppressed_count("Suppressed findings: 5 at anchor 100, 2 at anchor 75")
assert r == {"100": 5, "75": 2}, r
PY
echo -e "${GREEN}✓${NC} parse_suppressed_count handles canonical + edge cases"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- parse_classification_counts (fn-29.4) ---${NC}"
"${FLOW_PY[@]}" - "$SCRIPT_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from flowctl import parse_classification_counts

# Canonical summary line
r = parse_classification_counts("blah\nClassification counts: 2 introduced, 4 pre_existing.\n")
assert r == {"introduced": 2, "pre_existing": 4}, r

# Blockquote prefix + reversed order
r = parse_classification_counts("> Classification counts: 3 pre_existing, 1 introduced")
assert r == {"introduced": 1, "pre_existing": 3}, r

# Bold markdown wrappers
r = parse_classification_counts("**Classification counts:** 0 introduced, 5 pre-existing.")
assert r == {"introduced": 0, "pre_existing": 5}, r

# Summary with only one bucket → missing bucket defaults to 0
r = parse_classification_counts("Classification counts: 3 introduced.")
assert r == {"introduced": 3, "pre_existing": 0}, r

# Fallback: count per-finding Classification: lines when no summary
body = """Some review
**Classification**: introduced
blah
Classification: pre_existing
more
**Classification:** introduced
"""
r = parse_classification_counts(body)
assert r == {"introduced": 2, "pre_existing": 1}, r

# Fallback: inline introduced=true/false markers
body = "[P1, confidence 75, introduced=false] foo\n[P0, confidence 100, introduced=true] bar"
r = parse_classification_counts(body)
assert r == {"introduced": 1, "pre_existing": 1}, r

# Empty → None
assert parse_classification_counts("no classification anywhere") is None
assert parse_classification_counts("") is None
PY
echo -e "${GREEN}✓${NC} parse_classification_counts handles summary + per-finding fallback"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- triage-skip classifier (fn-29.6) ---${NC}"
"${FLOW_PY[@]}" - "$SCRIPT_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from flowctl import _classify_triage_path, _triage_deterministic, _triage_parse_llm_output

# Path classification
assert _classify_triage_path("bun.lock") == "lockfile"
assert _classify_triage_path("package-lock.json") == "lockfile"
assert _classify_triage_path("Cargo.lock") == "lockfile"
assert _classify_triage_path("src/main.py") == "code"
assert _classify_triage_path("plugins/flow-next/scripts/flowctl.py") == "code"
assert _classify_triage_path("README.md") == "docs"
assert _classify_triage_path("docs/guide.md") == "docs"
assert _classify_triage_path("plugins/flow-next/codex/hooks.json") == "generated"
assert _classify_triage_path("node_modules/pkg/index.js") == "generated"
assert _classify_triage_path("vendor/lib.go") == "generated"
assert _classify_triage_path("plugin/plugin.json") == "chore"
assert _classify_triage_path("CHANGELOG.md") == "chore"
assert _classify_triage_path("pyproject.toml") == "chore"
assert _classify_triage_path(".flow/specs/fn-1.md") == "artifact"
assert _classify_triage_path(".flow/tasks/fn-1.1.md") == "artifact"
assert _classify_triage_path("random.xyz") == "other"
# Generated-prefix must only match repo-root, not substring anywhere
# (e.g. scripts/build/release.sh must stay as code, not "generated").
assert _classify_triage_path("scripts/build/release.sh") == "code"
assert _classify_triage_path("packages/dist/util.ts") == "code"
assert _classify_triage_path("vendor_notes/README.md") == "docs"

# AC6: lockfile-only → SKIP
v, r = _triage_deterministic(["bun.lock"])
assert v == "SKIP" and "lockfile" in r.lower(), (v, r)

# AC7: chore-containing shapes require git context — without it, ambiguous.
# This prevents package.json dep edits from silently bypassing full review.
v, r = _triage_deterministic(["plugin/plugin.json", "CHANGELOG.md"])
assert v is None, (v, r)
v, r = _triage_deterministic(["package.json"])
assert v is None, (v, r)
v, r = _triage_deterministic(["bun.lock", "package.json"])
assert v is None, (v, r)

# AC8: docs-only → SKIP
v, r = _triage_deterministic(["README.md", "docs/guide.md"])
assert v == "SKIP" and "docs" in r.lower(), (v, r)

# AC9: any code → REVIEW (even alone)
v, r = _triage_deterministic(["plugins/flow-next/scripts/flowctl.py"])
assert v == "REVIEW", (v, r)
v, r = _triage_deterministic(["src/main.ts", "README.md"])
assert v == "REVIEW", (v, r)

# Empty diff → REVIEW (conservative)
v, r = _triage_deterministic([])
assert v == "REVIEW", (v, r)

# Generated-only → SKIP
v, r = _triage_deterministic(["plugins/flow-next/codex/skills/x.md", "plugins/flow-next/codex/hooks.json"])
assert v == "SKIP", (v, r)

# Artifact alone → REVIEW (conservative — flow state carries intent)
v, r = _triage_deterministic([".flow/specs/fn-29.md"])
assert v == "REVIEW", (v, r)

# Lockfile + generated → SKIP (no chore, no content check needed)
v, r = _triage_deterministic(["bun.lock", "node_modules/x.js"])
assert v == "SKIP", (v, r)

# LLM output parser
v, r = _triage_parse_llm_output("SKIP: lockfile only")
assert v == "SKIP" and r == "lockfile only"
v, r = _triage_parse_llm_output("REVIEW: touches auth logic")
assert v == "REVIEW"
v, r = _triage_parse_llm_output("> **SKIP: docs only**")
assert v == "SKIP"
v, r = _triage_parse_llm_output("reasoning blah\nSKIP: trivial")
assert v == "SKIP" and r == "trivial"
v, r = _triage_parse_llm_output("no verdict here")
assert v is None
v, r = _triage_parse_llm_output("")
assert v is None
PY
echo -e "${GREEN}✓${NC} triage-skip classifier + deterministic layer + LLM parser"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- triage-skip e2e (fn-29.6) ---${NC}"
# End-to-end: tiny git repo, three scenarios (SKIP, REVIEW, receipt).
TRIAGE_TEST_DIR="$TEST_DIR/triage-e2e"
rm -rf "$TRIAGE_TEST_DIR"
mkdir -p "$TRIAGE_TEST_DIR"
(
  cd "$TRIAGE_TEST_DIR"
  git init -q
  git config user.email test@test.com
  git config user.name test
  echo "base" > base.txt
  git add base.txt
  git commit -qm init
  git checkout -qb feature

  # AC6: lockfile-only → SKIP exit 0, receipt written
  echo "{}" > bun.lock
  git add bun.lock
  git commit -qm "dep bump"
  RECEIPT="$TRIAGE_TEST_DIR/r1.json"
  "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" triage-skip --base main --no-llm --receipt "$RECEIPT" --task fn-9-test.1 --json > "$TRIAGE_TEST_DIR/out1.json"
  EXIT1=$?
  [ "$EXIT1" = "0" ] || { echo "FAIL: expected exit 0 on lockfile SKIP, got $EXIT1"; exit 1; }
  grep -q '"mode": "triage_skip"' "$RECEIPT" || { echo "FAIL: receipt missing triage_skip mode"; cat "$RECEIPT"; exit 1; }
  grep -q '"verdict": "SHIP"' "$RECEIPT" || { echo "FAIL: receipt missing SHIP verdict"; cat "$RECEIPT"; exit 1; }
  grep -q '"id": "fn-9-test.1"' "$RECEIPT" || { echo "FAIL: receipt missing task id"; cat "$RECEIPT"; exit 1; }

  # AC9: add code → REVIEW exit 1, no receipt overwrite
  echo "print('x')" > script.py
  git add script.py
  git commit -qm "add script"
  RECEIPT2="$TRIAGE_TEST_DIR/r2.json"
  set +e
  "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" triage-skip --base main --no-llm --receipt "$RECEIPT2" --json > "$TRIAGE_TEST_DIR/out2.json"
  EXIT2=$?
  set -e
  [ "$EXIT2" = "1" ] || { echo "FAIL: expected exit 1 on code REVIEW, got $EXIT2"; exit 1; }
  [ ! -f "$RECEIPT2" ] || { echo "FAIL: receipt should not exist on REVIEW"; exit 1; }
  grep -q '"verdict": "REVIEW"' "$TRIAGE_TEST_DIR/out2.json" || { echo "FAIL: REVIEW verdict missing from json"; cat "$TRIAGE_TEST_DIR/out2.json"; exit 1; }
)
echo -e "${GREEN}✓${NC} triage-skip e2e: lockfile→SKIP+receipt, code→REVIEW+no-receipt"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- triage-skip chore content verification (fn-29.6 fix) ---${NC}"
# Chore classification (package.json etc.) must verify diff content — version
# bumps SKIP, dependency/script edits fall through to REVIEW.
CHORE_TEST_DIR="$TEST_DIR/triage-chore"
rm -rf "$CHORE_TEST_DIR"
mkdir -p "$CHORE_TEST_DIR"
(
  cd "$CHORE_TEST_DIR"
  git init -q
  git config user.email test@test.com
  git config user.name test
  printf '{\n  "name": "pkg",\n  "version": "0.1.0"\n}\n' > package.json
  printf '# Changelog\n' > CHANGELOG.md
  git add package.json CHANGELOG.md
  git commit -qm init
  git checkout -qb feature

  # Scenario A: pure version bump + CHANGELOG addition → SKIP
  printf '{\n  "name": "pkg",\n  "version": "0.1.1"\n}\n' > package.json
  printf '# Changelog\n\n## [0.1.1]\n- bump\n' > CHANGELOG.md
  git add -A
  git commit -qm "bump"
  set +e
  "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" triage-skip --base main --no-llm --json > "$CHORE_TEST_DIR/outA.json"
  EXITA=$?
  set -e
  [ "$EXITA" = "0" ] || { echo "FAIL: version bump should SKIP (exit 0), got $EXITA"; cat "$CHORE_TEST_DIR/outA.json"; exit 1; }
  grep -q '"verdict": "SHIP"' "$CHORE_TEST_DIR/outA.json" || { echo "FAIL: expected SHIP on version bump"; cat "$CHORE_TEST_DIR/outA.json"; exit 1; }

  # Scenario B: dependency edit in package.json → must REVIEW
  git reset --hard main -q
  git checkout -qb feature-deps
  printf '{\n  "name": "pkg",\n  "version": "0.1.0",\n  "dependencies": {\n    "lodash": "^4.0.0"\n  }\n}\n' > package.json
  git add package.json
  git commit -qm "add dep"
  set +e
  "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" triage-skip --base main --no-llm --json > "$CHORE_TEST_DIR/outB.json"
  EXITB=$?
  set -e
  [ "$EXITB" = "1" ] || { echo "FAIL: dep edit must REVIEW (exit 1), got $EXITB"; cat "$CHORE_TEST_DIR/outB.json"; exit 1; }
  grep -q '"verdict": "REVIEW"' "$CHORE_TEST_DIR/outB.json" || { echo "FAIL: expected REVIEW on dep edit"; cat "$CHORE_TEST_DIR/outB.json"; exit 1; }

  # Scenario C: CHANGELOG-only addition → SKIP
  git reset --hard main -q
  git checkout -qb feature-changelog
  printf '# Changelog\n\n## [0.1.1]\n- note\n' > CHANGELOG.md
  git add CHANGELOG.md
  git commit -qm "changelog"
  set +e
  "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" triage-skip --base main --no-llm --json > "$CHORE_TEST_DIR/outC.json"
  EXITC=$?
  set -e
  [ "$EXITC" = "0" ] || { echo "FAIL: CHANGELOG-only should SKIP (exit 0), got $EXITC"; cat "$CHORE_TEST_DIR/outC.json"; exit 1; }
)
echo -e "${GREEN}✓${NC} triage-skip chore verify: version→SKIP, deps→REVIEW, CHANGELOG→SKIP"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- parse_receipt_path ---${NC}"
# Test receipt path parsing for Ralph gating (both legacy and new fn-N-xxx formats)
"${FLOW_PY[@]}" - "$SCRIPT_DIR/hooks" <<'PY'
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

# Test completion receipt parsing (legacy format)
rtype, rid = guard.parse_receipt_path("/tmp/receipts/completion-fn-2.json")
assert rtype == "completion_review", f"Expected completion_review, got {rtype}"
assert rid == "fn-2", f"Expected fn-2, got {rid}"

# Test completion receipt parsing (new fn-N-xxx format)
rtype, rid = guard.parse_receipt_path("/tmp/receipts/completion-fn-7-abc.json")
assert rtype == "completion_review", f"Expected completion_review, got {rtype}"
assert rid == "fn-7-abc", f"Expected fn-7-abc, got {rid}"

# Test fallback
rtype, rid = guard.parse_receipt_path("/tmp/unknown.json")
assert rtype == "impl_review"
assert rid == "UNKNOWN"

# Receipt write detection must catch variable-based redirects like:
#   printf ... > "$RECEIPT_PATH"
# This was the bypass observed in a real Ralph run.
receipt_path = "/tmp/run/receipts/completion-fn-7-ci.json"
command = (
    "RECEIPT_DIR='/tmp/run/receipts'\n"
    'RECEIPT_PATH="$RECEIPT_DIR/completion-fn-7-ci.json"\n'
    "printf '{\"type\":\"completion_review\",\"id\":\"fn-7-ci\",\"mode\":\"rp\"}\\n' > \"$RECEIPT_PATH\""
)
assert guard.is_receipt_write_command(command, receipt_path), "variable receipt redirect not detected"
assert guard.command_has_json_field(command, "type")
assert guard.command_has_json_field(command, "id")
assert not guard.command_has_json_field(command, "verdict")

# All review receipts require a valid verdict and must match the filename.
assert guard.validate_receipt_data({
    "type": "completion_review",
    "id": "fn-7-ci",
    "mode": "rp",
}, receipt_path=receipt_path) == "missing or invalid verdict"
assert guard.validate_receipt_data({
    "type": "completion_review",
    "id": "fn-7-ci",
    "mode": "rp",
    "verdict": "SHIP",
}, receipt_path=receipt_path) == ""
assert guard.validate_receipt_data({
    "type": "completion_review",
    "id": "fn-7-other",
    "mode": "rp",
    "verdict": "SHIP",
}, receipt_path=receipt_path).startswith("id mismatch")
PY
echo -e "${GREEN}✓${NC} receipt path parsing and validation works"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- codex e2e (requires codex CLI) ---${NC}"
# Check if codex is available (handles its own auth)
codex_available="$(command -v codex >/dev/null && echo True || echo False)"
if [[ "$codex_available" == "True" ]]; then
  # Create a simple epic + task for testing
  EPIC3_JSON="$(scripts/flowctl spec create --title "Codex test epic" --json)"
  EPIC3="$(echo "$EPIC3_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$EPIC3" --title "Test task" --json >/dev/null

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
      "${FLOW_PY[@]}" - "$TEST_DIR/plan-receipt.json" "$EPIC3" <<'PY'
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
      "${FLOW_PY[@]}" - "$TEST_DIR/impl-receipt.json" "$EPIC3" <<'PY'
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

echo -e "${YELLOW}--- copilot e2e (requires copilot CLI) ---${NC}"
# Check if copilot is available. Use --skip-probe to avoid spending a premium
# request on availability detection; the real review below exercises auth for
# real. With --skip-probe, `authed` is null (can't know without a probe), so
# we gate on `available` alone and let a real auth failure fail the e2e below.
copilot_available="$(command -v copilot >/dev/null 2>&1 && echo True || echo False)"
if [[ "$copilot_available" == "True" ]]; then
  # Use gpt-5-mini + effort=low to minimize premium-request cost and wall time.
  # Note: claude-family models reject --effort (task-1 finding), so GPT is required.
  export FLOW_COPILOT_MODEL=gpt-5-mini
  export FLOW_COPILOT_EFFORT=low

  # Create a simple epic + task for testing
  EPIC4_JSON="$(scripts/flowctl spec create --title "Copilot test epic" --json)"
  EPIC4="$(echo "$EPIC4_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$EPIC4" --title "Test task" --json >/dev/null

  # Write a simple spec
  cat > ".flow/specs/${EPIC4}.md" << 'EOF'
# Copilot Test Epic

Simple test epic for smoke testing copilot reviews.

## Scope
- Test that copilot can review a plan
- Test that copilot can review an implementation
EOF

  cat > ".flow/tasks/${EPIC4}.1.md" << 'EOF'
# Test Task

Add a simple hello world function.

## Acceptance
- Function returns "hello world"
EOF

  # Test plan-review e2e
  # Create a simple code file inside the repo for the plan to reference
  mkdir -p src
  echo 'def hello_copilot(): return "hello copilot"' > src/hello_copilot.py
  set +e
  cop_plan_result="$(scripts/flowctl copilot plan-review "$EPIC4" --files "src/hello_copilot.py" --base main --receipt "$TEST_DIR/cop-plan-receipt.json" --json 2>&1)"
  cop_plan_rc=$?
  set -e

  if [[ "$cop_plan_rc" -eq 0 ]]; then
    # Verify receipt was written with correct schema (mode=copilot + model + effort)
    if [[ -f "$TEST_DIR/cop-plan-receipt.json" ]]; then
      "${FLOW_PY[@]}" - "$TEST_DIR/cop-plan-receipt.json" "$EPIC4" <<'PY'
import sys, json
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
expected_id = sys.argv[2]
assert data.get("type") == "plan_review", f"Expected type=plan_review, got {data.get('type')}"
assert data.get("id") == expected_id, f"Expected id={expected_id}, got {data.get('id')}"
assert data.get("mode") == "copilot", f"Expected mode=copilot, got {data.get('mode')}"
assert "verdict" in data, "Missing verdict in receipt"
assert "session_id" in data, "Missing session_id in receipt"
# New vs codex: copilot receipts must carry model + effort fields
assert data.get("model"), f"Missing or empty model in receipt: {data.get('model')!r}"
assert data.get("effort"), f"Missing or empty effort in receipt: {data.get('effort')!r}"
assert data["model"] == "gpt-5-mini", f"Expected model=gpt-5-mini, got {data['model']}"
assert data["effort"] == "low", f"Expected effort=low, got {data['effort']}"
PY
      echo -e "${GREEN}✓${NC} copilot plan-review e2e"
      PASS=$((PASS + 1))
    else
      echo -e "${RED}✗${NC} copilot plan-review e2e (no receipt)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo -e "${RED}✗${NC} copilot plan-review e2e (exit $cop_plan_rc)"
    echo "  output: $cop_plan_result" | head -5
    FAIL=$((FAIL + 1))
  fi

  # Re-review smoke: run plan-review again against the same --receipt.
  # Task-3 guards session resume on prior receipt mode==copilot — a copilot-
  # mode receipt here must yield the SAME session_id (resume path), not a
  # fresh UUID (new-session path). This proves cross-run continuity works.
  if [[ -f "$TEST_DIR/cop-plan-receipt.json" ]]; then
    prior_session="$("${FLOW_PY[@]}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$TEST_DIR/cop-plan-receipt.json")"
    set +e
    cop_re_result="$(scripts/flowctl copilot plan-review "$EPIC4" --files "src/hello_copilot.py" --base main --receipt "$TEST_DIR/cop-plan-receipt.json" --json 2>&1)"
    cop_re_rc=$?
    set -e
    if [[ "$cop_re_rc" -eq 0 ]]; then
      new_session="$("${FLOW_PY[@]}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$TEST_DIR/cop-plan-receipt.json")"
      if [[ "$prior_session" == "$new_session" ]]; then
        echo -e "${GREEN}✓${NC} copilot plan-review re-review resumes session"
        PASS=$((PASS + 1))
      else
        echo -e "${RED}✗${NC} copilot plan-review re-review (session changed: $prior_session -> $new_session)"
        FAIL=$((FAIL + 1))
      fi
    else
      echo -e "${RED}✗${NC} copilot plan-review re-review (exit $cop_re_rc)"
      FAIL=$((FAIL + 1))
    fi
  fi

  # Test impl-review e2e (create a simple change first)
  cat > "$TEST_DIR/repo/src/hello_copilot.py" << 'EOF'
def hello_copilot():
    return "hello copilot"
EOF
  git -C "$TEST_DIR/repo" add src/hello_copilot.py
  git -C "$TEST_DIR/repo" commit -m "Add hello_copilot function" >/dev/null

  set +e
  cop_impl_result="$(scripts/flowctl copilot impl-review "${EPIC4}.1" --base HEAD~1 --receipt "$TEST_DIR/cop-impl-receipt.json" --json 2>&1)"
  cop_impl_rc=$?
  set -e

  if [[ "$cop_impl_rc" -eq 0 ]]; then
    # Verify receipt was written with correct schema (mode=copilot + model + effort)
    if [[ -f "$TEST_DIR/cop-impl-receipt.json" ]]; then
      "${FLOW_PY[@]}" - "$TEST_DIR/cop-impl-receipt.json" "$EPIC4" <<'PY'
import sys, json
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
expected_id = f"{sys.argv[2]}.1"
assert data.get("type") == "impl_review", f"Expected type=impl_review, got {data.get('type')}"
assert data.get("id") == expected_id, f"Expected id={expected_id}, got {data.get('id')}"
assert data.get("mode") == "copilot", f"Expected mode=copilot, got {data.get('mode')}"
assert "verdict" in data, "Missing verdict in receipt"
assert "session_id" in data, "Missing session_id in receipt"
assert data.get("model"), f"Missing or empty model in receipt: {data.get('model')!r}"
assert data.get("effort"), f"Missing or empty effort in receipt: {data.get('effort')!r}"
assert data["model"] == "gpt-5-mini", f"Expected model=gpt-5-mini, got {data['model']}"
assert data["effort"] == "low", f"Expected effort=low, got {data['effort']}"
PY
      echo -e "${GREEN}✓${NC} copilot impl-review e2e"
      PASS=$((PASS + 1))
    else
      echo -e "${RED}✗${NC} copilot impl-review e2e (no receipt)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo -e "${RED}✗${NC} copilot impl-review e2e (exit $cop_impl_rc)"
    echo "  output: $cop_impl_result" | head -5
    FAIL=$((FAIL + 1))
  fi

  unset FLOW_COPILOT_MODEL FLOW_COPILOT_EFFORT
else
  echo -e "${YELLOW}⊘${NC} copilot e2e skipped (copilot not available or not authed)"
fi

echo -e "${YELLOW}--- depends_on_epics gate ---${NC}"
cd "$TEST_DIR/repo"  # Back to test repo
# Create epics and capture their IDs
DEP_BASE_JSON="$(scripts/flowctl spec create --title "Dep base" --json)"
DEP_BASE_ID="$(echo "$DEP_BASE_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --spec "$DEP_BASE_ID" --title "Base task" --json >/dev/null
DEP_CHILD_JSON="$(scripts/flowctl spec create --title "Dep child" --json)"
DEP_CHILD_ID="$(echo "$DEP_CHILD_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
DEP_CHILD_JSON_PATH="$(spec_json_path "$DEP_CHILD_ID")"
"${FLOW_PY[@]}" - "$DEP_CHILD_JSON_PATH" "$DEP_BASE_ID" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
base_id = sys.argv[2]
data = json.loads(path.read_text())
data["depends_on_epics"] = [base_id]
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
printf '{"specs":["%s"]}\n' "$DEP_CHILD_ID" > "$TEST_DIR/specs.json"
# Canonical --specs-file is silent; legacy --epics-file emits deprecation
# (verified separately in alias_smoke.sh).
blocked_json="$(scripts/flowctl next --specs-file "$TEST_DIR/specs.json" --json)"
"${FLOW_PY[@]}" - "$DEP_CHILD_ID" "$blocked_json" <<'PY'
import json, sys
child_id = sys.argv[1]
data = json.loads(sys.argv[2])
assert data["status"] == "none"
# fn-111.2: canonical keys only (legacy_reason / blocked_epics dual-emit removed).
assert data["reason"] == "blocked_by_spec_deps"
assert "legacy_reason" not in data, "removed dual-emit key resurfaced"
assert child_id in data.get("blocked_specs", {})
assert "blocked_epics" not in data, "removed dual-emit key resurfaced"
PY
echo -e "${GREEN}✓${NC} depends_on_specs blocks (canonical keys)"
PASS=$((PASS + 1))

# GH PR #95 regression: per-spec `ready` must honor the same spec-level dep
# gate as `next` — a blocked spec reports empty lists + blocked_by_specs,
# never its tasks as ready.
scripts/flowctl task create --spec "$DEP_CHILD_ID" --title "Child task" --json >/dev/null
ready_blocked_json="$(scripts/flowctl ready --spec "$DEP_CHILD_ID" --json)"
"${FLOW_PY[@]}" - "$DEP_BASE_ID" "$ready_blocked_json" <<'PY'
import json, sys
base_id = sys.argv[1]
data = json.loads(sys.argv[2])
assert data["ready"] == [], f"blocked spec leaked ready tasks: {data['ready']}"
assert data["blocked_by_specs"] == [base_id], data.get("blocked_by_specs")
assert "epic_blocked_by" not in data, "removed dual-emit key resurfaced"
PY
# Unblock: base spec done → child task becomes ready again.
DEP_BASE_JSON_PATH="$(spec_json_path "$DEP_BASE_ID")"
"${FLOW_PY[@]}" - "$DEP_BASE_JSON_PATH" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text())
data["status"] = "done"
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
ready_open_json="$(scripts/flowctl ready --spec "$DEP_CHILD_ID" --json)"
"${FLOW_PY[@]}" - "$DEP_CHILD_ID" "$ready_open_json" <<'PY'
import json, sys
child_id = sys.argv[1]
data = json.loads(sys.argv[2])
ids = [t["id"] for t in data["ready"]]
assert f"{child_id}.1" in ids, f"unblocked spec's task not ready: {ids}"
assert "blocked_by_specs" not in data, "gate keys must not appear when unblocked"
PY
echo -e "${GREEN}✓${NC} ready honors spec-level deps (GH PR #95)"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- stdin support ---${NC}"
cd "$TEST_DIR/repo"
STDIN_EPIC_JSON="$(scripts/flowctl spec create --title "Stdin test" --json)"
STDIN_EPIC="$(echo "$STDIN_EPIC_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
# Test epic set-plan with stdin
scripts/flowctl spec set-plan "$STDIN_EPIC" --file - --json <<'EOF'
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
scripts/flowctl task create --spec "$STDIN_EPIC" --title "Set-spec test" --json >/dev/null
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
scripts/flowctl task create --spec "$STDIN_EPIC" --title "Full replacement test" --json >/dev/null
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
scripts/flowctl task create --spec "$STDIN_EPIC" --title "Stdin replacement test" --json >/dev/null
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
scripts/flowctl checkpoint save --spec "$STDIN_EPIC" --json >/dev/null
# Verify checkpoint file exists
[[ -f ".flow/.checkpoint-${STDIN_EPIC}.json" ]] || { echo "checkpoint file not created"; FAIL=$((FAIL + 1)); }
# Modify epic spec
scripts/flowctl spec set-plan "$STDIN_EPIC" --file - --json <<'EOF'
# Modified content
EOF
# Restore from checkpoint
scripts/flowctl checkpoint restore --spec "$STDIN_EPIC" --json >/dev/null
# Verify original content restored
restored_spec="$(scripts/flowctl cat "$STDIN_EPIC")"
echo "$restored_spec" | grep -q "Testing stdin support" || { echo "checkpoint restore failed"; FAIL=$((FAIL + 1)); }
echo -e "${GREEN}✓${NC} checkpoint save/restore"
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

echo -e "${YELLOW}--- model-routing scaffold ceremony prose (fn-88.4) ---${NC}"
# Prose-contract checks on the setup workflow, following the same grep-the-skill
# pattern as the sync block above. These guard the ceremony prose the
# deterministic transforms (test_model_routing_scaffold.py) depend on.
MR_WORKFLOW="$PLUGIN_ROOT/skills/flow-next-setup/workflow.md"

# 1: Headless / non-interactive setup skips the Model Routing question silently.
if grep -q "skipped SILENTLY" "$MR_WORKFLOW"; then
  echo -e "${GREEN}✓${NC} setup workflow states the headless-skip rule"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} setup workflow missing headless-skip rule"
  FAIL=$((FAIL + 1))
fi

# 2: Frozen option strings, as-built casing.
if grep -qF '`Scaffold` / `Scaffold + enable codex delegation` / `Skip`' "$MR_WORKFLOW"; then
  echo -e "${GREEN}✓${NC} setup workflow carries the frozen Model Routing option set"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} setup workflow missing frozen option strings"
  FAIL=$((FAIL + 1))
fi

# 3: Delegation opt-in never pre-sets the first-use consent gate.
if grep -qE "NEVER.{0,40}work\.delegateConsent" "$MR_WORKFLOW"; then
  echo -e "${GREEN}✓${NC} setup workflow never pre-sets work.delegateConsent"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} setup workflow missing never-pre-set-delegateConsent contract"
  FAIL=$((FAIL + 1))
fi

# 4: Scaffold processing is ordered AFTER the Docs block.
if grep -q "the Docs block above" "$MR_WORKFLOW"; then
  echo -e "${GREEN}✓${NC} scaffold processing ordered after the Docs block"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} setup workflow missing after-Docs-block ordering"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- backend spec validation (fn-28.2) ---${NC}"
# Fresh epic + task for backend spec tests
BSPEC_EPIC_JSON="$(scripts/flowctl spec create --title "Backend spec test" --json)"
BSPEC_EPIC="$(echo "$BSPEC_EPIC_JSON" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
scripts/flowctl task create --spec "$BSPEC_EPIC" --title "Backend task" --json >/dev/null
BSPEC_TASK="${BSPEC_EPIC}.1"

# Test 1: valid full spec accepted
if scripts/flowctl task set-backend "$BSPEC_TASK" --review "codex:gpt-5.4:xhigh" --json >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} set-backend accepts valid codex:gpt-5.4:xhigh spec"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-backend rejected valid codex:gpt-5.4:xhigh spec"
  FAIL=$((FAIL + 1))
fi

# Test 2: unknown model warn-and-accepts (fn-76 R1 — ranking is a preference,
# the CLI is the availability authority; effort axis stays strict).
unknown_out="$(scripts/flowctl task set-backend "$BSPEC_TASK" --review "codex:gpt-99" --json 2>&1 || true)"
if echo "$unknown_out" | grep -q '"success": true' \
   && echo "$unknown_out" | grep -q "codex:gpt-99" \
   && echo "$unknown_out" | grep -q "not in flow-next's codex ranking"; then
  echo -e "${GREEN}✓${NC} set-backend warn-and-accepts unknown codex model (fn-76)"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-backend didn't warn-and-accept unknown codex model cleanly: $unknown_out"
  FAIL=$((FAIL + 1))
fi

# Test 2b: a bad EFFORT still hard-fails (effort axis stays strict, fn-76).
badeffort_out="$(scripts/flowctl task set-backend "$BSPEC_TASK" --review "codex:gpt-5.4:bogus-effort" --json 2>&1 || true)"
if echo "$badeffort_out" | grep -q '"success": false' && echo "$badeffort_out" | grep -q "Unknown effort for codex"; then
  echo -e "${GREEN}✓${NC} set-backend rejects unknown codex effort with helpful error"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-backend didn't reject unknown codex effort cleanly: $badeffort_out"
  FAIL=$((FAIL + 1))
fi

# Test 3: rp with model rejected
rp_out="$(scripts/flowctl task set-backend "$BSPEC_TASK" --review "rp:claude-opus" --json 2>&1 || true)"
if echo "$rp_out" | grep -q '"success": false' && echo "$rp_out" | grep -q "does not accept a model"; then
  echo -e "${GREEN}✓${NC} set-backend rejects rp:model spec"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-backend didn't reject rp:model: $rp_out"
  FAIL=$((FAIL + 1))
fi

# Test 4: copilot xhigh accepted
if scripts/flowctl task set-backend "$BSPEC_TASK" --review "copilot:claude-opus-4.5:xhigh" --json >/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} set-backend accepts copilot:claude-opus-4.5:xhigh"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} set-backend rejected valid copilot xhigh spec"
  FAIL=$((FAIL + 1))
fi

# Test 7: empty-string clears field without validation
if scripts/flowctl task set-backend "$BSPEC_TASK" --review "" --json >/dev/null 2>&1; then
  cleared="$("${FLOW_PY[@]}" -c "import json; print(json.load(open('.flow/tasks/${BSPEC_TASK}.json')).get('review'))")"
  if [[ "$cleared" == "None" || "$cleared" == "" ]]; then
    echo -e "${GREEN}✓${NC} empty string clears backend spec"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}✗${NC} empty string didn't clear: raw=$cleared"
    FAIL=$((FAIL + 1))
  fi
else
  echo -e "${RED}✗${NC} empty string rejected by validator (should bypass)"
  FAIL=$((FAIL + 1))
fi

# Test 8: epic set-backend also validates
epic_invalid="$(scripts/flowctl spec set-backend "$BSPEC_EPIC" --impl "bogus:foo" --json 2>&1 || true)"
if echo "$epic_invalid" | grep -q '"success": false' && echo "$epic_invalid" | grep -q "Unknown backend"; then
  echo -e "${GREEN}✓${NC} epic set-backend rejects unknown backend"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} epic set-backend didn't reject unknown backend: $epic_invalid"
  FAIL=$((FAIL + 1))
fi

echo -e "${YELLOW}--- memory migrate (fn-30.4) ---${NC}"
MIG_TEST_DIR="$TEST_DIR/memory-migrate"
rm -rf "$MIG_TEST_DIR"
mkdir -p "$MIG_TEST_DIR"
(
  cd "$MIG_TEST_DIR"
  git init -q
  git config user.email t@t
  git config user.name t
  mkdir -p .flow/memory
  cat > .flow/memory/pitfalls.md <<'LEGEOF'
# Pitfalls

## 2026-03-01 Race condition
Worker race.

---

## 2026-03-15 Null crash
Crash on empty payload.
LEGEOF
  cat > .flow/memory/conventions.md <<'LEGEOF'
# Conventions

## Use pnpm
Project standard.
LEGEOF
  cat > .flow/memory/decisions.md <<'LEGEOF'
# Decisions

## 2026-02-01 Chose Postgres
Replication story.
LEGEOF

  "$SCRIPT_DIR/flowctl" memory init --json >/dev/null

  # Dry-run must not write anything.
  dry_out=$("$SCRIPT_DIR/flowctl" memory migrate --dry-run --no-llm --json 2>&1)
  dry_count=$(echo "$dry_out" | jq '.migrated | length')
  [ "$dry_count" = "4" ] || { echo "FAIL: dry-run expected 4 migrated entries, got $dry_count"; echo "$dry_out"; exit 1; }
  [ ! -d .flow/memory/_legacy ] || { echo "FAIL: dry-run must not move legacy files"; exit 1; }
  [ -f .flow/memory/pitfalls.md ] || { echo "FAIL: dry-run removed pitfalls.md"; exit 1; }

  # Real migrate.
  real_out=$("$SCRIPT_DIR/flowctl" memory migrate --yes --no-llm --json 2>&1)
  real_count=$(echo "$real_out" | jq '.migrated | length')
  [ "$real_count" = "4" ] || { echo "FAIL: real migrate expected 4, got $real_count"; echo "$real_out"; exit 1; }

  # Legacy files moved to _legacy/
  [ -f .flow/memory/_legacy/pitfalls.md ] || { echo "FAIL: pitfalls.md not archived to _legacy"; exit 1; }
  [ ! -f .flow/memory/pitfalls.md ] || { echo "FAIL: pitfalls.md should have been moved"; exit 1; }

  # Categorized entries created.
  bug_count=$(find .flow/memory/bug -type f -name "*.md" ! -name "README.md" | wc -l | tr -d ' ')
  know_count=$(find .flow/memory/knowledge -type f -name "*.md" ! -name "README.md" | wc -l | tr -d ' ')
  [ "$bug_count" = "2" ] || { echo "FAIL: expected 2 bug entries, got $bug_count"; exit 1; }
  [ "$know_count" = "2" ] || { echo "FAIL: expected 2 knowledge entries, got $know_count"; exit 1; }

  # Entry carries YAML frontmatter with track + category.
  sample=$(find .flow/memory/bug -type f -name "race-condition*.md" | head -1)
  [ -n "$sample" ] || { echo "FAIL: race-condition entry missing"; exit 1; }
  grep -q "^track: bug$" "$sample" || { echo "FAIL: entry missing track frontmatter"; cat "$sample"; exit 1; }
  grep -q "^category:" "$sample" || { echo "FAIL: entry missing category frontmatter"; cat "$sample"; exit 1; }

  # Idempotent: re-running finds nothing to migrate.
  rerun=$("$SCRIPT_DIR/flowctl" memory migrate --yes --no-llm --json 2>&1)
  rerun_count=$(echo "$rerun" | jq '.migrated | length')
  [ "$rerun_count" = "0" ] || { echo "FAIL: second migrate found $rerun_count (expected 0 — idempotent)"; echo "$rerun"; exit 1; }
)
echo -e "${GREEN}✓${NC} memory migrate: dry-run, real, 3 legacy files → 4 entries, idempotent"
PASS=$((PASS + 1))

echo -e "${YELLOW}--- memory list-legacy (fn-35) ---${NC}"
LL_TEST_DIR="$TEST_DIR/list-legacy"
rm -rf "$LL_TEST_DIR"
mkdir -p "$LL_TEST_DIR"
(
  cd "$LL_TEST_DIR"
  git init -q
  git config user.email t@t
  git config user.name t
  mkdir -p .flow/memory
  "$SCRIPT_DIR/flowctl" memory init --json >/dev/null

  # Case 1: empty memory dir (no legacy files) — JSON returns {files: []}, rc=0.
  empty_json=$("$SCRIPT_DIR/flowctl" memory list-legacy --json 2>&1)
  empty_count=$(echo "$empty_json" | jq '.files | length')
  [ "$empty_count" = "0" ] || { echo "FAIL: empty list-legacy expected 0 files, got $empty_count"; echo "$empty_json"; exit 1; }

  # Seed two-entry pitfalls.md (matches migrate smoke shape).
  cat > .flow/memory/pitfalls.md <<'LEGEOF'
# Pitfalls

## 2026-03-01 Race condition
Worker race.

---

## 2026-03-15 Null crash
Crash on empty payload.
LEGEOF

  # Case 2: two-entry parse — JSON shape correct + entry_count=2.
  ll_json=$("$SCRIPT_DIR/flowctl" memory list-legacy --json 2>&1)
  files_count=$(echo "$ll_json" | jq '.files | length')
  [ "$files_count" = "1" ] || { echo "FAIL: expected 1 file, got $files_count"; echo "$ll_json"; exit 1; }
  pit_filename=$(echo "$ll_json" | jq -r '.files[0].filename')
  [ "$pit_filename" = "pitfalls.md" ] || { echo "FAIL: expected pitfalls.md, got $pit_filename"; exit 1; }
  pit_count=$(echo "$ll_json" | jq '.files[0].entry_count')
  [ "$pit_count" = "2" ] || { echo "FAIL: expected entry_count=2, got $pit_count"; echo "$ll_json"; exit 1; }
  pit_entries=$(echo "$ll_json" | jq '.files[0].entries | length')
  [ "$pit_entries" = "2" ] || { echo "FAIL: expected 2 entries array, got $pit_entries"; exit 1; }

  # Case 3: mechanical defaults present per entry — bug/build-errors for pitfalls.md.
  m_track=$(echo "$ll_json" | jq -r '.files[0].entries[0].mechanical_track')
  m_cat=$(echo "$ll_json" | jq -r '.files[0].entries[0].mechanical_category')
  [ "$m_track" = "bug" ] || { echo "FAIL: expected mechanical_track=bug, got $m_track"; exit 1; }
  [ "$m_cat" = "build-errors" ] || { echo "FAIL: expected mechanical_category=build-errors, got $m_cat"; exit 1; }
  # Second entry also carries the same mechanical default.
  m_track2=$(echo "$ll_json" | jq -r '.files[0].entries[1].mechanical_track')
  [ "$m_track2" = "bug" ] || { echo "FAIL: expected mechanical_track=bug on entry 2, got $m_track2"; exit 1; }

  # Case 4: text mode — human-readable output includes filename + count + a default.
  text_out=$("$SCRIPT_DIR/flowctl" memory list-legacy 2>&1)
  echo "$text_out" | grep -q "pitfalls.md (2 entries):" || { echo "FAIL: text mode missing 'pitfalls.md (2 entries):' header"; echo "$text_out"; exit 1; }
  echo "$text_out" | grep -q "default bug/build-errors" || { echo "FAIL: text mode missing mechanical default suffix"; echo "$text_out"; exit 1; }
)
echo -e "${GREEN}✓${NC} memory list-legacy: empty dir, two-entry parse, mechanical defaults, text mode"
PASS=$((PASS + 1))

# --- validator pass subcommands (fn-32.1 --validate) ---
echo -e "${YELLOW}--- validator pass (fn-32.1) ---${NC}"

VALIDATE_TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$VALIDATE_TEST_DIR"' EXIT

# Test: codex validate and copilot validate --help surfaces discoverable.
(
  cd "$VALIDATE_TEST_DIR"
  "$SCRIPT_DIR/flowctl" codex validate --help > /dev/null \
    || { echo "FAIL: codex validate --help"; exit 1; }
  "$SCRIPT_DIR/flowctl" copilot validate --help > /dev/null \
    || { echo "FAIL: copilot validate --help"; exit 1; }
)
echo -e "${GREEN}✓${NC} validate subcommands (codex + copilot): --help available"
PASS=$((PASS + 1))

# Test: no-findings no-op path writes validator block + preserves verdict.
# fn-113.4 split-by-mode: receipt mutation is the AUTONOMOUS path - opt in
# explicitly here (interactive default surfaces raw findings, no mutation).
(
  cd "$VALIDATE_TEST_DIR"
  export FLOW_AUTONOMOUS=1
  RPATH="$VALIDATE_TEST_DIR/receipt.json"
  cat > "$RPATH" <<'EOF'
{"type":"impl_review","id":"fn-32.1","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-noop"}
EOF
  out=$("$SCRIPT_DIR/flowctl" codex validate --receipt "$RPATH" --json 2>&1) \
    || { echo "FAIL: codex validate no-op"; echo "$out"; exit 1; }
  echo "$out" | grep -q '"dispatched": 0' \
    || { echo "FAIL: expected dispatched=0"; echo "$out"; exit 1; }
  grep -q '"validator"' "$RPATH" \
    || { echo "FAIL: validator block missing"; cat "$RPATH"; exit 1; }
  grep -q '"verdict": "NEEDS_WORK"' "$RPATH" \
    || { echo "FAIL: verdict changed unexpectedly"; cat "$RPATH"; exit 1; }
)
echo -e "${GREEN}✓${NC} codex validate: no-findings no-op writes validator block, preserves verdict"
PASS=$((PASS + 1))

# Test: missing session_id → error exit 2.
(
  cd "$VALIDATE_TEST_DIR"
  RPATH="$VALIDATE_TEST_DIR/receipt-nosession.json"
  echo '{"mode":"codex","verdict":"NEEDS_WORK"}' > "$RPATH"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" codex validate --receipt "$RPATH" --json 2>&1) || rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 for missing session_id, got $rc"; echo "$out"; exit 1; }
  echo "$out" | grep -q "No session_id" \
    || { echo "FAIL: expected 'No session_id' in error"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} codex validate: missing session_id exits 2 with clear error"
PASS=$((PASS + 1))

# Test: cross-backend guard — codex receipt, copilot validate → error.
(
  cd "$VALIDATE_TEST_DIR"
  RPATH="$VALIDATE_TEST_DIR/receipt-codex.json"
  echo '{"mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-xback"}' > "$RPATH"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" copilot validate --receipt "$RPATH" --json 2>&1) || rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 for cross-backend, got $rc"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "same backend" \
    || { echo "FAIL: expected cross-backend error"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} copilot validate: cross-backend receipt rejected with exit 2"
PASS=$((PASS + 1))

# Test: --receipt is required (argparse enforcement).
(
  cd "$VALIDATE_TEST_DIR"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" codex validate 2>&1) || rc=$?
  [ "$rc" -ne 0 ] || { echo "FAIL: expected nonzero exit when --receipt missing"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "receipt" \
    || { echo "FAIL: expected error mentioning --receipt"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} validate: --receipt required (argparse rejection)"
PASS=$((PASS + 1))

# --- deep-pass subcommands (fn-32.2 --deep) ---
echo -e "${YELLOW}--- deep-pass (fn-32.2) ---${NC}"

DEEP_TEST_DIR="$(mktemp -d)"

# Test: codex deep-pass and copilot deep-pass --help surfaces discoverable.
(
  cd "$DEEP_TEST_DIR"
  "$SCRIPT_DIR/flowctl" codex deep-pass --help > /dev/null \
    || { echo "FAIL: codex deep-pass --help"; exit 1; }
  "$SCRIPT_DIR/flowctl" copilot deep-pass --help > /dev/null \
    || { echo "FAIL: copilot deep-pass --help"; exit 1; }
  "$SCRIPT_DIR/flowctl" review-deep-auto --help > /dev/null \
    || { echo "FAIL: review-deep-auto --help"; exit 1; }
)
echo -e "${GREEN}✓${NC} deep-pass subcommands + review-deep-auto: --help available"
PASS=$((PASS + 1))

# Test: review-deep-auto — security glob matches produce adversarial + security.
(
  cd "$DEEP_TEST_DIR"
  out=$("$SCRIPT_DIR/flowctl" review-deep-auto --files "src/auth.ts,README.md" --json) \
    || { echo "FAIL: review-deep-auto security"; exit 1; }
  echo "$out" | grep -q '"security"' \
    || { echo "FAIL: expected security in auto_enabled"; echo "$out"; exit 1; }
  echo "$out" | grep -q '"adversarial"' \
    || { echo "FAIL: expected adversarial in selected"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-deep-auto: security glob triggers security pass"
PASS=$((PASS + 1))

# Test: review-deep-auto — performance glob.
(
  cd "$DEEP_TEST_DIR"
  out=$("$SCRIPT_DIR/flowctl" review-deep-auto --files "db/migrations/001.sql" --json) \
    || { echo "FAIL: review-deep-auto perf"; exit 1; }
  echo "$out" | grep -q '"performance"' \
    || { echo "FAIL: expected performance in auto_enabled"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-deep-auto: migration glob triggers performance pass"
PASS=$((PASS + 1))

# Test: review-deep-auto — non-matching paths yield adversarial only.
(
  cd "$DEEP_TEST_DIR"
  out=$("$SCRIPT_DIR/flowctl" review-deep-auto --files "src/utils/date.ts" --json) \
    || { echo "FAIL: review-deep-auto no-match"; exit 1; }
  echo "$out" | grep -q '"auto_enabled": \[\]' \
    || { echo "FAIL: expected empty auto_enabled"; echo "$out"; exit 1; }
  echo "$out" | grep -q '"adversarial"' \
    || { echo "FAIL: expected adversarial always-on"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-deep-auto: no-match paths yield adversarial only"
PASS=$((PASS + 1))

# Test: deep-pass requires --pass.
(
  cd "$DEEP_TEST_DIR"
  RPATH="$DEEP_TEST_DIR/receipt.json"
  printf '%s\n' '{"mode":"codex","verdict":"NEEDS_WORK","session_id":"s-dp"}' > "$RPATH"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" codex deep-pass --receipt "$RPATH" --json 2>&1) || rc=$?
  [ "$rc" -ne 0 ] || { echo "FAIL: expected nonzero exit when --pass missing"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "pass" \
    || { echo "FAIL: expected error mentioning --pass"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} deep-pass: --pass required (argparse rejection)"
PASS=$((PASS + 1))

# Test: deep-pass --pass only accepts valid values.
(
  cd "$DEEP_TEST_DIR"
  RPATH="$DEEP_TEST_DIR/receipt.json"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" codex deep-pass --pass bogus --receipt "$RPATH" --json 2>&1) || rc=$?
  [ "$rc" -ne 0 ] || { echo "FAIL: expected nonzero exit for bogus pass"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "invalid choice" \
    || { echo "FAIL: expected 'invalid choice' error"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} deep-pass: --pass rejects invalid values"
PASS=$((PASS + 1))

# Test: deep-pass requires session_id in receipt.
(
  cd "$DEEP_TEST_DIR"
  RPATH="$DEEP_TEST_DIR/receipt-nosess.json"
  printf '%s\n' '{"mode":"codex","verdict":"NEEDS_WORK"}' > "$RPATH"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" codex deep-pass --pass adversarial --receipt "$RPATH" --json 2>&1) || rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 for missing session_id, got $rc"; echo "$out"; exit 1; }
  echo "$out" | grep -q "No session_id" \
    || { echo "FAIL: expected 'No session_id' in error"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} deep-pass: missing session_id exits 2 with clear error"
PASS=$((PASS + 1))

# Test: cross-backend guard — codex receipt, copilot deep-pass → error.
(
  cd "$DEEP_TEST_DIR"
  RPATH="$DEEP_TEST_DIR/receipt-codex.json"
  printf '%s\n' '{"mode":"codex","verdict":"SHIP","session_id":"s-xbdp"}' > "$RPATH"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" copilot deep-pass --pass adversarial --receipt "$RPATH" --json 2>&1) || rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 for cross-backend, got $rc"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "same backend" \
    || { echo "FAIL: expected cross-backend error"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} deep-pass: cross-backend receipt rejected with exit 2"
PASS=$((PASS + 1))

# Test: helper functions — fingerprint/merge/promotion unit tests.
(
  cd "$DEEP_TEST_DIR"
  "${FLOW_PY[@]}" - "$SCRIPT_DIR/flowctl.py" <<'PYEOF' || { echo "FAIL: helper unit tests"; exit 1; }
import sys, importlib.util
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

# fingerprint: same file + near-line + same title
f1 = {"file":"src/auth.ts","line":42,"title":"null deref"}
f2 = {"file":"./src/auth.ts","line":45,"title":"Null Deref"}
assert mod.finding_fingerprint(f1) == mod.finding_fingerprint(f2), "near-line dedup fail"

# promotion anchors
for before, after in [(0,25),(25,50),(50,75),(75,100),(100,100)]:
    assert mod.promote_confidence(before) == after, f"promote({before}) != {after}"

# merge: primary+deep agreement promotes; cross-deep only dedups
primary = [{"id":"f1","file":"src/auth.ts","line":42,"title":"null deref","confidence":50,"severity":"P1","classification":"introduced"}]
deep = {
  "adversarial": [{"id":"a1","file":"src/auth.ts","line":40,"title":"Null Deref","confidence":75,"pass":"adversarial"}],
  "security":    [{"id":"s1","file":"src/auth.ts","line":42,"title":"null deref","confidence":75,"pass":"security"}],
}
r = mod.merge_deep_findings(primary, deep)
# primary f1 should be promoted TWICE (once per agreeing deep pass) → 50 → 75 → 100
assert len(r["promotions"]) == 2, f"expected 2 promotions, got {r['promotions']}"
f1m = next(x for x in r["merged"] if x["id"] == "f1")
assert f1m["confidence"] == 100, f"expected f1 promoted to 100, got {f1m['confidence']}"
# No deep-pass findings should survive (both match primary)
assert len(r["merged"]) == 1, f"expected only primary in merged, got {r['merged']}"

# auto-enable heuristic
assert mod.auto_enabled_passes(["src/auth.ts"]) == ["security"]
assert mod.auto_enabled_passes(["db/migrations/001.sql"]) == ["performance"]
assert mod.auto_enabled_passes(["src/utils/date.ts"]) == []

print("helpers OK")
PYEOF
)
echo -e "${GREEN}✓${NC} deep-pass helpers: fingerprint/promote/merge/auto-enable"
PASS=$((PASS + 1))

# Cleanup deep-pass test dir (use trash when available, fallback to rmdir tree)
trash "$DEEP_TEST_DIR" 2>/dev/null || true

# --- interactive walkthrough helpers (fn-32.3 --interactive) ---
echo -e "${YELLOW}--- interactive walkthrough (fn-32.3) ---${NC}"

WALK_TEST_DIR="$(mktemp -d)"

# Test: both walkthrough subcommands surface help.
(
  cd "$WALK_TEST_DIR"
  "$SCRIPT_DIR/flowctl" review-walkthrough-defer --help > /dev/null \
    || { echo "FAIL: review-walkthrough-defer --help"; exit 1; }
  "$SCRIPT_DIR/flowctl" review-walkthrough-record --help > /dev/null \
    || { echo "FAIL: review-walkthrough-record --help"; exit 1; }
)
echo -e "${GREEN}✓${NC} walkthrough subcommands: --help available"
PASS=$((PASS + 1))

# Test: --findings-file required on defer helper.
(
  cd "$WALK_TEST_DIR"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-defer --json 2>&1) || rc=$?
  [ "$rc" -ne 0 ] || { echo "FAIL: expected error without --findings-file"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "findings-file" \
    || { echo "FAIL: expected error mentioning --findings-file"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-defer: --findings-file required"
PASS=$((PASS + 1))

# Test: --receipt required on record helper.
(
  cd "$WALK_TEST_DIR"
  rc=0
  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-record --applied 1 --json 2>&1) || rc=$?
  [ "$rc" -ne 0 ] || { echo "FAIL: expected error without --receipt"; echo "$out"; exit 1; }
  echo "$out" | grep -qi "receipt" \
    || { echo "FAIL: expected error mentioning --receipt"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-record: --receipt required"
PASS=$((PASS + 1))

# Test: defer helper — append to sink, stamps session header, creates dir.
(
  cd "$WALK_TEST_DIR"
  git init -q
  git config user.email test@example.com
  git config user.name test
  git checkout -q -b feature/fn-32-walkthrough

  cat > findings.jsonl <<'EOF'
{"id":"f1","severity":"P1","confidence":75,"classification":"introduced","file":"src/auth.ts","line":42,"title":"null deref","suggested_fix":"guard before use"}
{"id":"f2","severity":"P2","confidence":50,"classification":"introduced","file":"src/cart.ts","line":88,"title":"off-by-one","suggested_fix":"use >= 1","deferred_reason":"needs product decision"}
EOF

  cat > receipt.json <<'EOF'
{"type":"impl_review","id":"fn-32.3","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-abc"}
EOF

  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-defer \
      --findings-file findings.jsonl --receipt receipt.json --json 2>&1) \
    || { echo "FAIL: defer dispatch"; echo "$out"; exit 1; }

  # Branch slug: feature/fn-32-walkthrough → feature-fn-32-walkthrough
  SINK=".flow/review-deferred/feature-fn-32-walkthrough.md"
  [ -f "$SINK" ] || { echo "FAIL: sink file missing at $SINK"; exit 1; }

  # Must contain top-level header once, session header once, both findings
  grep -qc "# Deferred review findings" "$SINK" || { echo "FAIL: missing top header"; exit 1; }
  grep -q "review session fn-32.3 (sess-abc)" "$SINK" || { echo "FAIL: missing session header with receipt ids"; cat "$SINK"; exit 1; }
  grep -q "null deref" "$SINK" || { echo "FAIL: f1 missing from sink"; exit 1; }
  grep -q "off-by-one" "$SINK" || { echo "FAIL: f2 missing from sink"; exit 1; }
  # Per-finding deferred_reason override must win over default
  grep -q "needs product decision" "$SINK" || { echo "FAIL: per-finding reason missing"; exit 1; }
  grep -q "deferred by user" "$SINK" || { echo "FAIL: default reason missing for f1"; exit 1; }

  echo "$out" | grep -q '"appended": 2' || { echo "FAIL: appended count wrong"; echo "$out"; exit 1; }
  echo "$out" | grep -q '"branch_slug": "feature-fn-32-walkthrough"' \
    || { echo "FAIL: branch slug wrong"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-defer: creates sink + stamps session + preserves per-finding reasons"
PASS=$((PASS + 1))

# Test: defer helper is append-only across sessions.
(
  cd "$WALK_TEST_DIR"
  cat > findings2.jsonl <<'EOF'
{"id":"f3","severity":"P1","confidence":75,"classification":"introduced","file":"src/new.ts","line":1,"title":"second session finding"}
EOF

  "$SCRIPT_DIR/flowctl" review-walkthrough-defer \
      --findings-file findings2.jsonl --json > /dev/null \
    || { echo "FAIL: second defer"; exit 1; }

  SINK=".flow/review-deferred/feature-fn-32-walkthrough.md"
  # Exactly one top-level header
  hcount=$(grep -c '^# Deferred review findings' "$SINK")
  [ "$hcount" = "1" ] || { echo "FAIL: expected 1 top header, got $hcount"; cat "$SINK"; exit 1; }
  # Exactly 2 session sections
  scount=$(grep -c '^## ' "$SINK")
  [ "$scount" = "2" ] || { echo "FAIL: expected 2 session sections, got $scount"; cat "$SINK"; exit 1; }
  # First session content must still be there
  grep -q "null deref" "$SINK" || { echo "FAIL: first session content lost"; exit 1; }
  grep -q "second session finding" "$SINK" || { echo "FAIL: second session not appended"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-defer: append-only (multi-session preserves prior content)"
PASS=$((PASS + 1))

# Test: defer helper — empty findings file is a no-op that still succeeds.
(
  cd "$WALK_TEST_DIR"
  : > empty.jsonl
  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-defer \
      --findings-file empty.jsonl --json 2>&1) \
    || { echo "FAIL: empty findings should not error"; echo "$out"; exit 1; }
  echo "$out" | grep -q '"appended": 0' \
    || { echo "FAIL: expected appended=0"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-defer: empty findings file no-op"
PASS=$((PASS + 1))

# Test: --branch override works when not in a git repo.
(
  cd "$WALK_TEST_DIR"
  mkdir -p nogit
  cd nogit
  cat > findings.jsonl <<'EOF'
{"id":"f1","severity":"P1","confidence":75,"classification":"introduced","file":"a.ts","line":1,"title":"test"}
EOF
  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-defer \
      --findings-file findings.jsonl --branch custom/slash-branch --json 2>&1) \
    || { echo "FAIL: --branch override"; echo "$out"; exit 1; }
  echo "$out" | grep -q '"branch_slug": "custom-slash-branch"' \
    || { echo "FAIL: expected sanitized branch slug"; echo "$out"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-defer: --branch override sanitizes slug"
PASS=$((PASS + 1))

# Test: record helper — stamps walkthrough block, preserves verdict.
(
  cd "$WALK_TEST_DIR"
  RPATH="record-receipt.json"
  cat > "$RPATH" <<'EOF'
{"type":"impl_review","id":"fn-32.3","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-r1"}
EOF
  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-record \
      --receipt "$RPATH" \
      --applied 3 --deferred 2 --skipped 1 --acknowledged 0 --lfg-rest true \
      --json 2>&1) \
    || { echo "FAIL: record dispatch"; echo "$out"; exit 1; }

  # Receipt must retain verdict + session_id and gain walkthrough block
  grep -q '"verdict": "NEEDS_WORK"' "$RPATH" || { echo "FAIL: verdict changed"; cat "$RPATH"; exit 1; }
  grep -q '"session_id": "sess-r1"' "$RPATH" || { echo "FAIL: session_id lost"; cat "$RPATH"; exit 1; }
  grep -q '"walkthrough"' "$RPATH" || { echo "FAIL: walkthrough block missing"; cat "$RPATH"; exit 1; }
  grep -q '"applied": 3' "$RPATH" || { echo "FAIL: applied count wrong"; cat "$RPATH"; exit 1; }
  grep -q '"lfg_rest": true' "$RPATH" || { echo "FAIL: lfg_rest wrong"; cat "$RPATH"; exit 1; }
  grep -q '"walkthrough_timestamp"' "$RPATH" || { echo "FAIL: walkthrough_timestamp missing"; cat "$RPATH"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-record: stamps block, preserves verdict + session_id"
PASS=$((PASS + 1))

# Test: record helper — creates receipt file when missing.
(
  cd "$WALK_TEST_DIR"
  RPATH="new-receipt.json"
  [ -f "$RPATH" ] && rm -- "$RPATH"
  out=$("$SCRIPT_DIR/flowctl" review-walkthrough-record \
      --receipt "$RPATH" --applied 0 --deferred 5 --json 2>&1) \
    || { echo "FAIL: record with missing receipt"; echo "$out"; exit 1; }
  [ -f "$RPATH" ] || { echo "FAIL: receipt not created"; exit 1; }
  grep -q '"deferred": 5' "$RPATH" || { echo "FAIL: deferred count wrong"; cat "$RPATH"; exit 1; }
  grep -q '"lfg_rest": false' "$RPATH" || { echo "FAIL: lfg_rest default wrong"; cat "$RPATH"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-record: creates receipt when missing, lfg_rest defaults false"
PASS=$((PASS + 1))

# Test: record helper — never flips verdict (walkthrough is additive).
(
  cd "$WALK_TEST_DIR"
  RPATH="ship-receipt.json"
  echo '{"type":"impl_review","id":"fn-32.3","mode":"codex","verdict":"SHIP","session_id":"sess-ship"}' > "$RPATH"
  "$SCRIPT_DIR/flowctl" review-walkthrough-record \
      --receipt "$RPATH" --applied 5 --json > /dev/null \
    || { echo "FAIL: record on SHIP"; exit 1; }
  grep -q '"verdict": "SHIP"' "$RPATH" || { echo "FAIL: verdict flipped from SHIP"; cat "$RPATH"; exit 1; }

  # Same on MAJOR_RETHINK
  echo '{"type":"impl_review","id":"fn-32.3","mode":"codex","verdict":"MAJOR_RETHINK"}' > "$RPATH"
  "$SCRIPT_DIR/flowctl" review-walkthrough-record \
      --receipt "$RPATH" --applied 0 --deferred 7 --json > /dev/null
  grep -q '"verdict": "MAJOR_RETHINK"' "$RPATH" || { echo "FAIL: verdict flipped from MAJOR_RETHINK"; cat "$RPATH"; exit 1; }
)
echo -e "${GREEN}✓${NC} review-walkthrough-record: never flips verdict"
PASS=$((PASS + 1))

# Test: lfg-rest accepts true/false/yes/1/0 (case-insensitive truthy).
(
  cd "$WALK_TEST_DIR"
  RPATH="lfg-receipt.json"
  for val in true TRUE yes 1; do
    echo '{"verdict":"NEEDS_WORK"}' > "$RPATH"
    "$SCRIPT_DIR/flowctl" review-walkthrough-record \
        --receipt "$RPATH" --lfg-rest "$val" --json > /dev/null
    grep -q '"lfg_rest": true' "$RPATH" \
      || { echo "FAIL: lfg-rest=$val should parse true"; cat "$RPATH"; exit 1; }
  done
  for val in false FALSE no 0 anything; do
    echo '{"verdict":"NEEDS_WORK"}' > "$RPATH"
    "$SCRIPT_DIR/flowctl" review-walkthrough-record \
        --receipt "$RPATH" --lfg-rest "$val" --json > /dev/null
    grep -q '"lfg_rest": false' "$RPATH" \
      || { echo "FAIL: lfg-rest=$val should parse false"; cat "$RPATH"; exit 1; }
  done
)
echo -e "${GREEN}✓${NC} review-walkthrough-record: --lfg-rest parses truthy forms (true/TRUE/yes/1) vs everything else"
PASS=$((PASS + 1))

# Test: Ralph-block enforced by SKILL.md bash snippet (simulate invocation).
(
  cd "$WALK_TEST_DIR"
  # Case A: REVIEW_RECEIPT_PATH set + --interactive → exit 2
  rc=0
  REVIEW_RECEIPT_PATH=/tmp/r.json bash -c '
ARGUMENTS="--interactive"
INTERACTIVE=false
for arg in $ARGUMENTS; do
  case "$arg" in --interactive) INTERACTIVE=true ;; esac
done
if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    echo "Error: --interactive blocked" >&2
    exit 2
  fi
fi
exit 0
' 2>/tmp/walkstderr || rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 under REVIEW_RECEIPT_PATH, got $rc"; cat /tmp/walkstderr; exit 1; }
  grep -qi "blocked" /tmp/walkstderr || { echo "FAIL: missing block message"; cat /tmp/walkstderr; exit 1; }

  # Case B: FLOW_RALPH=1 + --interactive → exit 2
  rc=0
  FLOW_RALPH=1 bash -c '
ARGUMENTS="fn-32.3 --validate --interactive"
INTERACTIVE=false
for arg in $ARGUMENTS; do
  case "$arg" in --interactive) INTERACTIVE=true ;; esac
done
if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    exit 2
  fi
fi
exit 0
' || rc=$?
  [ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 under FLOW_RALPH=1, got $rc"; exit 1; }

  # Case C: No --interactive in Ralph env → exit 0 (no block)
  rc=0
  REVIEW_RECEIPT_PATH=/tmp/r.json bash -c '
ARGUMENTS="fn-32.3 --validate"
INTERACTIVE=false
for arg in $ARGUMENTS; do
  case "$arg" in --interactive) INTERACTIVE=true ;; esac
done
if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    exit 2
  fi
fi
exit 0
' || rc=$?
  [ "$rc" -eq 0 ] || { echo "FAIL: Ralph env without --interactive should pass, got $rc"; exit 1; }
)
echo -e "${GREEN}✓${NC} SKILL.md Ralph-block: blocks --interactive under REVIEW_RECEIPT_PATH / FLOW_RALPH, passes without"
PASS=$((PASS + 1))

# Cleanup walkthrough test dir
trash "$WALK_TEST_DIR" 2>/dev/null || true

echo ""
echo -e "${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
echo -e "\n${GREEN}All tests passed!${NC}"
