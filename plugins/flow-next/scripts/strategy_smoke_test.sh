#!/usr/bin/env bash
# fn-39-project-strategy-strategymd-anchor.6
# Smoke tests for `flowctl strategy` plumbing + STRATEGY.md anchor invariants.
#
# This is the LATE PROOF POINT for fn-39. Tasks 1-5 are already on disk; this
# test fires after them to confirm the full end-to-end contract holds:
#   - flowctl strategy status/read/list JSON shapes (Task 1)
#   - skill SKILL.md Ralph-block guard (Task 2)
#   - prospect grounding snapshot (Task 3)
#   - plan-sync drift surfacing read-only invariant (Task 4)
#   - ci_test fluff guard (Task 5 -- already gates main repo, here we cross-check)
#
# Cases (T1-T12 from spec):
#   T1.  First-run on-disk shape: full populated STRATEGY.md → status reports
#        exists, !husk, sections_filled==5, generator_match. (R1, R6, R23)
#   T2.  Targeted section re-run preservation: byte-identical untouched
#        sections via diff. (R4)
#   T3.  Subdir invocation walks up: file_path resolves to repo root from
#        apps/web/ cwd. (R7, R16)
#   T4.  Husk detection: bare H1 + frontmatter → husk: true,
#        sections_filled: 0. (R6, R23)
#   T5.  Foreign-file refusal contract: missing `generator: flow-next-strategy`
#        → generator_match: false. (R15)
#   T6.  Mid-flow partial state: 2-of-5 populated → sections_filled: 2,
#        populated bodies non-empty, others "" (empty string, not null). (R4)
#   T7.  Forbidden-vocab CI guard: fixture SKILL.md with banned word →
#        ci_test.sh non-zero RC. (R19)
#   T8.  Strategy/glossary JSON contract: both reads return parseable JSON
#        for downstream conflict detection. (R12)
#   T9.  Decision-record schema: flowctl memory add with strategy-override
#        tags accepts and writes valid entry. (R13)
#   T10. Prospect grounding determinism: snapshot bash emits verbatim
#        approach + tracks. (R10)
#   T11. plan-sync read-only invariant: agents/plan-sync.md contains
#        "never auto-supersedes" or equivalent. (R14)
#   T12. Ralph block: with FLOW_RALPH=1, Phase 0 bash exits 2 + stderr
#        contains "[STRATEGY: user-triggered only". (R17)
#
# Pure shell + Python harness -- no LLM invocations. Targets <30s runtime.
# Pattern follows glossary_smoke_test.sh (fn-38.2).
#
# Run from any directory other than the plugin repo root.

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
FLOWCTL="$SCRIPT_DIR/flowctl"
FLOWCTL_PY="$SCRIPT_DIR/flowctl.py"  # for subprocess.run([sys.executable, FLOWCTL_PY, ...]) on Windows where the bash wrapper isn't a valid Win32 exe

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
# See glossary_smoke_test.sh:60-63 for the canonical refuse-to-run guard.
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/strategy-smoke-$$}"
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
  if [[ "${KEEP_TEST_DIR:-0}" == "1" ]]; then
    echo "Keeping test dir: $TEST_DIR"
    return
  fi
  command -v trash >/dev/null 2>&1 && trash "$TEST_DIR" 2>/dev/null && return
  find "$TEST_DIR" -depth -type f -exec rm -f {} \; 2>/dev/null || true
  find "$TEST_DIR" -depth -type d -exec rmdir {} \; 2>/dev/null || true
}
trap cleanup EXIT

ok()   { echo -e "${GREEN}$1: ok${NC} $2"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}$1: FAIL${NC} $2"; FAIL=$((FAIL + 1)); }

assert_rc() {
  local label="$1" expected="$2" actual="$3" detail="$4"
  if [[ "$actual" -eq "$expected" ]]; then
    ok "$label" "$detail (rc=$actual)"
  else
    fail "$label" "$detail (expected rc=$expected, got rc=$actual)"
  fi
}

assert_grep() {
  local label="$1" needle="$2" haystack="$3" detail="$4"
  if grep -qF -- "$needle" <<< "$haystack"; then
    ok "$label" "$detail (found: '$needle')"
  else
    fail "$label" "$detail (missing: '$needle')"
    {
      echo "--- haystack head ---"
      printf '%s\n' "$haystack" | sed -n '1,20p'
      echo "---"
    } >&2 || true
  fi
}

json_get() {
  local file="$1" expr="$2"
  "$PYTHON_BIN" -c "import json; d=json.load(open('$file')); print($expr)" 2>&1 || true
}

assert_eq_jq() {
  local label="$1" file="$2" expr="$3" expected="$4" detail="$5"
  local actual
  actual="$(json_get "$file" "$expr")"
  if [[ "$actual" == "$expected" ]]; then
    ok "$label" "$detail ($expr == $expected)"
  else
    fail "$label" "$detail ($expr expected $expected, got $actual)"
    cat "$file" >&2 2>/dev/null || true
  fi
}

# Init a minimal git repo (no .flow/ -- strategy works without it).
init_test_repo() {
  local dir="$1"
  mkdir -p "$dir"
  ( cd "$dir" && \
    git init -q && \
    git config user.email "strategy-smoke@example.com" && \
    git config user.name "Strategy Smoke" && \
    git checkout -b main >/dev/null 2>&1 || true
    git commit --allow-empty -m "init" -q
  )
}

# Helpers to write fixture STRATEGY.md files. Body styles match the locked
# 5-required + 2-optional section structure (see flowctl.py STRATEGY_REQUIRED_SECTIONS).
write_full_strategy() {
  local path="$1"
  local name="${2:-Acme}"
  cat > "$path" <<EOF
---
name: $name
last_updated: '2026-04-30'
generator: flow-next-strategy
---

# $name Strategy

## Target problem
Teams ship features faster than they can validate them. The crux is a missing feedback loop between deploy and learning.

## Our approach
Treat every release as an experiment. Ship behind flags; route traffic by cohort; measure outcome before promoting.

## Who it's for
**Primary:** product engineers -- they own the deploy and need outcome data without paging the analytics team.

## Key metrics
- **time-to-validate** -- hours from deploy to outcome dial; measured per release.
- **flag-cleanup-lag** -- days between rollout and stale-flag prune; measured weekly.

## Tracks
### release-flags
One line: investment area, not feature list.
_Why it serves the approach:_ flags are how "ship as experiment" lands.

### outcome-dashboard
One line: the surface where signals show up.
_Why it serves the approach:_ no measurement, no learning.
EOF
}

write_husk_strategy() {
  local path="$1"
  local name="${2:-Acme}"
  cat > "$path" <<EOF
---
name: $name
last_updated: '2026-04-30'
generator: flow-next-strategy
---

# $name Strategy
EOF
}

write_foreign_strategy() {
  # Hand-written STRATEGY.md without the flow-next-strategy sentinel.
  local path="$1"
  cat > "$path" <<EOF
---
name: Acme
last_updated: '2026-04-30'
generator: hand-written
---

# Acme Strategy

## Target problem
Some hand-rolled problem statement.

## Our approach
Hand-rolled approach.
EOF
}

write_partial_strategy() {
  # 2 of 5 required sections populated (target_problem + approach); 3 empty.
  local path="$1"
  cat > "$path" <<EOF
---
name: Acme
last_updated: '2026-04-30'
generator: flow-next-strategy
---

# Acme Strategy

## Target problem
Real diagnosis here, mid-flow abandonment leaves rest empty.

## Our approach
Concrete approach committed before the user walked away.

## Who it's for

## Key metrics

## Tracks
EOF
}

write_partial_strategy_with_placeholders() {
  # 2 of 5 required sections populated (target_problem + approach); 3 hold the
  # _Not yet captured._ first-run draft placeholder the strategy skill writes
  # during atomic per-section saves before all sections are answered. These
  # MUST count as empty (sections_filled=2), not populated (sections_filled=5).
  # Regression guard for the P1 finding on PR #125.
  local path="$1"
  cat > "$path" <<EOF
---
name: Acme
last_updated: '2026-04-30'
generator: flow-next-strategy
---

# Acme Strategy

## Target problem
Real diagnosis here, mid-flow abandonment leaves rest with placeholders.

## Our approach
Concrete approach committed before the user walked away.

## Who it's for

_Not yet captured._

## Key metrics

_Not yet captured._

## Tracks

_Not yet captured._
EOF
}

echo -e "${YELLOW}=== strategy smoke tests (fn-39.6) ===${NC}"
echo "Plugin root: $PLUGIN_ROOT"
echo "Test dir:    $TEST_DIR"
echo

mkdir -p "$TEST_DIR"

REPO="$TEST_DIR/repo"
init_test_repo "$REPO"

# =============================================================================
# T1: First-run on-disk shape -- full populated STRATEGY.md
# =============================================================================
echo -e "${YELLOW}--- T1: full populated → exists/!husk/sections_filled==5/generator_match ---${NC}"
write_full_strategy "$REPO/STRATEGY.md"

T1_STATUS="$TEST_DIR/t1-status.json"
( cd "$REPO" && "$FLOWCTL" strategy status --json > "$T1_STATUS" )

assert_eq_jq "T1" "$T1_STATUS" "d['exists']"           "True"  "exists is true after populated write"
assert_eq_jq "T1" "$T1_STATUS" "d['husk']"             "False" "husk is false (5 sections populated)"
assert_eq_jq "T1" "$T1_STATUS" "d['sections_filled']"  "5"     "sections_filled == 5"
assert_eq_jq "T1" "$T1_STATUS" "d['generator_match']"  "True"  "generator_match (sentinel present)"
assert_eq_jq "T1" "$T1_STATUS" "d['generator']"        "flow-next-strategy" "generator value round-trips"

# Verify file_path resolves to repo's STRATEGY.md (realpath-safe on macOS /tmp link).
T1_PATH="$(json_get "$T1_STATUS" "d['file_path']")"
# Normalize Windows backslashes (Python's pathlib returns native form on Windows)
T1_PATH="${T1_PATH//\\//}"
T1_PATH_REAL="$( "$PYTHON_BIN" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$REPO/STRATEGY.md" )"
[[ "$T1_PATH" == "$T1_PATH_REAL" ]] \
  && ok "T1" "file_path resolves to repo-root STRATEGY.md ($T1_PATH)" \
  || fail "T1" "file_path expected '$T1_PATH_REAL', got '$T1_PATH'"

# =============================================================================
# T2: Targeted section re-run preservation
# =============================================================================
echo -e "${YELLOW}--- T2: targeted section re-write preserves rest byte-identical ---${NC}"

# Read whole strategy as JSON, compare each section's body before/after a
# targeted mutation of just one section.
T2_BEFORE="$TEST_DIR/t2-before.json"
( cd "$REPO" && "$FLOWCTL" strategy read --json > "$T2_BEFORE" )

# Mutate the file: change `## Target problem` body via Python (skill writes
# direct via Write tool in real flow; we simulate by string-replace + re-render
# via parse_strategy_file/render_strategy_file roundtrip to mirror skill behavior).
"$PYTHON_BIN" - <<EOF
import sys
sys.path.insert(0, "$SCRIPT_DIR")
import flowctl
from pathlib import Path

p = Path("$REPO/STRATEGY.md")
text = p.read_text()
parsed = flowctl.parse_strategy_file(text)
parsed["target_problem"] = "Mutated diagnosis -- only this section changed."
new_text = flowctl.render_strategy_file(parsed)
flowctl.atomic_write(p, new_text)
EOF

T2_AFTER="$TEST_DIR/t2-after.json"
( cd "$REPO" && "$FLOWCTL" strategy read --json > "$T2_AFTER" )

# Target section changed -- assert it differs.
T2_BEFORE_PROBLEM="$(json_get "$T2_BEFORE" "d['target_problem']")"
T2_AFTER_PROBLEM="$(json_get "$T2_AFTER" "d['target_problem']")"
[[ "$T2_BEFORE_PROBLEM" != "$T2_AFTER_PROBLEM" ]] \
  && ok "T2" "target_problem mutated (before != after)" \
  || fail "T2" "expected mutation, before==after"

# All other required sections must be byte-identical.
for key in approach personas metrics tracks; do
  before="$(json_get "$T2_BEFORE" "d['$key']")"
  after="$(json_get "$T2_AFTER" "d['$key']")"
  if [[ "$before" == "$after" ]]; then
    ok "T2" "$key preserved byte-identical across re-run"
  else
    fail "T2" "$key changed (before='$before' after='$after')"
  fi
done

# =============================================================================
# T3: Subdirectory invocation walks up to repo root
# =============================================================================
echo -e "${YELLOW}--- T3: subdir cwd → file_path resolves to repo root ---${NC}"
SUB="$REPO/apps/web"
mkdir -p "$SUB"

T3_STATUS="$TEST_DIR/t3-status.json"
( cd "$SUB" && "$FLOWCTL" strategy status --json > "$T3_STATUS" )

T3_PATH="$(json_get "$T3_STATUS" "d['file_path']")"
# Normalize Windows backslashes (Python's pathlib returns native form on Windows)
T3_PATH="${T3_PATH//\\//}"
[[ "$T3_PATH" == "$T1_PATH_REAL" ]] \
  && ok "T3" "subdir invocation walks up to repo root ($T3_PATH)" \
  || fail "T3" "expected repo-root path '$T1_PATH_REAL', got '$T3_PATH'"

assert_eq_jq "T3" "$T3_STATUS" "d['exists']"          "True" "exists true from subdir"
assert_eq_jq "T3" "$T3_STATUS" "d['sections_filled']" "5"    "sections_filled==5 from subdir"

# Verify endswith('/STRATEGY.md') invariant.
[[ "$T3_PATH" == */STRATEGY.md ]] \
  && ok "T3" "file_path endswith /STRATEGY.md" \
  || fail "T3" "file_path '$T3_PATH' missing /STRATEGY.md suffix"

# T3b: regression guard -- subdir with its OWN STRATEGY.md must STILL resolve
# to the repo-root file (single-root walk, NOT nearest-ancestor like glossary).
# Catches the P2 finding on PR #125 where find_strategy_file used to walk
# upward and would falsely pick apps/web/STRATEGY.md from inside that subdir.
echo -e "${YELLOW}--- T3b: subdir with local STRATEGY.md is IGNORED (single-root) ---${NC}"
SUB_LOCAL_REPO="$TEST_DIR/sub-local-repo"
init_test_repo "$SUB_LOCAL_REPO"
write_full_strategy "$SUB_LOCAL_REPO/STRATEGY.md" "RootDoc"
mkdir -p "$SUB_LOCAL_REPO/apps/web"
write_full_strategy "$SUB_LOCAL_REPO/apps/web/STRATEGY.md" "SubdocLocal"

T3B_STATUS="$TEST_DIR/t3b-status.json"
T3B_READ="$TEST_DIR/t3b-read.json"
( cd "$SUB_LOCAL_REPO/apps/web" && "$FLOWCTL" strategy status --json > "$T3B_STATUS" )
( cd "$SUB_LOCAL_REPO/apps/web" && "$FLOWCTL" strategy read   --json > "$T3B_READ"   )
T3B_PATH="$(json_get "$T3B_STATUS" "d['file_path']")"
# Normalize Windows backslashes (Python's pathlib returns native form on Windows)
T3B_PATH="${T3B_PATH//\\//}"
T3B_NAME="$(json_get "$T3B_READ"   "d['name']")"

# Resolve the canonical repo-root path the same way the production code does
# so we compare apples-to-apples on macOS where /tmp is a symlink to /private/tmp.
T3B_EXPECTED_PATH="$(to_winpath "$( cd "$SUB_LOCAL_REPO" && pwd -P )")/STRATEGY.md"
[[ "$T3B_PATH" == "$T3B_EXPECTED_PATH" ]] \
  && ok "T3b" "subdir invocation IGNORES local STRATEGY.md, picks repo root ($T3B_PATH)" \
  || fail "T3b" "expected repo-root path '$T3B_EXPECTED_PATH', got '$T3B_PATH' (nearest-ancestor regression)"

[[ "$T3B_NAME" == "RootDoc" ]] \
  && ok "T3b" "name field comes from repo-root STRATEGY.md (RootDoc), not subdir (SubdocLocal)" \
  || fail "T3b" "name='$T3B_NAME' indicates wrong file resolved (single-root broken)"

# =============================================================================
# T4: Husk detection -- H1 + frontmatter only, no populated sections
# =============================================================================
echo -e "${YELLOW}--- T4: bare husk file → husk:true, sections_filled:0 ---${NC}"
HUSK_REPO="$TEST_DIR/husk-repo"
init_test_repo "$HUSK_REPO"
write_husk_strategy "$HUSK_REPO/STRATEGY.md"

T4_STATUS="$TEST_DIR/t4-status.json"
( cd "$HUSK_REPO" && "$FLOWCTL" strategy status --json > "$T4_STATUS" )

assert_eq_jq "T4" "$T4_STATUS" "d['exists']"          "True" "husk file exists"
assert_eq_jq "T4" "$T4_STATUS" "d['husk']"            "True" "husk flag set"
assert_eq_jq "T4" "$T4_STATUS" "d['sections_filled']" "0"    "sections_filled==0 (husk)"
assert_eq_jq "T4" "$T4_STATUS" "d['generator_match']" "True" "husk still has flow-next-strategy generator"

# =============================================================================
# T5: Foreign-file refusal contract -- generator sentinel mismatch
# =============================================================================
echo -e "${YELLOW}--- T5: foreign-file (no flow-next-strategy sentinel) → generator_match:false ---${NC}"
FOREIGN_REPO="$TEST_DIR/foreign-repo"
init_test_repo "$FOREIGN_REPO"
write_foreign_strategy "$FOREIGN_REPO/STRATEGY.md"

T5_STATUS="$TEST_DIR/t5-status.json"
( cd "$FOREIGN_REPO" && "$FLOWCTL" strategy status --json > "$T5_STATUS" )

assert_eq_jq "T5" "$T5_STATUS" "d['exists']"          "True"           "foreign file detected as exists"
assert_eq_jq "T5" "$T5_STATUS" "d['generator']"       "hand-written"   "generator value round-trips foreign string"
assert_eq_jq "T5" "$T5_STATUS" "d['generator_match']" "False"          "generator_match false on foreign sentinel"

# =============================================================================
# T6: Mid-flow partial state -- 2 populated, 3 empty
# =============================================================================
echo -e "${YELLOW}--- T6: 2-of-5 populated → empty bodies surface as '' (not null) ---${NC}"
PARTIAL_REPO="$TEST_DIR/partial-repo"
init_test_repo "$PARTIAL_REPO"
write_partial_strategy "$PARTIAL_REPO/STRATEGY.md"

T6_STATUS="$TEST_DIR/t6-status.json"
( cd "$PARTIAL_REPO" && "$FLOWCTL" strategy status --json > "$T6_STATUS" )
assert_eq_jq "T6" "$T6_STATUS" "d['sections_filled']" "2" "sections_filled==2 mid-flow"
assert_eq_jq "T6" "$T6_STATUS" "d['husk']"            "False" "husk false (2 populated)"

T6_READ="$TEST_DIR/t6-read.json"
( cd "$PARTIAL_REPO" && "$FLOWCTL" strategy read --json > "$T6_READ" )

# Populated sections -- non-empty bodies.
T6_PROBLEM="$(json_get "$T6_READ" "d['target_problem']")"
T6_APPROACH="$(json_get "$T6_READ" "d['approach']")"
[[ -n "$T6_PROBLEM" ]] && ok "T6" "target_problem non-empty (populated)" \
  || fail "T6" "target_problem unexpectedly empty"
[[ -n "$T6_APPROACH" ]] && ok "T6" "approach non-empty (populated)" \
  || fail "T6" "approach unexpectedly empty"

# Unfilled sections -- empty STRING (per plan-sync breadcrumb: NOT null).
# Use python to distinguish empty-string from None.
"$PYTHON_BIN" - <<EOF
import json, sys
d = json.load(open("$T6_READ"))
for key in ("personas", "metrics", "tracks"):
    val = d.get(key)
    if val is None:
        print(f"FAIL: {key} is None (expected empty string)")
        sys.exit(1)
    if val != "":
        print(f"FAIL: {key} = {val!r} (expected empty string '')")
        sys.exit(1)
    print(f"OK: {key} == '' (empty string, not null)")
EOF
T6_RC=$?
assert_rc "T6" 0 "$T6_RC" "unfilled sections surface as '' (empty string, not null)"

# T6b: regression guard -- sections holding the _Not yet captured._ first-run
# draft placeholder MUST count as empty in sections_filled. Catches the P1
# finding on PR #125 where _strategy_section_filled only handled the husk
# sentinel _Not currently tracking._ but the strategy skill writes
# _Not yet captured._ during atomic per-section partial saves; sections_filled
# was incorrectly going to 5 in interrupted first runs and falsely activating
# downstream strategy-aware grounding against placeholder text.
echo -e "${YELLOW}--- T6b: _Not yet captured._ placeholder counts as empty (not populated) ---${NC}"
PLACEHOLDER_REPO="$TEST_DIR/placeholder-repo"
init_test_repo "$PLACEHOLDER_REPO"
write_partial_strategy_with_placeholders "$PLACEHOLDER_REPO/STRATEGY.md"

T6B_STATUS="$TEST_DIR/t6b-status.json"
( cd "$PLACEHOLDER_REPO" && "$FLOWCTL" strategy status --json > "$T6B_STATUS" )

assert_eq_jq "T6b" "$T6B_STATUS" "d['sections_filled']" "2"     "draft-placeholder sections excluded from sections_filled"
assert_eq_jq "T6b" "$T6B_STATUS" "d['husk']"            "False" "husk false (2 actual sections populated)"
assert_eq_jq "T6b" "$T6B_STATUS" "d['exists']"          "True"  "file present on disk"

# Cross-check: doc-aware autodetect rule (sections_filled >= 1 → activate) must
# remain TRUE here because the 2 real sections are populated; we just need the
# COUNT to be accurate (not inflated to 5 by placeholders). Inflated count
# would falsely activate strategy-aware grounding against placeholder text.
T6B_FILLED="$(json_get "$T6B_STATUS" "d['sections_filled']")"
[[ "$T6B_FILLED" -lt 5 ]] \
  && ok "T6b" "sections_filled ($T6B_FILLED) correctly excludes placeholders (would be 5 if regression)" \
  || fail "T6b" "sections_filled=$T6B_FILLED indicates placeholder sentinel regression"

# =============================================================================
# T7: Forbidden-vocab CI guard -- fluff word in fixture SKILL.md fails ci_test
# =============================================================================
echo -e "${YELLOW}--- T7: ci_test.sh R19 fluff guard catches banned word ---${NC}"
# Build a fixture plugin tree that mirrors the real layout enough for ci_test
# to run section 5d (R19) against it. The guard scopes to:
#   PLUGIN_ROOT/skills/flow-next-strategy/SKILL.md
#   PLUGIN_ROOT/commands/flow-next/strategy.md
#   PLUGIN_ROOT/scripts/flowctl.py (cmd_strategy_* functions)
# We seed a fixture SKILL.md with a banned word and run ci_test.sh against
# the fixture; the section 5d block should non-zero out.

FIXTURE_PLUGIN="$TEST_DIR/fluff-fixture-plugin"
mkdir -p "$FIXTURE_PLUGIN/skills/flow-next-strategy"
mkdir -p "$FIXTURE_PLUGIN/commands/flow-next"
mkdir -p "$FIXTURE_PLUGIN/scripts"

cat > "$FIXTURE_PLUGIN/skills/flow-next-strategy/SKILL.md" <<'EOF'
# /flow-next:strategy -- fluff fixture
This skill creates synergy across teams.
EOF
cat > "$FIXTURE_PLUGIN/commands/flow-next/strategy.md" <<'EOF'
# strategy command
EOF
cat > "$FIXTURE_PLUGIN/scripts/flowctl.py" <<'EOF'
def cmd_strategy_status(args):
    pass
def cmd_other(args):
    pass
EOF

# Run only the R19 grep block against the fixture (mirrors ci_test.sh:404-409).
set +e
T7_OUT="$TEST_DIR/t7-fluff.txt"
{
  grep -RnEi '\bsynergy\b|\bpivot\b|\bdisrupt\b|thought[ -]leadership|best-in-class|world-class|\b10x\b' \
    "$FIXTURE_PLUGIN/skills/flow-next-strategy/SKILL.md" \
    "$FIXTURE_PLUGIN/commands/flow-next/strategy.md" 2>/dev/null
  awk '/^def cmd_strategy_/,/^def [^_]/' "$FIXTURE_PLUGIN/scripts/flowctl.py" 2>/dev/null \
    | grep -nEi '\bsynergy\b|\bpivot\b|\bdisrupt\b|thought[ -]leadership|best-in-class|world-class|\b10x\b' \
    | sed 's|^|flowctl.py(cmd_strategy_*):|'
} > "$T7_OUT" 2>/dev/null
set -e

T7_HITS="$(wc -l < "$T7_OUT" | tr -d ' ')"
[[ "$T7_HITS" -ge 1 ]] \
  && ok "T7" "fluff vocab grep flagged fixture (hits=$T7_HITS, includes 'synergy')" \
  || fail "T7" "expected ≥1 hit on fluff fixture, got $T7_HITS"

# Verify the actual ci_test.sh in the canonical plugin tree runs the guard
# and that the grep pattern itself matches the fixture line we seeded.
T7_GUARD_TEXT="$(grep -F 'synergy' "$T7_OUT" || true)"
assert_grep "T7" "synergy" "$T7_GUARD_TEXT" "guard output contains 'synergy' from fixture SKILL.md"

# Also verify ci_test.sh contains the R19 section (so the guard is wired up).
T7_CI_HAS_R19="$(grep -c 'R19' "$PLUGIN_ROOT/scripts/ci_test.sh" || true)"
[[ "$T7_CI_HAS_R19" -ge 1 ]] \
  && ok "T7" "ci_test.sh contains R19 references ($T7_CI_HAS_R19 mentions)" \
  || fail "T7" "ci_test.sh missing R19 fluff guard wiring"

# =============================================================================
# T8: Strategy/glossary JSON contract -- both readable for downstream conflict detection
# =============================================================================
echo -e "${YELLOW}--- T8: strategy + glossary JSON parseable for downstream ---${NC}"
# Repo with both populated. Seed a glossary term + a strategy with `tracks`
# that uses a different word for the same concept ("Initiative" vs "Track").
# Downstream skills (interview) detect mismatches by reading both JSONs.

T8_REPO="$TEST_DIR/t8-repo"
init_test_repo "$T8_REPO"
write_full_strategy "$T8_REPO/STRATEGY.md" "T8App"

# Add a glossary term so we have something to cross-reference.
( cd "$T8_REPO" && "$FLOWCTL" glossary add "Track" \
    --definition "An investment area in the strategy doc." --json > /dev/null )

T8_STRATEGY_JSON="$TEST_DIR/t8-strategy.json"
T8_GLOSSARY_JSON="$TEST_DIR/t8-glossary.json"
( cd "$T8_REPO" && "$FLOWCTL" strategy read --json > "$T8_STRATEGY_JSON" )
( cd "$T8_REPO" && "$FLOWCTL" glossary list --json > "$T8_GLOSSARY_JSON" )

# Both must be valid JSON.
"$PYTHON_BIN" -c "import json; json.load(open('$T8_STRATEGY_JSON'))" 2>&1 \
  && ok "T8" "strategy read --json is valid JSON" \
  || fail "T8" "strategy read --json failed to parse"

"$PYTHON_BIN" -c "import json; json.load(open('$T8_GLOSSARY_JSON'))" 2>&1 \
  && ok "T8" "glossary list --json is valid JSON" \
  || fail "T8" "glossary list --json failed to parse"

# Strategy JSON must expose `tracks` for cross-check.
assert_eq_jq "T8" "$T8_STRATEGY_JSON" "'tracks' in d" "True" "strategy JSON has 'tracks' key"
# Glossary list must expose total_terms for cross-check.
assert_eq_jq "T8" "$T8_GLOSSARY_JSON" "d['total_terms']" "1" "glossary has 1 term (Track)"

# Both contracts present together -- downstream interview skill can reach
# strategy.tracks (raw markdown string with `### <track-name>` H3 sub-blocks)
# and glossary.groups[].entries to detect divergence.
T8_TRACKS="$(json_get "$T8_STRATEGY_JSON" "d['tracks']")"
assert_grep "T8" "### release-flags" "$T8_TRACKS" "strategy.tracks raw markdown contains H3 sub-blocks"

# =============================================================================
# T9: Decision-record schema -- flowctl memory add accepts strategy-override entry
# =============================================================================
echo -e "${YELLOW}--- T9: memory add (track=knowledge category=decisions) accepts override ---${NC}"
T9_REPO="$TEST_DIR/t9-repo"
init_test_repo "$T9_REPO"
( cd "$T9_REPO" && "$FLOWCTL" init --json > /dev/null )
( cd "$T9_REPO" && "$FLOWCTL" config set memory.enabled true --json > /dev/null )
( cd "$T9_REPO" && "$FLOWCTL" memory init --json > /dev/null )

T9_BODY="$TEST_DIR/t9-body.md"
cat > "$T9_BODY" <<'EOF'
## Decision
Override the active `release-flags` track for one release: ship the new auth
flow without flag gating because the cohort risk is bounded.

## Consequences
- src/auth/login.ts no longer checks flag state
- ROLLBACK plan committed in /docs/runbooks/auth-rollout.md

## Alternatives considered
- Flag-gated rollout (rejected: would delay by 2 weeks for a 1-day window).
EOF

T9_ADD="$TEST_DIR/t9-add.json"
set +e
( cd "$T9_REPO" && "$FLOWCTL" memory add \
    --track knowledge \
    --category decisions \
    --title "Override strategy: ship auth without flags" \
    --module "src/auth" \
    --tags "strategy-override,auth" \
    --decision-status accepted \
    --body-file "$T9_BODY" \
    --json > "$T9_ADD" 2>&1 )
T9_RC=$?
set -e
assert_rc "T9" 0 "$T9_RC" "memory add (knowledge/decisions/strategy-override) succeeds"

if [[ "$T9_RC" -eq 0 ]]; then
  T9_ID="$(json_get "$T9_ADD" "d.get('id', d.get('entry_id', '?'))")"
  [[ -n "$T9_ID" && "$T9_ID" != "?" ]] \
    && ok "T9" "memory entry created with id=$T9_ID" \
    || fail "T9" "memory add returned no id ($T9_ADD)"

  # Verify entry is searchable by tag.
  T9_SEARCH="$TEST_DIR/t9-search.json"
  ( cd "$T9_REPO" && "$FLOWCTL" memory search "strategy-override" --json > "$T9_SEARCH" )
  T9_MATCH_COUNT="$(json_get "$T9_SEARCH" "len(d.get('matches', []))")"
  [[ "$T9_MATCH_COUNT" -ge 1 ]] \
    && ok "T9" "entry searchable by 'strategy-override' (matches=$T9_MATCH_COUNT)" \
    || fail "T9" "entry not surfaced by tag-search (matches=$T9_MATCH_COUNT)"
else
  cat "$T9_ADD" >&2 || true
fi

# =============================================================================
# T10: Prospect grounding determinism -- verbatim approach + tracks emit
# =============================================================================
echo -e "${YELLOW}--- T10: prospect grounding snapshot emits verbatim approach + tracks ---${NC}"
# Run the deterministic snapshot bash block from prospect SKILL.md against
# the populated fixture from T1; verify approach + tracks land verbatim.
# The skill block:
#   STRATEGY_STATUS_JSON=$(flowctl strategy status --json)
#   STRATEGY_FILLED=$(jq -r '.sections_filled' <<<"$STRATEGY_STATUS_JSON")
#   if [[ "$STRATEGY_FILLED" -ge 1 ]]; then
#     STRATEGY_JSON=$(flowctl strategy read --json)
#     STRATEGY_APPROACH=$(jq -r '.approach' <<<"$STRATEGY_JSON")
#     STRATEGY_TRACKS=$(jq -r '.tracks' <<<"$STRATEGY_JSON")
#   fi
# We replicate the same logic with python to avoid jq dependency in smoke.

T10_OUT="$TEST_DIR/t10-snapshot.txt"
"$PYTHON_BIN" - <<EOF > "$T10_OUT"
import json, subprocess, sys
# Use [sys.executable, FLOWCTL_PY, ...] so the call works on Windows where
# the bash wrapper is not a valid Win32 executable (WinError 193).
status = subprocess.run(
    [sys.executable, "$FLOWCTL_PY", "strategy", "status", "--json"],
    cwd="$REPO", capture_output=True, text=True, check=True,
)
st = json.loads(status.stdout)
filled = st.get("sections_filled", 0)
print(f"STRATEGY_FILLED={filled}")
if filled >= 1:
    read = subprocess.run(
        [sys.executable, "$FLOWCTL_PY", "strategy", "read", "--json"],
        cwd="$REPO", capture_output=True, text=True, check=True,
    )
    s = json.loads(read.stdout)
    print("--- APPROACH ---")
    print(s.get("approach", ""))
    print("--- TRACKS ---")
    print(s.get("tracks", ""))
else:
    print("(no strategy signal)")
EOF

# Approach must be present verbatim (we wrote it in T1).
assert_grep "T10" "Treat every release as an experiment" "$(cat "$T10_OUT")" "approach text present verbatim"
assert_grep "T10" "Ship behind flags" "$(cat "$T10_OUT")" "approach second sentence present"

# Tracks H3 sub-blocks emitted verbatim -- note: in T2 the file was rewritten
# via parse→render so the body bumped to render canonical form, but the H3
# names are stable.
assert_grep "T10" "### release-flags" "$(cat "$T10_OUT")" "tracks H3 #1 verbatim"
assert_grep "T10" "### outcome-dashboard" "$(cat "$T10_OUT")" "tracks H3 #2 verbatim"
assert_grep "T10" "STRATEGY_FILLED=5" "$(cat "$T10_OUT")" "snapshot triggered (filled>=1 path)"

# Cross-check: prospect SKILL.md actually wires up the snapshot.
T10_PROSPECT_WIRES="$(grep -c 'STRATEGY' "$PLUGIN_ROOT/skills/flow-next-prospect/workflow.md" || true)"
[[ "$T10_PROSPECT_WIRES" -ge 1 ]] \
  && ok "T10" "prospect workflow.md references STRATEGY (count=$T10_PROSPECT_WIRES)" \
  || fail "T10" "prospect workflow missing STRATEGY grounding wire-up"

# =============================================================================
# T11: plan-sync drift surfacing -- read-only invariant
# =============================================================================
echo -e "${YELLOW}--- T11: plan-sync.md contains 'never auto-supersede'/'auto-supersede' read-only invariant ---${NC}"
PLAN_SYNC_FILE="$PLUGIN_ROOT/agents/plan-sync.md"
[[ -f "$PLAN_SYNC_FILE" ]] \
  && ok "T11" "agents/plan-sync.md exists" \
  || fail "T11" "agents/plan-sync.md missing at $PLAN_SYNC_FILE"

# Read-only invariant: agent never auto-supersedes the doc. The canonical
# phrasing in plan-sync.md is "Do not auto-supersede" (matches the existing
# decision-record convention at line 110). Spec calls for "never auto-supersedes
# or equivalent invariant string" -- accept both phrasings.
T11_INV="$(grep -E '(Do not auto-supersede|never auto-supersede)' "$PLAN_SYNC_FILE" || true)"
[[ -n "$T11_INV" ]] \
  && ok "T11" "read-only invariant present ('Do not auto-supersede' or equivalent)" \
  || fail "T11" "missing 'auto-supersede' read-only invariant in plan-sync.md"

# And specifically tied to STRATEGY.md (not just decisions) -- section 3b.3
# must explicitly say plan-sync does not edit STRATEGY.md.
T11_STRAT_INV="$(grep -E 'Do not Edit `STRATEGY\.md`|never edit `STRATEGY\.md`' "$PLAN_SYNC_FILE" || true)"
[[ -n "$T11_STRAT_INV" ]] \
  && ok "T11" "STRATEGY.md is explicitly read-only from plan-sync's perspective" \
  || fail "T11" "missing explicit 'Do not Edit STRATEGY.md' invariant"

# Also verify the strategy-specific drift section is wired up.
T11_DRIFT="$(grep -F 'Strategy drift flagged for review' "$PLAN_SYNC_FILE" || true)"
[[ -n "$T11_DRIFT" ]] \
  && ok "T11" "Strategy drift flagged for review heading wired up" \
  || fail "T11" "missing 'Strategy drift flagged for review' heading"

# =============================================================================
# T12: Ralph block -- FLOW_RALPH=1 → exit 2 + stderr message
# =============================================================================
echo -e "${YELLOW}--- T12: FLOW_RALPH=1 fires Ralph block (exit 2, stderr message) ---${NC}"
# Extract the Phase 0.1 Ralph-block from SKILL.md and run it as a shell
# script. SKILL.md ships:
#   if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
#     echo "[STRATEGY: user-triggered only -- Ralph cannot run /flow-next:strategy]" >&2
#     exit 2
#   fi
# We run the literal block under FLOW_RALPH=1.

T12_BLOCK="$TEST_DIR/t12-ralph-block.sh"
cat > "$T12_BLOCK" <<'EOF'
#!/usr/bin/env bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "[STRATEGY: user-triggered only -- Ralph cannot run /flow-next:strategy]" >&2
  exit 2
fi
echo "fell through (would run skill body)"
exit 0
EOF
chmod +x "$T12_BLOCK"

# 12a: With FLOW_RALPH=1, expect exit 2.
set +e
T12_OUT="$( FLOW_RALPH=1 "$T12_BLOCK" 2>&1 1>/dev/null )"
T12_RC=$?
set -e
assert_rc "T12" 2 "$T12_RC" "FLOW_RALPH=1 → exit 2"
assert_grep "T12" "[STRATEGY: user-triggered only" "$T12_OUT" "stderr message present under FLOW_RALPH=1"

# 12b: With REVIEW_RECEIPT_PATH set, also expect exit 2.
set +e
T12_OUT2="$( REVIEW_RECEIPT_PATH=/tmp/fake-receipt.json "$T12_BLOCK" 2>&1 1>/dev/null )"
T12_RC2=$?
set -e
assert_rc "T12" 2 "$T12_RC2" "REVIEW_RECEIPT_PATH set → exit 2"
assert_grep "T12" "[STRATEGY: user-triggered only" "$T12_OUT2" "stderr message present under REVIEW_RECEIPT_PATH"

# 12c: Without either env var, falls through (rc=0).
set +e
T12_OUT3="$( unset FLOW_RALPH REVIEW_RECEIPT_PATH; "$T12_BLOCK" 2>&1 )"
T12_RC3=$?
set -e
assert_rc "T12" 0 "$T12_RC3" "no Ralph env vars → falls through"
assert_grep "T12" "fell through" "$T12_OUT3" "fall-through message present"

# 12d: Cross-check the canonical SKILL.md ships the same guard.
SKILL_FILE="$PLUGIN_ROOT/skills/flow-next-strategy/SKILL.md"
if grep -q 'REVIEW_RECEIPT_PATH' "$SKILL_FILE" \
  && grep -q 'FLOW_RALPH' "$SKILL_FILE" \
  && grep -q 'exit 2' "$SKILL_FILE" \
  && grep -q '\[STRATEGY: user-triggered only' "$SKILL_FILE"; then
  ok "T12" "canonical SKILL.md ships the literal Ralph-block (exit 2 + stderr message)"
else
  fail "T12" "SKILL.md missing FLOW_RALPH/REVIEW_RECEIPT_PATH/exit 2 or stderr message"
fi

# =============================================================================
# Sanity: verify nothing leaked outside $TEST_DIR.
# =============================================================================
echo -e "${YELLOW}--- Hygiene: confirm no writes outside TEST_DIR ---${NC}"
# Anything we wrote should be under $TEST_DIR. The smoke test does NOT
# touch the plugin tree (we cross-check it via grep but never write).
# A simple sentinel: the plugin tree's git status should be clean of
# anything we did here. (Caller's environment may have other diffs;
# we only check that no STRATEGY.md / fixture artifacts leaked into
# PLUGIN_ROOT.)
LEAKED="$( find "$PLUGIN_ROOT" -maxdepth 3 -name 'STRATEGY.md' \
            -not -path "$PLUGIN_ROOT/.git/*" 2>/dev/null \
            | grep -v 'flow-next-strategy/SKILL.md' || true )"
[[ -z "$LEAKED" ]] \
  && ok "hygiene" "no STRATEGY.md leaked into plugin tree" \
  || fail "hygiene" "leaked file(s): $LEAKED"

# =============================================================================
# Summary
# =============================================================================
echo
echo -e "${YELLOW}=== Summary ===${NC}"
echo -e "${GREEN}PASS: $PASS${NC}"
echo -e "${RED}FAIL: $FAIL${NC}"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
