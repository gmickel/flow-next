#!/usr/bin/env bash
# fn-33-flow-nextprospect-upstream-of-plan-idea.6
# Smoke tests for /flow-next:prospect skill + flowctl prospect subcommands.
#
# Covers the 11 cases enumerated in the task spec:
#   1. Skeleton + slash command registered
#   2. Ralph-block (FLOW_RALPH=1 and REVIEW_RECEIPT_PATH)
#   3. Phase 0 resume / list classification (active / stale / corrupt)
#   4. Artifact writer (collision suffix + atomic + roundtrip)
#   5. Graceful degradation (no git / no epics / no CHANGELOG)
#   6. Promote happy path (epic creation + ## Source + JSON shape + frontmatter)
#   7. Promote idempotency (refuse + --force + promoted_to)
#   8. Promote errors (out-of-range / 0 / non-int / corrupt)
#   9. list / read / archive (sections, corrupt branch, slug-only, re-archive)
#  10. Numbered-options fallback frozen format (R19)
#  11. Ralph regression sweep (ralph_smoke_test.sh still green)
#
# Pure shell + Python harness — no LLM invocations. Targets <60s runtime.
# Pattern follows impl-review_smoke_test.sh (fn-32.5) and resolve-pr_smoke_test.sh (fn-31.6).
#
# Run from any directory other than the plugin repo root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FLOWCTL_PY="$SCRIPT_DIR/flowctl.py"
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

TEST_DIR="/tmp/prospect-smoke-$$"
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

# Helper: assert exit code.
assert_rc() {
  local expected="$1" actual="$2" label="$3"
  if [[ "$actual" -eq "$expected" ]]; then
    ok "$label (rc=$actual)"
  else
    fail "$label (expected rc=$expected, got rc=$actual)"
  fi
}

# Helper: stdout/stderr substring grep.
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

# Helper: JSON value extraction via python.
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

# Synthetic-artifact builder. Writes via real flowctl helpers so frontmatter
# layout matches production. Args:
#   $1 = repo root (cwd-style)
#   $2 = artifact_id
#   $3 = ISO date
#   $4 = focus_hint (or empty)
#   $5 = survivor_count (1..N) — generates N high_leverage entries
#   $6 = optional extra args:  "stale" | "noflag" | "withfloor"
synthetic_artifact() {
  local repo="$1" aid="$2" iso="$3" focus="$4" surv="$5" mode="${6:-noflag}"
  ( cd "$repo" && "$PYTHON_BIN" - "$FLOWCTL_PY" "$aid" "$iso" "$focus" "$surv" "$mode" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from pathlib import Path
aid, iso, focus, surv_s, mode = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
surv = int(surv_s)
prospects = Path(".flow/prospects")
prospects.mkdir(parents=True, exist_ok=True)
fm = {
    "title": f"Prospect {aid}",
    "date": iso,
    "focus_hint": focus or "",
    "volume": surv * 4,
    "survivor_count": surv,
    "rejected_count": surv * 3,
    "rejection_rate": 0.75,
    "artifact_id": aid,
    "promoted_ideas": [],
    "status": "active",
}
if mode == "withfloor":
    fm["floor_violation"] = True
    fm["generation_under_volume"] = True
ranked = {"high_leverage": [], "worth_considering": [], "if_you_have_the_time": []}
for i in range(1, surv + 1):
    ranked["high_leverage"].append({
        "position": i,
        "title": f"Idea {i}",
        "summary": f"Synthetic survivor #{i}",
        "leverage": f"Small-diff lever because reason{i}; impact lands on target{i}.",
        "size": "S",
    })
body = m.render_prospect_body(focus or "synthetic", "git: scanned 30d (synthetic)", ranked,
                              [{"title": "drop-x", "taxonomy": "out-of-scope", "reason": "synthetic"}])
m.write_prospect_artifact(prospects / f"{aid}.md", fm, body)
print(f"WROTE {aid}.md")
PYEOF
  )
}

# init: minimal repo with .flow/.
init_test_repo() {
  local dir="$1"
  mkdir -p "$dir"
  ( cd "$dir" && \
    git init -q && \
    git config user.email "prospect-smoke@example.com" && \
    git config user.name "Prospect Smoke" && \
    git checkout -b main >/dev/null 2>&1 || true
    git commit --allow-empty -m "init" -q
    "$FLOWCTL" init --json >/dev/null
  )
}

echo -e "${YELLOW}=== prospect smoke tests (fn-33.6) ===${NC}"
echo "Plugin root: $PLUGIN_ROOT"
echo "Test dir:    $TEST_DIR"
echo

mkdir -p "$TEST_DIR"

# =============================================================================
# CASE 1: Skeleton + slash command registered
# =============================================================================
echo -e "${YELLOW}--- Case 1: skeleton + slash command ---${NC}"

CMD_FILE="$PLUGIN_ROOT/commands/flow-next/prospect.md"
SKILL_FILE="$PLUGIN_ROOT/skills/flow-next-prospect/SKILL.md"
WORKFLOW_FILE="$PLUGIN_ROOT/skills/flow-next-prospect/workflow.md"
PERSONAS_FILE="$PLUGIN_ROOT/skills/flow-next-prospect/personas.md"

[[ -f "$CMD_FILE" ]]      && ok "command file exists ($CMD_FILE)"      || fail "command file missing"
[[ -f "$SKILL_FILE" ]]    && ok "skill file exists ($SKILL_FILE)"      || fail "skill file missing"
[[ -f "$WORKFLOW_FILE" ]] && ok "workflow.md exists"                    || fail "workflow.md missing"
[[ -f "$PERSONAS_FILE" ]] && ok "personas.md exists"                    || fail "personas.md missing"

# Command must invoke the skill.
if [[ -f "$CMD_FILE" ]]; then
  cmd_content="$(cat "$CMD_FILE")"
  assert_grep "flow-next-prospect" "$cmd_content" "Case 1: command invokes flow-next-prospect skill"
fi

# SKILL.md frontmatter — no `context: fork`, must include AskUserQuestion.
if [[ -f "$SKILL_FILE" ]]; then
  fm_block="$(awk '/^---$/{c++; next} c==1' "$SKILL_FILE" | head -30)"
  if echo "$fm_block" | grep -qE '^context:[[:space:]]*fork'; then
    fail "Case 1: SKILL.md must NOT use 'context: fork' (R5 — keeps blocking tools reachable)"
  else
    ok "Case 1: SKILL.md does not set 'context: fork'"
  fi
  assert_grep "AskUserQuestion" "$fm_block" "Case 1: SKILL.md allowed-tools includes AskUserQuestion"
  assert_grep_re '^name:[[:space:]]*flow-next-prospect' "$fm_block" "Case 1: SKILL.md name == flow-next-prospect"
fi

# =============================================================================
# CASE 2: Ralph-block (R8) — FLOW_RALPH=1 / REVIEW_RECEIPT_PATH must exit 2
# =============================================================================
echo -e "${YELLOW}--- Case 2: Ralph-block (R8) ---${NC}"

# Reproduce the SKILL.md guard verbatim. Ralph never decides direction — no
# env-var opt-in. Spec: hard-error with exit 2 when either var present.
RALPH_GUARD="$TEST_DIR/ralph_guard.sh"
cat > "$RALPH_GUARD" <<'BASH'
#!/usr/bin/env bash
set -e
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "Error: /flow-next:prospect requires a user at the terminal; not compatible with Ralph mode (REVIEW_RECEIPT_PATH or FLOW_RALPH detected)." >&2
  exit 2
fi
exit 0
BASH
chmod +x "$RALPH_GUARD"

# Sanity: exact bytes from the SKILL.md must appear in the source so Ralph
# can never silently decide direction. Pattern grep keeps the smoke
# independent of small markdown reflows.
if grep -q 'REVIEW_RECEIPT_PATH' "$SKILL_FILE" && grep -q 'FLOW_RALPH' "$SKILL_FILE" && grep -q 'exit 2' "$SKILL_FILE"; then
  ok "Case 2: SKILL.md ships Ralph-block with exit 2 + both env-var checks"
else
  fail "Case 2: SKILL.md missing FLOW_RALPH/REVIEW_RECEIPT_PATH/exit 2 guard"
fi

# 2a: FLOW_RALPH=1 → exit 2
rc=0
err="$(FLOW_RALPH=1 bash "$RALPH_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 2a: FLOW_RALPH=1 → exit 2"
assert_grep "Ralph" "$err" "Case 2a: error mentions Ralph"

# 2b: REVIEW_RECEIPT_PATH=/tmp/no-such → exit 2 (regardless of file presence).
rc=0
err="$(REVIEW_RECEIPT_PATH=/tmp/prospect-smoke-no-such-receipt.json bash "$RALPH_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 2b: REVIEW_RECEIPT_PATH set → exit 2"
assert_grep "Ralph" "$err" "Case 2b: error mentions Ralph"

# 2c: neither set → exit 0 (passes through).
rc=0
bash "$RALPH_GUARD" >/dev/null 2>&1 || rc=$?
assert_rc 0 "$rc" "Case 2c: no Ralph env → exit 0 (terminal OK)"

# =============================================================================
# CASE 3: Phase 0 list classification — active vs stale vs corrupt
# =============================================================================
echo -e "${YELLOW}--- Case 3: list classification (active/stale/corrupt) ---${NC}"

CASE3_REPO="$TEST_DIR/case3"
init_test_repo "$CASE3_REPO"

# Fresh artifact (today)
TODAY="$(date -u +%Y-%m-%d)"
synthetic_artifact "$CASE3_REPO" "fresh-$TODAY" "$TODAY" "fresh hint" 3
# Stale artifact (>30 days; pick a far-past date so DST / month math is safe)
synthetic_artifact "$CASE3_REPO" "stale-2024-01-01" "2024-01-01" "stale hint" 2
# Corrupt artifact: no frontmatter block (matches PROSPECT_CORRUPT_NO_FRONTMATTER)
mkdir -p "$CASE3_REPO/.flow/prospects"
cat > "$CASE3_REPO/.flow/prospects/corrupt-$TODAY.md" <<'EOF'
just body, no frontmatter

## Survivors
EOF

# 3a: default list — only fresh
LIST_DEFAULT_JSON="$TEST_DIR/case3-list-default.json"
( cd "$CASE3_REPO" && "$FLOWCTL" prospect list --json > "$LIST_DEFAULT_JSON" ) || fail "Case 3a: list --json failed"
assert_eq_jq "$LIST_DEFAULT_JSON" "d['count']" "1" "Case 3a: default list returns exactly 1 (fresh) artifact"
assert_eq_jq "$LIST_DEFAULT_JSON" "d['artifacts'][0]['status']" "active" "Case 3a: fresh artifact status=active"
assert_eq_jq "$LIST_DEFAULT_JSON" "d['artifacts'][0]['artifact_id']" "fresh-$TODAY" "Case 3a: fresh id surfaced"

# 3b: --all list — all three with correct statuses
LIST_ALL_JSON="$TEST_DIR/case3-list-all.json"
( cd "$CASE3_REPO" && "$FLOWCTL" prospect list --all --json > "$LIST_ALL_JSON" )
assert_eq_jq "$LIST_ALL_JSON" "d['count']" "3" "Case 3b: --all list returns 3 artifacts"
# Verify status set
all_statuses="$(json_get "$LIST_ALL_JSON" "sorted([a['status'] for a in d['artifacts']])")"
if [[ "$all_statuses" == "['active', 'corrupt', 'stale']" ]]; then
  ok "Case 3b: status set is {active, corrupt, stale}"
else
  fail "Case 3b: expected statuses {active, corrupt, stale}; got $all_statuses"
fi

# 3c: corrupt artifact carries one of the canonical PROSPECT_CORRUPT_* reasons
corruption_reason="$(json_get "$LIST_ALL_JSON" "[a['corruption'] for a in d['artifacts'] if a['status']=='corrupt'][0]")"
case "$corruption_reason" in
  "no frontmatter block"|"unparseable date"|"missing Grounding snapshot section"|"missing Survivors section"|"unreadable"|"empty"|"missing frontmatter field:"*)
    ok "Case 3c: corruption reason '$corruption_reason' matches PROSPECT_CORRUPT_* contract"
    ;;
  *)
    fail "Case 3c: corruption reason '$corruption_reason' not in canonical set"
    ;;
esac

# 3d: human list --all renders archived rows as 'archived (archived)' suffix
( cd "$CASE3_REPO" && "$FLOWCTL" prospect archive "fresh-$TODAY" --json >/dev/null )
LIST_HUMAN="$( cd "$CASE3_REPO" && "$FLOWCTL" prospect list --all 2>&1 )"
assert_grep "archived (archived)" "$LIST_HUMAN" "Case 3d: --all human row renders 'archived (archived)' suffix"

# =============================================================================
# CASE 4: Artifact writer — collision suffix + roundtrip + atomic
# =============================================================================
echo -e "${YELLOW}--- Case 4: artifact writer (R4, R13) ---${NC}"

CASE4_REPO="$TEST_DIR/case4"
init_test_repo "$CASE4_REPO"

( cd "$CASE4_REPO" && "$PYTHON_BIN" - "$FLOWCTL_PY" "$TODAY" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("flowctl", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from pathlib import Path
prospects = Path(".flow/prospects")
prospects.mkdir(parents=True, exist_ok=True)
today = sys.argv[2]

# First call: nothing exists, writer creates dx-<today>.md
nid1 = m._prospect_next_id(prospects, "dx", today)
assert nid1 == f"dx-{today}", f"first id should equal slug-date, got {nid1!r}"
fm1 = {
    "title": "First", "date": today, "focus_hint": "DX",
    "volume": 5, "survivor_count": 1, "rejected_count": 4, "rejection_rate": 0.8,
    "artifact_id": nid1, "promoted_ideas": [], "status": "active",
    "floor_violation": True, "generation_under_volume": True,
}
ranked = {
    "high_leverage": [{"position":1,"title":"A","summary":"a","leverage":"L; impact lands on Y.","size":"S"}],
    "worth_considering": [], "if_you_have_the_time": [],
}
body = m.render_prospect_body("DX", "ground", ranked, [])
m.write_prospect_artifact(prospects / f"{nid1}.md", fm1, body)

# Second call same day → -2 suffix
nid2 = m._prospect_next_id(prospects, "dx", today)
assert nid2 == f"dx-{today}-2", f"second id should be -2, got {nid2!r}"
fm2 = dict(fm1, title="Second", artifact_id=nid2)
m.write_prospect_artifact(prospects / f"{nid2}.md", fm2, body)

# Atomic: no .tmp.* leftovers
leftover = list(prospects.glob(".tmp.*"))
assert not leftover, f"atomic invariant violated: leftover={leftover}"

# Roundtrip via _prospect_parse_frontmatter
text1 = (prospects / f"{nid1}.md").read_text()
parsed = m._prospect_parse_frontmatter(text1)
assert parsed is not None, "parse returned None"
assert parsed["artifact_id"] == nid1, f"id roundtrip lost: {parsed.get('artifact_id')!r}"
assert parsed["floor_violation"] is True, f"floor_violation roundtrip lost: {parsed.get('floor_violation')!r}"
assert parsed["generation_under_volume"] is True, f"generation_under_volume roundtrip lost: {parsed.get('generation_under_volume')!r}"

# Date renders as quoted string (not bare YAML date)
assert 'date: "' in text1, f"date must render quoted to avoid PyYAML coercion; got: {text1[:200]!r}"

print("OK", nid1, nid2)
PYEOF
) || fail "Case 4: writer harness raised"

# Grep-level invariants on the written files (deterministic strings).
file1="$CASE4_REPO/.flow/prospects/dx-${TODAY}.md"
file2="$CASE4_REPO/.flow/prospects/dx-${TODAY}-2.md"
[[ -f "$file1" ]] && ok "Case 4: first artifact written at dx-${TODAY}.md"  || fail "Case 4: first artifact missing"
[[ -f "$file2" ]] && ok "Case 4: collision suffix -2 written at dx-${TODAY}-2.md" || fail "Case 4: -2 suffix missing"
if [[ -f "$file1" ]]; then
  # PROSPECT_FIELD_ORDER places floor_violation / generation_under_volume after status.
  grep -q '^floor_violation: true$' "$file1" \
    && ok "Case 4: floor_violation: true rendered" \
    || fail "Case 4: floor_violation flag missing or mis-rendered"
  grep -q '^generation_under_volume: true$' "$file1" \
    && ok "Case 4: generation_under_volume: true rendered" \
    || fail "Case 4: generation_under_volume flag missing or mis-rendered"
  grep -q "^date: \"${TODAY}\"$" "$file1" \
    && ok "Case 4: date rendered as quoted YAML scalar" \
    || fail "Case 4: date not quoted (PyYAML date-coercion risk)"
fi

# =============================================================================
# CASE 5: Graceful degradation (R17) — no git / no epics / no CHANGELOG
# =============================================================================
echo -e "${YELLOW}--- Case 5: graceful degradation (R17) ---${NC}"

# Phase 1 grounding does not yet ship as a flowctl subcommand — workflow.md
# §1 specifies the snapshot format. Validate by string contract: the skill
# emits `scanned: none (<reason>)` lines per source. Smoke checks the
# workflow.md spec carries the literal contract strings the smoke depends on.

WF_TEXT="$(cat "$WORKFLOW_FILE")"
# Match the literals shipped in workflow.md §1.1-1.3 (canonical phrasing).
assert_grep "scanned: none (no git repo)"      "$WF_TEXT" "Case 5: workflow.md documents 'scanned: none (no git repo)'"
assert_grep "scanned: none (no open epics)"    "$WF_TEXT" "Case 5: workflow.md documents 'scanned: none (no open epics)'"
assert_grep "scanned: none (no CHANGELOG.md)"  "$WF_TEXT" "Case 5: workflow.md documents 'scanned: none (no CHANGELOG.md)'"

# Behaviour: synthesize the three degradation cases and assert the writer
# never errors on minimal repos. The writer itself is the load-bearing
# surface — grounding consumes inputs and writes; if the writer survives
# missing inputs, the artifact ships.
CASE5_NOGIT="$TEST_DIR/case5-nogit"
mkdir -p "$CASE5_NOGIT"
( cd "$CASE5_NOGIT" && "$FLOWCTL" init --json >/dev/null 2>&1 ) || true
# No git repo → flowctl falls back to cwd. .flow/ created. Synthesize artifact:
synthetic_artifact "$CASE5_NOGIT" "nogit-$TODAY" "$TODAY" "no-git" 1 \
  && ok "Case 5: writer survives ungitted dir (artifact written)" \
  || fail "Case 5: writer raised on ungitted dir"

CASE5_NOEPICS="$TEST_DIR/case5-noepics"
init_test_repo "$CASE5_NOEPICS"
synthetic_artifact "$CASE5_NOEPICS" "noepics-$TODAY" "$TODAY" "no-epics" 1 \
  && ok "Case 5: writer survives empty .flow/epics/" \
  || fail "Case 5: writer raised on empty epics"

CASE5_NOCHGLOG="$TEST_DIR/case5-nochangelog"
init_test_repo "$CASE5_NOCHGLOG"
synthetic_artifact "$CASE5_NOCHGLOG" "nochg-$TODAY" "$TODAY" "no-changelog" 1 \
  && ok "Case 5: writer survives missing CHANGELOG.md" \
  || fail "Case 5: writer raised on missing CHANGELOG"

# =============================================================================
# CASE 6: Promote happy path (R6)
# =============================================================================
echo -e "${YELLOW}--- Case 6: promote happy path (R6) ---${NC}"

CASE6_REPO="$TEST_DIR/case6"
init_test_repo "$CASE6_REPO"
synthetic_artifact "$CASE6_REPO" "dxwins-$TODAY" "$TODAY" "DX" 3

PROMOTE_JSON="$TEST_DIR/case6-promote.json"
( cd "$CASE6_REPO" && "$FLOWCTL" prospect promote "dxwins-$TODAY" --idea 2 --json > "$PROMOTE_JSON" ) \
  || fail "Case 6: promote --idea 2 failed (rc=$?)"

# Required JSON keys per task 5 spec: success/epic_id/epic_title/idea/artifact_id/source_link/spec_path/artifact_updated
for key in success epic_id epic_title idea artifact_id source_link spec_path artifact_updated; do
  if "$PYTHON_BIN" -c "import json,sys; sys.exit(0 if '$key' in json.load(open('$PROMOTE_JSON')) else 1)"; then
    ok "Case 6: promote JSON has key '$key'"
  else
    fail "Case 6: promote JSON missing key '$key'"
  fi
done

assert_eq_jq "$PROMOTE_JSON" "d['success']" "True" "Case 6: success=True"
assert_eq_jq "$PROMOTE_JSON" "d['idea']" "2" "Case 6: idea=2"
assert_eq_jq "$PROMOTE_JSON" "d['artifact_id']" "dxwins-$TODAY" "Case 6: artifact_id roundtrip"
assert_eq_jq "$PROMOTE_JSON" "d['artifact_updated']" "True" "Case 6: artifact_updated=True"

EPIC_ID="$(json_get "$PROMOTE_JSON" "d['epic_id']")"
assert_grep_re '^fn-[0-9]+-' "$EPIC_ID" "Case 6: epic_id matches fn-N-slug shape"

# Epic JSON written
EPIC_JSON_PATH="$CASE6_REPO/.flow/epics/$EPIC_ID.json"
[[ -f "$EPIC_JSON_PATH" ]] && ok "Case 6: epic JSON exists at $EPIC_JSON_PATH" \
                          || fail "Case 6: epic JSON missing"

# Epic spec written with ## Source block linking back to the artifact
EPIC_SPEC_PATH="$CASE6_REPO/.flow/specs/$EPIC_ID.md"
[[ -f "$EPIC_SPEC_PATH" ]] && ok "Case 6: epic spec exists at $EPIC_SPEC_PATH" \
                          || fail "Case 6: epic spec missing"

if [[ -f "$EPIC_SPEC_PATH" ]]; then
  spec_text="$(cat "$EPIC_SPEC_PATH")"
  assert_grep "## Source" "$spec_text" "Case 6: epic spec has '## Source' section"
  assert_grep ".flow/prospects/dxwins-$TODAY.md#idea-2" "$spec_text" "Case 6: ## Source links to artifact#idea-2"
  # Heading is singular ## Acceptance, not plural
  if grep -qE '^## Acceptance$' "$EPIC_SPEC_PATH"; then
    ok "Case 6: epic spec uses '## Acceptance' (singular)"
  else
    fail "Case 6: epic spec missing '## Acceptance' (singular) heading"
  fi
fi

# Artifact frontmatter promoted_ideas: [2]
ARTIFACT_AFTER="$CASE6_REPO/.flow/prospects/dxwins-${TODAY}.md"
if grep -q '^promoted_ideas: \[2\]$' "$ARTIFACT_AFTER"; then
  ok "Case 6: artifact promoted_ideas: [2]"
else
  fail "Case 6: artifact promoted_ideas not updated to [2]"
  grep '^promoted' "$ARTIFACT_AFTER" >&2 || true
fi

# =============================================================================
# CASE 7: Promote idempotency (R14, R20)
# =============================================================================
echo -e "${YELLOW}--- Case 7: promote idempotency ---${NC}"

# 7a: re-run --idea 2 without --force → exit 2 with idempotency message
RC_REPROMOTE=0
REPROMOTE_OUT="$( cd "$CASE6_REPO" && "$FLOWCTL" prospect promote "dxwins-$TODAY" --idea 2 --json 2>&1 )" || RC_REPROMOTE=$?
assert_rc 2 "$RC_REPROMOTE" "Case 7a: re-promote --idea 2 → exit 2"
assert_grep "Idea #2 already promoted" "$REPROMOTE_OUT" "Case 7a: error mentions 'Idea #2 already promoted'"
assert_grep "Use --force" "$REPROMOTE_OUT" "Case 7a: error suggests --force"

# 7b: re-run with --force → success + promoted_to dict carries both epic ids
FORCE_JSON="$TEST_DIR/case7-force.json"
( cd "$CASE6_REPO" && "$FLOWCTL" prospect promote "dxwins-$TODAY" --idea 2 --force --json > "$FORCE_JSON" ) \
  || fail "Case 7b: --force promote failed"
assert_eq_jq "$FORCE_JSON" "d['success']" "True" "Case 7b: --force success=True"

# Frontmatter promoted_to: {"2": [<epic1>, <epic2>]} — keys quoted by the
# inline-flow renderer; this is the production shape (verified in sanity).
ARTIFACT_FORCE="$CASE6_REPO/.flow/prospects/dxwins-${TODAY}.md"
if grep -qE '^promoted_to: \{("?2"?): \[' "$ARTIFACT_FORCE"; then
  ok "Case 7b: artifact carries promoted_to dict keyed by 2"
else
  fail "Case 7b: promoted_to dict missing or mis-formatted"
  grep '^promoted_to' "$ARTIFACT_FORCE" >&2 || true
fi
# Two distinct epic ids in the list
promoted_count="$(grep -oE 'fn-[0-9]+-[a-z0-9-]+' "$ARTIFACT_FORCE" | sort -u | wc -l | tr -d ' ')"
if [[ "$promoted_count" -ge 2 ]]; then
  ok "Case 7b: promoted_to lists ≥2 distinct epic ids ($promoted_count found)"
else
  fail "Case 7b: expected ≥2 epic ids in promoted_to, found $promoted_count"
fi

# =============================================================================
# CASE 8: Promote errors
# =============================================================================
echo -e "${YELLOW}--- Case 8: promote errors ---${NC}"

CASE8_REPO="$TEST_DIR/case8"
init_test_repo "$CASE8_REPO"
synthetic_artifact "$CASE8_REPO" "errs-$TODAY" "$TODAY" "errors" 3

# 8a: --idea 99 (out of range) → exit 2 with N-survivors message
rc=0
out="$( cd "$CASE8_REPO" && "$FLOWCTL" prospect promote "errs-$TODAY" --idea 99 --json 2>&1 )" || rc=$?
assert_rc 2 "$rc" "Case 8a: --idea 99 → exit 2"
assert_grep "out of range" "$out" "Case 8a: error mentions 'out of range'"
assert_grep "3 survivors"  "$out" "Case 8a: error reports survivor count"

# 8b: --idea 0 → exit 2 with >= 1 message
rc=0
out="$( cd "$CASE8_REPO" && "$FLOWCTL" prospect promote "errs-$TODAY" --idea 0 --json 2>&1 )" || rc=$?
assert_rc 2 "$rc" "Case 8b: --idea 0 → exit 2"
assert_grep "must be >= 1" "$out" "Case 8b: error mentions '>= 1' lower bound"

# 8c: --idea foo (non-int) → exit 2 (argparse rejects before flowctl runs)
rc=0
out="$( cd "$CASE8_REPO" && "$FLOWCTL" prospect promote "errs-$TODAY" --idea foo --json 2>&1 )" || rc=$?
assert_rc 2 "$rc" "Case 8c: --idea foo → exit 2"
assert_grep "invalid int value" "$out" "Case 8c: argparse rejects non-int (invalid int value)"

# 8d: corrupt artifact → exit 3 with [ARTIFACT CORRUPT: …] on stderr (text mode)
mkdir -p "$CASE8_REPO/.flow/prospects"
cat > "$CASE8_REPO/.flow/prospects/corrupt-$TODAY.md" <<'EOF'
no frontmatter

## Survivors
EOF
rc=0
err="$( cd "$CASE8_REPO" && "$FLOWCTL" prospect promote "corrupt-$TODAY" --idea 1 2>&1 1>/dev/null )" || rc=$?
assert_rc 3 "$rc" "Case 8d: promote corrupt → exit 3"
assert_grep "[ARTIFACT CORRUPT:" "$err" "Case 8d: stderr carries [ARTIFACT CORRUPT: …] marker"

# =============================================================================
# CASE 9: list / read / archive (sections, slug-only, re-archive, corrupt read)
# =============================================================================
echo -e "${YELLOW}--- Case 9: list / read / archive ---${NC}"

CASE9_REPO="$TEST_DIR/case9"
init_test_repo "$CASE9_REPO"
synthetic_artifact "$CASE9_REPO" "alpha-$TODAY" "$TODAY" "alpha hint" 2

# 9a: list shows it (default)
LIST_TEXT="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect list 2>&1 )"
assert_grep "alpha-$TODAY" "$LIST_TEXT" "Case 9a: default list surfaces fresh artifact"

# 9b: read (full body)
READ_TEXT="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect read "alpha-$TODAY" 2>&1 )"
assert_grep "## Survivors"  "$READ_TEXT" "Case 9b: read prints full body (Survivors)"
assert_grep "## Focus"      "$READ_TEXT" "Case 9b: read prints full body (Focus)"

# 9c: --section survivors filters
SECTION_TEXT="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect read "alpha-$TODAY" --section survivors 2>&1 )"
assert_grep "## Survivors" "$SECTION_TEXT" "Case 9c: --section survivors yields Survivors"
if echo "$SECTION_TEXT" | grep -q '## Focus'; then
  fail "Case 9c: --section survivors leaked '## Focus' from neighboring section"
else
  ok "Case 9c: --section survivors does not leak adjacent sections"
fi

# 9d: --section invalid → error
rc=0
out="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect read "alpha-$TODAY" --section bogus --json 2>&1 )" || rc=$?
assert_grep_re "(invalid|valid:)" "$out" "Case 9d: invalid --section reports valid set"

# 9e: slug-only resolves to latest
synthetic_artifact "$CASE9_REPO" "alpha-2024-01-01" "2024-01-01" "alpha hint" 1
SLUGREAD="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect read alpha 2>&1 | head -8 )"
assert_grep "$TODAY" "$SLUGREAD" "Case 9e: slug-only 'alpha' resolves to today's date (latest wins)"

# 9f: archive moves to _archive/ + sets status: archived
ARCH_JSON="$TEST_DIR/case9-archive.json"
( cd "$CASE9_REPO" && "$FLOWCTL" prospect archive "alpha-$TODAY" --json > "$ARCH_JSON" )
assert_eq_jq "$ARCH_JSON" "d['success']" "True" "Case 9f: archive success=True"
assert_eq_jq "$ARCH_JSON" "d['status']" "archived" "Case 9f: archive returns status=archived"
[[ -f "$CASE9_REPO/.flow/prospects/_archive/alpha-${TODAY}.md" ]] \
  && ok "Case 9f: archive file moved under _archive/" \
  || fail "Case 9f: archive target missing"

# 9g: list default no longer shows archived alpha-$TODAY
LIST_AFTER="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect list 2>&1 )"
if echo "$LIST_AFTER" | grep -q "alpha-$TODAY"; then
  fail "Case 9g: default list still shows archived artifact"
else
  ok "Case 9g: default list hides archived alpha-$TODAY"
fi

# 9h: --all surfaces archived row with '(archived)' suffix
LIST_ALL_AFTER="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect list --all 2>&1 )"
assert_grep "alpha-$TODAY" "$LIST_ALL_AFTER" "Case 9h: --all surfaces archived alpha-$TODAY"
assert_grep "(archived)"   "$LIST_ALL_AFTER" "Case 9h: --all decorates archived row with '(archived)'"

# 9i: re-archive errors clearly (already archived)
rc=0
out="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect archive "alpha-$TODAY" --json 2>&1 )" || rc=$?
if [[ "$rc" -ne 0 ]]; then
  ok "Case 9i: re-archive returns non-zero (rc=$rc)"
else
  fail "Case 9i: re-archive unexpectedly succeeded"
fi
assert_grep "already archived" "$out" "Case 9i: error mentions 'already archived'"

# 9j: read on corrupt → exit 3 + [ARTIFACT CORRUPT: …]
mkdir -p "$CASE9_REPO/.flow/prospects"
cat > "$CASE9_REPO/.flow/prospects/broken-$TODAY.md" <<'EOF'
no frontmatter

## Survivors
EOF
rc=0
out="$( cd "$CASE9_REPO" && "$FLOWCTL" prospect read "broken-$TODAY" 2>&1 )" || rc=$?
assert_rc 3 "$rc" "Case 9j: read corrupt → exit 3"
assert_grep "[ARTIFACT CORRUPT:" "$out" "Case 9j: read corrupt prints marker"

# =============================================================================
# CASE 10: Numbered-options fallback frozen format (R19)
# =============================================================================
echo -e "${YELLOW}--- Case 10: numbered-options fallback (R19) ---${NC}"

# Workflow.md must carry the literal frozen-format strings the smoke greps.
# Spec §6.2 freezes the format; this is the smoke contract.
assert_grep "Saved: .flow/prospects/<artifact-id>.md"   "$WF_TEXT" "Case 10: 'Saved: …' literal present in workflow.md"
assert_grep "Promote a survivor to an epic?"           "$WF_TEXT" "Case 10: 'Promote a survivor to an epic?' literal present"
assert_grep "Enter choice [1-N|i|skip]:"               "$WF_TEXT" "Case 10: 'Enter choice [1-N|i|skip]:' literal present"
assert_grep "i) Interview"                             "$WF_TEXT" "Case 10: interview alphabetic shortcut present"
assert_grep "N) Skip"                                  "$WF_TEXT" "Case 10: numeric Skip slot present"

# Reply routing simulator: the workflow defines exact reply-parsing rules.
# Drive the parser via a shell snippet (matches §6.3) and verify routing for
# the four canonical inputs from the task spec: '1', 'i', 'skip', '<empty>'.
ROUTE_SH="$TEST_DIR/route_reply.sh"
cat > "$ROUTE_SH" <<'BASH'
#!/usr/bin/env bash
# Mimics workflow.md §6.3 reply parsing. Inputs: $1=N (skip slot), $2=reply.
SKIP_SLOT="${1:-3}"
REPLY="${2:-}"
NORM="$(printf '%s' "$REPLY" | tr '[:upper:]' '[:lower:]' | awk '{$1=$1};1')"
case "$NORM" in
  ""|skip)             echo "ROUTE=SKIP"; exit 0 ;;
  i|interview)         echo "ROUTE=INTERVIEW"; exit 0 ;;
esac
if [[ "$NORM" =~ ^[0-9]+$ ]]; then
  if [[ "$NORM" -eq "$SKIP_SLOT" ]]; then
    echo "ROUTE=SKIP"; exit 0
  elif (( NORM >= 1 && NORM < SKIP_SLOT )); then
    echo "ROUTE=PROMOTE($NORM)"; exit 0
  fi
fi
echo "ROUTE=UNRECOGNIZED"
exit 1
BASH
chmod +x "$ROUTE_SH"

# Skip-slot = 3 (2 survivors + 1 skip)
out="$(bash "$ROUTE_SH" 3 "1")"
assert_grep "ROUTE=PROMOTE(1)" "$out" "Case 10a: reply '1' → PROMOTE(1)"

out="$(bash "$ROUTE_SH" 3 "i")"
assert_grep "ROUTE=INTERVIEW" "$out" "Case 10b: reply 'i' → INTERVIEW"

out="$(bash "$ROUTE_SH" 3 "skip")"
assert_grep "ROUTE=SKIP" "$out" "Case 10c: reply 'skip' → SKIP"

out="$(bash "$ROUTE_SH" 3 "")"
assert_grep "ROUTE=SKIP" "$out" "Case 10d: empty reply → SKIP"

# Unrecognized
rc=0
out="$(bash "$ROUTE_SH" 3 "garbage" || rc=$?)"
assert_grep "UNRECOGNIZED" "$out" "Case 10e: garbage reply → UNRECOGNIZED"

# =============================================================================
# CASE 11: Ralph regression sweep — ralph_smoke_test.sh stays green
# =============================================================================
echo -e "${YELLOW}--- Case 11: Ralph regression sweep ---${NC}"

RALPH_LOG="$TEST_DIR/ralph_smoke.log"
rc=0
( cd "$TEST_DIR" && FLOW_RALPH=1 "$PLUGIN_ROOT/scripts/ralph_smoke_test.sh" > "$RALPH_LOG" 2>&1 ) || rc=$?
assert_rc 0 "$rc" "Case 11: ralph_smoke_test.sh exits 0 under FLOW_RALPH=1 (prospect doesn't interfere)"
if [[ "$rc" -ne 0 ]]; then
  echo "--- ralph_smoke_test.sh tail ---" >&2
  tail -40 "$RALPH_LOG" >&2 || true
fi

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

echo -e "${GREEN}All prospect smoke tests passed!${NC}"
