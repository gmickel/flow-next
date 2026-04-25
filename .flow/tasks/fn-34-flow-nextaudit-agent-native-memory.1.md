---
satisfies: [R1, R2, R3, R4, R5, R6, R11]
---

## Description

Create the `/flow-next:audit` skill — markdown files that describe the workflow the host agent (Claude Code / Codex / Droid) executes when the user invokes the slash command. No code, no executable logic — just instructions the agent reads and follows.

This is the **Phase-0 task**: lays down the skill structure and workflow. Tasks 2 and 3 build the flowctl plumbing the skill calls and the surrounding rollup.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` (new — metadata + mode detection + interaction principles)
- `plugins/flow-next/skills/flow-next-audit/workflow.md` (new — phases 0–6)
- `plugins/flow-next/skills/flow-next-audit/phases.md` (new — 5 outcomes + decision criteria)
- `plugins/flow-next/commands/flow-next/audit.md` (new — slash command pass-through)

## Approach

### `SKILL.md` shape

Mirror `plugins/flow-next/skills/flow-next-prospect/SKILL.md` (most recent reference of an interactive skill) for structure. Frontmatter required fields: `name: flow-next-audit`, `description: <one paragraph triggering this skill on phrases like "audit memory", "review memory", "refresh learnings", "/flow-next:audit">`. 

Body sections:
1. **Mode Detection** — parse `$ARGUMENTS` for `mode:autofix` token. Strip and use remainder as scope hint. Same pattern as upstream `ce-compound-refresh:10-27`.
2. **Interaction Principles** — interactive uses blocking-question tool (`AskUserQuestion` Claude / `request_user_input` Codex / `ask_user` Droid); fallback to numbered options when tool unavailable; one question at a time; lead with recommendation.
3. **Reference to workflow.md** — main loop lives there.
4. **Reference to phases.md** — outcomes lookup.
5. **Output rules** — print full report as final deliverable.

### `workflow.md` shape

Document the 6 phases. Each phase ends with a "Done when" criterion so the agent knows to advance.

**Phase 0 — Discover & Triage**
- Walk `.flow/memory/` via Glob: `bug/**/*.md` + `knowledge/**/*.md`
- Skip legacy flat files (`pitfalls.md`, `conventions.md`, `decisions.md` at memory root) — count and report at end ("Skipped 12 legacy entries — run `flowctl memory migrate` first to make these auditable")
- Skip `_audit/`, `_review/`, any other `_*` directories
- Group entries by `module` field, then by `category`
- For 9+ entries: triage first — identify highest-impact cluster (most entries + most cross-references). Recommend starting area; ask in interactive, process all in autofix.
- For 1-8 entries: investigate directly.

**Phase 1 — Investigate (per entry)**
- Read entry frontmatter + body
- For each referenced file/symbol/module:
  - Read the file (if it exists) to verify the claim still holds
  - If file missing: `Glob` for renames (`**/<basename>`), `Grep` for symbols
  - Check git log for recent changes in the area (`git log --oneline -10 -- <path>`)
- Form recommendation per entry: Keep / Update / Consolidate / Replace / Delete + 2-4 evidence bullets + confidence (low/medium/high)
- For 3+ independent entries: dispatch parallel investigation subagents (see Subagent Strategy below)

**Phase 1.75 — Cross-doc analysis**
- Compare entries that share `module` or `category` for overlap (problem, solution, root cause, files)
- Detect supersession: newer canonical entry covers older narrower precursor
- Detect outright contradictions (entry A says use X, entry B says avoid X)
- Mark candidates for Consolidate / Replace based on cross-comparison

**Phase 2 — Classify**
- Apply phases.md decision criteria
- For Replace: check if evidence is sufficient (current code investigation provides enough to write successor) — if not, mark stale instead

**Phase 3 — Ask** (interactive only; autofix skips)
- Group obvious Keeps + obvious Updates → confirm batch
- Present Consolidate / Replace individually
- Present unambiguous Deletes individually unless auto-delete criteria met (code gone AND problem domain gone)
- Use blocking-question tool; one question at a time; lead with recommendation
- Autofix mode: mark ambiguous as stale via `flowctl memory mark-stale`

**Phase 4 — Execute**
- Keep: no edit, just report
- Update: agent edits frontmatter and/or body via Write tool (frontmatter must round-trip — preserve unknown fields)
- Consolidate: merge unique content into canonical; `git rm` subsumed entry
- Replace: write new entry; `git rm` old
- Delete: `git rm` (only when code AND problem domain both gone)
- For ambiguous in autofix: `flowctl memory mark-stale <id> --reason "..."`

**Phase 5 — Report + Commit**
- Print summary (Kept N, Updated N, Consolidated N, Replaced N, Deleted N, Marked stale N, Skipped N)
- Print per-entry detail (file path, classification, evidence, action taken)
- Detect git context (branch, dirty tree)
- Interactive: ask "commit options" (current branch / new branch + PR / don't commit)
- Autofix on main: create branch + commit + try PR; on feature branch: commit; staged files = only audit-modified entries
- Commit message: descriptive ("audit: update 3 entries, consolidate 2 overlapping, mark 1 stale")

**Phase 6 — Discoverability check**
- Identify CLAUDE.md / AGENTS.md substantive file (the one not just `@`-including the other)
- Semantic check: does it mention `.flow/memory/` with schema basics (track / category / module / tags / status) and when to consult?
- If missing: draft minimal addition matching file's tone; ask consent (interactive) or include as recommendation (autofix)
- If consent given + already committed in Phase 5: amend or follow-up commit, push if remote exists

### `phases.md` shape

The 5 outcomes lookup. Each section: meaning + when to use + when NOT to use + action steps + edge cases. Lift heavily from upstream `ce-compound-refresh:285-372` with naming swap (`learning` → `memory entry`, `docs/solutions/` → `.flow/memory/`).

Specific calibration for memory schema:
- **Update**: edit frontmatter `module` field, edit body code refs, fix related-doc paths. Preserve all other frontmatter (`title`, `date`, `track`, `category`, `tags`, etc).
- **Consolidate**: merge by combining `tags` arrays (dedupe), keeping the canonical entry's `module`, appending unique body content. Then `git rm` subsumed file.
- **Replace**: write new entry with same `track` and `category` (unless category itself drifted — agent decides). Use `flowctl memory add --track ... --category ... --title ... --body-file ...` if convenient, OR write the file directly with proper frontmatter.
- **Delete**: only when code gone AND problem domain gone. If problem persists under new implementation → Replace, not Delete.

### `commands/flow-next/audit.md`

Minimal slash-command pass-through. Mirror `commands/flow-next/prospect.md` shape. Just invokes the skill with `$ARGUMENTS`.

### Subagent Strategy (in workflow.md)

Cross-platform dispatch table:
- **Claude Code**: `Agent` tool with `subagent_type: Explore` (read-only investigation) or `general-purpose` (when needed)
- **Codex**: `spawn_agent` with `agent_type: explorer` per Codex docs
- **Droid**: equivalent (verify exact name in Droid docs at implementation time)
- **Fallback**: main thread investigation when subagent primitive unavailable

Investigation subagents are **read-only** (no Edit/Write/Bash), return structured evidence. Replacement subagents (when Replace chosen) run **sequentially** to protect orchestrator context.

## Investigation targets

**Required:**
- `/tmp/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound-refresh/SKILL.md` — upstream reference (the working pattern we're adapting)
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` — most recent in-repo skill reference for shape (prospect ships frontmatter, mode handling, blocking-question tool call)
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` — workflow.md shape reference
- `plugins/flow-next/commands/flow-next/prospect.md` — slash command pass-through pattern
- `plugins/flow-next/scripts/flowctl.py:3657-3741` — memory schema constants (so phase docs reference correct field names)
- `plugins/flow-next/scripts/flowctl.py:5350-5412` — `_memory_iter_entries` (entry walker the skill conceptually mirrors)
- CLAUDE.md memory-system block at lines 62-77 (schema reference)

**Optional:**
- `/tmp/compound-engineering-plugin/plugins/compound-engineering/skills/ce-compound-refresh/references/` — extra references upstream uses (for inspiration only; we don't need separate references file unless workflow gets complex)

## Key context

- Skill files are markdown — no Python, no shell, no testing. The "test" is invoking the skill in a real session.
- Mode detection MUST live in SKILL.md so the host agent finds it on first read. Don't bury in workflow.md.
- The slash command file (`commands/flow-next/audit.md`) is just the trigger — the actual workflow lives in `skills/flow-next-audit/`.
- Don't invent new `flowctl memory` subcommands beyond what Task 2 will provide (`mark-stale`, `mark-fresh`, `search --status`). Skill writes via Write tool + git commands for delete/move.
- For frontmatter round-trip when agent edits an entry: agent must preserve unknown fields (someone else's metadata). Read full frontmatter, mutate the specific field, write back. Easier path: invoke `flowctl memory mark-stale` for stale-flagging (that helper handles round-trip correctly via existing `write_memory_entry`).
- Subagent dispatch is platform-specific. Document all three; let the host agent pick the one that exists in its harness.
- Discoverability check should be cheap when nothing's needed (semantic match on existing content) and minimal when something's added (one-line addition to an existing section, not a new section unless absolutely required).

## Acceptance

- [ ] `plugins/flow-next/skills/flow-next-audit/SKILL.md` exists with valid frontmatter (`name`, `description`), mode detection logic for `mode:autofix`, interaction principles, references to workflow.md + phases.md.
- [ ] `plugins/flow-next/skills/flow-next-audit/workflow.md` documents Phases 0–6 with "Done when" criteria per phase.
- [ ] `plugins/flow-next/skills/flow-next-audit/phases.md` documents the 5 outcomes (Keep / Update / Consolidate / Replace / Delete) with memory-schema-specific calibration.
- [ ] `plugins/flow-next/commands/flow-next/audit.md` exists, invokes the skill with `$ARGUMENTS`, mirrors prospect command shape.
- [ ] Skill explicitly skips legacy flat files in Phase 0; report includes skipped count.
- [ ] Subagent dispatch documented for Claude (`Agent` + `Explore`/`general-purpose`), Codex (`spawn_agent` + `explorer`), Droid (equivalent or fallback note).
- [ ] Discoverability check (Phase 6) verifies CLAUDE.md/AGENTS.md substantive file mentions `.flow/memory/` semantically.
- [ ] Skill references the flowctl helpers Task 2 will add (`flowctl memory mark-stale`, `mark-fresh`, `search --status`) — even though those don't exist yet, the references are forward-looking. Task 2 must implement them to match.
- [ ] Cross-check: invoking `/flow-next:audit` in a real session produces the expected workflow shape (no actual audit run needed — just verifying the skill loads and starts Phase 0).
- [ ] No code in the skill files. Markdown only. No Python, no bash beyond illustrative snippets in workflow descriptions.


## Done summary
Created /flow-next:audit skill (markdown-only, agent-native): SKILL.md with mode detection + interaction principles, workflow.md covering phases 0-6 with Done-when criteria and cross-platform subagent dispatch, phases.md with the 5-outcomes lookup, plus a minimal slash-command pass-through. Forward-references flowctl helpers Task 2 will land.
## Evidence
- Commits: f9eacd9c431b181b35ee2f459ff51c02a002f3c5
- Tests: jq legacy entry count smoke check via flowctl memory list --json (2 entries surfaced from synthetic pitfalls.md)
- PRs: