# /flow-next:audit — agent-native memory staleness review

## Overview

Memory entries decay. A `.flow/memory/bug/runtime-errors/` entry logged six months ago might reference a file that's been renamed, a function that's been deleted, or a codepath that's been replaced. Without periodic review, the memory store accumulates zombie entries and `memory-scout` surfaces outdated advice.

`/flow-next:audit` is a **skill** — the host agent (Claude Code / Codex / Droid) walks `.flow/memory/`, reads each entry, uses Read/Grep/Glob to verify references against the current codebase, applies engineering judgment, and decides per entry whether to Keep / Update / Consolidate / Replace / Delete. Optional autofix mode applies unambiguous actions and marks ambiguous as stale.

The audit IS the agent. There's no Python audit-engine, no LLM-via-subprocess dispatch, no deterministic scorer with regex/stoplist — the host agent is already an LLM and does the work directly. flowctl provides only the persistence plumbing: mark-stale / mark-fresh helpers, search filter, schema extension.

This epic is a **minor bump (0.36.0 → 0.37.0)** — new skill, new slash command, two new flowctl subcommands, new flag on `memory search`, additive frontmatter fields.

## Architecture (agent-native)

```
User: /flow-next:audit                 (or /flow-next:audit mode:autofix [scope hint])
         │
         ▼
    Skill workflow runs in host agent
         │  (no subprocess dispatch — agent is the intelligence)
         │
         ├─ Phase 0: Discover & Triage
         │     walk .flow/memory/, group by track/category/module,
         │     find impact clusters
         │
         ├─ Phase 1: Investigate (per entry, via Read + Grep + Glob)
         │     parallel Agent dispatch for 3+ independent entries
         │
         ├─ Phase 1.75: Cross-doc analysis (overlap, supersession, conflicts)
         │
         ├─ Phase 2: Classify (Keep | Update | Consolidate | Replace | Delete)
         │
         ├─ Phase 3: Ask (interactive) | skip (autofix)
         │
         ├─ Phase 4: Execute
         │     Update → agent edits frontmatter via Write tool +
         │              flowctl memory mark-stale/mark-fresh helpers
         │     Consolidate → agent merges + deletes subsumed file
         │     Replace → agent writes successor + deletes old
         │     Delete → agent removes file
         │
         ├─ Phase 5: Report + Commit
         │
         └─ Phase 6: Discoverability check (CLAUDE.md / AGENTS.md surfaces .flow/memory/)
```

**flowctl plumbing (thin):**
- `flowctl memory mark-stale <id> --reason "..." [--audited-by "..."]` — sets `status: stale`, stamps `last_audited`, records `audit_notes`
- `flowctl memory mark-fresh <id>` — clears stale flag, stamps `last_audited`
- `flowctl memory search --status active|stale|all` — filter patch (default `active`)
- Schema extension: `MEMORY_OPTIONAL_FIELDS` += `last_audited`, `audit_notes`

That's it. No reference extractor, no resolver chain, no scorer, no codex/copilot dispatch.

## Mode detection

Skill checks `$ARGUMENTS` for `mode:autofix`:
- **Interactive** (default) — agent asks decisions via `AskUserQuestion` (Claude) / `request_user_input` (Codex) / `ask_user` (Droid). Falls back to numbered options in plain text if blocking-question tool unavailable.
- **Autofix** (`mode:autofix` token in arguments) — no questions; apply unambiguous actions, mark ambiguous as stale, print full report. This is the **Ralph-safe path** — autonomous loops can invoke autofix mode without human-in-the-loop questions.

Scope hint can follow the mode token: `/flow-next:audit mode:autofix runtime-errors` or `/flow-next:audit auth`.

## The 5 outcomes (lifted from upstream, adapted to memory schema)

| Outcome | Meaning | Default action |
|---------|---------|----------------|
| **Keep** | Still accurate and useful | No edit; report reviewed-without-change |
| **Update** | Solution still correct, references drifted | Agent edits in place via Write tool |
| **Consolidate** | Two entries overlap heavily, both correct | Merge unique content, delete subsumed entry |
| **Replace** | Old entry now misleading, successor exists | Write replacement entry, delete old |
| **Delete** | Code gone AND problem domain gone | `git rm` the file (preferred over stale-flag for truly obsolete) |

For **autofix mode** ambiguity: mark as stale via `flowctl memory mark-stale` instead of guessing.

## Legacy entries

Pre-fn-30 flat files (`.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md`) are skipped with a warning in the report:

```
Skipped 12 legacy entries — run `flowctl memory migrate` first to make these auditable.
```

Auditing legacy entries is half-broken (no frontmatter to write `status: stale` to, no track/category for scoping). The skill prints the count + skip reason and continues with categorized entries.

## Subagent dispatch

For batch sizes ≥3 independent entries, the orchestrator skill spawns parallel subagents using the host platform primitive:
- Claude Code: `Agent` with `subagent_type: Explore`
- Codex: `spawn_agent` with `agent_type: explorer`
- Droid: equivalent

Each investigation subagent is **read-only** — returns evidence + recommendation + confidence. Orchestrator merges results, asks questions on ambiguous cases (interactive) or marks stale (autofix), executes deletes/edits centrally. Replacement subagents (when Replace is chosen) run **sequentially**, one at a time, to protect context.

Each subagent receives the instruction to use Glob/Grep/Read tools (not shell commands) for investigation — avoids permission prompts.

## Discoverability check

After the audit completes, agent verifies CLAUDE.md / AGENTS.md (whichever holds substantive content; the other may be a `@`-include shim) mentions `.flow/memory/` in a way that future agents would find: knowledge store exists, schema basics (track / category / module / tags / status), when to consult. Adds a one-line mention if missing. Interactive: agent asks via blocking question. Autofix: includes as "Discoverability recommendation" in report.

## Acceptance criteria

- **R1:** Skill exists at `plugins/flow-next/skills/flow-next-audit/` with `SKILL.md`, `workflow.md`, `phases.md`. SKILL.md has the standard frontmatter (`name`, `description`) plus mode-detection logic.
- **R2:** Slash command `/flow-next:audit` registered at `plugins/flow-next/commands/flow-next/audit.md` (mirrors prospect/resolve-pr command shape — minimal pass-through to skill).
- **R3:** Workflow documents Phase 0 (Discover/Triage), Phase 1 (Investigate per entry, with parallel subagent dispatch for 3+ entries), Phase 1.75 (Cross-doc — overlap/supersession/conflicts), Phase 2 (Classify), Phase 3 (Ask interactive or skip autofix), Phase 4 (Execute), Phase 5 (Report + Commit), Phase 6 (Discoverability check).
- **R4:** 5 outcomes (Keep / Update / Consolidate / Replace / Delete) with decision criteria documented; mode-specific behavior (interactive asks, autofix decides + marks ambiguous as stale).
- **R5:** Skill explicitly skips legacy flat files (`pitfalls.md`, `conventions.md`, `decisions.md`) with a warning that recommends `flowctl memory migrate` first. Report includes skipped count.
- **R6:** Subagent dispatch documented with cross-platform primitives (Claude `Agent` / Codex `spawn_agent` / Droid equivalent). Read-only investigation subagents return evidence; orchestrator merges + executes.
- **R7:** `flowctl memory mark-stale <id> --reason "..." [--audited-by "..."]` subcommand added. Sets `status: stale`, stamps `last_audited` (today's date), records `audit_notes` from `--reason`. Atomic via existing `write_memory_entry`. Returns JSON when `--json` passed.
- **R8:** `flowctl memory mark-fresh <id>` subcommand added. Clears `status` (back to `active`), clears `audit_notes`, stamps `last_audited`. JSON support.
- **R9:** `cmd_memory_search` patched to accept `--status active|stale|all` (default `active`), mirroring `cmd_memory_list:5658-5778`. Stale entries excluded from default search results.
- **R10:** `MEMORY_OPTIONAL_FIELDS` extended with `last_audited`, `audit_notes`. `MEMORY_FIELD_ORDER` updated. `_MEMORY_QUOTED_STRING_FIELDS` extended for `last_audited` (date string). Validator picks up additions automatically via union.
- **R11:** Discoverability check runs at end of audit; verifies CLAUDE.md/AGENTS.md substantive file mentions `.flow/memory/` with schema basics; adds line if missing. Asks user for consent (interactive) or includes as recommendation (autofix).
- **R12:** Smoke test `plugins/flow-next/scripts/audit_smoke_test.sh` covers flowctl plumbing only (skills aren't unit-testable):
  - `mark-stale <id> --reason "x"` → entry has `status: stale`, `last_audited`, `audit_notes`
  - `mark-fresh <id>` after stale → entry has `status` cleared, `audit_notes` cleared, `last_audited` stamped
  - `memory list --status stale` surfaces stale-flagged entry
  - `memory search <q> --status stale` surfaces stale-flagged entry
  - `memory search <q>` (no flag) excludes stale entries (default `active`)
  - `memory search <q> --status all` includes both
  - Schema validation accepts `last_audited` + `audit_notes` without error
  - Idempotent re-mark-stale (mark twice → second is no-op or updates `last_audited`)
- **R13:** Ralph regression: skill in interactive mode blocks naturally under `FLOW_RALPH=1` (host agent can't answer `AskUserQuestion`). Autofix mode runs through. No flowctl-side Ralph-block needed (skill handles it). Smoke verifies `flowctl memory mark-stale` / `mark-fresh` / `search --status` all work cleanly under `FLOW_RALPH=1` (they're pure plumbing, no Ralph gate).
- **R14:** Docs: `CHANGELOG.md` 0.37.0 entry; `plugins/flow-next/README.md` adds skill entry + memory subcommand updates (`mark-stale`, `mark-fresh`, `search --status`); `CLAUDE.md` memory-system block adds audit bullet pointing at `/flow-next:audit` skill + `mark-stale/mark-fresh` helpers + `search --status` flag; `.flow/usage.md` mentions audit if relevant.
- **R15:** Website: `~/work/mickel.tech/app/apps/flow-next/page.tsx` memory feature card description appended with one-line audit lifecycle ("`/flow-next:audit` reviews entries against current code; agent decides Keep/Update/Consolidate/Replace/Delete; never deletes silently — autofix marks ambiguous as stale").
- **R16:** `scripts/sync-codex.sh` regenerates `plugins/flow-next/codex/` to mirror new skill + slash command + agents. Codex commands use `$flow-next-audit` prefix.
- **R17:** `scripts/bump.sh minor flow-next` lands version bump 0.36.0 → 0.37.0 across `.claude-plugin/`, `.codex-plugin/`, marketplace.json.

## Early proof point

Task fn-34.1 ships the skill files. Validates the workflow shape against upstream's `ce-compound-refresh` (we have a known-working reference). If the skill phases don't compose cleanly with the existing fn-30 memory schema (`status: active|stale`, frontmatter fields, track/category structure), revisit before fn-34.2 (flowctl plumbing).

## Risks

| Risk | Mitigation |
|------|------------|
| Skill workflow conflicts with existing memory schema | Cross-check against fn-30's `MEMORY_OPTIONAL_FIELDS`, `validate_memory_frontmatter`, `_memory_iter_entries` during fn-34.1 |
| Legacy flat-file entries unexpectedly audited and break (no frontmatter) | Skip-with-warning behavior baked into skill workflow (R5) |
| Subagent dispatch differs across host platforms | Document Claude `Agent` + Codex `spawn_agent` + Droid equivalent explicitly in workflow.md (R6) |
| Autofix mode silently destroys curated entries | Replace requires "sufficient evidence"; ambiguous cases get marked stale (not deleted); Delete reserved for "code gone AND problem domain gone" |
| `mark-stale` / `mark-fresh` race with manual edits | flowctl writes are atomic via existing `write_memory_entry`; if the entry was edited between read and write, the next audit will pick up the new content via the standard re-read |
| Discoverability edits churn CLAUDE.md/AGENTS.md unnecessarily | Skill checks if mention exists semantically, not via string match; skips when spirit already met (R11) |

## Boundaries

- **Not** building a Python audit engine. The agent reads + judges directly.
- **Not** dispatching codex/copilot via subprocess. Host agent is the intelligence.
- **Not** auditing legacy flat files. Skip with warning; user runs `memory migrate` first.
- **Not** auto-committing without user awareness. Skill commits in Phase 5 with descriptive message; interactive mode confirms; autofix uses sensible branch defaults (per upstream `ce-compound-refresh` Phase 5 logic).
- **Not** deleting silently. Delete reserved for unambiguous cases (code gone + problem domain gone). Default to Replace or Consolidate when there's still value to preserve.

## Decision context

**Why skill-based, not flowctl Python subcommand?** This plugin always runs inside an agentic environment (Claude Code / Codex / Droid). The host agent can read files, run grep, judge relevance, and write updates directly using its own tools. Spawning a second LLM via codex/copilot subprocess is wasteful (cost + latency) and adds machinery (subprocess timeouts, structured-verdict parsers, drift guards) that disappears in the agent-native architecture. Upstream's `ce-compound-refresh` skill is a working reference for this pattern.

**Why thin flowctl plumbing instead of skill-only?** The skill needs deterministic operations for atomic frontmatter writes (`mark-stale` / `mark-fresh`), schema-validated round-trip, and consistent search filtering. Those are pure persistence concerns where flowctl's existing helpers shine. The split is: flowctl owns "set this field on this entry"; skill owns "should this entry be flagged."

**Why `cmd_memory_search --status` patch in this epic?** Audit's value prop is "flag stale → it stops polluting future scout output." `memory-scout` uses search internally. If search keeps surfacing stale hits after audit flags them, audit accomplishes nothing observable. ~10 LoC mirroring `cmd_memory_list`.

**Why minor 0.37.0 not patch?** New skill + new slash command + two new flowctl subcommands + new flag on existing subcommand + additive frontmatter fields = user-visible surface change. Semver: minor.

**Why no `--allow-ralph` flag?** Original spec needed it because the audit was a flowctl Python subcommand that could be invoked headlessly. The skill version is invoked via slash command — Ralph mode either runs the skill in autofix mode (which works fine, no human-in-the-loop), or doesn't run it. The `mode:autofix` argument IS the Ralph-safe gate. Simpler.

## Follow-ups (not in this epic)

- **fn-35 candidate: Convert `flowctl memory migrate` from subprocess-dispatch to skill-based.** Same architectural critique applies — migrate runs inside an agentic environment, doesn't need to spawn codex/copilot via subprocess. Refactor: new `/flow-next:memory-migrate` skill (host agent classifies legacy entries), keep `flowctl memory migrate --no-llm` as headless mechanical fallback for CI/scripts.
- Cross-track staleness correlation (bug entry referring to code that knowledge entry also references — flag both)
- Integration with `/flow-next:prospect` (surface stale memory as ideation input)
- Scheduled weekly audit via `/schedule` background agent template — autofix mode is the natural fit
- `_audit/` report archive (if we decide reports are valuable to keep — currently the report is printed, not persisted)

## Tasks

Three tasks. Each fits one `/flow-next:work` iteration.

1. fn-34.1 — Skill files + slash command (`flow-next-audit/SKILL.md`, `workflow.md`, `phases.md` + `commands/flow-next/audit.md`)
2. fn-34.2 — flowctl plumbing (`mark-stale`, `mark-fresh`, `search --status` patch, schema extension)
3. fn-34.3 — Smoke test + docs + website + codex mirror + version bump

## Requirement coverage

| Req | Description | Task(s) |
|-----|-------------|---------|
| R1, R2 | Skill files + slash command exist | fn-34.1 |
| R3, R4 | Workflow phases + 5 outcomes documented | fn-34.1 |
| R5 | Legacy entry skip-with-warning | fn-34.1 |
| R6 | Subagent dispatch (cross-platform) | fn-34.1 |
| R7, R8 | `mark-stale` / `mark-fresh` flowctl subcommands | fn-34.2 |
| R9 | `memory search --status` patch | fn-34.2 |
| R10 | Schema extension | fn-34.2 |
| R11 | Discoverability check (skill phase) | fn-34.1 |
| R12 | Smoke test (flowctl plumbing) | fn-34.3 |
| R13 | Ralph regression | fn-34.3 |
| R14 | Docs (CHANGELOG, README, CLAUDE.md, .flow/usage.md) | fn-34.3 |
| R15 | Website | fn-34.3 |
| R16 | Codex mirror sync | fn-34.3 |
| R17 | Version bump 0.37.0 | fn-34.3 |
