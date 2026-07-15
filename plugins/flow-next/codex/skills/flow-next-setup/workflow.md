# Flow-Next Setup Workflow

Follow these steps in order. This workflow is **idempotent** - safe to re-run.

## Step 0: Resolve plugin path and detect platform

The plugin root is the parent of this skill's directory. From this SKILL.md location, go up to find `scripts/` and `.claude-plugin/`.

Example: if this file is at `~/.claude/plugins/cache/.../flow-next/0.3.12/skills/flow-next-setup/workflow.md`, then plugin root is `~/.claude/plugins/cache/.../flow-next/0.3.12/`.

Store this as `PLUGIN_ROOT` for use in later steps.

### Platform detection

Detect which platform is running:

```bash
if [ -n "${DROID_PLUGIN_ROOT:-}" ]; then
 PLATFORM="droid"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
 PLATFORM="claude-code"
elif [ -n "${CURSOR_AGENT:-}" ] && [ -f "${PLUGIN_ROOT}/.cursor-plugin/plugin.json" ] && [ ! -d "${PLUGIN_ROOT}/codex" ]; then
 PLATFORM="cursor"
else
 PLATFORM="codex"
fi
```

**Cursor ordering matters.** Cursor exposes **no** plugin-root env var, so without the `CURSOR_AGENT` check it would fall through to the `codex` branch and get Codex-shaped project instructions (`$flow-next-plan` command names + `.codex/` setup) — wrong, because a Cursor local install drives the workflow with `/flow-next:*` slash commands and resolves `flowctl` via `.flow/bin/flowctl`. `CURSOR_AGENT` is Cursor's own signal (set in its agent shell; it also sets `CI=1` / `CURSOR_TRACE_ID`, but `CURSOR_AGENT` is the canonical one). The `CURSOR_AGENT` branch MUST come before the `else → codex` fallback.

**Why the `.cursor-plugin/plugin.json` guard (don't classify Codex-hosted-in-Cursor as Cursor).** `CURSOR_AGENT` is **inherited by child processes** — so when Codex is launched *from* a Cursor Agent shell, the Codex process also sees `CURSOR_AGENT`, and a bare env check would misclassify a genuine Codex setup as `cursor` (skipping the `.codex/` agent + hook copy and writing the `/flow-next:` snippet instead of the Codex `$flow-next-` one — leaving the Codex setup incomplete). The env var alone only proves "a Cursor agent is somewhere in the process ancestry," not "this plugin is the Cursor local install." So the branch ALSO requires the `.cursor-plugin/plugin.json` manifest at the **resolved `PLUGIN_ROOT`** (the value resolved above): it is present only in a real Cursor install (`~/.cursor/plugins/local/flow-next/`, written by `install-cursor.sh`/`.ps1`) and absent from the `~/.codex` install — so a Codex process that merely inherited `CURSOR_AGENT` resolves a `PLUGIN_ROOT` without that manifest and correctly falls through to `codex`. (Same inherited-env-var class as the codex-delegation `CLAUDECODE` guard.)

**And `[ ! -d "${PLUGIN_ROOT}/codex" ]` distinguishes a real Cursor install from the shared repo source tree.** The manifest check alone isn't enough when Codex runs from the **checked-in plugin source** inside a Cursor shell (the Codex marketplace points at `./plugins/flow-next`, which carries *all three* of `.cursor-plugin/`, `.codex-plugin/`, and the `codex/` mirror) — there the `.cursor-plugin/plugin.json` is present in the source tree, so a manifest-only check + inherited `CURSOR_AGENT` would still misfire. `install-cursor.sh`/`.ps1` **exclude the `codex/` mirror** (enforced by `test_install_cursor_parity.py`), so a real Cursor install has **no `codex/` directory** at its root, while the source tree (and anything Codex loads from it) does. Requiring `codex/` to be **absent** therefore admits only the genuine Cursor install and rejects the shared source tree.

Store `PLATFORM` for use in later steps. This determines:
- Which manifest to read for version (`plugin.json`)
- Which docs file to prefer (CLAUDE.md vs AGENTS.md)
- Whether to copy Codex agents and hooks to project
- Which command-name syntax the docs snippet uses (`/flow-next:plan` for Claude Code / Droid / **Cursor**; `$flow-next-plan` for Codex)

## Step 1: Initialize .flow/

Use flowctl init (idempotent - safe to re-run, handles upgrades):

```bash
"${PLUGIN_ROOT}/scripts/flowctl" init --json
```

This creates/upgrades:
- `.flow/` directory structure (specs/, tasks/, memory/; legacy `epics/` is preserved when present, see Step 1b for migration)
- `meta.json` with schema version
- `config.json` with defaults (merges new keys on upgrade)

## Step 1b: Pre-1.0 layout detection (interactive migration arm)

Detect the pre-1.0 `.flow/` layout (epic-named directories from the 0.x era). When detected, prompt the user to migrate now, defer, or suppress the auto-detect banner permanently. This is the **interactive arm** of the consented-migrate design — the deterministic arm is `flowctl migrate-rename --yes`.

Detection rule:
- `.flow/epics/` exists AND `.flow/.flow_version` (the post-migration sentinel) is absent → pre-1.0 layout, prompt the user.
- `.flow/.flow_version` present → already migrated, skip this step entirely.
- `.flow/epics/` absent → fresh-install repo, skip this step entirely.

```bash
PRE_1_0_LAYOUT=0
if [[ -d .flow/epics && ! -f .flow/.flow_version ]]; then
 PRE_1_0_LAYOUT=1
fi
```

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When `PRE_1_0_LAYOUT=1`, prompt via `plain-text numbered prompt`:

- **header**: `Migrate .flow/?`
- **body**: `Detected pre-1.0 .flow/ layout (.flow/epics/ present, no .flow/.flow_version sentinel). flow-next 1.0 renames .flow/epics/ to .flow/specs/ on disk; alias mode keeps the old layout working but new tooling (flow-swarm, future specs) targets the canonical layout. Recommended: Migrate now — backup is automatic and rollback is one command. Confidence: [high].`
- **options**:
 - `Migrate now` — apply migration via `flowctl migrate-rename --yes`. Safe (backup written to `.flow/.backup-pre-1.0/`, rollback via `flowctl migrate-rollback`).
 - `Defer` — keep alias mode, suppress the auto-detect banner for 7 days. Re-prompted on the next `flowctl` invocation after the window expires.
 - `Suppress permanently` — keep alias mode, never auto-prompt. Print instructions for the `FLOW_NO_AUTO_MIGRATE=1` env var so the user can suppress the banner across the whole machine.
 - `abort` — exit cleanly. No migration, no banner-ack write, no Step 2-onward setup changes. Step 1's `flowctl init` may already have run (idempotent — safe to leave). Re-run `/flow-next:setup` later to complete setup.

### Routing the answer

**Migrate now** (recommended):
```bash
"${PLUGIN_ROOT}/scripts/flowctl" migrate-rename --yes --json
```
Surface the JSON output to the user (renamed entries + sentinel write). On error, print stderr verbatim and continue to Step 2 — the user can re-run setup or use `flowctl migrate-rollback` if needed. Migration failure is non-fatal for the rest of setup.

**Defer** (suppress banner 7 days):
```bash
# migrate-rename --dry-run writes .flow/.banner-acknowledged with an ISO-8601 UTC
# timestamp ending in `Z` as a side effect (T4's banner ack contract). It also
# prints the migration plan to stdout, which is value-add for the defer experience.
"${PLUGIN_ROOT}/scripts/flowctl" migrate-rename --dry-run --json
```
The dry-run output shows the user exactly what would change if they reconsidered, and the side-effect ack-file write is the canonical way to start the 7-day re-nudge window. Do NOT hand-roll the timestamp via `Edit` / `Write` — the format must match `now_iso()` exactly (`2026-05-08T14:23:11.123456Z`).

**Suppress permanently**:
Print the user-facing instructions verbatim:
```
To suppress the migration banner permanently, set FLOW_NO_AUTO_MIGRATE=1 in your shell profile:

 export FLOW_NO_AUTO_MIGRATE=1 # ~/.bashrc / ~/.zshrc / ~/.profile

Alias mode keeps your existing .flow/epics/ layout working indefinitely.
You can still migrate later via: flowctl migrate-rename --yes
```

**abort**:
Exit 0 immediately — no migration, no banner-ack file write, no Step 2-onward setup changes. Step 1's `flowctl init --json` ran before Step 1b, so `.flow/` (meta.json, config.json, directory scaffold) may already have been created or upgraded by `init` — that work is **not** rolled back; `init` is idempotent on re-run. Only the migration + remaining setup phases (Step 2 onward — version pin, file copy, docs update) are skipped. Print:
```
Setup cancelled at migration prompt. .flow/ may have been initialized/upgraded
by Step 1 (idempotent — safe to leave). No migration applied; Step 2 onward
skipped. Re-run /flow-next:setup later to complete setup.
```

**Continue to Step 2 regardless of answer (except `abort`, which exits 0).** Migration choice is otherwise independent of the rest of setup.

## Step 2: Check existing setup

Read `.flow/meta.json` and check for `setup_version` field.

Also read plugin version from the platform-specific manifest:
- Codex: `${PLUGIN_ROOT}/.codex-plugin/plugin.json`
- Claude Code: `${PLUGIN_ROOT}/.claude-plugin/plugin.json`
- Factory Droid: `${PLUGIN_ROOT}/.claude-plugin/plugin.json` (Droid's interop layer reads the Claude Code manifest directly for Claude-first plugins like flow-next)
- Cursor: `${PLUGIN_ROOT}/.cursor-plugin/plugin.json`

Check whichever matches `PLATFORM`. Fall back to `.claude-plugin/plugin.json` if the platform-specific file doesn't exist.

**If `setup_version` exists (already set up):**
- If **same version**: tell user "Already set up with v<VERSION>. Re-run to refresh files + docs? (y/n)"
 - If yes: continue from Step 3 — re-copy bin + templates + docs (idempotent; same-version refresh should NOT skip the file copy, otherwise a project running an unchanged version number but a moved template lands docs that point at a missing path)
 - If no: done
- If **older version**: tell user "Updating from v<OLD> to v<NEW>" and continue

**If no `setup_version`:** continue (first-time setup)

## Step 3: Create .flow/bin/ and .flow/templates/

```bash
mkdir -p .flow/bin .flow/templates
```

## Step 4: Copy files

**IMPORTANT: Do NOT read flowctl.py - it's too large. Just copy it.**

Copy using Bash `cp` with absolute paths:

```bash
cp "${PLUGIN_ROOT}/scripts/flowctl" .flow/bin/flowctl
cp "${PLUGIN_ROOT}/scripts/flowctl.cmd" .flow/bin/flowctl.cmd
cp "${PLUGIN_ROOT}/scripts/flowctl.py" .flow/bin/flowctl.py
cp "${PLUGIN_ROOT}/templates/spec.md" .flow/templates/spec.md
chmod +x .flow/bin/flowctl
```

`flowctl.cmd` is the Windows batch launcher (cmd.exe / PowerShell — Claude Desktop, native Codex, native Cursor); no `chmod +x` needed (PATHEXT resolves it, not the exec bit). The bash `flowctl` and the `.cmd` share one `flowctl.py` target.

`.flow/templates/spec.md` is the canonical 7-section spec scaffold that the AGENTS.md / CLAUDE.md snippet points downstream agents at. Copying it project-local means the path the snippet references resolves without depending on the plugin install location.

### Step 4a: Opt-in `<repo_root>/SPEC.md` customization (interactive)

The spec-template discovery cascade prefers a customized scaffold at the repo root over `.flow/templates/spec.md` and the bundled plugin copy. This step lets the user opt into seeding `<repo_root>/SPEC.md` from the canonical template so they can edit it without diving into `.flow/templates/`.

**Detect what's already at the repo root** (case-insensitive FS handling — macOS APFS, Windows NTFS):

```bash
HITS=$(ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l | tr -d ' ')
```

Then branch:

**1. `HITS=0` (neither file exists)** — ask the user via `plain-text numbered prompt`:

- **header**: `Copy canonical spec template to <repo-root>/SPEC.md?`
- **body**: `The spec template discovery cascade prefers <repo-root>/SPEC.md over .flow/templates/spec.md, so customizations there apply to every new spec without affecting other projects. The canonical template at ${PLUGIN_ROOT}/templates/spec.md ships with the 7 canonical sections, scope-owner annotations, and the ## Decision Context H3 conditional. Skipping is safe — the cascade falls through to .flow/templates/spec.md (just copied above), so all downstream skills still resolve a template.`
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
- **Customized** (any deviation after normalization): do NOT silently replace. Ask the user via `plain-text numbered prompt`:
 - **header**: `Overwrite customized <repo-root>/$EXISTING?`
 - **body**: `<repo-root>/$EXISTING exists and differs from the canonical template shipped with this plugin version (CRLF and trailing newlines ignored). Overwriting replaces your edits. Keeping skips this file (you can manually merge later via diff against \`${PLUGIN_ROOT}/templates/spec.md\`).`
 - **options**:
 - `Keep mine (Recommended)` — leave `<repo-root>/$EXISTING` unchanged. Print the path to the canonical template so the user can diff manually.
 - `Overwrite with canonical` — replace `<repo-root>/$EXISTING` (same filename — do NOT rename lowercase `spec.md` to uppercase `SPEC.md` here; preserve the user's casing) with the bundled template content. Repo customization is lost.
 - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, Step 3 mkdir, Step 4 bin/template copies above) may already have run; they are idempotent and safe to leave. No `<repo-root>/$EXISTING` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

**Note:** Setup writes uppercase `SPEC.md` only on the **fresh-seed** path (`HITS=0` `Copy template`). Never seed lowercase `spec.md` from scratch. The lowercase entry in the cascade is read-only at discovery time — present only for users who deliberately created lowercase. On the **re-setup overwrite** path above, preserve the user's existing filename casing via `$EXISTING` (so a lowercase `spec.md` stays lowercase after `Overwrite with canonical`).

Then handle `.flow/usage.md` — preserve any repo-customized variant:

1. Read [templates/usage.md](templates/usage.md) (this is the canonical content).
2. If `.flow/usage.md` does not exist → write the canonical content.
3. If `.flow/usage.md` exists → compare byte-for-byte with the canonical content:
 - **Identical**: no-op (skip the write entirely — re-running setup must not bump mtime on unchanged files).
 - **Customized** (any deviation): do NOT overwrite. Ask the user via `plain-text numbered prompt`:
 - **header**: `Overwrite customized .flow/usage.md?`
 - **body**: `.flow/usage.md exists and differs from the canonical template shipped with this plugin version. Overwriting replaces your edits. Keeping skips this file (you can manually merge later via diff against \`${PLUGIN_ROOT}/skills/flow-next-setup/templates/usage.md\`).`
 - **options**:
 - `Keep mine (Recommended)` — leave `.flow/usage.md` unchanged. Print the path to the canonical template so the user can diff manually.
 - `Overwrite with canonical` — replace `.flow/usage.md` with the template content. Repo customization is lost.
 - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, Step 3 mkdir, Step 4 bin/template copies above) may already have run; they are idempotent and safe to leave. No `.flow/usage.md` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

## Step 4b: Codex-specific project setup (PLATFORM=codex only)

**Skip this step entirely if PLATFORM is not `codex`.** (Claude Code / Droid / Cursor all skip it — Cursor drives the workflow with `/flow-next:*` slash commands and resolves `flowctl` via `.flow/bin/flowctl`, not project-scoped `.codex/` agents + hooks.)

On Codex, agents and hooks live in project-scoped `.codex/` directories (not in the plugin cache). Copy them:

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

### Copy hooks.json

```bash
HOOKS_SRC="${PLUGIN_ROOT}/codex/hooks.json"
[ -f "$HOOKS_SRC" ] || HOOKS_SRC="$HOME/.codex/hooks.json"

if [ -f "$HOOKS_SRC" ]; then
 mkdir -p .codex
 cp "$HOOKS_SRC" .codex/hooks.json
 echo "Copied hooks.json to .codex/hooks.json"
else
 echo "Warning: No hooks.json found at ${PLUGIN_ROOT}/codex/hooks.json or ~/.codex/hooks.json"
fi
```

### Enable Codex hooks feature (if config.toml exists)

```bash
if [ -f .codex/config.toml ]; then
 # `[features].hooks` is the current key; `codex_hooks` is the deprecated
 # pre-2026 spelling (Codex warns on every run). Goal: EXACTLY ONE
 # `hooks = true` under [features], NO `codex_hooks`. This must stay dedup-safe:
 # a config carrying BOTH keys (older setup/install left this) would, under a
 # naive `sed codex_hooks->hooks`, gain a DUPLICATE `hooks` key — invalid TOML
 # that breaks Codex hook loading. Use python3 to normalize idempotently.
 python3 - .codex/config.toml <<'PY'
import re, sys
path = sys.argv[1]
HOOKS = "hooks = true # flow-next"
sec = re.compile(r"^\s*\[([^\]]+)\]\s*$")
old = re.compile(r"^\s*codex_hooks\s*=")
new = re.compile(r"^\s*hooks\s*=")
try:
 text = open(path, encoding="utf-8").read()
except FileNotFoundError:
 text = ""
out, in_feat, feat_seen, kept = [], False, False, False
for line in text.splitlines():
 m = sec.match(line)
 if m:
 if in_feat and not kept:
 out.append(HOOKS); kept = True
 in_feat = m.group(1).strip() == "features"
 if in_feat:
 feat_seen = True; kept = False
 out.append(line); continue
 if in_feat:
 if old.match(line):
 continue # drop deprecated key
 if new.match(line):
 if kept:
 continue # drop duplicate hooks
 kept = True; out.append(line); continue
 out.append(line)
if in_feat and not kept:
 out.append(HOOKS)
if not feat_seen:
 if out and out[-1].strip():
 out.append("")
 out += ["[features]", HOOKS]
result = "\n".join(out).rstrip("\n") + "\n"
if result != text:
 open(path, "w", encoding="utf-8").write(result)
 print("Normalized .codex/config.toml -> single [features] hooks = true")
PY
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
HAVE_RP=$(which rp-cli >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_CODEX=$(which codex >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_COPILOT=$(which copilot >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_CURSOR=$(which cursor-agent >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_GROK=$(which grok >/dev/null 2>&1 && echo 1 || echo 0)

# fn-97: at least one bridge CLI on PATH gates the Model Routing question in 6d
# (with zero bridges every wiring route in the scaffold would be an inert
# install-note comment, so the question is not offered - install a bridge CLI
# and re-run /flow-next:setup to get it).
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
# is offered ONLY in an interactive setup AND only when a bridge CLI was
# detected (BRIDGE_DETECTED=1 above, fn-97). Under ANY non-interactive / autonomous
# marker, the question is skipped SILENTLY — setup must never block a headless
# driver. Scan the WHOLE autonomy-marker family (Ralph / receipt-path / autonomous
# / mode token), not a fixed pair — the same family every lifecycle skill honors.
ROUTING_ASK=1
if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
 || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* ]]; then
 ROUTING_ASK=0
fi
```

Store detection results for use in questions. When showing options, indicate current value if set (e.g., "(current)" after the matching option label).

### 6b: Check docs status

Choose the correct template based on platform:
- **Codex** (`PLATFORM=codex`): read [templates/agents-md-snippet.md](templates/agents-md-snippet.md) — uses `$flow-next-plan` syntax
- **Claude Code / Droid / Cursor**: read [templates/claude-md-snippet.md](templates/claude-md-snippet.md) — uses `/flow-next:plan` syntax (Cursor runs the same slash commands; on Cursor the snippet lands in AGENTS.md, which Cursor reads)

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

Build the prompt content (question text + numbered option list) dynamically. **Only include questions for config values that are NOT already set** — existing config is preserved, never overwritten. To change an already-set value, the user runs `flowctl config set <key> <value>` directly (the commands are surfaced in 6c's current-config notice).

Skipped questions = config values already persisted from a prior run. Asking again would either no-op (same answer) or silently flip a deliberate user choice — both are wrong. The grouped single-prompt design (a single `plain-text numbered prompt` call below, with one questions array containing only the unset entries) means a re-run with all config set produces zero config questions and asks only the always-include Docs + Star questions (plus the interactive-only Model Routing scaffold question, when `ROUTING_ASK=1`).

Available questions (include only if corresponding config is unset):

**Memory question** (include if CURRENT_MEMORY is empty):
```json
{
 "header": "Memory",
 "question": "Enable memory system? (Auto-captures learnings from NEEDS_WORK reviews)",
 "options": [
 {"label": "Yes (Recommended)", "description": "Auto-capture pitfalls and conventions from review feedback"},
 {"label": "No", "description": "Disable with: flowctl config set memory.enabled false"}
 ],
 "multiSelect": false
}
```

**Plan-Sync question** (include if CURRENT_PLANSYNC is empty):
```json
{
 "header": "Plan-Sync",
 "question": "Enable plan-sync? (Updates downstream task specs after implementation drift)",
 "options": [
 {"label": "Yes (Recommended)", "description": "Sync task specs when implementation differs from original plan"},
 {"label": "No", "description": "Disable with: flowctl config set planSync.enabled false"}
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
 "question": "Enable HTML artifact mode? (Renders specs/PRs as self-contained HTML review pages under .flow/artifacts/ — markdown stays the source of truth)",
 "options": [
 {"label": "Yes (Recommended)", "description": "Participating skills (capture, plan, make-pr) also emit regenerable HTML render lenses for human review"},
 {"label": "No", "description": "Markdown-only. Zero extra steps, zero token overhead. Enable later: flowctl config set artifacts.html.enabled true"}
 ],
 "multiSelect": false
}
```

**Review question** (include if CURRENT_BACKEND is empty):
```json
{
 "header": "Review",
 "question": "Which review backend for Carmack-level reviews?",
 "options": [
 {"label": "Codex CLI", "description": "Cross-platform, uses GPT 5.2 High for reviews. Simple setup, works everywhere. <detected if HAVE_CODEX=1, (not detected) if HAVE_CODEX=0>"},
 {"label": "Copilot CLI", "description": "Cross-platform, routes to Claude (Sonnet/Opus/Haiku 4.5) or GPT-5.2 via GitHub Copilot. Requires gh copilot auth. <detected if HAVE_COPILOT=1, (not detected) if HAVE_COPILOT=0>"},
 {"label": "Cursor CLI", "description": "Cross-platform, runs cursor-agent (default gpt-5.5-high 1M-ctx; also gpt-5.3-codex, composer-2.5, opus-4.8-thinking). Billed to your Cursor subscription. <detected if HAVE_CURSOR=1, (not detected) if HAVE_CURSOR=0>"},
 {"label": "RepoPrompt", "description": "macOS only. Auto-discovers git diffs + context, reviews scoped to actual changes, ~65% fewer tokens than traditional approaches. <detected if HAVE_RP=1, (not detected) if HAVE_RP=0>"},
 {"label": "None", "description": "Skip reviews, can configure later with --review flag"}
 ],
 "multiSelect": false
}
```

When `HAVE_CODEX=1` AND `PLATFORM` is NOT `codex`, append ` (Recommended - cross-family default)` to the `Codex CLI` label: the recommended multi-model pipeline reviews cross-family FROM THE WRITER, and on a Claude Code / Droid / Cursor host codex review is a different family than the session writer - so this question carries the ceremony's `review.backend codex` offer while the key is unset (fn-97). On a Codex host (`PLATFORM=codex`) do NOT add the label: the writer is GPT-family (the session model, or the optional terra worker pin), so codex review would be SAME-family - prefer a detected non-GPT backend there (copilot / cursor with a Claude-family model) and leave the options unannotated when none is detected. When `review.backend` is ALREADY set to something else, this question is skipped (existing config is never silently overwritten) - the offer instead rides the Model Routing scaffold as an explicit opt-in switch, Step 7's step 8 below.

Stored value is a bare backend name by default. Power users can also write a full spec like `codex:gpt-5.4:high`, `copilot:claude-opus-4.5:xhigh`, or `cursor:gpt-5.5-high` (cursor takes a model only — no `:effort`) via `flowctl config set review.backend <spec>` after setup — the review commands accept both forms.

**Model Routing question** (include ONLY when `ROUTING_ASK=1` AND `BRIDGE_DETECTED=1` — interactive setup with at least one bridge CLI (`codex` / `cursor-agent` / `grok`) detected per 6a; skipped silently under any non-interactive/autonomous marker, and skipped without a detected bridge CLI — the scaffold's wiring routes would all be inert install notes). Offers the recommended multi-model pipeline scaffold (composed + written in Step 7). The frozen option set is `Scaffold` / `Scaffold + enable codex delegation` / `Skip`; **include the `Scaffold + enable codex delegation` option ONLY when `HAVE_CODEX=1`** (drop that one object entirely when `HAVE_CODEX=0` — never show a delegation route to a missing binary):
```json
{
 "header": "Model Routing",
 "question": "Scaffold a recommended multi-model pipeline into your project instruction file? (a cost/intelligence/taste scores table + how-to-apply rules + the flow-next wiring for the bridge CLIs detected on this machine; shown in FULL before writing — yours to edit after)",
 "options": [
 {"label": "Scaffold", "description": "Write the model-routing example into the same CLAUDE.md/AGENTS.md the Docs step targets. Shown in full before writing; these are starting opinions you edit down, not up."},
 {"label": "Scaffold + enable codex delegation", "description": "Also set work.delegate=codex so /flow-next:work can offload bulk implementation to the codex CLI. First-use consent is still required — this never pre-approves it. INCLUDE THIS OPTION ONLY WHEN HAVE_CODEX=1."},
 {"label": "Skip", "description": "Don't scaffold a routing section (default). Re-run /flow-next:setup later to add it."}
 ],
 "multiSelect": false
}
```

**Docs question** (always include — adjust default based on platform):

For **Codex** (`PLATFORM=codex`):
```json
{
 "header": "Docs",
 "question": "Update project documentation with Flow-Next instructions?",
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
 "question": "Update project documentation with Flow-Next instructions?",
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
 "question": "Update project documentation with Flow-Next instructions?",
 "options": [
 {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (Cursor reads this)"},
 {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
 {"label": "Both", "description": "Add flow-next section to both files"},
 {"label": "Skip", "description": "Don't update documentation"}
 ],
 "multiSelect": false
}
```

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

**Note:** If none of rp-cli, codex, copilot, or cursor-agent is detected, add note to the Review question: "No review backend detected. Install rp-cli, codex, copilot, or cursor-agent for review support."

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
 3. Print the lavish-axi offer verbatim. **NEVER auto-install** — detect-and-instruct only, same discipline as /flow-next:map (global npm installs are user-consent territory):

 ```
 HTML artifact mode enabled.

 Optional companion — lavish-axi (annotate spec artifacts in the browser; feedback
 flows back as markdown-source edits, then the lens regenerates):

 Install: npm i -g lavish-axi
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
# Determine backend from answer
case "$review_answer" in
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
- AGENTS.md on **Claude Code / Droid / Cursor**: use [templates/claude-md-snippet.md](templates/claude-md-snippet.md) (uses `/flow-next:plan` syntax — Cursor runs the slash commands, so its AGENTS.md must carry the `/flow-next:` snippet, NOT the Codex `$flow-next-` one)
- CLAUDE.md (any platform): use [templates/claude-md-snippet.md](templates/claude-md-snippet.md)

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
 - `ask` (reason `customized` or `hash-absent`) - the block differs from canonical and is not provably pristine. The helper wrote nothing; ask via `plain-text numbered prompt`:
 - **header**: `Overwrite customized <FILE>?` (substitute CLAUDE.md or AGENTS.md)
 - **body**: `<FILE> contains a flow-next marker block that differs from the canonical template shipped with this plugin version and is not recorded as pristine. Overwriting replaces the marker block only; content outside the markers is untouched either way.`
 - **options**:
 - `Keep mine (Recommended)` - run `"${PLUGIN_ROOT}/scripts/flowctl" setup-block resolve --file <FILE> --template <same template> --choice keep --json`. This records the `"customized"` sentinel so future re-runs never re-ask and never overwrite. Print the canonical template path so the user can diff manually (`${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md`).
 - `Overwrite with canonical` - run the same `setup-block resolve` command with `--choice overwrite`. This replaces the marker block with the canonical snippet and records the new pristine hash; customizations inside the markers are lost, content outside the markers is preserved.
 - `abort` - exit cleanly, no further writes. Earlier steps (init, file copies, config writes, prior docs-file decisions for any already-processed file) may already have run; they are idempotent and safe to leave. Everything from here onward is skipped (remaining docs files, the Model Routing scaffold, and the Star step). Re-run `/flow-next:setup` later to complete setup.

The marker-block boundaries are load-bearing: pre-existing prose outside `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` is **never** modified by this step, and only the flowctl helper performs writes. Only the bytes between (and including) those markers are candidates for replacement.

**Model Routing scaffold** (only if the Model Routing question was asked — i.e. `ROUTING_ASK=1` AND `BRIDGE_DETECTED=1`; when either is 0 the question was never shown, so this step is a silent no-op — record `not offered` for the summary and skip to Star).

Run this **after** the Docs block above and **before** Star. It may touch the **same** file the Docs block just wrote this run — always **re-read the target from disk here**; never reuse an in-memory copy and never interleave the two writes. Set `ROUTING_OUTCOME=""` for the Step 8 summary and update it at each terminal branch below. Every "done with the block pipeline" terminal below still falls through to **step 7 (delegation)** — the delegation opt-in is independent of whether the block was written — then on to Star.

- If the answer was **`Skip`**: no-op. `ROUTING_OUTCOME="skipped"`. Done with the block pipeline — skip steps 1–7 (there is no delegation to set) and go to Star.
- Otherwise (**`Scaffold`** or **`Scaffold + enable codex delegation`**), run the block pipeline (step 1 once, then steps 2–6 **per resolved target file** — see the per-file loop below), then always run step 7 once:

**1. Resolve target file(s)** via this deterministic ladder (independent of whether the Docs question fired — evaluate in order, first match wins):
 a. **Docs answered this run** → mirror that choice: `CLAUDE.md only` → CLAUDE.md; `AGENTS.md only` → AGENTS.md; `Both` → the same block to **both** files; `Skip` → fall through to (b).
 b. **Docs skipped or already-current** → the file(s) that already carry the `<!-- BEGIN FLOW-NEXT -->` docs marker (marker in both → both).
 c. **Neither** → the platform-default mapping (the Step 6b buckets): Codex → AGENTS.md; Claude Code / Droid → CLAUDE.md; Cursor → AGENTS.md.

 **Shim guard** (apply to each resolved target before writing): read the file and take its non-empty content lines. If there is exactly **one** non-empty content line and it matches either `@<path>.md` **or** `See[:] <path>.md` (case-insensitive, `<path>` repo-relative), the target is a **shim** — do **not** write into it. Instead follow the pointer: if `<path>.md` exists in-repo, retarget to it (and re-apply the shim guard to that file); if it does not exist, print `Model-routing scaffold: <file> is a shim pointing at a missing <path>.md — skipping` and drop this target. Any other content = a normal file, proceed. Never turn a shim into a mixed file. If every resolved target drops out (all shims to missing files), `ROUTING_OUTCOME="skipped (shim)"`; done with the block pipeline (proceed to step 7).

 **Per-file loop — when step 1 resolved more than one target, run steps 2–6 once for each resolved target file** (mirroring the Docs step's "for each chosen file" loop). Compose/substitution, byte-compare, read-back, and write all happen **per file** — a CLAUDE.md and an AGENTS.md target can differ in both invocation syntax and drift state, so one file may no-op while the other needs a write. `Both` still means the same block in both files (R12): identical content modulo step 3's per-file invocation-syntax substitution. Inside the loop, every "done with the block pipeline" terminal ends the **current file only** — continue with the next target; step 7 runs **once**, after the last file.

**2. Compose the block** from [templates/model-routing-snippet.md](templates/model-routing-snippet.md) via a **deterministic line transform** — never hand-write or paraphrase it. Start from the template verbatim, then for **each** line beginning with a probe sentinel:
 - `<!-- probe:codex --> TEXT` when `HAVE_CODEX=1` → **strip** the `<!-- probe:codex --> ` prefix, leaving the bare active line `TEXT`.
 - `<!-- probe:codex --> TEXT` when `HAVE_CODEX=0` → **comment the whole route out** as a single inert HTML comment carrying an install note: `<!-- not detected on this machine — install codex, then uncomment: TEXT -->`.
 - `<!-- probe:cursor --> TEXT` → the same transform keyed on `HAVE_CURSOR` (install note names `cursor-agent`).
 - `<!-- probe:grok --> TEXT` → the same transform keyed on `HAVE_GROK` (install note names `grok`).

 Result invariant (R10): after the transform the composed block contains **no** `<!-- probe:` sentinel and **no active (non-comment) line that invokes a CLI whose probe failed** — every failed-probe route is fully enclosed in an HTML comment with an install note. All three probes (codex, cursor, grok) failing → every probe-gated wiring route is a commented-out note (the scores table + the native routes + always-on escalation/graceful-degrade rules still stand); you MAY note in the read-back that with none of the CLIs installed, `Skip` is reasonable — but still honor the user's choice.

**3. Substitute the invocation syntax per target file** — keyed on the target file's snippet family from the Docs mapping above, NOT on platform alone: rewrite every `/flow-next:<cmd>` → `$flow-next-<cmd>` (this covers the provenance line's `/flow-next:setup` **and** the `delegate:codex` work route's `/flow-next:work`) **only** when the target is AGENTS.md on **Codex** (the `agents-md-snippet.md` family); keep `/flow-next:` verbatim for CLAUDE.md on **every** platform and for AGENTS.md on **Claude Code / Droid / Cursor** (the `claude-md-snippet.md` family — Cursor runs the slash commands). When step 1 resolved **both** files on Codex, compose one copy per file: AGENTS.md gets `$flow-next-`, CLAUDE.md keeps `/flow-next:`.

**4. Inspect marker + byte-compare FIRST — before any read-back.** Read the resolved target from disk:
 - **Marker present** (`<!-- flow-next:model-routing:start -->` … `<!-- flow-next:model-routing:end -->`): extract that block inclusive and **byte-compare** it against the block composed in 2–3 **for this target file** (today's probe state + this file's invocation syntax — this is the *current composed canonical*):
 - **Identical** → silent no-op: show **nothing**, do **not** write, do **not** bump mtime (R11). `ROUTING_OUTCOME="unchanged (already current)"`. Done with the block pipeline (proceed to step 7).
 - **Different** (user edits **or** probe-state drift, e.g. cursor-agent installed since the last scaffold — drift counts as canonical drift, never a silent rewrite) → ask the user via `plain-text numbered prompt`, options `Keep mine (Recommended)` / `Overwrite with canonical` / `Skip`: `Keep mine` → leave unchanged, print the template path `${PLUGIN_ROOT}/skills/flow-next-setup/templates/model-routing-snippet.md` for a manual diff, `ROUTING_OUTCOME="kept (customized)"`, done; `Skip` → leave unchanged, `ROUTING_OUTCOME="skipped"`, done; `Overwrite with canonical` → continue to the read-back (step 5), replacing the existing marked block in place.
 - **No marker present** → scan for an existing model-routing-shaped heading OUTSIDE our markers (e.g. `## Picking models`, or a heading naming model routing / model selection). If one is found, this is a user-authored routing section: do **not** append a duplicate — ask the user via `plain-text numbered prompt` whether to `Add the flow-next block below yours` / `Skip`; `Skip` → `ROUTING_OUTCOME="skipped"`, done; `Add` → continue to the read-back (step 5), appending after that section. If no such heading is found, continue to the read-back (step 5), appending at end of file.

**5. Read-back (would-write path only).** Show the user the **full** composed block (probes + platform applied), then ask via `plain-text numbered prompt`, options `write` / `skip`: `skip` → no write, `ROUTING_OUTCOME="skipped"`, done; `write` → write the block. The block already includes its `<!-- flow-next:model-routing:start -->` / `<!-- flow-next:model-routing:end -->` fence and provenance line — append it (no-marker / augment cases) or replace the existing marked block in place (Overwrite case). Never a silent write.

**6. Post-write confirmation** — print one line inviting free editing: `Model-routing section written to <file> — this section is yours now; edit the scores/rules freely, or re-run /flow-next:setup to regenerate.` `ROUTING_OUTCOME="written to <file>"` (per file — when looping over multiple targets, join the per-file outcomes for the summary, e.g. `written to CLAUDE.md; AGENTS.md unchanged (already current)`).

**7. Delegation opt-in** (only if the answer was **`Scaffold + enable codex delegation`** — independent of the write branch above; run it even if the block was a no-op/kept, since the user explicitly opted into delegation):
 ```bash
 "${PLUGIN_ROOT}/scripts/flowctl" config set work.delegate codex --json
 ```
 **NEVER** set or touch `work.delegateConsent` — the first-use consent gate stays live (R9). Then **read the persisted value back to confirm** (ceremony validation reads PERSISTED config, never re-races env):
 ```bash
 DELEGATE_SET=$("${PLUGIN_ROOT}/scripts/flowctl" config get work.delegate --raw --json 2>/dev/null | jq -r 'if .value == null then "" else (.value | tostring) end')
 ```
 If `DELEGATE_SET` is `codex`, note `ROUTING_DELEGATE="enabled"`; otherwise print `Warning: work.delegate did not persist as codex — set it manually with flowctl config set work.delegate codex` and note `ROUTING_DELEGATE="failed"`.

**8. Review-backend switch offer** (fn-97 — run once, after step 7, only when ALL hold: the answer was `Scaffold` or `Scaffold + enable codex delegation`, `HAVE_CODEX=1`, `PLATFORM` is NOT `codex` — on a Codex host the writer is GPT-family, so switching review to codex would trade a genuinely cross-family backend for a same-family one; skip the offer there — and `CURRENT_BACKEND` is non-empty AND is not already codex — i.e. neither bare `codex` nor a `codex:...` spec form). This is the scaffold's `review.backend codex` offer for projects whose backend was configured before the scaffold existed; when `CURRENT_BACKEND` is empty the Review question in 6d already carried the offer, so this step is a silent no-op. Ask via `plain-text numbered prompt`:

```json
{
 "header": "Review Backend",
 "question": "The scaffolded pipeline reviews cross-family via codex. Switch review.backend from <CURRENT_BACKEND> to codex?",
 "options": [
 {"label": "Keep current (Recommended)", "description": "Leave review.backend as <CURRENT_BACKEND>. Switch later with: flowctl config set review.backend codex"},
 {"label": "Switch to codex", "description": "Set review.backend codex now (the scaffold's recommended cross-family default)"}
 ],
 "multiSelect": false
}
```

`Keep current` → no write, done. `Switch to codex` → run `"${PLUGIN_ROOT}/scripts/flowctl" config set review.backend codex --json`, then read the persisted value back (same read-back pattern as step 7); if it did not persist as `codex`, print `Warning: review.backend did not persist as codex — set it manually with flowctl config set review.backend codex`. This step never runs non-interactively (the whole scaffold pipeline is gated on `ROUTING_ASK=1`) and never fires when the user skipped the scaffold — declining the scaffold declines its pipeline too.

**Star:**
- If "Yes, star it":
 1. Check if `gh` CLI is available: `which gh`
 2. If available, run: `gh api -X PUT /user/starred/gmickel/flow-next`
 3. If `gh` not available or command fails, show: `Star manually: https://github.com/gmickel/flow-next`

## Step 8: Print Summary

```
Flow-Next setup complete!

Platform: <claude-code|codex|droid>

Installed:
- .flow/bin/flowctl (v<VERSION>)
- .flow/bin/flowctl.cmd (Windows PowerShell/cmd launcher)
- .flow/bin/flowctl.py
- .flow/templates/spec.md
- .flow/usage.md
- <repo-root>/SPEC.md (only if Step 4a "Copy template" was chosen — otherwise omit this line)
```

**If PLATFORM=codex, also show:**
```
Codex project setup:
- .codex/agents/*.toml (<N> agent configs)
- .codex/hooks.json (Ralph workflow guards)
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
- Review backend: <codex|rp|none>

Documentation updated:
- <files updated or "none">

Model routing scaffold: <ROUTING_OUTCOME — e.g. "written to CLAUDE.md" | "kept (customized)" | "unchanged (already current)" | "skipped" | "skipped (shim)" | "not offered">
<if Scaffold + enable codex delegation was chosen, also:>
- Codex delegation: <ROUTING_DELEGATE — "enabled (work.delegate=codex; first-use consent still required)" | "failed">

Notes:
- Re-run /flow-next:setup after plugin updates to refresh scripts
- Interested in autonomous mode? Run /flow-next:ralph-init
- Use Linear / GitHub Issues / GitLab / Jira for project management? Run /flow-next:tracker-sync to configure the (opt-in) two-way tracker bridge — it runs a discovery ceremony (detects Linear MCP / LINEAR_API_KEY / gh auth / glab auth or GITLAB_TOKEN / JIRA_BASE_URL + credential, asks, writes config), then syncs specs ⇄ issues; on Linear it additionally makes your PRs reviewable as Linear Diffs. Skips cleanly if you don't use a tracker; adds nothing to the base install until enabled.
- Uninstall (run manually): rm -rf .flow/bin .flow/templates .flow/usage.md and remove the <!-- BEGIN/END FLOW-NEXT --> and <!-- flow-next:model-routing:start/end --> blocks from docs — or run /flow-next:uninstall for full cleanup
- This setup is optional - plugin works without it
```

**Tracker-sync proposal (always show, after the Notes block).** Surface the tracker bridge as an explicit optional next step — the discovery ceremony is the bridge's own setup, separate from this skill (which never touches tracker config, keeping the zero-dep base clean):

```
Optional next step — connect a tracker:
 If your team lives in Linear, GitHub Issues, GitLab, or Jira, run /flow-next:tracker-sync to set up the
 two-way bridge (spec ⇄ issue, status, comments) and make PRs reviewable as Linear Diffs.
 Fully opt-in — nothing syncs until you confirm it in the discovery ceremony.
```
