---
satisfies: [R5]
---
# fn-189-human-first-visual-digest-skill.3 make-pr: diff-fenced structural sketches in ## Structural changes

## Description
Extend `plugins/flow-next/skills/flow-next-make-pr/mermaid-rules.md` (new section or sibling file linked one level deep from it) licensing a diff-fenced structural sketch (file-tree or call-tree shape, per the spec's shape 5 examples) as an alternate emission when: (a) the collapse-to-one-overview rule in section 4 would fire (more than 3 candidate diagrams), or (b) a trigger fires marginally (a diagram would have fewer than 4 nodes). Sketch obeys the SAME hallucination guardrails (section 7: paths from `diff_summary.files[]`, edges from `cross_module_changes[]`, no invented nodes) and the R13 prose-precedes-visual rule. State explicitly: sketches never count against the 3-diagram mermaid cap; `--no-mermaid` also suppresses sketches (the section is omitted entirely, unchanged semantics). DO NOT touch `pr-cognitive-aid.md`, the v1 schema, flowctl validator/renderer, or `html-lens.md`. Update the Phase 3 pointer in workflow/phases prose only if it enumerates emission shapes.

## Acceptance
R5: sketch license documented with both trigger conditions, guardrail + R13 inheritance explicit, cap non-interaction and --no-mermaid behavior stated; git diff shows zero changes to pr-cognitive-aid.md/flowctl.py schema paths.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
