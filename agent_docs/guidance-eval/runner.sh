#!/usr/bin/env bash
# guidance-eval runner: scaffold + drive clean-room bridge agents across the
# scenario x arm x model x rep matrix, grade each deterministically, and write a
# ledger-ready JSONL + a batch summary.
#
# Clean-room + hardening contract (binding - see README "Threat model"):
#   * claude models run `claude -p --bare` (else ~/.claude global state leaks in)
#     with explicit `--permission-mode acceptEdits --allowedTools "..."`.
#   * codex runs `codex exec --sandbox danger-full-access --skip-git-repo-check`
#     (workspace-write demonstrably blocks `git commit` in scratch dirs and
#     confounds grading).
#   * Every bridge call is FOREGROUND (waited on, rc captured), wrapped in a
#     per-run timeout with process-tree termination.
#   * Unique run ids; cwd + nested-git-root preflight before every bridge call;
#     retained per-run stdout/stderr + grade artifacts; failed/incomplete summary.
#   * Scratch repos live OUTSIDE this repo's working tree (RUN_ROOT default under
#     $TMPDIR) so an agent's git never touches the flow-next checkout.
#
# Usage:
#   ./runner.sh                 # full R13 baseline matrix
#   SCENARIOS=slugify MODELS=sonnet REPS_DISCRIMINATING=1 ./runner.sh   # quick smoke
#
# Overridable via env:
#   SCENARIOS  (default "slugify multitask")
#   ARMS       (default "minimal full")
#   MODELS     (default "sonnet haiku terra-medium")
#   REPS_DISCRIMINATING (default 3) reps for evidence-validity-discriminating cells
#   REPS_DEFAULT        (default 1) reps for the rest
#   TIMEOUT_SECS        (default 900) per-run wall-clock ceiling
#   MAX_CONCURRENCY     (default 4)
#   RUN_ROOT            (default "$TMPDIR/flow-guidance-eval-<pid>-<ts>")
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"

SCENARIOS="${SCENARIOS:-slugify multitask}"
ARMS="${ARMS:-minimal full}"
MODELS="${MODELS:-sonnet haiku terra-medium}"
REPS_DISCRIMINATING="${REPS_DISCRIMINATING:-3}"
REPS_DEFAULT="${REPS_DEFAULT:-1}"
TIMEOUT_SECS="${TIMEOUT_SECS:-900}"
MAX_CONCURRENCY="${MAX_CONCURRENCY:-4}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ROOT="${RUN_ROOT:-${TMPDIR:-/tmp}/flow-guidance-eval-$$-$STAMP}"
RESULTS_DIR="$RUN_ROOT/results"
JSONL="$RESULTS_DIR/results.jsonl"

# --- root-level nested-git-root guard ---------------------------------------
# RUN_ROOT must NOT sit inside any git repo (esp. this one): a scratch repo whose
# `git init` silently no-ops inside a parent tree would let agents commit into the
# wrong repo. Abort loudly before scaffolding anything.
mkdir -p "$RUN_ROOT"
# Canonicalize (collapse symlinks + `//`) so path-identity checks match the
# physical paths `git rev-parse --show-toplevel` returns (e.g. macOS /var -> /private/var).
RUN_ROOT="$(cd "$RUN_ROOT" && pwd -P)"
if git -C "$RUN_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "FATAL: RUN_ROOT ($RUN_ROOT) is inside a git repo:" >&2
  echo "       $(git -C "$RUN_ROOT" rev-parse --show-toplevel)" >&2
  echo "       Set RUN_ROOT to a path OUTSIDE any checkout (default is under \$TMPDIR)." >&2
  exit 1
fi
case "$RUN_ROOT/" in
  "$REPO_ROOT"/*) echo "FATAL: RUN_ROOT is inside the flow-next checkout ($REPO_ROOT)." >&2; exit 1 ;;
esac
mkdir -p "$RESULTS_DIR"
: > "$JSONL"

echo "guidance-eval runner"
echo "  repo:        $REPO_ROOT"
echo "  run root:    $RUN_ROOT"
echo "  scenarios:   $SCENARIOS"
echo "  arms:        $ARMS"
echo "  models:      $MODELS"
echo "  reps:        discriminating=$REPS_DISCRIMINATING default=$REPS_DEFAULT"
echo "  timeout:     ${TIMEOUT_SECS}s   concurrency: $MAX_CONCURRENCY"
echo

# Run "$@" in the foreground with a wall-clock deadline, as a NEW session/process
# group, and terminate the WHOLE GROUP (TERM then KILL) on timeout. Signalling the
# process group (negative pid) — not a pid-tree walk — catches descendants even
# after they are reparented when the bridge parent exits (the binding safety
# contract for unsandboxed Codex runs). perl provides setsid (macOS has no
# setsid(1)); a backgrounded child in a non-job-control script shares the shell's
# group, so setsid() always succeeds. Returns the command rc, or 124 on timeout.
run_with_timeout() {
  local secs="$1"; shift
  local marker="$RUN_ROOT/.timeout.$$.$RANDOM"
  rm -f "$marker"
  # After setsid the perl pid IS the new group's pgid; exec replaces perl with the
  # target, keeping it group leader. `$!` therefore equals the pgid to signal.
  perl -e 'use POSIX qw(setsid); setsid() or die "setsid: $!"; exec @ARGV or die "exec: $!"' -- "$@" &
  local leader=$!
  (
    sleep "$secs"
    : > "$marker"
    kill -TERM -"$leader" 2>/dev/null
    sleep 10
    kill -KILL -"$leader" 2>/dev/null
  ) &
  local watchdog=$!
  wait "$leader" 2>/dev/null
  local rc=$?
  if [ -f "$marker" ]; then
    # Timeout fired: the leader died from TERM, but TERM-ignoring descendants may
    # still be alive. Do NOT cancel the watchdog - let it finish its grace + KILL
    # of the whole group before we return.
    wait "$watchdog" 2>/dev/null || true
    rm -f "$marker"
    return 124
  fi
  # Normal completion: cancel the pending watchdog, then TERM+KILL-sweep any
  # stragglers left in the group (a completed run may still have orphans).
  kill "$watchdog" 2>/dev/null || true
  wait "$watchdog" 2>/dev/null || true
  kill -TERM -"$leader" 2>/dev/null || true
  sleep 1
  kill -KILL -"$leader" 2>/dev/null || true
  return "$rc"
}

# --- per-cell preflight ------------------------------------------------------
# Assert the scratch dir is its OWN git root (not nested inside a parent repo)
# right before we hand it to a bridge agent. Fail closed.
preflight_ok() {
  local dir="$1"
  [ -d "$dir" ] || { echo "preflight: missing dir $dir" >&2; return 1; }
  # Compare PHYSICAL paths on both sides: `git rev-parse --show-toplevel` returns
  # a canonical realpath, so the scratch dir must be canonicalized too (symlinks,
  # trailing/double slashes) or a benign /var->/private/var alias reads as a hazard.
  local real_dir top
  real_dir="$(cd "$dir" && pwd -P)" || { echo "preflight: cannot cd $dir" >&2; return 1; }
  top="$(git -C "$real_dir" rev-parse --show-toplevel 2>/dev/null)" || {
    echo "preflight: $real_dir is not a git repo" >&2; return 1; }
  if [ "$top" != "$real_dir" ]; then
    echo "preflight: $real_dir git root is $top (nested-repo hazard)" >&2; return 1
  fi
  case "$real_dir/" in
    "$REPO_ROOT"/*) echo "preflight: $real_dir is inside the flow-next checkout" >&2; return 1 ;;
  esac
  return 0
}

# --- one matrix cell ---------------------------------------------------------
run_one() {
  local scenario="$1" arm="$2" model="$3" rep="$4"
  local family run_id dir prompt started rc grade
  case "$model" in
    sonnet|haiku) family=claude ;;
    terra-medium) family=codex ;;
    *) echo "FATAL: unknown model '$model'" >&2; return 1 ;;
  esac
  run_id="${scenario}-${arm}-${model}-r${rep}-${STAMP}"
  dir="$RUN_ROOT/$run_id"
  prompt="$(cat "$HERE/scenarios/$scenario.txt")"

  # scaffold
  if ! "$HERE/setup.sh" "$dir" "$arm" "$scenario" "$family" "$model" "$rep" "$run_id" \
        > "$RUN_ROOT/$run_id.setup.log" 2>&1; then
    echo "[$run_id] SCAFFOLD FAILED (see $run_id.setup.log)"
    echo "{\"run_id\":\"$run_id\",\"status\":\"scaffold_failed\",\"scenario\":\"$scenario\",\"arm\":\"$arm\",\"model\":\"$model\",\"rep\":$rep}" >> "$JSONL"
    return 0
  fi

  # preflight (fail closed - never run a bridge against an unverified cwd)
  if ! preflight_ok "$dir"; then
    echo "[$run_id] PREFLIGHT FAILED"
    echo "{\"run_id\":\"$run_id\",\"status\":\"preflight_failed\",\"scenario\":\"$scenario\",\"arm\":\"$arm\",\"model\":\"$model\",\"rep\":$rep}" >> "$JSONL"
    return 0
  fi

  # drive the bridge agent (foreground, timeout + whole-group kill). The command
  # is a `bash -c` that cd's, then `exec`s the bridge (so the bridge stays the
  # session/group leader). Prompt/dir/model pass via env — no quoting hazard.
  started=$(date +%s)
  export GE_DIR="$dir" GE_LOG="$dir/agent.log" GE_PROMPT="$prompt" GE_MODEL="$model"
  if [ "$family" = claude ]; then
    run_with_timeout "$TIMEOUT_SECS" bash -c '
      cd "$GE_DIR" || exit 99
      exec claude -p "$GE_PROMPT" --model "$GE_MODEL" --bare --output-format text \
        --permission-mode acceptEdits \
        --allowedTools "Read,Bash,Edit,Write,Grep,Glob" </dev/null >"$GE_LOG" 2>&1'
  else
    run_with_timeout "$TIMEOUT_SECS" bash -c '
      cd "$GE_DIR" || exit 99
      exec codex exec --sandbox danger-full-access --skip-git-repo-check -C "$GE_DIR" \
        -m gpt-5.6-terra -c model_reasoning_effort=medium "$GE_PROMPT" </dev/null >"$GE_LOG" 2>&1'
  fi
  rc=$?
  unset GE_DIR GE_LOG GE_PROMPT GE_MODEL
  local wall=$(( $(date +%s) - started ))

  # grade (deterministic; never fatal to the batch)
  grade="$(python3 "$HERE/grade.py" "$dir" 2>"$dir/grade.err")" || grade=""
  if [ -z "$grade" ]; then
    grade="{\"run_id\":\"$run_id\",\"grade_error\":true}"
  fi
  # augment with runtime facts. `status` reflects whether the RUN COMPLETED
  # (bridge ok + graded); `passed` (from grade.py) reflects whether it scored
  # full marks. They are distinct on purpose: a completed run that scores low
  # (e.g. an evidence miss) is a valid DATA POINT, not an incomplete run - but it
  # must never hide as a success, so the summary reports both.
  grade="$(printf '%s' "$grade" | python3 -c "
import json,sys
o=json.load(sys.stdin)
o['bridge_rc']=$rc
o['wall_secs']=$wall
if o.get('grade_error'):
    o['status']='grade_error'
elif $rc==124:
    o['status']='timeout'
elif $rc!=0:
    o['status']='bridge_error'
else:
    o['status']='ok'
o.setdefault('passed', False)
print(json.dumps(o))")"
  echo "$grade" >> "$JSONL"
  printf '[%s] rc=%s wall=%ss score=%s passed=%s\n' "$run_id" "$rc" "$wall" \
    "$(printf '%s' "$grade" | python3 -c 'import json,sys;o=json.load(sys.stdin);print(o.get("score","?"))')" \
    "$(printf '%s' "$grade" | python3 -c 'import json,sys;o=json.load(sys.stdin);print(o.get("passed","?"))')"
}

throttle() { while [ "$(jobs -rp | wc -l)" -ge "$MAX_CONCURRENCY" ]; do sleep 5; done; }

is_discriminating() {  # evidence-validity historically at risk on the Claude family
  case "$1" in sonnet|haiku) return 0 ;; *) return 1 ;; esac
}

for scenario in $SCENARIOS; do
  for arm in $ARMS; do
    for model in $MODELS; do
      if is_discriminating "$model"; then reps=$REPS_DISCRIMINATING; else reps=$REPS_DEFAULT; fi
      for rep in $(seq 1 "$reps"); do
        throttle
        run_one "$scenario" "$arm" "$model" "$rep" &
      done
    done
  done
done
wait

# --- batch summary -----------------------------------------------------------
python3 - "$JSONL" "$RESULTS_DIR/summary.md" "$STAMP" <<'PY'
import json, sys
jsonl, out, stamp = sys.argv[1], sys.argv[2], sys.argv[3]
rows = []
with open(jsonl) as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))
completed = [r for r in rows if r.get("status") == "ok"]
incomplete = [r for r in rows if r.get("status") != "ok"]
# completed but did not score full marks - a real eval failure, NOT hidden as ok
not_passed = [r for r in completed if not r.get("passed")]
passed = [r for r in completed if r.get("passed")]
lines = [f"# guidance-eval batch summary ({stamp})", ""]
lines.append(f"- total runs: {len(rows)}")
lines.append(f"- completed: {len(completed)}  (passed: {len(passed)}, did-not-pass: {len(not_passed)})")
lines.append(f"- failed/incomplete (did not complete): {len(incomplete)}")
lines.append("")
lines.append("| run_id | status | passed | score | evidence_ok | tests_green | flowctl_calls |")
lines.append("|---|---|---|---|---|---|---|")
for r in sorted(rows, key=lambda x: x.get("run_id", "")):
    lines.append("| {run} | {st} | {ps} | {sc} | {ev} | {tg} | {fc} |".format(
        run=r.get("run_id", "?"), st=r.get("status", "?"),
        ps=r.get("passed", "-"),
        sc=r.get("score", "-"), ev=r.get("evidence_ok", "-"),
        tg=r.get("tests_green", "-"), fc=r.get("flowctl_calls", "-")))
if incomplete:
    lines += ["", "## Failed / incomplete (did not complete)", ""]
    for r in incomplete:
        lines.append(f"- {r.get('run_id','?')}: {r.get('status','?')}"
                     + (f" (rc={r['bridge_rc']})" if 'bridge_rc' in r else ""))
if not_passed:
    lines += ["", "## Completed but did NOT pass (eval failures — inspect)", ""]
    for r in not_passed:
        lines.append(f"- {r.get('run_id','?')}: score={r.get('score','?')}"
                     f" evidence_ok={r.get('evidence_ok','?')} tests_green={r.get('tests_green','?')}")
with open(out, "w") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
PY

echo
echo "results: $JSONL"
echo "summary: $RESULTS_DIR/summary.md"
