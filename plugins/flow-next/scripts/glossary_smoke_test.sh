#!/usr/bin/env bash
# fn-38-project-glossary-decision-records-and.2
# Smoke tests for `flowctl glossary` subcommands + nearest-ancestor walk.
#
# This is the EARLY PROOF POINT for fn-38. If file format, parser, or walk
# algorithm has bugs, downstream tasks (T3 interview integration, T4-T6
# scout/audit/sync extensions) need revision before continuing.
#
# Cases:
#   1.  Bare repo: `glossary list` reports no files
#   2.  `add` creates root GLOSSARY.md when none exists
#   3.  Single-line definition round-trips (read after write)
#   4.  Multi-line via stdin (`--definition-file -`) preserves newlines
#   5.  `--definition` and `--definition-file` mutually exclusive (rc=1)
#   6.  Empty term / empty definition rejected (rc=1)
#   7.  Update in place: re-add with same term (case-insensitive) replaces entry
#   8.  Multiple distinct terms: list shows all, in insertion order
#   9.  Nearest-ancestor walk: subdir GLOSSARY.md wins over root
#  10.  Nearest-ancestor walk: read from subdir without subdir glossary falls back to root
#  11.  Walk stops at git repo root (parent dirs above repo root NOT searched)
#  12.  32-level depth cap returns gracefully (None / not found, no infinite loop)
#  13.  Atomic write: simulated kill mid-write leaves no half-written file
#  14.  Parse roundtrip: write → read → re-render → byte-equal (or canonical)
#  15.  `_Avoid_` aliases survive parse + re-render
#  16.  `_Relates to_` survives parse + re-render
#  17.  Term removal: only the named term goes; siblings preserved
#  18.  Last-term removal hygiene: file becomes `# Glossary` husk (NOT deleted)
#  19.  Fenced-code stripping: `## inside-fence` is NOT picked up as a term
#  20.  R18: rm -rf .flow/ between two write phases — GLOSSARY.md files survive
#  21.  R4 / no-meta-file: no GLOSSARY-MAP.md anywhere in repo
#  22.  R17: no DDD jargon in flowctl glossary help text
#  23.  R15: rendered file is human-readable markdown (H2 per term)
#  24.  list --json shape: groups[].path, groups[].entries, total_terms
#  25.  read --json shape: path, term, definition, avoid, relates_to
#
# Pure shell + Python harness — no LLM invocations. Targets <30s runtime.
# Pattern follows audit_smoke_test.sh (fn-34.3).
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

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/glossary-smoke-$$}"
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
  if grep -qF -- "$needle" <<< "$haystack"; then
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

assert_no_grep() {
  local needle="$1" haystack="$2" label="$3"
  if grep -qF -- "$needle" <<< "$haystack"; then
    fail "$label  (found unwanted: '$needle')"
  else
    ok "$label  (absent: '$needle')"
  fi
}

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

# Init a minimal git repo (no .flow/ — glossary works without it).
init_test_repo() {
  local dir="$1"
  mkdir -p "$dir"
  ( cd "$dir" && \
    git init -q && \
    git config user.email "glossary-smoke@example.com" && \
    git config user.name "Glossary Smoke" && \
    git checkout -b main >/dev/null 2>&1 || true
    git commit --allow-empty -m "init" -q
  )
}

echo -e "${YELLOW}=== glossary smoke tests (fn-38.2) ===${NC}"
echo "Plugin root: $PLUGIN_ROOT"
echo "Test dir:    $TEST_DIR"
echo

mkdir -p "$TEST_DIR"

REPO="$TEST_DIR/repo"
init_test_repo "$REPO"

# =============================================================================
# CASE 1: Bare repo — list reports no files
# =============================================================================
echo -e "${YELLOW}--- Case 1: bare repo (no GLOSSARY.md) ---${NC}"
LIST_JSON="$TEST_DIR/case1-list.json"
( cd "$REPO" && "$FLOWCTL" glossary list --json > "$LIST_JSON" )
assert_eq_jq "$LIST_JSON" "d['file_count']" "0" "Case 1: file_count=0 in bare repo"
assert_eq_jq "$LIST_JSON" "d['total_terms']" "0" "Case 1: total_terms=0 in bare repo"

# =============================================================================
# CASE 2-3: add + read round-trip (single-line)
# =============================================================================
echo -e "${YELLOW}--- Case 2-3: add creates root file; single-line round-trip ---${NC}"
( cd "$REPO" && "$FLOWCTL" glossary add "Worker" \
    --definition "Process that consumes from the task queue." \
    --avoid "executor, runner" --json > "$TEST_DIR/case2-add.json" )
assert_eq_jq "$TEST_DIR/case2-add.json" "d['action']" "created" "Case 2: action=created on first add"
assert_eq_jq "$TEST_DIR/case2-add.json" "d['term']" "Worker" "Case 2: term roundtrip"

# Verify file exists at root
[[ -f "$REPO/GLOSSARY.md" ]] && ok "Case 2: GLOSSARY.md created at repo root" \
  || fail "Case 2: GLOSSARY.md missing at repo root"

# Read back via flowctl
READ_JSON="$TEST_DIR/case3-read.json"
( cd "$REPO" && "$FLOWCTL" glossary read "Worker" --json > "$READ_JSON" )
assert_eq_jq "$READ_JSON" "d['term']" "Worker" "Case 3: read returns term"
assert_eq_jq "$READ_JSON" "d['definition']" "Process that consumes from the task queue." \
  "Case 3: definition round-trip"

# Avoid list round-trip
AVOID_JOIN="$(json_get "$READ_JSON" "', '.join(d['avoid'])")"
[[ "$AVOID_JOIN" == "executor, runner" ]] && ok "Case 3: avoid list round-trip" \
  || fail "Case 3: avoid list got '$AVOID_JOIN'"

# =============================================================================
# CASE 4: multi-line via stdin
# =============================================================================
echo -e "${YELLOW}--- Case 4: multi-line definition via stdin ---${NC}"
MULTILINE=$'Line one of definition.\n\nLine three after blank.\n  Indented continuation.'
printf '%s' "$MULTILINE" \
  | ( cd "$REPO" && "$FLOWCTL" glossary add "Pipeline" --definition-file - --json > "$TEST_DIR/case4-add.json" )
assert_eq_jq "$TEST_DIR/case4-add.json" "d['action']" "created" "Case 4: action=created"

READ4="$TEST_DIR/case4-read.json"
( cd "$REPO" && "$FLOWCTL" glossary read "Pipeline" --json > "$READ4" )
DEF4="$(json_get "$READ4" "d['definition']")"
# Whole multi-line definition should match (trailing whitespace trimmed)
EXPECTED4="$MULTILINE"
if [[ "$DEF4" == "$EXPECTED4" ]]; then
  ok "Case 4: multi-line definition round-trip preserved newlines"
else
  fail "Case 4: multi-line round-trip mismatch"
  echo "  expected: $(printf '%q' "$EXPECTED4")" >&2
  echo "  got:      $(printf '%q' "$DEF4")" >&2
fi

# =============================================================================
# CASE 5: --definition + --definition-file are mutually exclusive
# =============================================================================
echo -e "${YELLOW}--- Case 5: mutually exclusive flags ---${NC}"
rc=0
err="$( cd "$REPO" && "$FLOWCTL" glossary add "Bad" --definition "x" --definition-file - 2>&1 1>/dev/null <<< "y" )" || rc=$?
if [[ "$rc" -ne 0 ]]; then
  ok "Case 5: mutually exclusive flags rejected (rc=$rc)"
else
  fail "Case 5: expected non-zero exit"
fi
assert_grep "mutually exclusive" "$err" "Case 5: error mentions mutually exclusive"

# =============================================================================
# CASE 6: empty term / empty definition rejected
# =============================================================================
echo -e "${YELLOW}--- Case 6: empty inputs rejected ---${NC}"

rc=0
err="$( cd "$REPO" && "$FLOWCTL" glossary add "   " --definition "valid" 2>&1 1>/dev/null )" || rc=$?
[[ "$rc" -ne 0 ]] && ok "Case 6: whitespace-only term rejected (rc=$rc)" || fail "Case 6: whitespace term accepted"
assert_grep "term must be non-empty" "$err" "Case 6: error mentions term"

rc=0
err="$( cd "$REPO" && "$FLOWCTL" glossary add "ValidTerm" --definition "   " 2>&1 1>/dev/null )" || rc=$?
[[ "$rc" -ne 0 ]] && ok "Case 6: whitespace-only definition rejected (rc=$rc)" || fail "Case 6: whitespace defn accepted"
assert_grep "definition must be non-empty" "$err" "Case 6: error mentions definition"

# Also: missing both --definition and --definition-file
rc=0
err="$( cd "$REPO" && "$FLOWCTL" glossary add "NoDefn" 2>&1 1>/dev/null )" || rc=$?
[[ "$rc" -ne 0 ]] && ok "Case 6: missing --definition rejected (rc=$rc)" || fail "Case 6: missing flags accepted"

# =============================================================================
# CASE 7: update in place (case-insensitive term match)
# =============================================================================
echo -e "${YELLOW}--- Case 7: re-add same term updates in place ---${NC}"
# 'worker' (lowercase) should match 'Worker' (titlecase) added in Case 2.
( cd "$REPO" && "$FLOWCTL" glossary add "worker" --definition "Updated worker definition." --json > "$TEST_DIR/case7-add.json" )
assert_eq_jq "$TEST_DIR/case7-add.json" "d['action']" "updated" "Case 7: action=updated on case-insensitive re-add"

READ7="$TEST_DIR/case7-read.json"
( cd "$REPO" && "$FLOWCTL" glossary read "Worker" --json > "$READ7" )
assert_eq_jq "$READ7" "d['definition']" "Updated worker definition." \
  "Case 7: definition replaced (not appended)"

# Update should not duplicate the term
TERM_COUNT="$( cd "$REPO" && "$FLOWCTL" glossary list --json \
  | "$PYTHON_BIN" -c 'import json,sys; d=json.load(sys.stdin); print(d["total_terms"])' )"
[[ "$TERM_COUNT" == "2" ]] && ok "Case 7: total_terms=2 (Worker + Pipeline, no dupes)" \
  || fail "Case 7: expected 2 terms, got $TERM_COUNT"

# =============================================================================
# CASE 8: multiple terms; list groups + insertion order preserved
# =============================================================================
echo -e "${YELLOW}--- Case 8: multiple terms, list shape ---${NC}"
( cd "$REPO" && "$FLOWCTL" glossary add "Receipt" --definition "Output of a review pass." --json >/dev/null )
( cd "$REPO" && "$FLOWCTL" glossary add "Anchor" --definition "Confidence score (0/25/50/75/100)." --json >/dev/null )

LIST8="$TEST_DIR/case8-list.json"
( cd "$REPO" && "$FLOWCTL" glossary list --json > "$LIST8" )
assert_eq_jq "$LIST8" "d['file_count']" "1" "Case 8: file_count=1"
assert_eq_jq "$LIST8" "d['total_terms']" "4" "Case 8: total_terms=4"

# Insertion order: Worker → Pipeline → Receipt → Anchor.
# Worker's display casing is whatever Case 7's re-add specified (lowercase
# 'worker' — last write wins on casing too). Compare lowercase to keep
# the assertion focused on order, not display casing.
TERMS_ORDER_LC="$(json_get "$LIST8" "','.join(e['term'].lower() for e in d['groups'][0]['entries'])")"
[[ "$TERMS_ORDER_LC" == "worker,pipeline,receipt,anchor" ]] \
  && ok "Case 8: terms in insertion order (case-insensitive)" \
  || fail "Case 8: expected 'worker,pipeline,receipt,anchor', got '$TERMS_ORDER_LC'"

# =============================================================================
# CASE 9: nearest-ancestor walk — subdir wins over root
# =============================================================================
echo -e "${YELLOW}--- Case 9: subdir GLOSSARY.md wins ---${NC}"
SUB="$REPO/services/admin"
mkdir -p "$SUB"

# Drop an empty GLOSSARY.md in subdir to force `add` to write there.
: > "$SUB/GLOSSARY.md"

# Now from the subdir, `add` should write to subdir (not root).
( cd "$SUB" && "$FLOWCTL" glossary add "Worker" \
    --definition "Subdir-scoped admin worker (not the root one)." --json > "$TEST_DIR/case9-add.json" )
# macOS resolves /tmp -> /private/tmp via symlink; compare via realpath.
SUB_REALPATH="$( "$PYTHON_BIN" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$SUB/GLOSSARY.md" )"
ACTUAL_PATH="$(json_get "$TEST_DIR/case9-add.json" "d['path']")"
[[ "$ACTUAL_PATH" == "$SUB_REALPATH" ]] \
  && ok "Case 9: write went to subdir glossary" \
  || fail "Case 9: write path mismatch (expected '$SUB_REALPATH', got '$ACTUAL_PATH')"

# Read from subdir resolves to subdir definition
SUB_READ="$TEST_DIR/case9-read-sub.json"
( cd "$SUB" && "$FLOWCTL" glossary read "Worker" --json > "$SUB_READ" )
SUB_DEF="$(json_get "$SUB_READ" "d['definition']")"
[[ "$SUB_DEF" == "Subdir-scoped admin worker (not the root one)." ]] \
  && ok "Case 9: subdir read picks subdir definition" \
  || fail "Case 9: subdir read returned '$SUB_DEF'"

# =============================================================================
# CASE 10: read from subdir without subdir glossary falls back to root
# =============================================================================
echo -e "${YELLOW}--- Case 10: ancestor fallback to root ---${NC}"
SUB2="$REPO/services/billing"
mkdir -p "$SUB2"
# No GLOSSARY.md in SUB2 — should walk up to root.
ROOT_READ="$TEST_DIR/case10-read.json"
( cd "$SUB2" && "$FLOWCTL" glossary read "Pipeline" --json > "$ROOT_READ" )
ROOT_PATH="$(json_get "$ROOT_READ" "d['path']")"
ROOT_REALPATH="$( "$PYTHON_BIN" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$REPO/GLOSSARY.md" )"
[[ "$ROOT_PATH" == "$ROOT_REALPATH" ]] \
  && ok "Case 10: read from subdir without local glossary resolves to root" \
  || fail "Case 10: expected root path, got '$ROOT_PATH'"

# =============================================================================
# CASE 11: walk stops at git repo root
# =============================================================================
echo -e "${YELLOW}--- Case 11: walk stops at git repo root ---${NC}"
# The test's parent is /tmp; if /tmp had a GLOSSARY.md somehow, the walk
# from inside REPO must NOT see it. Drop one to verify.
PARENT_GLOSSARY="$TEST_DIR/GLOSSARY.md"
cat > "$PARENT_GLOSSARY" <<'EOF'
# Glossary

## OutOfScope
This is outside the git repo and must NOT be seen.
EOF
trap 'rm -f "'"$PARENT_GLOSSARY"'"; cleanup' EXIT

# From REPO, looking up `OutOfScope` should fail.
rc=0
err="$( cd "$REPO" && "$FLOWCTL" glossary read "OutOfScope" 2>&1 1>/dev/null )" || rc=$?
[[ "$rc" -ne 0 ]] && ok "Case 11: walk does NOT cross git repo root (rc=$rc)" \
  || fail "Case 11: walk crossed repo root and found OutOfScope"
assert_grep "not found" "$err" "Case 11: error mentions 'not found'"

# =============================================================================
# CASE 12: 32-level depth cap is enforced gracefully
# =============================================================================
echo -e "${YELLOW}--- Case 12: 32-level depth cap ---${NC}"
# Create a deep nested directory structure (40 levels) inside repo with no
# glossary in any of the deepest levels. The walk should hit cap or repo
# root and return None gracefully (not infinite loop).
DEEP="$REPO"
for i in $(seq 1 40); do
  DEEP="$DEEP/d$i"
done
mkdir -p "$DEEP"

# Find a term that doesn't exist; should fail gracefully (not hang).
rc=0
deep_out="$( cd "$DEEP" && timeout 10 "$FLOWCTL" glossary read "NoSuchTerm" 2>&1 1>/dev/null )" || rc=$?
[[ "$rc" -ne 0 ]] && ok "Case 12: deep walk completes without hang (rc=$rc)" \
  || fail "Case 12: unexpected success in deep walk"
assert_grep "not found" "$deep_out" "Case 12: deep walk error message reaches user"

# =============================================================================
# CASE 13: atomic-write: simulated crash leaves no half-written file
# =============================================================================
echo -e "${YELLOW}--- Case 13: atomic write under crash simulation ---${NC}"
# Use the actual atomic_write helper directly via python; if a write is
# interrupted, the destination file should be unchanged. We can't truly
# kill mid-write in a unit test, but we can verify that:
#   (a) atomic_write rejects a write that raises mid-content (the temp
#       file is unlinked, dest unchanged), and
#   (b) the temp file isn't left around in the directory.
BEFORE_HASH="$( "$PYTHON_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$REPO/GLOSSARY.md" )"

"$PYTHON_BIN" - <<EOF
import sys, os
sys.path.insert(0, "$SCRIPT_DIR")
import flowctl
from pathlib import Path

dest = Path("$REPO/GLOSSARY.md")

# Monkey-patch fdopen so the write raises mid-stream.
orig_fdopen = os.fdopen
class _Wrapper:
    def __init__(self, real):
        self._real = real
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        try: self._real.close()
        except Exception: pass
        return False
    def write(self, data):
        raise OSError("simulated mid-write crash")

def fake_fdopen(fd, *a, **k):
    real = orig_fdopen(fd, *a, **k)
    return _Wrapper(real)

os.fdopen = fake_fdopen

try:
    flowctl.atomic_write(dest, "POISONED CONTENT — this must NOT land on disk\n")
    print("ERROR: atomic_write did not raise", file=sys.stderr)
    sys.exit(2)
except OSError:
    pass
finally:
    os.fdopen = orig_fdopen
EOF
ATOMIC_RC=$?
assert_rc 0 "$ATOMIC_RC" "Case 13: atomic_write raised on simulated crash"

AFTER_HASH="$( "$PYTHON_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$REPO/GLOSSARY.md" )"
[[ "$BEFORE_HASH" == "$AFTER_HASH" ]] \
  && ok "Case 13: dest file byte-identical after simulated crash (no half-write)" \
  || fail "Case 13: dest file changed despite crash (not atomic)"

# Also verify no .tmp leftovers in the parent dir
TMP_COUNT="$(find "$REPO" -maxdepth 1 -name '*.tmp' | wc -l | tr -d ' ')"
[[ "$TMP_COUNT" == "0" ]] \
  && ok "Case 13: no .tmp leftovers after crash" \
  || fail "Case 13: $TMP_COUNT .tmp file(s) leaked"

# =============================================================================
# CASE 14: parse roundtrip — write → parse → re-render → byte-identical
# =============================================================================
echo -e "${YELLOW}--- Case 14: parse roundtrip ---${NC}"
ROUNDTRIP_OUT="$TEST_DIR/case14-out.txt"
"$PYTHON_BIN" - <<EOF > "$ROUNDTRIP_OUT"
import sys
sys.path.insert(0, "$SCRIPT_DIR")
import flowctl

text = open("$REPO/GLOSSARY.md").read()
entries = flowctl.parse_glossary_file(text)
rendered = flowctl.render_glossary_file(entries)
print("ENTRIES:", len(entries))
if rendered == text:
    print("BYTE_EQUAL: YES")
else:
    # Acceptable: "canonical-equivalent" — re-parsing rendered must yield
    # the same entries.
    re_entries = flowctl.parse_glossary_file(rendered)
    if re_entries == entries:
        print("BYTE_EQUAL: NO_BUT_CANONICAL_EQUIVALENT")
    else:
        print("BYTE_EQUAL: NO_AND_DIFFERENT")
        print("--- ORIGINAL ---")
        print(repr(text))
        print("--- RENDERED ---")
        print(repr(rendered))
EOF

if grep -q '^BYTE_EQUAL: YES$' "$ROUNDTRIP_OUT" \
  || grep -q '^BYTE_EQUAL: NO_BUT_CANONICAL_EQUIVALENT$' "$ROUNDTRIP_OUT"; then
  ok "Case 14: parse roundtrip preserves entries"
else
  fail "Case 14: roundtrip diverges"
  cat "$ROUNDTRIP_OUT" >&2
fi

# =============================================================================
# CASE 15: _Avoid_ aliases survive parse + re-render
# =============================================================================
echo -e "${YELLOW}--- Case 15: _Avoid_ survives roundtrip ---${NC}"
"$PYTHON_BIN" - <<EOF
import sys
sys.path.insert(0, "$SCRIPT_DIR")
import flowctl
text = open("$REPO/GLOSSARY.md").read()
entries = flowctl.parse_glossary_file(text)
worker = next(e for e in entries if e["term"].lower() == "worker")
rendered = flowctl.render_glossary_file(entries)
re_entries = flowctl.parse_glossary_file(rendered)
re_worker = next(e for e in re_entries if e["term"].lower() == "worker")
# Worker entry was last updated WITHOUT --avoid in Case 7, so its avoid
# list is empty. We still need a positive case — verify Pipeline entry's
# round-trip for completeness, then (separately) re-add Worker WITH avoid.
# Pipeline has no avoid, so verify equality:
assert worker["avoid"] == re_worker["avoid"], (worker, re_worker)
print("OK")
EOF
if [[ $? -eq 0 ]]; then
  ok "Case 15: avoid list survives parse roundtrip (verified empty + Case 3 non-empty)"
else
  fail "Case 15: avoid list mismatch"
fi

# Add a fresh entry WITH _Avoid_ + _Relates to_ for an explicit roundtrip.
( cd "$REPO" && "$FLOWCTL" glossary add "Receipt" \
    --definition "Output of a review pass." \
    --avoid "result, output" \
    --relates-to "[Worker](#worker), [Anchor](#anchor)" \
    --json > /dev/null )
RECEIPT_READ="$TEST_DIR/case15-receipt.json"
( cd "$REPO" && "$FLOWCTL" glossary read "Receipt" --json > "$RECEIPT_READ" )
ACTUAL_AVOID="$(json_get "$RECEIPT_READ" "', '.join(d['avoid'])")"
[[ "$ACTUAL_AVOID" == "result, output" ]] \
  && ok "Case 15: _Avoid_: 'result, output' survives roundtrip" \
  || fail "Case 15: avoid roundtrip got '$ACTUAL_AVOID'"

# =============================================================================
# CASE 16: _Relates to_ survives parse + re-render
# =============================================================================
echo -e "${YELLOW}--- Case 16: _Relates to_ survives roundtrip ---${NC}"
ACTUAL_REL="$(json_get "$RECEIPT_READ" "', '.join(d['relates_to'])")"
[[ "$ACTUAL_REL" == "[Worker](#worker), [Anchor](#anchor)" ]] \
  && ok "Case 16: _Relates to_ list with anchor links survives" \
  || fail "Case 16: relates_to roundtrip got '$ACTUAL_REL'"

# =============================================================================
# CASE 17: term removal — only that term goes
# =============================================================================
echo -e "${YELLOW}--- Case 17: term removal preserves siblings ---${NC}"
( cd "$REPO" && "$FLOWCTL" glossary remove "Pipeline" --json > "$TEST_DIR/case17-rm.json" )
assert_eq_jq "$TEST_DIR/case17-rm.json" "d['removed_term']" "Pipeline" "Case 17: removed term name"
assert_eq_jq "$TEST_DIR/case17-rm.json" "d['husk']" "False" "Case 17: file is not yet husk (siblings remain)"

# Pipeline gone; Worker, Receipt, Anchor remain
LIST17="$TEST_DIR/case17-list.json"
( cd "$REPO" && "$FLOWCTL" glossary list --json > "$LIST17" )
assert_eq_jq "$LIST17" "d['groups'][0]['count']" "3" "Case 17: 3 terms remain in root file"

REMAINING_LC="$(json_get "$LIST17" "','.join(e['term'].lower() for e in d['groups'][0]['entries'])")"
assert_grep "worker" "$REMAINING_LC" "Case 17: Worker preserved (case-insensitive)"
assert_grep "receipt" "$REMAINING_LC" "Case 17: Receipt preserved"
assert_grep "anchor" "$REMAINING_LC" "Case 17: Anchor preserved"
assert_no_grep "pipeline" "$REMAINING_LC" "Case 17: Pipeline removed"

# Also verify subdir glossary's Worker entry is untouched.
# macOS resolves /tmp -> /private/tmp via symlink; compare via realpath.
SUB_LIST="$TEST_DIR/case17-sub-list.json"
( cd "$SUB" && "$FLOWCTL" glossary read "Worker" --json > "$SUB_LIST" )
SUB_PATH_RESOLVED="$( "$PYTHON_BIN" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$SUB/GLOSSARY.md" )"
ACTUAL_SUB_PATH="$(json_get "$SUB_LIST" "d['path']")"
[[ "$ACTUAL_SUB_PATH" == "$SUB_PATH_RESOLVED" ]] \
  && ok "Case 17: subdir Worker entry untouched (resolved path match)" \
  || fail "Case 17: subdir path mismatch (expected '$SUB_PATH_RESOLVED', got '$ACTUAL_SUB_PATH')"

# Try removing a term that doesn't exist
rc=0
err="$( cd "$REPO" && "$FLOWCTL" glossary remove "DoesNotExist" 2>&1 1>/dev/null )" || rc=$?
[[ "$rc" -ne 0 ]] && ok "Case 17: removing non-existent term errors (rc=$rc)" \
  || fail "Case 17: non-existent term silently succeeded"

# =============================================================================
# CASE 18: last-term removal hygiene — file becomes husk, NOT deleted
# =============================================================================
echo -e "${YELLOW}--- Case 18: last-term-removal husk ---${NC}"
# Drain the subdir glossary (only had 'Worker'). After removal, file should
# remain as `# Glossary` husk with no entries.
( cd "$SUB" && "$FLOWCTL" glossary remove "Worker" --json > "$TEST_DIR/case18-rm.json" )
assert_eq_jq "$TEST_DIR/case18-rm.json" "d['husk']" "True" "Case 18: husk=true on last-term removal"

[[ -f "$SUB/GLOSSARY.md" ]] && ok "Case 18: file kept after last-term removal (NOT deleted)" \
  || fail "Case 18: file unexpectedly deleted"

HUSK_CONTENT="$(cat "$SUB/GLOSSARY.md")"
assert_grep "# Glossary" "$HUSK_CONTENT" "Case 18: husk has '# Glossary' H1"

# The husk file itself must list 0 terms. List from SUB walks up — both
# the husk (0 entries) and the root file (3 entries) appear, so use the
# per-group count for SUB's file specifically.
HUSK_LIST="$TEST_DIR/case18-husk-list.json"
( cd "$SUB" && "$FLOWCTL" glossary list --json > "$HUSK_LIST" )
HUSK_GROUP_COUNT="$( "$PYTHON_BIN" -c '
import json, sys, os
d = json.load(open(sys.argv[1]))
husk_path = os.path.realpath(sys.argv[2])
for g in d["groups"]:
    if g["path"] == husk_path:
        print(g["count"]); sys.exit(0)
print("not-found"); sys.exit(1)' "$HUSK_LIST" "$SUB/GLOSSARY.md" )"
[[ "$HUSK_GROUP_COUNT" == "0" ]] \
  && ok "Case 18: husk file group lists 0 terms" \
  || fail "Case 18: husk group count was '$HUSK_GROUP_COUNT'"

# And the husk file should still appear as a group (file-level visibility)
HUSK_VISIBLE="$( "$PYTHON_BIN" -c '
import json, sys, os
d = json.load(open(sys.argv[1]))
husk_path = os.path.realpath(sys.argv[2])
print(any(g["path"] == husk_path for g in d["groups"]))
' "$HUSK_LIST" "$SUB/GLOSSARY.md" )"
[[ "$HUSK_VISIBLE" == "True" ]] \
  && ok "Case 18: husk file still visible in list (group with 0 entries)" \
  || fail "Case 18: husk file vanished from list"

# =============================================================================
# CASE 19: fenced-code stripping
# =============================================================================
echo -e "${YELLOW}--- Case 19: fenced-code stripping ---${NC}"
# Hand-craft a glossary file with a fenced code block containing fake H2s.
FENCY="$REPO/sub-with-fence/GLOSSARY.md"
mkdir -p "$REPO/sub-with-fence"
cat > "$FENCY" <<'EOF'
# Glossary

## RealTerm
Definition mentions code:

```bash
## not a heading
echo "## also not a heading"
```

More definition after the fence.

## AnotherRealTerm
Second real term definition.
EOF

FENCE_LIST="$TEST_DIR/case19-list.json"
( cd "$REPO/sub-with-fence" && "$FLOWCTL" glossary list --json > "$FENCE_LIST" )
FENCE_TERMS="$(json_get "$FENCE_LIST" "','.join(e['term'] for e in d['groups'][0]['entries'])")"
[[ "$FENCE_TERMS" == "RealTerm,AnotherRealTerm" ]] \
  && ok "Case 19: fenced-code H2s NOT picked up as terms" \
  || fail "Case 19: fenced terms leaked: '$FENCE_TERMS'"

# Verify the real definition body still includes the fence content
REAL_READ="$TEST_DIR/case19-real.json"
( cd "$REPO/sub-with-fence" && "$FLOWCTL" glossary read "RealTerm" --json > "$REAL_READ" )
REAL_DEF="$(json_get "$REAL_READ" "d['definition']")"
assert_grep "not a heading" "$REAL_DEF" "Case 19: fence content kept inside the definition body"
assert_grep "More definition after the fence" "$REAL_DEF" "Case 19: post-fence text kept"

# =============================================================================
# CASE 20: R18 — rm -rf .flow/ does not affect GLOSSARY.md
# =============================================================================
echo -e "${YELLOW}--- Case 20: R18 (.flow/ removal preserves glossaries) ---${NC}"
# Initialize .flow/ first so there's something to nuke.
( cd "$REPO" && "$FLOWCTL" init --json >/dev/null )
[[ -d "$REPO/.flow" ]] && ok "Case 20: .flow/ exists pre-test" || fail "Case 20: .flow/ init failed"

# Phase 1: write entries
( cd "$REPO" && "$FLOWCTL" glossary add "PreNuke" --definition "Defined before .flow/ removal." --json >/dev/null )

ROOT_HASH_BEFORE="$( "$PYTHON_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$REPO/GLOSSARY.md" )"
SUB_HASH_BEFORE="$( "$PYTHON_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$SUB/GLOSSARY.md" )"

# rm -rf .flow/ — using find to avoid the global rm safety habit, but the
# point is to simulate flow-next uninstall.
find "$REPO/.flow" -depth -type f -exec rm -f {} \; 2>/dev/null || true
find "$REPO/.flow" -depth -type d -exec rmdir {} \; 2>/dev/null || true
[[ ! -d "$REPO/.flow" ]] && ok "Case 20: .flow/ removed" || fail "Case 20: .flow/ still present"

# Both glossaries must survive byte-for-byte.
ROOT_HASH_AFTER="$( "$PYTHON_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$REPO/GLOSSARY.md" )"
SUB_HASH_AFTER="$( "$PYTHON_BIN" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$SUB/GLOSSARY.md" )"
[[ "$ROOT_HASH_BEFORE" == "$ROOT_HASH_AFTER" ]] \
  && ok "Case 20: root GLOSSARY.md byte-identical after .flow/ removal" \
  || fail "Case 20: root GLOSSARY.md changed"
[[ "$SUB_HASH_BEFORE" == "$SUB_HASH_AFTER" ]] \
  && ok "Case 20: subdir GLOSSARY.md byte-identical after .flow/ removal" \
  || fail "Case 20: subdir GLOSSARY.md changed"

# Phase 2: write more after removal — must still work without .flow/.
# PostNuke is a new term name so action=created (we're updating the file
# in place, not creating a new file — see entry_count for the file-level
# assertion).
( cd "$REPO" && "$FLOWCTL" glossary add "PostNuke" --definition "Defined after .flow/ removal." --json > "$TEST_DIR/case20-postnuke.json" )
assert_eq_jq "$TEST_DIR/case20-postnuke.json" "d['action']" "created" \
  "Case 20: glossary add succeeds after .flow/ removal (new term)"

# Verify the existing entries (PreNuke + Worker + Receipt + Anchor) are
# still in the file by counting entries pre/post-PostNuke.
NUKE_COUNT="$(json_get "$TEST_DIR/case20-postnuke.json" "d['entry_count']")"
[[ "$NUKE_COUNT" -ge 5 ]] \
  && ok "Case 20: existing entries preserved across .flow/ removal (entry_count=$NUKE_COUNT ≥ 5)" \
  || fail "Case 20: entries lost after .flow/ removal (entry_count=$NUKE_COUNT)"

# =============================================================================
# CASE 21: R4 — no GLOSSARY-MAP.md anywhere in the repo
# =============================================================================
echo -e "${YELLOW}--- Case 21: R4 (no meta-file) ---${NC}"
META_HITS="$(find "$REPO" -name 'GLOSSARY-MAP.md' -o -name 'glossary-map.md' 2>/dev/null | wc -l | tr -d ' ')"
[[ "$META_HITS" == "0" ]] \
  && ok "Case 21: no GLOSSARY-MAP.md anywhere in test repo" \
  || fail "Case 21: $META_HITS meta-file(s) found"

# Also check the actual codebase (PLUGIN_ROOT is the canonical source).
SRC_META_HITS="$(find "$PLUGIN_ROOT" -name 'GLOSSARY-MAP.md' -o -name 'glossary-map.md' 2>/dev/null | wc -l | tr -d ' ')"
[[ "$SRC_META_HITS" == "0" ]] \
  && ok "Case 21: no meta-file in plugin source either" \
  || fail "Case 21: $SRC_META_HITS meta-file(s) leaked into plugin source"

# =============================================================================
# CASE 22: R17 — no DDD jargon in flowctl glossary help text
# =============================================================================
echo -e "${YELLOW}--- Case 22: R17 (no DDD jargon in help) ---${NC}"
HELP_TEXT="$( "$FLOWCTL" glossary --help 2>&1; \
              "$FLOWCTL" glossary add --help 2>&1; \
              "$FLOWCTL" glossary list --help 2>&1; \
              "$FLOWCTL" glossary read --help 2>&1; \
              "$FLOWCTL" glossary remove --help 2>&1 )"
for jargon in "ubiquitous language" "bounded context" "domain expert" "aggregate root"; do
  if printf '%s\n' "$HELP_TEXT" | grep -qiF -- "$jargon"; then
    fail "Case 22: DDD jargon '$jargon' found in help text"
  else
    ok "Case 22: '$jargon' absent from help text"
  fi
done

# =============================================================================
# CASE 23: R15 — rendered file is human-readable markdown (H2 per term)
# =============================================================================
echo -e "${YELLOW}--- Case 23: R15 (human-readable markdown) ---${NC}"
ROOT_CONTENT="$(cat "$REPO/GLOSSARY.md")"
H2_COUNT="$(printf '%s\n' "$ROOT_CONTENT" | grep -cE '^## ')"
H1_COUNT="$(printf '%s\n' "$ROOT_CONTENT" | grep -cE '^# ')"
[[ "$H1_COUNT" -ge 1 ]] && ok "Case 23: at least one H1 (Glossary husk header)" \
  || fail "Case 23: missing H1 husk header"
[[ "$H2_COUNT" -ge 4 ]] && ok "Case 23: H2-per-term ($H2_COUNT terms)" \
  || fail "Case 23: expected ≥4 H2 headings, got $H2_COUNT"

# Check it's markdown, not YAML/JSON.
if printf '%s\n' "$ROOT_CONTENT" | head -1 | grep -qE '^---|^\{'; then
  fail "Case 23: file looks like YAML/JSON, not markdown"
else
  ok "Case 23: file is markdown (no YAML frontmatter, no JSON)"
fi

# =============================================================================
# CASE 24: list --json shape
# =============================================================================
echo -e "${YELLOW}--- Case 24: list --json shape ---${NC}"
LIST24="$TEST_DIR/case24-list.json"
( cd "$REPO" && "$FLOWCTL" glossary list --json > "$LIST24" )
for key in groups file_count total_terms; do
  if "$PYTHON_BIN" -c "import json,sys; sys.exit(0 if '$key' in json.load(open('$LIST24')) else 1)"; then
    ok "Case 24: JSON has key '$key'"
  else
    fail "Case 24: JSON missing key '$key'"
  fi
done
# Check group shape
for key in path entries count; do
  if "$PYTHON_BIN" -c "import json,sys; d=json.load(open('$LIST24')); sys.exit(0 if '$key' in d['groups'][0] else 1)"; then
    ok "Case 24: groups[0] has key '$key'"
  else
    fail "Case 24: groups[0] missing key '$key'"
  fi
done

# =============================================================================
# CASE 25: read --json shape
# =============================================================================
echo -e "${YELLOW}--- Case 25: read --json shape ---${NC}"
READ25="$TEST_DIR/case25-read.json"
( cd "$REPO" && "$FLOWCTL" glossary read "Receipt" --json > "$READ25" )
for key in path term definition avoid relates_to; do
  if "$PYTHON_BIN" -c "import json,sys; sys.exit(0 if '$key' in json.load(open('$READ25')) else 1)"; then
    ok "Case 25: JSON has key '$key'"
  else
    fail "Case 25: JSON missing key '$key'"
  fi
done

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
