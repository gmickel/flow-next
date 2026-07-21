# pick-python.sh — shared Python interpreter resolver for flow-next.
#
# Source this file, then call pick_python:
#   . "$SCRIPT_DIR/lib/pick-python.sh"        # resolver path varies by layout
#   pick_python || { flow_python_error "tool-name"; exit 1; }
#   exec "${FLOW_PY[@]}" some_script.py "$@"
#
# Two distinct names — do NOT conflate them:
#   PYTHON_BIN — optional user override: a *scalar* command name (e.g. python3.12,
#                py). Exportable; read as the first candidate, but still probed.
#                A bash array cannot be exported, so the override must stay scalar.
#   FLOW_PY    — the *resolved bash array* this fills (e.g. (python3) | (python) |
#                (py -3)). Callers exec "${FLOW_PY[@]}". An array is required so it
#                can carry the two-word `py -3`; a single string cannot be both a
#                multi-word invocation and a space-safe single token.
#
# Probe = functionality + minimum version. Each candidate must actually run and
# report Python 3.11+. This rejects the Windows Store `python3`
# App Execution Alias stub — a 0-byte reparse point that prints "Python was not
# found" and exits 9009 (never 0 with -c; bpo-41327) — which a bare `command -v`
# would wrongly accept, and equally rejects a genuinely-absent interpreter.
#
# Candidate order:  $PYTHON_BIN -> py -3 -> python3 -> python
#   `py -3` is first on Windows because the py launcher (C:\Windows\py.exe) is
#   installed by python.org / registry-resolved and is never a Store alias stub.
#   On mac/linux there is no `py`, so resolution falls through cleanly to
#   `python3` — identical to the pre-fix behavior (no regression).
#
# set -u-safe: PYTHON_BIN is read via ${PYTHON_BIN:-}. Callers running under
# `set -u` should guard reads as "${FLOW_PY[@]:-}" until pick_python has
# returned 0 (after which FLOW_PY is guaranteed non-empty).

pick_python() {
  FLOW_PY=()
  FLOW_PY_TOO_OLD=()
  local _cand
  local _rc
  local -a _argv
  for _cand in "${PYTHON_BIN:-}" "py -3" "python3" "python"; do
    [ -n "$_cand" ] || continue
    # Intentional word-split so the two-word `py -3` becomes two argv elements.
    read -r -a _argv <<< "$_cand"
    [ "${#_argv[@]}" -gt 0 ] || continue
    if "${_argv[@]}" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 3)" >/dev/null 2>&1; then
      FLOW_PY=("${_argv[@]}")
      return 0
    else
      _rc=$?
    fi
    if [ "$_rc" -eq 3 ]; then
      FLOW_PY_TOO_OLD+=("$_cand")
    fi
  done
  return 1
}

flow_python_error() {
  local _owner="${1:-flow-next}"
  if [ "${#FLOW_PY_TOO_OLD[@]}" -gt 0 ]; then
    echo "$_owner: Python 3.11 or newer is required; working but too-old candidate(s): ${FLOW_PY_TOO_OLD[*]}." >&2
    echo "  Install a supported Python, or set PYTHON_BIN to its command name." >&2
  else
    echo "$_owner: no working Python interpreter found (tried \$PYTHON_BIN, py -3, python3, python)." >&2
  fi
}
