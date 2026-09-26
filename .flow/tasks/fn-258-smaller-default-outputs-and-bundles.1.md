---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
---
# fn-258-smaller-default-outputs-and-bundles.1 Implement Smaller default outputs and bundles (audit wave 4)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented all ten fn-258 R-IDs. The worker anchor bundle now carries the text memory index, the glossary entries the task names (`glossary list --match`), the spec record without `review_attempts`/`tracker`, and `git status --short --branch`. Measured sizes dropped from 165-190k to 57-65k chars. The fn-83 comprehension eval was re-run on both bundles from one state and passed (lean 7/7 = current 7/7 on all three sets; see the q4 caveat below). Skill-side projections cover R3-R5, R7, R8, and R10. The subagent-drafted tracker-sync trim (R9) cuts the four references by about 35%, with each dropped step checked against facade code. For R6, every command shim is user-only and model-side invocations name `flow-next:flow-next-<name>`, rewritten to `$flow-next-<name>` in the Codex mirror.

stage: impl-review - ran [round 1 fan-out NEEDS_WORK (2 introduced: anchor fail-open regression; missed land/work command-form callers) .. round 2 SHIP]
Tier: session (jev intelligent 0.32) (actual: claude-opus-5-5)

Tests for enumerated error cases:
- R1: `test_anchor_bundle.py` covers the glossary skip reasons (no glossary, husk, no match), memory disabled, fail-open on git sections and on an unreadable task body (`UnreadableTaskBodyTest`), and per-section labeled-command equality.
- R2: `test_review_convergence_cap.py::test_spec_show_omits_ledgers_that_dedicated_readers_return`.
- R3: `test_glossary_match.py` covers term and alias hits, case and whitespace, whole words, no match, and no glossary.
- R6: `test_skill_id_invocations.py` covers shim frontmatter, target resolution, the command-form guard, and the named sites.

Decisions and deviations:
- The glossary matcher matches whole words. Substring matching hit short aliases such as `CI` and `pin` inside ordinary words and pulled in most of the glossary.
- The Ralph prompt templates were converted to skill ids, with their pinned hashes bumped. The spec treated them as user invocations, but `ralph.sh` renders the whole template into `claude -p`, so they are model-side. Left as command form, they would target now-hidden commands.
- The setup snippet sentinel stays `v2`. Bumping it re-prompts every install; the maintainer decides. Existing installs keep `/flow-next:prose` in their snippet until they refresh.
- Rejected review finding: OpenCode cannot resolve `flow-next:flow-next-<name>` literally. The base text's `/flow-next:<name>` was equally unresolvable there, so this is not a regression. Follow-up: an OpenCode-install rewrite of skill ids.
- Eval caveat: this worktree has no runtime state, so two dependency statuses read `todo`. Both arms answered q4 `todo`, and the key's `\bdone\b` regex passed that answer ("not done"). Scoring q4 as a fail, both arms are 6/6. A stricter q4 regex is an append-only follow-up.

Follow-ups (not built):
- An OpenCode skill-id rewrite at install.
- A stricter q4 regex in the fn-83 key.
- 17 codex actionable-sed patterns in `sync-codex.sh` that were already dead before this change.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: fc4f66171c30ff72005c31e186fef558e5d275a9, a96b3b0a3daea8081b117572b47419f75678a0d7
- Tests: python3 scripts/run_tests_parallel.py (5126 ran, 0 failures; green receipt a96b3b0a), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, python3 -m unittest test_anchor_bundle test_glossary_match test_skill_id_invocations test_review_convergence_cap, plugins/flow-next/scripts/glossary_smoke_test.sh (80/80), plugins/flow-next/scripts/smoke_test.sh (130 pass; 2 copilot live e2e INCONCLUSIVE: monthly quota exceeded), python3 optimization/worker-anchor/run_eval.py --arms bundle-lean,bundle-current (MERGE GATE PASS, 7/7 vs 7/7 x3), baseline: green (python3 scripts/run_tests_parallel.py 5115 ran pre-edit; ruff clean)
- PRs: