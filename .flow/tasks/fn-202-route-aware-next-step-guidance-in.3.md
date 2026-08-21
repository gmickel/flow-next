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
Closed the doc/conduct/harness surfaces for the fn-202 closer changes: pipeline-variations.md gains the closers-apply-this-rule line under "What holds on every route" plus two reciprocal `## See also` entries (capture `workflow.md#phase-6-suggested-next-step-r16`, plan `references/next-steps-menu.md`) in the existing `[label](path#anchor) - description` style; one falsifiable `- [ ]` conduct row each in agent_docs/conduct/capture.md (exactly-one Recommended-next line with reason + alternative above the unchanged `Next:` menu, no rubric copy, chart never recommended) and plan.md (exactly-one line above the numbered options, skip-plan-review must name one of the two ceremony shapes, AUTONOMOUS output carries no line); CHANGELOG `## Unreleased` created with a user-outcome-first entry, no version manifest touched.

Harness sync (R5): grep of scripts/sync-codex.sh recorded - the only heredoc replacement block (`SECTION3C`) targets flow-next-work/phases.md; plan steps.md gets only sed scout-name substitutions; none of the five touched prose files (capture workflow.md, rewrite-mode.md, split-proposal.md, next-steps-menu.md, plan steps.md) is covered by a hardcoded block, so the fn-202.1/.2 prose transforms through. sync-codex.sh run twice: first run brought 18 insertions into the mirror (4 files), second run produced zero diff; mirror committed with the canonical change. No Claude-builtin references in the new mirror prose (grep for AskUserQuestion/subagent_type/Explore/claude- clean).

Conduct dogfood (variant named per row):
- capture (base path, scratch scenario: the just-captured fn-202 shape - decisions resolved, no open [inferred], no Parked unknowns): rendered Phase 6 footer produced exactly one `Recommended next: /flow-next:plan <id>` line (reason: decisions resolved, near-zero remaining risk; alternative: work may suffice once tasks exist) above the verbatim `Next:` menu; no rubric text; chart not a target -> PASS.
- plan (interactive menu, scratch scenario: fn-202's own 3-task docs/prose plan): rendered menu carried exactly one line - skip recommendation naming the docs/chore-class ceremony shape with `/flow-next:plan-review` as the named alternative - above the unchanged numbered options; AUTONOMOUS path structurally recommendation-free (next-steps-menu.md loads only interactively) -> PASS.

baseline: green (focused suite `test_prompt_text_pinned test_skill_prose_diet` pre-edit)
Verify: `flowctl gate classify` -> FULL (force-full codex/ prefix); `gate check` -> RUN (no honorable receipt); full suite green (192 files / 4436 tests / 0 failures), ruff 0.16.0 clean; receipt minted `f61a4d78-unittest`.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
## Evidence
- Commits: f61a4d78
- Tests: python3 scripts/run_tests_parallel.py (192 files/4436/0 at f61a4d78, receipt minted), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent), dogfood: capture base path PASS, plan interactive menu PASS
- PRs:
stage: impl-review - ran (host conductor review, SHIP; anchor nit verified fixed)
stage: completion-review - skipped(user-directed: conductor reviewed each task diff + combined; formal backend review deferred to PR comments per instruction)
stage: plan-sync - skipped(empty: no downstream todo tasks)
