---
satisfies: [R15, R16, R17, R18, R19]
---

## Description

Phase 2 body context-section rendering: Decisions made, Memory left behind, Glossary / strategy notes, Open items, Where to look. Each section emits only when there's content (no empty placeholders). "Where to look" is the methodology #4 reviewer-focus list — formatted as questions, not labels (informed by practice-scout finding).

**Size:** M (workflow.md / phases.md prose for 5 sections)
**Files:** `plugins/flow-next/skills/flow-next-make-pr/workflow.md`, `plugins/flow-next/skills/flow-next-make-pr/phases.md`

## Approach

- **Decisions section** (R15): enumerate `memory_during_epic.decisions[]` from payload. Each entry → `**<title>** ([<id>](.flow/memory/knowledge/decisions/<file>)) — <first_sentence>. Alternatives considered: <alternatives_considered>.` Section omitted if empty.
- **Memory left behind section** (R16): enumerate `memory_during_epic.bugs[]` and `memory_during_epic.architecture_patterns[]`. One line per entry: `\`<id>\` — <first_sentence>`. Helps future debuggers find via `memory-scout`. Section omitted if both empty.
- **Glossary / strategy notes section** (R17): emits only when content exists.
  - Glossary: `**Glossary:** added \`<term>\`, renamed \`<old>\` → \`<new>\` (<N> files), removed \`<term>\`.` Each clause omitted if empty array.
  - Strategy: `**Strategy:** served tracks \`<track-1>\`, \`<track-2>\`. <Drift note if applicable>` from `strategy_alignment.tracks_served[]` + `drift_flagged[]`.
  - Heading omitted entirely if both glossary and strategy contributions empty.
- **Open items section** (R18): aggregate three sources: <!-- Updated by plan-sync: fn-42.1 emits deferred_findings as branch-slug-keyed sink, not per-task; review_receipts is empty in v1 -->
  - Spec `## Open Questions` block (already parsed into payload at `epic.spec_sections.open_questions`)
  - Deferred impl-review findings from `deferred_findings[].items[]` (v1 reads one branch-slug sink at `.flow/review-deferred/<branch-slug>.md`; items have no `task_id` attribution — provenance breadcrumb cites the branch / sink path, not a specific task)
  - Epic-review-flagged items — read directly via `flowctl show <epic-id> --json | jq '.completion_review_status'` (NOT in the export-cognitive-aid payload; v1's `review_receipts: []` is always empty per the implementation comment in flowctl.py)
  - Each item formatted as markdown checkbox with provenance breadcrumb: `- [ ] <item> — deferred from impl-review (branch sink)` / `— open question from spec` / `— flagged by epic-review`
  - Section omitted if all three sources empty
- **Where to look section** (R19, refined per practice-scout): explicit reviewer-focus list, formatted as **questions** not labels. Categories:
  - **Architecture:** drawn from spec `decision_context[]`. Format: `**Architecture:** \`<file:line>\` — <one-sentence focus question, e.g. "Does the abstract base class hierarchy hold up if a fourth implementation arrives?">`
  - **Security:** when `diff_summary.security_sensitive_paths` non-empty. Format: `**Security:** \`<file>\` — Was the trust boundary preserved here?` (or similar question form).
  - **Business correctness:** when files matching `commands/`, `routes/`, `pages/`, `app/` are touched. Format: `**Business correctness:** \`<file>\` — Does this still match the intended user-facing behavior?`
  - **Performance:** when files matching `hot-path` heuristics fire (loops, queries, render functions). Format: `**Performance:** \`<file>\` — Is the new code path on a hot path?`
  - **Tests** (5th category, refined per practice-scout): when test coverage is thin (no `*.test.*` / `*_test.*` / `tests/` files in diff). Format: `**Tests:** No new tests in this PR — what behavior assertion would catch a regression?`
  - One-sentence focus prompts must be questions; activate reviewer cognition more than labels.
  - Section omitted if no signals fire.
- **Echo-chamber risk mitigation:** every section's prose includes a "What this section MUST NOT do" callout to prevent the host agent from inventing content. E.g. for Decisions section: "MUST NOT paraphrase or extend the decision body — read-only mirror of the memory entry's first sentence."

## Investigation targets

**Required:**
- Task 1's `cmd_epic_export_cognitive_aid` payload schema — workflow.md prose references field names verbatim
- `plugins/flow-next/scripts/flowctl.py` memory frontmatter parser — to know what `alternatives_considered` looks like (string or list)
- `.flow/memory/knowledge/decisions/` — read 1-2 example entries to validate the rendering shape

**Optional:**
- `plugins/flow-next/skills/flow-next-audit/workflow.md` — Phase 5 reporting prose pattern
- Methodology line 540 (mickel.tech ref) — the "high-leverage decisions agent can't self-verify" framing

## Acceptance

- [ ] `workflow.md` Phase 2 prose specifies all 5 context sections (Decisions / Memory / Glossary-strategy / Open items / Where to look) with explicit field-name references to the export-cognitive-aid payload.
- [ ] Each section's omission rule documented: section heading omitted entirely (not left empty) when content is empty.
- [ ] Open items section aggregates 3 sources (spec `## Open Questions` from `epic.spec_sections.open_questions`, `deferred_findings[].items[]` branch-slug sink, epic-review-flagged via `flowctl show <epic-id> --json` `.completion_review_status` — NOT from `review_receipts` which is empty in v1) with provenance breadcrumb per item.
- [ ] Where-to-look section uses **questions** not labels for focus prompts. 5 categories documented (Architecture / Security / Business correctness / Performance / Tests). Each category's trigger condition references concrete payload signals.
- [ ] Each section includes a "What this section MUST NOT do" callout — read-only mirror of source data, no paraphrasing or extending.
- [ ] No code snippets in workflow.md that would actually generate sections — prose tells host agent WHAT to render.

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
