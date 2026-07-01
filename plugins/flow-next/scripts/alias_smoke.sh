#!/usr/bin/env bash
# fn-43-rename-epic-spec-across-flow-next.14
# Smoke tests for the deprecation-alias layer (T2 + T4): every legacy
# `flowctl epic*` / `--epic` / `EPICS_FILE` form must dispatch to the same
# canonical handler AND emit a one-shot stderr deprecation. Persisted JSON
# uses canonical keys only ("spec" / "specs"); legacy keys ("epic" / "epics")
# are co-emitted on read paths through 1.x (R31 dual-emit) and on `next`
# blocked-task output via `legacy_reason`.
#
# Each assertion runs in a fresh subshell so the per-process
# `_RENAME_DEPRECATION_EMITTED` set starts clean and the deprecation fires.
#
# Covers the 7 high-value alias paths from T14 spec (+ Case 9, fn-58.1):
#   1. `flowctl epic create` → cmd_spec_create dispatch + stderr deprecation
#   2. `flowctl epics --json` payload contains BOTH "specs": and "epics":
#   3. `flowctl tasks --epic <id> --json` matches `--spec`; persisted task JSON
#      contains "spec": only (no "epic":)
#   4. `--section epic` matches `--section spec`; payload contains BOTH "spec"
#      and "epic" top-level keys
#   5. Top-level `flowctl show fn-X` (NOT renamed) resolves spec + task
#   6. `EPICS_FILE=...` env var works AND emits deprecation; `SPECS_FILE=...`
#      is silent
#   7. `flowctl next --json` blocked-task contains BOTH "reason" AND
#      "legacy_reason"
#   9. `flowctl epic ready` / `epic unready` → cmd_spec_ready/_unready
#      dispatch + stderr deprecation; canonical `spec ready` silent (fn-58.1)
#
# Plus the FLOW_NO_DEPRECATION=1 suppression matrix.
#
# Pure shell + Python harness — no LLM invocations. Targets <30s runtime.
# Pattern follows smoke_test.sh / prospect_smoke_test.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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

# shellcheck source=lib/pick-python.sh
. "$SCRIPT_DIR/lib/pick-python.sh"
pick_python || { echo "ERROR: python not found (need python3 or python in PATH)" >&2; exit 1; }

# Safety: never run from the main plugin repo.
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/alias-smoke-$$}"
TEST_DIR="${TEST_DIR//\\//}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$TEST_DIR"
PASS_LOG="$TEST_DIR/.pass.log"
FAIL_LOG="$TEST_DIR/.fail.log"
: > "$PASS_LOG"
: > "$FAIL_LOG"
export PASS_LOG FAIL_LOG GREEN RED NC

cleanup() {
  if [[ "${KEEP_TEST_DIR:-0}" == "1" ]]; then
    echo "Keeping test dir: $TEST_DIR"
    return
  fi
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Counters live in files so subshell `ok`/`ko` calls aggregate correctly.
ok() { echo -e "${GREEN}✓${NC} $*"; printf '.\n' >> "$PASS_LOG"; }
ko() { echo -e "${RED}✗${NC} $*"; printf '.\n' >> "$FAIL_LOG"; }
export -f ok ko

echo -e "${YELLOW}=== alias deprecation smoke tests ===${NC}"

mkdir -p "$TEST_DIR/repo/scripts"
cd "$TEST_DIR/repo"
git init -q

cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl" scripts/flowctl
chmod +x scripts/flowctl

scripts/flowctl init --json >/dev/null

# Seed an initial commit so `spec export-cognitive-aid --base HEAD` has a
# merge-base anchor (Case 4 below).
git config user.email "alias-smoke@test"
git config user.name "Alias Smoke"
git add -A >/dev/null 2>&1 || true
git commit -q --allow-empty -m "init" >/dev/null 2>&1 || true

# Suppress the auto-migrate banner globally — we test it separately in
# migration_smoke.sh / banner_smoke.sh. The banner can't fire on a fresh
# init anyway (no .flow/epics/), but we set the knob so any test that
# seeds a pre-1.0 fixture below doesn't surface the banner.
export FLOW_NO_AUTO_MIGRATE=1

# ─────────────────────────────────────────────────────────────────────────────
# Case 1: `flowctl epic create` → cmd_spec_create dispatch + stderr deprecation
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 1: flowctl epic create dispatch + deprecation ---${NC}"
(
  STDERR_FILE="$TEST_DIR/case1-stderr.txt"
  STDOUT="$(scripts/flowctl epic create --title "Case 1 alias" --json 2>"$STDERR_FILE")"
  STDERR="$(cat "$STDERR_FILE")"

  # Stdout matches canonical shape (success + id + spec_path).
  case1_id="$(echo "$STDOUT" | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  if [[ -n "$case1_id" && "$case1_id" =~ ^fn-[0-9]+- ]]; then
    ok "Case 1: \`flowctl epic create\` returns canonical id ($case1_id)"
  else
    ko "Case 1: \`flowctl epic create\` did not return a canonical id; got: $STDOUT"
  fi

  # Stderr carries the deprecation marker.
  if echo "$STDERR" | grep -q 'flowctl epic is deprecated; use flowctl spec'; then
    ok "Case 1: stderr emits 'flowctl epic is deprecated' marker"
  else
    ko "Case 1: stderr missing deprecation marker; got: $STDERR"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 2: `flowctl epics --json` payload contains BOTH "specs": and "epics":
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 2: flowctl epics --json dual-emit + deprecation ---${NC}"
(
  STDERR_FILE="$TEST_DIR/case2-stderr.txt"
  STDOUT="$(scripts/flowctl epics --json 2>"$STDERR_FILE")"
  STDERR="$(cat "$STDERR_FILE")"

  # Both "specs" and "epics" keys present (R31 co-emit).
  if echo "$STDOUT" | "${FLOW_PY[@]}" -c '
import json, sys
data = json.load(sys.stdin)
assert "specs" in data, "missing canonical specs key"
assert "epics" in data, "missing legacy epics key"
print("OK")
' >/dev/null; then
    ok "Case 2: \`flowctl epics --json\` dual-emits 'specs' and 'epics' keys"
  else
    ko "Case 2: dual-emit missing in flowctl epics --json output: $STDOUT"
  fi

  # Stderr deprecation present.
  if echo "$STDERR" | grep -q 'flowctl epics is deprecated; use flowctl specs'; then
    ok "Case 2: stderr emits 'flowctl epics is deprecated' marker"
  else
    ko "Case 2: stderr missing deprecation marker; got: $STDERR"
  fi

  # Canonical `flowctl specs --json` must NOT emit deprecation.
  CANONICAL_STDERR_FILE="$TEST_DIR/case2-canonical-stderr.txt"
  scripts/flowctl specs --json 2>"$CANONICAL_STDERR_FILE" >/dev/null
  CANONICAL_STDERR="$(cat "$CANONICAL_STDERR_FILE")"
  if [[ -z "$CANONICAL_STDERR" ]]; then
    ok "Case 2: canonical \`flowctl specs\` is silent on stderr"
  else
    ko "Case 2: canonical flowctl specs leaked to stderr: $CANONICAL_STDERR"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 3: `flowctl tasks --epic <id>` matches `--spec`; persisted task JSON
# contains "spec": only.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 3: flowctl tasks --epic alias + canonical task JSON ---${NC}"
(
  CASE3_SPEC="$(scripts/flowctl spec create --title "Case 3 alias" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$CASE3_SPEC" --title "First" --json >/dev/null
  scripts/flowctl task create --spec "$CASE3_SPEC" --title "Second" --json >/dev/null

  # Canonical --spec.
  CANONICAL_OUT="$(scripts/flowctl tasks --spec "$CASE3_SPEC" --json 2>/dev/null)"

  # Legacy --epic.
  LEGACY_STDERR_FILE="$TEST_DIR/case3-stderr.txt"
  LEGACY_OUT="$(scripts/flowctl tasks --epic "$CASE3_SPEC" --json 2>"$LEGACY_STDERR_FILE")"
  LEGACY_STDERR="$(cat "$LEGACY_STDERR_FILE")"

  # Outputs must be byte-identical (same payload, same task list).
  if [[ "$CANONICAL_OUT" == "$LEGACY_OUT" ]]; then
    ok "Case 3: \`tasks --epic\` output identical to \`tasks --spec\`"
  else
    ko "Case 3: outputs diverge.\n  canonical: $CANONICAL_OUT\n  legacy:    $LEGACY_OUT"
  fi

  # Legacy form emits deprecation.
  if echo "$LEGACY_STDERR" | grep -q '\-\-epic is deprecated; use \-\-spec'; then
    ok "Case 3: \`tasks --epic\` emits stderr deprecation"
  else
    ko "Case 3: stderr missing deprecation; got: $LEGACY_STDERR"
  fi

  # Persisted task JSON has "spec" only (no "epic" — fn-43.2 invariant).
  TASK_JSON_PATH=".flow/tasks/${CASE3_SPEC}.1.json"
  if [[ -f "$TASK_JSON_PATH" ]]; then
    if "${FLOW_PY[@]}" -c '
import json, sys
data = json.load(open(sys.argv[1]))
assert "spec" in data, "missing canonical spec key on disk"
leaked = data.get("epic")
assert leaked is None, "legacy epic key leaked to disk: %s" % (leaked,)
print("OK")
' "$TASK_JSON_PATH" >/dev/null; then
      ok "Case 3: persisted task JSON has 'spec' only (no 'epic')"
    else
      ko "Case 3: persisted task JSON shape wrong"
      cat "$TASK_JSON_PATH" | sed 's/^/    /'
    fi
  else
    ko "Case 3: task JSON not found at $TASK_JSON_PATH"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 4: `--section epic` matches `--section spec`; payload top-level
# contains BOTH "spec" and "epic" keys.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 4: --section epic alias + dual-emit payload ---${NC}"
(
  CASE4_SPEC="$(scripts/flowctl spec create --title "Case 4 alias" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  cat > "$TEST_DIR/case4-spec.md" <<'EOF'
# Case 4 spec

## Acceptance

- **R1:** Trivial criterion.
EOF
  scripts/flowctl spec set-plan "$CASE4_SPEC" --file "$TEST_DIR/case4-spec.md" --json >/dev/null

  CANONICAL_OUT="$(scripts/flowctl spec export-cognitive-aid "$CASE4_SPEC" --base HEAD --section spec --json 2>/dev/null)"
  LEGACY_STDERR_FILE="$TEST_DIR/case4-stderr.txt"
  LEGACY_OUT="$(scripts/flowctl spec export-cognitive-aid "$CASE4_SPEC" --base HEAD --section epic --json 2>"$LEGACY_STDERR_FILE")"
  LEGACY_STDERR="$(cat "$LEGACY_STDERR_FILE")"

  if [[ "$CANONICAL_OUT" == "$LEGACY_OUT" ]]; then
    ok "Case 4: \`--section epic\` output identical to \`--section spec\`"
  else
    ko "Case 4: outputs diverge"
  fi

  if echo "$LEGACY_STDERR" | grep -q '\-\-section epic is deprecated; use \-\-section spec'; then
    ok "Case 4: \`--section epic\` emits stderr deprecation"
  else
    ko "Case 4: stderr missing deprecation; got: $LEGACY_STDERR"
  fi

  # Payload has BOTH top-level "spec" and "epic" keys (same value).
  if echo "$LEGACY_OUT" | "${FLOW_PY[@]}" -c '
import json, sys
data = json.load(sys.stdin)
assert "spec" in data, "missing canonical spec key"
assert "epic" in data, "missing legacy epic key"
assert data["spec"] == data["epic"], "spec/epic payload diverged"
print("OK")
' >/dev/null; then
    ok "Case 4: payload top-level dual-emits 'spec' and 'epic' (R31)"
  else
    ko "Case 4: payload missing spec/epic dual-emit"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 5: Top-level `flowctl show fn-X` (NOT renamed). Resolves both spec
# and task ids identically pre- and post-rename. No `flowctl spec show`
# subcommand exists.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 5: flowctl show top-level (not renamed) ---${NC}"
(
  CASE5_SPEC="$(scripts/flowctl spec create --title "Case 5 alias" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$CASE5_SPEC" --title "Task A" --json >/dev/null
  CASE5_TASK="${CASE5_SPEC}.1"

  # show on spec id resolves.
  if scripts/flowctl show "$CASE5_SPEC" --json 2>/dev/null \
       | "${FLOW_PY[@]}" -c "import json,sys; d=json.load(sys.stdin); assert d['id']=='${CASE5_SPEC}'; print('OK')" >/dev/null; then
    ok "Case 5: \`flowctl show <spec-id>\` resolves spec"
  else
    ko "Case 5: \`flowctl show <spec-id>\` failed to resolve"
  fi

  # show on task id resolves.
  if scripts/flowctl show "$CASE5_TASK" --json 2>/dev/null \
       | "${FLOW_PY[@]}" -c "import json,sys; d=json.load(sys.stdin); assert d['id']=='${CASE5_TASK}'; print('OK')" >/dev/null; then
    ok "Case 5: \`flowctl show <task-id>\` resolves task"
  else
    ko "Case 5: \`flowctl show <task-id>\` failed to resolve"
  fi

  # Confirm NO `flowctl spec show` subcommand was introduced (top-level
  # show is the only canonical surface).
  set +e
  scripts/flowctl spec show "$CASE5_SPEC" --json >/dev/null 2>&1
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    ok "Case 5: \`flowctl spec show\` rejected (no new subcommand introduced)"
  else
    ko "Case 5: \`flowctl spec show\` unexpectedly succeeded — drift from spec"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 6: `EPICS_FILE=` env var on `flowctl next` works AND emits stderr
# deprecation; `SPECS_FILE=` is silent.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 6: EPICS_FILE / SPECS_FILE env-var alias ---${NC}"
(
  CASE6_SPEC="$(scripts/flowctl spec create --title "Case 6 alias" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$CASE6_SPEC" --title "Task" --json >/dev/null
  printf '{"specs":["%s"]}\n' "$CASE6_SPEC" > "$TEST_DIR/case6-list.json"

  # Canonical SPECS_FILE — silent on stderr.
  CANONICAL_STDERR_FILE="$TEST_DIR/case6-canonical-stderr.txt"
  SPECS_FILE="$TEST_DIR/case6-list.json" scripts/flowctl next --json 2>"$CANONICAL_STDERR_FILE" >/dev/null
  CANONICAL_STDERR="$(cat "$CANONICAL_STDERR_FILE")"
  if [[ -z "$CANONICAL_STDERR" ]]; then
    ok "Case 6: SPECS_FILE env var is silent on stderr"
  else
    ko "Case 6: SPECS_FILE env var leaked to stderr: $CANONICAL_STDERR"
  fi

  # Legacy EPICS_FILE — emits deprecation.
  LEGACY_STDERR_FILE="$TEST_DIR/case6-legacy-stderr.txt"
  EPICS_FILE="$TEST_DIR/case6-list.json" scripts/flowctl next --json 2>"$LEGACY_STDERR_FILE" >/dev/null
  LEGACY_STDERR="$(cat "$LEGACY_STDERR_FILE")"
  if echo "$LEGACY_STDERR" | grep -q 'EPICS_FILE is deprecated; use SPECS_FILE'; then
    ok "Case 6: EPICS_FILE env var emits stderr deprecation"
  else
    ko "Case 6: stderr missing deprecation marker; got: $LEGACY_STDERR"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 7: `flowctl next --json` blocked-task contains BOTH "reason" AND
# "legacy_reason" (R31 dual-emit on the canonical reason code).
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 7: flowctl next blocked-task dual-emit (reason/legacy_reason) ---${NC}"
(
  CASE7_BASE="$(scripts/flowctl spec create --title "Case 7 base" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$CASE7_BASE" --title "Base" --json >/dev/null
  CASE7_CHILD="$(scripts/flowctl spec create --title "Case 7 child" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

  # Inject a spec-level dependency directly into the spec JSON (probe both
  # canonical + legacy paths).
  spec_path() {
    if [[ -f ".flow/specs/${1}.json" ]]; then printf '.flow/specs/%s.json' "$1"
    elif [[ -f ".flow/epics/${1}.json" ]]; then printf '.flow/epics/%s.json' "$1"
    else printf '.flow/specs/%s.json' "$1"
    fi
  }
  CHILD_PATH="$(spec_path "$CASE7_CHILD")"
  "${FLOW_PY[@]}" - "$CHILD_PATH" "$CASE7_BASE" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
base = sys.argv[2]
data = json.loads(path.read_text())
data["depends_on_epics"] = [base]
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY

  printf '{"specs":["%s"]}\n' "$CASE7_CHILD" > "$TEST_DIR/case7-list.json"
  STDOUT="$(scripts/flowctl next --specs-file "$TEST_DIR/case7-list.json" --json 2>/dev/null)"

  if echo "$STDOUT" | "${FLOW_PY[@]}" -c '
import json, sys
data = json.load(sys.stdin)
assert data["status"] == "none", f"unexpected status: {data}"
assert "reason" in data, "missing canonical reason"
assert "legacy_reason" in data, "missing legacy_reason"
assert data["reason"] == "blocked_by_spec_deps", f"wrong reason: {data['reason']}"
assert data["legacy_reason"] == "blocked_by_epic_deps", f"wrong legacy_reason: {data['legacy_reason']}"
assert "blocked_specs" in data, "missing blocked_specs"
assert "blocked_epics" in data, "missing blocked_epics"
print("OK")
' >/dev/null; then
    ok "Case 7: blocked-task carries both reason + legacy_reason (R31)"
  else
    ko "Case 7: dual-emit missing on blocked-task; got: $STDOUT"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 8: FLOW_NO_DEPRECATION=1 suppresses stderr warnings on every alias
# entry-point covered above.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 8: FLOW_NO_DEPRECATION=1 suppresses alias warnings ---${NC}"
(
  CASE8_SPEC_STDERR_FILE="$TEST_DIR/case8-spec-stderr.txt"
  FLOW_NO_DEPRECATION=1 scripts/flowctl epic create --title "Case 8 silent" --json 2>"$CASE8_SPEC_STDERR_FILE" >/dev/null
  if [[ -z "$(cat "$CASE8_SPEC_STDERR_FILE")" ]]; then
    ok "Case 8: FLOW_NO_DEPRECATION=1 silences \`flowctl epic create\`"
  else
    ko "Case 8: FLOW_NO_DEPRECATION=1 did not silence; got: $(cat "$CASE8_SPEC_STDERR_FILE")"
  fi

  CASE8_TASKS_STDERR_FILE="$TEST_DIR/case8-tasks-stderr.txt"
  CASE8_SPEC_ID="$(scripts/flowctl spec create --title "Case 8 driver" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  scripts/flowctl task create --spec "$CASE8_SPEC_ID" --title "T" --json >/dev/null
  FLOW_NO_DEPRECATION=1 scripts/flowctl tasks --epic "$CASE8_SPEC_ID" --json 2>"$CASE8_TASKS_STDERR_FILE" >/dev/null
  if [[ -z "$(cat "$CASE8_TASKS_STDERR_FILE")" ]]; then
    ok "Case 8: FLOW_NO_DEPRECATION=1 silences \`tasks --epic\`"
  else
    ko "Case 8: FLOW_NO_DEPRECATION=1 did not silence tasks --epic; got: $(cat "$CASE8_TASKS_STDERR_FILE")"
  fi

  CASE8_NEXT_STDERR_FILE="$TEST_DIR/case8-next-stderr.txt"
  printf '{"specs":["%s"]}\n' "$CASE8_SPEC_ID" > "$TEST_DIR/case8-list.json"
  FLOW_NO_DEPRECATION=1 EPICS_FILE="$TEST_DIR/case8-list.json" scripts/flowctl next --json 2>"$CASE8_NEXT_STDERR_FILE" >/dev/null
  if [[ -z "$(cat "$CASE8_NEXT_STDERR_FILE")" ]]; then
    ok "Case 8: FLOW_NO_DEPRECATION=1 silences EPICS_FILE env"
  else
    ko "Case 8: FLOW_NO_DEPRECATION=1 did not silence EPICS_FILE env; got: $(cat "$CASE8_NEXT_STDERR_FILE")"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Case 9: `flowctl epic ready` / `epic unready` → cmd_spec_ready/_unready
# dispatch + stderr deprecation; canonical `spec ready` silent (fn-58.1).
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Case 9: flowctl epic ready/unready alias + deprecation ---${NC}"
(
  CASE9_SPEC="$(scripts/flowctl spec create --title "Case 9 ready alias" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

  # Legacy `epic ready` dispatches to the canonical handler + deprecates.
  STDERR_FILE="$TEST_DIR/case9-stderr.txt"
  STDOUT="$(scripts/flowctl epic ready "$CASE9_SPEC" --json 2>"$STDERR_FILE")"
  STDERR="$(cat "$STDERR_FILE")"
  if echo "$STDOUT" | "${FLOW_PY[@]}" -c '
import json, sys
data = json.load(sys.stdin)
assert data["ready"] is True, f"ready not set: {data}"
assert data["changed"] is True, f"expected changed: {data}"
print("OK")
' >/dev/null; then
    ok "Case 9: \`flowctl epic ready\` sets ready via canonical handler"
  else
    ko "Case 9: \`flowctl epic ready\` wrong payload; got: $STDOUT"
  fi
  if echo "$STDERR" | grep -q 'flowctl epic is deprecated; use flowctl spec'; then
    ok "Case 9: \`epic ready\` stderr emits deprecation marker"
  else
    ko "Case 9: stderr missing deprecation marker; got: $STDERR"
  fi

  # Legacy `epic unready` round-trips the flag.
  UNREADY_OUT="$(scripts/flowctl epic unready "$CASE9_SPEC" --json 2>/dev/null)"
  if echo "$UNREADY_OUT" | "${FLOW_PY[@]}" -c '
import json, sys
data = json.load(sys.stdin)
assert data["ready"] is False, f"ready not cleared: {data}"
print("OK")
' >/dev/null; then
    ok "Case 9: \`flowctl epic unready\` clears ready"
  else
    ko "Case 9: \`flowctl epic unready\` wrong payload; got: $UNREADY_OUT"
  fi

  # Canonical `spec ready` must be silent on stderr.
  CANONICAL_STDERR_FILE="$TEST_DIR/case9-canonical-stderr.txt"
  scripts/flowctl spec ready "$CASE9_SPEC" --json 2>"$CANONICAL_STDERR_FILE" >/dev/null
  scripts/flowctl spec unready "$CASE9_SPEC" --json 2>>"$CANONICAL_STDERR_FILE" >/dev/null
  if [[ -z "$(cat "$CANONICAL_STDERR_FILE")" ]]; then
    ok "Case 9: canonical \`spec ready/unready\` silent on stderr"
  else
    ko "Case 9: canonical spec ready/unready leaked to stderr: $(cat "$CANONICAL_STDERR_FILE")"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
PASS_COUNT="$(wc -l < "$PASS_LOG" | tr -d '[:space:]')"
FAIL_COUNT="$(wc -l < "$FAIL_LOG" | tr -d '[:space:]')"
echo -e "\n${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi

echo -e "${GREEN}All alias smoke tests passed!${NC}"
