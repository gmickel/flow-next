#!/usr/bin/env bash
# fn-34-flow-nextaudit-agent-native-memory.3
# Smoke tests for /flow-next:audit flowctl plumbing (Task 2 surface only).
#
# Skills aren't unit-testable — the orchestrator skill is verified by manual
# invocation. This smoke covers the deterministic persistence layer:
#
#   1.  mark-stale roundtrip (status + last_audited + audit_notes)
#   2.  mark-stale --audited-by appends auditor identifier
#   3.  mark-stale --json output shape ({id, path, status, last_audited, audit_notes})
#   4.  mark-stale missing --reason errors (rc 2)
#   5.  mark-stale idempotent (re-mark replaces audit_notes, restamps last_audited)
#   6.  mark-fresh roundtrip (clears status + audit_notes, stamps last_audited)
#   7.  mark-fresh on never-stale entry no-ops cleanly (just stamps last_audited)
#   8.  search default --status active excludes stale entries
#   9.  search --status stale returns only stale entries
#  10.  search --status all returns both
#  11.  list --status stale (existing fn-30 path) still works (regression)
#  12.  schema validation accepts last_audited + audit_notes (round-trip via memory read)
#  13.  Ralph regression — mark-stale + mark-fresh + search work under FLOW_RALPH=1
#
# Pure shell + Python harness — no LLM invocations. Targets <30s runtime.
# Pattern follows prospect_smoke_test.sh (fn-33.6).
#
# Run from any directory other than the plugin repo root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FLOWCTL="$SCRIPT_DIR/flowctl"

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

TEST_DIR="/tmp/audit-smoke-$$"
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
  command -v trash >/dev/null 2>&1 && trash "$TEST_DIR" 2>/dev/null && return
  # Fallback: per-subtree removal (avoid recursive rm). Best-effort.
  find "$TEST_DIR" -depth -type f -exec rm -f {} \; 2>/dev/null || true
  find "$TEST_DIR" -depth -type d -exec rmdir {} \; 2>/dev/null || true
}
trap cleanup EXIT

ok()   { echo -e "${GREEN}PASS${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}FAIL${NC} $1"; FAIL=$((FAIL + 1)); }

assert_rc() {
  local expected="$1" actual="$2" label="$3"
  if [[ "$actual" -eq "$expected" ]]; then
    ok "$label (rc=$actual)"
  else
    fail "$label (expected rc=$expected, got rc=$actual)"
  fi
}

assert_grep() {
  local needle="$1" haystack="$2" label="$3"
  if printf '%s\n' "$haystack" | grep -qF -- "$needle"; then
    ok "$label  (found: '$needle')"
  else
    fail "$label  (missing: '$needle')"
    {
      echo "--- haystack head ---"
      printf '%s\n' "$haystack" | sed -n '1,20p'
      echo "---"
    } >&2 || true
  fi
}

assert_grep_re() {
  local pattern="$1" haystack="$2" label="$3"
  if printf '%s\n' "$haystack" | grep -qE -- "$pattern"; then
    ok "$label  (matched: /$pattern/)"
  else
    fail "$label  (no match: /$pattern/)"
    {
      echo "--- haystack head ---"
      printf '%s\n' "$haystack" | sed -n '1,20p'
      echo "---"
    } >&2 || true
  fi
}

# JSON value extraction via python.
json_get() {
  local file="$1" expr="$2"
  "$PYTHON_BIN" -c "import json; d=json.load(open('$file')); print($expr)" 2>&1 || true
}

assert_eq_jq() {
  local file="$1" expr="$2" expected="$3" label="$4"
  local actual
  actual="$(json_get "$file" "$expr")"
  if [[ "$actual" == "$expected" ]]; then
    ok "$label  ($expr == $expected)"
  else
    fail "$label  ($expr expected $expected, got $actual)"
    cat "$file" >&2 2>/dev/null || true
  fi
}

# init: minimal repo with .flow/ + memory enabled + tree initialized.
init_test_repo() {
  local dir="$1"
  mkdir -p "$dir"
  ( cd "$dir" && \
    git init -q && \
    git config user.email "audit-smoke@example.com" && \
    git config user.name "Audit Smoke" && \
    git checkout -b main >/dev/null 2>&1 || true
    git commit --allow-empty -m "init" -q
    "$FLOWCTL" init --json >/dev/null
    "$FLOWCTL" config set memory.enabled true --json >/dev/null
    "$FLOWCTL" memory init --json >/dev/null
  )
}

# Seed an entry; returns the entry id on stdout. Sixth arg = "no-overlap"
# bypasses overlap detection (useful when seeding deliberately-similar
# entries — e.g. two auth-related runtime-errors that should remain distinct).
seed_entry() {
  local dir="$1" track="$2" cat="$3" title="$4" module="${5:-}" tags="${6:-}" overlap="${7:-}"
  local args=(--track "$track" --category "$cat" --title "$title" --json)
  if [[ -n "$module" ]]; then args+=(--module "$module"); fi
  if [[ -n "$tags" ]];   then args+=(--tags "$tags"); fi
  if [[ "$overlap" == "no-overlap" ]]; then args+=(--no-overlap-check); fi
  ( cd "$dir" && "$FLOWCTL" memory add "${args[@]}" 2>/dev/null ) \
    | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["entry_id"])'
}

echo -e "${YELLOW}=== audit smoke tests (fn-34.3) ===${NC}"
echo "Plugin root: $PLUGIN_ROOT"
echo "Test dir:    $TEST_DIR"
echo

mkdir -p "$TEST_DIR"
TODAY="$(date -u +%Y-%m-%d)"

REPO="$TEST_DIR/repo"
init_test_repo "$REPO"

# =============================================================================
# Seed three entries
# =============================================================================
ENTRY_A="$(seed_entry "$REPO" bug runtime-errors "Null deref in auth middleware" "src/auth.ts" "auth,nullcheck")"
ENTRY_B="$(seed_entry "$REPO" knowledge conventions "Prefer pnpm over npm" "" "pnpm,tooling")"
ENTRY_C="$(seed_entry "$REPO" bug build-errors "Webpack OOM on monorepo build" "build/webpack.config.js" "webpack,oom")"

[[ -n "$ENTRY_A" ]] && ok "seed: bug/runtime-errors entry created ($ENTRY_A)" || fail "seed entry A failed"
[[ -n "$ENTRY_B" ]] && ok "seed: knowledge/conventions entry created ($ENTRY_B)" || fail "seed entry B failed"
[[ -n "$ENTRY_C" ]] && ok "seed: bug/build-errors entry created ($ENTRY_C)" || fail "seed entry C failed"

# =============================================================================
# CASE 1: mark-stale roundtrip
# =============================================================================
echo -e "${YELLOW}--- Case 1: mark-stale roundtrip ---${NC}"

# Snapshot body before mark-stale to verify it stays untouched.
BODY_BEFORE="$TEST_DIR/case1-body-before.txt"
( cd "$REPO" && "$FLOWCTL" memory read "$ENTRY_A" --json 2>/dev/null ) \
  | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin).get("body",""))' \
  > "$BODY_BEFORE"

( cd "$REPO" && "$FLOWCTL" memory mark-stale "$ENTRY_A" --reason "module renamed" >/dev/null )

READ_JSON="$TEST_DIR/case1-read.json"
( cd "$REPO" && "$FLOWCTL" memory read "$ENTRY_A" --json > "$READ_JSON" ) \
  || fail "Case 1: memory read $ENTRY_A failed"

assert_eq_jq "$READ_JSON" "d['frontmatter']['status']" "stale" \
  "Case 1: status=stale after mark-stale"
assert_eq_jq "$READ_JSON" "d['frontmatter']['last_audited']" "$TODAY" \
  "Case 1: last_audited stamped to today"
assert_eq_jq "$READ_JSON" "d['frontmatter']['audit_notes']" "module renamed" \
  "Case 1: audit_notes carries --reason verbatim"

BODY_AFTER="$TEST_DIR/case1-body-after.txt"
"$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("body",""))' "$READ_JSON" \
  > "$BODY_AFTER"

if diff -q "$BODY_BEFORE" "$BODY_AFTER" >/dev/null 2>&1; then
  ok "Case 1: body unchanged by mark-stale"
else
  fail "Case 1: body diverged after mark-stale"
fi

# =============================================================================
# CASE 2: mark-stale with --audited-by
# =============================================================================
echo -e "${YELLOW}--- Case 2: mark-stale --audited-by ---${NC}"

( cd "$REPO" && "$FLOWCTL" memory mark-stale "$ENTRY_A" \
    --reason "module renamed in PR #123" \
    --audited-by "/flow-next:audit" >/dev/null )

READ_JSON="$TEST_DIR/case2-read.json"
( cd "$REPO" && "$FLOWCTL" memory read "$ENTRY_A" --json > "$READ_JSON" )

NOTES="$(json_get "$READ_JSON" "d['frontmatter']['audit_notes']")"
assert_grep "module renamed in PR #123" "$NOTES" \
  "Case 2: audit_notes contains --reason text"
assert_grep "audited-by: /flow-next:audit" "$NOTES" \
  "Case 2: audit_notes contains '(audited-by: …)' suffix"

# =============================================================================
# CASE 3: mark-stale --json output shape
# =============================================================================
echo -e "${YELLOW}--- Case 3: mark-stale --json shape ---${NC}"

# Use ENTRY_C so we don't repeatedly bounce ENTRY_A.
JSON_OUT="$TEST_DIR/case3-mark-stale.json"
( cd "$REPO" && "$FLOWCTL" memory mark-stale "$ENTRY_C" --reason "build moved off webpack" --json > "$JSON_OUT" ) \
  || fail "Case 3: mark-stale --json invocation failed"

# Required keys per fn-34.2 ship: id, path, status, last_audited, audit_notes
for key in id path status last_audited audit_notes; do
  if "$PYTHON_BIN" -c "import json,sys; sys.exit(0 if '$key' in json.load(open('$JSON_OUT')) else 1)"; then
    ok "Case 3: JSON has key '$key'"
  else
    fail "Case 3: JSON missing key '$key'"
  fi
done

assert_eq_jq "$JSON_OUT" "d['status']" "stale" "Case 3: status=stale in JSON"
assert_eq_jq "$JSON_OUT" "d['last_audited']" "$TODAY" "Case 3: last_audited=today in JSON"
assert_eq_jq "$JSON_OUT" "d['id']" "$ENTRY_C" "Case 3: id roundtrip"

# json_output() helper wraps every flowctl JSON payload with `success: true`;
# audit-skill consumers should treat it as additive metadata.
assert_eq_jq "$JSON_OUT" "d['success']" "True" "Case 3: success=true wrapper present"

# =============================================================================
# CASE 4: mark-stale missing --reason errors
# =============================================================================
echo -e "${YELLOW}--- Case 4: mark-stale missing --reason errors ---${NC}"

rc=0
err="$( cd "$REPO" && "$FLOWCTL" memory mark-stale "$ENTRY_B" 2>&1 1>/dev/null )" || rc=$?
if [[ "$rc" -ne 0 ]]; then
  ok "Case 4: missing --reason returns non-zero (rc=$rc)"
else
  fail "Case 4: missing --reason unexpectedly succeeded"
fi
# argparse rejects with "required" on its own; flowctl validates non-empty
# reason after that. Either path satisfies the contract.
assert_grep_re "(required|reason)" "$err" "Case 4: stderr mentions 'required' or 'reason'"

# =============================================================================
# CASE 5: mark-stale idempotent (re-mark replaces audit_notes, restamps date)
# =============================================================================
echo -e "${YELLOW}--- Case 5: mark-stale idempotent ---${NC}"

# ENTRY_A is already stale from Case 1+2. Re-mark with a different reason.
( cd "$REPO" && "$FLOWCTL" memory mark-stale "$ENTRY_A" --reason "second audit pass" >/dev/null ) \
  || fail "Case 5: second mark-stale failed"

READ_JSON="$TEST_DIR/case5-read.json"
( cd "$REPO" && "$FLOWCTL" memory read "$ENTRY_A" --json > "$READ_JSON" )

assert_eq_jq "$READ_JSON" "d['frontmatter']['audit_notes']" "second audit pass" \
  "Case 5: audit_notes replaced (not appended)"
assert_eq_jq "$READ_JSON" "d['frontmatter']['status']" "stale" \
  "Case 5: status still stale after re-mark"
assert_eq_jq "$READ_JSON" "d['frontmatter']['last_audited']" "$TODAY" \
  "Case 5: last_audited restamped"

# =============================================================================
# CASE 6: mark-fresh roundtrip
# =============================================================================
echo -e "${YELLOW}--- Case 6: mark-fresh roundtrip ---${NC}"

( cd "$REPO" && "$FLOWCTL" memory mark-fresh "$ENTRY_A" >/dev/null )

READ_JSON="$TEST_DIR/case6-read.json"
( cd "$REPO" && "$FLOWCTL" memory read "$ENTRY_A" --json > "$READ_JSON" )

# status field is dropped (active is implicit default); read surfaces "active".
STATUS="$(json_get "$READ_JSON" "d['frontmatter'].get('status', 'active')")"
if [[ "$STATUS" == "active" ]]; then
  ok "Case 6: status=active after mark-fresh (or field dropped)"
else
  fail "Case 6: expected status=active, got $STATUS"
fi

# audit_notes cleared (or empty)
NOTES="$(json_get "$READ_JSON" "d['frontmatter'].get('audit_notes', '')")"
if [[ -z "$NOTES" ]]; then
  ok "Case 6: audit_notes cleared"
else
  fail "Case 6: audit_notes still set: '$NOTES'"
fi

assert_eq_jq "$READ_JSON" "d['frontmatter']['last_audited']" "$TODAY" \
  "Case 6: last_audited stamped on mark-fresh"

# =============================================================================
# CASE 7: mark-fresh on never-stale entry no-ops cleanly
# =============================================================================
echo -e "${YELLOW}--- Case 7: mark-fresh on never-stale entry ---${NC}"

# ENTRY_B was never marked stale.
rc=0
( cd "$REPO" && "$FLOWCTL" memory mark-fresh "$ENTRY_B" >/dev/null ) || rc=$?
assert_rc 0 "$rc" "Case 7: mark-fresh on active entry returns rc=0"

READ_JSON="$TEST_DIR/case7-read.json"
( cd "$REPO" && "$FLOWCTL" memory read "$ENTRY_B" --json > "$READ_JSON" )

assert_eq_jq "$READ_JSON" "d['frontmatter']['last_audited']" "$TODAY" \
  "Case 7: mark-fresh stamps last_audited even on already-active entry"
STATUS="$(json_get "$READ_JSON" "d['frontmatter'].get('status', 'active')")"
if [[ "$STATUS" == "active" ]]; then
  ok "Case 7: status remains active"
else
  fail "Case 7: unexpected status=$STATUS"
fi

# =============================================================================
# CASE 8: search default --status active excludes stale
# =============================================================================
echo -e "${YELLOW}--- Case 8: search default excludes stale ---${NC}"

# State at this point:
#   ENTRY_A — fresh (mark-fresh applied)
#   ENTRY_B — active (never stale)
#   ENTRY_C — stale (Case 3)

SEARCH_JSON="$TEST_DIR/case8-search.json"
( cd "$REPO" && "$FLOWCTL" memory search webpack --json > "$SEARCH_JSON" ) \
  || fail "Case 8: search invocation failed"

# Stale ENTRY_C should NOT appear in default search.
if "$PYTHON_BIN" -c "
import json,sys
d=json.load(open('$SEARCH_JSON'))
matches = d.get('matches', d.get('results', []))
ids = [m.get('entry_id', m.get('id','')) for m in matches]
sys.exit(0 if '$ENTRY_C' not in ids else 1)
"; then
  ok "Case 8: stale entry $ENTRY_C absent from default search"
else
  fail "Case 8: stale entry leaked into default search"
  cat "$SEARCH_JSON" >&2 || true
fi

# =============================================================================
# CASE 9: search --status stale returns only stale
# =============================================================================
echo -e "${YELLOW}--- Case 9: search --status stale ---${NC}"

SEARCH_JSON="$TEST_DIR/case9-search.json"
( cd "$REPO" && "$FLOWCTL" memory search webpack --status stale --json > "$SEARCH_JSON" ) \
  || fail "Case 9: search --status stale invocation failed"

if "$PYTHON_BIN" -c "
import json,sys
d=json.load(open('$SEARCH_JSON'))
matches = d.get('matches', d.get('results', []))
ids = [m.get('entry_id', m.get('id','')) for m in matches]
# Only stale entry C should appear; A is fresh, B doesn't match 'webpack'.
sys.exit(0 if '$ENTRY_C' in ids and '$ENTRY_A' not in ids else 1)
"; then
  ok "Case 9: --status stale surfaces $ENTRY_C only"
else
  fail "Case 9: --status stale unexpected results"
  cat "$SEARCH_JSON" >&2 || true
fi

# =============================================================================
# CASE 10: search --status all returns both
# =============================================================================
echo -e "${YELLOW}--- Case 10: search --status all ---${NC}"

# Make ENTRY_A stale again so a single 'auth' query has both an active and a
# stale candidate to disambiguate (B doesn't match 'auth').
( cd "$REPO" && "$FLOWCTL" memory mark-stale "$ENTRY_A" --reason "context drift" >/dev/null )

# Add a fresh entry that ALSO matches 'auth' so we can verify default vs all.
# Use --no-overlap-check: title/module/tags are similar enough to ENTRY_A that
# overlap detection would update A in place (returning the same id) instead
# of creating a distinct second entry.
ENTRY_D="$(seed_entry "$REPO" bug runtime-errors "Auth callback never resolves on logout" "src/auth.ts" "auth,callback" no-overlap)"
[[ -n "$ENTRY_D" ]] && ok "seed: extra fresh auth entry created ($ENTRY_D)" || fail "Case 10: seed extra entry failed"

# default — only D
SEARCH_JSON="$TEST_DIR/case10-default.json"
( cd "$REPO" && "$FLOWCTL" memory search auth --json > "$SEARCH_JSON" )
if "$PYTHON_BIN" -c "
import json,sys
d=json.load(open('$SEARCH_JSON'))
matches = d.get('matches', d.get('results', []))
ids = [m.get('entry_id', m.get('id','')) for m in matches]
sys.exit(0 if '$ENTRY_D' in ids and '$ENTRY_A' not in ids else 1)
"; then
  ok "Case 10: default search surfaces fresh entry, hides stale"
else
  fail "Case 10: default search unexpected results"
  cat "$SEARCH_JSON" >&2 || true
fi

# --status all — both A and D
SEARCH_JSON="$TEST_DIR/case10-all.json"
( cd "$REPO" && "$FLOWCTL" memory search auth --status all --json > "$SEARCH_JSON" )
if "$PYTHON_BIN" -c "
import json,sys
d=json.load(open('$SEARCH_JSON'))
matches = d.get('matches', d.get('results', []))
ids = [m.get('entry_id', m.get('id','')) for m in matches]
sys.exit(0 if '$ENTRY_D' in ids and '$ENTRY_A' in ids else 1)
"; then
  ok "Case 10: --status all surfaces both fresh and stale"
else
  fail "Case 10: --status all missing entries"
  cat "$SEARCH_JSON" >&2 || true
fi

# =============================================================================
# CASE 11: list --status stale (existing fn-30 behavior)
# =============================================================================
echo -e "${YELLOW}--- Case 11: list --status stale (regression) ---${NC}"

LIST_JSON="$TEST_DIR/case11-list.json"
( cd "$REPO" && "$FLOWCTL" memory list --status stale --json > "$LIST_JSON" )

# A and C are stale at this point.
if "$PYTHON_BIN" -c "
import json,sys
d=json.load(open('$LIST_JSON'))
items = d.get('entries', d.get('matches', []))
ids = [m.get('entry_id', m.get('id','')) for m in items]
sys.exit(0 if '$ENTRY_A' in ids and '$ENTRY_C' in ids else 1)
"; then
  ok "Case 11: list --status stale surfaces both stale entries"
else
  fail "Case 11: list --status stale missing expected entries"
  cat "$LIST_JSON" >&2 || true
fi

# =============================================================================
# CASE 12: schema validation accepts last_audited + audit_notes
# =============================================================================
echo -e "${YELLOW}--- Case 12: schema accepts audit fields ---${NC}"

# Write a hand-crafted entry with both fields and verify memory read parses it.
HAND_PATH="$REPO/.flow/memory/knowledge/conventions/hand-crafted-${TODAY}.md"
cat > "$HAND_PATH" <<EOF
---
title: Hand-crafted entry with audit fields
date: $TODAY
track: knowledge
category: conventions
last_audited: "$TODAY"
audit_notes: hand-rolled smoke entry
---

Body content.
EOF

READ_JSON="$TEST_DIR/case12-read.json"
rc=0
( cd "$REPO" && "$FLOWCTL" memory read "knowledge/conventions/hand-crafted-${TODAY}" --json > "$READ_JSON" 2>&1 ) || rc=$?
assert_rc 0 "$rc" "Case 12: memory read on hand-crafted entry succeeds"
assert_eq_jq "$READ_JSON" "d['frontmatter']['last_audited']" "$TODAY" \
  "Case 12: last_audited round-trips through validator"
assert_eq_jq "$READ_JSON" "d['frontmatter']['audit_notes']" "hand-rolled smoke entry" \
  "Case 12: audit_notes round-trips through validator"

# =============================================================================
# CASE 13: Ralph regression — plumbing works under FLOW_RALPH=1
# =============================================================================
echo -e "${YELLOW}--- Case 13: Ralph regression (plumbing not gated) ---${NC}"

# Spec is explicit: skill is Ralph-aware, plumbing is not. mark-stale /
# mark-fresh / search must run cleanly under FLOW_RALPH=1 because Ralph's
# auto-capture path calls mark-stale on conflict.
rc=0
( cd "$REPO" && FLOW_RALPH=1 "$FLOWCTL" memory mark-stale "$ENTRY_B" --reason "ralph-mode test" >/dev/null 2>&1 ) || rc=$?
assert_rc 0 "$rc" "Case 13a: mark-stale under FLOW_RALPH=1 returns rc=0"

rc=0
( cd "$REPO" && FLOW_RALPH=1 "$FLOWCTL" memory mark-fresh "$ENTRY_B" >/dev/null 2>&1 ) || rc=$?
assert_rc 0 "$rc" "Case 13b: mark-fresh under FLOW_RALPH=1 returns rc=0"

rc=0
( cd "$REPO" && FLOW_RALPH=1 "$FLOWCTL" memory search auth --status all --json >/dev/null 2>&1 ) || rc=$?
assert_rc 0 "$rc" "Case 13c: search --status all under FLOW_RALPH=1 returns rc=0"

# =============================================================================
# Results
# =============================================================================
echo
echo -e "${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi

echo -e "${GREEN}All audit smoke tests passed!${NC}"
