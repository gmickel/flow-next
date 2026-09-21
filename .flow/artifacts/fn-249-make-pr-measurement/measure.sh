#!/usr/bin/env bash
# make-pr measurement harness (fn-249 R8 / fn-252 R11).
# usage: measure.sh <point-label> <plugin-dir> <run-number>
# Runs one headless `make-pr --dry-run` on the fixed fixture and appends one
# JSON line (output tokens, tool calls, wall clock) to <point-label>/runs.jsonl.
set -euo pipefail

POINT="$1"; PLUGIN_DIR="$2"; RUN="$3"
ROOT="${MEASURE_ROOT:-$HOME/.cache/flow-next-measure}"
FIX="$ROOT/pr449"
SPEC="fn-248-capture-the-resolved-spec-template"
BASE="07905c2c36b6f96eea815e120e117fff6d2bc8dc"
HEAD_SHA="81990b699b4f352fdb31af5a7da98095311973a2"
MODEL="${MEASURE_MODEL:-claude-fable-5-1}"
OUT="$ROOT/$POINT"; mkdir -p "$OUT"

# Fresh fixture every run: same head, no prior aid artifact, no leftovers.
git -C "$FIX" reset -q --hard "$HEAD_SHA"
git -C "$FIX" clean -qfdx -- .flow/artifacts .flow/tmp 2>/dev/null || true
[ "$(git -C "$FIX" rev-parse HEAD)" = "$HEAD_SHA" ]
# A run picks its own scratch directory, under the user cache or beside the fixture.
# Park every leftover so the next run starts cold: anything matching make-pr-* in the
# user cache, and anything in the harness root that is not the fixture, the harness,
# a point directory or the parking area itself.
PARK="$ROOT/parked/$POINT-before-run$RUN"
for d in "$HOME"/.cache/make-pr-* "$ROOT"/*; do
  [ -e "$d" ] || continue
  case "$(basename "$d")" in pr449|measure.sh|parked|p[0-9]-*) [ "$(dirname "$d")" = "$ROOT" ] && continue ;; esac
  mkdir -p "$PARK"; mv "$d" "$PARK/"
done

STREAM="$OUT/run$RUN.stream.jsonl"
START=$(date +%s.%N)
( cd "$FIX" && FLOWCTL="$PLUGIN_DIR/scripts/flowctl" claude -p \
    "/flow-next:make-pr $SPEC --dry-run --base $BASE" \
    --model "$MODEL" --setting-sources project,local \
    --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions \
    --no-session-persistence --output-format stream-json --verbose \
    </dev/null >"$STREAM" 2>"$OUT/run$RUN.stderr" ) || echo "claude exit $?" >>"$OUT/run$RUN.stderr"
END=$(date +%s.%N)

python3 - "$STREAM" "$POINT" "$RUN" "$MODEL" "$START" "$END" >>"$OUT/runs.jsonl" <<'PY'
import json, sys
stream, point, run, model, start, end = sys.argv[1:7]
tools = 0; result = {}; out_by_msg = {}
for line in open(stream):
    try: ev = json.loads(line)
    except ValueError: continue
    if ev.get("type") == "assistant":
        msg = ev.get("message", {})
        tools += sum(1 for b in msg.get("content", []) if b.get("type") == "tool_use")
        if msg.get("id"):
            out_by_msg[msg["id"]] = msg.get("usage", {}).get("output_tokens", 0)
    elif ev.get("type") == "result":
        result = ev
usage = result.get("usage", {})
print(json.dumps({
    "point": point, "run": int(run), "model": model,
    "output_tokens": usage.get("output_tokens"),
    "output_tokens_stream_sum": sum(out_by_msg.values()),
    "tool_calls": tools,
    "wall_clock_s": round(float(end) - float(start), 1),
    "duration_ms": result.get("duration_ms"),
    "num_turns": result.get("num_turns"),
    "is_error": result.get("is_error"),
    "subtype": result.get("subtype"),
    "result_chars": len(result.get("result") or ""),
}))
PY
tail -1 "$OUT/runs.jsonl"
