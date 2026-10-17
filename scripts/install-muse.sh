#!/bin/bash
# Install Flow-Next into Muse Code (Meta's coding agent CLI) at user scope.
#
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/flow-next.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-muse.sh \
#     && trash /tmp/flow-next-install
#
# Usage: ./scripts/install-muse.sh
#
# Muse installs Claude-format plugins as-is, but its agent definitions accept
# only Muse tool names. This script builds a temporary bundle from the canonical
# plugin (plugins/flow-next/scripts/lib/muse_bundle.py translates the agents and
# adds the Muse dispatch note), installs it with `muse plugins install`,
# approves its agent definitions, and deletes the bundle. Muse owns the
# installed copy; re-run after `git pull` to update.
#
# POSIX only, matching install-opencode.sh. Never writes Muse settings.
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
        sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    *) die "unknown argument: $1 (see --help)" ;;
esac

command -v muse >/dev/null 2>&1 || die "muse not found on PATH; install Muse Code first: https://dev.meta.ai/docs/muse-code"
command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/flow-next-muse.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
BUNDLE="$WORK/flow-next"

python3 -B "$PLUGIN_DIR/scripts/lib/muse_bundle.py" "$PLUGIN_DIR" "$BUNDLE" \
    || die "bundle build failed"
python3 -B "$BUNDLE/scripts/lib/verify_tracker_manifest.py" "$BUNDLE/scripts" \
    || die "tracker package manifest mismatch in the bundle"

muse plugins install "$BUNDLE" --scope user || die "muse plugins install failed"
muse plugins approve flow-next || die "muse plugins approve failed"

echo "Installed flow-next into Muse Code. Commands: /flow-next:<name> (start with /flow-next:setup in a repo)."
echo "Start Muse with --disable-sandbox (muse --disable-sandbox, muse exec --disable-sandbox): review CLIs cannot run inside its sandbox."
echo "Optional: muse skills user-only plan --scope built-in, so plain \"plan ...\" requests reach flow-next instead of Muse's own /plan."
if [ -d "${CODEX_HOME:-$HOME/.codex}/skills/flow-next-plan" ]; then
    echo "Note: Muse also loads the Codex install's flow-next skills from ${CODEX_HOME:-$HOME/.codex}/skills."
    echo "      To use only this install, set \"context\": {\"foreign_personal_skills\": false} in ~/.config/muse/settings.json."
fi
