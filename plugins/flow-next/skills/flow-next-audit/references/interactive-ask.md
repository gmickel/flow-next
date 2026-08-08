# Phase 3: Ask (gated reference — interactive mode only)

> **Loaded only when `MODE` is `interactive`.** An autofix run (`mode:autofix`,
> and therefore every pilot / Ralph invocation) skips Phase 3 entirely and never
> reads this file: it asks nothing, marks genuinely ambiguous classifications
> stale, and reports Harden candidates and un-graduation proposals under
> Recommended without applying them. The autofix rules themselves stay inline in
> SKILL.md and workflow.md.

## Phase 3: Ask (interactive only)

**Goal:** confirm decisions with the user. Skip entirely in autofix mode.

### 3.1 — Group decisions to minimize friction

Bundle the easy ones, isolate the hard ones:

1. **Group obvious Keeps** — single batched confirmation: "These N entries reviewed without changes — proceed?"
2. **Group obvious Updates** — batched confirmation when the fixes are mechanical (path rename, module field update). "These N entries get straightforward reference updates — proceed?"
3. **Present Consolidate clusters individually** — show canonical doc + what merges + what gets deleted.
4. **Present Replace candidates individually** — show old guidance + current code finding + proposed successor outline.
5. **Present non-auto Delete cases individually** — show evidence, ask explicitly. Auto-Delete bypasses this.
6. **Present Harden candidates individually** — never batched. Each one edits shared repo infrastructure, so each needs its own explicit consent. See §3.4.
7. **Present un-graduation proposals individually** — a hardened entry whose gate is gone (§0.75.2). Show which surface was checked and what was missing; options are `mark-fresh` (recommended) / leave hardened / skip.

### 3.2 — Question style

Use `AskUserQuestion` (deferred — load via `ToolSearch select:AskUserQuestion` if its schema isn't yet in scope). If the tool is unreachable, fall back to printing a numbered list and reading a typed reply. (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.)

Rules:

- **One question at a time.**
- **Multiple choice** when natural.
- **Lead with the recommendation** — don't enumerate all 6 outcomes if only 2 are plausible.
- **One-sentence rationale** — evidence is in the report, not the question.

Example question shape (single entry):

```
Entry: bug/runtime-errors/oauth-callback-2025-08-12
Evidence:
  - module `src/auth/callback.ts` renamed to `src/auth/oauth/callback.ts`
  - function signature unchanged
  - no successor entry found
Recommendation: Update (rename references)

Options:
  1. Update (recommended)
  2. Skip for now
  3. Mark stale
```

### 3.3 — Harden candidate questions

One question per candidate, via the same blocking-question tool. Show the proposed gate type, the **draft artifact exactly as it would be written**, and the recurrence evidence as artifacts (never as a usage count — there is no read-side telemetry):

```
Entry: knowledge/conventions/timestamps-utc-2026-03-04
Lesson: always stamp timestamps UTC ISO-8601; naive datetime.now() broke receipt comparisons
Evidence:
  - 2 `## Update` headings (re-taught in fn-97 and fn-104)
  - 4 commits on the entry file
  - mechanizable: naive-datetime use is lint-detectable
  - duplication guard: no `DTZ` rule found in pyproject.toml
Proposed gate: (a) lint rule — add `DTZ` to the ruff `select` list in pyproject.toml

  [tool.ruff.lint]
  select = ["E", "F", "DTZ"]     # <- DTZ added

On accept: the edit is written, `ruff check` is run to confirm DTZ is active in the
resolved config, and only then is the entry demoted to a pointer at the gate
(file stays on disk, body intact).

Options:
  1. Accept — write the lint rule, verify, demote (recommended)
  2. Pick a different gate type (CI step / CLAUDE.md rule)
  3. Decline — keep the entry as context
```

Rules for these questions:

- **Always three options**: accept / pick a different gate type / decline. Declining is a first-class answer, not a failure.
- If the user picks option 2, present the alternative surfaces that actually exist in this repo with their drafts; never offer a surface the repo does not have, and never offer to scaffold one.
- For a **pointer-demotion** candidate (duplication guard found an active gate), there is no draft artifact — the question shows the existing gate and asks only accept / decline.
- Nothing is written before the answer. The draft is staging, not a preview of an applied edit.

### 3.4 — Skip discoverability check until Phase 6

Phase 3 only handles per-entry decisions. The CLAUDE.md / AGENTS.md discoverability question runs in Phase 6 — separate, after the report exists.

### Done when

- User has confirmed every batched group and every individual item.
- Skipped items are recorded in the report.
