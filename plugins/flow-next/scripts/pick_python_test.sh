#!/usr/bin/env bash
# fn-77-windows-python3-stub-fix-cross-context.5 — POSIX regression harness (R8, R9).
#
# Proves the shared functionality/version probe (scripts/lib/pick-python.sh) and the
# self-contained bash launcher (scripts/flowctl) reject the Microsoft Store
# `python3` App Execution Alias stub — a present-on-PATH interpreter that prints
# "Python was not found" and exits 9009 — and fall through to a working one,
# while keeping `python3`-first on mac/linux (no regression).
#
# This is the mac/linux/Git-Bash unit layer. The real windows-latest end-to-end
# coverage of flowctl.cmd + the bash launcher lives in the dedicated CI job
# (.github/workflows/test-flow-next.yml, job `windows-python3-stub`).
#
# Pure shell + a fake-stub PATH — no LLM invocations, no network. Targets <5s.
# Pattern follows alias_smoke.sh (file-backed PASS/FAIL counters).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="$SCRIPT_DIR/lib/pick-python.sh"
LAUNCHER="$SCRIPT_DIR/flowctl"

# A known-good real interpreter to back the fake `python`/`py` stubs. python3 on
# mac/linux; python (python.exe) on Windows Git Bash where python3 may be absent.
REAL_PY="$(command -v python3 || command -v python || true)"
if [ -z "$REAL_PY" ]; then
  echo "ERROR: need a working python3 or python on PATH to seed the harness" >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/pick-python-test-$$}"
TEST_DIR="${TEST_DIR//\\//}"
mkdir -p "$TEST_DIR"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0
ok()  { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
ko()  { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }

cleanup() {
  if [ "${KEEP_TEST_DIR:-0}" = "1" ]; then
    echo "Keeping test dir: $TEST_DIR"
    return
  fi
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo -e "${YELLOW}=== pick_python: Windows 9009-stub regression harness ===${NC}"

# ── Build the fake interpreter matrix ─────────────────────────────────────────
# python3  == the 9009 Store stub: present on PATH, non-functional on exec.
# python   == a working interpreter (delegates to the real one).
# py       == the py launcher; `py -3 ...` runs real Python (never a Store stub).
FAKE="$TEST_DIR/fakebin"; mkdir -p "$FAKE"
cat > "$FAKE/python3" <<EOF
#!/bin/bash
echo "Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases." >&2
exit 9009
EOF
cat > "$FAKE/python" <<EOF
#!/bin/bash
exec "$REAL_PY" "\$@"
EOF
cat > "$FAKE/py" <<EOF
#!/bin/bash
if [ "\${1:-}" = "-3" ]; then shift; fi
exec "$REAL_PY" "\$@"
EOF
chmod +x "$FAKE/python3" "$FAKE/python" "$FAKE/py"

# ── Baseline: the OLD presence-check (`command -v`) is fooled by the stub ──────
echo -e "${YELLOW}--- baseline: presence-check accepts the stub, exec rejects it ---${NC}"
if PATH="$FAKE:$PATH" bash -c 'command -v python3 >/dev/null'; then
  ok "OLD \`command -v python3\` selects the stub (presence, not functionality)"
else
  ko "expected \`command -v python3\` to find the stub"
fi
# The real Store stub exits 9009 (a native 32-bit code); bash truncates exit
# codes to 8 bits, so here we only assert NON-ZERO — which is exactly what the
# functionality probe rejects. The literal 9009 is verified in the Windows CI job.
PATH="$FAKE:$PATH" "$FAKE/python3" -c "import sys" >/dev/null 2>&1; stub_rc=$?
if [ "$stub_rc" -ne 0 ]; then
  ok "the stub exits non-zero on \`-c import sys\` (why presence-checking is unsafe)"
else
  ko "expected the fake stub to exit non-zero, got $stub_rc"
fi

# ── The NEW probe: resolve pick_python in an isolated shell ────────────────────
# Runs the resolver with a given PATH/env and prints FLOW_PY joined by '|'.
resolve() {
  local newpath="$1"; shift
  env -i PATH="$newpath" "$@" /bin/bash -c '
    set -uo pipefail
    . "'"$HELPER"'"
    if pick_python; then printf "%s|" "${FLOW_PY[@]}"; echo " rc=0"; else echo "NONE rc=$?"; fi
  '
}

echo -e "${YELLOW}--- pick_python resolution (functionality probe) ---${NC}"

# S1: Windows-like WITH py — py works, python3 is the stub, python works.
#     Expect FLOW_PY=(py -3): stub skipped AND py -3 preferred (two-word case).
out="$(resolve "$FAKE")"
case "$out" in
  "py|-3| rc=0") ok "S1 py -3 preferred, 9009 stub skipped (two-word array)";;
  *) ko "S1 expected 'py|-3|' got '$out'";;
esac

# S2: Windows-like WITHOUT py — only python3 (stub) + python (works).
#     Expect FLOW_PY=(python): stub rejected, falls through to bare python.
FAKE2="$TEST_DIR/fakebin2"; mkdir -p "$FAKE2"
cp "$FAKE/python3" "$FAKE/python" "$FAKE2/"
out="$(resolve "$FAKE2")"
case "$out" in
  "python| rc=0") ok "S2 stub rejected, fell through to python (single-word array)";;
  *) ko "S2 expected 'python|' got '$out'";;
esac

# S3 (R8): mac/linux — a working python3, no py. Expect FLOW_PY=(python3) first.
#     Skipped where the real interpreter is not named python3 (Windows Git Bash).
echo -e "${YELLOW}--- R8: mac/linux no-regression ---${NC}"
if [ "$(basename "$REAL_PY")" = "python3" ]; then
  out="$(resolve "$(dirname "$REAL_PY")")"
  case "$out" in
    "python3| rc=0") ok "S3 (R8) python3 selected first — no mac/linux regression";;
    *) ko "S3 (R8) expected 'python3|' got '$out'";;
  esac
else
  ok "S3 (R8) skipped — real interpreter is '$(basename "$REAL_PY")', not python3 (Windows Git Bash)"
fi

# S4a: PYTHON_BIN override IS probed — a broken override (stub) is rejected.
echo -e "${YELLOW}--- PYTHON_BIN scalar override is probed, not trusted ---${NC}"
out="$(resolve "$FAKE" PYTHON_BIN=python3)"
case "$out" in
  "py|-3| rc=0") ok "S4a broken PYTHON_BIN=python3 (stub) rejected, falls through";;
  *) ko "S4a expected 'py|-3|' got '$out'";;
esac

# S4b: PYTHON_BIN override pointing at a WORKING interpreter is selected first.
out="$(resolve "$FAKE" PYTHON_BIN=python)"
case "$out" in
  "python| rc=0") ok "S4b working PYTHON_BIN=python override selected first";;
  *) ko "S4b expected 'python|' got '$out'";;
esac

# S5: nothing works -> pick_python returns non-zero.
echo -e "${YELLOW}--- no working interpreter -> non-zero ---${NC}"
FAKE3="$TEST_DIR/fakebin3"; mkdir -p "$FAKE3"
cp "$FAKE/python3" "$FAKE3/"   # only the stub
out="$(resolve "$FAKE3")"
case "$out" in
  NONE*) ok "S5 only the stub on PATH -> pick_python returns non-zero";;
  *) ko "S5 expected NONE got '$out'";;
esac

# S5b: working-but-too-old candidates are rejected with the distinct minimum
# version error rather than being conflated with Store stubs/missing commands.
FAKE_OLD="$TEST_DIR/fakebin-old"; mkdir -p "$FAKE_OLD"
for name in py python3 python; do
  cat > "$FAKE_OLD/$name" <<'EOF'
#!/bin/bash
exit 3
EOF
  chmod +x "$FAKE_OLD/$name"
done
out="$(env -i PATH="$FAKE_OLD:/usr/bin:/bin" /bin/bash -c '
  . "'"$HELPER"'"
  if pick_python; then echo UNEXPECTED; else flow_python_error flowctl; fi
' 2>&1)"
if printf '%s' "$out" | grep -q "Python 3.11 or newer is required"; then
  ok "S5b working Python below 3.11 gets the actionable minimum-version error"
else
  ko "S5b expected Python 3.11 minimum error, got '$out'"
fi

# ── The resolved FLOW_PY array actually EXECUTES (both forms) ──────────────────
echo -e "${YELLOW}--- resolved array runs: two-word 'py -3' AND bare python3 ---${NC}"
exec_marker() {  # resolve on $1's PATH, then exec "${FLOW_PY[@]}" -c print(marker)
  local newpath="$1"
  env -i PATH="$newpath" /bin/bash -c '
    set -uo pipefail
    . "'"$HELPER"'"
    pick_python || { echo "NO-INTERP"; exit 1; }
    "${FLOW_PY[@]}" -c "print(\"EXEC-OK:\" + \"'"$2"'\")"
  ' 2>&1
}
# Two-word `py -3` array executes.
out="$(exec_marker "$FAKE" pyform)"
if printf '%s' "$out" | grep -q "EXEC-OK:pyform"; then
  ok "resolved (py -3) array execs a real interpreter"
else
  ko "expected EXEC-OK from (py -3) array, got '$out'"
fi
# Bare python3 array executes (real python3, no py present).
if [ "$(basename "$REAL_PY")" = "python3" ]; then
  out="$(exec_marker "$(dirname "$REAL_PY")" py3form)"
  if printf '%s' "$out" | grep -q "EXEC-OK:py3form"; then
    ok "resolved (python3) array execs a real interpreter"
  else
    ko "expected EXEC-OK from (python3) array, got '$out'"
  fi
else
  ok "bare-python3 exec skipped — real interpreter is not python3 (Windows Git Bash)"
fi

# ── The self-contained launcher: end-to-end exec through the inline probe ──────
echo -e "${YELLOW}--- bash launcher (inline probe) end-to-end ---${NC}"
LDIR="$TEST_DIR/ldir"; mkdir -p "$LDIR"
cp "$LAUNCHER" "$LDIR/flowctl"; chmod +x "$LDIR/flowctl"
cat > "$LDIR/flowctl.py" <<'PY'
import sys
print("ARGS:", sys.argv[1:])
PY

# S6: launcher with py present + python3=stub -> execs successfully (via py -3),
#     forwarding args. /usr/bin:/bin keep the launcher's `dirname`/coreutils.
out="$(env -i PATH="$FAKE:/usr/bin:/bin" /bin/bash "$LDIR/flowctl" hello world 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "ARGS: \['hello', 'world'\]"; then
  ok "S6 launcher execs via probed interpreter + forwards args (python3=stub)"
else
  ko "S6 launcher failed rc=$rc: $out"
fi

# S7: launcher where every python candidate is a stub -> errors non-zero, cleanly.
FAKE4="$TEST_DIR/fakebin4"; mkdir -p "$FAKE4"
cp "$FAKE/python3" "$FAKE4/python3"
cp "$FAKE/python3" "$FAKE4/python"   # 'python' is a stub too; no py present
out="$(env -i PATH="$FAKE4:/usr/bin:/bin" /bin/bash "$LDIR/flowctl" hello 2>&1)"; rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "no working Python interpreter"; then
  ok "S7 launcher errors cleanly when no interpreter works"
else
  ko "S7 launcher should have errored non-zero: rc=$rc: $out"
fi

# S8: a functional probe reporting an old interpreter must stop before loading
# flowctl.py and use the precise minimum-version diagnostic.
cat > "$LDIR/flowctl.py" <<'PY'
print("SOURCE-LOADED-UNEXPECTEDLY")
PY
out="$(env -i PATH="$FAKE_OLD:/usr/bin:/bin" /bin/bash "$LDIR/flowctl" hello 2>&1)"; rc=$?
if [ "$rc" -ne 0 ] \
  && printf '%s' "$out" | grep -q "Python 3.11 or newer is required" \
  && ! printf '%s' "$out" | grep -q "SOURCE-LOADED-UNEXPECTEDLY"; then
  ok "S8 launcher rejects Python below 3.11 before loading flowctl.py"
else
  ko "S8 expected pre-import Python minimum rejection: rc=$rc: $out"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo -e "${GREEN}All pick_python regression tests passed!${NC}"
