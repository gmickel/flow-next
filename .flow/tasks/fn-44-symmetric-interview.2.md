---
satisfies: [R1, R2, R3, R6, R7, R8, R9, R26]
---

## Description

Add `--scope=business|technical|both` flag (default `technical`) to `/flow-next:interview`. Implement pass-aware behavior with the byte-for-byte section merge contract from the fn-44 spec Edge Cases. Document the flag in the command-file metadata.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (flag parsing, autodetect, pass-behavior section, merge contract)
- `plugins/flow-next/commands/flow-next/interview.md` (flag documentation)

## Approach

**SKILL.md MUST NOT parse `--scope` / `--biz` / `--tech` inline.** All token-safe parsing lives in `flowctl scope resolve` (added by T1). SKILL.md calls the subcommand and consumes its JSON output:

```bash
# Use --raw "$ARGUMENTS" so flowctl tokenizes via shlex INSIDE the subcommand —
# preserves quoted paths with spaces (e.g., `/flow-next:interview --biz "docs/my spec.md"`).
# Unquoted $ARGUMENTS would word-split into broken tokens. <!-- Updated by plan-sync: fn-44-symmetric-interview.1 used `--raw "$ARGUMENTS"` not `"$@"` -->
RESOLVED_JSON=$("$FLOWCTL" scope resolve --json --raw "$ARGUMENTS")
SCOPE=$(printf '%s' "$RESOLVED_JSON" | jq -r '.scope')
ARGUMENTS=$(printf '%s' "$RESOLVED_JSON" | jq -r '.remaining_args | join(" ")')
```

`flowctl scope resolve --json` returns `{ "scope": "business|technical|both", "remaining_args": ["fn-1", "--docs", ...] }` — scope flags stripped, every other token preserved in order. Conflict / invalid-value errors exit non-zero (SKILL.md propagates).

Existing strip block at `SKILL.md:61-97` (for `--docs` / `--strategy`) runs AFTER scope resolution against the cleaned `RAW_ARGS`.

Flag matrix at `SKILL.md:101-111` extends with scope x doc/strategy rows (rows describe behavior, not parsing logic).

This architecture (parse-in-flowctl, decide-in-skill) is the spec's API Contracts commitment: skill drives workflow, flowctl provides atomic helpers.

Flag matrix at `SKILL.md:101-111` extends with scope x doc/strategy rows.

Pass behavior + merge contract (from fn-44 spec Edge Cases):
- **Technical pass** (`SCOPE == technical`, default): writes ONLY tech-owned sections (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, verifiable-AC). For `## Decision Context`: if FLAT (no H3 subsections), write/refine the flat body in place (R22 1.0.2 backward-compat — no H3 introduction). If `### Motivation` already exists (prior biz pass), preserve `### Motivation` byte-for-byte and write only `### Implementation Tradeoffs`. Preserves business-section bodies (`Goal & Context`, `Boundaries`) byte-for-byte. May overwrite `*Pending technical-scope interview pass.*` placeholder strings under tech-owned section headers. Reads existing business sections when populated; cites them in opener.
- **Business pass** (`SCOPE == business`): BEFORE drafting any question, runs the project-docs investigation (per R26): reads `README.md`, `CHANGELOG.md`, `STRATEGY.md`, `GLOSSARY.md`, `knowledge/decisions/` (TOC + first paragraph of recent N), `.flow/specs/` index, `docs/` if present. Items resolved by these sources are logged in `## Resolved via Project Docs` audit section; user is NOT asked about things the docs already define. Then drafts user-judgment-required biz questions only (symmetric to the existing codebase-investigation pattern at `SKILL.md:226`).

  Writes biz-owned sections (`Goal & Context`, `Boundaries`, outcome-AC). For `## Decision Context`: if FLAT (tech-only spec from 1.0.2), promote the existing flat body byte-for-byte into a new `### Implementation Tradeoffs` H3 and write the new `### Motivation` H3 as sibling. If H3s already exist, preserve `### Implementation Tradeoffs` and write/refine only `### Motivation`. Preserves technical-section bodies byte-for-byte. If a tech section is empty, writes the placeholder string; if the tech section has content, leaves it untouched (refine-mode).
- **Both pass** (`SCOPE == both`): runs biz pass first, then tech pass with biz output as in-memory context. Same merge contract applies in both phases.
- **Auxiliary sections** (`Strategy Alignment` / `Glossary Conflicts` / `Conversation Evidence` / `Resolved via Codebase`) are preserved across all scope modes — never deleted or rewritten by either pass.
- **R-IDs**: append-only across passes per fn-29 rules. Never renumber. Never replace existing.

**Inline skill constraint**: AskUserQuestion is unavailable in subagents (docs-scout finding). Interview skill must stay inline — no `context: fork`.

`commands/flow-next/interview.md` documents the new flag alongside `--docs` / `--strategy` entries with examples.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:61-97` — flag-strip pattern; mirror exactly
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:101-111` — flag matrix; extend
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:117-144` — DOC_AWARE/STRATEGY_AWARE autodetect
- `plugins/flow-next/commands/flow-next/interview.md` — existing flag documentation conventions
- fn-44 spec Edge Cases — section merge contract (load-bearing)

**Optional:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:150` — behavior-layer-on insertion point

## Acceptance

- [ ] `--scope=business|technical|both` flag parsed; default `technical`
- [ ] `--biz` / `--tech` short aliases resolve correctly
- [ ] Conflicting flags error cleanly with explicit message
- [ ] SKILL.md calls `flowctl scope resolve --json --raw "$ARGUMENTS"` for scope + remaining_args; no inline token parsing for scope flags. <!-- Updated by plan-sync: fn-44-symmetric-interview.1 shipped `--raw "$ARGUMENTS"` invocation for shell-quoting safety, not `"$@"` --> Tests cover `--scope` ordering (before/after spec id, interleaved with `--docs`).
- [ ] Business pass writes biz-owned sections (Goal & Context, Boundaries, `### Motivation`, outcome-AC); FLAT-to-substructured promotion preserves existing flat body byte-for-byte into `### Implementation Tradeoffs`; never alters `### Implementation Tradeoffs` after substructure exists
- [ ] Business pass preserves existing tech-section bodies byte-for-byte; writes placeholder `*Pending technical-scope interview pass.*` ONLY where tech section is empty; never overwrites populated tech section
- [ ] Technical pass reads biz sections when populated; cites in opener; silent when absent
- [ ] Technical pass writes tech-owned sections; for `## Decision Context`: keeps FLAT body when no H3 substructure exists (R22 1.0.2 compat — no H3 introduction); writes/refines `### Implementation Tradeoffs` only when `### Motivation` already exists; preserves `### Motivation` byte-for-byte when present; may only replace placeholder strings under tech section headers
- [ ] `--scope=both` runs biz pass first then tech pass; same merge contract applies in both phases
- [ ] Auxiliary sections (Strategy Alignment / Glossary Conflicts / Conversation Evidence / Resolved via Codebase) preserved across all scope modes
- [ ] R-IDs in `## Acceptance Criteria` are append-only across passes; never renumbered, never replaced
- [ ] `commands/flow-next/interview.md` documents `--scope` flag with examples
- [ ] `SKILL.md` cross-links `plugins/flow-next/templates/spec.md` when naming section structure (per R17)
- [ ] **R26 project-docs investigation**: `SKILL.md` `--scope=business` pass instructs the agent to read project docs (`README.md`, `CHANGELOG.md`, `STRATEGY.md`, `GLOSSARY.md`, `knowledge/decisions/`, `.flow/specs/` index, `docs/`) BEFORE drafting biz questions. Items resolved by docs land in `## Resolved via Project Docs` (parallel to existing `## Resolved via Codebase`). Symmetric to the "investigate codebase first" rule at SKILL.md:226. Verifiable: grep SKILL.md for the project-docs investigation block + `## Resolved via Project Docs` section name.


## Done summary

## Evidence
