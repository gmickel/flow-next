#!/usr/bin/env bash
# fn-50-codebase-feature-map-flow-nextmap-skill.1
# Smoke tests for /flow-next:map skill scaffold + clawpatch detection + Ralph-block.
#
# Cases (mirror task spec acceptance):
#   1. Skeleton — SKILL.md / workflow.md / slash-command shim exist; frontmatter
#      shape correct; AskUserQuestion in allowed-tools.
#   2. Ralph-block (R13) — FLOW_RALPH=1 and REVIEW_RECEIPT_PATH both produce
#      exit 2 with stderr diagnostic naming the trigger var. NO write to
#      $REVIEW_RECEIPT_PATH (decline-to-run only).
#   3. SUPPORTED_CLAWPATCH (R10) — version-pin constant appears verbatim in
#      SKILL.md prose; replayed bash version-comparison warns + continues
#      outside-range and passes silently inside range.
#   4. Install-detection (R1, R11) — `command -v clawpatch` missing branch
#      prints `pnpm add -g clawpatch` verbatim and exits 1; PNPM_HOME branch
#      detects pnpm-installed-but-not-on-PATH and prints the setup hint.
#   5. .clawpatch/.gitignore skeleton (R2) — replayed bash writes the skeleton
#      idempotently when .clawpatch/ exists, leaves repo `.gitignore` untouched.
#   6. Config-state echo (R12) — replayed bash emits the four-line block.
#   7. Argument parsing — `--` terminator, --source heuristic|auto|agent valid;
#      invalid --source exits 2.
#
# Pure shell — no clawpatch invocation (CI has no Node 22+ / clawpatch).
# All flowctl-touching cases are independent of clawpatch presence.
# Pattern follows prospect_smoke_test.sh (fn-33.6).
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

# Safety: never run from the main plugin repo (matches sibling smoke scripts).
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/map-smoke-$$}"
# Normalize Windows backslashes from $RUNNER_TEMP to forward slashes so paths
# interpolated into here-docs are clean.
TEST_DIR="${TEST_DIR//\\//}"
mkdir -p "$TEST_DIR"

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
    fail "$label  (unexpected: '$needle')"
  else
    ok "$label  (absent: '$needle')"
  fi
}

assert_grep_re() {
  local pattern="$1" haystack="$2" label="$3"
  if printf '%s\n' "$haystack" | grep -qE -- "$pattern"; then
    ok "$label  (matched: /$pattern/)"
  else
    fail "$label  (no match: /$pattern/)"
  fi
}

# =============================================================================
# CASE 1: Skeleton — SKILL.md / workflow.md / slash command exist
# =============================================================================
echo -e "${YELLOW}--- Case 1: skeleton + slash command ---${NC}"

CMD_FILE="$PLUGIN_ROOT/commands/flow-next/map.md"
SKILL_FILE="$PLUGIN_ROOT/skills/flow-next-map/SKILL.md"
WORKFLOW_FILE="$PLUGIN_ROOT/skills/flow-next-map/workflow.md"

[[ -f "$CMD_FILE" ]]      && ok "command file exists ($CMD_FILE)"      || fail "command file missing"
[[ -f "$SKILL_FILE" ]]    && ok "skill file exists ($SKILL_FILE)"      || fail "skill file missing"
[[ -f "$WORKFLOW_FILE" ]] && ok "workflow.md exists"                    || fail "workflow.md missing"

# Command must invoke the skill.
if [[ -f "$CMD_FILE" ]]; then
  cmd_content="$(cat "$CMD_FILE")"
  assert_grep "flow-next-map" "$cmd_content" "Case 1: command invokes flow-next-map skill"
fi

# SKILL.md frontmatter — must include AskUserQuestion, name=flow-next-map,
# no `context: fork`.
if [[ -f "$SKILL_FILE" ]]; then
  fm_block="$(awk '/^---$/{c++; next} c==1' "$SKILL_FILE" | head -30)"
  if echo "$fm_block" | grep -qE '^context:[[:space:]]*fork'; then
    fail "Case 1: SKILL.md must NOT use 'context: fork' (keeps blocking tools reachable)"
  else
    ok "Case 1: SKILL.md does not set 'context: fork'"
  fi
  assert_grep "AskUserQuestion" "$fm_block" "Case 1: SKILL.md allowed-tools includes AskUserQuestion"
  assert_grep_re '^name:[[:space:]]*flow-next-map' "$fm_block" "Case 1: SKILL.md name == flow-next-map"
fi

# Preamble FLOWCTL definition pattern present
assert_grep 'FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"' \
  "$(cat "$SKILL_FILE")" \
  "Case 1: SKILL.md carries canonical FLOWCTL prelude (Droid+Claude fallback)"

# =============================================================================
# CASE 2: Ralph-block (R13) — FLOW_RALPH=1 / REVIEW_RECEIPT_PATH must exit 2
#         with diagnostic naming trigger var; MUST NOT write to receipt path.
# =============================================================================
echo -e "${YELLOW}--- Case 2: Ralph-block (R13) ---${NC}"

# Sanity: bytes from the SKILL.md must appear in the source so Ralph can
# never silently invoke install/init prompts.
SKILL_TEXT="$(cat "$SKILL_FILE")"
if grep -q 'REVIEW_RECEIPT_PATH' "$SKILL_FILE" && grep -q 'FLOW_RALPH' "$SKILL_FILE" && grep -q 'exit 2' "$SKILL_FILE"; then
  ok "Case 2: SKILL.md ships Ralph-block with exit 2 + both env-var checks"
else
  fail "Case 2: SKILL.md missing FLOW_RALPH/REVIEW_RECEIPT_PATH/exit 2 guard"
fi

# R13 explicit: skill MUST NOT write to $REVIEW_RECEIPT_PATH.
assert_grep "decline-to-run" "$SKILL_TEXT" "Case 2: SKILL.md documents decline-to-run (no receipt write)"

# Reproduce the SKILL.md Ralph guard for behavioral verification.
RALPH_GUARD="$TEST_DIR/ralph_guard.sh"
cat > "$RALPH_GUARD" <<'BASH'
#!/usr/bin/env bash
set -e
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  if [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
    TRIGGER="REVIEW_RECEIPT_PATH"
  else
    TRIGGER="FLOW_RALPH"
  fi
  echo "Error: /flow-next:map declines under Ralph ($TRIGGER set); rerun interactively." >&2
  exit 2
fi
exit 0
BASH
chmod +x "$RALPH_GUARD"

# 2a: FLOW_RALPH=1 → exit 2; trigger var named.
rc=0
err="$(FLOW_RALPH=1 bash "$RALPH_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 2a: FLOW_RALPH=1 → exit 2"
assert_grep "FLOW_RALPH" "$err" "Case 2a: stderr names FLOW_RALPH"
assert_grep "Ralph" "$err" "Case 2a: stderr mentions Ralph"

# 2b: REVIEW_RECEIPT_PATH set → exit 2; trigger var named; receipt NOT touched.
RECEIPT_PATH="$TEST_DIR/sentinel-receipt.json"
echo '{"sentinel":"do-not-touch"}' > "$RECEIPT_PATH"
RECEIPT_BEFORE="$(cat "$RECEIPT_PATH")"
rc=0
err="$(REVIEW_RECEIPT_PATH="$RECEIPT_PATH" bash "$RALPH_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 2b: REVIEW_RECEIPT_PATH set → exit 2"
assert_grep "REVIEW_RECEIPT_PATH" "$err" "Case 2b: stderr names REVIEW_RECEIPT_PATH"
RECEIPT_AFTER="$(cat "$RECEIPT_PATH")"
if [[ "$RECEIPT_BEFORE" == "$RECEIPT_AFTER" ]]; then
  ok "Case 2b: receipt at \$REVIEW_RECEIPT_PATH UNCHANGED (decline-to-run is read-only)"
else
  fail "Case 2b: receipt at \$REVIEW_RECEIPT_PATH was MODIFIED (R13 violation)"
fi

# 2c: neither set → exit 0.
rc=0
bash "$RALPH_GUARD" >/dev/null 2>&1 || rc=$?
assert_rc 0 "$rc" "Case 2c: no Ralph env → exit 0 (terminal OK)"

# =============================================================================
# CASE 3: SUPPORTED_CLAWPATCH (R10) — version-pin + outside-range warn behavior
# =============================================================================
echo -e "${YELLOW}--- Case 3: SUPPORTED_CLAWPATCH version-range guard (R10) ---${NC}"

# Constant declared in SKILL.md prose
assert_grep 'SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"' "$SKILL_TEXT" "Case 3: SUPPORTED_CLAWPATCH constant in SKILL.md"

# Replay the workflow.md ver_cmp helper for behavioral verification.
VER_GUARD="$TEST_DIR/ver_guard.sh"
cat > "$VER_GUARD" <<'BASH'
#!/usr/bin/env bash
set -e
SUPPORTED_MIN="0.4.0"
SUPPORTED_MAX_EXCL="0.5.0"
CP_VER="$1"

ver_cmp() {
  local a="$1" b="$2"
  if [[ -z "$a" || -z "$b" ]]; then echo 0; return; fi
  local IFS=.
  # shellcheck disable=SC2206
  local A=($a) B=($b)
  for i in 0 1 2; do
    local ai="${A[$i]:-0}" bi="${B[$i]:-0}"
    if (( 10#$ai > 10#$bi )); then echo 1; return; fi
    if (( 10#$ai < 10#$bi )); then echo -1; return; fi
  done
  echo 0
}

if [[ -n "$CP_VER" ]]; then
  cmp_min="$(ver_cmp "$CP_VER" "$SUPPORTED_MIN")"
  cmp_max="$(ver_cmp "$CP_VER" "$SUPPORTED_MAX_EXCL")"
  if [[ "$cmp_min" == "-1" || "$cmp_max" != "-1" ]]; then
    echo "Warning: clawpatch $CP_VER outside supported range >=$SUPPORTED_MIN <$SUPPORTED_MAX_EXCL — continuing (degraded; behavior may differ)." >&2
  fi
fi
exit 0  # outside-range never blocks
BASH
chmod +x "$VER_GUARD"

# 3a: in-range version (0.4.0) → no warning, exit 0
rc=0
err="$(bash "$VER_GUARD" "0.4.0" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 3a: 0.4.0 in-range exits 0"
assert_no_grep "outside supported range" "$err" "Case 3a: 0.4.0 in-range emits no warning"

# 3b: in-range version (0.4.7) → no warning, exit 0
rc=0
err="$(bash "$VER_GUARD" "0.4.7" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 3b: 0.4.7 in-range exits 0"
assert_no_grep "outside supported range" "$err" "Case 3b: 0.4.7 in-range emits no warning"

# 3c: below-range version (0.3.9) → warning, exit 0 (degrades)
rc=0
err="$(bash "$VER_GUARD" "0.3.9" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 3c: 0.3.9 below-range still exits 0 (degrades)"
assert_grep "outside supported range" "$err" "Case 3c: 0.3.9 emits range warning"
assert_grep "0.3.9" "$err" "Case 3c: warning names the found version"

# 3d: above-range version (0.5.0) → warning, exit 0 (degrades)
rc=0
err="$(bash "$VER_GUARD" "0.5.0" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 3d: 0.5.0 above-range still exits 0 (degrades)"
assert_grep "outside supported range" "$err" "Case 3d: 0.5.0 emits range warning"

# 3e: empty version → no warning, exit 0 (defensive, parse failed elsewhere)
rc=0
err="$(bash "$VER_GUARD" "" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 3e: empty version exits 0 (defensive)"
assert_no_grep "outside supported range" "$err" "Case 3e: empty version emits no range warning"

# =============================================================================
# CASE 4: Install detection (R1, R11) — missing clawpatch → exit 1 + hint
# =============================================================================
echo -e "${YELLOW}--- Case 4: Install detection (R1) + PNPM_HOME (R11) ---${NC}"

# Replay the workflow.md Phase 1 logic with stubs to drive the branches.
INSTALL_GUARD="$TEST_DIR/install_guard.sh"
cat > "$INSTALL_GUARD" <<'BASH'
#!/usr/bin/env bash
set -e
# Stub clawpatch missing — synthesize the "not on PATH" branch.
if ! command -v clawpatch >/dev/null 2>&1; then
  cat >&2 <<'EOF'
clawpatch is not installed.

Install (requires Node 22+):

    pnpm add -g clawpatch

Then re-run /flow-next:map.
EOF

  if command -v pnpm >/dev/null 2>&1 && pnpm bin -g >/dev/null 2>&1; then
    PNPM_GLOBAL_BIN="$(pnpm bin -g 2>/dev/null)"
    cat >&2 <<EOF

Hint: pnpm is installed but \`clawpatch\` is not on PATH. Your pnpm global bin
is at: $PNPM_GLOBAL_BIN

pnpm v11 moved global binaries to \$PNPM_HOME/bin/. If you upgraded from pnpm 10
without running \`pnpm setup\`, install succeeds but PATH is unchanged. Run:

    pnpm setup
    # then re-source your shell rc (e.g. source ~/.zshrc) or open a new shell

…and re-run /flow-next:map.
EOF
  fi
  exit 1
fi
exit 0
BASH
chmod +x "$INSTALL_GUARD"

# 4a: clawpatch absent from PATH → exit 1 + verbatim install instructions
rc=0
# Empty PATH suppresses both clawpatch + pnpm so the no-pnpm branch fires.
# Preserve bash itself by including the bash binary's dir in PATH.
BASH_DIR="$(dirname "$(command -v bash)")"
err="$(env -i PATH="$BASH_DIR" HOME="$HOME" bash "$INSTALL_GUARD" 2>&1)" || rc=$?
assert_rc 1 "$rc" "Case 4a: missing clawpatch → exit 1"
assert_grep "pnpm add -g clawpatch" "$err" "Case 4a: prints verbatim install instructions"
assert_grep "Node 22+" "$err" "Case 4a: names Node 22+ requirement"

# 4b: pnpm-on-PATH-but-clawpatch-missing → PNPM_HOME hint surfaces.
PNPM_STUB_DIR="$TEST_DIR/pnpm-stub"
mkdir -p "$PNPM_STUB_DIR"
cat > "$PNPM_STUB_DIR/pnpm" <<'EOF'
#!/usr/bin/env bash
# Stub: simulate `pnpm bin -g` returning a global-bin path.
if [[ "$1" == "bin" && "$2" == "-g" ]]; then
  echo "/tmp/fake-pnpm-bin"
  exit 0
fi
exit 1
EOF
chmod +x "$PNPM_STUB_DIR/pnpm"

rc=0
err="$(env -i PATH="$PNPM_STUB_DIR:$BASH_DIR" HOME="$HOME" bash "$INSTALL_GUARD" 2>&1)" || rc=$?
assert_rc 1 "$rc" "Case 4b: pnpm-installed + clawpatch-missing → exit 1"
assert_grep "pnpm add -g clawpatch" "$err" "Case 4b: still prints install instructions"
assert_grep "pnpm setup" "$err" "Case 4b: PNPM_HOME hint surfaces (pnpm setup)"
assert_grep "PNPM_HOME" "$err" "Case 4b: hint names PNPM_HOME"
assert_grep "/tmp/fake-pnpm-bin" "$err" "Case 4b: hint surfaces pnpm bin -g output"

# =============================================================================
# CASE 5: .clawpatch/.gitignore skeleton (R2) — idempotent, self-contained
# =============================================================================
echo -e "${YELLOW}--- Case 5: .clawpatch/.gitignore skeleton (R2) ---${NC}"

GITIGNORE_GUARD="$TEST_DIR/gitignore_guard.sh"
cat > "$GITIGNORE_GUARD" <<'BASH'
#!/usr/bin/env bash
set -e
CLAWPATCH_DIR="$1"
GITIGNORE_PATH="$CLAWPATCH_DIR/.gitignore"
if [[ ! -f "$GITIGNORE_PATH" ]]; then
  cat > "$GITIGNORE_PATH" <<'EOF'
# Auto-managed by /flow-next:map — patterns scoped to .clawpatch/.
# Delete this directory entire to remove data + ignore rules together.

# Provider/agent transient state (clawpatch's own; not flow-next's)
.cache/
*.log
*.tmp

# Per-run patch artifacts (clawpatch patch/apply transients)
patches/*.tmp
EOF
fi
BASH
chmod +x "$GITIGNORE_GUARD"

CASE5_REPO="$TEST_DIR/case5"
mkdir -p "$CASE5_REPO/.clawpatch"
# Plant a sentinel repo .gitignore so we can prove it is NOT touched.
cat > "$CASE5_REPO/.gitignore" <<'EOF'
# user's repo gitignore — must not be modified
node_modules/
EOF
REPO_GITIGNORE_BEFORE="$(cat "$CASE5_REPO/.gitignore")"

# 5a: First-write — skeleton file appears, contents canonical
bash "$GITIGNORE_GUARD" "$CASE5_REPO/.clawpatch"
[[ -f "$CASE5_REPO/.clawpatch/.gitignore" ]] && ok "Case 5a: .clawpatch/.gitignore written" \
  || fail "Case 5a: .clawpatch/.gitignore NOT written"
SKEL_TEXT="$(cat "$CASE5_REPO/.clawpatch/.gitignore")"
assert_grep "Auto-managed by /flow-next:map" "$SKEL_TEXT" "Case 5a: skeleton header present"
assert_grep ".cache/" "$SKEL_TEXT" "Case 5a: .cache/ pattern present"
assert_grep "patches/*.tmp" "$SKEL_TEXT" "Case 5a: patches/*.tmp pattern present"

# 5b: Idempotency — second write must not modify (no `if exists` would clobber).
echo "user-added-pattern" >> "$CASE5_REPO/.clawpatch/.gitignore"
BEFORE_2ND="$(cat "$CASE5_REPO/.clawpatch/.gitignore")"
bash "$GITIGNORE_GUARD" "$CASE5_REPO/.clawpatch"
AFTER_2ND="$(cat "$CASE5_REPO/.clawpatch/.gitignore")"
if [[ "$BEFORE_2ND" == "$AFTER_2ND" ]]; then
  ok "Case 5b: re-run is no-op (idempotent — preserves user additions)"
else
  fail "Case 5b: re-run modified file (lost user-added content)"
fi

# 5c: Repo .gitignore must be untouched.
REPO_GITIGNORE_AFTER="$(cat "$CASE5_REPO/.gitignore")"
if [[ "$REPO_GITIGNORE_BEFORE" == "$REPO_GITIGNORE_AFTER" ]]; then
  ok "Case 5c: repo .gitignore unchanged (skeleton is self-contained inside .clawpatch/)"
else
  fail "Case 5c: repo .gitignore was modified (R2 self-containment violation)"
fi

# =============================================================================
# CASE 6: Config-state echo (R12) — four-line block layout
# =============================================================================
echo -e "${YELLOW}--- Case 6: Config-state echo (R12) ---${NC}"

# Workflow.md must contain the four field labels in order.
WF_TEXT="$(cat "$WORKFLOW_FILE")"
assert_grep "clawpatch:" "$WF_TEXT" "Case 6: workflow.md echo block names clawpatch version line"
assert_grep "CLAWPATCH_PROVIDER:" "$WF_TEXT" "Case 6: workflow.md echo block names CLAWPATCH_PROVIDER line"
assert_grep "flow-next review backend:" "$WF_TEXT" "Case 6: workflow.md echo block names flow-next review backend line"
assert_grep ".clawpatch/ last-mapped:" "$WF_TEXT" "Case 6: workflow.md echo block names .clawpatch/ last-mapped line"
assert_grep "informational; not proxied" "$WF_TEXT" "Case 6: workflow.md echo block flags backend as informational"

# =============================================================================
# CASE 7: Argument parsing — `--`, --source validation
# =============================================================================
echo -e "${YELLOW}--- Case 7: Argument parsing ---${NC}"

ARG_GUARD="$TEST_DIR/arg_guard.sh"
cat > "$ARG_GUARD" <<'BASH'
#!/usr/bin/env bash
set -e
SOURCE="heuristic"
EXTRA_PASSTHROUGH=()
seen_dashdash=0

# Disable globbing so passthrough tokens like `*.py` reach clawpatch verbatim.
set -f
# shellcheck disable=SC2086
set -- $ARGUMENTS
set +f
while [[ $# -gt 0 ]]; do
  if [[ "$seen_dashdash" == "1" ]]; then
    EXTRA_PASSTHROUGH+=("$1")
    shift
    continue
  fi
  case "$1" in
    --) seen_dashdash=1 ;;
    --source)
      if [[ $# -lt 2 || "$2" == "--" ]]; then
        echo "Error: --source requires a value (one of: heuristic, auto, agent)" >&2
        exit 2
      fi
      SOURCE="$2"
      shift
      ;;
    --source=*) SOURCE="${1#--source=}" ;;
    *) EXTRA_PASSTHROUGH+=("$1") ;;
  esac
  shift
done

case "$SOURCE" in
  heuristic|auto|agent) ;;
  *)
    echo "Error: --source must be one of: heuristic, auto, agent (got: $SOURCE)" >&2
    exit 2
    ;;
esac

echo "SOURCE=$SOURCE"
echo "EXTRA=${EXTRA_PASSTHROUGH[*]}"
BASH
chmod +x "$ARG_GUARD"

# 7a: empty args → default heuristic
rc=0
out="$(ARGUMENTS="" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 7a: empty args exit 0"
assert_grep "SOURCE=heuristic" "$out" "Case 7a: default SOURCE=heuristic"

# 7b: --source auto
rc=0
out="$(ARGUMENTS="--source auto" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 7b: --source auto exit 0"
assert_grep "SOURCE=auto" "$out" "Case 7b: SOURCE=auto"

# 7c: --source=agent (equals form)
rc=0
out="$(ARGUMENTS="--source=agent" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 7c: --source=agent exit 0"
assert_grep "SOURCE=agent" "$out" "Case 7c: SOURCE=agent (equals form)"

# 7d: -- terminator → extras flow through
rc=0
out="$(ARGUMENTS="-- --since-ref origin/main --paths src/" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 7d: -- terminator exit 0"
assert_grep "EXTRA=--since-ref origin/main --paths src/" "$out" "Case 7d: extras flow through"

# 7e: invalid --source → exit 2
rc=0
err="$(ARGUMENTS="--source nope" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 7e: invalid --source exits 2"
assert_grep "must be one of" "$err" "Case 7e: error names valid sources"

# 7f: dangling --source (end of args) → exit 2 cleanly, not crash under set -e
rc=0
err="$(ARGUMENTS="--source" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 7f: dangling --source at end of args exits 2 cleanly"
assert_grep "requires a value" "$err" "Case 7f: dangling --source emits 'requires a value'"

# 7g: --source followed by passthrough terminator → exit 2 cleanly
rc=0
err="$(ARGUMENTS="--source -- --paths src/" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 2 "$rc" "Case 7g: --source immediately before -- exits 2 cleanly"
assert_grep "requires a value" "$err" "Case 7g: --source-before-terminator emits 'requires a value'"

# 7h: glob in passthrough → reaches EXTRA verbatim (not expanded by skill)
# Stage a file in cwd that *would* match `*.py` if globbing were active;
# the canonical contract: `*.py` arrives as the literal string, not a list.
GLOB_DIR="$TEST_DIR/case7h"
mkdir -p "$GLOB_DIR"
touch "$GLOB_DIR/a.py" "$GLOB_DIR/b.py"
rc=0
out="$(cd "$GLOB_DIR" && ARGUMENTS="-- --paths *.py" bash "$ARG_GUARD" 2>&1)" || rc=$?
assert_rc 0 "$rc" "Case 7h: glob in passthrough exits 0"
assert_grep "EXTRA=--paths *.py" "$out" "Case 7h: glob '*.py' reaches EXTRA verbatim (set -f protects)"
# Negative: must NOT see expanded names a.py / b.py in EXTRA
if grep -qE 'EXTRA=.*\ba\.py\b' <<< "$out"; then
  fail "Case 7h: glob was expanded against cwd (a.py present in EXTRA) — set -f protection failed"
else
  ok "Case 7h: glob '*.py' was NOT expanded against cwd (set -f effective)"
fi

# =============================================================================
# Summary
# =============================================================================
TOTAL=$((PASS + FAIL))
echo
echo -e "${YELLOW}--- Summary ---${NC}"
echo "  Passed: $PASS / $TOTAL"
if [[ "$FAIL" -gt 0 ]]; then
  echo -e "${RED}  Failed: $FAIL${NC}"
  exit 1
fi
echo -e "${GREEN}  All cases passed.${NC}"
