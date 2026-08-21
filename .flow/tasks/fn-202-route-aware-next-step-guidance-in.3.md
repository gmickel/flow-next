---
satisfies: [R5, R6, R7]
---
# fn-202-route-aware-next-step-guidance-in.3 Docs cross-links, conduct rows, CHANGELOG, mirror sync + transform-through checks

## Description
Close the doc/conduct/harness surfaces for the two closer changes.

**Files:** plugins/flow-next/docs/pipeline-variations.md (one line under '## What holds on every route' noting the capture/plan closers apply this rule at the decision point + reciprocal `## See also` entries linking workflow.md#phase-6 and next-steps-menu.md, matching the existing `[label](path#anchor) - description` style); agent_docs/conduct/capture.md + plan.md (one falsifiable `- [ ]` row each, matching existing register: capture — 'Phase 6 printed exactly one Recommended next: line (reason + alternative) above the unchanged Next: menu; no rubric text copied; chart never recommended'; plan — 'interactive menu printed exactly one Recommended next: line above the numbered options; a skip-plan-review recommendation named one of the two ceremony shapes; AUTONOMOUS output carried no recommendation'; note which variant was dogfooded); CHANGELOG.md (create `## Unreleased`, user-outcome-first entry, no version bump).

**Harness sync (R5):** grep scripts/sync-codex.sh for replacement blocks covering ALL five touched prose files (capture workflow.md, rewrite-mode.md, split-proposal.md, next-steps-menu.md, plan steps.md) — expected: only steps.md sed scout-name substitutions, no heredocs; then ./scripts/sync-codex.sh TWICE (idempotent), commit the mirror diff. Confirm no Claude-builtin references were introduced (Cursor/Droid/Grok/OpenCode consume as-is; OpenCode needs nothing further). Dogfood: run capture once (base path) and plan once (interactive menu) in a scratch invocation; mark each conduct row pass/fail before done.

**Touches:** [plugins/flow-next/docs/pipeline-variations.md, agent_docs/conduct/capture.md, agent_docs/conduct/plan.md, CHANGELOG.md, plugins/flow-next/codex/**]

## Acceptance
- pipeline-variations.md notes the closers apply its rule + two See-also reciprocal links in existing style
- One new falsifiable conduct row in each of capture.md/plan.md incl. the skip-shape and no-chart checks; dogfood run per skill recorded pass/fail with variant named
- CHANGELOG `## Unreleased` entry present, outcome-first; no version manifest touched
- sync-codex.sh grep recorded (no heredoc covers the five files); sync run twice with zero second-run diff; mirror committed
- Full gate green at spec end: python3 scripts/run_tests_parallel.py + uvx ruff@0.16.0 check .

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
