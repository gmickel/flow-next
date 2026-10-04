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
elif [ -n "${CURSOR_AGENT:-}" ] \
  && [ -f "${PLUGIN_ROOT}/.cursor-plugin/plugin.json" ] \
  && case "${PLUGIN_ROOT_ABS}" in \
       "${CURSOR_HOME_ABS}"|"${CURSOR_HOME_ABS}"/*) true ;; \
       *) false ;; \
     esac; then
  PLATFORM="cursor"
elif [ -n "${GROK_AGENT:-}" ]; then
  PLATFORM="grok"
elif [ -f "${PLUGIN_ROOT}/.flow-next-opencode-manifest" ]; then
  PLATFORM="opencode"
elif [ -n "${CLAUDECODE:-}" ] \
  && [ -f "${PLUGIN_ROOT}/.claude-plugin/plugin.json" ]; then
  PLATFORM="claude-code"
else
  PLATFORM="codex"
fi
```

**Never reorder the rungs.** Each host's own signal (Droid, Cursor, Grok, OpenCode) outranks the
inherited `CLAUDECODE` marker, and `codex` is the fallback. Nested Droid → Grok is unsupported: a
grok child that inherits `DROID_PLUGIN_ROOT` classifies as `droid`, so stop NEEDS_HUMAN unless a
smoke confirms `DROID_PLUGIN_ROOT` does not propagate. The rationale for each rung and the
detection fixture matrix are in
[docs/platforms.md § Setup host detection](../../docs/platforms.md#setup-host-detection-rung-order-and-rationale).

Store `PLATFORM` for use in later steps. This determines:
- Which manifest to read for version (`plugin.json`)
- Which docs file to prefer (CLAUDE.md vs AGENTS.md)
- Whether to copy Codex agents to project (hooks are **not** copied)
- Which command-name syntax the docs snippet uses (Claude-format skill ids for Claude Code / Droid / **Cursor** / **Grok**; `/flow-next-plan` flat form for **OpenCode**; `$flow-next-plan` for Codex)

### Done when

- `PLUGIN_ROOT` resolves to a directory containing `scripts/` and a plugin manifest, and `PLATFORM` holds exactly one of `claude-code` / `codex` / `droid` / `cursor` / `grok` / `opencode`.
- **`PLATFORM` came from the host's own signals in the documented precedence, and every downstream choice matches it.** A Cursor or Grok repo that received the Codex `$flow-next-` snippet, a Codex install misclassified as Cursor through an inherited `CURSOR_AGENT`, a Claude Code run classified `codex` because the cascade looked for `CLAUDE_PLUGIN_ROOT` instead of `CLAUDECODE`, or an OpenCode install classified `codex` because the cascade missed `.flow-next-opencode-manifest`, has broken this.

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

Read all setup probes once:

```bash
"${PLUGIN_ROOT}/scripts/flowctl" setup-status --plugin-root "$PLUGIN_ROOT" --platform "$PLATFORM" --json
```

Keep this response through the ceremony. `first_run` supplies `SETUP_FIRST_RUN`,
`plugin_version` supplies `PLUGIN_VERSION`, and `optional_answers` holds prior
answers for `spec`, `leftovers`, `docs`, `criteria`, and `star`.
A missing or unreadable metadata file means first run. A same-version rerun
continues without a confirmation question; existing choices remain authoritative.

**Optional answers and unattended execution.** Before every optional question,
consult its saved answer. A saved decline skips that question and its action;
a saved completed choice skips the question too. Treat a saved Docs `Skip`
as the current Docs decline for the routing-block guard as well; no instruction
file is created merely because that question was suppressed. Revisit only when the user
explicitly asks to change that choice. Persist each attended answer immediately
under `.flow/meta.json` → `setup.optional_answers.<key>` as its answer label,
preserving all other metadata (including block hashes). This also applies to
Step 4a's Skip/Keep and Step 2b's Keep. Never record a missing answer as consent.
An unattended run (`FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`, or `mode:autonomous`)
asks nothing: defer unanswered optional
questions, record no answer, and continue without their optional mutations.
Existing explicit authorization still governs its scope. Customized-file
replacement without authorization returns `NEEDS_HUMAN`; no overwrite occurs.

## Step 2b: Leftover copy artifacts (cleanup offer)

**Setup never copies flowctl, the spec template, or the usage guide into a repo.** Every host resolves `flowctl` from the plugin install (Claude Code / Droid via their plugin-root env vars, Cursor / Grok / OpenCode by deriving the plugin root from the skill file's own absolute path, Codex from `$CODEX_HOME`). Repos set up before that carry leftover snapshots; this step offers to delete them.

Use `legacy_artifacts` from `setup-status` as the residue list; it comes
from flowctl's `LEGACY_COPY_ARTIFACTS` source of truth.

**None present → say nothing and continue to Step 4a.** Silence is the normal case.

**Customized-template guard (before the ask).** `.flow/templates/spec.md` is the one leftover a user may have EDITED — it used to sit in the spec-scaffold cascade, so a customized copy there is user-authored content, not a snapshot. Compare it against the bundled `${PLUGIN_ROOT}/templates/spec.md`: identical → a plain snapshot, list it with the rest; different → EXCLUDE it from the delete list and say so: `.flow/templates/spec.md differs from the bundled template - it looks customized. The cascade no longer reads it; copy it to a repo-root SPEC.md to keep using it (that is the customization point now), then delete it yourself.` Never delete a differing template under this offer.

**Any present →** list the exact paths, tell the user they are dead weight on every host (nothing reads them; deleting them changes nothing observable), and ask via `AskUserQuestion`:

- **header**: `Leftovers`
- **question**: `Delete these leftover flowctl copies? They are snapshots from an older install layout. Every flow-next skill now resolves flowctl from the plugin install itself, so nothing reads them — deleting them changes nothing observable in any workflow, and keeping them means a stale flowctl can shadow the current one.`
- **options**:
  - `Delete them (Recommended)` — remove the listed paths: `git rm -rq` for tracked ones (this stages the deletions in the user's index — say so; setup never commits), plain `rm -rf` for untracked. FIRST surface any listed tracked file with uncommitted modifications and exclude it from removal (never force-remove modified files; the user resolves those by hand).
  - `Keep them` — nothing is removed; setup continues normally. They stay inert.

**Never delete silently.** A leftover that disappeared without the user answering `Delete them` has broken this. After a delete, re-enumerate and print anything still present (declines, modified-file exclusions) — then continue either way; leftovers never block setup.

### Done when

- The residue probe ran on this pass, and its paths match flowctl's `LEGACY_COPY_ARTIFACTS` list.
- Nothing under `.flow/bin/`, `.flow/templates/`, or `.flow/usage.md` was written by this run, and nothing was deleted without an explicit `Delete them` answer.

## Step 4: Seed user-owned files

Nothing is copied into `.flow/` — flowctl, the spec template, and the usage guide all resolve from the plugin install. This step seeds only **user-owned** files: an optional repo-root `SPEC.md`, and (on Codex) the project's `.codex/agents/*.toml`.

### Step 4a: Opt-in `<repo_root>/SPEC.md` customization (interactive)

The spec-template discovery cascade prefers a customized scaffold at the repo root over the bundled plugin copy. This step lets the user opt into seeding `<repo_root>/SPEC.md` from the canonical template so they can edit it in place.

**Detect what's already at the repo root** (case-insensitive FS handling — macOS APFS, Windows NTFS):

```bash
# Count DISTINCT FILES, not argument names. `ls -1 SPEC.md spec.md` echoes each
# existing argument back, so on a case-insensitive FS one file prints as two
# names and `sort -u` de-duplicates nothing (HITS=2 on APFS for a repo
# holding only SPEC.md fires a bogus both-files warning). Inodes answer the
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

**1. `HITS=0` (neither file exists)** — ask the user via `AskUserQuestion`:

- **header**: `SPEC.md`
- **question**: `Copy the canonical spec template to <repo-root>/SPEC.md? Every new flow-next spec starts from a template. Lookup order: <repo-root>/SPEC.md first, then <repo-root>/spec.md, then the plugin's bundled copy — so a SPEC.md at the repo root is where you customize section wording for THIS project. Skipping is safe — the bundled template always resolves, and you can opt in any time by re-running /flow-next:setup.`
- **options**:
  - `Copy template` — write `<repo_root>/SPEC.md` from the bundled template (carries the customization-location top-comment). Print the path so the user knows where to edit.
  - `Skip` — no write. Cascade falls through to the plugin's bundled template. Opt in any time by re-running `/flow-next:setup`.
  - `abort` — exit cleanly. Earlier steps (Step 1 `flowctl init`, and Step 2b's leftover cleanup if you accepted it) may already have run; init is idempotent and safe to leave, and a completed cleanup means the instruction-file snippet has NOT yet been refreshed - finish setup (or re-run it) before relying on direct `flowctl` instructions in CLAUDE.md/AGENTS.md. No `<repo_root>/SPEC.md` write; Step 4b onward skipped. Re-run `/flow-next:setup` later to complete setup.

On `Copy template`: write the file via Bash `cp` with absolute paths.

```bash
cp "${PLUGIN_ROOT}/templates/spec.md" SPEC.md
```

**2-3. `HITS>=1` (a repo-root `SPEC.md` or `spec.md` exists):** read
[references/existing-spec.md](references/existing-spec.md) and follow it. A customized file is never
replaced without an explicit answer. Setup seeds uppercase `SPEC.md` only on the `HITS=0` path.

## Step 4b: Codex-specific project setup (PLATFORM=codex only)

**This step runs only when `PLATFORM` is `codex`.** A `.codex/agents/` directory created on a Claude Code, Droid, Cursor, Grok, or OpenCode host has broken this. (Cursor, Grok, and OpenCode drive the workflow with slash commands, not project-scoped `.codex/` agents. Grok never copies `.codex/agents`. OpenCode never copies `.codex/agents`.)

On Codex, agents live in project-scoped `.codex/` directories (not in the plugin cache). Copy them. **Do not copy or enable hooks here.**

### Copy agent .toml files

```bash
# Source: pre-built agents from plugin (or global install)
AGENTS_SRC="${PLUGIN_ROOT}/codex/agents"
[ -d "$AGENTS_SRC" ] || AGENTS_SRC="$HOME/.codex/agents"

if [ -d "$AGENTS_SRC" ]; then
  mkdir -p .codex/agents
  DIFFERING=()
  for f in "$AGENTS_SRC"/*.toml; do
    t=".codex/agents/$(basename "$f")"
    if [ ! -e "$t" ]; then cp "$f" "$t"; elif ! cmp -s "$f" "$t"; then DIFFERING+=("$t"); fi
  done
  echo "Agent configs in .codex/agents/: $(ls .codex/agents/*.toml 2>/dev/null | wc -l | tr -d ' '); differing from this release: ${#DIFFERING[@]}"
else
  echo "Warning: No agent .toml files found at ${PLUGIN_ROOT}/codex/agents/ or ~/.codex/agents/"
fi
```

A file in `DIFFERING` was edited locally or comes from an older release. Attended, ask once whether
to replace those files with this release's versions (local edits are lost); otherwise leave them
and list them in the summary.

### Done when

- **User-owned files — repo-root `SPEC.md`, `.flow/criteria.md` — were compared before writing, left untouched when identical, and never overwritten without an explicit answer.** A customized one silently replaced has broken this.
- `.codex/agents/*.toml` exists only when `PLATFORM=codex`, and no hook was copied or enabled here.

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

Use the Step 2 response, without repeating shell probes or config calls:

- `tools` supplies the `HAVE_CODEX`, `HAVE_COPILOT`, `HAVE_CURSOR`,
  `HAVE_CLAUDE`, and `HAVE_GROK` availability flags.
- `config` supplies raw `CURRENT_BACKEND`, `CURRENT_SPEC_IDS`, and
  `CURRENT_QA`. Only null means unset; false is an answer. A `CURRENT_BACKEND`
  of `rp` (or `rp:...`) names a removed backend: tell the user in one line
  "RepoPrompt review (rp, export) was removed in flow-next 8.0.0; review
  backends: claude, codex, copilot, cursor, host." and treat it as unset.
- `criteria_exists` supplies `CRITERIA_EXISTS`; symlinks count as existing.
- `tracker_active` supplies `TRACKER_CONFIGURED` from the canonical predicate.

### 6b: Check docs status

Choose the correct template based on platform:
- **Codex** (`PLATFORM=codex`): read [templates/agents-md-snippet.md](templates/agents-md-snippet.md) — uses `$flow-next-plan` syntax
- **Claude Code / Droid / Cursor / Grok**: read [templates/claude-md-snippet.md](templates/claude-md-snippet.md) — names skills by id (`flow-next:flow-next-plan`) (Cursor runs the same slash commands; on Cursor the snippet lands in AGENTS.md. Grok drives with `/flow-next-` slash commands and reads BOTH CLAUDE.md and AGENTS.md — lifecycle snippet targets CLAUDE.md by default; a pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form, marker-scoped)
- **OpenCode** (`PLATFORM=opencode`): same Claude-flavor template as above, rewritten `/flow-next:` → `/flow-next-` (flat command names; never `$flow-next-`) and skill ids `flow-next:flow-next-` → `flow-next-`. Lifecycle snippet lands in AGENTS.md. Rewrite the template into a temp file *before* any `setup-block` call so the helper hashes the bytes actually applied:

  ```bash
  SNIPPET_TEMPLATE="${PLUGIN_ROOT}/skills/flow-next-setup/templates/claude-md-snippet.md"
  if [[ "$PLATFORM" == "opencode" ]]; then
    SNIPPET_TEMPLATE="${TMPDIR:-/tmp}/flow-next-opencode-snippet.md"
    sed -e 's|/flow-next:|/flow-next-|g' -e 's|flow-next:flow-next-|flow-next-|g' \
      "${PLUGIN_ROOT}/skills/flow-next-setup/templates/claude-md-snippet.md" \
      > "$SNIPPET_TEMPLATE"
  fi
  ```

Both templates are the same slim rail: bare `flowctl`, `flowctl usage` pull directives, and an internal `<!-- flow-next:snippet:vN -->` sentinel that versions the block.

Use `docs` from the Step 2 response for each file: `missing`, `current`,
`outdated`, or `unreadable`. An unreadable file needs diagnosis before edits.
The existing setup-block helpers still own fresh write-time consent checks.

### 6c: Show current config notice

If ANY config values are already set, print a notice before asking questions:

```
Current configuration:
- Review backend: <current value, bare or spec form> (change with: flowctl config set review.backend <codex|copilot|cursor|claude|host|none OR spec form like codex:<model>:xhigh, cursor:<model>, or claude:<model>:<effort>>)
- Spec ids: <flow|tracker> (change with: flowctl config set tracker.specIds <flow|tracker>)
- Live QA: <off|on|auto> (change with: flowctl config set pipeline.qa <off|on|auto>)
```

Only include lines for config values that are set. If no config is set, skip this notice. (Spec ids line only when `CURRENT_SPEC_IDS` is non-empty — an unset key is not "set". Live QA line only when the 6d Live QA question is skipped: on a first run the materialized `off` is not yet an answer.)

### 6d: Build questions list

Build the questions array dynamically. **The questions array is built only from keys that read raw-null in `.flow/config.json`** (one exception: `pipeline.qa` materializes as `off` on init, so the Live QA question also treats that default as unanswered on a first setup run and never on a re-run). A re-run with everything set that asks a config question it already knows the answer to has broken this — existing config is preserved, never silently flipped. To change an already-set value, the user runs `flowctl config set <key> <value>` directly (the commands are surfaced in 6c's current-config notice).

Skipped questions = config values already persisted from a prior run. Asking again would either no-op (same answer) or silently flip a deliberate user choice — both are wrong. The questions go out in two `AskUserQuestion` calls, because the tool takes at most 4 questions per call, 4 options per question, and a header of at most 12 characters: the **config call** (Review, Live QA, Spec ids — only the unset entries) and then the **files call** (Docs, Criteria, Star). Skip a call whose array is empty, so a steady re-run with all choices recorded asks nothing. Filter the files call through `optional_answers` before applying its remaining gates. **There is no routing question** — the routing block is proposed, not negotiated (Step 7).

Available questions (include only if corresponding config is unset):

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

**Live QA question** (include if CURRENT_QA is empty, OR if CURRENT_QA is "off" AND `SETUP_FIRST_RUN=1` - the key materializes as `off` on init, so a first run treats that default as unanswered; a re-run treats a persisted value as the answer and never re-asks):
```json
{
  "header": "Live QA",
  "question": "Run a live QA pass before the PR? /flow-next:qa drives the running app like a real user against the spec's acceptance criteria and files evidence-backed findings. It needs a startable target (dev server, deploy URL, or running instance) and a browser driver. Rule: skills/flow-next-flow/references/gate-selection.md",
  "options": [
    {"label": "off (Recommended when nothing runs in a browser yet)", "description": "QA runs only when you invoke /flow-next:qa <spec> yourself. Enable later: flowctl config set pipeline.qa on|auto"},
    {"label": "on", "description": "One live pass per spec at all-tasks-done, before make-pr (rule: the flow skill's gate-selection reference)"},
    {"label": "auto", "description": "The live pass only where the flow skill's gate-selection reference selects it; other specs record skipped(reason) and advance"}
  ],
  "multiSelect": false
}
```

**Criteria question** (include if `CRITERIA_EXISTS=0` — an existing `.flow/criteria.md` is user content: never re-ask, never touch. Like the Step 4a SPEC.md offer, it seeds a user-owned file, not a setup-managed copy):
```json
{
  "header": "Criteria",
  "question": "Scaffold .flow/criteria.md? A plain markdown file of standing, project-wide acceptance criteria (- **G1:** every route change regenerates the contract...). When present, spec completion review judges every criterion against each spec's implementation and records met/violated/n-a in the review receipt. Absent = zero effect anywhere.",
  "options": [
    {"label": "Scaffold", "description": "Write .flow/criteria.md from the bundled template - documents the G-ID grammar with commented examples to replace with your own criteria"},
    {"label": "Skip", "description": "No file written, nothing changes. Opt in any time by creating .flow/criteria.md yourself (grammar: - **G<N>:** <criterion>) or explicitly asking setup to revisit this choice"}
  ],
  "multiSelect": false
}
```

**Review question** (include if CURRENT_BACKEND is empty): read
[references/review-question.md](references/review-question.md) for the four-option rule, the
per-platform menu and the stored value.

**No Model Routing question exists.** Setup never asks which models to route to,
never probes a CLI for slugs, and never proposes a pin. Step 7 writes one
commented example block and says so — that is the whole ceremony.

**Docs question** (include only when unanswered and docs are not current): read
[references/docs-question.md](references/docs-question.md) and use the block for this `PLATFORM`.

**Star question** (include only when unanswered):
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

Send the config call, then the files call, each through `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded).

**Note:** If docs are already current, skip the Docs question entirely.

**Note:** If no codex, copilot, cursor-agent, or claude is detected, add this note to the Review question: "No review backend detected. Install codex, copilot, cursor-agent, or claude for review support, or choose Host."

### Done when

- The config call and the files call each carried at most 4 questions, every question at most 4 options, and every header at most 12 characters; together they hold only the still-unanswered keys plus Docs / Star (and Criteria when its own gate passed).
- **No routing question was asked, no CLI was probed for model ids, and no pin was proposed or stamped.** Setup asking which model to route to, or writing a model id anywhere, has broken this.

## Step 7: Process Answers

Only process answers for questions that were asked (config values that were unset). Skip processing for config that was already set.

**Spec ids** (if question was asked — only when tracker was configured and the key was unset):
- If "Tracker" / label starts with `Tracker`: `"${PLUGIN_ROOT}/scripts/flowctl" config set tracker.specIds tracker --json`
- If "Flow": `"${PLUGIN_ROOT}/scripts/flowctl" config set tracker.specIds flow --json`
- Writing either value ends the ask-once contract: the next setup run sees a non-empty raw key and skips this question.

**Live QA** (if question was asked; match on the label's leading value):
- If "off"*: `"${PLUGIN_ROOT}/scripts/flowctl" config set pipeline.qa off --json`
- If "on": `"${PLUGIN_ROOT}/scripts/flowctl" config set pipeline.qa on --json`
- If "auto": `"${PLUGIN_ROOT}/scripts/flowctl" config set pipeline.qa auto --json`
- Any other answer: leave the persisted value alone (it stays the materialized `off`) and say so in the summary.
- Step 8 prints the one-line `/flow-next:features` recommendation whatever the persisted value.

**Criteria** (if question was asked):
- If "Scaffold": copy the bundled template (resolved from the plugin install - the file is user content from this moment on, so no re-run ever refreshes or compares it):

  ```bash
  cp "${PLUGIN_ROOT}/templates/criteria.md" .flow/criteria.md
  ```

- If "Skip": write no criteria file; persist `setup.optional_answers.criteria = "Skip"` in metadata so the next setup does not ask again.

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
  "Claude"*|"claude"*) REVIEW_BACKEND="claude" ;;
  *) REVIEW_BACKEND="none" ;;
esac

"${PLUGIN_ROOT}/scripts/flowctl" config set review.backend "$REVIEW_BACKEND" --json
```

**Docs:**

Use the correct template based on **target file** and **platform**:
- AGENTS.md on **Codex**: use [templates/agents-md-snippet.md](templates/agents-md-snippet.md) (uses `$flow-next-plan` syntax)
- AGENTS.md on **Claude Code / Droid / Cursor / Grok**: use [templates/claude-md-snippet.md](templates/claude-md-snippet.md) (names skills by Claude-format id — Cursor and Grok resolve those ids, so their AGENTS.md must carry this snippet, NOT the Codex `$flow-next-` one; a wrong Codex `$` block is consent-refreshed marker-scoped)
- AGENTS.md on **OpenCode**: use the Claude-flavor snippet rewritten `/flow-next:` → `/flow-next-` via the 6b temp-template block (`$SNIPPET_TEMPLATE`). Never the Codex `$flow-next-` form. Pass that rewritten file as `--template` to every `setup-block apply` / `resolve` for this platform so hashes match the bytes written.
- CLAUDE.md (any platform — including Grok's default lifecycle target): use [templates/claude-md-snippet.md](templates/claude-md-snippet.md). On OpenCode, if CLAUDE.md is also a resolved target, apply the same `/flow-next:` → `/flow-next-` rewrite (same `$SNIPPET_TEMPLATE`) so both files carry the flat form.

**Resolve the target file set:** an explicit Docs-question answer is authoritative - if the user is asked and selects specific files (or declines one), honor exactly that; never touch a file the user just deselected. The one addition is a backfill for the SKIPPED case: when the Docs question is omitted entirely because the block is already current (per the Note above), still run `apply` on each already-marker-bearing file. Rationale: a current-but-hashless block (written by a pre-hash plugin version) would otherwise never reach `apply`, so its pristine hash never gets backfilled and the NEXT template change wrongly prompts "Overwrite customized?". `apply` on a current block is cheap and idempotent - it returns `unchanged` and records the missing hash. So: resolve targets = files chosen by the Docs question when it was asked; OR, when the Docs question was skipped, the files already carrying the `<!-- BEGIN FLOW-NEXT -->` marker. Run the helper once per resolved file.

For each resolved file (CLAUDE.md and/or AGENTS.md) - the block mechanics (marker-scoped replace, per-`(path, id)` pristine-hash tracking in `.flow/meta.json` `setup.block_hashes` - a nested `{<path>: {<id>: <hash>}}` map; these call sites pass no `--id`, so they always read/write the default `FLOW-NEXT` id) are deterministic flowctl plumbing; this step owns only the ask:

1. Run the helper (repeat per resolved file, substituting the snippet template selected above):

   ```bash
   "${PLUGIN_ROOT}/scripts/flowctl" setup-block apply --file <FILE> \
     --template "${SNIPPET_TEMPLATE:-${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md}" --json
   ```

2. Route on the returned `action` - the first four need no prompt:
   - `appended` - no marker block existed; the snippet was appended at end of file (pre-existing content untouched) and its pristine hash recorded.
   - `refreshed` - the existing block matched its recorded pristine hash (never customized), so the helper silently replaced it with the new canonical and updated the hash. Existing installs receive template fixes without a prompt.
   - `unchanged` - the block already matches the canonical template. No write, no mtime bump.
   - `kept` - a previous "Keep mine" recorded the `"customized"` sentinel; the helper never re-asks and never silently overwrites. Leave it alone.
   - `ask` (reason `customized` or `hash-absent`) - the block differs from canonical and is not provably pristine. The helper wrote nothing; ask via `AskUserQuestion`:
     - **header**: `Overwrite`
     - **question**: `Overwrite the customized flow-next block in <FILE>? <FILE> contains a flow-next marker block that differs from the canonical template shipped with this plugin version and is not recorded as pristine. Overwriting replaces the marker block only; content outside the markers is untouched either way.`
     - **options**:
       - `Keep mine (Recommended)` - run `"${PLUGIN_ROOT}/scripts/flowctl" setup-block resolve --file <FILE> --template <same template> --choice keep --json`. This records the `"customized"` sentinel so future re-runs never re-ask and never overwrite. Print the canonical template path so the user can diff manually (`${PLUGIN_ROOT}/skills/flow-next-setup/templates/<snippet>.md`).
       - `Overwrite with canonical` - run the same `setup-block resolve` command with `--choice overwrite`. This replaces the marker block with the canonical snippet and records the new pristine hash; customizations inside the markers are lost, content outside the markers is preserved.
       - `abort` - exit cleanly, no further writes. Earlier steps (init, Step 2b's leftover cleanup if accepted, config writes, prior docs-file decisions for any already-processed file) may already have run; they are idempotent and safe to leave. Everything from here onward is skipped (remaining docs files, the routing block, and the Star step). Re-run `/flow-next:setup` later to complete setup.

The marker-block boundaries are load-bearing: **docs snippets are written through `flowctl setup-block apply`, touching only the bytes inside the flow-next markers.** Prose outside `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` that changed, or a write made by anything other than the helper, has broken this. And **an `ask` result prompts Keep mine / Overwrite / abort** — a customized block replaced without that answer has broken this too.

**Routing block** — one proposal, no question. Run this **after** the Docs block
above and before Star. Always re-read target files from disk after Docs;
never interleave the two writes. Two hard outs before the ladder: a **Docs
answer of `Skip`** is a decline of documentation edits and declines this write
too — record `skipped (docs declined)` and move on; a **headless or autonomous
run** (`FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`, or `mode:autonomous`) never writes the block — instruction-file edits are the
user's, so record `skipped (headless)` and move on.

Resolve the target with this ladder, first match wins:

1. Docs answered this run: mirror `CLAUDE.md only`, `AGENTS.md only`, or `Both`.
2. Otherwise the files already carrying `<!-- BEGIN FLOW-NEXT -->`.
3. Otherwise Codex / Cursor / Grok / OpenCode → `AGENTS.md`; Claude Code / Droid →
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
  `kept (yours)`. A block the user edited (or emptied) is theirs from the
  moment it exists - and setup may be re-run at any time (snippet bump, config
  change), so it must stay safe against every future run. Rewriting one has broken
  this.
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

**Star:**
- If "Yes, star it":
  1. Check if `gh` CLI is available: `which gh`
  2. If available, run: `gh api -X PUT /user/starred/gmickel/flow-next`
  3. If `gh` not available or command fails, show: `Star manually: https://github.com/gmickel/flow-next`

## Step 8: Print Summary

When `TYPESAFE_API_KEY` is absent or empty, add exactly one notice:
`Judge: off (TYPESAFE_API_KEY is not set).` Check presence only; never print,
store, request, or configure the key. See [judge](../../docs/judge.md).

```
Flow-Next setup complete!

Platform: <claude-code|codex|droid|cursor|grok|opencode>

Written:
- <CLAUDE.md and/or AGENTS.md> flow-next snippet (marker-fenced, sentinel v<N>)
- <repo-root>/SPEC.md (only if Step 4a "Copy template" was chosen — otherwise omit this line)
- .flow/criteria.md (only if the Criteria "Scaffold" option was chosen — otherwise omit this line)

Nothing was copied into .flow/ — flowctl comes from the plugin install:
  flowctl --help        # every command
  flowctl usage         # CLI cheatsheet + orchestration recipes, always current
```

**If PLATFORM=cursor, also show:**
```
Cursor host notes:
- flowctl resolves from the plugin install via the skill's own absolute path (Cursor exposes no plugin-root env vars) — nothing is copied into the repo
- Review default: host (host-native cross-family subagent; the model is named on the `reviewer` tier of the AGENTS.md routing block)
```

**If PLATFORM=grok, also show:**
```
Grok host notes:
- flowctl resolves from the plugin install via the skill's own absolute path (Grok exposes no plugin-root env vars) — nothing is copied into the repo
- Docs: /flow-next: slash snippet (CLAUDE.md default lifecycle target; Grok also reads AGENTS.md)
- Routing block: AGENTS.md (where host review reads the `reviewer` tier)
- Review: host offered (single-native-family fail-closed for Grok writers) + codex/copilot/cursor/claude/none
- No .codex/agents copy
- Detection: GROK_AGENT=1 (not ~/.grok or PATH)
```

**If PLATFORM=opencode, also show:**
```
OpenCode host notes:
- flowctl resolves from the plugin install via the skill's own absolute path (OpenCode exposes no plugin-root env vars) — nothing is copied into the repo
- Docs: AGENTS.md with the Claude snippet rewritten /flow-next: → /flow-next- (flat command names; never $flow-next-)
- Routing block: AGENTS.md
- Review: default menu (Host + None)
- Detection: ${PLUGIN_ROOT}/.flow-next-opencode-manifest (installer ownership file; never an env var)
- Invoke setup later as /flow-next-setup (flat), not /flow-next:setup
```

**If PLATFORM=codex, also show:**
```
Codex project setup:
- .codex/agents/*.toml (<N> agent configs)
```

**Then always show:**
```
Configuration (use flowctl config set to change):
- Memory: <enabled|disabled>
- Plan-Sync: <enabled|disabled>
- Plan-Sync cross-spec: <enabled|disabled>
- GitHub scout: <enabled|disabled>
- Spec ids: <flow|tracker|unset>   # only meaningful when a tracker is configured; tracker is the team default
- Live QA: <off|on|auto>
- Review backend: <host|codex|copilot|cursor|claude|none>

Documentation updated:
- <files updated or "none">

Model routing: <ROUTING_OUTCOME — "written to CLAUDE.md" | "kept (yours)" | "skipped (shim)" | "skipped (docs declined)" | "skipped (headless)">
- The block is a commented example; edit it to name the models you want per tier.

Notes:
- Plugin updates need no per-repo action, on any host — nothing was copied, so nothing goes stale. Re-run /flow-next:setup only when setup says the snippet schema bumped, or to change configuration / seed files.
- Live QA stage: off by default. Change it with `flowctl config set pipeline.qa <off|on|auto>`; what each value does is in the flow skill's gate-selection reference (`skills/flow-next-flow/references/gate-selection.md`). Needs a running app plus a browser driver
- Land patience: `flowctl config set land.patienceMinutes <minutes>` sets the wait after the last push when no human authorized the merge in-session.
- Use Linear / GitHub Issues / GitLab / Jira for project management? Run /flow-next:tracker-sync to configure the (opt-in) two-way tracker bridge — it runs a discovery ceremony (detects Linear MCP / LINEAR_API_KEY / gh auth / glab auth or GITLAB_TOKEN / JIRA_BASE_URL + credential, asks, writes config), then syncs specs ⇄ issues; on Linear it additionally makes your PRs reviewable as Linear Diffs. Skips cleanly if you don't use a tracker; adds nothing to the base install until enabled.
- Uninstall (run manually): remove the <!-- BEGIN/END FLOW-NEXT --> and <!-- flow-next:model-routing:start/end --> blocks from docs (plus any legacy .flow/bin, .flow/templates, .flow/usage.md leftovers, if you kept them) — or run /flow-next:uninstall for full cleanup
- This setup is optional - plugin works without it
```
**Tracker-sync proposal (always show, after the Notes block).** Surface the tracker bridge as an explicit optional next step — the discovery ceremony is the bridge's own setup, separate from this skill (which never touches tracker config, keeping the zero-dep base clean):

```
Optional next step — connect a tracker:
  If your team lives in Linear, GitHub Issues, GitLab, or Jira, run  /flow-next:tracker-sync  to set up the
  two-way bridge (spec ⇄ issue, status, comments) and make PRs reviewable as Linear Diffs.
  Fully opt-in — nothing syncs until you confirm it in the discovery ceremony.
```

**Feature-map recommendation (always, whatever `pipeline.qa` says).** Print one line after the tracker proposal, chosen by `"${PLUGIN_ROOT}/scripts/flowctl" features status --json` `.recommendation` (in a home-base workspace, where sibling repos hold the product code, add `--repo <path>` for each one the project instructions name). The map lets QA, drive and bug intake reuse how a user reaches each feature instead of rediscovering it. Setup never runs the seed itself: it launches and drives the live app. A repo with no drivable surface still gets the line; the seed pass refuses there on its own.

- `seed` (no `.flow/features/`):
  ```
  Recommended next step: run /flow-next:features to seed .flow/features/ - QA, drive and bug intake read it to reach each feature without rediscovering the route.
  ```
- `maintain` (a map is due):
  ```
  Recommended next step: run /flow-next:features to maintain .flow/features/ - it is due (<reasons joined by "; ">).
  ```
- `none` (a current map):
  ```
  Feature map: current. Run /flow-next:features when flow or setup reports it due.
  ```

