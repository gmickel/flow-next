# Flow-Next Setup Workflow

Follow these steps in order. This workflow is **idempotent** - safe to re-run.

## Step 0: Resolve plugin path and detect platform

The plugin root is the parent of this skill's directory. From this SKILL.md location, go up to find `scripts/` and `.claude-plugin/`.

Example: if this file is at `~/.claude/plugins/cache/.../flow-next/0.3.12/skills/flow-next-setup/workflow.md`, then plugin root is `~/.claude/plugins/cache/.../flow-next/0.3.12/`.

Store this as `PLUGIN_ROOT` for use in later steps.

### Platform detection

Detect which platform is running:

```bash
# Codex mirror: this workflow is consumed only by Codex.
# Host detection is irrelevant — always PLATFORM=codex
# (canonical Claude-format hosts never read this mirror).
PLATFORM="codex"
```

**Cursor ordering matters.** Cursor exposes **no** plugin-root env var, so without the `CURSOR_AGENT` check it would fall through to the `codex` branch and get Codex-shaped project instructions (`$flow-next-plan` command names + `.codex/` setup) — wrong, because a Cursor install (local or team-marketplace) drives the workflow with `/flow-next:*` slash commands. `CURSOR_AGENT` is Cursor's own signal (set in its agent shell; it also sets `CI=1` / `CURSOR_TRACE_ID`, but `CURSOR_AGENT` is the canonical one). The `CURSOR_AGENT` branch MUST come before the `else → codex` fallback.

**Why the `.cursor-plugin/plugin.json` guard (don't classify Codex-hosted-in-Cursor as Cursor).** `CURSOR_AGENT` is **inherited by child processes** — so when Codex is launched *from* a Cursor Agent shell, the Codex process also sees `CURSOR_AGENT`, and a bare env check would misclassify a genuine Codex setup as `cursor` (skipping the `.codex/` agent + hook copy and writing the `/flow-next:` snippet instead of the Codex `$flow-next-` one — leaving the Codex setup incomplete). The env var alone only proves "a Cursor agent is somewhere in the process ancestry," not "this plugin is a Cursor install." So the branch ALSO requires the `.cursor-plugin/plugin.json` manifest at the **resolved `PLUGIN_ROOT`**: present in real Cursor installs and in the dual-manifest source tree, but **absent** from a pure `~/.codex` install. A Codex process that merely inherited `CURSOR_AGENT` and resolves a Codex-home `PLUGIN_ROOT` (no Cursor manifest) correctly falls through to `codex`. (Same inherited-env-var class as the `CLAUDECODE` host guard below.)

**Positive path discriminator — `PLUGIN_ROOT` under `~/.cursor/` (never `codex/` absence).** The manifest + env checks alone are not enough when Codex runs from the **checked-in plugin source** inside a Cursor shell (Codex marketplace points at `./plugins/flow-next`, which carries `.cursor-plugin/`, `.codex-plugin/`, and the `codex/` mirror) — there the Cursor manifest is present in the workspace tree, so env+manifest would misfire. The positive signal is that a **real Cursor install** resolves `PLUGIN_ROOT` under `~/.cursor/` — local `install-cursor.sh`/`.ps1` → `~/.cursor/plugins/local/flow-next/`; team-marketplace repo-import → Cursor's marketplace plugin cache under `~/.cursor/` (and that cache **may contain `codex/`** because the whole plugin source is imported; explicit component paths in `.cursor-plugin/plugin.json` keep Cursor from loading the mirror as skills). A genuine Codex install resolves under `$CODEX_HOME` (default `~/.codex`); the shared source tree resolves to a workspace path. Neither is under `~/.cursor/`, so both correctly fall through to `codex` even with inherited `CURSOR_AGENT`. **Do not** key detection on the `codex/` directory being absent — that misclassifies marketplace repo-imports as Codex.

**Claude Code signal - `CLAUDECODE` + the Claude plugin manifest, and why the rung sits low (#306).** `CLAUDE_PLUGIN_ROOT` is **never set in the Bash environment of a running plugin skill** on Claude Code (probe-verified against 2.1.221 and re-verified at v3.16.3), so the branch that keyed on it could not fire on our PRIMARY host: every rung failed and setup fell through to `else -> codex`, writing Codex `$flow-next-` snippets into a repo driven by `/flow-next:` slash commands. The signal that IS present is `CLAUDECODE=1`. It is set by Claude Code itself, in every install mode (marketplace cache, local marketplace, `--plugin-dir` dev load), so it needs no plugin-root env var; `PLUGIN_ROOT` is already resolved from this file's own location.

`CLAUDECODE` is **inherited by child processes** - same class as the `CURSOR_AGENT` misfire above - so it is paired with a positive discriminator and a lowered position, never used bare:

- **Positive discriminator:** the Claude plugin manifest `.claude-plugin/plugin.json` must exist at the resolved `PLUGIN_ROOT`. That is present in every Claude-format install and **absent** from a Codex install root (`$CODEX_HOME`, whose manifest is a top-level `plugin.json`), so a `codex exec` child that inherited `CLAUDECODE` from its Claude parent still classifies `codex`.
- **Position: after Droid / Cursor / Grok, before the `codex` fallback.** Each of those hosts proves itself with a signal set by its OWN process (`DROID_PLUGIN_ROOT`, `CURSOR_AGENT` + a `~/.cursor/` install, `GROK_AGENT`), and all of them read the canonical Claude plugin format - so a Cursor or Grok agent launched **from** a Claude Code shell inherits `CLAUDECODE` and would be misclassified `claude-code` by a higher rung. Ordering is what keeps an inherited marker from outranking a host's own signal. This is a deliberate precedence change from the pre-#306 cascade, where the Claude rung sat second: that position only ever protected the `CLAUDE_PLUGIN_ROOT` reading, which on Claude Code is never there.

**Grok ordering matters (fn-126).** Grok Build (xAI's `grok` CLI) reads the canonical Claude plugin format AS-IS and drives with `/flow-next-*` / `/flow-next:` slash commands — not the Codex `$flow-next-` mirror. Without a positive signal it fell through to `else → codex` and setup wrote Codex-shaped `$flow-next-` snippets into AGENTS.md (dogfood 2026-07-22). **Probe-verified signal:** `GROK_AGENT=1` is set BY grok in its agent shell (absent from a plain-shell control on the same machine). **Rejected non-signals:** `~/.grok/` exists on the machine regardless (install dir), and `~/.grok/bin` on `PATH` is profile-level — neither distinguishes a grok session. The `GROK_AGENT` branch MUST come after Droid / Cursor (so a real Cursor/Droid host that merely inherited `GROK_AGENT` from a parent grok shell still classifies by its own higher-precedence signal), BEFORE the inherited-marker `CLAUDECODE` rung, and BEFORE the `else → codex` fallback.

**Known nesting edge (Droid → Grok) — NEEDS-HUMAN.** A grok child inherits `CLAUDECODE` from a Claude parent, and the Claude rung now sits BELOW grok, so Claude-from-parent does not misfire. It did **not** disprove `DROID_PLUGIN_ROOT` propagation: if a grok child inherits `DROID_PLUGIN_ROOT` from a Droid parent shell, the cascade classifies as `droid` (higher precedence). Treat nested Droid→Grok as **unsupported pending a this-process-is-grok discriminator** unless a NEEDS-HUMAN smoke confirms `DROID_PLUGIN_ROOT` does not propagate. Cursor-from-grok remains correct via its higher-precedence signal. The mirror-image nesting edge is Claude-from-Grok / Claude-from-Cursor: a Claude Code session launched inside a grok or Cursor agent shell inherits that host's marker and classifies as the parent host. That trade is deliberate - both markers are set by the parent's own process, and the reverse (Claude outranking them on an inherited `CLAUDECODE`) is the far more common nesting, since Claude sessions routinely spawn grok / cursor-agent bridges.

**Matrix (detection fixtures):** (1) marketplace whole-repo import under `~/.cursor/` + may have `codex/` → `cursor`; (2) local `install-cursor` under `~/.cursor/plugins/local/` (no `codex/`) → `cursor`; (3) Codex under `$CODEX_HOME` / `~/.codex` with inherited `CURSOR_AGENT` → `codex`; (4) Droid (`DROID_PLUGIN_ROOT`) still wins first — Droid/Cursor precedence unchanged; (5) standalone `GROK_AGENT=1` (no higher signal) → `grok`; (6) `GROK_AGENT=1` + `CURSOR_AGENT`(+cursor install) / `DROID_PLUGIN_ROOT` → higher host wins; (7) plain shell (no host signal) → `codex`; (8) Claude Code plugin skill — `CLAUDECODE=1`, `CLAUDE_PLUGIN_ROOT` **unset** (it never reaches a skill's Bash env), `PLUGIN_ROOT` carrying `.claude-plugin/plugin.json` → `claude-code`; (9) `CLAUDECODE=1` inherited by a Cursor / Grok / Droid child → that host's own signal wins (Claude rung is last before the fallback); (10) `CLAUDECODE=1` with a Codex-home `PLUGIN_ROOT` (no `.claude-plugin/plugin.json`) → `codex`.

Store `PLATFORM` for use in later steps. This determines:
- Which manifest to read for version (`plugin.json`)
- Which docs file to prefer (CLAUDE.md vs AGENTS.md)
- Whether to copy Codex agents to project (hooks are **not** copied here — Ralph is opt-in via the Ralph question + `/flow-next:ralph-init`)
- Which command-name syntax the docs snippet uses (`/flow-next:plan` for Claude Code / Droid / **Cursor** / **Grok**; `$flow-next-plan` for Codex)

### Done when

- `PLUGIN_ROOT` resolves to a directory containing `scripts/` and a plugin manifest, and `PLATFORM` holds exactly one of `claude-code` / `codex` / `droid` / `cursor` / `grok`.
- **`PLATFORM` came from the host's own signals in the documented precedence, and every downstream choice matches it.** A Cursor or Grok repo that received the Codex `$flow-next-` snippet, a Codex install misclassified as Cursor through an inherited `CURSOR_AGENT`, or a Claude Code run classified `codex` because the cascade looked for `CLAUDE_PLUGIN_ROOT` instead of `CLAUDECODE` (#306), has broken this.

## Step 1: Initialize .flow/

Use flowctl init (idempotent - safe to re-run, handles upgrades):

```bash
"${PLUGIN_ROOT}/scripts/flowctl" init --json
```

This creates/upgrades:
- `.flow/` directory structure (specs/, tasks/, memory/)
- `meta.json` with schema version
- `config.json` with defaults (merges new keys on upgrade; stamps a `$schema` key pointing at the published flow-config JSON Schema so editors validate/autocomplete - inert string, never fetched)

If the repo still has a pre-1.0 `.flow/epics/` layout, port it by hand before continuing (run `flowctl usage` and read "Pre-1.0 layout porting").

## Step 2: Check existing setup

Read `.flow/meta.json` and check for `setup_version` field.

Also read plugin version from the platform-specific manifest:
- Codex: `${PLUGIN_ROOT}/.codex-plugin/plugin.json`
- Claude Code: `${PLUGIN_ROOT}/.claude-plugin/plugin.json`
- Factory Droid: `${PLUGIN_ROOT}/.claude-plugin/plugin.json` (Droid's interop layer reads the Claude Code manifest directly for Claude-first plugins like flow-next)
- Cursor: `${PLUGIN_ROOT}/.cursor-plugin/plugin.json`
- Grok: `${PLUGIN_ROOT}/.claude-plugin/plugin.json` (Grok reads the canonical Claude plugin format AS-IS — no separate Grok manifest)

Check whichever matches `PLATFORM`. Fall back to `.claude-plugin/plugin.json` if the platform-specific file doesn't exist.

**If `setup_version` exists (already set up):**
- If **same version**: tell user "Already set up with v<VERSION>. Re-run to refresh the docs snippet + config? (y/n)" — a same-version re-run refreshes the versioned doc snippet and re-offers any unanswered config question; nothing is ever copied into the repo, so there are no snapshots to refresh
  - If yes: continue
  - If no: done
- If **older version**: tell user "Updating from v<OLD> to v<NEW>" and continue

**If no `setup_version`:** continue (first-time setup)

Old `setup_mode` / `setup_version` stamps from pre-copy-less installs are inert metadata — read them if you like, never act on them.

## Step 2b: Leftover copy artifacts (cleanup offer)

**Setup never copies flowctl, the spec template, or the usage guide into a repo.** Every host resolves `flowctl` from the plugin install (Claude Code / Droid via their plugin-root env vars, Cursor and Grok by deriving the plugin root from the skill file's own absolute path, Codex from `$CODEX_HOME`). Repos set up before that carry leftover snapshots; this step offers to delete them.

Enumerate the residue. The machine-readable list is flowctl's `PLUGIN_MODE_COPY_ARTIFACTS` — the single source of truth; keep this probe in step with it:

```bash
LEFTOVERS=""
for p in .flow/bin/flowctl .flow/bin/flowctl.cmd .flow/bin/flowctl.py \
         .flow/bin/flowctl_bootstrap.py .flow/bin/flowctl-help.txt \
         .flow/bin/flowctl_tracker .flow/templates/spec.md .flow/usage.md; do
  [ -e "$p" ] && LEFTOVERS="${LEFTOVERS}${p}"$'\n' || true
done   # || true: the loop's exit is the LAST iteration's test - an empty
       # LEFTOVERS (the normal copy-less case) must read as success, not failure
```

**None present → say nothing and continue to Step 4a.** Silence is the normal case.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

**Any present →** list the exact paths, tell the user they are dead weight on every host (nothing reads them; deleting them changes nothing observable), and ask via `plain-text numbered prompt`:

- **header**: `Delete leftover flowctl copies?`
- **question**: `These files are snapshots from an older install layout. Every flow-next skill now resolves flowctl from the plugin install itself, so nothing reads them — deleting them changes nothing observable in any workflow, and keeping them means a stale flowctl can shadow the current one.`
- **options**:
  - `Delete them (Recommended)` — remove the listed paths: `git rm -rq` for tracked ones, plain `rm -rf` for untracked. FIRST surface any listed tracked file with uncommitted modifications and exclude it from removal (never force-remove modified files; the user resolves those by hand).
  - `Keep them` — nothing is removed; setup continues normally. They stay inert.

**Never delete silently.** A leftover that disappeared without the user answering `Delete them` has broken this. After a delete, re-enumerate and print anything still present (declines, modified-file exclusions) — then continue either way; leftovers never block setup.

### Done when

- The residue probe ran on this pass, and its paths match flowctl's `PLUGIN_MODE_COPY_ARTIFACTS` list.
- Nothing under `.flow/bin/`, `.flow/templates/`, or `.flow/usage.md` was written by this run, and nothing was deleted without an explicit `Delete them` answer.

## Step 4: Seed user-owned files

Nothing is copied into `.flow/` — flowctl, the spec template, and the usage guide all resolve from the plugin install. This step seeds only **user-owned** files: an optional repo-root `SPEC.md`, and (on Codex) the project's `.codex/agents/*.toml`.

### Step 4a: Opt-in `<repo_root>/SPEC.md` customization (interactive)

The spec-template discovery cascade prefers a customized scaffold at the repo root over the bundled plugin copy. This step lets the user opt into seeding `<repo_root>/SPEC.md` from the canonical template so they can edit it in place.

**Detect what's already at the repo root** (case-insensitive FS handling — macOS APFS, Windows NTFS):

```bash
# Count DISTINCT FILES, not argument names. `ls -1 SPEC.md spec.md` echoes each
# existing argument back, so on a case-insensitive FS one file prints as two
# names and `sort -u` de-duplicates nothing (#305: HITS=2 on APFS for a repo
# holding only SPEC.md, firing the bogus both-files warning). Inodes answer the
# question the branches actually ask.
# Portable stat, per candidate: GNU form FIRST (`stat -c %i` -> inode; on BSD
# `-c` is unsupported and errors, so it falls through), BSD form second
# (`stat -f %i` -> inode). Order matters: GNU reads `-f` as --file-system and
# would print one shared filesystem id for BOTH files, collapsing a genuine
# two-file repo to HITS=1.
HITS=$(for f in SPEC.md spec.md; do
  [ -e "$f" ] || continue
  stat -c %i "$f" 2>/dev/null || stat -f %i "$f" 2>/dev/null
done | sort -u | wc -l | tr -d ' ')
```

Then branch:

**1. `HITS=0` (neither file exists)** — ask the user via `plain-text numbered prompt`:

- **header**: `Copy canonical spec template to <repo-root>/SPEC.md?`
- **body**: `Every new flow-next spec starts from a template. Lookup order: <repo-root>/SPEC.md first, then <repo-root>/spec.md, then the plugin's bundled copy — so a SPEC.md at the repo root is where you customize section wording for THIS project. Skipping is safe — the bundled template always resolves, and you can opt in any time by re-running /flow-next:setup.`
- **options**:
  - `Copy template` — write `<repo_root>/SPEC.md` from the bundled template (carries the customization-location top-comment). Print the path so the user knows where to edit.
  - `Skip` — no write. Cascade falls through to the plugin's bundled template. Opt in any time by re-running `/flow-next:setup`.
  - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, and Step 2b's leftover cleanup if you accepted it) may already have run; init is idempotent and safe to leave, and a completed cleanup means the instruction-file snippet has NOT yet been refreshed - finish setup (or re-run it) before relying on direct `flowctl` instructions in CLAUDE.md/AGENTS.md. No `<repo_root>/SPEC.md` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

On `Copy template`: write the file via Bash `cp` with absolute paths.

```bash
cp "${PLUGIN_ROOT}/templates/spec.md" SPEC.md
```

**2. `HITS=1` (one file: a single name, OR a case-insensitive FS where both names resolve to one inode)** — capture whichever filename actually exists into `EXISTING` (no prompt). Both the read-for-compare and the overwrite target route through `EXISTING` so lowercase `spec.md` repos do not silently fall back to a missing `SPEC.md`:

```bash
EXISTING=$(ls -1 SPEC.md spec.md 2>/dev/null | head -1)
```

Fall through to the byte-compare re-setup gate below.

**3. `HITS=2` (case-sensitive FS with both distinct files)** — prefer uppercase + print a stderr warning, then fall through to the byte-compare gate against `SPEC.md`:

```bash
echo "warn: both SPEC.md and spec.md exist at repo root; preferring uppercase. Unusual setup likely from cross-platform sync." >&2
EXISTING=SPEC.md
```

**Re-setup byte-compare gate** (when a repo-root spec file exists from a prior `/flow-next:setup`-`Copy template` and the user may have edited it). Read both sides via `EXISTING` and normalize before comparing:

```bash
# Normalize: strip trailing newlines + replace CRLF with LF
USER_CONTENT=$(cat "$EXISTING" | tr -d '\r')
CANONICAL_CONTENT=$(cat "${PLUGIN_ROOT}/templates/spec.md" | tr -d '\r')
# Strip trailing newlines from both
USER_NORM=$(printf '%s' "$USER_CONTENT")
CANONICAL_NORM=$(printf '%s' "$CANONICAL_CONTENT")
```

Or in Python:

```python
def normalize(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n").rstrip(b"\n")
identical = normalize(user_bytes) == normalize(canonical_bytes)
```

Then:

- **Identical** (after normalization): no-op. Skip the write — re-running setup must not bump mtime on unchanged files.
- **Customized** (any deviation after normalization): **the file is never replaced without an explicit answer** — a customized `SPEC.md` overwritten silently has broken this. Ask the user via `plain-text numbered prompt`:
  - **header**: `Overwrite customized <repo-root>/$EXISTING?`
  - **body**: `<repo-root>/$EXISTING exists and differs from the canonical template shipped with this plugin version (CRLF and trailing newlines ignored). Overwriting replaces your edits. Keeping skips this file (you can manually merge later via diff against \`${PLUGIN_ROOT}/templates/spec.md\`).`
  - **options**:
    - `Keep mine (Recommended)` — leave `<repo-root>/$EXISTING` unchanged. Print the path to the canonical template so the user can diff manually.
    - `Overwrite with canonical` — replace `<repo-root>/$EXISTING` (same filename — do NOT rename lowercase `spec.md` to uppercase `SPEC.md` here; preserve the user's casing) with the bundled template content. Repo customization is lost.
    - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, and Step 2b's leftover cleanup if you accepted it) may already have run; init is idempotent and safe to leave, and a completed cleanup means the instruction-file snippet has NOT yet been refreshed - finish setup (or re-run it) before relying on direct `flowctl` instructions in CLAUDE.md/AGENTS.md. No `<repo-root>/$EXISTING` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

**Note:** Setup writes uppercase `SPEC.md` only on the **fresh-seed** path (`HITS=0` `Copy template`). Never seed lowercase `spec.md` from scratch. The lowercase entry in the cascade is read-only at discovery time — present only for users who deliberately created lowercase. On the **re-setup overwrite** path above, preserve the user's existing filename casing via `$EXISTING` (so a lowercase `spec.md` stays lowercase after `Overwrite with canonical`).

## Step 4b: Codex-specific project setup (PLATFORM=codex only)

**This step runs only when `PLATFORM` is `codex`.** A `.codex/agents/` directory created on a Claude Code, Droid, Cursor, or Grok host has broken this. (Cursor and Grok drive the workflow with `/flow-next:*` slash commands, not project-scoped `.codex/` agents. Grok never copies `.codex/agents`.)

On Codex, agents live in project-scoped `.codex/` directories (not in the plugin cache). Copy them. **Do not copy or enable Ralph hooks here** — hooks are opt-in via the Ralph question (Step 6d, always asked) and `/flow-next:ralph-init` registration prose.

### Copy agent .toml files

```bash
# Source: pre-built agents from plugin (or global install)
AGENTS_SRC="${PLUGIN_ROOT}/codex/agents"
[ -d "$AGENTS_SRC" ] || AGENTS_SRC="${CODEX_HOME:-$HOME/.codex}/agents"

if [ -d "$AGENTS_SRC" ]; then
  mkdir -p .codex/agents
  cp "$AGENTS_SRC"/*.toml .codex/agents/
  echo "Copied $(ls .codex/agents/*.toml 2>/dev/null | wc -l | tr -d ' ') agent configs to .codex/agents/"
else
  echo "Warning: No agent .toml files found at ${PLUGIN_ROOT}/codex/agents/ or ${CODEX_HOME:-$HOME/.codex}/agents/"
fi
```

### Done when

- **User-owned files — repo-root `SPEC.md`, `.flow/criteria.md` — were compared before writing, left untouched when identical, and never overwritten without an explicit answer.** A customized one silently replaced has broken this.
- `.codex/agents/*.toml` exists only when `PLATFORM=codex`, and no Ralph hook was copied or enabled here.

## Step 5: Update meta.json

Read current `.flow/meta.json`, add/update these fields (preserve all others):

```json
{
  "setup_version": "<PLUGIN_VERSION>",
  "setup_date": "<ISO_DATE>"
}
```

## Step 6: Configuration Questions

### 6a: Detect current config and tools

Before asking questions, detect available tools and read current config:

```bash
# Detect available review backends
if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then HAVE_RP=1; else HAVE_RP=0; fi
HAVE_CODEX=$(which codex >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_COPILOT=$(which copilot >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_CURSOR=$(which cursor-agent >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_GROK=$(which grok >/dev/null 2>&1 && echo 1 || echo 0)

# The HAVE_* values feed the Review question's "(detected)" annotations only.
# Nothing here gates the routing block: setup never probes for routing, never
# asks a routing question, and never writes a model id into the block it
# proposes (fn-195 R5 — config that claims what is installed becomes config
# that lies).

# Read current config values if they exist.
# NB: pass `--raw` to bypass merged defaults. Without it, `flowctl config get`
# returns the built-in default for unset keys (e.g. `planSync.crossSpec` →
# `false`), and the `[[ -z "$CURRENT_*" ]]` guards below would skip first-run
# prompts for any default-false option. `--raw` makes `null` mean "absent
# from .flow/config.json"; we use an explicit `if .value == null` filter
# (NOT `.value // empty`, which collapses boolean `false` to "" because
# jq treats `false` as a falsy LHS for `//`). See PR #135 cycle 2.
CURRENT_BACKEND=$("${PLUGIN_ROOT}/scripts/flowctl" config get review.backend --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
CURRENT_MEMORY=$("${PLUGIN_ROOT}/scripts/flowctl" config get memory.enabled --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
CURRENT_PLANSYNC=$("${PLUGIN_ROOT}/scripts/flowctl" config get planSync.enabled --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
# planSync.crossSpec is canonical (the pre-1.1.3 legacy alias
# planSync.crossEpic was removed in 2.0.0 — a leftover key in the on-disk
# file is inert). The `--raw` probe checks only the canonical key.
CURRENT_CROSSSPEC=$("${PLUGIN_ROOT}/scripts/flowctl" config get planSync.crossSpec --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
CURRENT_GITHUB_SCOUT=$("${PLUGIN_ROOT}/scripts/flowctl" config get scouts.github --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
# Survives Step 1's `flowctl init`: init deliberately does NOT materialize the
# `artifacts` block into config.json (flowctl.py _INIT_UNMATERIALIZED_BLOCKS),
# so this raw probe reads null until the user explicitly decides — here in 6e
# or via `flowctl config set`. Merged reads still return the seeded default.
CURRENT_HTML_ARTIFACTS=$("${PLUGIN_ROOT}/scripts/flowctl" config get artifacts.html.enabled --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
# tracker.specIds is UNMATERIALIZED at init (fn-134 / R9) — raw null means "never
# asked", distinct from an explicit `flow` answer. Gate the Spec ids question on
# tracker configured AND this key unset so existing repos get asked on their next
# setup run without re-prompting once either value is written.
CURRENT_SPEC_IDS=$("${PLUGIN_ROOT}/scripts/flowctl" config get tracker.specIds --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
# Global criteria scaffold gate (fn-137): the question is offered only while
# .flow/criteria.md is absent. An existing file - scaffolded, hand-written, or
# customized - is user content and is never re-asked about, never touched.
CRITERIA_EXISTS=$( { test -e .flow/criteria.md || test -L .flow/criteria.md; } && echo 1 || echo 0)   # -e||-L: a dangling symlink or non-regular path COUNTS as existing (never re-ask/overwrite; a broken path is a validation error to surface, not a scaffold target)

# Call the canonical predicate; never re-derive it. A bare `-n "$TYPE"` counted
# an inactive value ("null", a typo) as configured, so setup persisted
# specIds=tracker while every mint gate saw the bridge as inactive.
TRACKER_CONFIGURED=$("${PLUGIN_ROOT}/scripts/flowctl" sync active --json 2>/dev/null | jq -r 'if .active == true then 1 else 0 end')
[[ -n "$TRACKER_CONFIGURED" ]] || TRACKER_CONFIGURED=0
```

Store detection results for use in questions. When showing options, indicate current value if set (e.g., "(current)" after the matching option label).

### 6b: Check docs status

Choose the correct template based on platform:
- **Codex** (`PLATFORM=codex`): read [templates/agents-md-snippet.md](templates/agents-md-snippet.md) — uses `$flow-next-plan` syntax
- **Claude Code / Droid / Cursor / Grok**: read [templates/claude-md-snippet.md](templates/claude-md-snippet.md) — uses `/flow-next:plan` slash syntax (Cursor runs the same slash commands; on Cursor the snippet lands in AGENTS.md. Grok drives with `/flow-next-` slash commands and reads BOTH CLAUDE.md and AGENTS.md — lifecycle snippet targets CLAUDE.md by default; a pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form, marker-scoped)

Both templates are the same slim rail: bare `flowctl`, `flowctl usage` pull directives, and an internal `<!-- flow-next:snippet:vN -->` sentinel that versions the block.

For each of CLAUDE.md and AGENTS.md:
1. Check if file exists
2. If exists, check if `<!-- BEGIN FLOW-NEXT -->` marker exists
3. If marker exists, extract content between markers and compare with template

Determine status for each file:
- **missing**: file doesn't exist or no flow-next section
- **current**: section exists and matches template
- **outdated**: section exists but differs from template

### 6c: Show current config notice

If ANY config values are already set, print a notice before asking questions:

```
Current configuration:
- Memory: <enabled|disabled> (change with: flowctl config set memory.enabled <true|false>)
- Plan-Sync: <enabled|disabled> (change with: flowctl config set planSync.enabled <true|false>)
- Plan-Sync cross-spec: <enabled|disabled> (change with: flowctl config set planSync.crossSpec <true|false>)
- Review backend: <current value, bare or spec form> (change with: flowctl config set review.backend <codex|rp|copilot|cursor|none OR spec form like codex:gpt-5.4:xhigh or cursor:gpt-5.5-high>)
- GitHub scout: <enabled|disabled> (change with: flowctl config set scouts.github <true|false>)
- HTML artifacts: <enabled|disabled> (change with: flowctl config set artifacts.html.enabled <true|false>)
- Spec ids: <flow|tracker> (change with: flowctl config set tracker.specIds <flow|tracker>)
```

Only include lines for config values that are set. If no config is set, skip this notice. (Spec ids line only when `CURRENT_SPEC_IDS` is non-empty — an unset key is not "set".)

### 6d: Build questions list

Build the prompt content (question text + numbered option list) dynamically. **The questions array is built only from keys that read raw-null in `.flow/config.json`.** A re-run with everything set that asks a config question it already knows the answer to has broken this — existing config is preserved, never silently flipped. To change an already-set value, the user runs `flowctl config set <key> <value>` directly (the commands are surfaced in 6c's current-config notice).

Skipped questions = config values already persisted from a prior run. Asking again would either no-op (same answer) or silently flip a deliberate user choice — both are wrong. The grouped single-prompt design (a single `plain-text numbered prompt` call below, with one questions array containing only the unset entries) means a re-run with all config set produces zero config questions and asks only Docs + Star, plus Ralph when `RALPH_ASK=1` and Global criteria while `.flow/criteria.md` is still absent. **There is no routing question** — the routing block is proposed, not negotiated (Step 7).

Available questions (include only if corresponding config is unset):

**Memory question** (include if CURRENT_MEMORY is empty):
```json
{
  "header": "Memory",
  "question": "Enable the memory system? When a review sends a task back for rework, the lesson learned is saved under .flow/memory/ and read by future planning and implementation - so the same mistake is not repeated across specs.",
  "options": [
    {"label": "Yes (Recommended)", "description": "Auto-capture pitfalls and conventions from review feedback into .flow/memory/"},
    {"label": "No", "description": "No learnings captured. Enable later with: flowctl config set memory.enabled true"}
  ],
  "multiSelect": false
}
```

**Plan-Sync question** (include if CURRENT_PLANSYNC is empty):
```json
{
  "header": "Plan-Sync",
  "question": "Enable plan-sync? After each task is implemented, a quick sync pass updates the not-yet-started tasks in the same spec to match what was ACTUALLY built - so later tasks never work from a stale plan.",
  "options": [
    {"label": "Yes (Recommended)", "description": "Sync remaining task specs whenever implementation deviates from the original plan"},
    {"label": "No", "description": "Later tasks keep their original wording. Enable later with: flowctl config set planSync.enabled true"}
  ],
  "multiSelect": false
}
```

**Plan-Sync cross-spec question** (include if CURRENT_PLANSYNC is "true" AND CURRENT_CROSSSPEC is empty)[^crossspec-legacy]:

[^crossspec-legacy]: The canonical config key is `planSync.crossSpec`. The pre-1.1.3 name `planSync.crossEpic` was removed in 2.0.0 — flowctl no longer reads it; a leftover key in `.flow/config.json` is inert.
```json
{
  "header": "Cross-Spec",
  "question": "Enable cross-spec plan-sync? (Also checks other open specs for stale references)",
  "options": [
    {"label": "No (Recommended)", "description": "Only sync within current spec. Faster, avoids long Ralph loops."},
    {"label": "Yes", "description": "Also update tasks in other specs that reference changed APIs/patterns."}
  ],
  "multiSelect": false
}
```

**GitHub Scout question** (include if CURRENT_GITHUB_SCOUT is empty):
```json
{
  "header": "GitHub Scout",
  "question": "Enable GitHub scout? (Searches public/private repos for patterns during planning, requires gh CLI)",
  "options": [
    {"label": "No (Recommended)", "description": "Skip cross-repo search. Faster plans, no gh CLI needed."},
    {"label": "Yes", "description": "Search GitHub repos for patterns/examples during /flow-next:plan"}
  ],
  "multiSelect": false
}
```

**Spec ids question** (include if `TRACKER_CONFIGURED=1` AND `CURRENT_SPEC_IDS` is empty — both conditions; skip entirely when no tracker is configured, and never re-ask once the key is set to either `flow` or `tracker`):
```json
{
  "header": "Spec ids",
  "question": "How should new specs get their ids? Parallel agents and branches both scanning only local .flow/specs/ collide on fn-N — that is structural, not unlucky. With a tracker configured, tracker-first keys each new spec to the issue (Linear/Jira WOR-17 → wor-17-slug; GitHub #123 → gh-123-slug; GitLab iid → gl-N-slug) so the tracker is the distributed allocator. Recommended: tracker. Choosing tracker means every new-spec creation contacts the tracker immediately — it creates the issue BEFORE the local spec exists. When the matching lifecycle touchpoint (tracker.perEvent.capture/plan/...) is already on, that is a reorder of an existing remote write; when those leaves are off (their default, and a bridge-active repo can have every lifecycle event disabled), it is an earlier remote write that flow-first would not make.",
  "options": [
    {"label": "Tracker (Recommended)", "description": "Mint KEY-N-slug / gh-N / gl-N from the issue; create the tracker issue first on a fresh idea. Stops parallel fn-N collisions."},
    {"label": "Flow", "description": "Keep sequential fn-N allocation (today's default). Safer offline; collisions remain possible across parallel worktrees/clones. An explicit Flow answer is remembered — setup will not ask again."}
  ],
  "multiSelect": false
}
```

**HTML Artifacts question** (include if CURRENT_HTML_ARTIFACTS is empty):
```json
{
  "header": "HTML Artifacts",
  "question": "Enable HTML artifact mode? Capture/plan/make-pr additionally render each spec and PR body as a self-contained HTML page under .flow/artifacts/ - nicer for humans to review in a browser. The markdown stays the source of truth; pages are regenerable any time.",
  "options": [
    {"label": "Yes (Recommended)", "description": "Also emit shareable HTML review pages alongside the markdown"},
    {"label": "No", "description": "Markdown-only. Zero extra steps, zero token overhead. Enable later: flowctl config set artifacts.html.enabled true"}
  ],
  "multiSelect": false
}
```

**Global criteria question** (include if `CRITERIA_EXISTS=0` — an existing `.flow/criteria.md` is user content: never re-ask, never touch. Like the Step 4a SPEC.md offer, it seeds a user-owned file, not a setup-managed copy):
```json
{
  "header": "Global criteria",
  "question": "Scaffold .flow/criteria.md? A plain markdown file of standing, project-wide acceptance criteria (- **G1:** every route change regenerates the contract...). When present, spec completion review judges every criterion against each spec's implementation and records met/violated/n-a in the review receipt. Absent = zero effect anywhere.",
  "options": [
    {"label": "Scaffold", "description": "Write .flow/criteria.md from the bundled template - documents the G-ID grammar with commented examples to replace with your own criteria"},
    {"label": "Skip", "description": "No file written, nothing changes. Opt in any time by creating .flow/criteria.md yourself (grammar: - **G<N>:** <criterion>) or re-running /flow-next:setup"}
  ],
  "multiSelect": false
}
```

**Review question** (include if CURRENT_BACKEND is empty):

**When `PLATFORM=cursor`** — lead with `host` (Recommended); keep every existing backend selectable; label the Cursor CLI option as circular/secondary from inside Cursor (fn-123 R6):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land. From inside Cursor, prefer a host-native fresh-context subagent pinned cross-family via AGENTS.md model-routing (no second CLI). External CLIs remain available. Guide: https://flow-next.dev/review/workflow/",
  "options": [
    {"label": "Host (Recommended)", "description": "Fresh-context host-native subagent; name a cross-family model on the `reviewer` tier of the AGENTS.md routing block (setup writes that block commented out; the slugs are yours to fill in). No external CLI. Preferred from inside Cursor."},
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI (secondary — circular from inside Cursor)", "description": "Runs the external cursor-agent CLI. Circular when already inside Cursor — prefer Host. Still selectable for multi-family reach via the cursor-agent model menu. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, far fewer tokens than full-repo approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
    {"label": "None", "description": "Skip AI reviews for now. Set later with flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

**When `PLATFORM=grok`** (fn-126) — offer `host` with the fail-closed cross-family caveat (this host reaches only one model family natively) plus every external backend; when `HAVE_CODEX=1` mark Codex Recommended (true cross-family vs a Grok writer):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land. This host reaches only one model family natively — host-native review fails closed unless the writer is from another family; cross-family review comes via bridge backends (codex/cursor/copilot). Guide: https://flow-next.dev/review/workflow/",
  "options": [
    {"label": "Host", "description": "Fresh-context host-native subagent; name the model on the `reviewer` tier of the AGENTS.md routing block (setup writes it commented out; you fill in the slug). Fail-closed: this host is single-native-family — native host review refuses same-family self-review (interactive → ask; autonomous → NEEDS_HUMAN) unless the writer is non-Grok. Cross-family via bridges."},
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI", "description": "Runs cursor-agent with a multi-family model menu (pick the family that did not write the diff). Billed to your Cursor subscription. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, far fewer tokens than full-repo approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
    {"label": "None", "description": "Skip AI reviews for now. Set later with flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

**When `PLATFORM` is neither `cursor` nor `grok`** (Claude Code / Droid / Codex — unchanged; Cursor and Grok each use their dedicated menu above):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land; a review backend is a second AI CLI - ideally a DIFFERENT model family than the one writing the code, for uncorrelated blind spots. Each needs its own install/subscription. Guide: https://flow-next.dev/review/workflow/",
  "options": [
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI", "description": "Runs cursor-agent with a multi-family model menu (pick the family that did not write the diff). Billed to your Cursor subscription. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, far fewer tokens than full-repo approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
    {"label": "None", "description": "Skip AI reviews for now. Set later with flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

When `HAVE_CODEX=1` AND `PLATFORM` is NOT `codex` AND `PLATFORM` is NOT `cursor`, append ` (Recommended - cross-family default)` to the `Codex CLI` label: the recommended multi-model pipeline reviews cross-family FROM THE WRITER, and on a Claude Code / Droid / Grok host codex review is a different family than the session writer - so this question carries the ceremony's `review.backend codex` offer while the key is unset (fn-97). On `PLATFORM=cursor` do NOT add the Codex Recommended label — `Host (Recommended)` already leads. On a Codex host (`PLATFORM=codex`) do NOT add the label: the writer is GPT-family (the session model, or an `implementer` tier pointing at the same family), so codex review would be SAME-family - prefer a detected non-GPT backend there (copilot / cursor with a Claude-family model) and leave the options unannotated when none is detected. When `review.backend` is ALREADY set to something else, this question is skipped (existing config is never silently overwritten) - the user changes it later with `flowctl config set review.backend <name>`, surfaced in 6c's current-config notice.

Stored value is a bare backend name by default (`host` / `codex` / `copilot` / `cursor` / `rp` / `none`). Power users can also write a full spec like `codex:gpt-5.4:high`, `copilot:claude-opus-4.5:xhigh`, or `cursor:gpt-5.5-high` (cursor takes a model only — no `:effort`) via `flowctl config set review.backend <spec>` after setup — the review commands accept both forms. Backend `host` is bare only (no `host:<model>` — the model is named on the `reviewer` tier of the AGENTS.md routing block).

**No Model Routing question exists.** Setup never asks which models to route to,
never probes a CLI for slugs, and never proposes a pin. Step 7 writes one
commented example block and says so — that is the whole ceremony (fn-195 R5/R6).

**Docs question** (always include — adjust default based on platform):

For **Codex** (`PLATFORM=codex`):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (Codex reads this)"},
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Claude Code / Droid**:
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "AGENTS.md only", "description": "Add flow-next section to AGENTS.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Cursor** (`PLATFORM=cursor`) — Cursor reads AGENTS.md, so recommend it (the `/flow-next:` snippet is wired in Step 7's write mapping, NOT the Codex `$flow-next-` one):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (Cursor reads this)"},
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Grok** (`PLATFORM=grok`) — Grok reads BOTH CLAUDE.md and AGENTS.md; lifecycle snippet defaults to CLAUDE.md (canonical Claude-format target, `/flow-next:` slash syntax — NOT the Codex `$flow-next-` one). A pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form (marker-scoped; text outside markers untouched). The routing block still targets AGENTS.md (where host-review workflows read it):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched. Grok loads both CLAUDE.md and AGENTS.md.",
  "options": [
    {"label": "CLAUDE.md only (Recommended)", "description": "Add flow-next section to CLAUDE.md (canonical Grok lifecycle target; /flow-next: slash syntax)"},
    {"label": "AGENTS.md only", "description": "Add flow-next section to AGENTS.md"},
    {"label": "Both", "description": "Add flow-next section to both files (recommended when you also want the routing block's sibling lifecycle snippet nearby)"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

**Ralph question.** Resolve its gate before reading question prose:

```bash
RALPH_ASK=1
if [[ "$PLATFORM" == "cursor" || "$PLATFORM" == "grok" ]]; then
  RALPH_ASK=0
  RALPH_OUTCOME="off (unsupported on $PLATFORM)"
elif [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
      || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* ]]; then
  RALPH_ASK=0
  RALPH_OUTCOME="off (non-interactive)"
fi
```

On Cursor/Grok: never offer, never register, never run `/flow-next:ralph-init`.
When `RALPH_ASK=1`, **MUST read and follow exactly**
[references/ralph-question.md](references/ralph-question.md) and add its object
to the grouped prompt. When zero, read no Ralph reference and ask no Ralph
question. Unknown/malformed gate state fails safe to `RALPH_ASK=0`: no hook
registration and no branch read.

**Star question** (always include):
```json
{
  "header": "Star",
  "question": "Flow-Next is free and open source. Star the repo on GitHub?",
  "options": [
    {"label": "Yes, star it", "description": "Uses gh CLI if available, otherwise shows link"},
    {"label": "No thanks", "description": "Skip starring"}
  ],
  "multiSelect": false
}
```

Print the prompt content built above and stop for the user's reply.

**Note:** If docs are already current, adjust the Docs question description to mention "(already up to date)" or skip that question entirely.

**Note:** If no supported RepoPrompt CLI, codex, copilot, or cursor-agent is detected, add this note to the Review question: "No review backend detected. Install RepoPrompt CE (`rpce-cli`), codex, copilot, or cursor-agent for review support."

### Done when

- One grouped `plain-text numbered prompt` call carried the questions array, and that array holds only the still-unanswered keys plus Docs / Star (and Ralph, Global criteria when their own gates passed).
- **No routing question was asked, no CLI was probed for model ids, and no pin was proposed or stamped.** Setup asking which model to route to, or writing a model id anywhere, has broken this (fn-195 R5/R6).
- **Under any autonomy marker (`FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, `FLOW_AUTONOMOUS`, `mode:autonomous`) the Ralph ceremony was skipped silently** — no reference read, no question, no summary noise. A run that blocked on it under an autonomy marker has broken this.

## Step 7: Process Answers

Only process answers for questions that were asked (config values that were unset). Skip processing for config that was already set.

**Memory** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set memory.enabled false --json`

**Plan-Sync** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.enabled false --json`

**Plan-Sync cross-spec** (if question was asked; canonical key is `planSync.crossSpec` — the legacy `planSync.crossEpic` alias was removed in 2.0.0):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.crossSpec true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set planSync.crossSpec false --json`

**GitHub Scout** (if question was asked):
- If "Yes": `"${PLUGIN_ROOT}/scripts/flowctl" config set scouts.github true --json`
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set scouts.github false --json`

**Spec ids** (if question was asked — only when tracker was configured and the key was unset):
- If "Tracker" / label starts with `Tracker`: `"${PLUGIN_ROOT}/scripts/flowctl" config set tracker.specIds tracker --json`
- If "Flow": `"${PLUGIN_ROOT}/scripts/flowctl" config set tracker.specIds flow --json`
- Writing either value ends the ask-once contract: the next setup run sees a non-empty raw key and skips this question.

**HTML Artifacts** (if question was asked):
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set artifacts.html.enabled false --json`
- If "Yes":
  1. `"${PLUGIN_ROOT}/scripts/flowctl" config set artifacts.html.enabled true --json`
  2. Ask ONE follow-up via `plain-text numbered prompt` — track or ignore the artifact directory:
     - **header**: `Artifacts in git?`
     - **question**: `Artifacts live at .flow/artifacts/<spec-id>/{spec,pr}.html (fixed paths, regenerable). Commit them or gitignore the directory?`
     - **options**:
       - `Commit artifacts (Recommended)` — keep `.flow/artifacts/` tracked. This is what makes make-pr blob links resolve for remote reviewers. No action needed (the auto-managed `.flow/.gitignore` block does not exclude `artifacts/`).
       - `Gitignore` — local-open only; make-pr skips blob links. Append the pattern below the auto-managed footer in `.flow/.gitignore` (user patterns there are preserved by flowctl), guarding against duplicates:
         ```bash
         grep -qx 'artifacts/' .flow/.gitignore 2>/dev/null || printf 'artifacts/\n' >> .flow/.gitignore
         # Untrack any artifacts committed before this choice so state converges (no-op when none)
         git rm -r --cached --quiet .flow/artifacts 2>/dev/null || true
         ```
  3. Print the lavish-axi offer verbatim. **The skill detects and instructs; it never installs.** A transcript showing setup running `npm i -g lavish-axi` has broken this — global installs are user-consent territory, the same discipline as /flow-next:map:

     ```
     HTML artifact mode enabled.

     Optional companion — lavish-axi (annotate spec artifacts in the browser; feedback
     flows back as markdown-source edits, then the lens regenerates):

       Install:   npm i -g lavish-axi
                  (or zero-setup, per run: npx lavish-axi <artifact.html>)

       Feedback model — session-spanning, pull-only: annotations queue in the global
       ~/.lavish-axi/state.json and survive the agent session; any later agent session
       drains the queue via the lavish-axi poll CLI. Nothing is pushed into the agent.

       Lifecycle: the local server idle-stops after ~30 min; reopening the artifact
       resumes the session. Without lavish-axi (or after idle-stop) the artifact still
       renders as a plain static page — it is never a dependency.

     flow-next never auto-installs lavish-axi.
     ```

**Global criteria** (if question was asked):
- If "Scaffold": copy the bundled template (resolved from the plugin install - the file is user content from this moment on, so no re-run ever refreshes or compares it):

  ```bash
  cp "${PLUGIN_ROOT}/templates/criteria.md" .flow/criteria.md
  ```

- If "Skip": do nothing - no file, no config key, no meta stamp. Declining leaves no trace.

**Review** (if question was asked):
Map user's answer to config value and persist:

```bash
# Determine backend from answer (Host before Cursor so "Host (Recommended)" never
# matches the Cursor* pattern; "Cursor CLI (secondary…)" still maps to cursor).
case "$review_answer" in
  "Host"*) REVIEW_BACKEND="host" ;;
  "Codex"*) REVIEW_BACKEND="codex" ;;
  "Copilot"*|"copilot"*) REVIEW_BACKEND="copilot" ;;
  "Cursor"*|"cursor"*) REVIEW_BACKEND="cursor" ;;
  "RepoPrompt"*) REVIEW_BACKEND="rp" ;;
  *) REVIEW_BACKEND="none" ;;
esac

"${PLUGIN_ROOT}/scripts/flowctl" config set review.backend "$REVIEW_BACKEND" --json
```

**Docs:**

Use the correct template based on **target file** and **platform**:
- AGENTS.md on **Codex**: use [templates/agents-md-snippet.md](templates/agents-md-snippet.md) (uses `$flow-next-plan` syntax)
- AGENTS.md on **Claude Code / Droid / Cursor / Grok**: use [templates/claude-md-snippet.md](templates/claude-md-snippet.md) (uses `/flow-next:plan` slash syntax — Cursor and Grok run the slash commands, so their AGENTS.md must carry the `/flow-next:` snippet, NOT the Codex `$flow-next-` one; a wrong Codex `$` block is consent-refreshed marker-scoped)
- CLAUDE.md (any platform — including Grok's default lifecycle target): use [templates/claude-md-snippet.md](templates/claude-md-snippet.md)

**Resolve the target file set:** an explicit Docs-question answer is authoritative - if the user is asked and selects specific files (or declines one), honor exactly that; never touch a file the user just deselected. The one addition is a backfill for the SKIPPED case: when the Docs question is omitted entirely because the block is already current (per the Note above), still run `apply` on each already-marker-bearing file. Rationale (R8): a current-but-hashless block (written by a pre-hash plugin version) would otherwise never reach `apply`, so its pristine hash never gets backfilled and the NEXT template change wrongly prompts "Overwrite customized?". `apply` on a current block is cheap and idempotent - it returns `unchanged` and records the missing hash. So: resolve targets = files chosen by the Docs question when it was asked; OR, when the Docs question was skipped, the files already carrying the `<!-- BEGIN FLOW-NEXT -->` marker. Run the helper once per resolved file.

For each resolved file (CLAUDE.md and/or AGENTS.md) - the block mechanics (marker-scoped replace, per-`(path, id)` pristine-hash tracking in `.flow/meta.json` `setup.block_hashes` - a nested `{<path>: {<id>: <hash>}}` map since fn-171; these call sites pass no `--id`, so they always read/write the default `FLOW-NEXT` id) are deterministic flowctl plumbing; this step owns only the ask:

1. Run the helper (repeat per resolved file, substituting the snippet template selected above):

   ```bash
   "${PLUGIN_ROOT}/scripts/flowctl" setup-block apply --file <FILE> \
     --template "${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md" --json
   ```

2. Route on the returned `action` - the first four need no prompt:
   - `appended` - no marker block existed; the snippet was appended at end of file (pre-existing content untouched) and its pristine hash recorded.
   - `refreshed` - the existing block matched its recorded pristine hash (never customized), so the helper silently replaced it with the new canonical and updated the hash. Existing installs receive template fixes without a prompt.
   - `unchanged` - the block already matches the canonical template. No write, no mtime bump.
   - `kept` - a previous "Keep mine" recorded the `"customized"` sentinel; the helper never re-asks and never silently overwrites. Leave it alone.
   - `ask` (reason `customized` or `hash-absent`) - the block differs from canonical and is not provably pristine. The helper wrote nothing; ask via `plain-text numbered prompt`:
     - **header**: `Overwrite customized <FILE>?` (substitute CLAUDE.md or AGENTS.md)
     - **body**: `<FILE> contains a flow-next marker block that differs from the canonical template shipped with this plugin version and is not recorded as pristine. Overwriting replaces the marker block only; content outside the markers is untouched either way.`
     - **options**:
       - `Keep mine (Recommended)` - run `"${PLUGIN_ROOT}/scripts/flowctl" setup-block resolve --file <FILE> --template <same template> --choice keep --json`. This records the `"customized"` sentinel so future re-runs never re-ask and never overwrite. Print the canonical template path so the user can diff manually (`${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md`).
       - `Overwrite with canonical` - run the same `setup-block resolve` command with `--choice overwrite`. This replaces the marker block with the canonical snippet and records the new pristine hash; customizations inside the markers are lost, content outside the markers is preserved.
       - `abort` - exit cleanly, no further writes. Earlier steps (init, file copies, config writes, prior docs-file decisions for any already-processed file) may already have run; they are idempotent and safe to leave. Everything from here onward is skipped (remaining docs files, the routing block, and the Star step). Re-run `/flow-next:setup` later to complete setup.

The marker-block boundaries are load-bearing: **docs snippets are written through `flowctl setup-block apply`, touching only the bytes inside the flow-next markers.** Prose outside `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` that changed, or a write made by anything other than the helper, has broken this. And **an `ask` result prompts Keep mine / Overwrite / abort** — a customized block replaced without that answer has broken this too.

**Routing block** — one proposal, no question. Run this **after** the Docs block
above and before Ralph/Star. Always re-read target files from disk after Docs;
never interleave the two writes. Two hard outs before the ladder: a **Docs
answer of `Skip`** is a decline of documentation edits and declines this write
too — record `skipped (docs declined)` and move on; a **headless or autonomous
run** (`FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, `FLOW_AUTONOMOUS=1`, or
`mode:autonomous`) never writes the block — instruction-file edits are the
user's, so record `skipped (headless)` and move on.

Resolve the target with this ladder, first match wins:

1. Docs answered this run: mirror `CLAUDE.md only`, `AGENTS.md only`, or `Both`.
2. Otherwise the files already carrying `<!-- BEGIN FLOW-NEXT -->`.
3. Otherwise Codex / Cursor / Grok → `AGENTS.md`; Claude Code / Droid →
   `CLAUDE.md`.

Per target, in order:

- **Shim guard.** A file whose only non-empty line matches `@<path>.md` or
  `See[:] <path>.md` (case-insensitive) is a pointer: retarget to that in-repo
  file and re-apply the guard. A missing pointer target drops that target with
  `Routing block: <file> is a shim pointing at a missing <path>.md — skipping`.
  Never mix content into a shim.
- **Existing block.** A file already carrying
  `<!-- flow-next:model-routing:start -->` is left **completely untouched** — no
  byte-compare, no refresh, no question, no mtime change. Record
  `kept (yours)`. Setup is re-run after every release; a block the user edited
  (or emptied) is theirs from the moment it exists. Rewriting one has broken
  this (fn-195 R5).
- **Unmarked routing prose.** A target already carrying a user-authored
  routing-shaped heading (a heading line containing `model routing` or
  `model-routing`, case-insensitive, without our markers) is theirs too: skip
  the write, record `kept (yours)`. Never append a second routing section
  beside one a human wrote.
- **No block.** Write [templates/model-routing-snippet.md](templates/model-routing-snippet.md)
  **verbatim** — markers included, every routing line still commented out. There
  is no composition step: no probe sentinels, no detected models, no date stamp,
  nothing substituted. Append it at the end of the file, leaving all other
  content untouched. Record `written to <file>`.

Then say what was written, once, in one sentence:
`Wrote a commented model-routing example to <file> — every line is commented out; edit it to name the models you want for each tier, or delete the block.`
(Nothing was written → say `kept (yours)` / `skipped (shim)` / `skipped (docs declined)` / `skipped (headless)` instead and move on.)

**Ralph** (only when its question was asked; Cursor/Grok remain
unsupported and read no Ralph reference):

- `Yes, enable or keep` → **MUST read and follow exactly**
  [references/ralph-enable.md](references/ralph-enable.md).
- `No (Recommended)` or an empty/default interactive answer → **MUST read and
  follow exactly** [references/ralph-disable.md](references/ralph-disable.md).

Unknown answer fails safe to the disable reference. Under any non-interactive
marker, do not read either Ralph reference, do not register hooks, and set
`RALPH_OUTCOME="off (non-interactive)"`.

**Star:**
- If "Yes, star it":
  1. Check if `gh` CLI is available: `which gh`
  2. If available, run: `gh api -X PUT /user/starred/gmickel/flow-next`
  3. If `gh` not available or command fails, show: `Star manually: https://github.com/gmickel/flow-next`

## Step 8: Print Summary

```
Flow-Next setup complete!

Platform: <claude-code|codex|droid|cursor|grok>

Written:
- <CLAUDE.md and/or AGENTS.md> flow-next snippet (marker-fenced, sentinel v<N>)
- <repo-root>/SPEC.md (only if Step 4a "Copy template" was chosen — otherwise omit this line)
- .flow/criteria.md (only if the Global criteria "Scaffold" option was chosen — otherwise omit this line)

Nothing was copied into .flow/ — flowctl comes from the plugin install:
  flowctl --help        # every command
  flowctl usage         # CLI cheatsheet + orchestration recipes, always current
```

**If PLATFORM=cursor, also show:**
```
Cursor host notes:
- flowctl resolves from the plugin install via the skill's own absolute path (Cursor exposes no plugin-root env vars) — nothing is copied into the repo
- Review default: host (host-native cross-family subagent; the model is named on the `reviewer` tier of the AGENTS.md routing block)
- Ralph: unsupported on Cursor (not offered; not registered)
```

**If PLATFORM=grok, also show:**
```
Grok host notes:
- flowctl resolves from the plugin install via the skill's own absolute path (Grok exposes no plugin-root env vars) — nothing is copied into the repo
- Docs: /flow-next: slash snippet (CLAUDE.md default lifecycle target; Grok also reads AGENTS.md)
- Routing block: AGENTS.md (where host review reads the `reviewer` tier)
- Review: host offered (single-native-family fail-closed for Grok writers) + rp/codex/copilot/cursor/none
- No .codex/agents copy; Ralph: unsupported on Grok (not offered; not registered)
- Detection: GROK_AGENT=1 (not ~/.grok or PATH)
```

**If PLATFORM=codex, also show:**
```
Codex project setup:
- .codex/agents/*.toml (<N> agent configs)
- Ralph hooks: only if Ralph was enabled (via ralph-init → .codex/hooks.json); otherwise none
```

**Then always show:**
```
Configuration (use flowctl config set to change):
- Memory: <enabled|disabled>
- Plan-Sync: <enabled|disabled>
- Plan-Sync cross-spec: <enabled|disabled>
- GitHub scout: <enabled|disabled>
- HTML artifacts: <enabled|disabled>
- Spec ids: <flow|tracker|unset>   # only meaningful when a tracker is configured; tracker is the team default
- Review backend: <host|codex|rp|copilot|cursor|none>

Documentation updated:
- <files updated or "none">

Model routing: <ROUTING_OUTCOME — "written to CLAUDE.md" | "kept (yours)" | "skipped (shim)" | "skipped (docs declined)" | "skipped (headless)">
- The block is a commented example; edit it to name the models you want per tier.

Notes:
- Plugin updates need no per-repo action, on any host — nothing was copied, so nothing goes stale. Re-run /flow-next:setup only when setup says the snippet schema bumped, or to change configuration / seed files.
- Ralph: answered in the setup ceremony (default off; skipped entirely on Cursor and Grok — unsupported). To enable later on supported hosts: /flow-next:ralph-init (merges project hooks; plugin ships none)
- Live QA stage: off by default. `flowctl config set pipeline.qa on` makes /flow-next:pilot run one live /flow-next:qa pass over the finished build before make-pr (needs a running app plus a browser driver)
- Use Linear / GitHub Issues / GitLab / Jira for project management? Run /flow-next:tracker-sync to configure the (opt-in) two-way tracker bridge — it runs a discovery ceremony (detects Linear MCP / LINEAR_API_KEY / gh auth / glab auth or GITLAB_TOKEN / JIRA_BASE_URL + credential, asks, writes config), then syncs specs ⇄ issues; on Linear it additionally makes your PRs reviewable as Linear Diffs. Skips cleanly if you don't use a tracker; adds nothing to the base install until enabled.
- Uninstall (run manually): remove the <!-- BEGIN/END FLOW-NEXT --> and <!-- flow-next:model-routing:start/end --> blocks from docs (plus any legacy .flow/bin, .flow/templates, .flow/usage.md leftovers, if you kept them) — or run /flow-next:uninstall for full cleanup (also strips Ralph guard hook entries from project settings)
- This setup is optional - plugin works without it
```
**Tracker-sync proposal (always show, after the Notes block).** Surface the tracker bridge as an explicit optional next step — the discovery ceremony is the bridge's own setup, separate from this skill (which never touches tracker config, keeping the zero-dep base clean):

```
Optional next step — connect a tracker:
  If your team lives in Linear, GitHub Issues, GitLab, or Jira, run  /flow-next:tracker-sync  to set up the
  two-way bridge (spec ⇄ issue, status, comments) and make PRs reviewable as Linear Diffs.
  Fully opt-in — nothing syncs until you confirm it in the discovery ceremony.
```

