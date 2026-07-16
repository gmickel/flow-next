#!/usr/bin/env bash
# guidance-eval scaffolder: build ONE clean-room scratch repo for one matrix cell.
#
# Usage:
#   setup.sh <run_dir> <arm> <scenario> <family> [model_name] [rep] [run_id]
#     arm       minimal | full                 (block-only: NO .flow/usage.md ships)
#               full-usage | full-usage-pretrim (block + on-demand usage.md variant)
#     scenario  slugify | multitask     (picks scenarios/<scenario>.txt at run time)
#     family    claude | codex          (target file: CLAUDE.md vs AGENTS.md; full-block twin selection)
#
# The scratch repo is a self-contained git repo with its OWN flow state, a logging
# shim on flowctl (appends "rc|args" to .flow/invocations.log), the chosen guidance
# block, and a project header. The block-only arms (minimal|full) ship NO
# .flow/usage.md - they measure the always-loaded block ALONE. The usage-aware
# arms ship the full block PLUS an on-demand .flow/usage.md:
#   full-usage          the CURRENT shipped template (post-trim), pulled live
#   full-usage-pretrim  the frozen pre-trim 5392-tok fixture (arms/usage-pretrim.md)
# so a trim can be gated usage-included: trimmed vs pre-trim, same block.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
FLOWCTL_PY="$REPO_ROOT/plugins/flow-next/scripts/flowctl.py"
TEMPLATE_DIR="$REPO_ROOT/plugins/flow-next/skills/flow-next-setup/templates"

run_dir="${1:?run_dir required}"
arm="${2:?arm required (minimal|full)}"
scenario="${3:?scenario required (slugify|multitask)}"
family="${4:?family required (claude|codex)}"
model_name="${5:-$family}"
rep="${6:-1}"
run_id="${7:-$(basename "$run_dir")}"

[ -f "$FLOWCTL_PY" ] || { echo "FATAL: flowctl.py not found at $FLOWCTL_PY" >&2; exit 1; }

# --- validate inputs before ANY destructive filesystem op --------------------
# This script `rm -rf`s run_dir, so guard the path and whitelist identifiers.
case "$arm"      in minimal|full|full-usage|full-usage-pretrim) ;; *) echo "FATAL: bad arm '$arm' (minimal|full|full-usage|full-usage-pretrim)" >&2; exit 1 ;; esac
case "$scenario" in slugify|multitask) ;; *) echo "FATAL: bad scenario '$scenario' (slugify|multitask)" >&2; exit 1 ;; esac
case "$family"   in claude|codex) ;; *) echo "FATAL: bad family '$family' (claude|codex)" >&2; exit 1 ;; esac
case "$model_name" in *[!A-Za-z0-9._-]*) echo "FATAL: model '$model_name' has unsafe chars" >&2; exit 1 ;; esac
case "$run_id"   in *[!A-Za-z0-9._-]*) echo "FATAL: run_id '$run_id' has unsafe chars (path component)" >&2; exit 1 ;; esac
case "$run_dir"  in /*) ;; *) echo "FATAL: run_dir must be an absolute path: '$run_dir'" >&2; exit 1 ;; esac
# Never rm -rf a path that already holds unrelated data: refuse a non-empty dir
# UNLESS it carries our own scratch marker (idempotent re-scaffold of a prior cell).
if [ -e "$run_dir" ]; then
  if [ ! -d "$run_dir" ]; then
    echo "FATAL: run_dir exists and is not a directory: '$run_dir'" >&2; exit 1
  fi
  if [ -n "$(ls -A "$run_dir" 2>/dev/null)" ] && [ ! -f "$run_dir/.eval-meta.json" ]; then
    echo "FATAL: run_dir '$run_dir' is non-empty and is not a prior guidance-eval scratch" >&2
    echo "       (no .eval-meta.json marker) - refusing to rm -rf it." >&2
    exit 1
  fi
fi

# --- resolve guidance block --------------------------------------------------
case "$arm" in
  minimal)
    block="$(cat "$HERE/arms/minimal-block.md")"
    ;;
  full|full-usage|full-usage-pretrim)
    # Derived LIVE from the shipped template so the baseline always reflects the
    # real current block (no drifting snapshot). Marker lines are stripped.
    # The usage-aware arms use the SAME block; they differ only in the
    # .flow/usage.md variant installed below.
    tmpl="$TEMPLATE_DIR/claude-md-snippet.md"
    [ "$family" = codex ] && tmpl="$TEMPLATE_DIR/agents-md-snippet.md"
    [ -f "$tmpl" ] || { echo "FATAL: full-block template not found at $tmpl" >&2; exit 1; }
    block="$(grep -v -e '<!-- BEGIN FLOW-NEXT -->' -e '<!-- END FLOW-NEXT -->' "$tmpl")"
    ;;
  *) echo "FATAL: unknown arm '$arm' (minimal|full|full-usage|full-usage-pretrim)" >&2; exit 1 ;;
esac

# usage-aware arms: resolve the usage.md variant BEFORE any destructive op
usage_src=""
case "$arm" in
  full-usage)
    usage_src="$TEMPLATE_DIR/usage.md"   # current shipped template (post-trim), live
    ;;
  full-usage-pretrim)
    usage_src="$HERE/arms/usage-pretrim.md"  # frozen 5392-tok pre-trim fixture
    ;;
esac
if [ -n "$usage_src" ] && [ ! -f "$usage_src" ]; then
  echo "FATAL: usage.md source not found at $usage_src" >&2; exit 1
fi

target=CLAUDE.md
[ "$family" = codex ] && target=AGENTS.md

# --- scaffold ----------------------------------------------------------------
rm -rf "$run_dir"
mkdir -p "$run_dir/src" "$run_dir/tests"
cd "$run_dir"

git init -q
git config user.name  "guidance-eval"
git config user.email "guidance-eval@example.invalid"
git config commit.gpgsign false

# flow state (init run directly, NOT via the shim - it is harness setup, not an agent action)
python3 "$FLOWCTL_PY" init --json >/dev/null

mkdir -p .flow/bin
cp "$FLOWCTL_PY" .flow/bin/flowctl.py
cat > .flow/bin/flowctl <<'SHIM'
#!/usr/bin/env bash
# logging shim: record "rc|args" for every agent flowctl invocation, then passthrough
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/flowctl.py" "$@"
RC=$?
printf '%s|%s\n' "$RC" "$*" >> "$DIR/../invocations.log"
exit $RC
SHIM
chmod +x .flow/bin/flowctl
: > .flow/invocations.log

# block-only arms measure the block alone: remove the on-demand usage.md.
# usage-aware arms install their variant instead (what /flow-next:setup would ship).
rm -f .flow/usage.md
if [ -n "$usage_src" ]; then
  cp "$usage_src" .flow/usage.md
fi

# project header + guidance block -> agent instruction file
{
  printf '# Project: flowlib\n\n'
  printf 'Small Python utility library. Tests run with: python3 -m unittest discover -s tests\n\n'
  printf '%s\n' "$block"
} > "$target"

# grading metadata (read by grade.py)
cat > .eval-meta.json <<META
{
  "run_id": "$run_id",
  "arm": "$arm",
  "scenario": "$scenario",
  "family": "$family",
  "model": "$model_name",
  "rep": $rep,
  "target_file": "$target"
}
META

git add -A
git commit -qm "scaffold ($arm/$scenario/$model_name)"
echo "scaffolded $run_id -> $run_dir (arm=$arm scenario=$scenario family=$family model=$model_name)"
