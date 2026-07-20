#!/usr/bin/env bash
# Comprehensive CI tests for flowctl.py and ralph.sh helpers
# Runs on Linux, macOS, and Windows (Git Bash)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Python interpreter resolution via the shared functionality probe (skips the
# Windows Store python3 alias stub; fills the FLOW_PY array). See lib/pick-python.sh.
# shellcheck source=lib/pick-python.sh
. "$SCRIPT_DIR/lib/pick-python.sh"
pick_python || { echo "ERROR: python not found" >&2; exit 1; }

# Use provided TEST_DIR or create temp
if [[ -z "${TEST_DIR:-}" ]]; then
  TEST_DIR="$(mktemp -d)"
  CLEANUP_TEST_DIR=1
else
  CLEANUP_TEST_DIR=0
fi

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
  [[ "$CLEANUP_TEST_DIR" == "1" ]] && rm -rf "$TEST_DIR"
}
trap cleanup EXIT

pass() { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }

# Helper to run flowctl
flowctl() {
  "${FLOW_PY[@]}" "$TEST_DIR/scripts/flowctl.py" "$@"
}

echo -e "${YELLOW}=== flow-next CI tests ===${NC}"
echo "Python: ${FLOW_PY[*]}"
echo "Test dir: $TEST_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p "$TEST_DIR/scripts"
cd "$TEST_DIR"
git init -q
git config user.email "ci@test.local"
git config user.name "CI Test"

cp "$PLUGIN_ROOT/scripts/flowctl.py" scripts/

# ─────────────────────────────────────────────────────────────────────────────
# 1. Basic Commands
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Basic Commands ---${NC}"

flowctl init --json >/dev/null && pass "init" || fail "init"

EPIC_JSON="$(flowctl spec create --title "Test Epic" --json)"
EPIC_ID="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$EPIC_JSON")"
[[ -n "$EPIC_ID" ]] && pass "epic create ($EPIC_ID)" || fail "epic create"

TASK1_JSON="$(flowctl task create --spec "$EPIC_ID" --title "Task One" --priority 2 --json)"
TASK1_ID="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$TASK1_JSON")"
[[ -n "$TASK1_ID" ]] && pass "task create ($TASK1_ID)" || fail "task create"

TASK2_JSON="$(flowctl task create --spec "$EPIC_ID" --title "Task Two" --priority 1 --json)"
TASK2_ID="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['id'])" <<< "$TASK2_JSON")"

flowctl list --json >/dev/null && pass "list" || fail "list"
flowctl show "$EPIC_ID" --json >/dev/null && pass "show epic" || fail "show epic"
flowctl show "$TASK1_ID" --json >/dev/null && pass "show task" || fail "show task"

# ─────────────────────────────────────────────────────────────────────────────
# 2. State Machine Transitions
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- State Machine ---${NC}"

# next should return plan (no plan review yet)
NEXT_JSON="$(flowctl next --require-plan-review --json)"
STATUS="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['status'])" <<< "$NEXT_JSON")"
[[ "$STATUS" == "plan" ]] && pass "next returns plan" || fail "next returns plan (got $STATUS)"

# set plan review status
flowctl spec set-plan-review-status "$EPIC_ID" --status ship --json >/dev/null && pass "set-plan-review-status" || fail "set-plan-review-status"

# next should now return work with higher priority task (Task Two, priority 1)
NEXT_JSON="$(flowctl next --json)"
NEXT_TASK="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin).get('task',''))" <<< "$NEXT_JSON")"
[[ "$NEXT_TASK" == "$TASK2_ID" ]] && pass "next picks high priority task" || fail "next picks high priority (expected $TASK2_ID, got $NEXT_TASK)"

# start task
flowctl start "$TASK2_ID" --json >/dev/null && pass "start task" || fail "start task"

# verify task is in_progress
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "in_progress" ]] && pass "task status is in_progress" || fail "task status (got $TASK_STATUS)"

# block task (requires --reason-file)
echo "Waiting for external API" > "$TEST_DIR/block_reason.md"
flowctl block "$TASK2_ID" --reason-file "$TEST_DIR/block_reason.md" --json >/dev/null && pass "block task" || fail "block task"
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "blocked" ]] && pass "task status is blocked" || fail "task blocked status (got $TASK_STATUS)"

# Note: there's no unblock command - use --force to restart blocked tasks
flowctl start "$TASK2_ID" --force --json >/dev/null && pass "restart blocked task (--force)" || fail "restart blocked task"
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "in_progress" ]] && pass "task status restored to in_progress" || fail "task unblocked status (got $TASK_STATUS)"

# done task (create temp files for evidence)
echo "Task completed" > "$TEST_DIR/summary.md"
echo '{"commits":["abc123"],"tests":["npm test"],"prs":[]}' > "$TEST_DIR/evidence.json"
flowctl done "$TASK2_ID" --summary-file "$TEST_DIR/summary.md" --evidence-json "$TEST_DIR/evidence.json" --json >/dev/null && pass "done task" || fail "done task"
TASK_STATUS="$(flowctl show "$TASK2_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['status'])")"
[[ "$TASK_STATUS" == "done" ]] && pass "task status is done" || fail "task done status (got $TASK_STATUS)"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Error Handling
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Error Handling ---${NC}"

# Invalid epic ID
set +e
ERR_OUT="$(flowctl show "fn-9999-xxx" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "invalid epic ID returns error" || fail "invalid epic ID should fail"

# Invalid task ID
set +e
ERR_OUT="$(flowctl start "fn-9999-xxx.99" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "invalid task ID returns error" || fail "invalid task ID should fail"

# Double start (task already done)
set +e
ERR_OUT="$(flowctl start "$TASK2_ID" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "start done task returns error" || fail "start done task should fail"

# ─────────────────────────────────────────────────────────────────────────────
# 3.5 Spec readiness flag (fn-58.1)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Spec Readiness (fn-58.1) ---${NC}"

# Lazy purity: never-toggled spec carries no `ready` key but JSON reads false.
READY_VAL="$(flowctl show "$EPIC_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['ready'])")"
[[ "$READY_VAL" == "False" ]] && pass "show emits explicit ready false" || fail "show ready default (got $READY_VAL)"

flowctl spec ready "$EPIC_ID" --json >/dev/null && pass "spec ready" || fail "spec ready"
READY_VAL="$(flowctl show "$EPIC_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['ready'])")"
[[ "$READY_VAL" == "True" ]] && pass "show reports ready true" || fail "show ready true (got $READY_VAL)"

# Badge shown ONLY while ready (human output).
if flowctl specs | grep -q "\[ready\] $EPIC_ID"; then
  pass "specs badge shown on ready spec"
else
  fail "specs badge missing on ready spec"
fi

flowctl spec unready "$EPIC_ID" --json >/dev/null && pass "spec unready" || fail "spec unready"
READY_VAL="$(flowctl specs --json | "${FLOW_PY[@]}" -c "import json,sys; print([e['ready'] for e in json.load(sys.stdin)['specs']][0])")"
[[ "$READY_VAL" == "False" ]] && pass "specs reports ready false after unready" || fail "specs ready false (got $READY_VAL)"

if flowctl specs | grep -q "\[ready\]"; then
  fail "badge still shown after unready"
else
  pass "badge gone after unready"
fi

# Idempotent no-op: second unready reports changed=false.
CHANGED="$(flowctl spec unready "$EPIC_ID" --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['changed'])")"
[[ "$CHANGED" == "False" ]] && pass "unready idempotent no-op" || fail "unready no-op (changed=$CHANGED)"

# `.M` task ids rejected.
set +e
ERR_OUT="$(flowctl spec ready "$TASK1_ID" --json 2>&1)"
ERR_RC=$?
set -e
[[ $ERR_RC -ne 0 ]] && pass "spec ready rejects task id" || fail "spec ready should reject task id"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Config System
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Config System ---${NC}"

flowctl config set memory.enabled true --json >/dev/null && pass "config set" || fail "config set"

CONFIG_VAL="$(flowctl config get memory.enabled --json | "${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['value'])")"
[[ "$CONFIG_VAL" == "True" ]] && pass "config get" || fail "config get (got $CONFIG_VAL)"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Memory System
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Memory System ---${NC}"

flowctl memory init --json >/dev/null && pass "memory init" || fail "memory init"

# fn-38 T1: lazy-dir-create — `flowctl memory init` must materialize
# `.flow/memory/knowledge/decisions/.gitkeep` (the directory loop walks
# MEMORY_CATEGORIES, so the new `decisions` slot is auto-created).
[[ -f "$TEST_DIR/.flow/memory/knowledge/decisions/.gitkeep" ]] && \
  pass "memory init lazy-creates decisions/.gitkeep" || \
  fail "memory init missing decisions/.gitkeep"

flowctl memory add --type pitfall "Never use sync IO in async handlers" --json >/dev/null && pass "memory add pitfall" || fail "memory add pitfall"
flowctl memory add --type convention "Use snake_case for functions" --json >/dev/null && pass "memory add convention" || fail "memory add convention"

MEM_LIST="$(flowctl memory list --json)"
# memory list returns {success: true, entries: [...], legacy: [...], count: N, status: "active"}
MEM_TOTAL="$("${FLOW_PY[@]}" -c "import json,sys; d=json.load(sys.stdin); print(d.get('count', 0))" <<< "$MEM_LIST")"
[[ "$MEM_TOTAL" -ge 2 ]] && pass "memory list ($MEM_TOTAL total)" || fail "memory list (got $MEM_TOTAL)"

# ─────────────────────────────────────────────────────────────────────────────
# 5b. Memory: decisions track (fn-38 task 1)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Memory: decisions track ---${NC}"

# (1) round-trip write→read of all three optional fields
DEC_JSON="$(flowctl memory add \
  --track knowledge --category decisions \
  --title "Use nearest-ancestor for glossary lookup" \
  --module flowctl \
  --tags "glossary,resolution" \
  --decision-status accepted \
  --superseded-by "knowledge/decisions/foo-2026-04-30" \
  --alternatives-considered "always-root,explicit-config,meta-file" \
  --json)"
DEC_ID="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['entry_id'])" <<< "$DEC_JSON")"
[[ -n "$DEC_ID" ]] && pass "memory add decisions ($DEC_ID)" || fail "memory add decisions"

DEC_PATH="$("${FLOW_PY[@]}" -c "import json,sys; print(json.load(sys.stdin)['path'])" <<< "$DEC_JSON")"
[[ -f "$DEC_PATH" ]] && pass "decisions entry written to disk" || fail "decisions entry missing on disk"

# Round-trip: parse the file we wrote, verify all three optional fields survived.
"${FLOW_PY[@]}" - "$DEC_PATH" << 'PYTEST'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
# Crude frontmatter splitter — the schema writes flat `key: value` so a
# line-by-line scan is enough for the round-trip assertion.
fm: dict[str, str] = {}
in_fm = False
for line in text.splitlines():
    if line.strip() == "---":
        if in_fm:
            break
        in_fm = True
        continue
    if not in_fm or ":" not in line:
        continue
    k, _, v = line.partition(":")
    fm[k.strip()] = v.strip()

errors = []
if fm.get("decision_status") != "accepted":
    errors.append(f"decision_status round-trip: got {fm.get('decision_status')!r}")
if fm.get("superseded_by") != "knowledge/decisions/foo-2026-04-30":
    errors.append(f"superseded_by round-trip: got {fm.get('superseded_by')!r}")
alts = fm.get("alternatives_considered") or ""
if not (alts.startswith("[") and alts.endswith("]")):
    errors.append(f"alternatives_considered should be inline-list flow style, got {alts!r}")
elif "always-root" not in alts or "explicit-config" not in alts or "meta-file" not in alts:
    errors.append(f"alternatives_considered missing items: {alts!r}")

if errors:
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("decisions round-trip OK")
PYTEST
[[ $? -eq 0 ]] && pass "decisions optional fields round-trip" || fail "decisions optional fields round-trip"

# (3) deterministic write order across repeated read+write cycles. Capture the
# first frontmatter block, parse + write_memory_entry the same dict, compare
# byte-for-byte. Field order is anchored by MEMORY_FIELD_ORDER; rerunning
# write_memory_entry on the same dict must produce the same bytes.
"${FLOW_PY[@]}" - "$TEST_DIR" "$DEC_PATH" << 'PYTEST'
import importlib.util
import sys
from pathlib import Path

test_dir = Path(sys.argv[1])
dec_path = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("flowctl", test_dir / "scripts/flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flowctl)

parsed = flowctl.parse_memory_frontmatter(dec_path)
# parse → re-write → compare. write_memory_entry must produce identical
# bytes across repeated cycles (deterministic field order anchored by
# MEMORY_FIELD_ORDER). Body is empty for this fixture.
body = ""

# Round-trip 1
flowctl.write_memory_entry(dec_path, parsed, body)
pass1 = dec_path.read_text(encoding="utf-8")

# Round-trip 2 — re-parse what we just wrote, write again. Idempotency check.
parsed2 = flowctl.parse_memory_frontmatter(dec_path)
flowctl.write_memory_entry(dec_path, parsed2, body)
pass2 = dec_path.read_text(encoding="utf-8")

errors = []
if pass1 != pass2:
    errors.append("write_memory_entry produced different bytes across repeated cycles")
# Sanity: the optional-field block must appear in MEMORY_FIELD_ORDER order
# (decision_status before superseded_by before alternatives_considered).
ds = pass2.find("decision_status:")
sb = pass2.find("superseded_by:")
ac = pass2.find("alternatives_considered:")
if not (0 <= ds < sb < ac):
    errors.append(
        f"decision-fields out of order: ds={ds} sb={sb} ac={ac}"
    )

if errors:
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("decisions deterministic write order OK")
PYTEST
[[ $? -eq 0 ]] && pass "decisions deterministic write order" || fail "decisions deterministic write order"

# (2) negative case — `decision_status` outside the enum must be rejected.
# argparse enforces `choices`, so this is a usage-error (rc=2) caught before
# cmd_memory_add runs. Belt + braces: the validator also enum-checks, so we
# verify a hand-crafted dict is rejected by validate_memory_frontmatter.
set +e
flowctl memory add --track knowledge --category decisions \
  --title "Bad status" --decision-status pending --json >/dev/null 2>&1
BAD_RC=$?
set -e
[[ $BAD_RC -ne 0 ]] && pass "decision_status rejects out-of-enum (cli)" || fail "decision_status should reject 'pending'"

"${FLOW_PY[@]}" - "$TEST_DIR" << 'PYTEST'
import importlib.util
import sys
from pathlib import Path

test_dir = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("flowctl", test_dir / "scripts/flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flowctl)

errors = flowctl.validate_memory_frontmatter({
    "title": "Bad",
    "date": "2026-04-30",
    "track": "knowledge",
    "category": "decisions",
    "applies_when": "Bad",
    "decision_status": "pending",
})
if not any("decision_status" in e for e in errors):
    print(f"validator should reject decision_status='pending', got {errors!r}")
    sys.exit(1)

# Sanity: valid status passes.
errors = flowctl.validate_memory_frontmatter({
    "title": "Good",
    "date": "2026-04-30",
    "track": "knowledge",
    "category": "decisions",
    "applies_when": "Good",
    "decision_status": "proposed",
})
if errors:
    print(f"validator should accept decision_status='proposed', got {errors!r}")
    sys.exit(1)

print("decision_status enum validation OK")
PYTEST
[[ $? -eq 0 ]] && pass "decision_status enum validator" || fail "decision_status enum validator"

# ─────────────────────────────────────────────────────────────────────────────
# 5c. Plugin-source hygiene — R17 forbidden vocabulary + R4 meta-file leaks
#     (fn-38 task 7). Two-tier guard mirrors the existing
#     AskUserQuestion / ToolSearch split: this canonical scan covers
#     skills/, agents/, commands/, and flowctl.py; the codex mirror scan
#     lives in scripts/sync-codex.sh validation block.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Plugin-source hygiene (R17 + R4) ---${NC}"

# R17: DDD vocabulary guard. Listed inline only inside the grep pattern;
# documentation refers to "the R17 forbidden list" without enumeration.
set +e
DDD_HITS="$(grep -RnE 'ubiquitous language|bounded context|domain expert|aggregate root' \
  "$PLUGIN_ROOT/skills" \
  "$PLUGIN_ROOT/scripts/flowctl.py" \
  "$PLUGIN_ROOT/agents" \
  "$PLUGIN_ROOT/commands" 2>/dev/null)"
set -e
if [[ -n "$DDD_HITS" ]]; then
  fail "R17 DDD vocabulary in canonical:"
  echo "$DDD_HITS" | sed 's/^/    /'
else
  pass "R17: no DDD vocabulary in canonical"
fi

# R4: no meta-file precedent leaks (early-design naming) into canonical prose.
set +e
META_HITS="$(grep -RnE 'GLOSSARY-MAP\.md|CONTEXT-MAP\.md' \
  "$PLUGIN_ROOT/skills" \
  "$PLUGIN_ROOT/scripts/flowctl.py" \
  "$PLUGIN_ROOT/agents" \
  "$PLUGIN_ROOT/commands" 2>/dev/null)"
set -e
if [[ -n "$META_HITS" ]]; then
  fail "R4 meta-file refs in canonical:"
  echo "$META_HITS" | sed 's/^/    /'
else
  pass "R4: no meta-file refs in canonical"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 5d. Strategy-doc fluff guard — R19 (fn-39 task 5).
#     This is the strategy-doc fluff guard, NOT R17 (DDD vocabulary).
#     Each grep block has one purpose; do not merge with section 5c.
#     Tier 1 jargon only (Rumelt's "fluff" hallmarks): synergy / pivot /
#     disrupt / thought-leadership / best-in-class / world-class / 10x.
#     Scope: flow-next-strategy skill + cmd_strategy_* in flowctl.py +
#     strategy.md command file. The references/interview.md file is
#     EXCLUDED from this guard — it must describe these anti-patterns
#     to push back on them (same exemption pattern as glossary references).
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Strategy-doc fluff guard (R19) ---${NC}"

set +e
FLUFF_HITS="$(grep -RnEi '\bsynergy\b|\bpivot\b|\bdisrupt\b|thought[ -]leadership|best-in-class|world-class|\b10x\b' \
  "$PLUGIN_ROOT/skills/flow-next-strategy/SKILL.md" \
  "$PLUGIN_ROOT/commands/flow-next/strategy.md" 2>/dev/null \
  ; awk '/^def cmd_strategy_/,/^def [^_]/' "$PLUGIN_ROOT/scripts/flowctl.py" 2>/dev/null \
    | grep -nEi '\bsynergy\b|\bpivot\b|\bdisrupt\b|thought[ -]leadership|best-in-class|world-class|\b10x\b' \
    | sed 's|^|flowctl.py(cmd_strategy_*):|')"
set -e
if [[ -n "$FLUFF_HITS" ]]; then
  fail "R19 strategy-doc fluff vocabulary in canonical:"
  echo "$FLUFF_HITS" | sed 's/^/    /'
else
  pass "R19: no strategy-doc fluff vocabulary in canonical"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 5e. Alias-vocabulary guard — R30 (fn-43 task 14).
#     Catch fresh prose that uses the legacy `flowctl epic` CLI surface
#     instead of the canonical 1.0 `flowctl spec`. Mirrors the R17 / R19
#     two-tier guard pattern (canonical scan here + Codex-mirror scan in
#     scripts/sync-codex.sh validation block).
#
#     Lines that legitimately reference the legacy form survive when they
#     describe deprecation / alias / legacy semantics — e.g. the migration
#     banner string, dispatcher comments, the `_emit_rename_deprecation`
#     helper itself. Excluded markers: `deprecat`, `legacy`, `alias`,
#     `_emit_rename_`, `removed in 2.0`. references/ files are excluded
#     so anti-pattern documentation can describe the legacy form.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Alias-vocabulary guard (R30) ---${NC}"

# Patterns: legacy verb (`flowctl epic*` / `flowctl epics`), legacy CLI flag
# (`--epic`), legacy section filter (`--section epic`), legacy env var
# (`EPICS_FILE`). Each must be absent from canonical prose unless the line
# describes deprecation / alias / legacy semantics. Argparse declarations
# of the legacy alias flags themselves (`"--epic-title",` / `"--epics-file",`
# as the first arg of an `add_argument(...)` call) are excluded — those are
# the alias entry points, not fresh prose using them.
set +e
ALIAS_HITS="$(grep -RnE 'flowctl epic\b|flowctl epics\b|--epic\b|--epics-file\b|--section epic\b|\bEPICS_FILE\b' \
  "$PLUGIN_ROOT/skills" \
  "$PLUGIN_ROOT/scripts/flowctl.py" \
  "$PLUGIN_ROOT/agents" \
  "$PLUGIN_ROOT/commands" 2>/dev/null \
  | grep -vE '/references/' \
  | grep -vE 'deprecat|legacy|alias|_emit_rename_|removed in 2\.0|flow-next 1\.0 renamed|R31|R30|fn-43|\bT[0-9]+\b' \
  | grep -vE '^[^:]+:[0-9]+:[[:space:]]+"--(epic|epics-file|epic-title)",?[[:space:]]*$')"
set -e
if [[ -n "$ALIAS_HITS" ]]; then
  fail "R30 legacy CLI vocabulary in canonical (use 'flowctl spec' / '--spec' / 'SPECS_FILE'):"
  echo "$ALIAS_HITS" | sed 's/^/    /'
else
  pass "R30: no legacy CLI vocabulary in canonical (alias context excluded)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 6. Symbol Extraction
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Symbol Extraction ---${NC}"

# Create sample files
mkdir -p "$TEST_DIR/src"

cat > "$TEST_DIR/src/sample.py" << 'EOF'
def calculate_total(items):
    return sum(items)

class OrderProcessor:
    def process(self):
        pass

__all__ = ["calculate_total", "OrderProcessor"]
EOF

cat > "$TEST_DIR/src/sample.ts" << 'EOF'
export function fetchData(url: string): Promise<any> {
    return fetch(url);
}

export class ApiClient {
    constructor() {}
}

export const API_VERSION = "1.0";
EOF

cat > "$TEST_DIR/src/sample.go" << 'EOF'
package main

func ProcessRequest(r *Request) error {
    return nil
}

type Handler struct {
    Name string
}
EOF

cat > "$TEST_DIR/src/sample.rs" << 'EOF'
pub fn handle_event(event: Event) -> Result<(), Error> {
    Ok(())
}

pub struct EventProcessor {
    id: u64,
}

impl EventProcessor {
    pub fn new() -> Self {
        Self { id: 0 }
    }
}
EOF

cat > "$TEST_DIR/src/sample.cs" << 'EOF'
public class UserService {
    public async Task<User> GetUserAsync(int id) {
        return await _repository.FindAsync(id);
    }
}

public interface IRepository<T> {
    Task<T> FindAsync(int id);
}

public record UserDto(string Name, string Email);
EOF

cat > "$TEST_DIR/src/sample.java" << 'EOF'
public class PaymentProcessor {
    public void processPayment(Payment payment) {
        // process
    }
}

public interface PaymentGateway {
    boolean authorize(String token);
}
EOF

# Test symbol extraction via Python directly
"${FLOW_PY[@]}" - "$TEST_DIR" << 'PYTEST'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
from flowctl import extract_symbols_from_file
from pathlib import Path

test_dir = Path(sys.argv[1])
errors = []

# Python
py_symbols = extract_symbols_from_file(test_dir / "src/sample.py")
if "calculate_total" not in py_symbols:
    errors.append(f"Python: missing calculate_total, got {py_symbols}")
if "OrderProcessor" not in py_symbols:
    errors.append(f"Python: missing OrderProcessor, got {py_symbols}")

# TypeScript
ts_symbols = extract_symbols_from_file(test_dir / "src/sample.ts")
if "fetchData" not in ts_symbols:
    errors.append(f"TS: missing fetchData, got {ts_symbols}")
if "ApiClient" not in ts_symbols:
    errors.append(f"TS: missing ApiClient, got {ts_symbols}")

# Go
go_symbols = extract_symbols_from_file(test_dir / "src/sample.go")
if "ProcessRequest" not in go_symbols:
    errors.append(f"Go: missing ProcessRequest, got {go_symbols}")
if "Handler" not in go_symbols:
    errors.append(f"Go: missing Handler, got {go_symbols}")

# Rust
rs_symbols = extract_symbols_from_file(test_dir / "src/sample.rs")
if "handle_event" not in rs_symbols:
    errors.append(f"Rust: missing handle_event, got {rs_symbols}")
if "EventProcessor" not in rs_symbols:
    errors.append(f"Rust: missing EventProcessor, got {rs_symbols}")

# C#
cs_symbols = extract_symbols_from_file(test_dir / "src/sample.cs")
if "UserService" not in cs_symbols:
    errors.append(f"C#: missing UserService, got {cs_symbols}")
if "IRepository" not in cs_symbols:
    errors.append(f"C#: missing IRepository, got {cs_symbols}")
if "UserDto" not in cs_symbols:
    errors.append(f"C#: missing UserDto (record), got {cs_symbols}")

# Java
java_symbols = extract_symbols_from_file(test_dir / "src/sample.java")
if "PaymentProcessor" not in java_symbols:
    errors.append(f"Java: missing PaymentProcessor, got {java_symbols}")
if "PaymentGateway" not in java_symbols:
    errors.append(f"Java: missing PaymentGateway, got {java_symbols}")

if errors:
    print("Symbol extraction errors:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("All symbol extractions passed")
PYTEST
[[ $? -eq 0 ]] && pass "symbol extraction (6 languages)" || fail "symbol extraction"

# RepoPrompt builder parsing regressions
"${FLOW_PY[@]}" - "$TEST_DIR" << 'PYTEST'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
from flowctl import extract_builder_tab_from_payload, parse_builder_tab

errors = []

tab = parse_builder_tab('Tab: tab-123 • Builder Session')
if tab != "tab-123":
    errors.append(f"Expected Tab output to parse as tab-123, got {tab!r}")

context = parse_builder_tab('Context: 123e4567-e89b-12d3-a456-426614174000 • Builder Session')
if context != "123e4567-e89b-12d3-a456-426614174000":
    errors.append(f"Expected Context output to parse UUID, got {context!r}")

context_json = parse_builder_tab('{"result":{"context_id":"ctx-1"}}')
if context_json != "ctx-1":
    errors.append(f"Expected nested context_id JSON to parse as ctx-1, got {context_json!r}")

payload_tab = extract_builder_tab_from_payload({"result": {"context_id": "ctx-2"}})
if payload_tab != "ctx-2":
    errors.append(f"Expected extractor to unwrap nested context_id, got {payload_tab!r}")

if errors:
    print("Builder parsing errors:")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)

print("Builder parsing tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "RepoPrompt builder parsing" || fail "RepoPrompt builder parsing"

# ─────────────────────────────────────────────────────────────────────────────
# 6b. RepoPrompt Setup Review Regression Coverage
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- RepoPrompt Setup Review ---${NC}"

"${FLOW_PY[@]}" - "$TEST_DIR" << 'PYTEST'
import importlib.util
import io
import json
import sys
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

test_dir = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("flowctl", test_dir / "scripts/flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flowctl)

errors = []

tab = flowctl.parse_builder_tab('{"result":{"tab_id":"json-tab-1"}}')
if tab != "json-tab-1":
    errors.append(f"parse_builder_tab should parse nested JSON tab ids, got {tab!r}")

nested = flowctl.parse_manage_workspaces('{"result":{"workspaces":[{"id":"ws-1","repoPaths":["/x"]}]}}')
if not nested or nested[0].get("id") != "ws-1":
    errors.append(f"parse_manage_workspaces should unwrap nested result objects, got {nested!r}")

string_items = flowctl.parse_manage_workspaces('["project-a", {"id":"ws-2","repoPaths":["/y"]}]')
if not string_items or string_items[0].get("name") != "project-a":
    errors.append(f"parse_manage_workspaces should preserve string workspace names, got {string_items!r}")


def make_result(stdout="", stderr=""):
    return SimpleNamespace(stdout=stdout, stderr=stderr)


def run_setup(fake_run, repo_root: str, summary: str, fake_try_run=None):
    flowctl.run_rp_cli = fake_run
    flowctl.try_run_rp_cli = fake_try_run or (lambda args, timeout=None: None)
    output = io.StringIO()
    with redirect_stdout(output):
        flowctl.cmd_rp_setup_review(
            Namespace(
                repo_root=repo_root,
                summary=summary,
                response_type=None,
                create=True,
                json=False,
            )
        )
    return output.getvalue().strip()


repo_root = "/workspace/test-project"
other_repo_root = "/workspace/other-project"
commands = []


def fake_bind_context(args, timeout=None):
    if args[:2] == ["--raw-json", "-e"] and args[2].startswith("call bind_context "):
        payload = json.loads(args[2][len("call bind_context "):])
        if payload.get("op") == "bind" and payload.get("working_dirs") == flowctl.normalize_repo_root(repo_root):
            return make_result(json.dumps({"window_id": 55, "match_method": "working_dirs"}))
    return None


def fake_bind_context_builder(args, timeout=None):
    commands.append(args)
    if args == ["-w", "55", "--raw-json", "-e", 'builder "Bind me"']:
        return make_result(json.dumps({"context_id": "tab-55"}))
    raise AssertionError(f"Unexpected rp-cli args: {args}")


result = run_setup(fake_bind_context_builder, repo_root, "Bind me", fake_try_run=fake_bind_context)
if result != "W=55 T=tab-55":
    errors.append(f"setup-review should prefer bind_context when available, got {result!r}")
if any("manage_workspaces" in arg or arg == "windows" for cmd in commands for arg in cmd):
    errors.append("setup-review should not fall back to manual workspace/window discovery when bind_context succeeds")

commands = []


def fake_reuse_existing(args, timeout=None):
    commands.append(args)
    if args == ["--raw-json", "-e", "windows"]:
        return make_result(json.dumps([
            {"windowID": 7, "rootFolderPaths": [other_repo_root]}
        ]))
    if args == [
        "--raw-json",
        "-e",
        'call manage_workspaces {"action": "list"}',
    ]:
        return make_result(json.dumps([
            {
                "id": "ws-1",
                "name": "test-project",
                "repoPaths": [repo_root],
                "showingWindows": [42],
            }
        ]))
    if args == ["-w", "42", "--raw-json", "-e", 'builder "Review me"']:
        return make_result(json.dumps({"context_id": "tab-123"}))
    raise AssertionError(f"Unexpected rp-cli args: {args}")


result = run_setup(fake_reuse_existing, repo_root, "Review me")
if result != "W=42 T=tab-123":
    errors.append(f"setup-review should reuse visible workspace window, got {result!r}")
if any(arg.startswith("workspace create ") for cmd in commands for arg in cmd):
    errors.append("setup-review should not create a new workspace when one with the same repo path is already visible")

commands = []


def fake_reopen_hidden_workspace(args, timeout=None):
    commands.append(args)
    if args == ["--raw-json", "-e", "windows"]:
        return make_result(json.dumps([
            {"windowID": 7, "rootFolderPaths": [other_repo_root]}
        ]))
    if args == [
        "--raw-json",
        "-e",
        'call manage_workspaces {"action": "list"}',
    ]:
        return make_result(json.dumps([
            {
                "id": "ws-hidden",
                "name": "test-project",
                "repoPaths": [repo_root],
                "showingWindows": [],
            }
        ]))
    if args == [
        "--raw-json",
        "-e",
        'call manage_workspaces {"action": "switch", "workspace": "ws-hidden", "open_in_new_window": true}',
    ]:
        return make_result(json.dumps({"window_id": 84}))
    if args == ["-w", "84", "--raw-json", "-e", 'builder "Reopen me"']:
        return make_result(json.dumps({"context_id": "tab-84"}))
    raise AssertionError(f"Unexpected rp-cli args: {args}")


result = run_setup(fake_reopen_hidden_workspace, repo_root, "Reopen me")
if result != "W=84 T=tab-84":
    errors.append(f"setup-review should reopen an existing hidden workspace before creating a duplicate, got {result!r}")
if any(arg.startswith("workspace create ") for cmd in commands for arg in cmd):
    errors.append("setup-review should switch an existing hidden workspace into a new window instead of creating a duplicate workspace")

if errors:
    print("RepoPrompt regression test errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)

print("RepoPrompt setup-review regressions passed")
PYTEST
[[ $? -eq 0 ]] && pass "RepoPrompt setup-review regression" || fail "RepoPrompt setup-review regression"

# ─────────────────────────────────────────────────────────────────────────────
# 6c. RepoPrompt Chat Send Compatibility
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- RepoPrompt Chat Send Compatibility ---${NC}"

"${FLOW_PY[@]}" - "$TEST_DIR" << 'PYTEST'
import importlib.util
import io
import json
import sys
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

test_dir = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("flowctl", test_dir / "scripts/flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flowctl)

errors = []


def make_result(stdout="", stderr=""):
    return SimpleNamespace(stdout=stdout, stderr=stderr)


def make_completed(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


msg_file = test_dir / "chat-send.md"
msg_file.write_text("Review this change.\n", encoding="utf-8")

# Modern RepoPrompt: prefer oracle_send and strip legacy-only fields.
oracle_calls = []
legacy_calls = []


def modern_unchecked(args, timeout=None):
    oracle_calls.append(args)
    return make_completed("## Chat Send ✅\n- **Chat**: `modern-chat`\n")


def modern_run(args, timeout=None):
    legacy_calls.append(args)
    raise AssertionError(f"Legacy fallback should not run: {args}")


flowctl.run_rp_cli_unchecked = modern_unchecked
flowctl.run_rp_cli = modern_run
modern_output = io.StringIO()
with redirect_stdout(modern_output):
    flowctl.cmd_rp_chat_send(
        Namespace(
            window=7,
            tab="tab-modern",
            message_file=str(msg_file),
            new_chat=True,
            chat_name="Smoke Preflight",
            chat_id=None,
            mode="review",
            selected_paths=["src/a.cs", "src/b.cs"],
            json=False,
        )
    )

expected_modern = [
    "-w",
    "7",
    "-t",
    "tab-modern",
    "-e",
    'call oracle_send {"message":"Review this change.\\n","mode":"review","new_chat":true}',
]
if oracle_calls != [expected_modern]:
    errors.append(f"modern chat-send should call oracle_send without legacy fields, got {oracle_calls!r}")
if legacy_calls:
    errors.append(f"modern chat-send unexpectedly used legacy fallback: {legacy_calls!r}")
if "modern-chat" not in modern_output.getvalue():
    errors.append(f"modern chat-send should print RepoPrompt response, got {modern_output.getvalue()!r}")

# Legacy RepoPrompt: fall back to chat_send and preserve old payload fields.
oracle_calls = []
legacy_calls = []


def legacy_unchecked(args, timeout=None):
    oracle_calls.append(args)
    return make_completed(stderr="Error:\nTool not found: oracle_send", returncode=2)


def legacy_run(args, timeout=None):
    legacy_calls.append(args)
    return make_result('{"chat_id":"legacy-chat"}')


flowctl.run_rp_cli_unchecked = legacy_unchecked
flowctl.run_rp_cli = legacy_run
legacy_output = io.StringIO()
with redirect_stdout(legacy_output):
    flowctl.cmd_rp_chat_send(
        Namespace(
            window=9,
            tab="tab-legacy",
            message_file=str(msg_file),
            new_chat=True,
            chat_name="Legacy Chat",
            chat_id="chat-123",
            mode="chat",
            selected_paths=["spec.md"],
            json=True,
        )
    )

expected_legacy = [
    "-w",
    "9",
    "-t",
    "tab-legacy",
    "-e",
    'call chat_send {"message":"Review this change.\\n","mode":"chat","new_chat":true,"chat_id":"chat-123","chat_name":"Legacy Chat","selected_paths":["spec.md"]}',
]
if oracle_calls != [[
    "-w",
    "9",
    "-t",
    "tab-legacy",
    "-e",
    'call oracle_send {"message":"Review this change.\\n","mode":"chat","new_chat":true,"chat_id":"chat-123"}',
]]:
    errors.append(f"legacy fallback should probe oracle_send first, got {oracle_calls!r}")
if legacy_calls != [expected_legacy]:
    errors.append(f"legacy fallback should preserve chat_send payload, got {legacy_calls!r}")
try:
    parsed = json.loads(legacy_output.getvalue())
except json.JSONDecodeError as exc:
    errors.append(f"legacy chat-send should emit JSON output: {exc}")
else:
    if parsed.get("chat") != "legacy-chat":
        errors.append(f"legacy chat-send should parse chat id from fallback output, got {parsed!r}")

# Real oracle_send failures should surface directly instead of falling back.
oracle_calls = []
legacy_calls = []


def broken_unchecked(args, timeout=None):
    oracle_calls.append(args)
    return make_completed(stderr="Error:\n[-32602] Invalid params: bad tab", returncode=1)


def broken_run(args, timeout=None):
    legacy_calls.append(args)
    raise AssertionError(f"Legacy fallback should not run for real oracle failures: {args}")


flowctl.run_rp_cli_unchecked = broken_unchecked
flowctl.run_rp_cli = broken_run
broken_stderr = io.StringIO()
try:
    with redirect_stderr(broken_stderr):
        flowctl.cmd_rp_chat_send(
            Namespace(
                window=3,
                tab="bad-tab",
                message_file=str(msg_file),
                new_chat=False,
                chat_name=None,
                chat_id=None,
                mode="chat",
                selected_paths=None,
                json=False,
            )
        )
except SystemExit as exc:
    if exc.code != 2:
        errors.append(f"real oracle failures should exit 2, got {exc.code!r}")
else:
    errors.append("real oracle failures should exit instead of falling back")
if "Invalid params: bad tab" not in broken_stderr.getvalue():
    errors.append(f"real oracle failure should preserve original error, got {broken_stderr.getvalue()!r}")
if legacy_calls:
    errors.append(f"real oracle failures should not call legacy chat_send, got {legacy_calls!r}")

if errors:
    print("RepoPrompt chat-send compatibility errors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)

print("RepoPrompt chat-send compatibility passed")
PYTEST
[[ $? -eq 0 ]] && pass "RepoPrompt chat-send compatibility" || fail "RepoPrompt chat-send compatibility"

# ─────────────────────────────────────────────────────────────────────────────
# 7. ralph.sh Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- ralph.sh Helpers ---${NC}"

# Test tag extraction
"${FLOW_PY[@]}" - << 'PYTEST'
import re
import sys

def extract_tag(text, tag):
    matches = re.findall(rf"<{tag}>(.*?)</{tag}>", text, flags=re.S)
    return matches[-1] if matches else ""

# Test cases
test1 = "<verdict>SHIP</verdict>"
assert extract_tag(test1, "verdict") == "SHIP", f"Expected SHIP, got {extract_tag(test1, 'verdict')}"

test2 = "<promise>continue</promise> some text <promise>stop</promise>"
assert extract_tag(test2, "promise") == "stop", f"Expected stop (last), got {extract_tag(test2, 'promise')}"

test3 = "no tags here"
assert extract_tag(test3, "verdict") == "", f"Expected empty, got {extract_tag(test3, 'verdict')}"

test4 = "<verdict>NEEDS_WORK</verdict>\n<reason>Missing tests</reason>"
assert extract_tag(test4, "verdict") == "NEEDS_WORK"
assert extract_tag(test4, "reason") == "Missing tests"

print("Tag extraction tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "tag extraction" || fail "tag extraction"

# Test JSON helpers (simulate ralph.sh json_get)
"${FLOW_PY[@]}" - << 'PYTEST'
import json

def json_get(key, data):
    val = data.get(key)
    if val is None:
        return ""
    elif isinstance(val, bool):
        return "1" if val else "0"
    else:
        return str(val)

test_data = {"status": "work", "task": "fn-1-abc.2", "blocked": False, "count": 5}

assert json_get("status", test_data) == "work"
assert json_get("task", test_data) == "fn-1-abc.2"
assert json_get("blocked", test_data) == "0"
assert json_get("count", test_data) == "5"
assert json_get("missing", test_data) == ""

print("JSON helper tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "JSON helpers" || fail "JSON helpers"

# Test attempts tracking
"${FLOW_PY[@]}" - "$TEST_DIR" << 'PYTEST'
import json
import sys
from pathlib import Path

test_dir = Path(sys.argv[1])
attempts_file = test_dir / "attempts.json"

def bump_attempts(path, task):
    data = {}
    if path.exists():
        data = json.loads(path.read_text())
    count = int(data.get(task, 0)) + 1
    data[task] = count
    path.write_text(json.dumps(data, indent=2))
    return count

# Test bump
assert bump_attempts(attempts_file, "fn-1.1") == 1
assert bump_attempts(attempts_file, "fn-1.1") == 2
assert bump_attempts(attempts_file, "fn-1.2") == 1
assert bump_attempts(attempts_file, "fn-1.1") == 3

# Verify file content
data = json.loads(attempts_file.read_text())
assert data["fn-1.1"] == 3
assert data["fn-1.2"] == 1

print("Attempts tracking tests passed")
PYTEST
[[ $? -eq 0 ]] && pass "attempts tracking" || fail "attempts tracking"

# ─────────────────────────────────────────────────────────────────────────────
# 8. Artifact File Handling (GH-21)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Artifact File Handling ---${NC}"

# Create artifact files that look like tasks but aren't
cat > ".flow/tasks/${EPIC_ID}.1-evidence.json" << 'EOF'
{"commits":["abc123"],"tests":["npm test"],"prs":[]}
EOF
cat > ".flow/tasks/${EPIC_ID}.1-summary.md" << 'EOF'
Task completed successfully
EOF

# next should still work (not crash on artifact files)
set +e
NEXT_OUT="$(flowctl next --json 2>&1)"
NEXT_RC=$?
set -e
[[ $NEXT_RC -eq 0 ]] && pass "next ignores artifact files" || fail "next with artifact files (rc=$NEXT_RC)"

# ─────────────────────────────────────────────────────────────────────────────
# 9. Async Control Commands
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}--- Async Control Commands ---${NC}"

# Test status command
flowctl status >/dev/null 2>&1
[[ $? -eq 0 ]] && pass "status command" || fail "status command"

# Test status --json (Python validates JSON, not jq)
STATUS_OUT="$(flowctl status --json)"
echo "$STATUS_OUT" | "${FLOW_PY[@]}" -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null
[[ $? -eq 0 ]] && pass "status --json" || fail "status --json invalid JSON"

# Test ralph pause/resume/stop commands
mkdir -p scripts/ralph/runs/test-run
echo "iteration: 1" > scripts/ralph/runs/test-run/progress.txt

flowctl ralph pause --run test-run >/dev/null
[[ -f scripts/ralph/runs/test-run/PAUSE ]] && pass "ralph pause" || fail "ralph pause"

flowctl ralph resume --run test-run >/dev/null
[[ ! -f scripts/ralph/runs/test-run/PAUSE ]] && pass "ralph resume" || fail "ralph resume"

flowctl ralph stop --run test-run >/dev/null
[[ -f scripts/ralph/runs/test-run/STOP ]] && pass "ralph stop" || fail "ralph stop"

rm -rf scripts/ralph/runs/test-run

# Test task reset
RESET_EPIC="$(flowctl spec create --title "Reset test" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
RESET_TASK="$(flowctl task create --spec "$RESET_EPIC" --title "Test task" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

flowctl start "$RESET_TASK" --json >/dev/null
flowctl done "$RESET_TASK" --json >/dev/null
flowctl task reset "$RESET_TASK" --json >/dev/null
RESET_STATUS="$(flowctl show "$RESET_TASK" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
[[ "$RESET_STATUS" == "todo" ]] && pass "task reset" || fail "task reset: status=$RESET_STATUS"

# Test task reset errors on in_progress
flowctl start "$RESET_TASK" --json >/dev/null
set +e
flowctl task reset "$RESET_TASK" --json 2>/dev/null
RESET_RC=$?
set -e
[[ $RESET_RC -ne 0 ]] && pass "task reset rejects in_progress" || fail "task reset should reject in_progress"

# Test epic add-dep/rm-dep
DEP_BASE="$(flowctl spec create --title "Dep base" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
DEP_CHILD="$(flowctl spec create --title "Dep child" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

flowctl spec add-dep "$DEP_CHILD" "$DEP_BASE" --json >/dev/null
DEPS="$(flowctl show "$DEP_CHILD" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(",".join(json.load(sys.stdin).get("depends_on_epics",[])))')"
[[ "$DEPS" == "$DEP_BASE" ]] && pass "epic add-dep" || fail "epic add-dep: deps=$DEPS"

flowctl spec rm-dep "$DEP_CHILD" "$DEP_BASE" --json >/dev/null
DEPS="$(flowctl show "$DEP_CHILD" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(",".join(json.load(sys.stdin).get("depends_on_epics",[])))')"
[[ -z "$DEPS" ]] && pass "epic rm-dep" || fail "epic rm-dep: deps=$DEPS"

# Test ralph auto-detection (single active run)
mkdir -p scripts/ralph/runs/auto-test
echo "iteration: 1" > scripts/ralph/runs/auto-test/progress.txt
flowctl ralph pause >/dev/null 2>&1  # Should auto-detect single run
[[ -f scripts/ralph/runs/auto-test/PAUSE ]] && pass "ralph auto-detect single run" || fail "ralph auto-detect"
rm -rf scripts/ralph/runs/auto-test

# Test multiple active runs error
mkdir -p scripts/ralph/runs/run-a scripts/ralph/runs/run-b
echo "iteration: 1" > scripts/ralph/runs/run-a/progress.txt
echo "iteration: 1" > scripts/ralph/runs/run-b/progress.txt
set +e
flowctl ralph pause 2>/dev/null
MULTI_RC=$?
set -e
[[ $MULTI_RC -ne 0 ]] && pass "ralph rejects multiple active runs" || fail "ralph should reject multiple runs"
rm -rf scripts/ralph/runs/run-a scripts/ralph/runs/run-b

# Test completion marker detection (run with markers not detected as active)
mkdir -p scripts/ralph/runs/completed-test
cat > scripts/ralph/runs/completed-test/progress.txt << 'PROGRESS'
iteration: 5
promise=RETRY

completion_reason=DONE
promise=COMPLETE
PROGRESS
ACTIVE_COUNT="$(flowctl status --json | "${FLOW_PY[@]}" -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get("active_runs",[])))')"
[[ "$ACTIVE_COUNT" == "0" ]] && pass "completed run excluded from active" || fail "completed run still active: count=$ACTIVE_COUNT"
rm -rf scripts/ralph/runs/completed-test

# Test task reset --cascade
CASCADE_EPIC="$(flowctl spec create --title "Cascade test" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
CASCADE_T1="$(flowctl task create --spec "$CASCADE_EPIC" --title "Base task" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
CASCADE_T2="$(flowctl task create --spec "$CASCADE_EPIC" --title "Dependent task" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
flowctl dep add "$CASCADE_T2" "$CASCADE_T1" --json >/dev/null  # T2 depends on T1
flowctl start "$CASCADE_T1" >/dev/null && flowctl done "$CASCADE_T1" >/dev/null
flowctl start "$CASCADE_T2" >/dev/null && flowctl done "$CASCADE_T2" >/dev/null
flowctl task reset "$CASCADE_T1" --cascade --json >/dev/null
T2_STATUS="$(flowctl show "$CASCADE_T2" --json | "${FLOW_PY[@]}" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
[[ "$T2_STATUS" == "todo" ]] && pass "task reset --cascade" || fail "cascade reset: t2 status=$T2_STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}=== Results ===${NC}"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
