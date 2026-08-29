---
satisfies: [R1, R2, R3, R4]
---
# fn-210-comment-as-alibi-finding-class-in-code.1 Implement Comment-as-alibi finding class in code review prompts

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added the comment-as-alibi finding class to the impl-review and standalone-review prompts (constant + template, byte-identical): a comment justifying a workaround flags the underlying code, severity is judged from the workaround, and rewriting or deleting the comment alone does not resolve the finding. Keep-list copied verbatim from the worker authoring rule. Hash pins and rendered fixtures updated in the same commit; codex mirror regenerated idempotently; CHANGELOG Unreleased entry added. Implemented via the no-plan route with a grok-4.6 bridge worker; in-host review verdict SHIP; full suite (4545) + ruff green.
## Evidence
- Commits: 27fc137e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_review_prompt_template_parity -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: