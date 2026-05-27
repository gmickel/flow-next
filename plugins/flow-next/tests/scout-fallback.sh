#!/usr/bin/env bash
# Thin wrapper invoking the scout-fallback contract test (fn-50.3).
#
# Uniform test-runner entrypoint matching the other bash-shim tests
# (see plugin smoke scripts). The actual assertions live in
# `test_scout_fallback_contract.py` — this wrapper just runs them via
# `python -m unittest discover` (NOT pytest — repo standard, see
# `test_repo_map.py` fn-50.2 precedent and the CI workflow at
# `.github/workflows/test-flow-next.yml`).
#
# Quick command from spec:
#   bash plugins/flow-next/tests/scout-fallback.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 -m unittest discover \
  -s "$HERE" \
  -p "test_scout_fallback_contract.py" \
  -v
