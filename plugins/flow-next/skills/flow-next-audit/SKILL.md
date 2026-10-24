---
name: flow-next-audit
description: Audit `.flow/memory/` entries against the current codebase and decide Keep / Update / Consolidate / Replace / Delete / Harden per entry. Triggers on /flow-next:audit, "audit memory", "review memory", "refresh learnings", "sweep stale memory", "consolidate overlapping memory entries", "graduate a recurring lesson into a gate". Optional `mode:autofix` token in arguments runs without questions and marks ambiguous as stale (Harden is never auto-applied). Optional scope hint after the mode token (concept, category, module, or path) narrows what gets audited.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:audit — agent-native memory staleness review

Memory entries decay. A `.flow/memory/bug/runtime-errors/` entry logged six months ago might reference a renamed file, a deleted function, or a codepath that no longer exists. Without periodic review, the store accumulates zombie entries and `memory-scout` surfaces outdated advice.

This skill IS the audit. The host agent (Claude Code / Codex / Droid) walks `.flow/memory/`, reads each entry, reads and searches the code and git history to verify references against the current codebase, applies engineering judgment, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete / Harden**. Optional autofix mode applies unambiguous actions and marks ambiguous as stale.

**Harden** is the graduation path: a lesson that keeps getting re-learned and states a mechanically checkable rule should stop riding the context window and become a gate. The audit proposes an artifact in a surface the repo already has — a lint rule or a CI step — verifies the gate actually fires, and only then demotes the entry to a pointer at it (file stays on disk, provenance intact). Propose-and-confirm by design: gate surfaces are shared repo infrastructure, so Harden never applies unattended.

Decision entries (`.flow/memory/knowledge/decisions/`) and glossary terms (`GLOSSARY.md` files at the repo root and on the ancestor chain) are walked alongside the rest of memory. Decisions get a calibrated judging question — "does the constraint that motivated this choice still hold?" — and Replace becomes a two-step supersession (write successor, mark old `decision_status: superseded`, never `git rm`). Glossary terms are scanned for code usage; zero-hit terms get a `<!-- stale: ... -->` HTML comment via Edit tool (no `flowctl glossary mark-stale` exists), `_Avoid_` aliases appearing in code surface as alias-creep findings.

There is no subprocess judgment or deterministic classification. `memory audit-scan --json` collects mechanical evidence; `memory apply --plan <file> --json` persists host-authored actions. The host agent is already an LLM and does the work directly. flowctl provides only thin persistence plumbing (`memory mark-stale`, `memory mark-fresh`, `memory mark-hardened`, `memory search --status`). All judgment — is this recurring, is it mechanizable, which gate surface, what should the rule say — stays in this skill; there is no `flowctl gate` subcommand and never will be.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the 6-outcomes lookup with memory-schema-specific calibration.**

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** — `AskUserQuestion` must stay reachable across phases. Subagents can't call blocking question tools (Claude Code issues #12890, #34592). Phase 3 (Ask) and Phase 6 (Discoverability check) both require user choice in interactive mode.

## Mode Detection

Parse `$ARGUMENTS` for the literal token `mode:autofix`. If present, strip it from the arguments — the remainder is the scope hint.

```bash
RAW_ARGS="$ARGUMENTS"
MODE="interactive"
if [[ "$RAW_ARGS" == *"mode:autofix"* || "$RAW_ARGS" == *"mode:autonomous"* || "${FLOW_AUTONOMOUS:-}" == "1" || "${AUTONOMOUS:-}" == "1" ]]; then
  MODE="autofix"
  # Strip token, collapse whitespace, trim.
  SCOPE_HINT=$(printf "%s" "$RAW_ARGS" | sed 's/mode:autofix//; s/mode:autonomous//' | tr -s ' ' | sed 's/^ //;s/ $//')
else
  SCOPE_HINT="$RAW_ARGS"
fi
```

| Mode | When | Behavior |
|------|------|----------|
| **Interactive** (default) | User is at the terminal | Ask decisions on ambiguous cases via blocking-question tool; confirm batched actions; run discoverability check with consent |
| **Autofix** (`mode:autofix` in arguments) | Autonomous or batch usage | No user questions. Apply Keep/Update/Consolidate/auto-Delete/Replace-with-sufficient-evidence directly. Mark ambiguous as stale. Print the full report. Discoverability surfaces as a recommendation, not an edit |

### Autofix mode rules

- **No user questions.** Never call the blocking-question tool.
- **Process all entries in scope.** No scope-narrowing question. If no scope hint was provided, process every categorized entry.
- **Attempt all safe actions.** Keep (`mark-fresh` stamp only), Update (write tool), Consolidate (merge + `git rm` subsumed), auto-Delete (only when code AND problem domain both gone), Replace (only with sufficient evidence to write a trustworthy successor).
- **Never apply Harden.** Classify and report Harden candidates (and un-graduation proposals) under Recommended with full detail — gate type, draft artifact, evidence, the `--gate-ref` that would be recorded — but write no artifact and demote no entry.
- **Mark ambiguous as stale.** When classification is genuinely ambiguous (Update vs Replace vs Consolidate vs Delete) or Replace evidence is insufficient, run `flowctl memory mark-stale <id> --reason "..."` instead of guessing. Stale-marking writes are atomic and round-trip safe.
- **Conservative confidence.** Borderline cases get marked stale; never deleted on autofix.
- **Always print the full report.** The report is the sole deliverable — there is no user to ask follow-ups.

## Interaction Principles (interactive mode only)

In autofix mode, skip user questions entirely and apply the rules above.

In interactive mode, follow these principles:

- Ask via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Fall back to numbered options in plain text only if the tool is unreachable or errors. Never silently skip the question.
- Prefer **multiple choice** when natural options exist.
- Lead with the **recommended option** and a one-sentence rationale.
- Do **not** ask the user to make decisions before evidence is gathered — Phase 1 investigates first, Phase 3 asks.
- Group obvious Keeps and obvious Updates together for batched confirmation. Present Consolidate / Replace / Delete one at a time.

The goal is automated maintenance with human oversight on judgment calls — not a question for every finding.

## Forbidden

- **Auditing legacy flat files** (`.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md` at the memory root). Skip with a warning that recommends `/flow-next:memory-migrate` first. Report includes the skipped count.
- **Auditing under `_audit/`, `_review/`, or any other `_*` directory** under `.flow/memory/`.
- **Deleting silently.** Delete is reserved for unambiguous cases (code gone AND problem domain gone). Default to Replace or Consolidate when there's still value to preserve.
- **`git rm` on superseded decision entries.** Decision history stays on disk. Replace for `knowledge/decisions/` entries means write a new entry and mark the old `decision_status: superseded` with `superseded_by: <new-id>` — never delete the old file.
- **Deleting glossary terms.** When a term has zero code hits, mark stale via Edit-tool HTML comment. Removing the term entry is the operator's call, surfaced in the report.
- **Auto-applying Harden.** In `mode:autofix` (and therefore any `flow --auto` invocation) Harden **never applies**: no gate artifact is written, no entry is demoted, no un-graduation is executed. Candidates surface under Recommended only. Graduation edits files outside `.flow/memory/` — lint config, CI, CLAUDE.md — and silent edits to shared repo infrastructure from an autonomous sweep are unacceptable. Audit proposes; a human accepts.
- **Demoting a lesson to a gate that was never verified to fire.** `memory mark-hardened` runs only after the gate is confirmed live (resolved lint config / a job that actually runs / the substantive instruction file). Verification failure leaves the entry `active` and reports a failed graduation. A gate that does not fire is worse than no gate.
- **`git rm` on Harden.** Ever, on any track. The entry file stays on disk as a pointer at the gate — that is what keeps "why does this rule exist?" answerable.
- **Scaffolding infrastructure to host a gate.** Never create a linter setup, a CI pipeline, or a config file that does not already exist. The gate lands in a lint or CI surface the repo already has; otherwise the entry stays `active` and the code-level fix is recommended through flow's repeated-mistake route.
- **Inventing flowctl subcommands** beyond what ships (`memory mark-stale`, `memory mark-fresh`, `memory mark-hardened`, `memory search --status`). There is no `flowctl gate` subcommand — the gate artifact is skill-authored prose/config written via Edit/Write. flowctl ships only `glossary {add,list,read,remove}` — there is no `flowctl glossary mark-stale`; use Edit tool. Use `memory apply --plan <file> --json` for memory moves, removals and reference rewrites.
- **Mass-renaming code from a glossary alias-creep finding.** The audit reports file:line locations and stops there; code rename is the operator's call.
- **Auto-committing without user awareness in interactive mode.** Phase 5 detects git context and asks. Autofix uses sensible defaults.
- **Setting `context: fork`** — blocking-question tools must stay reachable.
- **Running parallel replacement subagents.** Investigation subagents can run in parallel for 3+ independent entries; replacement subagents run sequentially to protect orchestrator context.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

Discover & Triage (0), Glossary scan (0.5), Change-detection pre-filter (0.75), Investigate (1),
Cross-doc analysis (1.75), Classify (2), Ask (3, interactive only), Execute (4), Report + Commit (5),
Discoverability check (6).

## Output rules

The full report is the deliverable — print it as markdown to stdout. Do not summarize internally and emit a one-liner.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

Report structure and schema: [workflow.md](workflow.md) §5.

Then per-entry detail (id, classification, evidence, action taken). For Consolidate: which entry was canonical, what unique content was merged, what was deleted. For Replace: what the old entry recommended vs what current code does, path to successor (decision Replace also notes the old entry now carries `decision_status: superseded`). For Marked stale: why ambiguous. For Harden: gate type, artifact path, `--gate-ref`, and how the gate was verified live (a failed graduation names the reason and states the entry was left active). For glossary terms: only stale + alias-creep cases get per-term lines (Keep is silent); husks get a one-line advisory each.

Autofix mode splits actions into **Applied** (writes succeeded) and **Recommended** (writes failed — e.g. permission denied — plus every Harden candidate, which autofix never attempts). The structure is the same; only the bucket differs.
