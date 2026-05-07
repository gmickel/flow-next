---
satisfies: [R10, R11, R12, R13, R14]
---

## Description

Phase 3 mermaid generation: trigger conditions, shape selection, hard caps, prose-summary-precedes-diagram rule, `--no-mermaid` skip flag. Plus a separate `mermaid-rules.md` ref file (informed by practice-scout) that codifies the reserved-word + special-char escape list so the host agent doesn't have to remember it.

**Size:** M (one new ref file + workflow.md Phase 3 section)
**Files:** `plugins/flow-next/skills/flow-next-make-pr/mermaid-rules.md`, `plugins/flow-next/skills/flow-next-make-pr/workflow.md`

## Approach

- **Trigger conditions in workflow.md Phase 3** (any → produce diagram, all-empty → skip section entirely):
  1. `cross_module_changes[]` non-empty
  2. `public_exports_changed[]` non-empty
  3. New top-level directory (file added in path that didn't exist on `base_ref`)
  4. Removed top-level directory (all files of dir in `--diff-filter=D`)
  5. >15 files in >3 distinct modules (high-fan-out epic — overview helps)
  - Skip if `--no-mermaid` flag passed
  - Skip if diff is purely additive within one module + <50 LOC (clutter > value)
  - Skip if repo has no detectable module structure (no `src/`, `plugins/`, `app/`, etc.)
- **Shape selection** (host agent picks one per trigger):
  - `flowchart LR` — module-level dependency changes (default for trigger 1)
  - `classDiagram` — type/class additions/removals (when `public_exports_changed` includes class symbols)
  - `sequenceDiagram` — new API endpoint or protocol flow (route handlers added)
  - `graph TB` — high-level "epic touches these N areas" overview (default for trigger 5)
- **Hard caps** (enforced in workflow.md prose + via post-render validator):
  - Max 3 diagrams per PR (more = clutter; reviewer tunes out)
  - Max 12 nodes per diagram (readability collapses past)
  - Max 25 edges per diagram (same readability cliff)
  - Max 12K characters per codefence (GitHub truncates above; safe margin)
  - If trigger conditions would produce >3 diagrams, collapse to ONE high-level overview
  - If a diagram would exceed 12 nodes, group by module/abstraction (e.g. "5 scout agents" → one node labeled `scouts (5)`)
- **`mermaid-rules.md` ref file** — separate file the workflow loads. Contains:
  - **Reserved words** that MUST be escaped or renamed: `end`, `default`, `subgraph`, `class`, `state`, `direction`, `click`, `style`, `o` and `x` as connecting nodes
  - **Special-character escape rule:** ALWAYS quote labels containing `(`, `)`, `:`, `&`, `@`, `/`, `#`, `;`. Use `A["Label with (parens) & colon:"]`. HTML-entity fallback: `#quot;` for `"`, `#35;` for `#` (decimal codes only, not hex).
  - **Shape decision matrix** with one example per shape (4 short examples)
  - **Validation checklist** for the host agent before emitting:
    - Quotes balanced
    - No bare `end` as node ID
    - No emoji or MathJax (silent rendering break)
    - No relative/internal links (must be absolute)
    - classDiagram: no inheritance cycles
    - flowchart: arrow chars (`>`, `->>`) preferred over ambiguous shapes
    - Total chars ≤12K per codefence
- **Prose-summary-precedes-diagram rule (R13):** every mermaid codefence is preceded by a one-paragraph plain-language description of the structural change. Diagram is supplementary; prose is load-bearing. Forges that don't render mermaid (rare but possible) still convey the change via the prose.
- **`--no-mermaid` flag (R14):** Phase 3 skipped entirely — no diagrams, but prose summaries still produced when triggers would have fired (so the section isn't silently empty).
- **Post-render validation:** workflow includes a "before emitting, host agent reviews each codefence against `mermaid-rules.md` validation checklist" step. If any rule violated, agent re-renders with the issue corrected.

## Investigation targets

**Required:**
- Task 1's `diff_summary` payload structure — particularly `cross_module_changes`, `public_exports_changed`, `modules_touched` arrays
- `https://mermaid.js.org/syntax/flowchart.html` — flowchart syntax (already documented by docs-scout)
- `https://mermaid.js.org/syntax/classDiagram.html` — classDiagram syntax
- `https://mermaid.js.org/syntax/sequenceDiagram.html` — sequenceDiagram syntax

**Optional:**
- `https://github.com/mermaid-js/mermaid/issues/325` — reserved words / lack of escaping (canonical reference)
- `https://github.com/mermaid-js/mermaid/issues/7590` — unquoted node label parse errors

## Acceptance

- [ ] `plugins/flow-next/skills/flow-next-make-pr/mermaid-rules.md` exists with: reserved-word list, special-char escape list, shape decision matrix (4 examples — flowchart LR / classDiagram / sequenceDiagram / graph TB), validation checklist (8 items minimum).
- [ ] `workflow.md` Phase 3 prose documents the 5 trigger conditions, shape selection by trigger, hard caps (max 3 diagrams, max 12 nodes, max 25 edges, max 12K chars), skip rules.
- [ ] Each diagram in the rendered body is preceded by a one-paragraph prose summary in plain language. Workflow.md prose enforces this — the diagram is supplementary; prose is the load-bearing description.
- [ ] `--no-mermaid` flag skips diagram emission but prose summaries still produced when triggers would have fired.
- [ ] Workflow.md instructs the host agent to validate each codefence against `mermaid-rules.md` checklist before emitting; re-render on violation.
- [ ] Section omitted entirely when zero triggers fire — never an empty `## Structural changes` heading.

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
