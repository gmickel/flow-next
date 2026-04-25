---
name: flow-next-audit
description: Audit `.flow/memory/` entries against the current codebase and decide Keep / Update / Consolidate / Replace / Delete per entry. Triggers on /flow-next:audit, "audit memory", "review memory", "refresh learnings", "sweep stale memory", "consolidate overlapping memory entries". Optional `mode:autofix` token in arguments runs without questions and marks ambiguous as stale. Optional scope hint after the mode token (concept, category, module, or path) narrows what gets audited.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:audit — agent-native memory staleness review

Memory entries decay. A `.flow/memory/bug/runtime-errors/` entry logged six months ago might reference a renamed file, a deleted function, or a codepath that no longer exists. Without periodic review, the store accumulates zombie entries and `memory-scout` surfaces outdated advice.

This skill IS the audit. The host agent (Claude Code / Codex / Droid) walks `.flow/memory/`, reads each entry, uses Read/Grep/Glob/git to verify references against the current codebase, applies engineering judgment, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete**. Optional autofix mode applies unambiguous actions and marks ambiguous as stale.

There is no Python audit-engine, no codex/copilot subprocess dispatch, no deterministic scorer. The host agent is already an LLM and does the work directly. flowctl provides only thin persistence plumbing (`memory mark-stale`, `memory mark-fresh`, `memory search --status`) — landed by Task 2 of this epic.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the 5-outcomes lookup with memory-schema-specific calibration.**

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
```

**Inline skill (no `context: fork`)** — `AskUserQuestion` must stay reachable across phases. Subagents can't call blocking question tools (Claude Code issues #12890, #34592). Phase 3 (Ask) and Phase 6 (Discoverability check) both require user choice in interactive mode. (sync-codex.sh rewrites `AskUserQuestion` to `request_user_input` in the Codex mirror.)

## Mode Detection

Parse `$ARGUMENTS` for the literal token `mode:autofix`. If present, strip it from the arguments — the remainder is the scope hint.

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
| **Interactive** (default) | User is at the terminal | Ask decisions on ambiguous cases via blocking-question tool; confirm batched actions; run discoverability check with consent |
| **Autofix** (`mode:autofix` in arguments) | Ralph or batch usage | No user questions. Apply Keep/Update/Consolidate/auto-Delete/Replace-with-sufficient-evidence directly. Mark ambiguous as stale. Print the full report. Discoverability surfaces as a recommendation, not an edit |

### Autofix mode rules

- **No user questions.** Never call the blocking-question tool.
- **Process all entries in scope.** No scope-narrowing question. If no scope hint was provided, process every categorized entry.
- **Attempt all safe actions.** Keep (no-op), Update (write tool), Consolidate (merge + `git rm` subsumed), auto-Delete (only when code AND problem domain both gone), Replace (only with sufficient evidence to write a trustworthy successor).
- **Mark ambiguous as stale.** When classification is genuinely ambiguous (Update vs Replace vs Consolidate vs Delete) or Replace evidence is insufficient, run `flowctl memory mark-stale <id> --reason "..."` instead of guessing. Stale-marking writes are atomic and round-trip safe.
- **Conservative confidence.** Borderline cases get marked stale; never deleted on autofix.
- **Always print the full report.** The report is the sole deliverable — there is no user to ask follow-ups.

## Interaction Principles (interactive mode only)

In autofix mode, skip user questions entirely and apply the rules above.

In interactive mode, follow these principles:

- Ask **one question at a time** via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Fall back to numbered options in plain text only if the tool is unreachable or errors. Never silently skip the question.
- Prefer **multiple choice** when natural options exist.
- Lead with the **recommended option** and a one-sentence rationale.
- Do **not** ask the user to make decisions before evidence is gathered — Phase 1 investigates first, Phase 3 asks.
- Group obvious Keeps and obvious Updates together for batched confirmation. Present Consolidate / Replace / Delete one at a time.

The goal is automated maintenance with human oversight on judgment calls — not a question for every finding.

## Forbidden

- **Auditing legacy flat files** (`.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md` at the memory root). Skip with a warning that recommends `/flow-next:memory-migrate` first. Report includes the skipped count.
- **Auditing under `_audit/`, `_review/`, or any other `_*` directory** under `.flow/memory/`.
- **Deleting silently.** Delete is reserved for unambiguous cases (code gone AND problem domain gone). Default to Replace or Consolidate when there's still value to preserve.
- **Inventing flowctl subcommands** beyond what Task 2 ships (`memory mark-stale`, `memory mark-fresh`, `memory search --status`). Use Write tool + git for moves and deletes.
- **Auto-committing without user awareness in interactive mode.** Phase 5 detects git context and asks. Autofix uses sensible defaults.
- **Setting `context: fork`** — blocking-question tools must stay reachable.
- **Running parallel replacement subagents.** Investigation subagents can run in parallel for 3+ independent entries; replacement subagents run sequentially to protect orchestrator context.

## Pre-check: local setup version

Same pattern as `/flow-next:plan` and `/flow-next:prospect` — non-blocking notice when `.flow/meta.json` `setup_version` lags the plugin version:

```bash
if [[ -f .flow/meta.json ]]; then
  SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
  PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  [[ -f "$PLUGIN_JSON" ]] || PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.factory-plugin/plugin.json"
  PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
  if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
    echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
  fi
fi
```

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Discover & Triage** — walk `.flow/memory/{bug,knowledge}/<category>/`, group by module / category, count, choose interaction path (focused / batch / broad), skip legacy + `_*` directories with a counted warning.
1. **Investigate** — per entry: read frontmatter + body, verify referenced files / symbols / modules against current code via Read / Grep / Glob, check git log in the area, form Keep / Update / Consolidate / Replace / Delete recommendation with 2-4 evidence bullets and confidence. For 3+ independent entries, dispatch parallel investigation subagents (read-only).
1.75 **Cross-doc analysis** — compare entries sharing module / category for overlap (problem, solution, root cause, files), supersession (newer canonical entry covers older narrower precursor), contradictions.
2. **Classify** — apply [phases.md](phases.md) decision criteria. For Replace, verify evidence is sufficient to write a trustworthy successor; mark stale otherwise.
3. **Ask** — interactive only; autofix skips. Group obvious Keeps + Updates → confirm batch. Present Consolidate / Replace / non-auto-Delete individually. Lead with recommendation. One question at a time.
4. **Execute** — Keep: no edit. Update: agent edits frontmatter / body via Write tool, preserving unknown fields. Consolidate: merge unique content into canonical, `git rm` subsumed. Replace: write new entry, `git rm` old. Delete: `git rm` (only when code AND problem domain both gone). Ambiguous in autofix: `flowctl memory mark-stale`.
5. **Report + Commit** — print Kept / Updated / Consolidated / Replaced / Deleted / Marked-stale / Skipped counts plus per-entry detail. Detect git context (current branch, dirty tree). Interactive: ask commit options. Autofix: branch-and-PR on main, commit on feature branch, stage only audit-modified files.
6. **Discoverability check** — verify the substantive CLAUDE.md / AGENTS.md (the one not just `@`-including the other) mentions `.flow/memory/` with schema basics (track / category / module / tags / status) and when to consult. Add a minimal line if missing — interactive asks consent, autofix surfaces as recommendation.

## Output rules

The full report is the deliverable — print it as markdown to stdout. Do not summarize internally and emit a one-liner.

Report structure (see [workflow.md](workflow.md) §5 for full schema):

```text
Memory Audit Summary
====================
Scanned: N entries
Skipped legacy: M (run `/flow-next:memory-migrate` first to make these auditable)

Kept: X
Updated: Y
Consolidated: C
Replaced: Z
Deleted: W
Marked stale: S
```

Then per-entry detail (id, classification, evidence, action taken). For Consolidate: which entry was canonical, what unique content was merged, what was deleted. For Replace: what the old entry recommended vs what current code does, path to successor. For Marked stale: why ambiguous.

Autofix mode splits actions into **Applied** (writes succeeded) and **Recommended** (writes failed — e.g. permission denied). The structure is the same; only the bucket differs.
