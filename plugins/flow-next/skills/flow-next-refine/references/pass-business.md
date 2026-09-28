# Interview — business pass (loaded when `SCOPE == business`, or for phase 1 of `both`)

> Read at the pass-routing branch point in SKILL.md. A technical-only interview never reads this file.

Contents:

- [Business pass](#business-pass)
- [Investigate Project Docs Before Asking (R26)](#investigate-project-docs-before-asking-r26)
- [Both pass (`SCOPE == both`)](#both-pass-scope--both)

## Business pass

Doc-aware default: the autodetect cascade in SKILL.md Setup still runs; doc-awareness does NOT auto-activate from the biz pass alone (`R26` adds project-docs investigation independently).

Run BEFORE the first AskUserQuestion call:

1. **Project-docs investigation (R26)** — see "Investigate Project Docs Before Asking" below. Symmetric to the codebase-investigation rule for the tech pass. Items resolved by docs land in `## Resolved via Project Docs`. The user is NOT asked about things the project docs already define.
2. **Draft only biz questions that pass the one test in SKILL.md** — load `questions-business.md` for the short check-list of what to look for in the spec. Asking nothing is a valid outcome.

Per-section write behavior (per the write-policy):

- **Writable biz sections** (`Goal & Context`, `Boundaries`, outcome-AC, `### Motivation` under `## Decision Context`): write/refine from interview answers.
- **Preserved tech sections** (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`): **come back byte-for-byte.** A single reworded, reordered, or re-wrapped line in any of the three is a broken pass. An empty tech section stays empty.
- **`## Decision Context`** (per `decision_context` shape):
  - When `shape == "substructured"` and `promote_flat_to_implementation_tradeoffs == true` (FLAT body exists from a prior tech-only pass): promote the existing flat body byte-for-byte into a new `### Implementation Tradeoffs` H3 (preserve the prose verbatim — same content, just under a new H3), and write the new `### Motivation` H3 as a sibling.
  - When `shape == "substructured"` and `promote_flat_to_implementation_tradeoffs == false` (H3s already exist): preserve `### Implementation Tradeoffs` byte-for-byte; write/refine ONLY `### Motivation`.
- **`## Acceptance Criteria`**: append outcome-AC R-IDs (R-IDs are append-only across passes — never renumber, never replace; take the next unused number). Source-tag each criterion you append (`[user]` = the PO answering in this pass, `[paraphrase]`, `[inferred]`, `[strategy:<track>]`); never tag or retag a criterion another pass wrote — see `write-back.md` § Source tags on acceptance criteria.
- **Auxiliary sections**: preserve byte-for-byte per the auxiliary-sections rule in SKILL.md; biz pass adds `Resolved via Project Docs`, plus `Resolved via Experiment` when it ran one.

## Investigate Project Docs Before Asking (R26)

Symmetric to the "Investigate Before Asking" codebase rule for the tech pass (SKILL.md, under "Interview Process"). **When `SCOPE == business` (or the biz phase of `both`), the project documentation below is investigated before any biz question is drafted** — regardless of doc-aware autodetect state. A first round drafted before `STRATEGY.md` was read and the other docs were searched has broken this.

Read `STRATEGY.md` (repo root) in full. Search the rest for what the spec touches rather than reading it end to end:

1. `README.md`, `CHANGELOG.md` (or `RELEASES.md` / `HISTORY.md`), and `GLOSSARY.md` (repo root) — search for the spec's terms and read the matching passages.
2. `knowledge/decisions/` (or `.flow/memory/knowledge/decisions/` — `flowctl memory list --track knowledge --category decisions --json` enumerates entries) — read the table-of-contents + first paragraph of each of the most-recent 10 entries (NOT full bodies; the first paragraph carries the decision; deeper drill-down is on-demand).
3. `.flow/specs/` index (`flowctl specs --json | jq -c '[.specs[] | select(.status == "open") | {id, title, status}]'` lists open specs) — scan titles + status; full-read only specs whose titles plausibly overlap the current spec's domain.
4. `docs/` directory (if present at repo root) — scan filenames; full-read only files whose names plausibly overlap.

Classify biz questions via the **Pre-Question Taxonomy** before asking:

- **Project-docs-answerable** ("what does the strategy say / what does CHANGELOG show we've already shipped / what does GLOSSARY define the canonical term as / what decision did we record for X") → resolve from the docs; log to spec's `## Resolved via Project Docs` section with `path:line` evidence (or `path` + section heading when line numbers are noisy).
- **User-judgment-required** ("who is this for / what should we explicitly NOT build") → ask via `AskUserQuestion` when the question passes the one test in SKILL.md.

If you find yourself asking the user a biz question that README/CHANGELOG/STRATEGY already answers, that's the bug. Stop and resolve from docs. Symmetric form of the existing "if you find yourself answering a 'should' question via grep, that's the bug" rule.

The `## Resolved via Project Docs` section is auxiliary and biz-pass-only (parallel to `## Resolved via Codebase` for the tech pass). Preserved across scope changes per the auxiliary-sections rule.

## Both pass (`SCOPE == both`)

Runs biz pass first, then tech pass in the same skill invocation. Each phase enforces its own merge contract:

1. **Phase 1: biz pass** — runs the full biz-pass workflow above. Writes biz sections; preserves any pre-existing tech sections byte-for-byte.
2. **Phase 2: tech pass** — runs the full tech-pass workflow (read `pass-technical.md` at that point) using the just-written biz output as in-memory context. Reads biz sections, cites them in the opener, writes tech sections, preserves biz sections byte-for-byte.

Auxiliary sections are preserved across both phases per the auxiliary-sections rule.

If the user interrupts between phase 1 and phase 2, the biz sections are written and the tech sections stay as they were. Re-running `--scope=technical` later picks up any open technical fork.

**Two write-policy calls for `both`** — biz first, then recompute state + tech:

```bash
#   BIZ_POLICY=$(printf '%s' "$CURRENT_SECTIONS" | "$FLOWCTL" scope write-policy business --current-sections-json -)
#   # ... run biz pass, write biz sections (in memory or to disk) ...
#   # Rebuild CURRENT_SECTIONS_AFTER_BIZ from the post-biz state — biz_pass_ran=true,
#   # decision_context_has_h3 likely true now (Motivation H3 written):
#   CURRENT_SECTIONS_AFTER_BIZ='{"decision_context_has_h3": true, "biz_pass_ran": true}'
#   TECH_POLICY=$(printf '%s' "$CURRENT_SECTIONS_AFTER_BIZ" | "$FLOWCTL" scope write-policy technical --current-sections-json -)
#   # ... run tech pass under TECH_POLICY ...
```
