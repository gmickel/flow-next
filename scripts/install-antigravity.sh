#!/bin/bash
# Install Flow-Next into Antigravity CLI (Google's `agy`) at user scope.
#
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/flow-next.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-antigravity.sh \
#     && trash /tmp/flow-next-install
#
# Usage: ./scripts/install-antigravity.sh
#
# Antigravity converts Claude-format plugins on install, but its loader skips
# agents with Claude model aliases and ignores `disallowedTools`. This script
# builds a temporary native bundle from the canonical plugin
# (plugins/flow-next/scripts/lib/antigravity_bundle.py maps agent models and
# tools, turns commands into hidden stub skills, and adds rules/AGENTS.md),
# installs it with `agy plugin install`, validates the installed copy with
# `agy plugin validate`, and deletes the bundle. Antigravity owns the
# installed copy; re-run after `git pull` to update.
#
# POSIX only, matching install-muse.sh. Never writes Antigravity settings.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$REPO_ROOT/plugins/flow-next"

die() {
    echo "ERROR: $*" >&2
    exit 1
}

case "${1:-}" in
    "") ;;
    -h|--help)
        sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    *) die "unknown argument: $1 (see --help)" ;;
esac

command -v agy >/dev/null 2>&1 || die "agy not found on PATH; install Antigravity CLI first: https://antigravity.google/docs/cli/reference.md"
command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/flow-next-antigravity.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
BUNDLE="$WORK/flow-next"

python3 -B "$PLUGIN_DIR/scripts/lib/antigravity_bundle.py" "$PLUGIN_DIR" "$BUNDLE" \
    || die "bundle build failed"
python3 -B "$BUNDLE/scripts/lib/verify_tracker_manifest.py" "$BUNDLE/scripts" \
    || die "tracker package manifest mismatch in the bundle"

agy plugin install "$BUNDLE" || die "agy plugin install failed"

# Validate the installed copy, not the bundle: every skill and agent the
# bundle carries must load, with no loader errors.
agy plugin list --json >"$WORK/list.json" || die "agy plugin list failed after install"
INSTALLED="$(python3 -c 'import json,sys
rows=[r for r in json.load(open(sys.argv[1])) if r.get("name")=="flow-next"]
print(rows[0]["path"] if len(rows)==1 and rows[0].get("path") else "")' "$WORK/list.json")" \
    || die "could not read agy plugin list output"
[ -n "$INSTALLED" ] || die "agy plugin list does not show exactly one flow-next install"
agy plugin validate "$INSTALLED" --json >"$WORK/validate.json" \
    || die "agy plugin validate reported errors for $INSTALLED (run: agy plugin validate $INSTALLED)"
python3 - "$WORK/validate.json" "$BUNDLE" <<'PY' || die "installed flow-next is incomplete (run: agy plugin validate $INSTALLED)"
import json, sys
from pathlib import Path
report, bundle = json.load(open(sys.argv[1])), Path(sys.argv[2])
want = {"skills": len(list(bundle.glob("skills/*/SKILL.md"))),
        "agents": len(list(bundle.glob("agents/*.md")))}
got = report.get("components", {})
errors = [f for f in report.get("findings", []) if f.get("severity") == "error"]
for f in errors:
    print(f"  {f.get('file')}: {f.get('message')}", file=sys.stderr)
for key, n in want.items():
    if got.get(key) != n:
        print(f"  {key}: {got.get(key)} loaded, {n} expected", file=sys.stderr)
sys.exit(1 if errors or any(got.get(k) != n for k, n in want.items()) else 0)
PY

echo "Installed flow-next into Antigravity CLI at $INSTALLED. Commands: /flow-next:<name> (start with /flow-next:setup in a repo)."
echo "Start flow-next sessions with: agy --settings '{\"toolPermission\":\"always-proceed\"}'"
echo "  Without it, Auto mode runs subagent shell commands where git storage is read-only and the network is off,"
echo "  so workers cannot commit or run review CLIs. It auto-approves every tool call: use it only in an environment you already trust."
