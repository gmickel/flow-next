---
name: flow-next-memory-migrate
description: Migrate pre-fn-30 legacy flat memory files (`.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md`) into the categorized YAML schema. Triggers on /flow-next:memory-migrate, "migrate memory", "convert legacy memory", "lift pitfalls into categorized schema", "convert old memory format". Optional `mode:autofix` token in arguments runs without questions and accepts mechanical defaults for ambiguous classifications. Optional scope hint after the mode token narrows the migration to a specific legacy file (e.g. `pitfalls.md`).
user-invocable: false
allowed-tools: request_user_input, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:memory-migrate — agent-native legacy migration

Pre-fn-30 flow-next stored memory as three flat markdown files: `.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md`. Each was a sequence of `---`-delimited segments with ad-hoc headings and no schema. fn-30 introduced the categorized schema (track / category / module / tags / status frontmatter, one entry per file). Existing flat files persisted but became invisible to `memory list`, `memory search`, and `flow-next-audit` because there's no frontmatter to scope or stale-flag.

This skill IS the migration. The host agent (Claude Code / Codex / Droid) reads each legacy entry, applies the mechanical default `(track, category)` from the source filename, overrides only when the entry's content warrants, and writes a categorized entry via `flowctl memory add`. Optional autofix mode accepts every mechanical default and marks ambiguous entries as `needs-review` in the report.

There is no Python classifier subprocess, no `codex`/`copilot` dispatch, no fast-model probability scoring. The host agent is already an LLM with full repo context and does the work directly. flowctl provides only thin parsing + persistence plumbing (`memory list-legacy --json`, existing `memory add`) — landed by Task 2 of this epic.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the (track, category) decision tree with mechanical baseline + override examples.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** — `request_user_input` must stay reachable across phases. Subagents can't call blocking question tools (Claude Code issues #12890, #34592). Phase 1 (Classify) needs user choice on ambiguous entries in interactive mode; Phase 4 (Cleanup) needs consent before renaming originals.

## Mode Detection

Parse `$ARGUMENTS` for the literal token `mode:autofix`. If present, strip it from the arguments — the remainder is the scope hint (a legacy filename like `pitfalls.md` to narrow the run, or empty to migrate all).

```bash
RAW_ARGS="$ARGUMENTS"
MODE="interactive"
if [[ "$RAW_ARGS" == *"mode:autofix"* ]]; then
 MODE="autofix"
 # Strip token, collapse whitespace, trim.
 SCOPE_HINT=$(printf "%s" "$RAW_ARGS" | sed 's/mode:autofix//' | tr -s ' ' | sed 's/^ //;s/ $//')
else
 SCOPE_HINT="$RAW_ARGS"
fi
```

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | User is at the terminal | Ask via blocking-question tool when an entry's content suggests overriding the mechanical default; confirm Phase 4 cleanup; show triage summary before writes |
| **Autofix** (`mode:autofix` in arguments) | Ralph or batch usage | No user questions. Apply mechanical defaults for every entry. Override only when the agent has high-confidence evidence from the entry body. Mark genuinely ambiguous entries as `needs-review` in the report. Default-decline Phase 4 cleanup. Print full report |

### Autofix mode rules

- **No user questions.** Never call the blocking-question tool.
- **Process every legacy entry in scope.** No scope-narrowing question. If no scope hint was provided, migrate all three legacy files.
- **Mechanical default wins on borderline.** Override only when the entry body unambiguously points at a different `(track, category)` (e.g. an entry titled "race condition in worker pool" inside `pitfalls.md` clearly warrants `bug/runtime-errors` over the mechanical `bug/build-errors`).
- **Ambiguous → mechanical default + log as `needs-review`.** Genuine "could be A or B" cases take the mechanical default and surface in the report so the user can re-classify later.
- **Default-decline Phase 4 cleanup.** Originals stay in place. Surface the rename suggestion as a recommendation in the report.
- **Always print the full report.** The report is the sole deliverable — there is no user to ask follow-ups.

## Interaction Principles (interactive mode only)

In autofix mode, skip user questions entirely and apply the rules above.

In interactive mode, follow these principles:

- Ask **one question at a time** via `request_user_input`. Fall back to numbered options in plain text only if the tool is unreachable or errors. Never silently skip the question.
- Prefer **multiple choice** when natural options exist.
- Lead with the **recommended option** (always the mechanical default unless the body warrants otherwise) and a one-sentence rationale.
- Do **not** ask the user to make decisions before the entry has been read — Phase 1 reads first, asks second.
- Group obvious mechanical-default migrations together for batched confirmation. Present overrides and ambiguous cases one at a time.

The goal is automated migration with human oversight on judgment calls — not a question for every entry.

## Subagent dispatch (mostly N/A)

This skill runs almost entirely on the main thread. Phase 1's "one entry per tool call" rule means classification iterates serially in the orchestrator — there is no investigation step independent enough to dispatch in parallel. Cross-platform tool naming (`Task` on Claude Code, `spawn_agent` on Codex, platform-equivalent on Droid) is documented here only for the rare case where the agent needs to spawn a focused investigation subagent (e.g. resolving an ambiguous override by reading a referenced file): keep such dispatches read-only (Read / Grep / Glob), do not let subagents call `flowctl memory add` directly, and merge results back on the main thread before Phase 2.

## Forbidden

- **Migrating files outside `MEMORY_LEGACY_FILES`** (`pitfalls.md`, `conventions.md`, `decisions.md` at `.flow/memory/` root). Any other `.md` at the memory root is user data — leave it alone.
- **Migrating entries inside categorized directories** (`.flow/memory/{bug,knowledge}/<category>/*.md`). Those are already migrated; re-running on them is a bug.
- **Auto-deleting legacy flat files.** Phase 4 renames originals to `.flow/memory/_migrated/<filename>.bak` for traceability — never `rm`. User can `git rm` later if they want.
- **Inventing flowctl subcommands** beyond what Task 2 ships (`memory list-legacy`). Phase 2 writes via existing `flowctl memory add`. Mechanical map is documented in phases.md so the agent doesn't need to call a flowctl helper for it.
- **Batch-classifying multiple entries in a single tool call.** Phase 1 enforces one entry per tool call. Agents under context pressure batch-classify in-prompt and silently skip entries (practice-scout flagged this real failure mode).
- **Setting `context: fork`** — blocking-question tools must stay reachable.
- **Re-running on already-migrated files.** Phase 0 checks `.flow/memory/_migrated/<filename>.bak` and skips with an "already migrated" log line.

## Pre-check: local setup version

Same pattern as `/flow-next:plan` and `/flow-next:audit` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

```bash
if [[ -f .flow/meta.json ]]; then
 SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
 PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
 [[ -f "$PLUGIN_JSON" ]] || PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
 PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
 if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
 echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
 fi
fi
```

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Detect & enumerate** — run `flowctl memory list-legacy --json`, check `_migrated/` for prior runs, apply scope hint, decide interaction path.
1. **Classify (one entry per tool call)** — for each entry: read title + body + filename context, default to mechanical `(track, category)`, override only with body-driven evidence. Interactive: ask on ambiguity. Autofix: take mechanical default + log `needs-review`.
2. **Write categorized entries** — invoke `flowctl memory add --track <t> --category <c> --title "..." --body-file <tmpfile>` per classified entry. Slug uniqueness handled by existing helper.
3. **Verify + Report** — re-read newly created entries, print summary (legacy files processed, entries migrated, overrides, needs-review).
4. **Optional cleanup** — interactive: ask whether to rename originals to `.flow/memory/_migrated/<filename>.bak`. Autofix: default-decline + surface as recommendation. On first cleanup, write `.flow/memory/_migrated/.gitignore` containing `*` (self-ignoring directory pattern). NEVER auto-delete.

## Output rules

The full report is the deliverable — print it as markdown to stdout. Do not summarize internally and emit a one-liner.

Report structure (see [workflow.md](workflow.md) §3 for full schema):

```text
Memory Migration Summary
========================
Legacy files processed: <N> (skipped: <K> already migrated)
Entries migrated: <M>
Overrides (mechanical → agent-decided): <P>
Needs review (ambiguous, took mechanical default): <Q>
```

Then per-entry detail (id, source filename, mechanical default, final classification, override rationale if any). For `needs-review` entries: why the agent couldn't decide.

Autofix mode splits actions into **Applied** (writes succeeded) and **Recommended** (writes failed — e.g. permission denied, schema validation failed). The structure is the same; only the bucket differs. Phase 4 cleanup is always **Recommended** in autofix.
