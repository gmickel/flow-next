#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Python interpreter resolution via the shared functionality probe (skips the
# Windows Store python3 alias stub; fills the FLOW_PY array). See lib/pick-python.sh.
# shellcheck source=lib/pick-python.sh
. "$SCRIPT_DIR/lib/pick-python.sh"
pick_python || { echo "ERROR: python not found (need python3 or python in PATH)" >&2; exit 1; }
REPO_ROOT="$(cd "$PLUGIN_ROOT/.." && pwd)"

# Safety: never run tests from the main plugin repo
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-/tmp/flow-next-ralph-e2e-$$}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

fail() { echo "ralph_e2e: $*" >&2; exit 1; }

cleanup() {
  if [[ "${KEEP_TEST_DIR:-0}" != "1" ]]; then
    rm -rf "$TEST_DIR"
  fi
}
trap cleanup EXIT

if [[ ! -x "$(command -v "$CLAUDE_BIN" || true)" ]]; then
  fail "claude not found (set CLAUDE_BIN if needed)"
fi

echo -e "${YELLOW}=== ralph e2e (real claude) ===${NC}"
echo "Test dir: $TEST_DIR"

mkdir -p "$TEST_DIR/repo"
cd "$TEST_DIR/repo"
git init -q
git config user.email "ralph-e2e@example.com"
git config user.name "Ralph E2E"
git checkout -b main >/dev/null 2>&1 || true

mkdir -p src
cat > src/index.ts <<'EOF'
export function add(a: number, b: number): number {
  return a + b;
}
EOF

cat > package.json <<'EOF'
{
  "name": "tmp-flow-next-ralph",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "test": "node -e \"console.log('ok')\""
  }
}
EOF

cat > README.md <<'EOF'
# tmp-flow-next-ralph

TBD
EOF

git add .
git commit -m "chore: init" >/dev/null

mkdir -p scripts/ralph
cp -R "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/." scripts/ralph/
cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl_bootstrap.py" scripts/ralph/flowctl_bootstrap.py
cp "$PLUGIN_ROOT/scripts/flowctl" scripts/ralph/flowctl
chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl

"${FLOW_PY[@]}" - <<'PY'
from pathlib import Path
import re
cfg = Path("scripts/ralph/config.env")
text = cfg.read_text()
text = text.replace("{{PLAN_REVIEW}}", "none").replace("{{WORK_REVIEW}}", "none")
text = re.sub(r"^REQUIRE_PLAN_REVIEW=.*$", "REQUIRE_PLAN_REVIEW=0", text, flags=re.M)
text = re.sub(r"^BRANCH_MODE=.*$", "BRANCH_MODE=new", text, flags=re.M)
text = re.sub(r"^MAX_ITERATIONS=.*$", "MAX_ITERATIONS=10", text, flags=re.M)
text = re.sub(r"^MAX_TURNS=.*$", "MAX_TURNS=60", text, flags=re.M)
text = re.sub(r"^MAX_ATTEMPTS_PER_TASK=.*$", "MAX_ATTEMPTS_PER_TASK=2", text, flags=re.M)
text = re.sub(r"^YOLO=.*$", "YOLO=1", text, flags=re.M)
text = re.sub(r"^EPICS=.*$", "EPICS=", text, flags=re.M)
cfg.write_text(text)
PY

scripts/ralph/flowctl init --json >/dev/null
scripts/ralph/flowctl spec create --title "Tiny lib" --json >/dev/null
scripts/ralph/flowctl spec create --title "Tiny follow-up" --json >/dev/null

cat > "$TEST_DIR/epic.md" <<'EOF'
# fn-1 Tiny lib

## Overview
Add a tiny add() helper and document it.

## Scope
- Small source change
- README update

## Approach
Edit src/index.ts and README.md only.

## Quick commands
- `npm test`

## Acceptance
- [ ] add() exported
- [ ] README updated with usage

## References
- None
EOF

scripts/ralph/flowctl spec set-plan fn-1 --file "$TEST_DIR/epic.md" --json >/dev/null
scripts/ralph/flowctl spec set-plan fn-2 --file "$TEST_DIR/epic.md" --json >/dev/null

cat > "$TEST_DIR/accept.md" <<'EOF'
- [ ] Export add(a,b) from src/index.ts
- [ ] Add README usage snippet
EOF

scripts/ralph/flowctl task create --spec fn-1 --title "Add add() helper" --acceptance-file "$TEST_DIR/accept.md" --json >/dev/null
scripts/ralph/flowctl task create --spec fn-2 --title "Add tiny note" --acceptance-file "$TEST_DIR/accept.md" --json >/dev/null

mkdir -p "$TEST_DIR/bin"
PLUGINS_DIR="$(dirname "$PLUGIN_ROOT")"
cat > "$TEST_DIR/bin/claude" <<EOF
#!/usr/bin/env bash
exec "$CLAUDE_BIN" --plugin-dir "$PLUGINS_DIR" "\$@"
EOF
chmod +x "$TEST_DIR/bin/claude"

echo -e "${YELLOW}--- running ralph ---${NC}"
CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh

"${FLOW_PY[@]}" - <<'PY'
import json
from pathlib import Path
for tid in ["fn-1.1", "fn-2.1"]:
    data = json.loads(Path(f".flow/tasks/{tid}.json").read_text())
    assert data["status"] == "done"
PY

run_dir="$(ls -1 scripts/ralph/runs | grep -v '^\\.gitkeep$' | head -n 1)"
"${FLOW_PY[@]}" - <<'PY' "$run_dir"
import json, sys
from pathlib import Path
run_dir = sys.argv[1]
assert Path(f"scripts/ralph/runs/{run_dir}/progress.txt").exists()
data = json.loads(Path(f"scripts/ralph/runs/{run_dir}/branches.json").read_text())
# Check run branch format (single branch for all epics)
assert "run_branch" in data, "branches.json should have run_branch"
assert data["run_branch"].startswith("ralph-"), f"run_branch should start with 'ralph-': {data['run_branch']}"
assert "base_branch" in data, "branches.json should have base_branch"
PY

echo -e "${GREEN}✓${NC} task done"
echo -e "${GREEN}✓${NC} ralph e2e complete"
echo "Run logs: $TEST_DIR/repo/scripts/ralph/runs"
echo "Claude logs: $HOME/.claude/projects"
