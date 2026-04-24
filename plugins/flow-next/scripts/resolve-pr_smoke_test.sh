#!/usr/bin/env bash
# Smoke test for the flow-next-resolve-pr skill.
#
# Validates:
#   1. GraphQL scripts exist, are executable, use strict bash, fail cleanly on bad args.
#   2. Skill artifacts present (SKILL.md, workflow.md, cluster-analysis.md, command, agent).
#   3. Triage shape: workflow.md Phase 2 describes new/pending split + actionability filter
#      + already-replied filter + "Triage: N new, M pending, K dropped" counts.
#   4. Cluster-gate shape: cluster-analysis.md carries both gate conditions (cross_invocation
#      signal + spatial-overlap precheck), the 11-item category enum, and the 4-row table.
#   5. File-overlap shape: workflow.md Phase 5 covers file sets, serializing overlaps, batch 4.
#   6. Dry-run shape: workflow.md Phase 4 has --dry-run early-exit before mutation phases.
#   7. Ralph isolation: no ralph template references resolve-pr / flow-next-resolve-pr /
#      pr-comment-resolver.
#
# Pure shape assertions — no live PR operations, no GraphQL calls, no mutations.
# Targets < 60s runtime on a modern laptop.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_DIR="$PLUGIN_ROOT/skills/flow-next-resolve-pr"
SKILL_SCRIPTS="$SKILL_DIR/scripts"
COMMAND_FILE="$PLUGIN_ROOT/commands/flow-next/resolve-pr.md"
AGENT_FILE="$PLUGIN_ROOT/agents/pr-comment-resolver.md"
RALPH_TEMPLATES="$PLUGIN_ROOT/skills/flow-next-ralph-init/templates"

TEST_DIR="$(mktemp -d -t resolve-pr-smoke-XXXXXX)"
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

pass() { echo -e "${GREEN}PASS${NC} $*"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}FAIL${NC} $*"; FAIL=$((FAIL + 1)); }

echo -e "${YELLOW}=== resolve-pr skill smoke tests ===${NC}"
echo "Plugin root:  $PLUGIN_ROOT"
echo "Skill dir:    $SKILL_DIR"
echo "Temp dir:     $TEST_DIR"
echo

# -----------------------------------------------------------------------------
# Section 1: Script sanity
# -----------------------------------------------------------------------------
echo -e "${YELLOW}--- Section 1: script sanity ---${NC}"

SCRIPTS=(get-pr-comments get-thread-for-comment reply-to-pr-thread resolve-pr-thread)

for s in "${SCRIPTS[@]}"; do
  path="$SKILL_SCRIPTS/$s"
  if [[ ! -f "$path" ]]; then
    fail "script missing: $s"
    continue
  fi
  if [[ ! -x "$path" ]]; then
    fail "script not executable: $s"
    continue
  fi
  if ! head -n5 "$path" | grep -q 'set -euo pipefail'; then
    fail "script missing 'set -euo pipefail': $s"
    continue
  fi
  pass "$s exists + executable + strict bash"
done

# Usage / arg-missing behaviour — each script must fail (non-zero) on no args
# and must not produce data output on stdout. We stub gh to guarantee no
# network call; ${VAR:?...} expansions fire before gh is reached anyway.
STUB_BIN="$TEST_DIR/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/gh" <<'EOF'
#!/usr/bin/env bash
echo "stub-gh called (should not happen in arg-validation tests)" >&2
exit 99
EOF
chmod +x "$STUB_BIN/gh"

check_usage_fails() {
  local script="$1"
  shift
  local out rc
  # shellcheck disable=SC2016
  out="$(PATH="$STUB_BIN:$PATH" bash "$SKILL_SCRIPTS/$script" "$@" 2>&1 </dev/null || true)"
  rc="$(PATH="$STUB_BIN:$PATH" bash "$SKILL_SCRIPTS/$script" "$@" >/dev/null 2>&1; echo $?)"
  if [[ "$rc" -eq 0 ]]; then
    fail "$script with missing args unexpectedly succeeded"
    return
  fi
  if echo "$out" | grep -qi "usage"; then
    pass "$script fails cleanly with usage message"
  else
    # Bash's ${VAR:?message} writes "bash: 1: Usage: ..." — accept either shape.
    if echo "$out" | grep -q "Usage"; then
      pass "$script fails cleanly with usage message"
    else
      fail "$script missing-args error lacks 'Usage' hint: $out"
    fi
  fi
}

check_usage_fails get-pr-comments
check_usage_fails get-thread-for-comment
check_usage_fails resolve-pr-thread
# reply-to-pr-thread also requires stdin — the THREAD_ID check fires first:
check_usage_fails reply-to-pr-thread

# -----------------------------------------------------------------------------
# Section 2: Skill artifacts + frontmatter
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}--- Section 2: skill artifacts ---${NC}"

check_file_exists() {
  local path="$1"; local label="$2"
  if [[ -f "$path" ]]; then
    pass "$label present"
  else
    fail "$label missing: $path"
  fi
}

check_file_exists "$SKILL_DIR/SKILL.md" "SKILL.md"
check_file_exists "$SKILL_DIR/workflow.md" "workflow.md"
check_file_exists "$SKILL_DIR/cluster-analysis.md" "cluster-analysis.md"
check_file_exists "$COMMAND_FILE" "commands/flow-next/resolve-pr.md"
check_file_exists "$AGENT_FILE" "agents/pr-comment-resolver.md"

# SKILL.md must carry required frontmatter keys.
if grep -q '^name: flow-next-resolve-pr' "$SKILL_DIR/SKILL.md" \
   && grep -q '^description:' "$SKILL_DIR/SKILL.md"; then
  pass "SKILL.md frontmatter (name + description)"
else
  fail "SKILL.md missing required frontmatter"
fi

# Command must reference the skill explicitly (so the dispatcher wires up).
if grep -q 'flow-next-resolve-pr' "$COMMAND_FILE"; then
  pass "resolve-pr.md command references flow-next-resolve-pr skill"
else
  fail "resolve-pr.md command does not reference the skill"
fi

# Agent must carry correct name in frontmatter.
if grep -q '^name: pr-comment-resolver' "$AGENT_FILE"; then
  pass "pr-comment-resolver.md frontmatter name"
else
  fail "pr-comment-resolver.md frontmatter name wrong or missing"
fi

# workflow.md must carry all phase headers.
WORKFLOW="$SKILL_DIR/workflow.md"
for phase in \
  '## Phase 0: Parse arguments' \
  '## Phase 1: Detect PR' \
  '## Phase 2: Triage' \
  '## Phase 3: Cluster analysis' \
  '## Phase 4: Plan' \
  '## Phase 5: Dispatch' \
  '## Phase 6: Validate' \
  '## Phase 7: Commit' \
  '## Phase 8: Reply' \
  '## Phase 9: Verify' \
  '## Phase 10: Summary'
do
  if grep -qF "$phase" "$WORKFLOW"; then
    pass "workflow.md has phase header: ${phase#\#\# }"
  else
    fail "workflow.md missing phase header: ${phase#\#\# }"
  fi
done

# -----------------------------------------------------------------------------
# Section 3: Triage shape (workflow.md Phase 2 narrative)
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}--- Section 3: triage shape (workflow.md Phase 2) ---${NC}"

# Extract Phase 2 text for targeted assertions.
PHASE2="$(awk '/^## Phase 2:/,/^## Phase 3:/' "$WORKFLOW")"

phase2_has() {
  local pattern="$1"; local label="$2"
  if echo "$PHASE2" | grep -qiE "$pattern"; then
    pass "triage describes: $label"
  else
    fail "triage missing: $label (pattern: $pattern)"
  fi
}

phase2_has 'new'                              'new thread class'
phase2_has 'pending'                          'pending class'
phase2_has 'actionability'                    'actionability filter'
phase2_has 'already.replied'                  'already-replied filter'
phase2_has 'Triage: *N new, *M pending, *K dropped' 'Triage count format'
phase2_has 'silent'                           'silent-drop language for non-actionable'

# -----------------------------------------------------------------------------
# Section 4: Cluster gate shape (cluster-analysis.md + workflow.md Phase 3)
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}--- Section 4: cluster-gate shape ---${NC}"

CLUSTER="$SKILL_DIR/cluster-analysis.md"

cluster_has() {
  local pattern="$1"; local label="$2"
  if grep -qiE "$pattern" "$CLUSTER"; then
    pass "cluster-analysis.md: $label"
  else
    fail "cluster-analysis.md missing: $label (pattern: $pattern)"
  fi
}

cluster_has 'cross_invocation\.signal *== *true'   'gate #1 (cross_invocation signal)'
cluster_has 'spatial-overlap precheck'             'gate #2 (spatial-overlap precheck)'

# 11-item category enum — all must appear verbatim.
for cat in error-handling validation type-safety naming performance testing security documentation style architecture other; do
  if grep -qE "\`$cat\`" "$CLUSTER"; then
    pass "cluster category present: $cat"
  else
    fail "cluster category missing: $cat"
  fi
done

# 4-row cluster-formation table — data rows covering the match combinations.
# Header starts with "| Thematic match"; data rows start with "| " (space after
# the leading pipe). Separator "|---|..." has no space and is excluded. Expect
# 1 header + 4 body = 5 lines with '^| '.
TABLE_DATA_ROWS="$(awk '/^\| Thematic match/,/^$/' "$CLUSTER" | grep -c '^| ' || true)"
if [[ "$TABLE_DATA_ROWS" -ge 5 ]]; then
  pass "cluster formation table has header + 4 data rows (found $TABLE_DATA_ROWS '^| ' lines)"
else
  fail "cluster formation table incomplete (found $TABLE_DATA_ROWS '^| ' lines, expected >=5)"
fi

# Phase 3 in workflow.md must reference cluster-analysis.md.
PHASE3="$(awk '/^## Phase 3:/,/^## Phase 4:/' "$WORKFLOW")"
if echo "$PHASE3" | grep -q 'cluster-analysis\.md'; then
  pass "workflow.md Phase 3 references cluster-analysis.md"
else
  fail "workflow.md Phase 3 does not link to cluster-analysis.md"
fi

# -----------------------------------------------------------------------------
# Section 5: File-overlap shape (workflow.md Phase 5 narrative)
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}--- Section 5: file-overlap shape (workflow.md Phase 5) ---${NC}"

PHASE5="$(awk '/^## Phase 5:/,/^## Phase 6:/' "$WORKFLOW")"

phase5_has() {
  local pattern="$1"; local label="$2"
  if echo "$PHASE5" | grep -qiE "$pattern"; then
    pass "Phase 5 describes: $label"
  else
    fail "Phase 5 missing: $label (pattern: $pattern)"
  fi
}

phase5_has 'file set'                     'file sets per unit'
phase5_has 'overlap'                      'overlap detection'
phase5_has 'serial|wave|topological'      'serialization of overlapping units'
phase5_has 'batch size.*4|4 units'        'batch size 4'

# -----------------------------------------------------------------------------
# Section 6: Dry-run shape (workflow.md Phase 4 early exit)
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}--- Section 6: dry-run shape (workflow.md Phase 4) ---${NC}"

PHASE4="$(awk '/^## Phase 4:/,/^## Phase 5:/' "$WORKFLOW")"

if echo "$PHASE4" | grep -qE 'DRY_RUN'; then
  pass "Phase 4 references DRY_RUN variable"
else
  fail "Phase 4 does not reference DRY_RUN"
fi

if echo "$PHASE4" | grep -qE '^[[:space:]]*exit[[:space:]]+0|Exiting.*--dry-run'; then
  pass "Phase 4 has dry-run early exit (exit 0 before mutation phases)"
else
  fail "Phase 4 missing early exit for --dry-run"
fi

# The early exit must precede Phase 5 (dispatch). Verify structurally by
# confirming 'exit 0' appears inside Phase 4's extracted span.
if echo "$PHASE4" | grep -n 'exit 0' >/dev/null; then
  pass "dry-run exits before Phases 5-8 (commit / reply / resolve)"
else
  fail "could not locate 'exit 0' in Phase 4"
fi

# Also verify SKILL.md documents the --dry-run flag.
if grep -q -- '--dry-run' "$SKILL_DIR/SKILL.md"; then
  pass "SKILL.md documents --dry-run flag"
else
  fail "SKILL.md does not document --dry-run flag"
fi

# -----------------------------------------------------------------------------
# Section 7: Ralph isolation — no resolve-pr references in Ralph template tree
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}--- Section 7: Ralph isolation ---${NC}"

# grep -c returns rc=1 when a file has 0 matches (common on fresh Ralph templates),
# which trips set -e. Guard the whole pipeline with `|| true` and then compute the
# total via awk.
RALPH_HITS="$({ grep -rEc 'resolve-pr|flow-next-resolve-pr|pr-comment-resolver' "$RALPH_TEMPLATES" 2>/dev/null || true; } | awk -F: '{sum += $2} END {print sum+0}')"
if [[ "$RALPH_HITS" -eq 0 ]]; then
  pass "Ralph templates contain 0 references to resolver surfaces"
else
  fail "Ralph templates contain $RALPH_HITS resolver reference(s) — should be 0"
  grep -rEn 'resolve-pr|flow-next-resolve-pr|pr-comment-resolver' "$RALPH_TEMPLATES" 2>/dev/null || true
fi

# Also check the installed ralph_smoke_test.sh itself doesn't invoke resolver
# scripts (it's read-only from our perspective — we assert it stays that way).
RALPH_SMOKE="$PLUGIN_ROOT/scripts/ralph_smoke_test.sh"
if [[ -f "$RALPH_SMOKE" ]]; then
  if grep -qE 'resolve-pr|flow-next-resolve-pr|pr-comment-resolver' "$RALPH_SMOKE"; then
    fail "ralph_smoke_test.sh references resolver surfaces"
  else
    pass "ralph_smoke_test.sh does not reference resolver surfaces"
  fi
else
  fail "ralph_smoke_test.sh missing from scripts/"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo
echo -e "${YELLOW}=== summary ===${NC}"
echo "passed: $PASS"
echo "failed: $FAIL"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
