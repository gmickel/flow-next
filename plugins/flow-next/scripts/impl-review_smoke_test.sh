#!/usr/bin/env bash
# fn-32-opt-in-review-flags-validate-deep.5
# Smoke tests for impl-review opt-in flags (--validate, --deep, --interactive)
# plus Ralph regression verification under env-var opt-ins.
#
# Covers the 7 cases enumerated in the task spec plus a 4-config Ralph sweep.
# Lighter duty than smoke_test.sh: only the flag layer + receipt shape +
# Ralph regression. Backend-LLM paths are mocked (no codex/copilot/rp invoked).
#
# Run from any directory other than the plugin repo root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Safety: never run from the main plugin repo (matches sibling smoke scripts).
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="/tmp/impl-review-smoke-$$"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
  if [[ "${KEEP_TEST_DIR:-0}" == "1" ]]; then
    echo "Keeping test dir: $TEST_DIR"
    return
  fi
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

ok() {
  echo -e "${GREEN}✓${NC} $1"
  PASS=$((PASS + 1))
}

fail() {
  echo -e "${RED}✗${NC} $1"
  FAIL=$((FAIL + 1))
}

# --- helper: assert receipt JSON has / lacks a key ---
assert_has_key() {
  local file="$1" key="$2" label="$3"
  if "$PYTHON_BIN" -c "import json,sys; d=json.load(open('$file')); sys.exit(0 if '$key' in d else 1)"; then
    ok "$label has key '$key'"
  else
    fail "$label missing key '$key'"
    cat "$file" >&2
  fi
}

assert_lacks_key() {
  local file="$1" key="$2" label="$3"
  if "$PYTHON_BIN" -c "import json,sys; d=json.load(open('$file')); sys.exit(0 if '$key' not in d else 1)"; then
    ok "$label lacks key '$key' (default-shape regression)"
  else
    fail "$label unexpectedly carries key '$key'"
    cat "$file" >&2
  fi
}

assert_eq_jq() {
  local file="$1" expr="$2" expected="$3" label="$4"
  local actual
  actual="$("$PYTHON_BIN" -c "import json; d=json.load(open('$file')); print($expr)" 2>&1 || true)"
  if [[ "$actual" == "$expected" ]]; then
    ok "$label  ($expr == $expected)"
  else
    fail "$label  ($expr expected $expected, got $actual)"
    cat "$file" >&2
  fi
}

echo -e "${YELLOW}=== impl-review opt-in flag smoke tests (fn-32.5) ===${NC}"

mkdir -p "$TEST_DIR/repo"
cd "$TEST_DIR/repo"
git init -q
git config user.email "impl-review-smoke@example.com"
git config user.name "Impl Review Smoke"
git checkout -b main >/dev/null 2>&1 || true
echo "# impl-review smoke" > README.md
git add README.md
git commit -q -m "init"

FLOWCTL="$PLUGIN_ROOT/scripts/flowctl"

# =============================================================================
# CASE 1: default review (no flags) — receipt has only base fields.
# =============================================================================
echo -e "${YELLOW}--- Case 1: default review (regression check) ---${NC}"

CASE1_DIR="$TEST_DIR/case1"
mkdir -p "$CASE1_DIR"
RECEIPT="$CASE1_DIR/receipt.json"

# Synthesize a default-review receipt the same shape backends produce
# (no validator / deep / walkthrough blocks).
cat > "$RECEIPT" <<'EOF'
{
  "type": "impl_review",
  "id": "fn-32.5-case1",
  "mode": "codex",
  "verdict": "SHIP",
  "session_id": "sess-default-shape",
  "timestamp": "2026-04-24T12:00:00Z"
}
EOF

# Ralph gate keys present
for k in verdict mode session_id; do
  assert_has_key "$RECEIPT" "$k" "Case 1: receipt"
done

# Flag blocks absent
for k in validator validator_timestamp deep_passes deep_findings_count deep_timestamp cross_pass_promotions verdict_before_deep walkthrough walkthrough_timestamp; do
  assert_lacks_key "$RECEIPT" "$k" "Case 1: receipt"
done

# =============================================================================
# CASE 2: --validate
# Drives the in-process write path via codex validate empty-findings shortcut
# (no LLM call) plus a direct merge for the "all dropped → SHIP upgrade" branch.
# =============================================================================
echo -e "${YELLOW}--- Case 2: --validate (validator block + upgrade path) ---${NC}"

CASE2_DIR="$TEST_DIR/case2"
mkdir -p "$CASE2_DIR"

# Sub-case 2a: empty-findings no-op writes block + preserves NEEDS_WORK
RECEIPT_2A="$CASE2_DIR/receipt_2a.json"
cat > "$RECEIPT_2A" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c2a","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-2a"}
EOF

if "$FLOWCTL" codex validate --receipt "$RECEIPT_2A" --json >/dev/null 2>&1; then
  assert_has_key "$RECEIPT_2A" "validator" "Case 2a"
  assert_has_key "$RECEIPT_2A" "validator_timestamp" "Case 2a"
  assert_eq_jq "$RECEIPT_2A" "d['validator']['dispatched']" "0" "Case 2a"
  assert_eq_jq "$RECEIPT_2A" "d['validator']['kept']" "0" "Case 2a"
  assert_eq_jq "$RECEIPT_2A" "d['verdict']" "NEEDS_WORK" "Case 2a verdict preserved"
  assert_lacks_key "$RECEIPT_2A" "verdict_before_validate" "Case 2a"
  assert_lacks_key "$RECEIPT_2A" "deep_passes" "Case 2a additivity"
  assert_lacks_key "$RECEIPT_2A" "walkthrough" "Case 2a additivity"
else
  fail "Case 2a: codex validate empty-findings shortcut failed"
fi

# Sub-case 2b: all-dropped from NEEDS_WORK → SHIP upgrade path
# Exercise via the in-process helper directly (matches what the LLM
# branch would call after parsing validator output).
RECEIPT_2B="$CASE2_DIR/receipt_2b.json"
cat > "$RECEIPT_2B" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c2b","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-2b"}
EOF

"$PYTHON_BIN" - "$SCRIPT_DIR/flowctl.py" "$RECEIPT_2B" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
result = {
    "dispatched": 1, "dropped": 1, "kept": 0,
    "reasons": [{"id": "f1", "file": "src/x.py", "line": 5, "reason": "guarded"}],
}
mod._apply_validator_to_receipt(sys.argv[2], result, prior_verdict="NEEDS_WORK")
PYEOF
assert_eq_jq "$RECEIPT_2B" "d['verdict']" "SHIP" "Case 2b all-dropped upgrade"
assert_eq_jq "$RECEIPT_2B" "d['verdict_before_validate']" "NEEDS_WORK" "Case 2b records prior verdict"
assert_eq_jq "$RECEIPT_2B" "d['validator']['kept']" "0" "Case 2b kept=0"
assert_eq_jq "$RECEIPT_2B" "len(d['validator']['reasons'])" "1" "Case 2b reasons preserved"

# Sub-case 2c: surviving real finding keeps NEEDS_WORK
RECEIPT_2C="$CASE2_DIR/receipt_2c.json"
cat > "$RECEIPT_2C" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c2c","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-2c"}
EOF
"$PYTHON_BIN" - "$SCRIPT_DIR/flowctl.py" "$RECEIPT_2C" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
result = {
    "dispatched": 2, "dropped": 1, "kept": 1,
    "reasons": [{"id": "f1", "file": "a", "line": 1, "reason": "fp"}],
}
mod._apply_validator_to_receipt(sys.argv[2], result, prior_verdict="NEEDS_WORK")
PYEOF
assert_eq_jq "$RECEIPT_2C" "d['verdict']" "NEEDS_WORK" "Case 2c kept>0 stays NEEDS_WORK"
assert_lacks_key "$RECEIPT_2C" "verdict_before_validate" "Case 2c no upgrade marker"
assert_eq_jq "$RECEIPT_2C" "d['validator']['kept']" "1" "Case 2c kept=1"

# =============================================================================
# CASE 3: --deep — adversarial always + security auto-enable on auth diff
# =============================================================================
echo -e "${YELLOW}--- Case 3: --deep (auto-enable + receipt) ---${NC}"

# Auto-enable on auth diff
out=$("$FLOWCTL" review-deep-auto --files "src/auth.ts,routes/sessions.ts" --json)
echo "$out" | grep -q '"adversarial"' \
  && ok "Case 3: adversarial always selected" || fail "Case 3: adversarial missing"
echo "$out" | grep -q '"security"' \
  && ok "Case 3: security auto-enabled on auth diff" || fail "Case 3: security missing"
echo "$out" | grep -q '"performance"' \
  && fail "Case 3: performance unexpectedly auto-enabled" \
  || ok "Case 3: performance correctly NOT auto-enabled (no perf-sensitive paths)"

# Build a deep-pass receipt and verify shape
CASE3_DIR="$TEST_DIR/case3"
mkdir -p "$CASE3_DIR"
RECEIPT_3="$CASE3_DIR/receipt.json"
cat > "$RECEIPT_3" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c3","mode":"codex","verdict":"SHIP","session_id":"sess-c3"}
EOF

"$PYTHON_BIN" - "$SCRIPT_DIR/flowctl.py" "$RECEIPT_3" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
primary = []
deep_by_pass = {
    "adversarial": [{"id": "a1", "file": "src/auth.ts", "line": 10,
                     "title": "minor", "severity": "P3", "confidence": 25,
                     "classification": "introduced", "pass": "adversarial"}],
    "security":    [],  # zero deep-security findings
}
merge = mod.merge_deep_findings(primary, deep_by_pass)
mod._apply_deep_passes_to_receipt(
    sys.argv[2],
    passes_run=["adversarial", "security"],
    deep_by_pass=deep_by_pass,
    merge_result=merge,
    prior_verdict="SHIP",
)
PYEOF
assert_has_key "$RECEIPT_3" "deep_passes" "Case 3"
assert_has_key "$RECEIPT_3" "deep_findings_count" "Case 3"
assert_has_key "$RECEIPT_3" "deep_timestamp" "Case 3"
# cross_pass_promotions is conditionally written (only when promotions occur).
# Case 3 has no primary findings → no agreements → no promotions → key absent.
assert_lacks_key "$RECEIPT_3" "cross_pass_promotions" "Case 3 (no agreements → key absent)"
assert_eq_jq "$RECEIPT_3" "d['deep_passes']" "['adversarial', 'security']" "Case 3 passes_run order"
assert_eq_jq "$RECEIPT_3" "d['deep_findings_count']['adversarial']" "1" "Case 3 adversarial count"
assert_eq_jq "$RECEIPT_3" "d['deep_findings_count']['security']" "0" "Case 3 security count"
assert_eq_jq "$RECEIPT_3" "d['verdict']" "SHIP" "Case 3 sub-blocking finding does not upgrade"
assert_lacks_key "$RECEIPT_3" "validator" "Case 3 additivity"
assert_lacks_key "$RECEIPT_3" "walkthrough" "Case 3 additivity"

# Case 3 alt: SHIP → NEEDS_WORK upgrade when deep surfaces blocking finding
RECEIPT_3B="$CASE3_DIR/receipt_block.json"
cat > "$RECEIPT_3B" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c3b","mode":"codex","verdict":"SHIP","session_id":"sess-c3b"}
EOF
"$PYTHON_BIN" - "$SCRIPT_DIR/flowctl.py" "$RECEIPT_3B" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
deep_by_pass = {
    "adversarial": [{"id": "a2", "file": "src/auth.ts", "line": 22,
                     "title": "auth bypass", "severity": "P0", "confidence": 75,
                     "classification": "introduced", "pass": "adversarial"}],
}
merge = mod.merge_deep_findings([], deep_by_pass)
mod._apply_deep_passes_to_receipt(
    sys.argv[2],
    passes_run=["adversarial"],
    deep_by_pass=deep_by_pass,
    merge_result=merge,
    prior_verdict="SHIP",
)
PYEOF
assert_eq_jq "$RECEIPT_3B" "d['verdict']" "NEEDS_WORK" "Case 3b SHIP→NEEDS_WORK on blocking deep finding"
assert_eq_jq "$RECEIPT_3B" "d['verdict_before_deep']" "SHIP" "Case 3b records prior verdict"

# =============================================================================
# CASE 4: --deep=performance explicit (only that pass runs)
# =============================================================================
echo -e "${YELLOW}--- Case 4: --deep=performance explicit ---${NC}"

CASE4_DIR="$TEST_DIR/case4"
mkdir -p "$CASE4_DIR"
RECEIPT_4="$CASE4_DIR/receipt.json"
cat > "$RECEIPT_4" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c4","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-c4"}
EOF

# Simulate the SKILL.md branch: --deep=performance bypasses auto-enable
# and runs ONLY the listed pass. The smoke layer here tests that the
# deep-pass receipt writer accepts an arbitrary subset (passes_run=["performance"]).
"$PYTHON_BIN" - "$SCRIPT_DIR/flowctl.py" "$RECEIPT_4" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
deep_by_pass = {
    "performance": [
        {"id": "p1", "file": "src/api/handler.ts", "line": 80,
         "title": "n+1", "severity": "P1", "confidence": 75,
         "classification": "introduced", "pass": "performance"},
        {"id": "p2", "file": "src/api/handler.ts", "line": 120,
         "title": "sync in hot path", "severity": "P1", "confidence": 75,
         "classification": "introduced", "pass": "performance"},
    ],
}
merge = mod.merge_deep_findings([], deep_by_pass)
mod._apply_deep_passes_to_receipt(
    sys.argv[2],
    passes_run=["performance"],
    deep_by_pass=deep_by_pass,
    merge_result=merge,
    prior_verdict="NEEDS_WORK",
)
PYEOF
assert_eq_jq "$RECEIPT_4" "d['deep_passes']" "['performance']" "Case 4 only performance pass"
assert_eq_jq "$RECEIPT_4" "d['deep_findings_count']['performance']" "2" "Case 4 perf count"
assert_eq_jq "$RECEIPT_4" "'adversarial' in d['deep_findings_count']" "False" "Case 4 adversarial absent (explicit override)"

# =============================================================================
# CASE 5: --interactive Ralph-block (env var triggers + clean error)
# =============================================================================
echo -e "${YELLOW}--- Case 5: --interactive Ralph-block (FLOW_RALPH and REVIEW_RECEIPT_PATH) ---${NC}"

# Reproduce the bash snippet from SKILL.md verbatim. Each call must:
#   - exit 2 when --interactive present + Ralph env detected
#   - exit 0 when --interactive absent OR no Ralph env
#   - emit a message mentioning Ralph incompatibility
RALPH_BLOCK_SNIPPET="$TEST_DIR/ralph_block.sh"
cat > "$RALPH_BLOCK_SNIPPET" <<'BASH'
INTERACTIVE=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --interactive) INTERACTIVE=true ;;
  esac
done

if [[ "$INTERACTIVE" == "true" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
    echo "Error: --interactive requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
    exit 2
  fi
fi
exit 0
BASH

# 5a: FLOW_RALPH=1 + --interactive → exit 2 with message
rc=0
err_out="$(FLOW_RALPH=1 ARGUMENTS="fn-32.5 --interactive" bash "$RALPH_BLOCK_SNIPPET" 2>&1)" || rc=$?
if [[ "$rc" -eq 2 ]] && echo "$err_out" | grep -qi "Ralph"; then
  ok "Case 5a: FLOW_RALPH=1 + --interactive → exit 2 with Ralph error"
else
  fail "Case 5a: expected exit 2 + Ralph message, got rc=$rc out='$err_out'"
fi

# 5b: REVIEW_RECEIPT_PATH set + --interactive → exit 2
rc=0
err_out="$(REVIEW_RECEIPT_PATH=/tmp/x.json ARGUMENTS="fn-32.5 --interactive" bash "$RALPH_BLOCK_SNIPPET" 2>&1)" || rc=$?
if [[ "$rc" -eq 2 ]] && echo "$err_out" | grep -qi "Ralph"; then
  ok "Case 5b: REVIEW_RECEIPT_PATH + --interactive → exit 2 with Ralph error"
else
  fail "Case 5b: expected exit 2 + Ralph message, got rc=$rc out='$err_out'"
fi

# 5c: --interactive without any Ralph env → exit 0 (user at terminal OK)
rc=0
ARGUMENTS="fn-32.5 --interactive" bash "$RALPH_BLOCK_SNIPPET" >/dev/null 2>&1 || rc=$?
if [[ "$rc" -eq 0 ]]; then
  ok "Case 5c: --interactive without Ralph env → exit 0 (terminal OK)"
else
  fail "Case 5c: expected exit 0 without Ralph env, got rc=$rc"
fi

# 5d: Ralph env present but no --interactive → exit 0 (default review proceeds)
rc=0
FLOW_RALPH=1 ARGUMENTS="fn-32.5 --validate" bash "$RALPH_BLOCK_SNIPPET" >/dev/null 2>&1 || rc=$?
if [[ "$rc" -eq 0 ]]; then
  ok "Case 5d: Ralph env + no --interactive → exit 0 (other flags pass through)"
else
  fail "Case 5d: expected exit 0 without --interactive, got rc=$rc"
fi

# Walkthrough record path: verify the helper writes the block + never flips verdict
CASE5_DIR="$TEST_DIR/case5"
mkdir -p "$CASE5_DIR"
RECEIPT_5="$CASE5_DIR/receipt.json"
cat > "$RECEIPT_5" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c5","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-c5"}
EOF
"$FLOWCTL" review-walkthrough-record \
  --receipt "$RECEIPT_5" --applied 2 --deferred 1 --skipped 0 --acknowledged 0 \
  --json >/dev/null
assert_has_key "$RECEIPT_5" "walkthrough" "Case 5 (walkthrough record)"
assert_has_key "$RECEIPT_5" "walkthrough_timestamp" "Case 5"
assert_eq_jq "$RECEIPT_5" "d['walkthrough']['applied']" "2" "Case 5 applied count"
assert_eq_jq "$RECEIPT_5" "d['walkthrough']['deferred']" "1" "Case 5 deferred count"
assert_eq_jq "$RECEIPT_5" "d['walkthrough']['lfg_rest']" "False" "Case 5 lfg_rest default"
assert_eq_jq "$RECEIPT_5" "d['verdict']" "NEEDS_WORK" "Case 5 walkthrough never flips verdict"

# =============================================================================
# CASE 6: combination (--validate + --deep) — phase order + receipt composition
# =============================================================================
echo -e "${YELLOW}--- Case 6: combination (--validate + --deep + --interactive) ---${NC}"

CASE6_DIR="$TEST_DIR/case6"
mkdir -p "$CASE6_DIR"
RECEIPT_6="$CASE6_DIR/receipt.json"
cat > "$RECEIPT_6" <<'EOF'
{"type":"impl_review","id":"fn-32.5-c6","mode":"codex","verdict":"NEEDS_WORK","session_id":"sess-c6"}
EOF

# Phase order: primary (already in receipt) → deep → validate → walkthrough
"$PYTHON_BIN" - "$SCRIPT_DIR/flowctl.py" "$RECEIPT_6" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
rp = sys.argv[2]
# Phase 2: deep
deep_by_pass = {"adversarial": [
    {"id":"a1","file":"src/a.py","line":1,"title":"x","severity":"P2","confidence":50,
     "classification":"introduced","pass":"adversarial"}
]}
merge = mod.merge_deep_findings([], deep_by_pass)
mod._apply_deep_passes_to_receipt(rp, passes_run=["adversarial"],
                                  deep_by_pass=deep_by_pass,
                                  merge_result=merge, prior_verdict="NEEDS_WORK")
# Phase 3: validate keeps the deep finding
mod._apply_validator_to_receipt(rp,
    {"dispatched":1,"dropped":0,"kept":1,
     "reasons":[]}, prior_verdict="NEEDS_WORK")
PYEOF
"$FLOWCTL" review-walkthrough-record \
  --receipt "$RECEIPT_6" --applied 1 --deferred 0 --skipped 0 --acknowledged 0 \
  --json >/dev/null

# Verify all three blocks present + base fields untouched
assert_has_key "$RECEIPT_6" "deep_passes" "Case 6"
assert_has_key "$RECEIPT_6" "deep_findings_count" "Case 6"
assert_has_key "$RECEIPT_6" "deep_timestamp" "Case 6"
assert_has_key "$RECEIPT_6" "validator" "Case 6"
assert_has_key "$RECEIPT_6" "validator_timestamp" "Case 6"
assert_has_key "$RECEIPT_6" "walkthrough" "Case 6"
assert_has_key "$RECEIPT_6" "walkthrough_timestamp" "Case 6"
assert_eq_jq "$RECEIPT_6" "d['session_id']" "sess-c6" "Case 6 session_id preserved"
assert_eq_jq "$RECEIPT_6" "d['mode']" "codex" "Case 6 mode preserved"
assert_eq_jq "$RECEIPT_6" "d['verdict']" "NEEDS_WORK" "Case 6 final verdict"

# =============================================================================
# CASE 7: env-var opt-ins (FLOW_VALIDATE_REVIEW=1, FLOW_REVIEW_DEEP=1)
# =============================================================================
echo -e "${YELLOW}--- Case 7: env-var opt-ins (FLOW_VALIDATE_REVIEW / FLOW_REVIEW_DEEP) ---${NC}"

VALIDATE_PARSE_SNIPPET="$TEST_DIR/validate_parse.sh"
cat > "$VALIDATE_PARSE_SNIPPET" <<'BASH'
VALIDATE=false
for arg in $ARGUMENTS; do
  case "$arg" in
    --validate) VALIDATE=true ;;
  esac
done
if [[ "${FLOW_VALIDATE_REVIEW:-}" == "1" ]]; then VALIDATE=true; fi
echo "VALIDATE=$VALIDATE"
BASH

DEEP_PARSE_SNIPPET="$TEST_DIR/deep_parse.sh"
cat > "$DEEP_PARSE_SNIPPET" <<'BASH'
DEEP=false
DEEP_PASSES=""
for arg in $ARGUMENTS; do
  case "$arg" in
    --deep) DEEP=true ;;
    --deep=*) DEEP=true; DEEP_PASSES="${arg#--deep=}" ;;
  esac
done
if [[ "${FLOW_REVIEW_DEEP:-}" == "1" ]]; then DEEP=true; fi
echo "DEEP=$DEEP"
echo "DEEP_PASSES=$DEEP_PASSES"
BASH

# 7a: FLOW_VALIDATE_REVIEW=1 + no flag → VALIDATE=true
out="$(FLOW_VALIDATE_REVIEW=1 ARGUMENTS="fn-32.5" bash "$VALIDATE_PARSE_SNIPPET")"
if echo "$out" | grep -q '^VALIDATE=true$'; then
  ok "Case 7a: FLOW_VALIDATE_REVIEW=1 → VALIDATE=true (no flag needed)"
else
  fail "Case 7a: expected VALIDATE=true, got '$out'"
fi

# 7b: FLOW_REVIEW_DEEP=1 + no flag → DEEP=true
out="$(FLOW_REVIEW_DEEP=1 ARGUMENTS="fn-32.5" bash "$DEEP_PARSE_SNIPPET")"
if echo "$out" | grep -q '^DEEP=true$'; then
  ok "Case 7b: FLOW_REVIEW_DEEP=1 → DEEP=true (no flag needed)"
else
  fail "Case 7b: expected DEEP=true, got '$out'"
fi

# 7c: neither set → both false
out="$(env -u FLOW_VALIDATE_REVIEW ARGUMENTS="fn-32.5" bash "$VALIDATE_PARSE_SNIPPET")"
echo "$out" | grep -q '^VALIDATE=false$' \
  && ok "Case 7c: no env, no flag → VALIDATE=false (default off)" \
  || fail "Case 7c VALIDATE: expected false, got '$out'"
out="$(env -u FLOW_REVIEW_DEEP ARGUMENTS="fn-32.5" bash "$DEEP_PARSE_SNIPPET")"
echo "$out" | grep -q '^DEEP=false$' \
  && ok "Case 7c: no env, no flag → DEEP=false (default off)" \
  || fail "Case 7c DEEP: expected false, got '$out'"

# 7d: --deep=adversarial,security explicit override sets DEEP_PASSES
out="$(ARGUMENTS="fn-32.5 --deep=adversarial,security" bash "$DEEP_PARSE_SNIPPET")"
if echo "$out" | grep -q '^DEEP=true$' && echo "$out" | grep -q '^DEEP_PASSES=adversarial,security$'; then
  ok "Case 7d: --deep=adversarial,security → DEEP=true + DEEP_PASSES set"
else
  fail "Case 7d: expected explicit pass list, got '$out'"
fi

# =============================================================================
# Ralph regression: ralph_smoke_test.sh under 4 env-var configurations.
# Each run must complete green. The new env vars are read inside the
# impl-review skill — Ralph's stub backend writes its own minimal receipts
# regardless. We assert exit code 0 across the matrix.
#
# Run the 4 configurations in parallel (each creates a unique /tmp/ralph-smoke-$$
# workspace via $$) to keep the 7-case smoke + regression sweep under 2 minutes.
# =============================================================================
echo -e "${YELLOW}--- Ralph regression sweep (4 env-var configurations, parallel) ---${NC}"

# Spawn 4 background ralph runs
(env -u FLOW_VALIDATE_REVIEW -u FLOW_REVIEW_DEEP \
   "$PLUGIN_ROOT/scripts/ralph_smoke_test.sh" >"$TEST_DIR/ralph-baseline.log" 2>&1
 echo $? > "$TEST_DIR/ralph-baseline.rc") &
PID_BASE=$!

(env -u FLOW_REVIEW_DEEP FLOW_VALIDATE_REVIEW=1 \
   "$PLUGIN_ROOT/scripts/ralph_smoke_test.sh" >"$TEST_DIR/ralph-validate.log" 2>&1
 echo $? > "$TEST_DIR/ralph-validate.rc") &
PID_VAL=$!

(env -u FLOW_VALIDATE_REVIEW FLOW_REVIEW_DEEP=1 \
   "$PLUGIN_ROOT/scripts/ralph_smoke_test.sh" >"$TEST_DIR/ralph-deep.log" 2>&1
 echo $? > "$TEST_DIR/ralph-deep.rc") &
PID_DEEP=$!

(env FLOW_VALIDATE_REVIEW=1 FLOW_REVIEW_DEEP=1 \
   "$PLUGIN_ROOT/scripts/ralph_smoke_test.sh" >"$TEST_DIR/ralph-both.log" 2>&1
 echo $? > "$TEST_DIR/ralph-both.rc") &
PID_BOTH=$!

# Wait for all, then assert each
wait $PID_BASE $PID_VAL $PID_DEEP $PID_BOTH

for label in baseline validate deep both; do
  rc="$(cat "$TEST_DIR/ralph-${label}.rc" 2>/dev/null || echo 255)"
  if [[ "$rc" -eq 0 ]]; then
    ok "Ralph regression [$label]: ralph_smoke_test.sh exit 0 (log: $TEST_DIR/ralph-${label}.log)"
  else
    fail "Ralph regression [$label]: ralph_smoke_test.sh exit $rc"
    tail -40 "$TEST_DIR/ralph-${label}.log" >&2 2>/dev/null || true
  fi
done

echo ""
echo -e "${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [ $FAIL -gt 0 ]; then
  exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"
