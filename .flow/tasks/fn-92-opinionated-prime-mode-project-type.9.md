---
satisfies: [R13, R19]
---

## Description
Flip the eval green + re-baseline the smoke expectation.

**Size:** M | **Files:** `optimization/prime/`, `plugins/flow-next/tests/test_prime_eval.py`, skill files (fixes only)

## Approach
- Run the task-4 harness against fixtures + the reference-repo expectation rows; fix skill-side regressions it finds; un-skip the unittest wrapper.
- Re-baseline R13: assessment of this repo produces the NEW headline shape with all 48 legacy criteria present and scored (resolution 14) - record as an expectation row, not byte-parity.
- Prose-contract tests per test_model_routing_scaffold.py pattern: canonical AND mirror carry the SV4 contract strings, whitelist table entries, stacks.md row schema.

## Key context
- This is the LAST implementation task: run impl-review with a wide base (git merge-base HEAD main) per the final-integration memory rule.

## Acceptance
- [ ] Emitter fixture expectations pass in CI (R19); wrapper un-skipped, 3-OS portable; live-repo eval runs non-CI with provenance recorded
- [ ] R13 re-baselined expectation recorded and passing (resolution 14)
- [ ] Prose contracts pin SV4 wording + whitelist + row schema on canonical AND mirror
- [ ] Wide-base impl-review noted for reviewers

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
