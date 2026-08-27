#!/bin/bash
# Generate pre-built Codex files from canonical skills/ and agents/ sources.
# Output: plugins/flow-next/codex/{skills/,agents/}
# (No hooks.json: Ralph hooks are opt-in via ralph-init project settings, not the mirror.)
#
# Idempotent — running twice produces identical output.
# Run after modifying skills/ or agents/ and commit the result.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$REPO_ROOT/plugins/flow-next"
CODEX_DIR="$PLUGIN_DIR/codex"
SRC_SKILLS="$PLUGIN_DIR/skills"
SRC_AGENTS="$PLUGIN_DIR/agents"

# Model defaults (same as install-codex.sh).
# Mirror-regen only: env > baseline. The fn-115 role map is gone (fn-195) -
# routing is a preference the user writes in their instruction file, not
# config flowctl stores; env still wins for one-shot overrides.
# These baselines ARE the shipped mirror truth (fn-195.5 review P1): a regen
# with no env must reproduce the committed mirror byte-for-byte. Bump them
# deliberately (with a CHANGELOG line), never by exporting env at sync time.
_SCOUT_INTELLIGENT_BASELINE="gpt-5.6-terra"
_SCOUT_FAST_BASELINE="gpt-5.6-luna"

CODEX_MODEL_INTELLIGENT="${CODEX_MODEL_INTELLIGENT:-$_SCOUT_INTELLIGENT_BASELINE}"
CODEX_MODEL_FAST="${CODEX_MODEL_FAST:-$_SCOUT_FAST_BASELINE}"
# Default reasoning effort for scout/analyst/editorial subagents.
# Review-shaped agents (quality-auditor) override to a higher tier — see reasoning_effort_for().
CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-medium}"
CODEX_REASONING_EFFORT_AUDITOR="${CODEX_REASONING_EFFORT_AUDITOR:-high}"
# fn-97: OPT-IN worker pin for the Codex mirror. Default is EMPTY = the worker
# keeps `inherit` (the Codex user's session model rules, same as the Claude-side
# worker) - flow-next never hardcodes a model opinion into generated config;
# routing opinions belong to the prompted layer (the AGENTS.md model table).
# To pin (eval-motivated recommendation: terra-medium matched gpt-5.6-sol
# hidden-suite correctness at ~2/3 wall-clock on frontier-authored specs,
# 2026-07-14 eval, n=3), set at sync time:
#   CODEX_MODEL_WORKER=gpt-5.6-terra CODEX_REASONING_EFFORT_WORKER=medium ./scripts/sync-codex.sh
CODEX_MODEL_WORKER="${CODEX_MODEL_WORKER:-}"
CODEX_REASONING_EFFORT_WORKER="${CODEX_REASONING_EFFORT_WORKER:-}"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────────────

# Scouts that need full intelligence (reasoning/judgment, not just scanning).
# repo/context/docs/github/practice were opus-on-Claude, downgraded to sonnet after a
# verified A/B (fn-84 fleet review — sonnet held quality). Codex has only INTELLIGENT/FAST,
# and FAST (gpt-5.4-mini) was NOT tested, so keep them INTELLIGENT (gpt-5.5) here = no Codex
# regression; the Claude-side opus→sonnet cut is the verified saving.
INTELLIGENT_SCOUTS="spec-scout agents-md-scout docs-gap-scout repo-scout docs-scout github-scout practice-scout plan-sync flow-gap-analyst"
# Agents that stay on opus in Claude Code (bug/gap detection = horsepower; failures invisible)
OPUS_AGENTS="quality-auditor"

rename_agent() {
  case "$1" in
    claude-md-scout) echo "agents-md-scout" ;;
    *) echo "$1" ;;
  esac
}

map_model() {
  local claude_model="$1" agent_name="${2:-}"
  # fn-97: worker pin is OPT-IN - only overrides `inherit` when the user set
  # CODEX_MODEL_WORKER at sync time (see above). Everything else keeps the
  # FAST/INTELLIGENT tier mapping below.
  if [ "$agent_name" = "worker" ] && [ -n "$CODEX_MODEL_WORKER" ]; then
    echo "$CODEX_MODEL_WORKER"
    return
  fi
  case "$claude_model" in
    opus|claude-opus-*)
      echo "$CODEX_MODEL_INTELLIGENT" ;;
    sonnet|claude-sonnet-*)
      if echo "$INTELLIGENT_SCOUTS" | grep -qw "$agent_name" 2>/dev/null; then
        echo "$CODEX_MODEL_INTELLIGENT"
      else
        echo "$CODEX_MODEL_FAST"
      fi ;;
    haiku|claude-haiku-*)
      echo "$CODEX_MODEL_FAST" ;;
    inherit|"")
      echo "" ;;
    *)
      echo "$CODEX_MODEL_INTELLIGENT" ;;
  esac
}

model_supports_reasoning() {
  case "$1" in
    *mini*|*spark*) return 1 ;;
    *) return 0 ;;
  esac
}

# Per-agent reasoning effort. Review-shaped agents (quality-auditor) need
# higher reasoning than scout/editorial agents — they're a second pair of
# eyes on uncommitted changes, so undershooting risks missed regressions.
reasoning_effort_for() {
  case "$1" in
    quality-auditor) echo "$CODEX_REASONING_EFFORT_AUDITOR" ;;
    worker)          echo "${CODEX_REASONING_EFFORT_WORKER:-$CODEX_REASONING_EFFORT}" ;;
    *)               echo "$CODEX_REASONING_EFFORT" ;;
  esac
}

# Determine sandbox mode for an agent
sandbox_for() {
  local name="$1"
  case "$name" in
    worker|plan-sync) echo "workspace-write" ;;
    *)                echo "read-only" ;;
  esac
}

# Nickname candidates for scouts (better parallel UX)
nicknames_for() {
  local name="$1"
  case "$name" in
    build-scout)          echo '["Foreman", "Constructor", "Assembler"]' ;;
    agents-md-scout)      echo '["Archivist", "Scribe", "Librarian"]' ;;
    docs-gap-scout)       echo '["Inspector", "Reviewer", "Auditor"]' ;;
    docs-scout)           echo '["Scholar", "Researcher", "Curator"]' ;;
    env-scout)            echo '["Provisioner", "Configurer", "Warden"]' ;;
    spec-scout)           echo '["Strategist", "Planner", "Coordinator"]' ;;
    github-scout)         echo '["Tracker", "Monitor", "Watcher"]' ;;
    memory-scout)         echo '["Chronicler", "Historian", "Recorder"]' ;;
    observability-scout)  echo '["Sentinel", "Observer", "Beacon"]' ;;
    practice-scout)       echo '["Mentor", "Guide", "Counselor"]' ;;
    repo-scout)           echo '["Explorer", "Surveyor", "Ranger"]' ;;
    security-scout)       echo '["Guardian", "Protector", "Shield"]' ;;
    testing-scout)        echo '["Verifier", "Validator", "Tester"]' ;;
    tooling-scout)        echo '["Mechanic", "Technician", "Tinker"]' ;;
    workflow-scout)       echo '["Automator", "Orchestrator", "Dispatcher"]' ;;
    flow-gap-analyst)     echo '["Analyst", "Evaluator", "Diagnostician"]' ;;
    quality-auditor)      echo '["Auditor", "Critic", "Appraiser"]' ;;
    *) echo "" ;;
  esac
}

is_scout_or_analyst() {
  local name="$1"
  case "$name" in
    *-scout|flow-gap-analyst|quality-auditor) return 0 ;;
    *) return 1 ;;
  esac
}

# ─── Clean & recreate ────────────────────────────────────────────────────────

echo -e "${BLUE}Cleaning codex/ directory...${NC}"
rm -rf "$CODEX_DIR"
mkdir -p "$CODEX_DIR/skills" "$CODEX_DIR/agents"

# ─── 1. Copy & patch skills ──────────────────────────────────────────────────

echo -e "${BLUE}Generating skills...${NC}"
skill_count=0

for skill_dir in "$SRC_SKILLS"/*/; do
  [ -d "$skill_dir" ] || continue
  skill=$(basename "$skill_dir")
  cp -R "${skill_dir%/}" "$CODEX_DIR/skills/"
  skill_count=$((skill_count + 1))
done

# Mirror canonical templates dir (R20: codex picks up templates/spec.md). Skills
# cross-link `../../templates/spec.md` from `skills/<name>/<file>.md` — after
# this copy the same relative path resolves to the mirrored copy at
# `codex/templates/spec.md` (2 levels up from `codex/skills/<name>/`).
if [ -d "$PLUGIN_DIR/templates" ]; then
  cp -R "$PLUGIN_DIR/templates" "$CODEX_DIR/"
fi

# Mirror canonical references dir (fn-62.2: shared disclosure files such as
# references/html-artifacts.md, loaded by skills only when the matching config
# gate is on). Same shape as the templates copy above: skills cite the file by
# repo-relative path; in the mirror, `../../references/<name>.md` from
# `codex/skills/<name>/<file>.md` resolves to `codex/references/<name>.md`.
# Reference files are tool-name-agnostic by contract, so NO rewrite pass below
# touches them — the mirror copy must stay byte-identical to canonical.
if [ -d "$PLUGIN_DIR/references" ]; then
  cp -R "$PLUGIN_DIR/references" "$CODEX_DIR/"
fi

# Mirror canonical docs dir (fn-202 / #363 codex P2 + P1: skill prose
# cross-links `../../docs/<name>.md` — pipeline-variations.md, ralph.md,
# flowctl.md, the reach/ pages...). The mirror carries them under the
# flow-next-OWNED namespace `codex/docs/flow-next/` (never loose under
# `codex/docs/`): install-codex.sh replaces ONLY `$CODEX_HOME/docs/flow-next/`
# wholesale, so an install can never delete or overwrite a user- or
# other-package-owned `$CODEX_HOME/docs/` file such as `docs/README.md` or
# `docs/reach/` (#363 codex P1, round 4). The docs-link transform below adds
# the matching `flow-next/` segment to mirror skill prose, so links resolve in
# BOTH layouts — in-repo (`codex/skills/<skill>/` → `codex/docs/flow-next/`)
# and installed (`$CODEX_HOME/skills/<skill>/` → `$CODEX_HOME/docs/flow-next/`).
# Markdown only, subdirs included (reach/ pages are link targets): docs are
# host-agnostic prose, so no OTHER rewrite pass touches them.
if [ -d "$PLUGIN_DIR/docs" ]; then
  mkdir -p "$CODEX_DIR/docs"
  cp -R "$PLUGIN_DIR/docs" "$CODEX_DIR/docs/flow-next"
  find "$CODEX_DIR/docs" -type f ! -name '*.md' -delete
fi

# --- Docs-mirror internal links: close the link universe (#363 codex P2, round 5) ---
# The copied docs pages carry canonical-relative links written for
# `plugins/flow-next/docs/<file>` — one directory shallower than their mirror
# location `codex/docs/flow-next/<file>` — so every link that leaves the docs
# dir dangles both in-repo and installed. Rewrite by TARGET CLASS, depth-aware
# per file location (top-level pages vs `reach/` pages), so no further
# link-class finding is possible:
#   1. Same-dir doc links (`](running-lean.md`, `](reach/x.md`,
#      `](../orchestration.md` from reach/) already resolve inside
#      `docs/flow-next/` — untouched.
#   2. Links up-and-into INSTALLED trees (`skills/`, `templates/`,
#      `references/`) gain one `../` — the mirror (and $CODEX_HOME) nests docs
#      one level deeper than canonical.
#   3. Links to targets OUTSIDE the installed universe (repo root, the plugin
#      README, `schema/`, `tests/`, the non-markdown `ci-workflow-example.yml`
#      the md-only filter above deletes) become absolute canonical GitHub URLs
#      computed from the CANONICAL docs location — they resolve everywhere and
#      never dangle on disk.
# Anchored on the exact canonical prefixes; no rewritten output re-matches any
# pattern, and the mirror is fully regenerated each run, so sync twice yields a
# zero second-run diff. The link-closure validation guard below hard-fails on
# any docs-mirror link that neither resolves on disk nor is an absolute URL.
DOCS_BLOB_URL="https://github.com/gmickel/flow-next/blob/main"
for df in "$CODEX_DIR/docs/flow-next"/*.md; do
  [ -f "$df" ] || continue
  sed -i.bak \
    -e "s|](\.\./\.\./\.\./|](${DOCS_BLOB_URL}/|g" \
    -e "s|](\.\./README\.md|](${DOCS_BLOB_URL}/plugins/flow-next/README.md|g" \
    -e "s|](\.\./schema/|](${DOCS_BLOB_URL}/plugins/flow-next/schema/|g" \
    -e "s|](\.\./tests/|](${DOCS_BLOB_URL}/plugins/flow-next/tests/|g" \
    -e "s|](ci-workflow-example\.yml|](${DOCS_BLOB_URL}/plugins/flow-next/docs/ci-workflow-example.yml|g" \
    -e 's|](\.\./skills/|](../../skills/|g' \
    -e 's|](\.\./templates/|](../../templates/|g' \
    -e 's|](\.\./references/|](../../references/|g' \
    "$df"
  rm -f "${df}.bak"
done
# reach/ pages sit one level deeper still — same classes, +1 depth.
for df in "$CODEX_DIR/docs/flow-next/reach"/*.md; do
  [ -f "$df" ] || continue
  sed -i.bak \
    -e "s|](\.\./\.\./\.\./\.\./|](${DOCS_BLOB_URL}/|g" \
    -e "s|](\.\./\.\./README\.md|](${DOCS_BLOB_URL}/plugins/flow-next/README.md|g" \
    -e "s|](\.\./\.\./schema/|](${DOCS_BLOB_URL}/plugins/flow-next/schema/|g" \
    -e "s|](\.\./\.\./tests/|](${DOCS_BLOB_URL}/plugins/flow-next/tests/|g" \
    -e 's|](\.\./\.\./skills/|](../../../skills/|g' \
    -e 's|](\.\./\.\./templates/|](../../../templates/|g' \
    -e 's|](\.\./\.\./references/|](../../../references/|g' \
    "$df"
  rm -f "${df}.bak"
done

# Image destinations need raw bytes, not the blob HTML page (#363 codex P3,
# round 10): a mirrored `![...](.../blob/main/...png)` renders broken in an
# installed viewer. Convert image-extension blob URLs to raw across the docs
# mirror; idempotent (a raw URL no longer matches blob/).
find "$CODEX_DIR/docs/flow-next" -name '*.md' -type f | while read -r df; do
  sed -i.bak -E 's|(github\.com/gmickel/flow-next)/blob/(main/[^)]+\.(png\|jpe?g\|gif\|svg\|webp))|\1/raw/\2|g' "$df"
  rm -f "${df}.bak"
done

# --- Docs-mirror invocation banner (#363 codex P2, rounds 7-8) ---------------
# The mirrored docs pages mention `/flow-next:<cmd>` in examples and prose. A
# REWRITE cannot work here: docs contain host-SPECIFIC examples (`claude -p
# "/flow-next:ralph-init"`, `/loop` recipes) where `$flow-next-*` is wrong and
# even dangerous (`$flow` expands inside double quotes in bash). Two attempts
# proved any rewrite/exclude-list is an enumeration racing the next page. The
# invariant instead: docs prose ships VERBATIM, and every mirrored page opens
# with one disclosure line mapping slash syntax to this host. Guard hard-fails
# on any page missing the banner.
DOCS_CODEX_BANNER='> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts'\'' own syntax and are quoted verbatim — do not convert them.'
find "$CODEX_DIR/docs/flow-next" -name '*.md' -type f | while read -r df; do
  awk -v banner="$DOCS_CODEX_BANNER" 'NR==1{print; print ""; print banner; print ""; next} {print}' "$df" > "${df}.tmp" && mv "${df}.tmp" "$df"
done
DOCS_BANNER_MISSING=$(grep -rL 'Codex install note:' "$CODEX_DIR/docs/flow-next" --include='*.md' 2>/dev/null | head -5) || true
if [ -n "$DOCS_BANNER_MISSING" ]; then
  echo -e "  ${RED}X${NC} docs-mirror pages missing the Codex invocation banner:"
  echo "$DOCS_BANNER_MISSING"
  exit 1
fi

# --- flow-next-drive: Codex Browser-Use preface ──────────────────────────────
# The canonical skill is `flow-next-drive` (no `@browser` collision — the old
# `browser` → `agent-browser` rename is gone; the copy loop above already
# mirrors the canonical dir name). We still want a Codex-only note: Codex
# desktop bundles a narrow-scope Browser Use plugin, and users should know when
# to delegate to it vs. drive with this skill. Inject that preface after the
# frontmatter; canonical (Claude/Droid) stays unchanged.
drive_skill="$CODEX_DIR/skills/flow-next-drive/SKILL.md"
if [ -f "$drive_skill" ]; then
  # Insert Codex-specific preface after the frontmatter block.
  awk '
    /^---$/ { fm++; print; next }
    fm == 2 && !inserted {
      print ""
      print "> **Codex note — Browser Use vs this skill:** Codex **desktop** (v0.124+) bundles a **Browser Use** plugin (invoke `$browser-use <task>`) controlling its in-app browser. Scope is narrow: `localhost`, `127.0.0.1`, `::1`, `file://`, current in-app tab. No cookies, no auth, no extensions, no production sites, no Electron apps, no mobile sims. For those narrow cases, delegate: use `$browser-use` directly, or just describe the task in prose (Codex routes natural-language plugin calls). Use **this skill** (the prose triggers listed above — `check the page`, `verify UI`, `test this app`, etc.) for everything outside that scope — production sites, authenticated flows, cookies/saved sessions, Electron / native apps, iOS Simulator, proxies, headed browsers, video recording, visual diff. In **Codex CLI** (no desktop app, no in-app browser), always use this skill — Browser Use is not available there."
      print ""
      inserted = 1
    }
    { print }
  ' "$drive_skill" > "${drive_skill}.tmp" && mv "${drive_skill}.tmp" "$drive_skill"
fi

# --- PATH patches (all .md files) ---
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  # Rewrite FLOWCTL assignment to the runtime CODEX_HOME form.
  # Inside Codex, neither DROID_PLUGIN_ROOT nor CLAUDE_PLUGIN_ROOT is ever set —
  # CODEX_HOME (defaulting to $HOME/.codex) resolves. The old
  # `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}` chain was dead
  # code in the mirror. See fn-48.1 (R4a).
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl|${CODEX_HOME:-$HOME/.codex}/scripts/flowctl|g' \
    -e 's|FLOWCTL="$HOME/.codex/scripts/flowctl"|FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"|g' \
    "$f"

  # fn-48.6: canonical files now use a once-per-skill `PLUGIN_ROOT` prelude
  # (e.g. flow-next-ralph-init/SKILL.md) to collapse 10+ inline expansions.
  # Rewrite the PLUGIN_ROOT assignment to the runtime Codex form so subsequent
  # `$PLUGIN_ROOT/...` references resolve. Then path-remap specific subtrees
  # that have different on-disk layouts in the Codex install (templates land
  # at `~/.codex/templates/<skill>` rather than `~/.codex/skills/<skill>/templates`).
  sed -i.bak \
    -e 's|PLUGIN_ROOT="\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}"|PLUGIN_ROOT="${CODEX_HOME:-$HOME/.codex}"|g' \
    "$f"

  # fn-197: no fallback injection here. Every canonical FLOWCTL preamble now
  # carries all three rungs itself (env var → derived plugin root → .flow/bin),
  # and only rung 1 is rewritten above — rungs 2 and 3 flow into the mirror
  # untouched. The old injector keyed on exact next-line equality with the
  # rung-3 string and would inject a DUPLICATE `.flow/bin` rung now that rung 2
  # sits between them. The paired validation guard below asserts the mirrored
  # chain instead.

  # Template/script path patches — both legacy inline form and the new
  # fn-48.6 `$PLUGIN_ROOT/...` consolidated form.
  sed -i.bak \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-ralph-init/templates|${CODEX_HOME:-$HOME/.codex}/templates/flow-next-ralph-init|g' \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-worktree-kit/scripts|${CODEX_HOME:-$HOME/.codex}/scripts|g' \
    -e 's|\$PLUGIN_ROOT/skills/flow-next-ralph-init/templates|${CODEX_HOME:-$HOME/.codex}/templates/flow-next-ralph-init|g' \
    -e 's|\$PLUGIN_ROOT/skills/flow-next-worktree-kit/scripts|${CODEX_HOME:-$HOME/.codex}/scripts|g' \
    -e 's|\${DROID_PLUGIN_ROOT:-\${CLAUDE_PLUGIN_ROOT}}/skills/|${CODEX_HOME:-$HOME/.codex}/skills/|g' \
    -e 's|\$PLUGIN_ROOT/skills/|${CODEX_HOME:-$HOME/.codex}/skills/|g' \
    "$f"
  # The two generic /skills/ rules above are a catch-all for skill-local asset
  # paths (e.g. resolve-pr's SCRIPTS dir) — install-codex.sh copies each skill
  # dir wholesale to CODEX_HOME/skills/, so that root always resolves. Specific
  # destinations (ralph-init templates, worktree-kit scripts) are rewritten
  # first and therefore win. $HOME (not ~) so the path expands inside quotes.

  sed -i.bak \
    -e 's|AGENTS_SRC="$HOME/.codex/agents"|AGENTS_SRC="${CODEX_HOME:-$HOME/.codex}/agents"|g' \
    -e 's|or ~/.codex/agents/|or ${CODEX_HOME:-$HOME/.codex}/agents/|g' \
    -e 's|\.factory-plugin/plugin\.json|.claude-plugin/plugin.json|g' \
    "$f"

  rm -f "${f}.bak"
done

# --- Relative docs links (all skill .md files): add the owned namespace ---
# Canonical `](../../docs/...)` (skill-root files) / `](../../../docs/...)`
# (references/ files) links gain a `flow-next/` segment in the mirror: the docs
# mirror above lives at `codex/docs/flow-next/`, and install-codex.sh replaces
# ONLY that owned dir under `$CODEX_HOME/docs/` — so the namespaced link depth
# resolves in-repo AND installed, and an install can never touch a non-owned
# `$CODEX_HOME/docs/` file (#363 codex P1, round 4). The two rules are anchored
# on the exact canonical depths; canonical prose never contains
# `docs/flow-next/` and the mirror is fully regenerated from canonical each
# run, so sync twice yields a zero second-run diff. The validation block below
# hard-fails on a double-applied segment, on any docs link left un-namespaced,
# and on any docs link that does not resolve on disk.
# The first-round depth-aware rewrite (+1 `../`) is deliberately GONE: it made
# links resolve in the repo tree only, and dangle one level too high once
# installed (#363 codex P2, round 3).
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  sed -i.bak \
    -e 's|](\.\./\.\./docs/|](../../docs/flow-next/|g' \
    -e 's|](\.\./\.\./\.\./docs/|](../../../docs/flow-next/|g' \
    "$f"
  rm -f "${f}.bak"
done

# --- Actionable next-step invocations → Codex command names (fn-202 / #363 P2) ---
# The capture/plan footer templates emit copy-pasteable next-step commands
# (`Recommended next:` line + `Next:` menu) and the surrounding judgment prose
# names the legal targets. On Codex, commands resolve as `$flow-next-<cmd>` —
# via dropdown / `$flow-next-*` / implicit invocation (docs/platforms.md), never
# `/flow-next:<cmd>` — so these ACTIONABLE surfaces get the same treatment as
# the impl-review invocations below and phases.md's `Next:` line above. Passive
# doc mentions in the same files (e.g. "`/flow-next:plan` does the breakdown
# later", the verbatim-pinned R25 suggestion) stay untouched per the existing
# rule — every pattern here is anchored to the actionable surface's own text.
# Idempotent: no output ever re-matches a `/flow-next:` pattern. .bak cleanup
# per file, same as every sed pass in this script.
#
# fn-205.5 (#364) widened the roster: make-pr's success footer, interview's
# suggest-next block + write-back suggestions, prospect's promote menu +
# reply-parsing suggestions, chart's capture handoff + shape-B/frontier
# closers, audit's legacy-skip remediation lines, and guide's routing-matrix
# route column are all copy-pasteable closer output and ride the same pass.
# Each new pattern stays anchored to its surface's own text; a reworded
# literal must move its anchor in the same change (the closer-roster guard
# below fails the sync otherwise). Deliberate exclusion: prospect's
# `**Next step:** /flow-next:interview` artifact template line documents what
# flowctl's write_prospect_artifact emits verbatim on every host — rewriting
# the doc would mis-describe the artifact; presentation is governed by the
# canonical files' host-command-form clause.
for nf in \
  "$CODEX_DIR/skills/flow-next-capture/workflow.md" \
  "$CODEX_DIR/skills/flow-next-capture/references/rewrite-mode.md" \
  "$CODEX_DIR/skills/flow-next-capture/references/split-proposal.md" \
  "$CODEX_DIR/skills/flow-next-plan/references/next-steps-menu.md" \
  "$CODEX_DIR/skills/flow-next-make-pr/create-and-finalize.md" \
  "$CODEX_DIR/skills/flow-next-interview/SKILL.md" \
  "$CODEX_DIR/skills/flow-next-interview/references/write-back.md" \
  "$CODEX_DIR/skills/flow-next-prospect/workflow.md" \
  "$CODEX_DIR/skills/flow-next-chart/references/briefing-and-reopen.md" \
  "$CODEX_DIR/skills/flow-next-chart/references/chart-mode.md" \
  "$CODEX_DIR/skills/flow-next-audit/SKILL.md" \
  "$CODEX_DIR/skills/flow-next-audit/workflow.md" \
  "$CODEX_DIR/skills/flow-next-guide/SKILL.md"; do
  [ -f "$nf" ] || continue
  sed -i.bak \
    -e 's|Recommended next: /flow-next:<stage>|Recommended next: $flow-next-<stage>|g' \
    -e 's|^  /flow-next:\([a-z-]*\) <SPEC_ID>|  $flow-next-\1 <SPEC_ID>|' \
    -e 's|may need /flow-next:sync to align|may need $flow-next-sync to align|g' \
    -e 's|`/flow-next:\([a-z-]*\) fn-N-slug`|`$flow-next-\1 fn-N-slug`|g' \
    -e 's|Parked unknowns lean `/flow-next:interview`|Parked unknowns lean `$flow-next-interview`|g' \
    -e 's|design risk lean `/flow-next:plan`|design risk lean `$flow-next-plan`|g' \
    -e 's|still leans `/flow-next:plan`|still leans `$flow-next-plan`|g' \
    -e 's|Legal targets are ONLY `/flow-next:interview`, `/flow-next:plan`|Legal targets are ONLY `$flow-next-interview`, `$flow-next-plan`|g' \
    -e 's|Same legal targets (`/flow-next:interview`, `/flow-next:plan`|Same legal targets (`$flow-next-interview`, `$flow-next-plan`|g' \
    -e 's|`/flow-next:guide` with a "signals conflict" reason|`$flow-next-guide` with a "signals conflict" reason|g' \
    -e 's|`/flow-next:guide` on genuinely conflicting signals|`$flow-next-guide` on genuinely conflicting signals|g' \
    -e 's|(routing to `/flow-next:work`)|(routing to `$flow-next-work`)|g' \
    -e 's|recommend `/flow-next:plan-review`|recommend `$flow-next-plan-review`|g' \
    -e 's|; /flow-next:interview <id> can still split later|; $flow-next-interview <id> can still split later|g' \
    -e 's|consider /flow-next:interview <id> after capture lands|consider $flow-next-interview <id> after capture lands|g' \
    -e 's|Consider reviewing before /flow-next:plan to avoid re-solving|Consider reviewing before $flow-next-plan to avoid re-solving|g' \
    -e 's|Reviewer feedback → /flow-next:resolve-pr|Reviewer feedback → $flow-next-resolve-pr|g' \
    -e 's|Body inspection → /flow-next:make-pr|Body inspection → $flow-next-make-pr|g' \
    -e 's|Reviewer should run: /flow-next:resolve-pr|Reviewer should run: $flow-next-resolve-pr|g' \
    -e 's|re-run /flow-next:make-pr (skill detects the existing branch and re-tries)|re-run $flow-next-make-pr (skill detects the existing branch and re-tries)|g' \
    -e 's|An OPEN PR exists. /flow-next:resolve-pr addresses review feedback|An OPEN PR exists. $flow-next-resolve-pr addresses review feedback|g' \
    -e 's|→ `/flow-next:plan fn-N`|→ `$flow-next-plan fn-N`|g' \
    -e 's|→ `/flow-next:work fn-N` (or more interview|→ `$flow-next-work fn-N` (or more interview|g' \
    -e 's|→ `/flow-next:work fn-N.M`|→ `$flow-next-work fn-N.M`|g' \
    -e 's|→ `/flow-next:plan <file>`|→ `$flow-next-plan <file>`|g' \
    -e 's|`/flow-next:visual fn-N` for a spec input|`$flow-next-visual fn-N` for a spec input|g' \
    -e 's|`/flow-next:visual fn-N.M` for a task input|`$flow-next-visual fn-N.M` for a task input|g' \
    -e 's|`/flow-next:visual <file-path>` for the file input|`$flow-next-visual <file-path>` for the file input|g' \
    -e 's|Run `/flow-next:plan fn-N` to research|Run `$flow-next-plan fn-N` to research|g' \
    -e 's|then suggest `/flow-next:plan`.|then suggest `$flow-next-plan`.|g' \
    -e 's|instead: `/flow-next:interview <spec-id>`|instead: `$flow-next-interview <spec-id>`|g' \
    -e 's|suggest `/flow-next:plan <file>` to create spec + tasks|suggest `$flow-next-plan <file>` to create spec + tasks|g' \
    -e 's|(ask /flow-next:interview what to refine)|(ask $flow-next-interview what to refine)|g' \
    -e 's|Run /flow-next:chart on the selected survivor|Run $flow-next-chart on the selected survivor|g' \
    -e 's|Run /flow-next:interview <spec-or-task-id> to refine|Run $flow-next-interview <spec-or-task-id> to refine|g' \
    -e 's|running `/flow-next:capture .flow/charts/|running `$flow-next-capture .flow/charts/|g' \
    -e 's|Recommend `/flow-next:capture` or authoring|Recommend `$flow-next-capture` or authoring|g' \
    -e 's|separate `/flow-next:chart <id>` (or pinned) invocations|separate `$flow-next-chart <id>` (or pinned) invocations|g' \
    -e 's|recommends `/flow-next:memory-migrate` first|recommends `$flow-next-memory-migrate` first|g' \
    -e 's|`/flow-next:memory-migrate` first to make these auditable|`$flow-next-memory-migrate` first to make these auditable|g' \
    -e 's@| `/flow-next:\([a-z-]*\)`@| `$flow-next-\1`@g' \
    "$nf"
  rm -f "${nf}.bak"
done

# --- STRUCTURAL: Task tool → agent invocation ---

# flow-next-work: phases.md + its reached-path references (wave-join.md,
# host-deferred-review.md carry the same actionable invocations post branch-disclosure).
# The work-rolling beta's scheduler reference carries the same actionable
# per-task impl-review invocation (fn-203 Phase B), so it rides the same pass.
for wf in "$CODEX_DIR/skills/flow-next-work/phases.md" "$CODEX_DIR"/skills/flow-next-work/references/*.md "$CODEX_DIR"/skills/flow-next-work-rolling/references/*.md; do
  [ -f "$wf" ] || continue
  # Actionable impl-review invocations must use the Codex skill name. Passive
  # /flow-next: mentions elsewhere stay.
  sed -i.bak \
    -e 's|`/flow-next:impl-review <task-id> --base \$BASE_COMMIT --review=host`|`$flow-next-impl-review <task-id> --base $BASE_COMMIT --review=host`|g' \
    -e 's|`/flow-next:impl-review <task-id> --base <task-normalized-integrated-base> --review=<backend>`|`$flow-next-impl-review <task-id> --base <task-normalized-integrated-base> --review=<backend>`|g' \
    "$wf"
  rm -f "${wf}.bak"
done

phases="$CODEX_DIR/skills/flow-next-work/phases.md"
if [ -f "$phases" ]; then

  # Replace section 3c with agent invocation
  start_line=$(grep -n "^### 3c\. Spawn Worker" "$phases" | cut -d: -f1)
  end_line=$(grep -n "^### 3d\." "$phases" | cut -d: -f1)
  if [ -n "$start_line" ] && [ -n "$end_line" ]; then
    end_line=$((end_line - 1))
    head -n $((start_line - 1)) "$phases" > "${phases}.tmp"
    cat >> "${phases}.tmp" << 'SECTION3C'
### 3c. Run Worker Agent(s)

Use the **worker** agent role to implement each selected task. For a multi-task
wave, create one isolated mutable workspace and task-unique summary/evidence
paths per worker, then dispatch the selected workers concurrently. For a
one-task wave, use the existing single-worker path.

**Commit the spec and task files BEFORE creating the workspaces.** A wave
workspace is branched from a commit, so anything still uncommitted in the
conductor's checkout does not exist inside it — and a freshly planned spec is
uncommitted by default. A worker dispatched into such a workspace cannot
re-anchor at all: `$FLOWCTL show <task-id>` finds no task there, and the failure
looks like a broken worker rather than a missing commit. Commit `.flow/` first
(`git add -A`), then create the workspaces from that commit. Verified 2026-08-14
on the first live wave dispatch. Single-worker runs are unaffected — they share
the conductor's checkout.

The worker gets fresh context and handles:
- Re-anchoring (reading spec, git status, task-relevant glossary terms when populated)
- Implementation
- Committing
- Review cycles (if enabled)
- Completing the task (flowctl done)

The last two responsibilities apply only to the existing single-worker path. A
parallel-wave worker defers review and all shared lifecycle work to the
conductor after integration.

**`REVIEW_MODE` is per-task, not a fixed run-wide value.** Resolve it for THIS task: if the user
passed an explicit `--review=<backend>` to `/flow-next:work`, use that (a deliberate run-wide override
wins for every task); OTHERWISE resolve task-aware — `REVIEW_MODE=$($FLOWCTL review-backend "$TASK_ID")`
— so a task's own `review:` override (e.g. `review: cursor:...` under a `codex` project default) selects
its backend rather than the project default. `none` still skips review.

**Invoke the worker:**

"Use the worker agent to implement this task:

TASK_ID: fn-X.Y
SPEC_ID: fn-X
FLOWCTL: $FLOWCTL
REVIEW_MODE: none|rp|codex|copilot|cursor|host-deferred
RALPH_MODE: true|false
PARALLEL_WAVE: true|false
WORKSPACE: <isolated mutable workspace>
HANDOVER_SUMMARY: <task-unique summary path>
HANDOVER_EVIDENCE: <task-unique evidence path>
BASELINE_HANDOFF: green (verified at <sha8> by <task-id>)

Follow your phases exactly."

`BASELINE_HANDOFF` is optional. The conductor MAY pass it only when ALL hold: the prior task in this run reached done with its Phase 5 Verify green over the SAME Quick commands, HEAD has not moved since except by that task's own receipt commit, and the new task's declared Touches do not intersect files changed since that verification. Conductor judgment on stated facts; when in doubt, omit the line. The first task of a run never receives a handoff (nothing verified yet).

Set `PARALLEL_WAVE: true` only for a concurrently dispatched multi-task wave.
Those workers implement, test, commit, and return their workspace, commits, and
the exact handover paths. They do **not** call `flowctl done`, project tracker
state, invoke plan-sync, run impl-review, or integrate their own commit. This
host-deferred shape is independent of `REVIEW_MODE`; the conductor preserves
the resolved backend and applies it after integration. The prompt fields are an
internal handoff, not a public CLI or stored schema.

**Host review routes OUTSIDE the worker (fn-123 R5) — and gates BEFORE done.** When the resolved review mode is \`host\`, pass \`REVIEW_MODE: host-deferred\`: the worker skips review dispatch AND defers \`flowctl done\` (returns with the task still in_progress + summary/evidence files written). The conductor then runs \`$flow-next-impl-review <task-id> --review=host\` as the mandatory gate and only on SHIP runs \`flowctl done\` with the worker-prepared summary/evidence plus the review receipt; NEEDS_WORK drives the bounded fix loop before done.

**Worker returns** (both paths): task id, terminal status, commit range, and the
summary/evidence paths (plus the review receipt path when the single-worker path
ran review). Content lives in those files — read them, never a restatement.

SECTION3C
    tail -n +$end_line "$phases" >> "${phases}.tmp"
    mv "${phases}.tmp" "$phases"
  fi

  # Text replacements
  sed -i.bak \
    -e 's/Use the Task tool to spawn a `worker` subagent/Use the worker agent role/g' \
    -e 's/spawn a worker subagent with fresh context/use the worker agent with fresh context/g' \
    -e 's/spawn a worker subagent/use the worker agent/g' \
    -e 's/After worker returns/After the worker agent returns/g' \
    -e 's/the worker failed/the worker agent failed/g' \
    -e 's/Use the Task tool to spawn the `plan-sync` subagent/Use the plan_sync agent/g' \
    -e 's/spawn the `plan-sync` subagent/use the plan_sync agent/g' \
    -e 's/quality auditor subagent/quality_auditor agent/g' \
    -e 's/Task flow-next:quality-auditor/Use the quality_auditor agent/g' \
    -e 's|Next: /flow-next:make-pr <spec-id>   # or /flow-next:qa <spec-id> first|Next: $flow-next-make-pr <spec-id>   # or $flow-next-qa <spec-id> first|g' \
    -e 's/spawn worker/run worker agent/g' \
    -e 's/\*\*For each task\*\*, spawn a worker subagent with fresh context/**For each task**, use the worker agent with fresh context/g' \
    "$phases"
  rm -f "${phases}.bak"
fi

# flow-next-work: SKILL.md
work_skill="$CODEX_DIR/skills/flow-next-work/SKILL.md"
if [ -f "$work_skill" ]; then
  sed -i.bak \
    -e 's/worker subagent with fresh context/worker agent with fresh context/g' \
    -e 's/worker subagent/worker agent/g' \
    -e 's/Worker subagent/Worker agent/g' \
    -e 's/Each task is implemented by a `worker` subagent/Each task is implemented by the `worker` agent role/g' \
    -e 's/worker handles/worker agent handles/g' \
    -e 's/The worker invokes/The worker agent invokes/g' \
    "$work_skill"
  rm -f "${work_skill}.bak"
fi

# canonical templates/usage.md (mirrored to codex/templates/) — Codex command-name syntax
# This template is what `flowctl usage` prints; nothing copies it into a repo.
# On Codex the CLI reads THIS mirror copy, and Codex project docs use `$flow-next-<cmd>`
# names, not `/flow-next:<cmd>` (same per-platform split the agents-md-snippet
# vs claude-md-snippet templates and workflow.md's model-routing substitution
# encode). Rewrite command tokens in the mirror template only — skill prose
# elsewhere keeps `/flow-next:` (agents resolve those contextually; this file
# is a user-facing project doc where a literal `/flow-next:work` invocation
# would hit an unavailable command). Validation below guards regression.
setup_usage="$CODEX_DIR/templates/usage.md"
if [ -f "$setup_usage" ]; then
  sed -i.bak -E 's|/flow-next:([a-z-]+)|$flow-next-\1|g' "$setup_usage"
  rm -f "${setup_usage}.bak"
fi

# fn-126 R4: the Codex mirror is consumed ONLY by Codex. Replace the multi-host
# Step-0 detection cascade with unconditional PLATFORM="codex" (canonical hosts
# never read this mirror; a GROK_AGENT / CURSOR_AGENT inheritance must not
# reclassify a Codex session). Hard-fail guard below enforces no host-detection
# branches in the mirror Step-0 bash fence.
setup_wf="$CODEX_DIR/skills/flow-next-setup/workflow.md"
if [ -f "$setup_wf" ]; then
  awk '
    # fn-126 R4: first ```bash under Step 0 Platform detection → unconditional codex
    /^## Step 0: Resolve plugin path and detect platform/ {in_step0=1}
    in_step0 && /^## / && !/^## Step 0:/ {in_step0=0; det_done=0}
    in_step0 && !det_done && /^```bash$/ {
      print "```bash"
      print "# Codex mirror: this workflow is consumed only by Codex."
      print "# Host detection is irrelevant — always PLATFORM=codex"
      print "# (canonical Claude-format hosts never read this mirror)."
      print "PLATFORM=\"codex\""
      skip_det=1
      det_done=1
      next
    }
    skip_det && /^```$/ {
      print
      skip_det=0
      next
    }
    skip_det {next}
    {print}
  ' "$setup_wf" > "${setup_wf}.step0tmp" && mv "${setup_wf}.step0tmp" "$setup_wf"
fi

# flow-next-plan: steps.md
# NOTE: no `../../templates/spec.md` → `../../../templates/spec.md` rewrite —
# the codex mirror now ships its own `codex/templates/spec.md` (sibling to
# `codex/skills/`), so `../../templates/spec.md` from `codex/skills/<name>/<file>.md`
# resolves correctly to the mirrored template. Canonical and mirror use the
# same relative path string.
plan_steps="$CODEX_DIR/skills/flow-next-plan/steps.md"
if [ -f "$plan_steps" ]; then
  sed -i.bak \
    -e 's|`flow-next:repo-scout`|the `repo_scout` agent|g' \
    -e 's|`flow-next:practice-scout`|the `practice_scout` agent|g' \
    -e 's|`flow-next:docs-scout`|the `docs_scout` agent|g' \
    -e 's|`flow-next:github-scout`|the `github_scout` agent|g' \
    -e 's|`flow-next:memory-scout`|the `memory_scout` agent|g' \
    -e 's|`flow-next:spec-scout`|the `spec_scout` agent|g' \
    -e 's|`flow-next:docs-gap-scout`|the `docs_gap_scout` agent|g' \
    -e 's|`flow-next:flow-gap-analyst`|the `flow_gap_analyst` agent|g' \
    -e 's|Task flow-next:flow-gap-analyst|Use the flow_gap_analyst agent|g' \
    "$plan_steps"
  rm -f "${plan_steps}.bak"
fi

# flow-next-plan: SKILL.md
plan_skill="$CODEX_DIR/skills/flow-next-plan/SKILL.md"
if [ -f "$plan_skill" ]; then
  sed -i.bak \
    -e 's/launches every scout in the depth-appropriate set, in ONE parallel Task call/launches every scout in the depth-appropriate set as parallel multi-agent threads (Codex spawns them concurrently)/g' \
    "$plan_skill"
  rm -f "${plan_skill}.bak"
fi

# flow-next-prime: workflow.md
prime_wf="$CODEX_DIR/skills/flow-next-prime/workflow.md"
if [ -f "$prime_wf" ]; then
  sed -i.bak \
    -e 's|Task flow-next:tooling-scout|Use the tooling_scout agent|g' \
    -e 's|Task flow-next:claude-md-scout|Use the agents_md_scout agent|g' \
    -e 's|Task flow-next:env-scout|Use the env_scout agent|g' \
    -e 's|Task flow-next:testing-scout|Use the testing_scout agent|g' \
    -e 's|Task flow-next:build-scout|Use the build_scout agent|g' \
    -e 's|Task flow-next:docs-gap-scout|Use the docs_gap_scout agent|g' \
    -e 's|Task flow-next:observability-scout|Use the observability_scout agent|g' \
    -e 's|Task flow-next:security-scout|Use the security_scout agent|g' \
    -e 's|Task flow-next:workflow-scout|Use the workflow_scout agent|g' \
    -e 's/Run all 9 scouts in parallel using the Task tool:/Run all 9 scouts in parallel (Codex spawns them as multi-agent threads):/g' \
    -e 's/Launch all 9 scouts in parallel for speed/Launch all 9 scout agents in parallel for speed/g' \
    "$prime_wf"
  rm -f "${prime_wf}.bak"
fi

# --- BEHAVIORAL: RP warnings for review skills ---
RP_WARNING='
---

## CRITICAL: RepoPrompt Commands Are SLOW - DO NOT RETRY

**READ THIS BEFORE RUNNING ANY COMMANDS:**

1. **`setup-review` takes 5-15 MINUTES** - It runs the RepoPrompt context builder which indexes files. This is NORMAL. Do NOT assume it is stuck.

2. **`chat-send` takes 2-10 MINUTES** - It waits for the LLM to generate a full review. This is NORMAL. Do NOT assume it is stuck.

3. **Run commands directly and WAIT** - Do NOT use background jobs. Just run the command and wait:
   ```bash
   # Run setup-review - takes 5-15 minutes, just wait
   $FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "..."
   # You will see file paths printed as it indexes - this is progress, not errors
   ```

4. **Output is progress, not errors** - The context builder prints file paths as it indexes. Seeing many lines of output is NORMAL. Do not interpret this as an error loop.

5. **NEVER retry these commands** - If you run them again, you will create duplicate reviews and waste time. Run ONCE and WAIT.

6. **Exit code 0 = success** - When the command finishes, check the exit code. If it is 0, it worked.

**If a command has been running for less than 15 minutes, WAIT. Do not retry. Do not output <promise>RETRY</promise>.**

---
'

for skill in flow-next-impl-review flow-next-plan-review flow-next-spec-completion-review; do
  # Prefer the backend-split workflow-rp.md (fn-48.3+) — the RP warning only
  # applies to the RP path. If the skill hasn't been split yet, fall back to
  # the monolithic workflow.md so unaffected skills keep the warning at the
  # top of their file.
  if [ -f "$CODEX_DIR/skills/$skill/workflow-rp.md" ]; then
    wf="$CODEX_DIR/skills/$skill/workflow-rp.md"
  else
    wf="$CODEX_DIR/skills/$skill/workflow.md"
  fi
  if [ -f "$wf" ]; then
    { head -1 "$wf"; echo "$RP_WARNING"; tail -n +2 "$wf"; } > "${wf}.tmp"
    mv "${wf}.tmp" "$wf"
  fi
  sk="$CODEX_DIR/skills/$skill/SKILL.md"
  if [ -f "$sk" ]; then
    sed -i.bak \
      -e 's|setup-review|setup-review (5-15 min, DO NOT RETRY)|g' \
      -e 's|chat-send|chat-send (2-10 min, DO NOT RETRY)|g' \
      "$sk"
    rm -f "${sk}.bak"
  fi
done

# --- NAMING: claude-md-scout → agents-md-scout ---
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  sed -i.bak \
    -e 's/claude-md-scout/agents-md-scout/g' \
    -e 's/claude_md_scout/agents_md_scout/g' \
    "$f"
  rm -f "${f}.bak"
done

# --- TOOL NAMES: read-only Explore dispatch → spawn_agent (fn-100 R12) ---
# Canonical prose writes the interview fact-scout dispatch Claude-native as
# "(`Task` with `subagent_type: Explore`)". Codex spawns subagents via
# `spawn_agent` with `agent_type: explorer` (same naming as the audit
# workflow's platform table). Exact-phrase match only: the "`Task` tool with
# `subagent_type: Explore`" variants (audit platform table, capture prose)
# deliberately document the Claude Code naming inside cross-platform tables
# and must NOT be rewritten. A validation guard below hard-fails if the
# exact dispatch phrase survives in the mirror.
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  sed -i.bak \
    -e 's/`Task` with `subagent_type: Explore`/`spawn_agent` with `agent_type: explorer`/g' \
    -e 's/(sonnet on Claude Code)/(the host'"'"'s mid-tier)/g' \
    "$f"
  rm -f "${f}.bak"
done

# --- TOOL NAMES: AskUserQuestion → plain-text numbered prompt (fn-45) ---
# Canonical skills use Claude-native `AskUserQuestion`. Codex's structured
# `request_user_input` errors outside Plan mode (openai/codex #10384, #11536,
# #12694 — closed without resolution as of Feb 2026), so the Codex mirror
# instead instructs the agent to render a plain-text numbered prompt with a
# final `N+1. Other — type your own answer` option, then stop and wait for
# the user's next message. The mirror never mentions `request_user_input` —
# validation guards below (R6) hard-fail if it leaks in.
#
# Order:
#   1. Strip maintainer breadcrumbs (any form — parens, bare sentence)
#   2. Strip ToolSearch references (Claude-only schema-load mechanism)
#   3. Rewrite AskUserQuestion → plain-text numbered-prompt instruction
find "$CODEX_DIR/skills" -name "*.md" -type f | while read -r f; do
  # 1. Strip maintainer breadcrumbs in their original (canonical) form,
  #    BEFORE the AskUserQuestion → plain-text-numbered-prompt rewrite happens.
  #    Use python for multi-form matching (sed gets unwieldy here).
  python3 - "$f" <<'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as fp:
    text = fp.read()

# Strip parenthetical breadcrumbs (allow whitespace incl. newlines inside
# the parens — canonical authors sometimes wrap them across lines).
text = re.sub(
    r' *\(sync-codex\.sh\s+rewrites[^)]*Codex mirror\.?\)',
    '',
    text,
)
# Strip non-parenthetical sentence breadcrumbs (any leading space, the
# sentence, optional period).
text = re.sub(
    r' *sync-codex\.sh rewrites[^.\n]*Codex mirror\.?',
    '',
    text,
)

# Strip maintainer-note BULLETS about the Codex mirror generation itself
# ("- **Codex mirror** ... regenerated in fn-NN — keep this file Claude-native
# ...", "- Codex mirror is regenerated in fn-NN — keep this file Claude-native
# ..."). These are author-facing reminders that the canonical file is the
# source and the mirror is derived; they're meaningless (and self-contradictory)
# inside the already-rewritten mirror, where they'd tell the Codex agent to
# "keep this file Claude-native". Run BEFORE the AskUserQuestion rewrite so the
# `Claude-native` anchor is still present.
#
# Two concrete shapes (handle each explicitly — a single lazy regex backtracks
# unpredictably across the wrapped form):
#   The bullet may lead with a bare "Codex mirror" OR a bold-opening
#   "**Codex mirror ...**" where the bold span carries extra words before it
#   closes (e.g. "**Codex mirror is regenerated in fn-68.5**"). `(?:\*\*)?`
#   matches an OPTIONAL opening bold marker (zero or two asterisks) so both the
#   tracker-sync (bare-led) and backlog-mode (bold-led) breadcrumbs are stripped.
#   (a) two-line bullet — "- **Codex mirror** ...\n  Claude-native ...\n"
#       (line 1 opens the bullet, line 2 is a 2-space-indented continuation
#       carrying the `Claude-native` anchor).
text = re.sub(
    r'(?m)^- (?:\*\*)?Codex mirror[^\n]*\n  [^\n]*Claude-native[^\n]*\n',
    '',
    text,
)
#   (b) single-line bullet — "- **Codex mirror** ... Claude-native ...\n"
#       (both the `Codex mirror` lead and the `Claude-native` anchor on one line).
text = re.sub(
    r'(?m)^- (?:\*\*)?Codex mirror[^\n]*Claude-native[^\n]*\n',
    '',
    text,
)

with open(path, 'w') as fp:
    fp.write(text)
PYEOF

  # 2. Strip ToolSearch references — Codex doesn't use ToolSearch.
  #    Run case-insensitively. Cover parenthetical, bare-sentence,
  #    multi-line bullet, and standalone-backtick variants.
  python3 - "$f" <<'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as fp:
    text = fp.read()

# Strip parenthetical ToolSearch fallback notes (case-insensitive on the verb).
text = re.sub(
    r' *\([Cc]all `ToolSearch`[^)]*\)',
    '',
    text,
)
text = re.sub(
    r' *\([Cc]all `ToolSearch select:[^`]+`[^)]*\)',
    '',
    text,
)
text = re.sub(
    r' *\(deferred — load via `ToolSearch select:[^`]+`[^)]*\)',
    '',
    text,
)
# Strip "If <X>'s schema isn't loaded ..., call `ToolSearch` ..." sentences
# FIRST — the generic "call `ToolSearch` ..." stripper below would eat the
# suffix and leave a dangling fragment (e.g. fn-45 review observed
# `flow-next-memory-migrate/workflow.md` keeping "If <X>'s schema isn't
# loaded on Claude Code," with no completing clause).
text = re.sub(
    r"If `[^`]+`'s schema isn'?t loaded on Claude Code, call `ToolSearch`[^.\n]*\.",
    '',
    text,
)
# Belt-and-suspenders: any dangling "If <X>'s schema isn't loaded on Claude
# Code," fragment (no completing clause) left over from an earlier rewrite
# also gets stripped — keep the mirror prose self-consistent.
text = re.sub(
    r"If `[^`]+`'s schema isn'?t loaded on Claude Code,? *\n?",
    '',
    text,
)
# Strip "Call/call `ToolSearch` with ..." sentences (case-insensitive).
text = re.sub(
    r'(?:^|(?<=[.\s]))[Cc]all `ToolSearch`[^.\n]*\.',
    '',
    text,
    flags=re.MULTILINE,
)
# Strip standalone ToolSearch backtick refs in line items.
text = re.sub(
    r'`ToolSearch select:[^`]+`',
    '',
    text,
)
# Strip multi-line bullet items that mention ToolSearch with a Claude-only
# anti-pattern flavor — these don't apply on Codex.
# Pattern: dash-bullet where any line contains ToolSearch (multi-line aware).
# Match the bullet from "- **...**" through to the end of the bullet (next
# blank line OR next dash-bullet at same indent).
def strip_toolsearch_bullets(text):
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect start of a top-level bullet that contains ToolSearch in
        # the bullet body (line + continuation lines until next blank or
        # next bullet).
        if re.match(r'^- \*\*', line):
            # Collect bullet content
            bullet = [line]
            j = i + 1
            while j < len(lines) and (lines[j].startswith('  ') or lines[j] == ''):
                if lines[j] == '' and j + 1 < len(lines) and not lines[j + 1].startswith('  '):
                    break
                bullet.append(lines[j])
                j += 1
            bullet_text = '\n'.join(bullet)
            if 'ToolSearch' in bullet_text:
                # Skip — strip this bullet from output
                i = j
                continue
        out.append(line)
        i += 1
    return '\n'.join(out)

text = strip_toolsearch_bullets(text)

# Collapse double spaces that result from strips — fence-aware: fenced-block
# whitespace is meaning-bearing (visual-skill trees, aligned file-tree
# comments), and leading indentation outside fences is structure, not residue.
# A fence closes only on a MATCHING delimiter (same char, run length >= the
# opener's, no info string) — outer ```` wrappers keep inner ``` blocks intact.
def collapse_interior_spaces(text):
    out = []
    fence = None  # (delimiter char, run length) of the open fence, else None
    for line in text.split('\n'):
        stripped = line.lstrip()
        m = re.match(r'(`{3,}|~{3,})(.*)', stripped)
        if m:
            marker, rest = m.group(1), m.group(2)
            if fence is None:
                fence = (marker[0], len(marker))
                out.append(line)
                continue
            if marker[0] == fence[0] and len(marker) >= fence[1] and not rest.strip():
                fence = None
                out.append(line)
                continue
            # Non-matching fence line inside an open fence is content —
            # falls through to the in-fence branch below.
        if fence is not None:
            out.append(line)
            continue
        indent = line[:len(line) - len(stripped)]
        out.append(indent + re.sub(r'  +', ' ', stripped))
    return '\n'.join(out)

text = collapse_interior_spaces(text)
# Collapse blank-line runs to max 2.
text = re.sub(r'\n{3,}', '\n\n', text)
# Trim trailing whitespace per line.
text = '\n'.join(line.rstrip() for line in text.split('\n'))

with open(path, 'w') as fp:
    fp.write(text)
PYEOF

  # 3. Rewrite AskUserQuestion invocations into a plain-text numbered-prompt
  #    instruction for the Codex mirror (fn-45). Distinct re.sub calls handle
  #    the canonical surface forms, longest-most-specific first so bare-token
  #    rules don't eat structured ones. Hard mandates softened to "MUST ask
  #    via the plain-text numbered prompt"; auto-fix-loop "Never use" mandates
  #    preserve semantics (token rewrite only). Frontmatter `allowed-tools:`
  #    lines keep the legacy `request_user_input` token — Codex reads
  #    agents/openai.yaml for the actual contract; the frontmatter is residue
  #    that just needs to clear the askq_refs guard.
  python3 - "$f" <<'PYEOF'
import re, sys
path = sys.argv[1]
with open(path) as fp:
    text = fp.read()

# Track whether this file referenced AskUserQuestion in prose (frontmatter
# only doesn't count — that's harmless residue). We use this flag after
# substitutions to inject the R2 instruction block exactly once.
prose_text = re.sub(r'(?ms)\A---\n.*?\n---\n', '', text)
had_ask_in_prose = bool(re.search(r'\bAskUserQuestion\b', prose_text))

# --- Longest-most-specific patterns first ----------------------------------

# A. Hard mandate "CRITICAL REQUIREMENT: You MUST use the `AskUserQuestion`
#    tool for every question." → softened mandate (R3). Used by
#    flow-next-interview/SKILL.md:217.
text = re.sub(
    r'\*\*CRITICAL REQUIREMENT\*\*: You MUST use the `AskUserQuestion` tool for every question\.',
    '**CRITICAL REQUIREMENT**: For every question, you MUST ask via the plain-text numbered prompt described below.',
    text,
)

# B. Hard mandate "**CRITICAL**: You MUST use the `AskUserQuestion` tool for
#    consent." → softened mandate (R3). Used by
#    flow-next-prime/workflow.md:194.
text = re.sub(
    r'\*\*CRITICAL\*\*: You MUST use the `AskUserQuestion` tool for consent\.',
    '**CRITICAL**: For consent, you MUST ask via the plain-text numbered prompt described below.',
    text,
)

# C. "MUST use `AskUserQuestion` tool" bullet / mandate (R3).
#    Used by flow-next-prime/workflow.md:306, SKILL.md:109 fragment.
text = re.sub(
    r'MUST use `AskUserQuestion` tool',
    'MUST ask via the plain-text numbered prompt described below',
    text,
)

# D. "ONLY ask questions via AskUserQuestion tool calls" (R3).
#    Used by flow-next-interview/SKILL.md:221.
text = re.sub(
    r'ONLY ask questions via AskUserQuestion tool calls',
    'ONLY ask via the plain-text numbered prompt',
    text,
)

# E. Anti-mandate "do NOT use AskUserQuestion tool" — used in
#    flow-next-plan/SKILL.md:117 + flow-next-ralph-init/SKILL.md:37 to tell
#    the agent "ask in plain text ad-hoc, not via the structured tool". On
#    Codex there IS no structured tool, so the negation is a tautology.
#    Strip the parenthetical entirely (along with optional surrounding
#    whitespace + parens) to keep the prose clean. Also drop the now-empty
#    leading space.
text = re.sub(
    r' *\(do NOT use AskUserQuestion tool\)',
    '',
    text,
)
# Bare-form fallback (no parens) — leave a soft replacement in case the
# anti-mandate appears outside a parenthetical somewhere.
text = re.sub(
    r'do NOT use AskUserQuestion tool',
    'ask using plain text instead of any structured prompt tool',
    text,
)

# F. Auto-fix-loop mandate "Never use AskUserQuestion in this loop" (R3
#    boundary — token rewrite only, intent preserved). Used by
#    impl-review/plan-review/spec-completion-review workflow.md + SKILL.md.
text = re.sub(
    r'Never use AskUserQuestion in this loop',
    'Never use the plain-text numbered prompt in this loop',
    text,
)

# G. "Call AskUserQuestion tool with question and options." prose
#    (flow-next-interview/SKILL.md:231).
text = re.sub(
    r'Call AskUserQuestion tool with question and options\.',
    'Render the question and options as a plain-text numbered prompt (see below).',
    text,
)

# H. Frontmatter `allowed-tools: AskUserQuestion, ...` — STRIP the token
#    entirely from the mirror. fn-45 originally rewrote it to
#    `request_user_input` on the assumption that Codex reads
#    `agents/openai.yaml` for the tool contract and treats SKILL.md
#    frontmatter as harmless residue. In practice the agent reads
#    SKILL.md frontmatter, trusts the listed tools, and calls
#    `request_user_input` — which errors out in Default mode
#    (openai/codex #10384, #11536, #12694). Stripping the token leaves
#    only tools the mirror actually uses. Clean up any leading comma or
#    trailing comma left behind so the list stays well-formed.
def _strip_aukq(match):
    head = match.group(1)
    rest = match.group(2)
    # Drop the token AND a trailing ", " if present; else drop a leading
    # ", " if it was the last item.
    if rest.startswith(', '):
        return head + rest[2:]
    if head.endswith(', '):
        return head[:-2] + rest
    return head + rest
text = re.sub(
    r'^(allowed-tools:[^\n]*?)\bAskUserQuestion\b(.*)$',
    _strip_aukq,
    text,
    flags=re.MULTILINE,
)

# I. Generic backticked invocation: `AskUserQuestion`
#    → `plain-text numbered prompt` (kept backticked for in-prose readability).
text = re.sub(
    r'`AskUserQuestion`',
    '`plain-text numbered prompt`',
    text,
)

# J. Generic "AskUserQuestion tool" (no backticks) → "plain-text numbered
#    prompt". Catches inline mentions in headings + non-backticked prose.
text = re.sub(
    r'AskUserQuestion tool',
    'plain-text numbered prompt',
    text,
)

# K. Bare AskUserQuestion (table cells, headings, residual prose). Catch-all
#    last so structured patterns above run first.
text = re.sub(
    r'\bAskUserQuestion\b',
    'plain-text numbered prompt',
    text,
)

# L. Strip Claude-only schema-loader prose left over after AskUserQuestion
#    substitution. Examples (post-substitution):
#      "Use `plain-text numbered prompt`. It's a deferred tool — call first
#       to load its schema if it isn't already in scope."
#    On Codex there is no schema to load — strip the deferred-tool sentence.
text = re.sub(
    r" It'?s a deferred tool — call first to load its schema if it isn'?t already in scope\.",
    '',
    text,
)

# L2. Strip the vestigial "Do NOT / Never just print questions as text"
#     anti-print prose. In canonical (Claude) it correctly means "use the
#     structured AskUserQuestion tool, not bare prose". After the A-K
#     rewrites turn the tool reference into the plain-text numbered prompt,
#     the same sentence becomes a self-contradiction ("ask via plain text
#     ... but do not print as text"). Drop it in the mirror. Covers:
#       1. " — Never just print questions as text" (em-dash bullet form,
#          no trailing period — appears mid-bullet, run FIRST so the
#          generic rule below doesn't leave a dangling em-dash)
#       2. " Do NOT just print questions as text." (trailing-sentence form)
#       3. " Never just print questions as text." (trailing-sentence form,
#          appears after bullet body in SKILL.md)
text = re.sub(
    r' — (?:Do NOT|Never) just print questions as text\.?',
    '',
    text,
)
text = re.sub(
    r' (?:Do NOT|Never) just print questions as text\.?',
    '',
    text,
)

# M. Strip / soften UI-shape prose that assumes a structured prompt tool.
#    "The tool provides an interactive UI." → drop the sentence (its
#    immediate sibling sentences still describe per-question structure
#    advice that translates fine to plain text).
text = re.sub(
    r'The tool provides an interactive UI\. ?',
    '',
    text,
)

# N. Structured-tool API prose — directives that reference fields and
#    concepts that only exist in Claude's AskUserQuestion JSON contract.
#    On Codex these become misleading. Translate to plain-text equivalents
#    that still convey the intent.
text = re.sub(
    r'Use `multiSelect: true` so users can pick multiple items',
    'Allow multi-select when options are not exclusive — number the options as `1.` … `N.` and ask the user to reply with the numbers (or labels) of all that apply',
    text,
)
text = re.sub(
    r'Build the questions array dynamically',
    'Build the prompt content (question text + numbered option list) dynamically',
    text,
)
text = re.sub(
    r'Use `plain-text numbered prompt` with the built questions array\.',
    'Print the prompt content built above and stop for the user\'s reply.',
    text,
)
text = re.sub(
    r'platform blocking question tool',
    'plain-text numbered prompt',
    text,
)
# Handle multi-line bold-wrapped variant like:
#     **blocking
#     question tool**
# (canonical authors sometimes wrap mid-phrase). Collapse to a single
# inline replacement.
text = re.sub(
    r'\*\*blocking\s+question tool\*\*',
    '**plain-text numbered prompt**',
    text,
)
text = re.sub(
    r'blocking question tool',
    'plain-text numbered prompt',
    text,
)
# Hyphenated form: "blocking-question tool" / "blocking-question tools".
text = re.sub(
    r'blocking-question tools?',
    'plain-text numbered prompt',
    text,
)
# Interview-skill anti-patterns that assumed structured-tool prompts.
# After fn-45, "output questions as text" IS the contract on Codex —
# the "DO NOT" bullets directly contradict the plain-text instruction.
# Strip both bullets and the "Anti-pattern (WRONG)" framing that followed
# (the literal plain-text example WAS the bad pattern under structured
# tools, but it IS the correct pattern on plain-text Codex).
text = re.sub(
    r'^- DO NOT output questions as text\n',
    '',
    text,
    flags=re.MULTILINE,
)
text = re.sub(
    r'^- DO NOT list questions in your response\n',
    '',
    text,
    flags=re.MULTILINE,
)
# "per tool call" → "per prompt turn" — the multi-question batching
# rule still applies, but framed for plain-text turns rather than
# structured tool invocations.
text = re.sub(
    r'\bper tool call\b',
    'per prompt turn',
    text,
)
# "tool call" residual mentions in bullet items / inline prose.
text = re.sub(
    r'\bin a single tool call\b',
    'in a single prompt turn',
    text,
)
text = re.sub(
    r'\btool call(s?)\b',
    r'prompt turn\1',
    text,
)
# The interview "Anti-pattern (WRONG)" example showed a plain-text
# numbered question as the wrong pattern under structured tools — on
# Codex that example IS the correct pattern. Drop the inverted framing
# block entirely (header + fenced example + "Correct pattern:" line).
text = re.sub(
    r'\*\*Anti-pattern \(WRONG\)\*\*:\n```\nQuestion 1:[^`]+```\n\n\*\*Correct pattern\*\*:[^\n]*\n',
    '',
    text,
)
# "Per-finding blocking question" prose (used in R8 recap line) —
# rewrite to drop the Claude-blocking-tool framing.
text = re.sub(
    r'Per-finding blocking question',
    'Per-finding plain-text numbered prompt',
    text,
)
# "the blocking tool" / "platform blocking tool" / "blocking-question tool"
# residual refs.
text = re.sub(
    r'\bthe (?:platform )?blocking tool\b',
    'the plain-text numbered prompt',
    text,
)
# "via blocking question" / "a blocking question" / "blocking prompt"
# residual refs (Claude-specific framing on Codex).
text = re.sub(
    r'\bvia (?:a |the )?blocking question\b',
    'via plain-text numbered prompt',
    text,
)
text = re.sub(
    r'\b(a |the )blocking question\b',
    r'\1plain-text numbered prompt',
    text,
)
text = re.sub(
    r'\bblocking prompt\b',
    'plain-text numbered prompt',
    text,
)
# Bare "blocking question" (no article — e.g. "surfaces blocking question
# with frozen options") and bold-wrapped variants.
text = re.sub(
    r'\*\*blocking question\*\*',
    '**plain-text numbered prompt**',
    text,
)
text = re.sub(
    r'\bblocking question\b',
    'plain-text numbered prompt',
    text,
)
# "no blocking tool is available/reachable" — describes a fallback gate.
# On Codex the "blocking tool" framing doesn't apply.
text = re.sub(
    r'\bno blocking tool is (available|reachable)\b',
    r'plain text is the prompt mechanism',
    text,
)
# "the platform's question tool" — phrasing inherited from canonical;
# Codex doesn't have a structured question tool.
text = re.sub(
    r"\bthe platform'?s question tool\b",
    'the plain-text numbered prompt',
    text,
)

# O. Strip the stale "Fall back if the tool is unreachable" fallback prose.
#    In canonical (Claude) the phrasing means: "if the structured
#    AskUserQuestion tool is unavailable, drop to plain-text numbered list".
#    After A-N collapse the tool references into the plain-text numbered
#    prompt itself, the surviving fallback sentences read as if the
#    plain-text numbered prompt is a tool with a separate "fall back to
#    plain text" path — which is nonsensical (the plain-text numbered
#    prompt IS that path) and reintroduces the Codex Default-mode failure
#    fn-45 was meant to fix by sending the agent looking for a nonexistent
#    prompt tool. Strip every variant, preserving any non-fallback tail
#    clauses (e.g. "Never silently skip the question.") that follow the
#    strip site. Must run AFTER M/N — the multi-line pattern references
#    "the plain-text numbered prompt", which only exists post-rewrite of
#    canonical "the blocking tool".
#
#    Patterns matched longest-most-specific-first so bare strippers don't
#    eat the suffix of the longer-tail replacement.
#
# b. " Fall back ... — never silently skip the question." → preserve the
#    never-skip tail (sole site: flow-next-strategy/SKILL.md).
text = re.sub(
    r' Fall back to numbered options in chat only when the tool is unreachable in the harness or the call errors — never silently skip the question\.',
    ' Never silently skip the question.',
    text,
)
# a. " Fall back to numbered options in plain text only if the tool is
#    unreachable or errors." → strip (capture / memory-migrate / audit).
text = re.sub(
    r' Fall back to numbered options in plain text only if the tool is unreachable or errors\.',
    '',
    text,
)
# c. " Fall back to a numbered options prompt only if the tool is
#    unreachable." → strip (make-pr).
text = re.sub(
    r' Fall back to a numbered options prompt only if the tool is unreachable\.',
    '',
    text,
)
# d. " Fall back to numbered options in plain text only when the tool is
#    unreachable." → strip (interview).
text = re.sub(
    r' Fall back to numbered options in plain text only when the tool is unreachable\.',
    '',
    text,
)
# e. "; fall back to printing the numbered list and reading a typed reply
#    if the tool is unreachable." → "." (prospect:157).
text = re.sub(
    r'; fall back to printing the numbered list and reading a typed reply if the tool is unreachable\.',
    '.',
    text,
)
# f. "; fall back to numbered-options when the tool is unreachable." → "."
#    (prospect:605).
text = re.sub(
    r'; fall back to numbered-options when the tool is unreachable\.',
    '.',
    text,
)
# g. " If the tool is unreachable, print the frozen-string format below
#    and read the user's reply from chat." → strip (prospect:851).
text = re.sub(
    r" If the tool is unreachable, print the frozen-string format below and read the user'?s reply from chat\.",
    '',
    text,
)
# h. " If the tool is unreachable, fall back to printing a numbered list
#    and reading a typed reply." → strip (audit/workflow:476).
text = re.sub(
    r' If the tool is unreachable, fall back to printing a numbered list and reading a typed reply\.',
    '',
    text,
)
# i. Multi-line paragraph (impl-review/walkthrough.md:43-45):
#       If the tool is unreachable, fall through to a chat-prompt fallback (print
#       the question, wait for the user's next message). The fallback is less
#       reliable — prefer the plain-text numbered prompt wherever available.
#    Strip the whole paragraph.
text = re.sub(
    r"If the tool is unreachable, fall through to a chat-prompt fallback \(print\nthe question, wait for the user'?s next message\)\. The fallback is less\nreliable — prefer the plain-text numbered prompt wherever available\.\n",
    '',
    text,
)

# --- R2 instruction block injection ----------------------------------------
# Inject the full plain-text numbered-prompt contract once per file. The
# instruction tells the Codex agent how to render options, how to signal
# the freeform "Other" affordance, and that it must STOP after printing.
INSTRUCTION = (
    '**Ask the user via plain text.** Render the options below as a '
    'numbered list `1.` … `N.`, followed by a final option '
    '`N+1. Other — type your own answer`. Print the question, then the '
    'numbered list, then **stop and wait for the user\'s next message '
    'before continuing**. Parse the reply as: a bare number `1`–`N+1` → '
    'that option; the literal text of an option label → that option; free '
    'text after `Other` → custom answer.'
)

def is_negative_context(line):
    """True when 'plain-text numbered prompt' appears in a context that
    is NOT a live ask — auto-fix-loop sites, skip/no-prompt prose,
    reference/checklist bullets about what something IS NOT or what is
    skipped. Injecting R2 here either contradicts the surrounding prose
    or pollutes deterministic/Ralph branches."""
    # Auto-fix-loop hard mandates.
    if 'Never use' in line and 'plain-text numbered prompt' in line:
        return True
    if 'do NOT use' in line and 'plain-text numbered prompt' in line:
        return True
    # Hard-error / no-user prose ("questions hard-error ...", "no user to
    # ask ..."). These lines DESCRIBE a Ralph/autonomous branch that refuses
    # to ask — injecting the R2 ask block here would contradict the branch
    # semantics (observed: make-pr autonomous bullet, fn-59.3 review).
    if ('hard-error' in line or 'no user to ask' in line) \
            and 'plain-text numbered prompt' in line:
        return True
    # Capability-negation prose ("cannot call X", "can't ask via X", "cannot
    # use X"). These describe a subagent/context that is UNABLE to ask — a
    # descriptive site (e.g. "the worker is a subagent and cannot call
    # `plain-text numbered prompt`"), NOT a live ask.
    # Injecting the R2 block here flips the meaning into an instruction to ask.
    if re.search(r"\b(?:cannot|can[’']?t|could not|couldn[’']?t)\s+(?:call|use|ask\b[^.]*?via)\b", line) \
            and 'plain-text numbered prompt' in line:
        return True
    # Skip/no-prompt prose ("skips the ... preview", "no plain-text ...
    # call", etc.). These describe deterministic branches, not active asks.
    if re.search(r'\bskips? the `?plain-text numbered prompt`?', line):
        return True
    if re.search(r'\bno `?plain-text numbered prompt`? call', line):
        return True
    if re.search(r'without (?:a |an |any )?(?:`?plain-text numbered prompt`?|prompt) call', line):
        return True
    # Reference-style "It is not / X is not ..." bullets. These describe
    # what the prompt isn't — not a live ask site.
    if re.search(r'(?:It|This|That) is not\b', line) and 'plain-text numbered prompt' in line:
        return True
    # Forbidden / never-reached / never-interactive prose. An autonomous-only
    # skill (pilot) — and tracker-sync's Phase-0 autonomy invariant — describe
    # the prompt path ONLY to forbid it: "never an interactive `plain-text
    # numbered prompt`", "`plain-text numbered prompt` is forbidden on the tick
    # path", "`plain-text numbered prompt` is never reached / never reachable",
    # "no path reaches `plain-text numbered prompt`", "NO code path may reach
    # `plain-text numbered prompt`", "Never asks interactively". Injecting the R2
    # ask block here contradicts the surface-don't-block / autonomous contract
    # (fn-68 R14: the backlog/Ralph path never reaches an interactive prompt).
    # The verb regex mis-reads the leading "Asking ..." / "Never asks ..." OR the
    # trailing "ask the human" as an active-ask anchor, so this guard must catch
    # the negation explicitly.
    #
    # CASE-INSENSITIVE on purpose: the tracker-sync invariant capitalizes it as
    # "NO code path may reach" (review caught this — a case-sensitive
    # "no ... reaches" missed both the uppercase AND the "may reach" form). The
    # `reach` clause covers reach / reaches / reached / reachable, with or
    # without an intervening modal ("may"/"can"/"could"/"will") and the optional
    # "code" qualifier.
    if 'plain-text numbered prompt' in line and re.search(
        r'\b(?:is|are) forbidden\b'
        r'|\bnever an interactive\b'
        r'|\bnever asks?\s+interactively\b'
        r'|\b(?:no|never)\b[^.]*?\b(?:code\s+)?path[^.]*?\breach(?:es|ed|able)?\b'
        r'|\bis\s+never\s+reach(?:ed|able)\b'
        r'|\bnever\s+reach(?:es|ed|able)\b',
        line,
        re.IGNORECASE,
    ):
        return True
    return False

def is_table_line(line):
    """True for markdown table rows or delimiter rows. Injecting a
    paragraph between table rows breaks the table — skip these as
    injection anchors."""
    stripped = line.lstrip()
    return stripped.startswith('|') or stripped.startswith('|-')

# Verbs that indicate an active ask / prompt site. The R2 instruction
# block belongs adjacent to one of these — not in deterministic prose,
# reference lists, or "what X is not" bullets.
ACTIVE_ASK_VERBS = re.compile(
    r'\b('
    r'[Aa]sk|MUST ask|[Mm]ust use|[Mm]ust ask|MUST use|'
    r'[Uu]se `?plain-text numbered prompt`?|'
    r'[Dd]efault to `?plain-text numbered prompt`?|'
    r'[Ff]ormat the question|'
    r'[Rr]ender|[Ss]urface|[Ff]ire|[Pp]resent|[Ss]how|'
    r'[Cc]all `?plain-text numbered prompt`?|'
    r'[Ii]nvoke `?plain-text numbered prompt`?|'
    r'via `?plain-text numbered prompt`?'
    r')\b'
)

def is_active_ask_anchor(line):
    """True when the line is a plausible active-ask site for the R2
    instruction. Anchors should describe ASKING via the prompt, not
    skipping it or describing what it isn't."""
    if 'plain-text numbered prompt' not in line:
        return False
    return bool(ACTIVE_ASK_VERBS.search(line))

# Inject once per file. Two strategies, in priority order:
#  1. If a hard-mandate pattern (A/B/C) fired, it left a "described below"
#     sentinel. Splice the instruction immediately after that paragraph.
#  2. Otherwise, if the original file referenced AskUserQuestion in prose
#     in an affirmative context, splice the instruction immediately before
#     the FIRST positive (non-negative, non-table) noun-phrase reference so
#     the substituted noun phrase has a definition the agent can resolve.
#     If every remaining reference is a negative mandate or sits inside a
#     markdown table, skip injection entirely — the surrounding prose is
#     either contradicting it or structurally fragile.
if 'described below' in text:
    lines = text.split('\n')
    out = []
    injected = False
    for line in lines:
        out.append(line)
        if not injected and 'described below' in line:
            out.append('')
            out.append(INSTRUCTION)
            injected = True
    text = '\n'.join(out)
elif had_ask_in_prose and 'plain-text numbered prompt' in text:
    lines = text.split('\n')
    # Track fenced-code-block state so we never inject inside a ``` ... ```
    # region (would split a working code example). Anchor must be:
    #   - active-ask shape (verb match in line)
    #   - not a negative context (skip / Never use / It is not / ...)
    #   - not a markdown table row or delimiter
    #   - not inside a fenced code block
    in_fence = False
    anchor_idx = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not is_active_ask_anchor(line):
            continue
        if is_negative_context(line):
            continue
        if is_table_line(line):
            continue
        anchor_idx = i
        break
    if anchor_idx >= 0:
        out = []
        for i, line in enumerate(lines):
            if i == anchor_idx:
                out.append(INSTRUCTION)
                out.append('')
            out.append(line)
        text = '\n'.join(out)

# Collapse double spaces / blank-line runs left over from substitutions —
# fence-aware: fenced-block whitespace is meaning-bearing (visual-skill trees,
# aligned file-tree comments); leading indent outside fences is structure.
# A fence closes only on a MATCHING delimiter (same char, run length >= the
# opener's, no info string) — outer ```` wrappers keep inner ``` blocks intact.
def collapse_interior_spaces(text):
    out = []
    fence = None  # (delimiter char, run length) of the open fence, else None
    for line in text.split('\n'):
        stripped = line.lstrip()
        m = re.match(r'(`{3,}|~{3,})(.*)', stripped)
        if m:
            marker, rest = m.group(1), m.group(2)
            if fence is None:
                fence = (marker[0], len(marker))
                out.append(line)
                continue
            if marker[0] == fence[0] and len(marker) >= fence[1] and not rest.strip():
                fence = None
                out.append(line)
                continue
            # Non-matching fence line inside an open fence is content —
            # falls through to the in-fence branch below.
        if fence is not None:
            out.append(line)
            continue
        indent = line[:len(line) - len(stripped)]
        out.append(indent + re.sub(r'  +', ' ', stripped))
    return '\n'.join(out)

text = collapse_interior_spaces(text)
text = re.sub(r'\n{3,}', '\n\n', text)
text = '\n'.join(line.rstrip() for line in text.split('\n'))

with open(path, 'w') as fp:
    fp.write(text)
PYEOF
done

# Remove .DS_Store and other cruft
find "$CODEX_DIR" -name ".DS_Store" -delete 2>/dev/null || true

# --- UI metadata: agents/openai.yaml for key skills ---
generate_openai_yaml() {
  local skill="$1" display="$2" desc="$3" color="$4" implicit="$5"
  local prompt="${6:-}"
  local dir="$CODEX_DIR/skills/$skill/agents"
  mkdir -p "$dir"
  {
    echo "interface:"
    echo "  display_name: \"$display\""
    echo "  short_description: \"$desc\""
    echo "  brand_color: \"$color\""
    [ -n "$prompt" ] && echo "  default_prompt: \"$prompt\""
    echo "policy:"
    echo "  allow_implicit_invocation: $implicit"
  } > "$dir/openai.yaml"
}

# Workflow skills (blue, implicit - surfaced in the model catalog so prose
# like "plan this feature" / "pilot this to completion" resolves the skill)
generate_openai_yaml "flow-next-plan"      "Flow Plan"      "Create structured build plans from feature requests" "#3B82F6" true "Plan out this feature: "
generate_openai_yaml "flow-next-work"      "Flow Work"      "Execute planned tasks with worker subagents"          "#3B82F6" true "Work on: "
generate_openai_yaml "flow-next-interview" "Flow Interview" "Deep Q&A to refine specs and requirements"            "#3B82F6" true
generate_openai_yaml "flow-next-setup"     "Flow Setup"     "Initialize flow-next in current project"              "#3B82F6" true
generate_openai_yaml "flow-next-prospect"  "Flow Prospect"  "Generate ranked candidate ideas grounded in the repo" "#3B82F6" true "What should we build next? "
generate_openai_yaml "flow-next-chart"     "Flow Chart"     "Decision-map discovery for one oversized unclear idea before capture" "#3B82F6" true "Chart out: "
generate_openai_yaml "flow-next-guide"     "Flow Guide"     "Prompt-first router for the smallest sufficient flow-next workflow"   "#3B82F6" true
generate_openai_yaml "flow-next-capture"   "Flow Capture"   "Synthesize conversation context into a flow-next spec" "#3B82F6" true "Capture this as a spec: "
generate_openai_yaml "flow-next-strategy"  "Flow Strategy"  "Generate or update repo-root STRATEGY.md (problem, approach, personas, metrics, tracks)" "#3B82F6" true
generate_openai_yaml "flow-next-audit"     "Flow Audit"     "Review .flow/memory/ entries against current code"   "#3B82F6" true
generate_openai_yaml "flow-next-memory-migrate" "Flow Memory Migrate" "Migrate legacy flat memory files to categorized YAML schema" "#3B82F6" true
generate_openai_yaml "flow-next-make-pr" "Flow Make PR" "Render a cognitive-aid PR body from flow-next state and open via gh" "#3B82F6" true
generate_openai_yaml "flow-next-tracker-sync" "Flow Tracker Sync" "Project a spec to a tracker (Linear/GitHub/GitLab/Jira) and reconcile two-way — NOT plan-sync" "#3B82F6" true
generate_openai_yaml "flow-next-qa" "Flow QA" "Live-app real-user QA pass derived from the spec — drives the running app, files P0/P1/P2 findings, emits a YES/NO verdict" "#3B82F6" true
generate_openai_yaml "flow-next-pilot" "Flow Pilot" "Single-tick autonomous build-loop conductor — one ready spec, one stage per tick, terminal PILOT_VERDICT line" "#3B82F6" true
generate_openai_yaml "flow-next-land" "Flow Land" "Cadence-tick autonomous PR babysitter — CI-fix, resolve, converge, merge, close, release; terminal LAND_VERDICT line" "#3B82F6" true

# Review skills (red, implicit)
generate_openai_yaml "flow-next-impl-review" "Flow Implementation Review" "Carmack-level code review via RepoPrompt"  "#EF4444" true
generate_openai_yaml "flow-next-plan-review" "Flow Plan Review"           "Carmack-level plan review via RepoPrompt"  "#EF4444" true
generate_openai_yaml "flow-next-spec-completion-review" "Flow Spec Completion Review" "Verify spec implementation matches the spec" "#EF4444" true
generate_openai_yaml "flow-next-resolve-pr"  "Flow Resolve PR"            "Resolve PR review feedback via GraphQL"    "#EF4444" true "Resolve PR "

# Utility skills (blue/amber, implicit allowed)
generate_openai_yaml "flow-next"       "Flow Tasks" "Manage .flow/ tasks and specs"                           "#3B82F6" true
generate_openai_yaml "flow-next-prime" "Flow Prime" "Comprehensive codebase assessment for agent readiness"    "#F59E0B" true
generate_openai_yaml "flow-next-map"   "Flow Map"   "Wrap clawpatch map for a semantic feature index (opt-in)" "#F59E0B" true
# Visual stays OUT of the Codex catalog (explicit false): its trigger-rich
# description is the whole point on hosts that match on it, and injecting that
# text into every session's shared skills budget is exactly the cost the
# digest exists to save. Reachable by /flow-next:visual and by $name.
generate_openai_yaml "flow-next-visual" "Flow Visual" "Restate a spec, task, diff, or the current topic as a compact markdown digest" "#F59E0B" false
# Work-rolling is an EXPERIMENTAL beta (fn-203 Phase B): user-invoked only,
# explicit false so it never enters the implicit skill catalog - the pipeline
# (pilot/land) stays on canonical flow-next-work. Reachable by
# $flow-next-work-rolling. It graduates or is deleted (fn-203 R10).
generate_openai_yaml "flow-next-work-rolling" "Flow Work Rolling [experimental]" "Rolling-frontier work variant - per-task admission, isolated workspaces, conductor-owned review (experimental - can change or disappear)" "#3B82F6" false
generate_openai_yaml "flow-next-ralph-init" "Flow Ralph Init" "Scaffold the repo-local Ralph autonomous harness" "#3B82F6" true

# Internal skills (gray, explicit-only). These are spawned by other skills,
# never by user prose. Codex defaults allow_implicit_invocation to TRUE when
# no openai.yaml exists, silently injecting name+description into EVERY
# session's skill catalog (a shared budget of min(8000 chars, 2% of context;
# codex-rs/core-skills/src/render.rs) - overflow truncates ALL skills'
# descriptions, including unrelated user skills). Hidden skills stay fully
# invocable by the skills that dispatch them (paths in prose) and via $name.
generate_openai_yaml "flow-next-drive"          "Flow Drive [internal]"          "Browser/app driver used by Flow QA"                 "#9CA3AF" false
generate_openai_yaml "flow-next-sync"           "Flow Plan-Sync [internal]"      "Downstream task-spec sync used by Flow Work"        "#9CA3AF" false
generate_openai_yaml "flow-next-export-context" "Flow Export Context [internal]" "Context bundle export used by reviews"              "#9CA3AF" false
generate_openai_yaml "flow-next-worktree-kit"   "Flow Worktree Kit [internal]"   "Worktree helper used by Flow Work"                  "#9CA3AF" false
generate_openai_yaml "flow-next-deps"           "Flow Deps [internal]"           "Dependency-graph helper used by planning skills"    "#9CA3AF" false

# --- Deprecation redirect skills (1.0 alias surface) ---
# The last redirect alias, flow-next-epic-review, was retired on all platforms
# in fn-124 (self-declared dead since 2.0), which left the redirect generator
# with no callers — removed here. Reintroduce a generator only if a new
# deprecation alias is ever needed on the Codex mirror.

# --- Catalog description diet (surfaced skills only) ---
# Codex injects each implicit skill's SKILL.md frontmatter `description` into
# the model context verbatim (render.rs uses `description`, NOT openai.yaml's
# short_description, capped 1024 chars each) under the shared skills budget.
# Canonical descriptions are Claude-Code-length (250-700 chars, "Triggers on
# /flow-next:..." tails); at 22 surfaced skills that alone would blow the
# budget and truncate every skill on the user's machine. Rewrite the MIRROR
# frontmatter description to a tight catalog line (target <=160 chars, no
# colons so the unquoted YAML stays valid). Hidden (internal) skills keep
# their canonical descriptions - they are never injected.
# MAINTENANCE: a new user-facing skill needs an entry here; the validation
# guard below hard-fails when a surfaced skill's description exceeds 200 chars.
python3 - "$CODEX_DIR" <<'PYEOF'
import sys, pathlib
codex_dir = pathlib.Path(sys.argv[1])
DIET = {
    "flow-next-plan": "Plan a feature into a flow-next spec with tasks in .flow/. Use when asked to plan, spec out, or break down work (fn-N ids).",
    "flow-next-work": "Execute a flow-next spec or task end-to-end with worker subagents, gates, and commits. Use when asked to work on, implement, or execute fn-N.",
    "flow-next-pilot": "Single-tick autonomous build-loop conductor. Advances one ready spec one stage per tick, emits PILOT_VERDICT. Use when asked to pilot a spec or backlog.",
    "flow-next-land": "Autonomous PR babysitter tick. Fixes CI, resolves feedback, merges when converged, closes the spec, releases. Emits LAND_VERDICT. Use when asked to land PRs.",
    "flow-next-make-pr": "Open a PR with a cognitive-aid body rendered from flow-next spec state via gh. Use whenever asked to make or open a PR in a flow-next repo.",
    "flow-next-resolve-pr": "Resolve PR review feedback. Fetches unresolved threads, triages, fixes, replies and resolves via GraphQL. Use when asked to address review comments.",
    "flow-next-interview": "In-depth Q&A to refine a spec, task, or spec file before building. Use when asked to flesh out, refine, or interrogate requirements.",
    "flow-next-capture": "Synthesize the current conversation into a flow-next spec with read-back gating. Use when asked to capture this as a spec.",
    "flow-next-setup": "Install or refresh flowctl and project instructions for flow-next in this repo. Use when asked to set up flow-next.",
    "flow-next-prospect": "Generate ranked candidate ideas grounded in the repo. Use when asked what to build next.",
    "flow-next-chart": "Decision-map discovery for one oversized unclear idea before capture. Resolve one decision per invocation, brief for capture. Use when asked to chart an idea or work a chart decision.",
    "flow-next-guide": "Recommend the smallest sufficient flow-next workflow from the starting state. Stateless router. Use when unsure which command or stage applies next.",
    "flow-next-strategy": "Create or update repo-root STRATEGY.md (problem, approach, users, metrics, tracks). Use for strategy or roadmap doc requests.",
    "flow-next-audit": "Audit .flow/memory/ entries against current code and keep, update, consolidate, replace, delete, or harden each. Use when asked to audit memory or graduate a recurring lesson into a gate.",
    "flow-next-memory-migrate": "Migrate legacy flat .flow/memory files to the categorized YAML schema. One-time ceremony. Use when asked to migrate flow memory.",
    "flow-next-tracker-sync": "Project a flow-next spec to a tracker issue (Linear, GitHub, GitLab, Jira) and reconcile two-way. Use when asked to sync to a tracker. NOT plan-sync.",
    "flow-next-qa": "Live-app QA pass derived from the spec. Drives the running app, files P0/P1/P2 findings with evidence, emits a YES or NO qa_verdict receipt.",
    "flow-next-prime": "Assess codebase agent and production readiness. Classifies the project, verifies commands run, leads with a verdict and ranked next actions.",
    "flow-next-map": "Build a semantic feature index of the repo via clawpatch map (opt-in). Use when asked to map the repo.",
    "flow-next-impl-review": "Carmack-level implementation review of changes via the configured backend. Use when asked to review code or a diff in a flow-next repo.",
    "flow-next-plan-review": "Carmack-level review of a flow-next spec or plan via the configured backend. Use when asked to review a plan or spec.",
    "flow-next-spec-completion-review": "Verify that a spec's completed tasks fully implement the spec requirements. Use at spec completion before close.",
    "flow-next-ralph-init": "Scaffold the repo-local Ralph autonomous harness and project hooks. Use when asked to set up Ralph.",
    "flow-next": "Manage .flow/ tasks and specs. Use for show or list tasks, task status, what is ready, show fn-N. NOT for planning or executing (use the plan and work skills).",
}
failed = 0
for skill, desc in DIET.items():
    p = codex_dir / "skills" / skill / "SKILL.md"
    if not p.is_file():
        print(f"DIET-FAIL: {skill}/SKILL.md missing")
        failed += 1
        continue
    lines = p.read_text(encoding="utf-8").split("\n")
    done = False
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            lines[i] = f"description: {desc}"
            done = True
            break
        if i > 0 and line == "---":
            break
    if not done:
        print(f"DIET-FAIL: no description line in {skill}/SKILL.md frontmatter")
        failed += 1
        continue
    p.write_text("\n".join(lines), encoding="utf-8")
if failed:
    sys.exit(1)
print(f"  diet applied to {len(DIET)} surfaced skill descriptions")
PYEOF

# REQUIRED list — every user-facing slash-command skill MUST have an
# openai.yaml entry above. When you add a new skill, add it here AND add
# a generate_openai_yaml call. Validation will fail otherwise.
# See CLAUDE.md > "Adding a new user-facing skill" for the full checklist.
REQUIRED_OPENAI_YAML_SKILLS=(
  "flow-next-plan"
  "flow-next-work"
  "flow-next-interview"
  "flow-next-setup"
  "flow-next-prospect"
  "flow-next-capture"
  "flow-next-strategy"
  "flow-next-audit"
  "flow-next-memory-migrate"
  "flow-next-make-pr"
  "flow-next-tracker-sync"
  "flow-next-qa"
  "flow-next-pilot"
  "flow-next-land"
  "flow-next-impl-review"
  "flow-next-plan-review"
  "flow-next-spec-completion-review"
  "flow-next-resolve-pr"
  "flow-next"
  "flow-next-prime"
  "flow-next-map"
  "flow-next-visual"
  "flow-next-ralph-init"
  "flow-next-drive"
  "flow-next-sync"
  "flow-next-export-context"
  "flow-next-worktree-kit"
  "flow-next-deps"
  "flow-next-work-rolling"
)

openai_yaml_count=$(find "$CODEX_DIR/skills" -name "openai.yaml" | wc -l | tr -d ' ')
echo -e "  ${GREEN}✓${NC} $openai_yaml_count openai.yaml metadata files generated"

echo -e "  ${GREEN}✓${NC} $skill_count skills generated"

# ─── 2. Convert agents (.md → .toml) ─────────────────────────────────────────

echo -e "${BLUE}Generating agents...${NC}"
agent_count=0

for md_file in "$SRC_AGENTS"/*.md; do
  [ -f "$md_file" ] || continue
  basename_raw="$(basename "${md_file%.md}")"
  codex_name=$(rename_agent "$basename_raw")

  # Parse YAML frontmatter
  # Known keys: name/description/model map into TOML. Cursor-native `readonly:`
  # (fn-123 R4) and Claude-only keys (disallowedTools, color, user-invocable)
  # are recognized so they never leak into developer_instructions and never
  # trip a future strict-key guard. Codex enforces read-only via sandbox_mode
  # (sandbox_for), not a `readonly` TOML field — so we swallow, not emit.
  name="" description="" model=""
  in_frontmatter=0 frontmatter_done=0
  body=""

  while IFS= read -r line; do
    if [ "$frontmatter_done" = "1" ]; then
      body+="$line"$'\n'
      continue
    fi
    if [ "$line" = "---" ]; then
      if [ "$in_frontmatter" = "0" ]; then in_frontmatter=1; continue; fi
      frontmatter_done=1; continue
    fi
    if [ "$in_frontmatter" = "1" ]; then
      case "$line" in
        name:*)             name="${line#name: }"; name="${name#name:}"; name="$(echo "$name" | xargs)" ;;
        description:*)      description="${line#description: }"; description="${description#description:}"; description="$(echo "$description" | xargs)" ;;
        model:*)            model="${line#model: }"; model="${model#model:}"; model="$(echo "$model" | xargs)" ;;
        readonly:*)         ;; # Cursor-native; Codex uses sandbox_mode (tolerated, not emitted)
        disallowedTools:*)  ;; # Claude/Droid-only capability blacklist
        color:*)            ;; # Claude UI chrome
        user-invocable:*)   ;; # Claude plugin catalog flag
        ""|\#*)             ;; # blank / comment lines in frontmatter
      esac
    fi
  done < "$md_file"

  # Map model
  codex_model=$(map_model "$model" "$codex_name")
  sandbox=$(sandbox_for "$codex_name")

  # Clean body: strip leading/trailing blank lines
  body="$(echo "$body" | awk 'NF{p=1} p')"
  body="$(echo "$body" | awk '{a[NR]=$0} END{for(i=NR;i>=1;i--) if(a[i]!=""){for(j=1;j<=i;j++) print a[j]; break}}')"

  # Patch body for agents-md-scout
  if [ "$basename_raw" = "claude-md-scout" ]; then
    body="$(echo "$body" | sed \
      -e 's/CLAUDE\.md/AGENTS.md/g' \
      -e 's/claude\.md/agents.md/g' \
      -e 's/Claude Code/Codex/g')"
    description="Used by /flow-next:prime to analyze AGENTS.md quality and completeness. Do not invoke directly."
  fi

  # FLOWCTL prelude rewrite (fn-50.6): canonical agents use the
  # `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` form
  # (Droid + Claude fallback). In Codex neither env var is set, so the
  # expansion resolves to `/scripts/flowctl` — broken. Mirror the skill-side
  # rewrite (line ~183) here so generated `.toml` agent bodies use the direct
  # runtime Codex form plus the local `.flow/bin/flowctl` fallback. fn-50.3 added the
  # repo-scout `repo-map` probes that surfaced this gap.
  body="$(echo "$body" | sed -E 's|\$\{DROID_PLUGIN_ROOT:-\$\{CLAUDE_PLUGIN_ROOT\}\}/scripts/flowctl|${CODEX_HOME:-$HOME/.codex}/scripts/flowctl|g')"
  # Rewrite skill-file paths in agent bodies: neither plugin-root variable
  # resolves inside Codex; the installed mirror lives at CODEX_HOME/skills/.
  body="$(echo "$body" | sed -E 's|\$\{DROID_PLUGIN_ROOT:-\$\{CLAUDE_PLUGIN_ROOT\}\}/skills/|${CODEX_HOME:-$HOME/.codex}/skills/|g')"
  # fn-197: no fallback injection here either. Canonical agent bodies carry the
  # full three-rung chain (env var → derived plugin root → .flow/bin); only rung 1
  # is rewritten above, and rungs 2/3 mirror through untouched. Injecting after
  # the CODEX_HOME rung would now emit a duplicate `.flow/bin` line between
  # rungs 1 and 2.

  # Escape backslashes for TOML triple-quoted strings
  body="$(echo "$body" | sed 's/\\/\\\\/g')"

  # Write .toml
  toml="$CODEX_DIR/agents/$codex_name.toml"
  {
    echo "# Auto-generated by sync-codex.sh from ${basename_raw}.md — do not edit manually"
    echo "name = \"$codex_name\""
    echo "description = \"$description\""
    if [ -n "$codex_model" ]; then
      echo "model = \"$codex_model\""
      if model_supports_reasoning "$codex_model"; then
        echo "model_reasoning_effort = \"$(reasoning_effort_for "$codex_name")\""
      fi
    else
      echo "# model: inherited from parent"
    fi
    echo "sandbox_mode = \"$sandbox\""

    # Nicknames for scouts/analysts
    nicks=$(nicknames_for "$codex_name")
    if [ -n "$nicks" ]; then
      echo "nickname_candidates = $nicks"
    fi

    echo ""
    echo "developer_instructions = \"\"\""
    echo "$body"
    echo "\"\"\""
  } > "$toml"

  agent_count=$((agent_count + 1))
done

echo -e "  ${GREEN}✓${NC} $agent_count agents generated"

# ─── 3. Hooks (none by default; fn-114) ───────────────────────────────────────
# Codex mirror ships ZERO hooks. Plugin hooks/ is gone; Ralph guard registration
# is agent-driven via /flow-next:ralph-init into project .codex/hooks.json.
# Remove any stale mirror hooks.json left from older sync runs.
echo -e "${BLUE}Hooks: zero-default (no codex/hooks.json)...${NC}"
if [ -f "$CODEX_DIR/hooks.json" ]; then
  rm -f "$CODEX_DIR/hooks.json"
  echo -e "  ${GREEN}✓${NC} removed stale codex/hooks.json"
else
  echo -e "  ${GREEN}✓${NC} no codex/hooks.json (correct)"
fi

# ─── Validation ───────────────────────────────────────────────────────────────

echo -e "${BLUE}Validating...${NC}"
errors=0

# Count skills
actual_skills=$(find "$CODEX_DIR/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
if [ "$actual_skills" != "$skill_count" ]; then
  echo -e "  ${RED}✗${NC} Expected $skill_count skills, found $actual_skills"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} $actual_skills skills"
fi

# Count agents
actual_agents=$(find "$CODEX_DIR/agents" -name "*.toml" | wc -l | tr -d ' ')
if [ "$actual_agents" != "$agent_count" ]; then
  echo -e "  ${RED}✗${NC} Expected $agent_count agents, found $actual_agents"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} $actual_agents agents"
fi

# Validate TOML files parse (basic: check for required keys)
toml_errors=0
for toml in "$CODEX_DIR/agents"/*.toml; do
  if ! grep -q 'developer_instructions' "$toml" 2>/dev/null; then
    echo -e "  ${RED}✗${NC} $(basename "$toml") missing developer_instructions"
    toml_errors=$((toml_errors + 1))
  fi
done
if [ "$toml_errors" -eq 0 ]; then
  echo -e "  ${GREEN}✓${NC} All .toml files have required keys"
else
  errors=$((errors + toml_errors))
fi

# Assert no default hooks.json in the Codex mirror (fn-114 zero-default)
if [ -f "$CODEX_DIR/hooks.json" ]; then
  echo -e "  ${RED}✗${NC} codex/hooks.json must not ship (Ralph is opt-in via ralph-init)"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} no codex/hooks.json (zero-default)"
fi

# Check no bare CLAUDE_PLUGIN_ROOT without fallback in skills
bare_refs=$( { grep -r 'CLAUDE_PLUGIN_ROOT}/' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v 'CLAUDE_PLUGIN_ROOT:-' || true; } | { grep -v '\.codex' || true; } | wc -l | tr -d ' ')
if [ "$bare_refs" != "0" ]; then
  echo -e "  ${YELLOW}!${NC} $bare_refs bare CLAUDE_PLUGIN_ROOT refs (may need patching)"
else
  echo -e "  ${GREEN}✓${NC} No bare CLAUDE_PLUGIN_ROOT refs"
fi

# Check no plugin-root /skills/ path refs survive (must be rewritten to
# ${CODEX_HOME:-$HOME/.codex}/skills/ or a specific destination — an unrewritten ref expands
# to a broken /skills/... path inside Codex where neither var is set)
skills_refs=$( { grep -rE '(DROID_PLUGIN_ROOT|CLAUDE_PLUGIN_ROOT|\$PLUGIN_ROOT)[^[:space:]]*/skills/' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$skills_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $skills_refs unrewritten plugin-root /skills/ path refs in codex/skills/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No unrewritten plugin-root /skills/ path refs"
fi

# Check no "Task flow-next:" in codex skills
task_refs=$( { grep -r 'Task flow-next:' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$task_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $task_refs 'Task flow-next:' refs remain in codex/skills/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No 'Task flow-next:' refs"
fi

# Check no "/flow-next:" slash-command tokens in the mirrored usage.md template —
# it is what `flowctl usage` prints on Codex, where commands resolve as
# `$flow-next-<cmd>`, not `/flow-next:<cmd>`. The targeted rewrite above must
# have converted every token.
usage_slash_refs=$( { grep -c '/flow-next:' "$CODEX_DIR/templates/usage.md" 2>/dev/null || true; } | tr -d ' ')
[ -n "$usage_slash_refs" ] || usage_slash_refs=0
if [ "$usage_slash_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $usage_slash_refs '/flow-next:' refs remain in codex templates/usage.md — should be \$flow-next-<cmd>"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No '/flow-next:' refs in codex templates/usage.md"
fi

# fn-197: setup is copy-less on every host — the mirror must ship the converged
# snippet template and must not resurrect a copy step or a mode ceremony.
if [ -f "$CODEX_DIR/skills/flow-next-setup/templates/agents-md-snippet.md" ]; then
  echo -e "  ${GREEN}✓${NC} Converged AGENTS.md snippet template present in mirror"
else
  echo -e "  ${RED}✗${NC} Converged AGENTS.md snippet template missing from mirror"
  errors=$((errors + 1))
fi

copy_refs=$( { grep -cE '^## Step 3: Create \.flow/bin/|setup-mode set|Copy mode only' "$CODEX_DIR/skills/flow-next-setup/workflow.md" 2>/dev/null || true; } | tr -d ' ')
[ -n "$copy_refs" ] || copy_refs=0
if [ "$copy_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} copy-mode setup machinery leaked into the codex mirror setup workflow (refs=$copy_refs)"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No copy-mode setup machinery in codex setup workflow"
fi

# fn-126 R4: mirror Step-0 detection bash must be unconditional PLATFORM=codex
# (no multi-host cascade — Codex always reads this mirror as PLATFORM=codex).
# Scope: the first ```bash fence under the Step 0 heading only (prose may still
# mention host signals for documentation; the executable detection block must not).
setup_mirror_wf="$CODEX_DIR/skills/flow-next-setup/workflow.md"
if [ -f "$setup_mirror_wf" ]; then
  det_block=$(awk '
    /^## Step 0: Resolve plugin path and detect platform/ {in_s0=1; next}
    in_s0 && /^## / {exit}
    in_s0 && /^```bash$/ {grab=1; next}
    grab && /^```$/ {exit}
    grab {print}
  ' "$setup_mirror_wf")
  det_bad=0
  # Fail-CLOSED (codex impl-review): the executable content must be EXACTLY the
  # single `PLATFORM="codex"` assignment. Strip comment/blank lines, then require
  # the remainder to equal that one line — so ANY future branch (new signal,
  # if/case, extra assignment) fails, not just the four named signals.
  det_exec=$(printf '%s\n' "$det_block" | sed 's/#.*$//' | grep -vE '^[[:space:]]*$' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [ "$det_exec" != 'PLATFORM="codex"' ]; then
    echo -e "  ${RED}✗${NC} codex mirror setup Step-0 executable content is not exactly 'PLATFORM=\"codex\"' (fn-126 R4 — must be unconditional; got: $(printf '%s' "$det_exec" | tr '\n' '|'))"
    det_bad=1
  fi
  if [ "$det_bad" = "0" ]; then
    echo -e "  ${GREEN}✓${NC} Codex mirror setup Step-0 is unconditional PLATFORM=codex (no host-detection branches)"
  else
    errors=$((errors + 1))
  fi
else
  echo -e "  ${RED}✗${NC} codex mirror setup workflow missing — cannot validate Step-0 (fn-126 R4)"
  errors=$((errors + 1))
fi

# Check no "AskUserQuestion" or "ToolSearch select:AskUserQuestion" in codex
# skill prose — should all have been rewritten to the plain-text numbered
# prompt by Stage 3 (fn-45). Bare AskUserQuestion in the Codex skill prose
# is a sync bug.
# Exclude templates/ subdirs (those are user-script templates, not skill prose
# that the agent reads — e.g., ralph-init/templates/watch-filter.py uses the
# tool name as a dict key for hook event emoji mapping, which is intentional).
askq_refs=$( { grep -rE 'AskUserQuestion|ToolSearch select:AskUserQuestion' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$askq_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $askq_refs Claude-native tool refs (AskUserQuestion / ToolSearch) remain in codex skill prose — extend sync transforms"
  { grep -rnE 'AskUserQuestion|ToolSearch select:AskUserQuestion' "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-native tool refs in Codex skill prose"
fi

# fn-197: the three-rung FLOWCTL chain must reach the mirror intact — rung 1
# rewritten to the CODEX_HOME form, then the derived-plugin-root rung, then the
# `.flow/bin` rung exactly once. This guard is the pair of the deleted fallback
# injectors: with the canonical text carrying all three rungs, the failure mode
# flipped from "missing rung" to "duplicated rung".
# Scope: skill/agent PROSE only. `templates/` holds self-contained user scripts
# (ralph's harness resolves its own sibling launcher, never the plugin root).
chain_problems=$( { grep -rlE '^[[:space:]]*FLOWCTL=' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | while read -r cf; do
  [ -f "$cf" ] || continue
  awk -v file="$cf" '
    function strip(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
    /^[[:space:]]*FLOWCTL=/ { want = 2; next }
    want == 2 {
      # Full-line equality (same style as the rung-3 check below): the probe-proven
      # rung-2 wording is byte-identical everywhere, trailing comment included. A
      # prefix match would accept a truncated or reworded tail.
      if (strip($0) != "[ -x \"$FLOWCTL\" ] || FLOWCTL=\"<plugin-root>/scripts/flowctl\"   # <plugin-root> = the directory two levels above this skill'"'"'s SKILL.md file (the harness gave you that file'"'"'s absolute path when the skill loaded); substitute it literally")
        print file ":" NR ": rung 2 (derived plugin root) missing or reworded after FLOWCTL="
      want = 1; next
    }
    want == 1 {
      if (strip($0) != "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\"")
        print file ":" NR ": rung 3 (.flow/bin) missing after rung 2"
      want = 0; prev_rung3 = 1; next
    }
    {
      if (prev_rung3 && strip($0) == "[ -x \"$FLOWCTL\" ] || FLOWCTL=\".flow/bin/flowctl\"")
        print file ":" NR ": duplicate .flow/bin fallback rung"
      prev_rung3 = 0
    }
  ' "$cf"
done )
if [ -n "$chain_problems" ]; then
  echo -e "  ${RED}✗${NC} FLOWCTL resolution chain broken in the codex mirror:"
  printf '%s\n' "$chain_problems" | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} Three-rung FLOWCTL chain intact in codex mirror (no duplicate fallback rungs)"
fi

# fn-100 R12: the Claude-native fact-scout dispatch phrase must not survive in
# the mirror — the Explore-dispatch transform above rewrites it to
# `spawn_agent` with `agent_type: explorer`. Exact-phrase match: the
# "`Task` tool with" variants in cross-platform tables are deliberate
# documentation of the Claude Code naming and are excluded by construction.
scout_refs=$( { grep -r '`Task` with `subagent_type: Explore`' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$scout_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $scout_refs Claude-native Explore-dispatch refs remain in codex skill prose — Explore-dispatch transform (fn-100 R12) should have rewritten these"
  { grep -rn '`Task` with `subagent_type: Explore`' "$CODEX_DIR/skills/" 2>/dev/null || true; } | head -5
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-native Explore-dispatch refs in Codex skill prose"
fi

# fn-202 (#363 codex P2 + P1): every relative `docs/` markdown link in mirror
# skill prose must carry the owned `flow-next/` namespace segment AND resolve
# on disk under `codex/docs/flow-next/` (mirrored above, md-only) — the only
# docs dir install-codex.sh may replace. Fails on an un-namespaced link (the
# namespace transform missed a new link depth), a double-applied segment
# (`docs/flow-next/flow-next/`), or a link pointing at a nonexistent file
# (e.g. a canonical link to a doc that is not markdown, or a docs/ file
# deleted upstream).
docs_link_problems=$( { grep -rno '](\(\.\./\)\{1,\}docs/[^)#]*' "$CODEX_DIR/skills/" 2>/dev/null || true; } | while IFS=: read -r lf ln match; do
  target="${match#](}"
  # Leading `(` on each pattern: required for `case` inside `$( )` under
  # macOS /bin/bash 3.2 (the shebang), which otherwise fails to parse at the
  # bare `pattern)` form. Semantics unchanged.
  case "$target" in
    (*docs/flow-next/flow-next/*) echo "$lf:$ln: docs-link namespace applied twice → $target"; continue ;;
    (*docs/flow-next/*) ;;
    (*) echo "$lf:$ln: docs link missing the flow-next/ namespace → $target"; continue ;;
  esac
  [ -f "$(dirname "$lf")/$target" ] || echo "$lf:$ln: broken relative docs link → $target"
done )
if [ -n "$docs_link_problems" ]; then
  echo -e "  ${RED}✗${NC} bad relative docs links in codex skill prose — extend the namespaced docs-link transform:"
  printf '%s\n' "$docs_link_problems" | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} All relative docs links in codex skill prose are namespaced and resolve"
fi

# fn-202 (#363 codex P2, round 5): link-closure property for the docs mirror.
# Every markdown link in codex/docs/flow-next/** must either (a) resolve on
# disk within the mirror tree at its mirror location, or (b) be an absolute
# http(s) URL. Any other link hard-fails the sync — it dangles in-repo or
# installed (or both). Because install-codex.sh copies codex/skills/,
# codex/templates/, codex/references/, and codex/docs/flow-next/ verbatim to
# the SAME relative layout under $CODEX_HOME, the on-disk check against the
# repo mirror IS the installed-layout check — one tree, two locations, same
# relative geometry. Fence-aware (fenced code blocks carry link-shaped
# placeholders like `[link](path)`); inline-code fragments (backticks) and
# space-bearing pseudo-targets are prose, not links, and are skipped.
docs_closure_problems=$(python3 - "$CODEX_DIR/docs/flow-next" <<'PYEOF'
import os, re, sys
root = sys.argv[1]
link_re = re.compile(r'\]\(([^)]*)\)')
for dirpath, _dirs, files in os.walk(root):
    for name in sorted(files):
        if not name.endswith('.md'):
            continue
        path = os.path.join(dirpath, name)
        in_fence = False
        with open(path, encoding='utf-8') as fp:
            for ln, line in enumerate(fp, 1):
                if re.match(r'\s*(```|~~~)', line):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                for m in link_re.finditer(line):
                    target = m.group(1)
                    if target.startswith(('http://', 'https://', '#')):
                        continue
                    if not target or '`' in target or ' ' in target:
                        continue  # inline-code fragment / prose, not a link
                    rel = target.split('#', 1)[0]
                    if not rel:
                        continue
                    if not os.path.isfile(os.path.normpath(os.path.join(dirpath, rel))):
                        rp = os.path.relpath(path, root)
                        print(f"{rp}:{ln}: docs-mirror link neither resolves on disk nor absolute URL -> {target}")
PYEOF
)
if [ -n "$docs_closure_problems" ]; then
  echo -e "  ${RED}✗${NC} docs-mirror link universe not closed — extend the docs-mirror link transform above:"
  printf '%s\n' "$docs_closure_problems" | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} Docs-mirror link universe closed (every link resolves on disk or is an absolute URL)"
fi

# fn-202 (#363 codex P2): the `Recommended next:` footer template is a
# copy-pasteable invocation — on Codex it must carry the `$flow-next-<stage>`
# form. A `/flow-next:` spelling here means a new/renamed footer surface missed
# the actionable next-step transform above — extend that file list, don't
# blanket-sed (passive doc mentions legitimately keep `/flow-next:`).
recnext_refs=$( { grep -rn 'Recommended next: /flow-next:' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$recnext_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $recnext_refs 'Recommended next: /flow-next:' template lines remain in codex skill prose — extend the actionable next-step transform"
  { grep -rn 'Recommended next: /flow-next:' "$CODEX_DIR/skills/" 2>/dev/null || true; } | head -5
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} Recommended-next templates use \$flow-next-<stage> in Codex skill prose"
fi

# fn-205.5 (#364): closer-roster expected-output guard. For every file in the
# actionable next-step transform roster above, its inventoried copy-pasteable
# closer literals must appear in the mirror ONLY in rewritten ($flow-next-)
# form. Each entry is one anchored fixed-string check, tab-separated:
# mirror-relative path <TAB> forbidden colon-form anchor <TAB> expected
# rewritten literal. The forbidden anchor must be ABSENT (a hit means a
# canonical closer literal was reworded without moving its transform anchor —
# the sed silently stopped matching at exit 0 — or a new roster file missed
# the transform) AND the expected rewritten literal must be PRESENT (fn-205.6,
# routed .5 review P2: absence alone cannot see a sed whose anchor broke when
# the canonical text ALSO changed — both greps miss the reworded line; the
# positive half fails the sync instead of staling the mirror at exit 0).
# Fix the content or extend the transform, NEVER relax this guard.
# Deliberately NOT a whole-mirror semantic grep: passive /flow-next:
# mentions across ~90 mirror files must stay untouched and unflagged. New
# closer files enter coverage by joining the roster above AND this list;
# future closers are caught at review time by the conduct checklists.
closer_literal_fails=0
while IFS="$(printf '\t')" read -r rel pat expect; do
  [ -n "$rel" ] || continue
  cf="$CODEX_DIR/skills/$rel"
  if [ ! -f "$cf" ]; then
    echo -e "  ${RED}✗${NC} closer-roster file missing from mirror: skills/$rel"
    closer_literal_fails=$((closer_literal_fails + 1))
    continue
  fi
  if grep -qF "$pat" "$cf"; then
    echo -e "  ${RED}✗${NC} un-rewritten closer literal in skills/$rel: $pat"
    closer_literal_fails=$((closer_literal_fails + 1))
  fi
  if [ -n "$expect" ] && ! grep -qF "$expect" "$cf"; then
    echo -e "  ${RED}✗${NC} expected rewritten closer literal missing from skills/$rel: $expect"
    closer_literal_fails=$((closer_literal_fails + 1))
  fi
done <<'CLOSER_ROSTER'
flow-next-capture/workflow.md	  /flow-next:plan <SPEC_ID>	  $flow-next-plan <SPEC_ID>
flow-next-capture/workflow.md	  /flow-next:interview <SPEC_ID>	  $flow-next-interview <SPEC_ID>
flow-next-capture/workflow.md	  /flow-next:visual <SPEC_ID>	  $flow-next-visual <SPEC_ID>
flow-next-capture/references/rewrite-mode.md	  /flow-next:plan <SPEC_ID>	  $flow-next-plan <SPEC_ID>
flow-next-capture/references/rewrite-mode.md	  /flow-next:interview <SPEC_ID>	  $flow-next-interview <SPEC_ID>
flow-next-capture/references/rewrite-mode.md	  /flow-next:visual <SPEC_ID>	  $flow-next-visual <SPEC_ID>
flow-next-capture/references/split-proposal.md	; /flow-next:interview <id> can still split later	; $flow-next-interview <id> can still split later
flow-next-plan/references/next-steps-menu.md	`/flow-next:work fn-N-slug`	`$flow-next-work fn-N-slug`
flow-next-plan/references/next-steps-menu.md	`/flow-next:interview fn-N-slug`	`$flow-next-interview fn-N-slug`
flow-next-plan/references/next-steps-menu.md	`/flow-next:plan-review fn-N-slug`	`$flow-next-plan-review fn-N-slug`
flow-next-work/phases.md	Next: /flow-next:make-pr <spec-id>	Next: $flow-next-make-pr <spec-id>
flow-next-make-pr/create-and-finalize.md	Reviewer feedback → /flow-next:resolve-pr	Reviewer feedback → $flow-next-resolve-pr
flow-next-make-pr/create-and-finalize.md	Body inspection → /flow-next:make-pr	Body inspection → $flow-next-make-pr
flow-next-make-pr/create-and-finalize.md	Reviewer should run: /flow-next:resolve-pr	Reviewer should run: $flow-next-resolve-pr
flow-next-make-pr/create-and-finalize.md	re-run /flow-next:make-pr (skill detects	re-run $flow-next-make-pr (skill detects
flow-next-make-pr/create-and-finalize.md	An OPEN PR exists. /flow-next:resolve-pr	An OPEN PR exists. $flow-next-resolve-pr
flow-next-interview/SKILL.md	→ `/flow-next:plan fn-N`	→ `$flow-next-plan fn-N`
flow-next-interview/SKILL.md	→ `/flow-next:work fn-N` (or more interview	→ `$flow-next-work fn-N` (or more interview
flow-next-interview/SKILL.md	→ `/flow-next:work fn-N.M`	→ `$flow-next-work fn-N.M`
flow-next-interview/SKILL.md	→ `/flow-next:plan <file>`	→ `$flow-next-plan <file>`
flow-next-interview/SKILL.md	`/flow-next:visual fn-N` for a spec input	`$flow-next-visual fn-N` for a spec input
flow-next-interview/SKILL.md	`/flow-next:visual fn-N.M` for a task input	`$flow-next-visual fn-N.M` for a task input
flow-next-interview/SKILL.md	`/flow-next:visual <file-path>` for the file input	`$flow-next-visual <file-path>` for the file input
flow-next-interview/references/write-back.md	Run `/flow-next:plan fn-N` to research	Run `$flow-next-plan fn-N` to research
flow-next-interview/references/write-back.md	then suggest `/flow-next:plan`.	then suggest `$flow-next-plan`.
flow-next-interview/references/write-back.md	instead: `/flow-next:interview <spec-id>`	instead: `$flow-next-interview <spec-id>`
flow-next-interview/references/write-back.md	suggest `/flow-next:plan <file>` to create spec + tasks	suggest `$flow-next-plan <file>` to create spec + tasks
flow-next-prospect/workflow.md	(ask /flow-next:interview what to refine)	(ask $flow-next-interview what to refine)
flow-next-prospect/workflow.md	Run /flow-next:chart on the selected survivor	Run $flow-next-chart on the selected survivor
flow-next-prospect/workflow.md	Run /flow-next:interview <spec-or-task-id> to refine	Run $flow-next-interview <spec-or-task-id> to refine
flow-next-chart/references/briefing-and-reopen.md	running `/flow-next:capture .flow/charts/	running `$flow-next-capture .flow/charts/
flow-next-chart/references/chart-mode.md	Recommend `/flow-next:capture` or authoring	Recommend `$flow-next-capture` or authoring
flow-next-chart/references/chart-mode.md	separate `/flow-next:chart <id>` (or pinned) invocations	separate `$flow-next-chart <id>` (or pinned) invocations
flow-next-audit/SKILL.md	recommends `/flow-next:memory-migrate` first	recommends `$flow-next-memory-migrate` first
flow-next-audit/SKILL.md	`/flow-next:memory-migrate` first to make these auditable	`$flow-next-memory-migrate` first to make these auditable
flow-next-audit/workflow.md	`/flow-next:memory-migrate` first to make these auditable	`$flow-next-memory-migrate` first to make these auditable
flow-next-guide/SKILL.md	| `/flow-next:strategy`	| `$flow-next-strategy`
flow-next-guide/SKILL.md	| `/flow-next:prospect`	| `$flow-next-prospect`
flow-next-guide/SKILL.md	| `/flow-next:chart`	| `$flow-next-chart`
flow-next-guide/SKILL.md	| `/flow-next:capture`	| `$flow-next-capture`
flow-next-guide/SKILL.md	| `/flow-next:interview`	| `$flow-next-interview`
flow-next-guide/SKILL.md	| `/flow-next:plan`	| `$flow-next-plan`
flow-next-guide/SKILL.md	| `/flow-next:work`	| `$flow-next-work`
flow-next-guide/SKILL.md	| `/flow-next:visual`	| `$flow-next-visual`
CLOSER_ROSTER
if [ "$closer_literal_fails" != "0" ]; then
  echo -e "  ${RED}✗${NC} $closer_literal_fails un-rewritten closer literal(s) — a transform anchor no longer matches its canonical text"
  errors=$((errors + closer_literal_fails))
else
  echo -e "  ${GREEN}✓${NC} Closer-roster literals all appear in rewritten \$flow-next- form"
fi

# fn-50.6 symmetry rule: agent toml bodies must not carry unrewritten
# plugin-root /skills/ paths - the agents-pipeline rewrite maps them to
# ${CODEX_HOME:-$HOME/.codex}/skills/. The skills-side guard above has no agents coverage.
agent_skill_refs=$( { grep -rE '(DROID_PLUGIN_ROOT|CLAUDE_PLUGIN_ROOT|\$PLUGIN_ROOT)[^[:space:]]*/skills/' "$CODEX_DIR/agents/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$agent_skill_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $agent_skill_refs unrewritten plugin-root /skills/ path refs in codex/agents/"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No unrewritten plugin-root /skills/ path refs in codex/agents/"
fi

# fn-156 R2: executable Codex-home paths must remain portable across multiple
# Codex homes. The runtime form is allowed; these exact prose snippets only
# describe the default location and are never evaluated by a shell. Keep the
# allowlist narrow so a newly baked primary-home path fails closed.
is_narrative_primary_home_ref() {
  case "$1" in
    *'sync-codex.sh rewrites it to `$HOME/.codex/scripts/flowctl` for the Codex mirror'* | \
    *'`config.toml` (`$CODEX_HOME`, default `~/.codex`)'* | \
    *'`agents/` (`$CODEX_HOME`, default `~/.codex`)'* | \
    *'**There is NO "defer to `~/.codex/config.toml`"'* | \
    *'> `[mcp_servers]` configured in `~/.codex/config.toml`, a `codex exec'* | \
    *'a pure `~/.codex` install'* | \
    *'under `$CODEX_HOME` (default `~/.codex`)'* | \
    *'under `$CODEX_HOME` / `~/.codex` with inherited `CURSOR_AGENT`'*)
      return 0
      ;;
  esac
  return 1
}

primary_home_refs=0
while IFS= read -r primary_home_ref; do
  stripped_primary_home_ref=$(printf '%s\n' "$primary_home_ref" | sed 's|\${CODEX_HOME:-\$HOME/\.codex}||g')
  if ! printf '%s\n' "$stripped_primary_home_ref" | grep -Eq '\$HOME/\.codex|~/\.codex'; then
    continue
  fi
  if is_narrative_primary_home_ref "$primary_home_ref"; then
    continue
  fi
  echo -e "  ${RED}✗${NC} executable primary-home reference escaped CODEX_HOME rewrite: $primary_home_ref"
  primary_home_refs=$((primary_home_refs + 1))
done < <(grep -rnE '\$HOME/\.codex|~/\.codex' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" "$CODEX_DIR/references/" "$CODEX_DIR/templates/" 2>/dev/null || true)
if [ "$primary_home_refs" != "0" ]; then
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No executable primary-home references escaped CODEX_HOME rewrite"
fi

# fn-100 R12 follow-up: the Claude-specific scout-tier example "(sonnet on
# Claude Code)" must read platform-neutral in the mirror — the transform above
# rewrites it to "(the host's mid-tier)".
tier_refs=$( { grep -r '(sonnet on Claude Code)' "$CODEX_DIR/skills/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$tier_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $tier_refs Claude-specific scout-tier example(s) remain in codex skill prose — the tier-example transform should have rewritten these"
  { grep -rn '(sonnet on Claude Code)' "$CODEX_DIR/skills/" 2>/dev/null || true; } | head -5
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No Claude-specific scout-tier examples in Codex skill prose"
fi

# R6 mirror scan — `request_user_input` must NOT leak into the Codex mirror
# (fn-45). The Codex Default-mode + CLI surface errors on `request_user_input`
# calls (openai/codex #10384, #11536, #12694). Stage 3 instructs the agent to
# render a plain-text numbered prompt instead; any surviving reference is a
# sync bug that would re-introduce the failure. Exclude /templates/ subdirs.
# Patterns: backticked invocation, "tool" form, function-call form, the two
# hard-mandate phrasings that survived the old `request_user_input` rewrite
# era, AND `allowed-tools:` frontmatter listings (v1.1.7 — fn-45 originally
# exempted these as "harmless residue", but agents trust the frontmatter
# tool list and call the unavailable tool).
RUI_PATTERN='`request_user_input`|request_user_input tool|request_user_input\(|MUST use `request_user_input`|ONLY ask via `request_user_input`|^allowed-tools:.*\brequest_user_input\b'
rui_refs=$( { grep -rnE "$RUI_PATTERN" "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$rui_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $rui_refs request_user_input refs leaked into codex skill prose — Stage 3 (fn-45) should have rewritten these"
  { grep -rnE "$RUI_PATTERN" "$CODEX_DIR/skills/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | head -10
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No request_user_input refs in Codex skill prose"
fi

# R17 mirror scan — DDD vocabulary guard for the Codex mirror (fn-38 task 7).
# Canonical clean + mechanical rewrite should keep mirror clean, but a derived
# artifact deserves its own validation. Pattern strings are the authoritative
# forbidden list — see CLAUDE.md / fn-38 spec for rationale.
ddd_refs=$( { grep -rE 'ubiquitous language|bounded context|domain expert|aggregate root' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$ddd_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $ddd_refs R17 forbidden-vocabulary refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R17 forbidden vocabulary in Codex mirror"
fi

# R4 mirror scan — no early-design meta-file references leaked into mirror.
meta_refs=$( { grep -rE 'GLOSSARY-MAP\.md|CONTEXT-MAP\.md' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$meta_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $meta_refs R4 meta-file refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R4 meta-file refs in Codex mirror"
fi

# R19 mirror scan — strategy-doc fluff guard for the Codex mirror (fn-39 task 5).
# Tier 1 jargon only — Rumelt's "fluff" hallmarks. Scope is the Codex mirror
# of the strategy skill; references/interview.md is excluded (must describe
# anti-patterns to push back on them — same exemption as the canonical guard).
fluff_refs=$( { grep -rEi '\bsynergy\b|\bpivot\b|\bdisrupt\b|thought[ -]leadership|best-in-class|world-class|\b10x\b' "$CODEX_DIR/skills/flow-next-strategy/" 2>/dev/null || true; } | { grep -v '/references/interview\.md' || true; } | wc -l | tr -d ' ')
if [ "$fluff_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $fluff_refs R19 strategy-doc fluff refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R19 strategy-doc fluff in Codex mirror"
fi

# R30 mirror scan — alias-vocabulary guard for the Codex mirror (fn-43 task 14).
# Catch fresh prose that uses the legacy `flowctl epic*` CLI surface instead
# of canonical 1.0 `flowctl spec*`. Lines describing deprecation / alias /
# legacy semantics are excluded — these legitimately reference the legacy
# form. references/ files are also excluded (anti-pattern documentation).
alias_refs=$( { grep -rE 'flowctl epic\b|flowctl epics\b|--epic\b|--epics-file\b|--section epic\b|\bEPICS_FILE\b' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -vE '/references/' || true; } | { grep -vE 'deprecat|legacy|alias|_emit_rename_|removed in 2\.0|flow-next 1\.0 renamed|R31|R30|fn-43|\bT[0-9]+\b' || true; } | { grep -vE '^[^:]+:[0-9]+:[[:space:]]+"--(epic|epics-file|epic-title)",?[[:space:]]*$' || true; } | wc -l | tr -d ' ')
if [ "$alias_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $alias_refs R30 legacy CLI vocabulary refs in codex mirror — clean canonical first, then re-run sync"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R30 legacy CLI vocabulary in Codex mirror"
fi

# R21 canonical scan — spec-template duplication guard (fn-44 task 1).
# The canonical spec template at `plugins/flow-next/templates/spec.md` is
# the single source of truth for the 7-section spec structure. Any other
# skill markdown file that inline-duplicates the canonical sequence is a
# drift hazard — the template owns the section list; skills cross-link.
#
# Detection: ANY `*.md` under `plugins/flow-next/skills/*/` (not just
# SKILL.md — also workflow.md, phases.md, steps.md, examples.md, ...)
# containing `^## Goal & Context` followed within 30 lines by both
# `^## Architecture & Data Models` AND `^## API Contracts` triggers an
# error. The template at `plugins/flow-next/templates/spec.md` is the
# only allowed location for the full canonical sequence.
#
# False-positive avoidance: skills that legitimately quote the section
# names in isolation (e.g., a question bank or a reference file) won't
# trip the guard because the three headers must co-occur within a 30-line
# window AND each must be at column 1 (`^## `). Single-mention references
# pass through fine.
CANONICAL_SKILLS_DIR="plugins/flow-next/skills"
spec_template_dup_hits=""
if [ -d "$CANONICAL_SKILLS_DIR" ]; then
  # One awk pass per file: scan for `^## Goal & Context`; on a hit, look
  # ahead 30 lines for both `^## Architecture & Data Models` AND
  # `^## API Contracts`. If both co-occur in the window, print the file
  # and the line number of the Goal & Context marker. Single-mention
  # references won't trip — all three headers must co-occur at column 1.
  spec_template_dup_hits=$(find "$CANONICAL_SKILLS_DIR" -name "*.md" -type f 2>/dev/null \
    | xargs -I {} awk '
        FNR == NR { lines[FNR] = $0; total = FNR }
        END {
          for (i = 1; i <= total; i++) {
            if (lines[i] ~ /^## Goal & Context/) {
              arch = 0; api = 0
              for (j = i + 1; j <= i + 30 && j <= total; j++) {
                if (lines[j] ~ /^## Architecture & Data Models/) arch = 1
                if (lines[j] ~ /^## API Contracts/) api = 1
              }
              if (arch && api) {
                printf "%s:%d\n", FILENAME, i
              }
            }
          }
        }
      ' {} 2>/dev/null)
fi
if [ -n "$spec_template_dup_hits" ]; then
  spec_template_dup_count=$(printf '%s\n' "$spec_template_dup_hits" | wc -l | tr -d ' ')
  echo -e "  ${RED}✗${NC} $spec_template_dup_count R21 spec-template duplication(s) in canonical skill markdown:"
  printf '%s\n' "$spec_template_dup_hits" | sed 's/^/    /'
  echo -e "    Canonical template lives at plugins/flow-next/templates/spec.md."
  echo -e "    Replace the duplicated section list with a cross-link."
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} No R21 spec-template duplication in canonical skill markdown"
fi

# Validate openai.yaml files — every skill in REQUIRED_OPENAI_YAML_SKILLS
# MUST have one. Missing entries fail CI. Extras are fine (utility skills
# may opt in later).
yaml_missing=0
for required_skill in "${REQUIRED_OPENAI_YAML_SKILLS[@]}"; do
  yf="$CODEX_DIR/skills/$required_skill/agents/openai.yaml"
  if [ ! -f "$yf" ]; then
    echo -e "  ${RED}✗${NC} REQUIRED $required_skill/agents/openai.yaml missing — add a generate_openai_yaml call (see CLAUDE.md > Adding a new user-facing skill)"
    yaml_missing=$((yaml_missing + 1))
  fi
done
if [ "$yaml_missing" -eq 0 ]; then
  yaml_count=$(find "$CODEX_DIR/skills" -name "openai.yaml" | wc -l | tr -d ' ')
  echo -e "  ${GREEN}✓${NC} All ${#REQUIRED_OPENAI_YAML_SKILLS[@]} required skills have openai.yaml ($yaml_count total)"
else
  errors=$((errors + yaml_missing))
fi

# Validate openai.yaml content (each must have interface + policy keys)
yaml_errors=0
for yf in $(find "$CODEX_DIR/skills" -name "openai.yaml"); do
  if ! grep -q 'interface:' "$yf" || ! grep -q 'policy:' "$yf"; then
    echo -e "  ${RED}✗${NC} $(dirname "$(dirname "$yf")" | xargs basename)/agents/openai.yaml missing required keys"
    yaml_errors=$((yaml_errors + 1))
  fi
done

# Catalog-policy guard: EVERY mirror skill must declare an explicit
# allow_implicit_invocation - Codex defaults ABSENT to true, so a skill
# without one silently lands in every session's shared skill catalog
# (that inversion shipped for months: internals injected, user verbs hidden).
for sd in "$CODEX_DIR/skills"/*/; do
  sname=$(basename "$sd")
  if ! grep -q 'allow_implicit_invocation:' "$sd/agents/openai.yaml" 2>/dev/null; then
    echo -e "  ${RED}✗${NC} $sname has no explicit allow_implicit_invocation (Codex defaults ABSENT to true) - add a generate_openai_yaml call"
    yaml_errors=$((yaml_errors + 1))
  fi
done

# Catalog-budget guard: surfaced (implicit true) skills' mirror descriptions
# are injected verbatim into the shared skills context budget (min(8000 chars,
# 2% of window)); the diet pass above must keep each <=200 chars.
for sd in "$CODEX_DIR/skills"/*/; do
  sname=$(basename "$sd")
  grep -q 'allow_implicit_invocation: true' "$sd/agents/openai.yaml" 2>/dev/null || continue
  dlen=$(awk '/^description:/{sub(/^description: */,""); print length($0); exit}' "$sd/SKILL.md" 2>/dev/null)
  if [ -z "$dlen" ] || [ "$dlen" -gt 200 ]; then
    echo -e "  ${RED}✗${NC} $sname is surfaced in the model catalog but its description is ${dlen:-missing} chars (max 200) - add/trim its DIET entry"
    yaml_errors=$((yaml_errors + 1))
  fi
done

if [ "$yaml_errors" -eq 0 ]; then
  echo -e "  ${GREEN}✓${NC} All openai.yaml files have required keys, explicit catalog policy, and dieted surfaced descriptions"
else
  errors=$((errors + yaml_errors))
fi

# Check claude-md-scout renamed (exclude provenance comments in .toml headers,
# and the untransformed docs/ mirror — platforms.md documents the rename itself)
claude_md_refs=$( { grep -r 'claude-md-scout' "$CODEX_DIR/" 2>/dev/null || true; } | { grep -v '# Auto-generated' || true; } | { grep -v "^$CODEX_DIR/docs/" || true; } | wc -l | tr -d ' ')
if [ "$claude_md_refs" != "0" ]; then
  echo -e "  ${RED}✗${NC} $claude_md_refs 'claude-md-scout' refs remain"
  errors=$((errors + 1))
else
  echo -e "  ${GREEN}✓${NC} claude-md-scout fully renamed to agents-md-scout"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────

echo
if [ "$errors" -gt 0 ]; then
  echo -e "${RED}Sync completed with $errors error(s)${NC}"
  exit 1
fi

# fn-139.5: keep the flowctl_tracker distribution manifest fresh as part of the
# standard sync step (test_tracker_distribution.py fails CI when it is stale).
python3 "$SCRIPT_DIR/gen_tracker_manifest.py"

echo -e "${GREEN}Sync complete:${NC} $skill_count skills, $agent_count agents (no default hooks)"
echo -e "  ${BLUE}Output:${NC} plugins/flow-next/codex/"
