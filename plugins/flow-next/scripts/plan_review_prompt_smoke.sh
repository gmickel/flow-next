#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Python interpreter resolution via the shared functionality probe (skips the
# Windows Store python3 alias stub; fills the FLOW_PY array). See lib/pick-python.sh.
# shellcheck source=lib/pick-python.sh
. "$SCRIPT_DIR/lib/pick-python.sh"
pick_python || { echo "ERROR: python not found (need python3 or python in PATH)" >&2; exit 1; }

# Safety: never run tests from the main plugin repo
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-/tmp/flow-next-plan-review-smoke-rp-$$}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
# SPEC_ID is captured from `flowctl spec create --json` below — fn-43 slugs
# titles into the id (e.g. fn-1-tiny-lib), so a hard-coded `fn-1` doesn't
# work. The env var still overrides for callers who control the title.
SPEC_ID="${EPIC_ID:-${SPEC_ID:-}}"

fail() { echo "plan_review_prompt_smoke: $*" >&2; exit 1; }

command -v "$CLAUDE_BIN" >/dev/null 2>&1 || fail "claude not found (set CLAUDE_BIN if needed)"
command -v rp-cli >/dev/null 2>&1 || fail "rp-cli not found (required for rp review)"

echo "Test dir: $TEST_DIR"

mkdir -p "$TEST_DIR/repo"
cd "$TEST_DIR/repo"

git init -q
git config user.email "plan-review-smoke@example.com"
git config user.name "Plan Review Smoke"
git checkout -b main >/dev/null 2>&1 || true

mkdir -p src
cat > src/index.ts <<'EOF'
export function add(a: number, b: number): number {
  return a + b;
}
EOF

cat > package.json <<'EOF'
{
  "name": "tmp-flow-next-plan-review-smoke",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "test": "node -e \"console.log('ok')\""
  }
}
EOF

cat > README.md <<'EOF'
# tmp-flow-next-plan-review-smoke

TBD
EOF

git add .
git commit -m "chore: init" >/dev/null

mkdir -p scripts/ralph
cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl" scripts/ralph/flowctl
chmod +x scripts/ralph/flowctl

FLOWCTL="scripts/ralph/flowctl"
$FLOWCTL init --json >/dev/null
# Capture the slug-stamped spec id from create's JSON output. fn-43+
# stamps the title into the id (e.g. "Tiny lib" -> fn-1-tiny-lib); a
# hard-coded fn-1 would no longer match.
if [[ -z "$SPEC_ID" ]]; then
  SPEC_ID=$($FLOWCTL spec create --title "Tiny lib" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['id'])")
else
  $FLOWCTL spec create --title "Tiny lib" --json >/dev/null
fi
EPIC_ID="$SPEC_ID"  # back-compat for callers reading the var name

cat > "$TEST_DIR/epic.md" <<'EOF'
# fn-1 Tiny lib

## Overview
Add a tiny add() helper doc update and verify README.

## Current State
- `add()` exists in `src/index.ts`
- README is a placeholder

## Scope
- `src/index.ts`: add brief JSDoc (params + return)
- `README.md`: add TS usage snippet and note TS tooling required

## Approach
Edit src/index.ts and README.md only. Repo is source-only (no build step).

## Quick commands
- `npm test` (smoke only)

## Acceptance
- [ ] `add(a: number, b: number): number` exported as named export
- [ ] `add()` has brief JSDoc (params + return)
- [ ] README includes:
  - snippet:
    ```ts
    import { add } from "./src/index.ts";
    console.log(add(1, 2)); // 3
    ```
  - note that TS tooling is required to run
- [ ] `npm test` passes (smoke only)

## Risks
- README import path is TypeScript source; call out runtime requirements

## References
- None
EOF

$FLOWCTL spec set-plan "$EPIC_ID" --file "$TEST_DIR/epic.md" --json >/dev/null

RUN_DIR="scripts/ralph/runs/smoke-plan-review"
RECEIPT_PATH="$RUN_DIR/receipts/plan-$EPIC_ID.json"
mkdir -p "$RUN_DIR/receipts"

PROMPT_OUT="$TEST_DIR/prompt_plan.txt"
"${FLOW_PY[@]}" - "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/prompt_plan.md" "$PROMPT_OUT" "$EPIC_ID" "$RECEIPT_PATH" <<'PY'
import sys
from pathlib import Path

tpl = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])
epic = sys.argv[3]
receipt = sys.argv[4]

text = tpl.replace("{{SPEC_ID}}", epic)
text = text.replace("{{PLAN_REVIEW}}", "rp")
text = text.replace("{{REQUIRE_PLAN_REVIEW}}", "1")
text = text.replace("{{REVIEW_RECEIPT_PATH}}", receipt)
out.write_text(text)
PY

cat <<EOF
Repo ready: $TEST_DIR/repo
Prompt file: $PROMPT_OUT
Receipt path: $RECEIPT_PATH

Open RepoPrompt window on:
  $TEST_DIR/repo

PLUGINS_DIR: $(dirname "$PLUGIN_ROOT")

Interactive run (ensure plugin available):
  cd "$TEST_DIR/repo"
  FLOW_RALPH=1 REVIEW_RECEIPT_PATH="$RECEIPT_PATH" $CLAUDE_BIN --plugin-dir "$(dirname "$PLUGIN_ROOT")"
  Then paste: \`cat $PROMPT_OUT\`

Auto (headless) run (ensure plugin available):
  cd "$TEST_DIR/repo"
  FLOW_RALPH=1 REVIEW_RECEIPT_PATH="$RECEIPT_PATH" $CLAUDE_BIN --plugin-dir "$(dirname "$PLUGIN_ROOT")" -p "\$(cat $PROMPT_OUT)"
EOF
