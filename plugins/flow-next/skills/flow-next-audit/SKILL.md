---
name: flow-next-audit
description: Audit `.flow/memory/` entries against the current codebase and decide Keep / Update / Consolidate / Replace / Delete / Harden per entry. Triggers on /flow-next:audit, "audit memory", "review memory", "refresh learnings", "sweep stale memory", "consolidate overlapping memory entries", "graduate a recurring lesson into a gate". Optional `mode:autofix` token in arguments runs without questions and marks ambiguous as stale (Harden is never auto-applied). Optional scope hint after the mode token (concept, category, module, or path) narrows what gets audited.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:audit — agent-native memory staleness review

Memory entries decay. A `.flow/memory/bug/runtime-errors/` entry logged six months ago might reference a renamed file, a deleted function, or a codepath that no longer exists. Without periodic review, the store accumulates zombie entries and `memory-scout` surfaces outdated advice.

This skill IS the audit. The host agent (Claude Code / Codex / Droid) walks `.flow/memory/`, reads each entry, uses Read/Grep/Glob/git to verify references against the current codebase, applies engineering judgment, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete / Harden**. Optional autofix mode applies unambiguous actions and marks ambiguous as stale.

**Harden** is the graduation path: a lesson that keeps getting re-learned and states a mechanically checkable rule should stop riding the context window and become a gate. The audit proposes an artifact in a surface the repo already has — a lint rule, a CI step, or a rule in the substantive CLAUDE.md / AGENTS.md — verifies the gate actually fires, and only then demotes the entry to a pointer at it (file stays on disk, provenance intact). Propose-and-confirm by design: gate surfaces are shared repo infrastructure, so Harden never applies unattended.

Decision entries (`.flow/memory/knowledge/decisions/`) and glossary terms (`GLOSSARY.md` files at the repo root and on the ancestor chain) are walked alongside the rest of memory. Decisions get a calibrated judging question — "does the constraint that motivated this choice still hold?" — and Replace becomes a two-step supersession (write successor, mark old `decision_status: superseded`, never `git rm`). Glossary terms are scanned for code usage; zero-hit terms get a `<!-- stale: ... -->` HTML comment via Edit tool (no `flowctl glossary mark-stale` exists), `_Avoid_` aliases appearing in code surface as alias-creep findings.

There is no Python audit-engine, no codex/copilot subprocess dispatch, no deterministic scorer. The host agent is already an LLM and does the work directly. flowctl provides only thin persistence plumbing (`memory mark-stale`, `memory mark-fresh`, `memory mark-hardened`, `memory search --status`). All judgment — is this recurring, is it mechanizable, which gate surface, what should the rule say — stays in this skill; there is no `flowctl gate` subcommand and never will be.

**Read [workflow.md](workflow.md) for the full phase-by-phase execution. Read [phases.md](phases.md) for the 6-outcomes lookup with memory-schema-specific calibration.**

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** — `AskUserQuestion` must stay reachable across phases. Subagents can't call blocking question tools (Claude Code issues #12890, #34592). Phase 3 (Ask) and Phase 6 (Discoverability check) both require user choice in interactive mode. (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.)

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
- **Never apply Harden.** Classify and report Harden candidates (and un-graduation proposals) under Recommended with full detail — gate type, draft artifact, evidence, the `--gate-ref` that would be recorded — but write no artifact and demote no entry.
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
- **`git rm` on superseded decision entries.** Decision history stays on disk. Replace for `knowledge/decisions/` entries means write a new entry and mark the old `decision_status: superseded` with `superseded_by: <new-id>` — never delete the old file.
- **Deleting glossary terms.** When a term has zero code hits, mark stale via Edit-tool HTML comment. Removing the term entry is the operator's call, surfaced in the report.
- **Auto-applying Harden.** In `mode:autofix` (and therefore any pilot / Ralph invocation) Harden **never applies**: no gate artifact is written, no entry is demoted, no un-graduation is executed. Candidates surface under Recommended only. Graduation edits files outside `.flow/memory/` — lint config, CI, CLAUDE.md — and silent edits to shared repo infrastructure from an autonomous sweep are unacceptable. Audit proposes; a human accepts.
- **Demoting a lesson to a gate that was never verified to fire.** `memory mark-hardened` runs only after the gate is confirmed live (resolved lint config / a job that actually runs / the substantive instruction file). Verification failure leaves the entry `active` and reports a failed graduation. A gate that does not fire is worse than no gate.
- **`git rm` on Harden.** Ever, on any track. The entry file stays on disk as a pointer at the gate — that is what keeps "why does this rule exist?" answerable.
- **Scaffolding infrastructure to host a gate.** Never create a linter setup, a CI pipeline, or a config file that does not already exist. The gate lands in a surface the repo already has, degrades to the substantive instruction file, or the entry stays Keep.
- **Inventing flowctl subcommands** beyond what ships (`memory mark-stale`, `memory mark-fresh`, `memory mark-hardened`, `memory search --status`). There is no `flowctl gate` subcommand — the gate artifact is skill-authored prose/config written via Edit/Write. fn-38 task 2 ships only `glossary {add,list,read,remove}` — there is no `flowctl glossary mark-stale`; use Edit tool. Use Write tool + git for moves and deletes.
- **Mass-renaming code from a glossary alias-creep finding.** The audit reports file:line locations and stops there; code rename is the operator's call.
- **Auto-committing without user awareness in interactive mode.** Phase 5 detects git context and asks. Autofix uses sensible defaults.
- **Setting `context: fork`** — blocking-question tools must stay reachable.
- **Running parallel replacement subagents.** Investigation subagents can run in parallel for 3+ independent entries; replacement subagents run sequentially to protect orchestrator context.

## Workflow

Execute the phases in [workflow.md](workflow.md) in order:

0. **Discover & Triage** — walk `.flow/memory/{bug,knowledge}/<category>/`, group by module / category, count, choose interaction path (focused / batch / broad), skip legacy + `_*` directories with a counted warning. `knowledge/decisions/` entries are picked up automatically by the same glob.
0.5 **Glossary scan** — enumerate `GLOSSARY.md` files via `flowctl glossary list --json`; per term, grep tracked code for the term and each `_Avoid_` alias (case-insensitive whole-word, normalized whitespace); zero hits + zero alias hits → mark stale via Edit tool (HTML comment after the term heading); alias hits → surface as alias-creep finding for Phase 3 (interactive) or report (autofix); skip husk files (`count: 0`) with a single advisory.
0.75 **Change-detection pre-filter** — pre-scan recurrence artifacts (`## Update` heading count, entry-file commit count, `related_to` size) BEFORE the auto-Keep decision, so a recurrence-qualified entry reaches Phase 1 even when its module is unchanged; hardened entries get a cheap gate-liveness check instead of re-investigation.
1. **Investigate** — per entry: read frontmatter + body, verify referenced files / symbols / modules against current code via Read / Grep / Glob, check git log in the area, form Keep / Update / Consolidate / Replace / Delete / Harden recommendation with 2-4 evidence bullets and confidence. For 3+ independent entries, dispatch parallel investigation subagents (read-only). Decision entries use the calibrated judging question — "does the constraint still hold?" — see [phases.md](phases.md) §Decision-entry calibration.
1.75 **Cross-doc analysis** — compare entries sharing module / category for overlap (problem, solution, root cause, files), supersession (newer canonical entry covers older narrower precursor), contradictions.
2. **Classify** — apply [phases.md](phases.md) decision criteria and the outcome-precedence rule (correctness > Consolidate > Harden). For Replace, verify evidence is sufficient to write a trustworthy successor; mark stale otherwise. For decision entries, Replace = supersede (write new entry; mark old `decision_status: superseded`, `superseded_by: <new-id>`; never `git rm` the old). Harden requires a recurrence signal AND mechanizability, and passes the duplication guard first.
3. **Ask** — interactive only; autofix skips. Group obvious Keeps + Updates → confirm batch. Present Consolidate / Replace / non-auto-Delete individually. Present each Harden candidate individually with gate type, draft artifact, evidence bullets, and accept / different-gate-type / decline. Surface glossary alias-creep findings per alias. Lead with recommendation. One question at a time.
4. **Execute** — Keep: no edit. Update: agent edits frontmatter / body via Write tool, preserving unknown fields. Consolidate: merge unique content into canonical, `git rm` subsumed. Replace: write new entry, `git rm` old (decisions: write new + edit old's frontmatter to mark superseded, never `git rm`). Delete: `git rm` (only when code AND problem domain both gone). Harden: write the artifact, verify the gate fires, then `flowctl memory mark-hardened <id> --gate-ref "<path>#<rule-id> -- <note>"` — never `git rm`; verification failure leaves the entry active. Glossary stale: Edit comment after term heading. Ambiguous in autofix: `flowctl memory mark-stale`.
5. **Report + Commit** — print Kept / Updated / Consolidated / Replaced / Deleted / Hardened / Marked-stale / Skipped counts plus per-entry detail and a Glossary section (Kept / Marked stale / Alias-creep / Husks). Detect git context (current branch, dirty tree). Interactive: ask commit options. Autofix: branch-and-PR on main, commit on feature branch, stage only audit-modified files.
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
Hardened: H  (failed graduations: HF; un-graduated: HU)
Marked stale: S

Glossary
--------
Files scanned: F (H husks)
Terms scanned: T
Kept: K_g
Marked stale: S_g
Alias-creep flagged: A_g
```

Then per-entry detail (id, classification, evidence, action taken). For Consolidate: which entry was canonical, what unique content was merged, what was deleted. For Replace: what the old entry recommended vs what current code does, path to successor (decision Replace also notes the old entry now carries `decision_status: superseded`). For Marked stale: why ambiguous. For Harden: gate type, artifact path, `--gate-ref`, and how the gate was verified live (a failed graduation names the reason and states the entry was left active). For glossary terms: only stale + alias-creep cases get per-term lines (Keep is silent); husks get a one-line advisory each.

Autofix mode splits actions into **Applied** (writes succeeded) and **Recommended** (writes failed — e.g. permission denied — plus every Harden candidate, which autofix never attempts). The structure is the same; only the bucket differs.
