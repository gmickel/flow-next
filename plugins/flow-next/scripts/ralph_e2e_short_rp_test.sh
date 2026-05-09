#!/usr/bin/env bash
set -euo pipefail

# Short e2e test: fn-1 (1 task) → fn-2 (1 task)
# Minimal specs to avoid task expansion during planning

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-/tmp/flow-next-ralph-e2e-short-$$}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
FLOWCTL=""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() { echo "ralph_e2e_short: $*" >&2; exit 1; }

cleanup() {
  if [[ "${KEEP_TEST_DIR:-0}" != "1" && "${CREATE:-0}" != "1" ]]; then
    rm -rf "$TEST_DIR"
  fi
}
trap cleanup EXIT

command -v "$CLAUDE_BIN" >/dev/null 2>&1 || fail "claude not found"
command -v rp-cli >/dev/null 2>&1 || fail "rp-cli not found"

echo -e "${YELLOW}=== ralph e2e SHORT (rp) ===${NC}"
echo "Test dir: $TEST_DIR"

mkdir -p "$TEST_DIR/repo"
cd "$TEST_DIR/repo"
git init -q
git config user.email "ralph-e2e@example.com"
git config user.name "Ralph E2E"
git checkout -b main >/dev/null 2>&1 || true

mkdir -p src
cat > src/index.ts <<'EOF'
export const placeholder = 0;
EOF

cat > package.json <<'EOF'
{"name": "tmp-flow-next-ralph", "private": true, "version": "0.0.0"}
EOF

cat > README.md <<'EOF'
# tmp-flow-next-ralph
EOF

git add .
git commit -m "chore: init" >/dev/null

mkdir -p scripts/ralph
cp -R "$PLUGIN_ROOT/skills/flow-next-ralph-init/templates/." scripts/ralph/
cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/ralph/flowctl.py
cp "$PLUGIN_ROOT/scripts/flowctl" scripts/ralph/flowctl
chmod +x scripts/ralph/ralph.sh scripts/ralph/ralph_once.sh scripts/ralph/flowctl
FLOWCTL="scripts/ralph/flowctl"

python3 - <<'PY'
from pathlib import Path
import re
cfg = Path("scripts/ralph/config.env")
text = cfg.read_text()
text = text.replace("{{PLAN_REVIEW}}", "rp").replace("{{WORK_REVIEW}}", "rp")
text = re.sub(r"^REQUIRE_PLAN_REVIEW=.*$", "REQUIRE_PLAN_REVIEW=1", text, flags=re.M)
text = re.sub(r"^BRANCH_MODE=.*$", "BRANCH_MODE=new", text, flags=re.M)
text = re.sub(r"^MAX_ITERATIONS=.*$", "MAX_ITERATIONS=4", text, flags=re.M)
text = re.sub(r"^MAX_ATTEMPTS_PER_TASK=.*$", "MAX_ATTEMPTS_PER_TASK=2", text, flags=re.M)
text = re.sub(r"^YOLO=.*$", "YOLO=1", text, flags=re.M)
text = re.sub(r"^EPICS=.*$", "EPICS=fn-1,fn-2", text, flags=re.M)
cfg.write_text(text)
PY

scripts/ralph/flowctl init --json >/dev/null

# Setup .flow/bin + docs (mirror /flow-next:setup)
mkdir -p .flow/bin
cp "$PLUGIN_ROOT/scripts/flowctl" .flow/bin/flowctl
cp "$PLUGIN_ROOT/scripts/flowctl.py" .flow/bin/flowctl.py
chmod +x .flow/bin/flowctl
cp "$PLUGIN_ROOT/skills/flow-next-setup/templates/usage.md" .flow/usage.md
cat "$PLUGIN_ROOT/skills/flow-next-setup/templates/claude-md-snippet.md" > CLAUDE.md
echo -e "${GREEN}✓${NC} Setup mirrored"

scripts/ralph/flowctl spec create --title "Add function" --json >/dev/null
scripts/ralph/flowctl spec create --title "Add docs" --json >/dev/null

# MINIMAL epic spec - one clear deliverable, no room for task expansion
cat > "$TEST_DIR/epic1.md" <<'EOF'
# fn-1 Add function

Add `add(a, b)` to src/index.ts. Return a+b. Include JSDoc with @param and @returns.

## Acceptance
- [ ] `add(a: number, b: number): number` exported from src/index.ts
- [ ] JSDoc present

ONE task only. No README changes.
EOF

cat > "$TEST_DIR/epic2.md" <<'EOF'
# fn-2 Add docs

Add one-line note to README.md stating this is a tiny math library.

## Acceptance
- [ ] README has "tiny math library" note

ONE task only.
EOF

scripts/ralph/flowctl spec set-plan fn-1 --file "$TEST_DIR/epic1.md" --json >/dev/null
scripts/ralph/flowctl spec set-plan fn-2 --file "$TEST_DIR/epic2.md" --json >/dev/null
scripts/ralph/flowctl spec set-plan-review-status fn-2 --status ship --json >/dev/null

cat > "$TEST_DIR/accept1.md" <<'EOF'
- [ ] `add(a: number, b: number): number` exported
- [ ] JSDoc with @param and @returns
EOF

cat > "$TEST_DIR/accept2.md" <<'EOF'
- [ ] README mentions "tiny math library"
EOF

scripts/ralph/flowctl task create --spec fn-1 --title "Add add() function" --acceptance-file "$TEST_DIR/accept1.md" --json >/dev/null
scripts/ralph/flowctl task create --spec fn-2 --title "Add README note" --acceptance-file "$TEST_DIR/accept2.md" --json >/dev/null

mkdir -p "$TEST_DIR/bin"
PLUGINS_DIR="$(dirname "$PLUGIN_ROOT")"
cat > "$TEST_DIR/bin/claude" <<EOF
#!/usr/bin/env bash
exec "$CLAUDE_BIN" --plugin-dir "$PLUGINS_DIR" "\$@"
EOF
chmod +x "$TEST_DIR/bin/claude"

# Copy hooks (workaround #14410)
HOOKS_SRC="$PLUGIN_ROOT/scripts/hooks"
if [[ -d "$HOOKS_SRC" ]]; then
  mkdir -p ".claude/hooks"
  cp -r "$HOOKS_SRC"/* ".claude/hooks/"
  chmod +x ".claude/hooks/"*.py 2>/dev/null || true
  cat > ".claude/settings.local.json" <<'HOOKSJSON'
{
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]}],
    "PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ralph-guard.py", "timeout": 5}]}]
  }
}
HOOKSJSON
  echo -e "${GREEN}✓${NC} Hooks installed"
fi

git add .
git commit -m "chore: add flow setup" >/dev/null

if [[ "${CREATE:-0}" == "1" ]]; then
  echo -e "${GREEN}✓${NC} Test repo created: $TEST_DIR/repo"
  echo ""
  echo "Next steps:"
  echo "  1. Open RepoPrompt on: $TEST_DIR/repo"
  echo "  2. Re-run without CREATE:"
  echo "     TEST_DIR=$TEST_DIR KEEP_TEST_DIR=1 $0"
  exit 0
fi

echo -e "${YELLOW}--- running ralph (short) ---${NC}"
CLAUDE_BIN="$TEST_DIR/bin/claude" scripts/ralph/ralph.sh

# Assertions
python3 - <<'PY'
import json
from pathlib import Path
for tid in ["fn-1.1", "fn-2.1"]:
    data = json.loads(Path(f".flow/tasks/{tid}.json").read_text())
    assert data["status"] == "done", f"{tid} not done"
runs = [p for p in Path("scripts/ralph/runs").iterdir() if p.is_dir() and p.name != ".gitkeep"]
runs.sort()
run_dir = runs[0].name
assert Path(f"scripts/ralph/runs/{run_dir}/progress.txt").exists()
data = json.loads(Path(f"scripts/ralph/runs/{run_dir}/branches.json").read_text())
assert "run_branch" in data and data["run_branch"].startswith("ralph-")
assert "base_branch" in data
receipts = Path(f"scripts/ralph/runs/{run_dir}/receipts")
plan = json.loads(Path(receipts / "plan-fn-1.json").read_text())
assert plan["type"] == "plan_review"
impl1 = json.loads(Path(receipts / "impl-fn-1.1.json").read_text())
assert impl1["type"] == "impl_review"
impl2 = json.loads(Path(receipts / "impl-fn-2.1.json").read_text())
assert impl2["type"] == "impl_review"
PY

echo -e "${GREEN}✓${NC} ralph e2e short complete"
echo "Run logs: $TEST_DIR/repo/scripts/ralph/runs"
