# Interview — business pass (loaded when `SCOPE == business`, or for phase 1 of `both`)

> Read at the pass-routing branch point in SKILL.md. A technical-only interview never reads this file.

Contents:

- [Business pass](#business-pass)
- [Investigate Project Docs Before Asking (R26)](#investigate-project-docs-before-asking-r26)
- [Both pass (`SCOPE == both`)](#both-pass-scope--both)

## Business pass

Doc-aware default: the autodetect cascade in SKILL.md Setup still runs; doc-awareness does NOT auto-activate from the biz pass alone (`R26` adds project-docs investigation independently).

Run BEFORE the first plain-text numbered prompt call:

1. **Project-docs investigation (R26)** — see "Investigate Project Docs Before Asking" below. Symmetric to the codebase-investigation rule for the tech pass. Items resolved by docs land in `## Resolved via Project Docs`. The user is NOT asked about things the project docs already define.
2. **Draft only user-judgment-required biz questions** — load `questions-business.md` for the question taxonomy. Walk problem framing, target user/persona, success metrics, MVP boundary, business constraints, what-not-to-build, prioritization rationale, business risks, UX expectations.

Per-section write behavior (per the write-policy):

- **Writable biz sections** (`Goal & Context`, `Boundaries`, outcome-AC, `### Motivation` under `## Decision Context`): write/refine from interview answers.
- **Preserved tech sections** (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`): **come back byte-for-byte.** A single reworded, reordered, or re-wrapped line in any of the three is a broken pass. If a tech section is EMPTY (listed in `placeholder_write`), write the placeholder line `*Pending technical-scope interview pass.*` under its heading so the read-back makes the intentional emptiness visible. If a tech section has content, leave it untouched (refine-mode for a re-run on an already-tech-populated spec).
- **`## Decision Context`** (per `decision_context` shape):
 - When `shape == "substructured"` and `promote_flat_to_implementation_tradeoffs == true` (FLAT body exists from a prior tech-only pass): promote the existing flat body byte-for-byte into a new `### Implementation Tradeoffs` H3 (preserve the prose verbatim — same content, just under a new H3), and write the new `### Motivation` H3 as a sibling.
 - When `shape == "substructured"` and `promote_flat_to_implementation_tradeoffs == false` (H3s already exist): preserve `### Implementation Tradeoffs` byte-for-byte; write/refine ONLY `### Motivation`.
- **`## Acceptance Criteria`**: append outcome-AC R-IDs (R-IDs are append-only across passes per fn-29 rules — never renumber, never replace; take the next unused number). Source-tag each criterion you append (`[user]` = the PO answering in this pass, `[paraphrase]`, `[inferred]`, `[strategy:<track>]`); never tag or retag a criterion another pass wrote — see `write-back.md` § Source tags on acceptance criteria.
- **Auxiliary sections**: preserve byte-for-byte per the auxiliary-sections rule in SKILL.md; biz pass adds `Resolved via Project Docs` only.

## Investigate Project Docs Before Asking (R26)

Symmetric to the "Investigate Before Asking" codebase rule for the tech pass (SKILL.md, under "Interview Process"). **When `SCOPE == business` (or the biz phase of `both`), the project documentation below is investigated before any biz question is drafted** — regardless of doc-aware autodetect state. A first round drafted before the read list has been walked has broken this.

Read — in order, with the bounded reads called out so this doesn't balloon into a multi-hour scan:

1. `README.md` (repo root) — full read.
2. `CHANGELOG.md` (or project-equivalent release notes — `RELEASES.md`, `HISTORY.md`) — full read.
3. `STRATEGY.md` (repo root) — full read.
4. `GLOSSARY.md` (repo root) — full read.
5. `knowledge/decisions/` (or `.flow/memory/knowledge/decisions/` — `flowctl memory list --track knowledge --category decisions --json` enumerates entries) — read the table-of-contents + first paragraph of each of the most-recent 10 entries (NOT full bodies; the first paragraph carries the decision; deeper drill-down is on-demand).
6. `.flow/specs/` index (`flowctl specs --json` lists open specs) — scan titles + status; full-read only specs whose titles plausibly overlap the current spec's domain.
7. `docs/` directory (if present at repo root) — scan filenames; full-read only files whose names plausibly overlap.

Classify biz questions via the **Pre-Question Taxonomy** before asking:

- **Project-docs-answerable** ("what does the strategy say / what does CHANGELOG show we've already shipped / what does GLOSSARY define the canonical term as / what decision did we record for X") → resolve from the docs; log to spec's `## Resolved via Project Docs` section with `path:line` evidence (or `path` + section heading when line numbers are noisy).
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

- **User-judgment-required** ("what should our success metric be / what's MVP scope / what should we explicitly NOT build") → ask via `plain-text numbered prompt`.

If you find yourself asking the user a biz question that README/CHANGELOG/STRATEGY already answers, that's the bug. Stop and resolve from docs. Symmetric form of the existing "if you find yourself answering a 'should' question via grep, that's the bug" rule.

The `## Resolved via Project Docs` section is auxiliary and biz-pass-only (parallel to `## Resolved via Codebase` for the tech pass). Preserved across scope changes per the auxiliary-sections rule.

## Both pass (`SCOPE == both`)

Runs biz pass first, then tech pass in the same skill invocation. Each phase enforces its own merge contract:

1. **Phase 1: biz pass** — runs the full biz-pass workflow above. Writes biz sections; preserves any pre-existing tech sections byte-for-byte (with placeholder lines under empty tech sections).
2. **Phase 2: tech pass** — runs the full tech-pass workflow (read `pass-technical.md` at that point) using the just-written biz output as in-memory context. Reads biz sections, cites them in the opener, writes tech sections, preserves biz sections byte-for-byte.

Auxiliary sections are preserved across both phases per the auxiliary-sections rule.

If the user interrupts between phase 1 and phase 2, the biz sections are written but the tech sections retain placeholder lines. Re-running `--scope=technical` later completes the spec.

**Two write-policy calls for `both`** — biz first, then recompute state + tech:

```bash
# BIZ_POLICY=$(printf '%s' "$CURRENT_SECTIONS" | "$FLOWCTL" scope write-policy business --current-sections-json -)
# # ... run biz pass, write biz sections (in memory or to disk) ...
# # Rebuild CURRENT_SECTIONS_AFTER_BIZ from the post-biz state — biz_pass_ran=true,
# # decision_context_has_h3 likely true now (Motivation H3 written), placeholder lines
# # under empty tech sections counted as "no content" for tech-pass overwrite logic:
# CURRENT_SECTIONS_AFTER_BIZ='{"decision_context_has_h3": true, "biz_pass_ran": true, "tech_sections_have_content": {"Architecture & Data Models": <still-bool>, ...}}'
# TECH_POLICY=$(printf '%s' "$CURRENT_SECTIONS_AFTER_BIZ" | "$FLOWCTL" scope write-policy technical --current-sections-json -)
# # ... run tech pass under TECH_POLICY ...
```
