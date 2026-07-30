---
satisfies: [R3]
---
# fn-136-structured-review-artifact-schema-in.4 Prompt-template tightening + no-new-LLM guards

## Description
Tighten the flowctl Output Format blocks so parsing is reliable; prove the constraints.

**Size:** S

**Files:** flowctl.py review prompt templates; sync-codex run; a constraint-guard test.

### Approach
- Tighten ONLY where the .1 survey found ambiguity (e.g. mandate File:Line even for repo-wide findings via "File:Line: -", standardize R-ID mention form); templates live in flowctl python so most backends need zero skill-prose change; if rp/host skill prose needs a line, measure token delta <= 0.
- Guard test: the diff introduces no new subprocess/LLM invocation sites (grep-based assertion over flowctl.py's invocation inventory - document the mechanism).
- FLOW-NEXT-ONLY SAFETY GUARD (binding): assembled-prompt diffs across the fn-130 reached-path b0 fixtures must be confined to the '## Output Format' blocks - zero changes to review instructions, criteria, rubrics, or any other prompt content (fixture-diff assertion). Format constraints may only DISAMBIGUATE the already-mandated shape (e.g. 'File:Line: -' for repo-wide findings), never add requirements that could shift reviewer judgment.
- Run scripts/sync-codex.sh twice (idempotency) if any skill prose touched.

## Acceptance
- [ ] Template tightening per survey; token-delta <= 0 for any prose touch; sync-codex idempotent (R3).
- [ ] Fixture-diff guard proves prompt changes confined to Output Format blocks (flow-next-only behavior preserved) (R3).
- [ ] No-new-LLM guard in place (R3).

## Done summary
Tightened all review prompt Output Format contracts to parser-compatible
severity, confidence, classification, File:Line, canonical R-ID, problem, and
suggestion fields. Added explicit repo-wide `File:Line: -` parsing, immutable
format-only prompt guards across fn-130 corpus variants, SHA-bound real-token
evidence, Codex mirror parity/idempotency checks, and AST-based no-new-invocation
guards.

RepoPrompt CE converged to SHIP in the same context/chat after three fix rounds.
Final verification: 231 focused tests, 3,387 full-suite tests, and pinned Ruff
0.16.0 all green. Actual cl100k_base/o200k_base deltas are non-positive for
all eleven assembled prompt variants.
## Evidence
- Commits: 4d0dae0b8b93bdc39a34c86a93846bcb86197c52, 54b9e8e48863062990a12b54cc3c9c5506047a8e, d6c98db7a95251e5e7c3fe9b689b7081a067a267, 75559519730b253aba28eb4c66c90260f4b9bfea
- Tests: baseline: none, cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_template_parity test_review_prompt_constraints test_review_findings_parser test_backend_spec test_prompt_text_pinned test_tracker_distribution -q (231 passed), python3 scripts/run_tests_parallel.py (3387 passed, 0 failures, 0 errors, 4 skipped), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh twice (idempotent)
- PRs: