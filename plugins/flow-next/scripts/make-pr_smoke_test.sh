#!/usr/bin/env bash
# fn-42-flow-nextmake-pr-pr-as-cognitive-aid.7
# Smoke tests for `flowctl spec export-cognitive-aid` aggregator (Task 1)
# and the /flow-next:make-pr skill body-rendering / --dry-run plumbing.
#
# This is the LATE PROOF POINT for fn-42. Tasks 1-6 land the flowctl
# subcommand + skill body rendering; this test fires after them to confirm
# the export plumbing and (where applicable) the skill scaffold are wired.
#
# Cases (T1-T11 from spec R29):
#   T1.  `flowctl spec export-cognitive-aid <epic> --base main --json` returns
#        valid JSON with all top-level keys.
#   T2.  (removed fn-111: --section export filter deleted)
#        without flag.
#   T3.  `diff_summary.files[]` populated; per-file additions/deletions match
#        `git diff --numstat`.
#   T4.  `memory_during_epic` includes seeded decisions/bugs/architecture-patterns
#        entries.
#   T5.  `glossary_changes.added[]` includes a new term added in HEAD vs base.
#   T6.  `strategy_alignment.tracks_served[]` populated when STRATEGY.md
#        present and the spec carries a `## Strategy Alignment` section.
#   T7.  Empty-epic handling — epic with 0 tasks → `tasks_summary.total: 0`,
#        `done: 0`. Subcommand exits 0 (graceful).
#   T8.  All-empty optional inputs (no STRATEGY.md / no memory / no glossary
#        / no deferred) → all empty arrays, no crash, exits 0.
#   T9.  Branch-no-commits-ahead → `diff_summary.files: []` (no error).
#   T10. Skill `--dry-run` produces stdout output containing `## TL;DR`,
#        `## R-ID coverage`, `## Critical changes` markers (loose match).
#        SKIPS as deferred-to-manual today: skill is interactive markdown
#        with `AskUserQuestion` blocking tools — not unit-shell-testable.
#        We assert the canonical skill prose carries the required section
#        markers (so the rendered body necessarily contains them).
#   T11. Mermaid trigger logic — fixture with cross-module imports
#        produces `cross_module_changes` non-empty (the trigger that gates
#        the skill's mermaid emission). The codefence emission itself is
#        the skill's job; we test the export-side trigger signal.
#
# Pure shell + Python harness — no LLM invocations. Targets <60s runtime.
# Pattern follows strategy_smoke_test.sh (fn-39.6) and prospect_smoke_test.sh (fn-33.6).
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

# shellcheck source=lib/pick-python.sh
. "$SCRIPT_DIR/lib/pick-python.sh"
pick_python || { echo "ERROR: python not found (need python3 or python in PATH)" >&2; exit 1; }

# Safety: never run from the main plugin repo (matches sibling smoke scripts).
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/make-pr-smoke-$$}"
# Normalize Windows backslashes from $RUNNER_TEMP to forward slashes
# so paths interpolated into `python -c "..."` source code are not
# corrupted by Python escape parsing (e.g. `D:\a\_temp` → `D:<bell>...`).
# Windows accepts forward-slash paths natively; no-op on Linux/macOS.
TEST_DIR="${TEST_DIR//\\//}"
PASS=0
FAIL=0
SKIP=0

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
skip() { echo -e "${YELLOW}$1: SKIP${NC} $2"; SKIP=$((SKIP + 1)); }

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
  "${FLOW_PY[@]}" -c "import json; d=json.load(open(r'$file')); print($expr)" 2>&1 | tr -d '\r' || true
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

# Build a comprehensive fixture repo:
#   - git repo on `main` branch with initial commit
#   - flowctl init + memory enabled + memory init
#   - 1 epic with 3 R-IDs (R1, R2, R3) and `## Strategy Alignment` section
#   - 2 done tasks with done_summary + evidence.commits (real commits)
#   - 1 decision memory entry (knowledge/decisions/)
#   - 1 bug memory entry (bug/runtime-errors/)
#   - 1 architecture-patterns entry (knowledge/architecture-patterns/)
#   - GLOSSARY.md with 1 base term + 1 added on a feature branch (HEAD vs base diff)
#   - STRATEGY.md with 5 sections + tracks `track-alpha`/`track-beta`
#   - 1 deferred review finding at `.flow/review-deferred/<branch-slug>.md`
#   - Multi-file diff with cross-module imports
build_fixture() {
  local repo="$1"
  mkdir -p "$repo"
  (
    cd "$repo"
    git init -q
    git config user.email "make-pr-smoke@example.com"
    git config user.name "Make-PR Smoke"
    git checkout -b main >/dev/null 2>&1 || git branch -m main >/dev/null 2>&1 || true
    git commit --allow-empty -m "init" -q

    # flowctl init + memory enabled
    "$FLOWCTL" init --json >/dev/null
    "$FLOWCTL" config set memory.enabled true --json >/dev/null
    "$FLOWCTL" memory init --json >/dev/null

    # STRATEGY.md (5 sections, generator sentinel, 2 tracks)
    cat > STRATEGY.md <<'EOF'
---
name: SmokeApp
last_updated: '2026-04-30'
generator: flow-next-strategy
---

# SmokeApp Strategy

## Target problem
Small repos drift fast.

## Our approach
Lock invariants in tests; ship as soon as green.

## Who it's for
**Primary:** repo maintainers.

## Key metrics
- **green-ci-rate** -- percent.

## Tracks
### track-alpha
Investment area alpha.

### track-beta
Investment area beta.
EOF

    # GLOSSARY.md (base term only on main)
    "$FLOWCTL" glossary add "BaseTerm" --definition "A baseline term defined on main." --json >/dev/null

    # Seed a SECOND glossary file at a subdir on main so the feature branch
    # can delete it whole-file (PR #131 follow-up reproducer T14): glossary
    # deletions vs base must surface in `glossary_changes.removed[]`.
    mkdir -p apps/legacy
    cat > apps/legacy/GLOSSARY.md <<'EOF'
# Glossary

## LegacyGlossaryTerm

A term defined only at base in apps/legacy; the feature branch deletes the whole file.
EOF

    # Seed a public-export file on main so the feature branch can delete it
    # and exercise `_export_detect_public_exports` deletion handling.
    mkdir -p src/legacy_pkg
    cat > src/legacy_pkg/__init__.py <<'EOF'
"""Legacy package public surface — deleted on feature branch for smoke test."""

def legacy_one():
    return 1


def legacy_two():
    return 2


class LegacyClass:
    pass
EOF
    git add -A
    git commit -m "main: seed STRATEGY + GLOSSARY base term + legacy_pkg surface" -q

    # Capture base SHA for the diff calculation
    git tag fixture-base

    # Switch to a feature branch so HEAD diverges from main for the
    # diff_summary calculation (`--base main` walks merge-base..HEAD).
    git checkout -b fixture-feature -q

    # Create epic + spec
    EPIC_RAW="$("$FLOWCTL" spec create --title "Smoke fixture epic" --json)"
    EPIC_ID="$(echo "$EPIC_RAW" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
    echo "$EPIC_ID" > "$repo/.epic_id"

    # Set epic spec with 3 R-IDs and Strategy Alignment section. Use a
    # quoted heredoc so triple-backticks inside the spec body do not
    # trigger shell command substitution.
    cat > /tmp/make-pr-smoke-spec.md <<'EOF'
# Smoke fixture epic

## Goal & Context

A fixture epic for the make-pr smoke test. It exists to exercise the export-cognitive-aid aggregator end-to-end against a known-state repo.

## Architecture & Data Models

A small two-module fixture with a cross-module import.

## Acceptance Criteria

- **R1:** A baseline criterion. [paraphrase]
- **R2:** A second criterion. [paraphrase]
- **R3:** A third criterion. [paraphrase]

## Strategy Alignment

- track-alpha
- track-beta

## Boundaries

- Out of scope: actually shipping anything.
EOF
    "$FLOWCTL" spec set-plan "$EPIC_ID" --file /tmp/make-pr-smoke-spec.md --json >/dev/null
    rm -f /tmp/make-pr-smoke-spec.md

    # Create + complete 2 tasks (each with one real evidence commit)
    T1_RAW="$("$FLOWCTL" task create --spec "$EPIC_ID" --title "First task" --json)"
    T1_ID="$(echo "$T1_RAW" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

    # Create cross-module changes via two new files in different module roots.
    mkdir -p src/mod_a src/mod_b
    cat > src/mod_a/foo.py <<'EOF'
"""Module A foo file."""

def foo():
    return "foo"
EOF
    cat > src/mod_b/bar.py <<'EOF'
"""Module B bar file."""
from src.mod_a.foo import foo

def bar():
    return foo() + "bar"
EOF
    git add -A
    T1_COMMIT="$(git commit -m "feat: add mod_a/foo + mod_b/bar (cross-module import)" -q && git rev-parse HEAD)"

    "$FLOWCTL" start "$T1_ID" --json >/dev/null
    cat > /tmp/make-pr-smoke-t1-summary.md <<'EOF'
Added mod_a/foo and mod_b/bar (cross-module import).
EOF
    cat > /tmp/make-pr-smoke-t1-evidence.json <<EOF
{"commits": ["$T1_COMMIT"], "tests": [], "files_touched": ["src/mod_a/foo.py", "src/mod_b/bar.py"]}
EOF
    "$FLOWCTL" done "$T1_ID" \
      --summary-file /tmp/make-pr-smoke-t1-summary.md \
      --evidence-json /tmp/make-pr-smoke-t1-evidence.json \
      --json >/dev/null
    rm -f /tmp/make-pr-smoke-t1-summary.md /tmp/make-pr-smoke-t1-evidence.json

    # Add `satisfies: [R1]` to T1 spec
    T1_SPEC=".flow/tasks/$T1_ID.md"
    if [[ -f "$T1_SPEC" ]]; then
      # Insert satisfies frontmatter at the top
      "${FLOW_PY[@]}" - "$T1_SPEC" "R1" <<'PYEOF'
import sys, pathlib
path = pathlib.Path(sys.argv[1])
rid = sys.argv[2]
content = path.read_text()
fm = f"---\nsatisfies: [{rid}]\n---\n\n"
if content.startswith("---"):
    # already has frontmatter — splice in satisfies
    end = content.find("\n---", 3)
    if end > 0:
        head = content[:end]
        tail = content[end:]
        if "satisfies:" not in head:
            head += f"\nsatisfies: [{rid}]"
        path.write_text(head + tail)
        sys.exit(0)
path.write_text(fm + content)
PYEOF
      git add -A
      git commit -m "task: $T1_ID satisfies $T1_ID:R1" -q >/dev/null
    fi

    # T2 — second task, second commit
    T2_RAW="$("$FLOWCTL" task create --spec "$EPIC_ID" --title "Second task" --json)"
    T2_ID="$(echo "$T2_RAW" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
    cat > src/mod_a/baz.py <<'EOF'
"""Module A baz file."""

def baz():
    return "baz"
EOF
    git add -A
    T2_COMMIT="$(git commit -m "feat: add mod_a/baz" -q && git rev-parse HEAD)"

    "$FLOWCTL" start "$T2_ID" --json >/dev/null
    cat > /tmp/make-pr-smoke-t2-summary.md <<'EOF'
Added mod_a/baz.
EOF
    cat > /tmp/make-pr-smoke-t2-evidence.json <<EOF
{"commits": ["$T2_COMMIT"], "tests": [], "files_touched": ["src/mod_a/baz.py"]}
EOF
    "$FLOWCTL" done "$T2_ID" \
      --summary-file /tmp/make-pr-smoke-t2-summary.md \
      --evidence-json /tmp/make-pr-smoke-t2-evidence.json \
      --json >/dev/null
    rm -f /tmp/make-pr-smoke-t2-summary.md /tmp/make-pr-smoke-t2-evidence.json

    # Add satisfies frontmatter to T2 spec for R2
    T2_SPEC=".flow/tasks/$T2_ID.md"
    if [[ -f "$T2_SPEC" ]]; then
      "${FLOW_PY[@]}" - "$T2_SPEC" "R2" <<'PYEOF'
import sys, pathlib
path = pathlib.Path(sys.argv[1])
rid = sys.argv[2]
content = path.read_text()
if content.startswith("---"):
    end = content.find("\n---", 3)
    if end > 0:
        head = content[:end]
        tail = content[end:]
        if "satisfies:" not in head:
            head += f"\nsatisfies: [{rid}]"
        path.write_text(head + tail)
        sys.exit(0)
fm = f"---\nsatisfies: [{rid}]\n---\n\n"
path.write_text(fm + content)
PYEOF
      git add -A
      git commit -m "task: $T2_ID satisfies $T2_ID:R2" -q >/dev/null
    fi

    # Memory entries
    cat > /tmp/make-pr-smoke-decision-body.md <<'EOF'
## Decision
Use cross-module imports between mod_a and mod_b for the smoke fixture.

## Alternatives considered
- Single-module fixture (rejected: misses module-boundary signal).
EOF
    "$FLOWCTL" memory add \
      --track knowledge --category decisions \
      --title "Cross-module fixture for smoke test" \
      --module "src" --tags "smoke,fixture" \
      --decision-status accepted \
      --body-file /tmp/make-pr-smoke-decision-body.md \
      --json >/dev/null
    rm -f /tmp/make-pr-smoke-decision-body.md

    cat > /tmp/make-pr-smoke-bug-body.md <<'EOF'
## Symptoms
Sample bug observed during fixture build.

## Root cause
Sample root cause.

## Fix
Sample fix.
EOF
    "$FLOWCTL" memory add \
      --track bug --category runtime-errors \
      --title "Sample runtime bug surfaced by fixture" \
      --module "src/mod_a/foo.py" --tags "smoke,bug" \
      --root-cause "Sample root cause" \
      --symptoms "Sample symptom" \
      --body-file /tmp/make-pr-smoke-bug-body.md \
      --json >/dev/null
    rm -f /tmp/make-pr-smoke-bug-body.md

    cat > /tmp/make-pr-smoke-pattern-body.md <<'EOF'
## Pattern
Cross-module import isolation: keep public surface in `__init__.py`, never reach across.

## Applies when
Two modules need to share state.
EOF
    "$FLOWCTL" memory add \
      --track knowledge --category architecture-patterns \
      --title "Cross-module import isolation pattern" \
      --module "src" --tags "architecture,smoke" \
      --body-file /tmp/make-pr-smoke-pattern-body.md \
      --json >/dev/null
    rm -f /tmp/make-pr-smoke-pattern-body.md

    # Glossary: add a NEW term on the feature branch (HEAD vs base diff signal)
    "$FLOWCTL" glossary add "FixtureTerm" \
      --definition "A term added on the feature branch for diff signal." --json >/dev/null
    git add -A
    git commit -m "docs: add FixtureTerm to GLOSSARY.md" -q >/dev/null

    # Nested subdirectory glossary added entirely on the feature branch
    # (PR #131 review reproducer): subdir glossary deltas must surface in
    # `glossary_changes.added[]` — `find_all_glossaries(repo_root)` walks
    # ancestors of repo_root and returns just the root, missing this file.
    mkdir -p apps/web
    cat > apps/web/GLOSSARY.md <<'EOF'
# Glossary

## NestedTerm

A term defined only in the apps/web subdirectory glossary.
EOF
    git add -A
    git commit -m "docs: add apps/web/GLOSSARY.md (nested glossary)" -q >/dev/null

    # Delete the base-only glossary file at apps/legacy/GLOSSARY.md so the
    # diff exercises the whole-file glossary deletion path (PR #131 T14).
    # Pre-fix: HEAD walk skips deleted files entirely, so `LegacyGlossaryTerm`
    # never lands in `removed[]`. Post-fix: union with `git ls-tree` at
    # merge-base surfaces the deletion.
    git rm -q apps/legacy/GLOSSARY.md
    rmdir apps/legacy 2>/dev/null || true
    git commit -m "docs: delete apps/legacy/GLOSSARY.md (whole-file glossary deletion)" -q >/dev/null

    # Delete the seeded public-export file so the diff exercises the
    # `+++ /dev/null` deletion path in `_export_detect_public_exports`.
    git rm -q src/legacy_pkg/__init__.py
    rmdir src/legacy_pkg 2>/dev/null || true
    git commit -m "feat: drop legacy_pkg public surface" -q >/dev/null

    # Deferred review finding
    EPIC_BRANCH="$("$FLOWCTL" show "$EPIC_ID" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin).get("branch_name") or "")')"
    BRANCH_SLUG="${EPIC_BRANCH:-fixture-branch}"
    mkdir -p .flow/review-deferred
    cat > ".flow/review-deferred/$BRANCH_SLUG.md" <<EOF
# Deferred review findings — $BRANCH_SLUG

- [ ] (P2) Sample deferred finding from impl-review of $T1_ID.
EOF
    git add -A
    git commit -m "chore: deferred review finding placeholder" -q >/dev/null
  )
}

echo -e "${YELLOW}=== make-pr smoke tests (fn-42.7) ===${NC}"
echo "Plugin root: $PLUGIN_ROOT"
echo "Test dir:    $TEST_DIR"
echo

mkdir -p "$TEST_DIR"

REPO="$TEST_DIR/repo"
build_fixture "$REPO"

EPIC_ID="$(cat "$REPO/.epic_id")"
[[ -n "$EPIC_ID" ]] || { echo "ERROR: fixture failed — no epic id captured" >&2; exit 1; }
echo "Fixture epic: $EPIC_ID"
echo

# =============================================================================
# T1: Full payload — all top-level keys present, exit 0, valid JSON
# =============================================================================
echo -e "${YELLOW}--- T1: full payload — top-level keys + valid JSON ---${NC}"
T1_OUT="$TEST_DIR/t1-full.json"
set +e
( cd "$REPO" && "$FLOWCTL" spec export-cognitive-aid "$EPIC_ID" --base main --json > "$T1_OUT" )
T1_RC=$?
set -e
assert_rc "T1" 0 "$T1_RC" "export-cognitive-aid full payload exits 0"

# Validate JSON
"${FLOW_PY[@]}" -c "import json; json.load(open('$T1_OUT'))" 2>/dev/null \
  && ok "T1" "stdout is valid JSON" \
  || fail "T1" "stdout is NOT valid JSON"

# Top-level key presence: required by spec architecture (canonical "spec" key
# from fn-43.2 R31 dual-emit; legacy "epic" co-emit is verified separately
# in alias_smoke.sh Case 4).
for key in spec tasks tasks_summary memory_during_epic glossary_changes \
           strategy_alignment diff_summary deferred_findings; do
  assert_eq_jq "T1" "$T1_OUT" "'$key' in d" "True" "top-level key '$key' present"
done

# spec.id matches the fixture
T1_EPIC_ID="$(json_get "$T1_OUT" "d['spec']['id']")"
[[ "$T1_EPIC_ID" == "$EPIC_ID" ]] \
  && ok "T1" "spec.id roundtrips ($T1_EPIC_ID)" \
  || fail "T1" "spec.id expected $EPIC_ID, got $T1_EPIC_ID"

# tasks_summary correct: 2 done, 0 open
assert_eq_jq "T1" "$T1_OUT" "d['tasks_summary']['total']" "2" "tasks_summary.total == 2"
assert_eq_jq "T1" "$T1_OUT" "d['tasks_summary']['done']"  "2" "tasks_summary.done == 2"
assert_eq_jq "T1" "$T1_OUT" "d['tasks_summary']['open']"  "0" "tasks_summary.open == 0"

# =============================================================================
# T3: diff_summary.files[] populated with cross-module changes
# =============================================================================
echo -e "${YELLOW}--- T3: diff_summary.files[] populated; counts match git numstat ---${NC}"
T3_FILES_COUNT="$(json_get "$T1_OUT" "len(d['diff_summary']['files'])")"
[[ "$T3_FILES_COUNT" -ge 3 ]] \
  && ok "T3" "diff_summary.files has $T3_FILES_COUNT entries (>=3)" \
  || fail "T3" "expected >=3 files in diff (mod_a/foo, mod_b/bar, mod_a/baz, glossary, deferred), got $T3_FILES_COUNT"

# Specifically: src/mod_a/foo.py + src/mod_b/bar.py + src/mod_a/baz.py present
for path in "src/mod_a/foo.py" "src/mod_b/bar.py" "src/mod_a/baz.py"; do
  T3_FOUND="$(json_get "$T1_OUT" "any(f['path'] == '$path' for f in d['diff_summary']['files'])")"
  [[ "$T3_FOUND" == "True" ]] \
    && ok "T3" "$path present in diff_summary.files" \
    || fail "T3" "$path missing from diff_summary.files"
done

# Per-file additions/deletions: cross-check vs git numstat
T3_FOO_ADDS="$(json_get "$T1_OUT" "next(f['additions'] for f in d['diff_summary']['files'] if f['path']=='src/mod_a/foo.py')")"
T3_GIT_ADDS="$( cd "$REPO" && git diff --numstat main..HEAD -- src/mod_a/foo.py | awk '{print $1}' )"
[[ "$T3_FOO_ADDS" == "$T3_GIT_ADDS" ]] \
  && ok "T3" "src/mod_a/foo.py additions match git numstat ($T3_FOO_ADDS)" \
  || fail "T3" "additions mismatch: export=$T3_FOO_ADDS, git=$T3_GIT_ADDS"

# diff_summary.cross_module_changes non-empty (mod_a / mod_b boundary crossing)
T3_XM_COUNT="$(json_get "$T1_OUT" "len(d['diff_summary']['cross_module_changes'])")"
[[ "$T3_XM_COUNT" -ge 1 ]] \
  && ok "T3" "cross_module_changes has $T3_XM_COUNT entries (>=1)" \
  || fail "T3" "expected >=1 cross-module change (mod_a→mod_b), got $T3_XM_COUNT"

# =============================================================================
# T4: memory_during_epic includes seeded entries
# =============================================================================
echo -e "${YELLOW}--- T4: memory_during_epic — decisions / bugs / architecture_patterns ---${NC}"
T4_DEC_COUNT="$(json_get "$T1_OUT" "len(d['memory_during_epic']['decisions'])")"
T4_BUG_COUNT="$(json_get "$T1_OUT" "len(d['memory_during_epic']['bugs'])")"
T4_ARCH_COUNT="$(json_get "$T1_OUT" "len(d['memory_during_epic']['architecture_patterns'])")"

[[ "$T4_DEC_COUNT" -ge 1 ]] \
  && ok "T4" "decisions[] has $T4_DEC_COUNT entries (>=1)" \
  || fail "T4" "expected >=1 decision entry, got $T4_DEC_COUNT"
[[ "$T4_BUG_COUNT" -ge 1 ]] \
  && ok "T4" "bugs[] has $T4_BUG_COUNT entries (>=1)" \
  || fail "T4" "expected >=1 bug entry, got $T4_BUG_COUNT"
[[ "$T4_ARCH_COUNT" -ge 1 ]] \
  && ok "T4" "architecture_patterns[] has $T4_ARCH_COUNT entries (>=1)" \
  || fail "T4" "expected >=1 architecture-patterns entry, got $T4_ARCH_COUNT"

# Verify the seeded title round-trips
T4_DEC_TITLE="$(json_get "$T1_OUT" "d['memory_during_epic']['decisions'][0]['title']")"
[[ "$T4_DEC_TITLE" == "Cross-module fixture for smoke test" ]] \
  && ok "T4" "decision title round-trips ('$T4_DEC_TITLE')" \
  || fail "T4" "decision title mismatch: got '$T4_DEC_TITLE'"

T4_BUG_TITLE="$(json_get "$T1_OUT" "d['memory_during_epic']['bugs'][0]['title']")"
[[ "$T4_BUG_TITLE" == "Sample runtime bug surfaced by fixture" ]] \
  && ok "T4" "bug title round-trips ('$T4_BUG_TITLE')" \
  || fail "T4" "bug title mismatch: got '$T4_BUG_TITLE'"

# =============================================================================
# T5: glossary_changes.added[] includes FixtureTerm (new in HEAD vs main)
# =============================================================================
echo -e "${YELLOW}--- T5: glossary_changes.added[] includes new term ---${NC}"
T5_ADDED_COUNT="$(json_get "$T1_OUT" "len(d['glossary_changes']['added'])")"
[[ "$T5_ADDED_COUNT" -ge 1 ]] \
  && ok "T5" "glossary_changes.added has $T5_ADDED_COUNT entries (>=1)" \
  || fail "T5" "expected >=1 added term, got $T5_ADDED_COUNT"

# Specifically `FixtureTerm` should be present
T5_HAS_FIXTURETERM="$(json_get "$T1_OUT" "any('FixtureTerm' in (a.get('term') or '') for a in d['glossary_changes']['added'])")"
[[ "$T5_HAS_FIXTURETERM" == "True" ]] \
  && ok "T5" "'FixtureTerm' present in glossary_changes.added" \
  || fail "T5" "'FixtureTerm' missing from glossary_changes.added"

# removed[] has exactly 1 entry — the deleted apps/legacy/GLOSSARY.md
# `LegacyGlossaryTerm` (T14 reproducer). No other removals expected.
assert_eq_jq "T5" "$T1_OUT" "len(d['glossary_changes']['removed'])" "1" "glossary_changes.removed has exactly 1 entry (LegacyGlossaryTerm)"

# =============================================================================
# T6: strategy_alignment.tracks_served[] populated when STRATEGY.md present
# =============================================================================
echo -e "${YELLOW}--- T6: strategy_alignment.tracks_served populated ---${NC}"
T6_TRACKS_COUNT="$(json_get "$T1_OUT" "len(d['strategy_alignment']['tracks_served'])")"
[[ "$T6_TRACKS_COUNT" -ge 2 ]] \
  && ok "T6" "tracks_served has $T6_TRACKS_COUNT entries (>=2)" \
  || fail "T6" "expected >=2 tracks (track-alpha, track-beta), got $T6_TRACKS_COUNT"

# Specific track names round-trip
for track in "track-alpha" "track-beta"; do
  T6_HAS="$(json_get "$T1_OUT" "'$track' in d['strategy_alignment']['tracks_served']")"
  [[ "$T6_HAS" == "True" ]] \
    && ok "T6" "track '$track' in tracks_served" \
    || fail "T6" "track '$track' missing from tracks_served"
done

# =============================================================================
# T7: Empty-epic handling — epic with 0 tasks
# =============================================================================
echo -e "${YELLOW}--- T7: empty epic (0 tasks) — graceful, exits 0 ---${NC}"
EMPTY_REPO="$TEST_DIR/empty-repo"
mkdir -p "$EMPTY_REPO"
(
  cd "$EMPTY_REPO"
  git init -q
  git config user.email "make-pr-smoke@example.com"
  git config user.name "Make-PR Smoke"
  git checkout -b main >/dev/null 2>&1 || git branch -m main >/dev/null 2>&1 || true
  git commit --allow-empty -m "init" -q
  "$FLOWCTL" init --json >/dev/null

  EPIC_RAW="$("$FLOWCTL" spec create --title "Empty epic" --json)"
  EPIC_ID_E="$(echo "$EPIC_RAW" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  echo "$EPIC_ID_E" > .epic_id

  # Set spec with 1 R-ID so we have an uncovered_r_ids check
  cat > /tmp/empty-spec.md <<'EOF'
# Empty epic

## Goal & Context
No tasks yet.

## Acceptance Criteria
- **R1:** Will be added later. [paraphrase]
EOF
  "$FLOWCTL" spec set-plan "$EPIC_ID_E" --file /tmp/empty-spec.md --json >/dev/null
  rm -f /tmp/empty-spec.md
)
EMPTY_EPIC_ID="$(cat "$EMPTY_REPO/.epic_id")"

T7_OUT="$TEST_DIR/t7-empty.json"
set +e
( cd "$EMPTY_REPO" && "$FLOWCTL" spec export-cognitive-aid "$EMPTY_EPIC_ID" --base main --json > "$T7_OUT" )
T7_RC=$?
set -e
assert_rc "T7" 0 "$T7_RC" "empty epic export exits 0"

assert_eq_jq "T7" "$T7_OUT" "d['tasks_summary']['total']" "0" "empty epic: tasks_summary.total == 0"
assert_eq_jq "T7" "$T7_OUT" "d['tasks_summary']['done']"  "0" "empty epic: tasks_summary.done == 0"
assert_eq_jq "T7" "$T7_OUT" "d['tasks_summary']['open']"  "0" "empty epic: tasks_summary.open == 0"

# uncovered_r_ids should include R1 (criterion exists, no satisfying task)
T7_UNCOVERED="$(json_get "$T7_OUT" "d['tasks_summary']['uncovered_r_ids']")"
assert_grep "T7" "R1" "$T7_UNCOVERED" "uncovered_r_ids contains R1"

# =============================================================================
# T8: All-empty optional inputs — no STRATEGY/glossary/memory/deferred
# =============================================================================
echo -e "${YELLOW}--- T8: all-empty optional inputs — no crash, empty arrays ---${NC}"
# Same as T7 (empty repo has no STRATEGY.md, no glossary, no memory entries, no deferred review)
assert_eq_jq "T8" "$T7_OUT" "len(d['memory_during_epic']['decisions'])" "0" "no memory: decisions[] empty"
assert_eq_jq "T8" "$T7_OUT" "len(d['memory_during_epic']['bugs'])" "0" "no memory: bugs[] empty"
assert_eq_jq "T8" "$T7_OUT" "len(d['memory_during_epic']['architecture_patterns'])" "0" "no memory: architecture_patterns[] empty"
assert_eq_jq "T8" "$T7_OUT" "len(d['glossary_changes']['added'])" "0" "no glossary: added[] empty"
assert_eq_jq "T8" "$T7_OUT" "len(d['glossary_changes']['removed'])" "0" "no glossary: removed[] empty"
assert_eq_jq "T8" "$T7_OUT" "len(d['strategy_alignment']['tracks_served'])" "0" "no STRATEGY.md: tracks_served[] empty"
assert_eq_jq "T8" "$T7_OUT" "len(d['deferred_findings'])" "0" "no deferred review: deferred_findings[] empty"

# T8 (cont.): full-fixture deferred_findings[].path is repo-relative POSIX,
# not absolute, so the breadcrumb stays usable for remote PR reviewers and
# doesn't leak machine-specific filesystem paths into the rendered body.
assert_eq_jq "T8" "$T1_OUT" "len(d['deferred_findings']) >= 1" "True" \
  "fixture deferred_findings[] non-empty"
T8_DEFER_PATH="$(json_get "$T1_OUT" "d['deferred_findings'][0]['path']")"
case "$T8_DEFER_PATH" in
  /*) fail "T8" "deferred_findings[0].path is absolute (got: $T8_DEFER_PATH)" ;;
  [A-Za-z]:[/\\]*) fail "T8" "deferred_findings[0].path is Windows-absolute (got: $T8_DEFER_PATH)" ;;
  "") fail "T8" "deferred_findings[0].path is empty" ;;
  *) ok "T8" "deferred_findings[0].path is repo-relative ($T8_DEFER_PATH)" ;;
esac
case "$T8_DEFER_PATH" in
  *\\*) fail "T8" "deferred_findings[0].path contains backslash — must be POSIX (got: $T8_DEFER_PATH)" ;;
  *) ok "T8" "deferred_findings[0].path uses POSIX separators (no backslashes)" ;;
esac
assert_grep "T8" ".flow/review-deferred/" "$T8_DEFER_PATH" \
  "deferred_findings[0].path under .flow/review-deferred/"

# =============================================================================
# T9: Branch-no-commits-ahead — diff_summary.files: []
# =============================================================================
echo -e "${YELLOW}--- T9: branch with no commits ahead of base — diff_summary.files: [] ---${NC}"
NOAHEAD_REPO="$TEST_DIR/noahead-repo"
mkdir -p "$NOAHEAD_REPO"
(
  cd "$NOAHEAD_REPO"
  git init -q
  git config user.email "make-pr-smoke@example.com"
  git config user.name "Make-PR Smoke"
  git checkout -b main >/dev/null 2>&1 || git branch -m main >/dev/null 2>&1 || true
  git commit --allow-empty -m "init" -q
  "$FLOWCTL" init --json >/dev/null
  EPIC_RAW="$("$FLOWCTL" spec create --title "No-ahead epic" --json)"
  echo "$EPIC_RAW" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])' > .epic_id
)
NOAHEAD_EPIC_ID="$(cat "$NOAHEAD_REPO/.epic_id")"

T9_OUT="$TEST_DIR/t9-noahead.json"
set +e
( cd "$NOAHEAD_REPO" && "$FLOWCTL" spec export-cognitive-aid "$NOAHEAD_EPIC_ID" --base main --json > "$T9_OUT" )
T9_RC=$?
set -e
assert_rc "T9" 0 "$T9_RC" "no-commits-ahead exits 0 (graceful)"
assert_eq_jq "T9" "$T9_OUT" "len(d['diff_summary']['files'])" "0" "diff_summary.files: [] (no commits ahead)"
assert_eq_jq "T9" "$T9_OUT" "d['diff_summary']['lines_added']" "0" "diff_summary.lines_added == 0"

# =============================================================================
# T10: Skill body-rendering smoke — assert canonical SKILL prose carries
# the section markers the rendered body must include.
# =============================================================================
echo -e "${YELLOW}--- T10: skill body — section markers in canonical workflow.md ---${NC}"
WORKFLOW_FILE="$PLUGIN_ROOT/skills/flow-next-make-pr/workflow.md"
PHASES_FILE="$PLUGIN_ROOT/skills/flow-next-make-pr/phases.md"
SKILL_FILE="$PLUGIN_ROOT/skills/flow-next-make-pr/SKILL.md"

if [[ ! -f "$WORKFLOW_FILE" ]] || [[ ! -f "$SKILL_FILE" ]]; then
  skip "T10" "skill files not yet on disk (Tasks 3-6 not landed)"
else
  # Required body markers per spec R7
  WF_TEXT="$(cat "$WORKFLOW_FILE")"
  PH_TEXT="$(cat "$PHASES_FILE" 2>/dev/null || true)"
  COMBINED="$WF_TEXT
$PH_TEXT"

  for marker in "## TL;DR" "## R-ID coverage" "## Critical changes" "## How to review this PR" "## Review plan" "## Decisions" "## Memory left behind" "## Open items"; do
    if grep -qF -- "$marker" <<< "$COMBINED"; then
      ok "T10" "section marker '$marker' present in skill prose"
    else
      fail "T10" "section marker '$marker' missing from skill prose"
    fi
  done

  # fn-93: the risk-ranked Review plan + How-to-review coaching block replace the
  # old per-category '## Where to look' section — assert it is gone from the render order.
  if grep -qF -- "## Where to look" <<< "$COMBINED"; then
    fail "T10" "'## Where to look' still present — fn-93 replaced it with '## Review plan' + '## How to review this PR'"
  else
    ok "T10" "'## Where to look' absent from render contract (folded into the Review plan)"
  fi

  # `--dry-run` short-circuit: SKILL.md must document it
  assert_grep "T10" "--dry-run" "$(cat "$SKILL_FILE")" "SKILL.md documents --dry-run flag"

  # `gh pr create` reachable in workflow (Phase 4)
  assert_grep "T10" "gh pr create" "$WF_TEXT" "workflow.md invokes 'gh pr create'"
fi

# =============================================================================
# T11: Mermaid trigger logic — cross_module_changes signal feeds skill
# =============================================================================
echo -e "${YELLOW}--- T11: mermaid trigger — cross_module_changes non-empty ---${NC}"
# T11 is the export-side of the mermaid trigger. The skill emits the codefence
# only when this signal is non-empty (and `--no-mermaid` not set). Already
# proven in T3 that the fixture's cross-module imports surface as
# cross_module_changes >= 1. Re-check explicitly + cross-check the
# canonical mermaid-rules.md ships the trigger list.

T11_XM="$(json_get "$T1_OUT" "len(d['diff_summary']['cross_module_changes']) >= 1")"
[[ "$T11_XM" == "True" ]] \
  && ok "T11" "cross_module_changes signal flows from fixture to export" \
  || fail "T11" "fixture's cross-module import not detected (mermaid trigger broken)"

MERMAID_RULES="$PLUGIN_ROOT/skills/flow-next-make-pr/mermaid-rules.md"
if [[ -f "$MERMAID_RULES" ]]; then
  M_TEXT="$(cat "$MERMAID_RULES")"
  assert_grep "T11" "cross_module_changes" "$M_TEXT" "mermaid-rules.md references cross_module_changes trigger"
  assert_grep "T11" "flowchart LR" "$M_TEXT" "mermaid-rules.md references flowchart LR shape"
  # Hard caps
  assert_grep "T11" "12 nodes" "$M_TEXT" "mermaid-rules.md documents 12-node cap"
  assert_grep "T11" "3 diagrams" "$M_TEXT" "mermaid-rules.md documents 3-diagram cap"
else
  skip "T11" "mermaid-rules.md not on disk (Task 5 not landed)"
fi

# =============================================================================
# T12: Deleted public-export files surface in public_exports_changed
# =============================================================================
echo -e "${YELLOW}--- T12: deleted __init__.py removed-exports surface ---${NC}"
# The feature branch deletes src/legacy_pkg/__init__.py. Its `def legacy_one`,
# `def legacy_two`, and `class LegacyClass` should all show up in
# public_exports_changed[].removed for that file. Regression guard for
# the case where `+++ /dev/null` would otherwise drop the deleted file's
# `-def`/`-class` lines on the floor (PR #131 review).

T12_DEL_FOUND="$(json_get "$T1_OUT" "any(e['file'] == 'src/legacy_pkg/__init__.py' for e in d['diff_summary']['public_exports_changed'])")"
[[ "$T12_DEL_FOUND" == "True" ]] \
  && ok "T12" "src/legacy_pkg/__init__.py present in public_exports_changed" \
  || fail "T12" "deleted src/legacy_pkg/__init__.py missing from public_exports_changed"

if [[ "$T12_DEL_FOUND" == "True" ]]; then
  T12_REMOVED="$(json_get "$T1_OUT" "sorted(next(e['removed'] for e in d['diff_summary']['public_exports_changed'] if e['file']=='src/legacy_pkg/__init__.py'))")"
  T12_EXPECTED="['LegacyClass', 'legacy_one', 'legacy_two']"
  [[ "$T12_REMOVED" == "$T12_EXPECTED" ]] \
    && ok "T12" "removed[] contains legacy_one, legacy_two, LegacyClass" \
    || fail "T12" "removed[] mismatch — expected $T12_EXPECTED, got $T12_REMOVED"

  T12_ADDED="$(json_get "$T1_OUT" "next(e['added'] for e in d['diff_summary']['public_exports_changed'] if e['file']=='src/legacy_pkg/__init__.py')")"
  [[ "$T12_ADDED" == "[]" ]] \
    && ok "T12" "added[] empty for deleted file" \
    || fail "T12" "added[] should be [] for deleted file, got $T12_ADDED"
fi

# =============================================================================
# T13: Nested-subdir glossary deltas surface in glossary_changes
# =============================================================================
echo -e "${YELLOW}--- T13: nested apps/web/GLOSSARY.md surfaces in glossary_changes.added ---${NC}"
# The feature branch adds `apps/web/GLOSSARY.md` (with `NestedTerm`) entirely
# after the base commit. Pre-fix: `find_all_glossaries(repo_root)` only walks
# ancestors of repo_root and returns the root file, so the nested glossary's
# new term is silently dropped. Post-fix: downward repo walk picks up every
# `GLOSSARY.md` and `NestedTerm` shows up in `glossary_changes.added[]`.

T13_HAS_NESTED="$(json_get "$T1_OUT" "any('NestedTerm' in (a.get('term') or '') for a in d['glossary_changes']['added'])")"
[[ "$T13_HAS_NESTED" == "True" ]] \
  && ok "T13" "'NestedTerm' from apps/web/GLOSSARY.md present in glossary_changes.added" \
  || fail "T13" "'NestedTerm' missing — nested subdir glossary not diffed"

# =============================================================================
# T14: Whole-file glossary deletion vs base surfaces in glossary_changes.removed
# =============================================================================
echo -e "${YELLOW}--- T14: deleted apps/legacy/GLOSSARY.md surfaces in glossary_changes.removed ---${NC}"
# Fixture seeds `apps/legacy/GLOSSARY.md` with `LegacyGlossaryTerm` on main,
# then deletes the whole file on the feature branch. Pre-fix:
# `_export_find_glossaries_downward(repo_root)` only walks HEAD, so the
# deleted-file's terms never enter the diff and `removed[]` stays empty.
# Post-fix: union with `_export_find_glossaries_at_base` (via `git ls-tree`)
# picks up the base path; HEAD content reads as empty → `LegacyGlossaryTerm`
# surfaces in `removed[]` with no matching `added[]` entry.

T14_HAS_REMOVED="$(json_get "$T1_OUT" "'LegacyGlossaryTerm' in d['glossary_changes']['removed']")"
[[ "$T14_HAS_REMOVED" == "True" ]] \
  && ok "T14" "'LegacyGlossaryTerm' from deleted apps/legacy/GLOSSARY.md present in glossary_changes.removed" \
  || fail "T14" "'LegacyGlossaryTerm' missing — whole-file glossary deletion not detected vs base"

# Sanity: deleted term must NOT also appear in added[] (would indicate diffing logic is wrong).
T14_NOT_ADDED="$(json_get "$T1_OUT" "not any('LegacyGlossaryTerm' in (a.get('term') or '') for a in d['glossary_changes']['added'])")"
[[ "$T14_NOT_ADDED" == "True" ]] \
  && ok "T14" "'LegacyGlossaryTerm' correctly absent from glossary_changes.added" \
  || fail "T14" "'LegacyGlossaryTerm' incorrectly listed in added[] — diff polarity inverted"

# =============================================================================
# Sanity: verify nothing leaked outside $TEST_DIR.
# =============================================================================
echo -e "${YELLOW}--- Hygiene: confirm no writes outside TEST_DIR ---${NC}"
LEAKED="$( find "$PLUGIN_ROOT" -maxdepth 3 -name '.epic_id' -not -path "$PLUGIN_ROOT/.git/*" 2>/dev/null || true )"
[[ -z "$LEAKED" ]] \
  && ok "hygiene" "no fixture artifacts leaked into plugin tree" \
  || fail "hygiene" "leaked file(s): $LEAKED"

# =============================================================================
# Summary
# =============================================================================
echo
echo -e "${YELLOW}=== Summary ===${NC}"
echo -e "${GREEN}PASS: $PASS${NC}"
echo -e "${RED}FAIL: $FAIL${NC}"
echo -e "${YELLOW}SKIP: $SKIP${NC}"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
