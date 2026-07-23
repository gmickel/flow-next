# Flow-Next Setup Workflow

Follow these steps in order. This workflow is **idempotent** - safe to re-run.

## Step 0: Resolve plugin path and detect platform

The plugin root is the parent of this skill's directory. From this SKILL.md location, go up to find `scripts/` and `.claude-plugin/`.

Example: if this file is at `~/.claude/plugins/cache/.../flow-next/0.3.12/skills/flow-next-setup/workflow.md`, then plugin root is `~/.claude/plugins/cache/.../flow-next/0.3.12/`.

Store this as `PLUGIN_ROOT` for use in later steps.

### Platform detection

Detect which platform is running:

```bash
# Positive Cursor install signal: resolved PLUGIN_ROOT lives under ~/.cursor/
# (local install-cursor.sh OR team-marketplace repo-import cache). Do NOT key
# on codex/ absence — marketplace whole-repo imports contain codex/ and still
# classify as cursor. Codex installs resolve under $CODEX_HOME (~/.codex) and
# the shared source tree resolves to a workspace path; neither matches.
PLUGIN_ROOT_ABS="$(cd "${PLUGIN_ROOT}" 2>/dev/null && pwd -P || printf '%s' "${PLUGIN_ROOT}")"
CURSOR_HOME_ABS="$(cd "${HOME}/.cursor" 2>/dev/null && pwd -P || printf '%s' "${HOME}/.cursor")"

if [ -n "${DROID_PLUGIN_ROOT:-}" ]; then
  PLATFORM="droid"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  PLATFORM="claude-code"
elif [ -n "${CURSOR_AGENT:-}" ] \
  && [ -f "${PLUGIN_ROOT}/.cursor-plugin/plugin.json" ] \
  && case "${PLUGIN_ROOT_ABS}" in \
       "${CURSOR_HOME_ABS}"|"${CURSOR_HOME_ABS}"/*) true ;; \
       *) false ;; \
     esac; then
  PLATFORM="cursor"
elif [ -n "${GROK_AGENT:-}" ]; then
  PLATFORM="grok"
else
  PLATFORM="codex"
fi
```

**Cursor ordering matters.** Cursor exposes **no** plugin-root env var, so without the `CURSOR_AGENT` check it would fall through to the `codex` branch and get Codex-shaped project instructions (`$flow-next-plan` command names + `.codex/` setup) — wrong, because a Cursor install (local or team-marketplace) drives the workflow with `/flow-next:*` slash commands and resolves `flowctl` via `.flow/bin/flowctl`. `CURSOR_AGENT` is Cursor's own signal (set in its agent shell; it also sets `CI=1` / `CURSOR_TRACE_ID`, but `CURSOR_AGENT` is the canonical one). The `CURSOR_AGENT` branch MUST come before the `else → codex` fallback.

**Why the `.cursor-plugin/plugin.json` guard (don't classify Codex-hosted-in-Cursor as Cursor).** `CURSOR_AGENT` is **inherited by child processes** — so when Codex is launched *from* a Cursor Agent shell, the Codex process also sees `CURSOR_AGENT`, and a bare env check would misclassify a genuine Codex setup as `cursor` (skipping the `.codex/` agent + hook copy and writing the `/flow-next:` snippet instead of the Codex `$flow-next-` one — leaving the Codex setup incomplete). The env var alone only proves "a Cursor agent is somewhere in the process ancestry," not "this plugin is a Cursor install." So the branch ALSO requires the `.cursor-plugin/plugin.json` manifest at the **resolved `PLUGIN_ROOT`**: present in real Cursor installs and in the dual-manifest source tree, but **absent** from a pure `~/.codex` install. A Codex process that merely inherited `CURSOR_AGENT` and resolves a Codex-home `PLUGIN_ROOT` (no Cursor manifest) correctly falls through to `codex`. (Same inherited-env-var class as the codex-delegation `CLAUDECODE` guard.)

**Positive path discriminator — `PLUGIN_ROOT` under `~/.cursor/` (never `codex/` absence).** The manifest + env checks alone are not enough when Codex runs from the **checked-in plugin source** inside a Cursor shell (Codex marketplace points at `./plugins/flow-next`, which carries `.cursor-plugin/`, `.codex-plugin/`, and the `codex/` mirror) — there the Cursor manifest is present in the workspace tree, so env+manifest would misfire. The positive signal is that a **real Cursor install** resolves `PLUGIN_ROOT` under `~/.cursor/` — local `install-cursor.sh`/`.ps1` → `~/.cursor/plugins/local/flow-next/`; team-marketplace repo-import → Cursor's marketplace plugin cache under `~/.cursor/` (and that cache **may contain `codex/`** because the whole plugin source is imported; explicit component paths in `.cursor-plugin/plugin.json` keep Cursor from loading the mirror as skills). A genuine Codex install resolves under `$CODEX_HOME` (default `~/.codex`); the shared source tree resolves to a workspace path. Neither is under `~/.cursor/`, so both correctly fall through to `codex` even with inherited `CURSOR_AGENT`. **Do not** key detection on the `codex/` directory being absent — that misclassifies marketplace repo-imports as Codex.

**Grok ordering matters (fn-126).** Grok Build (xAI's `grok` CLI) reads the canonical Claude plugin format AS-IS and drives with `/flow-next-*` / `/flow-next:` slash commands — not the Codex `$flow-next-` mirror. Without a positive signal it fell through to `else → codex` and setup wrote Codex-shaped `$flow-next-` snippets into AGENTS.md (dogfood 2026-07-22). **Probe-verified signal:** `GROK_AGENT=1` is set BY grok in its agent shell (absent from a plain-shell control on the same machine). **Rejected non-signals:** `~/.grok/` exists on the machine regardless (install dir), and `~/.grok/bin` on `PATH` is profile-level — neither distinguishes a grok session. The `GROK_AGENT` branch MUST come after Droid / Claude / Cursor (so a real Claude/Cursor/Droid host that merely inherited `GROK_AGENT` from a parent grok shell still classifies by its own higher-precedence signal) and BEFORE the `else → codex` fallback.

**Known nesting edge (Droid → Grok) — NEEDS-HUMAN.** The probe disproved `CLAUDE_PLUGIN_ROOT` propagation into a grok child, so Claude-from-parent does not misfire. It did **not** disprove `DROID_PLUGIN_ROOT` propagation: if a grok child inherits `DROID_PLUGIN_ROOT` from a Droid parent shell, the cascade classifies as `droid` (higher precedence). Treat nested Droid→Grok as **unsupported pending a this-process-is-grok discriminator** unless a NEEDS-HUMAN smoke confirms `DROID_PLUGIN_ROOT` does not propagate. Claude/Cursor-from-grok remain correct via higher-precedence signals.

**Matrix (detection fixtures):** (1) marketplace whole-repo import under `~/.cursor/` + may have `codex/` → `cursor`; (2) local `install-cursor` under `~/.cursor/plugins/local/` (no `codex/`) → `cursor`; (3) Codex under `$CODEX_HOME` / `~/.codex` with inherited `CURSOR_AGENT` → `codex`; (4) Claude (`CLAUDE_PLUGIN_ROOT`) / Droid (`DROID_PLUGIN_ROOT`) still win first — precedence unchanged; (5) standalone `GROK_AGENT=1` (no higher signal) → `grok`; (6) `GROK_AGENT=1` + `CLAUDE_PLUGIN_ROOT` / `CURSOR_AGENT`(+cursor install) / `DROID_PLUGIN_ROOT` → higher host wins; (7) plain shell (no host signal) → `codex`.

Store `PLATFORM` for use in later steps. This determines:
- Which manifest to read for version (`plugin.json`)
- Which docs file to prefer (CLAUDE.md vs AGENTS.md)
- Whether to copy Codex agents to project (hooks are **not** copied here — Ralph is opt-in via the Ralph question + `/flow-next:ralph-init`)
- Which command-name syntax the docs snippet uses (`/flow-next:plan` for Claude Code / Droid / **Cursor** / **Grok**; `$flow-next-plan` for Codex)

## Step 1: Initialize .flow/

Use flowctl init (idempotent - safe to re-run, handles upgrades):

```bash
"${PLUGIN_ROOT}/scripts/flowctl" init --json
```

This creates/upgrades:
- `.flow/` directory structure (specs/, tasks/, memory/)
- `meta.json` with schema version
- `config.json` with defaults (merges new keys on upgrade)

If the repo still has a pre-1.0 `.flow/epics/` layout, port it by hand before continuing (see `.flow/usage.md` "Pre-1.0 layout porting").

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
- If **same version**: tell user "Already set up with v<VERSION>. Re-run to refresh files + docs? (y/n)"
  - If yes: continue from Step 2b — the mode gate runs on EVERY pass (PR #227 review: a same-version re-run in a plugin-mode repo must not fall straight into Step 3's copies); copy-mode repos then flow into Step 3's re-copy (idempotent; same-version refresh should NOT skip the file copy, otherwise a project running an unchanged version number but a moved template lands docs that point at a missing path)
  - If no: done
- If **older version**: tell user "Updating from v<OLD> to v<NEW>" and continue

**If no `setup_version`:** continue (first-time setup)

## Step 2b: Setup mode (fn-121 — Claude Code only)

Two install modes exist. **Copy mode** (the only mode before fn-121, and the only mode on non-Claude hosts): flowctl + templates + usage.md are copied into `.flow/` as repo-committed snapshots; plugin updates require a setup re-run to refresh them. **Plugin mode** (Claude Code only): nothing is copied — bare `flowctl` rides the plugin's `bin/` PATH injection, the guide is pulled via `flowctl usage`, the spec template resolves through the bundled cascade, and the only repo artifact is a slim versioned CLAUDE.md snippet. Plugin-mode repos never need a setup re-run for plugin updates.

```bash
CURRENT_MODE=$(jq -r '.setup_mode // empty' .flow/meta.json 2>/dev/null)
```

**If `PLATFORM` is not `claude-code`:** plugin mode is Claude-Code-only (Cursor exposes no plugin-root env vars and no bin PATH injection; Grok likewise has no plugin-root bin PATH injection; Codex resolves `$HOME/.codex/scripts/flowctl`; Droid's bin support is unverified) — never OFFER it on these hosts. But never silently CONVERT either (PR #227 review): when `CURRENT_MODE` is `plugin` (a Claude-Code-managed repo visited from this host), ask via `AskUserQuestion` (sync-codex.sh carries an equivalent guard in the mirror): `Keep plugin mode` — skip Step 3, Step 4's copies, and the Step 7c stamp entirely (set `MODE=plugin-kept`; config/ceremony steps still run, and the Docs step may target AGENTS.md only — CLAUDE.md's FLOW-NEXT block is the Claude-Code-managed rail and is NEVER touched in kept mode, PR #227 review: writing the copy-mode snippet there would destroy the sentinel while the plugin stamp stands) — or `Convert to copy mode` — proceed as copy (writes the snapshots; Step 7c stamps copy). Recommend per host (PR #227 review): on Codex/Droid recommend Keep (Codex skills self-resolve flowctl from `$HOME/.codex/scripts/`; Droid reads the plugin root envs) — on Cursor **and Grok** recommend CONVERT and say why: neither exposes plugin-root env vars / bin PATH injection, so with no `.flow/bin` the skill preambles cannot resolve flowctl and flow-next skills will not function on this host until the repo has copies. When `CURRENT_MODE` is anything else, set `MODE=copy` silently and continue to Step 3.

**If `PLATFORM=claude-code` and `CURRENT_MODE` is empty (first mode decision):** ask via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror — unreachable in practice, since this branch requires `PLATFORM=claude-code`):

- **header**: `Setup mode`
- **question**: `This decides where the flowctl CLI lives (the small task-tracking tool every flow-next skill shells out to). Does anyone use this repo WITHOUT the Claude Code plugin — Codex/Cursor/Droid teammates, CI jobs, or plain terminal sessions? Full comparison: https://flow-next.dev/skills/setup/`
- **options**:
  - `No — plugin mode (Recommended for Claude-Code-only repos)` — nothing is copied into the repo; Claude Code resolves flowctl from the plugin itself, and plugin updates land silently (you never re-run setup). The only repo artifact is a slim CLAUDE.md snippet.
  - `Yes — copy mode` — commits snapshot copies of flowctl under `.flow/bin/` so plugin-less tools (other agents, CI, plain shells) can run it. Trade-off: after each plugin update, re-run `/flow-next:setup` per repo to refresh the copies.
  - `abort` — exit cleanly; nothing written beyond the idempotent Steps 1-2.

**If `CURRENT_MODE` is set (re-run):** print `Setup mode: <CURRENT_MODE>` and ask keep-or-switch (same tool): `Keep <CURRENT_MODE> (Recommended)` / `Switch to <other>` / `abort`. Keep = refresh within the current mode.

**Transition table (copy → plugin), consent-gated — NEVER silent deletion:**

1. Enumerate leftover copy artifacts actually present: `.flow/bin/flowctl`, `.flow/bin/flowctl.cmd`, `.flow/bin/flowctl.py`, `.flow/bin/flowctl_bootstrap.py`, `.flow/bin/flowctl-help.txt`, `.flow/templates/spec.md`, `.flow/usage.md`.
2. None present → proceed as plugin mode.
3. Any present → list them and ask: `Remove copy-mode artifacts? (required for plugin mode)` with options `Remove listed files` / `Keep them — stay in copy mode`. On Remove: `git rm -q` tracked paths, plain `rm` for untracked ones — but FIRST surface any listed tracked file with uncommitted modifications and exclude it from removal (never force-remove modified files; the user resolves those manually).
4. After removal attempt, re-enumerate. Anything still present (decline, modified-file exclusions, partial failure) → print the exact remaining paths, set `MODE=copy`, and continue as copy mode. `flowctl setup-mode set plugin` (Step 7c) would refuse anyway — the plumbing enforces this table even on prose error.

**Plugin mode path through the rest of this workflow:** skip Step 3 and Step 4's copy block and Step 4's `.flow/usage.md` handling entirely (nothing is copied); Step 4a (repo-root SPEC.md offer) still runs — it seeds a user-owned file, not a `.flow/` copy. Steps 5-7 run normally with the plugin-mode adjustments marked inline (Docs template + Step 7c stamp). Copy mode = every step exactly as written.

## Step 3: Create .flow/bin/ and .flow/templates/

**Copy mode only — in plugin mode skip to Step 4a.**

```bash
mkdir -p .flow/bin .flow/templates
```

## Step 4: Copy files

**Copy mode only — in plugin mode skip to Step 4a.**

**IMPORTANT: Do NOT read flowctl.py - it's too large. Just copy it.**

Copy using Bash `cp` with absolute paths:

```bash
cp "${PLUGIN_ROOT}/scripts/flowctl" .flow/bin/flowctl
cp "${PLUGIN_ROOT}/scripts/flowctl.cmd" .flow/bin/flowctl.cmd
cp "${PLUGIN_ROOT}/scripts/flowctl.py" .flow/bin/flowctl.py
cp "${PLUGIN_ROOT}/scripts/flowctl_bootstrap.py" .flow/bin/flowctl_bootstrap.py
cp "${PLUGIN_ROOT}/scripts/flowctl-help.txt" .flow/bin/flowctl-help.txt
cp "${PLUGIN_ROOT}/templates/spec.md" .flow/templates/spec.md
chmod +x .flow/bin/flowctl
```

`flowctl.cmd` is the Windows batch launcher (cmd.exe / PowerShell — Claude Desktop, native Codex, native Cursor); no `chmod +x` needed (PATHEXT resolves it, not the exec bit). The bash `flowctl` and the `.cmd` share the small `flowctl_bootstrap.py` front end, tracked `flowctl-help.txt`, and source-of-truth `flowctl.py`. Only exact static help/usage requests use fast paths; every other command compiles tracked source in memory and never reads executable cache state.

`.flow/templates/spec.md` is the canonical 7-section spec scaffold that the AGENTS.md / CLAUDE.md snippet points downstream agents at. Copying it project-local means the path the snippet references resolves without depending on the plugin install location.

### Step 4a: Opt-in `<repo_root>/SPEC.md` customization (interactive)

The spec-template discovery cascade prefers a customized scaffold at the repo root over `.flow/templates/spec.md` and the bundled plugin copy. This step lets the user opt into seeding `<repo_root>/SPEC.md` from the canonical template so they can edit it without diving into `.flow/templates/`.

**Detect what's already at the repo root** (case-insensitive FS handling — macOS APFS, Windows NTFS):

```bash
HITS=$(ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l | tr -d ' ')
```

Then branch:

**1. `HITS=0` (neither file exists)** — ask the user via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror):

- **header**: `Copy canonical spec template to <repo-root>/SPEC.md?`
- **body**: `Every new flow-next spec starts from a template. Lookup order: <repo-root>/SPEC.md first, then .flow/templates/spec.md, then the plugin's bundled copy — so a SPEC.md at the repo root is where you customize section wording for THIS project without touching .flow/ internals. Skipping is safe — the later fallbacks always resolve, and you can opt in any time by copying .flow/templates/spec.md to the repo root.`
- **options**:
  - `Copy template` — write `<repo_root>/SPEC.md` from the bundled template (carries the customization-location top-comment). Print the path so the user knows where to edit.
  - `Skip` — no write. Cascade falls through to `.flow/templates/spec.md`. Documentation cross-links (CLAUDE.md / AGENTS.md snippets) explain how to opt in later: just copy `.flow/templates/spec.md` to `<repo-root>/SPEC.md`.
  - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, Step 3 mkdir, Step 4 bin/template copies above) may already have run; they are idempotent and safe to leave. No `<repo_root>/SPEC.md` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

On `Copy template`: write the file via Bash `cp` with absolute paths.

```bash
cp "${PLUGIN_ROOT}/templates/spec.md" SPEC.md
```

**2. `HITS=1` (single hit OR case-insensitive FS collapsing both to one)** — capture whichever filename actually exists into `EXISTING` (no prompt). Both the read-for-compare and the overwrite target route through `EXISTING` so lowercase `spec.md` repos do not silently fall back to a missing `SPEC.md`:

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
- **Customized** (any deviation after normalization): do NOT silently replace. Ask the user via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror):
  - **header**: `Overwrite customized <repo-root>/$EXISTING?`
  - **body**: `<repo-root>/$EXISTING exists and differs from the canonical template shipped with this plugin version (CRLF and trailing newlines ignored). Overwriting replaces your edits. Keeping skips this file (you can manually merge later via diff against \`${PLUGIN_ROOT}/templates/spec.md\`).`
  - **options**:
    - `Keep mine (Recommended)` — leave `<repo-root>/$EXISTING` unchanged. Print the path to the canonical template so the user can diff manually.
    - `Overwrite with canonical` — replace `<repo-root>/$EXISTING` (same filename — do NOT rename lowercase `spec.md` to uppercase `SPEC.md` here; preserve the user's casing) with the bundled template content. Repo customization is lost.
    - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, Step 3 mkdir, Step 4 bin/template copies above) may already have run; they are idempotent and safe to leave. No `<repo-root>/$EXISTING` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

**Note:** Setup writes uppercase `SPEC.md` only on the **fresh-seed** path (`HITS=0` `Copy template`). Never seed lowercase `spec.md` from scratch. The lowercase entry in the cascade is read-only at discovery time — present only for users who deliberately created lowercase. On the **re-setup overwrite** path above, preserve the user's existing filename casing via `$EXISTING` (so a lowercase `spec.md` stays lowercase after `Overwrite with canonical`).

Then handle `.flow/usage.md` — preserve any repo-customized variant:

1. Read [../../templates/usage.md](../../templates/usage.md) (this is the canonical content, bundled at `${PLUGIN_ROOT}/templates/usage.md` since fn-121).
2. If `.flow/usage.md` does not exist → write the canonical content.
3. If `.flow/usage.md` exists → compare byte-for-byte with the canonical content:
   - **Identical**: no-op (skip the write entirely — re-running setup must not bump mtime on unchanged files).
   - **Customized** (any deviation): do NOT overwrite. Ask the user via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror):
     - **header**: `Overwrite customized .flow/usage.md?`
     - **body**: `.flow/usage.md exists and differs from the canonical template shipped with this plugin version. Overwriting replaces your edits. Keeping skips this file (you can manually merge later via diff against \`${PLUGIN_ROOT}/templates/usage.md\`).`
     - **options**:
       - `Keep mine (Recommended)` — leave `.flow/usage.md` unchanged. Print the path to the canonical template so the user can diff manually.
       - `Overwrite with canonical` — replace `.flow/usage.md` with the template content. Repo customization is lost.
       - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, Step 3 mkdir, Step 4 bin/template copies above) may already have run; they are idempotent and safe to leave. No `.flow/usage.md` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

## Step 4b: Codex-specific project setup (PLATFORM=codex only)

**Skip this step entirely if PLATFORM is not `codex`.** (Claude Code / Droid / Cursor / Grok all skip it — Cursor and Grok drive the workflow with `/flow-next:*` slash commands and resolve `flowctl` via `.flow/bin/flowctl`, not project-scoped `.codex/` agents. Grok never copies `.codex/agents`.)

On Codex, agents live in project-scoped `.codex/` directories (not in the plugin cache). Copy them. **Do not copy or enable Ralph hooks here** — hooks are opt-in via the Ralph question (Step 6d, always asked) and `/flow-next:ralph-init` registration prose.

### Copy agent .toml files

```bash
# Source: pre-built agents from plugin (or global install)
AGENTS_SRC="${PLUGIN_ROOT}/codex/agents"
[ -d "$AGENTS_SRC" ] || AGENTS_SRC="$HOME/.codex/agents"

if [ -d "$AGENTS_SRC" ]; then
  mkdir -p .codex/agents
  cp "$AGENTS_SRC"/*.toml .codex/agents/
  echo "Copied $(ls .codex/agents/*.toml 2>/dev/null | wc -l | tr -d ' ') agent configs to .codex/agents/"
else
  echo "Warning: No agent .toml files found at ${PLUGIN_ROOT}/codex/agents/ or ~/.codex/agents/"
fi
```

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

# fn-97: at least one bridge CLI on PATH gates the Model Routing question in 6d
# on non-host-native hosts (with zero bridges every wiring route in the scaffold
# would be an inert install-note comment, so the question is not offered —
# install a bridge CLI and re-run /flow-next:setup to get it).
# fn-123 R6 / fn-126: PLATFORM=cursor or PLATFORM=grok is the exception —
# host-native AGENTS.md pins need no external bridge CLI, so Model Routing is
# still offered when ROUTING_ASK=1.
BRIDGE_DETECTED=0
if [[ "$HAVE_CODEX" == "1" || "$HAVE_CURSOR" == "1" || "$HAVE_GROK" == "1" ]]; then
  BRIDGE_DETECTED=1
fi

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

# Optional model-routing scaffold ceremony (Step 6d question + Step 7 processing)
# is offered ONLY in an interactive setup. On non-host-native hosts also require a
# bridge CLI (BRIDGE_DETECTED=1, fn-97). On PLATFORM=cursor or PLATFORM=grok offer
# when interactive regardless of bridges (fn-123 R6 / fn-126 host-native pins).
# Under ANY non-interactive / autonomous marker, the question is skipped SILENTLY
# — setup must never block a headless driver. Scan the WHOLE autonomy-marker
# family (Ralph / receipt-path / autonomous / mode token), not a fixed pair —
# the same family every lifecycle skill honors.
ROUTING_ASK=1
if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
      || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* ]]; then
  ROUTING_ASK=0
fi
```

Store detection results for use in questions. When showing options, indicate current value if set (e.g., "(current)" after the matching option label).

### 6b: Check docs status

Choose the correct template based on platform AND mode:
- **Codex** (`PLATFORM=codex`): read [templates/agents-md-snippet.md](templates/agents-md-snippet.md) — uses `$flow-next-plan` syntax
- **Claude Code in plugin mode** (`MODE=plugin`): read [templates/claude-md-snippet-plugin.md](templates/claude-md-snippet-plugin.md) — bare `flowctl` (plugin-bin PATH), `flowctl usage` pull directives, internal `<!-- flow-next:snippet:vN -->` sentinel. CLAUDE.md is the REQUIRED target (the rail's guarantee is CLAUDE.md's every-turn presence); AGENTS.md is an optional secondary.
- **Claude Code (copy mode) / Droid / Cursor / Grok**: read [templates/claude-md-snippet.md](templates/claude-md-snippet.md) — uses `/flow-next:plan` slash syntax (Cursor runs the same slash commands; on Cursor the snippet lands in AGENTS.md. Grok drives with `/flow-next-` slash commands and reads BOTH CLAUDE.md and AGENTS.md — lifecycle snippet targets CLAUDE.md by default; a pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form, marker-scoped)

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
```

Only include lines for config values that are set. If no config is set, skip this notice.

### 6d: Build questions list

Build the questions array dynamically. **Only include questions for config values that are NOT already set** — existing config is preserved, never overwritten. To change an already-set value, the user runs `flowctl config set <key> <value>` directly (the commands are surfaced in 6c's current-config notice).

Skipped questions = config values already persisted from a prior run. Asking again would either no-op (same answer) or silently flip a deliberate user choice — both are wrong. The grouped single-prompt design (a single `AskUserQuestion` call below, with one questions array containing only the unset entries) means a re-run with all config set produces zero config questions and asks only Docs + Star, plus Ralph when `RALPH_ASK=1` and Model Routing when its interactive platform/bridge gate passes.

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

**Review question** (include if CURRENT_BACKEND is empty):

**When `PLATFORM=cursor`** — lead with `host` (Recommended); keep every existing backend selectable; label the Cursor CLI option as circular/secondary from inside Cursor (fn-123 R6):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land. From inside Cursor, prefer a host-native fresh-context subagent pinned cross-family via AGENTS.md model-routing (no second CLI). External CLIs remain available. Guide: https://flow-next.dev/review/workflow/",
  "options": [
    {"label": "Host (Recommended)", "description": "Fresh-context host-native subagent; pin a cross-family Cursor model slug in the AGENTS.md model-routing section (setup scaffolds the pins). No external CLI. Preferred from inside Cursor."},
    {"label": "Codex CLI", "description": "OpenAI's codex CLI, reviews on its top reasoning tier (GPT family). Cross-platform, simple setup. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
    {"label": "Copilot CLI", "description": "Routes to Claude- or GPT-family reviewers via your GitHub Copilot plan. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
    {"label": "Cursor CLI (secondary — circular from inside Cursor)", "description": "Runs the external cursor-agent CLI. Circular when already inside Cursor — prefer Host. Still selectable for multi-family reach via the cursor-agent model menu. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
    {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, far fewer tokens than full-repo approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
    {"label": "None", "description": "Skip AI reviews for now. Set later with flowctl config set review.backend <name>, or per-run via --review"}
  ],
  "multiSelect": false
}
```

**When `PLATFORM=grok`** (fn-126) — offer `host` with the fail-closed cross-family caveat (Grok is single-native-family `grok-4.5`) plus every external backend; when `HAVE_CODEX=1` mark Codex Recommended (true cross-family vs a Grok writer):
```json
{
  "header": "Review",
  "question": "Which review backend? Plans and implementations get reviewed before they land. Grok's only native model family is grok-4.5 — host-native review fails closed unless the writer is non-Grok; cross-family review comes via bridge backends (codex/cursor/copilot). Guide: https://flow-next.dev/review/workflow/",
  "options": [
    {"label": "Host", "description": "Fresh-context host-native subagent; pin from AGENTS.md model-routing (setup scaffolds). Fail-closed: Grok is single-native-family (grok-4.5) — native host review refuses same-family self-review (interactive → ask; autonomous → NEEDS_HUMAN) unless the writer is non-Grok. Cross-family via bridges."},
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

When `HAVE_CODEX=1` AND `PLATFORM` is NOT `codex` AND `PLATFORM` is NOT `cursor`, append ` (Recommended - cross-family default)` to the `Codex CLI` label: the recommended multi-model pipeline reviews cross-family FROM THE WRITER, and on a Claude Code / Droid / Grok host codex review is a different family than the session writer - so this question carries the ceremony's `review.backend codex` offer while the key is unset (fn-97). On `PLATFORM=cursor` do NOT add the Codex Recommended label — `Host (Recommended)` already leads. On a Codex host (`PLATFORM=codex`) do NOT add the label: the writer is GPT-family (the session model, or the optional terra worker pin), so codex review would be SAME-family - prefer a detected non-GPT backend there (copilot / cursor with a Claude-family model) and leave the options unannotated when none is detected. When `review.backend` is ALREADY set to something else, this question is skipped (existing config is never silently overwritten) - the offer instead rides the Model Routing scaffold as an explicit opt-in switch, Step 7's step 8 below.

Stored value is a bare backend name by default (`host` / `codex` / `copilot` / `cursor` / `rp` / `none`). Power users can also write a full spec like `codex:gpt-5.4:high`, `copilot:claude-opus-4.5:xhigh`, or `cursor:gpt-5.5-high` (cursor takes a model only — no `:effort`) via `flowctl config set review.backend <spec>` after setup — the review commands accept both forms. Backend `host` is bare only (no `host:<model>` — pins live in the AGENTS.md model-routing section).

**Model Routing question** — include only when `ROUTING_ASK=1` AND
(`BRIDGE_DETECTED=1` OR `PLATFORM=cursor` OR `PLATFORM=grok`). The frozen
option set is `Scaffold` / `Scaffold + enable codex delegation` / `Skip`; the
delegation option exists only when `HAVE_CODEX=1`.

Resolve `PLATFORM` first, then **MUST read exactly one applicable direct
question reference** and add its question object to the grouped prompt:

- Bridge-host offer gate: `ROUTING_ASK=1` AND `BRIDGE_DETECTED=1`. Cursor and
  Grok are host-native exceptions.
- `cursor` → [references/model-routing-question-cursor.md](references/model-routing-question-cursor.md)
- `grok` → [references/model-routing-question-grok.md](references/model-routing-question-grok.md)
- `claude-code`, `droid`, or `codex` →
  [references/model-routing-question-bridge.md](references/model-routing-question-bridge.md)

Unknown `PLATFORM` fails open to the bridge question reference. If the gate is
false, do not read any model-routing question or implementation reference and
record `not offered`.

**Docs question** (always include — adjust default based on platform):

For **Claude Code in plugin mode** (`MODE=plugin`) — CLAUDE.md is the commit prerequisite, so the option set differs (no CLAUDE.md-less variant):
```json
{
  "header": "Docs",
  "question": "Write the Flow-Next snippet? Plugin mode requires it in CLAUDE.md (the always-loaded rail that replaces the copied files).",
  "options": [
    {"label": "CLAUDE.md (Recommended)", "description": "Required for plugin mode; marker-bounded block, content outside untouched"},
    {"label": "CLAUDE.md + AGENTS.md", "description": "Same block in both (AGENTS.md optional secondary)"},
    {"label": "Skip — fall back to copy mode", "description": "No rail means no plugin mode; setup continues as copy mode (Step 3-4 copies run before Step 7)"}
  ],
  "multiSelect": false
}
```
On `Skip — fall back to copy mode`: set `MODE=copy` and run the skipped Steps 3-4 copies NOW (before Step 7), then continue — `setup_mode` will stamp `copy` in Step 7c. Never stamp plugin without the CLAUDE.md rail.

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

For **Grok** (`PLATFORM=grok`) — Grok reads BOTH CLAUDE.md and AGENTS.md; lifecycle snippet defaults to CLAUDE.md (canonical Claude-format target, `/flow-next:` slash syntax — NOT the Codex `$flow-next-` one). A pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form (marker-scoped; text outside markers untouched). Model-routing block still targets AGENTS.md (where host-review workflows read it):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched. Grok loads both CLAUDE.md and AGENTS.md.",
  "options": [
    {"label": "CLAUDE.md only (Recommended)", "description": "Add flow-next section to CLAUDE.md (canonical Grok lifecycle target; /flow-next: slash syntax)"},
    {"label": "AGENTS.md only", "description": "Add flow-next section to AGENTS.md"},
    {"label": "Both", "description": "Add flow-next section to both files (recommended when you also want the model-routing block's sibling lifecycle snippet nearby)"},
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

Use `AskUserQuestion` with the built questions array (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.

**Note:** If docs are already current, adjust the Docs question description to mention "(already up to date)" or skip that question entirely.

**Note:** If no supported RepoPrompt CLI, codex, copilot, or cursor-agent is detected, add this note to the Review question: "No review backend detected. Install RepoPrompt CE (`rpce-cli`), codex, copilot, or cursor-agent for review support."

### 6e: Model-pin refresh ceremony (fn-115.2)

Runs on **fresh setup AND re-runs**, **after** Step 6d questions. Resolve the
gate before reading any ceremony instructions:

```bash
MODELS_ASK=1
if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
      || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* ]]; then
  MODELS_ASK=0
  MODELS_CEREMONY="skipped (autonomous)"
fi
```

When `MODELS_ASK=0`, do nothing else: no reference read, CLI probe, receipt
scan, question, config write, or summary noise. When `MODELS_ASK=1`, you
**MUST read and follow exactly one direct reference now**:
[references/model-pins.md](references/model-pins.md). Do not continue to Step 7
until that reference reaches its terminal outcome. Unknown/malformed gate state
fails open by reading the reference; only an explicit zero skips it.

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

**HTML Artifacts** (if question was asked):
- If "No": `"${PLUGIN_ROOT}/scripts/flowctl" config set artifacts.html.enabled false --json`
- If "Yes":
  1. `"${PLUGIN_ROOT}/scripts/flowctl" config set artifacts.html.enabled true --json`
  2. Ask ONE follow-up via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror) — track or ignore the artifact directory:
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
  3. Print the lavish-axi offer verbatim. **NEVER auto-install** — detect-and-instruct only, same discipline as /flow-next:map (global npm installs are user-consent territory):

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
- AGENTS.md on **Claude Code (copy mode) / Droid / Cursor / Grok**: use [templates/claude-md-snippet.md](templates/claude-md-snippet.md) (uses `/flow-next:plan` slash syntax — Cursor and Grok run the slash commands, so their AGENTS.md must carry the `/flow-next:` snippet, NOT the Codex `$flow-next-` one; a wrong Codex `$` block is consent-refreshed marker-scoped)
- CLAUDE.md on **Claude Code in plugin mode** (`MODE=plugin`): use [templates/claude-md-snippet-plugin.md](templates/claude-md-snippet-plugin.md) — the slim rail with the `<!-- flow-next:snippet:v1 -->` sentinel that `flowctl setup-mode set plugin` (Step 7c) verifies; writing the regular snippet here would make the plugin stamp refuse. AGENTS.md as an optional plugin-mode secondary gets the same plugin template.
- CLAUDE.md (any platform, copy mode — including Grok's default lifecycle target): use [templates/claude-md-snippet.md](templates/claude-md-snippet.md)

**Resolve the target file set:** an explicit Docs-question answer is authoritative - if the user is asked and selects specific files (or declines one), honor exactly that; never touch a file the user just deselected. The one addition is a backfill for the SKIPPED case: when the Docs question is omitted entirely because the block is already current (per the Note above), still run `apply` on each already-marker-bearing file. Rationale (R8): a current-but-hashless block (written by a pre-hash plugin version) would otherwise never reach `apply`, so its pristine hash never gets backfilled and the NEXT template change wrongly prompts "Overwrite customized?". `apply` on a current block is cheap and idempotent - it returns `unchanged` and records the missing hash. So: resolve targets = files chosen by the Docs question when it was asked; OR, when the Docs question was skipped, the files already carrying the `<!-- BEGIN FLOW-NEXT -->` marker. Run the helper once per resolved file.

For each resolved file (CLAUDE.md and/or AGENTS.md) - the block mechanics (marker-scoped replace, per-target pristine-hash tracking in `.flow/meta.json` `setup.block_hashes`) are deterministic flowctl plumbing; this step owns only the ask:

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
   - `ask` (reason `customized` or `hash-absent`) - the block differs from canonical and is not provably pristine. The helper wrote nothing; ask via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt for the Codex mirror):
     - **header**: `Overwrite customized <FILE>?` (substitute CLAUDE.md or AGENTS.md)
     - **body**: `<FILE> contains a flow-next marker block that differs from the canonical template shipped with this plugin version and is not recorded as pristine. Overwriting replaces the marker block only; content outside the markers is untouched either way.`
     - **options**:
       - `Keep mine (Recommended)` - run `"${PLUGIN_ROOT}/scripts/flowctl" setup-block resolve --file <FILE> --template <same template> --choice keep --json`. This records the `"customized"` sentinel so future re-runs never re-ask and never overwrite. Print the canonical template path so the user can diff manually (`${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md`).
       - `Overwrite with canonical` - run the same `setup-block resolve` command with `--choice overwrite`. This replaces the marker block with the canonical snippet and records the new pristine hash; customizations inside the markers are lost, content outside the markers is preserved.
       - `abort` - exit cleanly, no further writes. Earlier steps (init, file copies, config writes, prior docs-file decisions for any already-processed file) may already have run; they are idempotent and safe to leave. Everything from here onward is skipped (remaining docs files, the Model Routing scaffold, and the Star step). Re-run `/flow-next:setup` later to complete setup.

The marker-block boundaries are load-bearing: pre-existing prose outside `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` is **never** modified by this step, and only the flowctl helper performs writes. Only the bytes between (and including) those markers are candidates for replacement.

**Model Routing scaffold** (only if its question was asked). Run this
after the Docs block above and before Ralph/Star. Always re-read target files from
disk after Docs; never interleave the two writes.

- `Skip` → `ROUTING_OUTCOME="skipped"`; read no implementation reference.
- `Scaffold` or `Scaffold + enable codex delegation` → resolve `PLATFORM`, then
  **MUST read and follow exactly one direct implementation reference**:
  - `cursor` → [references/model-routing-cursor.md](references/model-routing-cursor.md)
  - `grok` → [references/model-routing-grok.md](references/model-routing-grok.md)
  - `claude-code`, `droid`, or `codex` →
    [references/model-routing-bridge.md](references/model-routing-bridge.md)

Unknown `PLATFORM` fails open to the bridge reference. Never read more than one
implementation reference for one run. The delegation opt-in remains
independent of whether a selected reference writes, keeps, or no-ops the block.

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

### Step 7c: Stamp setup mode (fn-121 — stamp-last commit point)

Runs after every Step 7 write, before Step 8. The stamp is the ONLY write path for `setup_mode` and lives in plumbing so a wrong prose path cannot produce an invalid stamp:

```bash
"${PLUGIN_ROOT}/scripts/flowctl" setup-mode set <MODE> --json
```

- `MODE=plugin-kept` (non-Claude host honoring an existing plugin stamp): do NOT run the stamp command at all — the existing `setup_mode: "plugin"` stays untouched. `MODE_OUTCOME="plugin (kept - managed from Claude Code)"`.
- `MODE=copy`: stamps unconditionally. `MODE_OUTCOME="copy"`.
- `MODE=plugin`: the command verifies the commit-point invariants itself — CLAUDE.md carries the `<!-- BEGIN FLOW-NEXT -->` block with a current `<!-- flow-next:snippet:vN -->` sentinel AND no copy artifacts remain — and refuses with an itemized failure list otherwise. On success `MODE_OUTCOME="plugin"`. On refusal (a Docs abort, a failed write, a kept-customized block without the sentinel, or leftover artifacts slipped through): print the failures verbatim, then MATERIALIZE copy mode before stamping it (PR #227 review: never stamp copy with the copy files absent) - run the skipped Step 3 mkdir and Step 4 copies now (idempotent), then `setup-mode set copy`, and set `MODE_OUTCOME="copy (plugin refused: <first failure>)"`. Never leave `setup_mode` unset on a completed setup run.

Include `Setup mode: <MODE_OUTCOME>` in the Step 8 summary.

## Step 8: Print Summary

```
Flow-Next setup complete!

Platform: <claude-code|codex|droid|cursor|grok>

Installed:
- .flow/bin/flowctl (v<VERSION>)
- .flow/bin/flowctl.cmd (Windows PowerShell/cmd launcher)
- .flow/bin/flowctl.py
- .flow/templates/spec.md
- .flow/usage.md
- <repo-root>/SPEC.md (only if Step 4a "Copy template" was chosen — otherwise omit this line)
```

**If PLATFORM=cursor, also show:**
```
Cursor host notes:
- Copy mode only (.flow/bin/flowctl) — Cursor exposes no plugin-root env vars / bin PATH injection
- Review default: host (host-native cross-family subagent pins in AGENTS.md model-routing)
- Ralph: unsupported on Cursor (not offered; not registered)
```

**If PLATFORM=grok, also show:**
```
Grok host notes:
- Copy mode only (.flow/bin/flowctl) — Grok exposes no plugin-root bin PATH injection
- Docs: /flow-next: slash snippet (CLAUDE.md default lifecycle target; Grok also reads AGENTS.md)
- Model-routing block: AGENTS.md (host-review pin target)
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
To use from command line:
  export PATH=".flow/bin:$PATH"
  flowctl --help

Configuration (use flowctl config set to change):
- Memory: <enabled|disabled>
- Plan-Sync: <enabled|disabled>
- Plan-Sync cross-spec: <enabled|disabled>
- GitHub scout: <enabled|disabled>
- HTML artifacts: <enabled|disabled>
- Review backend: <host|codex|rp|copilot|cursor|none>

Documentation updated:
- <files updated or "none">

Model routing scaffold: <ROUTING_OUTCOME — e.g. "written to CLAUDE.md" | "kept (customized)" | "unchanged (already current)" | "skipped" | "skipped (shim)" | "not offered">
<if Scaffold + enable codex delegation was chosen, also:>
- Codex delegation: <ROUTING_DELEGATE — "enabled (work.delegate=codex; first-use consent still required)" | "failed">

Model-pin ceremony (fn-115.2): <MODELS_CEREMONY — "written" | "stamped" | "skipped" | "skipped (autonomous)">
- Role map keys: models.roles.<fastJudge|review|delegate|scoutFast|scoutIntelligent>.<codex|copilot|cursor>
- Stamp key: models.verifiedAt (ISO date). Re-run setup to refresh; flowctl status nudges after ~90 days.

Notes:
- Re-run /flow-next:setup after plugin updates to refresh scripts
- Ralph: answered in the setup ceremony (default off; skipped entirely on Cursor and Grok — unsupported). To enable later on supported hosts: /flow-next:ralph-init (merges project hooks; plugin ships none)
- Use Linear / GitHub Issues / GitLab / Jira for project management? Run /flow-next:tracker-sync to configure the (opt-in) two-way tracker bridge — it runs a discovery ceremony (detects Linear MCP / LINEAR_API_KEY / gh auth / glab auth or GITLAB_TOKEN / JIRA_BASE_URL + credential, asks, writes config), then syncs specs ⇄ issues; on Linear it additionally makes your PRs reviewable as Linear Diffs. Skips cleanly if you don't use a tracker; adds nothing to the base install until enabled.
- Uninstall (run manually): rm -rf .flow/bin .flow/templates .flow/usage.md and remove the <!-- BEGIN/END FLOW-NEXT --> and <!-- flow-next:model-routing:start/end --> blocks from docs — or run /flow-next:uninstall for full cleanup (also strips Ralph guard hook entries from project settings)
- This setup is optional - plugin works without it
```
**Tracker-sync proposal (always show, after the Notes block).** Surface the tracker bridge as an explicit optional next step — the discovery ceremony is the bridge's own setup, separate from this skill (which never touches tracker config, keeping the zero-dep base clean):

```
Optional next step — connect a tracker:
  If your team lives in Linear, GitHub Issues, GitLab, or Jira, run  /flow-next:tracker-sync  to set up the
  two-way bridge (spec ⇄ issue, status, comments) and make PRs reviewable as Linear Diffs.
  Fully opt-in — nothing syncs until you confirm it in the discovery ceremony.
```

### Step 8a: Plugin-mode summary variant (fn-121)

When `MODE_OUTCOME` is `plugin`, the Step 8 copy-mode summary above is WRONG for this repo — its `Installed:` paths were deliberately never written, the `export PATH=".flow/bin:$PATH"` block points at a directory the plugin stamp forbids, and the "Re-run /flow-next:setup after plugin updates" note is exactly the treadmill plugin mode removes. Replace the `Installed:` block, the "To use from command line" block, and that Notes line with:

```
Setup mode: plugin (Claude Code)

Written:
- CLAUDE.md flow-next snippet (marker-fenced, sentinel v<N>)
- <repo-root>/SPEC.md (only if Step 4a "Copy template" was chosen — otherwise omit this line)

Nothing was copied into .flow/ — flowctl rides the plugin's PATH:
  flowctl --help        # any agent shell, no export needed
  flowctl usage         # CLI cheatsheet + orchestration recipes, always current

Plugin updates land silently. You never re-run setup for an update.
(Re-run /flow-next:setup only to change configuration or switch modes.)
```

Everything else in the Step 8 summary (Configuration block, Documentation updated, Model routing scaffold, Model-pin ceremony, the remaining Notes lines, the tracker proposal) prints unchanged in both modes.
