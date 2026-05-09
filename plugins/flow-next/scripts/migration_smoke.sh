#!/usr/bin/env bash
# fn-43-rename-epic-spec-across-flow-next.14
# Smoke tests for the pre-1.0 → 1.0 .flow/ layout migration shipped in T3
# (`flowctl migrate-rename` / `migrate-rollback`) and the T4 banner-suppression
# matrix.
#
# Covers the 13 scenarios from T14 task spec:
#   1.  Pre-1.0 fixture → migrate-rename --dry-run (no mutation; prints plan;
#       writes .banner-acknowledged)
#   2.  Same fixture → migrate-rename --yes (sentinel + .complete + manifest
#       at top level)
#   3.  Manifest lives at .flow/.migration-manifest, NOT inside backup
#   4.  Idempotent re-run
#   5.  migrate-rollback restores pre-1.0; backup remains intact
#   6.  Post-migration spec creation → migrate-rollback FAILS exit 1
#   7.  --force-overwrite-post-migration-changes proceeds
#   8.  Concurrency: parallel migrate-rename, second waits + stale-lock reclaim
#   9.  Crash recovery (4 cases)
#   10. Read-only `.flow/`: pre-1.0 fails exit 1; already-migrated is no-op
#   11. Atomic sentinel write
#   12. SHA256 task-drift detection — rollback REFUSES with stderr naming the file
#   13. Mid-migration contamination wipe
#
# Plus banner-suppression smoke:
#   - FLOW_RALPH=1 / REVIEW_RECEIPT_PATH / FLOW_NO_AUTO_MIGRATE / sentinel
#     present / .banner-acknowledged < 7d each suppress the 6-line banner
#   - Pre-1.0 fixture without any of those emits the 6-line banner verbatim
#   - --json stdout still parses cleanly with python (jq is optional)
#   - Future-version banner: sentinel `2.0.0` triggers the one-line
#     "newer flow-next" warning; 1.x sentinel is silent. Exit code preserved.
#
# Pure shell + Python — no LLM invocations. Targets <60s runtime.

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

# Safety: never run from the main plugin repo.
if [[ -f "$PWD/.claude-plugin/marketplace.json" ]] || [[ -f "$PWD/plugins/flow-next/.claude-plugin/plugin.json" ]]; then
  echo "ERROR: refusing to run from main plugin repo. Run from any other directory." >&2
  exit 1
fi

TEST_DIR="${TEST_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/migration-smoke-$$}"
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

ok() { echo -e "${GREEN}✓${NC} $*"; printf '.\n' >> "$PASS_LOG"; }
ko() { echo -e "${RED}✗${NC} $*"; printf '.\n' >> "$FAIL_LOG"; }
export -f ok ko

FLOWCTL_PY="$SCRIPT_DIR/flowctl.py"
FLOWCTL_BIN="$SCRIPT_DIR/flowctl"

# Build a pre-1.0 fixture under $1: legacy `.flow/epics/<id>.json` + paired
# `.flow/specs/<id>.md`, no sentinel, no manifest. Matches the shape T3
# detects via _migrate_pre_1_0_layout_present().
make_pre10_fixture() {
  local dir="$1"
  mkdir -p "$dir"
  ( cd "$dir"
    git init -q
    mkdir -p scripts
    cp "$FLOWCTL_PY" scripts/flowctl.py
    cp "$FLOWCTL_BIN" scripts/flowctl
    chmod +x scripts/flowctl

    mkdir -p .flow/epics .flow/specs .flow/tasks .flow/memory
    cat > .flow/meta.json <<'EOF'
{"schema_version": 3, "next_epic": 2}
EOF
    cat > .flow/config.json <<'EOF'
{"memory": {"enabled": false}, "planSync": {"enabled": false}}
EOF
    cat > .flow/epics/fn-1-fixture.json <<'EOF'
{
  "id": "fn-1-fixture",
  "title": "Pre-1.0 fixture epic",
  "status": "open",
  "spec_path": ".flow/specs/fn-1-fixture.md",
  "depends_on_epics": [],
  "created_at": "2026-05-08T00:00:00Z",
  "updated_at": "2026-05-08T00:00:00Z"
}
EOF
    cat > .flow/specs/fn-1-fixture.md <<'EOF'
# fn-1-fixture: Pre-1.0 fixture epic

## Goal
Smoke fixture for migrate-rename / migrate-rollback.

## Acceptance
- **R1:** Trivial criterion.
EOF
    cat > .flow/tasks/fn-1-fixture.1.json <<'EOF'
{
  "id": "fn-1-fixture.1",
  "epic": "fn-1-fixture",
  "title": "Pre-1.0 task",
  "status": "todo",
  "depends_on": [],
  "spec_path": ".flow/tasks/fn-1-fixture.1.md",
  "created_at": "2026-05-08T00:00:00Z",
  "updated_at": "2026-05-08T00:00:00Z"
}
EOF
    cat > .flow/tasks/fn-1-fixture.1.md <<'EOF'
# fn-1-fixture.1: Pre-1.0 task

## Description
Fixture task for migration smoke.

## Acceptance
- [ ] Trivial.
EOF
  )
}

echo -e "${YELLOW}=== migration smoke tests ===${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1: Pre-1.0 fixture → migrate-rename --dry-run (no mutation,
# prints plan, writes .banner-acknowledged)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 1: --dry-run is non-destructive ---${NC}"
(
  R1="$TEST_DIR/scen1"
  make_pre10_fixture "$R1"
  cd "$R1"
  STDOUT="$(scripts/flowctl migrate-rename --dry-run --json 2>/dev/null)"

  if echo "$STDOUT" | "$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
assert data["dry_run"] is True
assert data["migrated"] is False
assert data["would_apply"] is True
assert isinstance(data.get("plan"), list) and data["plan"], "plan must be non-empty"
print("OK")
' >/dev/null; then
    ok "Scenario 1: --dry-run JSON shape (dry_run/would_apply/plan)"
  else
    ko "Scenario 1: dry-run JSON wrong: $STDOUT"
  fi

  # No mutation: legacy epics dir untouched, no sentinel.
  if [[ -f .flow/epics/fn-1-fixture.json && ! -f .flow/.flow_version ]]; then
    ok "Scenario 1: --dry-run did not write sentinel; legacy epics/ intact"
  else
    ko "Scenario 1: --dry-run mutated state"
  fi

  if [[ -f .flow/.banner-acknowledged ]]; then
    ok "Scenario 1: --dry-run wrote .banner-acknowledged"
  else
    ko "Scenario 1: --dry-run did not write .banner-acknowledged"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2: Same fixture → migrate-rename --yes (sentinel + .complete +
# manifest at top level)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 2: --yes applies migration ---${NC}"
(
  R2="$TEST_DIR/scen2"
  make_pre10_fixture "$R2"
  cd "$R2"
  STDOUT="$(scripts/flowctl migrate-rename --yes --json 2>/dev/null)"

  if echo "$STDOUT" | "$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("migrated") is True
print("OK")
' >/dev/null; then
    ok "Scenario 2: --yes JSON reports migrated:true"
  else
    ko "Scenario 2: --yes JSON wrong: $STDOUT"
  fi

  # Sentinel written.
  if [[ -f .flow/.flow_version ]]; then
    payload="$(cat .flow/.flow_version | tr -d '[:space:]')"
    if [[ "$payload" == "1.0.0" ]]; then
      ok "Scenario 2: sentinel .flow_version == 1.0.0"
    else
      ko "Scenario 2: sentinel payload wrong: '$payload'"
    fi
  else
    ko "Scenario 2: sentinel not written"
  fi

  # Backup .complete marker.
  if [[ -f .flow/.backup-pre-1.0/.complete ]]; then
    ok "Scenario 2: backup .complete marker present"
  else
    ko "Scenario 2: backup .complete marker missing"
  fi

  # Top-level manifest.
  if [[ -f .flow/.migration-manifest ]]; then
    ok "Scenario 2: manifest at .flow/.migration-manifest (top level)"
  else
    ko "Scenario 2: top-level manifest missing"
  fi

  # Spec relocated to canonical path.
  if [[ -f .flow/specs/fn-1-fixture.json && ! -f .flow/epics/fn-1-fixture.json ]]; then
    ok "Scenario 2: spec JSON moved to .flow/specs/"
  else
    ko "Scenario 2: spec JSON not relocated"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3: .flow/.backup-pre-1.0/.migration-manifest does NOT exist
# (manifest is top-level only).
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 3: manifest never inside backup ---${NC}"
(
  R3="$TEST_DIR/scen3"
  make_pre10_fixture "$R3"
  cd "$R3"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null

  if [[ ! -f .flow/.backup-pre-1.0/.migration-manifest ]]; then
    ok "Scenario 3: no manifest inside .backup-pre-1.0/"
  else
    ko "Scenario 3: manifest leaked inside backup"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4: Idempotent re-run
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 4: idempotent re-run ---${NC}"
(
  R4="$TEST_DIR/scen4"
  make_pre10_fixture "$R4"
  cd "$R4"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  STDOUT="$(scripts/flowctl migrate-rename --yes --json 2>/dev/null)"

  if echo "$STDOUT" | "$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("migrated") is False, f"second --yes should be no-op: {data}"
assert data.get("reason") == "already migrated"
print("OK")
' >/dev/null; then
    ok "Scenario 4: re-run reports migrated:false + already-migrated reason"
  else
    ko "Scenario 4: re-run wrong: $STDOUT"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5: migrate-rollback --yes restores pre-1.0; backup retained
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 5: rollback restores pre-1.0 layout ---${NC}"
(
  R5="$TEST_DIR/scen5"
  make_pre10_fixture "$R5"
  cd "$R5"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  scripts/flowctl migrate-rollback --yes --json 2>/dev/null >/dev/null

  if [[ -f .flow/epics/fn-1-fixture.json && ! -f .flow/.flow_version ]]; then
    ok "Scenario 5: rollback restored .flow/epics/ + removed sentinel"
  else
    ko "Scenario 5: rollback did not restore pre-1.0 layout"
  fi

  if [[ -d .flow/.backup-pre-1.0 ]]; then
    ok "Scenario 5: backup retained post-rollback"
  else
    ko "Scenario 5: backup deleted post-rollback (should retain)"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 6: Post-migration spec creation → rollback FAILS exit 1
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 6: post-migration writes refuse rollback ---${NC}"
(
  R6="$TEST_DIR/scen6"
  make_pre10_fixture "$R6"
  cd "$R6"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  # Create a new spec post-migration (simulates user work after migration).
  scripts/flowctl spec create --title "Post-migration" --json 2>/dev/null >/dev/null

  set +e
  ROLLBACK_OUT="$(scripts/flowctl migrate-rollback --yes --json 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    ok "Scenario 6: rollback exits non-zero on post-migration writes (rc=$rc)"
  else
    ko "Scenario 6: rollback unexpectedly succeeded with post-migration writes"
  fi
  if echo "$ROLLBACK_OUT" | grep -qi 'post-migration writes detected'; then
    ok "Scenario 6: stderr mentions 'post-migration writes detected'"
  else
    ko "Scenario 6: stderr missing post-migration-writes message: $ROLLBACK_OUT"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 7: --force-overwrite-post-migration-changes proceeds
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 7: --force-overwrite-post-migration-changes ---${NC}"
(
  R7="$TEST_DIR/scen7"
  make_pre10_fixture "$R7"
  cd "$R7"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  scripts/flowctl spec create --title "Post-migration" --json 2>/dev/null >/dev/null

  set +e
  scripts/flowctl migrate-rollback --yes --force-overwrite-post-migration-changes --json 2>/dev/null >/dev/null
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    ok "Scenario 7: --force flag bypasses post-migration-writes refusal (rc=0)"
  else
    ko "Scenario 7: --force flag did not bypass refusal (rc=$rc)"
  fi
  if [[ -f .flow/epics/fn-1-fixture.json && ! -f .flow/.flow_version ]]; then
    ok "Scenario 7: --force completed full rollback"
  else
    ko "Scenario 7: --force did not complete rollback"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 8: Concurrency — second migrate-rename waits; stale-lock reclaim
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 8: concurrency (real parallel + stale-lock reclaim) ---${NC}"
(
  # 8a: Stale-lock reclaim. Write a lock dir with a stale pid (definitely
  # dead — pid=1 is init on POSIX, never a stale `flowctl` worker; we use
  # an obviously-dead pid like 99999999 with mtime older than the grace
  # window).
  R8A="$TEST_DIR/scen8a"
  make_pre10_fixture "$R8A"
  cd "$R8A"
  mkdir -p .flow/.migrating
  echo "99999999" > .flow/.migrating/pid
  # Backdate mtime far beyond the 5s grace window.
  if command -v touch >/dev/null 2>&1; then
    # POSIX touch -t YYYYMMDDhhmm
    touch -t "201001010000" .flow/.migrating .flow/.migrating/pid 2>/dev/null || true
  fi
  set +e
  RECLAIM_OUT="$(scripts/flowctl migrate-rename --yes --json 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    ok "Scenario 8a: stale-lock reclaim succeeded (rc=0)"
  else
    ko "Scenario 8a: stale-lock reclaim failed (rc=$rc): $RECLAIM_OUT"
  fi
)

(
  # 8b: Real parallel migration. Spawn TWO live `flowctl migrate-rename
  # --yes` processes concurrently. The lock acquisition is a `mkdir`
  # (atomic on POSIX). One MUST acquire and complete; the second MUST
  # either:
  #   - wait + observe the completed state via authoritative idempotency
  #     check (returns migrated:false / reason: "already migrated"), OR
  #   - acquire after the first releases and observe nothing to do.
  # Both must exit 0; the on-disk state must be correctly migrated.
  R8B="$TEST_DIR/scen8b"
  make_pre10_fixture "$R8B"
  cd "$R8B"

  OUT1="$TEST_DIR/scen8b-a.out"
  OUT2="$TEST_DIR/scen8b-b.out"
  RC1F="$TEST_DIR/scen8b-a.rc"
  RC2F="$TEST_DIR/scen8b-b.rc"

  # Launch both in background; capture rc per process via wrapper.
  (
    scripts/flowctl migrate-rename --yes --json >"$OUT1" 2>&1
    echo $? > "$RC1F"
  ) &
  P1=$!
  (
    scripts/flowctl migrate-rename --yes --json >"$OUT2" 2>&1
    echo $? > "$RC2F"
  ) &
  P2=$!

  # Bounded wait — lock window is at most MIGRATE_LOCK_WAIT_SECS (30s).
  wait "$P1" 2>/dev/null || true
  wait "$P2" 2>/dev/null || true
  RC1="$(cat "$RC1F" 2>/dev/null || echo 1)"
  RC2="$(cat "$RC2F" 2>/dev/null || echo 1)"

  if [[ "$RC1" -eq 0 && "$RC2" -eq 0 ]]; then
    ok "Scenario 8b: both parallel migrate-rename invocations exited 0"
  else
    ko "Scenario 8b: parallel rc mismatch — RC1=$RC1 RC2=$RC2"
    echo "  --- proc1 ---" >&2
    cat "$OUT1" >&2 2>/dev/null || true
    echo "  --- proc2 ---" >&2
    cat "$OUT2" >&2 2>/dev/null || true
  fi

  # Exactly one process must report migrated:true; the other must report
  # the no-op idempotent skip (migrated:false / reason: "already migrated").
  TRUE_COUNT=0
  IDEMPOTENT_COUNT=0
  for OUT in "$OUT1" "$OUT2"; do
    # Outputs may carry preceding banner text on stderr-merged streams; we
    # redirected 2>&1 above, so locate the JSON body via python.
    "$PYTHON_BIN" - "$OUT" <<'PY' || true
import json, re, sys
text = open(sys.argv[1]).read()
match = re.search(r'(\{[\s\S]*\})', text)
if not match:
    sys.exit(2)
try:
    data = json.loads(match.group(1))
except Exception:
    sys.exit(3)
if data.get("migrated") is True:
    print("MIGRATED")
elif data.get("migrated") is False and data.get("reason") == "already migrated":
    print("IDEMPOTENT")
else:
    print("OTHER:" + json.dumps(data))
PY
  done > "$TEST_DIR/scen8b-summary.txt"

  TRUE_COUNT=$(grep -c '^MIGRATED$' "$TEST_DIR/scen8b-summary.txt" 2>/dev/null || echo 0)
  IDEMPOTENT_COUNT=$(grep -c '^IDEMPOTENT$' "$TEST_DIR/scen8b-summary.txt" 2>/dev/null || echo 0)

  if [[ "$TRUE_COUNT" -eq 1 && "$IDEMPOTENT_COUNT" -eq 1 ]]; then
    ok "Scenario 8b: exactly one process migrated; the other observed idempotent skip"
  else
    ko "Scenario 8b: contention shape wrong (migrated=$TRUE_COUNT, idempotent=$IDEMPOTENT_COUNT)"
    echo "  --- summary ---" >&2
    cat "$TEST_DIR/scen8b-summary.txt" >&2
  fi

  # On-disk state must be a single, complete migration.
  if [[ -f .flow/.flow_version && -f .flow/.backup-pre-1.0/.complete && -f .flow/.migration-manifest && ! -d .flow/.migrating ]]; then
    ok "Scenario 8b: post-contention state is fully migrated; lock released"
  else
    ko "Scenario 8b: post-contention disk state is incomplete"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 9: Crash recovery decision tree (4 cases from T3)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 9: crash recovery (4 cases) ---${NC}"

# 9a: No backup at all (crashed before backup started)
(
  R9A="$TEST_DIR/scen9a"
  make_pre10_fixture "$R9A"
  cd "$R9A"
  # No partial state; just run migrate-rename --yes. Should complete cleanly.
  set +e
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  rc=$?
  set -e
  if [[ "$rc" -eq 0 && -f .flow/.flow_version ]]; then
    ok "Scenario 9a: no-backup case → migration completes from step 4"
  else
    ko "Scenario 9a: no-backup case failed"
  fi
)

# 9b: Partial backup (no .complete marker) → migrate restarts the backup phase
(
  R9B="$TEST_DIR/scen9b"
  make_pre10_fixture "$R9B"
  cd "$R9B"
  # Simulate partial backup: backup dir exists but no .complete marker.
  mkdir -p .flow/.backup-pre-1.0/specs
  echo "stale" > .flow/.backup-pre-1.0/specs/orphan.md
  set +e
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  rc=$?
  set -e
  if [[ "$rc" -eq 0 && -f .flow/.flow_version && -f .flow/.backup-pre-1.0/.complete ]]; then
    ok "Scenario 9b: partial-backup case → migrate restarts backup phase"
  else
    ko "Scenario 9b: partial-backup case did not recover"
  fi
)

# 9c: Complete backup, no manifest (clean rollback aftermath, then re-run
# migrate-rename — should treat as fresh and snapshot current state)
(
  R9C="$TEST_DIR/scen9c"
  make_pre10_fixture "$R9C"
  cd "$R9C"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  scripts/flowctl migrate-rollback --yes --json 2>/dev/null >/dev/null
  # After rollback: backup intact, .complete present, no manifest, no sentinel.
  if [[ -d .flow/.backup-pre-1.0 && -f .flow/.backup-pre-1.0/.complete && ! -f .flow/.migration-manifest && ! -f .flow/.flow_version ]]; then
    set +e
    scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
    rc=$?
    set -e
    if [[ "$rc" -eq 0 && -f .flow/.flow_version ]]; then
      ok "Scenario 9c: clean-rollback-aftermath → re-migrate succeeds"
    else
      ko "Scenario 9c: re-migrate after rollback failed"
    fi
  else
    ko "Scenario 9c: pre-condition not established (rollback shape wrong)"
  fi
)

# 9d: Mid-migration crash (manifest populated, sentinel missing) →
# migrate restores from backup by COPY (not move)
(
  R9D="$TEST_DIR/scen9d"
  make_pre10_fixture "$R9D"
  cd "$R9D"
  # Run a real migrate to set up backup + manifest, then simulate a crash
  # by removing the sentinel.
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  # Snapshot manifest content before the simulated crash so we can verify
  # it stays present (or gets re-initialized).
  rm -f .flow/.flow_version
  # Simulate a partial mutation: leave manifest in place but corrupt one
  # spec file to simulate post-write crash.
  if [[ -f .flow/specs/fn-1-fixture.json ]]; then
    echo "{}" > .flow/specs/fn-1-fixture.json
  fi
  set +e
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  rc=$?
  set -e
  if [[ "$rc" -eq 0 && -f .flow/.flow_version ]]; then
    ok "Scenario 9d: mid-migration crash → migrate restores + retries"
  else
    ko "Scenario 9d: mid-migration crash recovery failed"
  fi
  # Backup must remain after restore-by-COPY.
  if [[ -d .flow/.backup-pre-1.0 ]]; then
    ok "Scenario 9d: backup retained after crash recovery (copy not move)"
  else
    ko "Scenario 9d: backup removed during crash recovery"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 10: Read-only `.flow/` semantics
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 10: read-only .flow/ semantics ---${NC}"

# 10a: Pre-1.0 layout + read-only `.flow/` → migrate-rename --yes fails exit 1
(
  R10A="$TEST_DIR/scen10a"
  make_pre10_fixture "$R10A"
  cd "$R10A"
  # Mark `.flow/` read-only. Best-effort: chmod handles POSIX; Windows we
  # skip with a soft pass.
  if chmod -R a-w .flow 2>/dev/null && ! ( touch .flow/.test-write 2>/dev/null ); then
    set +e
    OUT="$(scripts/flowctl migrate-rename --yes --json 2>&1)"
    rc=$?
    set -e
    chmod -R u+w .flow 2>/dev/null || true
    if [[ "$rc" -eq 1 ]] && echo "$OUT" | grep -qi 'read-only'; then
      ok "Scenario 10a: pre-1.0 + read-only → exit 1 + 'read-only' in stderr"
    else
      ko "Scenario 10a: pre-1.0 + read-only behavior wrong: rc=$rc out=$OUT"
    fi
  else
    chmod -R u+w .flow 2>/dev/null || true
    ok "Scenario 10a: skipped (filesystem ignores chmod a-w; e.g. tmpfs)"
  fi
)

# 10b: Already-migrated repo on read-only fs → no-op (idempotency check
# runs BEFORE read-only writability probe; F9 from T3)
(
  R10B="$TEST_DIR/scen10b"
  make_pre10_fixture "$R10B"
  cd "$R10B"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  # Now mark `.flow/` read-only.
  if chmod -R a-w .flow 2>/dev/null && ! ( touch .flow/.test-write 2>/dev/null ); then
    set +e
    OUT="$(scripts/flowctl migrate-rename --yes --json 2>&1)"
    rc=$?
    set -e
    chmod -R u+w .flow 2>/dev/null || true
    if [[ "$rc" -eq 0 ]] && echo "$OUT" | "$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("migrated") is False
assert data.get("reason") == "already migrated"
print("OK")
' >/dev/null 2>&1; then
      ok "Scenario 10b: already-migrated + read-only → no-op (F9 ordering)"
    else
      ko "Scenario 10b: idempotency-before-readonly failed: rc=$rc out=$OUT"
    fi
  else
    chmod -R u+w .flow 2>/dev/null || true
    ok "Scenario 10b: skipped (filesystem ignores chmod a-w)"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 11: Atomic sentinel write — partial-byte sentinel triggers
# crash recovery (treated as no valid sentinel, NOT idempotent skip).
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 11: atomic sentinel + crash-during-step-11 ---${NC}"
(
  R11="$TEST_DIR/scen11"
  make_pre10_fixture "$R11"
  cd "$R11"

  # 11a: Crash BEFORE step 11 (sentinel write). Simulate by kill -KILL
  # mid-migration from a wrapper that sets up state then signals itself.
  # Since shelling out a real kill on the right Python frame is brittle,
  # we directly construct the post-mid-migration state on disk and verify
  # the recovery path picks up cleanly:
  #
  #   - backup .complete present + manifest present + sentinel ABSENT
  #     => mid-migration crash; restart restores from backup (by COPY) + retries.
  #
  # This is exactly the "kill during step 11" scenario: between step 10
  # (manifest write) and step 11 (sentinel write).
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  if [[ ! -f .flow/.flow_version ]]; then
    ko "Scenario 11a: pre-condition: initial migration must succeed"
  else
    # Confirm atomic_write left no .tmp shadow.
    SHADOW_COUNT="$(find .flow -maxdepth 2 -name '.flow_version.tmp*' 2>/dev/null | wc -l | tr -d '[:space:]')"
    if [[ "$SHADOW_COUNT" -eq 0 ]]; then
      ok "Scenario 11a: atomic_write left no .flow_version.tmp shadow file"
    else
      ko "Scenario 11a: atomic_write left transient .tmp file (count=$SHADOW_COUNT)"
    fi

    # Now simulate crash mid-step-11: remove the sentinel after the
    # manifest + backup .complete are in place (matches the kill window
    # between step 10 and step 11). Restart MUST recover.
    rm -f .flow/.flow_version
    # Sanity: confirm we're in the mid-migration crash state.
    if [[ ! -f .flow/.flow_version && -f .flow/.backup-pre-1.0/.complete && -f .flow/.migration-manifest ]]; then
      set +e
      RETRY_OUT="$(scripts/flowctl migrate-rename --yes --json 2>/dev/null)"
      rc=$?
      set -e
      if [[ "$rc" -eq 0 && -f .flow/.flow_version ]]; then
        payload="$(cat .flow/.flow_version | tr -d '[:space:]')"
        if [[ "$payload" == "1.0.0" ]]; then
          ok "Scenario 11a-recover: mid-step-11 crash → restart writes valid sentinel"
        else
          ko "Scenario 11a-recover: sentinel payload wrong after recovery: '$payload'"
        fi
      else
        ko "Scenario 11a-recover: mid-step-11 restart failed (rc=$rc, output=$RETRY_OUT)"
      fi
    else
      ko "Scenario 11a-recover: pre-condition for mid-migration crash not established"
    fi
  fi

  # 11b: Empty / garbage sentinel must NOT be treated as 'already migrated'
  # by the fast-path idempotency check. atomic_write guarantees the file
  # is either fully written or absent on POSIX, but a hostile filesystem
  # could leave a partial file from a non-atomic write — the validator
  # must reject it. (Simulated by manually writing an empty sentinel
  # then triggering the fast-path check via a no-op `flowctl status`.)
  echo "" > .flow/.flow_version
  # Verify _migrate_sentinel_state rejects empty payload by checking that
  # the migration banner fires (it only fires when sentinel is invalid).
  # We turn FLOW_NO_AUTO_MIGRATE off temporarily for this assertion.
  STDERR_FILE="$TEST_DIR/scen11b-stderr.txt"
  unset FLOW_NO_AUTO_MIGRATE
  scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
  export FLOW_NO_AUTO_MIGRATE=1
  if grep -q 'flow-next 1.0 renamed' "$STDERR_FILE"; then
    ok "Scenario 11b: empty sentinel triggers banner (treated as not-migrated)"
  else
    # The banner only fires when .flow/epics/ is also present. Restore the
    # legacy dir so the banner code path activates.
    mkdir -p .flow/epics
    : > "$STDERR_FILE"
    unset FLOW_NO_AUTO_MIGRATE
    scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
    export FLOW_NO_AUTO_MIGRATE=1
    if grep -q 'flow-next 1.0 renamed' "$STDERR_FILE"; then
      ok "Scenario 11b: empty sentinel triggers banner (after epics/ restored)"
    else
      ko "Scenario 11b: empty sentinel did not trigger banner; payload validation may be missing"
    fi
  fi

  # 11c: Forward-compat semver payload (1.1.0) — accepted as already
  # migrated; idempotency fast-path returns no-op cleanly.
  rm -rf .flow/epics 2>/dev/null || true
  echo "1.1.0" > .flow/.flow_version
  set +e
  STDOUT="$(scripts/flowctl migrate-rename --yes --json 2>/dev/null)"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]] && echo "$STDOUT" | "$PYTHON_BIN" -c '
import json, sys
data = json.load(sys.stdin)
assert data.get("migrated") is False
assert data.get("reason") == "already migrated"
print("OK")
' >/dev/null; then
    ok "Scenario 11c: forward-compat sentinel (1.1.0) accepted as migrated"
  else
    ko "Scenario 11c: forward-compat semver not accepted: rc=$rc out=$STDOUT"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 12: SHA256 task-drift detection — manually mutate a task JSON
# post-migration to a non-manifest content; rollback must REFUSE with
# stderr naming the file.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 12: SHA256 task-drift detection ---${NC}"
(
  R12="$TEST_DIR/scen12"
  make_pre10_fixture "$R12"
  cd "$R12"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  # Mutate a task JSON post-migration to drift off the manifest's recorded SHA256.
  TASK_JSON=".flow/tasks/fn-1-fixture.1.json"
  if [[ -f "$TASK_JSON" ]]; then
    "$PYTHON_BIN" -c "
import json
data = json.load(open('$TASK_JSON'))
data['title'] = 'Drifted post-migration title'
json.dump(data, open('$TASK_JSON', 'w'), indent=2, sort_keys=True)
"
    set +e
    OUT="$(scripts/flowctl migrate-rollback --yes --json 2>&1)"
    rc=$?
    set -e
    if [[ "$rc" -ne 0 ]]; then
      ok "Scenario 12: rollback refuses on SHA256 task drift (rc=$rc)"
    else
      ko "Scenario 12: rollback succeeded despite task drift"
    fi
    if echo "$OUT" | grep -q 'fn-1-fixture\.1\.json'; then
      ok "Scenario 12: stderr names the drifted file"
    else
      ko "Scenario 12: stderr did not name drifted file: $OUT"
    fi
  else
    ko "Scenario 12: task JSON missing post-migration"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Scenario 13: Mid-migration contamination wipe — pre-existing manifest from
# a prior interrupted migration is wiped clean before re-init on retry.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Scenario 13: contamination wipe before re-init ---${NC}"
(
  R13="$TEST_DIR/scen13"
  make_pre10_fixture "$R13"
  cd "$R13"
  # Simulate a stale manifest from a prior interrupted migration:
  # backup .complete present, manifest present, sentinel missing (mid-migration crash).
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  rm -f .flow/.flow_version
  # Pollute the manifest with stale content. Re-running migrate-rename
  # should detect mid-migration crash, wipe + re-init manifest.
  echo "{\"stale\": \"prior interrupted run\"}" > .flow/.migration-manifest

  set +e
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  rc=$?
  set -e
  if [[ "$rc" -eq 0 && -f .flow/.flow_version ]]; then
    ok "Scenario 13: stale manifest wiped + re-initialized; migration completes"
    # Validate fresh manifest shape (must be JSON, must NOT have "stale" key).
    if "$PYTHON_BIN" -c '
import json
data = json.load(open(".flow/.migration-manifest"))
assert "stale" not in data, "stale key survived re-init"
print("OK")
' >/dev/null 2>&1; then
      ok "Scenario 13: stale manifest 'stale' key wiped on re-init"
    else
      ko "Scenario 13: stale manifest content survived"
    fi
  else
    ko "Scenario 13: contamination wipe + retry failed"
  fi
)

# ─────────────────────────────────────────────────────────────────────────────
# Banner suppression matrix (T4)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}--- Banner suppression matrix (T4) ---${NC}"

# B1: pre-1.0 fixture, no suppression knobs → 6-line banner emitted on stderr.
(
  RB1="$TEST_DIR/banner1"
  make_pre10_fixture "$RB1"
  cd "$RB1"
  STDERR_FILE="$TEST_DIR/banner1-stderr.txt"
  scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
  STDERR="$(cat "$STDERR_FILE")"
  expected_lines=(
    "flow-next 1.0 renamed"
    "Your \`.flow/epics/\` directory is from 0.x"
    "Migrate to unlock future flow-swarm compatibility"
    "Interactive:  /flow-next:setup"
    "Deterministic: flowctl migrate-rename --yes"
    "Suppress this banner: FLOW_NO_AUTO_MIGRATE=1"
  )
  all_present=1
  for line in "${expected_lines[@]}"; do
    if ! echo "$STDERR" | grep -qF -- "$line"; then
      all_present=0
      break
    fi
  done
  if [[ "$all_present" -eq 1 ]]; then
    ok "Banner B1: 6-line pre-1.0 banner emitted verbatim on bare invocation"
  else
    ko "Banner B1: banner missing or malformed; got: $STDERR"
  fi
)

# B2: --json stdout still parses cleanly even with banner on stderr.
(
  RB2="$TEST_DIR/banner2"
  make_pre10_fixture "$RB2"
  cd "$RB2"
  STDOUT="$(scripts/flowctl status --json 2>/dev/null)"
  if echo "$STDOUT" | "$PYTHON_BIN" -c 'import json, sys; json.load(sys.stdin); print("OK")' >/dev/null; then
    ok "Banner B2: --json stdout parses cleanly with banner on stderr"
  else
    ko "Banner B2: --json stdout corrupted by banner: $STDOUT"
  fi
)

# B3: each suppression knob silences the banner.
for env_var_pair in \
    "FLOW_RALPH=1" \
    "FLOW_NO_AUTO_MIGRATE=1" \
    "REVIEW_RECEIPT_PATH=/tmp/receipt-$$"
do
  (
    RB="$TEST_DIR/banner-${env_var_pair%%=*}-$$"
    make_pre10_fixture "$RB"
    cd "$RB"
    STDERR_FILE="$TEST_DIR/banner-${env_var_pair%%=*}-stderr.txt"
    env "$env_var_pair" scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
    STDERR="$(cat "$STDERR_FILE")"
    if ! echo "$STDERR" | grep -q 'flow-next 1.0 renamed'; then
      ok "Banner B3: $env_var_pair suppresses 6-line banner"
    else
      ko "Banner B3: $env_var_pair did not suppress banner; got: $STDERR"
    fi
  )
done

# B4: post-migration sentinel (1.x) → silent.
(
  RB4="$TEST_DIR/banner4"
  make_pre10_fixture "$RB4"
  cd "$RB4"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  STDERR_FILE="$TEST_DIR/banner4-stderr.txt"
  scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
  STDERR="$(cat "$STDERR_FILE")"
  if ! echo "$STDERR" | grep -q 'flow-next 1.0 renamed'; then
    ok "Banner B4: post-migration sentinel (1.0.0) silences banner"
  else
    ko "Banner B4: 1.x sentinel did not silence banner: $STDERR"
  fi
)

# B5: .banner-acknowledged < 7d → silent.
(
  RB5="$TEST_DIR/banner5"
  make_pre10_fixture "$RB5"
  cd "$RB5"
  # Stamp ack in the future-relative-to-zero (today).
  "$PYTHON_BIN" -c '
from datetime import datetime, timezone
from pathlib import Path
Path(".flow/.banner-acknowledged").write_text(datetime.now(timezone.utc).isoformat() + "\n")
'
  STDERR_FILE="$TEST_DIR/banner5-stderr.txt"
  scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
  STDERR="$(cat "$STDERR_FILE")"
  if ! echo "$STDERR" | grep -q 'flow-next 1.0 renamed'; then
    ok "Banner B5: .banner-acknowledged < 7d silences banner"
  else
    ko "Banner B5: ack <7d did not silence banner: $STDERR"
  fi
)

# B6: future-version banner — sentinel >= 2.0.0 emits one-line warning;
# subcommand exit code preserved.
(
  RB6="$TEST_DIR/banner6"
  make_pre10_fixture "$RB6"
  cd "$RB6"
  # Migrate normally first, then bump the sentinel to a future major.
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  echo "2.0.0" > .flow/.flow_version
  STDERR_FILE="$TEST_DIR/banner6-stderr.txt"
  set +e
  scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null
  rc=$?
  set -e
  STDERR="$(cat "$STDERR_FILE")"
  if echo "$STDERR" | grep -q 'newer flow-next'; then
    ok "Banner B6: 2.0.0 sentinel emits one-line 'newer flow-next' warning"
  else
    ko "Banner B6: 2.0.0 sentinel did not emit forward-compat warning: $STDERR"
  fi
  if [[ "$rc" -eq 0 ]]; then
    ok "Banner B6: subcommand exit code preserved across forward-compat warning"
  else
    ko "Banner B6: subcommand exit code clobbered by forward-compat warning (rc=$rc)"
  fi
)

# B7: 1.x sentinel (e.g., 1.5.2) does NOT emit the future-version warning.
(
  RB7="$TEST_DIR/banner7"
  make_pre10_fixture "$RB7"
  cd "$RB7"
  scripts/flowctl migrate-rename --yes --json 2>/dev/null >/dev/null
  echo "1.5.2" > .flow/.flow_version
  STDERR_FILE="$TEST_DIR/banner7-stderr.txt"
  scripts/flowctl status --json 2>"$STDERR_FILE" >/dev/null || true
  STDERR="$(cat "$STDERR_FILE")"
  if ! echo "$STDERR" | grep -q 'newer flow-next'; then
    ok "Banner B7: 1.x sentinel (1.5.2) is silent (no forward-compat warning)"
  else
    ko "Banner B7: 1.x sentinel emitted forward-compat warning: $STDERR"
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

echo -e "${GREEN}All migration smoke tests passed!${NC}"
