# Interview — spec write-back templates (loaded at completion)

> Loaded at the Completion step to write the refined spec, per input type. Only ONE branch runs
> (NEW IDEA / EXISTING SPEC / Flow Task / File Path). Split out of the always-loaded SKILL.md so
> its ~160 lines are not held in context across the whole interview.

## Write Refined Spec

After interview complete, write everything back — **scope depends on input type**.

**Single-emission write pattern (all branches below):** compose the body and Write it ONCE via the **Write tool** to a **literal unique path** — the Write render is the user-visible read-back. Path-persistence rule: bash vars do NOT survive across tool calls, and that applies to the draft path itself — compose the path in agent context (`${TMPDIR:-/tmp}/flow-interview-<kind>-<id>-<agent-chosen 4-char suffix>.md`) and type it verbatim in the Write call AND the flowctl `--file <path>` call; never a shell variable across tool calls (`mktemp` only for paths created and consumed within one bash block). **Edit-cycle Read rule:** if the user requests revisions after seeing the render, apply them via the Edit tool (deltas only), then **Read the FULL draft file** before re-asking approval — the Read render is that cycle's full read-back and satisfies Edit's read-before-edit for the next cycle.

The canonical spec section structure lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (the single source of truth — never re-embed the section list inline per R17). The templates below show the additional **interview audit sections** that layer onto the canonical structure; the underlying spec sections (`## Goal & Context`, `## Architecture & Data Models`, ...) come from the template.

Section-write rules from the scope-aware pass behavior (above) MUST be honored — the write-policy result from `flowctl scope write-policy` is the source of truth for which sections this scope writes vs preserves. The `## Decision Context` substructure / FLAT-vs-substructured promotion logic is in the write-policy; do not invent inline.

### For NEW IDEA (text input, no Flow ID)

Create spec with interview output. **DO NOT create tasks** — that's `/flow-next:plan`'s job.

The canonical section layout for the spec body is in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — the **template file is the seed** for the canonical 7-section structure (`Goal & Context`, `Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, `Acceptance Criteria`, `Boundaries`, `Decision Context`). `flowctl spec skeleton` is **NOT** the seed here — it returns a 1.0.2-shape skeleton (`Overview` / `Scope` / `Approach` / `Quick commands` / `Acceptance` / `References`) for R22 byte-for-byte backward-compat with the pre-1.1.0 `flowctl spec create` output, which uses different section names than the new canonical template. Reading from `flowctl spec skeleton` here would seed sections the scope-aware write-policy doesn't recognize. Read the template file directly. Fill the scope-owned canonical sections per the write-policy above, then append the auxiliary interview-audit sections below the canonical body (the R21 sync-codex drift guard forbids re-embedding the canonical section sequence in any skill markdown — the template file is the only allowed location).

```bash
$FLOWCTL spec create --title "..." --json

# Build the spec body in-memory:
#   1. Seed from the canonical template FILE (not `flowctl spec skeleton` —
#      that command stays 1.0.2-compatible per R22; its section names
#      (Overview / Scope / Approach / Quick commands / Acceptance / References)
#      don't match the scope-aware write-policy's canonical section names).
#
#      Resolve the template via the 4-tier discovery cascade. The full walker
#      (cascade order, case-insensitive FS probe, both-exist warning, plugin-root
#      fallback) is single-sourced in ../../references/spec-template-discovery.md —
#      Read it and run its walker to set TEMPLATE_PATH + TEMPLATE.
#      Fill section bodies from interview answers under your scope's writable
#      sections per the write-policy (frontmatter + scope-owner markers may be
#      stripped from the final spec body — authoring guidance, not spec content).
#   2. Append the auxiliary interview-audit sections (only those that fired):
```

Compose the full body and Write it ONCE to a literal unique path (e.g. `${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md`) via the **Write tool** — per the single-emission write pattern above. The body:

```markdown
<canonical body from skeleton, with interview-answered prose under each
 writable section per the write-policy — biz pass fills biz-owned sections,
 tech pass fills tech-owned, placeholders under empty other-side sections>

## Resolved via Codebase
(optional — written by the technical pass when codebase-investigation resolved items)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered. Lets reviewers spot-check assumptions later.

## Resolved via Project Docs
(optional — written by the business pass per R26 when project-docs investigation resolved items)
Items the agent answered via README / CHANGELOG / STRATEGY / GLOSSARY / knowledge decisions / .flow specs / docs, with `path` or `path:line` evidence. Symmetric to `## Resolved via Codebase` but biz-pass-only.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen (use-canonical / redefine / this-is-different), file:line of the canonical entry. Lets reviewers see where vocabulary tightened.

## Strategy Conflicts
(optional — only when STRATEGY_AWARE=1 surfaced behavior-(e) hits during the interview)
Per-line: user-wording vs. canonical-strategy-wording (track name or approach), STRATEGY.md path, resolution chosen (align-with-strategy / flag-as-drift / this-is-different). Lets reviewers see where the spec aligns or pushes back on strategic intent. Read-only signal for plan-sync — the interview never edits STRATEGY.md.

## Open Questions
Unresolved items that need research during planning
```

Then hand flowctl the draft file — the literal path typed verbatim (never a shell variable across tool calls):

```bash
$FLOWCTL spec set-plan <id> --file "${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md" --json
```

Then suggest: "Run `/flow-next:plan fn-N` to research best practices and create tasks."

### For EXISTING SPEC (fn-N that already has tasks)

**First check if tasks exist:**
```bash
$FLOWCTL tasks --spec <id> --json
```

**If tasks exist:** Only update the spec (add edge cases, clarify requirements). **Do NOT touch task specs** — plan already created them.

**If no tasks:** Update spec, then suggest `/flow-next:plan`.

The canonical section layout for the spec body is in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md). Read the existing spec, refine sections under your scope per the write-policy (preserving sections owned by the other scope byte-for-byte), and append/update the auxiliary interview-audit sections. The R21 drift guard forbids re-embedding the canonical section sequence in this skill — read the existing body, do not regenerate from a template.

**Reuse the spec body already fetched at Detect Input Type** (`$FLOWCTL cat <id>` ran there) — do NOT re-fetch here. Re-fetch only if the interview mutated the spec on disk since that read (e.g. an earlier partial write-back in this run).

Refine canonical sections under your scope's writable list (per write-policy) while preserving sections owned by the other scope byte-for-byte, append the auxiliary interview-audit sections (only those that fired), and Write the merged body ONCE to a literal unique path (e.g. `${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md`) via the **Write tool** — per the single-emission write pattern above. The body:

```markdown
<merged body: canonical sections from the Detect-Input-Type read, with this
 scope's writable sections refined from interview answers, other-scope sections
 preserved byte-for-byte per the write-policy>

## Resolved via Codebase
(optional — written by the technical pass when codebase-investigation resolved items)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered.

## Resolved via Project Docs
(optional — written by the business pass per R26 when project-docs investigation resolved items)
Items the agent answered via README / CHANGELOG / STRATEGY / GLOSSARY / knowledge decisions / .flow specs / docs, with `path` or `path:line` evidence.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen, file:line of the canonical entry.

## Strategy Conflicts
(optional — only when STRATEGY_AWARE=1 surfaced behavior-(e) hits during the interview)
Per-line: user-wording vs. canonical-strategy-wording, STRATEGY.md path, resolution chosen.

## Open Questions
Unresolved items
```

Then hand flowctl the draft file — the literal path typed verbatim:

```bash
$FLOWCTL spec set-plan <id> --file "${TMPDIR:-/tmp}/flow-interview-spec-<id>-<suffix>.md" --json
```

### For Flow Task ID (fn-N.M)

**First check if task has existing spec from planning:**
```bash
$FLOWCTL cat <id>
```

**If task has substantial planning content** (description with file refs, sizing, approach):
- **Do NOT overwrite** — planning detail would be lost
- Only ADD new acceptance criteria discovered in interview: read the existing acceptance (already fetched via `$FLOWCTL cat <id>` above), append the new criteria, and Write the merged list ONCE via the **Write tool** to a literal unique path (e.g. `${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md`) — per the single-emission write pattern above. Then:
  ```bash
  $FLOWCTL task set-acceptance <id> --file "${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md" --json
  ```
- Or suggest interviewing the spec instead: `/flow-next:interview <spec-id>`

**If task is minimal** (just title, empty or stub description):
- Update task with interview findings
- Focus on **requirements**, not implementation details
- Write the description and acceptance each ONCE via the **Write tool** to literal unique paths (e.g. `${TMPDIR:-/tmp}/flow-interview-desc-<id>-<suffix>.md` / `${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md`) — per the single-emission write pattern above. Then:

```bash
$FLOWCTL task set-spec <id> --description "${TMPDIR:-/tmp}/flow-interview-desc-<id>-<suffix>.md" --acceptance "${TMPDIR:-/tmp}/flow-interview-acc-<id>-<suffix>.md" --json
```

Description should capture:
- What needs to be accomplished (not how)
- Edge cases discovered in interview
- Constraints and requirements

Do NOT add: file/line refs, sizing, implementation approach — that's plan's job.

### For File Path

Rewrite the file with refined spec:
- Preserve any existing structure/format
- Add sections for areas covered in interview
- Include edge cases, acceptance criteria
- Keep it requirements-focused (what, not how)

This is typically a pre-spec doc. After interview, suggest `/flow-next:plan <file>` to create spec + tasks.
