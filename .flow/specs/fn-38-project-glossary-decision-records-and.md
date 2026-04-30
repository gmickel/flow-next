## Overview

Three new artifacts (`GLOSSARY.md` at repo root, `knowledge/decisions/` memory category, doc-aware mode in `/flow-next:interview`) plus extensions to `docs-gap-scout`, `/flow-next:audit`, `/flow-next:sync`, and a terminology guard. Foundational schema + flowctl plumbing land first; interview integration depends on both; downstream extensions (scout / audit / sync) consume the new artifacts; docs and the R17 guard close the epic.

## Conversation Evidence

> user (turn 1, part 1): "Do you think this would be a good optional extension of our interview skill? Maybe with a flag or an option. Interview, you know, just interview, and then the user can either just write with docs or minus minus docs."
> user (turn 1, part 2): "We'd have to make it fit flow next. So none of his terminology improve on the skills, and then potentially our auditor skills or drift skills and doc scouts should take that into account if it exists as potential paths."
> user (turn 1, part 3): "We will not be mentioning the inspiration for this."
> user (turn 3): "we always need to follow the core tenet of 'the repo is state' and 'the repo is memory' -- the flow next memory is different"
> user (turn 4): "also tell me which DDD stuff you are removing, i think this is his ubiquitous language stuff"
> user (turn 6): "not sure about dropping the subdirectory GLOSSARY.md files, discuss"
> user (turn 7): "use /flow-next:flow-next:capture to capture this"

## Goal & Context

<!-- Source-tag breakdown: 60% [user] / 30% [paraphrase] / 10% [inferred] -->

Projects accumulate vocabulary that isn't standard CS jargon — terms with project-specific canonical meaning, mode names whose word is overloaded, role names that look ordinary but carry precise semantics. Without a canonical reference, agents reading the codebase have to infer meaning from usage, and the same word ends up meaning different things in different turns of the same conversation.

Separately, projects accumulate **decisions** — choices that are hard to reverse, surprising-without-context, and the result of real trade-offs. flow-next memory currently captures backward-looking learnings (`bug/*`, `knowledge/*`) but has no shape for forward-looking decisions with their rejected alternatives. Architecture-patterns is the closest neighbor but tracks "what we observed", not "what we picked and why".

This epic introduces a project glossary at the repo root and a decision-records memory category, then layers four behaviors on top of the existing interview skill that activate when either artifact is present. The glossary lives at the repo root because project knowledge belongs to the project — every agent that walks `CLAUDE.md` / `AGENTS.md` should also read it. Decisions live under `.flow/memory/knowledge/decisions/` because they have a flow-next-shaped lifecycle (status, supersession, audit).

## Architecture & Data Models

<!-- Source-tag breakdown: 50% [paraphrase] / 50% [inferred] -->

Three artifacts:

1. **`GLOSSARY.md` at repo root** — plain markdown, structured per-term sections. Term name (heading), one-line definition, optional `_Avoid_` aliases, optional relationships block. Subdirectory `GLOSSARY.md` files are supported via nearest-ancestor resolution: when working inside a subdirectory, the nearest-ancestor `GLOSSARY.md` applies; root applies otherwise. No meta-file equivalent — the filesystem already encodes structure. Format precedent: H2-per-term with paragraph definition (GitBook + glossarify-md convention).

2. **`knowledge/decisions/` memory category** — extends the categorized memory schema with one new knowledge category. Reuses the existing frontmatter (`title`, `date`, `track`, `category`, `module`, `tags`), plus optional decision-specific fields (`decision_status`: proposed | accepted | superseded; `superseded_by`; `alternatives_considered`). Body is a 1-3 sentence floor; `Considered Options` and `Consequences` sections are optional. Indexed by `memory-scout`, walked by `/flow-next:audit`, listed by `flowctl memory list/search/read`.

3. **Doc-aware mode in `/flow-next:interview`** — autodetects when `GLOSSARY.md` exists at the repo root OR `.flow/memory/knowledge/decisions/` has any entry. Off when neither is present. Forced on by `--docs` (creates `GLOSSARY.md` lazily on first resolved term); forced off by `--no-docs`.

When doc-aware mode is on, four behaviors layer onto the existing interview workflow:

- (a) **Phase-zero glossary scan** — read the nearest-ancestor `GLOSSARY.md`, find any term in the user's request that has a defined canonical entry; if the user's wording conflicts with the canonical term, surface the conflict as the first interview question.
- (b) **Fuzzy-term sharpening** — when the user uses overloaded language across the conversation, propose a canonical term, ask which is meant, append the resolved term to `GLOSSARY.md` via `flowctl glossary add`.
- (c) **Code/spec contradiction surfacing** — when grep reveals the code disagrees with a user assertion, surface the contradiction as a question rather than a silent codebase-resolved entry.
- (d) **Inline writes** — glossary append on every term resolution; decision entry written via `flowctl memory add --track knowledge --category decisions ...` only when the three-criteria gate passes. Decision writes follow the capture/audit pattern: agent shows draft via `AskUserQuestion` before writing.

Throttle for (a): only flag glossary conflicts when the term is load-bearing for the current spec. A casual passing mention of a defined word does not trigger; specifying behavior that depends on a precise meaning does.

## API Contracts

<!-- Source-tag breakdown: 30% [paraphrase] / 70% [inferred] -->

flowctl glossary subcommands (atomic writes; no judgment):

- `flowctl glossary add <term> --definition "..." [--avoid "a,b,c"] [--relates-to "..."]` — append or update a term entry. Writes to nearest-ancestor `GLOSSARY.md`; creates the file at repo root if no ancestor exists. Multi-line definitions accepted via `--definition-file -` (read from stdin) or `--definition-file <path>`.
- `flowctl glossary list [--json]` — emit all defined terms (term + definition + avoid aliases). When multiple `GLOSSARY.md` files exist, group by file.
- `flowctl glossary read <term>` — print the entry for a term. Resolution starts from cwd and walks ancestors.
- `flowctl glossary remove <term>` — delete the entry from the file that defines it.

Decision entries reuse existing memory commands (`flowctl memory add --track knowledge --category decisions ...`); no new subcommands required for decision records.

## Edge Cases & Constraints

<!-- Source-tag breakdown: 35% [user] / 25% [paraphrase] / 40% [inferred] -->

- **Term divergence across subdirectories** — a sub-glossary may legitimately define a term differently from root (e.g., admin role concept vs consumer role concept). Audit may surface as a "potential conflict" but does not forbid divergence. [inferred]
- **No DDD jargon** — skill prose, file format, tooling output, and user-facing documentation must not use the phrases "ubiquitous language", "bounded context", "domain expert", "aggregate root", or equivalent DDD terminology. [user]
- **Three-criteria decision gate** — before writing a decision entry, verify hard-to-reverse + surprising-without-context + result-of-real-trade-off. If any of the three fails, skip the decision write. The gate is enforced in interview skill prose, not in the schema (schema is permissive). [paraphrase]
- **Interview drag throttle** — glossary-conflict question on every defined word would exhaust users. Conflict surfaces only when the term is load-bearing for the current spec. [paraphrase]
- **No meta-file for subdirectory glossaries** — the filesystem already encodes subproject structure. Nearest-ancestor resolution is sufficient. [user]
- **Adoption gradient** — projects without `GLOSSARY.md` and without decision entries see no behavior change in interview. Autodetect keeps the cost-of-presence at zero for projects that don't need it. [paraphrase]
- **Survives flow-next uninstall** — `GLOSSARY.md` at repo root is project state, not flow-next bookkeeping. Removing `.flow/` deletes decisions but leaves the glossary intact. [paraphrase]
- **Nearest-ancestor walk is bounded** — walk stops at git repo root (`get_repo_root()`), filesystem boundary (`st_dev` change), or a 32-level defensive cap. Symlinks are not followed by walking logic; `pathlib.Path.parent` traversal does not recurse into them. [inferred]
- **Write-target follows read-target** — `flowctl glossary add` writes to whichever `GLOSSARY.md` the lookup would resolve. To force creation of a new subdirectory glossary, drop an empty `GLOSSARY.md` in the target subdir first, then run `add` from inside that subtree. [inferred]
- **Multi-line definitions** — `--definition` is single-line (shell quoting); multi-line definitions use `--definition-file -` (stdin) or `--definition-file <path>`. Behavior (b) inline writes use the stdin variant. [inferred]
- **Decision write confirmation** — decision entries follow the capture/audit pattern: agent shows the proposed entry via `AskUserQuestion` before writing. User can approve, edit, or skip. [inferred]

## Acceptance Criteria

- **R1:** `GLOSSARY.md` lives at the repo root; subdirectory `GLOSSARY.md` files are supported. Neither is placed under `.flow/`. [user]
- **R2:** A `decisions` knowledge category exists; new decision entries land at `.flow/memory/knowledge/decisions/<slug>-<date>.md` with the same frontmatter shape as other categorized entries. [paraphrase]
- **R3:** flowctl resolves glossary lookups via nearest-ancestor walk from the working directory. When run inside a subdirectory with its own `GLOSSARY.md`, that file applies; root applies otherwise. [user]
- **R4:** No meta-file (e.g. `GLOSSARY-MAP.md` or equivalent) is introduced for multi-glossary repos. Subdirectory glossaries are discovered via filesystem walk. [user]
- **R5:** `/flow-next:interview` autodetects doc-aware mode when `GLOSSARY.md` exists at the repo root OR `.flow/memory/knowledge/decisions/` has at least one entry. When neither is present, interview operates as today. [paraphrase]
- **R6:** `/flow-next:interview --docs` forces doc-aware mode on (lazily creating `GLOSSARY.md` at repo root on first term resolution); `--no-docs` forces it off. [paraphrase]
- **R7:** In doc-aware mode, when a user's request contains a term that conflicts with the nearest-ancestor glossary's canonical definition AND the term is load-bearing for the current spec, the interview surfaces the conflict as a question. [paraphrase]
- **R8:** In doc-aware mode, when fuzzy-term sharpening resolves an overloaded term, the resolution is written to the nearest-ancestor `GLOSSARY.md` via `flowctl glossary add` before the next question. [paraphrase]
- **R9:** In doc-aware mode, when grep reveals code-versus-assertion contradiction, the contradiction is surfaced as a question (not silently resolved). [paraphrase]
- **R10:** In doc-aware mode, decision entries are written only when all three gate criteria hold: hard-to-reverse, surprising-without-context, result-of-real-trade-off. Writes follow the capture/audit pattern (agent shows draft via `AskUserQuestion` before writing). [paraphrase]
- **R11:** `docs-gap-scout` extends its scan to include `GLOSSARY.md` files (root + subdirectories) and `.flow/memory/knowledge/decisions/` entries. When a planned change touches a defined term or invalidates a decision constraint, the scout flags those targets. [user]
- **R12:** `/flow-next:audit` walks glossary terms (greps code for term + `_Avoid_` aliases; marks stale on absence; surfaces alias-creep) and decision entries (verifies the constraint still holds; prompts for supersession on conflict). [user]
- **R13:** `/flow-next:sync` (plan-sync) detects glossary-term renames and implicit decision overrides during drift detection, and updates downstream specs accordingly. [user]
- **R14:** flowctl ships glossary subcommands (`add`, `list`, `read`, `remove`) with atomic writes (write-then-rename) and schema validation. Multi-line input accepted via `--definition-file -` / `--definition-file <path>`. [paraphrase]
- **R15:** `GLOSSARY.md` is human-readable markdown with structured per-term sections (H2 heading per term, paragraph definition, optional `_Avoid_` line, optional relationships block); not YAML or any other format requiring tooling to parse. [paraphrase]
- **R16:** Decision entry bodies use a 1-3 sentence floor; `Considered Options` and `Consequences` sections are optional and only included when they add genuine value. [paraphrase]
- **R17:** No DDD terminology ("ubiquitous language", "bounded context", "domain expert", "aggregate root", or equivalent) appears in skill prose, file format documentation, flowctl help text, or user-facing output. An automated grep test enforces this in CI. [user]
- **R18:** Removing `.flow/` (e.g. via `rm -rf .flow/` or flow-next uninstall) deletes decision entries under `.flow/memory/knowledge/decisions/` but leaves `GLOSSARY.md` files (root + subdirectories) intact. The glossary is project state, not flow-next bookkeeping. [user]

## Boundaries

<!-- Source-tag breakdown: 25% [user] / 75% [inferred] -->

Out of scope:

- A glossary-relationships meta-file. [user]
- DDD-style bounded-context modeling discipline forced on every project. [user]
- Multi-context relationship modeling (cross-context shared types). [inferred]
- Migration tooling for projects that already maintain a different glossary format. [inferred]
- A `--commit` flag on the glossary or decision-write subcommands; user owns staging. [inferred]
- Auto-generated glossary-from-code (term extraction via static analysis); glossary entries are user-curated. [inferred]
- Decision-supersession workflow (offering to supersede on `audit` is a follow-up, not part of this epic). [inferred]
- Subdir-scoped force flag (e.g. `--scope here`); to create a new subdirectory glossary, drop an empty `GLOSSARY.md` first. [inferred]
- Slug normalization for term names with special characters (`/`, `#`, spaces); v1 accepts plain ASCII heading text. [inferred]
- Validation that `superseded_by` points to an existing decision id; dangling refs surface during `/flow-next:audit`. [inferred]
- Concurrent-write coordination across parallel `flowctl glossary add` calls; atomic-write protects single calls but read-modify-write races may lose updates (Ralph + manual editing simultaneously). Document the limitation; defer locking. [inferred]
- File-watching / cache invalidation for long-lived agent loops; v1 re-reads on every command. [inferred]

## Decision Context

<!-- Source-tag breakdown: 60% [paraphrase] / 40% [inferred] -->

**Why root placement for the glossary, not under `.flow/`?** Project knowledge belongs to the project. Every agent that reads `CLAUDE.md` / `AGENTS.md` should also read `GLOSSARY.md`. Hiding it under `.flow/` makes it invisible to non-flow-next tooling. Root placement also survives flow-next uninstall. (User explicitly invoked the "repo is state" tenet.)

**Why fold decisions into memory instead of a separate `.flow/decisions/` directory?** Decisions have a lifecycle (proposed → accepted → superseded). They get audited, searched, and surfaced by `memory-scout`. The categorized memory schema already captures every field a decision needs. A separate top-level concept would duplicate audit + search infrastructure for no gain. The user noted "the flow next memory is different" — different from the project glossary, but still the right home for decision records because decisions are flow-next-shaped state.

**Why autodetect instead of a config flag?** Most projects don't need glossaries. Forcing config gymnastics on everyone is annoying. Autodetect keeps the surface invisible until the project commits to the concept (by writing the first term).

**Why nearest-ancestor resolution for subdirectory glossaries?** Monorepos, plugin architectures, and library + example app repos legitimately have subprojects with distinct vocabularies. Forcing a single root glossary fights the filesystem signal. The resolution rule is simple enough to explain in one sentence and doesn't require a meta-file. Algorithm precedent: tsconfig.json (first-match-wins), bounded at git repo root (gitignore convention).

**Why the three-criteria gate for decisions?** Hard-to-reverse + surprising-without-context + real-trade-off kills the bulk of would-be decision entries. Most "decisions" are easy to reverse, obvious in context, or had no real alternative. Without the gate, the decisions store fills with cruft within a quarter.

**Why no DDD terminology?** flow-next is pragmatic and used across many project shapes (CLI tools, libraries, dev tools, plugins). DDD vocabulary excludes a large fraction of users and adds modeling discipline most projects don't need. The same artifact (a project glossary) can live without the DDD framing.

**Closed-epic foundations** (no flowctl dep edges added; closed deps are no-ops, but listed for traceability):

- **fn-30** (memory schema upgrade) — fn-38's `knowledge/decisions/` category extends the categorized YAML frontmatter schema; new optional fields (`decision_status`, `superseded_by`, `alternatives_considered`) layer onto existing frontmatter shape.
- **fn-34** (`/flow-next:audit` agent-native) — R12 extends the audit walk with glossary terms + decision entries; per-entry judge phase carries over directly.
- **fn-36** (interview grill-me enhancements) — R5–R10 layer onto fn-36's lead-with-recommendation, codebase-before-asking, and depth-cap-4 patterns.
- **fn-15-96t** (plan-sync agent) — R13 extends drift detection with two new signal types (glossary renames, decision overrides).

## Approach

<!-- Source-tag breakdown: 100% [inferred] (planning detail) -->

**Sequencing.** Foundational tier ships first (T1 schema, T2 plumbing — parallel-startable). Interview integration (T3) and downstream extensions (T4-T6) consume both. Quality + docs close (T7-T8). Critical path: T1 + T2 → T3 → T7 + T8.

**Reuse points** (verified in repo-scout):

- `MEMORY_CATEGORIES` constants block at `flowctl.py:3659-3676` — extension point for `decisions` category
- `MEMORY_REQUIRED_FIELDS` / `MEMORY_OPTIONAL_FIELDS` / `MEMORY_KNOWLEDGE_FIELDS` at `flowctl.py:3679-3698` — extension point for decision-specific fields
- `MEMORY_FIELD_ORDER` at `flowctl.py:3722-3741` — deterministic write order; new fields need explicit slots
- `atomic_write()` at `flowctl.py:798` — used directly for `GLOSSARY.md` writes (whole-file replace)
- `validate_memory_frontmatter()` at `flowctl.py:4571-4655` and `validate_prospect_frontmatter()` at `flowctl.py:4150-4182` — templates for `validate_glossary_entry`
- `cmd_memory_init()` at `flowctl.py:4965-5052` — pattern for lazy `decisions/` directory creation
- `cmd_prospect_*` at `flowctl.py:7534-7952` — cleanest recent pattern for new `cmd_glossary_*` subcommands
- `get_repo_root()` at `flowctl.py:87-99` — anchor for nearest-ancestor walk
- `flow-next-interview/SKILL.md:135-142` — Investigate-Codebase-Before-Asking pattern; doc-aware Phase-zero glossary scan layers on
- `flow-next-interview/questions.md:5-21` — Pre-Question Taxonomy; doc-aware mode adds glossary-lookup as a third axis
- `flow-next-audit/workflow.md:21-127` — Phase 0 walks `MEMORY_CATEGORIES`; decisions walk is automatic once schema extended
- `agents/docs-gap-scout.md:39, 59-68` — current scan list + change-type → doc-update mapping
- `scripts/sync-codex.sh:485-491` — `AskUserQuestion → request_user_input` rewrite (no new sync rule needed)

**Format precedents** (from docs-scout):

- H2-per-term + paragraph definition: GitBook + glossarify-md convention
- Y-statement (1-sentence ADR floor) for decision body shape
- tsconfig.json first-match-wins for nearest-ancestor walk
- gitignore ceiling-at-git-root for walk bounding

**Net-new code** (no precedent in repo):

- `find_nearest_glossary(start: Path) -> Optional[Path]` near `flowctl.py:87` — bounded ancestor walk
- Markdown section parser (regex `re.finditer` on H2 headings, with fenced-code stripping)
- `validate_glossary_entry` (term + definition + optional aliases shape)
- `cmd_glossary_add/list/read/remove`
- Argparse `glossary` subparser registration after `prospect_sub` block
- Doc-aware autodetect bash in `flow-next-interview/SKILL.md`
- `--docs` / `--no-docs` flag parsing in interview slash command
- R17 grep guard in `ci_test.sh` (or new `terminology_smoke_test.sh`)

## Risks / Dependencies

<!-- Source-tag breakdown: 100% [inferred] (planning detail) -->

**Risks:**

- **Order-of-deps T2 → T3.** Minimum viable T2 to unblock T3 is `glossary add` + `glossary read` (with nearest-ancestor walk). `list` and `remove` can ship later without blocking interview work — but the task is small enough to keep in one piece.
- **Performance of nearest-ancestor walk in agent loops** — unlikely to matter (small N, infrequent reads, depth-capped). Defer caching until profiled.
- **R17 enforcement regression** — manual review on first ship; automated grep guard in T7 prevents regression on subsequent edits.
- **Audit grep scope (R12)** — "marks stale on absence" needs a concrete rule for what counts as "absent". Default: grep tracked code files (excluding `.flow/`, `node_modules`, etc.). T5 settles this.
- **Decision write read-back UX drag** — every gate-pass triggers an AskUserQuestion. If the gate fires often, interviews get long. Mitigation: gate is strict (three criteria); most decisions don't trigger.

**Dependencies:**

- No flowctl dependency edges to other open epics (per epic-scout). fn-38 is unblocked.
- Closed-epic foundations: fn-30 (memory schema), fn-34 (audit), fn-36 (interview), fn-15-96t (plan-sync) — listed in Decision Context above.
- Tooling deps: `git rev-parse` for repo-root resolution (already in flowctl); stdlib `re` for markdown parsing (no new deps).

## Test notes

<!-- Source-tag breakdown: 100% [inferred] -->

- **Test framework**: bash smoke tests (`plugins/flow-next/scripts/*_smoke_test.sh`), each refusing to run from main repo. Pattern: pure bash + inline python heredocs. Reference: `audit_smoke_test.sh:1-90`.
- **New smoke**: `plugins/flow-next/scripts/glossary_smoke_test.sh` covers: nearest-ancestor walk (root + subdir), atomic writes, multi-line definition via stdin, parse roundtrip, `_Avoid_` aliases, term removal.
- **Extended smoke**: `ci_test.sh` memory section (`ci_test.sh:170-180`) gains a `decisions` track assertion; new R17 grep guard scans skill prose + flowctl.py for forbidden DDD vocabulary.
- **No new pytest**: flowctl tests are bash + python heredocs; the project does not use pytest.

## References

- **flow-next captured spec**: `.flow/specs/fn-38-project-glossary-decision-records-and.md` (this file)
- **Memory schema constants**: `plugins/flow-next/scripts/flowctl.py:3659-3744`
- **Atomic write helper**: `plugins/flow-next/scripts/flowctl.py:798-809`
- **Memory subcommand patterns**: `plugins/flow-next/scripts/flowctl.py:5107-5660` (memory_add/read/list)
- **Prospect subcommand patterns** (cleaner recent reference): `plugins/flow-next/scripts/flowctl.py:7534-7952`
- **Interview skill (doc-aware extension point)**: `plugins/flow-next/skills/flow-next-interview/SKILL.md` + `questions.md`
- **Audit skill (R12 extension point)**: `plugins/flow-next/skills/flow-next-audit/workflow.md:21-127`
- **Plan-sync agent (R13 extension point)**: `plugins/flow-next/agents/plan-sync.md:85-103`
- **docs-gap-scout (R11 extension point)**: `plugins/flow-next/agents/docs-gap-scout.md:39, 59-68`
- **sync-codex.sh (validation gate)**: `scripts/sync-codex.sh:485-491, 760-770`
- **External format precedents**:
  - [npryce/adr-tools](https://github.com/npryce/adr-tools) — original Nygard ADR template
  - [Y-statements (Olaf Zimmermann)](https://medium.com/olzzio/y-statements-10eb07b5a177) — 1-sentence ADR shape
  - [open-gitops GLOSSARY.md](https://github.com/open-gitops/documents/blob/main/GLOSSARY.md) — H2-per-term real-world model
  - [glossarify-md](https://github.com/about-code/glossarify-md) — H2-per-term tooling expectation
  - [EditorConfig spec](https://spec.editorconfig.org/) — ancestor walk semantics
  - [TypeScript handbook (tsconfig.json)](https://www.typescriptlang.org/docs/handbook/tsconfig-json.html) — first-match-wins resolution

## Quick commands

```bash
# Glossary smoke test (T2 ships this)
plugins/flow-next/scripts/glossary_smoke_test.sh

# Decisions category — schema validation (T1 ships this)
.flow/bin/flowctl memory init
.flow/bin/flowctl memory add --track knowledge --category decisions \
  --title "Use nearest-ancestor for glossary lookup" \
  --body "Hard to reverse: clients depend on resolution behavior. Surprising: not the obvious 'always-root' default. Trade-off: subdir flexibility vs single-source-of-truth simplicity."

# Doc-aware autodetect (T3 ships this)
[[ -f GLOSSARY.md ]] && echo "doc-aware would activate"
.flow/bin/flowctl memory list --track knowledge --category decisions --json | jq '.entries | length'

# R17 terminology guard (T7 ships this)
grep -RnE 'ubiquitous language|bounded context|domain expert|aggregate root' \
  plugins/flow-next/skills plugins/flow-next/scripts/flowctl.py \
  plugins/flow-next/agents plugins/flow-next/commands && \
  echo "FAIL: DDD jargon detected" || echo "PASS"
```

## Early proof point

Task `fn-38-...2` (flowctl glossary plumbing) validates the fundamental approach: `GLOSSARY.md` format + nearest-ancestor walk + atomic writes round-trip cleanly. If parser fails on multi-line definitions, or nearest-ancestor walk has subtle bugs (cycle handling, ceiling detection), or the file format proves unreadable in practice, the entire downstream chain (T3 interview integration, T4-T6 scout/audit/sync extensions) needs revision before continuing. Re-evaluate format choice (H2-per-term vs alternatives) and walk algorithm before T3+ proceeds.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | GLOSSARY.md at repo root + subdirs supported | fn-38-...2 | — |
| R2  | `decisions` knowledge category exists | fn-38-...1 | — |
| R3  | Nearest-ancestor walk for lookups | fn-38-...2 | — |
| R4  | No meta-file introduced | fn-38-...2, fn-38-...7 | T2 doesn't add one; T7 grep-verifies |
| R5  | Interview autodetects doc-aware mode | fn-38-...3 | — |
| R6  | `--docs` / `--no-docs` flags | fn-38-...3 | — |
| R7  | Term-conflict surfaced when load-bearing | fn-38-...3 | — |
| R8  | Inline glossary write on resolution | fn-38-...3 | — |
| R9  | Code/spec contradiction surfaced | fn-38-...3 | — |
| R10 | Three-criteria gate + read-back for decision write | fn-38-...3 | — |
| R11 | docs-gap-scout extends scan | fn-38-...4 | — |
| R12 | /flow-next:audit walks glossary + decisions | fn-38-...5 | — |
| R13 | /flow-next:sync detects glossary/decision drift | fn-38-...6 | — |
| R14 | flowctl glossary subcommands + multi-line | fn-38-...2 | — |
| R15 | GLOSSARY.md is human-readable markdown | fn-38-...2 | — |
| R16 | Decision body 1-3 sentence floor | fn-38-...1 | Schema permissive; format documented in T1 |
| R17 | No DDD terminology + automated grep | fn-38-...3, fn-38-...7 | T3 enforces in prose; T7 ships the grep |
| R18 | Glossary survives flow-next uninstall | fn-38-...2 | Root placement satisfies; T2 verifies |
