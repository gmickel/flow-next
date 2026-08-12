---
satisfies: [R5]
---
# fn-189-human-first-visual-digest-skill.3 make-pr: diff-fenced structural sketches in ## Structural changes

## Description
Extend `plugins/flow-next/skills/flow-next-make-pr/mermaid-rules.md` (new section or sibling file linked one level deep from it) licensing a diff-fenced structural sketch (file-tree or call-tree shape, per the spec's shape 5 examples) as an alternate emission when: (a) the collapse-to-one-overview rule in section 4 would fire (more than 3 candidate diagrams), or (b) a trigger fires marginally (a diagram would have fewer than 4 nodes). Sketch obeys the SAME hallucination guardrails (section 7: paths from `diff_summary.files[]`, edges from `cross_module_changes[]`, no invented nodes) and the prose-precedes-visual rule (make-pr's internal rule R13 in `mermaid-rules.md` section 5 - not an R-ID of this spec). State explicitly: sketches never count against the 3-diagram mermaid cap; `--no-mermaid` also suppresses sketches (the section is omitted entirely, unchanged semantics). DO NOT touch `pr-cognitive-aid.md`, the v1 schema, flowctl validator/renderer, or `html-lens.md`. Update the Phase 3 pointer in workflow/phases prose only if it enumerates emission shapes.

## Acceptance
R5: sketch license documented with both trigger conditions, guardrail + prose-precedes-visual inheritance explicit, cap non-interaction and --no-mermaid behavior stated; git diff shows zero changes to pr-cognitive-aid.md/flowctl.py schema paths.

## Done summary
make-pr's `## Structural changes` now licenses a diff-fenced structural sketch (file-tree or call-tree) as an alternate emission alongside mermaid: new `mermaid-rules.md` §8 documents both trigger conditions (§4 collapse-to-one would fire; a trigger fires marginally with a <4-node diagram), inherits §7 hallucination guardrails and the §5 prose-precedes-visual rule (R13), states sketches sit outside the 3-diagram cap, and states `--no-mermaid` still omits the whole section. Phase 3 pointers in `workflow.md` (§3.2 + two Done-when lines) and `SKILL.md` name the alternate emission; the codex mirror was regenerated.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)
## Evidence
- Commits: 4ac591fa73c326de811579c75c0961d982565bd0
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_command_shim_flatten -q (OK; test_visual_skill not yet authored - task .5), python3 scripts/run_tests_parallel.py (191 files, 4489 tests, 1 failure: test_chart_docs_inventory skill-count pin 30!=29 - inherited, owned by task .4), uvx ruff@0.16.0 check . (All checks passed), ./scripts/sync-codex.sh x2 (idempotent; 1 pre-existing error: flow-next-visual allow_implicit_invocation - owned by task .4)
- PRs:
stage: plan-sync - ran (no drift; .5 references verified against mermaid-rules.md §8)
