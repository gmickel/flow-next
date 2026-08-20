#!/bin/bash
# Install Flow-Next into OpenCode (${XDG_CONFIG_HOME:-$HOME/.config}/opencode).
#
# One-liner install (no manual clone needed):
#   git clone --depth 1 https://github.com/gmickel/flow-next.git /tmp/flow-next-install \
#     && /tmp/flow-next-install/scripts/install-opencode.sh \
#     && rm -rf /tmp/flow-next-install
#
# Usage: ./scripts/install-opencode.sh [--dest <path>] [--force]
#
# POSIX only (no Windows .ps1 in this spec). Snapshot-of-working-tree: a COPY,
# never a symlink. Re-run after `git pull` to update. Deletions apply only to
# paths listed in the ownership manifest, never to user files outside it.
#
# Pinned OpenCode directory layout (fn-201, 2026-08-20, local opencode 1.18.19 +
# https://opencode.ai/config.json; recorded in /tmp/opencode-pins.md):
#   skills/    <root>/skills/<name>/SKILL.md
#   agents/    <root>/agents/<name>.md     (filename becomes agent name)
#   commands/  <root>/commands/<name>.md   (filename becomes /name command)
# ALL PLURAL. Skills + support dirs are copied; agents/ and commands/ are
# generated at install time by plugins/flow-next/scripts/lib/opencode_generate.py
# (never a committed OpenCode tree; canonical prose is not rewritten).
#
# What gets installed:
#   - Skills:     skills/<name>/            (canonical, as-is, minus flow-next-setup/)
#   - Support:    scripts/, templates/, references/, docs/  at the config root
#                 (two levels above any skills/<name>/SKILL.md — the existing
#                 plugin-root resolution rung, zero prose changes)
#   - Agents:     agents/flow-next-<name>.md    (generated; body byte-identical)
#   - Commands:   commands/flow-next-<name>.md  (generated stubs; uninstall
#                 verbatim; setup excluded by name)
#   - Manifest:   .flow-next-opencode-manifest  (sorted relative paths; no
#                 timestamps; no absolute paths)
#   - Hooks:      none. Never register Ralph / OpenCode JS hooks.
#   - ~/.claude/: never written.
#
# Support dirs follow the spec's derivation rule: grep-derived ${PLUGIN_ROOT}/
# and ../../ top-level segments MINUS the named exclusion list:
#   .claude-plugin/  — host manifest, not a runtime read
#   .cursor-plugin/  — host manifest
#   .codex-plugin/   — host manifest
#   codex/           — committed Codex rewrite mirror (must not land at dest)
#   skills/          — installed separately (and minus flow-next-setup/)
#   non-filesystem   — URL fragments and similar grep noise
# Result installed here: scripts, templates, references, docs.
# (Task 3 pins derived − exclusions == this list.)
#
# flow-next-setup/ is excluded: OpenCode dispatches skills by description match,
# so an installed setup SKILL is phrase-reachable and would land in setup's
# else→codex platform fallback. Setup is unsupported on OpenCode in this spec.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/plugins/flow-next"

MANIFEST_NAME=".flow-next-opencode-manifest"
# Owned support-dir names at the config root (see derivation comment above).
SUPPORT_DIRS=(scripts templates references docs)
SKIP_SKILL="flow-next-setup"

usage() {
    cat <<'EOF'
Usage: install-opencode.sh [--dest <path>] [--force] [--help]

Install flow-next into OpenCode's config directory by scattering canonical
files (skills as-is, plugin-root support dirs at the config root).

Options:
  --dest <path>  Install here instead of ${XDG_CONFIG_HOME:-$HOME/.config}/opencode
  --force        Replace unclaimed support dirs / skill dirs that already exist
  --help         Show this help

What gets installed:
  skills/<name>/     canonical skills except flow-next-setup/
  scripts/           flowctl + tracker package + lib/ (and the rest of scripts/)
  templates/         spec.md, criteria.md, ...
  references/        shared disclosure files
  docs/              plugin docs
  agents/            generated OpenCode agents (flow-next-<name>.md)
  commands/          generated slash-command stubs (uninstall verbatim; no setup)
  .flow-next-opencode-manifest
                     sorted relative paths of every installed file and directory

Pinned OpenCode directory names (2026-08-20, opencode 1.18.19,
https://opencode.ai/config.json): skills/, agents/, commands/ (all plural).

Not installed:
  flow-next-setup    unsupported on OpenCode (no command stub either)
  Ralph / hooks      OpenCode hook system is incompatible; never registered

Re-run to update the snapshot. Deletions apply only to paths listed in the
ownership manifest; user files outside those paths stay untouched.

This installer never writes into ~/.claude/.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

# True if $1 exists (including a dangling symlink).
exists() {
    [ -e "$1" ] || [ -L "$1" ]
}

# Manifest claims prefix $1 when a line is exactly that prefix or prefix/...
manifest_claims() {
    local prefix="$1"
    local mf="$2"
    if [ ! -f "$mf" ]; then
        return 1
    fi
    if grep -E -q "^${prefix}(/|$)" "$mf"; then
        return 0
    fi
    return 1
}

# Reject relative paths that could escape dest.
unsafe_relpath() {
    case "$1" in
        ""|/*)
            return 0
            ;;
    esac
    case "/$1/" in
        */../*)
            return 0
            ;;
    esac
    return 1
}

# Copy $1/ into $2/ (real-dir, --delete). rsync preferred; tar fallback.
# Excludes Python/OS cruft so a stale __pycache__ does not survive a re-run.
copy_tree() {
    local src="$1"
    local dest="$2"
    if [ ! -d "$src" ]; then
        die "source directory not found: $src"
    fi
    if exists "$dest" && [ ! -d "$dest" ]; then
        die "refusing to replace non-directory: $dest"
    fi
    mkdir -p "$dest"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete --delete-excluded \
            --exclude '__pycache__/' \
            --exclude '*.pyc' \
            --exclude '.DS_Store' \
            "$src/" "$dest/"
    else
        # Fallback without rsync: clean + tar (same contract as install-cursor.sh).
        rm -rf "$dest"
        mkdir -p "$dest"
        (cd "$src" && tar --exclude='__pycache__' --exclude='*.pyc' \
            --exclude='.DS_Store' -cf - .) | (cd "$dest" && tar -xf -)
    fi
}

# Print dest-relative paths (the prefix itself, then every file/dir under it)
# excluding __pycache__, *.pyc, .DS_Store. Byte-stable after LC_ALL=C sort.
list_tree_paths() {
    local abs="$1"
    local prefix="$2"
    exists "$abs" || return 0
    printf '%s\n' "$prefix"
    if [ -d "$abs" ]; then
        (cd "$abs" && find . \( -name '__pycache__' -o -name '*.pyc' -o -name '.DS_Store' \) -prune -o -print) \
            | sed -e '/^\.$/d' -e 's|^\./||' \
            | while IFS= read -r rel || [ -n "$rel" ]; do
                [ -n "$rel" ] || continue
                printf '%s/%s\n' "$prefix" "$rel"
            done
    fi
}

# Abort if $1 exists and is not claimed by $2, unless --force.
# A first install never deletes user-authored content to claim a path.
preflight_target() {
    local target="$1"
    local rel="$2"
    local mf="$3"
    if ! exists "$target"; then
        return 0
    fi
    if manifest_claims "$rel" "$mf"; then
        return 0
    fi
    if [ "$FORCE" -eq 1 ]; then
        echo "warning: $target exists and is not claimed by $MANIFEST_PATH; --force replacing it" >&2
        return 0
    fi
    die "$target exists and is not claimed by $MANIFEST_PATH; refusing to overwrite. Re-run with --force to replace it."
}

# Generate <dest>/agents/flow-next-<name>.md from canonical agents/*.md.
# Mapping, fail-closed cases, and schema pin live in opencode_generate.py.
generate_agents() {
    local dest="$1"
    local paths_file="$2"
    python3 -B "$PLUGIN_DIR/scripts/lib/opencode_generate.py" \
        --agents "$PLUGIN_DIR/agents" "$dest" "$paths_file" \
        || die "OpenCode agent generation failed"
}

# Generate <dest>/commands/flow-next-<name>.md stubs (uninstall verbatim;
# setup excluded by name). Roster and mapping live in opencode_generate.py.
generate_commands() {
    local dest="$1"
    local paths_file="$2"
    python3 -B "$PLUGIN_DIR/scripts/lib/opencode_generate.py" \
        --commands "$PLUGIN_DIR/commands" "$PLUGIN_DIR/skills" "$dest" "$paths_file" \
        || die "OpenCode command generation failed"
}

# --uninstall: remove exactly the manifest-listed paths plus the manifest.
# Reads the MANIFEST, never the current source tree — a skill renamed
# upstream between install and uninstall still gets cleaned. Unsafe
# relpaths abort before any removal.
uninstall_owned_paths() {
    local mf="$DEST/$MANIFEST_NAME"
    if [ ! -f "$mf" ]; then
        die "no ownership manifest at $mf; nothing to uninstall (refusing to guess paths from the source tree)"
    fi
    local sorted
    sorted="$(mktemp "${TMPDIR:-/tmp}/flow-next-opencode-un.XXXXXX")"
    LC_ALL=C sort -u "$mf" | LC_ALL=C sort -r > "$sorted"
    while IFS= read -r rel || [ -n "$rel" ]; do
        [ -n "$rel" ] || continue
        if unsafe_relpath "$rel"; then
            rm -f "$sorted"
            die "ownership manifest $mf contains an unsafe path: $rel; no paths were removed"
        fi
    done < "$sorted"
    while IFS= read -r rel || [ -n "$rel" ]; do
        [ -n "$rel" ] || continue
        local target="$DEST/$rel"
        if exists "$target"; then
            rm -rf "$target"
        fi
    done < "$sorted"
    rm -f "$sorted"
    rm -f "$mf"
    # Parent dirs (skills/, agents/, commands/) are not manifest-listed because
    # they can be shared with user content; drop them only when empty.
    for _parent in skills agents commands; do
        rmdir "$DEST/$_parent" 2>/dev/null || true
    done
    echo "Uninstalled flow-next from OpenCode ($DEST)."
    echo "Removed paths listed in the ownership manifest; other files in $DEST were left untouched."
}

FORCE=0
UNINSTALL=0
DEST=""
DEST_SET=0

while [ $# -gt 0 ]; do
    case "$1" in
        --dest)
            if [ $# -lt 2 ]; then
                die "--dest requires a path (example: --dest /tmp/opencode-dest)"
            fi
            DEST="$2"
            DEST_SET=1
            shift 2
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --uninstall)
            UNINSTALL=1
            shift
            ;;
        --)
            shift
            break
            ;;
        -*)
            die "unknown option: $1 (try --help)"
            ;;
        *)
            die "unexpected argument: $1 (try --help)"
            ;;
    esac
done

if [ "$DEST_SET" -eq 1 ]; then
    if [ -z "$DEST" ]; then
        die "--dest requires a non-empty path"
    fi
    case "$DEST" in
        -*)
            die "--dest path looks like a flag: $DEST"
            ;;
    esac
else
    DEST="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
fi

if [ "$UNINSTALL" -eq 1 ]; then
    uninstall_owned_paths
    exit 0
fi

if [ ! -d "$PLUGIN_DIR/skills" ]; then
    die "skills directory not found: $PLUGIN_DIR/skills (run this from a flow-next checkout)"
fi
if [ ! -f "$PLUGIN_DIR/scripts/flowctl" ]; then
    die "flowctl not found: $PLUGIN_DIR/scripts/flowctl (run this from a flow-next checkout)"
fi
for _dir in "${SUPPORT_DIRS[@]}"; do
    if [ ! -d "$PLUGIN_DIR/$_dir" ]; then
        die "required support dir not found: $PLUGIN_DIR/$_dir"
    fi
done

MANIFEST_PATH="$DEST/$MANIFEST_NAME"
OLD_MANIFEST=""
if [ -f "$MANIFEST_PATH" ]; then
    OLD_MANIFEST="$MANIFEST_PATH"
fi

echo "Installing flow-next into OpenCode ($DEST)..."

# Pre-flight: unclaimed support dirs (and skill dirs we are about to own).
for _dir in "${SUPPORT_DIRS[@]}"; do
    preflight_target "$DEST/$_dir" "$_dir" "$OLD_MANIFEST"
done
if exists "$DEST/skills" && [ ! -d "$DEST/skills" ]; then
    die "refusing to replace non-directory: $DEST/skills"
fi
for skill_dir in "$PLUGIN_DIR/skills"/*/; do
    [ -d "$skill_dir" ] || continue
    name="$(basename "$skill_dir")"
    if [ "$name" = "$SKIP_SKILL" ]; then
        continue
    fi
    preflight_target "$DEST/skills/$name" "skills/$name" "$OLD_MANIFEST"
done

mkdir -p "$DEST"

# Skills (canonical as-is), excluding flow-next-setup/.
mkdir -p "$DEST/skills"
SKILL_COUNT=0
for skill_dir in "$PLUGIN_DIR/skills"/*/; do
    [ -d "$skill_dir" ] || continue
    name="$(basename "$skill_dir")"
    if [ "$name" = "$SKIP_SKILL" ]; then
        echo "skipping $PLUGIN_DIR/skills/$SKIP_SKILL (setup is not supported on OpenCode)"
        continue
    fi
    copy_tree "$skill_dir" "$DEST/skills/$name"
    SKILL_COUNT=$((SKILL_COUNT + 1))
done

# Plugin-root support dirs at the config root.
for _dir in "${SUPPORT_DIRS[@]}"; do
    copy_tree "$PLUGIN_DIR/$_dir" "$DEST/$_dir"
done

# Generated agents/commands (fail closed: a generation error aborts install).
GEN_PATHS="$(mktemp "${TMPDIR:-/tmp}/flow-next-opencode-gen.XXXXXX")"
generate_agents "$DEST" "$GEN_PATHS"
generate_commands "$DEST" "$GEN_PATHS"

# Build the new ownership manifest from what we actually installed (+ generated).
NEW_MANIFEST="$(mktemp "${TMPDIR:-/tmp}/flow-next-opencode-mf.XXXXXX")"
{
    for skill_dir in "$DEST/skills"/*/; do
        [ -d "$skill_dir" ] || continue
        name="$(basename "$skill_dir")"
        # Only list skill dirs that came from this snapshot (skip user skills
        # and the excluded setup skill, even if a previous copy left it).
        if [ "$name" = "$SKIP_SKILL" ]; then
            continue
        fi
        if [ ! -d "$PLUGIN_DIR/skills/$name" ]; then
            continue
        fi
        list_tree_paths "$DEST/skills/$name" "skills/$name"
    done
    for _dir in "${SUPPORT_DIRS[@]}"; do
        list_tree_paths "$DEST/$_dir" "$_dir"
    done
    if [ -s "$GEN_PATHS" ]; then
        cat "$GEN_PATHS"
    fi
} | LC_ALL=C sort -u > "$NEW_MANIFEST"
rm -f "$GEN_PATHS"

if [ ! -s "$NEW_MANIFEST" ]; then
    rm -f "$NEW_MANIFEST"
    die "ownership manifest would be empty after install into $DEST (source tree produced no paths)"
fi

# Drop paths the previous manifest owned that this snapshot no longer ships.
# Reads the OLD manifest, never the source tree — a skill renamed upstream
# between installs still gets cleaned. Longest-first via reverse lex order so
# children go before parents. (Not a pipeline: die must abort the installer,
# not a subshell.)
if [ -n "$OLD_MANIFEST" ]; then
    SORTED_OLD="$(mktemp "${TMPDIR:-/tmp}/flow-next-opencode-old.XXXXXX")"
    STALE="$(mktemp "${TMPDIR:-/tmp}/flow-next-opencode-stale.XXXXXX")"
    LC_ALL=C sort -u "$OLD_MANIFEST" > "$SORTED_OLD"
    # comm collates with LC_COLLATE; must match the C sort that built both files.
    LC_ALL=C comm -23 "$SORTED_OLD" "$NEW_MANIFEST" | LC_ALL=C sort -r > "$STALE"
    rm -f "$SORTED_OLD"
    while IFS= read -r rel || [ -n "$rel" ]; do
        [ -n "$rel" ] || continue
        if unsafe_relpath "$rel"; then
            rm -f "$STALE" "$NEW_MANIFEST"
            die "ownership manifest $OLD_MANIFEST contains an unsafe path: $rel"
        fi
        target="$DEST/$rel"
        if exists "$target"; then
            rm -rf "$target"
        fi
    done < "$STALE"
    rm -f "$STALE"
fi

# Atomic replace of the dest-root manifest (not listed in itself).
mv "$NEW_MANIFEST" "$MANIFEST_PATH"

# fn-139.5: fail closed if the tracker package/verifier did not land, then
# verify the installed scripts/ dir (same contract as install-cursor.sh).
if [ ! -f "$DEST/scripts/flowctl_tracker/MANIFEST.json" ] \
    || [ ! -f "$DEST/scripts/lib/verify_tracker_manifest.py" ]; then
    die "flowctl_tracker manifest/verifier missing after copy under $DEST/scripts - corrupt checkout/install; re-clone and re-run"
fi
if ! python3 "$DEST/scripts/lib/verify_tracker_manifest.py" "$DEST/scripts"; then
    die "flowctl_tracker manifest verification FAILED under $DEST/scripts - install is corrupt; re-clone and re-run"
fi
echo ""
echo "Installed. OpenCode discovers components from $DEST:"
echo "  skills:    $SKILL_COUNT (flow-next-setup excluded)"
echo "  scripts:   $DEST/scripts"
echo "  templates: $DEST/templates"
echo "  references: $DEST/references"
echo "  docs:      $DEST/docs"
echo "  agents:    $DEST/agents"
echo "  commands:  $DEST/commands"
echo "  manifest:  $MANIFEST_PATH"
echo ""
echo "Not installed: setup (unsupported), Ralph/hooks."
echo ""
echo "Next steps:"
echo "  1. Restart OpenCode (or start a new session) so it rescans $DEST."
echo "  2. /flow-next:setup is NOT supported on OpenCode — run flowctl init"
echo "     and set config keys by hand (see plugins/flow-next/docs/platforms.md"
echo "     once that section ships)."
echo "  3. Drive the workflow with the flat slash form: /flow-next-<name>"
echo "     (not /flow-next:<name>)."
echo ""
echo "Re-run this script after 'git pull' to update the snapshot."
echo "Owned paths are listed in $MANIFEST_PATH."
