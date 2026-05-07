---
satisfies: [R7, R8, R9]
---

## Description

Phase 2 body-header rendering: TL;DR (3-5 bullets), R-ID coverage table (every R-ID → satisfying task → evidence commit, with ⚠️ on uncovered), Critical changes section (high-churn / cross-module / public-interface / security-sensitive / behavior-visible). The host agent's reasoning identifies critical changes directly from the structured `export-cognitive-aid` payload — no second-model pass.

**Size:** M (workflow.md / phases.md sections + 10 hallucination-guardrail rules)
**Files:** `plugins/flow-next/skills/flow-next-make-pr/workflow.md`, `plugins/flow-next/skills/flow-next-make-pr/phases.md`

## Approach

- **Critical-changes priority order** (host agent applies in this sequence, capped at 7 bullets total):
  1. High-churn (top 5 by `additions+deletions` from `diff_summary.high_churn_files`)
  2. Cross-module (`diff_summary.cross_module_changes` array)
  3. Public interface (`diff_summary.public_exports_changed` — `removed` items are potentially breaking, NEVER weaken to non-breaking)
  4. Security-sensitive paths (`diff_summary.security_sensitive_paths`)
  5. Behavior-visible (paths matching `commands/`, `routes/`, `pages/`, `app/`)
- **R-ID coverage table** — table layout exact:
  ```markdown
  | R-ID | Acceptance criterion | Task | Evidence |
  |------|----------------------|------|----------|
  | R1   | <text, max 120 chars, ellipsis> | [fn-N.1](.flow/tasks/fn-N.1.md) | [`<sha7>`](../../commit/<sha>) |
  ```
  - Mapping derived ONLY from payload `tasks[].satisfies[]` — never inferred. If R-ID has no satisfying task in payload, render `⚠️ uncovered` in Task column. Body must explicitly note the gap so reviewer knows.
  - Truncate criterion text to 120 chars + ellipsis.
- **Hallucination guardrails (skill prose includes these as load-bearing rules — informed by practice-scout findings):**
  1. **No hallucinated file references** — only paths from `diff_summary.files[]`, never fabricate from spec/intent.
  2. **No hallucinated symbol names** — derive only from `public_exports_changed`.
  3. **No hallucinated SHAs** — SHAs come from payload only.
  4. **No "non-breaking" weakening** — every `public_exports_changed.removed` is potentially breaking; never reclassify.
  5. **No copy-pasted diff content** — body talks ABOUT the diff (paths, churn, structure); never quotes code.
  6. **No inflated scope** — every claim traces to R-ID coverage table or `done_summary`; if doesn't trace, drop.
  7. **No R-ID misattribution** — `tasks[].satisfies[]` is the source of truth; don't infer from titles.
  8. **No stale references** — cross-check against `diff_summary.files[]` status (file marked `D` shouldn't appear in body as if existing).
  9. **No invented "why"** — Decision Context section is read-only mirror of `.flow/memory/knowledge/decisions/` + spec `## Decision Context`; never paraphrase or extend.
  10. **Trace every claim** — the meta-rule: every claim in the body must trace to a structured field in the export payload.
- **TL;DR composition rule:** 3-5 bullets, each one a single-line summary in plain language. Drawn from `epic.spec_sections.goal_and_context` first paragraph + `tasks[].done_summary` first sentence (top 5 by lines-changed).
- **Section omission discipline:** if `tasks_summary.uncovered_r_ids` is empty AND no critical changes detected (heuristic: <5 files, <50 LOC, no module-boundary signal), Critical Changes section is still included with the lead bullet stating "Limited churn — review the R-ID coverage table for surface area." Empty TL;DR or empty R-ID coverage = the body shouldn't be generated; abort with "epic has no work to summarize" message.

## Investigation targets

**Required:**
- `.flow/specs/fn-42-flow-nextmake-pr-pr-as-cognitive-aid.md` (Architecture & Data Models §PR body template) — the canonical body shape
- Task 1's output structure for `export-cognitive-aid` payload — workflow.md prose references payload field names verbatim
- `plugins/flow-next/skills/flow-next-audit/workflow.md` (Phase 4 prose pattern) — how a workflow describes "render this section using these inputs"

## Acceptance

- [ ] `workflow.md` Phase 2 prose specifies the body section order: Title + summary block + TL;DR + R-ID coverage table + Critical changes (Decisions / Memory / Glossary / Open items / Where to look come in Task 4; Structural changes mermaid in Task 5).
- [ ] R-ID coverage table format documented exactly (markdown table syntax, column order, link conventions, ⚠️ uncovered handling, 120-char ellipsis rule).
- [ ] Critical-changes section documents the 5-tier priority (high-churn → cross-module → public interface → security-sensitive → behavior-visible) with the 7-bullet cap and per-tier triggering condition mapping to `diff_summary` field names.
- [ ] Hallucination-guardrail rules (10 items above) appear as a numbered subsection in workflow.md, framed as load-bearing — every claim in body must trace to a payload field.
- [ ] Section-omission rule documented: empty content → omit entire heading; never empty placeholder. Empty TL;DR / empty R-ID coverage → abort.
- [ ] No code snippets in workflow.md that would actually generate the body (the host agent does that). Workflow tells the agent WHAT to render and WHAT NOT to fabricate; doesn't write the renderer.

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
