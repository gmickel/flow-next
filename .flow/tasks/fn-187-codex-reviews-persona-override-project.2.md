---
satisfies: [R3]
---
# fn-187-codex-reviews-persona-override-project.2 Plan-review prompt gains the 'You ARE the reviewer' role anchor (template + fallback, pins updated)

## Description
R3 - Port the role-anchor paragraph that impl/standalone/completion review prompts already open with ('**You ARE the reviewer - review directly.** Do not invoke any flow-next skill, `flowctl <backend>` review command, or a nested agent/backend to perform this review: this prompt already reached you through that machinery, and nesting it fails inside the sandbox (app-server init) and can only self-review.') into: plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md AND the PLAN_REVIEW_PROMPT_FALLBACK constant in flowctl.py (~:9433) - the template and fallback must stay byte-identical (test_review_prompt_template_parity). Match the placement/formatting the other three prompts use (read impl-review-prompt.md line ~3 for the pattern). Update the two SHA pins in tests/test_prompt_text_pinned.py (the plan template hash and the plan fallback constant hash) in the SAME commit, and state the prompt rationale in the commit message body (this is the deliberate-change path the pin test exists to audit). Run test_prompt_text_pinned, test_review_prompt_constraints (template parity + generated-mirror checks will need the codex mirror regen - the orchestrator runs sync-codex at close-out, but you may run ./scripts/sync-codex.sh yourself if test_prompt_templates_match_generated_codex_mirrors requires it to go green, then run it a second time to prove idempotency). Touch nothing else.

## Acceptance
R3 met: anchor present in template + fallback (byte-identical parity), both SHA pins updated with rationale in the commit message, prompt suites green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
