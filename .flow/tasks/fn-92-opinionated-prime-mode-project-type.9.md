---
satisfies: [R13, R19]
---

## Description
Flip the eval green + re-baseline the smoke expectation.

**Size:** M | **Files:** `optimization/prime/`, `plugins/flow-next/tests/test_prime_eval.py`, skill files (fixes only)

## Approach
- Run the task-4 harness against fixtures + the reference-repo expectation rows; fix skill-side regressions it finds; un-skip the unittest wrapper.
- Re-baseline R13 as a BLOCKING non-CI full-prime smoke protocol (final review round): controlled scout/emitter evidence + disposable repos; a documented runner command executes the COMPLETE prime flow and asserts: all 48 legacy criterion IDs present and scored, hard-gate Level-2 cap fires on a broken-build fixture, group scores excluded from maturity math, per-surface aggregation, the verdict headline shape, and `git status --porcelain` unchanged pre/post (non-mutating policy proof); model/version/result provenance persisted with a pass threshold.
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
